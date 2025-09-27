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
    python start_evaluation.py full 17500 --data-dir diag_data_normalized  # 使用不同数据目录
"""

import argparse
import subprocess
import sys
import json
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List


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


def load_json_file(file_path: str) -> Dict[str, Any]:
    """加载JSON文件"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"⚠️  无法加载文件 {file_path}: {e}")
        return {}


def find_latest_result_files(report_id: str, config_path: str = "config/config.yaml") -> tuple:
    """查找最新的baseline和RAG结果文件"""
    from src.config_loader import ConfigLoader
    config = ConfigLoader(config_path)
    output_base = config.get_path('output_results')
    output_dir = Path(output_base)
    
    # 判断是否为批处理模式（通过配置文件名判断）
    is_batch_mode = "openai" in config_path
    
    if is_batch_mode:
        # 批处理模式的文件路径和命名
        baseline_dir = output_dir / "baseline_results_batch"
        rag_dir = output_dir / "rerun_with_rag_batch"
        
        # 批处理模式的文件名模式
        baseline_files = list(baseline_dir.glob(f"baseline_batch_report_*{report_id}*.json"))
        rag_files = list(rag_dir.glob(f"rag_enhanced_batch_report_{report_id}_*.json"))
    else:
        # 普通模式的文件路径和命名
        baseline_dir = output_dir / "baseline_results"
        rag_dir = output_dir / "rerun_with_rag"
        
        # 普通模式的文件名模式
        baseline_files = list(baseline_dir.glob(f"*{report_id}*.json"))
        rag_files = list(rag_dir.glob(f"*{report_id}*.json"))
    
    baseline_file = str(max(baseline_files, key=os.path.getctime)) if baseline_files else ""
    rag_file = str(max(rag_files, key=os.path.getctime)) if rag_files else ""
    
    return baseline_file, rag_file


