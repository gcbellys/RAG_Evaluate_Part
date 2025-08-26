#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API结果重新整理脚本

功能：
1. 将现有的baseline和RAG结果按API分类整理
2. 提取每个API的响应数据
3. 生成评估分数和总结报告
4. 跳过没有响应的API
"""

import json
import os
import glob
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Any
import shutil
from datetime import datetime

class APIResultsReorganizer:
    """API结果重新整理器"""
    
    def __init__(self, base_dir: str = "."):
        """初始化"""
        self.base_dir = Path(base_dir)
        self.apis = ["openai", "anthropic", "gemini", "moonshot", "deepseek"]
        self.results_dir = self.base_dir / "results_of_apis"
        
        # 统计信息
        self.stats = {
            api: {
                "baseline_count": 0,
                "rag_count": 0,
                "total_symptoms": 0,
                "successful_comparisons": 0,
                "failed_responses": 0
            } for api in self.apis
        }
    
    def load_baseline_data(self) -> Dict[str, Dict]:
        """加载baseline数据"""
        print("📁 正在加载baseline数据...")
        baseline_dir = self.base_dir / "baseline_results"
        baseline_data = {}
        
        for file_path in baseline_dir.glob("*.json"):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                report_id = data.get('report_id', file_path.stem)
                baseline_data[report_id] = data
                print(f"  ✅ 加载baseline: {report_id}")
                
            except Exception as e:
                print(f"  ❌ 加载baseline失败: {file_path} - {e}")
        
        print(f"📊 共加载 {len(baseline_data)} 个baseline文件")
        return baseline_data
    
    def load_comparison_data(self) -> Dict[str, Dict]:
        """加载comparison数据"""
        print("📁 正在加载comparison数据...")
        comparison_dir = self.base_dir / "rerun_comparisons"
        comparison_data = {}
        
        for file_path in comparison_dir.glob("*_comparison_*.json"):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # 从文件名提取report_id
                filename = file_path.stem
                if "report_" in filename:
                    parts = filename.split("_")
                    report_id = parts[1]  # report_4000_comparison_timestamp
                    comparison_data[f"diagnostic_{report_id}"] = data  # 修正格式匹配
                    print(f"  ✅ 加载comparison: diagnostic_{report_id}")
                
            except Exception as e:
                print(f"  ❌ 加载comparison失败: {file_path} - {e}")
        
        print(f"📊 共加载 {len(comparison_data)} 个comparison文件")
        return comparison_data
    
    def extract_api_responses(self, baseline_data: Dict, comparison_data: Dict):
        """提取并整理API响应"""
        print("🔄 正在提取和整理API响应...")
        
        for report_id in baseline_data.keys():
            baseline_report = baseline_data[report_id]
            comparison_report = comparison_data.get(report_id, {})
            
            print(f"\n📋 处理报告: {report_id}")
            
            # 处理baseline数据
            self._process_baseline_responses(report_id, baseline_report)
            
            # 处理RAG比较数据
            if comparison_report:
                self._process_rag_responses(report_id, comparison_report)
                self._generate_evaluation_scores(report_id, comparison_report)
            else:
                print(f"  ⚠️ 未找到 {report_id} 的comparison数据")
    
    def _process_baseline_responses(self, report_id: str, baseline_report: Dict):
        """处理baseline响应"""
        symptoms = baseline_report.get('symptoms', [])
        
        for symptom in symptoms:
            symptom_id = symptom.get('symptom_id', 'unknown')
            diagnosis = symptom.get('diagnosis', 'unknown')
            api_responses = symptom.get('api_responses', {})
            
            for api_name, response_data in api_responses.items():
                if api_name in self.apis:
                    # 保存baseline响应
                    baseline_file = self.results_dir / api_name / "baseline_responses" / f"{report_id}_{symptom_id}_baseline.json"
                    
                    response_content = {
                        "report_id": report_id,
                        "symptom_id": symptom_id,
                        "diagnosis": diagnosis,
                        "api_name": api_name,
                        "response_type": "baseline",
                        "response_data": response_data
                    }
                    
                    try:
                        baseline_file.parent.mkdir(parents=True, exist_ok=True)
                        with open(baseline_file, 'w', encoding='utf-8') as f:
                            json.dump(response_content, f, ensure_ascii=False, indent=2)
                        
                        self.stats[api_name]["baseline_count"] += 1
                        print(f"    ✅ 保存baseline响应: {api_name} - {symptom_id}")
                        
                    except Exception as e:
                        print(f"    ❌ 保存baseline响应失败: {api_name} - {e}")
                        self.stats[api_name]["failed_responses"] += 1
    
    def _process_rag_responses(self, report_id: str, comparison_report: Dict):
        """处理RAG响应"""
        for symptom_text, symptom_data in comparison_report.items():
            # 生成symptom_id
            symptom_id = f"{report_id}_{hash(symptom_text) % 10000}"
            
            for api_name, api_data in symptom_data.items():
                if api_name in self.apis:
                    # 保存RAG响应
                    rag_file = self.results_dir / api_name / "rag_responses" / f"{report_id}_{symptom_id}_rag.json"
                    
                    rag_content = {
                        "report_id": report_id,
                        "symptom_id": symptom_id,
                        "symptom_text": symptom_text,
                        "api_name": api_name,
                        "response_type": "rag_augmented",
                        "rag_organ": api_data.get('rag_organ'),
                        "rag_locations": api_data.get('rag_locations'),
                        "organ_changed": api_data.get('organ_changed'),
                        "locations_changed": api_data.get('locations_changed'),
                        "rag_metrics": api_data.get('rag_metrics', {}),
                        "rag_organ_accuracy": api_data.get('rag_organ_accuracy', {})
                    }
                    
                    try:
                        rag_file.parent.mkdir(parents=True, exist_ok=True)
                        with open(rag_file, 'w', encoding='utf-8') as f:
                            json.dump(rag_content, f, ensure_ascii=False, indent=2)
                        
                        self.stats[api_name]["rag_count"] += 1
                        print(f"    ✅ 保存RAG响应: {api_name} - {symptom_id}")
                        
                    except Exception as e:
                        print(f"    ❌ 保存RAG响应失败: {api_name} - {e}")
                        self.stats[api_name]["failed_responses"] += 1
    
    def _generate_evaluation_scores(self, report_id: str, comparison_report: Dict):
        """生成评估分数"""
        # 为每个API生成报告级别的评估分数
        api_scores = defaultdict(list)
        
        for symptom_text, symptom_data in comparison_report.items():
            for api_name, api_data in symptom_data.items():
                if api_name in self.apis:
                    baseline_metrics = api_data.get('baseline_metrics', {})
                    rag_metrics = api_data.get('rag_metrics', {})
                    
                    score_data = {
                        "symptom_text": symptom_text,
                        "baseline_score": baseline_metrics.get('overall_score', 0),
                        "rag_score": rag_metrics.get('overall_score', 0),
                        "improvement": rag_metrics.get('overall_score', 0) - baseline_metrics.get('overall_score', 0),
                        "baseline_metrics": baseline_metrics,
                        "rag_metrics": rag_metrics,
                        "organ_accuracy_improved": api_data.get('organ_accuracy_improved', False)
                    }
                    
                    api_scores[api_name].append(score_data)
        
        # 保存每个API的评估分数
        for api_name, scores in api_scores.items():
            if scores:
                score_file = self.results_dir / api_name / "evaluation_scores" / f"{report_id}_evaluation_scores.json"
                
                # 计算总体统计
                total_improvement = sum(score['improvement'] for score in scores)
                avg_improvement = total_improvement / len(scores) if scores else 0
                improved_count = sum(1 for score in scores if score['improvement'] > 0)
                
                evaluation_data = {
                    "report_id": report_id,
                    "api_name": api_name,
                    "total_symptoms": len(scores),
                    "average_improvement": round(avg_improvement, 2),
                    "improved_symptoms": improved_count,
                    "improvement_rate": round(improved_count / len(scores) * 100, 1) if scores else 0,
                    "symptom_scores": scores
                }
                
                try:
                    score_file.parent.mkdir(parents=True, exist_ok=True)
                    with open(score_file, 'w', encoding='utf-8') as f:
                        json.dump(evaluation_data, f, ensure_ascii=False, indent=2)
                    
                    self.stats[api_name]["successful_comparisons"] += 1
                    self.stats[api_name]["total_symptoms"] += len(scores)
                    print(f"    ✅ 保存评估分数: {api_name} - {len(scores)}个症状")
                    
                except Exception as e:
                    print(f"    ❌ 保存评估分数失败: {api_name} - {e}")
    
    def generate_api_summaries(self):
        """为每个API生成总结报告"""
        print("\n📊 正在生成API总结报告...")
        
        for api_name in self.apis:
            api_dir = self.results_dir / api_name
            summary_file = api_dir / f"{api_name}_rag_effect_summary.txt"
            
            # 收集该API的所有评估分数
            score_files = list((api_dir / "evaluation_scores").glob("*_evaluation_scores.json"))
            
            if not score_files:
                # 创建空总结
                summary_content = f"""
