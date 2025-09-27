#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
独立脚本：使用已有的RAG检索结果重新运行LLM评估

功能:
1. 根据报告ID，自动查找最新的RAG检索缓存文件。
2. 逐一处理缓存文件中的每个症状。
3. 将RAG检索结果格式化后，构建增强型Prompt。
4. 调用APIManager，让所有配置的LLM重新处理这些增强型Prompt。
5. 将新的LLM输出结果保存到专属的文件夹中。
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

# --- 关键：确保脚本能找到src目录下的模块 ---
# 将项目根目录添加到Python路径中
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


class RerunWorkflow:
    """使用已有RAG结果重新运行LLM的工作流"""

    def __init__(self, report_id: int, config_path: str = "config/config.yaml"):
        self.report_id = report_id
        self.config = ConfigLoader(config_path)
        self.api_manager = APIManager()
        self.evaluator = Evaluator()
        self.logger = ReportLogger()

        # --- 路径定义 ---
        # 获取项目根目录（从workflows/向上一级）
        self.project_root = Path(__file__).resolve().parent.parent
        # RAG缓存文件的存放位置
        self.rag_output_dir = self.project_root / "final_result" / "rag_search_output"
        
        # 统一在final_result下管理所有结果
        self.final_result_dir = self.project_root / "final_result"
        self.baseline_results_dir = self.final_result_dir / "baseline_results"
        self.rerun_results_dir = self.final_result_dir / "rerun_with_rag"
        self.comparison_results_dir = self.final_result_dir / "rerun_comparisons"
        
        # 创建所有必要的目录
        for dir_path in [self.baseline_results_dir, self.rerun_results_dir, self.comparison_results_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)
        
        print(f"🎯 报告ID: {self.report_id}")
        print(f"🔍 RAG缓存目录: {self.rag_output_dir}")
        print(f"📋 Baseline结果目录: {self.baseline_results_dir}")
        print(f"💾 RAG增强结果目录: {self.rerun_results_dir}")
        print(f"📊 对比结果目录: {self.comparison_results_dir}")

    def find_latest_rag_cache(self) -> Path:
        """根据报告ID查找最新的RAG结果文件 (.jsonl)"""
        search_pattern = f"report_{self.report_id}_ragoutcome:*.jsonl"
        files = glob.glob(str(self.rag_output_dir / search_pattern))
        
        if not files:
            raise FileNotFoundError(f"在目录 {self.rag_output_dir} 中未找到报告ID {self.report_id} 的RAG缓存文件。")
        
        latest_file = max(files, key=os.path.getctime)
        print(f"🔍 找到最新的RAG缓存文件: {Path(latest_file).name}")
        return Path(latest_file)

    def find_or_create_baseline_results(self) -> Path:
        """查找或创建对应的baseline结果文件"""
        # 先在统一的baseline_results目录中查找
        search_pattern = f"report_diagnostic_{self.report_id}_evaluation_*.json"
        files = glob.glob(str(self.baseline_results_dir / search_pattern))
        
        # 过滤掉标准化版本和用户格式版本
        detailed_files = [f for f in files if 'standardized' not in f and 'user_format' not in f]
        
        if detailed_files:
            latest_file = max(detailed_files, key=os.path.getctime)
            print(f"📋 找到已有baseline结果: {Path(latest_file).name}")
            return Path(latest_file)
        
        # 如果没有找到，尝试在旧的results目录查找
        old_results_dir = self.project_root / "results"
        old_files = glob.glob(str(old_results_dir / search_pattern))
        old_detailed_files = [f for f in old_files if 'standardized' not in f and 'user_format' not in f]
        
        if old_detailed_files:
            latest_file = max(old_detailed_files, key=os.path.getctime)
            print(f"📋 找到旧的baseline结果: {Path(latest_file).name}")
            return Path(latest_file)
        
        # 如果都没有找到，自动运行baseline评估
        print(f"🚨 未找到报告ID {self.report_id} 的baseline结果，正在自动生成...")
        return self._run_baseline_evaluation()

    def _run_baseline_evaluation(self) -> Path:
        """运行baseline评估并返回结果文件路径"""
        print(f"\n🔄 正在为报告 {self.report_id} 运行baseline评估...")
        
        # 加载测试数据
        from data_loader import DataLoader
        data_loader = DataLoader()
        
        # 寻找测试文件
        test_data_path = Path("/home/duojiechen/Central_Data/Testset_0_43000-43508/diagnostic_results_normalized")
        test_file = test_data_path / f"diagnostic_{self.report_id}.json"
        
        if not test_file.exists():
            raise FileNotFoundError(f"测试文件不存在: {test_file}")
        
        # 加载报告数据
        report_data = data_loader.load_report_data(test_file)
        if 'error' in report_data:
            raise ValueError(f"加载报告数据失败: {report_data['error']}")
        
        print(f"📄 已加载报告数据，包含 {len(report_data.get('symptoms', []))} 个症状")
        
        # 处理报告 - 使用与main_workflow.py相同的逻辑
        report_results = self._process_baseline_report(report_data)
        
        # 保存结果到统一目录
        result_file = self._save_baseline_results(report_results)
        
        print(f"✅ Baseline评估完成，结果保存至: {result_file}")
        return result_file

    def _process_baseline_report(self, report_data: Dict[str, Any]) -> Dict[str, Any]:
        """处理baseline报告，与main_workflow.py逻辑一致"""
        report_id = report_data.get('report_id', 'unknown')
        symptoms = report_data.get('symptoms', [])
        
        print(f"🔄 正在处理baseline报告 {report_id}，包含 {len(symptoms)} 个症状")
        
        report_results = {
            'report_id': report_id,
            'timestamp': datetime.now().isoformat(),
            'symptoms': [],
            'token_summary': {
                'total_tokens': 0,
                'total_prompt_tokens': 0,
                'total_completion_tokens': 0,
                'api_breakdown': {}
            }
        }
        
        # 加载系统提示词
        system_prompt_path = Path("prompt/system_prompt.txt")
        if system_prompt_path.exists():
            with open(system_prompt_path, 'r', encoding='utf-8') as f:
                system_prompt = f.read().strip()
        else:
            system_prompt = "你是一个医学专家，请根据症状识别相关的器官和解剖位置。"
        
        # 处理每个症状
        for i, symptom_item in enumerate(symptoms, 1):
            symptom_id = symptom_item.get('symptom_id', 'unknown')
            symptom_text = symptom_item.get('symptom_text', '')
            
            print(f"  🔄 处理症状 {i}/{len(symptoms)}: {symptom_text[:50]}...")
            
            # 提取期望的器官信息
            expected_organs = symptom_item.get('expected_results', [])
            
            try:
                # 调用API处理症状（baseline，不使用RAG）
                api_result = self.api_manager.process_symptom(symptom_item, system_prompt)
                
                # 构建症状数据结构
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
                        'anatomical_locations': response.get('anatomical_locations', []),
                        'success': response.get('success', False),
                        'model': response.get('model', ''),
                        'usage': response.get('usage', {}),  # 关键：保存token使用信息
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
                print(f"    ❌ {error_msg}")
                
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

    def _save_baseline_results(self, report_results: Dict[str, Any]) -> Path:
        """保存baseline结果到统一目录"""
        report_id = report_results['report_id']
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 保存详细结果
        detailed_filename = f"report_diagnostic_{report_id}_evaluation_{timestamp}.json"
        detailed_path = self.baseline_results_dir / detailed_filename
        
        with open(detailed_path, 'w', encoding='utf-8') as f:
            json.dump(report_results, f, ensure_ascii=False, indent=2)
        
        # 显示token统计摘要
        token_summary = report_results.get('token_summary', {})
        total_tokens = token_summary.get('total_tokens', 0)
        if total_tokens > 0:
            print(f"📊 Token使用统计: {total_tokens:,} tokens")
            for api, stats in token_summary.get('api_breakdown', {}).items():
                if stats['calls'] > 0:
                    print(f"  {api.upper():12}: {stats['total_tokens']:,} tokens ({stats['calls']}次调用)")
        
        print(f"💾 Baseline结果已保存: {detailed_path}")
        return detailed_path

    def _evaluate_rag_quality(self, rag_results: Dict[str, Any]) -> Tuple[float, str]:
        """评估RAG结果的质量和可靠性，加入信息一致性检查"""
        if not rag_results:
            return 0.0, "无检索结果"
        
        total_refs = 0
        quality_score = 0.0
        quality_indicators = []
        
        # 收集所有器官信息用于一致性检查
        all_organs = []
        all_locations = []
        
        for key, value in rag_results.items():
            if isinstance(value, dict) and 'units' in value:
                for unit in value.get('units', []):
                    total_refs += 1
                    u_unit = unit.get('u_unit', {})
                    text = u_unit.get('d_diagnosis', '')
                    organ = u_unit.get('o_organ', {})
                    
                    # 收集器官和位置信息
                    if organ and isinstance(organ, dict):
                        organ_name = organ.get('organName', '')
                        locations = organ.get('anatomicalLocations', [])
                        if organ_name:
                            all_organs.append(organ_name)
                        if locations:
                            all_locations.extend(locations)
                    
                    # 基础质量评估因子
                    if len(text) > 30:  # 详细的诊断文本
                        quality_score += 0.3
                    if organ and isinstance(organ, dict):  # 有器官信息
                        quality_score += 0.2
                        if organ.get('anatomicalLocations'):  # 有解剖位置
                            quality_score += 0.2
                    if any(medical_term in text.lower() for medical_term in 
                           ['diagnosis', 'condition', 'disease', 'syndrome', 'disorder']):
                        quality_score += 0.1
        
        if total_refs > 0:
            avg_quality = quality_score / total_refs
            quality_indicators.append(f"检索到{total_refs}条结果")
            
            # 信息一致性检查 - 这是关键改进！
            consistency_penalty = 0.0
            unique_organs = set(all_organs)
            unique_locations = set(all_locations)
            
            # 如果器官信息不一致（超过1个不同的器官），大幅降低质量
            if len(unique_organs) > 1:
                consistency_penalty += 0.4  # 重大惩罚
                quality_indicators.append(f"器官信息不一致({len(unique_organs)}种器官)")
                
            # 如果解剖位置过于分散，也降低质量
            if len(unique_locations) > 5:  # 超过5个不同位置认为过于分散
                consistency_penalty += 0.2
                quality_indicators.append("解剖位置信息过于分散")
                
            # 应用一致性惩罚
            avg_quality = max(0.0, avg_quality - consistency_penalty)
            
            # 重新分类质量等级
            if avg_quality > 0.6:
                quality_indicators.append("质量较高")
            elif avg_quality > 0.3:
                quality_indicators.append("质量中等")
            else:
                quality_indicators.append("质量较低")
                
            # 特别标记不一致的情况
            if consistency_penalty > 0:
                if consistency_penalty >= 0.4:
                    quality_indicators.append("信息冲突严重")
                else:
                    quality_indicators.append("信息轻微冲突")
        else:
            avg_quality = 0.0
            quality_indicators.append("无有效结果")
        
        return min(avg_quality, 1.0), "; ".join(quality_indicators)

    def _convert_new_rag_format(self, new_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """将新的RAG检索格式转换为旧格式兼容的结构"""
        converted = {}
        
        for i, result in enumerate(new_results):
            if "related_units" not in result:
                continue
                
            # 为每个结果创建一个rag_s_id
            rag_s_id = f"rag_s_{i+1}_id"
            
            # 提取症状文本
            symptom_text = result.get("symptom_data", {}).get("s_text", "")
            
            # 转换related_units为旧格式的units
            units = []
            for unit in result.get("related_units", []):
                converted_unit = {
                    "u_id": unit.get("u_id", ""),
                    "u_unit": {
                        "d_diagnosis": unit.get("diagnosis_text", ""),
                        "o_organ": unit.get("organ", {}),
                        "b_textual_basis": {
                            "medicalInference": unit.get("basis_text", "")
                        }
                    }
                }
                units.append(converted_unit)
            
            converted[rag_s_id] = {
                "s_text": symptom_text,
                "units": units
            }
        
        return converted

    def _filter_consistent_rag_info(self, rag_results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """过滤掉冲突的RAG信息，保留最一致的信息"""
        if not rag_results:
            return []
        
        # 收集所有信息
        all_info = []
        organ_counts = {}
        
        for key, value in rag_results.items():
            if isinstance(value, dict) and 'units' in value:
                for unit in value.get('units', []):
                    u_unit = unit.get('u_unit', {})
                    text = u_unit.get('d_diagnosis', '')
                    organ = u_unit.get('o_organ', {})
                    
                    if organ and isinstance(organ, dict):
                        organ_name = organ.get('organName', '')
                        if organ_name:
                            info_item = {'text': text, 'organ': organ}
                            all_info.append(info_item)
                            organ_counts[organ_name] = organ_counts.get(organ_name, 0) + 1
        
        if not organ_counts:
            return []
        
        # 找到最常见的器官（认为是最可能正确的）
        most_common_organ = max(organ_counts, key=organ_counts.get)
        
        # 如果所有信息都指向同一个器官，返回所有信息
        if len(organ_counts) == 1:
            return all_info
        
        # 如果有冲突，只保留最常见器官的信息
        filtered_info = [info for info in all_info 
                        if info['organ'].get('organName') == most_common_organ]
        
        return filtered_info

    def _build_augmented_prompt(self, original_query: str, rag_results: Dict[str, Any]) -> str:
        """
        构建智能增强型Prompt，让LLM可以选择性相信RAG
        """
        # 评估RAG质量
        rag_quality, quality_desc = self._evaluate_rag_quality(rag_results)
        
        # 过滤掉冲突的信息，保留一致的高质量信息
        primary_refs = self._filter_consistent_rag_info(rag_results)

        def fmt_ref(ref: Dict[str, Any]) -> str:
            organ_part = ""
            organ = ref.get('organ')
            if organ and isinstance(organ, dict):
                name = organ.get('organName', '')
                locs = organ.get('anatomicalLocations', [])
                loc_str = ", ".join(locs)
                organ_part = f" | organ: {name} | locations: {loc_str}"
            text = ref.get('text', '')
            return f"- {text}{organ_part}".strip()

        # 构建智能提示词
        aug_parts = [
            "🔍 症状分析任务：",
            f"症状：{original_query.strip()}",
            "",
        ]
        
        # 根据RAG质量调整策略
        if primary_refs and rag_quality > 0.0:
            primary_block = "\n".join([fmt_ref(r) for r in primary_refs])
            
            # 决策策略基于质量和一致性
            if "信息冲突严重" in quality_desc:
                strategy = "⚠️ 决策策略：检索信息存在严重冲突，建议主要依据您的医学知识，谨慎使用检索信息"
            elif "信息冲突" in quality_desc:
                strategy = "🛡️ 决策策略：检索信息存在冲突，建议优先使用医学常识，检索信息仅作参考"
            elif rag_quality > 0.6:
                strategy = "🎯 决策策略：检索信息质量较高且一致，建议重点参考但需结合医学常识判断"
            elif rag_quality > 0.3:
                strategy = "⚖️ 决策策略：检索信息质量中等，建议谨慎参考，优先依据医学专业知识"
            else:
                strategy = "🛡️ 决策策略：检索信息质量较低，建议主要依据医学常识，检索信息仅作辅助参考"
            
            aug_parts.extend([
                f"📚 检索系统提供的参考信息：",
                f"💡 质量评估：{quality_desc} (质量评分: {rag_quality:.2f})",
                "",
                "参考内容：",
                primary_block,
                "",
                strategy,
                "",
                "请综合以上信息进行分析：",
                "1. 优先使用您的医学专业知识",
                "2. 理性评估检索信息的可靠性和相关性", 
                "3. 当检索信息与医学常识冲突时，请相信您的专业判断",
                "4. 说明您的决策理由",
                "",
                "请严格按照JSON格式输出：",
                "{",
                '  "organ": "主要相关器官",',
                '  "anatomical_locations": ["解剖位置1", "解剖位置2", ...],',
                f'  "rag_quality_used": {rag_quality:.2f},',
                '  "decision_rationale": "简述决策理由和参考信息使用情况"',
                "}"
            ])
        else:
            # 没有RAG信息或质量很差时，回退到基础模式
            aug_parts.extend([
                "📚 检索系统未提供有效的参考信息",
                "",
                "请基于您的医学专业知识进行分析：",
                "",
                "请严格按照JSON格式输出：",
                "{",
                '  "organ": "主要相关器官",',
                '  "anatomical_locations": ["解剖位置1", "解剖位置2", ...],',
                '  "rag_quality_used": 0.0,',
                '  "decision_rationale": "基于医学常识的独立判断"',
                "}"
            ])
        
        return "\n".join(aug_parts)

    def run(self):
        """执行完整的工作流程"""
        try:
            # 1. 初始化API管理器
            print("\n🔧 初始化API连接...")
            if not self.api_manager.initialize_clients(self.config.config):
                print("❌ API客户端初始化失败，请检查配置")
                return
            
            # 2. 查找RAG缓存文件
            rag_cache_file = self.find_latest_rag_cache()
            
            # 3. 查找或创建baseline结果
            baseline_file = self.find_or_create_baseline_results()
            baseline_data = {}
            if baseline_file:
                with open(baseline_file, 'r', encoding='utf-8') as f:
                    baseline_results = json.load(f)
                    # 将baseline结果按症状文本索引，同时保存期望结果
                    for symptom in baseline_results.get('symptoms', []):
                        diagnosis = symptom.get('diagnosis', '')
                        baseline_data[diagnosis] = {
                            'api_responses': symptom.get('api_responses', {}),
                            'expected_organs': symptom.get('expected_organs', [])
                        }
            
            # 4. 处理RAG缓存文件
            all_rag_results = {}
            all_comparisons = {}
            
            # 初始化token统计
            rag_token_summary = {
                'total_tokens': 0,
                'total_prompt_tokens': 0,
                'total_completion_tokens': 0,
                'api_breakdown': {}
            }
            
            print(f"\n🚀 开始处理RAG缓存文件...")
            
            # 加载系统提示词
            system_prompt_path = Path("prompt/system_prompt.txt")
            system_prompt = system_prompt_path.read_text(encoding='utf-8') if system_prompt_path.exists() else "你是一个医学专家，请根据症状识别相关的器官和解剖位置。"
            
            with open(rag_cache_file, 'r', encoding='utf-8') as f:
                for i, line in enumerate(f):
                    try:
                        data = json.loads(line)
                        original_query = data.get("query", "").strip()
                        # 兼容新旧RAG格式：新格式使用rag_results，旧格式使用s
                        if "rag_results" in data and "results" in data["rag_results"]:
                            # 新格式：转换为旧格式兼容的结构
                            rag_s_block = self._convert_new_rag_format(data["rag_results"]["results"])
                        else:
                            # 旧格式
                            rag_s_block = data.get("s", {})
                        
                        if not original_query:
                            print(f"⚠️  第 {i+1} 行缺少 'query' 字段，跳过。")
                            continue
                            
                        print(f"\n--- 正在处理症状 {i+1}: {original_query[:50]}... ---")
                        
                        # 构建增强型Prompt
                        augmented_prompt = self._build_augmented_prompt(original_query, rag_s_block)
                        
                        # 调用所有API进行处理
                        symptom_item_for_api = {
                            'symptom_id': f'rerun_{self.report_id}_{i}',
                            'symptom_text': augmented_prompt,
                            'expected_results': []  # 可以从原始数据中提取
                        }
                        
                        api_results = self.api_manager.process_symptom(symptom_item_for_api, system_prompt)
                        
                        # 为每个API结果添加评估（如果有期望结果）
                        for api_name, response in api_results.items():
                            if response.get('success') and response.get('parsed_data'):
                                # 这里可以添加评估逻辑，但目前我们只关注API响应
                                pass
                            
                            # 统计RAG增强的token使用
                            if 'usage' in response and response['usage']:
                                usage = response['usage']
                                total_tokens = usage.get('total_tokens', 0)
                                prompt_tokens = usage.get('prompt_tokens', 0)
                                completion_tokens = usage.get('completion_tokens', 0)
                                
                                # 更新总计
                                rag_token_summary['total_tokens'] += total_tokens
                                rag_token_summary['total_prompt_tokens'] += prompt_tokens
                                rag_token_summary['total_completion_tokens'] += completion_tokens
                                
                                # 更新API分解
                                if api_name not in rag_token_summary['api_breakdown']:
                                    rag_token_summary['api_breakdown'][api_name] = {
                                        'total_tokens': 0,
                                        'prompt_tokens': 0,
                                        'completion_tokens': 0,
                                        'calls': 0
                                    }
                                
                                api_breakdown = rag_token_summary['api_breakdown'][api_name]
                                api_breakdown['total_tokens'] += total_tokens
                                api_breakdown['prompt_tokens'] += prompt_tokens
                                api_breakdown['completion_tokens'] += completion_tokens
                                api_breakdown['calls'] += 1
                        
                        all_rag_results[original_query] = {
                            'api_responses': api_results,
                            'rag_context': rag_s_block,
                            'augmented_prompt': augmented_prompt
                        }
                        
                        # 如果有baseline数据，进行对比
                        if original_query in baseline_data:
                            baseline_info = baseline_data[original_query]
                            baseline_api_responses = baseline_info['api_responses']
                            expected_results = baseline_info['expected_organs']  # 使用baseline中的期望结果
                            comparison = self._compare_responses(baseline_api_responses, api_results, expected_results)
                            all_comparisons[original_query] = comparison
                        
                        print(f"✅ 完成症状处理: {original_query[:30]}...")
                        
                    except json.JSONDecodeError:
                        print(f"⚠️  第 {i+1} 行不是有效的JSON格式，跳过。")
                    except Exception as e:
                        print(f"❌ 处理第 {i+1} 行时出错: {e}")
                        
            # 5. 保存最终结果
            if all_rag_results:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                
                # 构建完整的RAG结果（包含token统计）
                complete_rag_results = {
                    'report_id': self.report_id,
                    'timestamp': datetime.now().isoformat(),
                    'symptoms': all_rag_results,
                    'token_summary': rag_token_summary
                }
                
                # 保存RAG增强结果
                rag_output_filename = self.rerun_results_dir / f"report_{self.report_id}_withRAG_{timestamp}.json"
                with open(rag_output_filename, 'w', encoding='utf-8') as f:
                    json.dump(complete_rag_results, f, ensure_ascii=False, indent=2)
                
                # 显示token统计摘要
                total_tokens = rag_token_summary.get('total_tokens', 0)
                if total_tokens > 0:
                    print(f"\n📊 RAG增强Token使用统计: {total_tokens:,} tokens")
                    for api, stats in rag_token_summary.get('api_breakdown', {}).items():
                        if stats['calls'] > 0:
                            print(f"  {api.upper():12}: {stats['total_tokens']:,} tokens ({stats['calls']}次调用)")
                
                print(f"\n✅ RAG增强结果已保存: {rag_output_filename}")
                
                # 保存对比结果（如果有）
                if all_comparisons:
                    comparison_filename = self.comparison_results_dir / f"report_{self.report_id}_comparison_{timestamp}.json"
                    with open(comparison_filename, 'w', encoding='utf-8') as f:
                        json.dump(all_comparisons, f, ensure_ascii=False, indent=2)
                    
                    print(f"✅ 对比结果已保存: {comparison_filename}")
                    
                    # 生成简化的评测结果文件
                    simplified_filename = self.comparison_results_dir / f"report_{self.report_id}_evaluation_summary_{timestamp}.json"
                    simplified_results = self._generate_evaluation_summary(all_comparisons, baseline_data)
                    with open(simplified_filename, 'w', encoding='utf-8') as f:
                        json.dump(simplified_results, f, ensure_ascii=False, indent=2)
                    
                    print(f"✅ 评测摘要已保存: {simplified_filename}")
                    
                    # 创建专门的结果文件夹并生成分数报告
                    result_folder = self.comparison_results_dir / f"report_{self.report_id}_results_{timestamp}"
                    result_folder.mkdir(exist_ok=True)
                    
                    # 移动evaluation_summary到新文件夹
                    new_summary_path = result_folder / f"report_{self.report_id}_evaluation_summary.json"
                    shutil.move(str(simplified_filename), str(new_summary_path))
                    
                    # 生成分数报告
                    score_report_path = self._generate_score_report(simplified_results, result_folder, timestamp)
                    
                    print(f"✅ 分数报告已保存: {score_report_path}")
                    print(f"📁 完整结果已保存到: {result_folder}")
                
                print("\n🎉 ===== 任务完成! =====")
                print(f"📊 成功处理了 {len(all_rag_results)} 个症状")
                print(f"\n📁 生成的文件:")
                print(f"  📋 Baseline结果: {baseline_file}")
                print(f"  💾 RAG增强结果: {rag_output_filename}")
                if all_comparisons:
                    print(f"  📈 详细对比结果: {comparison_filename}")
                    print(f"  📂 完整结果文件夹: {result_folder}")
                    print(f"    ├── 📝 评测摘要 (JSON): report_{self.report_id}_evaluation_summary.json")
                    print(f"    └── 📊 分数报告 (TXT): report_{self.report_id}_rag_score_report.txt")
                    print(f"\n✨ 分数报告包含:")
                    print(f"     - 总体效果概览 (改善/负面/无变化比例)")
                    print(f"     - 平均指标改善 (精确率、召回率、F1分数、综合得分)")
                    print(f"     - 各症状详细分析")
                    print(f"     - 结论与建议 (最佳/最差API，总体RAG效果评估)")

        except FileNotFoundError as e:
            print(f"\n❌ 错误: {e}")
            print("   请确保您已为该报告ID成功运行了RAG检索步骤。")
        except Exception as e:
            print(f"\n❌ 工作流程执行时发生严重错误: {e}")
            logging.error(f"工作流程失败: {e}", exc_info=True)

    def _compare_responses(self, baseline_responses: Dict[str, Any], rag_responses: Dict[str, Any], expected_results: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        """对比baseline和RAG增强的API响应，包含详细的评估指标"""
        comparison = {}
        
        # 找到共同的API
        common_apis = set(baseline_responses.keys()) & set(rag_responses.keys())
        
        # 准备期望的解剖位置用于评估
        expected_locations = []
        expected_organs = []
        if expected_results:
            for expected_result in expected_results:
                expected_locations.extend(expected_result.get('anatomicalLocations', []))
                organ_name = expected_result.get('organName', '')
                if organ_name:
                    expected_organs.append(organ_name)
        expected_locations = list(set(expected_locations))  # 去重
        expected_organs = list(set(expected_organs))  # 去重
        
        for api_name in common_apis:
            baseline_resp = baseline_responses.get(api_name, {})
            rag_resp = rag_responses.get(api_name, {})
            
            # 提取基本信息
            baseline_organ = baseline_resp.get('organ_name', '')
            rag_organ = rag_resp.get('organ_name', '')
            baseline_locations = baseline_resp.get('anatomical_locations', [])
            rag_locations = rag_resp.get('anatomical_locations', [])
            
            # 计算器官准确率
            baseline_organ_accuracy = self._calculate_organ_accuracy(baseline_organ, expected_organs)
            rag_organ_accuracy = self._calculate_organ_accuracy(rag_organ, expected_organs)
            
            # 计算解剖位置评估指标
            baseline_metrics = self._calculate_location_metrics(baseline_locations, expected_locations)
            rag_metrics = self._calculate_location_metrics(rag_locations, expected_locations)
            
            # 计算改善情况
            metrics_improvement = {
                'precision_improvement': rag_metrics['precision'] - baseline_metrics['precision'],
                'recall_improvement': rag_metrics['recall'] - baseline_metrics['recall'],
                'f1_improvement': rag_metrics['f1_score'] - baseline_metrics['f1_score'],
                'overall_improvement': rag_metrics['overall_score'] - baseline_metrics['overall_score']
            }
            
            comparison[api_name] = {
                # 基本对比信息
                'baseline_organ': baseline_organ,
                'rag_organ': rag_organ,
                'baseline_locations': baseline_locations,
                'rag_locations': rag_locations,
                'organ_changed': baseline_organ != rag_organ,
                'locations_changed': baseline_locations != rag_locations,
                
                # 器官准确率评估
                'baseline_organ_accuracy': baseline_organ_accuracy,
                'rag_organ_accuracy': rag_organ_accuracy,
                'organ_accuracy_improved': rag_organ_accuracy['category'] == 'exact_match' and baseline_organ_accuracy['category'] != 'exact_match',
                
                # 解剖位置评估指标
                'baseline_metrics': baseline_metrics,
                'rag_metrics': rag_metrics,
                'metrics_improvement': metrics_improvement,
                
                # 综合评估
                'overall_assessment': self._assess_overall_improvement(baseline_metrics, rag_metrics, baseline_organ_accuracy, rag_organ_accuracy)
            }
        
        return comparison

    def _calculate_organ_accuracy(self, predicted_organ: str, expected_organs: List[str]) -> Dict[str, Any]:
        """计算器官准确率"""
        if not expected_organs:
            return {
                'category': 'unknown',
                'score': 0.0,
                'description': '无期望器官信息'
            }
        
        if not predicted_organ:
            return {
                'category': 'incorrect',
                'score': 0.0,
                'description': '未识别出任何器官'
            }
        
        # 精确匹配
        if predicted_organ in expected_organs:
            return {
                'category': 'exact_match',
                'score': 1.0,
                'description': f'精确匹配期望器官: {predicted_organ}'
            }
        
        # 部分匹配检查（简单的包含关系）
        for expected_organ in expected_organs:
            if (predicted_organ.lower() in expected_organ.lower() or 
                expected_organ.lower() in predicted_organ.lower()):
                return {
                    'category': 'partial_match',
                    'score': 0.6,
                    'description': f'部分匹配: 预测"{predicted_organ}" vs 期望"{expected_organ}"'
                }
        
        # 完全错误
        return {
            'category': 'incorrect',
            'score': 0.0,
            'description': f'完全错误: 预测"{predicted_organ}" 不匹配期望{expected_organs}'
        }

    def _calculate_location_metrics(self, predicted_locations: List[str], expected_locations: List[str]) -> Dict[str, float]:
        """计算解剖位置的各项评估指标"""
        if not expected_locations:
            return {
                'precision': 0.0,
                'recall': 0.0,
                'f1_score': 0.0,
                'overgeneration_penalty': 0.0,
                'overall_score': 0.0
            }
        
        if not predicted_locations:
            return {
                'precision': 0.0,
                'recall': 0.0,
                'f1_score': 0.0,
                'overgeneration_penalty': 0.0,
                'overall_score': 0.0
            }
        
        # 计算正确识别的数量
        correct_count = 0
        for location in predicted_locations:
            if location in expected_locations:
                correct_count += 1
        
        # 精确率 = 正确识别数量 / 预测总数量
        precision = correct_count / len(predicted_locations)
        
        # 召回率 = 正确识别数量 / 期望总数量
        recall = correct_count / len(expected_locations)
        
        # F1分数
        f1_score = 0.0
        if precision + recall > 0:
            f1_score = 2 * (precision * recall) / (precision + recall)
        
        # 过度生成惩罚
        over_generation = max(0, len(predicted_locations) - len(expected_locations))
        overgeneration_penalty = 1.0 - (over_generation / max(len(expected_locations), 1))
        overgeneration_penalty = max(0.0, overgeneration_penalty)
        
        # 综合得分 (100分制)
        overall_score = (precision * 0.4 + recall * 0.4 + overgeneration_penalty * 0.2) * 100
        
        return {
            'precision': round(precision * 100, 1),
            'recall': round(recall * 100, 1),
            'f1_score': round(f1_score * 100, 1),
            'overgeneration_penalty': round(overgeneration_penalty * 100, 1),
            'overall_score': round(overall_score, 1)
        }

    def _assess_overall_improvement(self, baseline_metrics: Dict[str, float], rag_metrics: Dict[str, float], 
                                  baseline_organ: Dict[str, Any], rag_organ: Dict[str, Any]) -> str:
        """评估RAG增强的整体改善情况"""
        improvements = []
        
        # 器官准确率改善
        if rag_organ['score'] > baseline_organ['score']:
            improvements.append(f"器官识别改善 ({baseline_organ['category']} → {rag_organ['category']})")
        
        # 各项指标改善
        if rag_metrics['precision'] > baseline_metrics['precision']:
            improvements.append(f"精确率提升 {rag_metrics['precision'] - baseline_metrics['precision']:.1f}%")
        
        if rag_metrics['recall'] > baseline_metrics['recall']:
            improvements.append(f"召回率提升 {rag_metrics['recall'] - baseline_metrics['recall']:.1f}%")
        
        if rag_metrics['f1_score'] > baseline_metrics['f1_score']:
            improvements.append(f"F1分数提升 {rag_metrics['f1_score'] - baseline_metrics['f1_score']:.1f}%")
        
        if rag_metrics['overall_score'] > baseline_metrics['overall_score']:
            improvements.append(f"综合得分提升 {rag_metrics['overall_score'] - baseline_metrics['overall_score']:.1f}分")
        
        if improvements:
            return "✅ RAG增强有效: " + "; ".join(improvements)
        elif rag_metrics['overall_score'] == baseline_metrics['overall_score']:
            return "⚪ RAG增强无明显影响"
        else:
            return "❌ RAG增强可能产生负面影响"

    def _generate_evaluation_summary(self, all_comparisons: Dict[str, Any], baseline_data: Dict[str, Any]) -> Dict[str, Any]:
        """生成简化的评测结果摘要，按用户要求的格式"""
        evaluation_summary = {}
        
        for symptom_text, comparisons in all_comparisons.items():
            # 获取期望结果
            expected_organs = []
            expected_locations = []
            if symptom_text in baseline_data:
                for expected_result in baseline_data[symptom_text]['expected_organs']:
                    if isinstance(expected_result, dict):
                        organ_name = expected_result.get('organName', '')
                        locations = expected_result.get('anatomicalLocations', [])
                        if organ_name:
                            expected_organs.append(organ_name)
                        expected_locations.extend(locations)
            
            # 去重
            expected_organs = list(set(expected_organs))
            expected_locations = list(set(expected_locations))
            
            symptom_summary = {
                "expected_outcome": {
                    "organs": expected_organs,
                    "anatomical_locations": expected_locations
                }
            }
            
            # 为每个API生成对比结果
            for api_name, comparison in comparisons.items():
                # Baseline API结果
                baseline_outcome = {
                    "organ": comparison.get('baseline_organ', ''),
                    "anatomical_locations": comparison.get('baseline_locations', []),
                    "metrics": comparison.get('baseline_metrics', {}),
                    "organ_accuracy": comparison.get('baseline_organ_accuracy', {})
                }
                
                # RAG增强结果
                rag_outcome = {
                    "organ": comparison.get('rag_organ', ''),
                    "anatomical_locations": comparison.get('rag_locations', []),
                    "metrics": comparison.get('rag_metrics', {}),
                    "organ_accuracy": comparison.get('rag_organ_accuracy', {})
                }
                
                # 改善分析
                improvement_analysis = {
                    "metrics_improvement": comparison.get('metrics_improvement', {}),
                    "assessment": comparison.get('overall_assessment', ''),
                    "organ_improved": comparison.get('organ_accuracy_improved', False),
                    "locations_changed": comparison.get('locations_changed', False)
                }
                
                symptom_summary[f"{api_name}_baseline_outcome"] = baseline_outcome
                symptom_summary[f"{api_name}_with_rag_outcome"] = rag_outcome
                symptom_summary[f"{api_name}_improvement"] = improvement_analysis
            
            # 使用症状文本的前50个字符作为键名
            symptom_key = symptom_text[:50] + "..." if len(symptom_text) > 50 else symptom_text
            evaluation_summary[symptom_key] = symptom_summary
        
        return {
            "report_id": self.report_id,
            "timestamp": datetime.now().isoformat(),
            "total_symptoms": len(evaluation_summary),
            "symptoms": evaluation_summary
        }

    def _generate_score_report(self, simplified_results: Dict[str, Any], result_folder: Path, timestamp: str) -> Path:
        """生成RAG效果分数报告 (TXT格式)"""
        report_path = result_folder / f"report_{self.report_id}_rag_score_report.txt"
        
        # 收集所有API名称
        api_names = set()
        for symptom_data in simplified_results['symptoms'].values():
            for key in symptom_data.keys():
                if key.endswith('_improvement'):
                    api_name = key.replace('_improvement', '')
                    api_names.add(api_name)
        
        api_names = sorted(list(api_names))
        
        # 准备统计数据
        api_stats = {}
        for api_name in api_names:
            api_stats[api_name] = {
                'precision_improvements': [],
                'recall_improvements': [],
                'f1_improvements': [],
                'overall_improvements': [],
                'positive_effects': 0,
                'negative_effects': 0,
                'no_effects': 0,
                'organ_improvements': 0
            }
        
        # 收集每个症状的数据
        symptom_details = []
        for symptom_name, symptom_data in simplified_results['symptoms'].items():
            symptom_info = {
                'name': symptom_name,
                'apis': {}
            }
            
            for api_name in api_names:
                improvement_key = f"{api_name}_improvement"
                if improvement_key in symptom_data:
                    improvement = symptom_data[improvement_key]
                    metrics = improvement.get('metrics_improvement', {})
                    
                    # 收集统计数据
                    precision_imp = metrics.get('precision_improvement', 0)
                    recall_imp = metrics.get('recall_improvement', 0)
                    f1_imp = metrics.get('f1_improvement', 0)
                    overall_imp = metrics.get('overall_improvement', 0)
                    
                    api_stats[api_name]['precision_improvements'].append(precision_imp)
                    api_stats[api_name]['recall_improvements'].append(recall_imp)
                    api_stats[api_name]['f1_improvements'].append(f1_imp)
                    api_stats[api_name]['overall_improvements'].append(overall_imp)
                    
                    # 分类效果
                    if overall_imp > 0:
                        api_stats[api_name]['positive_effects'] += 1
                    elif overall_imp < 0:
                        api_stats[api_name]['negative_effects'] += 1
                    else:
                        api_stats[api_name]['no_effects'] += 1
                    
                    # 器官改善
                    if improvement.get('organ_improved', False):
                        api_stats[api_name]['organ_improvements'] += 1
                    
                    # 保存症状详情
                    symptom_info['apis'][api_name] = {
                        'precision_improvement': precision_imp,
                        'recall_improvement': recall_imp,
                        'f1_improvement': f1_imp,
                        'overall_improvement': overall_imp,
                        'assessment': improvement.get('assessment', ''),
                        'organ_improved': improvement.get('organ_improved', False),
                        'locations_changed': improvement.get('locations_changed', False)
                    }
            
            symptom_details.append(symptom_info)
        
        # 计算平均值
        for api_name in api_names:
            stats = api_stats[api_name]
            if stats['precision_improvements']:
                stats['avg_precision'] = sum(stats['precision_improvements']) / len(stats['precision_improvements'])
                stats['avg_recall'] = sum(stats['recall_improvements']) / len(stats['recall_improvements'])
                stats['avg_f1'] = sum(stats['f1_improvements']) / len(stats['f1_improvements'])
                stats['avg_overall'] = sum(stats['overall_improvements']) / len(stats['overall_improvements'])
            else:
                stats['avg_precision'] = 0.0
                stats['avg_recall'] = 0.0
                stats['avg_f1'] = 0.0
                stats['avg_overall'] = 0.0
        
        # 生成报告
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write("=" * 80 + "\n")
            f.write(f"RAG 效果分析报告 - Report {self.report_id}\n")
            f.write("=" * 80 + "\n")
            f.write(f"生成时间: {timestamp}\n")
            f.write(f"总症状数: {len(symptom_details)}\n")
            f.write(f"评测APIs: {', '.join(api_names)}\n")
            f.write("\n")
            
            # 1. 总体效果概览
            f.write("█ 总体效果概览\n")
            f.write("-" * 60 + "\n")
            for api_name in api_names:
                stats = api_stats[api_name]
                total_symptoms = len(stats['overall_improvements'])
                f.write(f"\n【{api_name.upper()}】\n")
                f.write(f"  ✅ 改善症状: {stats['positive_effects']}/{total_symptoms} ({stats['positive_effects']/total_symptoms*100:.1f}%)\n")
                f.write(f"  ❌ 负面影响: {stats['negative_effects']}/{total_symptoms} ({stats['negative_effects']/total_symptoms*100:.1f}%)\n")
                f.write(f"  ⚪ 无明显变化: {stats['no_effects']}/{total_symptoms} ({stats['no_effects']/total_symptoms*100:.1f}%)\n")
                f.write(f"  🎯 器官识别改善: {stats['organ_improvements']}/{total_symptoms} ({stats['organ_improvements']/total_symptoms*100:.1f}%)\n")
            f.write("\n")
            
            # 2. 平均指标改善
            f.write("█ 平均指标改善\n")
            f.write("-" * 60 + "\n")
            f.write(f"{'API':<12} {'精确率':<10} {'召回率':<10} {'F1分数':<10} {'综合得分':<10}\n")
            f.write("-" * 60 + "\n")
            for api_name in api_names:
                stats = api_stats[api_name]
                f.write(f"{api_name:<12} ")
                f.write(f"{stats['avg_precision']:+6.1f}%   ")
                f.write(f"{stats['avg_recall']:+6.1f}%   ")
                f.write(f"{stats['avg_f1']:+6.1f}%   ")
                f.write(f"{stats['avg_overall']:+6.1f}分\n")
            f.write("\n")
            
            # 3. 各症状详细分析
            f.write("█ 各症状详细分析\n")
            f.write("-" * 80 + "\n")
            for i, symptom_info in enumerate(symptom_details, 1):
                f.write(f"\n{i}. 【{symptom_info['name']}】\n")
                f.write("-" * 40 + "\n")
                
                for api_name in api_names:
                    if api_name in symptom_info['apis']:
                        api_data = symptom_info['apis'][api_name]
                        f.write(f"\n  [{api_name.upper()}]\n")
                        f.write(f"    精确率改善: {api_data['precision_improvement']:+6.1f}%\n")
                        f.write(f"    召回率改善: {api_data['recall_improvement']:+6.1f}%\n")
                        f.write(f"    F1分数改善: {api_data['f1_improvement']:+6.1f}%\n")
                        f.write(f"    综合得分改善: {api_data['overall_improvement']:+6.1f}分\n")
                        f.write(f"    器官识别改善: {'是' if api_data['organ_improved'] else '否'}\n")
                        f.write(f"    位置信息变化: {'是' if api_data['locations_changed'] else '否'}\n")
                        f.write(f"    总体评估: {api_data['assessment']}\n")
                f.write("\n")
            
            # 4. 结论与建议
            f.write("█ 结论与建议\n")
            f.write("-" * 60 + "\n")
            
            # 找出表现最好和最差的API
            best_api = max(api_names, key=lambda x: api_stats[x]['avg_overall'])
            worst_api = min(api_names, key=lambda x: api_stats[x]['avg_overall'])
            
            f.write(f"\n【最佳表现API】: {best_api.upper()}\n")
            f.write(f"  平均综合得分改善: {api_stats[best_api]['avg_overall']:+.1f}分\n")
            f.write(f"  改善症状比例: {api_stats[best_api]['positive_effects']/len(api_stats[best_api]['overall_improvements'])*100:.1f}%\n")
            
            f.write(f"\n【需要改进API】: {worst_api.upper()}\n")
            f.write(f"  平均综合得分改善: {api_stats[worst_api]['avg_overall']:+.1f}分\n")
            f.write(f"  负面影响症状比例: {api_stats[worst_api]['negative_effects']/len(api_stats[worst_api]['overall_improvements'])*100:.1f}%\n")
            
            # 总体RAG效果评估
            total_positive = sum(stats['positive_effects'] for stats in api_stats.values())
            total_negative = sum(stats['negative_effects'] for stats in api_stats.values())
            total_evaluations = sum(len(stats['overall_improvements']) for stats in api_stats.values())
            
            f.write(f"\n【总体RAG效果】:\n")
            f.write(f"  积极影响: {total_positive}/{total_evaluations} ({total_positive/total_evaluations*100:.1f}%)\n")
            f.write(f"  负面影响: {total_negative}/{total_evaluations} ({total_negative/total_evaluations*100:.1f}%)\n")
            
            if total_positive > total_negative:
                f.write(f"  🎯 结论: RAG增强总体上**有效**，建议继续使用和优化\n")
            elif total_positive < total_negative:
                f.write(f"  ⚠️  结论: RAG增强存在问题，建议检查检索质量和增强策略\n")
            else:
                f.write(f"  ⚪ 结论: RAG增强效果不明显，建议优化检索模型和增强方法\n")
            
            f.write("\n" + "=" * 80 + "\n")
        
        return report_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="使用已有的RAG检索结果重新运行LLM评估。")
    parser.add_argument("report_id", type=int, help="需要处理的报告ID (例如: 4000)")
    parser.add_argument("--config", default="config/config.yaml", help="配置文件路径")
    args = parser.parse_args()

    workflow = RerunWorkflow(args.report_id, args.config)
    workflow.run()
