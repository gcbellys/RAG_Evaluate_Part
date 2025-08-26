#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RAG评估系统 - 主启动脚本

这是项目的主入口，提供多种工作流程选择：
1. 完整RAG评估流程（推荐）
2. 仅基础评估（不含RAG）
3. 仅RAG增强评估（使用现有缓存）
4. 单独的RAG检索

用法：
    python start_evaluation.py --help                    # 查看帮助
    python start_evaluation.py full 4000                 # 完整流程（单个报告）
    python start_evaluation.py full 4000 4002            # 完整流程（范围）
    python start_evaluation.py baseline 4000             # 仅基础评估
    python start_evaluation.py rag-only 4000             # 仅RAG增强（需要已有缓存）
"""

import argparse
import subprocess
import sys
from pathlib import Path


def run_workflow_command(command: str, description: str) -> bool:
    """运行工作流命令"""
    print(f"\n🚀 {description}")
    print(f"💻 执行: {command}")
    print("=" * 60)
    
    try:
        result = subprocess.run(command, shell=True, check=True)
        print("=" * 60)
        print(f"✅ {description} - 完成")
        return True
    except subprocess.CalledProcessError as e:
        print("=" * 60)
        print(f"❌ {description} - 失败 (错误码: {e.returncode})")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="RAG评估系统主启动脚本",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
工作流程说明:
  full      完整RAG评估流程 (推荐)
            1. RAG检索 → 2. 基础评估 → 3. RAG增强评估 → 4. 对比分析
  
  baseline  仅运行基础评估 (不含RAG)
            适用于获得baseline结果
  
  rag-only  仅运行RAG增强评估
            需要已有RAG缓存，会自动生成baseline如果缺失
  
  retrieve  仅运行RAG检索
            为后续评估准备缓存数据

示例:
  python start_evaluation.py full 4000         # 完整评估报告4000
  python start_evaluation.py full 4000 4002    # 批量评估4000-4002
  python start_evaluation.py baseline 4001     # 仅基础评估4001
        """
    )
    
    parser.add_argument("workflow", choices=["full", "baseline", "rag-only", "retrieve"],
                        help="选择工作流程类型")
    parser.add_argument("start_id", type=int, help="开始报告ID")
    parser.add_argument("end_id", type=int, nargs='?', help="结束报告ID (可选)")
    parser.add_argument("--max_files", type=int, help="最大处理文件数量")
    parser.add_argument("--top_k", type=int, default=3, help="RAG检索top_k参数")
    parser.add_argument("--config", type=str, default="config/config.yaml", help="配置文件路径")
    
    args = parser.parse_args()
    
    start_id = args.start_id
    end_id = args.end_id if args.end_id else start_id
    workflow = args.workflow
    
    print("=" * 70)
    print("🎯 RAG评估系统")
    print("=" * 70)
    print(f"📋 工作流程: {workflow}")
    print(f"📊 报告范围: {start_id} - {end_id}")
    print(f"🔍 检索参数: top_k={args.top_k}")
    print(f"⚙️  配置文件: {args.config}")
    
    project_root = Path(__file__).parent
    success = True
    
    if workflow == "full":
        # 完整流程：使用优化的管道脚本
        cmd = f"python workflows/run_full_pipeline.py {start_id}"
        if end_id != start_id:
            cmd += f" {end_id}"
        if args.top_k != 3:
            cmd += f" --top_k {args.top_k}"
        cmd += f" --config {args.config}"
        success = run_workflow_command(cmd, "完整RAG评估流程")
        
    elif workflow == "baseline":
        # 仅基础评估
        cmd = f"python workflows/main_workflow.py --start_id {start_id} --end_id {end_id} --config {args.config}"
        if args.max_files:
            cmd += f" --max_files {args.max_files}"
        success = run_workflow_command(cmd, "基础评估 (不含RAG)")
        
    elif workflow == "rag-only":
        # 仅RAG增强评估
        for report_id in range(start_id, end_id + 1):
            cmd = f"python workflows/rerun_with_rag.py {report_id} --config {args.config}"
            if not run_workflow_command(cmd, f"RAG增强评估 (报告 {report_id})"):
                success = False
                break
                
    elif workflow == "retrieve":
        # 仅RAG检索
        cmd = f"bash scripts/step1_rag_retrieve.sh {start_id} {end_id} {args.top_k}"
        success = run_workflow_command(cmd, "RAG检索")
    
    # 最终结果
    print("\n" + "=" * 70)
    if success:
        print("🎉 工作流程执行成功!")
        print("\n📁 结果文件位置:")
        print("   • RAG缓存: final_result/rag_search_output/")
        print("   • 基础结果: final_result/baseline_results/")
        print("   • RAG增强结果: final_result/rerun_with_rag/")
        print("   • 对比分析: final_result/rerun_comparisons/")
    else:
        print("❌ 工作流程执行失败!")
        print("请检查错误信息并重试。")
    
    print("=" * 70)


if __name__ == "__main__":
    main()
