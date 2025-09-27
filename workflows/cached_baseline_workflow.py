#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
使用缓存API管理器的优化baseline评估工作流程
通过会话复用和缓存大幅减少token消耗
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
from cached_api_manager import CachedAPIManager
from evaluator import Evaluator


class CachedBaselineWorkflow:
    """使用缓存的baseline评估工作流程"""
    
    def __init__(self, config_path: str = "config/config.yaml"):
        """初始化工作流程"""
        self.config = ConfigLoader(config_path)
        self.data_loader = DataLoader()
        self.cached_api_manager = CachedAPIManager(cache_ttl=3600)  # 1小时缓存
        self.evaluator = Evaluator()
        
        # 从配置文件获取输出路径
        output_base = self.config.get_path('output_results')
        self.output_base_dir = Path(output_base)
        
        # 创建结果目录
        self.results_dir = self.output_base_dir / "baseline_results"
        self.results_dir.mkdir(parents=True, exist_ok=True)
    
    def run_cached_baseline_evaluation(self, report_id: str) -> str:
        """运行缓存优化的baseline评估"""
        print(f"🎯 开始缓存优化的baseline评估 - 报告 {report_id}")
        
        # 1. 初始化API客户端
        if not self.cached_api_manager.initialize_clients(self.config.config):
            raise Exception("API客户端初始化失败")
        
        # 2. 加载报告数据
        report_data = self.data_loader.load_report(report_id)
        if not report_data:
            raise Exception(f"无法加载报告 {report_id}")
        
        symptoms = report_data.get('symptoms', [])
        print(f"📄 已加载报告数据，包含 {len(symptoms)} 个症状")
        
        # 3. 加载系统提示词
        system_prompt_path = Path("prompt/system_prompt.txt")
        if system_prompt_path.exists():
            with open(system_prompt_path, 'r', encoding='utf-8') as f:
                system_prompt = f.read().strip()
        else:
            system_prompt = "You are a medical expert. Analyze symptoms and identify relevant organs."
        
        print(f"📝 系统提示词长度: {len(system_prompt)} 字符 (~{len(system_prompt)//4:,} tokens)")
        
        # 4. 批量处理症状 (使用缓存和会话复用)
        print(f"\n🚀 开始批量处理症状...")
        api_results = self.cached_api_manager.process_symptoms_batch(symptoms, system_prompt)
        
        # 5. 构建报告结果
        report_results = {
            'report_id': report_id,
            'timestamp': datetime.now().isoformat(),
            'symptoms': [],
            'token_summary': {
                'total_tokens': 0,
                'total_prompt_tokens': 0,
                'total_completion_tokens': 0,
                'api_breakdown': {}
            },
            'optimization_stats': {
                'cache_stats': self.cached_api_manager.get_cache_stats(),
                'session_stats': {}
            }
        }
        
        # 6. 处理每个症状的结果
        for symptom_item in symptoms:
            symptom_text = symptom_item.get('symptom_text', '')
            symptom_id = symptom_item.get('symptom_id', 'unknown')
            expected_organs = symptom_item.get('expected_results', [])
            
            if symptom_text not in api_results:
                print(f"⚠️  症状 {symptom_text} 没有API结果")
                continue
            
            symptom_data = {
                'symptom_id': symptom_id,
                'diagnosis': symptom_text,
                'expected_organs': expected_organs,
                'api_responses': {}
            }
            
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
                            'calls': 0
                        }
                    
                    api_breakdown = report_results['token_summary']['api_breakdown'][api_name]
                    api_breakdown['total_tokens'] += total_tokens
                    api_breakdown['prompt_tokens'] += prompt_tokens
                    api_breakdown['completion_tokens'] += completion_tokens
                    api_breakdown['calls'] += 1
                
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
        
        # 7. 收集会话统计
        for provider, session in self.cached_api_manager.sessions.items():
            session_stats = session.get_token_savings()
            report_results['optimization_stats']['session_stats'][provider] = session_stats
        
        # 8. 保存结果
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        result_filename = self.results_dir / f"cached_baseline_{report_id}_{timestamp}.json"
        
        with open(result_filename, 'w', encoding='utf-8') as f:
            json.dump(report_results, f, ensure_ascii=False, indent=2)
        
        # 9. 显示统计信息
        self._print_optimization_summary(report_results)
        
        print(f"\n✅ 缓存优化baseline评估完成")
        print(f"💾 结果已保存: {result_filename}")
        
        return str(result_filename)
    
    def _print_optimization_summary(self, report_results: Dict[str, Any]):
        """显示优化统计摘要"""
        token_summary = report_results.get('token_summary', {})
        total_tokens = token_summary.get('total_tokens', 0)
        
        print(f"\n📊 Token使用统计:")
        print(f"   总计: {total_tokens:,} tokens")
        
        for api, stats in token_summary.get('api_breakdown', {}).items():
            if stats['calls'] > 0:
                avg_tokens = stats['total_tokens'] / stats['calls']
                print(f"   {api.upper():12}: {stats['total_tokens']:,} tokens ({stats['calls']}次调用, 平均{avg_tokens:.0f})")
        
        # 显示优化统计
        optimization_stats = report_results.get('optimization_stats', {})
        
        # 缓存统计
        cache_stats = optimization_stats.get('cache_stats', {})
        if cache_stats.get('tokens_saved', 0) > 0:
            print(f"\n💾 缓存统计:")
            print(f"   缓存条目: {cache_stats['valid_cached']}/{cache_stats['total_cached']}")
            print(f"   节省tokens: {cache_stats['tokens_saved']:,}")
        
        # 会话统计
        session_stats = optimization_stats.get('session_stats', {})
        total_session_saved = 0
        
        if session_stats:
            print(f"\n🔄 会话复用统计:")
            for provider, stats in session_stats.items():
                saved = stats.get('tokens_saved', 0)
                total_session_saved += saved
                if saved > 0:
                    print(f"   {provider.upper():12}: 节省 {saved:,} tokens")
        
        # 总节省
        total_saved = cache_stats.get('tokens_saved', 0) + total_session_saved
        if total_saved > 0:
            print(f"\n💰 总计优化节省: {total_saved:,} tokens")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="缓存优化的baseline评估")
    parser.add_argument("report_id", help="报告ID")
    parser.add_argument("--config", default="config/config.yaml", help="配置文件路径")
    
    args = parser.parse_args()
    
    print("=" * 80)
    print("🎯 缓存优化Baseline评估")
    print("=" * 80)
    print(f"📋 报告ID: {args.report_id}")
    print(f"⚙️  配置文件: {args.config}")
    
    try:
        workflow = CachedBaselineWorkflow(args.config)
        result_file = workflow.run_cached_baseline_evaluation(args.report_id)
        
        print("\n" + "=" * 80)
        print("✅ 评估成功完成!")
        print(f"📁 结果文件: {result_file}")
        print("=" * 80)
        
    except Exception as e:
        print("\n" + "=" * 80)
        print(f"❌ 评估失败: {e}")
        print("=" * 80)
        sys.exit(1)


if __name__ == "__main__":
    main()