def extract_token_stats(data: Dict[str, Any], data_type: str) -> Dict[str, Any]:
    """提取token统计信息"""
    if data_type == "baseline":
        # 检查是否为批处理模式的格式（有report_id字段且symptoms是列表）
        if 'report_id' in data and isinstance(data.get('symptoms', []), list):
            # 批处理模式格式
            symptoms = data.get('symptoms', [])
            token_summary = {
                'total_tokens': 0,
                'total_prompt_tokens': 0,
                'total_completion_tokens': 0,
                'cache_read_tokens_total': 0,
                'cache_creation_tokens_total': 0,
                'api_breakdown': {}
            }
            
            symptom_stats = {}
            for symptom in symptoms:
                symptom_text = symptom.get('symptom_text', '')
                api_responses = symptom.get('api_responses', {})
                
                symptom_tokens = {}
                for api_name, api_data in api_responses.items():
                    usage = api_data.get('usage', {})
                    if usage:
                        tokens = usage.get('total_tokens', 0)
                        prompt_tokens = usage.get('prompt_tokens', 0)
                        completion_tokens = usage.get('completion_tokens', 0)
                        cached_tokens = usage.get('prompt_tokens_details', {}).get('cached_tokens', 0)
                        
                        symptom_tokens[api_name] = tokens
                        
                        # 累加到总计
                        token_summary['total_tokens'] += tokens
                        token_summary['total_prompt_tokens'] += prompt_tokens
                        token_summary['total_completion_tokens'] += completion_tokens
                        token_summary['cache_read_tokens_total'] += cached_tokens
                        
                        # API级别统计
                        if api_name not in token_summary['api_breakdown']:
                            token_summary['api_breakdown'][api_name] = {
                                'total_tokens': 0,
                                'prompt_tokens': 0,
                                'completion_tokens': 0,
                                'cache_read_tokens': 0,
                                'cache_creation_tokens': 0,
                                'calls': 0
                            }
                        
                        api_breakdown = token_summary['api_breakdown'][api_name]
                        api_breakdown['total_tokens'] += tokens
                        api_breakdown['prompt_tokens'] += prompt_tokens
                        api_breakdown['completion_tokens'] += completion_tokens
                        api_breakdown['cache_read_tokens'] += cached_tokens
                        api_breakdown['calls'] += 1
                
                if symptom_tokens:
                    symptom_stats[symptom_text] = symptom_tokens
            
            return {
                'total_summary': token_summary,
                'symptom_breakdown': symptom_stats
            }
        else:
            # 原有格式
            token_summary = data.get('token_summary', {})
            symptoms = data.get('symptoms', [])
            
            symptom_stats = {}
            for symptom in symptoms:
                diagnosis = symptom.get('diagnosis', '')
                api_responses = symptom.get('api_responses', {})
                
                symptom_tokens = {}
                for api_name, api_data in api_responses.items():
                    usage = api_data.get('usage', {})
                    if usage:
                        symptom_tokens[api_name] = usage.get('total_tokens', 0)
                
                if symptom_tokens:
                    symptom_stats[diagnosis] = symptom_tokens
            
            return {
                'total_summary': token_summary,
                'symptom_breakdown': symptom_stats
            }
    
    elif data_type == "rag":
        # 检查是否为批处理模式的格式（有report_id字段且symptoms是列表）
        if 'report_id' in data and isinstance(data.get('symptoms', []), list):
            # 批处理模式格式
            symptoms = data.get('symptoms', [])
            token_summary = {
                'total_tokens': 0,
                'total_prompt_tokens': 0,
                'total_completion_tokens': 0,
                'cache_read_tokens_total': 0,
                'cache_creation_tokens_total': 0,
                'api_breakdown': {}
            }
            
            symptom_stats = {}
            for symptom in symptoms:
                symptom_text = symptom.get('symptom_text', '')
                api_responses = symptom.get('api_responses', {})
                
                symptom_tokens = {}
                for api_name, api_data in api_responses.items():
                    usage = api_data.get('usage', {})
                    if usage:
                        tokens = usage.get('total_tokens', 0)
                        prompt_tokens = usage.get('prompt_tokens', 0)
                        completion_tokens = usage.get('completion_tokens', 0)
                        cached_tokens = usage.get('prompt_tokens_details', {}).get('cached_tokens', 0)
                        
                        symptom_tokens[api_name] = tokens
                        
                        # 累加到总计
                        token_summary['total_tokens'] += tokens
                        token_summary['total_prompt_tokens'] += prompt_tokens
                        token_summary['total_completion_tokens'] += completion_tokens
                        token_summary['cache_read_tokens_total'] += cached_tokens
                        
                        # API级别统计
                        if api_name not in token_summary['api_breakdown']:
                            token_summary['api_breakdown'][api_name] = {
                                'total_tokens': 0,
                                'prompt_tokens': 0,
                                'completion_tokens': 0,
                                'cache_read_tokens': 0,
                                'cache_creation_tokens': 0,
                                'calls': 0
                            }
                        
                        api_breakdown = token_summary['api_breakdown'][api_name]
                        api_breakdown['total_tokens'] += tokens
                        api_breakdown['prompt_tokens'] += prompt_tokens
                        api_breakdown['completion_tokens'] += completion_tokens
                        api_breakdown['cache_read_tokens'] += cached_tokens
                        api_breakdown['calls'] += 1
                
                if symptom_tokens:
                    symptom_stats[symptom_text] = symptom_tokens
            
            return {
                'total_summary': token_summary,
                'symptom_breakdown': symptom_stats
            }
        # RAG格式 - 检查新格式和旧格式
        elif 'token_summary' in data and 'symptoms' in data:
            # 新格式 - 确保包含缓存统计字段
            token_summary = data['token_summary']
            # 确保新格式也有缓存统计字段
            if 'cache_read_tokens_total' not in token_summary:
                token_summary['cache_read_tokens_total'] = 0
            if 'cache_creation_tokens_total' not in token_summary:
                token_summary['cache_creation_tokens_total'] = 0
                
            # 确保API breakdown也有缓存字段
            for api_data in token_summary.get('api_breakdown', {}).values():
                if 'cache_read_tokens' not in api_data:
                    api_data['cache_read_tokens'] = 0
                if 'cache_creation_tokens' not in api_data:
                    api_data['cache_creation_tokens'] = 0
                    
            symptoms_data = data['symptoms']
        else:
            # 旧格式，手动计算
            token_summary = {
                'total_tokens': 0,
                'total_prompt_tokens': 0,
                'total_completion_tokens': 0,
                'cache_read_tokens_total': 0,        # 新增
                'cache_creation_tokens_total': 0,    # 新增
                'api_breakdown': {}
            }
            symptoms_data = data
        
        symptom_stats = {}
        for diagnosis, symptom_data in symptoms_data.items():
            if isinstance(symptom_data, dict) and 'api_responses' in symptom_data:
                api_responses = symptom_data['api_responses']
                symptom_tokens = {}
                
                for api_name, api_data in api_responses.items():
                    usage = api_data.get('usage', {})
                    if usage:
                        tokens = usage.get('total_tokens', 0)
                        cache_read = usage.get('cache_read_tokens', 0)          # 新增
                        cache_create = usage.get('cache_creation_tokens', 0)     # 新增
                        symptom_tokens[api_name] = tokens
                        
                        # 如果是旧格式，累加到总计
                        if 'token_summary' not in data:
                            token_summary['total_tokens'] += tokens
                            token_summary['total_prompt_tokens'] += usage.get('prompt_tokens', 0)
                            token_summary['total_completion_tokens'] += usage.get('completion_tokens', 0)
                            token_summary['cache_read_tokens_total'] += cache_read        # 新增
                            token_summary['cache_creation_tokens_total'] += cache_create   # 新增
                            
                            if api_name not in token_summary['api_breakdown']:
                                token_summary['api_breakdown'][api_name] = {
                                    'total_tokens': 0,
                                    'prompt_tokens': 0,
                                    'completion_tokens': 0,
                                    'cache_read_tokens': 0,           # 新增
                                    'cache_creation_tokens': 0,       # 新增
                                    'calls': 0
                                }
                            
                            api_breakdown = token_summary['api_breakdown'][api_name]
                            api_breakdown['total_tokens'] += tokens
                            api_breakdown['prompt_tokens'] += usage.get('prompt_tokens', 0)
                            api_breakdown['completion_tokens'] += usage.get('completion_tokens', 0)
                            api_breakdown['cache_read_tokens'] += cache_read              # 新增
                            api_breakdown['cache_creation_tokens'] += cache_create        # 新增
                            api_breakdown['calls'] += 1
                
                if symptom_tokens:
                    symptom_stats[diagnosis] = symptom_tokens
        
        return {
            'total_summary': token_summary,
            'symptom_breakdown': symptom_stats
        }
    
    return {}


