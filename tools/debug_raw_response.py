#!/usr/bin/env python3
"""
调试API客户端的原始响应格式
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

def debug_raw_response():
    """调试原始响应格式"""
    print("🧪 调试便宜的API客户端原始响应格式")
    print("=" * 50)
    
    try:
        # 测试Moonshot
        print("\n📞 测试Moonshot...")
        from api_clients.moonshot_client import MoonshotClient
        
        api_key = os.getenv('MOONSHOT_API_KEY')
        client = MoonshotClient(api_key=api_key, model="moonshot-v1-8k")
        
        print("✅ MoonshotClient创建成功")
        
        # 测试简单响应
        print("\n📞 测试简单响应...")
        response1 = client.generate_response(
            system_prompt="You are a helpful assistant.",
            user_prompt="Say hello",
            max_tokens=50
        )
        
        print(f"✅ 调用成功: {response1['success']}")
        print(f"📝 响应字段: {list(response1.keys())}")
        print(f"🔍 organ_name: '{response1.get('organ_name', '')}'")
        print(f"📍 anatomical_locations: {response1.get('anatomical_locations', [])}")
        print(f"📊 parsed_data: {response1.get('parsed_data', 'None')}")
        
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
            print(f"📝 响应字段: {list(response2.keys())}")
            print(f"🔍 organ_name: '{response2.get('organ_name', '')}'")
            print(f"📍 anatomical_locations: {response2.get('anatomical_locations', [])}")
            print(f"📊 parsed_data: {response2.get('parsed_data', 'None')}")
            
            # 检查原始响应
            if 'response' in response2:
                print(f"📄 原始响应前200字符: {response2['response'][:200]}...")
        else:
            print("❌ 系统提示词文件不存在")
            
    except Exception as e:
        print(f"❌ 测试异常: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_raw_response()
