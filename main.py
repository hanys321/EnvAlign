# -*- coding: utf-8 -*-
"""
EnvAlign 主入口
用法: python main.py [命令] [选项]

命令:
  eval     — 运行多模型测评
  score    — 运行 LLM-as-Judge 评分
  bias     — 计算偏见报告
  report   — 生成完整评估报告（含图表）
  all      — 执行完整流程（eval → score → report）
"""

import sys
import os

# 确保项目根目录在 sys.path 中
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def cmd_eval(args):
    """运行测评"""
    from engine.evaluator import run_evaluation

    model_ids = None
    max_q = None

    if "--models" in args:
        idx = args.index("--models")
        model_ids = args[idx + 1].split(",") if idx + 1 < len(args) else None

    if "--max-questions" in args:
        idx = args.index("--max-questions")
        max_q = int(args[idx + 1]) if idx + 1 < len(args) else None

    run_evaluation(model_ids=model_ids, max_questions=max_q)


def cmd_score(args):
    """运行评分"""
    from analysis.value_analyzer import run_scoring

    force = "--force" in args
    max_samples = None
    if "--max-samples" in args:
        idx = args.index("--max-samples")
        max_samples = int(args[idx + 1]) if idx + 1 < len(args) else None

    run_scoring(force_rescore=force, max_samples=max_samples)


def cmd_bias(args):
    """计算偏见报告"""
    from analysis.bias_detector import compute_bias_report, get_model_ranking

    report = compute_bias_report()
    if report:
        ranking = get_model_ranking(report)
        print("\n=== 模型偏见排名（偏移度越小越公平）===")
        for i, r in enumerate(ranking, 1):
            print(f"  {i}. {r['model']}: 平均偏见度 = {r['avg_bias']:.3f}")


def cmd_report(args):
    """生成完整报告"""
    from reporter.report_generator import generate_report

    output = None
    if "--output" in args:
        idx = args.index("--output")
        output = args[idx + 1] if idx + 1 < len(args) else None

    generate_report(output_path=output)


def cmd_all(args):
    """执行完整流程"""
    print("=" * 50)
    print("EnvAlign 完整评估流程")
    print("=" * 50)

    print("\n[1/3] 运行多模型测评...")
    cmd_eval(args)

    print("\n[2/3] 运行 LLM-as-Judge 评分...")
    cmd_score(args)

    print("\n[3/3] 生成评估报告...")
    cmd_report(args)

    print("\n全部完成!")


COMMANDS = {
    "eval": cmd_eval,
    "score": cmd_score,
    "bias": cmd_bias,
    "report": cmd_report,
    "all": cmd_all,
}


def print_usage():
    print(__doc__)
    print("可用命令:", ", ".join(COMMANDS.keys()))
    print()
    print("示例:")
    print("  python main.py eval                          # 全量测评")
    print("  python main.py eval --max-questions 5        # 快速测试（只测5题）")
    print("  python main.py eval --models glm-4-flash     # 只测指定模型")
    print("  python main.py score                         # 评分")
    print("  python main.py score --force                 # 强制重新评分")
    print("  python main.py bias                          # 计算偏见")
    print("  python main.py report                        # 生成报告")
    print("  python main.py all --max-questions 5         # 完整流程（快速测试）")


if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help", "help"):
        print_usage()
        sys.exit(0)

    command = sys.argv[1]
    if command not in COMMANDS:
        print(f"未知命令: {command}")
        print_usage()
        sys.exit(1)

    COMMANDS[command](sys.argv[2:])
