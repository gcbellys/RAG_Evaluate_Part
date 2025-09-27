#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试增强版prompt的效果
使用置信度感知的RAG结果和新的prompt进行实际测试
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Any

# 添加脚本路径
sys.path.append(str(Path(__file__).parent / "scripts"))
from confidence_aware_rag_adapter import ConfidenceAwareRAGAdapter

def load_enhanced_prompt() -> str:
    """加载增强版prompt"""
    prompt_file = Path(__file__).parent / "prompt" / "rag_enhanced_prompt.txt"
    with open(prompt_file, 'r', encoding='utf-8') as f:
        return f.read()

def format_rag_results_for_prompt(symptom: str, rag_results: List[Dict[str, Any]]) -> str:
    """将RAG结果格式化为prompt所需的格式"""
    
    if not rag_results:
        return f"""
**Patient Symptom**: {symptom}

**Search Results**: No relevant results found in the medical knowledge base.
Please base your assessment entirely on your clinical expertise.
"""
    
    # 按置信度分组
    high_conf = []
    medium_conf = []
    low_conf = []
    very_low_conf = []
    
    for result in rag_results:
        similarity = result.get('cosine_similarity', 0)
        if similarity >= 0.85:
            high_conf.append(result)
        elif similarity >= 0.65:
            medium_conf.append(result)
        elif similarity >= 0.45:
            low_conf.append(result)
        else:
            very_low_conf.append(result)
    
    formatted_results = f"""
**Patient Symptom**: {symptom}

**Search Results from Medical Knowledge Base**:

"""
    
    # 高置信度结果
    if high_conf:
        formatted_results += f"""
🎯 **HIGH CONFIDENCE RESULTS (Similarity >0.85)**:
"""
        for i, result in enumerate(high_conf, 1):
            similarity = result.get('cosine_similarity', 0)
            symptom_text = result.get('symptom', '')
            metadata = result.get('metadata', {})
            
            # 提取诊断和器官信息
            diagnosis = "Unknown"
            organ = "Unknown"
            locations = []
            
            if isinstance(metadata, dict):
                u_unit_set = metadata.get('U_unit_set', [])
                if u_unit_set and isinstance(u_unit_set, list):
                    u_unit = u_unit_set[0].get('u_unit', {})
                    diagnosis = u_unit.get('d_diagnosis', 'Unknown')
                    organ_info = u_unit.get('o_organ', {})
                    organ = organ_info.get('organName', 'Unknown')
                    locations = organ_info.get('anatomicalLocations', [])
            
            formatted_results += f"""
Result {i}: (Similarity: {similarity:.3f})
- Symptom: "{symptom_text}"
- Related Diagnosis: {diagnosis}
- Organ: {organ}
- Anatomical Locations: {', '.join(locations[:3]) if locations else 'Not specified'}
"""
    
    # 中等置信度结果
    if medium_conf:
        formatted_results += f"""
📊 **MEDIUM CONFIDENCE RESULTS (Similarity 0.65-0.85)**:
"""
        for i, result in enumerate(medium_conf, 1):
            similarity = result.get('cosine_similarity', 0)
            symptom_text = result.get('symptom', '')
            metadata = result.get('metadata', {})
            
            diagnosis = "Unknown"
            organ = "Unknown"
            locations = []
            
            if isinstance(metadata, dict):
                u_unit_set = metadata.get('U_unit_set', [])
                if u_unit_set and isinstance(u_unit_set, list):
                    u_unit = u_unit_set[0].get('u_unit', {})
                    diagnosis = u_unit.get('d_diagnosis', 'Unknown')
                    organ_info = u_unit.get('o_organ', {})
                    organ = organ_info.get('organName', 'Unknown')
                    locations = organ_info.get('anatomicalLocations', [])
            
            formatted_results += f"""
Result {i}: (Similarity: {similarity:.3f})
- Symptom: "{symptom_text}"
- Related Diagnosis: {diagnosis}
- Organ: {organ}
- Anatomical Locations: {', '.join(locations[:3]) if locations else 'Not specified'}
"""
    
    # 低置信度结果
    if low_conf:
        formatted_results += f"""
⚠️ **LOW CONFIDENCE RESULTS (Similarity 0.45-0.65)**:
"""
        for i, result in enumerate(low_conf, 1):
            similarity = result.get('cosine_similarity', 0)
            symptom_text = result.get('symptom', '')
            formatted_results += f"""
Result {i}: (Similarity: {similarity:.3f}) - "{symptom_text}" [TREAT WITH SKEPTICISM]
"""
    
    # 极低置信度结果
    if very_low_conf:
        formatted_results += f"""
❌ **VERY LOW CONFIDENCE RESULTS (Similarity <0.45)**:
{len(very_low_conf)} results with very low similarity - Generally should be ignored.
"""
    
    formatted_results += f"""

**Summary**:
- High Confidence: {len(high_conf)} results
- Medium Confidence: {len(medium_conf)} results  
- Low Confidence: {len(low_conf)} results
- Very Low Confidence: {len(very_low_conf)} results

Please evaluate each result critically and use only those that enhance your clinical assessment.
"""
    
    return formatted_results

