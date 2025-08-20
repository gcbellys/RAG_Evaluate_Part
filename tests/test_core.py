#!/usr/bin/env python3
"""
核心功能测试
测试数据加载、评估和API管理功能
"""

import sys
import json
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from src.data_loader import DataLoader
from src.evaluator import Evaluator
from src.api_manager import APIManager

def test_data_loading():
    """测试数据加载功能"""
    print("🧪 测试数据加载功能...")
    
    data_loader = DataLoader()
    test_data_path = Path("test_set")
    
    if not test_data_path.exists():
        print("❌ test_set 目录不存在，跳过数据加载测试")
        return False
    
    try:
        # 测试获取文件列表
        files = data_loader.get_diagnostic_files(test_data_path, max_files=3)
        print(f"✅ 获取到 {len(files)} 个测试文件")
        
        # 测试ID范围过滤
        range_files = data_loader.get_reports_by_id_range(test_data_path, start_id=4000, end_id=4002)
        print(f"✅ ID范围过滤: 找到 {len(range_files)} 个文件")
        
        # 测试加载单个Report
        if files:
            report_data = data_loader.load_report_data(files[0])
            print(f"✅ 成功加载Report: {report_data['report_id']}")
            print(f"   症状数量: {report_data['total_symptoms']}")
            print(f"   有效症状: {report_data['valid_symptoms']}")
        
        return True
        
    except Exception as e:
        print(f"❌ 数据加载测试失败: {e}")
        return False

def test_evaluation():
    """测试评估功能"""
    print("\n🧪 测试评估功能...")
    
    evaluator = Evaluator()
    
    # 模拟测试数据
    mock_api_response = {
        'success': True,
        'parsed_response': {
            'anatomicalLocations': ['Heart', 'Lung']
        }
    }
    
    mock_expected_results = [
        {'anatomicalLocations': ['Heart']},
        {'anatomicalLocations': ['Lung']}
    ]
    
    try:
        # 测试单个响应评估
        evaluation = evaluator.evaluate_single_response(mock_api_response, mock_expected_results)
        print(f"✅ 评估完成:")
        print(f"   综合得分: {evaluation['overall_score']}")
        print(f"   精确率: {evaluation['precision']}%")
        print(f"   召回率: {evaluation['recall']}%")
        print(f"   过度生成惩罚: {evaluation['overgeneration_penalty']}%")
        
        return True
        
    except Exception as e:
        print(f"❌ 评估测试失败: {e}")
        return False

def test_api_management():
    """测试API管理功能"""
    print("\n🧪 测试API管理功能...")
    
    api_manager = APIManager()
    
    try:
        # 测试客户端数量
        client_count = api_manager.get_client_count()
        print(f"✅ 初始客户端数量: {client_count}")
        
        # 测试客户端名称列表
        client_names = api_manager.get_client_names()
        print(f"✅ 支持的客户端: {', '.join(client_names)}")
        
        return True
        
    except Exception as e:
        print(f"❌ API管理测试失败: {e}")
        return False

def main():
    """主测试函数"""
    print("🚀 开始核心功能测试")
    print("=" * 50)
    
    tests = [
        ("数据加载", test_data_loading),
        ("评估功能", test_evaluation),
        ("API管理", test_api_management)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
                print(f"✅ {test_name} 测试通过")
            else:
                print(f"❌ {test_name} 测试失败")
        except Exception as e:
            print(f"❌ {test_name} 测试异常: {e}")
    
    print("\n" + "=" * 50)
    print(f"📊 测试结果: {passed}/{total} 通过")
    
    if passed == total:
        print("🎉 所有核心功能测试通过！")
        return True
    else:
        print("⚠️  部分测试失败，请检查相关功能")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
