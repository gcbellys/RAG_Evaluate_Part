#!/usr/bin/env python3
"""
真正的会话复用API管理器
第一次发送system prompt，后续调用复用对话历史
"""

import os
import sys
import json
import time
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from api_clients.openai_client import OpenAIClient
from api_clients.anthropic_client import AnthropicClient
from api_clients.gemini_client import GeminiClient
from api_clients.moonshot_client import MoonshotClient
from api_clients.deepseek_client import DeepseekClient


@dataclass
class SessionState:
    """会话状态"""
    messages: List[Dict[str, str]]
    system_prompt_sent: bool
    total_calls: int
    total_tokens_saved: int


class SessionReuseClient:
    """支持会话复用的API客户端包装器"""
    
    def __init__(self, client, provider_name: str):
        self.client = client
        self.provider = provider_name
        self.session = SessionState(
            messages=[],
            system_prompt_sent=False,
            total_calls=0,
            total_tokens_saved=0
        )
        self.system_prompt_tokens = 0
        
    def _estimate_tokens(self, text: str) -> int:
        """估算token数量"""
        return len(text) // 4
    
    def initialize_session(self, system_prompt: str) -> bool:
        """初始化会话，发送system prompt"""
        if self.session.system_prompt_sent:
            print(f"💾 {self.provider.upper()} 会话已初始化，跳过")
            return True
        
        self.system_prompt_tokens = self._estimate_tokens(system_prompt)
        
        # 初始化对话历史
        self.session.messages = [
            {"role": "system", "content": system_prompt}
        ]
        self.session.system_prompt_sent = True
        
        print(f"🔄 {self.provider.upper()} 初始化会话 (system prompt: {self.system_prompt_tokens:,} tokens)")
        return True
    
    def generate_with_session_reuse(self, user_prompt: str, max_tokens: int = 1000) -> Dict[str, Any]:
        """使用会话复用生成响应"""
        if not self.session.system_prompt_sent:
            return {
                'success': False,
                'error': 'Session not initialized',
                'usage': {}
            }
        
        try:
            # 添加用户消息到对话历史
            self.session.messages.append({"role": "user", "content": user_prompt})
            
            # 调用API
            if hasattr(self.client, 'generate_response_with_messages'):
                response = self.client.generate_response_with_messages(
                    messages=self.session.messages,
                    max_tokens=max_tokens
                )
            else:
                # 对于不支持messages的客户端，使用传统方式
                response = self.client.generate_response(
                    system_prompt=self.session.messages[0]["content"],
                    user_prompt=user_prompt,
                    max_tokens=max_tokens
                )
            
            # 如果成功，添加助手响应到对话历史
            if response.get('success'):
                assistant_message = response.get('response', '')
                self.session.messages.append({"role": "assistant", "content": assistant_message})
                
                # 计算token节省
                usage = response.get('usage', {})
                actual_prompt_tokens = usage.get('prompt_tokens', 0)
                
                # 估算如果每次都发送system prompt会用多少tokens
                user_tokens = self._estimate_tokens(user_prompt)
                estimated_without_session = self.system_prompt_tokens + user_tokens
                
                # 实际节省 = 估算的完整prompt - 实际使用的prompt tokens
                if self.session.total_calls > 0:  # 第一次调用不算节省
                    estimated_savings = max(0, estimated_without_session - actual_prompt_tokens)
                    self.session.total_tokens_saved += estimated_savings
                else:
                    estimated_savings = 0
                
                self.session.total_calls += 1
                
                # 添加会话信息到响应
                response['session_info'] = {
                    'session_reuse': True,
                    'call_number': self.session.total_calls,
                    'estimated_savings_this_call': estimated_savings,
                    'total_savings': self.session.total_tokens_saved,
                    'conversation_length': len(self.session.messages)
                }
            
            return response
            
        except Exception as e:
            return {
                'success': False,
                'error': f"Session generation error: {str(e)}",
                'usage': {}
            }
    
    def get_session_stats(self) -> Dict[str, Any]:
        """获取会话统计信息"""
        return {
            'total_calls': self.session.total_calls,
            'total_tokens_saved': self.session.total_tokens_saved,
            'conversation_length': len(self.session.messages),
            'system_prompt_sent': self.session.system_prompt_sent
        }


