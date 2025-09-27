#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RAG评估系统 - 主工作流程（批处理优化版）
基于原始main_workflow.py，但使用BatchAPIManager支持OpenAI Batch API
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
sys.path.append(str(Path(__file__).parent.parent / "src"))

from config_loader import ConfigLoader
from data_loader import DataLoader
from batch_api_manager import BatchAPIManager  # 使用批处理API管理器
from evaluator import Evaluator
from utils.logger import ReportLogger


class MainWorkflowBatch:
    """主工作流程类（批处理优化版）"""
    
    def __init__(self, config_path: str = "config/config.yaml", 
                 enable_batch: bool = True,
                 batch_threshold: int = 10):
        """初始化主工作流程"""
        self.config = ConfigLoader(config_path)
        self.data_loader = DataLoader()
        
        # 使用批处理API管理器
        self.api_manager = BatchAPIManager(
            enable_batch=enable_batch,
            batch_threshold=batch_threshold
        )
        
        self.evaluator = Evaluator()
        self.logger = ReportLogger()
        
        # 从配置文件获取输出路径
        output_base = self.config.get_path('output_results')
        self.output_base_dir = Path(output_base)
        
        # 创建结果目录（使用不同的目录名以区分）
        self.results_dir = self.output_base_dir / "baseline_results_batch"
        self.results_dir.mkdir(parents=True, exist_ok=True)
        
        # 创建日志目录
        self.logs_dir = Path("logs")
        self.logs_dir.mkdir(exist_ok=True)
    
    def process_report(self, report_data: Dict[str, Any], force_batch: bool = False) -> Dict[str, Any]:
        """处理单个报告（支持批处理）"""
        report_id = report_data.get('report_id', 'unknown')
        symptoms = report_data.get('symptoms', [])
        
        print(f"\n📋 处理报告 {report_id}")
        print(f"   症状数量: {len(symptoms)}")
        
        # 加载系统提示词
        system_prompt_path = Path(self.config.get_path('system_prompt'))
        if not system_prompt_path.is_absolute():
            system_prompt_path = Path(__file__).parent.parent / system_prompt_path
        
        try:
            with open(system_prompt_path, 'r', encoding='utf-8') as f:
                system_prompt = f.read().strip()
        except Exception as e:
            print(f"❌ 系统提示词加载失败: {e}")
            return {}
        
        # 使用批处理API管理器处理症状
        try:
            report_results = self.api_manager.process_report_symptoms_batch(
                report_data=report_data,
                system_prompt=system_prompt,
                force_batch=force_batch
            )
            
            print(f"✅ 报告 {report_id} 处理完成")
            return report_results
            
        except Exception as e:
            print(f"❌ 报告 {report_id} 处理失败: {e}")
            return {}
    
    def run_evaluation(self, 
                      start_id: int, 
                      end_id: int, 
                      max_files: Optional[int] = None,
                      force_batch: bool = False,
                      data_dir: str = "test_set") -> bool:
        """运行评估流程"""
        
        print("=" * 70)
        print("🎯 RAG评估系统 - 基础评估（批处理优化）")
        print("=" * 70)
        print(f"📋 报告范围: {start_id} - {end_id}")
        print(f"📁 数据目录: {data_dir}")
        print(f"🚀 批处理模式: {'启用' if self.api_manager.enable_batch else '禁用'}")
        print(f"📊 批处理阈值: {self.api_manager.batch_threshold}")
        print(f"🎯 强制批处理: {'是' if force_batch else '否'}")
        if max_files:
            print(f"📁 最大文件数: {max_files}")
        print("=" * 70)
        
        # 1. 初始化API客户端
        print("\n🔧 初始化API客户端...")
        if not self.api_manager.initialize_clients(self.config.config):
            print("❌ API客户端初始化失败")
            return False
        
        # 2. 测试连通性
        system_prompt_path = Path(self.config.get_path('system_prompt'))
        if not system_prompt_path.is_absolute():
            system_prompt_path = Path(__file__).parent.parent / system_prompt_path
        
        try:
            with open(system_prompt_path, 'r', encoding='utf-8') as f:
                system_prompt = f.read().strip()
        except Exception as e:
            print(f"❌ 系统提示词加载失败: {e}")
            return False
        
        if not self.api_manager.test_connectivity(system_prompt):
            print("❌ API连通性测试失败")
            return False
        
        print(f"\n📊 API客户端状态:")
        print(f"   总客户端数: {self.api_manager.get_client_count()}")
        print(f"   支持批处理: {len(self.api_manager.get_batch_client_names())}")
        print(f"   客户端列表: {', '.join(self.api_manager.get_client_names())}")
        if self.api_manager.get_batch_client_names():
            print(f"   批处理支持: {', '.join(self.api_manager.get_batch_client_names())}")
        
        # 3. 加载数据
        print("\n📂 加载测试数据...")
        
        # 使用自定义数据目录或配置文件中的路径
        if data_dir != "test_set":
            # 使用自定义数据目录
            input_data_path = Path(f"/home/duojiechen/Projects/Central_Data/RAG_System/{data_dir}")
        else:
            # 使用配置文件中的路径
            input_data_path = Path(self.config.get_path('input_data'))
        
        # 获取指定范围的文件
        report_files = self.data_loader.get_reports_by_id_range(
            input_data_path, 
            start_id, 
            end_id, 
            max_files=max_files
        )
        
        if not report_files:
            print("❌ 没有找到有效的测试数据")
            return False
        
        print(f"✅ 找到 {len(report_files)} 个报告文件")
        
        # 加载所有报告数据
        all_reports = []
        for file_path in report_files:
            try:
                report_data = self.data_loader.load_report_data(file_path)
                if report_data and report_data.get('symptoms'):
                    all_reports.append(report_data)
                    print(f"   📄 加载报告: {report_data['report_id']} ({len(report_data['symptoms'])} 症状)")
                else:
                    print(f"   ⚠️  跳过空报告: {file_path.stem}")
            except Exception as e:
                print(f"   ❌ 加载失败: {file_path.stem} - {e}")
                continue
        
        if not all_reports:
            print("❌ 没有找到有效的测试数据")
            return False
        
        print(f"✅ 成功加载 {len(all_reports)} 个报告")
        
        # 4. 处理每个报告
        all_results = []
        total_symptoms = 0
        
        for i, report_data in enumerate(all_reports, 1):
            report_id = report_data['report_id']
            symptoms_count = len(report_data['symptoms'])
            total_symptoms += symptoms_count
            
            print(f"\n📋 处理报告 {i}/{len(all_reports)}: {report_id}")
            
            try:
                # 处理报告
                report_results = self.process_report(report_data, force_batch=force_batch)
                
                if report_results:
                    # 保存结果
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    result_file = self.results_dir / f"baseline_batch_report_{report_id}_{timestamp}.json"
                    
                    with open(result_file, 'w', encoding='utf-8') as f:
                        json.dump(report_results, f, ensure_ascii=False, indent=2)
                    
                    all_results.append(report_results)
                    print(f"✅ 报告 {report_id} 处理完成，结果已保存: {result_file}")
                else:
                    print(f"❌ 报告 {report_id} 处理失败")
                    
            except Exception as e:
                print(f"❌ 报告 {report_id} 处理异常: {e}")
                continue
        
        # 5. 生成总体摘要
        if all_results:
            print(f"\n📊 生成总体摘要...")
            
            summary = {
                'timestamp': datetime.now().isoformat(),
                'processing_mode': 'baseline_batch',
                'report_range': f"{start_id}-{end_id}",
                'total_reports': len(all_results),
                'total_symptoms': total_symptoms,
                'batch_settings': {
                    'enable_batch': self.api_manager.enable_batch,
                    'batch_threshold': self.api_manager.batch_threshold,
                    'force_batch': force_batch
                },
                'api_clients': self.api_manager.get_client_names(),
                'batch_clients': self.api_manager.get_batch_client_names(),
                'results_summary': []
            }
            
            # 统计每个报告的API成功率
            for result in all_results:
                report_summary = {
                    'report_id': result['report_id'],
                    'symptoms_count': len(result['symptoms']),
                    'processing_mode': result.get('processing_mode', 'unknown'),
                    'api_success_rates': {}
                }
                
                for symptom in result['symptoms']:
                    for api_name, api_response in symptom.get('api_responses', {}).items():
                        if api_name not in report_summary['api_success_rates']:
                            report_summary['api_success_rates'][api_name] = {'total': 0, 'success': 0}
                        
                        report_summary['api_success_rates'][api_name]['total'] += 1
                        if api_response.get('success'):
                            report_summary['api_success_rates'][api_name]['success'] += 1
                
                # 计算成功率百分比
                for api_name, stats in report_summary['api_success_rates'].items():
                    if stats['total'] > 0:
                        stats['success_rate'] = (stats['success'] / stats['total']) * 100
                    else:
                        stats['success_rate'] = 0
                
                summary['results_summary'].append(report_summary)
            
            # 保存总体摘要
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            summary_file = self.results_dir / f"baseline_batch_summary_{start_id}_{end_id}_{timestamp}.json"
            
            with open(summary_file, 'w', encoding='utf-8') as f:
                json.dump(summary, f, ensure_ascii=False, indent=2)
            
            print(f"📄 总体摘要已保存: {summary_file}")
        
        # 6. 清理批处理文件
        print(f"\n🧹 清理旧的批处理文件...")
        self.api_manager.cleanup_batch_files(keep_days=7)
        
        # 7. 显示最终统计
        print("\n" + "=" * 70)
        print("🎉 基础评估（批处理优化）完成!")
        print("=" * 70)
        print(f"📊 处理统计:")
        print(f"   处理报告: {len(all_results)}/{len(all_reports)}")
        print(f"   总症状数: {total_symptoms}")
        print(f"   结果目录: {self.results_dir}")
        print(f"   批处理模式: {'启用' if self.api_manager.enable_batch else '禁用'}")
        
        if self.api_manager.enable_batch and self.api_manager.get_batch_client_names():
            print(f"   批处理客户端: {', '.join(self.api_manager.get_batch_client_names())}")
            print(f"   💰 OpenAI成本节省: ~50%")
        
        print("=" * 70)
        
        return len(all_results) > 0


