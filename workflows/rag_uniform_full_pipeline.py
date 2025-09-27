#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RAG Uniform数据库增强版完整评估流程 - 专用于Uniform Random Unit数据库

功能：
1. 专门针对Uniform Random Unit数据库的RAG评估
2. 使用最新的增强版RAG搜索策略（查询扩展、语义重排、多样性过滤等）
3. 集成置信度感知的智能prompt系统
4. 自动运行完整的RAG评估流程
5. 生成详细的评估报告
6. 支持批量处理和并行评估
7. 使用修复后的高质量索引系统

用法：
    python workflows/rag_uniform_full_pipeline.py 43001        # 单个报告
    python workflows/rag_uniform_full_pipeline.py 43001 43010  # 报告范围
    python workflows/rag_uniform_full_pipeline.py 43001 --enhanced  # 使用增强版RAG

特点：
- 使用修复后的Faiss索引 (/home/duojiechen/projects/Rag_system/RAG_3DB/faiss_indexes/rag_uniform_db)
- 🚀 增强版RAG搜索：查询扩展、语义重排、自适应Top-K
- 🧠 置信度感知prompt：根据相似度动态调整LLM指令
- 🎯 自主判断增强：强调临床经验优先，批判性评估RAG结果
- 专门优化的Uniform Random Unit数据库评估

