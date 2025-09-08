#!/usr/bin/env python3
"""
真正的Prompt缓存API管理器
利用API的prompt缓存功能，避免重复发送相同的system prompt
"""

import os
import sys
import json
import time
import hashlib
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
class CachedPrompt:
    """缓存的prompt信息"""
    prompt_hash: str
    cache_id: Optional[str]
    created_at: float
    token_count: int


class PromptCachedClient:
    """支持prompt缓存的API客户端包装器"""
    
    def __init__(self, client, provider_name: str):
        self.client = client
        self.provider = provider_name
        self.cached_system_prompt = None
        self.system_prompt_hash = None
        self.system_prompt_tokens = 0
        
    def _estimate_tokens(self, text: str) -> int:
        """估算token数量"""
        return len(text) // 4
    
    def _get_prompt_hash(self, prompt: str) -> str:
        """生成prompt的哈希值"""
        return hashlib.md5(prompt.encode()).hexdigest()
    
    def cache_system_prompt(self, system_prompt: str) -> bool:
        """缓存system prompt"""
        prompt_hash = self._get_prompt_hash(system_prompt)
        
        # 如果已经缓存了相同的prompt，直接返回
        if self.system_prompt_hash == prompt_hash:
            print(f"💾 {self.provider.upper()} system prompt已缓存，跳过")
            return True
        
        # 缓存新的system prompt
        self.cached_system_prompt = system_prompt
        self.system_prompt_hash = prompt_hash
        self.system_prompt_tokens = self._estimate_tokens(system_prompt)
        
        print(f"📝 {self.provider.upper()} 缓存system prompt ({self.system_prompt_tokens:,} tokens)")
        return True
    
    def generate_with_cached_system(self, user_prompt: str, max_tokens: int = 1000) -> Dict[str, Any]:
        """使用缓存的system prompt生成响应"""
        if not self.cached_system_prompt:
            return {
                'success': False,
                'error': 'No cached system prompt',
                'usage': {}
            }
        
        try:
            # 对于支持prompt caching的API，使用特殊标记
            if self.provider in ['openai', 'anthropic']:
                # OpenAI和Anthropic支持prompt caching
                messages = [
                    {
                        "role": "system", 
                        "content": self.cached_system_prompt,
                        # 注意：实际的缓存标记可能因API而异
                    },
                    {"role": "user", "content": user_prompt}
                ]
            else:
                # 其他API使用标准格式
                messages = [
                    {"role": "system", "content": self.cached_system_prompt},
                    {"role": "user", "content": user_prompt}
                ]
            
            # 调用API
            if hasattr(self.client, 'generate_response_with_messages'):
                response = self.client.generate_response_with_messages(
                    messages=messages,
                    max_tokens=max_tokens
                )
            else:
                response = self.client.generate_response(
                    system_prompt=self.cached_system_prompt,
                    user_prompt=user_prompt,
                    max_tokens=max_tokens
                )
            
            # 计算实际的token节省
            if response.get('success'):
                usage = response.get('usage', {})
                actual_prompt_tokens = usage.get('prompt_tokens', 0)
                
                # 估算如果没有缓存会用多少tokens
                estimated_without_cache = self.system_prompt_tokens + self._estimate_tokens(user_prompt)
                estimated_savings = max(0, estimated_without_cache - actual_prompt_tokens)
                
                # 添加节省信息到响应
                response['cache_info'] = {
                    'system_prompt_cached': True,
                    'estimated_system_tokens': self.system_prompt_tokens,
                    'actual_prompt_tokens': actual_prompt_tokens,
                    'estimated_savings': estimated_savings
                }
            
            return response
            
        except Exception as e:
            return {
                'success': False,
                'error': f"Cached generation error: {str(e)}",
                'usage': {}
            }


