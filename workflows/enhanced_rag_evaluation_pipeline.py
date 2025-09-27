·#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
增强版RAG评估流程
集成了置信度感知搜索和自主判断增强prompt的完整测试流程
"""

import os
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any

# 添加脚本路径
sys.path.append(str(Path(__file__).parent.parent / "scripts"))
from confidence_aware_rag_adapter import ConfidenceAwareRAGAdapter

class EnhancedRAGEvaluationPipeline:
    """增强版RAG评估流程"""
    
    def __init__(self, rag_db_type: str = 'uniform', debug: bool = True):
        self.rag_db_type = rag_db_type
        self.debug = debug
        
        # 初始化置信度感知适配器
        self.rag_adapter = ConfidenceAwareRAGAdapter(
            rag_db_type=rag_db_type,
            debug=debug
        )
        
        # 加载增强prompt
        self.enhanced_prompt = self._load_enhanced_prompt()
        
        if debug:
            print("🚀 增强版RAG评估流程初始化完成")
    
    def _load_enhanced_prompt(self) -> str:
        """加载增强版prompt模板"""
        prompt_file = Path(__file__).parent.parent / "prompt" / "rag_enhanced_prompt.txt"
        with open(prompt_file, 'r', encoding='utf-8') as f:
            return f.read()
    
    def _format_rag_for_enhanced_prompt(self, symptom: str, rag_results: List[Dict[str, Any]]) -> str:
        """将RAG结果格式化为增强prompt所需格式"""
        
        if not rag_results:
            return f"""
**Patient Symptom**: {symptom}

**Search Results**: No relevant results found in the medical knowledge base.
⚠️ **Guidance**: Please base your assessment entirely on your clinical expertise.
"""
        
        # 按置信度分组
        confidence_groups = {
            'high': [],      # >0.85
            'medium': [],    # 0.65-0.85
            'low': [],       # 0.45-0.65
            'very_low': []   # <0.45
        }
        
        for result in rag_results:
            similarity = result.get('cosine_similarity', 0)
            if similarity >= 0.85:
                confidence_groups['high'].append(result)
            elif similarity >= 0.65:
                confidence_groups['medium'].append(result)
            elif similarity >= 0.45:
                confidence_groups['low'].append(result)
            else:
                confidence_groups['very_low'].append(result)
        
        formatted_output = f"""
**Patient Symptom**: {symptom}

**Search Results from Medical Knowledge Base**:
"""
        
        # 高置信度结果
        if confidence_groups['high']:
            formatted_output += f"""
🎯 **HIGH CONFIDENCE RESULTS (Similarity >0.85)** - Consider as strong supporting evidence if medically sound:
"""
            for i, result in enumerate(confidence_groups['high'], 1):
                formatted_output += self._format_single_result(result, i)
        
        # 中等置信度结果
        if confidence_groups['medium']:
            formatted_output += f"""
📊 **MEDIUM CONFIDENCE RESULTS (Similarity 0.65-0.85)** - Use cautiously, verify against clinical knowledge:
"""
            for i, result in enumerate(confidence_groups['medium'], 1):
                formatted_output += self._format_single_result(result, i)
        
        # 低置信度结果
        if confidence_groups['low']:
            formatted_output += f"""
⚠️ **LOW CONFIDENCE RESULTS (Similarity 0.45-0.65)** - Treat with skepticism, require strong medical justification:
"""
            for i, result in enumerate(confidence_groups['low'], 1):
                formatted_output += self._format_single_result(result, i, brief=True)
        
        # 极低置信度结果
        if confidence_groups['very_low']:
            formatted_output += f"""
❌ **VERY LOW CONFIDENCE RESULTS (Similarity <0.45)** - Generally ignore unless exceptionally relevant:
{len(confidence_groups['very_low'])} results with very low similarity scores.
"""
        
        # 添加统计信息
        formatted_output += f"""

**Confidence Distribution Summary**:
- 🎯 High Confidence: {len(confidence_groups['high'])} results
- 📊 Medium Confidence: {len(confidence_groups['medium'])} results  
- ⚠️ Low Confidence: {len(confidence_groups['low'])} results
- ❌ Very Low Confidence: {len(confidence_groups['very_low'])} results

