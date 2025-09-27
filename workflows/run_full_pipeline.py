#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
一键运行完整的RAG评估流程

功能：
1. 自动运行RAG检索 (step1) 
2. 自动运行RAG增强评估 (rerun_with_rag.py)
3. 生成完整的对比报告

用法：
    python run_full_pipeline.py 4000        # 单个报告
    python run_full_pipeline.py 4000 4002   # 报告范围
"""

import argparse
import subprocess
import sys
from pathlib import Path


def run_command(command: str, description: str) -> bool:
    """运行命令并实时显示输出"""
    print(f"\n🚀 {description}")
    print(f"💻 执行命令: {command}")
    print("=" * 80)
    
    try:
        # 实时输出而不是捕获
        result = subprocess.run(command, shell=True, check=True, text=True)
        print("=" * 80)
        print(f"✅ {description} - 成功完成")
        return True
    except subprocess.CalledProcessError as e:
        print("=" * 80)
        print(f"❌ {description} - 失败")
        print(f"错误码: {e.returncode}")
        return False


def main():
    parser = argparse.ArgumentParser(description="一键运行完整的RAG评估流程")
    parser.add_argument("start_id", type=int, help="开始报告ID")
    parser.add_argument("end_id", type=int, nargs='?', help="结束报告ID (可选，默认与start_id相同)")
    parser.add_argument("--top_k", type=int, default=3, help="RAG检索的top_k参数")
    parser.add_argument("--config", type=str, default="config/config_cn.yaml", help="配置文件路径")
    parser.add_argument("--db_type", type=str, default="sequential-block", 
                       choices=["sequential-block", "report-context", "uniform-random"],
                       help="使用的数据库类型")
    parser.add_argument("--use_new_rag", action="store_true", 
                       help="使用新构建的RAG索引（默认使用原有索引）")
    
    args = parser.parse_args()
    
    start_id = args.start_id
    end_id = args.end_id if args.end_id else start_id
    top_k = args.top_k
    
    print("=" * 60)
    print("🎯 RAG评估系统 - 完整流程")
    print("=" * 60)
    print(f"📋 报告范围: {start_id} - {end_id}")
    print(f"🔍 检索参数: top_k={top_k}")
    print(f"🗄️  数据库类型: {args.db_type}")
    print(f"🆕 使用新RAG: {'是' if args.use_new_rag else '否'}")
    
    base_dir = Path(__file__).parent.parent  # 项目根目录
    success_count = 0
    total_reports = end_id - start_id + 1
    
    for report_id in range(start_id, end_id + 1):
        print(f"\n{'='*40}")
        print(f"📊 处理报告 {report_id} ({success_count + 1}/{total_reports})")
        print(f"{'='*40}")
        
        # Step 1: RAG检索
        if args.use_new_rag:
            step1_cmd = f"bash {base_dir}/scripts/step1_rag_retrieve_new.sh {report_id} {report_id} {top_k} {args.db_type}"
        else:
            step1_cmd = f"bash {base_dir}/scripts/step1_rag_retrieve.sh {report_id} {report_id} {top_k}"
        
        if not run_command(step1_cmd, f"RAG检索 (报告 {report_id})"):
            print(f"⚠️  跳过报告 {report_id} 的后续步骤")
            continue
        
        # Step 2: RAG增强评估
        step2_cmd = f"python {base_dir}/workflows/rerun_with_rag.py {report_id} --config {args.config}"
        if not run_command(step2_cmd, f"RAG增强评估 (报告 {report_id})"):
            print(f"⚠️  报告 {report_id} 的RAG增强评估失败")
            continue
        
        success_count += 1
        print(f"🎉 报告 {report_id} 处理完成!")
    
    # 最终总结
    print("\n" + "=" * 60)
    print("📈 流程执行总结")
    print("=" * 60)
    print(f"✅ 成功处理: {success_count}/{total_reports} 个报告")
    
    if success_count > 0:
        print("\n📁 结果文件位置:")
        print(f"   🔍 RAG缓存: final_result/rag_search_output/")
        print(f"   🤖 RAG增强结果: final_result/rerun_with_rag/")
        print(f"   📊 对比分析: final_result/rerun_comparisons/")
        print("\n🎯 建议: 查看对比分析文件，了解RAG增强的效果")
    else:
        print("❌ 没有成功处理任何报告，请检查配置和数据")
    
    print("\n🏁 流程结束")


if __name__ == "__main__":
    main()
