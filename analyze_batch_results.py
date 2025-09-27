#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量RAG评估结果分析脚本
分析 results/rerun_comparisons 目录中的所有评估结果
"""

import json
import os
import glob
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime
import statistics

def load_comparison_results(results_dir: str) -> Dict[str, Any]:
    """加载所有对比结果文件"""
    comparison_files = glob.glob(os.path.join(results_dir, "report_*_comparison_*.json"))
    
    all_results = {}
    for file_path in sorted(comparison_files):
        filename = os.path.basename(file_path)
        # 提取报告ID
        report_id = filename.split('_')[1]
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                all_results[report_id] = data
        except Exception as e:
            print(f"⚠️  加载文件 {filename} 失败: {e}")
    
    return all_results

def analyze_api_performance(all_results: Dict[str, Any]) -> Dict[str, Dict]:
    """分析各API的整体表现"""
    api_stats = {}
    
    for report_id, data in all_results.items():
        # 遍历每个症状（JSON的顶级键）
        for symptom_name, symptom_data in data.items():
            if isinstance(symptom_data, dict):
                # 遍历每个API的结果
                for api_name, api_result in symptom_data.items():
                    if isinstance(api_result, dict) and 'metrics_improvement' in api_result:
                        if api_name not in api_stats:
                            api_stats[api_name] = {
                                'total_symptoms': 0,
                                'improved': 0,
                                'degraded': 0,
                                'unchanged': 0,
                                'precision_changes': [],
                                'recall_changes': [],
                                'f1_changes': [],
                                'overall_score_changes': []
                            }
                        
                        stats = api_stats[api_name]
                        stats['total_symptoms'] += 1
                        
                        # 获取改善数据
                        improvement = api_result.get('metrics_improvement', {})
                        
                        # 分类改善情况
                        overall_change = improvement.get('overall_improvement', 0)
                        if overall_change > 2:  # 显著改善阈值
                            stats['improved'] += 1
                        elif overall_change < -2:  # 显著恶化阈值
                            stats['degraded'] += 1
                        else:
                            stats['unchanged'] += 1
                        
                        # 收集数值变化
                        stats['precision_changes'].append(improvement.get('precision_improvement', 0))
                        stats['recall_changes'].append(improvement.get('recall_improvement', 0))
                        stats['f1_changes'].append(improvement.get('f1_improvement', 0))
                        stats['overall_score_changes'].append(improvement.get('overall_improvement', 0))
    
    return api_stats

def analyze_symptom_patterns(all_results: Dict[str, Any]) -> Dict[str, Any]:
    """分析症状类型的RAG效果模式"""
    symptom_analysis = {}
    
    for report_id, data in all_results.items():
        # 遍历每个症状（JSON的顶级键）
        for symptom_name, symptom_data in data.items():
            if isinstance(symptom_data, dict):
                if symptom_name not in symptom_analysis:
                    symptom_analysis[symptom_name] = {
                        'occurrences': 0,
                        'api_results': {},
                        'avg_improvements': {}
                    }
                
                symptom_analysis[symptom_name]['occurrences'] += 1
                
                # 遍历每个API的结果
                for api_name, api_result in symptom_data.items():
                    if isinstance(api_result, dict) and 'metrics_improvement' in api_result:
                        if api_name not in symptom_analysis[symptom_name]['api_results']:
                            symptom_analysis[symptom_name]['api_results'][api_name] = []
                        
                        improvement = api_result.get('metrics_improvement', {})
                        symptom_analysis[symptom_name]['api_results'][api_name].append({
                            'overall_score_change': improvement.get('overall_improvement', 0),
                            'f1_change': improvement.get('f1_improvement', 0),
                            'precision_change': improvement.get('precision_improvement', 0),
                            'recall_change': improvement.get('recall_improvement', 0)
                        })
    
    # 计算平均改善
    for symptom, data in symptom_analysis.items():
        data['avg_improvements'] = {}
        for api_name, results in data['api_results'].items():
            if results:
                data['avg_improvements'][api_name] = {
                    'avg_overall_score': statistics.mean([r['overall_score_change'] for r in results]),
                    'avg_f1': statistics.mean([r['f1_change'] for r in results]),
                    'avg_precision': statistics.mean([r['precision_change'] for r in results]),
                    'avg_recall': statistics.mean([r['recall_change'] for r in results])
                }
    
    return symptom_analysis

def generate_summary_report(all_results: Dict[str, Any], api_stats: Dict[str, Dict], 
                          symptom_analysis: Dict[str, Any]) -> str:
    """生成综合分析报告"""
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    total_reports = len(all_results)
    total_symptoms = sum(len([k for k, v in data.items() if isinstance(v, dict) and any(isinstance(vv, dict) and 'metrics_improvement' in vv for vv in v.values())]) for data in all_results.values())
    
    report = f"""
