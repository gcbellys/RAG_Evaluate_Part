#!/usr/bin/env python3
"""
调试客户端创建过程
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

def debug_client_creation():
    """调试客户端创建过程"""
    print("🧪 调试客户端创建过程")
    print("=" * 60)
    
    try:
        from src.api_manager import APIManager
        from src.config_loader import ConfigLoader
        
        # 加载配置
        config_loader = ConfigLoader()
        config = config_loader.config
        
        print("📋 配置信息:")
        openai_config = config['api_config']['openai']
        print(f"  base_url: {openai_config['base_url']}")
        print(f"  model: {openai_config['model']}")
        print(f"  api_key_env: {openai_config['api_key_env']}")
        
        # 获取API密钥
        api_key = os.getenv(openai_config['api_key_env'])
        print(f"  API密钥: {api_key[:20]}...{api_key[-20:]}")
        print(f"  密钥长度: {len(api_key)}")
        
        # 创建API管理器
        api_manager = APIManager()
        
        # 手动创建OpenAI客户端（模拟API管理器的过程）
        print("\n🔧 手动创建OpenAI客户端...")
        from api_clients.openai_client import OpenAIClient
        
        # 方式1：使用完全相同的参数
        print("📞 方式1: 完全相同的参数")
        client1 = OpenAIClient(
            api_key=api_key,
            base_url=openai_config['base_url'],
            model=openai_config['model']
        )
        
        response1 = client1.generate_response(
            system_prompt="You are a helpful assistant.",
            user_prompt="Say hello",
            max_tokens=50
        )
        
        if response1.get('success'):
            print(f"✅ 方式1成功: {response1['response'][:30]}...")
        else:
            print(f"❌ 方式1失败: {response1.get('error')}")
        
        # 方式2：使用默认参数（成功的测试脚本方式）
        print("\n📞 方式2: 默认参数（测试脚本方式）")
        client2 = OpenAIClient(
            api_key=api_key,
            model="gpt-4"
        )
        
        response2 = client2.generate_response(
            system_prompt="You are a helpful assistant.",
            user_prompt="Say hello",
            max_tokens=50
        )
        
        if response2.get('success'):
            print(f"✅ 方式2成功: {response2['response'][:30]}...")
        else:
            print(f"❌ 方式2失败: {response2.get('error')}")
        
        # 方式3：通过API管理器
        print("\n📞 方式3: 通过API管理器")
        if api_manager.initialize_clients(config):
            openai_client = api_manager.clients.get('openai')
            if openai_client:
                response3 = openai_client.generate_response(
                    system_prompt="You are a helpful assistant.",
                    user_prompt="Say hello",
                    max_tokens=50
                )
                
                if response3.get('success'):
                    print(f"✅ 方式3成功: {response3['response'][:30]}...")
                else:
                    print(f"❌ 方式3失败: {response3.get('error')}")
            else:
                print("❌ 无法从API管理器获取OpenAI客户端")
        else:
            print("❌ API管理器初始化失败")
            
    except Exception as e:
        print(f"❌ 调试过程异常: {e}")

def main():
    """主函数"""
    debug_client_creation()

if __name__ == "__main__":
    main()
