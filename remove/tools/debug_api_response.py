#!/usr/bin/env python3
"""
调试API响应内容
检查API返回的原始数据
"""

import os
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

# 加载环境变量
from dotenv import load_dotenv
env_path = Path(__file__).parent.parent / "config" / ".env"
load_dotenv(env_path)

def test_api_raw_response():
    """测试API的原始响应"""
    print("🧪 测试API原始响应")
    print("=" * 50)
    
    # 测试症状
    test_symptom = "80 millimeter aortic valve gradient"
    
    # 测试OpenAI
    print(f"\n📞 测试OpenAI: {test_symptom}")
    try:
        from api_clients.openai_client import OpenAIClient
        
        api_key = os.getenv('OPENAI_API_KEY')
        client = OpenAIClient(api_key=api_key, model="gpt-4")
        
        response = client.generate_response(
            system_prompt="You are a helpful assistant.",
            user_prompt=test_symptom,
            max_tokens=200
        )
        
        print(f"✅ 调用成功: {response['success']}")
        if response.get('success'):
            print(f"📝 原始响应: {response['response']}")
        else:
            print(f"❌ 错误: {response.get('error')}")
            
    except Exception as e:
        print(f"❌ 异常: {e}")
    
    # 测试Anthropic
    print(f"\n📞 测试Anthropic: {test_symptom}")
    try:
        from api_clients.anthropic_client import AnthropicClient
        
        api_key = os.getenv('ANTHROPIC_API_KEY')
        client = AnthropicClient(api_key=api_key)
        
        response = client.generate_response(
            system_prompt="You are a helpful assistant.",
            user_prompt=test_symptom,
            max_tokens=200
        )
        
        print(f"✅ 调用成功: {response['success']}")
        if response.get('success'):
            print(f"📝 原始响应: {response['response']}")
        else:
            print(f"❌ 错误: {response.get('error')}")
            
    except Exception as e:
        print(f"❌ 异常: {e}")

def test_with_system_prompt():
    """使用实际的系统提示词测试"""
    print(f"\n🧪 使用实际系统提示词测试")
    print("=" * 50)
    
    # 读取系统提示词
    prompt_path = Path(__file__).parent.parent / "prompt" / "system_prompt.txt"
    if prompt_path.exists():
        with open(prompt_path, 'r', encoding='utf-8') as f:
            system_prompt = f.read()
        print(f"📄 系统提示词长度: {len(system_prompt)} 字符")
        print(f"📄 前100字符: {system_prompt[:100]}...")
    else:
        print("❌ 系统提示词文件不存在")
        return
    
    test_symptom = "80 millimeter aortic valve gradient"
    
    # 测试OpenAI
    print(f"\n📞 测试OpenAI (带系统提示词): {test_symptom}")
    try:
        from api_clients.openai_client import OpenAIClient
        
        api_key = os.getenv('OPENAI_API_KEY')
        client = OpenAIClient(api_key=api_key, model="gpt-4")
        
        response = client.generate_response(
            system_prompt=system_prompt,
            user_prompt=test_symptom,
            max_tokens=500
        )
        
        print(f"✅ 调用成功: {response['success']}")
        if response.get('success'):
            print(f"📝 原始响应: {response['response']}")
            
            # 尝试解析JSON
            try:
                import json
                parsed = json.loads(response['response'])
                print(f"✅ JSON解析成功: {json.dumps(parsed, indent=2, ensure_ascii=False)}")
            except json.JSONDecodeError as e:
                print(f"❌ JSON解析失败: {e}")
                print(f"📝 响应内容: {response['response']}")
        else:
            print(f"❌ 错误: {response.get('error')}")
            
    except Exception as e:
        print(f"❌ 异常: {e}")

def main():
    """主函数"""
    print("🔍 调试API响应内容")
    print("=" * 60)
    
    # 测试简单响应
    test_api_raw_response()
    
    # 测试带系统提示词的响应
    test_with_system_prompt()

if __name__ == "__main__":
    main()
