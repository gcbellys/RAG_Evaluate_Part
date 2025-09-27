#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批处理模式的对比分析工作流
生成基础评估与RAG增强评估的详细对比分析
"""

import json
import sys
import os
import argparse
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Tuple

# 添加src目录到Python路径
sys.path.append(str(Path(__file__).resolve().parent.parent / "src"))

try:
    from config_loader import ConfigLoader
    from evaluator import Evaluator
except ImportError as e:
    print(f"错误: 无法导入必要的模块: {e}")
    sys.exit(1)


class BatchComparisonWorkflow:
    """批处理模式的对比分析工作流"""
    
    def __init__(self, config_path: str = "config/config_openai.yaml"):
        self.config = ConfigLoader(config_path)
        self.evaluator = Evaluator()
        
        # 获取输出路径
        output_base = self.config.get_path('output_results')
        self.output_base_dir = Path(output_base)
        
        # 设置目录路径
        self.baseline_dir = self.output_base_dir / "baseline_results_batch"
        self.rag_dir = self.output_base_dir / "rerun_with_rag_batch"
        self.comparison_dir = self.output_base_dir / "rerun_comparisons"
        
        # 创建对比分析目录
        self.comparison_dir.mkdir(parents=True, exist_ok=True)
    
    def find_batch_files(self, report_id: str) -> Tuple[str, str]:
        """查找批处理模式的基础和RAG文件"""
        # 查找基础结果文件
        baseline_files = list(self.baseline_dir.glob(f"baseline_batch_report_*{report_id}*.json"))
        baseline_file = str(max(baseline_files, key=os.path.getctime)) if baseline_files else ""
        
        # 查找RAG增强结果文件
        rag_files = list(self.rag_dir.glob(f"rag_enhanced_batch_report_{report_id}_*.json"))
        rag_file = str(max(rag_files, key=os.path.getctime)) if rag_files else ""
        
        return baseline_file, rag_file
    
    def load_json_file(self, file_path: str) -> Dict[str, Any]:
        """加载JSON文件"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"⚠️  无法加载文件 {file_path}: {e}")
            return {}
    
    def compare_symptom_results(self, baseline_symptom: Dict, rag_symptom: Dict) -> Dict[str, Any]:
        """对比单个症状的结果"""
        comparison = {
            'symptom_id': baseline_symptom.get('symptom_id', ''),
            'symptom_text': baseline_symptom.get('symptom_text', ''),
            'expected_results': baseline_symptom.get('expected_results', []),
            'api_comparisons': {}
        }
        
        # 获取所有API
        baseline_apis = set(baseline_symptom.get('api_responses', {}).keys())
        rag_apis = set(rag_symptom.get('api_responses', {}).keys())
        all_apis = baseline_apis | rag_apis
        
        for api_name in all_apis:
            baseline_api = baseline_symptom.get('api_responses', {}).get(api_name, {})
            rag_api = rag_symptom.get('api_responses', {}).get(api_name, {})
            
            # 评估基础结果
            baseline_eval = self.evaluator.evaluate_single_response(
                baseline_api, 
                baseline_symptom.get('expected_results', [])
            ) if baseline_api else {'overall_score': 0.0, 'precision': 0.0, 'recall': 0.0}
            
            # 评估RAG增强结果
            rag_eval = self.evaluator.evaluate_single_response(
                rag_api,
                rag_symptom.get('expected_results', [])
            ) if rag_api else {'overall_score': 0.0, 'precision': 0.0, 'recall': 0.0}
            
            # 计算改善
            improvement = {
                'overall_score': rag_eval['overall_score'] - baseline_eval['overall_score'],
                'precision': rag_eval['precision'] - baseline_eval['precision'],
                'recall': rag_eval['recall'] - baseline_eval['recall']
            }
            
            # Token使用对比
            baseline_tokens = baseline_api.get('usage', {}).get('total_tokens', 0)
            rag_tokens = rag_api.get('usage', {}).get('total_tokens', 0)
            cached_tokens = rag_api.get('usage', {}).get('prompt_tokens_details', {}).get('cached_tokens', 0)
            
            comparison['api_comparisons'][api_name] = {
                'baseline_evaluation': baseline_eval,
                'rag_evaluation': rag_eval,
                'improvement': improvement,
                'token_usage': {
                    'baseline_tokens': baseline_tokens,
                    'rag_tokens': rag_tokens,
                    'token_difference': rag_tokens - baseline_tokens,
                    'cached_tokens': cached_tokens
                },
                'baseline_response': baseline_api.get('anatomical_locations', []),
                'rag_response': rag_api.get('anatomical_locations', [])
            }
        
        return comparison
    
    def generate_comparison_report(self, report_id: str) -> bool:
        """生成对比分析报告"""
        print(f"🔍 正在生成报告 {report_id} 的对比分析...")
        
        # 查找文件
        baseline_file, rag_file = self.find_batch_files(report_id)
        
        if not baseline_file or not rag_file:
            print(f"⚠️  报告 {report_id} 缺少必要文件:")
            print(f"     Baseline: {bool(baseline_file)} - {baseline_file}")
            print(f"     RAG: {bool(rag_file)} - {rag_file}")
            return False
        
        # 加载数据
        baseline_data = self.load_json_file(baseline_file)
        rag_data = self.load_json_file(rag_file)
        
        if not baseline_data or not rag_data:
            print(f"⚠️  报告 {report_id} 数据加载失败")
            return False
        
        # 生成对比分析
        comparison_report = {
            'report_id': report_id,
            'timestamp': datetime.now().isoformat(),
            'baseline_file': baseline_file,
            'rag_file': rag_file,
            'total_symptoms': len(baseline_data.get('symptoms', [])),
            'symptom_comparisons': [],
            'summary': {
                'total_apis': 0,
                'improved_symptoms': 0,
                'degraded_symptoms': 0,
                'unchanged_symptoms': 0,
                'average_improvement': {
                    'overall_score': 0.0,
                    'precision': 0.0,
                    'recall': 0.0
                },
                'total_token_usage': {
                    'baseline_total': 0,
                    'rag_total': 0,
                    'total_cached': 0,
                    'total_difference': 0
                }
            }
        }
        
        # 对比每个症状
        baseline_symptoms = baseline_data.get('symptoms', [])
        rag_symptoms = rag_data.get('symptoms', [])
        
        total_improvements = {'overall_score': 0.0, 'precision': 0.0, 'recall': 0.0}
        improved_count = 0
        degraded_count = 0
        unchanged_count = 0
        
        for i, (baseline_symptom, rag_symptom) in enumerate(zip(baseline_symptoms, rag_symptoms)):
            symptom_comparison = self.compare_symptom_results(baseline_symptom, rag_symptom)
            comparison_report['symptom_comparisons'].append(symptom_comparison)
            
            # 统计改善情况
            for api_name, api_comp in symptom_comparison['api_comparisons'].items():
                improvement = api_comp['improvement']['overall_score']
                if improvement > 0.01:
                    improved_count += 1
                elif improvement < -0.01:
                    degraded_count += 1
                else:
                    unchanged_count += 1
                
                # 累加改善值
                for metric in ['overall_score', 'precision', 'recall']:
                    total_improvements[metric] += api_comp['improvement'][metric]
                
                # 累加token使用
                token_usage = api_comp['token_usage']
                comparison_report['summary']['total_token_usage']['baseline_total'] += token_usage['baseline_tokens']
                comparison_report['summary']['total_token_usage']['rag_total'] += token_usage['rag_tokens']
                comparison_report['summary']['total_token_usage']['total_cached'] += token_usage['cached_tokens']
        
        # 计算总体统计
        total_api_comparisons = sum(len(s['api_comparisons']) for s in comparison_report['symptom_comparisons'])
        comparison_report['summary']['total_apis'] = total_api_comparisons
        comparison_report['summary']['improved_symptoms'] = improved_count
        comparison_report['summary']['degraded_symptoms'] = degraded_count
        comparison_report['summary']['unchanged_symptoms'] = unchanged_count
        
        # 计算平均改善
        if total_api_comparisons > 0:
            for metric in ['overall_score', 'precision', 'recall']:
                comparison_report['summary']['average_improvement'][metric] = total_improvements[metric] / total_api_comparisons
        
        # 计算token差异
        token_summary = comparison_report['summary']['total_token_usage']
        token_summary['total_difference'] = token_summary['rag_total'] - token_summary['baseline_total']
        
        # 保存对比分析结果
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        comparison_file = self.comparison_dir / f"report_{report_id}_batch_comparison_{timestamp}.json"
        
        with open(comparison_file, 'w', encoding='utf-8') as f:
            json.dump(comparison_report, f, ensure_ascii=False, indent=2)
        
        # 生成可读的摘要报告
        summary_file = self.comparison_dir / f"report_{report_id}_batch_summary_{timestamp}.txt"
        self.generate_summary_report(comparison_report, summary_file)
        
        print(f"✅ 对比分析完成:")
        print(f"   📊 详细对比: {comparison_file}")
        print(f"   📄 摘要报告: {summary_file}")
        print(f"   📈 改善/恶化/不变: {improved_count}/{degraded_count}/{unchanged_count}")
        
        return True
    
    def generate_summary_report(self, comparison_report: Dict[str, Any], output_file: Path):
        """生成可读的摘要报告"""
        lines = []
        lines.append("=" * 80)
        lines.append(f"📊 RAG增强效果对比分析报告")
        lines.append(f"📋 报告ID: {comparison_report['report_id']}")
        lines.append(f"⏰ 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("=" * 80)
        
        summary = comparison_report['summary']
        
        # 总体统计
        lines.append(f"\n📈 总体统计:")
        lines.append(f"   症状数量: {comparison_report['total_symptoms']}")
        lines.append(f"   API评估数: {summary['total_apis']}")
        lines.append(f"   改善: {summary['improved_symptoms']} 个")
        lines.append(f"   恶化: {summary['degraded_symptoms']} 个")
        lines.append(f"   不变: {summary['unchanged_symptoms']} 个")
        
        # 平均改善
        avg_imp = summary['average_improvement']
        lines.append(f"\n📊 平均性能改善:")
        lines.append(f"   综合得分: {avg_imp['overall_score']:+.3f}")
        lines.append(f"   精确率:   {avg_imp['precision']:+.3f}")
        lines.append(f"   召回率:   {avg_imp['recall']:+.3f}")
        
        # Token使用统计
        token_usage = summary['total_token_usage']
        lines.append(f"\n💰 Token使用统计:")
        lines.append(f"   Baseline总计: {token_usage['baseline_total']:,} tokens")
        lines.append(f"   RAG增强总计: {token_usage['rag_total']:,} tokens")
        lines.append(f"   缓存节省:     {token_usage['total_cached']:,} tokens")
        lines.append(f"   净增加:       {token_usage['total_difference']:+,} tokens")
        
        if token_usage['baseline_total'] > 0:
            percentage = (token_usage['total_difference'] / token_usage['baseline_total']) * 100
            lines.append(f"   变化百分比:   {percentage:+.1f}%")
        
        # 详细症状分析
        lines.append(f"\n🔍 详细症状分析:")
        for i, symptom_comp in enumerate(comparison_report['symptom_comparisons']):
            lines.append(f"\n   症状 {i+1}: {symptom_comp['symptom_text'][:50]}...")
            
            for api_name, api_comp in symptom_comp['api_comparisons'].items():
                improvement = api_comp['improvement']
                token_usage = api_comp['token_usage']
                
                lines.append(f"     {api_name.upper()}:")
                lines.append(f"       性能: 综合{improvement['overall_score']:+.3f}, 精确{improvement['precision']:+.3f}, 召回{improvement['recall']:+.3f}")
                lines.append(f"       Token: {token_usage['baseline_tokens']} → {token_usage['rag_tokens']} ({token_usage['token_difference']:+})")
                if token_usage['cached_tokens'] > 0:
                    lines.append(f"       缓存: {token_usage['cached_tokens']} tokens")
        
        lines.append("\n" + "=" * 80)
        lines.append("🏁 分析完成")
        lines.append("=" * 80)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))


def main():
    parser = argparse.ArgumentParser(description="批处理模式对比分析")
    parser.add_argument("report_id", type=str, help="报告ID")
    parser.add_argument("--config", type=str, default="config/config_openai.yaml", help="配置文件路径")
    
    args = parser.parse_args()
    
    workflow = BatchComparisonWorkflow(args.config)
    success = workflow.generate_comparison_report(args.report_id)
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
