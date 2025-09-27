#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RAG搜索质量分析工具
分析当前RAG检索的问题并提供优化建议
"""

import json
import glob
import numpy as np
from pathlib import Path
from typing import Dict, List, Any, Tuple
from collections import defaultdict, Counter
import statistics

def load_rag_results(rag_dir: str) -> Dict[str, Any]:
    """加载RAG检索结果"""
    results = {}
    
    files = glob.glob(f"{rag_dir}/*.jsonl")
    for file_path in files:
        report_id = Path(file_path).name.split('_')[1]
        
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            
        results[report_id] = []
        for line in lines:
            if line.strip():
                results[report_id].append(json.loads(line))
    
    return results

def analyze_similarity_distribution(rag_results: Dict[str, Any]) -> Dict[str, Any]:
    """分析相似度分布"""
    all_similarities = []
    perfect_matches = 0
    low_similarities = 0
    
    similarity_by_symptom = defaultdict(list)
    
    for report_id, symptoms in rag_results.items():
        for symptom_data in symptoms:
            symptom = symptom_data.get('symptom', 'unknown')
            
            for result in symptom_data.get('rag_results', []):
                sim = result.get('cosine_similarity', 0)
                all_similarities.append(sim)
                similarity_by_symptom[symptom].append(sim)
                
                if sim >= 0.99:
                    perfect_matches += 1
                elif sim < 0.5:
                    low_similarities += 1
    
    return {
        'total_retrievals': len(all_similarities),
        'perfect_matches': perfect_matches,
        'low_similarities': low_similarities,
        'mean_similarity': statistics.mean(all_similarities) if all_similarities else 0,
        'median_similarity': statistics.median(all_similarities) if all_similarities else 0,
        'similarity_std': statistics.stdev(all_similarities) if len(all_similarities) > 1 else 0,
        'similarity_distribution': {
            '0.9-1.0': sum(1 for s in all_similarities if 0.9 <= s <= 1.0),
            '0.7-0.9': sum(1 for s in all_similarities if 0.7 <= s < 0.9),
            '0.5-0.7': sum(1 for s in all_similarities if 0.5 <= s < 0.7),
            '0.3-0.5': sum(1 for s in all_similarities if 0.3 <= s < 0.5),
            '0.0-0.3': sum(1 for s in all_similarities if 0.0 <= s < 0.3),
        },
        'symptom_similarities': dict(similarity_by_symptom)
    }

def analyze_retrieval_relevance(rag_results: Dict[str, Any]) -> Dict[str, Any]:
    """分析检索相关性"""
    query_result_matches = []
    semantic_mismatches = []
    
    for report_id, symptoms in rag_results.items():
        for symptom_data in symptoms:
            query = symptom_data.get('symptom', '')
            
            for i, result in enumerate(symptom_data.get('rag_results', [])):
                retrieved_symptom = result.get('symptom', '')
                similarity = result.get('cosine_similarity', 0)
                
                # 检查语义匹配
                if query.lower() == retrieved_symptom.lower():
                    query_result_matches.append({
                        'query': query,
                        'result': retrieved_symptom,
                        'similarity': similarity,
                        'rank': i + 1
                    })
                elif similarity > 0.8:  # 高相似度但不同症状
                    semantic_mismatches.append({
                        'query': query,
                        'result': retrieved_symptom,
                        'similarity': similarity,
                        'rank': i + 1
                    })
    
    return {
        'exact_matches': len(query_result_matches),
        'semantic_mismatches': len(semantic_mismatches),
        'match_examples': query_result_matches[:10],
        'mismatch_examples': semantic_mismatches[:10]
    }

def analyze_top_k_effectiveness(rag_results: Dict[str, Any]) -> Dict[str, Any]:
    """分析Top-K检索效果"""
    rank_similarities = defaultdict(list)
    
    for report_id, symptoms in rag_results.items():
        for symptom_data in symptoms:
            for i, result in enumerate(symptom_data.get('rag_results', [])):
                rank = i + 1
                similarity = result.get('cosine_similarity', 0)
                rank_similarities[rank].append(similarity)
    
    rank_stats = {}
    for rank, sims in rank_similarities.items():
        if sims:
            rank_stats[f'rank_{rank}'] = {
                'count': len(sims),
                'mean_similarity': statistics.mean(sims),
                'high_quality_ratio': sum(1 for s in sims if s > 0.7) / len(sims)
            }
    
    return rank_stats

def identify_problematic_symptoms(rag_results: Dict[str, Any]) -> List[Dict[str, Any]]:
    """识别检索效果差的症状类型"""
    symptom_performance = defaultdict(list)
    
    for report_id, symptoms in rag_results.items():
        for symptom_data in symptoms:
            symptom = symptom_data.get('symptom', '')
            
            # 计算该症状的平均检索质量
            similarities = []
            for result in symptom_data.get('rag_results', []):
                similarities.append(result.get('cosine_similarity', 0))
            
            if similarities:
                avg_sim = statistics.mean(similarities)
                max_sim = max(similarities)
                symptom_performance[symptom].append({
                    'avg_similarity': avg_sim,
                    'max_similarity': max_sim,
                    'report_id': report_id
                })
    
    # 找出表现最差的症状
    problematic = []
    for symptom, performances in symptom_performance.items():
        overall_avg = statistics.mean([p['avg_similarity'] for p in performances])
        overall_max = statistics.mean([p['max_similarity'] for p in performances])
        
        if overall_avg < 0.6 or overall_max < 0.8:  # 阈值可调
            problematic.append({
                'symptom': symptom,
                'occurrences': len(performances),
                'avg_similarity': overall_avg,
                'max_similarity': overall_max,
                'examples': performances[:3]
            })
    
    return sorted(problematic, key=lambda x: x['avg_similarity'])

def generate_optimization_recommendations(analysis_results: Dict[str, Any]) -> List[str]:
    """生成优化建议"""
    recommendations = []
    
    sim_stats = analysis_results['similarity_stats']
    relevance = analysis_results['relevance_analysis']
    topk = analysis_results['topk_analysis']
    problematic = analysis_results['problematic_symptoms']
    
    # 基于相似度分布的建议
    if sim_stats['perfect_matches'] / sim_stats['total_retrievals'] > 0.3:
        recommendations.append("🔍 检测到大量完美匹配(相似度=1.0)，建议增加查询扩展和语义多样性")
    
    if sim_stats['low_similarities'] / sim_stats['total_retrievals'] > 0.2:
        recommendations.append("⚠️ 低相似度检索过多，建议降低相似度阈值或增加Top-K值")
    
    if sim_stats['mean_similarity'] < 0.6:
        recommendations.append("📊 平均相似度偏低，建议优化查询预处理和向量编码策略")
    
    # 基于Top-K效果的建议
    if 'rank_1' in topk and 'rank_3' in topk:
        rank1_quality = topk['rank_1']['high_quality_ratio']
        rank3_quality = topk['rank_3']['high_quality_ratio']
        
        if rank1_quality < 0.5:
            recommendations.append("🎯 Top-1检索质量差，建议实现查询重写和多角度检索")
        
        if rank3_quality - rank1_quality > 0.2:
            recommendations.append("📈 后续排名质量较好，建议增加Top-K值到5-10")
    
    # 基于问题症状的建议
    if len(problematic) > 5:
        recommendations.append("🔧 多个症状检索效果差，建议实现症状特异性检索策略")
    
    # 基于语义匹配的建议
    if relevance['semantic_mismatches'] > relevance['exact_matches']:
        recommendations.append("🧠 语义匹配不准确，建议优化embedding模型或实现混合检索")
    
    return recommendations

def main():
    """主函数"""
    print("🔍 开始分析RAG搜索质量...")
    
    # 加载RAG检索结果
    rag_results = load_rag_results("results/rag_output_uniform")
    
    if not rag_results:
        print("❌ 未找到RAG检索结果文件")
        return
    
    print(f"✅ 加载了 {len(rag_results)} 个报告的检索结果")
    
    # 执行各项分析
    print("\n📊 分析相似度分布...")
    similarity_stats = analyze_similarity_distribution(rag_results)
    
    print("🎯 分析检索相关性...")
    relevance_analysis = analyze_retrieval_relevance(rag_results)
    
    print("📈 分析Top-K效果...")
    topk_analysis = analyze_top_k_effectiveness(rag_results)
    
    print("⚠️ 识别问题症状...")
    problematic_symptoms = identify_problematic_symptoms(rag_results)
    
    # 汇总分析结果
    analysis_results = {
        'similarity_stats': similarity_stats,
        'relevance_analysis': relevance_analysis,
        'topk_analysis': topk_analysis,
        'problematic_symptoms': problematic_symptoms
    }
    
    # 生成优化建议
    recommendations = generate_optimization_recommendations(analysis_results)
    
    # 输出报告
    print("\n" + "="*80)
    print("📋 RAG搜索质量分析报告")
    print("="*80)
    
    print(f"\n📊 相似度统计:")
    print(f"  总检索次数: {similarity_stats['total_retrievals']}")
    print(f"  完美匹配: {similarity_stats['perfect_matches']} ({similarity_stats['perfect_matches']/similarity_stats['total_retrievals']*100:.1f}%)")
    print(f"  低相似度: {similarity_stats['low_similarities']} ({similarity_stats['low_similarities']/similarity_stats['total_retrievals']*100:.1f}%)")
    print(f"  平均相似度: {similarity_stats['mean_similarity']:.3f}")
    print(f"  相似度标准差: {similarity_stats['similarity_std']:.3f}")
    
    print(f"\n📈 相似度分布:")
    for range_name, count in similarity_stats['similarity_distribution'].items():
        percentage = count / similarity_stats['total_retrievals'] * 100
        print(f"  {range_name}: {count} ({percentage:.1f}%)")
    
    print(f"\n🎯 检索相关性:")
    print(f"  精确匹配: {relevance_analysis['exact_matches']}")
    print(f"  语义不匹配: {relevance_analysis['semantic_mismatches']}")
    
    print(f"\n📊 Top-K效果:")
    for rank_key, stats in topk_analysis.items():
        print(f"  {rank_key}: 平均相似度 {stats['mean_similarity']:.3f}, 高质量比例 {stats['high_quality_ratio']:.1%}")
    
    print(f"\n⚠️ 问题症状 (前10个):")
    for i, symptom in enumerate(problematic_symptoms[:10]):
        print(f"  {i+1}. {symptom['symptom'][:50]}... (平均相似度: {symptom['avg_similarity']:.3f})")
    
    print(f"\n🚀 优化建议:")
    for i, rec in enumerate(recommendations, 1):
        print(f"  {i}. {rec}")
    
    # 保存详细报告
    with open("results/rag_search_quality_analysis.json", 'w', encoding='utf-8') as f:
        json.dump(analysis_results, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ 详细分析结果已保存到: results/rag_search_quality_analysis.json")

if __name__ == "__main__":
    main()
