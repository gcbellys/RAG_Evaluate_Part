#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试增强版RAG搜索效果

对比原版和增强版的搜索结果质量
"""

import sys
import json
from pathlib import Path

# 添加脚本目录到路径
sys.path.append(str(Path(__file__).parent))

from enhanced_rag3db_search_adapter import EnhancedRAG3DBSearchAdapter, MedicalTextPreprocessor

def test_medical_preprocessing():
    """测试医学文本预处理"""
    print("🧪 测试医学文本预处理")
    print("=" * 50)
    
    preprocessor = MedicalTextPreprocessor()
    
    test_cases = [
        "elevated PSA",
        "dyspnea on exertion", 
        "aortic valve replacement with a 21-mm magna ease aortic valve bioprosthesis",
        "RUL and RLL mass",
        "CHF with reduced EF"
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{i}. 测试用例: '{test_case}'")
        result = preprocessor.preprocess(test_case)
        
        print(f"   展开缩写: {result['expanded']}")
        print(f"   器官系统: {result['organ_system']}")
        print(f"   医学术语: {result['medical_terms']}")
        print(f"   同义词变体: {len(result['variants'])} 个")
        for variant in result['variants'][:3]:  # 只显示前3个
            if variant != result['expanded']:
                print(f"     - {variant}")

def test_single_symptom_search():
    """测试单个症状的搜索效果"""
    print("\n🔍 测试单症状搜索")
    print("=" * 50)
    
    try:
        adapter = EnhancedRAG3DBSearchAdapter(rag_db_type='uniform')
        
        test_symptom = "elevated PSA"
        print(f"\n测试症状: '{test_symptom}'")
        
        results = adapter.search_symptoms([test_symptom], top_k=3)
        
        if test_symptom in results:
            search_results = results[test_symptom]
            print(f"\n✅ 找到 {len(search_results)} 个结果:")
            
            for i, result in enumerate(search_results, 1):
                print(f"\n{i}. 排名 #{result['rank']}")
                print(f"   相似度: {result['cosine_similarity']:.4f}")
                print(f"   医学相关性: {result.get('medical_relevance', 'N/A'):.4f}")
                print(f"   综合分数: {result.get('combined_score', 'N/A'):.4f}")
                print(f"   症状: {result['symptom'][:100]}...")
                
                # 显示诊断信息
                metadata = result.get('metadata', {})
                u_unit_set = metadata.get('U_unit_set', [])
                if u_unit_set:
                    unit = u_unit_set[0]
                    u_unit = unit.get('u_unit', {})
                    diagnosis = u_unit.get('d_diagnosis', '')
                    organ = u_unit.get('o_organ', {})
                    organ_name = organ.get('organName', '')
                    
                    print(f"   诊断: {diagnosis[:100]}...")
                    print(f"   器官: {organ_name}")
        else:
            print("❌ 未找到搜索结果")
        
        adapter.close()
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")

def compare_search_quality():
    """对比搜索质量"""
    print("\n📊 对比搜索质量")
    print("=" * 50)
    
    # 这里可以添加与原版搜索的对比逻辑
    # 由于需要同时运行两个版本，暂时跳过
    print("⚠️  质量对比需要同时运行原版和增强版，暂时跳过")
    print("   建议：运行完整的评估流程后对比结果文件")

def main():
    """主测试函数"""
    print("🚀 增强版RAG搜索测试")
    print("=" * 60)
    
    # 测试1: 医学文本预处理
    test_medical_preprocessing()
    
    # 测试2: 单症状搜索
    test_single_symptom_search()
    
    # 测试3: 质量对比
    compare_search_quality()
    
    print("\n" + "=" * 60)
    print("✅ 测试完成")
    print("\n💡 使用建议:")
    print("   1. 运行增强版检索: bash scripts/step1_enhanced_rag3db_retrieve.sh 43001 43002")
    print("   2. 对比原版结果: 查看输出文件中的 'enhanced_ragoutcome' vs 'ragoutcome'")
    print("   3. 运行完整评估: python workflows/rag3db_full_pipeline.py 43001 43002")

if __name__ == "__main__":
    main()
