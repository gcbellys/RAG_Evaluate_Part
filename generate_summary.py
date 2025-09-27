#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成RAG数据库性能对比总结
"""

import csv
import statistics

def generate_performance_summary():
    """生成性能对比总结"""
    
    strategies = ['baseline', 'uniform', 'report_context', 'sequential_block']
    results = {}

    for strategy in strategies:
        file_path = f'results/analysis_reports_fixed/{strategy}_results_analysis.csv'
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                data = list(reader)
                
            precisions = [float(row['precision']) for row in data]
            recalls = [float(row['recall']) for row in data]
            f1_scores = [float(row['f1_score']) for row in data]
            
            # 计算非零值的统计
            non_zero_precisions = [p for p in precisions if p > 0]
            non_zero_recalls = [r for r in recalls if r > 0]
            non_zero_f1s = [f for f in f1_scores if f > 0]
            
            results[strategy] = {
                'total_symptoms': len(data),
                'avg_precision': statistics.mean(precisions),
                'avg_recall': statistics.mean(recalls),
                'avg_f1_score': statistics.mean(f1_scores),
                'std_precision': statistics.stdev(precisions) if len(precisions) > 1 else 0.0,
                'std_recall': statistics.stdev(recalls) if len(recalls) > 1 else 0.0,
                'std_f1_score': statistics.stdev(f1_scores) if len(f1_scores) > 1 else 0.0,
                'non_zero_count': len(non_zero_f1s),
                'zero_count': len(f1_scores) - len(non_zero_f1s),
                'success_rate': len(non_zero_f1s) / len(f1_scores) * 100 if f1_scores else 0,
                'avg_precision_nz': statistics.mean(non_zero_precisions) if non_zero_precisions else 0,
                'avg_recall_nz': statistics.mean(non_zero_recalls) if non_zero_recalls else 0,
                'avg_f1_score_nz': statistics.mean(non_zero_f1s) if non_zero_f1s else 0
            }
        except Exception as e:
            print(f'Error processing {strategy}: {e}')

    print('📊 RAG数据库性能对比总结')
    print('=' * 100)
    
    # 总体性能对比
    print('🎯 总体性能对比 (所有症状)')
    print('-' * 100)
    print(f"{'策略':<20} {'精准度':<10} {'召回率':<10} {'F1分数':<10} {'症状数':<8} {'成功率%':<10}")
    print('-' * 100)

    strategy_names = {
        'baseline': 'Baseline (基线)',
        'uniform': 'Uniform Random',
        'report_context': 'Report Context', 
        'sequential_block': 'Sequential Block'
    }
    
    for strategy, data in results.items():
        name = strategy_names.get(strategy, strategy)
        print(f"{name:<20} {data['avg_precision']:<10.4f} {data['avg_recall']:<10.4f} {data['avg_f1_score']:<10.4f} {data['total_symptoms']:<8} {data['success_rate']:<10.1f}")

    print('\n🎯 有效预测性能对比 (仅非零分症状)')
    print('-' * 100)
    print(f"{'策略':<20} {'精准度':<10} {'召回率':<10} {'F1分数':<10} {'有效数':<8} {'零分数':<8}")
    print('-' * 100)
    
    for strategy, data in results.items():
        name = strategy_names.get(strategy, strategy)
        print(f"{name:<20} {data['avg_precision_nz']:<10.4f} {data['avg_recall_nz']:<10.4f} {data['avg_f1_score_nz']:<10.4f} {data['non_zero_count']:<8} {data['zero_count']:<8}")

    print('\n📈 性能变化分析')
    print('-' * 100)
    
    baseline_f1 = results['baseline']['avg_f1_score']
    baseline_f1_nz = results['baseline']['avg_f1_score_nz']
    
    print(f"{'策略':<20} {'F1变化':<12} {'F1变化%':<10} {'有效F1变化':<15} {'有效F1变化%':<12}")
    print('-' * 100)
    
    for strategy, data in results.items():
        if strategy == 'baseline':
            continue
            
        name = strategy_names.get(strategy, strategy)
        f1_change = data['avg_f1_score'] - baseline_f1
        f1_change_pct = (f1_change / baseline_f1) * 100 if baseline_f1 > 0 else 0
        
        f1_nz_change = data['avg_f1_score_nz'] - baseline_f1_nz
        f1_nz_change_pct = (f1_nz_change / baseline_f1_nz) * 100 if baseline_f1_nz > 0 else 0
        
        print(f"{name:<20} {f1_change:<+12.4f} {f1_change_pct:<+10.1f} {f1_nz_change:<+15.4f} {f1_nz_change_pct:<+12.1f}")

    print('\n🔍 关键发现')
    print('-' * 100)
    
    # 找出最佳RAG策略
    rag_strategies = {k: v for k, v in results.items() if k != 'baseline'}
    best_strategy = max(rag_strategies.keys(), key=lambda x: results[x]['avg_f1_score'])
    best_name = strategy_names[best_strategy]
    
    print(f"• 最佳RAG策略: {best_name}")
    print(f"• 基线F1分数: {baseline_f1:.4f}")
    print(f"• 最佳RAG F1分数: {results[best_strategy]['avg_f1_score']:.4f}")
    print(f"• 性能变化: {((results[best_strategy]['avg_f1_score'] - baseline_f1) / baseline_f1 * 100):+.1f}%")
    
    # 成功率分析
    baseline_success = results['baseline']['success_rate']
    print(f"\n• 基线成功率: {baseline_success:.1f}%")
    for strategy in ['uniform', 'report_context', 'sequential_block']:
        rag_success = results[strategy]['success_rate']
        name = strategy_names[strategy]
        print(f"• {name}成功率: {rag_success:.1f}% ({rag_success - baseline_success:+.1f}%)")
    
    print('=' * 100)

if __name__ == "__main__":
    generate_performance_summary()
