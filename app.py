# -*- coding: utf-8 -*-
"""
EnvAlign Streamlit Dashboard
交互式评估结果展示

启动方式: streamlit run app.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import json
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px

from config import DIMENSIONS, RESULTS_DIR, EVAL_RESULTS_PATH, SCORE_RESULTS_PATH


# ── 页面配置 ──────────────────────────────────────────────
st.set_page_config(
    page_title="EnvAlign 评估仪表盘",
    page_icon="🔍",
    layout="wide",
)

DIM_LABELS = list(DIMENSIONS.values())
DIM_KEYS = list(DIMENSIONS.keys())
DIM_SHORT = ["经济vs环保", "短期vs长期", "公平vs效率", "人类vs生态", "技术vs预防"]


@st.cache_data
def load_data():
    """加载所有数据"""
    evals = []
    scores = []
    bias_report = {}

    if os.path.exists(EVAL_RESULTS_PATH):
        with open(EVAL_RESULTS_PATH, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    evals.append(json.loads(line))

    if os.path.exists(SCORE_RESULTS_PATH):
        with open(SCORE_RESULTS_PATH, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    scores.append(json.loads(line))

    bias_path = os.path.join(RESULTS_DIR, "bias_report.json")
    if os.path.exists(bias_path):
        with open(bias_path, "r", encoding="utf-8") as f:
            bias_report = json.load(f)

    return evals, scores, bias_report


def main():
    st.title("🔍 EnvAlign — 大模型环境政策价值对齐评估")
    st.markdown("---")

    evals, scores, bias_report = load_data()

    if not scores:
        st.warning("暂无评估数据。请先运行测评和评分流程：`python main.py all`")
        st.info("""
**快速开始：**
1. 复制 `.env.example` 为 `.env`，填入 API Key
2. 安装依赖：`pip install -r requirements.txt`
3. 运行：`python main.py all --max-questions 5`
4. 重新打开此页面
""")
        return

    # 侧边栏
    st.sidebar.header("筛选条件")
    models = list(set(s["model"] for s in scores))
    selected_models = st.sidebar.multiselect("选择模型", models, default=models)
    regions = list(set(s["region"] for s in scores))
    selected_regions = st.sidebar.multiselect("选择地区", regions, default=regions)

    # 过滤数据
    filtered = [
        s for s in scores
        if s["model"] in selected_models and s["region"] in selected_regions
    ]

    if not filtered:
        st.error("筛选后无数据，请调整筛选条件。")
        return

    # ── Tab 布局 ────────────────────────────────────────
    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 价值倾向总览",
        "📡 雷达图对比",
        "⚖️ 偏见检测",
        "📝 原始回答浏览",
    ])

    # ── Tab 1: 总览 ────────────────────────────────────
    with tab1:
        st.header("各模型价值倾向评分总览")

        rows = []
        for s in filtered:
            row = {
                "模型": s["model"],
                "地区": s["region"],
                "题目": s["question_id"],
            }
            for i, dk in enumerate(DIM_KEYS):
                row[DIM_SHORT[i]] = s["scores"].get(dk, 0)
            rows.append(row)

        df = pd.DataFrame(rows)

        # 各模型平均分
        st.subheader("平均评分")
        avg_df = df.groupby("模型")[DIM_SHORT].mean().round(2)
        st.dataframe(avg_df, use_container_width=True)

        # 柱状图
        fig = go.Figure()
        for model in selected_models:
            if model in avg_df.index:
                fig.add_trace(go.Bar(
                    name=model,
                    x=DIM_SHORT,
                    y=avg_df.loc[model].values,
                ))
        fig.update_layout(
            title="各模型维度评分对比",
            yaxis=dict(title="评分 (1-5)", range=[0, 5.5]),
            barmode="group",
        )
        fig.add_hline(y=3, line_dash="dash", line_color="gray", annotation_text="中立线")
        st.plotly_chart(fig, use_container_width=True)

    # ── Tab 2: 雷达图 ──────────────────────────────────
    with tab2:
        st.header("价值倾向雷达图")

        df_radar = pd.DataFrame(rows)
        avg_by_model = df_radar.groupby("模型")[DIM_SHORT].mean()

        fig = go.Figure()
        for model in selected_models:
            if model in avg_by_model.index:
                vals = avg_by_model.loc[model].values.tolist()
                vals.append(vals[0])  # 闭合
                labels = DIM_SHORT + [DIM_SHORT[0]]

                fig.add_trace(go.Scatterpolar(
                    r=vals,
                    theta=labels,
                    fill="toself",
                    name=model,
                    opacity=0.6,
                ))

        fig.update_layout(
            polar=dict(radialaxis=dict(visible=True, range=[1, 5])),
            showlegend=True,
            title="模型价值倾向雷达图",
        )
        st.plotly_chart(fig, use_container_width=True)

        st.markdown("""