作者: AI Assistant
日期: 2025-09-24 (增强版)
"""

import argparse
import subprocess
import sys
import json
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List

# 添加脚本路径以支持增强版RAG
sys.path.append(str(Path(__file__).parent.parent / "scripts"))
try:
    from enhanced_rag_search_adapter import EnhancedRAGSearchAdapter
    from confidence_aware_rag_adapter import ConfidenceAwareRAGAdapter
    ENHANCED_RAG_AVAILABLE = True
except ImportError:
    print("⚠️ 增强版RAG模块未找到，将使用标准RAG流程")
    ENHANCED_RAG_AVAILABLE = False


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


def run_enhanced_rag_evaluation(start_id: int, end_id: int, top_k: int, config_path: str, 
                               data_dir: str, use_enhanced: bool = True) -> bool:
    """运行增强版RAG评估流程"""
    
    if not ENHANCED_RAG_AVAILABLE or not use_enhanced:
        print("🔄 回退到标准RAG流程")
        return run_uniform_db_evaluation(start_id, end_id, top_k, config_path, data_dir)
    
    rag_db_type = "uniform"
    db_info = get_db_info(rag_db_type)
    
    print(f"\n{'='*80}")
    print(f"🚀 RAG Uniform数据库增强版评估")
    print(f"📋 {db_info.get('description', '')}")
    print(f"✨ 特点: {db_info.get('features', '')}")
    print(f"🔥 增强功能: 查询扩展、语义重排、置信度感知prompt")
    print(f"📊 报告范围: {start_id} - {end_id}")
    print(f"🔍 Top-K: {top_k}")
    print(f"🗂️  索引路径: /home/duojiechen/projects/Rag_system/RAG_3DB/faiss_indexes/rag_uniform_db")
    print(f"{'='*80}")
    
    base_dir = Path(__file__).parent.parent
    success_count = 0
    total_reports = end_id - start_id + 1
    
    # 初始化增强版RAG适配器
    try:
        rag_adapter = ConfidenceAwareRAGAdapter(
            rag_db_type=rag_db_type,
            debug=True
        )
        print("✅ 增强版RAG适配器初始化成功")
    except Exception as e:
        print(f"❌ 增强版RAG适配器初始化失败: {e}")
        print("🔄 回退到标准RAG流程")
        return run_uniform_db_evaluation(start_id, end_id, top_k, config_path, data_dir)
    
    # Step 1: 增强版RAG检索
    print(f"\n{'='*60}")
    print("🔍 Step 1: 增强版RAG检索阶段")
    print(f"{'='*60}")
    
    for report_id in range(start_id, end_id + 1):
        print(f"\n{'='*40}")
        print(f"📊 处理报告 {report_id} ({success_count + 1}/{total_reports})")
        print(f"🗃️  数据库: Uniform Random Unit Database (增强版)")
        print(f"{'='*40}")
        
        try:
            # 读取诊断文件
            if data_dir == "test_set":
                input_file = f"/home/duojiechen/Central_Data/Testset_0_43000-43508/diagnostic_results_normalized/diagnostic_{report_id}.json"
            else:
                input_file = f"{data_dir}/diagnostic_{report_id}.json"
            
            if not os.path.exists(input_file):
                print(f"⚠️ 输入文件不存在: {input_file}")
                continue
            
            # 使用增强版RAG进行检索和评估 - 一体化流程
            enhanced_rag_cmd = f"python {base_dir}/workflows/enhanced_rag_evaluation_pipeline.py --file {input_file} --top_k {top_k} --output_dir results/enhanced_evaluation --rag_db_type uniform"
            
            if not run_command(enhanced_rag_cmd, f"增强版RAG检索和评估 (报告 {report_id})"):
                print(f"⚠️ 报告 {report_id} 的增强版RAG处理失败，尝试分步处理")
                
                # 分步处理：先RAG检索
                rag_cmd = f"python {base_dir}/scripts/confidence_aware_rag_adapter.py --file {input_file} --top_k {top_k} --output_dir results/rag_output_uniform --rag_db_type uniform"
                
                if not run_command(rag_cmd, f"增强版RAG检索 (报告 {report_id})"):
                    print(f"⚠️ 报告 {report_id} 的增强版RAG检索失败")
                    continue
                
                # 再进行标准评估
                step2_cmd = f"python {base_dir}/workflows/rerun_with_rag.py {report_id} --config {config_path} --rag_cache_dir results/rag_output_uniform"
                if data_dir != "test_set":
                    step2_cmd += f" --data-dir {data_dir}"
                
                if not run_command(step2_cmd, f"RAG评估 (报告 {report_id})"):
                    print(f"⚠️ 报告 {report_id} 的RAG评估失败")
                    continue
            
            success_count += 1
            print(f"🎉 报告 {report_id} 增强版处理完成!")
            
        except Exception as e:
            print(f"❌ 报告 {report_id} 处理异常: {e}")
            continue
    
    # 评估结果统计
    print(f"\n{'='*80}")
    print(f"📊 RAG Uniform数据库增强版评估完成")
    print(f"✅ 成功处理: {success_count}/{total_reports} 个报告")
    print(f"🚀 使用功能: 增强版RAG搜索 + 置信度感知prompt")
    print(f"📁 结果保存在: results/")
    print(f"{'='*80}")
    
    return success_count > 0


def run_uniform_db_evaluation(start_id: int, end_id: int, top_k: int, config_path: str, data_dir: str) -> bool:
    """运行Uniform数据库的完整评估流程"""
    
    rag_db_type = "uniform"  # 固定使用uniform数据库
    db_info = get_db_info(rag_db_type)
    
    print(f"\n{'='*80}")
    print(f"🎯 RAG Uniform数据库评估")
    print(f"📋 {db_info.get('description', '')}")
    print(f"✨ 特点: {db_info.get('features', '')}")
    print(f"📊 报告范围: {start_id} - {end_id}")
    print(f"🔍 Top-K: {top_k}")
    print(f"🗂️  索引路径: /home/duojiechen/projects/Rag_system/RAG_3DB/faiss_indexes/rag_uniform_db")
    print(f"{'='*80}")
    
    base_dir = Path(__file__).parent.parent  # 项目根目录
    success_count = 0
    total_reports = end_id - start_id + 1
    
    # Step 1: RAG检索（使用修复后的Uniform数据库）
    print(f"\n{'='*60}")
    print("🔍 Step 1: RAG Uniform数据库检索阶段")
    print(f"{'='*60}")
    
    rag_cmd = f"bash {base_dir}/scripts/step1_rag3db_retrieve.sh {start_id} {end_id} {top_k} {rag_db_type} {config_path}"
    if data_dir != "test_set":
        rag_cmd += f" --data-dir {data_dir}"
        
    if not run_command(rag_cmd, f"RAG Uniform数据库检索"):
        print("❌ RAG检索失败，无法继续")
        return False
    
    # Step 2: 逐个进行RAG增强评估
    print(f"\n{'='*60}")
    print("🚀 Step 2: RAG Uniform增强评估阶段")
    print(f"{'='*60}")
    
    for report_id in range(start_id, end_id + 1):
        print(f"\n{'='*40}")
        print(f"📊 处理报告 {report_id} ({success_count + 1}/{total_reports})")
        print(f"🗃️  数据库: Uniform Random Unit Database")
        print(f"{'='*40}")
        
        # RAG增强评估 - 指定uniform专用的RAG缓存目录
        step2_cmd = f"python {base_dir}/workflows/rerun_with_rag.py {report_id} --config {config_path} --rag_cache_dir results/rag_output_uniform"
        if data_dir != "test_set":
            step2_cmd += f" --data-dir {data_dir}"
            
        if not run_command(step2_cmd, f"RAG Uniform增强评估 (报告 {report_id})"):
            print(f"⚠️  报告 {report_id} 的RAG增强评估失败")
            continue
        
        success_count += 1
        print(f"🎉 报告 {report_id} 处理完成!")
    
    # 评估结果统计
    print(f"\n{'='*80}")
    print(f"📊 RAG Uniform数据库评估完成")
    print(f"✅ 成功处理: {success_count}/{total_reports} 个报告")
    print(f"📁 结果保存在: results/")
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


def generate_uniform_summary_report(start_id: int, end_id: int, config_path: str) -> bool:
    """生成Uniform数据库评估总结报告"""
    
    print(f"\n{'='*80}")
    print("📋 生成RAG Uniform数据库评估总结报告")
    print(f"{'='*80}")
    
    # 创建总结报告
    summary = {
        'evaluation_info': {
            'timestamp': datetime.now().isoformat(),
            'report_range': f"{start_id}-{end_id}",
            'total_reports': end_id - start_id + 1,
            'database_type': 'uniform',
            'database_name': 'Uniform Random Unit Database',
            'index_path': '/home/duojiechen/projects/Rag_system/RAG_3DB/faiss_indexes/rag_uniform_db',
            'search_method': 'FIXED_similarity_calculation'
        },
        'database_info': get_db_info('uniform'),
        'results_location': {
            'rag_cache': 'results/rag_output_uniform/',
            'baseline_results': 'results/baseline_results/',
            'rag_enhanced_results': 'results/rerun_with_rag/',
            'comparison_results': 'results/rerun_comparisons/',
            'token_analysis': 'results/tokens/'
        },
        'technical_details': {
            'faiss_index_type': 'IndexFlatIP',
            'vector_dimension': 768,
            'total_vectors': 43000,
            'similarity_metric': 'cosine_similarity',
            'model_used': 'SapBERT (cambridgeltl/SapBERT-from-PubMedBERT-fulltext)'
        }
    }
    
    # 保存总结报告
    output_dir = Path("results")
    output_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    summary_file = output_dir / f"rag_uniform_evaluation_summary_{start_id}_{end_id}_{timestamp}.json"
    
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    
    print(f"📄 总结报告已保存: {summary_file}")
    return True


def main():
    parser = argparse.ArgumentParser(
        description="RAG Uniform数据库增强版完整评估流程",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
RAG Uniform数据库增强版说明:
  专门针对Uniform Random Unit Database的增强版评估流程
  - 纯随机采样的43,000个SDU数据库
  - 使用修复后的高质量Faiss索引
  - 🚀 增强版RAG搜索：查询扩展、语义重排、多样性过滤
  - 🧠 置信度感知prompt：根据相似度动态调整LLM指令
  - 🎯 自主判断增强：强调临床经验优先
  - 索引路径: /home/duojiechen/projects/Rag_system/RAG_3DB/faiss_indexes/rag_uniform_db

示例:
  # 标准RAG流程
  python workflows/rag_uniform_full_pipeline.py 43001
  python workflows/rag_uniform_full_pipeline.py 43001 43010
  
  # 增强版RAG流程 (推荐)
  python workflows/rag_uniform_full_pipeline.py 43001 --enhanced
  python workflows/rag_uniform_full_pipeline.py 43001 43010 --enhanced --top_k 5
  
  # 强制使用标准流程
  python workflows/rag_uniform_full_pipeline.py 43001 --no-enhanced
        """
    )
    
    parser.add_argument("start_id", type=int, help="开始报告ID")
    parser.add_argument("end_id", type=int, nargs='?', help="结束报告ID (可选)")
    parser.add_argument("--top_k", type=int, default=3, help="RAG检索top_k参数")
    parser.add_argument("--config", type=str, default="config/config_cn.yaml", 
                       help="配置文件路径")
    parser.add_argument("--data_dir", type=str, default="test_set",
                       help="数据目录路径 (默认: test_set)")
    parser.add_argument("--enhanced", action="store_true", default=True,
                       help="使用增强版RAG搜索和置信度感知prompt (默认开启)")
    parser.add_argument("--no-enhanced", action="store_true", 
                       help="强制使用标准RAG流程")
    
    args = parser.parse_args()
    
    start_id = args.start_id
    end_id = args.end_id if args.end_id else start_id
    
    # 确定是否使用增强版
    use_enhanced = args.enhanced and not args.no_enhanced and ENHANCED_RAG_AVAILABLE
    
    print("=" * 80)
    print("🎯 RAG Uniform数据库增强版评估系统")
    print("=" * 80)
    print(f"📋 报告范围: {start_id} - {end_id}")
    print(f"📁 数据目录: {args.data_dir}")
    print(f"🔍 检索参数: top_k={args.top_k}")
    print(f"⚙️  配置文件: {args.config} (默认: config_cn.yaml)")
    print(f"🗂️  数据库类型: Uniform Random Unit Database (固定)")
    print(f"📊 索引状态: 修复后的高质量索引")
    
    if use_enhanced:
        print(f"🚀 评估模式: 增强版 (查询扩展 + 语义重排 + 置信度感知prompt)")
        print(f"🧠 Prompt类型: 置信度感知 + 自主判断增强")
    else:
        print(f"📊 评估模式: 标准版")
        if not ENHANCED_RAG_AVAILABLE:
            print(f"⚠️  增强版模块不可用，使用标准流程")
        elif args.no_enhanced:
            print(f"ℹ️  用户选择标准流程")
    
    # 运行评估
    if use_enhanced:
        print(f"🚀 启动增强版RAG评估流程")
        success = run_enhanced_rag_evaluation(start_id, end_id, args.top_k, args.config, args.data_dir, True)
    else:
        print(f"📊 启动标准RAG评估流程")
        success = run_uniform_db_evaluation(start_id, end_id, args.top_k, args.config, args.data_dir)
    
    if success:
        generate_uniform_summary_report(start_id, end_id, args.config)
    
    # 最终结果
    print("\n" + "=" * 80)
    if success:
        if use_enhanced:
            print("🎉 RAG Uniform数据库增强版评估流程执行成功!")
            print("\n🚀 增强功能使用情况:")
            print("   • ✅ 查询扩展 (同义词、缩写、医学术语)")
            print("   • ✅ 多查询检索 (提高召回率)")
            print("   • ✅ 语义重排 (提高精确度)")
            print("   • ✅ 多样性过滤 (避免重复结果)")
            print("   • ✅ 自适应Top-K (动态调整检索数量)")
            print("   • ✅ 置信度感知prompt (根据相似度调整指令)")
            print("   • ✅ 自主判断增强 (强调临床经验优先)")
        else:
            print("🎉 RAG Uniform数据库标准评估流程执行成功!")
        
        print("\n📁 结果文件位置:")
        print("   • RAG缓存: results/rag_output_uniform/")
        print("   • 基础结果: results/baseline_results/")
        print("   • RAG增强结果: results/rerun_with_rag/")
        print("   • 对比分析: results/rerun_comparisons/")
        print("   • 总结报告: results/rag_uniform_evaluation_summary_*.json")
        
        print(f"\n🔍 数据库特点:")
        db_info = get_db_info('uniform')
        print(f"   • {db_info.get('name', 'Uniform Database')}: {db_info.get('features', '')}")
        print(f"   • 索引类型: IndexFlatIP (余弦相似度)")
        print(f"   • 向量维度: 768")
        print(f"   • 总向量数: 43,000")
        
        if use_enhanced:
            print(f"\n💡 下一步建议:")
            print(f"   • 使用 analyze_batch_results.py 分析整体效果")
            print(f"   • 对比增强版与标准版的性能差异")
            print(f"   • 查看置信度感知prompt的实际影响")
    else:
        if use_enhanced:
            print("❌ RAG Uniform数据库增强版评估流程执行失败!")
        else:
            print("❌ RAG Uniform数据库标准评估流程执行失败!")
        print("请检查错误信息并重试。")
    
    print("=" * 80)


if __name__ == "__main__":
    main()
