#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RAG搜索增强效果对比工具
对比原始搜索和增强搜索的效果差异
"""

import json
import glob
import numpy as np
from pathlib import Path
from typing import Dict, List, Any, Tuple
from collections import defaultdict
import statistics

def load_search_results(file_pattern: str) -> Dict[str, Any]:
    """加载搜索结果文件"""
    files = glob.glob(file_pattern)
    if not files:
        return {}
    
    # 取最新的文件
    latest_file = max(files, key=lambda x: Path(x).stat().st_mtime)
    
    results = {}
    with open(latest_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    for line in lines:
        if line.strip():
            data = json.loads(line)
            symptom = data.get('symptom', 'unknown')
            results[symptom] = data
    
    return results

def compare_similarity_scores(original_results: Dict[str, Any], 
                            enhanced_results: Dict[str, Any]) -> Dict[str, Any]:
    """对比相似度分数"""
    comparison = {
        'symptom_comparisons': {},
        'overall_stats': {
            'original': {'similarities': [], 'avg_top1': 0, 'avg_top3': 0},
            'enhanced': {'similarities': [], 'avg_top1': 0, 'avg_top3': 0}
        }
    }
    
    for symptom in original_results.keys():
        if symptom in enhanced_results:
            orig_data = original_results[symptom]
            enh_data = enhanced_results[symptom]
            
            orig_results = orig_data.get('rag_results', [])
            enh_results = enh_data.get('rag_results', [])
            
            # 提取相似度
            orig_sims = [r.get('cosine_similarity', 0) for r in orig_results]
            enh_sims = [r.get('cosine_similarity', 0) for r in enh_results]
            
            comparison['symptom_comparisons'][symptom] = {
                'original_similarities': orig_sims,
                'enhanced_similarities': enh_sims,
                'original_top1': orig_sims[0] if orig_sims else 0,
                'enhanced_top1': enh_sims[0] if enh_sims else 0,
                'original_avg': statistics.mean(orig_sims) if orig_sims else 0,
                'enhanced_avg': statistics.mean(enh_sims) if enh_sims else 0,
                'improvement': (statistics.mean(enh_sims) - statistics.mean(orig_sims)) if orig_sims and enh_sims else 0
            }
            
            # 添加到总体统计
            comparison['overall_stats']['original']['similarities'].extend(orig_sims)
            comparison['overall_stats']['enhanced']['similarities'].extend(enh_sims)
    
    # 计算总体平均值
    orig_all_sims = comparison['overall_stats']['original']['similarities']
    enh_all_sims = comparison['overall_stats']['enhanced']['similarities']
    
    if orig_all_sims:
        comparison['overall_stats']['original']['avg_all'] = statistics.mean(orig_all_sims)
        comparison['overall_stats']['original']['std_all'] = statistics.stdev(orig_all_sims) if len(orig_all_sims) > 1 else 0
    
    if enh_all_sims:
        comparison['overall_stats']['enhanced']['avg_all'] = statistics.mean(enh_all_sims)
        comparison['overall_stats']['enhanced']['std_all'] = statistics.stdev(enh_all_sims) if len(enh_all_sims) > 1 else 0
    
    return comparison

def analyze_retrieval_quality(original_results: Dict[str, Any], 
                            enhanced_results: Dict[str, Any]) -> Dict[str, Any]:
    """分析检索质量改进"""
    quality_analysis = {
        'relevance_improvements': [],
        'diversity_improvements': [],
        'semantic_improvements': []
    }
    
    for symptom in original_results.keys():
        if symptom in enhanced_results:
            orig_results = original_results[symptom].get('rag_results', [])
            enh_results = enhanced_results[symptom].get('rag_results', [])
            
            # 分析相关性改进
            orig_symptoms = [r.get('symptom', '') for r in orig_results]
            enh_symptoms = [r.get('symptom', '') for r in enh_results]
            
            # 计算与查询的词汇重叠
            query_words = set(symptom.lower().split())
            
            orig_relevance = []
            for s in orig_symptoms:
                s_words = set(s.lower().split())
                overlap = len(query_words.intersection(s_words)) / len(query_words.union(s_words)) if query_words.union(s_words) else 0
                orig_relevance.append(overlap)
            
            enh_relevance = []
            for s in enh_symptoms:
                s_words = set(s.lower().split())
                overlap = len(query_words.intersection(s_words)) / len(query_words.union(s_words)) if query_words.union(s_words) else 0
                enh_relevance.append(overlap)
            
            if orig_relevance and enh_relevance:
                relevance_improvement = statistics.mean(enh_relevance) - statistics.mean(orig_relevance)
                quality_analysis['relevance_improvements'].append({
                    'symptom': symptom,
                    'original_relevance': statistics.mean(orig_relevance),
                    'enhanced_relevance': statistics.mean(enh_relevance),
                    'improvement': relevance_improvement
                })
            
            # 分析多样性改进
            orig_unique = len(set(orig_symptoms))
            enh_unique = len(set(enh_symptoms))
            
            diversity_improvement = (enh_unique - orig_unique) / max(len(orig_symptoms), 1)
            quality_analysis['diversity_improvements'].append({
                'symptom': symptom,
                'original_diversity': orig_unique / len(orig_symptoms) if orig_symptoms else 0,
                'enhanced_diversity': enh_unique / len(enh_symptoms) if enh_symptoms else 0,
                'improvement': diversity_improvement
            })
    
    return quality_analysis

def generate_comparison_report(comparison: Dict[str, Any], 
                             quality_analysis: Dict[str, Any]) -> str:
    """生成对比报告"""
    
    report = f"""