**Evaluation Guidance**:
- Focus on high confidence results that align with your clinical knowledge
- Critically assess medium confidence results for medical accuracy
- Generally ignore low and very low confidence results unless they provide unique insights
- Remember: Your clinical expertise is the primary foundation for diagnosis
"""
        
        return formatted_output
    
    def _format_single_result(self, result: Dict[str, Any], index: int, brief: bool = False) -> str:
        """格式化单个RAG结果"""
        similarity = result.get('cosine_similarity', 0)
        symptom_text = result.get('symptom', '')
        metadata = result.get('metadata', {})
        
        # 提取诊断和器官信息
        diagnosis = "Unknown"
        organ = "Unknown"
        locations = []
        medical_inference = ""
        
        if isinstance(metadata, dict):
            u_unit_set = metadata.get('U_unit_set', [])
            if u_unit_set and isinstance(u_unit_set, list):
                u_unit = u_unit_set[0].get('u_unit', {})
                diagnosis = u_unit.get('d_diagnosis', 'Unknown')
                organ_info = u_unit.get('o_organ', {})
                organ = organ_info.get('organName', 'Unknown')
                locations = organ_info.get('anatomicalLocations', [])
                
                # 提取医学推理
                textual_basis = u_unit.get('b_textual_basis', {})
                medical_inference = textual_basis.get('medicalInference', '')
        
        if brief:
            return f"""
Result {index}: (Similarity: {similarity:.3f})
- Symptom: "{symptom_text}"
- Diagnosis: {diagnosis}
- Organ: {organ}
"""
        else:
            return f"""
Result {index}: (Similarity: {similarity:.3f})
- **Symptom Description**: "{symptom_text}"
- **Related Diagnosis**: {diagnosis}
- **Primary Organ**: {organ}
- **Anatomical Locations**: {', '.join(locations[:4]) if locations else 'Not specified'}
- **Medical Reasoning**: {medical_inference[:200] + '...' if len(medical_inference) > 200 else medical_inference}
"""
    
    def create_enhanced_prompt(self, symptom: str, rag_results: List[Dict[str, Any]]) -> str:
        """创建完整的增强prompt"""
        
        formatted_rag = self._format_rag_for_enhanced_prompt(symptom, rag_results)
        
        complete_prompt = f"""{self.enhanced_prompt}

{formatted_rag}

**CRITICAL REMINDER**: 
1. First conduct your independent clinical analysis based on the symptom
2. Then critically evaluate each search result for medical accuracy and relevance
3. Only incorporate search results that genuinely enhance your clinical assessment
4. Be explicit about which results you trust, reject, and why
5. Indicate clearly how much the search results influenced your final decision

