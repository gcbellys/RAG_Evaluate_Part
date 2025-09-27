#!/usr/bin/env python3
"""
测试修复后的系统
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

def test_fixed_system():
    """测试修复后的系统"""
    print("🧪 测试修复后的系统")
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
            
            # 测试症状处理
            test_symptom = {
                'symptom_text': '80 millimeter aortic valve gradient',
                'expected_results': [
                    {
                        'organName': 'Heart (Cor)',
                        'anatomicalLocations': ['Aortic Valve', 'Left Ventricle (LV)']
                    }
                ]
            }
            
            print(f"\n📝 测试症状: {test_symptom['symptom_text']}")
            
            # 读取系统提示词
            prompt_path = Path(__file__).parent.parent / "prompt" / "system_prompt.txt"
            if prompt_path.exists():
                with open(prompt_path, 'r', encoding='utf-8') as f:
                    system_prompt = f.read()
                
                # 处理症状
                api_responses = api_manager.process_symptom(test_symptom, system_prompt)
                
                print(f"📊 获得 {len(api_responses)} 个API响应")
                
                for api_name, response in api_responses.items():
                    print(f"\n🔍 {api_name}:")
                    print(f"  成功: {response.get('success')}")
                    if response.get('success'):
                        print(f"  器官名称: '{response.get('organ_name', '')}'")
                        print(f"  解剖位置: {response.get('anatomical_locations', [])}")
                        print(f"  解析数据: {response.get('parsed_data', 'None')}")
                    else:
                        print(f"  错误: {response.get('error', '')}")
            else:
                print("❌ 系统提示词文件不存在")
        else:
            print("❌ API管理器初始化失败")
            
    except Exception as e:
        print(f"❌ 测试异常: {e}")
        import traceback
        traceback.print_exc()

def main():
    """主函数"""
    test_fixed_system()

if __name__ == "__main__":
    main()
