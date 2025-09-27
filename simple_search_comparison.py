#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简化的RAG搜索对比工具
"""

import json
import glob
from pathlib import Path

def load_and_compare():
    """加载并对比搜索结果"""
    
    # 加载原始结果
    orig_files = glob.glob('results/rag_output_uniform/report_*_FIXED_*.jsonl')
    orig_file = max(orig_files, key=lambda x: Path(x).stat().st_mtime) if orig_files else None
    
    # 加载增强结果
    enh_files = glob.glob('results/rag_output_uniform/diagnostic_*_ENHANCED_*.jsonl')
    enh_file = max(enh_files, key=lambda x: Path(x).stat().st_mtime) if enh_files else None
    
    if not orig_file or not enh_file:
        print("❌ 找不到对比文件")
        return
    
    print(f"📄 原始文件: {Path(orig_file).name}")
    print(f"📄 增强文件: {Path(enh_file).name}")
    
    # 读取数据
    orig_data = {}
    with open(orig_file, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                data = json.loads(line)
                orig_data[data['symptom']] = data
    
    enh_data = {}
    with open(enh_file, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                data = json.loads(line)
                enh_data[data['symptom']] = data
    
    print(f"\n📊 对比结果:")
    print("="*80)
    
    for symptom in orig_data.keys():
        if symptom in enh_data:
            orig_results = orig_data[symptom].get('rag_results', [])
            enh_results = enh_data[symptom].get('rag_results', [])
            
            print(f"\n🔍 症状: {symptom}")
            print("-" * 60)
            
            # 原始结果
            print("📋 原始搜索:")
            for i, result in enumerate(orig_results[:3]):
                sim = result.get('cosine_similarity', 0)
                symptom_text = result.get('symptom', '')[:40]
                print(f"  {i+1}. {symptom_text}... (相似度: {sim:.3f})")
            
            # 增强结果
            print("🚀 增强搜索:")
            for i, result in enumerate(enh_results[:3]):
                sim = result.get('cosine_similarity', 0)
                combined = result.get('combined_score', sim)
                symptom_text = result.get('symptom', '')[:40]
                query_variant = result.get('source_info', {}).get('query_variant', '')
                print(f"  {i+1}. {symptom_text}... (相似度: {sim:.3f}, 综合: {combined:.3f})")
                if query_variant != symptom:
                    print(f"      查询变体: {query_variant}")
            
            # 计算改进
            orig_avg = sum(r.get('cosine_similarity', 0) for r in orig_results) / len(orig_results) if orig_results else 0
            enh_avg = sum(r.get('cosine_similarity', 0) for r in enh_results) / len(enh_results) if enh_results else 0
            improvement = enh_avg - orig_avg
            
            status = "✅ 改进" if improvement > 0.01 else "❌ 下降" if improvement < -0.01 else "⚪ 无变化"
            print(f"📈 平均相似度变化: {orig_avg:.3f} → {enh_avg:.3f} ({improvement:+.3f}) {status}")
    
    print("\n" + "="*80)

if __name__ == "__main__":
    load_and_compare()
