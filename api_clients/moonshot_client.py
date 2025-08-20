import openai
from typing import Dict, Any, Optional
import time

class MoonshotClient:
    """Moonshot API客户端"""
    
    def __init__(self, api_key: str, base_url: str = "https://api.moonshot.cn/v1", model: str = "moonshot-v1-8k"):
        self.client = openai.OpenAI(
            api_key=api_key,
            base_url=base_url
        )
        self.model = model
        
    def generate_response(self, 
                         system_prompt: str, 
                         user_prompt: str, 
                         max_tokens: int = 1000,
                         temperature: float = 0.1) -> Dict[str, Any]:
        """生成回复"""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=max_tokens,
                temperature=temperature
            )
            
            raw_response = response.choices[0].message.content
            
            # 尝试提取和解析JSON
            parsed_data = self._extract_and_parse_json(raw_response)
            
            return {
                'success': True,
                'response': raw_response,
                'parsed_data': parsed_data,
                'organ_name': parsed_data.get('organ_name', ''),
                'anatomical_locations': parsed_data.get('anatomical_locations', []),
                'usage': response.usage.dict() if response.usage else None,
                'model': self.model
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'model': self.model
            }
    
    def batch_generate(self, 
                       system_prompt: str, 
                       prompts: list, 
                       **kwargs) -> list:
        """批量生成回复"""
        results = []
        
        for i, prompt in enumerate(prompts):
            print(f"处理第 {i+1}/{len(prompts)} 个请求...")
            result = self.generate_response(system_prompt, prompt, **kwargs)
            results.append(result)
            
            # 添加延迟避免API限制
            time.sleep(0.1)
            
        return results
    
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
