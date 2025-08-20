#!/usr/bin/env python3
"""
调试环境变量加载问题
"""

import os
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

def check_env_before_api_manager():
    """检查导入API管理器之前的环境变量"""
    print("🧪 导入API管理器之前的环境变量")
    print("=" * 50)
    
    # 手动加载环境变量
    from dotenv import load_dotenv
    env_path = Path(__file__).parent.parent / "config" / ".env"
    load_dotenv(env_path)
    
    api_key = os.getenv('OPENAI_API_KEY')
    print(f"OpenAI密钥: {api_key[:20]}...{api_key[-20:] if api_key else 'None'}")
    print(f"密钥长度: {len(api_key) if api_key else 0}")
    
    return api_key

def check_env_after_api_manager():
    """检查导入API管理器之后的环境变量"""
    print("\n🧪 导入API管理器之后的环境变量")
    print("=" * 50)
    
    # 导入API管理器（这会触发模块级别的环境变量加载）
    from src.api_manager import APIManager
    
    api_key = os.getenv('OPENAI_API_KEY')
    print(f"OpenAI密钥: {api_key[:20]}...{api_key[-20:] if api_key else 'None'}")
    print(f"密钥长度: {len(api_key) if api_key else 0}")
    
    return api_key

def test_direct_with_both_keys():
    """使用两个密钥进行直接测试"""
    print("\n🧪 使用两个密钥进行直接测试")
    print("=" * 50)
    
    key1 = check_env_before_api_manager()
    key2 = check_env_after_api_manager()
    
    if key1 == key2:
        print("✅ 环境变量一致")
    else:
        print("❌ 环境变量不一致!")
        print(f"导入前: {key1[:30]}...{key1[-10:] if key1 else 'None'}")
        print(f"导入后: {key2[:30]}...{key2[-10:] if key2 else 'None'}")
    
    # 测试第二个密钥
    if key2:
        try:
            from api_clients.openai_client import OpenAIClient
            client = OpenAIClient(api_key=key2, model="gpt-4")
            response = client.generate_response(
                system_prompt="You are a helpful assistant.",
                user_prompt="Say hello",
                max_tokens=50
            )
            
            if response.get('success'):
                print(f"✅ 使用第二个密钥直接调用成功")
            else:
                print(f"❌ 使用第二个密钥直接调用失败: {response.get('error')}")
                
        except Exception as e:
            print(f"❌ 测试第二个密钥异常: {e}")

def main():
    """主函数"""
    print("🔍 调试环境变量加载问题")
    print("=" * 60)
    
    test_direct_with_both_keys()

if __name__ == "__main__":
    main()
