#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调试零分问题 - 分析为什么很多症状得分为0
"""

import json
from pathlib import Path

def debug_specific_case():
    """调试具体案例"""
    
    # 1. 检查基线文件中的期望结果
    baseline_file = "/home/duojiechen/projects/Rag_system/Rag_Evaluate/results/baseline_results/report_diagnostic_diagnostic_43060_evaluation_20250925_212827.json"
    
    print("🔍 检查基线文件...")
    with open(baseline_file, 'r', encoding='utf-8') as f:
        baseline_data = json.load(f)
    
    # 找到 "became bradycardic" 症状
    target_symptom = "became bradycardic"
    expected_organs = None
    
    for symptom in baseline_data.get('symptoms', []):
        if symptom.get('diagnosis') == target_symptom:
            expected_organs = symptom.get('expected_organs', [])
            print(f"✅ 找到症状: {target_symptom}")
            print(f"📋 期望器官: {expected_organs}")
            break
    
    # 2. 检查RAG文件中的预测结果
    rag_file = "/home/duojiechen/projects/Rag_system/Rag_Evaluate/results/report_context/rerun_with_rag/report_43060_withRAG_20250925_213106.json"
    
    print(f"\n🔍 检查RAG文件...")
    with open(rag_file, 'r', encoding='utf-8') as f:
        rag_data = json.load(f)
    
    symptoms_data = rag_data.get('symptoms', {})
    if target_symptom in symptoms_data:
        symptom_data = symptoms_data[target_symptom]
        api_responses = symptom_data.get('api_responses', {})
        
        print(f"✅ 找到RAG症状: {target_symptom}")
        
        # 检查各个API的响应
        for api_name, api_data in api_responses.items():
            if api_data.get('success', False):
                parsed_data = api_data.get('parsed_data', {})
                if 'full_response' in parsed_data:
                    predicted_organs = parsed_data['full_response'].get('organs', [])
                    print(f"🤖 {api_name} 预测器官: {predicted_organs}")
                    
                    # 计算匹配情况
                    if expected_organs and predicted_organs:
                        print(f"\n📊 匹配分析:")
                        
                        # 期望的器官-位置对
                        expected_pairs = set()
                        for organ in expected_organs:
                            organ_name = organ.get('organName', '')
                            locations = organ.get('anatomicalLocations', [])
                            for location in locations:
                                expected_pairs.add((organ_name, location))
                        
                        # 预测的器官-位置对
                        predicted_pairs = set()
                        for organ in predicted_organs:
                            organ_name = organ.get('organName', '')
                            locations = organ.get('anatomicalLocations', [])
                            for location in locations:
                                predicted_pairs.add((organ_name, location))
                        
                        print(f"   期望对: {expected_pairs}")
                        print(f"   预测对: {predicted_pairs}")
                        print(f"   交集: {expected_pairs.intersection(predicted_pairs)}")
                        
                        # 计算指标
                        intersection = expected_pairs.intersection(predicted_pairs)
                        precision = len(intersection) / len(predicted_pairs) if predicted_pairs else 0
                        recall = len(intersection) / len(expected_pairs) if expected_pairs else 0
                        f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
                        
                        print(f"   精准度: {precision:.4f}")
                        print(f"   召回率: {recall:.4f}")
                        print(f"   F1分数: {f1:.4f}")
                    break
    else:
        print(f"❌ 未在RAG文件中找到症状: {target_symptom}")

def check_successful_case():
    """检查一个成功的案例"""
    print(f"\n" + "="*60)
    print("🎯 检查成功案例: malodorous stools")
    
    # 检查基线
    baseline_file = "/home/duojiechen/projects/Rag_system/Rag_Evaluate/results/baseline_results/report_diagnostic_diagnostic_43060_evaluation_20250925_212827.json"
    
    with open(baseline_file, 'r', encoding='utf-8') as f:
        baseline_data = json.load(f)
    
    target_symptom = "malodorous stools"
    expected_organs = None
    
    for symptom in baseline_data.get('symptoms', []):
        if symptom.get('diagnosis') == target_symptom:
            expected_organs = symptom.get('expected_organs', [])
            print(f"✅ 期望器官: {expected_organs}")
            break
    
    # 检查RAG预测
    rag_file = "/home/duojiechen/projects/Rag_system/Rag_Evaluate/results/report_context/rerun_with_rag/report_43060_withRAG_20250925_213106.json"
    
    with open(rag_file, 'r', encoding='utf-8') as f:
        rag_data = json.load(f)
    
    symptoms_data = rag_data.get('symptoms', {})
    if target_symptom in symptoms_data:
        symptom_data = symptoms_data[target_symptom]
        api_responses = symptom_data.get('api_responses', {})
        
        for api_name, api_data in api_responses.items():
            if api_data.get('success', False):
                parsed_data = api_data.get('parsed_data', {})
                if 'full_response' in parsed_data:
                    predicted_organs = parsed_data['full_response'].get('organs', [])
                    print(f"🤖 {api_name} 预测器官: {predicted_organs}")
                    break

if __name__ == "__main__":
    debug_specific_case()
    check_successful_case()
