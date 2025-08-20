#!/usr/bin/env python3
"""
调试完整工作流流程
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

def debug_full_workflow():
    """调试完整工作流流程"""
    print("🧪 调试完整工作流流程")
    print("=" * 50)
    
    try:
        from src.api_manager import APIManager
        from src.config_loader import ConfigLoader
        
        # 加载配置
        config_loader = ConfigLoader()
        config = config_loader.config
        
        print("📋 配置信息:")
        print(f"  API配置: {list(config.get('api_config', {}).keys())}")
        
        # 创建API管理器
        api_manager = APIManager()
        
        # 初始化客户端
        if api_manager.initialize_clients(config):
            print("✅ API管理器初始化成功")
            print(f"📊 客户端数量: {api_manager.get_client_count()}")
            print(f"🔌 客户端名称: {api_manager.get_client_names()}")
            
            # 测试症状
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
                
                print(f"📄 系统提示词长度: {len(system_prompt)} 字符")
                
                # 处理症状
                print("\n🔄 处理症状...")
                api_responses = api_manager.process_symptom(test_symptom, system_prompt)
                
                print(f"📊 获得 {len(api_responses)} 个API响应")
                
                for api_name, response in api_responses.items():
                    print(f"\n🔍 {api_name} 响应详情:")
                    print(f"  成功: {response.get('success')}")
                    print(f"  所有字段: {list(response.keys())}")
                    
                    if response.get('success'):
                        print(f"  器官名称: '{response.get('organ_name', '')}'")
                        print(f"  解剖位置: {response.get('anatomical_locations', [])}")
                        print(f"  解析数据: {response.get('parsed_data', 'None')}")
                        
                        # 检查原始响应
                        if 'response' in response:
                            print(f"  原始响应前100字符: {response['response'][:100]}...")
                        
                        # 检查是否有其他相关字段
                        for key, value in response.items():
                            if 'organ' in key.lower() or 'anatomical' in key.lower() or 'location' in key.lower():
                                print(f"  相关字段 {key}: {value}")
                    else:
                        print(f"  错误: {response.get('error', '')}")
                
                # 测试process_report_symptoms
                print(f"\n🔄 测试process_report_symptoms...")
                report_data = {
                    'report_id': 'test_report',
                    'file_path': 'test_path',
                    'total_symptoms': 1,
                    'valid_symptoms': 1,
                    'symptoms': [test_symptom]
                }
                
                report_results = api_manager.process_report_symptoms(report_data, system_prompt)
                print(f"📊 Report结果: {report_results['report_id']}")
                print(f"📝 症状数量: {len(report_results['symptoms'])}")
                
                if report_results['symptoms']:
                    symptom_result = report_results['symptoms'][0]
                    print(f"🔍 第一个症状结果:")
                    print(f"  症状ID: {symptom_result['symptom_id']}")
                    print(f"  API响应数量: {len(symptom_result['api_responses'])}")
                    
                    for api_name, api_response in symptom_result['api_responses'].items():
                        print(f"    {api_name}: organ_name='{api_response.get('organ_name', '')}', locations={api_response.get('anatomical_locations', [])}")
            else:
                print("❌ 系统提示词文件不存在")
        else:
            print("❌ API管理器初始化失败")
            
    except Exception as e:
        print(f"❌ 测试异常: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_full_workflow()