def main():
    parser = argparse.ArgumentParser(
        description="RAG评估系统主工作流程（批处理优化版）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
这是基础评估的批处理优化版本：
- 保持与原始main_workflow.py相同的功能
- OpenAI API调用使用Batch API，成本降低50%
- 其他API保持传统逐条调用模式
- 支持智能阈值控制和自动回退

适用场景：
- 需要基础评估（不含RAG）
- 希望降低OpenAI API成本
- 大规模评估任务

示例:
  python main_workflow_batch.py --start_id 4000 --end_id 4000
  python main_workflow_batch.py --start_id 4000 --end_id 4002 --force-batch
        """
    )
    
    parser.add_argument("--start_id", type=int, required=True, help="开始报告ID")
    parser.add_argument("--end_id", type=int, required=True, help="结束报告ID")
    parser.add_argument("--config", type=str, default="config/config.yaml", help="配置文件路径")
    parser.add_argument("--max_files", type=int, help="最大处理文件数量")
    
    # 数据目录参数
    parser.add_argument("--data-dir", type=str, default="test_set",
                       help="数据目录路径 (默认: test_set)")
    
    # 批处理相关参数
    parser.add_argument("--disable-batch", action="store_true", help="禁用批处理模式")
    parser.add_argument("--batch-threshold", type=int, default=10,
                       help="启用批处理的最小症状数量阈值 (默认10)")
    parser.add_argument("--force-batch", action="store_true",
                       help="强制使用批处理，忽略阈值限制")
    
    args = parser.parse_args()
    
    # 创建工作流程实例
    workflow = MainWorkflowBatch(
        config_path=args.config,
        enable_batch=not args.disable_batch,
        batch_threshold=args.batch_threshold
    )
    
    # 运行评估
    success = workflow.run_evaluation(
        start_id=args.start_id,
        end_id=args.end_id,
        max_files=args.max_files,
        force_batch=args.force_batch,
        data_dir=args.data_dir
    )
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