def generate_token_analysis(start_id: int, end_id: int, config_path: str = "config/config.yaml") -> bool:
    """生成token使用分析报告"""
    print(f"\n🔍 正在生成Token使用分析报告...")
    
    from src.config_loader import ConfigLoader
    config = ConfigLoader(config_path)
    output_base = config.get_path('output_results')
    
    # 创建tokens目录
    tokens_dir = Path(output_base) / "tokens"
    tokens_dir.mkdir(parents=True, exist_ok=True)
    
    all_reports_analysis = {}
    
    for report_id in range(start_id, end_id + 1):
        print(f"\n📊 分析报告 {report_id}...")
        
        # 查找文件
        baseline_file, rag_file = find_latest_result_files(str(report_id), config_path)
        
        if not baseline_file or not rag_file:
            print(f"⚠️  报告 {report_id} 缺少必要文件 (baseline: {bool(baseline_file)}, rag: {bool(rag_file)})")
            continue
        
        # 加载数据
        baseline_data = load_json_file(baseline_file)
        rag_data = load_json_file(rag_file)
        
        if not baseline_data or not rag_data:
            print(f"⚠️  报告 {report_id} 数据加载失败")
            continue
        
        # 提取token统计
        baseline_stats = extract_token_stats(baseline_data, "baseline")
        rag_stats = extract_token_stats(rag_data, "rag")
        
        # 生成对比分析
        baseline_total = baseline_stats['total_summary'].get('total_tokens', 0)
        rag_total = rag_stats['total_summary'].get('total_tokens', 0)
        
        # 统计API和症状数量
        baseline_apis = set()
        rag_apis = set()
        all_symptoms = set(baseline_stats['symptom_breakdown'].keys()) | set(rag_stats['symptom_breakdown'].keys())
        
        for symptom_tokens in baseline_stats['symptom_breakdown'].values():
            baseline_apis.update(symptom_tokens.keys())
        
        for symptom_tokens in rag_stats['symptom_breakdown'].values():
            rag_apis.update(symptom_tokens.keys())
        
        all_apis = baseline_apis | rag_apis
        
        # 症状级别对比
        symptom_comparison = {}
        for symptom in all_symptoms:
            baseline_symptom_tokens = baseline_stats['symptom_breakdown'].get(symptom, {})
            rag_symptom_tokens = rag_stats['symptom_breakdown'].get(symptom, {})
            
            baseline_symptom_total = sum(baseline_symptom_tokens.values())
            rag_symptom_total = sum(rag_symptom_tokens.values())
            
            symptom_comparison[symptom] = {
                'baseline_tokens': baseline_symptom_total,
                'rag_tokens': rag_symptom_total,
                'difference': rag_symptom_total - baseline_symptom_total,
                'api_breakdown': {}
            }
            
            # API级别对比
            for api in all_apis:
                baseline_api_tokens = baseline_symptom_tokens.get(api, 0)
                rag_api_tokens = rag_symptom_tokens.get(api, 0)
                
                if baseline_api_tokens > 0 or rag_api_tokens > 0:
                    symptom_comparison[symptom]['api_breakdown'][api] = {
                        'baseline': baseline_api_tokens,
                        'rag': rag_api_tokens,
                        'difference': rag_api_tokens - baseline_api_tokens
                    }
        
        # API总体对比
        api_comparison = {}
        baseline_api_breakdown = baseline_stats['total_summary'].get('api_breakdown', {})
        rag_api_breakdown = rag_stats['total_summary'].get('api_breakdown', {})
        
        for api in all_apis:
            baseline_api_total = baseline_api_breakdown.get(api, {}).get('total_tokens', 0)
            rag_api_total = rag_api_breakdown.get(api, {}).get('total_tokens', 0)
            
            api_comparison[api] = {
                'baseline_tokens': baseline_api_total,
                'rag_tokens': rag_api_total,
                'difference': rag_api_total - baseline_api_total,
                'baseline_calls': baseline_api_breakdown.get(api, {}).get('calls', 0),
                'rag_calls': rag_api_breakdown.get(api, {}).get('calls', 0)
            }
        
        # 报告分析结果
        report_analysis = {
            'report_id': report_id,
            'summary': {
                'total_symptoms': len(all_symptoms),
                'total_apis': len(all_apis),
                'baseline_total_tokens': baseline_total,
                'rag_total_tokens': rag_total,
                'token_difference': rag_total - baseline_total,
                'percentage_change': ((rag_total - baseline_total) / baseline_total * 100) if baseline_total > 0 else 0,
                'cache_read_tokens_total': rag_stats['total_summary'].get('cache_read_tokens_total', 0),  # 新增
                'cache_creation_tokens_total': rag_stats['total_summary'].get('cache_creation_tokens_total', 0)  # 新增
            },
            'api_comparison': api_comparison,
            'symptom_comparison': symptom_comparison
        }
        
        all_reports_analysis[f'report_{report_id}'] = report_analysis
        
        # 显示摘要
        print(f"   ✅ 报告 {report_id}: {len(all_symptoms)}症状, {len(all_apis)}API")
        print(f"      Token变化: {baseline_total:,} → {rag_total:,} ({rag_total - baseline_total:+,})")
    
    if not all_reports_analysis:
        print("❌ 没有成功分析任何报告")
        return False
    
    # 保存详细分析结果
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # 保存JSON格式
    json_filename = tokens_dir / f"token_analysis_{start_id}_{end_id}_{timestamp}.json"
    with open(json_filename, 'w', encoding='utf-8') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'report_range': f"{start_id}-{end_id}",
            'reports': all_reports_analysis
        }, f, ensure_ascii=False, indent=2)
    
    # 生成简洁的token使用报告
    txt_filename = tokens_dir / f"token_usage_{start_id}_{end_id}_{timestamp}.txt"
    
    report_lines = []
    report_lines.append("=" * 80)
    report_lines.append(f"📊 Token使用统计报告")
    report_lines.append(f"📋 报告范围: {start_id} - {end_id}")
    report_lines.append(f"⏰ 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report_lines.append("=" * 80)
    
    # 总体统计
    total_baseline_tokens = sum(r['summary']['baseline_total_tokens'] for r in all_reports_analysis.values())
    total_rag_tokens = sum(r['summary']['rag_total_tokens'] for r in all_reports_analysis.values())
    total_symptoms = sum(r['summary']['total_symptoms'] for r in all_reports_analysis.values())
    total_cache_read = sum(r['summary'].get('cache_read_tokens_total', 0) for r in all_reports_analysis.values())
    
    report_lines.append(f"\n📈 总体统计:")
    report_lines.append(f"   处理报告数: {len(all_reports_analysis)}")
    report_lines.append(f"   总症状数: {total_symptoms}")
    report_lines.append(f"   Baseline总tokens: {total_baseline_tokens:,}")
    report_lines.append(f"   RAG增强总tokens: {total_rag_tokens:,}")
    report_lines.append(f"   估计缓存读取tokens: {total_cache_read:,}")
    report_lines.append(f"   估计节省prompt tokens: {total_cache_read:,}")  # 采用cache_read近似节省量
    
    # 各报告详情
    for report_key, analysis in all_reports_analysis.items():
        report_id = analysis['report_id']
        summary = analysis['summary']
        
        report_lines.append(f"\n📋 报告 {report_id}:")
        report_lines.append(f"   症状数量: {summary['total_symptoms']}")
        report_lines.append(f"   API数量: {summary['total_apis']}")
        
        # Baseline API tokens
        report_lines.append(f"\n   🔵 Baseline Token使用:")
        report_lines.append(f"     总计: {summary['baseline_total_tokens']:,} tokens")
        for api, api_data in analysis['api_comparison'].items():
            if api_data['baseline_tokens'] > 0:
                calls = api_data['baseline_calls']
                avg_tokens = api_data['baseline_tokens'] / calls if calls > 0 else 0
                report_lines.append(f"     {api.upper():10}: {api_data['baseline_tokens']:,} tokens ({calls}次调用, 平均{avg_tokens:.0f})")
        
        # RAG API tokens
        report_lines.append(f"\n   🟢 RAG增强 Token使用:")
        report_lines.append(f"     总计: {summary['rag_total_tokens']:,} tokens")
        for api, api_data in analysis['api_comparison'].items():
            if api_data['rag_tokens'] > 0:
                calls = api_data['rag_calls']
                avg_tokens = api_data['rag_tokens'] / calls if calls > 0 else 0
                cache_read_api = analysis['api_comparison'][api].get('cache_read_tokens', 0)
                report_lines.append(f"     {api.upper():10}: {api_data['rag_tokens']:,} tokens ({calls}次调用, 平均{avg_tokens:.0f}), 缓存读取≈{cache_read_api:,}")
        
        # 缓存统计
        cache_read_total = summary.get('cache_read_tokens_total', 0)
        if cache_read_total > 0:
            report_lines.append(f"\n   💾 缓存效果统计:")
            report_lines.append(f"     估计缓存读取: {cache_read_total:,} tokens")
            report_lines.append(f"     估计节省:     {cache_read_total:,} tokens")
        
        # 症状级别tokens
        report_lines.append(f"\n   🔍 各症状Token使用:")
        for symptom, symptom_data in analysis['symptom_comparison'].items():
            if symptom_data['baseline_tokens'] > 0 or symptom_data['rag_tokens'] > 0:
                report_lines.append(f"     症状: {symptom}")
                report_lines.append(f"       Baseline: {symptom_data['baseline_tokens']:,} tokens")
                report_lines.append(f"       RAG增强:  {symptom_data['rag_tokens']:,} tokens")
                
                # 症状内API分解
                api_breakdown = symptom_data['api_breakdown']
                if api_breakdown:
                    report_lines.append(f"       API分解:")
                    for api, api_data in api_breakdown.items():
                        if api_data['baseline'] > 0 or api_data['rag'] > 0:
                            report_lines.append(f"         {api.upper():8}: Baseline {api_data['baseline']:,}, RAG {api_data['rag']:,}")
    
    report_lines.append("\n" + "=" * 80)
    report_lines.append("🏁 统计完成")
    report_lines.append("=" * 80)
    
    with open(txt_filename, 'w', encoding='utf-8') as f:
        f.write('\n'.join(report_lines))
    
    # 显示结果
    print(f"\n✅ Token分析完成!")
    print(f"📁 详细数据: {json_filename}")
    print(f"📄 可读报告: {txt_filename}")
    print(f"\n📊 关键统计:")
    print(f"   处理报告: {len(all_reports_analysis)}个")
    print(f"   总症状数: {total_symptoms}")
    print(f"   Token变化: {total_baseline_tokens:,} → {total_rag_tokens:,} ({total_rag_tokens - total_baseline_tokens:+,})")
    
    return True


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
  
  batch     批处理评估模式 (OpenAI Batch API)
            使用异步批处理，成本更低，适合大规模评估
  
  full_batch 完整RAG评估流程 + 批处理优化 (推荐)
            与full相同的4步流程，但OpenAI使用Batch API降低成本50%
  
  rag3db    使用RAG_3DB系统进行评估 (新功能)
            基于新构建的三个RAG数据库进行检索与评估
  
  rag3db_compare 对比所有RAG_3DB数据库 (新功能)
            同时评估三个RAG数据库并生成对比分析

示例:
  python start_evaluation.py full 4000         # 完整评估报告4000
  python start_evaluation.py full_batch 4000   # 完整评估+批处理优化4000
  python start_evaluation.py full 4000 4002    # 批量评估4000-4002
  python start_evaluation.py baseline 4001     # 仅基础评估4001
  python start_evaluation.py batch 4000        # 批处理模式评估4000
  python start_evaluation.py rag3db 4000 --rag_db_type uniform      # RAG_3DB评估
  python start_evaluation.py rag3db_compare 4000 4002               # 对比所有RAG_3DB
        """
    )
    
    parser.add_argument("workflow", choices=["full", "full_batch", "baseline", "rag-only", "retrieve", "batch", "rag3db", "rag3db_compare"],
                        help="选择工作流程类型")
    parser.add_argument("start_id", type=int, help="开始报告ID")
    parser.add_argument("end_id", type=int, nargs='?', help="结束报告ID (可选)")
    parser.add_argument("--max_files", type=int, help="最大处理文件数量")
    parser.add_argument("--top_k", type=int, default=3, help="RAG检索top_k参数")
    parser.add_argument("--config", type=str, default="config/config.yaml", help="配置文件路径")
    
    # 批处理相关参数
    parser.add_argument("--disable-batch", action="store_true", help="禁用批处理模式")
    parser.add_argument("--batch-threshold", type=int, default=10, help="启用批处理的最小症状数量阈值")
    parser.add_argument("--force-batch", action="store_true", help="强制使用批处理")
    
    # 数据目录参数
    parser.add_argument("--data-dir", type=str, default="test_set",
                       help="数据目录路径 (默认: test_set)")
    
    # RAG_3DB相关参数
    parser.add_argument("--rag_db_type", type=str, default="uniform",
                       choices=['uniform', 'report_context', 'sequential_block'],
                       help="RAG_3DB数据库类型 (默认: uniform)")
    parser.add_argument("--compare_all_dbs", action="store_true",
                       help="对比所有三个RAG_3DB数据库")
    
    args = parser.parse_args()
    
    start_id = args.start_id
    end_id = args.end_id if args.end_id else start_id
    workflow = args.workflow
    
    print("=" * 70)
    print("🎯 RAG评估系统")
    print("=" * 70)
    print(f"📋 工作流程: {workflow}")
    print(f"📊 报告范围: {start_id} - {end_id}")
    print(f"📁 数据目录: {args.data_dir}")
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
        if args.data_dir != "test_set":
            cmd += f" --data-dir {args.data_dir}"
        success = run_workflow_command(cmd, "完整RAG评估流程")
        
    elif workflow == "full_batch":
        # 完整流程 + 批处理优化 - 使用 OpenAI 专用配置
        config_file = "config/config_openai.yaml"
        cmd = f"python workflows/full_batch_pipeline.py {start_id}"
        if end_id != start_id:
            cmd += f" {end_id}"
        if args.top_k != 3:
            cmd += f" --top_k {args.top_k}"
        cmd += f" --config {config_file}"
        if args.batch_threshold != 10:
            cmd += f" --batch-threshold {args.batch_threshold}"
        if args.force_batch:
            cmd += " --force-batch"
        if args.data_dir != "test_set":
            cmd += f" --data-dir {args.data_dir}"
        success = run_workflow_command(cmd, "完整RAG评估流程 (批处理优化)")
        
    elif workflow == "baseline":
        # 仅基础评估
        cmd = f"python workflows/main_workflow.py --start_id {start_id} --end_id {end_id} --config {args.config}"
        if args.max_files:
            cmd += f" --max_files {args.max_files}"
        if args.data_dir != "test_set":
            cmd += f" --data-dir {args.data_dir}"
        success = run_workflow_command(cmd, "基础评估 (不含RAG)")
        
    elif workflow == "rag-only":
        # 仅RAG增强评估
        for report_id in range(start_id, end_id + 1):
            cmd = f"python workflows/rerun_with_rag.py {report_id} --config {args.config}"
            if args.data_dir != "test_set":
                cmd += f" --data-dir {args.data_dir}"
            if not run_workflow_command(cmd, f"RAG增强评估 (报告 {report_id})"):
                success = False
                break
                
    elif workflow == "retrieve":
        # 仅RAG检索
        cmd = f"bash scripts/step1_rag_retrieve.sh {start_id} {end_id} {args.top_k}"
        if args.data_dir != "test_set":
            cmd += f" --data-dir {args.data_dir}"
        success = run_workflow_command(cmd, "RAG检索")
        
    elif workflow == "batch":
        # 批处理评估
        cmd = f"python workflows/batch_workflow.py {start_id}"
        if end_id != start_id:
            cmd += f" {end_id}"
        cmd += f" --config {args.config}"
        if args.max_files:
            cmd += f" --max_files {args.max_files}"
        if args.disable_batch:
            cmd += " --disable-batch"
        if args.batch_threshold != 10:
            cmd += f" --batch-threshold {args.batch_threshold}"
        if args.force_batch:
            cmd += " --force-batch"
        if args.data_dir != "test_set":
            cmd += f" --data-dir {args.data_dir}"
        success = run_workflow_command(cmd, "批处理评估")
        
    elif workflow == "rag3db":
        # RAG_3DB系统评估
        config_file = "config/config_rag3db.yaml"
        cmd = f"python workflows/rag3db_full_pipeline.py {start_id}"
        if end_id != start_id:
            cmd += f" {end_id}"
        cmd += f" --rag_db_type {args.rag_db_type}"
        if args.top_k != 3:
            cmd += f" --top_k {args.top_k}"
        cmd += f" --config {config_file}"
        if args.data_dir != "test_set":
            cmd += f" --data_dir {args.data_dir}"
        success = run_workflow_command(cmd, f"RAG_3DB评估 ({args.rag_db_type})")
        
    elif workflow == "rag3db_compare":
        # RAG_3DB对比评估
        config_file = "config/config_rag3db.yaml"
        cmd = f"python workflows/rag3db_full_pipeline.py {start_id}"
        if end_id != start_id:
            cmd += f" {end_id}"
        cmd += " --compare_all_dbs"
        if args.top_k != 3:
            cmd += f" --top_k {args.top_k}"
        cmd += f" --config {config_file}"
        if args.data_dir != "test_set":
            cmd += f" --data_dir {args.data_dir}"
        success = run_workflow_command(cmd, "RAG_3DB对比评估")
    
    # 最终结果
    print("\n" + "=" * 70)
    if success:
        print("🎉 工作流程执行成功!")
        print("\n📁 结果文件位置:")
        if workflow == "batch":
            print("   • 批处理结果: results/batch_results/")
        elif workflow == "full_batch":
            print("   • RAG缓存: Evaluate_output/rag_search_output/")
            print("   • 基础结果: Evaluate_output/baseline_results_batch/")
            print("   • RAG增强结果: Evaluate_output/rerun_with_rag_batch/")
            print("   • 对比分析: Evaluate_output/rerun_comparisons/")
            print("   • 批处理文件: batch_processing/")
        else:
            print("   • RAG缓存: Evaluate_output/rag_search_output/")
            print("   • 基础结果: Evaluate_output/baseline_results/")
            print("   • RAG增强结果: Evaluate_output/rerun_with_rag/")
            print("   • 对比分析: Evaluate_output/rerun_comparisons/")
        
        # 如果是完整流程，自动生成token分析
        if workflow in ["full", "full_batch"]:
            # 根据工作流选择对应的配置文件
            token_config = "config/config_openai.yaml" if workflow == "full_batch" else args.config
            if generate_token_analysis(start_id, end_id, token_config):
                print("   • Token分析: Evaluate_output/tokens/")
            else:
                print("   ⚠️  Token分析失败")
        
        # 显示批处理优化信息
        if workflow == "full_batch":
            print(f"\n💰 成本优化:")
            print("   • OpenAI API: 使用Batch API，成本降低50%")
            print("   • 其他API: 保持传统调用模式")
        
        # 显示RAG_3DB系统信息
        elif workflow in ["rag3db", "rag3db_compare"]:
            print(f"\n🗃️  RAG_3DB系统信息:")
            if workflow == "rag3db":
                db_info = {
                    'uniform': 'Uniform Random Unit Database - 纯随机采样，最大数据多样性',
                    'report_context': 'Report Context Database - 报告级采样，保持完整报告上下文',
                    'sequential_block': 'Sequential Block Database - 顺序采样，保持时间顺序'
                }
                print(f"   • 使用数据库: {db_info.get(args.rag_db_type, args.rag_db_type)}")
                print(f"   • 数据规模: 43,000个症状-诊断单元")
                print(f"   • 向量维度: 768维 (SapBERT)")
            else:
                print("   • 对比评估: 三个RAG数据库全面对比")
                print("   • Uniform Random Unit: 纯随机采样")
                print("   • Report Context: 报告级采样")
                print("   • Sequential Block: 顺序采样")
                print("   • 总数据规模: 129,000个症状-诊断单元")
            print("   • 检索模型: SapBERT (医疗领域预训练)")
            print("   • 索引技术: Faiss (余弦相似度)")
            print("   • 存储系统: MongoDB")
    else:
        print("❌ 工作流程执行失败!")
        print("请检查错误信息并重试。")
    
    print("=" * 70)


if __name__ == "__main__":
    main()
