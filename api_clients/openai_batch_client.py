#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OpenAI Batch API 客户端
支持异步批处理和传统逐条调用的混合模式
"""

import openai
import json
import time
import os
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
from datetime import datetime
import tempfile
import uuid

class OpenAIBatchClient:
    """OpenAI Batch API客户端 - 支持批处理和逐条调用"""
    
    def __init__(self, api_key: str, base_url: str = None, model: str = "gpt-4"):
        self.client = openai.OpenAI(
            api_key=api_key,
            base_url=base_url
        )
        self.model = model
        self.batch_dir = Path("batch_processing")
        self.batch_dir.mkdir(exist_ok=True)
        
    def generate_response(self, 
                         system_prompt: str, 
                         user_prompt: str, 
                         max_tokens: int = 1000,
                         temperature: float = 0.1) -> Dict[str, Any]:
        """传统的逐条生成回复 - 保持向后兼容"""
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
    
    def generate_batch_jsonl(self, 
                           system_prompt: str, 
                           tasks: List[Dict[str, Any]], 
                           max_tokens: int = 1000,
                           temperature: float = 0.1) -> str:
        """生成批处理JSONL文件
        
        Args:
            system_prompt: 系统提示词
            tasks: 任务列表，每个任务包含 {'id': str, 'prompt': str, 'metadata': dict}
            max_tokens: 最大token数
            temperature: 温度参数
            
        Returns:
            生成的JSONL文件路径
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        batch_id = str(uuid.uuid4())[:8]
        jsonl_file = self.batch_dir / f"batch_input_{timestamp}_{batch_id}.jsonl"
        
        with open(jsonl_file, "w", encoding="utf-8") as f:
            for task in tasks:
                line = {
                    "custom_id": task["id"],
                    "method": "POST",
                    "url": "/v1/chat/completions",
                    "body": {
                        "model": self.model,
                        "temperature": temperature,
                        "max_tokens": max_tokens,
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": task["prompt"]},
                        ],
                    },
                }
                f.write(json.dumps(line, ensure_ascii=False) + "\n")
        
        print(f"📝 生成批处理JSONL文件: {jsonl_file}")
        print(f"   包含 {len(tasks)} 个任务")
        return str(jsonl_file)
    
    def create_batch_job(self, jsonl_file_path: str) -> str:
        """创建批处理作业
        
        Args:
            jsonl_file_path: JSONL文件路径
            
        Returns:
            批处理作业ID
        """
        print(f"📤 上传批处理文件: {jsonl_file_path}")
        
        # 上传JSONL文件
        with open(jsonl_file_path, "rb") as f:
            uploaded = self.client.files.create(
                file=f,
                purpose="batch",
            )
        
        print(f"✅ 文件上传成功，文件ID: {uploaded.id}")
        
        # 创建批处理作业
        batch = self.client.batches.create(
            input_file_id=uploaded.id,
            endpoint="/v1/chat/completions",
            completion_window="24h",
        )
        
        print(f"🚀 批处理作业创建成功")
        print(f"   作业ID: {batch.id}")
        print(f"   状态: {batch.status}")
        print(f"   预计完成时间: 24小时内")
        
        return batch.id
    
    def poll_batch_status(self, batch_id: str, poll_interval: int = 30) -> Dict[str, Any]:
        """轮询批处理作业状态直到完成
        
        Args:
            batch_id: 批处理作业ID
            poll_interval: 轮询间隔（秒）
            
        Returns:
            批处理作业信息
        """
        print(f"⏳ 开始轮询批处理作业状态: {batch_id}")
        print(f"   轮询间隔: {poll_interval}秒")
        
        start_time = time.time()
        
        while True:
            try:
                batch = self.client.batches.retrieve(batch_id)
                elapsed = int(time.time() - start_time)
                
                print(f"📊 [{elapsed:04d}s] 状态: {batch.status}")
                
                if batch.status == "completed":
                    print(f"✅ 批处理作业完成!")
                    print(f"   总耗时: {elapsed}秒")
                    print(f"   请求总数: {batch.request_counts.total}")
                    print(f"   成功数: {batch.request_counts.completed}")
                    print(f"   失败数: {batch.request_counts.failed}")
                    return batch.dict()
                    
                elif batch.status in ("failed", "expired", "cancelled"):
                    print(f"❌ 批处理作业失败: {batch.status}")
                    if hasattr(batch, 'errors') and batch.errors:
                        for error in batch.errors:
                            print(f"   错误: {error}")
                    return batch.dict()
                    
                elif batch.status == "in_progress":
                    if hasattr(batch, 'request_counts'):
                        completed = batch.request_counts.completed
                        total = batch.request_counts.total
                        if total > 0:
                            progress = (completed / total) * 100
                            print(f"   进度: {completed}/{total} ({progress:.1f}%)")
                
                time.sleep(poll_interval)
                
            except Exception as e:
                print(f"❌ 轮询状态时出错: {e}")
                time.sleep(poll_interval)
    
    def download_batch_results(self, batch_id: str) -> Dict[str, Any]:
        """下载批处理结果
        
        Args:
            batch_id: 批处理作业ID
            
        Returns:
            解析后的结果字典 {custom_id: response_data}
        """
        print(f"📥 下载批处理结果: {batch_id}")
        
        # 获取批处理信息
        batch = self.client.batches.retrieve(batch_id)
        
        if batch.status != "completed":
            raise RuntimeError(f"批处理作业未完成: {batch.status}")
        
        if not batch.output_file_id:
            raise RuntimeError("批处理作业没有输出文件")
        
        # 下载结果文件
        content = self.client.files.content(batch.output_file_id).content
        lines = content.decode("utf-8").strip().split("\n")
        
        print(f"📊 解析 {len(lines)} 条结果...")
        
        # 解析结果
        results = {}
        success_count = 0
        error_count = 0
        
        for line in lines:
            try:
                obj = json.loads(line)
                custom_id = obj.get("custom_id")
                
                if obj.get("response"):
                    # 成功的响应
                    response_body = obj["response"]["body"]
                    raw_response = response_body["choices"][0]["message"]["content"]
                    usage = response_body.get("usage", {})
                    
                    # 解析JSON内容
                    parsed_data = self._extract_and_parse_json(raw_response)
                    
                    results[custom_id] = {
                        'success': True,
                        'response': raw_response,
                        'parsed_data': parsed_data,
                        'organ_name': parsed_data.get('organ_name', ''),
                        'anatomical_locations': parsed_data.get('anatomical_locations', []),
                        'usage': usage,
                        'model': self.model
                    }
                    success_count += 1
                    
                elif obj.get("error"):
                    # 错误的响应
                    error_info = obj["error"]
                    results[custom_id] = {
                        'success': False,
                        'error': f"{error_info.get('type', 'unknown')}: {error_info.get('message', 'unknown error')}",
                        'model': self.model
                    }
                    error_count += 1
                    
            except Exception as e:
                print(f"⚠️  解析结果行时出错: {e}")
                error_count += 1
        
        print(f"✅ 结果解析完成: {success_count} 成功, {error_count} 失败")
        
        # 保存结果到本地文件
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        result_file = self.batch_dir / f"batch_results_{batch_id}_{timestamp}.json"
        
        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump({
                'batch_id': batch_id,
                'timestamp': timestamp,
                'total_results': len(results),
                'success_count': success_count,
                'error_count': error_count,
                'results': results
            }, f, ensure_ascii=False, indent=2)
        
        print(f"💾 结果已保存到: {result_file}")
        
        return results
    
    def batch_generate(self, 
                      system_prompt: str, 
                      tasks: List[Dict[str, Any]], 
                      max_tokens: int = 1000,
                      temperature: float = 0.1,
                      poll_interval: int = 30) -> Dict[str, Any]:
        """完整的批处理流程
        
        Args:
            system_prompt: 系统提示词
            tasks: 任务列表，每个任务包含 {'id': str, 'prompt': str, 'metadata': dict}
            max_tokens: 最大token数
            temperature: 温度参数
            poll_interval: 轮询间隔（秒）
            
        Returns:
            批处理结果字典 {custom_id: response_data}
        """
        print(f"🚀 开始批处理流程，共 {len(tasks)} 个任务")
        
        # 1. 生成JSONL文件
        jsonl_file = self.generate_batch_jsonl(
            system_prompt=system_prompt,
            tasks=tasks,
            max_tokens=max_tokens,
            temperature=temperature
        )
        
        # 2. 创建批处理作业
        batch_id = self.create_batch_job(jsonl_file)
        
        # 3. 轮询状态直到完成
        batch_info = self.poll_batch_status(batch_id, poll_interval)
        
        # 4. 下载结果
        if batch_info.get('status') == 'completed':
            results = self.download_batch_results(batch_id)
            return results
        else:
            raise RuntimeError(f"批处理作业未成功完成: {batch_info.get('status')}")
    
    def generate_response_with_messages(self, 
                                       messages: list, 
                                       max_tokens: int = 1000,
                                       temperature: float = 0.1) -> Dict[str, Any]:
        """使用消息列表生成回复 - 支持会话复用"""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
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
                'model': self.model,
                'usage': {}
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
            
            # 支持新的智能RAG格式: {"organ": "...", "anatomical_locations": [...], ...}
            if 'organ' in data and 'anatomical_locations' in data:
                organ_name = data.get('organ', '')
                anatomical_locations = data.get('anatomical_locations', [])
                
                return {
                    'organ_name': organ_name,
                    'anatomical_locations': anatomical_locations,
                    'full_response': data
                }
            
            # 支持旧的格式: {"organs": [{"organName": "...", "anatomicalLocations": [...]}]}
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
    
    def cleanup_batch_files(self, keep_days: int = 7):
        """清理旧的批处理文件
        
        Args:
            keep_days: 保留天数
        """
        if not self.batch_dir.exists():
            return
        
        cutoff_time = time.time() - (keep_days * 24 * 3600)
        cleaned_count = 0
        
        for file_path in self.batch_dir.glob("*"):
            if file_path.is_file() and file_path.stat().st_mtime < cutoff_time:
                try:
                    file_path.unlink()
                    cleaned_count += 1
                except Exception as e:
                    print(f"⚠️  清理文件失败 {file_path}: {e}")
        
        if cleaned_count > 0:
            print(f"🧹 清理了 {cleaned_count} 个旧的批处理文件")