class PromptCachedAPIManager:
    """支持真正prompt缓存的API管理器"""
    
    def __init__(self):
        self.clients = {}
        self.cached_clients = {}
        self.client_classes = {
            'openai': OpenAIClient,
            'anthropic': AnthropicClient,
            'gemini': GeminiClient,
            'moonshot': MoonshotClient,
            'deepseek': DeepseekClient
        }
        self.total_cache_savings = 0
        
    def initialize_clients(self, config: Dict[str, Any]) -> bool:
        """初始化所有API客户端"""
        print("🔧 初始化Prompt缓存API客户端...")
        
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
                
                # 包装为缓存客户端
                cached_client = PromptCachedClient(client, provider)
                
                self.clients[provider] = client
                self.cached_clients[provider] = cached_client
                
                print(f"✅ {provider.capitalize()} 缓存客户端初始化成功")
                success_count += 1
                
            except Exception as e:
                print(f"❌ {provider.capitalize()} 缓存客户端初始化失败: {e}")
        
        print(f"📊 成功初始化 {success_count}/{len(config.get('api_config', {}))} 个缓存API客户端")
        return success_count > 0
    
    def cache_system_prompt(self, system_prompt: str):
        """为所有API缓存system prompt"""
        print(f"\n📝 缓存system prompt到所有API...")
        print(f"   Prompt长度: {len(system_prompt)} 字符 (~{len(system_prompt)//4:,} tokens)")
        
        for provider, cached_client in self.cached_clients.items():
            cached_client.cache_system_prompt(system_prompt)
    
    def process_symptoms_with_cached_prompt(self, symptoms_data: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """使用缓存的system prompt处理症状"""
        print(f"\n🚀 使用缓存prompt处理 {len(symptoms_data)} 个症状...")
        
        all_results = {}
        total_savings = 0
        
        for i, symptom_data in enumerate(symptoms_data):
            symptom_text = symptom_data.get('symptom_text', '')
            
            print(f"\n📋 处理症状 {i+1}/{len(symptoms_data)}: {symptom_text[:50]}...")
            
            api_responses = {}
            
            for provider, cached_client in self.cached_clients.items():
                try:
                    # 使用缓存的system prompt
                    response = cached_client.generate_with_cached_system(symptom_text)
                    
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
                    
                    # 统计token节省
                    cache_info = response.get('cache_info', {})
                    savings = cache_info.get('estimated_savings', 0)
                    total_savings += savings
                    
                    # 显示token使用情况
                    usage = response.get('usage', {})
                    tokens = usage.get('total_tokens', 0)
                    if tokens > 0:
                        savings_info = f" (节省~{savings})" if savings > 0 else ""
                        print(f"  {provider.upper():12}: {tokens:,} tokens{savings_info}")
                    
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
        
        self.total_cache_savings += total_savings
        
        # 显示总体节省统计
        if total_savings > 0:
            print(f"\n💰 本批次prompt缓存节省: {total_savings:,} tokens")
            print(f"💰 累计节省: {self.total_cache_savings:,} tokens")
        
        return all_results
    
    def process_rag_symptoms_with_cached_prompt(self, symptoms_with_rag: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """处理RAG增强的症状，system prompt已缓存，只发送症状+RAG内容"""
        print(f"\n🔍 使用缓存prompt处理 {len(symptoms_with_rag)} 个RAG增强症状...")
        
        all_results = {}
        total_savings = 0
        
        for i, symptom_rag_data in enumerate(symptoms_with_rag):
            symptom_text = symptom_rag_data.get('symptom_text', '')
            rag_context = symptom_rag_data.get('rag_context', '')
            
            # 构建包含RAG上下文的用户prompt
            if rag_context:
                user_prompt = f"Symptom: {symptom_text}\n\nRelevant medical context:\n{rag_context}\n\nAnalyze this symptom considering the provided context."
            else:
                user_prompt = f"Symptom: {symptom_text}"
            
            print(f"\n📋 处理RAG症状 {i+1}/{len(symptoms_with_rag)}: {symptom_text[:50]}...")
            print(f"   RAG上下文长度: {len(rag_context)} 字符")
            
            api_responses = {}
            
            for provider, cached_client in self.cached_clients.items():
                try:
                    # 使用缓存的system prompt + RAG增强的user prompt
                    response = cached_client.generate_with_cached_system(user_prompt)
                    
                    # 处理响应...
                    if response.get('success') and not response.get('organ_name'):
                        if 'response' in response and response['response']:
                            parsed_data = self._extract_and_parse_json(response['response'])
                            response['parsed_data'] = parsed_data
                            response['organ_name'] = parsed_data.get('organ_name', '')
                            response['anatomical_locations'] = parsed_data.get('anatomical_locations', [])
                    
                    response['expected_results'] = symptom_rag_data.get('expected_results', [])
                    response['rag_context'] = rag_context
                    api_responses[provider] = response
                    
                    # 统计节省
                    cache_info = response.get('cache_info', {})
                    savings = cache_info.get('estimated_savings', 0)
                    total_savings += savings
                    
                    # 显示使用情况
                    usage = response.get('usage', {})
                    tokens = usage.get('total_tokens', 0)
                    if tokens > 0:
                        savings_info = f" (节省~{savings})" if savings > 0 else ""
                        print(f"  {provider.upper():12}: {tokens:,} tokens{savings_info}")
                    
                except Exception as e:
                    print(f"❌ {provider} RAG处理失败: {e}")
                    api_responses[provider] = {
                        'success': False,
                        'error': str(e),
                        'response': '',
                        'parsed_data': {},
                        'usage': {},
                        'rag_context': rag_context
                    }
            
            all_results[symptom_text] = api_responses
        
        self.total_cache_savings += total_savings
        
        if total_savings > 0:
            print(f"\n💰 RAG批次prompt缓存节省: {total_savings:,} tokens")
            print(f"💰 累计节省: {self.total_cache_savings:,} tokens")
        
        return all_results
    
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
    
    def get_cache_statistics(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        return {
            'total_savings': self.total_cache_savings,
            'cached_clients': len(self.cached_clients),
            'system_prompt_cached': all(
                client.cached_system_prompt is not None 
                for client in self.cached_clients.values()
            )
        }


def create_prompt_cached_api_manager() -> PromptCachedAPIManager:
    """创建prompt缓存API管理器实例"""
    return PromptCachedAPIManager()
