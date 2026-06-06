# -*- coding: utf-8 -*-
"""
价值倾向分析模块 — LLM-as-Judge 评分
"""

import json
import os
import re
import time

from tqdm import tqdm

from config import (
    SCORE_RESULTS_PATH,
    RESULTS_DIR,
    JUDGE_TEMPERATURE,
    MAX_TOKENS,
    MAX_RETRIES,
)
from engine.prompt_templates import build_judge_prompt
from engine.evaluator import load_eval_results
from models import create_judge


def _parse_judge_output(text: str) -> dict | None:
    """从Judge回答中解析JSON评分结果"""
    # 尝试直接解析
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # 尝试提取 JSON 块
    match = re.search(r"\{[^{}]+\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass

    return None


def _validate_scores(scores: dict) -> dict | None:
    """校验评分是否合法"""
    dims = ["dim1", "dim2", "dim3", "dim4", "dim5"]
    result = {}
    for d in dims:
        v = scores.get(d)
        if v is None:
            return None
        try:
            v = int(v)
        except (ValueError, TypeError):
            return None
        if v < 1 or v > 5:
            return None
        result[d] = v
    result["reasoning"] = scores.get("reasoning", "")
    return result


def run_scoring(
    force_rescore: bool = False,
    max_samples: int | None = None,
):
    """
    对所有测评结果执行 LLM-as-Judge 评分。

    Args:
        force_rescore: 是否强制重新评分（覆盖已有结果）
        max_samples: 最大评分样本数（用于快速测试）
    """
    os.makedirs(RESULTS_DIR, exist_ok=True)
    eval_results = load_eval_results()

    if not eval_results:
        print("没有测评结果可评分，请先运行测评。")
        return

    if max_samples:
        eval_results = eval_results[:max_samples]

    # 加载已评分的 eval_id
    scored_ids = set()
    if not force_rescore and os.path.exists(SCORE_RESULTS_PATH):
        with open(SCORE_RESULTS_PATH, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    rec = json.loads(line.strip())
                    scored_ids.add(rec["eval_id"])
                except (json.JSONDecodeError, KeyError):
                    continue

    # 创建 Judge
    try:
        judge = create_judge()
    except ValueError as e:
        print(f"Judge 模型初始化失败: {e}")
        print("请检查 .env 中的 API Key 配置。")
        return

    print(f"Judge 模型: {judge.model_id}")
    print(f"待评分: {len(eval_results)} 条, 已完成: {len(scored_ids)}\n")

    new_count = 0
    fail_count = 0

    with open(SCORE_RESULTS_PATH, "a", encoding="utf-8") as fout:
        pbar = tqdm(eval_results, desc="评分进度")
        for record in pbar:
            eval_id = record["eval_id"]

            if eval_id in scored_ids:
                continue

            if not record.get("response"):
                continue

            judge_prompt = build_judge_prompt(
                question=record["question"],
                response=record["response"],
            )

            # 调用 Judge（带重试）
            parsed = None
            for attempt in range(MAX_RETRIES):
                try:
                    result = judge.chat(
                        prompt=judge_prompt,
                        temperature=JUDGE_TEMPERATURE,
                        max_tokens=MAX_TOKENS,
                    )
                    raw = result["content"]
                    parsed = _parse_judge_output(raw)
                    if parsed:
                        validated = _validate_scores(parsed)
                        if validated:
                            parsed = validated
                            break
                    print(f"    [解析失败] 重试 {attempt+1}/{MAX_RETRIES}")
                    time.sleep(1)
                except Exception as e:
                    print(f"    [Judge错误] {e}, 重试 {attempt+1}/{MAX_RETRIES}")
                    time.sleep(2)

            if parsed and _validate_scores(parsed):
                score_record = {
                    "eval_id": eval_id,
                    "question_id": record["question_id"],
                    "dimension": record["dimension"],
                    "region": record["region"],
                    "model": record["model"],
                    "scores": {
                        "dim1": parsed["dim1"],
                        "dim2": parsed["dim2"],
                        "dim3": parsed["dim3"],
                        "dim4": parsed["dim4"],
                        "dim5": parsed["dim5"],
                    },
                    "reasoning": parsed.get("reasoning", ""),
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                }
                fout.write(json.dumps(score_record, ensure_ascii=False) + "\n")
                fout.flush()
                new_count += 1
            else:
                fail_count += 1

            time.sleep(0.3)
        pbar.close()

    print(f"\n评分完成! 成功 {new_count} 条, 失败 {fail_count} 条")
    print(f"结果保存在: {SCORE_RESULTS_PATH}")


def load_score_results(path: str = SCORE_RESULTS_PATH) -> list[dict]:
    """加载评分结果"""
    results = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                results.append(json.loads(line))
    return results
