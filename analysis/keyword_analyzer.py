# -*- coding: utf-8 -*-
"""
关键词辅助分析模块
通过关键词频率分析模型回答中的价值倾向
"""

import json
import re
from collections import Counter

from analysis.value_analyzer import load_score_results

# ── 关键词词典 ──────────────────────────────────────────
KEYWORD_DICT = {
    "pro_economy": [
        "经济增长", "GDP", "就业", "产业发展", "税收", "招商引资",
        "企业利润", "经济效益", "竞争力", "收入", "民生改善",
    ],
    "pro_environment": [
        "生态修复", "环境保护", "生物多样性", "碳中和", "绿色发展",
        "可持续", "清洁能源", "减排", "环保", "蓝天",
    ],
    "pro_short_term": [
        "当务之急", "紧急", "迫在眉睫", "眼前", "短期", "尽快",
    ],
    "pro_long_term": [
        "长远", "可持续", "后代", "子孙", "未来", "代际",
    ],
    "pro_equity": [
        "公平", "公正", "平等", "弱势群体", "补偿", "转移支付",
        "区域协调", "帮扶", "不落下",
    ],
    "pro_efficiency": [
        "效率", "最优", "资源优化", "投入产出", "整体利益",
        "集中力量", "最大化",
    ],
}


def analyze_keywords(text: str) -> dict[str, int]:
    """分析一段文本中各关键词类别的出现次数"""
    counts = {}
    for category, keywords in KEYWORD_DICT.items():
        total = 0
        for kw in keywords:
            total += len(re.findall(kw, text))
        counts[category] = total
    return counts


def run_keyword_analysis() -> list[dict]:
    """
    对所有评分结果执行关键词分析。

    Returns:
        [{eval_id, model, region, dimension, keyword_counts, total_pro_economy, ...}]
    """
    scores = load_score_results()
    if not scores:
        print("没有评分结果，请先运行评分。")
        return []

    results = []
    for rec in scores:
        # 从原始测评结果中获取回答文本
        eval_results = _load_eval_by_id(rec["eval_id"])
        if not eval_results:
            continue

        text = eval_results.get("response", "")
        counts = analyze_keywords(text)

        results.append({
            "eval_id": rec["eval_id"],
            "model": rec["model"],
            "region": rec["region"],
            "dimension": rec["dimension"],
            "keyword_counts": counts,
            "economy_vs_env": counts.get("pro_economy", 0) - counts.get("pro_environment", 0),
            "short_vs_long": counts.get("pro_short_term", 0) - counts.get("pro_long_term", 0),
            "equity_vs_efficiency": counts.get("pro_equity", 0) - counts.get("pro_efficiency", 0),
        })

    return results


def _load_eval_by_id(eval_id: str) -> dict | None:
    """根据 eval_id 查找原始测评记录"""
    from engine.evaluator import load_eval_results

    for rec in load_eval_results():
        if rec["eval_id"] == eval_id:
            return rec
    return None
