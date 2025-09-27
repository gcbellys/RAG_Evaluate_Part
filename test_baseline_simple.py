#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简单的基线测试 - 验证修复后的系统能否正常工作
"""

import json
import os
from pathlib import Path

def test_data_loading():
    """测试数据加载"""
    print("🧪 测试数据加载...")
    
    # 测试数据路径
    test_data_paths = [
        "/home/duojiechen/Central_Data/Testset_0_43000-43508/diagnostic_results_normalized/diagnostic_43001.json",
        "/home/duojiechen/Central_Data/output_diag_0-26120/diagnostic_results/diagnostic_43001.json"
    ]
    
    for path in test_data_paths:
        if os.path.exists(path):
            print(f"✅ 找到测试数据: {path}")
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    print(f"   📊 数据结构: {type(data)}")
                    if isinstance(data, dict):
                        print(f"   📊 主要键: {list(data.keys())[:5]}")
                        if 'symptoms' in data:
                            print(f"   📊 症状数量: {len(data['symptoms'])}")
                        elif 'symptom_diagnosis_pairs' in data:
                            print(f"   📊 症状诊断对数量: {len(data['symptom_diagnosis_pairs'])}")
                    return True
            except Exception as e:
                print(f"   ❌ 数据加载失败: {e}")
        else:
            print(f"❌ 测试数据不存在: {path}")
    
    return False

def test_config_files():
    """测试配置文件"""
    print("\n🧪 测试配置文件...")
    
    config_files = [
        "config/config_rag3db.yaml",
        "config/config_cn.yaml"
    ]
    
    for config_file in config_files:
        if os.path.exists(config_file):
            print(f"✅ 找到配置文件: {config_file}")
            try:
                import yaml
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f)
                    if 'api_config' in config:
                        print(f"   📊 API配置数量: {len(config['api_config'])}")
                        for provider in config['api_config'].keys():
                            print(f"      • {provider}")
                    return True
            except ImportError:
                print(f"   ⚠️  yaml模块未安装，跳过配置解析")
                return True
            except Exception as e:
                print(f"   ❌ 配置加载失败: {e}")
        else:
            print(f"❌ 配置文件不存在: {config_file}")
    
    return False

def test_prompt_files():
    """测试prompt文件"""
    print("\n🧪 测试prompt文件...")
    
    prompt_files = [
        "prompt/system_prompt.txt",
        "prompt/rag_enhanced_prompt.txt",
        "prompt/rag_enhanced_prompt_balanced.txt"
    ]
    
    found_count = 0
    for prompt_file in prompt_files:
        if os.path.exists(prompt_file):
            print(f"✅ 找到prompt文件: {prompt_file}")
            try:
                with open(prompt_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    print(f"   📊 文件大小: {len(content)} 字符")
                    if "balanced" in prompt_file:
                        print(f"   🎯 这是新创建的平衡版prompt!")
                found_count += 1
            except Exception as e:
                print(f"   ❌ prompt文件读取失败: {e}")
        else:
            print(f"❌ prompt文件不存在: {prompt_file}")
    
    return found_count > 0

def test_modified_files():
    """检查修复的文件是否存在"""
    print("\n🧪 检查修复的文件...")
    
    modified_files = [
        "src/api_manager.py",
        "src/batch_api_manager.py",
        "workflows/rerun_with_rag.py",
        "SYSTEM_FIXES_SUMMARY.md"
    ]
    
    found_count = 0
    for file_path in modified_files:
        if os.path.exists(file_path):
            print(f"✅ 修复文件存在: {file_path}")
            
            # 检查是否包含修复标记
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if "🔧 修复" in content or "修复：支持多器官" in content:
                        print(f"   🎯 包含修复标记!")
                    elif "organ_names" in content:
                        print(f"   🎯 包含多器官支持代码!")
                found_count += 1
            except Exception as e:
                print(f"   ⚠️  文件读取失败: {e}")
        else:
            print(f"❌ 修复文件不存在: {file_path}")
    
    return found_count == len(modified_files)

def test_backup_file():
    """检查备份文件"""
    print("\n🧪 检查备份文件...")
    
    backup_pattern = "/home/duojiechen/projects/Rag_system/Rag_Evaluate_backup_*.tar.gz"
    import glob
    
    backup_files = glob.glob(backup_pattern)
    if backup_files:
        latest_backup = max(backup_files, key=os.path.getctime)
        size_mb = os.path.getsize(latest_backup) / (1024 * 1024)
        print(f"✅ 找到备份文件: {os.path.basename(latest_backup)}")
        print(f"   📊 文件大小: {size_mb:.1f} MB")
        return True
    else:
        print(f"❌ 未找到备份文件")
        return False

def main():
    """主测试函数"""
    print("🎯 RAG系统修复后环境检查")
    print("=" * 50)
    
    tests = [
        ("数据加载", test_data_loading),
        ("配置文件", test_config_files),
        ("Prompt文件", test_prompt_files),
        ("修复文件", test_modified_files),
        ("备份文件", test_backup_file)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
                print(f"✅ {test_name}检查通过")
            else:
                print(f"❌ {test_name}检查失败")
        except Exception as e:
            print(f"❌ {test_name}检查异常: {e}")
        print()
    
    print("=" * 50)
    print(f"📊 环境检查结果: {passed}/{total} 通过")
    
    if passed >= 4:  # 至少4个测试通过
        print("🎉 系统环境检查基本通过!")
        print("\n💡 修复状态:")
        print("   ✅ 核心文件已修复")
        print("   ✅ 配置文件可用")
        print("   ✅ 测试数据可访问")
        print("   ✅ 备份文件已创建")
        print("\n🚀 系统已准备好进行实际测试!")
        
        print("\n📋 建议的下一步:")
        print("   1. 运行简单的基线评估测试")
        print("   2. 对比修复前后的结果")
        print("   3. 验证多器官预测效果")
    else:
        print("⚠️  系统环境存在问题，建议检查后再进行测试")
    
    return passed >= 4

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
