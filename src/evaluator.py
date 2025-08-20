#!/usr/bin/env python3
"""
整合的评估器
包含所有评估、结果保存和报告生成功能
"""

import json
from datetime import datetime
from typing import Dict, Any, List
from pathlib import Path

class Evaluator:
    """整合的评估器 - 支持多种评估方法和结果保存"""
    
    def __init__(self):
        pass
    
    def evaluate_single_response(self, 
                               api_response: Dict[str, Any], 
                               expected_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """评估单个API响应的解剖位置准确性"""
        if not api_response.get('success', False):
            return {
                'overall_score': 0.0,
                'precision': 0.0,
                'recall': 0.0,
                'overgeneration_penalty': 0.0,
                'detailed_analysis': 'API调用失败'
            }
        
        # 获取期望和实际的解剖位置
        expected_locations = []
        for expected_result in expected_results:
            expected_locations.extend(expected_result.get('anatomicalLocations', []))
        
        # 去重
        expected_locations = list(set(expected_locations))
        
        actual_locations = []
        # 检查多种可能的字段名
        if 'parsed_data' in api_response and api_response['parsed_data']:
            actual_locations = api_response['parsed_data'].get('anatomical_locations', [])
        elif 'anatomical_locations' in api_response and api_response['anatomical_locations']:
            actual_locations = api_response['anatomical_locations']
        elif 'parsed_response' in api_response and api_response['parsed_response']:
            actual_locations = api_response['parsed_response'].get('anatomicalLocations', [])
        
        if not expected_locations or not actual_locations:
            return {
                'overall_score': 0.0,
                'precision': 0.0,
                'recall': 0.0,
                'overgeneration_penalty': 0.0,
                'detailed_analysis': '缺少解剖位置信息'
            }
        
        # 1. 计算Precision (精确率) - 40%权重
        precision = self._calculate_precision(actual_locations, expected_locations)
        
        # 2. 计算Recall (召回率) - 40%权重
        recall = self._calculate_recall(actual_locations, expected_locations)
        
        # 3. 计算过度生成惩罚 - 20%权重
        overgeneration_penalty = self._calculate_overgeneration_penalty(actual_locations, expected_locations)
        
        # 4. 计算综合得分 (100分制)
        overall_score = (precision * 0.4 + recall * 0.4 + overgeneration_penalty * 0.2) * 100
        
        # 5. 生成详细分析
        analysis = self._generate_analysis(actual_locations, expected_locations, precision, recall, overgeneration_penalty)
        
        return {
            'overall_score': round(overall_score, 1),
            'precision': round(precision * 100, 1),
            'recall': round(recall * 100, 1),
            'overgeneration_penalty': round(overgeneration_penalty * 100, 1),
            'detailed_analysis': analysis
        }
    
    def evaluate_report_responses(self, report_results: Dict[str, Any]) -> Dict[str, Any]:
        """评估整个Report的所有症状响应"""
        print(f"📊 评估Report {report_results['report_id']} 的 {len(report_results['symptoms'])} 个症状...")
        
        report_evaluation = {
            'report_id': report_results['report_id'],
            'total_symptoms': report_results['total_symptoms'],
            'valid_symptoms': report_results['valid_symptoms'],
            'evaluation_timestamp': datetime.now().isoformat(),
            'symptom_evaluations': [],
            'summary': {
                'total_api_calls': 0,
                'successful_api_calls': 0,
                'failed_api_calls': 0,
                'average_overall_score': 0.0,
                'average_precision': 0.0,
                'average_recall': 0.0
            }
        }
        
        total_scores = []
        total_precision = []
        total_recall = []
        
        for symptom_result in report_results['symptoms']:
            symptom_evaluation = {
                'symptom_id': symptom_result['symptom_id'],
                'symptom_text': symptom_result['symptom_text'],
                'expected_results': symptom_result['expected_results'],
                'api_evaluations': {}
            }
            
            # 评估每个API的响应
            for api_name, api_response in symptom_result['api_responses'].items():
                report_evaluation['summary']['total_api_calls'] += 1
                
                if api_response.get('success'):
                    report_evaluation['summary']['successful_api_calls'] += 1
                    
                    # 评估API响应
                    evaluation = self.evaluate_single_response(api_response, symptom_result['expected_results'])
                    symptom_evaluation['api_evaluations'][api_name] = evaluation
                    
                    # 累计分数
                    total_scores.append(evaluation['overall_score'])
                    total_precision.append(evaluation['precision'])
                    total_recall.append(evaluation['recall'])
                else:
                    report_evaluation['summary']['failed_api_calls'] += 1
                    symptom_evaluation['api_evaluations'][api_name] = {
                        'overall_score': 0.0,
                        'precision': 0.0,
                        'recall': 0.0,
                        'overgeneration_penalty': 0.0,
                        'detailed_analysis': f"API调用失败: {api_response.get('error', '未知错误')}"
                    }
            
            report_evaluation['symptom_evaluations'].append(symptom_evaluation)
        
        # 计算平均分数
        if total_scores:
            report_evaluation['summary']['average_overall_score'] = round(sum(total_scores) / len(total_scores), 1)
            report_evaluation['summary']['average_precision'] = round(sum(total_precision) / len(total_precision), 1)
            report_evaluation['summary']['average_recall'] = round(sum(total_recall) / len(total_recall), 1)
        
        return report_evaluation
    
    def save_report_results(self, report_results: Dict[str, Any], report_evaluation: Dict[str, Any], output_dir: Path):
        """按Report级别保存结果，文件名格式为report:i_baseline_evaluation_standardized"""
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # 构造Report结果文件名
        report_id = report_results['report_id']
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_file = output_dir / f"report:{report_id}_baseline_evaluation_standardized.json"
        
        # 准备保存的数据
        evaluation_results = {
            'metadata': {
                'report_id': report_id,
                'file_path': report_results['file_path'],
                'processing_timestamp': report_results['processing_timestamp'],
                'evaluation_timestamp': report_evaluation['evaluation_timestamp'],
                'total_symptoms': report_results['total_symptoms'],
                'valid_symptoms': report_results['valid_symptoms'],
                'api_clients': list(report_results['symptoms'][0]['api_responses'].keys()) if report_results['symptoms'] else []
            },
            'symptoms': []
        }
        
        # 处理每个症状的结果
        for symptom_result in report_results['symptoms']:
            symptom_data = {
                'symptom_id': symptom_result['symptom_id'],
                'symptom_text': symptom_result['symptom_text'],
                'expected_results': symptom_result['expected_results'],
                'total_u_units': symptom_result['total_u_units'],
                'api_responses': {}
            }
            
            # 标准化API响应
            for client_name, response in symptom_result['api_responses'].items():
                parsed_response = {}
                if response.get('success'):
                    try:
                        # 去除可能的Markdown代码块标记
                        text = response['response'].strip().replace('```json', '').replace('```', '').strip()
                        parsed_response = json.loads(text)
                    except (json.JSONDecodeError, AttributeError):
                        response['success'] = False
                        response['error'] = "Failed to parse JSON response"
                
                symptom_data['api_responses'][client_name] = {
                    'success': response.get('success', False),
                    'model': response.get('model', 'Unknown'),
                    'organ_name': parsed_response.get('organName', ''),
                    'anatomical_locations': parsed_response.get('anatomicalLocations', []),
                    'usage': response.get('usage', {}),
                    'error': response.get('error')
                }
            
            evaluation_results['symptoms'].append(symptom_data)
        
        # 添加评估摘要
        evaluation_results['evaluation_summary'] = report_evaluation['summary']
        
        # 保存到文件
        try:
            with open(results_file, 'w', encoding='utf-8') as f:
                json.dump(evaluation_results, f, ensure_ascii=False, indent=2)
            print(f"✅ Report {report_id} 结果已保存到: {results_file}")
            return str(results_file)
        except Exception as e:
            print(f"❌ 保存Report {report_id} 结果失败: {e}")
            raise
    
    def _calculate_precision(self, actual_locations: List[str], expected_locations: List[str]) -> float:
        """计算Precision (精确率)"""
        if not actual_locations:
            return 0.0
        
        # 计算正确返回的数量
        correct_count = 0
        for location in actual_locations:
            if location in expected_locations:
                correct_count += 1
        
        # Precision = 正确数量 / 实际返回总数
        precision = correct_count / len(actual_locations)
        return precision
    
    def _calculate_recall(self, actual_locations: List[str], expected_locations: List[str]) -> float:
        """计算Recall (召回率)"""
        if not expected_locations:
            return 0.0
        
        # 计算正确返回的数量
        correct_count = 0
        for location in actual_locations:
            if location in expected_locations:
                correct_count += 1
        
        # Recall = 正确数量 / 期望总数
        recall = correct_count / len(expected_locations)
        return recall
    
    def _calculate_overgeneration_penalty(self, actual_locations: List[str], expected_locations: List[str]) -> float:
        """计算过度生成惩罚"""
        if not expected_locations:
            return 0.0
        
        # 计算返回数量与期望数量的比例
        ratio = len(actual_locations) / len(expected_locations)
        
        # 惩罚机制：
        # - 如果返回数量 <= 期望数量：无惩罚 (1.0分)
        # - 如果返回数量 > 期望数量且 <= 2倍：线性惩罚 (1.0 → 0.5)
        # - 如果返回数量 > 2倍且 <= 3倍：线性惩罚 (0.5 → 0.0)
        # - 如果返回数量 > 3倍：最大惩罚 (0.0分)
        
        if ratio <= 1.0:
            # 无过度生成，无惩罚
            penalty = 1.0
        elif ratio <= 2.0:
            # 线性惩罚：从1.0降到0.5
            penalty = 1.0 - (ratio - 1.0) * 0.5
        elif ratio <= 3.0:
            # 线性惩罚：从0.5降到0.0
            penalty = 0.5 - (ratio - 2.0) * 0.5
        else:
            # 超过3倍，最大惩罚
            penalty = 0.0
        
        return penalty
    
    def _generate_analysis(self, actual_locations: List[str], expected_locations: List[str], 
                          precision: float, recall: float, overgeneration_penalty: float) -> str:
        """生成详细分析报告"""
        # 计算正确数量
        correct_count = 0
        for location in actual_locations:
            if location in expected_locations:
                correct_count += 1
        
        analysis = f"Precision(精确率): {correct_count}/{len(actual_locations)} ({precision:.1%}); "
        analysis += f"Recall(召回率): {correct_count}/{len(expected_locations)} ({recall:.1%}); "
        analysis += f"过度生成惩罚: {overgeneration_penalty:.1%}"
        
        return analysis
