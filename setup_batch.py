#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批处理模式安装和设置脚本
确保OpenAI Batch API所需的依赖项正确安装
"""

import subprocess
import sys
import os
from pathlib import Path


def run_command(command: str, description: str) -> bool:
    """运行命令并显示结果"""
    print(f"🔧 {description}...")
    print(f"   执行: {command}")
    
    try:
        result = subprocess.run(command, shell=True, check=True, 
                              capture_output=True, text=True)
        print(f"✅ {description} - 成功")
        if result.stdout:
            print(f"   输出: {result.stdout.strip()}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} - 失败")
        print(f"   错误: {e.stderr.strip() if e.stderr else str(e)}")
        return False


def check_python_version():
    """检查Python版本"""
    print("🐍 检查Python版本...")
    version = sys.version_info
    print(f"   当前版本: Python {version.major}.{version.minor}.{version.micro}")
    
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print("❌ Python版本过低，需要Python 3.8+")
        return False
    
    print("✅ Python版本符合要求")
    return True


def install_dependencies():
    """安装必要的依赖项"""
    print("\n📦 安装依赖项...")
    
    dependencies = [
        ("openai", "升级OpenAI库到最新版本"),
        ("python-dotenv", "环境变量管理"),
        ("pyyaml", "YAML配置文件支持"),
        ("pathlib", "路径处理（通常已内置）")
    ]
    
    success_count = 0
    
    for package, description in dependencies:
        if package == "openai":
            # 特别处理OpenAI库，确保是最新版本
            cmd = f"{sys.executable} -m pip install -U openai"
        else:
            cmd = f"{sys.executable} -m pip install {package}"
        
        if run_command(cmd, f"安装 {package} - {description}"):
            success_count += 1
        else:
            print(f"⚠️  {package} 安装失败，可能需要手动安装")
    
    print(f"\n📊 依赖项安装结果: {success_count}/{len(dependencies)} 成功")
    return success_count == len(dependencies)


def check_openai_version():
    """检查OpenAI库版本"""
    print("\n🔍 检查OpenAI库版本...")
    
    try:
        import openai
        version = openai.__version__
        print(f"   当前版本: {version}")
        
        # 检查是否支持Batch API（需要1.3.0+）
        from packaging import version as pkg_version
        if pkg_version.parse(version) >= pkg_version.parse("1.3.0"):
            print("✅ OpenAI库版本支持Batch API")
            return True
        else:
            print("❌ OpenAI库版本过低，需要1.3.0+支持Batch API")
            return False
            
    except ImportError:
        print("❌ OpenAI库未安装")
        return False
    except ImportError as e:
        print(f"⚠️  无法检查版本: {e}")
        return True  # 假设版本正确


def test_openai_client():
    """测试OpenAI客户端基本功能"""
    print("\n🧪 测试OpenAI客户端...")
    
    try:
        import openai
        
        # 检查是否设置了API密钥
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            print("⚠️  OPENAI_API_KEY 环境变量未设置")
            print("   请设置环境变量或在.env文件中配置")
            return False
        
        # 创建客户端（不实际调用API）
        client = openai.OpenAI(api_key=api_key)
        print("✅ OpenAI客户端创建成功")
        
        # 检查Batch API相关方法是否存在
        if hasattr(client, 'batches') and hasattr(client, 'files'):
            print("✅ Batch API方法可用")
            return True
        else:
            print("❌ Batch API方法不可用，请升级OpenAI库")
            return False
            
    except Exception as e:
        print(f"❌ OpenAI客户端测试失败: {e}")
        return False


def create_batch_directory():
    """创建批处理工作目录"""
    print("\n📁 创建批处理工作目录...")
    
    batch_dir = Path("batch_processing")
    batch_dir.mkdir(exist_ok=True)
    
    results_dir = Path("results/batch_results")
    results_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"✅ 目录创建成功:")
    print(f"   批处理文件: {batch_dir}")
    print(f"   结果目录: {results_dir}")
    
    return True


def create_example_env():
    """创建示例环境变量文件"""
    print("\n📝 创建示例环境变量文件...")
    
    env_example_path = Path("config/.env.example")
    env_path = Path("config/.env")
    
    env_content = """# OpenAI API配置
OPENAI_API_KEY=sk-your-openai-api-key-here

# 其他API配置
ANTHROPIC_API_KEY=sk-ant-your-anthropic-key-here
GEMINI_API_KEY=your-gemini-api-key-here
MOONSHOT_API_KEY=sk-your-moonshot-key-here
DEEPSEEK_API_KEY=sk-your-deepseek-key-here

# 批处理配置
BATCH_POLL_INTERVAL=30
BATCH_TIMEOUT=86400
"""
    
    # 创建示例文件
    with open(env_example_path, 'w', encoding='utf-8') as f:
        f.write(env_content)
    
    print(f"✅ 示例环境变量文件已创建: {env_example_path}")
    
    # 如果.env文件不存在，复制示例文件
    if not env_path.exists():
        with open(env_path, 'w', encoding='utf-8') as f:
            f.write(env_content)
        print(f"✅ 环境变量文件已创建: {env_path}")
        print("⚠️  请编辑.env文件，填入正确的API密钥")
    else:
        print(f"ℹ️  环境变量文件已存在: {env_path}")
    
    return True


def main():
    """主函数"""
    print("=" * 70)
    print("🚀 OpenAI Batch API 批处理模式安装设置")
    print("=" * 70)
    
    success_steps = 0
    total_steps = 6
    
    # 1. 检查Python版本
    if check_python_version():
        success_steps += 1
    
    # 2. 安装依赖项
    if install_dependencies():
        success_steps += 1
    
    # 3. 检查OpenAI版本
    if check_openai_version():
        success_steps += 1
    
    # 4. 测试OpenAI客户端
    if test_openai_client():
        success_steps += 1
    
    # 5. 创建目录
    if create_batch_directory():
        success_steps += 1
    
    # 6. 创建环境变量文件
    if create_example_env():
        success_steps += 1
    
    # 显示结果
    print("\n" + "=" * 70)
    print(f"📊 安装设置完成: {success_steps}/{total_steps} 步骤成功")
    
    if success_steps == total_steps:
        print("🎉 批处理模式安装设置完成!")
        print("\n📋 下一步:")
        print("1. 编辑 config/.env 文件，填入正确的API密钥")
        print("2. 运行测试: python start_evaluation.py batch 4000 --force-batch")
        print("3. 查看结果: results/batch_results/")
    else:
        print("⚠️  部分步骤失败，请检查错误信息并手动修复")
        print("\n🔧 常见问题解决:")
        print("- 如果pip安装失败，尝试: pip install --user 或使用虚拟环境")
        print("- 如果OpenAI版本过低，运行: pip install -U openai")
        print("- 确保设置了OPENAI_API_KEY环境变量")
    
    print("=" * 70)


if __name__ == "__main__":
    main()
