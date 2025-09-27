#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
多数据库RAG评估工作流

用途：针对三种RAG数据库（uniform / report_context / sequential_block）分别执行：
1) RAG检索
2) rerun_with_rag 评测
并将结果隔离写入 results/<namespace>/ 子目录，方便对比。

示例：
python workflows/multi_db_full_pipeline.py 43001 --config config/config_cn.yaml --top_k 2
"""

import argparse
import subprocess
from pathlib import Path
import sys


BASE_DIR = Path(__file__).resolve().parent.parent


DB_CONFIGS = {
    "uniform": {
        "namespace": "uniform",
        "index_dir": "/home/duojiechen/projects/Rag_system/RAG_3DB/faiss_indexes/rag_uniform_db",
    },
    "report_context": {
        "namespace": "report_context",
        "index_dir": "/home/duojiechen/projects/Rag_system/RAG_3DB/faiss_indexes/rag_report_context_db",
    },
    "sequential_block": {
        "namespace": "sequential_block",
        "index_dir": "/home/duojiechen/projects/Rag_system/RAG_3DB/faiss_indexes/rag_sequential_block_db",
    },
}


def run_cmd(cmd: str) -> int:
    print("\n" + "=" * 80)
    print(f"💻 {cmd}")
    print("=" * 80)
    return subprocess.call(cmd, shell=True)


def main():
    parser = argparse.ArgumentParser(description="多数据库RAG评估工作流")
    parser.add_argument("start_id", type=int, help="开始报告ID")
    parser.add_argument("end_id", type=int, nargs='?', help="结束报告ID(可选)")
    parser.add_argument("--config", default="config/config_cn.yaml", help="配置文件路径")
    parser.add_argument("--top_k", type=int, default=2, help="RAG检索Top-K")
    parser.add_argument("--data_dir", type=str, default="test_set", help="数据目录")
    args = parser.parse_args()

    start_id = args.start_id
    end_id = args.end_id if args.end_id else start_id

    # 按报告循环：先baseline，再三库RAG（每个报告完整闭环）

    for rid in range(start_id, end_id + 1):
        print("\n" + "=" * 80)
        print(f"🧩 处理报告 {rid}: baseline → 3库RAG")
        print("=" * 80)

        # 0) baseline-only（每个报告一次）
        baseline_cmd = (
            f"python {BASE_DIR}/workflows/rerun_with_rag.py {rid} --config {args.config} "
            f"--baseline_only --data_dir {args.data_dir}"
        )
        rc0 = run_cmd(baseline_cmd)
        if rc0 != 0:
            print(f"❌ baseline 生成失败: report={rid}")
            continue

        # 1) 三个数据库依次跑 RAG
        for db_key in ["uniform", "report_context", "sequential_block"]:
            cfg = DB_CONFIGS[db_key]
            ns = cfg["namespace"]

            print("\n" + "#" * 80)
            print(f"🚀 评估数据库: {db_key}  → 命名空间: {ns} → 报告 {rid}")
            print("#" * 80)

            # 检索（单report）
            step1_cmd = (
                f"bash {BASE_DIR}/scripts/step1_rag3db_retrieve.sh {rid} {rid} {args.top_k} {db_key} {args.config}"
            )
            if args.data_dir != "test_set":
                step1_cmd += f" --data-dir {args.data_dir}"
            rc = run_cmd(step1_cmd)
            if rc != 0:
                print(f"❌ 检索阶段失败: {db_key} report={rid}")
                continue

            # RAG评测（要求baseline存在）
            rerun_cmd = (
                f"python {BASE_DIR}/workflows/rerun_with_rag.py {rid} --config {args.config} "
                f"--rag_cache_dir results/rag_output_{ns} --results_namespace {ns} --require_baseline"
            )
            if args.data_dir != "test_set":
                rerun_cmd += f" --data_dir {args.data_dir}"
            rc2 = run_cmd(rerun_cmd)
            if rc2 != 0:
                print(f"⚠️ rerun 失败: {db_key} report={rid}")
                continue

    print("\n" + "=" * 80)
    print("✅ 多数据库评估完成。结果已按命名空间写入 results/<namespace>/ 下。")
    print("- uniform: results/uniform/")
    print("- report_context: results/report_context/")
    print("- sequential_block: results/sequential_block/")
    print("=" * 80)


if __name__ == "__main__":
    main()


