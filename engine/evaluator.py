# -*- coding: utf-8 -*-
"""
多模型测评引擎
负责调度题库 × 模型 × 地区变体的完整测评流程
"""

import json
import os
import time
from pathlib import Path

from tqdm import tqdm

from config import (
    QUESTION_BANK_PATH,
    EVAL_RESULTS_PATH,
    RESULTS_DIR,
    DEFAULT_TEMPERATURE,
    MAX_TOKENS,
    MAX_RETRIES,
    REGIONS,
)
from engine.prompt_templates import SYSTEM_PROMPT_SUBJECT, build_eval_prompt
from models import create_adapter, get_available_models


def load_question_bank(path: str = QUESTION_BANK_PATH) -> list[dict]:
    """加载题库"""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _load_completed_ids(results_path: str) -> set[str]:
    """加载已完成的测评记录ID，用于断点续评"""
    done = set()
    if not os.path.exists(results_path):
        return done
    with open(results_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
                done.add(rec["eval_id"])
            except (json.JSONDecodeError, KeyError):
                continue
    return done


def _make_eval_id(q_id: str, model_id: str, region: str) -> str:
    """生成唯一测评ID"""
    return f"{q_id}__{model_id}__{region}"


def _call_with_retry(adapter, prompt: str, max_retries: int = MAX_RETRIES) -> dict:
    """带重试的模型调用"""
    import openai

    for attempt in range(max_retries):
        try:
            return adapter.chat(
                prompt=prompt,
                system_prompt=SYSTEM_PROMPT_SUBJECT,
                temperature=DEFAULT_TEMPERATURE,
                max_tokens=MAX_TOKENS,
            )
        except openai.RateLimitError:
            wait = 2 ** (attempt + 1)
            print(f"    [限流] 等待 {wait}s 后重试...")
            time.sleep(wait)
        except openai.APIError as e:
            print(f"    [API错误] {e}，重试 {attempt+1}/{max_retries}")
            time.sleep(2)
    return {"model": adapter.model_id, "content": "", "usage": {}, "latency_ms": 0}


def run_evaluation(
    model_ids: list[str] | None = None,
    region_filter: list[str] | None = None,
    question_filter: list[str] | None = None,
    max_questions: int | None = None,
):
    """
    执行完整测评流程。

    Args:
        model_ids: 要测评的模型列表，None则全部
        region_filter: 地区变体过滤，None则全部
        question_filter: 题目ID过滤，None则全部
        max_questions: 最大题目数（用于快速测试）
    """
    # 准备
    os.makedirs(RESULTS_DIR, exist_ok=True)
    questions = load_question_bank()
    if question_filter:
        questions = [q for q in questions if q["id"] in question_filter]
    if max_questions:
        questions = questions[:max_questions]

    if model_ids is None:
        model_ids = get_available_models()
    regions = region_filter or REGIONS

    # 断点续评
    done_ids = _load_completed_ids(EVAL_RESULTS_PATH)

    # 创建适配器
    adapters = {}
    for mid in model_ids:
        try:
            adapters[mid] = create_adapter(mid)
            print(f"  [OK] {mid}")
        except ValueError as e:
            print(f"  [跳过] {mid}: {e}")

    if not adapters:
        print("没有可用的模型适配器，请检查 .env 中的 API Key 配置。")
        return

    total = len(questions) * len(adapters) * len(regions)
    done_count = 0
    new_count = 0

    print(f"\n开始测评: {len(questions)} 题 × {len(adapters)} 模型 × {len(regions)} 地区 = {total} 次")
    print(f"已完成: {len(done_ids)}, 待执行: {total - len(done_ids)}\n")

    with open(EVAL_RESULTS_PATH, "a", encoding="utf-8") as fout:
        pbar = tqdm(total=total, desc="测评进度")
        for q in questions:
            for region in regions:
                question_text = q["variants"].get(region, q["base_question"])
                for mid, adapter in adapters.items():
                    eval_id = _make_eval_id(q["id"], mid, region)
                    pbar.update(1)

                    if eval_id in done_ids:
                        done_count += 1
                        continue

                    result = _call_with_retry(adapter, build_eval_prompt(question_text))

                    record = {
                        "eval_id": eval_id,
                        "question_id": q["id"],
                        "dimension": q["dimension"],
                        "region": region,
                        "model": mid,
                        "question": question_text,
                        "response": result["content"],
                        "usage": result["usage"],
                        "latency_ms": result["latency_ms"],
                        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                    }

                    fout.write(json.dumps(record, ensure_ascii=False) + "\n")
                    fout.flush()
                    new_count += 1

                    # 简单限流：每次调用后短暂等待
                    time.sleep(0.3)

        pbar.close()

    print(f"\n测评完成! 新增 {new_count} 条, 跳过已完成 {done_count} 条")
    print(f"结果保存在: {EVAL_RESULTS_PATH}")


def load_eval_results(path: str = EVAL_RESULTS_PATH) -> list[dict]:
    """加载测评结果"""
    results = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                results.append(json.loads(line))
    return results
