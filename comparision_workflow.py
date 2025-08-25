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
sys.path.append(str(Path(__file__).parent.parent / "Rag_Build" / "src"))

from config_loader import ConfigLoader
from data_loader import DataLoader
from api_manager import APIManager
from evaluator import Evaluator
from utils.logger import ReportLogger
from enhanced_search_engine import EnhancedMedicalSearchEngine


class MainWorkflow:
    """主工作流程类"""
    
    def __init__(self, config_path: str = "config/config.yaml", rag_cache_path: Optional[str] = None):
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
        
        # RAG 缓存（优先）或在线检索引擎
        self.rag_cache: Dict[str, List[Dict[str, Any]]] = {}
        if rag_cache_path and Path(rag_cache_path).exists():
            self._load_rag_cache(rag_cache_path)
            self.search_engine = None
            print(f"✅ 已加载RAG缓存: {rag_cache_path} (共 {len(self.rag_cache)} 条)")
        else:
            # 初始化RAG搜索引擎（仅在没有缓存时）
            default_index_dir = "/home/duojiechen/Projects/Rag_system/Rag_Build/enhanced_faiss_indexes"
            self.rag_index_dir = os.getenv("RAG_INDEX_DIR", default_index_dir)
            try:
                self.search_engine = EnhancedMedicalSearchEngine(self.rag_index_dir)
                print(f"✅ RAG 搜索引擎已初始化: {self.rag_index_dir}")
            except Exception as e:
                print(f"❌ RAG 搜索引擎初始化失败: {e}")
                self.search_engine = None

    def _load_rag_cache(self, cache_path: str) -> None:
        """加载由 Rag_Build 生成的 JSONL 缓存，按 query 建立映射"""
        cache_file = Path(cache_path)
        mapping: Dict[str, List[Dict[str, Any]]] = {}
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        obj = json.loads(line)
                    except Exception:
                        continue
                    query = (obj.get('query') or '').strip()
                    results = obj.get('results') or []
                    if query:
                        mapping[query] = results
        except Exception as e:
            print(f"⚠️ 加载RAG缓存失败: {e}")
        self.rag_cache = mapping

    def _lookup_rag_cache(self, symptom_text: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """在缓存中查找对应症状的检索结果（精确匹配，找不到则返回空）"""
        key = (symptom_text or '').strip()
        if not key:
            return []
        items = self.rag_cache.get(key) or []
        return items[:top_k]
    
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
                
                # 先运行基线：不带RAG增强的原始提示
                baseline_api_result = self.api_manager.process_symptom(symptom_item, system_prompt)
                # 组装并评估基线结果
                baseline_api_responses: Dict[str, Any] = {}
                for api_name, response in baseline_api_result.items():
                    api_response_data = {
                        'response': response.get('response', ''),
                        'parsed_data': response.get('parsed_data', {}),
                        'organ_name': response.get('organ_name', ''),
                        'anatomical_locations': response.get('anatomical_locations', [])
                    }
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
                    baseline_api_responses[api_name] = api_response_data

                # 第一步：使用RAG进行检索（优先缓存，其次在线），获得参考证据
                rag_results = None
                rag_primary_refs: List[Dict[str, Any]] = []
                rag_context_refs: List[Dict[str, Any]] = []
                if self.rag_cache:
                    try:
                        cached = self._lookup_rag_cache(symptom_text, top_k=3)
                        for item in cached:
                            text = item.get('text') or item.get('d_diagnosis') or ''
                            organ = item.get('o_organ')  # dict: {organName, anatomicalLocations}
                            rag_primary_refs.append({'text': text, 'organ': organ})
                    except Exception as re:
                        print(f"    读取RAG缓存失败，继续使用原始症状: {re}")
                elif self.search_engine is not None and symptom_text:
                    try:
                        rag_results = self.search_engine.comprehensive_search(
                            query=symptom_text,
                            top_k=3,
                            rerank=False,
                            force_query_type='symptom'
                        )
                        # 组装主检索结果（text + organ，如可用）
                        for item in rag_results.get('primary_results', [])[:3]:
                            data = item.get('data', {})
                            text = item.get('symptom_text') or data.get('text') or ''
                            organ = data.get('organ')
                            rag_primary_refs.append({
                                'text': text,
                                'organ': organ
                            })
                        # 组装上下文中的相关诊断（通常包含 organ）
                        for diag in rag_results.get('context_results', {}).get('related_diagnoses', [])[:5]:
                            rag_context_refs.append({
                                'text': diag.get('diagnosis_text', ''),
                                'organ': diag.get('organ')
                            })
                    except Exception as re:
                        print(f"    RAG检索失败，继续使用原始症状: {re}")
                
                # 第二步：将RAG证据注入用户提示，作为参考
                augmented_symptom_text = self._build_augmented_prompt(symptom_text, rag_primary_refs, rag_context_refs)
                augmented_item = dict(symptom_item)
                augmented_item['symptom_text'] = augmented_symptom_text
                
                # 调用API（RAG增强）
                api_result = self.api_manager.process_symptom(augmented_item, system_prompt)
                
                # 为每个症状构建完整的数据结构
                symptom_data = {
                    'symptom_id': symptom_id,
                    'diagnosis': symptom_text,
                    'expected_organs': expected_organs,
                    'api_responses': {},
                    'api_responses_baseline': {},
                    'api_responses_with_rag': {},
                    'comparison': {},
                    'rag_retrieval': {
                        'primary_refs': rag_primary_refs,
                        'context_refs': rag_context_refs
                    }
                }
                
                # 处理RAG增强后的API响应和评估
                rag_api_responses: Dict[str, Any] = {}
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
                    
                    rag_api_responses[api_name] = api_response_data
                
                # 保存两套结果，并将 api_responses 指向 with_rag 以兼容原有下游
                symptom_data['api_responses_with_rag'] = rag_api_responses
                symptom_data['api_responses_baseline'] = baseline_api_responses
                symptom_data['api_responses'] = rag_api_responses
                
                # 生成对比摘要（with_rag - baseline）
                all_api_names = set(list(baseline_api_responses.keys()) + list(rag_api_responses.keys()))
                for name in all_api_names:
                    base_eval = baseline_api_responses.get(name, {}).get('evaluation')
                    rag_eval = rag_api_responses.get(name, {}).get('evaluation')
                    if base_eval and rag_eval:
                        comp = {
                            'overall_delta': round(rag_eval.get('overall_score', 0) - base_eval.get('overall_score', 0), 1),
                            'precision_delta': round(rag_eval.get('precision', 0) - base_eval.get('precision', 0), 1),
                            'recall_delta': round(rag_eval.get('recall', 0) - base_eval.get('recall', 0), 1),
                            'overgeneration_penalty_delta': round(rag_eval.get('overgeneration_penalty', 0) - base_eval.get('overgeneration_penalty', 0), 1),
                            'baseline_prediction': {
                                'organ_name': baseline_api_responses.get(name, {}).get('organ_name', ''),
                                'anatomical_locations': baseline_api_responses.get(name, {}).get('anatomical_locations', [])
                            },
                            'with_rag_prediction': {
                                'organ_name': rag_api_responses.get(name, {}).get('organ_name', ''),
                                'anatomical_locations': rag_api_responses.get(name, {}).get('anatomical_locations', [])
                            }
                        }
                    else:
                        comp = {
                            'overall_delta': 0.0,
                            'precision_delta': 0.0,
                            'recall_delta': 0.0,
                            'overgeneration_penalty_delta': 0.0,
                            'baseline_prediction': {
                                'organ_name': baseline_api_responses.get(name, {}).get('organ_name', ''),
                                'anatomical_locations': baseline_api_responses.get(name, {}).get('anatomical_locations', [])
                            },
                            'with_rag_prediction': {
                                'organ_name': rag_api_responses.get(name, {}).get('organ_name', ''),
                                'anatomical_locations': rag_api_responses.get(name, {}).get('anatomical_locations', [])
                            }
                        }
                    symptom_data['comparison'][name] = comp
                
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

    def _build_augmented_prompt(self, symptom_text: str, primary_refs: List[Dict[str, Any]], context_refs: List[Dict[str, Any]]) -> str:
        """将RAG检索到的证据拼接到用户提示中，提供文本与对应器官参考"""
        if not primary_refs and not context_refs:
            return symptom_text
        
        def fmt_ref(ref: Dict[str, Any]) -> str:
            organ_part = ""
            organ = ref.get('organ')
            if organ:
                # organ 可能是字符串或字典
                if isinstance(organ, str):
                    organ_part = f" | organ: {organ}"
                elif isinstance(organ, dict):
                    # 常见结构: {'organName': 'xxx', 'anatomicalLocations': [...]}
                    name = organ.get('organName') or organ.get('name') or ''
                    locs = organ.get('anatomicalLocations') or organ.get('locations') or []
                    if isinstance(locs, list):
                        loc_str = ", ".join(locs)
                    else:
                        loc_str = str(locs)
                    organ_part = f" | organ: {name} | locations: {loc_str}" if name or loc_str else ""
            text = ref.get('text') or ''
            return f"- {text}{organ_part}".strip()
        
        primary_block = "\n".join([fmt_ref(r) for r in primary_refs]) if primary_refs else ""
        context_block = "\n".join([fmt_ref(r) for r in context_refs]) if context_refs else ""
        
        aug_parts = [
            "以下是我的症状描述：",
            symptom_text.strip(),
            "",
            "下面给你一些来自检索系统（RAG）的相关参考，请在回答时以这些参考为主要依据进行推理与归纳，同时严格输出JSON结构：",
            "参考-主检索：",
            primary_block if primary_block else "(无)",
            "",
            "参考-相关诊断：",
            context_block if context_block else "(无)"
        ]
        return "\n".join([p for p in aug_parts if p is not None])
    
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
    parser.add_argument("--rag_cache", type=str, help="RAG检索结果缓存(JSONL)路径，若提供则优先使用缓存")
    
    args = parser.parse_args()
    
    # 创建并运行工作流程
    workflow = MainWorkflow(args.config, rag_cache_path=args.rag_cache)
    workflow.run_workflow(
        start_id=args.start_id,
        end_id=args.end_id,
        max_files=args.max_files,
        mock_mode=args.mock_mode
    )


if __name__ == "__main__":
    main()


