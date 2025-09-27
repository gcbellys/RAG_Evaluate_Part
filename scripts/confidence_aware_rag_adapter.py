#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
置信度感知的RAG适配器
根据相似度置信度调整RAG上下文的表述方式，让LLM对低置信度结果保持谨慎
"""

import os
import sys
import json
import numpy as np
from typing import List, Dict, Any, Tuple
from pathlib import Path
from datetime import datetime

# 继承增强版搜索适配器
sys.path.append(str(Path(__file__).parent))
from enhanced_rag_search_adapter import EnhancedRAGSearchAdapter

class ConfidenceAwareRAGAdapter(EnhancedRAGSearchAdapter):
    """置信度感知的RAG适配器"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # 置信度阈值配置
        self.confidence_thresholds = {
            'high_confidence': 0.85,      # 高置信度阈值
            'medium_confidence': 0.65,    # 中等置信度阈值  
            'low_confidence': 0.45,       # 低置信度阈值
            'very_low_confidence': 0.30   # 极低置信度阈值
        }
        
        # 置信度标签配置
        self.confidence_labels = {
            'high': {
                'label': '🎯 高度相关',
                'reliability': '可信度: 高',
                'instruction': '以下信息高度相关，可作为主要参考依据'
            },
            'medium': {
                'label': '📊 中度相关', 
                'reliability': '可信度: 中等',
                'instruction': '以下信息中度相关，建议结合其他信息综合判断'
            },
            'low': {
                'label': '⚠️ 低度相关',
                'reliability': '可信度: 较低', 
                'instruction': '以下信息相关性较低，请谨慎参考，优先依靠临床经验'
            },
            'very_low': {
                'label': '❓ 相关性存疑',
                'reliability': '可信度: 很低',
                'instruction': '以下信息相关性存疑，仅供参考，不建议作为主要依据'
            }
        }
    
    def _classify_confidence(self, similarity: float) -> str:
        """根据相似度分类置信度等级"""
        if similarity >= self.confidence_thresholds['high_confidence']:
            return 'high'
        elif similarity >= self.confidence_thresholds['medium_confidence']:
            return 'medium'
        elif similarity >= self.confidence_thresholds['low_confidence']:
            return 'low'
        else:
            return 'very_low'
    
    def _format_rag_context_with_confidence(self, symptom: str, rag_results: List[Dict[str, Any]]) -> str:
        """格式化带置信度标识的RAG上下文"""
        
        if not rag_results:
            return f"❌ 未找到与症状 '{symptom}' 相关的参考信息。请完全依靠临床经验进行诊断。"
        
        # 按置信度分组
        confidence_groups = {
            'high': [],
            'medium': [], 
            'low': [],
            'very_low': []
        }
        
        for result in rag_results:
            similarity = result.get('cosine_similarity', 0)
            confidence_level = self._classify_confidence(similarity)
            confidence_groups[confidence_level].append(result)
        
        # 构建上下文
        context_parts = []
        context_parts.append(f"📋 症状: {symptom}")
        context_parts.append(f"🔍 检索到 {len(rag_results)} 条相关医学信息，按可信度分类如下：\n")
        
        # 按置信度从高到低展示
        for confidence_level in ['high', 'medium', 'low', 'very_low']:
            results = confidence_groups[confidence_level]
            if not results:
                continue
                
            label_info = self.confidence_labels[confidence_level]
            context_parts.append(f"## {label_info['label']} ({label_info['reliability']})")
            context_parts.append(f"**{label_info['instruction']}**\n")
            
            for i, result in enumerate(results, 1):
                similarity = result.get('cosine_similarity', 0)
                symptom_text = result.get('symptom', '')
                metadata = result.get('metadata', {})
                
                # 提取诊断信息
                diagnosis = "未知诊断"
                organ = "未知器官"
                locations = []
                
                if isinstance(metadata, dict):
                    u_unit_set = metadata.get('U_unit_set', [])
                    if u_unit_set and isinstance(u_unit_set, list):
                        u_unit = u_unit_set[0].get('u_unit', {})
                        diagnosis = u_unit.get('d_diagnosis', '未知诊断')
                        organ_info = u_unit.get('o_organ', {})
                        organ = organ_info.get('organName', '未知器官')
                        locations = organ_info.get('anatomicalLocations', [])
                
                context_parts.append(f"### 参考信息 {i} (相似度: {similarity:.3f})")
                context_parts.append(f"- **症状描述**: {symptom_text}")
                context_parts.append(f"- **相关诊断**: {diagnosis}")
                context_parts.append(f"- **涉及器官**: {organ}")
                if locations:
                    context_parts.append(f"- **解剖位置**: {', '.join(locations[:3])}")
                
                # 根据置信度添加特殊说明
                if confidence_level == 'high':
                    context_parts.append("- **建议**: 此信息高度可信，可作为诊断的重要参考")
                elif confidence_level == 'medium':
                    context_parts.append("- **建议**: 此信息具有一定参考价值，建议结合其他信息")
                elif confidence_level == 'low':
                    context_parts.append("- **⚠️ 注意**: 此信息相关性较低，请谨慎使用")
                else:  # very_low
                    context_parts.append("- **❗ 警告**: 此信息相关性存疑，不建议作为主要依据")
                
                context_parts.append("")  # 空行分隔
        
        # 添加总体指导
        high_count = len(confidence_groups['high'])
        medium_count = len(confidence_groups['medium'])
        low_count = len(confidence_groups['low'])
        very_low_count = len(confidence_groups['very_low'])
        
        context_parts.append("## 📊 信息质量总结")
        context_parts.append(f"- 高可信度信息: {high_count} 条")
        context_parts.append(f"- 中等可信度信息: {medium_count} 条") 
        context_parts.append(f"- 低可信度信息: {low_count} 条")
        context_parts.append(f"- 存疑信息: {very_low_count} 条")
        
        # 根据信息质量分布给出指导
        if high_count >= 2:
            guidance = "✅ **诊断建议**: 有充足的高质量参考信息，可以较为自信地进行诊断分析"
        elif high_count + medium_count >= 2:
            guidance = "📊 **诊断建议**: 有一定质量的参考信息，建议综合分析后给出诊断"
        elif high_count + medium_count >= 1:
            guidance = "⚠️ **诊断建议**: 参考信息有限，请主要依靠临床经验，谨慎使用检索信息"
        else:
            guidance = "❗ **诊断建议**: 检索信息质量较差，请完全依靠临床经验进行诊断，忽略检索结果"
        
        context_parts.append(f"\n{guidance}")
        
        return "\n".join(context_parts)
    
    def generate_confidence_aware_prompt(self, symptom: str, rag_results: List[Dict[str, Any]], 
                                       base_prompt: str = None) -> str:
        """生成置信度感知的完整prompt"""
        
        # 默认基础prompt
        if base_prompt is None:
            base_prompt = """你是一位经验丰富的临床医生。请根据给定的症状信息，结合提供的医学参考资料，进行诊断分析。

**重要说明**:
1. 优先依靠你的医学知识和临床经验
2. 参考资料按可信度分级，请根据可信度等级合理使用
3. 对于低可信度的信息，请保持谨慎态度
4. 如果参考信息质量较差，请主要依靠临床经验

请提供以下分析：
1. 最可能的诊断及其理由
2. 需要考虑的鉴别诊断
3. 建议的进一步检查
4. 涉及的器官系统和解剖位置"""
        
        # 格式化RAG上下文
        rag_context = self._format_rag_context_with_confidence(symptom, rag_results)
        
        # 组合完整prompt
        full_prompt = f"""{base_prompt}

## 🔍 医学参考资料

{rag_context}

## 📝 请基于以上信息进行分析

**当前症状**: {symptom}

请根据参考资料的可信度等级，结合你的临床经验，提供诊断分析："""

        return full_prompt
    
    def save_confidence_aware_results(self, results: Dict[str, List[Dict[str, Any]]], 
                                    output_file: str, include_prompts: bool = True):
        """保存包含置信度信息和prompt的结果"""
        output_data = []
        
        for symptom, symptom_results in results.items():
            # 基础结果条目
            result_entry = {
                "symptom": symptom,
                "query": symptom,
                "rag_results": symptom_results,
                "database_type": self.rag_db_type,
                "database_description": "Uniform Random Unit Database (Confidence-Aware)",
                "search_method": "CONFIDENCE_AWARE_enhanced_search",
                "enhancement_config": self.config,
                "top_k": len(symptom_results),
                "timestamp": datetime.now().isoformat()
            }
            
            # 添加置信度分析
            if symptom_results:
                confidences = [self._classify_confidence(r.get('cosine_similarity', 0)) 
                             for r in symptom_results]
                confidence_stats = {
                    'high': confidences.count('high'),
                    'medium': confidences.count('medium'), 
                    'low': confidences.count('low'),
                    'very_low': confidences.count('very_low')
                }
                result_entry['confidence_analysis'] = {
                    'confidence_distribution': confidence_stats,
                    'dominant_confidence': max(confidence_stats.items(), key=lambda x: x[1])[0],
                    'avg_similarity': sum(r.get('cosine_similarity', 0) for r in symptom_results) / len(symptom_results)
                }
            
            # 添加置信度感知的prompt
            if include_prompts:
                confidence_prompt = self.generate_confidence_aware_prompt(symptom, symptom_results)
                result_entry['confidence_aware_prompt'] = confidence_prompt
            
            output_data.append(result_entry)
        
        # 保存为JSONL格式
        with open(output_file, 'w', encoding='utf-8') as f:
            for entry in output_data:
                f.write(json.dumps(entry, ensure_ascii=False) + '\n')
        
        if self.debug:
            print(f"💾 置信度感知检索结果已保存: {output_file}")

