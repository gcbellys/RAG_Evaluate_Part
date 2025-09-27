#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
完整批处理RAG评估流程
保持与full流程相同的步骤，但在OpenAI API调用时使用Batch API优化成本
"""

import argparse
import subprocess
import sys
import json
import os
import yaml
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List


def run_command(command: str, description: str) -> bool:
    """运行命令并显示结果"""
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


def load_config(config_path: str) -> Dict[str, Any]:
    """加载配置文件"""
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        return config
    except Exception as e:
        print(f"❌ 配置文件加载失败: {e}")
        sys.exit(1)


def run_full_batch_pipeline(start_id: int, 
                           end_id: int, 
                           top_k: int = 3,
                           config_path: str = "config/config.yaml",
                           batch_threshold: int = 10,
                           force_batch: bool = False,
                           data_dir: str = "test_set") -> bool:
    """运行完整的批处理RAG评估流程"""
    
    print("=" * 70)
    print("🎯 完整批处理RAG评估流程")
    print("=" * 70)
    print(f"📋 报告范围: {start_id} - {end_id}")
    print(f"📁 数据目录: {data_dir}")
    print(f"🔍 检索参数: top_k={top_k}")
    print(f"⚙️  配置文件: {config_path}")
    print(f"🚀 批处理模式: OpenAI使用Batch API，其他API使用传统模式")
    print(f"📊 批处理阈值: {batch_threshold}")
    print(f"🎯 强制批处理: {'是' if force_batch else '否'}")
    print("=" * 70)
    
    success_steps = 0
    total_steps = 4
    
    # 步骤1: RAG检索（使用批量优化版本）
    print(f"\n{'='*20} 步骤 1/4: RAG检索 {'='*20}")
    
    # 判断是否使用批量检索（多个报告时使用批量版本）
    if end_id > start_id:
        print("🚀 检测到多个报告，使用批量优化RAG检索（一次初始化FAISS索引）")
        cmd = f"bash scripts/step1_rag_retrieve_batch.sh {start_id} {end_id} {top_k} {config_path}"
    else:
        print("🚀 单个报告，使用标准RAG检索")
        cmd = f"bash scripts/step1_rag_retrieve.sh {start_id} {end_id} {top_k} {config_path}"
    
    if data_dir != "test_set":
        cmd += f" --data-dir {data_dir}"
    
    if run_command(cmd, "RAG检索 - 从知识库检索相关信息"):
        success_steps += 1
    else:
        print("❌ RAG检索失败，无法继续后续步骤")
        return False
    
    # 步骤2: 基础评估（使用批处理优化）
    print(f"\n{'='*20} 步骤 2/4: 基础评估 {'='*20}")
    cmd = f"python workflows/main_workflow_batch.py --start_id {start_id} --end_id {end_id} --config {config_path}"
    if batch_threshold != 10:
        cmd += f" --batch-threshold {batch_threshold}"
    if force_batch:
        cmd += " --force-batch"
    if data_dir != "test_set":
        cmd += f" --data-dir {data_dir}"
    
    if run_command(cmd, "基础评估 (使用批处理优化)"):
        success_steps += 1
    else:
        print("❌ 基础评估失败")
        return False
    
    # 步骤3: RAG增强评估（使用批处理优化）
    print(f"\n{'='*20} 步骤 3/4: RAG增强评估 {'='*20}")
    success_rag = True
    for report_id in range(start_id, end_id + 1):
        cmd = f"python workflows/rerun_with_rag_batch.py {report_id} --config {config_path}"
        if batch_threshold != 10:
            cmd += f" --batch-threshold {batch_threshold}"
        if force_batch:
            cmd += " --force-batch"
        if data_dir != "test_set":
            cmd += f" --data-dir {data_dir}"
        
        if not run_command(cmd, f"RAG增强评估 - 报告 {report_id} (使用批处理优化)"):
            success_rag = False
            break
    
    if success_rag:
        success_steps += 1
    else:
        print("❌ RAG增强评估失败")
        return False
    
    # 步骤4: 对比分析和Token统计
    print(f"\n{'='*20} 步骤 4/4: 对比分析 {'='*20}")
    
    # 4.1: 生成对比分析报告
    success_comparison = True
    for report_id in range(start_id, end_id + 1):
        cmd = f"python workflows/batch_comparison_workflow.py {report_id} --config {config_path}"
        if not run_command(cmd, f"对比分析 - 报告 {report_id}"):
            success_comparison = False
            break
    
    if success_comparison:
        print("✅ 对比分析完成")
    else:
        print("⚠️  对比分析失败，但不影响主流程")
    
    # 4.2: Token使用统计
    try:
        # 导入token分析函数
        sys.path.append(str(Path(__file__).parent.parent))
        from start_evaluation import generate_token_analysis
        
        if generate_token_analysis(start_id, end_id, config_path):
            print("✅ Token使用分析完成")
        else:
            print("⚠️  Token分析失败，但不影响主流程")
            
    except Exception as e:
        print(f"⚠️  Token分析异常: {e}")
    
    # 步骤4总是算作成功（即使部分失败也不影响主流程）
    success_steps += 1
    
    # 最终结果
    print("\n" + "=" * 70)
    if success_steps == total_steps:
        print("🎉 完整批处理RAG评估流程执行成功!")
        print(f"📊 成功完成 {success_steps}/{total_steps} 个步骤")
        
        print("\n📁 结果文件位置:")
        print("   • RAG缓存: Evaluate_output/rag_search_output/")
        print("   • 基础结果: Evaluate_output/baseline_results_batch/")
        print("   • RAG增强结果: Evaluate_output/rerun_with_rag_batch/")
        print("   • 对比分析: Evaluate_output/rerun_comparisons/")
        print("   • Token分析: Evaluate_output/tokens/")
        print("   • 批处理文件: batch_processing/")
        
        print(f"\n💰 成本优化:")
        print("   • OpenAI API: 使用Batch API，成本降低50%")
        print("   • 其他API: 保持传统调用模式")
        
        return True
    else:
        print("❌ 完整批处理RAG评估流程执行失败!")
        print(f"📊 完成 {success_steps}/{total_steps} 个步骤")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="完整批处理RAG评估流程",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
完整批处理RAG评估流程说明:
  这个流程与 'full' 模式完全相同，包含以下4个步骤：
  1. RAG检索 → 2. 基础评估 → 3. RAG增强评估 → 4. 对比分析
  
  区别在于：
  - OpenAI API调用使用Batch API，成本降低50%
  - 其他API保持传统逐条调用模式
  - 自动智能阈值控制和回退机制
  
  适用场景：
  - 需要完整RAG评估对比
  - 希望降低OpenAI API成本
  - 大规模评估任务
  - 可以接受轻微延迟（批处理排队时间）

示例:
  python full_batch_pipeline.py 4000                    # 单个报告
  python full_batch_pipeline.py 4000 4002               # 批量报告
  python full_batch_pipeline.py 4000 --force-batch      # 强制批处理
  python full_batch_pipeline.py 4000 --batch-threshold 5 # 自定义阈值
        """
    )
    
    parser.add_argument("start_id", type=int, help="开始报告ID")
    parser.add_argument("end_id", type=int, nargs='?', help="结束报告ID (可选)")
    parser.add_argument("--top_k", type=int, default=3, help="RAG检索top_k参数")
    parser.add_argument("--config", type=str, default="config/config.yaml", help="配置文件路径")
    
    # 批处理相关参数
    parser.add_argument("--batch-threshold", type=int, default=10,
                       help="启用批处理的最小症状数量阈值 (默认10)")
    parser.add_argument("--force-batch", action="store_true",
                       help="强制使用批处理，忽略阈值限制")
    
    # 数据目录参数
    parser.add_argument("--data-dir", type=str, default="test_set",
                       help="数据目录路径 (默认: test_set)")
    
    args = parser.parse_args()
    
    start_id = args.start_id
    end_id = args.end_id if args.end_id else start_id
    
    # 运行完整批处理流程
    success = run_full_batch_pipeline(
        start_id=start_id,
        end_id=end_id,
        top_k=args.top_k,
        config_path=args.config,
        batch_threshold=args.batch_threshold,
        force_batch=args.force_batch,
        data_dir=args.data_dir
    )
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