=== {api_name.upper()} RAG效果总结 ===
生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

❌ 状态: 无可用数据
   该API可能没有成功的响应，或者配额用完了。

统计信息:
- Baseline响应数: {self.stats[api_name]['baseline_count']}
- RAG响应数: {self.stats[api_name]['rag_count']}
- 失败响应数: {self.stats[api_name]['failed_responses']}
"""
            else:
                # 分析数据并生成详细总结
                summary_content = self._generate_detailed_summary(api_name, score_files)
            
            try:
                with open(summary_file, 'w', encoding='utf-8') as f:
                    f.write(summary_content)
                print(f"  ✅ 生成总结: {api_name}")
            except Exception as e:
                print(f"  ❌ 生成总结失败: {api_name} - {e}")
    
    def _generate_detailed_summary(self, api_name: str, score_files: List[Path]) -> str:
        """生成详细的API总结"""
        all_improvements = []
        all_scores = []
        total_symptoms = 0
        improved_symptoms = 0
        
        for score_file in score_files:
            try:
                with open(score_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                all_improvements.append(data['average_improvement'])
                improved_symptoms += data['improved_symptoms']
                total_symptoms += data['total_symptoms']
                
                for symptom in data['symptom_scores']:
                    all_scores.append({
                        'baseline': symptom['baseline_score'],
                        'rag': symptom['rag_score'],
                        'improvement': symptom['improvement']
                    })
                    
            except Exception as e:
                print(f"    ⚠️ 读取分数文件失败: {score_file} - {e}")
        
        if not all_scores:
            return f"❌ {api_name.upper()}: 无有效数据"
        
        # 计算统计指标
        avg_improvement = sum(all_improvements) / len(all_improvements) if all_improvements else 0
        improvement_rate = improved_symptoms / total_symptoms * 100 if total_symptoms > 0 else 0
        
        avg_baseline = sum(score['baseline'] for score in all_scores) / len(all_scores)
        avg_rag = sum(score['rag'] for score in all_scores) / len(all_scores)
        
        # 效果评估
        if avg_improvement > 5:
            effect_assessment = "🎉 显著提升"
        elif avg_improvement > 1:
            effect_assessment = "✅ 轻微提升"
        elif avg_improvement > -1:
            effect_assessment = "➖ 基本无变化"
        else:
            effect_assessment = "❌ 性能下降"
        
        summary_content = f"""
