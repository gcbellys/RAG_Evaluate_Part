#!/bin/bash

# 批量RAG检索脚本
# 用法: bash batch_rag_retrieve.sh START_ID END_ID DB_TYPE [TOP_K]

set -e

# 参数检查
if [ $# -lt 3 ]; then
    echo "用法: $0 START_ID END_ID DB_TYPE [TOP_K]"
    echo "示例: $0 43001 43010 sequential-block 3"
    exit 1
fi

START_ID=$1
END_ID=$2
DB_TYPE=$3
TOP_K=${4:-3}

# 验证数据库类型
if [[ ! "$DB_TYPE" =~ ^(sequential-block|report-context|uniform-random)$ ]]; then
    echo "❌ 错误: 数据库类型必须是 sequential-block, report-context, 或 uniform-random"
    exit 1
fi

echo "========================================"
echo "🔍 批量RAG检索"
echo "========================================"
echo "📊 报告范围: $START_ID - $END_ID"
echo "🔍 Top-K: $TOP_K"
echo "🗄️  数据库类型: $DB_TYPE"
echo "📁 索引目录: /home/duojiechen/projects/Rag_system/Rag_Build/${DB_TYPE}_indexes"
echo "📁 输出目录: /home/duojiechen/projects/Rag_system/Rag_Evaluate_feature/final_result/rag_search_output"
echo "========================================"

# 激活环境
source /usr/local/miniconda/etc/profile.d/conda.sh
conda activate RAG_ws

echo "🔧 当前Python环境: $(which python)"
echo "🔧 当前Conda环境: $CONDA_DEFAULT_ENV"

# 批量检索
TOTAL_COUNT=$((END_ID - START_ID + 1))
CURRENT_COUNT=0

for i in $(seq $START_ID $END_ID); do
    CURRENT_COUNT=$((CURRENT_COUNT + 1))
    echo ""
    echo "📊 处理报告 $i ($CURRENT_COUNT/$TOTAL_COUNT)"
    echo "🔍 检索 diagnostic_$i.json (TopK=$TOP_K, DB=$DB_TYPE)..."
    
    # 调用RAG检索脚本
    bash /home/duojiechen/projects/Rag_system/Rag_Evaluate_feature/scripts/step1_rag_retrieve_new.sh $i $i $TOP_K $DB_TYPE
    
    if [ $? -eq 0 ]; then
        echo "✅ diagnostic_$i.json 检索完成"
    else
        echo "❌ diagnostic_$i.json 检索失败"
        exit 1
    fi
done

echo ""
echo "========================================"
echo "🎉 批量RAG检索完成!"
echo "📁 结果保存在: /home/duojiechen/projects/Rag_system/Rag_Evaluate_feature/final_result/rag_search_output"
echo "🗄️  使用数据库: $DB_TYPE"
echo "📊 成功处理: $TOTAL_COUNT 个报告"
echo "========================================"
