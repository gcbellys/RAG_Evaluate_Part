#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批处理工作流程
支持OpenAI Batch API的RAG评估工作流程
"""

import argparse
import json
import os
import sys
import yaml
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from src.batch_api_manager import BatchAPIManager
from src.data_loader import DataLoader
from src.evaluator import Evaluator
from src.token_analyzer import TokenAnalyzer


def load_config(config_path: str) -> Dict[str, Any]:
    """加载配置文件"""
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        print(f"✅ 配置文件加载成功: {config_path}")
        return config
    except Exception as e:
        print(f"❌ 配置文件加载失败: {e}")
        sys.exit(1)


def load_system_prompt(prompt_path: str) -> str:
    """加载系统提示词"""
    try:
        with open(prompt_path, 'r', encoding='utf-8') as f:
            prompt = f.read().strip()
        print(f"✅ 系统提示词加载成功: {prompt_path}")
        return prompt
    except Exception as e:
        print(f"❌ 系统提示词加载失败: {e}")
        sys.exit(1)


def save_results(results: Dict[str, Any], output_dir: str, filename_prefix: str = "batch_results"):
    """保存结果到文件"""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # 保存详细结果
    detailed_file = output_path / f"{filename_prefix}_detailed_{timestamp}.json"
    with open(detailed_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print(f"💾 详细结果已保存: {detailed_file}")
    
    # 保存摘要
    summary = {
        'timestamp': timestamp,
        'processing_mode': results.get('processing_mode', 'batch'),
        'report_id': results.get('report_id'),
        'total_symptoms': results.get('total_symptoms', 0),
        'valid_symptoms': results.get('valid_symptoms', 0),
        'api_summary': {}
    }
    
    # 统计API使用情况
    for symptom in results.get('symptoms', []):
        for api_name, api_response in symptom.get('api_responses', {}).items():
            if api_name not in summary['api_summary']:
                summary['api_summary'][api_name] = {
                    'total_calls': 0,
                    'successful_calls': 0,
                    'failed_calls': 0,
                    'total_tokens': 0
                }
            
            summary['api_summary'][api_name]['total_calls'] += 1
            
            if api_response.get('success'):
                summary['api_summary'][api_name]['successful_calls'] += 1
                usage = api_response.get('usage', {})
                if usage:
                    summary['api_summary'][api_name]['total_tokens'] += usage.get('total_tokens', 0)
            else:
                summary['api_summary'][api_name]['failed_calls'] += 1
    
    summary_file = output_path / f"{filename_prefix}_summary_{timestamp}.json"
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    
    print(f"📊 摘要结果已保存: {summary_file}")
    
    return detailed_file, summary_file


def run_batch_evaluation(config: Dict[str, Any], 
                        system_prompt: str,
                        start_id: int,
                        end_id: int,
                        enable_batch: bool = True,
                        batch_threshold: int = 10,
                        force_batch: bool = False,
                        max_files: int = None) -> bool:
    """运行批处理评估"""
    
    print("=" * 70)
    print("🚀 批处理RAG评估系统")
    print("=" * 70)
    print(f"📋 报告范围: {start_id} - {end_id}")
    print(f"🔧 批处理模式: {'启用' if enable_batch else '禁用'}")
    print(f"📊 批处理阈值: {batch_threshold}")
    print(f"🎯 强制批处理: {'是' if force_batch else '否'}")
    if max_files:
        print(f"📁 最大文件数: {max_files}")
    print("=" * 70)
    
    # 1. 初始化API管理器
    print("\n🔧 初始化批处理API管理器...")
    api_manager = BatchAPIManager(
        enable_batch=enable_batch,
        batch_threshold=batch_threshold
    )
    
    if not api_manager.initialize_clients(config):
        print("❌ API客户端初始化失败")
        return False
    
    # 2. 测试连通性
    if not api_manager.test_connectivity(system_prompt):
        print("❌ API连通性测试失败")
        return False
    
    print(f"\n📊 API客户端状态:")
    print(f"   总客户端数: {api_manager.get_client_count()}")
    print(f"   支持批处理: {len(api_manager.get_batch_client_names())}")
    print(f"   客户端列表: {', '.join(api_manager.get_client_names())}")
    print(f"   批处理支持: {', '.join(api_manager.get_batch_client_names())}")
    
    # 3. 加载数据
    print("\n📂 加载测试数据...")
    data_loader = DataLoader()
    
    input_data_path = Path(config['paths']['input_data'])
    
    # 获取指定范围的文件
    report_files = data_loader.get_reports_by_id_range(
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
            report_data = data_loader.load_report_data(file_path)
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
    results_dir = Path(config['paths']['output_results']) / "batch_results"
    results_dir.mkdir(parents=True, exist_ok=True)
    
    all_results = []
    total_symptoms = 0
    
    for i, report_data in enumerate(all_reports, 1):
        report_id = report_data['report_id']
        symptoms_count = len(report_data['symptoms'])
        total_symptoms += symptoms_count
        
        print(f"\n📋 处理报告 {i}/{len(all_reports)}: {report_id}")
        print(f"   症状数量: {symptoms_count}")
        
        try:
            # 使用批处理API管理器处理报告
            report_results = api_manager.process_report_symptoms_batch(
                report_data=report_data,
                system_prompt=system_prompt,
                force_batch=force_batch
            )
            
            # 保存单个报告结果
            detailed_file, summary_file = save_results(
                report_results, 
                str(results_dir),
                f"report_{report_id}"
            )
            
            all_results.append(report_results)
            print(f"✅ 报告 {report_id} 处理完成")
            
        except Exception as e:
            print(f"❌ 报告 {report_id} 处理失败: {e}")
            continue
    
    # 5. 生成总体摘要
    if all_results:
        print(f"\n📊 生成总体摘要...")
        
        overall_summary = {
            'timestamp': datetime.now().isoformat(),
            'processing_mode': 'batch',
            'report_range': f"{start_id}-{end_id}",
            'total_reports': len(all_results),
            'total_symptoms': total_symptoms,
            'batch_settings': {
                'enable_batch': enable_batch,
                'batch_threshold': batch_threshold,
                'force_batch': force_batch
            },
            'api_clients': api_manager.get_client_names(),
            'batch_clients': api_manager.get_batch_client_names(),
            'reports': []
        }
        
        for result in all_results:
            report_summary = {
                'report_id': result['report_id'],
                'symptoms_count': len(result['symptoms']),
                'processing_mode': result.get('processing_mode', 'unknown'),
                'api_responses_summary': {}
            }
            
            # 统计每个API的成功率
            for symptom in result['symptoms']:
                for api_name, api_response in symptom.get('api_responses', {}).items():
                    if api_name not in report_summary['api_responses_summary']:
                        report_summary['api_responses_summary'][api_name] = {
                            'total': 0, 'success': 0, 'failed': 0
                        }
                    
                    report_summary['api_responses_summary'][api_name]['total'] += 1
                    if api_response.get('success'):
                        report_summary['api_responses_summary'][api_name]['success'] += 1
                    else:
                        report_summary['api_responses_summary'][api_name]['failed'] += 1
            
            overall_summary['reports'].append(report_summary)
        
        # 保存总体摘要
        summary_file = results_dir / f"overall_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(overall_summary, f, ensure_ascii=False, indent=2)
        
        print(f"📄 总体摘要已保存: {summary_file}")
    
    # 6. 清理批处理文件
    print(f"\n🧹 清理旧的批处理文件...")
    api_manager.cleanup_batch_files(keep_days=7)
    
    # 7. 显示最终统计
    print("\n" + "=" * 70)
    print("🎉 批处理评估完成!")
    print("=" * 70)
    print(f"📊 处理统计:")
    print(f"   处理报告: {len(all_results)}/{len(all_reports)}")
    print(f"   总症状数: {total_symptoms}")
    print(f"   结果目录: {results_dir}")
    print(f"   批处理模式: {'启用' if enable_batch else '禁用'}")
    
    if enable_batch and api_manager.get_batch_client_names():
        print(f"   批处理客户端: {', '.join(api_manager.get_batch_client_names())}")
    
    print("=" * 70)
    
    return len(all_results) > 0


def main():
    parser = argparse.ArgumentParser(
        description="批处理RAG评估系统",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
批处理模式说明:
  --enable-batch     启用批处理模式 (默认启用)
  --disable-batch    禁用批处理模式，使用传统逐条调用
  --batch-threshold  启用批处理的最小症状数量阈值 (默认10)
  --force-batch      强制使用批处理，忽略阈值限制
  
示例:
  python batch_workflow.py 4000                    # 批处理模式评估报告4000
  python batch_workflow.py 4000 4002               # 批量评估4000-4002
  python batch_workflow.py 4000 --disable-batch    # 禁用批处理
  python batch_workflow.py 4000 --force-batch      # 强制批处理
        """
    )
    
    parser.add_argument("start_id", type=int, help="开始报告ID")
    parser.add_argument("end_id", type=int, nargs='?', help="结束报告ID (可选)")
    parser.add_argument("--config", type=str, default="config/config.yaml", help="配置文件路径")
    parser.add_argument("--max_files", type=int, help="最大处理文件数量")
    
    # 批处理相关参数
    batch_group = parser.add_mutually_exclusive_group()
    batch_group.add_argument("--enable-batch", action="store_true", default=True, 
                           help="启用批处理模式 (默认)")
    batch_group.add_argument("--disable-batch", action="store_true", 
                           help="禁用批处理模式")
    
    parser.add_argument("--batch-threshold", type=int, default=10,
                       help="启用批处理的最小症状数量阈值 (默认10)")
    parser.add_argument("--force-batch", action="store_true",
                       help="强制使用批处理，忽略阈值限制")
    
    args = parser.parse_args()
    
    # 处理参数
    start_id = args.start_id
    end_id = args.end_id if args.end_id else start_id
    enable_batch = not args.disable_batch  # 默认启用，除非明确禁用
    
    # 加载配置
    config = load_config(args.config)
    
    # 加载系统提示词
    system_prompt_path = Path(config['paths']['system_prompt'])
    if not system_prompt_path.is_absolute():
        system_prompt_path = Path(__file__).parent.parent / system_prompt_path
    
    system_prompt = load_system_prompt(str(system_prompt_path))
    
    # 运行批处理评估
    success = run_batch_evaluation(
        config=config,
        system_prompt=system_prompt,
        start_id=start_id,
        end_id=end_id,
        enable_batch=enable_batch,
        batch_threshold=args.batch_threshold,
        force_batch=args.force_batch,
        max_files=args.max_files
    )
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
