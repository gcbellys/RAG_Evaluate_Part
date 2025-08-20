#!/usr/bin/env python3
"""
强制测试修复后的API客户端
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

def force_test_openai():
    """强制测试OpenAI客户端"""
    print("🧪 强制测试修复后的OpenAI客户端")
    print("=" * 60)
    
    try:
        # 强制重新导入
        if 'api_clients.openai_client' in sys.modules:
            del sys.modules['api_clients.openai_client']
        
        from api_clients.openai_client import OpenAIClient
        
        api_key = os.getenv('OPENAI_API_KEY')
        client = OpenAIClient(api_key=api_key, model="gpt-4")
        
        print("✅ OpenAIClient创建成功")
        
        # 测试简单响应
        print("\n📞 测试简单响应...")
        response = client.generate_response(
            system_prompt="You are a helpful assistant.",
            user_prompt="Say hello",
            max_tokens=50
        )
        
        print(f"✅ 调用成功: {response['success']}")
        if response.get('success'):
            print(f"📝 响应: {response['response']}")
            print(f"🔍 解析数据: {response.get('parsed_data', 'None')}")
            print(f"💓 器官名称: {response.get('organ_name', 'None')}")
            print(f"📍 解剖位置: {response.get('anatomical_locations', 'None')}")
        
        # 测试带系统提示词的响应
        print("\n📞 测试带系统提示词的响应...")
        prompt_path = Path(__file__).parent.parent / "prompt" / "system_prompt.txt"
        if prompt_path.exists():
            with open(prompt_path, 'r', encoding='utf-8') as f:
                system_prompt = f.read()
            
            response2 = client.generate_response(
                system_prompt=system_prompt,
                user_prompt="80 millimeter aortic valve gradient",
                max_tokens=500
            )
            
            print(f"✅ 调用成功: {response2['success']}")
            if response2.get('success'):
                print(f"📝 响应: {response2['response'][:200]}...")
                print(f"🔍 解析数据: {response2.get('parsed_data', 'None')}")
                print(f"💓 器官名称: {response2.get('organ_name', 'None')}")
                print(f"📍 解剖位置: {response2.get('anatomical_locations', 'None')}")
        else:
            print("❌ 系统提示词文件不存在")
            
    except Exception as e:
        print(f"❌ 测试异常: {e}")
        import traceback
        traceback.print_exc()

def main():
    """主函数"""
    print("🔍 强制测试修复后的API客户端")
    print("=" * 70)
    
    force_test_openai()

if __name__ == "__main__":
    main()
