#!/bin/bash
# -*- coding: utf-8 -*-
"""
RAG_env 环境依赖安装脚本
自动在 RAG_env 环境中安装所有必需的依赖项
"""

set -e  # 遇到错误立即退出

echo "=========================================="
echo "🚀 RAG_env 环境依赖安装脚本"
echo "=========================================="

# 检查是否在正确的目录
if [ ! -f "requirements.txt" ]; then
    echo "❌ 错误: 未找到 requirements.txt 文件"
    echo "请确保在 Rag_Evaluate 目录中运行此脚本"
    exit 1
fi

# 检查 conda 是否可用
if ! command -v conda &> /dev/null; then
    echo "❌ 错误: conda 未安装或不在 PATH 中"
    exit 1
fi

# 检查 RAG_env 环境是否存在
if ! conda env list | grep -q "RAG_env"; then
    echo "❌ 错误: RAG_env 环境不存在"
    echo "请先创建环境: conda create -n RAG_env python=3.9"
    exit 1
fi

echo "✅ 检查通过，开始安装..."

# 激活环境的函数
activate_env() {
    echo "🔄 激活 RAG_env 环境..."
    source $(conda info --base)/etc/profile.d/conda.sh
    conda activate RAG_env
    echo "✅ 环境已激活: $(which python)"
}

# 安装基础依赖
install_basic_deps() {
    echo ""
    echo "📦 安装基础依赖..."
    pip install -r requirements.txt
    echo "✅ 基础依赖安装完成"
}

# 检测 CUDA 版本
detect_cuda() {
    echo ""
    echo "🔍 检测 CUDA 版本..."
    
    if command -v nvidia-smi &> /dev/null; then
        CUDA_VERSION=$(nvidia-smi | grep "CUDA Version" | sed 's/.*CUDA Version: \([0-9]\+\.[0-9]\+\).*/\1/')
        echo "✅ 检测到 CUDA 版本: $CUDA_VERSION"
        
        # 根据 CUDA 版本选择 PyTorch 安装命令
        if [[ "$CUDA_VERSION" == "12."* ]]; then
            TORCH_INDEX="cu121"
        elif [[ "$CUDA_VERSION" == "11.8"* ]]; then
            TORCH_INDEX="cu118"
        elif [[ "$CUDA_VERSION" == "11."* ]]; then
            TORCH_INDEX="cu118"  # 默认使用 cu118
        else
            TORCH_INDEX="cpu"
            echo "⚠️  未识别的 CUDA 版本，将安装 CPU 版本"
        fi
    else
        echo "⚠️  未检测到 NVIDIA GPU，将安装 CPU 版本"
        TORCH_INDEX="cpu"
    fi
    
    echo "🎯 将使用 PyTorch 索引: $TORCH_INDEX"
}

# 安装 PyTorch
install_pytorch() {
    echo ""
    echo "🔥 安装 PyTorch..."
    
    if [ "$TORCH_INDEX" = "cpu" ]; then
        pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
    else
        pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/$TORCH_INDEX
    fi
    
    echo "✅ PyTorch 安装完成"
}

# 安装 Faiss
install_faiss() {
    echo ""
    echo "🔍 安装 Faiss..."
    
    if [ "$TORCH_INDEX" = "cpu" ]; then
        echo "📦 安装 Faiss CPU 版本..."
        pip install faiss-cpu
    else
        echo "🚀 安装 Faiss GPU 版本..."
        # 尝试使用 conda 安装 GPU 版本
        if conda install -y -c conda-forge faiss-gpu; then
            echo "✅ Faiss GPU 版本安装成功"
        else
            echo "⚠️  Faiss GPU 安装失败，回退到 CPU 版本"
            pip install faiss-cpu
        fi
    fi
    
    echo "✅ Faiss 安装完成"
}

# 验证安装
verify_installation() {
    echo ""
    echo "🧪 验证安装..."
    
    python -c "
import sys
print(f'Python 版本: {sys.version}')

try:
    import torch
    print(f'✅ PyTorch: {torch.__version__}')
    print(f'   CUDA 可用: {torch.cuda.is_available()}')
    if torch.cuda.is_available():
        print(f'   CUDA 设备数: {torch.cuda.device_count()}')
except ImportError as e:
    print(f'❌ PyTorch 导入失败: {e}')

try:
    import faiss
    print(f'✅ Faiss: {faiss.__version__ if hasattr(faiss, \"__version__\") else \"已安装\"}')
except ImportError as e:
    print(f'❌ Faiss 导入失败: {e}')

try:
    import openai
    print(f'✅ OpenAI: {openai.__version__}')
except ImportError as e:
    print(f'❌ OpenAI 导入失败: {e}')

try:
    import anthropic
    print(f'✅ Anthropic: {anthropic.__version__}')
except ImportError as e:
    print(f'❌ Anthropic 导入失败: {e}')

try:
    import pandas as pd
    print(f'✅ Pandas: {pd.__version__}')
except ImportError as e:
    print(f'❌ Pandas 导入失败: {e}')

print('\\n🎉 核心依赖验证完成！')
"
}

# 显示环境变量提醒
show_env_reminder() {
    echo ""
    echo "=========================================="
    echo "🔑 环境变量设置提醒"
    echo "=========================================="
    echo "请确保设置以下 API 密钥环境变量："
    echo ""
    echo "export OPENAI_API_KEY='your-openai-key'"
    echo "export ANTHROPIC_API_KEY='your-anthropic-key'"
    echo "export GEMINI_API_KEY='your-gemini-key'"
    echo "export MOONSHOT_API_KEY='your-moonshot-key'"
    echo "export DEEPSEEK_API_KEY='your-deepseek-key'"
    echo ""
    echo "或者在项目根目录创建 .env 文件："
    echo "cp config/.env.example config/.env"
    echo "# 然后编辑 config/.env 文件填入密钥"
    echo ""
}

# 主安装流程
main() {
    activate_env
    install_basic_deps
    detect_cuda
    install_pytorch
    install_faiss
    verify_installation
    show_env_reminder
    
    echo "=========================================="
    echo "🎉 安装完成！"
    echo "=========================================="
    echo "现在您可以运行："
    echo "conda activate RAG_env"
    echo "python start_evaluation.py --help"
    echo "=========================================="
}

# 运行主函数
main "$@"

