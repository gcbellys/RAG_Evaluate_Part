#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RAG评估系统 - 主工作流程
不包含FAISS/RAG功能的基础版本
"""

import os
import sys
import json
import argparse
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path

# 添加src目录到Python路径
sys.path.append(str(Path(__file__).parent / "src"))

from config_loader import ConfigLoader
from data_loader import DataLoader
from api_manager import APIManager
from evaluator import Evaluator
from utils.logger import ReportLogger


class MainWorkflow:
    """主工作流程类"""
    
    def __init__(self, config_path: str = "config/config.yaml"):
        """初始化主工作流程"""
        self.config = ConfigLoader(config_path)
        self.data_loader = DataLoader()
        self.api_manager = APIManager()
        self.evaluator = Evaluator()
        self.logger = ReportLogger()
        
        # 创建结果目录
        self.results_dir = Path("results")
        self.results_dir.mkdir(exist_ok=True)
        
        # 创建日志目录
        self.logs_dir = Path("logs")
        self.logs_dir.mkdir(exist_ok=True)
    
    def process_report(self, report_data: Dict[str, Any]) -> Dict[str, Any]:
        """处理单个报告"""
        report_id = report_data.get('report_id', 'unknown')
        symptoms = report_data.get('symptoms', [])
        
        print(f"\n正在处理报告 {report_id}，包含 {len(symptoms)} 个症状")
        
        report_results = {
            'report_id': report_id,
            'timestamp': datetime.now().isoformat(),
            'symptoms': []
        }
        
        # 处理每个症状
        for symptom_item in symptoms:
            symptom_id = symptom_item.get('symptom_id', 'unknown')
            symptom_text = symptom_item.get('symptom_text', '')
            
            print(f"  处理症状 {symptom_id}: {symptom_text[:50]}...")
            
            # 提取期望的器官信息
            expected_organs = symptom_item.get('expected_results', [])
            
            # 调用API处理症状
            try:
                # 加载系统提示词
                system_prompt_path = Path("prompt/system_prompt.txt")
                if system_prompt_path.exists():
                    with open(system_prompt_path, 'r', encoding='utf-8') as f:
                        system_prompt = f.read().strip()
                else:
                    system_prompt = "你是一个医学专家，请根据症状识别相关的器官和解剖位置。"
                
                api_result = self.api_manager.process_symptom(symptom_item, system_prompt)
                
                # 为每个症状构建完整的数据结构
                symptom_data = {
                    'symptom_id': symptom_id,
                    'diagnosis': symptom_text,
                    'expected_organs': expected_organs,
                    'api_responses': {}
                }
                
                # 处理每个API的响应和评估
                for api_name, response in api_result.items():
                    api_response_data = {
                        'response': response.get('response', ''),
                        'parsed_data': response.get('parsed_data', {}),
                        'organ_name': response.get('organ_name', ''),
                        'anatomical_locations': response.get('anatomical_locations', [])
                    }
                    
                    # 评估这个API的响应
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
                
            except Exception as e:
                error_msg = f"处理症状 {symptom_id} 时出错: {str(e)}"
                print(f"    {error_msg}")
                
                # 即使出错也要保存症状的基本信息
                symptom_data = {
                    'symptom_id': symptom_id,
                    'diagnosis': symptom_text,
                    'expected_organs': expected_organs,
                    'error': str(e),
                    'api_responses': {}
                }
                report_results['symptoms'].append(symptom_data)
        
        return report_results
    
    def save_results(self, report_results: Dict[str, Any]) -> str:
        """保存单个报告的结果"""
        report_id = report_results['report_id']
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 保存详细结果
        detailed_filename = f"report_{report_id}_evaluation_{timestamp}.json"
        detailed_path = self.results_dir / detailed_filename
        
        with open(detailed_path, 'w', encoding='utf-8') as f:
            json.dump(report_results, f, ensure_ascii=False, indent=2)
        
        # 保存标准化结果
        standardized_results = self._standardize_results(report_results)
        standardized_filename = f"report_{report_id}_evaluation_standardized_{timestamp}.json"
        standardized_path = self.results_dir / standardized_filename
        
        with open(standardized_path, 'w', encoding='utf-8') as f:
            json.dump(standardized_results, f, ensure_ascii=False, indent=2)
        
        # 保存用户期望格式（扁平化，每个症状独立）
        user_format_results = self._generate_user_format(report_results)
        user_format_filename = f"report_{report_id}_user_format_{timestamp}.json"
        user_format_path = self.results_dir / user_format_filename
        
        with open(user_format_path, 'w', encoding='utf-8') as f:
            json.dump(user_format_results, f, ensure_ascii=False, indent=2)
        
        print(f"结果已保存到:")
        print(f"  详细结果: {detailed_path}")
        print(f"  标准化结果: {standardized_path}")
        print(f"  用户格式: {user_format_path}")
        
        return str(detailed_path)
    
    def _standardize_results(self, report_results: Dict[str, Any]) -> Dict[str, Any]:
        """标准化结果格式 - 用户期望的格式"""
        standardized = {
            'report_number': report_results['report_id'],
            'timestamp': report_results['timestamp'],
            'symptoms': []
        }
        
        # 标准化每个症状的数据
        for symptom_idx, symptom in enumerate(report_results['symptoms']):
            # 使用智能处理期望结果
            expected_result = self._process_expected_organs(symptom)
            
            # 构建API响应列表
            api_responses = []
            api_number = 1
            
            for api_name, response in symptom.get('api_responses', {}).items():
                api_response_data = {
                    'api_number': api_number,
                    'api_name': api_name,
                    'api_response': {
                        'organ': response.get('organ_name', ''),
                        'a_position': ', '.join(response.get('anatomical_locations', []))
                    },
                    'api_eva': response.get('evaluation', {})
                }
                api_responses.append(api_response_data)
                api_number += 1
            
            standardized_symptom = {
                'report_number': report_results['report_id'],
                'symptom_number': symptom_idx + 1,
                'symptom_name': symptom.get('diagnosis', ''),
                'expected_result': expected_result,
                'api_responses': api_responses
            }
            
            # 如果有错误信息，也保存
            if 'error' in symptom:
                standardized_symptom['error'] = symptom['error']
            
            standardized['symptoms'].append(standardized_symptom)
        
        return standardized
    
    def _generate_user_format(self, report_results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """生成用户期望的扁平化格式 - 每个症状作为独立条目"""
        user_format_list = []
        
        for symptom_idx, symptom in enumerate(report_results['symptoms']):
            # 智能处理期望结果 - 按器官分组并去重
            expected_result = self._process_expected_organs(symptom)
            
            # 构建API响应列表
            api_responses = []
            api_number = 1
            
            for api_name, response in symptom.get('api_responses', {}).items():
                api_response_data = {
                    'api_number': api_number,
                    'api_name': api_name,
                    'api_response': {
                        'organ': response.get('organ_name', ''),
                        'a_position': ', '.join(response.get('anatomical_locations', []))
                    },
                    'api_eva': response.get('evaluation', {})
                }
                api_responses.append(api_response_data)
                api_number += 1
            
            # 创建用户格式的条目
            user_format_entry = {
                'report_number': report_results['report_id'],
                'symptom_number': symptom_idx + 1,
                'symptom_name': symptom.get('diagnosis', ''),
                'expected_result': expected_result,
                'api_responses': api_responses
            }
            
            # 如果有错误信息，也保存
            if 'error' in symptom:
                user_format_entry['error'] = symptom['error']
            
            user_format_list.append(user_format_entry)
        
        return user_format_list
    
    def _process_expected_organs(self, symptom: Dict[str, Any]) -> Dict[str, str]:
        """智能处理期望器官数据 - 按器官分组，保留真正的多器官分布"""
        if not symptom.get('expected_organs'):
            return {
                'diag': symptom.get('diagnosis', ''),
                'organ': '',
                'a_position': ''
            }
        
        # 按器官名称分组
        organ_groups = {}
        all_diagnoses = set()
        
        for expected in symptom['expected_organs']:
            if isinstance(expected, dict):
                organ_name = expected.get('organName', '')
                locations = expected.get('anatomicalLocations', [])
                diagnosis = expected.get('d_diagnosis', '')
                
                if organ_name:
                    if organ_name not in organ_groups:
                        organ_groups[organ_name] = set()
                    organ_groups[organ_name].update(locations)
                
                if diagnosis:
                    all_diagnoses.add(diagnosis)
            elif isinstance(expected, str):
                if expected not in organ_groups:
                    organ_groups[expected] = set()
        
        # 构建结果
        unique_organs = list(organ_groups.keys())
        all_unique_locations = []
        
        for organ, locations in organ_groups.items():
            all_unique_locations.extend(list(locations))
        
        # 去重位置信息
        unique_locations = list(set(all_unique_locations))
        
        return {
            'diag': '; '.join(sorted(all_diagnoses)) if all_diagnoses else symptom.get('diagnosis', ''),
            'organ': ', '.join(sorted(unique_organs)),
            'a_position': ', '.join(sorted(unique_locations)),
            'organ_distribution': {
                organ: sorted(list(locations)) for organ, locations in organ_groups.items()
            }  # 额外添加器官分布详情
        }
    
    def generate_summary_report(self, all_results: List[Dict[str, Any]]) -> str:
        """生成汇总报告"""
        if not all_results:
            return ""
        
        summary = {
            'total_reports': len(all_results),
            'timestamp': datetime.now().isoformat(),
            'overall_metrics': {
                'average_precision': 0,
                'average_recall': 0,
                'average_f1_score': 0,
                'average_overgeneration_penalty': 0
            },
            'report_summaries': []
        }
        
        total_precision = 0
        total_recall = 0
        total_f1 = 0
        total_overgeneration = 0
        valid_reports = 0
        
        for result in all_results:
            report_summary = {
                'report_id': result['report_id'],
                'symptoms_count': len(result['symptoms']),
                'metrics': {}
            }
            
            # 计算该报告的平均指标
            report_precision = 0
            report_recall = 0
            report_f1 = 0
            report_overgeneration = 0
            valid_symptoms = 0
            
            for symptom in result['symptoms']:
                # 计算该症状的平均指标（如果有多个API）
                symptom_precision = 0
                symptom_recall = 0
                symptom_f1 = 0
                symptom_overgeneration = 0
                valid_apis = 0
                
                for api_name, response in symptom['api_responses'].items():
                    evaluation = response.get('evaluation', {})
                    if evaluation and 'precision' in evaluation:
                        symptom_precision += evaluation.get('precision', 0)
                        symptom_recall += evaluation.get('recall', 0)
                        symptom_f1 += evaluation.get('f1_score', 0)
                        symptom_overgeneration += evaluation.get('overgeneration_penalty', 0)
                        valid_apis += 1
                
                if valid_apis > 0:
                    report_precision += symptom_precision / valid_apis
                    report_recall += symptom_recall / valid_apis
                    report_f1 += symptom_f1 / valid_apis
                    report_overgeneration += symptom_overgeneration / valid_apis
                    valid_symptoms += 1
            
            if valid_symptoms > 0:
                report_summary['metrics'] = {
                    'precision': (report_precision / valid_symptoms) * 100,
                    'recall': (report_recall / valid_symptoms) * 100,
                    'f1_score': (report_f1 / valid_symptoms) * 100,
                    'overgeneration_penalty': (report_overgeneration / valid_symptoms) * 100
                }
                
                total_precision += report_summary['metrics']['precision']
                total_recall += report_summary['metrics']['recall']
                total_f1 += report_summary['metrics']['f1_score']
                total_overgeneration += report_summary['metrics']['overgeneration_penalty']
                valid_reports += 1
            
            summary['report_summaries'].append(report_summary)
        
        # 计算总体平均指标
        if valid_reports > 0:
            summary['overall_metrics'] = {
                'average_precision': total_precision / valid_reports,
                'average_recall': total_recall / valid_reports,
                'average_f1_score': total_f1 / valid_reports,
                'average_overgeneration_penalty': total_overgeneration / valid_reports
            }
        
        # 保存汇总报告
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        summary_filename = f"summary_report_{timestamp}.json"
        summary_path = self.results_dir / summary_filename
        
        with open(summary_path, 'w', encoding='utf-8') as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        
        print(f"\n汇总报告已保存到: {summary_path}")
        return str(summary_path)
    
    def run_workflow(self, start_id: int = None, end_id: int = None, max_files: int = None, mock_mode: bool = False):
        """运行主工作流程"""
        print("=== RAG评估系统 - 基础版本 ===")
        print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        try:
            # 测试API连接
            print("\n1. 测试API连接...")
            if not self.api_manager.initialize_clients(self.config.config):
                print("API客户端初始化失败，请检查配置")
                return
            
            if not self.api_manager.test_connectivity():
                print("API连接测试失败，请检查配置")
                return
            
            # 加载数据
            print("\n2. 加载数据...")
            data_path = Path(self.config.config.get('data_path', 'test_set'))
            
            if start_id is not None and end_id is not None:
                file_paths = self.data_loader.get_reports_by_id_range(data_path, start_id, end_id)
                print(f"找到 {len(file_paths)} 个文件 (ID范围: {start_id}-{end_id})")
            else:
                file_paths = self.data_loader.get_diagnostic_files(data_path)
                print(f"找到 {len(file_paths)} 个文件")
            
            # 加载每个文件的数据
            reports = []
            for file_path in file_paths:
                report_data = self.data_loader.load_report_data(file_path)
                if 'error' not in report_data:
                    reports.append(report_data)
            
            print(f"成功加载 {len(reports)} 个报告")
            
            if max_files:
                reports = reports[:max_files]
                print(f"限制处理文件数量: {max_files}")
            
            if not reports:
                print("没有找到可处理的报告")
                return
            
            # 处理报告
            print(f"\n3. 开始处理 {len(reports)} 个报告...")
            all_results = []
            
            for i, report in enumerate(reports, 1):
                print(f"\n进度: {i}/{len(reports)}")
                
                try:
                    result = self.process_report(report)
                    all_results.append(result)
                    
                    # 保存单个报告结果
                    self.save_results(result)
                    
                except Exception as e:
                    print(f"处理报告 {report.get('report_id', 'unknown')} 时出错: {str(e)}")
                    continue
            
            # 生成汇总报告
            if all_results:
                print(f"\n4. 生成汇总报告...")
                self.generate_summary_report(all_results)
            
            print(f"\n=== 工作流程完成 ===")
            print(f"成功处理: {len(all_results)} 个报告")
            print(f"结果保存在: {self.results_dir}")
            
        except Exception as e:
            print(f"工作流程执行出错: {str(e)}")
            logging.error(f"工作流程执行出错: {str(e)}", exc_info=True)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="RAG评估系统 - 基础版本")
    parser.add_argument("--start_id", type=int, help="开始报告ID")
    parser.add_argument("--end_id", type=int, help="结束报告ID")
    parser.add_argument("--max_files", type=int, help="最大处理文件数量")
    parser.add_argument("--mock_mode", action="store_true", help="启用模拟模式")
    parser.add_argument("--config", default="config/config.yaml", help="配置文件路径")
    
    args = parser.parse_args()
    
    # 创建并运行工作流程
    workflow = MainWorkflow(args.config)
    workflow.run_workflow(
        start_id=args.start_id,
        end_id=args.end_id,
        max_files=args.max_files,
        mock_mode=args.mock_mode
    )


if __name__ == "__main__":
    main()
