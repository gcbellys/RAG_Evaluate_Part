import requests
import json
from typing import Dict, Any
import time
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

class GeminiClient:
    """Gemini API客户端 - 使用原生REST API"""
    
    def __init__(self, api_key: str, model: str = "gemini-2.0-flash"):
        self.api_key = api_key
        self.model = model
        self.base_url = "https://generativelanguage.googleapis.com/v1beta"
        
        # 创建带重试机制的session
        self.session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
    def generate_response(self, 
                         system_prompt: str, 
                         user_prompt: str, 
                         max_tokens: int = 1000,
                         temperature: float = 0.1) -> Dict[str, Any]:
        """生成回复"""
        try:
            # 合并系统提示词和用户提示词
            full_prompt = f"{system_prompt}\n\nSymptom: {user_prompt}"
            
            url = f"{self.base_url}/models/{self.model}:generateContent"
            
            headers = {
                'Content-Type': 'application/json',
                'X-goog-api-key': self.api_key
            }
            
            data = {
                "contents": [
                    {
                        "parts": [
                            {
                                "text": full_prompt
                            }
                        ]
                    }
                ]
            }
            
            # 使用session进行请求，增加SSL验证选项
            response = self.session.post(
                url, 
                headers=headers, 
                json=data, 
                timeout=60,
                verify=True  # 确保SSL验证
            )
            
            if response.status_code == 200:
                result = response.json()
                
                if 'candidates' in result and len(result['candidates']) > 0:
                    text = result['candidates'][0]['content']['parts'][0]['text']
                    
                    # 提取使用量信息
                    usage = {}
                    if 'usageMetadata' in result:
                        usage_meta = result['usageMetadata']
                        usage = {
                            'prompt_tokens': usage_meta.get('promptTokenCount', 0),
                            'completion_tokens': usage_meta.get('candidatesTokenCount', 0),
                            'total_tokens': usage_meta.get('totalTokenCount', 0)
                        }
                    
                    # 尝试解析JSON响应
                    parsed_data = self._extract_and_parse_json(text)
                    
                    # 标准化输出格式，与其他API保持一致
                    standardized_data = self._standardize_output(parsed_data)
                    
                    return {
                        'success': True,
                        'response': text,
                        'parsed_data': standardized_data,
                        'usage': usage,
                        'model': self.model
                    }
                else:
                    return {
                        'success': False,
                        'error': 'No candidates in response',
                        'model': self.model
                    }
            else:
                return {
                    'success': False,
                    'error': f"API request failed: {response.status_code} - {response.text}",
                    'model': self.model
                }
            
        except requests.exceptions.SSLError as e:
            return {
                'success': False,
                'error': f"SSL连接错误: {str(e)}",
                'model': self.model
            }
        except requests.exceptions.ConnectionError as e:
            return {
                'success': False,
                'error': f"连接错误: {str(e)}",
                'model': self.model
            }
        except requests.exceptions.Timeout as e:
            return {
                'success': False,
                'error': f"请求超时: {str(e)}",
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
    
    def _extract_and_parse_json(self, text: str) -> dict:
        """从文本中提取并解析JSON"""
        try:
            # 尝试直接解析
            import json
            return json.loads(text)
        except json.JSONDecodeError:
            # 如果直接解析失败，尝试从Markdown代码块中提取
            import re
            import json
            
            # 查找JSON代码块
            json_pattern = r'```(?:json)?\s*(\{.*?\})\s*```'
            match = re.search(json_pattern, text, re.DOTALL)
            
            if match:
                try:
                    json_str = match.group(1)
                    return json.loads(json_str)
                except json.JSONDecodeError:
                    pass
            
            # 如果都失败了，返回空字典
            return {}
    
    def _standardize_output(self, parsed_data: dict) -> dict:
        """标准化输出格式，与其他API保持一致"""
        try:
            if not parsed_data or 'organs' not in parsed_data:
                return {}
            
            # 获取第一个器官的信息（与其他API保持一致）
            first_organ = parsed_data['organs'][0] if parsed_data['organs'] else {}
            
            return {
                'organ_name': first_organ.get('organName', ''),
                'anatomical_locations': first_organ.get('anatomicalLocations', []),
                'full_response': parsed_data
            }
        except Exception:
            return {}
