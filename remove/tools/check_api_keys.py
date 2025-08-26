#!/usr/bin/env python3
"""
API密钥检查工具
检查所有API密钥的配置状态
"""

import os
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from src.api_manager import APIManager
from src.config_loader import ConfigLoader

def check_api_keys():
    """检查所有API密钥配置"""
    print("🔍 检查API密钥配置")
    print("=" * 50)
    
    # 加载配置
    config_loader = ConfigLoader()
    config = config_loader.config
    
    # 创建API管理器
    api_manager = APIManager()
    
    # 检查环境变量
    print("📋 环境变量检查:")
    for provider, provider_config in config.get('api_config', {}).items():
        api_key_env = provider_config.get('api_key_env')
        if api_key_env:
            api_key = os.getenv(api_key_env)
            if api_key:
                # 隐藏大部分密钥，只显示前4位和后4位
                masked_key = api_key[:4] + "*" * (len(api_key) - 8) + api_key[-4:] if len(api_key) > 8 else "***"
                print(f"  ✅ {provider.capitalize()}: {masked_key}")
                
                # 验证密钥格式
                if api_manager._validate_api_key(provider, api_key):
                    print(f"     格式: ✅ 正确")
                else:
                    print(f"     格式: ❌ 可能不正确")
            else:
                print(f"  ❌ {provider.capitalize()}: 环境变量 {api_key_env} 未设置")
        else:
            print(f"  ⚠️  {provider.capitalize()}: 缺少 api_key_env 配置")
    
    print("\n🔧 尝试初始化API客户端...")
    
    # 尝试初始化客户端
    if api_manager.initialize_clients(config):
        print("✅ API客户端初始化成功")
        
        # 测试连通性（使用简单的测试）
        print("\n🧪 测试API连通性...")
        test_system_prompt = "You are a helpful assistant."
        
        if api_manager.test_connectivity(test_system_prompt):
            print("✅ API连通性测试通过")
        else:
            print("❌ API连通性测试失败")
    else:
        print("❌ API客户端初始化失败")

def main():
    """主函数"""
    try:
        check_api_keys()
    except Exception as e:
        print(f"❌ 检查过程中出现错误: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
