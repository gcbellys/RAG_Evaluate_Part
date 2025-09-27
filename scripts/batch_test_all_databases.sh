#!/bin/bash

# 批量测试所有数据库类型
# 用法: bash batch_test_all_databases.sh START_ID END_ID [TOP_K]

set -e

# 参数检查
if [ $# -lt 2 ]; then
    echo "用法: $0 START_ID END_ID [TOP_K]"
    echo "示例: $0 43001 43010 3"
    exit 1
fi

START_ID=$1
END_ID=$2
TOP_K=${3:-3}

# 数据库类型数组
DATABASES=("sequential-block" "report-context" "uniform-random")

echo "========================================"
echo "🚀 批量测试所有数据库类型"
echo "========================================"
echo "📊 报告范围: $START_ID - $END_ID"
echo "🔍 Top-K: $TOP_K"
echo "🗄️  数据库类型: ${DATABASES[*]}"
echo "========================================"

# 激活环境
source /usr/local/miniconda/etc/profile.d/conda.sh
conda activate RAG_ws

TOTAL_DATABASES=${#DATABASES[@]}
CURRENT_DB=0

for DB_TYPE in "${DATABASES[@]}"; do
    CURRENT_DB=$((CURRENT_DB + 1))
    echo ""
    echo "========================================"
    echo "🗄️  测试数据库 $CURRENT_DB/$TOTAL_DATABASES: $DB_TYPE"
    echo "========================================"
    
    # 检查索引是否存在
    INDEX_DIR="/home/duojiechen/projects/Rag_system/Rag_Build/${DB_TYPE}_indexes"
    if [ ! -d "$INDEX_DIR" ]; then
        echo "❌ 错误: 索引目录不存在: $INDEX_DIR"
        echo "请先构建 $DB_TYPE 数据库的索引"
        continue
    fi
    
    echo "📁 索引目录: $INDEX_DIR"
    echo "🔍 开始批量测试..."
    
    # 使用完整pipeline测试
    python /home/duojiechen/projects/Rag_system/Rag_Evaluate_feature/workflows/run_full_pipeline.py $START_ID $END_ID --use_new_rag --db_type $DB_TYPE --top_k $TOP_K
    
    if [ $? -eq 0 ]; then
        echo "✅ $DB_TYPE 数据库测试完成"
    else
        echo "❌ $DB_TYPE 数据库测试失败"
    fi
    
    echo "📊 $DB_TYPE 测试结果保存在:"
    echo "   📁 RAG检索: final_result/rag_search_output/"
    echo "   📁 评估结果: final_result/rerun_comparisons/"
done

echo ""
echo "========================================"
echo "🎉 所有数据库测试完成!"
echo "========================================"
echo "📊 测试范围: 报告 $START_ID - $END_ID"
echo "🗄️  测试数据库: ${DATABASES[*]}"
echo "📁 查看结果: final_result/rerun_comparisons/"
echo "========================================"
