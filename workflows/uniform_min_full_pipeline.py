#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
最小化Uniform完整评估流程（从头编写）
- 固定使用 Uniform RAG 系统与索引: /home/duojiechen/projects/Rag_system/RAG_3DB/faiss_indexes/rag_uniform_db
- 步骤：Step1 RAG检索 → Step2 按报告 rerun_with_rag（先baseline后RAG对比）
- 使用已有脚本：scripts/step1_rag3db_retrieve.sh 与 workflows/rerun_with_rag.py
- 结果目录统一在 results/

用法：
  python workflows/uniform_min_full_pipeline.py 43001              # 单个报告
  python workflows/uniform_min_full_pipeline.py 43001 43005       # 范围
  python workflows/uniform_min_full_pipeline.py 43001 43005 --top_k 3 --config config/config_cn.yaml
"""

import argparse
import subprocess
import sys
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).parent.parent
UNIFORM_INDEX_DIR = "/home/duojiechen/projects/Rag_system/RAG_3DB/faiss_indexes/rag_uniform_db"
RESULTS_BASE = BASE_DIR / "results"


def run_cmd(cmd: str, desc: str) -> bool:
    print(f"\n🚀 {desc}")
    print(f"💻 执行命令: {cmd}")
    print("=" * 80)
    try:
        subprocess.run(cmd, shell=True, check=True)
        print("=" * 80)
        print(f"✅ {desc} - 成功完成")
        return True
    except subprocess.CalledProcessError as e:
        print("=" * 80)
        print(f"❌ {desc} - 失败 (code={e.returncode})")
        return False


def ensure_dirs():
    (RESULTS_BASE / "rag_output_uniform").mkdir(parents=True, exist_ok=True)
    (RESULTS_BASE / "baseline_results").mkdir(parents=True, exist_ok=True)
    (RESULTS_BASE / "rerun_with_rag").mkdir(parents=True, exist_ok=True)
    (RESULTS_BASE / "rerun_comparisons").mkdir(parents=True, exist_ok=True)


def main():
    parser = argparse.ArgumentParser(description="最小化Uniform完整评估流程")
    parser.add_argument("start_id", type=int, help="开始报告ID")
    parser.add_argument("end_id", type=int, nargs='?', help="结束报告ID (可选)")
    parser.add_argument("--top_k", type=int, default=3, help="RAG检索Top-K")
    parser.add_argument("--config", type=str, default="config/config_cn.yaml", help="配置文件路径")
    parser.add_argument("--data_dir", type=str, default="test_set", help="数据目录（默认test_set）")

    args = parser.parse_args()
    start_id = args.start_id
    end_id = args.end_id if args.end_id else args.start_id

    print("=" * 80)
    print("🎯 最小化Uniform完整评估流程")
    print("=" * 80)
    print(f"📋 报告范围: {start_id} - {end_id}")
    print(f"🗂️  索引路径: {UNIFORM_INDEX_DIR}")
    print(f"🔍 Top-K: {args.top_k}")
    print(f"⚙️  配置: {args.config}")
    print(f"📁 数据目录: {args.data_dir}")

    ensure_dirs()

    # Step 1: RAG检索（固定uniform）
    print("\n" + "-" * 60)
    print("🔎 Step 1: Uniform RAG检索")
    step1 = (
        f"bash {BASE_DIR}/scripts/step1_rag3db_retrieve.sh {start_id} {end_id} {args.top_k} uniform {args.config}"
    )
    if args.data_dir != "test_set":
        step1 += f" --data-dir {args.data_dir}"
    if not run_cmd(step1, "RAG检索（Uniform）"):
        print("❌ 检索失败，中止")
        sys.exit(1)

    # Step 2: RAG增强评估（逐报告）
    print("\n" + "-" * 60)
    print("🚀 Step 2: RAG增强评估（逐报告）")
    ok = True
    for report_id in range(start_id, end_id + 1):
        cmd = (
            f"python {BASE_DIR}/workflows/rerun_with_rag.py {report_id} --config {args.config} --rag_cache_dir results/rag_output_uniform"
        )
        if args.data_dir != "test_set":
            cmd += f" --data-dir {args.data_dir}"
        if not run_cmd(cmd, f"RAG增强评估（报告 {report_id}）"):
            ok = False
            break

    # 汇总
    print("\n" + "=" * 80)
    if ok:
        print("🎉 Uniform最小化完整流程执行成功！")
        print("\n📁 结果位置：")
        print("   • RAG缓存: results/rag_output_uniform/")
        print("   • Baseline: results/baseline_results/ 或 baseline_results_batch/")
        print("   • RAG增强: results/rerun_with_rag/")
        print("   • 对比分析: results/rerun_comparisons/")
    else:
        print("❌ Uniform最小化完整流程执行失败！请检查上方日志。")
    print("=" * 80)


if __name__ == "__main__":
    main()
