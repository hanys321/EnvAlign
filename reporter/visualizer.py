# -*- coding: utf-8 -*-
"""
可视化模块
生成雷达图、热力图、箱线图等图表
"""

import os
import json

import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from config import RESULTS_DIR, DIMENSIONS

# 中文字体设置
plt.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei", "Arial Unicode MS"]
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["figure.dpi"] = 160
plt.rcParams["savefig.dpi"] = 220
plt.rcParams["axes.titlesize"] = 22
plt.rcParams["axes.labelsize"] = 17
plt.rcParams["xtick.labelsize"] = 14
plt.rcParams["ytick.labelsize"] = 14
plt.rcParams["legend.fontsize"] = 14

DIM_LABELS = [
    "经济发展↔环境保护",
    "短期利益↔长期可持续",
    "区域公平↔整体效率",
    "人类中心↔生态中心",
    "技术乐观↔预防原则",
]
DIM_SHORT = ["经济\nvs\n环保", "短期\nvs\n长期", "公平\nvs\n效率", "人类\nvs\n生态", "技术\nvs\n预防"]
DIM_SHORT_FLAT = ["经济vs环保", "短期vs长期", "公平vs效率", "人类vs生态", "技术vs预防"]
MODEL_LABELS = {
    "glm-4-flash": "GLM-4-Flash",
    "qwen-plus": "通义千问-Plus",
    "deepseek-chat": "DeepSeek-Chat",
    "doubao-pro": "豆包-Pro",
}


def _model_label(model: str) -> str:
    return MODEL_LABELS.get(model, model)


def plot_radar_chart(report: dict, output_dir: str | None = None):
    """
    为每个模型生成价值雷达图。
    """
    out_dir = output_dir or os.path.join(RESULTS_DIR, "figures")
    os.makedirs(out_dir, exist_ok=True)

    summaries = report.get("model_summaries", {})
    if not summaries:
        print("无模型评分数据，跳过雷达图。")
        return

    angles = np.linspace(0, 2 * np.pi, len(DIM_SHORT), endpoint=False).tolist()
    angles += angles[:1]

    fig, ax = plt.subplots(figsize=(11, 10), subplot_kw=dict(polar=True))

    colors = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd"]

    for i, (model, dims) in enumerate(summaries.items()):
        values = [dims.get(f"dim{j+1}", {}).get("mean", 3) for j in range(5)]
        values += values[:1]
        ax.plot(
            angles,
            values,
            "o-",
            linewidth=3,
            markersize=8,
            label=_model_label(model),
            color=colors[i % len(colors)],
        )
        ax.fill(angles, values, alpha=0.12, color=colors[i % len(colors)])

    ax.set_thetagrids(np.degrees(angles[:-1]), DIM_SHORT)
    ax.set_ylim(1, 5)
    ax.set_yticks([1, 2, 3, 4, 5])
    ax.set_yticklabels(["1", "2", "3", "4", "5"], fontsize=14)
    ax.tick_params(axis="x", pad=16, labelsize=15)
    ax.grid(linewidth=1.1, alpha=0.55)
    ax.set_title("各模型价值倾向雷达图", fontsize=24, fontweight="bold", pad=34)
    ax.legend(loc="upper right", bbox_to_anchor=(1.34, 1.12), frameon=True)

    path = os.path.join(out_dir, "radar_chart.png")
    fig.savefig(path, bbox_inches="tight", pad_inches=0.35)
    plt.close(fig)
    print(f"雷达图已保存: {path}")


