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
from typing import Dict, List, Any
from pathlib import Path
import glob

# --- 关键：确保脚本能找到src目录下的模块 ---
# 将项目根目录添加到Python路径中
sys.path.append(str(Path(__file__).resolve().parent / "src"))

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
        # RAG缓存文件的存放位置
        self.rag_output_dir = Path("/home/duojiechen/Projects/Rag_system/Rag_Evaluate/final_result/rag_search_output")
        
        # 统一在final_result下管理所有结果
        self.final_result_dir = Path("final_result")
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
        old_results_dir = Path("results")
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
        test_data_path = Path("/home/duojiechen/Projects/Central_Data/RAG_System/test_set")
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
            'symptoms': []
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
        
        print(f"💾 Baseline结果已保存: {detailed_path}")
        return detailed_path

    def _build_augmented_prompt(self, original_query: str, rag_results: Dict[str, Any]) -> str:
        """
        根据RAG结果构建增强型Prompt。
        此逻辑与comparision_workflow.py保持一致。
        """
        primary_refs = []
        if not rag_results:
            return original_query

        # 遍历rag_s_1_id, rag_s_2_id等
        for key, value in rag_results.items():
            if isinstance(value, dict) and 'units' in value:
                for unit in value.get('units', []):
                    u_unit = unit.get('u_unit', {})
                    text = u_unit.get('d_diagnosis', '')
                    organ = u_unit.get('o_organ', {})
                    primary_refs.append({'text': text, 'organ': organ})

        if not primary_refs:
            return original_query

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

        primary_block = "\n".join([fmt_ref(r) for r in primary_refs])
        
        # --- Prompt模板 ---
        aug_parts = [
            "以下是我的症状描述：",
            original_query.strip(),
            "",
            "下面给你一些来自检索系统（RAG）的相关参考，请在回答时以这些参考为主要依据进行推理与归纳，同时严格输出JSON结构：",
            "--- 参考资料 ---",
            primary_block if primary_block else "(无)",
            "--- 请根据以上信息回答 ---",
        ]
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
            
            print(f"\n🚀 开始处理RAG缓存文件...")
            
            # 加载系统提示词
            system_prompt_path = Path("prompt/system_prompt.txt")
            system_prompt = system_prompt_path.read_text(encoding='utf-8') if system_prompt_path.exists() else "你是一个医学专家，请根据症状识别相关的器官和解剖位置。"
            
            with open(rag_cache_file, 'r', encoding='utf-8') as f:
                for i, line in enumerate(f):
                    try:
                        data = json.loads(line)
                        original_query = data.get("query", "").strip()
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
                
                # 保存RAG增强结果
                rag_output_filename = self.rerun_results_dir / f"report_{self.report_id}_withRAG_{timestamp}.json"
                with open(rag_output_filename, 'w', encoding='utf-8') as f:
                    json.dump(all_rag_results, f, ensure_ascii=False, indent=2)
                
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
