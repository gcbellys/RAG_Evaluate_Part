#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
优化的评估工作流程
真正利用prompt缓存，system prompt只上传一次，大幅减少token消耗
"""

import os
import sys
import json
import argparse
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any

# 添加src目录到Python路径
sys.path.append(str(Path(__file__).parent.parent / "src"))

from config_loader import ConfigLoader
from data_loader import DataLoader
from prompt_cached_api_manager import PromptCachedAPIManager
from evaluator import Evaluator


class OptimizedEvaluationWorkflow:
    """优化的评估工作流程 - 真正的prompt缓存"""
    
    def __init__(self, config_path: str = "config/config.yaml"):
        """初始化工作流程"""
        self.config = ConfigLoader(config_path)
        self.data_loader = DataLoader()
        self.cached_api_manager = PromptCachedAPIManager()
        self.evaluator = Evaluator()
        
        # 创建结果目录
        self.results_dir = Path("final_result/optimized_results")
        self.results_dir.mkdir(parents=True, exist_ok=True)
    
    def run_optimized_baseline_evaluation(self, report_id: str) -> str:
        """运行优化的baseline评估"""
        print(f"🎯 开始优化baseline评估 - 报告 {report_id}")
        print("💡 特点: System prompt只上传一次，后续复用")
        
        # 1. 初始化API客户端
        if not self.cached_api_manager.initialize_clients(self.config.config):
            raise Exception("API客户端初始化失败")
        
        # 2. 加载报告数据
        report_data = self.data_loader.load_report(report_id)
        if not report_data:
            raise Exception(f"无法加载报告 {report_id}")
        
        symptoms = report_data.get('symptoms', [])
        print(f"📄 已加载报告数据，包含 {len(symptoms)} 个症状")
        
        # 3. 加载并缓存系统提示词
        system_prompt_path = Path("prompt/system_prompt.txt")
        if system_prompt_path.exists():
            with open(system_prompt_path, 'r', encoding='utf-8') as f:
                system_prompt = f.read().strip()
        else:
            system_prompt = "You are a medical expert. Analyze symptoms and identify relevant organs."
        
        # 🔑 关键：一次性缓存system prompt到所有API
        self.cached_api_manager.cache_system_prompt(system_prompt)
        
        # 4. 批量处理症状 (只发送症状文本，复用缓存的system prompt)
        print(f"\n🚀 开始批量处理症状 (复用缓存的system prompt)...")
        api_results = self.cached_api_manager.process_symptoms_with_cached_prompt(symptoms)
        
        # 5. 构建和保存结果
        result_file = self._save_optimized_results(report_id, api_results, symptoms, "baseline")
        
        # 6. 显示优化统计
        cache_stats = self.cached_api_manager.get_cache_statistics()
        print(f"\n💰 优化统计:")
        print(f"   System prompt缓存: {'✅' if cache_stats['system_prompt_cached'] else '❌'}")
        print(f"   总节省tokens: {cache_stats['total_savings']:,}")
        
        # 7. 计算理论节省
        estimated_system_tokens = len(system_prompt) // 4
        theoretical_savings = estimated_system_tokens * len(symptoms) * len(self.cached_api_manager.cached_clients) - estimated_system_tokens * len(self.cached_api_manager.cached_clients)
        print(f"   理论节省tokens: {theoretical_savings:,}")
        print(f"   节省率: {theoretical_savings / (theoretical_savings + cache_stats['total_savings']) * 100:.1f}%")
        
        print(f"\n✅ 优化baseline评估完成")
        print(f"💾 结果已保存: {result_file}")
        
        return result_file
    
    def run_optimized_rag_evaluation(self, report_id: str, rag_data: List[Dict[str, Any]]) -> str:
        """运行优化的RAG增强评估"""
        print(f"🎯 开始优化RAG增强评估 - 报告 {report_id}")
        print("💡 特点: System prompt复用，只发送症状+RAG上下文")
        
        # 1. 确保system prompt已缓存
        if not self.cached_api_manager.cached_clients:
            raise Exception("请先运行baseline评估以缓存system prompt")
        
        # 检查是否已缓存system prompt
        cached_count = sum(1 for client in self.cached_api_manager.cached_clients.values() 
                          if client.cached_system_prompt is not None)
        
        if cached_count == 0:
            print("⚠️  System prompt未缓存，重新缓存...")
            system_prompt_path = Path("prompt/system_prompt.txt")
            if system_prompt_path.exists():
                with open(system_prompt_path, 'r', encoding='utf-8') as f:
                    system_prompt = f.read().strip()
                self.cached_api_manager.cache_system_prompt(system_prompt)
        else:
            print(f"✅ System prompt已缓存到 {cached_count} 个API")
        
        # 2. 处理RAG增强症状
        print(f"\n🔍 处理 {len(rag_data)} 个RAG增强症状...")
        api_results = self.cached_api_manager.process_rag_symptoms_with_cached_prompt(rag_data)
        
        # 3. 保存结果
        result_file = self._save_optimized_results(report_id, api_results, rag_data, "rag")
        
        # 4. 显示统计
        cache_stats = self.cached_api_manager.get_cache_statistics()
        print(f"\n💰 RAG优化统计:")
        print(f"   累计节省tokens: {cache_stats['total_savings']:,}")
        
        print(f"\n✅ 优化RAG评估完成")
        print(f"💾 结果已保存: {result_file}")
        
        return result_file
    
    def _save_optimized_results(self, report_id: str, api_results: Dict[str, Dict[str, Any]], 
                               symptoms_data: List[Dict[str, Any]], eval_type: str) -> str:
        """保存优化的评估结果"""
        
        report_results = {
            'report_id': report_id,
            'evaluation_type': eval_type,
            'timestamp': datetime.now().isoformat(),
            'symptoms': [],
            'token_summary': {
                'total_tokens': 0,
                'total_prompt_tokens': 0,
                'total_completion_tokens': 0,
                'api_breakdown': {}
            },
            'optimization_stats': self.cached_api_manager.get_cache_statistics()
        }
        
        # 处理每个症状的结果
        for symptom_item in symptoms_data:
            symptom_text = symptom_item.get('symptom_text', '')
            symptom_id = symptom_item.get('symptom_id', 'unknown')
            expected_organs = symptom_item.get('expected_results', [])
            
            if symptom_text not in api_results:
                continue
            
            symptom_data = {
                'symptom_id': symptom_id,
                'diagnosis': symptom_text,
                'expected_organs': expected_organs,
                'api_responses': {}
            }
            
            # 如果是RAG类型，添加RAG上下文信息
            if eval_type == "rag":
                symptom_data['rag_context'] = symptom_item.get('rag_context', '')
            
            api_responses = api_results[symptom_text]
            
            # 处理每个API的响应
            for api_name, response in api_responses.items():
                api_response_data = {
                    'response': response.get('response', ''),
                    'parsed_data': response.get('parsed_data', {}),
                    'organ_name': response.get('organ_name', ''),
                    'anatomical_locations': response.get('anatomical_locations', []),
                    'success': response.get('success', False),
                    'model': response.get('model', ''),
                    'usage': response.get('usage', {}),
                    'cache_info': response.get('cache_info', {}),
                    'error': response.get('error', '')
                }
                
                # 统计token使用
                if 'usage' in response and response['usage']:
                    usage = response['usage']
                    total_tokens = usage.get('total_tokens', 0)
                    prompt_tokens = usage.get('prompt_tokens', 0)
                    completion_tokens = usage.get('completion_tokens', 0)
                    
                    # 更新总计
                    report_results['token_summary']['total_tokens'] += total_tokens
                    report_results['token_summary']['total_prompt_tokens'] += prompt_tokens
                    report_results['token_summary']['total_completion_tokens'] += completion_tokens
                    
                    # 更新API分解
                    if api_name not in report_results['token_summary']['api_breakdown']:
                        report_results['token_summary']['api_breakdown'][api_name] = {
                            'total_tokens': 0,
                            'prompt_tokens': 0,
                            'completion_tokens': 0,
                            'calls': 0,
                            'cache_savings': 0
                        }
                    
                    api_breakdown = report_results['token_summary']['api_breakdown'][api_name]
                    api_breakdown['total_tokens'] += total_tokens
                    api_breakdown['prompt_tokens'] += prompt_tokens
                    api_breakdown['completion_tokens'] += completion_tokens
                    api_breakdown['calls'] += 1
                    
                    # 添加缓存节省信息
                    cache_info = response.get('cache_info', {})
                    api_breakdown['cache_savings'] += cache_info.get('estimated_savings', 0)
                
                # 评估API响应
                if response.get('success') and response.get('parsed_data'):
                    evaluation = self.evaluator.evaluate_single_response(
                        api_response=response,
                        expected_results=expected_organs
                    )
                    api_response_data['evaluation'] = evaluation
                else:
                    api_response_data['evaluation'] = {
                        'overall_score': 0.0,
                        'precision': 0.0,
                        'recall': 0.0,
                        'overgeneration_penalty': 0.0,
                        'detailed_analysis': 'API调用失败或无有效数据'
                    }
                
                symptom_data['api_responses'][api_name] = api_response_data
            
            report_results['symptoms'].append(symptom_data)
        
        # 保存结果
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        result_filename = self.results_dir / f"optimized_{eval_type}_{report_id}_{timestamp}.json"
        
        with open(result_filename, 'w', encoding='utf-8') as f:
            json.dump(report_results, f, ensure_ascii=False, indent=2)
        
        # 显示token统计
        self._print_token_summary(report_results)
        
        return str(result_filename)
    
    def _print_token_summary(self, report_results: Dict[str, Any]):
        """显示token使用摘要"""
        token_summary = report_results.get('token_summary', {})
        total_tokens = token_summary.get('total_tokens', 0)
        
        print(f"\n📊 Token使用统计:")
        print(f"   总计: {total_tokens:,} tokens")
        
        for api, stats in token_summary.get('api_breakdown', {}).items():
            if stats['calls'] > 0:
                avg_tokens = stats['total_tokens'] / stats['calls']
                cache_savings = stats.get('cache_savings', 0)
                savings_info = f" (缓存节省{cache_savings:,})" if cache_savings > 0 else ""
                print(f"   {api.upper():12}: {stats['total_tokens']:,} tokens ({stats['calls']}次调用, 平均{avg_tokens:.0f}){savings_info}")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="优化的评估工作流程")
    parser.add_argument("mode", choices=["baseline", "rag"], help="评估模式")
    parser.add_argument("report_id", help="报告ID")
    parser.add_argument("--config", default="config/config.yaml", help="配置文件路径")
    
    args = parser.parse_args()
    
    print("=" * 80)
    print("🎯 优化评估工作流程 - Prompt缓存版")
    print("=" * 80)
    print(f"📋 模式: {args.mode}")
    print(f"📋 报告ID: {args.report_id}")
    print(f"⚙️  配置文件: {args.config}")
    
    try:
        workflow = OptimizedEvaluationWorkflow(args.config)
        
        if args.mode == "baseline":
            result_file = workflow.run_optimized_baseline_evaluation(args.report_id)
        else:
            # RAG模式需要先有RAG数据
            print("⚠️  RAG模式需要提供RAG数据，此处为演示")
            # 这里应该加载RAG数据
            rag_data = []  # 实际应该从RAG缓存文件加载
            result_file = workflow.run_optimized_rag_evaluation(args.report_id, rag_data)
        
        print("\n" + "=" * 80)
        print("✅ 优化评估成功完成!")
        print(f"📁 结果文件: {result_file}")
        print("💡 关键优化: System prompt只上传一次，大幅减少token消耗")
        print("=" * 80)
        
    except Exception as e:
        print("\n" + "=" * 80)
        print(f"❌ 评估失败: {e}")
        print("=" * 80)
        sys.exit(1)


if __name__ == "__main__":
    main()
