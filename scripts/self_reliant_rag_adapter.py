#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自主判断增强的RAG适配器
强调LLM的临床经验和自主判断能力，将RAG信息作为辅助参考
"""

import os
import sys
import json
from typing import List, Dict, Any
from pathlib import Path
from datetime import datetime

# 继承置信度感知适配器
sys.path.append(str(Path(__file__).parent))
from confidence_aware_rag_adapter import ConfidenceAwareRAGAdapter

class SelfReliantRAGAdapter(ConfidenceAwareRAGAdapter):
    """自主判断增强的RAG适配器"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # 自主判断prompt模板
        self.self_reliant_prompts = {
            'clinical_first': self._get_clinical_first_prompt(),
            'critical_thinking': self._get_critical_thinking_prompt(),
            'evidence_based': self._get_evidence_based_prompt()
        }
    
    def _get_clinical_first_prompt(self) -> str:
        """临床经验优先的prompt"""
        return """你是一位资深的临床医生，拥有丰富的诊断经验和深厚的医学知识。

🎯 **核心指导原则**:
1. **首先依靠你的临床经验和医学知识**进行独立分析
2. **批判性地评估**提供的参考信息，不要盲目接受
3. **如果参考信息与你的临床判断冲突，优先相信你的经验**
4. **将参考信息作为辅助验证**，而非主要依据

📋 **诊断流程**:
1. 基于症状，运用你的医学知识进行初步诊断分析
2. 考虑可能的鉴别诊断和病理生理机制
3. 然后参考提供的医学资料进行验证或补充
4. 如果发现参考资料有误或不相关，请明确指出并说明理由

⚠️ **重要提醒**:
- 参考资料可能存在错误、不完整或不相关的情况
- 你的临床经验和医学训练是最可靠的基础
- 保持独立思考，不要被低质量的参考信息误导"""

    def _get_critical_thinking_prompt(self) -> str:
        """批判性思维prompt"""
        return """你是一位具有批判性思维的临床专家，善于独立分析和质疑。

🧠 **思维模式**:
1. **独立分析**: 首先基于症状进行独立的临床推理
2. **批判评估**: 对每条参考信息进行批判性评估
3. **证据权衡**: 权衡不同信息源的可靠性和相关性
4. **自信决策**: 基于综合判断做出自信的诊断决策

🔍 **评估标准**:
- 参考信息的医学逻辑是否合理？
- 症状描述与诊断是否匹配？
- 解剖位置和病理机制是否正确？
- 信息是否与已知医学知识一致？

💡 **决策原则**:
- 如果参考信息支持你的判断 → 可以作为佐证
- 如果参考信息与你的判断冲突 → 深入分析原因，优先相信你的专业判断
- 如果参考信息不相关 → 忽略并说明理由
- 如果参考信息质量差 → 完全依靠你的临床经验"""

    def _get_evidence_based_prompt(self) -> str:
        """循证医学prompt"""
        return """你是一位循证医学专家，擅长整合多源信息并做出基于证据的临床决策。

📊 **循证思维**:
1. **临床经验为基石**: 你的医学训练和临床经验是最重要的证据来源
2. **信息质量评估**: 严格评估每条参考信息的质量和可信度
3. **证据整合**: 将高质量信息与临床经验相结合
4. **不确定性管理**: 在信息不足时，明确表达不确定性

🎯 **证据层级** (从高到低):
1. 你的临床经验和医学知识
2. 高相似度且逻辑合理的参考信息
3. 中等相似度但需要验证的信息
4. 低相似度或逻辑存疑的信息

⚖️ **决策框架**:
- 当证据充分且一致时 → 给出明确诊断
- 当证据冲突时 → 说明不同可能性，优先考虑临床经验支持的诊断
- 当证据不足时 → 诚实表达不确定性，建议进一步检查
- 当参考信息质量差时 → 主要依靠临床经验，明确说明参考信息的局限性"""

    def generate_self_reliant_prompt(self, symptom: str, rag_results: List[Dict[str, Any]], 
                                   prompt_style: str = 'clinical_first') -> str:
        """生成强调自主判断的prompt"""
        
        # 获取基础prompt模板
        base_prompt = self.self_reliant_prompts.get(prompt_style, self.self_reliant_prompts['clinical_first'])
        
        # 格式化RAG上下文（使用置信度感知格式）
        rag_context = self._format_rag_context_with_confidence(symptom, rag_results)
        
        # 根据信息质量调整指导语
        if rag_results:
            high_confidence_count = sum(1 for r in rag_results 
                                      if self._classify_confidence(r.get('cosine_similarity', 0)) == 'high')
            medium_confidence_count = sum(1 for r in rag_results 
                                        if self._classify_confidence(r.get('cosine_similarity', 0)) == 'medium')
            
            if high_confidence_count >= 2:
                guidance = """
🟢 **当前情况**: 有较多高质量参考信息可用
📋 **建议策略**: 
1. 先进行独立临床分析
2. 将高质量参考信息作为重要佐证
3. 对中低质量信息保持谨慎
4. 最终诊断应基于你的临床判断与高质量信息的结合"""
            elif high_confidence_count + medium_confidence_count >= 2:
                guidance = """
🟡 **当前情况**: 有一定质量的参考信息，但需要谨慎评估
📋 **建议策略**:
1. 主要依靠你的临床经验进行分析
2. 批判性地评估参考信息的相关性和准确性
3. 只采用与你的临床判断一致且逻辑合理的信息
4. 对存疑信息明确指出问题所在"""
            else:
                guidance = """
🔴 **当前情况**: 参考信息质量较差，相关性存疑
📋 **建议策略**:
1. **完全依靠你的临床经验和医学知识**
2. 忽略低质量的参考信息
3. 基于症状特点进行独立的病理生理分析
4. 明确说明为什么忽略了参考信息"""
        else:
            guidance = """
⚪ **当前情况**: 无可用参考信息
📋 **建议策略**: 完全基于你的临床经验和医学知识进行诊断分析"""
        
        # 组合完整prompt
        full_prompt = f"""{base_prompt}

{guidance}

## 🔍 提供的参考信息

{rag_context}

## 🎯 请进行独立的临床分析

**患者症状**: {symptom}

**分析要求**:
1. **首先进行独立分析**: 基于症状，运用你的医学知识分析可能的诊断
2. **批判性评估参考信息**: 评估每条参考信息的质量、相关性和准确性
3. **整合判断**: 将你的临床经验与可靠的参考信息相结合
4. **明确表态**: 对于不可靠或不相关的参考信息，请明确指出并说明理由

**请提供**:
1. 基于临床经验的初步诊断分析
2. 对参考信息的批判性评估
3. 最终诊断建议及其理由
4. 建议的进一步检查或处理"""

        return full_prompt
    
    def test_different_prompt_styles(self, symptom: str, rag_results: List[Dict[str, Any]]) -> Dict[str, str]:
        """测试不同风格的prompt"""
        prompts = {}
        
        for style_name in self.self_reliant_prompts.keys():
            prompts[style_name] = self.generate_self_reliant_prompt(
                symptom, rag_results, style_name
            )
        
        return prompts
    
    def save_self_reliant_results(self, results: Dict[str, List[Dict[str, Any]]], 
                                output_file: str, prompt_style: str = 'clinical_first'):
        """保存自主判断增强的结果"""
        output_data = []
        
        for symptom, symptom_results in results.items():
            # 基础结果条目
            result_entry = {
                "symptom": symptom,
                "query": symptom,
                "rag_results": symptom_results,
                "database_type": self.rag_db_type,
                "database_description": "Uniform Random Unit Database (Self-Reliant)",
                "search_method": "SELF_RELIANT_enhanced_search",
                "enhancement_config": self.config,
                "prompt_style": prompt_style,
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
            
            # 添加自主判断prompt
            self_reliant_prompt = self.generate_self_reliant_prompt(symptom, symptom_results, prompt_style)
            result_entry['self_reliant_prompt'] = self_reliant_prompt
            
            # 添加所有风格的prompt用于对比
            all_prompts = self.test_different_prompt_styles(symptom, symptom_results)
            result_entry['all_prompt_styles'] = all_prompts
            
            output_data.append(result_entry)
        
        # 保存为JSONL格式
        with open(output_file, 'w', encoding='utf-8') as f:
            for entry in output_data:
                f.write(json.dumps(entry, ensure_ascii=False) + '\n')
        
        if self.debug:
            print(f"💾 自主判断增强结果已保存: {output_file}")

def main():
    """主函数 - 演示自主判断增强RAG"""
    import argparse
    
    parser = argparse.ArgumentParser(description="自主判断增强RAG适配器")
    parser.add_argument("--file", required=True, help="输入的诊断文件路径")
    parser.add_argument("--top_k", type=int, default=3, help="返回的top-k结果数量")
    parser.add_argument("--output_dir", required=True, help="输出目录")
    parser.add_argument("--rag_db_type", default="uniform", help="RAG数据库类型")
    parser.add_argument("--prompt_style", default="clinical_first", 
                       choices=['clinical_first', 'critical_thinking', 'evidence_based'],
                       help="Prompt风格选择")
    
    args = parser.parse_args()
    
    # 自主判断配置
    self_reliant_config = {
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
            'similarity_threshold': 0.3  # 降低阈值以获取更多结果进行评估
        },
        'result_enhancement': {
            'diversity_filtering': True,
            'semantic_reranking': True,
            'relevance_scoring': True,
            'max_results': args.top_k
        }
    }
    
    # 初始化自主判断适配器
    adapter = SelfReliantRAGAdapter(
        rag_db_type=args.rag_db_type,
        enhancement_config=self_reliant_config,
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
    
    # 执行自主判断增强检索
    results = adapter.search_symptoms(symptoms, args.top_k)
    
    # 保存结果
    input_filename = Path(args.file).stem
    output_filename = f"{input_filename}_SELF_RELIANT_{args.prompt_style}_ragoutcome_{args.rag_db_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jsonl"
    output_path = Path(args.output_dir) / output_filename
    
    adapter.save_self_reliant_results(results, str(output_path), args.prompt_style)
    
    print(f"✅ 自主判断增强检索完成！输出文件: {output_path}")
    
    # 演示不同风格的prompt
    if symptoms:
        sample_symptom = symptoms[0]
        sample_results = results.get(sample_symptom, [])
        
        print(f"\n🎯 演示症状 '{sample_symptom}' 的不同prompt风格:")
        print("="*80)
        
        all_prompts = adapter.test_different_prompt_styles(sample_symptom, sample_results)
        
        for style, prompt in all_prompts.items():
            print(f"\n📋 {style.upper()} 风格:")
            print("-" * 40)
            print(prompt[:800] + "..." if len(prompt) > 800 else prompt)
            print()

if __name__ == "__main__":
    main()
