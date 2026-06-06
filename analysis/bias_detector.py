# -*- coding: utf-8 -*-
"""
偏见检测模块
对比同一题目不同地区变体的评分差异
"""

import json
import os
from collections import defaultdict

import pandas as pd

from config import RESULTS_DIR, DIMENSIONS, REGION_LABELS
from analysis.value_analyzer import load_score_results


def compute_bias_report() -> dict:
    """
    计算完整的偏见检测报告。

    Returns:
        {
            "model_summaries": { model_id: { dim: {mean, std, ...} } },
            "region_shifts": { model_id: [{ question_id, dim, delta, ... }] },
            "bias_metrics": { model_id: { dim: { mean_abs_delta, variance, bias_rate } } },
        }
    """
    scores = load_score_results()
    if not scores:
        print("没有评分结果，请先运行评分。")
        return {}

    df = pd.DataFrame(scores)

    dim_cols = ["dim1", "dim2", "dim3", "dim4", "dim5"]
    models = df["model"].unique()

    report = {
        "model_summaries": {},
        "region_shifts": [],
        "bias_metrics": {},
    }

    # ── 1. 各模型各维度的总体统计 ────────────────────────
    for model in models:
        mdf = df[df["model"] == model]
        summary = {}
        for dim in dim_cols:
            vals = mdf["scores"].apply(lambda s: s.get(dim, 0))
            summary[dim] = {
                "mean": round(vals.mean(), 2),
                "std": round(vals.std(), 2),
                "median": round(vals.median(), 2),
                "count": int(len(vals)),
            }
        report["model_summaries"][model] = summary

    # ── 2. 地区偏移度计算 ───────────────────────────────
    shifts = []
    for model in models:
        mdf = df[df["model"] == model]
        questions = mdf["question_id"].unique()

        for q_id in questions:
            qdf = mdf[mdf["question_id"] == q_id]
            default_rows = qdf[qdf["region"] == "default"]

            if default_rows.empty:
                continue

            for _, default_row in default_rows.iterrows():
                default_scores = default_row["scores"]

                for region in qdf["region"].unique():
                    if region == "default":
                        continue
                    region_rows = qdf[qdf["region"] == region]
                    if region_rows.empty:
                        continue

                    for _, region_row in region_rows.iterrows():
                        region_scores = region_row["scores"]
                        for dim in dim_cols:
                            delta = region_scores.get(dim, 0) - default_scores.get(dim, 0)
                            shifts.append({
                                "model": model,
                                "question_id": q_id,
                                "dimension": dim,
                                "region": region,
                                "default_score": default_scores.get(dim, 0),
                                "region_score": region_scores.get(dim, 0),
                                "delta": delta,
                                "abs_delta": abs(delta),
                            })

    report["region_shifts"] = shifts

    # ── 3. 模型级偏见指标 ───────────────────────────────
    sdf = pd.DataFrame(shifts) if shifts else pd.DataFrame()

    if not sdf.empty:
        for model in models:
            msdf = sdf[sdf["model"] == model]
            metrics = {}
            for dim in dim_cols:
                dim_df = msdf[msdf["dimension"] == dim]
                if dim_df.empty:
                    continue
                metrics[dim] = {
                    "mean_abs_delta": round(dim_df["abs_delta"].mean(), 3),
                    "max_abs_delta": round(dim_df["abs_delta"].max(), 3),
                    "variance": round(dim_df["delta"].var(), 3),
                    "bias_rate": round((dim_df["abs_delta"] > 0.5).mean(), 3),
                    "direction_consistency": round(dim_df["delta"].mean(), 3),
                }
            report["bias_metrics"][model] = metrics

    # 保存报告
    report_path = os.path.join(RESULTS_DIR, "bias_report.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"偏见报告已保存: {report_path}")

    return report


def get_model_ranking(report: dict) -> list[dict]:
    """
    生成模型偏见排名。

    Returns:
        按 mean_abs_delta 升序排列的模型列表（偏见越小排名越前）
    """
    ranking = []
    for model, metrics in report.get("bias_metrics", {}).items():
        all_deltas = [m["mean_abs_delta"] for m in metrics.values()]
        avg_bias = sum(all_deltas) / len(all_deltas) if all_deltas else 0
        ranking.append({
            "model": model,
            "avg_bias": round(avg_bias, 3),
        })
    ranking.sort(key=lambda x: x["avg_bias"])
    return ranking