================================================================================
RAG Uniform数据库批量评估综合分析报告
================================================================================
生成时间: {timestamp}
评估报告数: {total_reports}
总症状数: {total_symptoms}
评估范围: 报告 {min(all_results.keys())} - {max(all_results.keys())}

█ API整体表现分析
------------------------------------------------------------
"""
    
    for api_name, stats in api_stats.items():
        total = stats['total_symptoms']
        improved_pct = (stats['improved'] / total) * 100
        degraded_pct = (stats['degraded'] / total) * 100
        unchanged_pct = (stats['unchanged'] / total) * 100
        
        avg_precision = statistics.mean(stats['precision_changes'])
        avg_recall = statistics.mean(stats['recall_changes'])
        avg_f1 = statistics.mean(stats['f1_changes'])
        avg_overall = statistics.mean(stats['overall_score_changes'])
        
        report += f"""
【{api_name.upper()}】
  总症状数: {total}
  ✅ 显著改善: {stats['improved']} ({improved_pct:.1f}%)
  ❌ 显著恶化: {stats['degraded']} ({degraded_pct:.1f}%)
  ⚪ 无明显变化: {stats['unchanged']} ({unchanged_pct:.1f}%)
  
  平均指标变化:
    精确率: {avg_precision:+.1f}%
    召回率: {avg_recall:+.1f}%
    F1分数: {avg_f1:+.1f}%
    综合得分: {avg_overall:+.1f}分
"""
    
    report += f"""
█ 症状类型效果分析 (Top 10 最常见症状)
------------------------------------------------------------
"""
    
    # 按出现频率排序症状
    sorted_symptoms = sorted(symptom_analysis.items(), 
                           key=lambda x: x[1]['occurrences'], reverse=True)[:10]
    
    for symptom, data in sorted_symptoms:
        report += f"\n【{symptom}】 (出现 {data['occurrences']} 次)\n"
        
        for api_name, avg_improvements in data['avg_improvements'].items():
            avg_score = avg_improvements['avg_overall_score']
            avg_f1 = avg_improvements['avg_f1']
            
            if avg_score > 2:
                effect = "✅ 有效"
            elif avg_score < -2:
                effect = "❌ 负面"
            else:
                effect = "⚪ 中性"
            
            report += f"  {api_name}: {effect} (得分{avg_score:+.1f}, F1{avg_f1:+.1f}%)\n"
    
    report += f"""
█ 总体结论
------------------------------------------------------------
"""
    
    # 计算总体RAG效果
    all_api_improvements = []
    for api_name, stats in api_stats.items():
        if stats['overall_score_changes']:  # 确保有数据
            avg_improvement = statistics.mean(stats['overall_score_changes'])
            all_api_improvements.append(avg_improvement)
            
            if avg_improvement > 2:
                effect = "✅ RAG增强整体有效"
            elif avg_improvement < -2:
                effect = "❌ RAG增强存在问题"
            else:
                effect = "⚪ RAG增强效果中性"
            
            report += f"• {api_name}: {effect} (平均改善 {avg_improvement:+.1f}分)\n"
        else:
            report += f"• {api_name}: ⚠️ 无有效数据\n"
    
    overall_avg = statistics.mean(all_api_improvements) if all_api_improvements else 0
    if overall_avg > 1:
        conclusion = "✅ RAG系统整体表现良好，建议继续使用"
    elif overall_avg < -1:
        conclusion = "❌ RAG系统需要优化，建议检查检索质量和增强策略"
    else:
        conclusion = "⚪ RAG系统效果中等，可考虑进一步调优"
    
    report += f"""
【最终结论】: {conclusion}
平均综合得分改善: {overall_avg:+.1f}分

================================================================================
"""
    
    return report

def main():
    """主函数"""
    results_dir = "results/rerun_comparisons"
    
    print("🔍 正在加载批量评估结果...")
    all_results = load_comparison_results(results_dir)
    
    if not all_results:
        print("❌ 未找到任何评估结果文件")
        return
    
    print(f"✅ 成功加载 {len(all_results)} 个报告的评估结果")
    
    print("📊 正在分析API表现...")
    api_stats = analyze_api_performance(all_results)
    
    print("🔬 正在分析症状模式...")
    symptom_analysis = analyze_symptom_patterns(all_results)
    
    print("📝 正在生成综合报告...")
    summary_report = generate_summary_report(all_results, api_stats, symptom_analysis)
    
    # 保存报告
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = f"results/RAG_Uniform_Batch_Analysis_{timestamp}.txt"
    
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(summary_report)
    
    print(f"✅ 综合分析报告已保存: {report_file}")
    print("\n" + "="*80)
    print(summary_report)

if __name__ == "__main__":
    main()