def plot_bias_boxplot(report: dict, output_dir: str | None = None):
    """
    生成偏见检测箱线图：各模型在各维度上的地区偏移分布。
    """
    out_dir = output_dir or os.path.join(RESULTS_DIR, "figures")
    os.makedirs(out_dir, exist_ok=True)

    shifts = report.get("region_shifts", [])
    if not shifts:
        print("无地区偏移数据，跳过箱线图。")
        return

    sdf = pd.DataFrame(shifts)
    models = sdf["model"].unique()

    fig, axes = plt.subplots(1, len(models), figsize=(8.4 * len(models), 9.6), sharey=True)
    if len(models) == 1:
        axes = [axes]

    for idx, model in enumerate(models):
        msdf = sdf[sdf["model"] == model]
        data = [msdf[msdf["dimension"] == f"dim{j+1}"]["delta"].values for j in range(5)]

        bp = axes[idx].boxplot(
            data,
            labels=DIM_SHORT_FLAT,
            patch_artist=True,
            widths=0.62,
            medianprops={"color": "#B00020", "linewidth": 2.2},
            whiskerprops={"linewidth": 1.6},
            capprops={"linewidth": 1.6},
        )
        for patch in bp["boxes"]:
            patch.set_facecolor("#D9E2F3")
            patch.set_linewidth(1.5)

        axes[idx].axhline(y=0, color="red", linestyle="--", alpha=0.6, linewidth=1.6)
        axes[idx].set_title(_model_label(model), fontsize=26, fontweight="bold", pad=20)
        axes[idx].set_xlabel("评估维度", fontsize=22, fontweight="bold", labelpad=18)
        axes[idx].grid(axis="y", linestyle="--", alpha=0.28)
        axes[idx].tick_params(axis="x", rotation=24, labelsize=19, pad=8)
        axes[idx].tick_params(axis="y", labelsize=20, pad=8)
        if idx == 0:
            axes[idx].set_ylabel(
                "地区偏移度 Δ\n地区版本评分 - 默认版本评分",
                fontsize=23,
                fontweight="bold",
                labelpad=18,
            )

    fig.suptitle("各模型地区偏见分布（偏移度 Δ）", fontsize=32, fontweight="bold", y=1.035)
    fig.tight_layout(w_pad=3.2)

    path = os.path.join(out_dir, "bias_boxplot.png")
    fig.savefig(path, bbox_inches="tight", pad_inches=0.35)
    plt.close(fig)
    print(f"箱线图已保存: {path}")


def plot_model_comparison_bar(report: dict, output_dir: str | None = None):
    """
    生成模型间各维度评分对比柱状图。
    """
    out_dir = output_dir or os.path.join(RESULTS_DIR, "figures")
    os.makedirs(out_dir, exist_ok=True)

    summaries = report.get("model_summaries", {})
    if not summaries:
        print("无模型评分数据，跳过柱状图。")
        return

    models = list(summaries.keys())
    x = np.arange(len(DIM_SHORT))
    width = 0.8 / len(models)

    fig, ax = plt.subplots(figsize=(15.5, 8.2))
    colors = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd"]

    for i, model in enumerate(models):
        values = [
            summaries[model].get(f"dim{j+1}", {}).get("mean", 3) for j in range(5)
        ]
        bars = ax.bar(
            x + i * width,
            values,
            width,
            label=_model_label(model),
            color=colors[i % len(colors)],
            alpha=0.88,
        )
        ax.bar_label(bars, labels=[f"{v:.2f}" for v in values], padding=3, fontsize=11, rotation=90)

    ax.set_xlabel("评估维度", fontsize=18, labelpad=14)
    ax.set_ylabel("平均评分（1-5）", fontsize=18, labelpad=12)
    ax.set_title("各模型在各维度上的平均价值倾向评分", fontsize=24, fontweight="bold", pad=22)
    ax.set_xticks(x + width * (len(models) - 1) / 2)
    ax.set_xticklabels(DIM_SHORT_FLAT, fontsize=15)
    ax.set_ylim(0, 5.85)
    ax.tick_params(axis="y", labelsize=15)
    ax.grid(axis="y", linestyle="--", alpha=0.28)
    neutral = ax.axhline(y=3, color="gray", linestyle="--", alpha=0.65, linewidth=1.6, label="中立线")
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.13), ncol=5, frameon=True)
    ax.text(
        len(DIM_SHORT_FLAT) - 0.35,
        3.08,
        "中立线=3",
        fontsize=13,
        color="dimgray",
        ha="right",
    )

    fig.tight_layout(rect=[0, 0.08, 1, 1])
    path = os.path.join(out_dir, "dimension_comparison_bar.png")
    fig.savefig(path, bbox_inches="tight", pad_inches=0.35)
    plt.close(fig)
    print(f"柱状图已保存: {path}")


def generate_all_figures(report: dict | None = None, output_dir: str | None = None):
    """一键生成所有图表"""
    if report is None:
        from analysis.bias_detector import compute_bias_report
        report = compute_bias_report()

    if not report:
        print("无法生成图表：偏见报告为空。")
        return

    print("生成可视化图表...")
    plot_radar_chart(report, output_dir)
    plot_bias_boxplot(report, output_dir)
    plot_model_comparison_bar(report, output_dir)
    print("所有图表生成完成!")