=== {api_name.upper()} RAG效果总结 ===
生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

🎯 总体效果: {effect_assessment}

📊 核心指标:
- 平均改善分数: {avg_improvement:.2f} 分
- 改善率: {improvement_rate:.1f}% ({improved_symptoms}/{total_symptoms} 个症状)
- 平均baseline分数: {avg_baseline:.1f}/100
- 平均RAG分数: {avg_rag:.1f}/100

📈 详细统计:
- 处理报告数: {len(score_files)}
- 总症状数: {total_symptoms}
- 改善症状数: {improved_symptoms}
- 无变化症状数: {total_symptoms - improved_symptoms - sum(1 for s in all_scores if s['improvement'] < 0)}
- 恶化症状数: {sum(1 for s in all_scores if s['improvement'] < 0)}

🔧 技术统计:
- Baseline响应数: {self.stats[api_name]['baseline_count']}
- RAG响应数: {self.stats[api_name]['rag_count']}
- 成功比较数: {self.stats[api_name]['successful_comparisons']}
- 失败响应数: {self.stats[api_name]['failed_responses']}

💡 结论:
"""
        
        if avg_improvement > 5:
            summary_content += """RAG系统对该API带来了显著的性能提升，建议继续使用RAG增强。"""
        elif avg_improvement > 1:
            summary_content += """RAG系统对该API带来了轻微的性能提升，总体上是有益的。"""
        elif avg_improvement > -1:
            summary_content += """RAG系统对该API的影响中性，可能需要调整RAG策略或提示词。"""
        else:
            summary_content += """RAG系统对该API造成了性能下降，建议检查RAG质量或考虑不使用RAG。"""
        
        return summary_content
    
    def run(self):
        """执行完整的重新整理流程"""
        print("🚀 开始API结果重新整理")
        print("=" * 60)
        
        # 1. 加载数据
        baseline_data = self.load_baseline_data()
        comparison_data = self.load_comparison_data()
        
        # 2. 提取和整理响应
        self.extract_api_responses(baseline_data, comparison_data)
        
        # 3. 生成总结报告
        self.generate_api_summaries()
        
        # 4. 显示最终统计
        self.print_final_statistics()
        
        print("\n🎉 API结果重新整理完成!")
        print(f"📁 结果保存在: {self.results_dir}")
    
    def print_final_statistics(self):
        """打印最终统计信息"""
        print("\n📊 最终统计信息:")
        print("=" * 40)
        
        for api_name in self.apis:
            stats = self.stats[api_name]
            print(f"\n{api_name.upper()}:")
            print(f"  📁 Baseline响应: {stats['baseline_count']}")
            print(f"  🔄 RAG响应: {stats['rag_count']}")
            print(f"  📊 评估完成: {stats['successful_comparisons']}")
            print(f"  🎯 总症状数: {stats['total_symptoms']}")
            print(f"  ❌ 失败响应: {stats['failed_responses']}")

def main():
    """主函数"""
    print("🔧 API结果重新整理工具")
    print("此工具将重新整理现有的评估结果，按API分类存储")
    print()
    
    # 确认当前目录
    current_dir = Path.cwd()
    print(f"📂 当前工作目录: {current_dir}")
    
    # 检查必要目录
    required_dirs = ["baseline_results", "rerun_comparisons", "results_of_apis"]
    missing_dirs = [d for d in required_dirs if not (current_dir / d).exists()]
    
    if missing_dirs:
        print(f"❌ 缺少必要目录: {missing_dirs}")
        print("请在正确的目录中运行此脚本")
        return 1
    
    # 运行重新整理
    reorganizer = APIResultsReorganizer()
    reorganizer.run()
    
    return 0

if __name__ == "__main__":
    exit(main())
