#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试修复后的系统 - 验证多器官支持
"""

import sys
import json
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.append(str(project_root))

from src.api_manager import APIManager
from src.config_loader import ConfigLoader

def test_api_manager_multi_organ_support():
    """测试API管理器的多器官支持"""
    print("🧪 测试API管理器多器官支持...")
    
    api_manager = APIManager()
    
    # 测试多器官JSON解析
    test_json_multi_organ = """
    {
        "organs": [
            {
                "organName": "Heart (Cor)",
                "anatomicalLocations": ["Left Ventricle", "Aortic Valve"],
                "relevance": "High"
            },
            {
                "organName": "Lung (Pulmo)",
                "anatomicalLocations": ["Left Lower Lobe", "Right Upper Lobe"],
                "relevance": "Medium"
            },
            {
                "organName": "Brain",
                "anatomicalLocations": ["Cerebral Cortex", "Brainstem"],
                "relevance": "High"
            }
        ]
    }
    """
    
    # 测试解析
    result = api_manager._extract_and_parse_json(test_json_multi_organ)
    
    print(f"📊 解析结果:")
    print(f"   器官数量: {result.get('total_organs', 0)}")
    print(f"   器官列表: {result.get('organ_names', [])}")
    print(f"   解剖位置数量: {len(result.get('anatomical_locations', []))}")
    print(f"   解剖位置: {result.get('anatomical_locations', [])}")
    print(f"   向后兼容字段: {result.get('organ_name', 'N/A')}")
    
    # 验证修复效果
    expected_organs = 3
    expected_locations = 6  # 2+2+2
    
    success = True
    if result.get('total_organs', 0) != expected_organs:
        print(f"❌ 器官数量错误: 期望{expected_organs}, 实际{result.get('total_organs', 0)}")
        success = False
    
    if len(result.get('anatomical_locations', [])) != expected_locations:
        print(f"❌ 解剖位置数量错误: 期望{expected_locations}, 实际{len(result.get('anatomical_locations', []))}")
        success = False
    
    if len(result.get('organ_names', [])) != expected_organs:
        print(f"❌ 器官名称列表错误: 期望{expected_organs}, 实际{len(result.get('organ_names', []))}")
        success = False
    
    if success:
        print("✅ API管理器多器官支持测试通过!")
        return True
    else:
        print("❌ API管理器多器官支持测试失败!")
        return False

def test_single_organ_backward_compatibility():
    """测试单器官的向后兼容性"""
    print("\n🧪 测试单器官向后兼容性...")
    
    api_manager = APIManager()
    
    # 测试单器官JSON
    test_json_single_organ = """
    {
        "organs": [
            {
                "organName": "Heart (Cor)",
                "anatomicalLocations": ["Left Ventricle", "Right Ventricle"],
                "relevance": "High"
            }
        ]
    }
    """
    
    result = api_manager._extract_and_parse_json(test_json_single_organ)
    
    print(f"📊 单器官解析结果:")
    print(f"   器官数量: {result.get('total_organs', 0)}")
    print(f"   主器官: {result.get('organ_name', 'N/A')}")
    print(f"   解剖位置: {result.get('anatomical_locations', [])}")
    
    # 验证向后兼容性
    success = True
    if result.get('total_organs', 0) != 1:
        print(f"❌ 单器官数量错误")
        success = False
    
    if result.get('organ_name', '') != "Heart (Cor)":
        print(f"❌ 向后兼容字段错误")
        success = False
    
    if success:
        print("✅ 单器官向后兼容性测试通过!")
        return True
    else:
        print("❌ 单器官向后兼容性测试失败!")
        return False

def test_config_loading():
    """测试配置加载"""
    print("\n🧪 测试配置加载...")
    
    try:
        config = ConfigLoader("config/config_rag3db.yaml")
        print("✅ 配置文件加载成功!")
        
        # 检查API配置
        api_config = config.config.get('api_config', {})
        print(f"📊 API配置数量: {len(api_config)}")
        
        for provider in api_config.keys():
            print(f"   • {provider}: {api_config[provider].get('model', 'N/A')}")
        
        return True
    except Exception as e:
        print(f"❌ 配置加载失败: {e}")
        return False

def main():
    """主测试函数"""
    print("🎯 RAG系统修复验证测试")
    print("=" * 60)
    
    tests = [
        test_api_manager_multi_organ_support,
        test_single_organ_backward_compatibility,
        test_config_loading
    ]
    
    passed = 0
    total = len(tests)
    
    for test_func in tests:
        try:
            if test_func():
                passed += 1
        except Exception as e:
            print(f"❌ 测试异常: {e}")
    
    print("\n" + "=" * 60)
    print(f"📊 测试结果: {passed}/{total} 通过")
    
    if passed == total:
        print("🎉 所有测试通过! 修复验证成功!")
        print("\n💡 关键改进:")
        print("   ✅ API管理器支持多器官输出")
        print("   ✅ 保持向后兼容性")
        print("   ✅ 配置系统正常工作")
        print("\n🚀 系统已准备好进行实际评估!")
    else:
        print("⚠️  部分测试失败，需要进一步检查")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
