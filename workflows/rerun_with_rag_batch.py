#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
独立脚本：使用已有的RAG检索结果重新运行LLM评估（批处理优化版）

功能:
1. 根据报告ID，自动查找最新的RAG检索缓存文件。
2. 逐一处理缓存文件中的每个症状。
3. 将RAG检索结果格式化后，构建增强型Prompt。
4. 调用BatchAPIManager，让所有配置的LLM重新处理这些增强型Prompt（OpenAI使用Batch API）。
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
    from batch_api_manager import BatchAPIManager  # 使用批处理API管理器
    from evaluator import Evaluator
    from utils.logger import ReportLogger
except ImportError as e:
    print("错误: 无法导入必要的模块。请确保此脚本位于项目根目录，并且'src'文件夹存在。")
    print(f"详细错误: {e}")
    sys.exit(1)


class RerunWorkflowBatch:
    """使用已有RAG结果重新运行LLM的工作流（批处理优化版）"""

    def __init__(self, report_id: int, 
                 config_path: str = "config/config.yaml",
                 enable_batch: bool = True,
                 batch_threshold: int = 10,
                 data_dir: str = "test_set"):
        self.report_id = report_id
        self.data_dir = data_dir
        self.config = ConfigLoader(config_path)
        
        # 使用批处理API管理器
        self.api_manager = BatchAPIManager(
            enable_batch=enable_batch,
            batch_threshold=batch_threshold
        )
        
        self.evaluator = Evaluator()
        self.logger = ReportLogger()

        # --- 路径定义 ---
        # 获取项目根目录（从workflows/向上一级）
        self.project_root = Path(__file__).resolve().parent.parent
        
        # 从配置文件获取输出路径
        output_base = self.config.get_path('output_results')
        self.output_base_dir = self.project_root / output_base
        
        # RAG检索结果目录
        self.rag_cache_dir = self.output_base_dir / "rag_search_output"
        
        # 输出目录（使用不同的目录名以区分）
        self.output_dir = self.output_base_dir / "rerun_with_rag_batch"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # 日志目录
        self.logs_dir = self.project_root / "logs"
        self.logs_dir.mkdir(exist_ok=True)

    def find_latest_rag_cache(self) -> str:
        """查找指定报告ID的最新RAG缓存文件"""
        print(f"🔍 查找报告 {self.report_id} 的RAG缓存文件...")
        print(f"   搜索目录: {self.rag_cache_dir}")
        
        if not self.rag_cache_dir.exists():
            raise FileNotFoundError(f"RAG缓存目录不存在: {self.rag_cache_dir}")
        
        # 搜索模式：包含报告ID的JSONL文件
        pattern = f"report_{self.report_id}_ragoutcome:*.jsonl"
        cache_files = list(self.rag_cache_dir.glob(pattern))
        
        if not cache_files:
            raise FileNotFoundError(f"未找到报告 {self.report_id} 的RAG缓存文件")
        
        # 按修改时间排序，选择最新的
        latest_file = max(cache_files, key=lambda x: x.stat().st_mtime)
        
        print(f"✅ 找到RAG缓存文件: {latest_file}")
        print(f"   文件大小: {latest_file.stat().st_size / 1024:.1f} KB")
        print(f"   修改时间: {datetime.fromtimestamp(latest_file.stat().st_mtime)}")
        
        return str(latest_file)

    def load_rag_cache(self, cache_file_path: str) -> Dict[str, Any]:
        """加载RAG缓存文件"""
        print(f"📂 加载RAG缓存文件: {cache_file_path}")
        
        try:
            with open(cache_file_path, 'r', encoding='utf-8') as f:
                raw_data = json.load(f)
            
            # 处理不同的缓存文件格式
            if isinstance(raw_data, list):
                # 新格式：数组格式的RAG缓存
                print("   检测到数组格式的RAG缓存文件")
                
                # 转换为标准格式
                cache_data = {
                    'report_id': self.report_id,
                    'file_path': f"diagnostic_{self.report_id}.json",
                    'cache_file': cache_file_path,
                    'symptoms': []
                }
                
                # 处理每个查询项
                for item in raw_data:
                    if 'query' in item and 's' in item:
                        # 提取症状文本和RAG结果
                        symptom_text = item['query']
                        rag_results = []
                        
                        # 处理RAG搜索结果
                        s_data = item['s']
                        for s_key, s_value in s_data.items():
                            if isinstance(s_value, dict) and 's_text' in s_value:
                                rag_results.append({
                                    'content': s_value['s_text'],
                                    'source': s_key,
                                    'score': 0.9,  # 默认相似度分数
                                    'metadata': s_value.get('units', [])
                                })
                        
                        # 构建症状数据
                        symptom_data = {
                            'symptom_id': f"diagnostic_{self.report_id}_symptom_{len(cache_data['symptoms'])}",
                            'symptom_index': len(cache_data['symptoms']),
                            'symptom_text': symptom_text,
                            'expected_results': [{
                                'organName': item.get('expected_organs', [''])[0] if item.get('expected_organs') else '',
                                'anatomicalLocations': item.get('expected_a_locations', [])
                            }],
                            'rag_results': rag_results,
                            'total_u_units': len(rag_results)
                        }
                        
                        cache_data['symptoms'].append(symptom_data)
                
            elif isinstance(raw_data, dict):
                # 旧格式：字典格式的RAG缓存
                print("   检测到字典格式的RAG缓存文件")
                cache_data = raw_data
                
                # 验证必要字段
                if 'report_id' not in cache_data:
                    cache_data['report_id'] = self.report_id
                
                if 'symptoms' not in cache_data:
                    raise ValueError("缓存文件缺少 symptoms 字段")
            
            else:
                raise ValueError("不支持的缓存文件格式")
            
            symptoms_count = len(cache_data['symptoms'])
            print(f"✅ RAG缓存加载成功")
            print(f"   报告ID: {cache_data['report_id']}")
            print(f"   症状数量: {symptoms_count}")
            
            return cache_data
            
        except Exception as e:
            print(f"❌ RAG缓存加载失败: {e}")
            raise

    def format_rag_context(self, rag_results: List[Dict[str, Any]]) -> str:
        """格式化RAG检索结果为上下文文本"""
        if not rag_results:
            return "未找到相关参考信息。"
        
        context_parts = []
        context_parts.append("参考信息：")
        
        for i, result in enumerate(rag_results, 1):
            content = result.get('content', '').strip()
            source = result.get('source', '未知来源')
            score = result.get('score', 0.0)
            
            if content:
                context_parts.append(f"\n{i}. 来源：{source} (相似度: {score:.3f})")
                context_parts.append(f"   内容：{content}")
        
        return '\n'.join(context_parts)

    def build_enhanced_prompt(self, symptom_text: str, rag_context: str) -> str:
        """构建增强型提示词"""
        enhanced_prompt = f"""症状描述：
{symptom_text}

{rag_context}

请基于上述症状描述和参考信息，分析并输出结果。"""
        
        return enhanced_prompt

    def process_symptoms_with_rag(self, cache_data: Dict[str, Any], 
                                 system_prompt: str,
                                 force_batch: bool = False) -> Dict[str, Any]:
        """使用RAG增强信息处理症状（支持批处理）"""
        symptoms = cache_data['symptoms']
        report_id = cache_data['report_id']
        
        print(f"\n📋 开始处理报告 {report_id} 的 {len(symptoms)} 个症状...")
        print(f"🚀 批处理模式: {'启用' if self.api_manager.enable_batch else '禁用'}")
        print(f"📊 批处理阈值: {self.api_manager.batch_threshold}")
        print(f"🎯 强制批处理: {'是' if force_batch else '否'}")
        
        # 准备增强后的症状数据
        enhanced_symptoms = []
        
        for symptom in symptoms:
            symptom_text = symptom.get('symptom_text', '')
            rag_results = symptom.get('rag_results', [])
            
            # 格式化RAG上下文
            rag_context = self.format_rag_context(rag_results)
            
            # 构建增强型提示词
            enhanced_prompt = self.build_enhanced_prompt(symptom_text, rag_context)
            
            # 构建增强后的症状数据
            enhanced_symptom = {
                'symptom_id': symptom.get('symptom_id'),
                'symptom_index': symptom.get('symptom_index'),
                'symptom_text': enhanced_prompt,  # 使用增强后的提示词
                'original_symptom_text': symptom_text,  # 保留原始症状文本
                'rag_context': rag_context,  # 保留RAG上下文
                'rag_results': rag_results,  # 保留原始RAG结果
                'expected_results': symptom.get('expected_results', []),
                'total_u_units': symptom.get('total_u_units', 0)
            }
            
            enhanced_symptoms.append(enhanced_symptom)
        
        # 构建增强后的报告数据
        enhanced_report_data = {
            'report_id': report_id,
            'file_path': cache_data.get('file_path', ''),
            'total_symptoms': len(enhanced_symptoms),
            'valid_symptoms': len(enhanced_symptoms),
            'symptoms': enhanced_symptoms
        }
        
        # 使用批处理API管理器处理症状
        try:
            report_results = self.api_manager.process_report_symptoms_batch(
                report_data=enhanced_report_data,
                system_prompt=system_prompt,
                force_batch=force_batch
            )
            
            # 添加RAG相关的元数据
            report_results['rag_enhanced'] = True
            report_results['rag_cache_file'] = cache_data.get('cache_file', '')
            report_results['processing_mode'] = report_results.get('processing_mode', 'sequential') + '_rag'
            
            print(f"✅ 报告 {report_id} RAG增强处理完成")
            return report_results
            
        except Exception as e:
            print(f"❌ 报告 {report_id} RAG增强处理失败: {e}")
            raise

    def save_results(self, results: Dict[str, Any]) -> str:
        """保存结果到文件"""
        report_id = results.get('report_id', 'unknown')
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 生成文件名
        filename = f"rag_enhanced_batch_report_{report_id}_{timestamp}.json"
        output_file = self.output_dir / filename
        
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
            
            print(f"💾 结果已保存: {output_file}")
            print(f"   文件大小: {output_file.stat().st_size / 1024:.1f} KB")
            
            return str(output_file)
            
        except Exception as e:
            print(f"❌ 结果保存失败: {e}")
            raise

    def run(self, force_batch: bool = False) -> bool:
        """运行完整的RAG增强评估流程"""
        
        print("=" * 70)
        print("🎯 RAG增强评估（批处理优化版）")
        print("=" * 70)
        print(f"📋 报告ID: {self.report_id}")
        print(f"🚀 批处理模式: {'启用' if self.api_manager.enable_batch else '禁用'}")
        print(f"📊 批处理阈值: {self.api_manager.batch_threshold}")
        print(f"🎯 强制批处理: {'是' if force_batch else '否'}")
        print("=" * 70)
        
        try:
            # 1. 查找并加载RAG缓存
            print(f"\n{'='*20} 步骤 1/4: 加载RAG缓存 {'='*20}")
            cache_file = self.find_latest_rag_cache()
            cache_data = self.load_rag_cache(cache_file)
            
            # 2. 初始化API客户端
            print(f"\n{'='*20} 步骤 2/4: 初始化API客户端 {'='*20}")
            if not self.api_manager.initialize_clients(self.config.config):
                print("❌ API客户端初始化失败")
                return False
            
            # 3. 加载系统提示词并测试连通性
            system_prompt_path = Path(self.config.get_path('system_prompt'))
            if not system_prompt_path.is_absolute():
                system_prompt_path = self.project_root / system_prompt_path
            
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
            
            # 4. 处理症状
            print(f"\n{'='*20} 步骤 3/4: RAG增强处理 {'='*20}")
            results = self.process_symptoms_with_rag(
                cache_data, 
                system_prompt, 
                force_batch=force_batch
            )
            
            # 5. 保存结果
            print(f"\n{'='*20} 步骤 4/4: 保存结果 {'='*20}")
            output_file = self.save_results(results)
            
            # 6. 清理批处理文件
            print(f"\n🧹 清理旧的批处理文件...")
            self.api_manager.cleanup_batch_files(keep_days=7)
            
            # 7. 显示最终统计
            print("\n" + "=" * 70)
            print("🎉 RAG增强评估（批处理优化）完成!")
            print("=" * 70)
            print(f"📊 处理统计:")
            print(f"   报告ID: {self.report_id}")
            print(f"   症状数量: {len(results.get('symptoms', []))}")
            print(f"   输出文件: {output_file}")
            print(f"   批处理模式: {'启用' if self.api_manager.enable_batch else '禁用'}")
            
            if self.api_manager.enable_batch and self.api_manager.get_batch_client_names():
                print(f"   批处理客户端: {', '.join(self.api_manager.get_batch_client_names())}")
                print(f"   💰 OpenAI成本节省: ~50%")
            
            print("=" * 70)
            
            return True
            
        except Exception as e:
            print(f"\n❌ RAG增强评估失败: {e}")
            return False


def main():
    parser = argparse.ArgumentParser(
        description="RAG增强评估（批处理优化版）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
这是RAG增强评估的批处理优化版本：
- 使用已有的RAG检索缓存
- 构建增强型提示词
- OpenAI API调用使用Batch API，成本降低50%
- 其他API保持传统逐条调用模式
- 支持智能阈值控制和自动回退

适用场景：
- 已有RAG检索缓存
- 需要RAG增强评估
- 希望降低OpenAI API成本

示例:
  python rerun_with_rag_batch.py 4000
  python rerun_with_rag_batch.py 4000 --force-batch
  python rerun_with_rag_batch.py 4000 --disable-batch
        """
    )
    
    parser.add_argument("report_id", type=int, help="报告ID")
    parser.add_argument("--config", type=str, default="config/config.yaml", help="配置文件路径")
    
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
    workflow = RerunWorkflowBatch(
        report_id=args.report_id,
        config_path=args.config,
        enable_batch=not args.disable_batch,
        batch_threshold=args.batch_threshold,
        data_dir=args.data_dir
    )
    
    # 运行RAG增强评估
    success = workflow.run(force_batch=args.force_batch)
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
