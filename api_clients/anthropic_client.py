import anthropic
from typing import Dict, Any, Optional
import time
import hashlib
import json
from pathlib import Path

class PromptCacheManager:
    """提示词缓存管理器"""
    
    def __init__(self):
        self.cache_dir = Path.home() / ".cache" / "rag_evaluate" / "anthropic_cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_map = {}  # prompt_hash -> cache_id
        self.load_cache_mapping()
    
    def get_cache_id(self, prompt_text: str) -> Optional[str]:
        """获取缓存的ID"""
        prompt_hash = hashlib.md5(prompt_text.encode()).hexdigest()
        return self.cache_map.get(prompt_hash)
    
    def save_cache_id(self, prompt_text: str, cache_id: str):
        """保存缓存ID"""
        prompt_hash = hashlib.md5(prompt_text.encode()).hexdigest()
        self.cache_map[prompt_hash] = cache_id
        
        # 保存到文件
        cache_file = self.cache_dir / "cache_mapping.json"
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(self.cache_map, f, ensure_ascii=False, indent=2)
    
    def load_cache_mapping(self):
        """加载缓存映射"""
        cache_file = self.cache_dir / "cache_mapping.json"
        if cache_file.exists():
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    self.cache_map = json.load(f)
            except:
                self.cache_map = {}


class AnthropicClient:
    """Anthropic API客户端 - 使用官方anthropic包，支持Prompt Caching"""
    
    def __init__(self, api_key: str, base_url: str = None, model: str = "claude-3-7-sonnet-20250219"):
        # 强制使用官方API，忽略传入的base_url参数
        self.client = anthropic.Anthropic(
            api_key=api_key,
            base_url="https://api.anthropic.com"
        )
        self.model = model
        self.cache_manager = PromptCacheManager()
        
    def generate_response(self,
                         system_prompt: str,
                         user_prompt: str,
                         max_tokens: int = 1000,
                         temperature: float = 0.1,
                         use_caching: bool = True) -> Dict[str, Any]:
        """生成回复，支持Prompt Caching"""
        try:
            # 如果不使用缓存，直接走标准流程
            if not use_caching:
                messages = [
                    {
                        "role": "user",
                        "content": f"{system_prompt}\n\nSymptom: {user_prompt}"
                    }
                ]
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    messages=messages
                )
            else:
                # 使用缓存流程
                # 无论是否已存在缓存，API调用结构都是一样的
                messages = [
                    {
                        "role": "user",
                        "content": f"Symptom: {user_prompt}"
                    }
                ]
                
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    messages=messages,
                    system=[
                        {
                            "type": "text",
                            "text": system_prompt,
                            # 使用 ephemeral 类型的缓存
                            "cache_control": {"type": "ephemeral"}
                        }
                    ]
                )
                
                # API调用后，检查是否是第一次创建了缓存
                # 使用正确的字段名：cache_creation_input_tokens 和 cache_read_input_tokens
                cache_created = False
                if hasattr(response.usage, 'cache_creation_input_tokens'):
                    cache_created = response.usage.cache_creation_input_tokens > 0
                
                # 如果缓存刚刚被创建，并且我们本地还没记录，就保存它
                if cache_created and not self.cache_manager.get_cache_id(system_prompt):
                    print("检测到缓存创建，正在保存...")
                    # 注意：Anthropic的ephemeral缓存没有返回具体的ID，我们只需记录一个状态即可
                    self.cache_manager.save_cache_id(system_prompt, "cached_for_session")

            # --- 后续的JSON解析和结果格式化代码保持不变 ---
            raw_response = response.content[0].text
            parsed_data = self._extract_and_parse_json(raw_response)
            
            # 构造统一的usage返回结构
            # 使用正确的字段名：cache_creation_input_tokens 和 cache_read_input_tokens
            usage_info = {
                'total_tokens': 0,
                'prompt_tokens': 0,
                'completion_tokens': 0,
                'cache_creation_tokens': 0,  # 保持兼容性，实际使用 *_input_tokens 字段
                'cache_read_tokens': 0,      # 保持兼容性，实际使用 *_input_tokens 字段
            }
            if response.usage:
                usage_info['prompt_tokens'] = response.usage.input_tokens
                usage_info['completion_tokens'] = response.usage.output_tokens
                usage_info['total_tokens'] = response.usage.input_tokens + response.usage.output_tokens
                if hasattr(response.usage, 'cache_creation_input_tokens'):
                    usage_info['cache_creation_tokens'] = response.usage.cache_creation_input_tokens
                if hasattr(response.usage, 'cache_read_input_tokens'):
                    usage_info['cache_read_tokens'] = response.usage.cache_read_input_tokens

            return {
                'success': True,
                'response': raw_response,
                'parsed_data': parsed_data,
                'organ_name': parsed_data.get('organ_name', ''),
                'anatomical_locations': parsed_data.get('anatomical_locations', []),
                'usage': usage_info,
                'model': self.model
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'model': self.model
            }
    
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
    
    def batch_generate(self,
                       system_prompt: str,
                       prompts: list,
                       use_caching: bool = True,
                       **kwargs) -> list:
        """批量生成回复，支持Prompt Caching"""
        results = []
        
        for i, prompt in enumerate(prompts):
            print(f"处理第 {i+1}/{len(prompts)} 个请求...")
            result = self.generate_response(system_prompt, prompt, use_caching=use_caching, **kwargs)
            results.append(result)
            
            # 添加延迟避免API限制
            time.sleep(0.1)
        
        return results
