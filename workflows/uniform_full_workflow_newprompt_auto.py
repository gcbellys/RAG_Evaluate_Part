#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Uniform 数据库 - 新工作流（自动baseline，不改动现有代码）
顺序：新RAG检索（confidence-aware）→ RAG增强评估（rerun_with_rag 自动先baseline再RAG）
- 新RAG检索：scripts/confidence_aware_rag_adapter.py（写入 results/rag_output_uniform）
- RAG增强评估：workflows/rerun_with_rag.py（先生成/查找 baseline，再使用RAG缓存对比）
- Prompt策略：临时将 prompt/system_prompt.txt 替换为 prompt/rag_enhanced_prompt.txt，结束后恢复

用法：
  python workflows/uniform_full_workflow_newprompt_auto.py 43001               # 单个报告
  python workflows/uniform_full_workflow_newprompt_auto.py 43001 43005        # 报告范围
  python workflows/uniform_full_workflow_newprompt_auto.py 43001 43005 --top_k 3 --config config/config_cn.yaml
"""

import argparse
import subprocess
import sys
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).parent.parent
PROMPT_DIR = BASE_DIR / "prompt"
SYSTEM_PROMPT = PROMPT_DIR / "system_prompt.txt"
ENHANCED_PROMPT = PROMPT_DIR / "rag_enhanced_prompt.txt"
BACKUP_PROMPT = PROMPT_DIR / f"system_prompt_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
RAG_CACHE_DIR = BASE_DIR / "results" / "rag_output_uniform"


def run_cmd(cmd: str, desc: str) -> bool:
    print(f"\n🚀 {desc}")
    print(f"💻 执行: {cmd}")
    print("=" * 80)
    try:
        subprocess.run(cmd, shell=True, check=True)
        print("=" * 80)
        print(f"✅ {desc} - 成功")
        return True
    except subprocess.CalledProcessError as e:
        print("=" * 80)
        print(f"❌ {desc} - 失败 (code={e.returncode})")
        return False


def replace_system_prompt_temporarily() -> bool:
    if not ENHANCED_PROMPT.exists():
        print(f"❌ 新prompt不存在: {ENHANCED_PROMPT}")
        return False
    try:
        # 备份现有system_prompt
        if SYSTEM_PROMPT.exists():
            SYSTEM_PROMPT.replace(BACKUP_PROMPT)
        # 写入增强版prompt为system_prompt
        content = ENHANCED_PROMPT.read_text(encoding='utf-8')
        SYSTEM_PROMPT.write_text(content, encoding='utf-8')
        print(f"🧠 已启用增强版prompt作为system_prompt: {SYSTEM_PROMPT.name}")
        return True
    except Exception as e:
        print(f"❌ 替换system_prompt失败: {e}")
        return False


def restore_system_prompt_if_needed():
    try:
        if BACKUP_PROMPT.exists():
            # 恢复备份
            if SYSTEM_PROMPT.exists():
                SYSTEM_PROMPT.unlink()
            BACKUP_PROMPT.replace(SYSTEM_PROMPT)
            print("♻️ 已恢复原始system_prompt")
    except Exception as e:
        print(f"⚠️ 恢复system_prompt时出现问题: {e}")


def build_input_path(report_id: int, data_dir: str) -> Path:
    if data_dir == "test_set":
        return Path(f"/home/duojiechen/Central_Data/Testset_0_43000-43508/diagnostic_results_normalized/diagnostic_{report_id}.json")
    else:
        return Path(data_dir) / f"diagnostic_{report_id}.json"


def main():
    parser = argparse.ArgumentParser(description="Uniform新工作流：新RAG→RAG评估（rerun自动baseline）")
    parser.add_argument("start_id", type=int, help="开始报告ID")
    parser.add_argument("end_id", type=int, nargs='?', help="结束报告ID (可选)")
    parser.add_argument("--top_k", type=int, default=3, help="RAG检索Top-K")
    parser.add_argument("--config", type=str, default="config/config_cn.yaml", help="配置文件路径")
    parser.add_argument("--data_dir", type=str, default="test_set", help="数据目录，默认test_set")

    args = parser.parse_args()
    start_id = args.start_id
    end_id = args.end_id if args.end_id else args.start_id

    print("=" * 80)
    print("🎯 Uniform新工作流（两步）：新RAG → RAG评估（含baseline）")
    print("=" * 80)
    print(f"📋 报告范围: {start_id} - {end_id}")
    print(f"🔍 Top-K: {args.top_k}")
    print(f"⚙️ 配置: {args.config}")
    print(f"📁 数据目录: {args.data_dir}")

    success_steps = 0

    # 步骤0：启用增强版prompt（临时替换system_prompt）
    print("\n" + "-" * 60)
    print("🧠 启用增强版prompt (临时替换 system_prompt.txt)")
    replace_system_prompt_temporarily()

    # 准备RAG缓存目录
    try:
        RAG_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        print(f"📁 已准备RAG缓存目录: {RAG_CACHE_DIR}")
    except Exception as e:
        print(f"❌ 创建RAG缓存目录失败: {e}")

    try:
        # 步骤1：新RAG检索（confidence-aware，写入统一缓存）
        print("\n" + "-" * 60)
        print("🔎 步骤1/2：运行新RAG检索（confidence-aware）")
        retrieval_ok = True
        for report_id in range(start_id, end_id + 1):
            input_file = build_input_path(report_id, args.data_dir)
            if not input_file.exists():
                print(f"⚠️ 输入文件不存在，跳过: {input_file}")
                retrieval_ok = False
                continue
            rag_cmd = (
                f"python {BASE_DIR}/scripts/confidence_aware_rag_adapter.py "
                f"--file {input_file} --top_k {args.top_k} "
                f"--output_dir {RAG_CACHE_DIR} --rag_db_type uniform"
            )
            if not run_cmd(rag_cmd, f"新RAG检索 - 报告 {report_id}"):
                retrieval_ok = False
                break
        if not retrieval_ok:
            print("❌ 新RAG检索失败，退出")
            return
        success_steps += 1

        # 步骤2：RAG增强评估（rerun_with_rag 自动先baseline再RAG对比）
        print("\n" + "-" * 60)
        print("🚀 步骤2/2：运行RAG增强评估（自动baseline→RAG）")
        rerun_ok = True
        for report_id in range(start_id, end_id + 1):
            rerun_cmd = (
                f"python {BASE_DIR}/workflows/rerun_with_rag.py {report_id} "
                f"--config {args.config} --rag_cache_dir {RAG_CACHE_DIR}"
            )
            if args.data_dir != "test_set":
                rerun_cmd += f" --data-dir {args.data_dir}"
            if not run_cmd(rerun_cmd, f"RAG增强评估 - 报告 {report_id}"):
                rerun_ok = False
                break
        if not rerun_ok:
            print("❌ RAG增强评估失败，退出")
            return
        success_steps += 1

    finally:
        # 恢复system_prompt
        restore_system_prompt_if_needed()

    # 结果汇总
    print("\n" + "=" * 80)
    if success_steps == 2:
        print("🎉 新工作流执行成功！")
        print("\n📁 结果位置：")
        print("   • Baseline结果: results/baseline_results/ 或 baseline_results_batch/")
        print("   • RAG缓存: results/rag_output_uniform/")
        print("   • RAG增强结果: results/rerun_with_rag/")
        print("   • 对比分析: results/rerun_comparisons/")
    else:
        print("❌ 新工作流执行未完成，请检查日志。")
    print("=" * 80)


if __name__ == "__main__":
    main()
