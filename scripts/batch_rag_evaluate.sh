#!/bin/bash

# 批量RAG增强评估脚本
# 用法: bash batch_rag_evaluate.sh START_ID END_ID

set -e

# 参数检查
if [ $# -lt 2 ]; then
    echo "用法: $0 START_ID END_ID"
    echo "示例: $0 43001 43010"
    exit 1
fi

START_ID=$1
END_ID=$2

echo "========================================"
echo "🤖 批量RAG增强评估"
echo "========================================"
echo "📊 报告范围: $START_ID - $END_ID"
echo "📋 配置文件: config/config_cn.yaml"
echo "🔑 API密钥: config/.env"
echo "========================================"

# 激活环境
source /usr/local/miniconda/etc/profile.d/conda.sh
conda activate RAG_ws

echo "🔧 当前Python环境: $(which python)"
echo "🔧 当前Conda环境: $CONDA_DEFAULT_ENV"

# 批量评估
TOTAL_COUNT=$((END_ID - START_ID + 1))
CURRENT_COUNT=0
SUCCESS_COUNT=0
FAILED_COUNT=0

for i in $(seq $START_ID $END_ID); do
    CURRENT_COUNT=$((CURRENT_COUNT + 1))
    echo ""
    echo "📊 处理报告 $i ($CURRENT_COUNT/$TOTAL_COUNT)"
    echo "🤖 运行RAG增强评估..."
    
    # 调用RAG增强评估
    python /home/duojiechen/projects/Rag_system/Rag_Evaluate_feature/workflows/rerun_with_rag.py $i --config config/config_cn.yaml
    
    if [ $? -eq 0 ]; then
        echo "✅ 报告 $i 评估完成"
        SUCCESS_COUNT=$((SUCCESS_COUNT + 1))
    else
        echo "❌ 报告 $i 评估失败"
        FAILED_COUNT=$((FAILED_COUNT + 1))
    fi
done

echo ""
echo "========================================"
echo "📊 批量RAG增强评估完成!"
echo "========================================"
echo "✅ 成功处理: $SUCCESS_COUNT/$TOTAL_COUNT 个报告"
if [ $FAILED_COUNT -gt 0 ]; then
    echo "❌ 失败报告: $FAILED_COUNT 个"
fi
echo "📁 结果文件位置:"
echo "   🤖 RAG增强结果: final_result/rerun_with_rag/"
echo "   📊 对比分析: final_result/rerun_comparisons/"
echo "========================================"
