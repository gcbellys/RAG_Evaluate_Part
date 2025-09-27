#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API评分分析脚本

功能：
1. 读取每个API在RAG使用前后的所有评分
2. 计算分数平均值
3. 统计RAG增强的提升和下降比例
4. 生成详细的分析报告

输出格式：
api_name:
  s_numbers: 总症状数量
  scores_without_rag: 各指标平均分
  scores_with_rag: 各指标平均分
  improvement_ratio: RAG增强有提升的比例
  decline_ratio: RAG增强有下降的比例
"""

import json
import os
import glob
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Any, Tuple
import statistics

class APIScoreAnalyzer:
    """API评分分析器"""
    
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
            "no_change": []
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
    
    def extract_api_scores(self, comparison_data: Dict[str, Dict]):
        """提取每个API的评分数据"""
        print("🔄 正在提取API评分数据...")
        
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
                            self._process_api_scores(api, symptom_data[api], symptom_name)
    
    def _process_api_scores(self, api: str, symptom_data: Dict, symptom_name: str):
        """处理单个API的评分"""
        # 直接获取评分指标
        baseline_metrics = symptom_data.get("baseline_metrics", {})
        rag_metrics = symptom_data.get("rag_metrics", {})
        
        # 存储评分数据
        if baseline_metrics and rag_metrics:
            baseline_score = baseline_metrics.get("overall_score", 0)
            rag_score = rag_metrics.get("overall_score", 0)
            
            self.api_scores[api]["baseline_scores"].append(baseline_score)
            self.api_scores[api]["rag_scores"].append(rag_score)
            
            # 判断是否有提升
            if rag_score > baseline_score:
                self.api_scores[api]["improvements"].append(rag_score - baseline_score)
            elif rag_score < baseline_score:
                self.api_scores[api]["declines"].append(baseline_score - rag_score)
            else:
                self.api_scores[api]["no_change"].append(0)
            
            print(f"    {api}: baseline={baseline_score}, RAG={rag_score}")
    
    def calculate_statistics(self):
        """计算统计信息"""
        print("\n📊 正在计算统计信息...")
        
        for api in self.apis:
            baseline_scores = self.api_scores[api]["baseline_scores"]
            rag_scores = self.api_scores[api]["rag_scores"]
            improvements = self.api_scores[api]["improvements"]
            declines = self.api_scores[api]["declines"]
            no_change = self.api_scores[api]["no_change"]
            
            if not baseline_scores:
                print(f"  ⚠️  {api}: 无数据")
                continue
            
            total_symptoms = len(baseline_scores)
            improvement_count = len(improvements)
            decline_count = len(declines)
            no_change_count = len(no_change)
            
            # 计算平均分
            baseline_avg = statistics.mean(baseline_scores) if baseline_scores else 0
            rag_avg = statistics.mean(rag_scores) if rag_scores else 0
            
            # 计算比例
            improvement_ratio = improvement_count / total_symptoms if total_symptoms > 0 else 0
            decline_ratio = decline_count / total_symptoms if total_symptoms > 0 else 0
            no_change_ratio = no_change_count / total_symptoms if total_symptoms > 0 else 0
            
            self.stats[api] = {
                "s_numbers": total_symptoms,
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
                "no_change_count": no_change_count
            }
            
            print(f"  ✅ {api}: {total_symptoms}个症状, 提升率{improvement_ratio*100:.1f}%, 下降率{decline_ratio*100:.1f}%")
    
    def generate_report(self, output_file: str = "api_score_analysis_report.json"):
        """生成分析报告"""
        print(f"\n📝 正在生成分析报告: {output_file}")
        
        # 创建详细报告
        detailed_report = {
            "analysis_timestamp": str(Path.cwd()),
            "total_apis": len(self.apis),
            "api_statistics": self.stats,
            "summary": {
                "total_symptoms_processed": sum(stat["s_numbers"] for stat in self.stats.values()),
                "apis_with_data": [api for api, stat in self.stats.items() if stat["s_numbers"] > 0],
                "best_improvement_api": max(self.stats.items(), key=lambda x: x[1]["improvement_ratio"])[0] if self.stats else None,
                "worst_decline_api": max(self.stats.items(), key=lambda x: x[1]["decline_ratio"])[0] if self.stats else None
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
        print("🎯 API评分分析摘要")
        print("="*80)
        
        for api, stat in self.stats.items():
            if stat["s_numbers"] == 0:
                continue
                
            print(f"\n📊 {api.upper()}:")
            print(f"  症状总数: {stat['s_numbers']}")
            print(f"  无RAG平均分: {stat['scores_without_rag']['overall_score']}")
            print(f"  有RAG平均分: {stat['scores_with_rag']['overall_score']}")
            print(f"  RAG提升比例: {stat['improvement_ratio']}% ({stat['improvement_count']}个)")
            print(f"  RAG下降比例: {stat['decline_ratio']}% ({stat['decline_count']}个)")
            print(f"  无变化比例: {stat['no_change_ratio']}% ({stat['no_change_count']}个)")
            
            # 计算平均提升/下降
            if stat['improvement_count'] > 0:
                # 计算提升的分数差值
                improvements = []
                for i, (rag_score, baseline_score) in enumerate(zip(stat['scores_with_rag']['total_scores'], 
                                                                   stat['scores_without_rag']['total_scores'])):
                    if rag_score > baseline_score:
                        improvements.append(rag_score - baseline_score)
                
                if improvements:
                    avg_improvement = statistics.mean(improvements)
                    print(f"  平均提升分数: {avg_improvement:.2f}")
            
            if stat['decline_count'] > 0:
                # 计算下降的分数差值
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
        print("🚀 开始API评分分析...")
        
        # 1. 加载数据
        comparison_data = self.load_comparison_data()
        
        # 2. 提取评分
        self.extract_api_scores(comparison_data)
        
        # 3. 计算统计
        self.calculate_statistics()
        
        # 4. 生成报告
        self.generate_report()
        
        print("\n✅ API评分分析完成！")
        return self.stats

def main():
    """主函数"""
    analyzer = APIScoreAnalyzer()
    stats = analyzer.run_analysis()
    
    # 返回结果供其他脚本使用
    return stats

if __name__ == "__main__":
    main()
