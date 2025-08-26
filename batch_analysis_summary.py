#!/usr/bin/env python3
"""
批量分析10个报告的RAG效果总结
"""
import json
import glob
from pathlib import Path

def analyze_batch_results():
    """分析批量测试的整体效果"""
    results_dir = Path("final_result/rerun_comparisons")
    
    total_reports = 0
    total_symptoms = 0
    overall_stats = {
        'deepseek': {'improved': 0, 'degraded': 0, 'unchanged': 0},
        'moonshot': {'improved': 0, 'degraded': 0, 'unchanged': 0}
    }
    
    print("=" * 80)
    print("📊 RAG系统批量评估总结 (4050-4059共10个报告)")
    print("=" * 80)
    
    for score_file in sorted(glob.glob(str(results_dir / "*/report_*_rag_score_report.txt"))):
        report_id = Path(score_file).parent.name.split('_')[1]
        total_reports += 1
        
        with open(score_file, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # 提取关键统计信息
        lines = content.split('\n')
        for i, line in enumerate(lines):
            if '总症状数:' in line:
                symptoms_count = int(line.split(':')[1].strip())
                total_symptoms += symptoms_count
                
            if '【DEEPSEEK】' in line and i+1 < len(lines):
                for j in range(i+1, min(i+5, len(lines))):
                    if '改善症状:' in lines[j]:
                        improved = int(lines[j].split('/')[0].split(':')[1].strip())
                        overall_stats['deepseek']['improved'] += improved
                    elif '负面影响:' in lines[j]:
                        degraded = int(lines[j].split('/')[0].split(':')[1].strip())
                        overall_stats['deepseek']['degraded'] += degraded
                    elif '无明显变化:' in lines[j]:
                        unchanged = int(lines[j].split('/')[0].split(':')[1].strip())
                        overall_stats['deepseek']['unchanged'] += unchanged
                        
            if '【MOONSHOT】' in line and i+1 < len(lines):
                for j in range(i+1, min(i+5, len(lines))):
                    if '改善症状:' in lines[j]:
                        improved = int(lines[j].split('/')[0].split(':')[1].strip())
                        overall_stats['moonshot']['improved'] += improved
                    elif '负面影响:' in lines[j]:
                        degraded = int(lines[j].split('/')[0].split(':')[1].strip())
                        overall_stats['moonshot']['degraded'] += degraded
                    elif '无明显变化:' in lines[j]:
                        unchanged = int(lines[j].split('/')[0].split(':')[1].strip())
                        overall_stats['moonshot']['unchanged'] += unchanged
        
        print(f"✅ 分析报告 {report_id}: {symptoms_count} 个症状")
    
    print(f"\n📋 总体统计:")
    print(f"   📁 处理报告数: {total_reports}")
    print(f"   🔬 总症状数: {total_symptoms}")
    
    print(f"\n🤖 API效果对比:")
    for api, stats in overall_stats.items():
        total_api_symptoms = sum(stats.values())
        improved_pct = (stats['improved'] / total_api_symptoms * 100) if total_api_symptoms > 0 else 0
        degraded_pct = (stats['degraded'] / total_api_symptoms * 100) if total_api_symptoms > 0 else 0
        unchanged_pct = (stats['unchanged'] / total_api_symptoms * 100) if total_api_symptoms > 0 else 0
        
        print(f"\n   【{api.upper()}】")
        print(f"     ✅ 改善: {stats['improved']}/{total_api_symptoms} ({improved_pct:.1f}%)")
        print(f"     ❌ 负面: {stats['degraded']}/{total_api_symptoms} ({degraded_pct:.1f}%)")
        print(f"     ⚪ 无变化: {stats['unchanged']}/{total_api_symptoms} ({unchanged_pct:.1f}%)")
        
        if improved_pct > degraded_pct:
            print(f"     📈 总体效果: 正面 (净改善 {improved_pct - degraded_pct:.1f}%)")
        elif degraded_pct > improved_pct:
            print(f"     📉 总体效果: 负面 (净损失 {degraded_pct - improved_pct:.1f}%)")
        else:
            print(f"     📊 总体效果: 中性")
    
    print("\n🎯 结论:")
    if overall_stats['deepseek']['improved'] + overall_stats['moonshot']['improved'] > \
       overall_stats['deepseek']['degraded'] + overall_stats['moonshot']['degraded']:
        print("   ✅ 智能RAG系统总体有效，能够改善LLM的医学诊断准确性")
    else:
        print("   ⚠️ 智能RAG系统需要进一步优化")
    
    print("=" * 80)

if __name__ == "__main__":
    analyze_batch_results()
