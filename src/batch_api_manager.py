#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批处理API管理器
支持OpenAI Batch API和传统逐条调用的混合模式
"""

import os
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
import json

# 尝试加载dotenv
try:
    from dotenv import load_dotenv
    # 指定.env文件的路径
    env_path = Path(__file__).parent.parent / "config" / ".env"
    load_dotenv(env_path)
except ImportError:
    print("⚠️  python-dotenv 未安装，无法自动加载 .env 文件")

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from api_clients.openai_batch_client import OpenAIBatchClient
from api_clients.anthropic_client import AnthropicClient
from api_clients.gemini_client import GeminiClient
from api_clients.moonshot_client import MoonshotClient
from api_clients.deepseek_client import DeepseekClient


class BatchAPIManager:
    """支持批处理和逐条调用的API管理器"""
    
    def __init__(self, enable_batch: bool = True, batch_threshold: int = 10):
        """
        Args:
            enable_batch: 是否启用批处理模式
            batch_threshold: 启用批处理的最小任务数量阈值
        """
        self.clients = {}
        self.batch_clients = {}  # 支持批处理的客户端
        self.enable_batch = enable_batch
        self.batch_threshold = batch_threshold
        
        self.client_classes = {
            'openai': OpenAIBatchClient,  # 使用批处理客户端
            'anthropic': AnthropicClient,
            'gemini': GeminiClient,
            'moonshot': MoonshotClient,
            'deepseek': DeepseekClient
        }
        
        # 支持批处理的API提供商
        self.batch_supported = {'openai'}
    
    def initialize_clients(self, config: Dict[str, Any]) -> bool:
        """初始化所有API客户端"""
        print("🔧 初始化API客户端...")
        print(f"   批处理模式: {'启用' if self.enable_batch else '禁用'}")
        print(f"   批处理阈值: {self.batch_threshold} 个任务")
        
        success_count = 0
        for provider in config.get('api_config', {}).keys():
            try:
                client_config = config['api_config'][provider]
                client_class = self.client_classes[provider]
                
                # 从环境变量获取API密钥
                api_key_env = client_config.get('api_key_env')
                if not api_key_env:
                    print(f"⚠️  {provider.capitalize()} 缺少 api_key_env 配置")
                    continue
                
                api_key = os.getenv(api_key_env)
                if not api_key:
                    print(f"⚠️  {provider.capitalize()} 环境变量 {api_key_env} 未设置")
                    continue
                
                if provider in ['openai', 'moonshot', 'deepseek']:
                    client = client_class(
                        api_key=api_key,
                        base_url=client_config.get('base_url'),
                        model=client_config['model']
                    )
                else:
                    client = client_class(
                        api_key=api_key,
                        model=client_config['model']
                    )
                
                self.clients[provider] = client
                
                # 标记支持批处理的客户端
                if provider in self.batch_supported:
                    self.batch_clients[provider] = client
                    print(f"✅ {provider.capitalize()} 客户端初始化成功 (支持批处理)")
                else:
                    print(f"✅ {provider.capitalize()} 客户端初始化成功")
                
                success_count += 1
                
            except Exception as e:
                print(f"❌ {provider.capitalize()} 客户端初始化失败: {e}")
        
        print(f"📊 成功初始化 {success_count}/{len(config.get('api_config', {}))} 个API客户端")
        print(f"   其中 {len(self.batch_clients)} 个支持批处理")
        return success_count > 0
    
    def test_connectivity(self, system_prompt: str = None) -> bool:
        """测试所有API客户端的连通性"""
        print("\n🧪 测试API连通性...")
        
        simple_system_prompt = "You are a helpful assistant."
        test_symptom = "Say hello"
        success_count = 0
        
        for name, client in self.clients.items():
            max_retries = 3
            retry_count = 0
            
            while retry_count < max_retries:
                try:
                    print(f"🔍 测试 {name}... (尝试 {retry_count + 1}/{max_retries})")
                    response = client.generate_response(
                        system_prompt=simple_system_prompt,
                        user_prompt=test_symptom,
                        max_tokens=50
                    )
                    
                    if response.get('success'):
                        print(f"✅ {name} 连接成功")
                        success_count += 1
                        break
                    else:
                        error_msg = response.get('error', '未知错误')
                        print(f"❌ {name} 连接失败: {error_msg}")
                        
                        if 'Connection error' in error_msg or 'timeout' in error_msg.lower():
                            retry_count += 1
                            if retry_count < max_retries:
                                print(f"🔄 连接错误，等待重试...")
                                import time
                                time.sleep(2)
                                continue
                        break
                        
                except Exception as e:
                    print(f"❌ {name} 测试异常: {e}")
                    retry_count += 1
                    if retry_count < max_retries:
                        print(f"🔄 异常，等待重试...")
                        import time
                        time.sleep(2)
                        continue
                    break
        
        print(f"📊 API连通性测试: {success_count}/{len(self.clients)} 成功")
        return success_count > 0
    
    def process_report_symptoms_batch(self, 
                                    report_data: Dict[str, Any], 
                                    system_prompt: str,
                                    force_batch: bool = False) -> Dict[str, Any]:
        """使用批处理模式处理整个Report的所有症状
        
        Args:
            report_data: 报告数据
            system_prompt: 系统提示词
            force_batch: 强制使用批处理（忽略阈值）
        """
        symptoms = report_data['symptoms']
        total_symptoms = len(symptoms)
        
        print(f"🔄 处理Report {report_data['report_id']} 的 {total_symptoms} 个症状...")
        
        # 决定是否使用批处理
        use_batch = (
            self.enable_batch and 
            len(self.batch_clients) > 0 and 
            (total_symptoms >= self.batch_threshold or force_batch)
        )
        
        if use_batch:
            print(f"🚀 使用批处理模式 (阈值: {self.batch_threshold})")
            return self._process_with_batch(report_data, system_prompt)
        else:
            print(f"🔄 使用传统逐条模式")
            return self._process_with_sequential(report_data, system_prompt)
    
    def _process_with_batch(self, report_data: Dict[str, Any], system_prompt: str) -> Dict[str, Any]:
        """使用批处理模式处理症状"""
        symptoms = report_data['symptoms']
        
        # 准备批处理任务
        batch_tasks = {}
        for provider in self.batch_clients.keys():
            batch_tasks[provider] = []
            
            for symptom_data in symptoms:
                task_id = f"{provider}_{symptom_data['symptom_id']}"
                batch_tasks[provider].append({
                    'id': task_id,
                    'prompt': symptom_data['symptom_text'],
                    'metadata': {
                        'symptom_id': symptom_data['symptom_id'],
                        'symptom_index': symptom_data['symptom_index'],
                        'expected_results': symptom_data['expected_results']
                    }
                })
        
        # 执行批处理
        batch_results = {}
        for provider, tasks in batch_tasks.items():
            if not tasks:
                continue
                
            print(f"📦 执行 {provider} 批处理，{len(tasks)} 个任务...")
            
            try:
                client = self.batch_clients[provider]
                results = client.batch_generate(
                    system_prompt=system_prompt,
                    tasks=tasks,
                    max_tokens=1000,
                    temperature=0.1,
                    poll_interval=30
                )
                batch_results[provider] = results
                print(f"✅ {provider} 批处理完成")
                
            except Exception as e:
                print(f"❌ {provider} 批处理失败: {e}")
                print(f"🔄 回退到逐条处理...")
                
                # 回退到逐条处理
                sequential_results = {}
                for task in tasks:
                    try:
                        response = client.generate_response(
                            system_prompt=system_prompt,
                            user_prompt=task['prompt']
                        )
                        sequential_results[task['id']] = response
                    except Exception as seq_e:
                        sequential_results[task['id']] = {
                            'success': False,
                            'error': str(seq_e),
                            'model': getattr(client, 'model', 'unknown')
                        }
                
                batch_results[provider] = sequential_results
        
        # 处理非批处理客户端
        for provider, client in self.clients.items():
            if provider in self.batch_clients:
                continue  # 已经在批处理中处理了
            
            print(f"🔄 处理 {provider} (逐条模式)...")
            provider_results = {}
            
            for symptom_data in symptoms:
                task_id = f"{provider}_{symptom_data['symptom_id']}"
                try:
                    response = client.generate_response(
                        system_prompt=system_prompt,
                        user_prompt=symptom_data['symptom_text']
                    )
                    response['expected_results'] = symptom_data.get('expected_results', [])
                    provider_results[task_id] = response
                    
                except Exception as e:
                    provider_results[task_id] = {
                        'success': False,
                        'error': str(e),
                        'expected_results': symptom_data.get('expected_results', []),
                        'model': getattr(client, 'model', 'unknown')
                    }
            
            batch_results[provider] = provider_results
        
        # 重新组织结果为原始格式
        return self._reorganize_batch_results(report_data, batch_results)
    
    def _process_with_sequential(self, report_data: Dict[str, Any], system_prompt: str) -> Dict[str, Any]:
        """使用传统逐条模式处理症状"""
        from datetime import datetime
        
        report_results = {
            'report_id': report_data['report_id'],
            'file_path': report_data['file_path'],
            'total_symptoms': report_data['total_symptoms'],
            'valid_symptoms': report_data['valid_symptoms'],
            'processing_timestamp': datetime.now().isoformat(),
            'symptoms': []
        }
        
        for symptom_data in report_data['symptoms']:
            print(f"  📝 处理症状: {symptom_data['symptom_text'][:50]}...")
            
            # 调用API处理症状
            api_responses = self.process_symptom(symptom_data, system_prompt)
            
            # 构造症状结果
            symptom_result = {
                'symptom_id': symptom_data['symptom_id'],
                'symptom_index': symptom_data['symptom_index'],
                'symptom_text': symptom_data['symptom_text'],
                'expected_results': symptom_data['expected_results'],
                'total_u_units': symptom_data['total_u_units'],
                'api_responses': api_responses
            }
            
            report_results['symptoms'].append(symptom_result)
        
        return report_results
    
    def _reorganize_batch_results(self, 
                                report_data: Dict[str, Any], 
                                batch_results: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """重新组织批处理结果为原始格式"""
        from datetime import datetime
        
        report_results = {
            'report_id': report_data['report_id'],
            'file_path': report_data['file_path'],
            'total_symptoms': report_data['total_symptoms'],
            'valid_symptoms': report_data['valid_symptoms'],
            'processing_timestamp': datetime.now().isoformat(),
            'processing_mode': 'batch',
            'symptoms': []
        }
        
        for symptom_data in report_data['symptoms']:
            symptom_id = symptom_data['symptom_id']
            
            # 收集该症状的所有API响应
            api_responses = {}
            for provider, provider_results in batch_results.items():
                task_id = f"{provider}_{symptom_id}"
                if task_id in provider_results:
                    response = provider_results[task_id]
                    # 确保包含期望结果
                    response['expected_results'] = symptom_data.get('expected_results', [])
                    api_responses[provider] = response
            
            # 构造症状结果
            symptom_result = {
                'symptom_id': symptom_data['symptom_id'],
                'symptom_index': symptom_data['symptom_index'],
                'symptom_text': symptom_data['symptom_text'],
                'expected_results': symptom_data['expected_results'],
                'total_u_units': symptom_data['total_u_units'],
                'api_responses': api_responses
            }
            
            report_results['symptoms'].append(symptom_result)
        
        return report_results
    
    def process_symptom(self, symptom_data: Dict[str, Any], system_prompt: str) -> Dict[str, Any]:
        """处理单个症状 - 兼容原有接口"""
        api_responses: Dict[str, Any] = {}
        symptom_text = symptom_data.get('symptom_text', '')

        for name, client in self.clients.items():
            try:
                response = client.generate_response(
                    system_prompt=system_prompt,
                    user_prompt=symptom_text
                )
                
                # 确保响应包含解析后的数据
                if response.get('success') and not response.get('organ_name'):
                    if 'response' in response and response['response']:
                        parsed_data = self._extract_and_parse_json(response['response'])
                        response['parsed_data'] = parsed_data
                        response['organ_name'] = parsed_data.get('organ_name', '')
                        response['anatomical_locations'] = parsed_data.get('anatomical_locations', [])
                
                response['expected_results'] = symptom_data.get('expected_results', [])
                api_responses[name] = response
                
            except Exception as e:
                api_responses[name] = {
                    'success': False,
                    'error': str(e),
                    'expected_results': symptom_data.get('expected_results', [])
                }
                
        return api_responses if isinstance(api_responses, dict) else {}
    
    def get_client_count(self) -> int:
        """获取已初始化的客户端数量"""
        return len(self.clients)
    
    def get_client_names(self) -> List[str]:
        """获取已初始化的客户端名称列表"""
        return list(self.clients.keys())
    
    def get_batch_client_names(self) -> List[str]:
        """获取支持批处理的客户端名称列表"""
        return list(self.batch_clients.keys())
    
    def _extract_and_parse_json(self, text: str) -> Dict[str, Any]:
        """提取和解析JSON内容，支持多种格式"""
        try:
            import json
            import re
            
            # 移除Markdown代码块标记
            json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                # 如果没有代码块，尝试直接查找JSON
                json_match = re.search(r'(\{.*\})', text, re.DOTALL)
                if json_match:
                    json_str = json_match.group(1)
                else:
                    return {'organ_name': '', 'anatomical_locations': []}
            
            # 解析JSON
            data = json.loads(json_str)
            
            # 支持新的智能RAG格式
            if 'organ' in data and 'anatomical_locations' in data:
                organ_name = data.get('organ', '')
                anatomical_locations = data.get('anatomical_locations', [])
                
                return {
                    'organ_name': organ_name,
                    'anatomical_locations': anatomical_locations,
                    'full_response': data
                }
            
            # 支持旧的格式: 多器官支持
            organs = data.get('organs', [])
            if organs:
                # 🔧 修复：支持多器官输出
                all_organ_names = []
                all_anatomical_locations = []
                
                for organ in organs:
                    organ_name = organ.get('organName', '')
                    locations = organ.get('anatomicalLocations', [])
                    
                    if organ_name:
                        all_organ_names.append(organ_name)
                        all_anatomical_locations.extend(locations)
                
                unique_locations = list(dict.fromkeys(all_anatomical_locations))
                
                return {
                    'organ_names': all_organ_names,
                    'organ_name': all_organ_names[0] if all_organ_names else '',
                    'anatomical_locations': unique_locations,
                    'total_organs': len(all_organ_names),
                    'full_response': data
                }
            
            return {'organ_name': '', 'anatomical_locations': []}
            
        except Exception as e:
            print(f"JSON解析失败: {e}")
            return {'organ_name': '', 'anatomical_locations': []}
    
    def cleanup_batch_files(self, keep_days: int = 7):
        """清理所有批处理客户端的旧文件"""
        for provider, client in self.batch_clients.items():
            if hasattr(client, 'cleanup_batch_files'):
                try:
                    client.cleanup_batch_files(keep_days)
                except Exception as e:
                    print(f"⚠️  清理 {provider} 批处理文件失败: {e}")
