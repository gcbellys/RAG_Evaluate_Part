#!/usr/bin/env python3
"""
调试API管理器问题
对比测试脚本和API管理器的行为差异
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

def test_direct_api_call():
    """直接测试API调用（类似测试脚本）"""
    print("🧪 直接API调用测试")
    print("=" * 50)
    
    # 测试OpenAI
    try:
        from api_clients.openai_client import OpenAIClient
        api_key = os.getenv('OPENAI_API_KEY')
        print(f"OpenAI密钥: {api_key[:10]}...{api_key[-10:] if api_key else 'None'}")
        
        client = OpenAIClient(api_key=api_key, model="gpt-4")
        response = client.generate_response(
            system_prompt="You are a helpful assistant.",
            user_prompt="Say hello",
            max_tokens=50
        )
        
        if response.get('success'):
            print(f"✅ 直接调用OpenAI成功: {response['response'][:50]}...")
        else:
            print(f"❌ 直接调用OpenAI失败: {response.get('error')}")
            
    except Exception as e:
        print(f"❌ 直接调用OpenAI异常: {e}")

def test_api_manager():
    """通过API管理器测试"""
    print("\n🧪 API管理器测试")
    print("=" * 50)
    
    try:
        from src.api_manager import APIManager
        from src.config_loader import ConfigLoader
        
        # 加载配置
        config_loader = ConfigLoader()
        config = config_loader.config
        
        # 创建API管理器
        api_manager = APIManager()
        
        # 初始化客户端
        if api_manager.initialize_clients(config):
            print("✅ API管理器初始化成功")
            
            # 测试连通性
            if api_manager.test_connectivity():
                print("✅ API管理器连通性测试成功")
            else:
                print("❌ API管理器连通性测试失败")
        else:
            print("❌ API管理器初始化失败")
            
    except Exception as e:
        print(f"❌ API管理器测试异常: {e}")

def test_environment_variables():
    """测试环境变量"""
    print("\n🧪 环境变量测试")
    print("=" * 50)
    
    api_keys = {
        'OPENAI_API_KEY': os.getenv('OPENAI_API_KEY'),
        'ANTHROPIC_API_KEY': os.getenv('ANTHROPIC_API_KEY'),
        'GEMINI_API_KEY': os.getenv('GEMINI_API_KEY'),
        'MOONSHOT_API_KEY': os.getenv('MOONSHOT_API_KEY'),
        'DEEPSEEK_API_KEY': os.getenv('DEEPSEEK_API_KEY')
    }
    
    for key, value in api_keys.items():
        if value:
            masked = value[:10] + "..." + value[-10:] if len(value) > 20 else "***"
            print(f"✅ {key}: {masked}")
        else:
            print(f"❌ {key}: 未设置")

def main():
    """主函数"""
    print("🔍 调试API管理器问题")
    print("=" * 60)
    
    # 测试环境变量
    test_environment_variables()
    
    # 直接API调用测试
    test_direct_api_call()
    
    # API管理器测试
    test_api_manager()

if __name__ == "__main__":
    main()
