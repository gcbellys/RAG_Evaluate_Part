#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RAG_3DB完整评估流程 - 使用新的三个RAG数据库系统

功能：
1. 支持三种RAG数据库的评估：Uniform Random Unit, Report Context, Sequential Block
2. 自动运行完整的RAG评估流程
3. 生成对比分析报告
4. 支持批量处理和并行评估

用法：
    python workflows/rag3db_full_pipeline.py 4000        # 单个报告，使用默认数据库
    python workflows/rag3db_full_pipeline.py 4000 4002   # 报告范围，使用默认数据库
    python workflows/rag3db_full_pipeline.py 4000 --rag_db_type report_context  # 指定数据库类型
    python workflows/rag3db_full_pipeline.py 4000 4002 --compare_all_dbs        # 对比所有数据库

作者: AI Assistant
日期: 2025-09-23
"""

import argparse
import subprocess
import sys
import json
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List


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


def get_db_info(db_type: str) -> Dict[str, str]:
    """获取数据库信息"""
    db_configs = {
        'uniform': {
            'name': 'Uniform Random Unit Database',
            'description': '纯随机采样的SDU数据库，43,000个症状-诊断单元',
            'features': '最大数据多样性，无上下文偏差'
        },
        'report_context': {
            'name': 'Report Context Database', 
            'description': '报告级采样的SDU数据库，保持完整报告上下文，43,000个症状-诊断单元',
            'features': '保持报告上下文，症状关联性强'
        },
        'sequential_block': {
            'name': 'Sequential Block Database',
            'description': '顺序采样的SDU数据库，保持时间顺序，43,000个症状-诊断单元', 
            'features': '保持时间顺序，反映数据演变'
        }
    }
    return db_configs.get(db_type, {})


def run_single_db_evaluation(start_id: int, end_id: int, rag_db_type: str, 
                            top_k: int, config_path: str, data_dir: str) -> bool:
    """运行单个数据库的完整评估流程"""
    
    db_info = get_db_info(rag_db_type)
    print(f"\n{'='*80}")
    print(f"🎯 开始评估 - {db_info.get('name', rag_db_type)}")
    print(f"📋 {db_info.get('description', '')}")
    print(f"✨ 特点: {db_info.get('features', '')}")
    print(f"📊 报告范围: {start_id} - {end_id}")
    print(f"🔍 Top-K: {top_k}")
    print(f"{'='*80}")
    
    base_dir = Path(__file__).parent.parent  # 项目根目录
    success_count = 0
    total_reports = end_id - start_id + 1
    
    # Step 1: RAG检索（使用新的RAG_3DB系统）
    print(f"\n{'='*60}")
    print("🔍 Step 1: RAG_3DB检索阶段")
    print(f"{'='*60}")
    
    rag_cmd = f"bash {base_dir}/scripts/step1_rag3db_retrieve.sh {start_id} {end_id} {top_k} {rag_db_type} {config_path}"
    if data_dir != "test_set":
        rag_cmd += f" --data-dir {data_dir}"
        
    if not run_command(rag_cmd, f"RAG_3DB检索 ({rag_db_type})"):
        print("❌ RAG检索失败，无法继续")
        return False
    
    # Step 2: 逐个进行RAG增强评估
    print(f"\n{'='*60}")
    print("🚀 Step 2: RAG增强评估阶段")
    print(f"{'='*60}")
    
    for report_id in range(start_id, end_id + 1):
        print(f"\n{'='*40}")
        print(f"📊 处理报告 {report_id} ({success_count + 1}/{total_reports})")
        print(f"🗃️  数据库: {rag_db_type}")
        print(f"{'='*40}")
        
        # RAG增强评估
        step2_cmd = f"python {base_dir}/workflows/rerun_with_rag.py {report_id} --config {config_path}"
        if data_dir != "test_set":
            step2_cmd += f" --data-dir {data_dir}"
            
        if not run_command(step2_cmd, f"RAG增强评估 (报告 {report_id})"):
            print(f"⚠️  报告 {report_id} 的RAG增强评估失败")
            continue
        
        success_count += 1
        print(f"🎉 报告 {report_id} 处理完成!")
    
    # 评估结果统计
    print(f"\n{'='*80}")
    print(f"📊 {db_info.get('name', rag_db_type)} 评估完成")
    print(f"✅ 成功处理: {success_count}/{total_reports} 个报告")
    print(f"📁 结果保存在: Evaluate_output/")
    print(f"{'='*80}")
    
    return success_count > 0


def run_comparison_analysis(start_id: int, end_id: int, db_types: List[str], 
                          config_path: str) -> bool:
    """运行多数据库对比分析"""
    
    print(f"\n{'='*80}")
    print("📊 多数据库对比分析")
    print(f"🔍 对比数据库: {', '.join(db_types)}")
    print(f"📋 报告范围: {start_id} - {end_id}")
    print(f"{'='*80}")
    
    base_dir = Path(__file__).parent.parent
    
    # 生成对比分析报告
    for report_id in range(start_id, end_id + 1):
        print(f"\n📊 生成报告 {report_id} 的对比分析...")
        
        comp_cmd = f"python {base_dir}/workflows/comparision_workflow.py --start_id {report_id} --end_id {report_id} --config {config_path}"
        
        if not run_command(comp_cmd, f"对比分析 (报告 {report_id})"):
            print(f"⚠️  报告 {report_id} 的对比分析失败")
            continue
        
        print(f"✅ 报告 {report_id} 对比分析完成")
    
    return True


def generate_summary_report(start_id: int, end_id: int, db_types: List[str], 
                          config_path: str) -> bool:
    """生成总结报告"""
    
    print(f"\n{'='*80}")
    print("📋 生成RAG_3DB评估总结报告")
    print(f"{'='*80}")
    
    # 创建总结报告
    summary = {
        'evaluation_info': {
            'timestamp': datetime.now().isoformat(),
            'report_range': f"{start_id}-{end_id}",
            'total_reports': end_id - start_id + 1,
            'databases_evaluated': db_types
        },
        'database_info': {
            db_type: get_db_info(db_type) for db_type in db_types
        },
        'results_location': {
            'rag_cache': 'Evaluate_output/rag_search_output/',
            'baseline_results': 'Evaluate_output/baseline_results/',
            'rag_enhanced_results': 'Evaluate_output/rerun_with_rag/',
            'comparison_results': 'Evaluate_output/rerun_comparisons/',
            'token_analysis': 'Evaluate_output/tokens/'
        }
    }
    
    # 保存总结报告
    output_dir = Path("Evaluate_output")
    output_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    summary_file = output_dir / f"rag3db_evaluation_summary_{start_id}_{end_id}_{timestamp}.json"
    
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    
    print(f"📄 总结报告已保存: {summary_file}")
    return True


def main():
    parser = argparse.ArgumentParser(
        description="RAG_3DB完整评估流程",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
RAG数据库类型说明:
  uniform          Uniform Random Unit Database
                   纯随机采样的SDU数据库，最大数据多样性
  
  report_context   Report Context Database  
                   报告级采样的SDU数据库，保持完整报告上下文
  
  sequential_block Sequential Block Database
                   顺序采样的SDU数据库，保持时间顺序

示例:
  python workflows/rag3db_full_pipeline.py 4000
  python workflows/rag3db_full_pipeline.py 4000 4002 --rag_db_type report_context
  python workflows/rag3db_full_pipeline.py 4000 4002 --compare_all_dbs
        """
    )
    
    parser.add_argument("start_id", type=int, help="开始报告ID")
    parser.add_argument("end_id", type=int, nargs='?', help="结束报告ID (可选)")
    parser.add_argument("--rag_db_type", default="uniform", 
                       choices=['uniform', 'report_context', 'sequential_block'],
                       help="RAG数据库类型 (默认: uniform)")
    parser.add_argument("--top_k", type=int, default=3, help="RAG检索top_k参数")
    parser.add_argument("--config", type=str, default="config/config_rag3db.yaml", 
                       help="配置文件路径")
    parser.add_argument("--data_dir", type=str, default="test_set",
                       help="数据目录路径 (默认: test_set)")
    parser.add_argument("--compare_all_dbs", action="store_true",
                       help="对比所有三个数据库")
    
    args = parser.parse_args()
    
    start_id = args.start_id
    end_id = args.end_id if args.end_id else start_id
    
    print("=" * 80)
    print("🎯 RAG_3DB评估系统")
    print("=" * 80)
    print(f"📋 报告范围: {start_id} - {end_id}")
    print(f"📁 数据目录: {args.data_dir}")
    print(f"🔍 检索参数: top_k={args.top_k}")
    print(f"⚙️  配置文件: {args.config}")
    
    success = True
    
    if args.compare_all_dbs:
        # 对比所有三个数据库
        db_types = ['uniform', 'report_context', 'sequential_block']
        print(f"🔄 对比模式: 评估所有三个RAG数据库")
        
        for db_type in db_types:
            if not run_single_db_evaluation(start_id, end_id, db_type, 
                                           args.top_k, args.config, args.data_dir):
                print(f"❌ {db_type} 数据库评估失败")
                success = False
        
        # 生成对比分析
        if success:
            run_comparison_analysis(start_id, end_id, db_types, args.config)
            generate_summary_report(start_id, end_id, db_types, args.config)
    else:
        # 单个数据库评估
        db_types = [args.rag_db_type]
        print(f"🎯 单数据库模式: {args.rag_db_type}")
        
        success = run_single_db_evaluation(start_id, end_id, args.rag_db_type,
                                         args.top_k, args.config, args.data_dir)
        
        if success:
            generate_summary_report(start_id, end_id, db_types, args.config)
    
    # 最终结果
    print("\n" + "=" * 80)
    if success:
        print("🎉 RAG_3DB评估流程执行成功!")
        print("\n📁 结果文件位置:")
        print("   • RAG缓存: Evaluate_output/rag_search_output/")
        print("   • 基础结果: Evaluate_output/baseline_results/")
        print("   • RAG增强结果: Evaluate_output/rerun_with_rag/")
        print("   • 对比分析: Evaluate_output/rerun_comparisons/")
        print("   • 总结报告: Evaluate_output/rag3db_evaluation_summary_*.json")
        
        if args.compare_all_dbs:
            print(f"\n🔍 数据库对比:")
            for db_type in db_types:
                db_info = get_db_info(db_type)
                print(f"   • {db_info.get('name', db_type)}: {db_info.get('features', '')}")
    else:
        print("❌ RAG_3DB评估流程执行失败!")
        print("请检查错误信息并重试。")
    
    print("=" * 80)


if __name__ == "__main__":
    main()
