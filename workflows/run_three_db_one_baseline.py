#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
三库统一流程工作流（不改动既有流程，新增独立脚本）

目标（每个报告）：
1) 先分别对三种数据库（sequential-block、report-context、uniform-random）执行 RAG 检索
2) 仅执行一次 baseline 评估（共享 baseline 结果）
3) 分别使用三种数据库的 RAG 结果执行 RAG 复评并与统一 baseline 对比

说明：
- 完全复用现有脚本与目录结构：
  - 检索：scripts/step1_rag_retrieve_new.sh
  - baseline：workflows/cached_baseline_workflow.py（结果保存在 final_result/baseline_results/）
  - RAG 复评：workflows/rerun_with_rag.py（RAG 相关输出保存在 final_result/{db_type}_results/...）
- 本脚本只负责编排顺序，不改动任何既有逻辑与实现
"""

import argparse
import subprocess
from pathlib import Path


THREE_DBS = [
    "sequential-block",
    "report-context",
    "uniform-random",
]


def run_command(command: str, description: str) -> bool:
    """运行命令并实时输出，失败返回 False。"""
    print(f"\n🚀 {description}")
    print(f"💻 执行命令: {command}")
    print("=" * 80)
    try:
        subprocess.run(command, shell=True, check=True, text=True)
        print("=" * 80)
        print(f"✅ {description} - 成功完成")
        return True
    except subprocess.CalledProcessError as e:
        print("=" * 80)
        print(f"❌ {description} - 失败 (exit {e.returncode})")
        return False


def main():
    parser = argparse.ArgumentParser(description="三库先检索、一次baseline、三次RAG复评 的统一工作流")
    parser.add_argument("start_id", type=int, help="开始报告ID")
    parser.add_argument("end_id", type=int, nargs='?', help="结束报告ID (可选，默认与start_id相同)")
    parser.add_argument("--top_k", type=int, default=3, help="RAG检索的top_k参数")
    parser.add_argument("--config", type=str, default="config/config_cn.yaml", help="配置文件路径")
    parser.add_argument("--use_new_rag", action="store_true", help="使用新构建的RAG索引（与现有run_full_pipeline一致）")
    parser.add_argument("--pre_retrieve_all", action="store_true",
                        help="先对给定范围内所有报告与所有DB一次性完成RAG检索，然后再逐报告执行baseline与复评")
    parser.add_argument("--dbs", type=str, nargs='*', default=THREE_DBS,
                        help="要参与流程的数据库类型列表，默认三种全跑")

    args = parser.parse_args()

    start_id = args.start_id
    end_id = args.end_id if args.end_id else start_id
    base_dir = Path(__file__).parent.parent  # 项目根目录

    print("=" * 60)
    print("🎯 三库统一流程 - 先三库检索 -> 一次baseline -> 三次RAG复评")
    print("=" * 60)
    print(f"📋 报告范围: {start_id} - {end_id}")
    print(f"🗄️  数据库: {', '.join(args.dbs)}")
    print(f"🔍 top_k: {args.top_k}")
    print(f"⚙️  配置: {args.config}")
    print(f"🆕 使用新RAG: {'是' if args.use_new_rag else '否'}")
    print(f"🧊 先整段预检索: {'是' if args.pre_retrieve_all else '否'}")

    success_count = 0
    total = end_id - start_id + 1

    # 可选 Step 0: 先整段预检索，避免每个报告重复初始化模型/索引
    if args.pre_retrieve_all:
        # 严格按顺序：预热DB1并整段检索 -> 预热DB2并整段检索 -> 预热DB3并整段检索
        for db in args.dbs:
            # 使用单进程批量检索脚本，加载一次模型与索引，跨范围完成检索
            pre_cmd = (
                f"python {base_dir}/workflows/batch_rag_retrieve.py "
                f"{start_id} {end_id} --db_type {db} --top_k {args.top_k}"
            )
            if not run_command(pre_cmd, f"整段RAG检索（单进程预热，{db}） - 报告范围 {start_id}-{end_id}"):
                print(f"⚠️  预检索失败（{db}），后续步骤可能缺少检索缓存")

    for report_id in range(start_id, end_id + 1):
        print(f"\n{'=' * 40}")
        print(f"📊 处理报告 {report_id} ({success_count + 1}/{total})")
        print(f"{'=' * 40}")

        # Step 1: 若未启用整段预检索，则逐报告执行三库检索；否则跳过
        if not args.pre_retrieve_all:
            for db in args.dbs:
                if args.use_new_rag:
                    step1_cmd = f"bash {base_dir}/scripts/step1_rag_retrieve_new.sh {report_id} {report_id} {args.top_k} {db}"
                else:
                    step1_cmd = f"bash {base_dir}/scripts/step1_rag_retrieve.sh {report_id} {report_id} {args.top_k}"

                if not run_command(step1_cmd, f"RAG检索 ({db}) - 报告 {report_id}"):
                    print(f"⚠️  跳过报告 {report_id} 后续步骤")
                    break
            else:
                pass  # 所有DB均成功

        # Step 2: 分别用三库做 RAG 复评（第一次会自动生成 baseline，后面复用）
        all_ok = True
        for db in args.dbs:
            rag_eval_cmd = f"python {base_dir}/workflows/rerun_with_rag.py {report_id} --config {args.config} --db_type {db}"
            ok = run_command(rag_eval_cmd, f"RAG增强评估 ({db}) - 报告 {report_id}")
            all_ok = all_ok and ok

        if all_ok:
            success_count += 1
            print(f"🎉 报告 {report_id} 全流程完成!")

    # Summaries
    print("\n" + "=" * 60)
    print("📈 三库统一流程执行总结")
    print("=" * 60)
    print(f"✅ 成功处理: {success_count}/{total} 个报告")
    print("\n📁 结果文件位置:")
    print("   🔍 RAG缓存: final_result/{db_type}_results/rag_search_output/")
    print("   🤖 RAG增强: final_result/{db_type}_results/rerun_with_rag/")
    print("   📊 对比分析: final_result/{db_type}_results/rerun_comparisons/")
    print("   📋 baseline共享: final_result/baseline_results/")
    print("\n🏁 流程结束")


if __name__ == "__main__":
    main()