def main():
    """主函数 - 演示置信度感知RAG"""
    import argparse
    
    parser = argparse.ArgumentParser(description="置信度感知RAG适配器")
    parser.add_argument("--file", required=True, help="输入的诊断文件路径")
    parser.add_argument("--top_k", type=int, default=3, help="返回的top-k结果数量")
    parser.add_argument("--output_dir", required=True, help="输出目录")
    parser.add_argument("--rag_db_type", default="uniform", help="RAG数据库类型")
    
    args = parser.parse_args()
    
    # 置信度感知配置
    confidence_config = {
        'query_expansion': {
            'enabled': True,
            'synonym_expansion': True,
            'abbreviation_expansion': True,
            'medical_term_expansion': True,
            'max_expansions': 3
        },
        'retrieval_strategy': {
            'multi_query': True,
            'adaptive_top_k': True,
            'base_top_k': args.top_k,
            'max_top_k': args.top_k * 3,
            'similarity_threshold': 0.3  # 降低阈值以获取更多结果进行置信度分析
        },
        'result_enhancement': {
            'diversity_filtering': True,
            'semantic_reranking': True,
            'relevance_scoring': True,
            'max_results': args.top_k
        }
    }
    
    # 初始化置信度感知适配器
    adapter = ConfidenceAwareRAGAdapter(
        rag_db_type=args.rag_db_type,
        enhancement_config=confidence_config,
        debug=True
    )
    
    # 读取输入文件
    with open(args.file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # 提取症状
    symptoms = []
    if isinstance(data, list):
        for item in data:
            if isinstance(item, dict) and 's_symptom' in item:
                symptoms.append(item['s_symptom'])
    
    print(f"📋 提取到 {len(symptoms)} 个症状")
    
    # 执行置信度感知检索
    results = adapter.search_symptoms(symptoms, args.top_k)
    
    # 保存结果
    input_filename = Path(args.file).stem
    output_filename = f"{input_filename}_CONFIDENCE_AWARE_ragoutcome_{args.rag_db_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jsonl"
    output_path = Path(args.output_dir) / output_filename
    
    adapter.save_confidence_aware_results(results, str(output_path), include_prompts=True)
    
    print(f"✅ 置信度感知检索完成！输出文件: {output_path}")
    
    # 演示置信度感知prompt
    if symptoms:
        print(f"\n🎯 演示症状 '{symptoms[0]}' 的置信度感知prompt:")
        print("="*80)
        sample_prompt = adapter.generate_confidence_aware_prompt(
            symptoms[0], 
            results.get(symptoms[0], [])
        )
        print(sample_prompt[:1000] + "..." if len(sample_prompt) > 1000 else sample_prompt)

if __name__ == "__main__":
    main()
