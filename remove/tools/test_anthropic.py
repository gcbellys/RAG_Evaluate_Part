#!/usr/bin/env python3
"""
专门测试Anthropic API连接
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

def test_anthropic_connection():
    """测试Anthropic连接"""
    print("🧪 测试Anthropic API连接")
    print("=" * 50)
    
    # 获取API密钥
    api_key = os.getenv('ANTHROPIC_API_KEY')
    if not api_key:
        print("❌ ANTHROPIC_API_KEY 环境变量未设置")
        return False
    
    print(f"🔑 API密钥: {api_key[:20]}...{api_key[-20:]}")
    print(f"📏 密钥长度: {len(api_key)}")
    
    # 测试1: 直接使用anthropic包
    print("\n📞 测试1: 直接使用anthropic包")
    try:
        import anthropic
        
        client = anthropic.Anthropic(api_key=api_key)
        print("✅ Anthropic客户端创建成功")
        
        # 测试简单请求
        response = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=50,
            messages=[
                {
                    "role": "user",
                    "content": "Say hello"
                }
            ]
        )
        
        print(f"✅ API调用成功: {response.content[0].text}")
        return True
        
    except Exception as e:
        print(f"❌ 直接调用失败: {e}")
        return False

def test_anthropic_client():
    """测试Anthropic客户端类"""
    print("\n📞 测试2: 使用AnthropicClient类")
    try:
        from api_clients.anthropic_client import AnthropicClient
        
        api_key = os.getenv('ANTHROPIC_API_KEY')
        client = AnthropicClient(
            api_key=api_key,
            model="claude-3-5-sonnet-20241022"
        )
        
        print("✅ AnthropicClient创建成功")
        
        # 测试generate_response方法
        response = client.generate_response(
            system_prompt="You are a helpful assistant.",
            user_prompt="Say hello",
            max_tokens=50
        )
        
        if response.get('success'):
            print(f"✅ generate_response成功: {response['response']}")
            return True
        else:
            print(f"❌ generate_response失败: {response.get('error')}")
            return False
            
    except Exception as e:
        print(f"❌ AnthropicClient测试异常: {e}")
        return False

def test_network_connectivity():
    """测试网络连接"""
    print("\n🌐 测试网络连接")
    try:
        import requests
        
        # 测试Anthropic API端点
        url = "https://api.anthropic.com/v1"
        response = requests.get(url, timeout=10)
        print(f"✅ 网络连接测试: {response.status_code}")
        
        # 测试DNS解析
        import socket
        host = "api.anthropic.com"
        ip = socket.gethostbyname(host)
        print(f"✅ DNS解析: {host} -> {ip}")
        
        return True
        
    except Exception as e:
        print(f"❌ 网络连接测试失败: {e}")
        return False

def main():
    """主函数"""
    print("🔍 Anthropic连接问题诊断")
    print("=" * 60)
    
    # 测试网络连接
    network_ok = test_network_connectivity()
    
    # 测试API连接
    api_ok = test_anthropic_connection()
    
    # 测试客户端类
    client_ok = test_anthropic_client()
    
    # 总结
    print("\n📊 测试结果总结")
    print("=" * 30)
    print(f"🌐 网络连接: {'✅' if network_ok else '❌'}")
    print(f"🔌 API连接: {'✅' if api_ok else '❌'}")
    print(f"📱 客户端类: {'✅' if client_ok else '❌'}")
    
    if not network_ok:
        print("\n💡 建议: 检查网络连接和防火墙设置")
    elif not api_ok:
        print("\n💡 建议: 检查API密钥和账户状态")
    elif not client_ok:
        print("\n💡 建议: 检查客户端代码实现")
    else:
        print("\n🎉 所有测试通过！")

if __name__ == "__main__":
    main()