================================================================================
RAG搜索增强效果对比报告
================================================================================
生成时间: {Path().cwd()}

█ 总体相似度对比
------------------------------------------------------------
"""
    
    orig_stats = comparison['overall_stats']['original']
    enh_stats = comparison['overall_stats']['enhanced']
    
    if 'avg_all' in orig_stats and 'avg_all' in enh_stats:
        improvement = enh_stats['avg_all'] - orig_stats['avg_all']
        improvement_pct = (improvement / orig_stats['avg_all']) * 100 if orig_stats['avg_all'] > 0 else 0
        
        report += f"""
原始搜索平均相似度: {orig_stats['avg_all']:.4f} (±{orig_stats.get('std_all', 0):.4f})
增强搜索平均相似度: {enh_stats['avg_all']:.4f} (±{enh_stats.get('std_all', 0):.4f})
整体改进: {improvement:+.4f} ({improvement_pct:+.1f}%)
"""
    
    report += f"""
█ 各症状详细对比
------------------------------------------------------------
"""
    
    # 按改进程度排序
    symptom_improvements = []
    for symptom, data in comparison['symptom_comparisons'].items():
        symptom_improvements.append((symptom, data['improvement']))
    
    symptom_improvements.sort(key=lambda x: x[1], reverse=True)
    
    for symptom, improvement in symptom_improvements[:10]:  # 显示前10个
        data = comparison['symptom_comparisons'][symptom]
        
        status = "✅ 改进" if improvement > 0.01 else "❌ 下降" if improvement < -0.01 else "⚪ 无变化"
        
        report += f"""
【{symptom[:50]}...】 {status}
  原始: Top-1={data['original_top1']:.3f}, 平均={data['original_avg']:.3f}
  增强: Top-1={data['enhanced_top1']:.3f}, 平均={data['enhanced_avg']:.3f}
  改进: {improvement:+.3f}
"""
    
    report += f"""
█ 检索质量分析
------------------------------------------------------------
"""
    
    # 相关性改进统计
    relevance_improvements = quality_analysis['relevance_improvements']
    if relevance_improvements:
        avg_relevance_improvement = statistics.mean([r['improvement'] for r in relevance_improvements])
        positive_improvements = sum(1 for r in relevance_improvements if r['improvement'] > 0)
        
        report += f"""
相关性改进:
  平均改进: {avg_relevance_improvement:+.3f}
  改进症状数: {positive_improvements}/{len(relevance_improvements)} ({positive_improvements/len(relevance_improvements)*100:.1f}%)
"""
    
    # 多样性改进统计
    diversity_improvements = quality_analysis['diversity_improvements']
    if diversity_improvements:
        avg_diversity_improvement = statistics.mean([d['improvement'] for d in diversity_improvements])
        positive_diversity = sum(1 for d in diversity_improvements if d['improvement'] > 0)
        
        report += f"""
多样性改进:
  平均改进: {avg_diversity_improvement:+.3f}
  改进症状数: {positive_diversity}/{len(diversity_improvements)} ({positive_diversity/len(diversity_improvements)*100:.1f}%)
"""
    
    report += f"""
█ 结论与建议
------------------------------------------------------------
"""
    
    if 'avg_all' in orig_stats and 'avg_all' in enh_stats:
        overall_improvement = enh_stats['avg_all'] - orig_stats['avg_all']
        
        if overall_improvement > 0.05:
            conclusion = "✅ 增强搜索显著改善了检索质量"
        elif overall_improvement > 0.01:
            conclusion = "🔄 增强搜索有轻微改善"
        elif overall_improvement > -0.01:
            conclusion = "⚪ 增强搜索效果中性"
        else:
            conclusion = "❌ 增强搜索可能需要进一步调优"
        
        report += f"""
{conclusion}

建议:
"""
        if overall_improvement > 0.01:
            report += "• 继续使用增强搜索策略\n• 考虑进一步优化查询扩展词典\n"
        else:
            report += "• 调整相似度阈值\n• 优化查询扩展策略\n• 考虑增加Top-K值\n"
    
    report += """
================================================================================
"""
    
    return report

def main():
    """主函数"""
    print("🔍 开始对比RAG搜索增强效果...")
    
    # 加载原始和增强搜索结果
    original_pattern = "results/rag_output_uniform/report_*_FIXED_ragoutcome_uniform_*.jsonl"
    enhanced_pattern = "results/rag_output_uniform/diagnostic_*_ENHANCED_ragoutcome_uniform_*.jsonl"
    
    original_results = load_search_results(original_pattern)
    enhanced_results = load_search_results(enhanced_pattern)
    
    if not original_results:
        print("❌ 未找到原始搜索结果")
        return
    
    if not enhanced_results:
        print("❌ 未找到增强搜索结果")
        return
    
    print(f"✅ 加载原始结果: {len(original_results)} 个症状")
    print(f"✅ 加载增强结果: {len(enhanced_results)} 个症状")
    
    # 执行对比分析
    print("📊 对比相似度分数...")
    comparison = compare_similarity_scores(original_results, enhanced_results)
    
    print("🔬 分析检索质量...")
    quality_analysis = analyze_retrieval_quality(original_results, enhanced_results)
    
    # 生成报告
    print("📝 生成对比报告...")
    report = generate_comparison_report(comparison, quality_analysis)
    
    # 保存报告
    report_file = "results/rag_search_enhancement_comparison.txt"
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"✅ 对比报告已保存: {report_file}")
    print(report)

if __name__ == "__main__":
    main()
