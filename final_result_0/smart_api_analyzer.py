#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能API评分分析脚本

功能：
1. 真正识别和排除无效的API调用（空结果、全0分等）
2. 基于实际有效数据进行RAG增强效果分析
3. 生成准确的分析报告
"""

import json
import os
import glob
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Any, Tuple
import statistics

class SmartAPIScoreAnalyzer:
    """智能API评分分析器"""
    
    def __init__(self, base_dir: str = "."):
        """初始化"""
        self.base_dir = Path(base_dir)
        self.apis = ["moonshot", "deepseek", "openai", "anthropic", "gemini"]
        
        # 存储每个API的评分数据
        self.api_scores = {api: {
            "baseline_scores": [],
            "rag_scores": [],
            "improvements": [],
            "declines": [],
            "no_change": [],
            "valid_reports": [],
            "invalid_reports": [],
            "empty_results": [],
            "zero_scores": []
        } for api in self.apis}
        
        # 统计信息
        self.stats = {}
        
    def load_comparison_data(self) -> Dict[str, Dict]:
        """加载comparison数据"""
        print("📁 正在加载comparison数据...")
        comparison_dir = self.base_dir / "rerun_comparisons"
        comparison_data = {}
        
        # 查找所有comparison文件
        for file_path in comparison_dir.glob("*_comparison_*.json"):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # 从文件名提取report_id
                filename = file_path.stem
                if "report_" in filename:
                    parts = filename.split("_")
                    report_id = parts[1]  # report_4000_comparison_timestamp
                    comparison_data[f"diagnostic_{report_id}"] = data
                    print(f"  ✅ 加载comparison: diagnostic_{report_id}")
                
            except Exception as e:
                print(f"  ❌ 加载comparison失败: {file_path} - {e}")
        
        print(f"📊 共加载 {len(comparison_data)} 个comparison文件")
        return comparison_data
    
    def is_api_call_valid(self, api_data: Dict) -> Tuple[bool, str]:
        """判断API调用是否真正有效"""
        # 检查器官名称是否为空
        baseline_organ = api_data.get("baseline_organ", "")
        rag_organ = api_data.get("rag_organ", "")
        
        if not baseline_organ or not rag_organ:
            return False, "器官名称为空"
        
        # 检查位置数组是否为空
        baseline_locations = api_data.get("baseline_locations", [])
        rag_locations = api_data.get("rag_locations", [])
        
        if not baseline_locations and not rag_locations:
            return False, "位置数组为空"
        
        # 检查metrics是否存在
        baseline_metrics = api_data.get("baseline_metrics", {})
        rag_metrics = api_data.get("rag_metrics", {})
        
        if not baseline_metrics or not rag_metrics:
            return False, "metrics数据缺失"
        
        # 检查是否所有分数都为0
        baseline_score = baseline_metrics.get("overall_score", 0)
        rag_score = rag_metrics.get("overall_score", 0)
        
        if baseline_score == 0 and rag_score == 0:
            return False, "所有分数都为0"
        
        # 检查器官识别是否完全失败
        baseline_organ_accuracy = api_data.get("baseline_organ_accuracy", {})
        rag_organ_accuracy = api_data.get("rag_organ_accuracy", {})
        
        if (baseline_organ_accuracy.get("description", "") == "未识别出任何器官" and 
            rag_organ_accuracy.get("description", "") == "未识别出任何器官"):
            return False, "完全未识别出器官"
        
        return True, "有效"
    
    def extract_api_scores(self, comparison_data: Dict[str, Dict]):
        """提取每个API的评分数据，真正排除无效数据"""
        print("🔄 正在提取API评分数据（智能排除无效数据）...")
        
        for report_id, report_data in comparison_data.items():
            print(f"\n📋 处理报告: {report_id}")
            
            # 获取症状列表 - 这里每个症状是一个键值对
            symptoms = report_data
            
            for symptom_name, symptom_data in symptoms.items():
                if isinstance(symptom_data, dict) and any(api in symptom_data for api in self.apis):
                    print(f"  处理症状: {symptom_name}")
                    
                    # 处理每个API的评分
                    for api in self.apis:
                        if api in symptom_data:
                            self._process_api_scores(api, symptom_data[api], symptom_name, report_id)
    
    def _process_api_scores(self, api: str, symptom_data: Dict, symptom_name: str, report_id: str):
        """处理单个API的评分，智能排除无效数据"""
        # 首先判断API调用是否真正有效
        is_valid, reason = self.is_api_call_valid(symptom_data)
        
        if not is_valid:
            # 记录无效数据
            self.api_scores[api]["invalid_reports"].append(report_id)
            
            # 分类记录不同类型的无效数据
            if "器官名称为空" in reason or "位置数组为空" in reason:
                self.api_scores[api]["empty_results"].append(report_id)
            elif "所有分数都为0" in reason:
                self.api_scores[api]["zero_scores"].append(report_id)
            
            print(f"    {api}: {reason} (已排除)")
            return
        
        # 获取评分指标
        baseline_metrics = symptom_data.get("baseline_metrics", {})
        rag_metrics = symptom_data.get("rag_metrics", {})
        
        baseline_score = baseline_metrics.get("overall_score", 0)
        rag_score = rag_metrics.get("overall_score", 0)
        
        # 存储有效数据
        self.api_scores[api]["baseline_scores"].append(baseline_score)
        self.api_scores[api]["rag_scores"].append(rag_score)
        self.api_scores[api]["valid_reports"].append(report_id)
        
        # 判断是否有提升
        if rag_score > baseline_score:
            self.api_scores[api]["improvements"].append(rag_score - baseline_score)
        elif rag_score < baseline_score:
            self.api_scores[api]["declines"].append(baseline_score - rag_score)
        else:
            self.api_scores[api]["no_change"].append(0)
        
        print(f"    {api}: baseline={baseline_score}, RAG={rag_score} (有效)")
    
    def calculate_statistics(self):
        """计算统计信息"""
        print("\n📊 正在计算统计信息...")
        
        for api in self.apis:
            baseline_scores = self.api_scores[api]["baseline_scores"]
            rag_scores = self.api_scores[api]["rag_scores"]
            improvements = self.api_scores[api]["improvements"]
            declines = self.api_scores[api]["declines"]
            no_change = self.api_scores[api]["no_change"]
            valid_reports = self.api_scores[api]["valid_reports"]
            invalid_reports = self.api_scores[api]["invalid_reports"]
            empty_results = self.api_scores[api]["empty_results"]
            zero_scores = self.api_scores[api]["zero_scores"]
            
            if not baseline_scores:
                print(f"  ⚠️  {api}: 无有效数据")
                continue
            
            total_symptoms = len(baseline_scores)
            improvement_count = len(improvements)
            decline_count = len(declines)
            no_change_count = len(no_change)
            unique_valid_reports = len(set(valid_reports))
            unique_invalid_reports = len(set(invalid_reports))
            unique_empty_results = len(set(empty_results))
            unique_zero_scores = len(set(zero_scores))
            
            # 计算平均分
            baseline_avg = statistics.mean(baseline_scores) if baseline_scores else 0
            rag_avg = statistics.mean(rag_scores) if rag_scores else 0
            
            # 计算比例
            improvement_ratio = improvement_count / total_symptoms if total_symptoms > 0 else 0
            decline_ratio = decline_count / total_symptoms if total_symptoms > 0 else 0
            no_change_ratio = no_change_count / total_symptoms if total_symptoms > 0 else 0
            
            self.stats[api] = {
                "s_numbers": total_symptoms,
                "valid_reports_count": unique_valid_reports,
                "invalid_reports_count": unique_invalid_reports,
                "empty_results_count": unique_empty_results,
                "zero_scores_count": unique_zero_scores,
                "scores_without_rag": {
                    "overall_score": round(baseline_avg, 2),
                    "total_scores": baseline_scores
                },
                "scores_with_rag": {
                    "overall_score": round(rag_avg, 2),
                    "total_scores": rag_scores
                },
                "improvement_ratio": round(improvement_ratio * 100, 2),
                "decline_ratio": round(decline_ratio * 100, 2),
                "no_change_ratio": round(no_change_ratio * 100, 2),
                "improvement_count": improvement_count,
                "decline_count": decline_count,
                "no_change_count": no_change_count,
                "data_quality": {
                    "valid_symptoms": total_symptoms,
                    "invalid_reports": unique_invalid_reports,
                    "empty_results": unique_empty_results,
                    "zero_scores": unique_zero_scores,
                    "data_completeness": f"{unique_valid_reports}/{unique_valid_reports + unique_invalid_reports}"
                }
            }
            
            print(f"  ✅ {api}: {total_symptoms}个有效症状, 提升率{improvement_ratio*100:.1f}%, 下降率{decline_ratio*100:.1f}%")
            if unique_invalid_reports > 0:
                print(f"     ⚠️  发现{unique_invalid_reports}个无效报告，已排除")
                if unique_empty_results > 0:
                    print(f"       其中{unique_empty_results}个为空结果")
                if unique_zero_scores > 0:
                    print(f"       其中{unique_zero_scores}个为全0分")
    
    def generate_report(self, output_file: str = "smart_api_analysis_report.json"):
        """生成分析报告"""
        print(f"\n📝 正在生成智能分析报告: {output_file}")
        
        # 创建详细报告
        detailed_report = {
            "analysis_timestamp": str(Path.cwd()),
            "total_apis": len(self.apis),
            "data_quality_note": "已智能排除空结果、全0分等无效API调用",
            "api_statistics": self.stats,
            "summary": {
                "total_symptoms_processed": sum(stat["s_numbers"] for stat in self.stats.values()),
                "apis_with_valid_data": [api for api, stat in self.stats.items() if stat["s_numbers"] > 0],
                "best_improvement_api": max(self.stats.items(), key=lambda x: x[1]["improvement_ratio"])[0] if self.stats else None,
                "worst_decline_api": max(self.stats.items(), key=lambda x: x[1]["decline_ratio"])[0] if self.stats else None,
                "most_stable_api": max(self.stats.items(), key=lambda x: x[1]["no_change_ratio"])[0] if self.stats else None
            }
        }
        
        # 保存到文件
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(detailed_report, f, ensure_ascii=False, indent=2)
        
        print(f"  ✅ 报告已保存到: {output_file}")
        
        # 生成人类可读的摘要
        self._generate_human_readable_summary()
    
    def _generate_human_readable_summary(self):
        """生成人类可读的摘要"""
        print("\n" + "="*80)
        print("🎯 智能API评分分析摘要")
        print("="*80)
        
        for api, stat in self.stats.items():
            if stat["s_numbers"] == 0:
                continue
                
            print(f"\n📊 {api.upper()}:")
            print(f"  有效症状总数: {stat['s_numbers']}")
            print(f"  有效报告数量: {stat['data_quality']['valid_symptoms']}")
            print(f"  无效报告数量: {stat['data_quality']['invalid_reports']}")
            if stat['data_quality']['empty_results'] > 0:
                print(f"    其中空结果: {stat['data_quality']['empty_results']}")
            if stat['data_quality']['zero_scores'] > 0:
                print(f"    其中全0分: {stat['data_quality']['zero_scores']}")
            print(f"  无RAG平均分: {stat['scores_without_rag']['overall_score']}")
            print(f"  有RAG平均分: {stat['scores_with_rag']['overall_score']}")
            print(f"  RAG提升比例: {stat['improvement_ratio']}% ({stat['improvement_count']}个)")
            print(f"  RAG下降比例: {stat['decline_ratio']}% ({stat['decline_count']}个)")
            print(f"  无变化比例: {stat['no_change_ratio']}% ({stat['no_change_count']}个)")
            
            # 计算平均提升/下降
            if stat['improvement_count'] > 0:
                improvements = []
                for i, (rag_score, baseline_score) in enumerate(zip(stat['scores_with_rag']['total_scores'], 
                                                                   stat['scores_without_rag']['total_scores'])):
                    if rag_score > baseline_score:
                        improvements.append(rag_score - baseline_score)
                
                if improvements:
                    avg_improvement = statistics.mean(improvements)
                    print(f"  平均提升分数: {avg_improvement:.2f}")
            
            if stat['decline_count'] > 0:
                declines = []
                for i, (rag_score, baseline_score) in enumerate(zip(stat['scores_with_rag']['total_scores'], 
                                                                   stat['scores_without_rag']['total_scores'])):
                    if rag_score < baseline_score:
                        declines.append(baseline_score - rag_score)
                
                if declines:
                    avg_decline = statistics.mean(declines)
                    print(f"  平均下降分数: {avg_decline:.2f}")
        
        print("\n" + "="*80)
    
    def run_analysis(self):
        """运行完整分析"""
        print("🚀 开始智能API评分分析...")
        
        # 1. 加载数据
        comparison_data = self.load_comparison_data()
        
        # 2. 提取评分
        self.extract_api_scores(comparison_data)
        
        # 3. 计算统计
        self.calculate_statistics()
        
        # 4. 生成报告
        self.generate_report()
        
        print("\n✅ 智能API评分分析完成！")
        return self.stats

def main():
    """主函数"""
    analyzer = SmartAPIScoreAnalyzer()
    stats = analyzer.run_analysis()
    
    # 返回结果供其他脚本使用
    return stats

if __name__ == "__main__":
    main()
