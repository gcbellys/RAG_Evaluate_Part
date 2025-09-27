import os
import time
import re
import json
from typing import Dict, Any, Optional
from openai import OpenAI
from dotenv import load_dotenv

# 加载.env文件
load_dotenv()


class QwenClient:
    """Qwen API客户端"""

    def __init__(self,
                 api_key: Optional[str] = None,
                 base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1",
                 model: str = "qwen-plus"):
        # 支持 .env 中的 DASHSCOPE_API_KEY
        self.client = OpenAI(
            api_key=api_key or os.getenv("DASHSCOPE_API_KEY"),
            base_url=base_url
        )
        self.model = model

    def generate_response(self,
                          system_prompt: str,
                          user_prompt: str,
                          max_tokens: int = 1000,
                          temperature: float = 0.1,
                          enable_thinking: Optional[bool] = None) -> Dict[str, Any]:
        """生成回复"""
        try:
            extra_body = {}
            if enable_thinking is not None:
                extra_body["enable_thinking"] = enable_thinking

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=max_tokens,
                temperature=temperature,
                extra_body=extra_body if extra_body else None
            )

            raw_response = response.choices[0].message.content
            parsed_data = self._extract_and_parse_json(raw_response)

            return {
                "success": True,
                "response": raw_response,
                "parsed_data": parsed_data,
                "usage": response.usage.dict() if response.usage else None,
                "model": self.model
            }

        except Exception as e:
            return {"success": False, "error": str(e), "model": self.model}

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
            time.sleep(0.1)
        return results

    def _extract_and_parse_json(self, text: str) -> Dict[str, Any]:
        """提取和解析JSON"""
        try:
            match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
            if match:
                json_str = match.group(1)
            else:
                match = re.search(r"(\{.*\})", text, re.DOTALL)
                if match:
                    json_str = match.group(1)
                else:
                    return {}

            return json.loads(json_str)
        except Exception as e:
            print(f"JSON解析失败: {e}")
            return {}

    def generate_response_with_messages(self,
                                        messages: list,
                                        max_tokens: int = 1000,
                                        temperature: float = 0.1,
                                        enable_thinking: Optional[bool] = None) -> Dict[str, Any]:
        """使用消息列表生成回复"""
        try:
            extra_body = {}
            if enable_thinking is not None:
                extra_body["enable_thinking"] = enable_thinking

            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                extra_body=extra_body if extra_body else None
            )

            raw_response = response.choices[0].message.content
            parsed_data = self._extract_and_parse_json(raw_response)

            return {
                "success": True,
                "response": raw_response,
                "parsed_data": parsed_data,
                "usage": response.usage.dict() if response.usage else None,
                "model": self.model
            }
        except Exception as e:
            return {"success": False, "error": str(e), "model": self.model}
