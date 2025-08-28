#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Moonshot API评分分析测试脚本

专门用于测试Moonshot API的RAG前后评分分析
"""

from api_score_analyzer import APIScoreAnalyzer

def test_moonshot_only():
    """只分析Moonshot API"""
    print("🎯 开始Moonshot API专项分析...")
    
    analyzer = APIScoreAnalyzer()
    
    # 只保留moonshot
    analyzer.apis = ["moonshot"]
    
    # 运行分析
    stats = analyzer.run_analysis()
    
    # 输出Moonshot的详细结果
    if "moonshot" in stats:
        moonshot_stat = stats["moonshot"]
        print("\n" + "="*60)
        print("🔍 MOONSHOT API 详细分析结果")
        print("="*60)
        print(f"症状总数: {moonshot_stat['s_numbers']}")
        print(f"无RAG平均分: {moonshot_stat['scores_without_rag']['overall_score']}")
        print(f"有RAG平均分: {moonshot_stat['scores_with_rag']['overall_score']}")
        print(f"RAG提升比例: {moonshot_stat['improvement_ratio']}% ({moonshot_stat['improvement_count']}个)")
        print(f"RAG下降比例: {moonshot_stat['decline_ratio']}% ({moonshot_stat['decline_count']}个)")
        print(f"无变化比例: {moonshot_stat['no_change_ratio']}% ({moonshot_stat['no_change_count']}个)")
        
        # 计算平均提升/下降分数
        if moonshot_stat['improvement_count'] > 0:
            # 计算提升的分数差值
            improvements = []
            for i, (rag_score, baseline_score) in enumerate(zip(moonshot_stat['scores_with_rag']['total_scores'], 
                                                               moonshot_stat['scores_without_rag']['total_scores'])):
                if rag_score > baseline_score:
                    improvements.append(rag_score - baseline_score)
            
            if improvements:
                avg_improvement = sum(improvements) / len(improvements)
                print(f"平均提升分数: {avg_improvement:.2f}")
        
        if moonshot_stat['decline_count'] > 0:
            # 计算下降的分数差值
            declines = []
            for i, (rag_score, baseline_score) in enumerate(zip(moonshot_stat['scores_with_rag']['total_scores'], 
                                                               moonshot_stat['scores_without_rag']['total_scores'])):
                if rag_score < baseline_score:
                    declines.append(baseline_score - rag_score)
            
            if declines:
                avg_decline = sum(declines) / len(declines)
                print(f"平均下降分数: {avg_decline:.2f}")
        
        print("="*60)
    else:
        print("❌ 未找到Moonshot API的数据")
    
    return stats

if __name__ == "__main__":
    test_moonshot_only()
