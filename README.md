# EnvAlign — 大语言模型环境政策建议的价值对齐评估框架

> 评估 豆包 / 通义千问 / DeepSeek 等大模型在回答环境政策问题时的价值倾向与区域偏见

## 项目简介

EnvAlign 是一个面向**环境政策领域**的大语言模型价值对齐评估工具。通过标准化的环境伦理两难问题题库，系统性地评估主流大模型在以下5个维度上的价值倾向：

| 维度 | 低分端(1) | 高分端(5) |
|------|-----------|-----------|
| 经济发展↔环境保护 | 强烈偏向环保 | 强烈偏向经济发展 |
| 短期利益↔长期可持续 | 强烈偏向长期 | 强烈偏向短期 |
| 区域公平↔整体效率 | 强烈偏向公平 | 强烈偏向效率 |
| 人类中心↔生态中心 | 强烈偏向生态 | 强烈偏向人类 |
| 技术乐观↔预防原则 | 强烈偏向预防 | 强烈偏向技术乐观 |

同时，每道题目设计有**多个地区变体**（北京/河北/西部地区），用于检测模型是否存在**区域偏见**。

## 项目结构

```
EnvAlign/
├── EnvAlign_伦理设计项目文档.pdf    #项目系统实现文档
├── main.py                  # CLI 主入口
├── app.py                   # Streamlit 交互式仪表盘
├── config.py                # 全局配置
├── requirements.txt         # 依赖
├── .env.example             # API Key 配置模板
├── data/
│   └── question_bank.json   # 题库（50题×4地区变体）
├── models/
│   ├── __init__.py           # 模型工厂
│   └── base_adapter.py      # 统一 API 适配器
├── engine/
│   ├── __init__.py
│   ├── evaluator.py          # 多模型测评引擎
│   └── prompt_templates.py   # Prompt 模板
├── analysis/
│   ├── __init__.py
│   ├── value_analyzer.py     # LLM-as-Judge 评分
│   ├── bias_detector.py      # 偏见检测
│   └── keyword_analyzer.py   # 关键词辅助分析
├── reporter/
│   ├── __init__.py
│   ├── visualizer.py         # 可视化图表
│   └── report_generator.py   # HTML 报告生成
├── usage research/           # 问卷和初步使用调研结果
├── results/                  # 输出目录（自动创建）
└── README.md
```

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置 API Key

```bash
cp .env.example .env
# 编辑 .env 填入你的 API Key
```

需要至少一个模型的 API Key：
- **智谱 GLM**（免费）: https://open.bigmodel.cn
- **通义千问**（有免费额度）: https://dashscope.console.aliyun.com
- **DeepSeek**（有免费额度）: https://platform.deepseek.com

### 3. 运行测评

```bash
# 快速测试（5题）
python main.py all --max-questions 5

# 全量测评
python main.py all

# 也可以分步执行
python main.py eval                        # 测评
python main.py score                       # 评分
python main.py bias                        # 偏见分析
python main.py report                      # 生成报告
```

### 4. 查看结果

```bash
# 启动交互式仪表盘
streamlit run app.py

# 或查看生成的 HTML 报告
# results/report.html
```

## 使用示例

```bash
# 只测评指定模型
python main.py eval --models glm-4-flash,deepseek-chat

# 强制重新评分
python main.py score --force

# 指定报告输出路径
python main.py report --output my_report.html
```

## 题库说明

题库包含 **50 道环境政策两难问题**，覆盖 5 个伦理维度：

- **D1 (10题)**: 经济发展 vs 环境保护
- **D2 (10题)**: 短期利益 vs 长期可持续
- **D3 (10题)**: 区域公平 vs 整体效率
- **D4 (10题)**: 人类中心 vs 生态中心
- **D5 (10题)**: 技术乐观 vs 预防原则

每道题设计 4 个地区变体：
- `default`: 一般城市（无特定地区）
- `beijing`: 北京市
- `hebei`: 河北省工业城市
- `western`: 西部地区资源型城市

## 技术架构

```
展示层: Streamlit Dashboard + HTML/PDF 报告
分析层: LLM-as-Judge 评分 + 偏见检测 + 关键词分析
引擎层: 多模型调度器 + API 适配器 + 断点续评
数据层: JSON 题库 + JSONL 测评记录 + JSON 分析结果
```

## 省钱方案

本项目使用以下免费/低成本模型方案：
- **被测模型**: GLM-4-Flash（免费）、通义千问-Plus（免费额度）、DeepSeek-Chat（极低成本）
- **Judge 模型**: GLM-4-Flash（免费，替代 GPT-4）
- 所有 API 调用均支持**断点续评**，避免重复消耗

## 伦理声明

本项目遵循以下伦理原则：
1. **透明性**: 所有评分 Prompt 和评估维度完全公开
2. **公平性**: 题库设计经多人审查，力求无引导性
3. **可问责性**: 评估结果仅供学术参考，不代表对任何模型的定性判断
4. **数据伦理**: 不收集个人隐私数据，仅使用公开 API 输出

## 许可证

MIT License — 仅供学术研究使用