**评分说明：**
- **经济vs环保**: 1=强烈环保倾向, 5=强烈经济倾向
- **短期vs长期**: 1=长期优先, 5=短期优先
- **公平vs效率**: 1=公平优先, 5=效率优先
- **人类vs生态**: 1=生态中心, 5=人类中心
- **技术vs预防**: 1=预防原则, 5=技术乐观
""")

    # ── Tab 3: 偏见检测 ────────────────────────────────
    with tab3:
        st.header("地区偏见分析")

        if not bias_report or "region_shifts" not in bias_report:
            st.warning("暂无偏见分析数据。请先运行：`python main.py bias`")
        else:
            shifts = bias_report["region_shifts"]
            sdf = pd.DataFrame(shifts)
            sdf = sdf[sdf["model"].isin(selected_models)]

            if sdf.empty:
                st.warning("筛选后无偏见数据。")
            else:
                # 箱线图
                fig = px.box(
                    sdf,
                    x="dimension",
                    y="delta",
                    color="model",
                    facet_col="region",
                    title="各模型地区偏移分布",
                    labels={"delta": "偏移度 (Δ)", "dimension": "维度"},
                )
                fig.add_hline(y=0, line_dash="dash", line_color="red")
                st.plotly_chart(fig, use_container_width=True)

                # 偏见指标表
                st.subheader("偏见指标汇总")
                bias_metrics = bias_report.get("bias_metrics", {})
                metric_rows = []
                for model, metrics in bias_metrics.items():
                    if model not in selected_models:
                        continue
                    for i, dk in enumerate(DIM_KEYS):
                        m = metrics.get(dk, {})
                        metric_rows.append({
                            "模型": model,
                            "维度": DIM_SHORT[i],
                            "平均绝对偏移": m.get("mean_abs_delta", 0),
                            "最大绝对偏移": m.get("max_abs_delta", 0),
                            "偏见率(|Δ|>0.5)": m.get("bias_rate", 0),
                            "方向一致性": m.get("direction_consistency", 0),
                        })
                if metric_rows:
                    st.dataframe(pd.DataFrame(metric_rows), use_container_width=True)

    # ── Tab 4: 原始回答 ────────────────────────────────
    with tab4:
        st.header("原始回答浏览")

        # 选择题目
        q_ids = sorted(set(s["question_id"] for s in filtered))
        selected_q = st.selectbox("选择题目", q_ids)

        if selected_q:
            col1, col2 = st.columns(2)

            # 左侧：评分
            q_scores = [s for s in filtered if s["question_id"] == selected_q]
            with col1:
                st.subheader("评分结果")
                for s in q_scores:
                    st.markdown(f"**{s['model']}** ({s['region']})")
                    score_str = " | ".join(
                        f"{DIM_SHORT[i]}={s['scores'].get(dk, '-')}"
                        for i, dk in enumerate(DIM_KEYS)
                    )
                    st.code(score_str)
                    if s.get("reasoning"):
                        st.caption(f"理由: {s['reasoning']}")
                    st.markdown("---")

            # 右侧：原始回答
            with col2:
                st.subheader("模型回答")
                q_evals = [e for e in evals if e["question_id"] == selected_q
                           and e["model"] in selected_models
                           and e["region"] in selected_regions]
                for e in q_evals:
                    st.markdown(f"**{e['model']}** ({e['region']})")
                    st.text_area(
                        "回答",
                        value=e.get("response", "无回答"),
                        height=150,
                        disabled=True,
                        key=f"{e['eval_id']}_resp",
                    )


if __name__ == "__main__":
    main()
