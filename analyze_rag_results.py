#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RAG评估结果分析工具
生成四个CSV文件分析不同RAG策略的性能指标
"""

import json
import pandas as pd
import os
from pathlib import Path
from typing import Dict, List, Tuple, Any
import re
from collections import defaultdict

class RAGResultsAnalyzer:
    def __init__(self, results_dir: str = "/home/duojiechen/projects/Rag_system/Rag_Evaluate/results"):
        self.results_dir = Path(results_dir)
        self.strategies = {
            'baseline': 'baseline_results',
            'uniform': 'uniform',
            'report_context': 'report_context', 
            'sequential_block': 'sequential_block'
        }
        
    def extract_report_id(self, filename: str) -> str:
        """从文件名提取报告ID"""
        match = re.search(r'diagnostic_(\d+)', filename)
        return match.group(1) if match else "unknown"
    
    def calculate_metrics(self, expected_organs: List[Dict], predicted_organs: List[Dict]) -> Tuple[float, float, float]:
        """
        计算精准度、召回率和F1分数
        
        Args:
            expected_organs: 期望的器官和解剖位置列表
            predicted_organs: 预测的器官和解剖位置列表
            
        Returns:
            Tuple[precision, recall, f1_score]
        """
        # 提取期望的器官-位置对
        expected_pairs = set()
        for organ in expected_organs:
            organ_name = organ.get('organName', '')
            locations = organ.get('anatomicalLocations', [])
            for location in locations:
                expected_pairs.add((organ_name, location))
        
        # 提取预测的器官-位置对
        predicted_pairs = set()
        for organ in predicted_organs:
            organ_name = organ.get('organName', '')
            locations = organ.get('anatomicalLocations', [])
            for location in locations:
                predicted_pairs.add((organ_name, location))
        
        # 计算指标
        if len(predicted_pairs) == 0:
            precision = 0.0
        else:
            precision = len(expected_pairs.intersection(predicted_pairs)) / len(predicted_pairs)
        
        if len(expected_pairs) == 0:
            recall = 0.0
        else:
            recall = len(expected_pairs.intersection(predicted_pairs)) / len(expected_pairs)
        
        if precision + recall == 0:
            f1_score = 0.0
        else:
            f1_score = 2 * (precision * recall) / (precision + recall)
        
        return precision, recall, f1_score
    
    def analyze_baseline_results(self) -> List[Dict]:
        """分析基线结果"""
        baseline_dir = self.results_dir / 'baseline_results'
        results = []
        
        for json_file in baseline_dir.glob('*.json'):
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                report_id = self.extract_report_id(json_file.name)
                
                for symptom in data.get('symptoms', []):
                    symptom_text = symptom.get('diagnosis', 'unknown_symptom')
                    expected_organs = symptom.get('expected_organs', [])
                    
                    # 获取API响应中的预测结果（以moonshot为主要API）
                    api_responses = symptom.get('api_responses', {})
                    
                    # 尝试从不同API获取结果
                    predicted_organs = []
                    for api_name in ['moonshot', 'anthropic', 'gemini', 'deepseek', 'qwen']:
                        if api_name in api_responses:
                            api_data = api_responses[api_name]
                            if 'full_response' in api_data.get('parsed_data', {}):
                                predicted_organs = api_data['parsed_data']['full_response'].get('organs', [])
                                break
                            elif 'organs' in api_data.get('parsed_data', {}):
                                predicted_organs = api_data['parsed_data']['organs']
                                break
                    
                    # 计算指标
                    precision, recall, f1_score = self.calculate_metrics(expected_organs, predicted_organs)
                    
                    results.append({
                        'symptom_name': symptom_text,
                        'report_id': report_id,
                        'precision': precision,
                        'recall': recall,
                        'f1_score': f1_score
                    })
                    
            except Exception as e:
                print(f"处理文件 {json_file} 时出错: {e}")
                continue
        
        return results
    
    def analyze_rag_results(self, strategy: str) -> List[Dict]:
        """分析RAG增强结果"""
        strategy_dir = self.results_dir / strategy
        results = []
        
        # 查找RAG增强结果文件
        rag_dir = strategy_dir / 'rerun_with_rag'
        baseline_dir = strategy_dir / 'baseline_results'
        
        if not rag_dir.exists():
            print(f"警告: {rag_dir} 目录不存在")
            return results
        
        for json_file in rag_dir.glob('*.json'):
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                report_id = self.extract_report_id(json_file.name)
                
                # 处理不同的数据结构
                if 'symptoms' in data:
                    # 新格式
                    symptoms_data = data['symptoms']
                    if isinstance(symptoms_data, list):
                        # 批处理格式
                        for symptom in symptoms_data:
                            symptom_text = symptom.get('symptom_text', 'unknown_symptom')
                            expected_organs = symptom.get('expected_organs', [])
                            
                            # 获取API响应
                            api_responses = symptom.get('api_responses', {})
                            predicted_organs = []
                            
                            for api_name in ['moonshot', 'anthropic', 'gemini', 'deepseek', 'qwen']:
                                if api_name in api_responses:
                                    api_data = api_responses[api_name]
                                    if 'full_response' in api_data.get('parsed_data', {}):
                                        predicted_organs = api_data['parsed_data']['full_response'].get('organs', [])
                                        break
                                    elif 'organs' in api_data.get('parsed_data', {}):
                                        predicted_organs = api_data['parsed_data']['organs']
                                        break
                            
                            precision, recall, f1_score = self.calculate_metrics(expected_organs, predicted_organs)
                            
                            results.append({
                                'symptom_name': symptom_text,
                                'report_id': report_id,
                                'precision': precision,
                                'recall': recall,
                                'f1_score': f1_score
                            })
                    else:
                        # 字典格式
                        for symptom_key, symptom_data in symptoms_data.items():
                            if isinstance(symptom_data, dict) and 'api_responses' in symptom_data:
                                symptom_text = symptom_key
                                expected_organs = symptom_data.get('expected_organs', [])
                                
                                api_responses = symptom_data.get('api_responses', {})
                                predicted_organs = []
                                
                                for api_name in ['moonshot', 'anthropic', 'gemini', 'deepseek', 'qwen']:
                                    if api_name in api_responses:
                                        api_data = api_responses[api_name]
                                        if 'full_response' in api_data.get('parsed_data', {}):
                                            predicted_organs = api_data['parsed_data']['full_response'].get('organs', [])
                                            break
                                        elif 'organs' in api_data.get('parsed_data', {}):
                                            predicted_organs = api_data['parsed_data']['organs']
                                            break
                                
                                precision, recall, f1_score = self.calculate_metrics(expected_organs, predicted_organs)
                                
                                results.append({
                                    'symptom_name': symptom_text,
                                    'report_id': report_id,
                                    'precision': precision,
                                    'recall': recall,
                                    'f1_score': f1_score
                                })
                else:
                    # 旧格式 - 直接是症状字典
                    for symptom_key, symptom_data in data.items():
                        if isinstance(symptom_data, dict) and 'api_responses' in symptom_data:
                            symptom_text = symptom_key
                            expected_organs = symptom_data.get('expected_organs', [])
                            
                            api_responses = symptom_data.get('api_responses', {})
                            predicted_organs = []
                            
                            for api_name in ['moonshot', 'anthropic', 'gemini', 'deepseek', 'qwen']:
                                if api_name in api_responses:
                                    api_data = api_responses[api_name]
                                    if 'full_response' in api_data.get('parsed_data', {}):
                                        predicted_organs = api_data['parsed_data']['full_response'].get('organs', [])
                                        break
                                    elif 'organs' in api_data.get('parsed_data', {}):
                                        predicted_organs = api_data['parsed_data']['organs']
                                        break
                            
                            precision, recall, f1_score = self.calculate_metrics(expected_organs, predicted_organs)
                            
                            results.append({
                                'symptom_name': symptom_text,
                                'report_id': report_id,
                                'precision': precision,
                                'recall': recall,
                                'f1_score': f1_score
                            })
                    
            except Exception as e:
                print(f"处理文件 {json_file} 时出错: {e}")
                continue
        
        return results
    
    def generate_csv_reports(self, output_dir: str = None):
        """生成四个CSV报告"""
        if output_dir is None:
            output_dir = self.results_dir / 'analysis_reports'
        
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)
        
        print("🚀 开始分析RAG评估结果...")
        
        # 1. 分析基线结果
        print("📊 分析基线结果...")
        baseline_results = self.analyze_baseline_results()
        if baseline_results:
            baseline_df = pd.DataFrame(baseline_results)
            baseline_csv = output_path / 'baseline_results_analysis.csv'
            baseline_df.to_csv(baseline_csv, index=False, encoding='utf-8')
            print(f"✅ 基线结果已保存: {baseline_csv}")
            print(f"   - 总症状数: {len(baseline_results)}")
            print(f"   - 平均精准度: {baseline_df['precision'].mean():.4f}")
            print(f"   - 平均召回率: {baseline_df['recall'].mean():.4f}")
            print(f"   - 平均F1分数: {baseline_df['f1_score'].mean():.4f}")
        else:
            print("❌ 未找到基线结果")
        
        # 2-4. 分析三种RAG策略
        for strategy_name, strategy_dir in [('uniform', 'uniform'), 
                                           ('report_context', 'report_context'), 
                                           ('sequential_block', 'sequential_block')]:
            print(f"📊 分析{strategy_name}策略结果...")
            rag_results = self.analyze_rag_results(strategy_dir)
            
            if rag_results:
                rag_df = pd.DataFrame(rag_results)
                rag_csv = output_path / f'{strategy_name}_results_analysis.csv'
                rag_df.to_csv(rag_csv, index=False, encoding='utf-8')
                print(f"✅ {strategy_name}结果已保存: {rag_csv}")
                print(f"   - 总症状数: {len(rag_results)}")
                print(f"   - 平均精准度: {rag_df['precision'].mean():.4f}")
                print(f"   - 平均召回率: {rag_df['recall'].mean():.4f}")
                print(f"   - 平均F1分数: {rag_df['f1_score'].mean():.4f}")
            else:
                print(f"❌ 未找到{strategy_name}结果")
        
        print(f"\n🎉 分析完成! 所有CSV文件已保存到: {output_path}")
        
        # 生成汇总报告
        self.generate_summary_report(output_path)
    
    def generate_summary_report(self, output_path: Path):
        """生成汇总对比报告"""
        summary_data = []
        
        for strategy in ['baseline', 'uniform', 'report_context', 'sequential_block']:
            csv_file = output_path / f'{strategy}_results_analysis.csv'
            if csv_file.exists():
                df = pd.read_csv(csv_file)
                summary_data.append({
                    'strategy': strategy,
                    'total_symptoms': len(df),
                    'avg_precision': df['precision'].mean(),
                    'avg_recall': df['recall'].mean(),
                    'avg_f1_score': df['f1_score'].mean(),
                    'std_precision': df['precision'].std(),
                    'std_recall': df['recall'].std(),
                    'std_f1_score': df['f1_score'].std()
                })
        
        if summary_data:
            summary_df = pd.DataFrame(summary_data)
            summary_csv = output_path / 'strategy_comparison_summary.csv'
            summary_df.to_csv(summary_csv, index=False, encoding='utf-8')
            print(f"📋 策略对比汇总已保存: {summary_csv}")


def main():
    """主函数"""
    analyzer = RAGResultsAnalyzer()
    analyzer.generate_csv_reports()


if __name__ == "__main__":
    main()
