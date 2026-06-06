# -*- coding: utf-8 -*-
"""
综合评估报告生成器
输出 HTML 报告
"""

import os
import json
import datetime

from jinja2 import Template

from config import RESULTS_DIR, TEMPLATES_DIR, DIMENSIONS
from analysis.bias_detector import compute_bias_report, get_model_ranking
from reporter.visualizer import generate_all_figures


def generate_report(output_path: str | None = None):
    """生成完整的 HTML 评估报告"""
    # 1. 计算偏见报告
    report = compute_bias_report()
    if not report:
        print("报告为空，请先完成测评和评分。")
        return

    # 2. 生成图表
    fig_dir = os.path.join(RESULTS_DIR, "figures")
    generate_all_figures(report, fig_dir)

    # 3. 模型排名
    ranking = get_model_ranking(report)

    # 4. 渲染 HTML
    summaries = report.get("model_summaries", {})
    bias_metrics = report.get("bias_metrics", {})
    dim_names = list(DIMENSIONS.values())

    dim_labels = [
        "经济发展↔环境保护",
        "短期利益↔长期可持续",
        "区域公平↔整体效率",
        "人类中心↔生态中心",
        "技术乐观↔预防原则",
    ]

    html = _render_html(summaries, bias_metrics, ranking, dim_labels)

    # 5. 保存
    if output_path is None:
        output_path = os.path.join(RESULTS_DIR, "report.html")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"报告已保存: {output_path}")


def _render_html(summaries, bias_metrics, ranking, dim_labels) -> str:
    """渲染 HTML 报告"""

    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

    # 构建表格行
    summary_rows = ""
    for model, dims in summaries.items():
        scores = [dims.get(f"dim{i+1}", {}).get("mean", "-") for i in range(5)]
        cells = f"<td><strong>{model}</strong></td>" + "".join(f"<td>{s}</td>" for s in scores)
        summary_rows += f"<tr>{cells}</tr>\n"

    bias_rows = ""
    for model, metrics in bias_metrics.items():
        vals = []
        for i in range(5):
            m = metrics.get(f"dim{i+1}", {})
            vals.append(f"{m.get('mean_abs_delta', 0):.3f}")
        cells = f"<td><strong>{model}</strong></td>" + "".join(f"<td>{v}</td>" for v in vals)
        bias_rows += f"<tr>{cells}</tr>\n"

    ranking_rows = ""
    for i, r in enumerate(ranking, 1):
        ranking_rows += f"<tr><td>{i}</td><td>{r['model']}</td><td>{r['avg_bias']:.3f}</td></tr>\n"

    # 图片路径
    fig_dir = "figures"
    radar_path = os.path.join(fig_dir, "radar_chart.png")
    box_path = os.path.join(fig_dir, "bias_boxplot.png")
    bar_path = os.path.join(fig_dir, "dimension_comparison_bar.png")

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>EnvAlign 评估报告</title>
<style>
body {{ font-family: "Microsoft YaHei", sans-serif; max-width: 1280px; margin: 0 auto; padding: 24px; color: #333; font-size: 16px; line-height: 1.7; }}
h1 {{ color: #1f3a5f; border-bottom: 3px solid #1f3a5f; padding-bottom: 10px; }}
h2 {{ color: #2c5f8a; margin-top: 30px; }}
table {{ border-collapse: collapse; width: 100%; margin: 15px 0; }}
th, td {{ border: 1px solid #ddd; padding: 10px 12px; text-align: center; }}
th {{ background-color: #1f3a5f; color: white; }}
tr:nth-child(even) {{ background-color: #f8f9fa; }}
img {{ width: 100%; max-width: 1220px; display: block; margin: 22px auto; border: 1px solid #eee; }}
.meta {{ color: #666; font-size: 0.9em; }}
.card {{ background: #f8f9fa; border-radius: 8px; padding: 20px; margin: 15px 0; }}
</style>
</head>
<body>

<h1>EnvAlign — 大语言模型环境政策建议价值对齐评估报告</h1>
<p class="meta">生成时间: {now} | 评估框架: EnvAlign v1.0</p>

<h2>一、评估概述</h2>
<div class="card">
<p>本报告使用 EnvAlign 框架，对多个主流大语言模型在环境政策建议场景下的价值倾向进行系统评估。</p>
<p>评估维度共5个：</p>
<ol>
<li><strong>{dim_labels[0]}</strong>（1=环保优先，5=经济优先）</li>
<li><strong>{dim_labels[1]}</strong>（1=长期优先，5=短期优先）</li>
<li><strong>{dim_labels[2]}</strong>（1=公平优先，5=效率优先）</li>
<li><strong>{dim_labels[3]}</strong>（1=生态中心，5=人类中心）</li>
<li><strong>{dim_labels[4]}</strong>（1=预防原则，5=技术乐观）</li>
</ol>
</div>

<h2>二、各模型价值倾向评分（平均分）</h2>
<table>
<tr><th>模型</th>{"".join(f"<th>{l}</th>" for l in dim_labels)}</tr>
{summary_rows}
</table>

<h2>三、价值倾向雷达图</h2>
<img src="{radar_path}" alt="雷达图">

<h2>四、各维度评分对比</h2>
<img src="{bar_path}" alt="柱状图">

<h2>五、地区偏见分析</h2>
<h5>5.1 偏见指标（平均绝对偏移度）</h5>
<table>
<tr><th>模型</th>{"".join(f"<th>{l}</th>" for l in dim_labels)}</tr>
{bias_rows}
</table>

<h5>5.2 地区偏移分布（箱线图）</h5>
<img src="{box_path}" alt="箱线图">

<h5>5.3 偏见排名（偏移度越小越公平）</h5>
<table>
<tr><th>排名</th><th>模型</th><th>平均偏见度</th></tr>
{ranking_rows}
</table>

<h2>六、结论与讨论</h2>
<div class="card">
<p><strong>说明：</strong>以上结果基于有限的题目样本和自动化评分方法，仅反映模型在特定环境政策问题上的价值倾向趋势，
不代表对任何模型的定性评价。详细分析请结合原始数据和项目文档。</p>
</div>

<hr>
<p class="meta" style="text-align:center;">
EnvAlign &mdash; 大语言模型环境政策建议价值对齐评估框架 | 仅供学术研究使用
</p>
</body>
</html>"""

    return html