Please provide your assessment in the required JSON format.
"""
        
        return complete_prompt
    
    def run_enhanced_evaluation(self, symptoms: List[str], top_k: int = 3) -> Dict[str, Any]:
        """运行增强版评估"""
        
        if self.debug:
            print(f"🔍 开始增强版RAG评估，处理 {len(symptoms)} 个症状")
        
        # 1. 执行置信度感知RAG检索
        rag_results = self.rag_adapter.search_symptoms(symptoms, top_k)
        
        # 2. 为每个症状创建增强prompt
        enhanced_prompts = {}
        evaluation_data = {}
        
        for symptom in symptoms:
            symptom_rag_results = rag_results.get(symptom, [])
            
            # 创建增强prompt
            enhanced_prompt = self.create_enhanced_prompt(symptom, symptom_rag_results)
            enhanced_prompts[symptom] = enhanced_prompt
            
            # 收集评估数据
            evaluation_data[symptom] = {
                'rag_results': symptom_rag_results,
                'enhanced_prompt': enhanced_prompt,
                'confidence_analysis': self._analyze_confidence_distribution(symptom_rag_results),
                'prompt_length': len(enhanced_prompt),
                'timestamp': datetime.now().isoformat()
            }
            
            if self.debug:
                print(f"✅ 症状 '{symptom}' 增强prompt已生成 (长度: {len(enhanced_prompt)} 字符)")
        
        return {
            'evaluation_data': evaluation_data,
            'enhanced_prompts': enhanced_prompts,
            'summary': self._generate_evaluation_summary(evaluation_data)
        }
    
    def _analyze_confidence_distribution(self, rag_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """分析置信度分布"""
        if not rag_results:
            return {
                'total_results': 0,
                'high_confidence': 0,
                'medium_confidence': 0,
                'low_confidence': 0,
                'very_low_confidence': 0,
                'avg_similarity': 0,
                'max_similarity': 0,
                'min_similarity': 0
            }
        
        similarities = [r.get('cosine_similarity', 0) for r in rag_results]
        
        high_conf = sum(1 for s in similarities if s >= 0.85)
        medium_conf = sum(1 for s in similarities if 0.65 <= s < 0.85)
        low_conf = sum(1 for s in similarities if 0.45 <= s < 0.65)
        very_low_conf = sum(1 for s in similarities if s < 0.45)
        
        return {
            'total_results': len(rag_results),
            'high_confidence': high_conf,
            'medium_confidence': medium_conf,
            'low_confidence': low_conf,
            'very_low_confidence': very_low_conf,
            'avg_similarity': sum(similarities) / len(similarities),
            'max_similarity': max(similarities),
            'min_similarity': min(similarities)
        }
    
    def _generate_evaluation_summary(self, evaluation_data: Dict[str, Any]) -> Dict[str, Any]:
        """生成评估总结"""
        total_symptoms = len(evaluation_data)
        total_results = sum(data['confidence_analysis']['total_results'] for data in evaluation_data.values())
        
        # 汇总置信度分布
        total_high = sum(data['confidence_analysis']['high_confidence'] for data in evaluation_data.values())
        total_medium = sum(data['confidence_analysis']['medium_confidence'] for data in evaluation_data.values())
        total_low = sum(data['confidence_analysis']['low_confidence'] for data in evaluation_data.values())
        total_very_low = sum(data['confidence_analysis']['very_low_confidence'] for data in evaluation_data.values())
        
        # 计算平均prompt长度
        avg_prompt_length = sum(data['prompt_length'] for data in evaluation_data.values()) / total_symptoms if total_symptoms > 0 else 0
        
        return {
            'total_symptoms': total_symptoms,
            'total_rag_results': total_results,
            'confidence_distribution': {
                'high': total_high,
                'medium': total_medium,
                'low': total_low,
                'very_low': total_very_low
            },
            'avg_prompt_length': avg_prompt_length,
            'evaluation_quality': self._assess_evaluation_quality(total_high, total_medium, total_low, total_very_low)
        }
    
    def _assess_evaluation_quality(self, high: int, medium: int, low: int, very_low: int) -> str:
        """评估整体质量"""
        total = high + medium + low + very_low
        if total == 0:
            return "No RAG results available"
        
        high_ratio = high / total
        reliable_ratio = (high + medium) / total
        
        if high_ratio >= 0.5:
            return "Excellent - Many high confidence results"
        elif reliable_ratio >= 0.6:
            return "Good - Sufficient reliable results"
        elif reliable_ratio >= 0.3:
            return "Fair - Some useful results, use cautiously"
        else:
            return "Poor - Rely primarily on clinical expertise"
    
    def save_evaluation_results(self, results: Dict[str, Any], output_file: str):
        """保存评估结果"""
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        
        if self.debug:
            print(f"💾 增强版评估结果已保存: {output_file}")
    
    def save_prompts_for_testing(self, enhanced_prompts: Dict[str, str], output_dir: str):
        """保存prompt文件用于LLM测试"""
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)
        
        for symptom, prompt in enhanced_prompts.items():
            safe_filename = symptom.replace(' ', '_').replace('/', '_')[:50]
            prompt_file = output_path / f"enhanced_prompt_{safe_filename}.txt"
            
            with open(prompt_file, 'w', encoding='utf-8') as f:
                f.write(prompt)
            
            if self.debug:
                print(f"📄 Prompt已保存: {prompt_file}")

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="增强版RAG评估流程")
    parser.add_argument("--file", required=True, help="输入的诊断文件路径")
    parser.add_argument("--top_k", type=int, default=3, help="RAG检索的top-k数量")
    parser.add_argument("--output_dir", default="results/enhanced_evaluation", help="输出目录")
    parser.add_argument("--rag_db_type", default="uniform", help="RAG数据库类型")
    
    args = parser.parse_args()
    
    # 创建输出目录
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 初始化评估流程
    pipeline = EnhancedRAGEvaluationPipeline(
        rag_db_type=args.rag_db_type,
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
    
    # 运行增强版评估
    results = pipeline.run_enhanced_evaluation(symptoms, args.top_k)
    
    # 保存结果
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = output_dir / f"enhanced_evaluation_results_{timestamp}.json"
    pipeline.save_evaluation_results(results, str(results_file))
    
    # 保存prompt文件
    prompts_dir = output_dir / f"prompts_{timestamp}"
    pipeline.save_prompts_for_testing(results['enhanced_prompts'], str(prompts_dir))
    
    # 显示总结
    summary = results['summary']
    print(f"\n📊 评估总结:")
    print(f"   症状数量: {summary['total_symptoms']}")
    print(f"   RAG结果总数: {summary['total_rag_results']}")
    print(f"   置信度分布: 高={summary['confidence_distribution']['high']}, 中={summary['confidence_distribution']['medium']}, 低={summary['confidence_distribution']['low']}, 极低={summary['confidence_distribution']['very_low']}")
    print(f"   平均prompt长度: {summary['avg_prompt_length']:.0f} 字符")
    print(f"   评估质量: {summary['evaluation_quality']}")
    
    print(f"\n✅ 增强版RAG评估完成！")
    print(f"📁 结果文件: {results_file}")
    print(f"📄 Prompt文件: {prompts_dir}")
    print(f"🧪 可以使用生成的prompt文件进行LLM测试")

if __name__ == "__main__":
    main()