def create_complete_prompt(symptom: str, rag_results: List[Dict[str, Any]]) -> str:
    """创建完整的测试prompt"""
    
    base_prompt = load_enhanced_prompt()
    formatted_results = format_rag_results_for_prompt(symptom, rag_results)
    
    complete_prompt = f"""{base_prompt}

{formatted_results}

Please provide your assessment in the required JSON format, ensuring you:
1. First state your independent clinical assessment
2. Critically evaluate each search result
3. Clearly indicate which results you trust/reject and why
4. Show the influence of search results on your final decision
"""
    
    return complete_prompt

def test_enhanced_prompt_on_sample():
    """在样本数据上测试增强版prompt"""
    
    print("🧪 测试增强版prompt效果")
    print("="*60)
    
    # 初始化置信度感知适配器
    adapter = ConfidenceAwareRAGAdapter(
        rag_db_type='uniform',
        debug=False
    )
    
    # 测试症状
    test_symptoms = [
        "headache",
        "numbness around the back portion of her head", 
        "brain lesions"
    ]
    
    for symptom in test_symptoms:
        print(f"\n🔍 测试症状: {symptom}")
        print("-" * 40)
        
        # 获取RAG结果
        results = adapter.search_symptoms([symptom], top_k=3)
        rag_results = results.get(symptom, [])
        
        # 创建完整prompt
        complete_prompt = create_complete_prompt(symptom, rag_results)
        
        # 保存prompt到文件
        output_file = f"prompt_test_{symptom.replace(' ', '_')}.txt"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(complete_prompt)
        
        print(f"✅ Prompt已保存: {output_file}")
        
        # 显示关键信息
        if rag_results:
            similarities = [r.get('cosine_similarity', 0) for r in rag_results]
            high_conf = sum(1 for s in similarities if s >= 0.85)
            medium_conf = sum(1 for s in similarities if 0.65 <= s < 0.85)
            low_conf = sum(1 for s in similarities if 0.45 <= s < 0.65)
            very_low_conf = sum(1 for s in similarities if s < 0.45)
            
            print(f"📊 置信度分布: 高={high_conf}, 中={medium_conf}, 低={low_conf}, 极低={very_low_conf}")
            print(f"📈 相似度范围: {min(similarities):.3f} - {max(similarities):.3f}")
        else:
            print("❌ 无RAG结果")
        
        # 显示prompt预览
        print(f"📄 Prompt长度: {len(complete_prompt)} 字符")
        print(f"📋 Prompt预览:")
        print(complete_prompt[:500] + "..." if len(complete_prompt) > 500 else complete_prompt)

def main():
    """主函数"""
    print("🚀 启动增强版prompt测试")
    
    try:
        test_enhanced_prompt_on_sample()
        print(f"\n✅ 测试完成！")
        print(f"📁 生成的prompt文件可用于LLM测试")
        print(f"🎯 关键改进:")
        print(f"   • 强调临床经验优先")
        print(f"   • 置信度感知评估")
        print(f"   • 明确的决策透明度")
        print(f"   • 批判性思维引导")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
