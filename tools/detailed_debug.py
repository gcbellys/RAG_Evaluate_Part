#!/usr/bin/env python3
"""
详细调试API调用差异
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

def compare_openai_calls():
    """对比OpenAI的不同调用方式"""
    print("🧪 对比OpenAI调用方式")
    print("=" * 60)
    
    api_key = os.getenv('OPENAI_API_KEY')
    print(f"使用的API密钥: {api_key[:15]}...{api_key[-15:]}")
    
    # 方式1：直接调用（成功的方式）
    print("\n📞 方式1: 直接调用")
    try:
        from api_clients.openai_client import OpenAIClient
        
        client1 = OpenAIClient(api_key=api_key, model="gpt-4")
        print(f"客户端1 - 模型: gpt-4, base_url: 默认")
        
        response1 = client1.generate_response(
            system_prompt="You are a helpful assistant.",
            user_prompt="Say hello",
            max_tokens=50
        )
        
        if response1.get('success'):
            print(f"✅ 直接调用成功: {response1['response'][:30]}...")
        else:
            print(f"❌ 直接调用失败: {response1.get('error')}")
            
    except Exception as e:
        print(f"❌ 直接调用异常: {e}")
    
    # 方式2：使用配置文件中的参数
    print("\n📞 方式2: 使用配置参数")
    try:
        from api_clients.openai_client import OpenAIClient
        
        # 模拟API管理器的调用方式
        client2 = OpenAIClient(
            api_key=api_key, 
            base_url="https://api.openai.com/v1",  # 来自配置文件
            model="gpt-4"  # 来自配置文件
        )
        print(f"客户端2 - 模型: gpt-4, base_url: https://api.openai.com/v1")
        
        response2 = client2.generate_response(
            system_prompt="You are a helpful assistant.",
            user_prompt="Say hello",
            max_tokens=50
        )
        
        if response2.get('success'):
            print(f"✅ 配置参数调用成功: {response2['response'][:30]}...")
        else:
            print(f"❌ 配置参数调用失败: {response2.get('error')}")
            
    except Exception as e:
        print(f"❌ 配置参数调用异常: {e}")
    
    # 方式3：通过API管理器
    print("\n📞 方式3: 通过API管理器")
    try:
        from src.api_manager import APIManager
        from src.config_loader import ConfigLoader
        
        config_loader = ConfigLoader()
        config = config_loader.config
        api_manager = APIManager()
        
        # 手动创建OpenAI客户端（模拟API管理器的方式）
        if api_manager.initialize_clients(config):
            openai_client = api_manager.clients.get('openai')
            if openai_client:
                print(f"客户端3 - 通过API管理器创建")
                
                response3 = openai_client.generate_response(
                    system_prompt="You are a helpful assistant.",
                    user_prompt="Say hello",
                    max_tokens=50
                )
                
                if response3.get('success'):
                    print(f"✅ API管理器调用成功: {response3['response'][:30]}...")
                else:
                    print(f"❌ API管理器调用失败: {response3.get('error')}")
            else:
                print("❌ 无法从API管理器获取OpenAI客户端")
        else:
            print("❌ API管理器初始化失败")
            
    except Exception as e:
        print(f"❌ API管理器调用异常: {e}")

def main():
    """主函数"""
    print("🔍 详细调试API调用差异")
    print("=" * 70)
    
    compare_openai_calls()

if __name__ == "__main__":
    main()
