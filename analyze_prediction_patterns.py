#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
分析预测模式 - 验证基线是否预测更多器官和位置
"""

import csv
import json
import statistics
from pathlib import Path
from collections import defaultdict

def analyze_prediction_complexity():
    """分析各策略的预测复杂度"""
    
    strategies = ['baseline', 'uniform', 'report_context', 'sequential_block']
    results = {}
    
    print("🔍 分析各策略的预测复杂度...")
    print("=" * 80)
    
    for strategy in strategies:
        csv_file = f'/home/duojiechen/projects/Rag_system/Rag_Evaluate/results/analysis_reports_fixed/{strategy}_results_analysis.csv'
        
        try:
            with open(csv_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                data = list(reader)
            
            # 统计成功率定义
            total_symptoms = len(data)
            non_zero_f1 = sum(1 for row in data if float(row['f1_score']) > 0)
            success_rate = non_zero_f1 / total_symptoms * 100
            
            print(f"\n📊 {strategy.upper()} 策略:")
            print(f"   总症状数: {total_symptoms}")
            print(f"   非零F1症状数: {non_zero_f1}")
            print(f"   成功率: {success_rate:.1f}% (非零F1分数的症状比例)")
            
            # 分析F1分数分布
            f1_scores = [float(row['f1_score']) for row in data]
            zero_count = sum(1 for f1 in f1_scores if f1 == 0.0)
            low_count = sum(1 for f1 in f1_scores if 0.0 < f1 <= 0.3)
            mid_count = sum(1 for f1 in f1_scores if 0.3 < f1 <= 0.7)
            high_count = sum(1 for f1 in f1_scores if f1 > 0.7)
            
            print(f"   F1分数分布:")
            print(f"     零分 (0.0): {zero_count} ({zero_count/total_symptoms*100:.1f}%)")
            print(f"     低分 (0-0.3]: {low_count} ({low_count/total_symptoms*100:.1f}%)")
            print(f"     中分 (0.3-0.7]: {mid_count} ({mid_count/total_symptoms*100:.1f}%)")
            print(f"     高分 (>0.7): {high_count} ({high_count/total_symptoms*100:.1f}%)")
            
            results[strategy] = {
                'total': total_symptoms,
                'success_count': non_zero_f1,
                'success_rate': success_rate,
                'zero_count': zero_count,
                'distribution': {
                    'zero': zero_count,
                    'low': low_count,
                    'mid': mid_count,
                    'high': high_count
                }
            }
            
        except Exception as e:
            print(f"处理{strategy}时出错: {e}")
    
    return results

def analyze_organ_location_complexity():
    """分析器官和位置预测的复杂度"""
    
    print(f"\n🔬 分析器官和位置预测复杂度...")
    print("=" * 80)
    
    # 分析基线文件中的预测复杂度
    baseline_file = "/home/duojiechen/projects/Rag_system/Rag_Evaluate/results/baseline_results/report_diagnostic_diagnostic_43060_evaluation_20250925_212827.json"
    rag_file = "/home/duojiechen/projects/Rag_system/Rag_Evaluate/results/report_context/rerun_with_rag/report_43060_withRAG_20250925_213106.json"
    
    try:
        # 分析基线预测
        with open(baseline_file, 'r', encoding='utf-8') as f:
            baseline_data = json.load(f)
        
        print("📋 基线预测分析 (报告43060):")
        baseline_stats = analyze_single_file_predictions(baseline_data, "baseline")
        
        # 分析RAG预测
        with open(rag_file, 'r', encoding='utf-8') as f:
            rag_data = json.load(f)
        
        print(f"\n📋 RAG预测分析 (报告43060):")
        rag_stats = analyze_single_file_predictions(rag_data, "rag")
        
        # 对比分析
        print(f"\n📊 预测复杂度对比:")
        print(f"   基线平均器官数: {baseline_stats['avg_organs']:.2f}")
        print(f"   RAG平均器官数: {rag_stats['avg_organs']:.2f}")
        print(f"   基线平均位置数: {baseline_stats['avg_locations']:.2f}")
        print(f"   RAG平均位置数: {rag_stats['avg_locations']:.2f}")
        print(f"   基线预测失败率: {baseline_stats['failure_rate']:.1f}%")
        print(f"   RAG预测失败率: {rag_stats['failure_rate']:.1f}%")
        
    except Exception as e:
        print(f"分析器官位置复杂度时出错: {e}")

def analyze_single_file_predictions(data, data_type):
    """分析单个文件的预测复杂度"""
    
    organ_counts = []
    location_counts = []
    total_predictions = 0
    failed_predictions = 0
    
    if data_type == "baseline":
        symptoms = data.get('symptoms', [])
        
        for symptom in symptoms:
            api_responses = symptom.get('api_responses', {})
            
            # 获取第一个成功的API响应
            predicted_organs = []
            for api_name in ['moonshot', 'anthropic', 'gemini', 'deepseek', 'qwen']:
                if api_name in api_responses:
                    api_data = api_responses[api_name]
                    if api_data.get('success', False):
                        if 'full_response' in api_data.get('parsed_data', {}):
                            predicted_organs = api_data['parsed_data']['full_response'].get('organs', [])
                            break
                        elif 'organs' in api_data.get('parsed_data', {}):
                            predicted_organs = api_data['parsed_data']['organs']
                            break
            
            total_predictions += 1
            
            if not predicted_organs:
                failed_predictions += 1
                organ_counts.append(0)
                location_counts.append(0)
            else:
                organ_counts.append(len(predicted_organs))
                total_locations = sum(len(organ.get('anatomicalLocations', [])) for organ in predicted_organs)
                location_counts.append(total_locations)
                
                # 显示具体预测
                symptom_text = symptom.get('diagnosis', 'unknown')[:50]
                print(f"     症状: {symptom_text}...")
                print(f"       预测器官数: {len(predicted_organs)}, 位置数: {total_locations}")
                if len(predicted_organs) > 0:
                    for organ in predicted_organs:
                        organ_name = organ.get('organName', 'Unknown')
                        locations = organ.get('anatomicalLocations', [])
                        print(f"         {organ_name}: {locations}")
    
    elif data_type == "rag":
        symptoms_data = data.get('symptoms', {})
        
        for symptom_text, symptom_data in symptoms_data.items():
            if isinstance(symptom_data, dict) and 'api_responses' in symptom_data:
                api_responses = symptom_data.get('api_responses', {})
                
                # 获取第一个成功的API响应
                predicted_organs = []
                for api_name in ['moonshot', 'anthropic', 'gemini', 'deepseek', 'qwen']:
                    if api_name in api_responses:
                        api_data = api_responses[api_name]
                        if api_data.get('success', False):
                            if 'full_response' in api_data.get('parsed_data', {}):
                                predicted_organs = api_data['parsed_data']['full_response'].get('organs', [])
                                break
                            elif 'organs' in api_data.get('parsed_data', {}):
                                predicted_organs = api_data['parsed_data']['organs']
                                break
                
                total_predictions += 1
                
                if not predicted_organs:
                    failed_predictions += 1
                    organ_counts.append(0)
                    location_counts.append(0)
                else:
                    organ_counts.append(len(predicted_organs))
                    total_locations = sum(len(organ.get('anatomicalLocations', [])) for organ in predicted_organs)
                    location_counts.append(total_locations)
                    
                    # 显示具体预测
                    print(f"     症状: {symptom_text[:50]}...")
                    print(f"       预测器官数: {len(predicted_organs)}, 位置数: {total_locations}")
                    if len(predicted_organs) > 0:
                        for organ in predicted_organs:
                            organ_name = organ.get('organName', 'Unknown')
                            locations = organ.get('anatomicalLocations', [])
                            print(f"         {organ_name}: {locations}")
    
    return {
        'avg_organs': statistics.mean(organ_counts) if organ_counts else 0,
        'avg_locations': statistics.mean(location_counts) if location_counts else 0,
        'failure_rate': failed_predictions / total_predictions * 100 if total_predictions > 0 else 0,
        'total_predictions': total_predictions,
        'failed_predictions': failed_predictions
    }

def main():
    """主函数"""
    print("🎯 验证成功率定义和预测复杂度分析")
    print("=" * 80)
    
    # 1. 分析成功率定义
    success_results = analyze_prediction_complexity()
    
    # 2. 分析器官位置预测复杂度
    analyze_organ_location_complexity()
    
    print(f"\n💡 关键发现:")
    print("=" * 80)
    print("🔍 成功率定义: 获得非零F1分数的症状占总症状的比例")
    print("📊 基线成功率高可能原因:")
    print("   1. 基线AI模型更容易给出预测结果(即使不准确)")
    print("   2. RAG信息可能导致AI更加谨慎，部分情况下不给出预测")
    print("   3. 需要验证基线是否预测了更多器官和位置")

if __name__ == "__main__":
    main()
