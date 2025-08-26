#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能RAG评估器 - 让LLM选择性相信RAG

主要改进：
1. 多阶段推理：独立判断 → RAG参考 → 综合决策
2. RAG置信度评估：让LLM评估检索结果的可靠性
3. 动态权重调整：根据症状类型和置信度调整RAG权重
4. 保守策略：当RAG不确定时，优先使用基础判断
"""

import os
import sys
import json
import argparse
import logging
import shutil
from datetime import datetime
from typing import Dict, List, Any, Tuple
from pathlib import Path
import glob

# 获取项目根目录
sys.path.append(str(Path(__file__).resolve().parent.parent / "src"))

try:
    from config_loader import ConfigLoader
    from api_manager import APIManager
    from evaluator import Evaluator
    from utils.logger import ReportLogger
except ImportError as e:
    print("错误: 无法导入必要的模块。请确保此脚本位于项目根目录，并且'src'文件夹存在。")
    print(f"详细错误: {e}")
    sys.exit(1)


class SmartRAGEvaluator:
    """智能RAG评估器 - 支持选择性相信RAG"""
    
    def __init__(self, report_id: int, config_path: str = "config/config.yaml"):
        self.report_id = report_id
        self.config = ConfigLoader(config_path)
        self.api_manager = APIManager()
        self.evaluator = Evaluator()
        self.logger = ReportLogger()
        
        # 路径定义
        self.project_root = Path(__file__).resolve().parent.parent
        self.rag_output_dir = self.project_root / "final_result" / "rag_search_output"
        self.final_result_dir = self.project_root / "final_result"
        self.smart_results_dir = self.final_result_dir / "smart_rag_results"
        self.smart_comparisons_dir = self.final_result_dir / "smart_rag_comparisons"
        
        # 创建目录
        for dir_path in [self.smart_results_dir, self.smart_comparisons_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)
        
        print(f"🧠 智能RAG评估器启动")
        print(f"🎯 报告ID: {self.report_id}")
        print(f"🔍 RAG缓存目录: {self.rag_output_dir}")
        print(f"💾 智能结果目录: {self.smart_results_dir}")

    def find_latest_rag_cache(self) -> Path:
        """查找最新的RAG缓存文件"""
        search_pattern = f"report_{self.report_id}_ragoutcome:*.jsonl"
        files = glob.glob(str(self.rag_output_dir / search_pattern))
        
        if not files:
            raise FileNotFoundError(f"在目录 {self.rag_output_dir} 中未找到报告ID {self.report_id} 的RAG缓存文件。")
        
        latest_file = max(files, key=os.path.getctime)
        print(f"🔍 找到最新的RAG缓存文件: {Path(latest_file).name}")
        return Path(latest_file)

    def _build_baseline_prompt(self, symptom_text: str) -> str:
        """构建基础提示词（不含RAG）"""
        return f"""请根据以下症状描述，识别相关的器官和解剖位置：

症状：{symptom_text}

