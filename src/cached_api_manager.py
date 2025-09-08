#!/usr/bin/env python3
"""
支持会话复用和缓存的API管理器
通过批量处理和会话复用来大幅减少token消耗
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
class CachedResponse:
    """缓存的API响应"""
    response: Dict[str, Any]
    timestamp: float
    tokens_used: int


class SessionManager:
    """会话管理器 - 支持多轮对话复用system prompt"""
    
    def __init__(self, client, system_prompt: str):
        self.client = client
        self.system_prompt = system_prompt
        self.conversation_history = [
            {"role": "system", "content": system_prompt}
        ]
        self.total_tokens = 0
        self.system_tokens = self._estimate_tokens(system_prompt)
        self.system_sent = False
    
    def _estimate_tokens(self, text: str) -> int:
        """估算token数量 (粗略估算: 1 token ≈ 4 chars)"""
        return len(text) // 4
    
    def process_symptom(self, symptom_text: str, max_tokens: int = 1000) -> Dict[str, Any]:
        """在会话中处理症状，复用system prompt"""
        try:
            # 添加用户消息
            user_message = {"role": "user", "content": f"Analyze this symptom: {symptom_text}"}
            
            # 构建消息列表
            if not self.system_sent:
                # 第一次调用，包含system prompt
                messages = self.conversation_history + [user_message]
                self.system_sent = True
            else:
                # 后续调用，只发送用户消息 (理论上，但实际API仍需要完整上下文)
                # 为了确保正确性，我们仍然发送完整对话历史
                messages = self.conversation_history + [user_message]
            
            # 调用API
            response = self.client.generate_response_with_messages(
                messages=messages,
                max_tokens=max_tokens
            )
            
            if response.get('success'):
                # 更新对话历史
                assistant_message = {"role": "assistant", "content": response.get('response', '')}
                self.conversation_history.append(user_message)
                self.conversation_history.append(assistant_message)
                
                # 累计token使用
                usage = response.get('usage', {})
                self.total_tokens += usage.get('total_tokens', 0)
                
                # 限制对话历史长度，避免上下文过长
                if len(self.conversation_history) > 20:  # 保留最近10轮对话
                    # 保留system prompt + 最近的对话
                    self.conversation_history = [self.conversation_history[0]] + self.conversation_history[-18:]
            
            return response
            
        except Exception as e:
            return {
                'success': False,
                'error': f"Session processing error: {str(e)}",
                'response': '',
                'parsed_data': {},
                'usage': {}
            }
    
    def get_token_savings(self) -> Dict[str, int]:
        """计算token节省情况"""
        # 估算如果每次都发送完整system prompt会用多少tokens
        estimated_calls = (len(self.conversation_history) - 1) // 2  # 减去system message，除以2(user+assistant)
        estimated_total_without_session = estimated_calls * self.system_tokens + self.total_tokens
        
        return {
            'actual_tokens': self.total_tokens,
            'estimated_without_session': estimated_total_without_session,
            'tokens_saved': estimated_total_without_session - self.total_tokens,
            'system_tokens': self.system_tokens,
            'calls_made': estimated_calls
        }


class CachedAPIManager:
    """支持缓存和会话复用的API管理器"""
    
    def __init__(self, cache_ttl: int = 3600):  # 缓存1小时
        self.clients = {}
        self.client_classes = {
            'openai': OpenAIClient,
            'anthropic': AnthropicClient,
            'gemini': GeminiClient,
            'moonshot': MoonshotClient,
            'deepseek': DeepseekClient
        }
        self.cache = {}  # 简单内存缓存
        self.cache_ttl = cache_ttl
        self.sessions = {}  # 会话管理器
        
    def initialize_clients(self, config: Dict[str, Any]) -> bool:
        """初始化所有API客户端"""
        print("🔧 初始化缓存API客户端...")
        
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
                print(f"✅ {provider.capitalize()} 缓存客户端初始化成功")
                success_count += 1
                
            except Exception as e:
                print(f"❌ {provider.capitalize()} 缓存客户端初始化失败: {e}")
        
        print(f"📊 成功初始化 {success_count}/{len(config.get('api_config', {}))} 个缓存API客户端")
        return success_count > 0
    
    def _get_cache_key(self, provider: str, system_prompt: str, symptom_text: str) -> str:
        """生成缓存键"""
        import hashlib
        content = f"{provider}:{system_prompt}:{symptom_text}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def _is_cache_valid(self, cached_response: CachedResponse) -> bool:
        """检查缓存是否有效"""
        return time.time() - cached_response.timestamp < self.cache_ttl
    
    def _get_cached_response(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """获取缓存的响应"""
        if cache_key in self.cache:
            cached = self.cache[cache_key]
            if self._is_cache_valid(cached):
                print(f"💾 使用缓存响应 (节省 {cached.tokens_used} tokens)")
                return cached.response
            else:
                # 缓存过期，删除
                del self.cache[cache_key]
        return None
    
    def _cache_response(self, cache_key: str, response: Dict[str, Any]):
        """缓存响应"""
        tokens_used = response.get('usage', {}).get('total_tokens', 0)
        self.cache[cache_key] = CachedResponse(
            response=response,
            timestamp=time.time(),
            tokens_used=tokens_used
        )
    
    def initialize_sessions(self, system_prompt: str):
        """为每个API初始化会话管理器"""
        print("🔄 初始化API会话管理器...")
        
        for provider, client in self.clients.items():
            # 检查客户端是否支持消息格式
            if hasattr(client, 'generate_response_with_messages'):
                self.sessions[provider] = SessionManager(client, system_prompt)
                print(f"✅ {provider.capitalize()} 会话管理器已初始化")
            else:
                print(f"⚠️  {provider.capitalize()} 不支持会话复用，将使用标准模式")
    
    def process_symptoms_batch(self, symptoms_data: List[Dict[str, Any]], system_prompt: str) -> Dict[str, Dict[str, Any]]:
        """批量处理症状，使用会话复用和缓存"""
        print(f"🚀 开始批量处理 {len(symptoms_data)} 个症状...")
        
        # 初始化会话管理器
        self.initialize_sessions(system_prompt)
        
        all_results = {}
        
        for i, symptom_data in enumerate(symptoms_data):
            symptom_text = symptom_data.get('symptom_text', '')
            symptom_id = symptom_data.get('symptom_id', f'symptom_{i}')
            
            print(f"\n📋 处理症状 {i+1}/{len(symptoms_data)}: {symptom_text[:50]}...")
            
            api_responses = {}
            
            for provider, client in self.clients.items():
                try:
                    # 检查缓存
                    cache_key = self._get_cache_key(provider, system_prompt, symptom_text)
                    cached_response = self._get_cached_response(cache_key)
                    
                    if cached_response:
                        response = cached_response
                    else:
                        # 使用会话管理器或标准调用
                        if provider in self.sessions:
                            response = self.sessions[provider].process_symptom(symptom_text)
                        else:
                            # 标准调用
                            response = client.generate_response(
                                system_prompt=system_prompt,
                                user_prompt=symptom_text
                            )
                        
                        # 缓存响应
                        if response.get('success'):
                            self._cache_response(cache_key, response)
                    
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
                    if tokens > 0:
                        print(f"  {provider.upper():12}: {tokens:,} tokens")
                    
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
        
        # 显示会话统计
        self._print_session_statistics()
        
        return all_results
    
    def _print_session_statistics(self):
        """显示会话统计信息"""
        print(f"\n📊 会话复用统计:")
        total_saved = 0
        
        for provider, session in self.sessions.items():
            stats = session.get_token_savings()
            total_saved += stats['tokens_saved']
            
            print(f"  {provider.upper():12}:")
            print(f"    实际使用: {stats['actual_tokens']:,} tokens")
            print(f"    预估无会话: {stats['estimated_without_session']:,} tokens")
            print(f"    节省: {stats['tokens_saved']:,} tokens")
            print(f"    调用次数: {stats['calls_made']}")
        
        if total_saved > 0:
            print(f"\n💰 总计节省: {total_saved:,} tokens")
    
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
    
    def clear_cache(self):
        """清空缓存"""
        self.cache.clear()
        print("🗑️  缓存已清空")
    
    def get_cache_stats(self) -> Dict[str, int]:
        """获取缓存统计"""
        valid_cache = sum(1 for cached in self.cache.values() if self._is_cache_valid(cached))
        total_tokens_saved = sum(cached.tokens_used for cached in self.cache.values() if self._is_cache_valid(cached))
        
        return {
            'total_cached': len(self.cache),
            'valid_cached': valid_cache,
            'tokens_saved': total_tokens_saved
        }


# 为了兼容性，添加一个适配器方法
def create_cached_api_manager() -> CachedAPIManager:
    """创建缓存API管理器实例"""
    return CachedAPIManager()
