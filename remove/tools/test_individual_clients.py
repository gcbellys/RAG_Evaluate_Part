#!/usr/bin/env python3
"""
测试单个API客户端
逐个测试每个客户端的连接和响应
"""

import os
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

def test_openai_client():
    """测试OpenAI客户端"""
    print("🔍 测试OpenAI客户端...")
    try:
        from api_clients.openai_client import OpenAIClient
        
        # 从环境变量获取API密钥
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            print("❌ OPENAI_API_KEY 环境变量未设置")
            return False
        
        client = OpenAIClient(api_key=api_key, model="gpt-4")
        
        # 简单测试
        response = client.generate_response(
            system_prompt="You are a helpful assistant.",
            user_prompt="Say hello",
            max_tokens=50
        )
        
        if response.get('success'):
            print("✅ OpenAI客户端测试成功")
            print(f"   响应: {response['response'][:100]}...")
            return True
        else:
            print(f"❌ OpenAI客户端测试失败: {response.get('error')}")
            return False
            
    except Exception as e:
        print(f"❌ OpenAI客户端测试异常: {e}")
        return False

def test_anthropic_client():
    """测试Anthropic客户端"""
    print("🔍 测试Anthropic客户端...")
    try:
        from api_clients.anthropic_client import AnthropicClient
        
        # 从环境变量获取API密钥
        api_key = os.getenv('ANTHROPIC_API_KEY')
        if not api_key:
            print("❌ ANTHROPIC_API_KEY 环境变量未设置")
            return False
        
        client = AnthropicClient(api_key=api_key)
        
        # 简单测试
        response = client.generate_response(
            system_prompt="You are a helpful assistant.",
            user_prompt="Say hello",
            max_tokens=50
        )
        
        if response.get('success'):
            print("✅ Anthropic客户端测试成功")
            print(f"   响应: {response['response'][:100]}...")
            return True
        else:
            print(f"❌ Anthropic客户端测试失败: {response.get('error')}")
            return False
            
    except Exception as e:
        print(f"❌ Anthropic客户端测试异常: {e}")
        return False

def test_gemini_client():
    """测试Gemini客户端"""
    print("🔍 测试Gemini客户端...")
    try:
        from api_clients.google_client import GeminiClient
        
        # 从环境变量获取API密钥
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            print("❌ GEMINI_API_KEY 环境变量未设置")
            return False
        
        client = GeminiClient(api_key=api_key)
        
        # 简单测试
        response = client.generate_response(
            system_prompt="You are a helpful assistant.",
            user_prompt="Say hello",
            max_tokens=50
        )
        
        if response.get('success'):
            print("✅ Gemini客户端测试成功")
            print(f"   响应: {response['response'][:100]}...")
            return True
        else:
            print(f"❌ Gemini客户端测试失败: {response.get('error')}")
            return False
            
    except Exception as e:
        print(f"❌ Gemini客户端测试异常: {e}")
        return False

def test_moonshot_client():
    """测试Moonshot客户端"""
    print("🔍 测试Moonshot客户端...")
    try:
        from api_clients.moonshot_client import MoonshotClient
        
        # 从环境变量获取API密钥
        api_key = os.getenv('MOONSHOT_API_KEY')
        if not api_key:
            print("❌ MOONSHOT_API_KEY 环境变量未设置")
            return False
        
        client = MoonshotClient(api_key=api_key)
        
        # 简单测试
        response = client.generate_response(
            system_prompt="You are a helpful assistant.",
            user_prompt="Say hello",
            max_tokens=50
        )
        
        if response.get('success'):
            print("✅ Moonshot客户端测试成功")
            print(f"   响应: {response['response'][:100]}...")
            return True
        else:
            print(f"❌ Moonshot客户端测试失败: {response.get('error')}")
            return False
            
    except Exception as e:
        print(f"❌ Moonshot客户端测试异常: {e}")
        return False

def test_deepseek_client():
    """测试Deepseek客户端"""
    print("🔍 测试Deepseek客户端...")
    try:
        from api_clients.deepseek_client import DeepseekClient
        
        # 从环境变量获取API密钥
        api_key = os.getenv('DEEPSEEK_API_KEY')
        if not api_key:
            print("❌ DEEPSEEK_API_KEY 环境变量未设置")
            return False
        
        client = DeepseekClient(api_key=api_key)
        
        # 简单测试
        response = client.generate_response(
            system_prompt="You are a helpful assistant.",
            user_prompt="Say hello",
            max_tokens=50
        )
        
        if response.get('success'):
            print("✅ Deepseek客户端测试成功")
            print(f"   响应: {response['response'][:100]}...")
            return True
        else:
            print(f"❌ Deepseek客户端测试失败: {response.get('error')}")
            return False
            
    except Exception as e:
        print(f"❌ Deepseek客户端测试异常: {e}")
        return False

def main():
    """主测试函数"""
    print("🚀 开始测试单个API客户端")
    print("=" * 60)
    
    # 加载环境变量
    from dotenv import load_dotenv
    # 指定.env文件的路径
    env_path = Path(__file__).parent.parent / "config" / ".env"
    load_dotenv(env_path)
    
    tests = [
        ("OpenAI", test_openai_client),
        ("Anthropic", test_anthropic_client),
        ("Gemini", test_gemini_client),
        ("Moonshot", test_moonshot_client),
        ("Deepseek", test_deepseek_client)
    ]
    
    results = {}
    
    for name, test_func in tests:
        print(f"\n{'='*20} {name} {'='*20}")
        try:
            success = test_func()
            results[name] = success
        except Exception as e:
            print(f"❌ {name} 测试出现异常: {e}")
            results[name] = False
    
    # 总结结果
    print("\n" + "=" * 60)
    print("📊 测试结果总结:")
    
    success_count = 0
    for name, success in results.items():
        status = "✅ 成功" if success else "❌ 失败"
        print(f"  {name}: {status}")
        if success:
            success_count += 1
    
    print(f"\n🎯 总体结果: {success_count}/{len(results)} 个客户端测试成功")
    
    if success_count == 0:
        print("❌ 所有客户端都测试失败，请检查API密钥和网络连接")
    elif success_count < len(results):
        print("⚠️  部分客户端测试失败，建议修复后再使用")
    else:
        print("🎉 所有客户端测试成功！")
    
    return success_count > 0

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