请严格按照JSON格式输出：
{{
    "organ": "主要相关器官",
    "anatomical_locations": ["解剖位置1", "解剖位置2", ...]
}}"""

    def _evaluate_rag_confidence(self, symptom_text: str, rag_results: Dict[str, Any]) -> Tuple[str, float]:
        """评估RAG结果的可靠性和置信度"""
        # 简单的置信度评估逻辑
        confidence_score = 0.5  # 基础分数
        confidence_reasoning = []
        
        if not rag_results:
            return "RAG未提供相关信息", 0.0
        
        # 统计RAG结果数量和质量
        total_refs = 0
        high_quality_refs = 0
        
        for key, value in rag_results.items():
            if isinstance(value, dict) and 'units' in value:
                for unit in value.get('units', []):
                    total_refs += 1
                    u_unit = unit.get('u_unit', {})
                    text = u_unit.get('d_diagnosis', '')
                    organ = u_unit.get('o_organ', {})
                    
                    # 质量评估
                    if len(text) > 20 and organ:  # 有一定长度的文本和器官信息
                        high_quality_refs += 1
                    
                    # 相关性评估（简单关键词匹配）
                    if any(word in text.lower() for word in symptom_text.lower().split()):
                        confidence_score += 0.1
        
        # 计算质量比例
        if total_refs > 0:
            quality_ratio = high_quality_refs / total_refs
            confidence_score += quality_ratio * 0.3
            confidence_reasoning.append(f"检索到{total_refs}条结果，其中{high_quality_refs}条高质量")
        else:
            confidence_reasoning.append("未检索到有效结果")
            
        # 限制置信度范围
        confidence_score = min(max(confidence_score, 0.0), 1.0)
        
        reasoning = "; ".join(confidence_reasoning)
        return reasoning, confidence_score

    def _build_smart_prompt(self, symptom_text: str, rag_results: Dict[str, Any], 
                           baseline_prediction: str = None) -> str:
        """构建智能RAG提示词"""
        
        # 评估RAG置信度
        rag_reasoning, rag_confidence = self._evaluate_rag_confidence(symptom_text, rag_results)
        
        # 构建RAG参考信息
        rag_refs = []
        if rag_results:
            for key, value in rag_results.items():
                if isinstance(value, dict) and 'units' in value:
                    for unit in value.get('units', []):
                        u_unit = unit.get('u_unit', {})
                        text = u_unit.get('d_diagnosis', '')
                        organ = u_unit.get('o_organ', {})
                        
                        if text and organ:
                            organ_info = ""
                            if isinstance(organ, dict):
                                name = organ.get('organName', '')
                                locs = organ.get('anatomicalLocations', [])
                                if name:
                                    organ_info = f" [器官: {name}"
                                    if locs:
                                        organ_info += f", 位置: {', '.join(locs)}"
                                    organ_info += "]"
                            
                            rag_refs.append(f"- {text}{organ_info}")
        
        # 构建提示词
        prompt_parts = [
            f"请分析以下症状，识别相关的器官和解剖位置：",
            f"",
            f"🔍 症状描述：{symptom_text}",
            f""
        ]
        
        # 添加基础判断（如果有）
        if baseline_prediction:
            prompt_parts.extend([
                f"📋 您的初步判断：",
                f"{baseline_prediction}",
                f""
            ])
        
        # 添加RAG参考信息
        if rag_refs:
            rag_block = "\n".join(rag_refs)
            prompt_parts.extend([
                f"📚 检索系统提供的参考信息（置信度: {rag_confidence:.1%}）：",
                f"💡 评估：{rag_reasoning}",
                f"",
                f"参考内容：",
                rag_block,
                f""
            ])
        else:
            prompt_parts.extend([
                f"📚 检索系统未找到相关参考信息",
                f""
            ])
        
        # 添加智能决策指令
        decision_strategy = ""
        if rag_confidence > 0.7:
            decision_strategy = "🎯 决策策略：检索信息置信度较高，建议重点参考但结合医学常识判断"
        elif rag_confidence > 0.4:
            decision_strategy = "⚖️ 决策策略：检索信息质量中等，建议谨慎参考，优先依据医学常识"
        else:
            decision_strategy = "🛡️ 决策策略：检索信息置信度较低，建议主要依据医学常识，仅将检索信息作为辅助参考"
        
        prompt_parts.extend([
            decision_strategy,
            f"",
            f"请综合以上信息，给出您的最终判断。要求：",
            f"1. 优先使用医学专业知识",
            f"2. 理性评估检索信息的可靠性",
            f"3. 当检索信息与医学常识冲突时，优先相信医学常识",
            f"4. 严格按照JSON格式输出",
            f"",
            f"输出格式：",
            f"{{",
            f'    "organ": "主要相关器官",',
            f'    "anatomical_locations": ["解剖位置1", "解剖位置2", ...],',
            f'    "confidence_used": {rag_confidence:.2f},',
            f'    "decision_rationale": "简述决策理由"',
            f"}}"
        ])
        
        return "\n".join(prompt_parts)

    def process_symptom_smart(self, symptom_text: str, rag_results: Dict[str, Any]) -> Dict[str, Any]:
        """智能处理单个症状"""
        print(f"\n--- 🧠 智能分析症状: {symptom_text[:50]}... ---")
        
        results = {
            'symptom_text': symptom_text,
            'rag_confidence': 0.0,
            'api_responses': {}
        }
        
        # 评估RAG置信度
        rag_reasoning, rag_confidence = self._evaluate_rag_confidence(symptom_text, rag_results)
        results['rag_confidence'] = rag_confidence
        results['rag_reasoning'] = rag_reasoning
        
        print(f"📊 RAG置信度: {rag_confidence:.1%} ({rag_reasoning})")
        
        # 构建智能提示词
        smart_prompt = self._build_smart_prompt(symptom_text, rag_results)
        
        # 调用API
        symptom_item = {
            'symptom_id': f'smart_{hash(symptom_text) % 10000}',
            'symptom_text': smart_prompt
        }
        
        # 加载系统提示词
        system_prompt_path = self.project_root / "prompt" / "system_prompt.txt"
        if system_prompt_path.exists():
            with open(system_prompt_path, 'r', encoding='utf-8') as f:
                system_prompt = f.read().strip()
        else:
            system_prompt = "你是一个医学专家，请根据症状识别相关的器官和解剖位置。"
        
        # 处理所有API
        api_responses = self.api_manager.process_symptom(symptom_item, system_prompt)
        
        for api_name, response in api_responses.items():
            if response and response.get('success'):
                # 解析响应，提取置信度信息
                parsed_data = response.get('parsed_data', {})
                confidence_used = parsed_data.get('confidence_used', rag_confidence)
                decision_rationale = parsed_data.get('decision_rationale', 'N/A')
                
                results['api_responses'][api_name] = {
                    'response': response.get('response', ''),
                    'parsed_data': parsed_data,
                    'organ_name': response.get('organ_name', ''),
                    'anatomical_locations': response.get('anatomical_locations', []),
                    'confidence_used': confidence_used,
                    'decision_rationale': decision_rationale,
                    'success': True
                }
                
                print(f"  {api_name}: 器官={response.get('organ_name', 'N/A')}, "
                      f"置信度使用={confidence_used:.2f}")
            else:
                results['api_responses'][api_name] = {
                    'success': False,
                    'error': response.get('error', 'Unknown error') if response else 'No response'
                }
        
        return results

    def run(self) -> str:
        """运行智能RAG评估"""
        try:
            # 查找RAG缓存
            rag_cache_file = self.find_latest_rag_cache()
            
            # 初始化API连接
            print(f"\n🔧 初始化API连接...")
            if not self.api_manager.initialize_clients(self.config.config):
                raise Exception("API客户端初始化失败")
            
            all_results = []
            
            # 处理RAG缓存文件
            print(f"\n🚀 开始智能RAG分析...")
            with open(rag_cache_file, 'r', encoding='utf-8') as f:
                for i, line in enumerate(f):
                    try:
                        data = json.loads(line)
                        symptom_text = data.get("query")
                        rag_s_block = data.get("s", {})
                        
                        if not symptom_text:
                            print(f"⚠️ 第 {i+1} 行缺少 'query' 字段，跳过")
                            continue
                        
                        # 智能处理症状
                        result = self.process_symptom_smart(symptom_text, rag_s_block)
                        all_results.append(result)
                        
                    except json.JSONDecodeError:
                        print(f"⚠️ 第 {i+1} 行不是有效的JSON格式，跳过")
                    except Exception as e:
                        print(f"❌ 处理第 {i+1} 行时出错: {e}")
            
            # 保存结果
            if all_results:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_filename = self.smart_results_dir / f"report_{self.report_id}_smart_rag_{timestamp}.json"
                
                final_result = {
                    'report_id': self.report_id,
                    'timestamp': datetime.now().isoformat(),
                    'total_symptoms': len(all_results),
                    'evaluation_type': 'smart_rag',
                    'symptoms': all_results
                }
                
                with open(output_filename, 'w', encoding='utf-8') as f:
                    json.dump(final_result, f, ensure_ascii=False, indent=2)
                
                print(f"\n🎉 ===== 智能RAG评估完成! =====")
                print(f"📊 成功处理了 {len(all_results)} 个症状")
                print(f"💾 结果已保存: {output_filename}")
                
                # 生成置信度统计
                self._generate_confidence_report(all_results, timestamp)
                
                return str(output_filename)
            else:
                print(f"❌ 没有成功处理任何症状")
                return ""
                
        except Exception as e:
            print(f"❌ 智能RAG评估失败: {e}")
            logging.error(f"智能RAG评估失败: {e}", exc_info=True)
            return ""

    def _generate_confidence_report(self, results: List[Dict], timestamp: str):
        """生成置信度分析报告"""
        report_path = self.smart_comparisons_dir / f"report_{self.report_id}_confidence_analysis_{timestamp}.txt"
        
        # 统计置信度分布
        confidence_levels = {'high': 0, 'medium': 0, 'low': 0}
        api_confidence_usage = {}
        
        for result in results:
            confidence = result.get('rag_confidence', 0)
            
            if confidence > 0.7:
                confidence_levels['high'] += 1
            elif confidence > 0.4:
                confidence_levels['medium'] += 1
            else:
                confidence_levels['low'] += 1
            
            # 统计API的置信度使用情况
            for api_name, api_result in result.get('api_responses', {}).items():
                if api_result.get('success'):
                    if api_name not in api_confidence_usage:
                        api_confidence_usage[api_name] = []
                    api_confidence_usage[api_name].append(api_result.get('confidence_used', 0))
        
        # 生成报告
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write("================================================================================\n")
            f.write(f"智能RAG置信度分析报告 - Report {self.report_id}\n")
            f.write("================================================================================\n")
            f.write(f"生成时间: {timestamp}\n")
            f.write(f"总症状数: {len(results)}\n\n")
            
            f.write("█ RAG置信度分布\n")
            f.write("------------------------------------------------------------\n")
            total = len(results)
            f.write(f"🔥 高置信度 (>70%): {confidence_levels['high']}/{total} ({confidence_levels['high']/total*100:.1f}%)\n")
            f.write(f"⚖️ 中等置信度 (40-70%): {confidence_levels['medium']}/{total} ({confidence_levels['medium']/total*100:.1f}%)\n")
            f.write(f"🛡️ 低置信度 (<40%): {confidence_levels['low']}/{total} ({confidence_levels['low']/total*100:.1f}%)\n\n")
            
            f.write("█ API置信度使用统计\n")
            f.write("------------------------------------------------------------\n")
            for api_name, confidences in api_confidence_usage.items():
                if confidences:
                    avg_confidence = sum(confidences) / len(confidences)
                    f.write(f"{api_name.upper()}:\n")
                    f.write(f"  平均置信度使用: {avg_confidence:.2f}\n")
                    f.write(f"  置信度范围: {min(confidences):.2f} - {max(confidences):.2f}\n\n")
            
            f.write("█ 详细症状分析\n")
            f.write("--------------------------------------------------------------------------------\n")
            for i, result in enumerate(results, 1):
                symptom = result['symptom_text']
                confidence = result['rag_confidence']
                reasoning = result.get('rag_reasoning', 'N/A')
                
                f.write(f"\n{i}. 【{symptom}】\n")
                f.write(f"   RAG置信度: {confidence:.1%}\n")
                f.write(f"   评估理由: {reasoning}\n")
                
                for api_name, api_result in result.get('api_responses', {}).items():
                    if api_result.get('success'):
                        used_conf = api_result.get('confidence_used', 0)
                        rationale = api_result.get('decision_rationale', 'N/A')
                        f.write(f"   {api_name}: 使用置信度={used_conf:.2f}, 决策理由={rationale}\n")
        
        print(f"📊 置信度分析报告已保存: {report_path}")


def main():
    parser = argparse.ArgumentParser(description="智能RAG评估器 - 让LLM选择性相信RAG")
    parser.add_argument("report_id", type=int, help="需要处理的报告ID")
    parser.add_argument("--config", default="config/config.yaml", help="配置文件路径")
    
    args = parser.parse_args()
    
    evaluator = SmartRAGEvaluator(args.report_id, args.config)
    evaluator.run()


if __name__ == "__main__":
    main()