class SessionReuseAPIManager:
    """支持真正会话复用的API管理器"""
    
    def __init__(self):
        self.clients = {}
        self.session_clients = {}
        self.client_classes = {
            'openai': OpenAIClient,
            'anthropic': AnthropicClient,
            'gemini': GeminiClient,
            'moonshot': MoonshotClient,
            'deepseek': DeepseekClient
        }
        self.total_session_savings = 0
        
    def initialize_clients(self, config: Dict[str, Any]) -> bool:
        """初始化所有API客户端"""
        print("🔧 初始化会话复用API客户端...")
        
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
                
                # 创建原始客户端
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
                
                # 包装为会话复用客户端
                session_client = SessionReuseClient(client, provider)
                
                self.clients[provider] = client
                self.session_clients[provider] = session_client
                
                print(f"✅ {provider.capitalize()} 会话复用客户端初始化成功")
                success_count += 1
                
            except Exception as e:
                print(f"❌ {provider.capitalize()} 会话复用客户端初始化失败: {e}")
        
        print(f"📊 成功初始化 {success_count}/{len(config.get('api_config', {}))} 个会话复用API客户端")
        return success_count > 0
    
    def initialize_all_sessions(self, system_prompt: str):
        """为所有API初始化会话"""
        print(f"\n🔄 初始化所有API会话...")
        print(f"   System prompt长度: {len(system_prompt)} 字符 (~{len(system_prompt)//4:,} tokens)")
        
        for provider, session_client in self.session_clients.items():
            session_client.initialize_session(system_prompt)
    
    def process_symptoms_with_session_reuse(self, symptoms_data: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """使用会话复用处理症状"""
        print(f"\n🚀 使用会话复用处理 {len(symptoms_data)} 个症状...")
        
        all_results = {}
        
        for i, symptom_data in enumerate(symptoms_data):
            symptom_text = symptom_data.get('symptom_text', '')
            
            print(f"\n📋 处理症状 {i+1}/{len(symptoms_data)}: {symptom_text[:50]}...")
            
            api_responses = {}
            
            for provider, session_client in self.session_clients.items():
                try:
                    # 使用会话复用
                    response = session_client.generate_with_session_reuse(symptom_text)
                    
                    # 确保响应包含解析后的数据
                    if response.get('success') and not response.get('organ_name'):
                        if 'response' in response and response['response']:
                            parsed_data = self._extract_and_parse_json(response['response'])
                            response['parsed_data'] = parsed_data
                            response['organ_name'] = parsed_data.get('organ_name', '')
                            response['anatomical_locations'] = parsed_data.get('anatomical_locations', [])
                    
                    # 添加期望结果
                    response['expected_results'] = symptom_data.get('expected_results', [])
                    api_responses[provider] = response
                    
                    # 显示token使用情况
                    usage = response.get('usage', {})
                    tokens = usage.get('total_tokens', 0)
                    session_info = response.get('session_info', {})
                    savings = session_info.get('estimated_savings_this_call', 0)
                    
                    if tokens > 0:
                        if savings > 0:
                            print(f"  {provider.upper():12}: {tokens:,} tokens (节省{savings:,})")
                        else:
                            print(f"  {provider.upper():12}: {tokens:,} tokens (首次调用)")
                    
                except Exception as e:
                    print(f"❌ {provider} 处理失败: {e}")
                    api_responses[provider] = {
                        'success': False,
                        'error': str(e),
                        'response': '',
                        'parsed_data': {},
                        'usage': {}
                    }
            
            all_results[symptom_text] = api_responses
        
        # 显示总体会话统计
        self._print_session_statistics()
        
        return all_results
    
    def _print_session_statistics(self):
        """显示会话统计信息"""
        print(f"\n📊 会话复用统计:")
        total_savings = 0
        
        for provider, session_client in self.session_clients.items():
            stats = session_client.get_session_stats()
            if stats['total_calls'] > 0:
                print(f"  {provider.upper():12}:")
                print(f"    调用次数: {stats['total_calls']}")
                print(f"    节省tokens: {stats['total_tokens_saved']:,}")
                print(f"    对话长度: {stats['conversation_length']} 消息")
                total_savings += stats['total_tokens_saved']
        
        if total_savings > 0:
            print(f"\n💰 总计节省: {total_savings:,} tokens")
            self.total_session_savings = total_savings
    
    def _extract_and_parse_json(self, response_text: str) -> Dict[str, Any]:
        """从响应中提取并解析JSON"""
        try:
            # 尝试直接解析
            if response_text.strip().startswith('{'):
                return json.loads(response_text)
            
            # 寻找JSON代码块
            import re
            json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
                parsed = json.loads(json_str)
                
                # 提取器官信息
                if 'organs' in parsed and parsed['organs']:
                    first_organ = parsed['organs'][0]
                    return {
                        'organ_name': first_organ.get('organName', ''),
                        'anatomical_locations': first_organ.get('anatomicalLocations', []),
                        'full_response': parsed
                    }
            
            return {}
            
        except Exception as e:
            print(f"⚠️  JSON解析失败: {e}")
            return {}
    
    def get_session_statistics(self) -> Dict[str, Any]:
        """获取会话统计信息"""
        return {
            'total_savings': self.total_session_savings,
            'session_clients': len(self.session_clients),
            'all_sessions_initialized': all(
                client.session.system_prompt_sent 
                for client in self.session_clients.values()
            )
        }


def create_session_reuse_api_manager() -> SessionReuseAPIManager:
    """创建会话复用API管理器实例"""
    return SessionReuseAPIManager()
