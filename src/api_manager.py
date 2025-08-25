#!/usr/bin/env python3
"""
整合的API管理器
包含所有API客户端初始化、管理和调用功能
"""

import os
import sys
from pathlib import Path
from typing import Dict, Any, List

# 尝试加载dotenv
try:
    from dotenv import load_dotenv
    # 指定.env文件的路径
    env_path = Path(__file__).parent.parent / "config" / ".env"
    load_dotenv(env_path)
except ImportError:
    print("⚠️  python-dotenv 未安装，无法自动加载 .env 文件")
    print("   请手动设置环境变量或安装: pip install python-dotenv")

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from api_clients.openai_client import OpenAIClient
from api_clients.anthropic_client import AnthropicClient
from api_clients.gemini_client import GeminiClient
from api_clients.moonshot_client import MoonshotClient
from api_clients.deepseek_client import DeepseekClient

class APIManager:
    """整合的API管理器 - 支持多种API客户端和症状处理"""
    
    def __init__(self):
        self.clients = {}
        self.client_classes = {
            'openai': OpenAIClient,
            'anthropic': AnthropicClient,
            'gemini': GeminiClient,
            'moonshot': MoonshotClient,
            'deepseek': DeepseekClient
        }
    
    def initialize_clients(self, config: Dict[str, Any]) -> bool:
        """初始化所有API客户端"""
        print("🔧 初始化API客户端...")
        
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
                
                # 验证API密钥格式（暂时跳过，因为测试脚本已经证明密钥有效）
                # if not self._validate_api_key(provider, api_key):
                #     print(f"⚠️  {provider.capitalize()} API密钥格式可能不正确")
                #     continue
                
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
                print(f"✅ {provider.capitalize()} 客户端初始化成功")
                success_count += 1
                
            except Exception as e:
                print(f"❌ {provider.capitalize()} 客户端初始化失败: {e}")
        
        print(f"📊 成功初始化 {success_count}/{len(config.get('api_config', {}))} 个API客户端")
        return success_count > 0
    
    def _validate_api_key(self, provider: str, api_key: str) -> bool:
        """验证API密钥格式"""
        if not api_key or len(api_key) < 10:
            return False
        
        # 基本格式检查（更宽松）
        if provider == 'openai' and not (api_key.startswith('sk-') or api_key.startswith('sk-proj-')):
            return False
        elif provider == 'anthropic' and not (api_key.startswith('sk-ant-') or api_key.startswith('sk-')):
            return False
        elif provider == 'gemini' and not (api_key.startswith('AIza') or len(api_key) > 20):
            return False
        elif provider == 'moonshot' and not (api_key.startswith('sk-') or len(api_key) > 20):
            return False
        elif provider == 'deepseek' and not (api_key.startswith('sk-') or len(api_key) > 20):
            return False
        
        return True
    
    def test_connectivity(self, system_prompt: str = None) -> bool:
        """测试所有API客户端的连通性"""
        print("\n🧪 测试API连通性...")
        
        # 使用简单的测试提示词，避免复杂的系统提示词导致的问题
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
                        
                        # 如果是连接错误，尝试重试
                        if 'Connection error' in error_msg or 'timeout' in error_msg.lower():
                            retry_count += 1
                            if retry_count < max_retries:
                                print(f"🔄 连接错误，等待重试...")
                                import time
                                time.sleep(2)  # 等待2秒后重试
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
        
        # 如果没有任何API可用，返回False
        if success_count == 0:
            print("❌ 所有API都不可用，请检查配置")
            return False
        
        # 如果有部分API可用，显示警告但继续
        if success_count < len(self.clients):
            print(f"⚠️  只有 {success_count}/{len(self.clients)} 个API可用")
            print("建议修复不可用的API配置后再继续")
        
        return success_count > 0
    
    def process_symptom(self, symptom_data: Dict[str, Any], system_prompt: str) -> Dict[str, Any]:
        """使用所有API客户端处理单个症状"""
        api_responses = {}
        symptom_text = symptom_data['symptom_text']
        
        for name, client in self.clients.items():
            try:
                response = client.generate_response(
                    system_prompt=system_prompt,
                    user_prompt=symptom_text
                )
                
                # 确保响应包含解析后的数据
                if response.get('success') and not response.get('organ_name'):
                    # 如果API客户端没有解析数据，尝试手动解析
                    if 'response' in response and response['response']:
                        parsed_data = self._extract_and_parse_json(response['response'])
                        response['parsed_data'] = parsed_data
                        response['organ_name'] = parsed_data.get('organ_name', '')
                        response['anatomical_locations'] = parsed_data.get('anatomical_locations', [])
                
                # 将期望结果附加到每个响应中，以便后续评估
                response['expected_results'] = symptom_data['expected_results']
                api_responses[name] = response
            except Exception as e:
                api_responses[name] = {
                    'success': False,
                    'error': str(e),
                    'expected_results': symptom_data['expected_results']
                }
                
        return api_responses
    
    def process_report_symptoms(self, report_data: Dict[str, Any], system_prompt: str) -> Dict[str, Any]:
        """处理整个Report的所有症状"""
        print(f"🔄 处理Report {report_data['report_id']} 的 {len(report_data['symptoms'])} 个症状...")
        
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
    
    def get_client_count(self) -> int:
        """获取已初始化的客户端数量"""
        return len(self.clients)
    
    def get_client_names(self) -> List[str]:
        """获取已初始化的客户端名称列表"""
        return list(self.clients.keys())
    
    def _extract_and_parse_json(self, text: str) -> Dict[str, Any]:
        """提取和解析JSON内容"""
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
            
            # 提取器官名称和解剖位置
            organs = data.get('organs', [])
            if organs:
                # 取第一个器官作为主要器官
                primary_organ = organs[0]
                organ_name = primary_organ.get('organName', '')
                anatomical_locations = primary_organ.get('anatomicalLocations', [])
                
                return {
                    'organ_name': organ_name,
                    'anatomical_locations': anatomical_locations,
                    'full_response': data
                }
            
            return {'organ_name': '', 'anatomical_locations': []}
            
        except Exception as e:
            print(f"JSON解析失败: {e}")
            return {'organ_name': '', 'anatomical_locations': []}
