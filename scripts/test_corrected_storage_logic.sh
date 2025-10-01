#!/bin/bash

# 测试修正后的存储逻辑

echo "🧪 测试修正后的存储逻辑"
echo "========================================"

# 测试参数
REPORT_ID=43001
DB_TYPE="sequential-block"

echo "📊 测试参数:"
echo "  报告ID: $REPORT_ID"
echo "  数据库类型: $DB_TYPE"
echo ""

# 激活环境
source /usr/local/miniconda/etc/profile.d/conda.sh
conda activate RAG_ws

echo "🔧 当前Python环境: $(which python)"
echo "🔧 当前Conda环境: $CONDA_DEFAULT_ENV"
echo ""

# 1. 测试RAG检索（现在应该存储到数据库特定目录）
echo "🔍 步骤1: RAG检索测试 (存储到数据库特定目录)"
bash /home/duojiechen/projects/Rag_system/Rag_Evaluate_feature/scripts/step1_rag_retrieve_new.sh $REPORT_ID $REPORT_ID 3 $DB_TYPE

if [ $? -eq 0 ]; then
    echo "✅ RAG检索测试成功"
else
    echo "❌ RAG检索测试失败"
    exit 1
fi

echo ""

# 2. 检查新的目录结构
echo "📁 步骤2: 检查新的目录结构"
echo ""

BASE_DIR="/home/duojiechen/projects/Rag_system/Rag_Evaluate_feature/final_result"

echo "📂 修正后的目录结构:"
echo ""

# 共享的baseline目录
echo "🔄 共享Baseline目录 (所有数据库共用):"
BASELINE_DIR="$BASE_DIR/baseline_results"
if [ -d "$BASELINE_DIR" ]; then
    echo "  ✅ $BASELINE_DIR"
    ls -la "$BASELINE_DIR" | grep $REPORT_ID | head -2 || echo "  (暂无该报告的baseline结果)"
else
    echo "  ❌ $BASELINE_DIR 不存在"
fi

echo ""

# 数据库特定的目录
echo "🗄️  数据库特定目录 ($DB_TYPE):"
DB_RESULT_DIR="$BASE_DIR/${DB_TYPE}_results"
if [ -d "$DB_RESULT_DIR" ]; then
    echo "  ✅ $DB_RESULT_DIR"
    echo ""
    echo "  📁 子目录结构:"
    ls -la "$DB_RESULT_DIR"
    
    echo ""
    echo "  🔍 RAG检索结果:"
    RAG_SEARCH_DIR="$DB_RESULT_DIR/rag_search_output"
    if [ -d "$RAG_SEARCH_DIR" ]; then
        echo "    ✅ $RAG_SEARCH_DIR"
        ls -la "$RAG_SEARCH_DIR" | grep $REPORT_ID | tail -3 || echo "    (暂无该报告的RAG检索结果)"
    else
        echo "    ❌ $RAG_SEARCH_DIR 不存在"
    fi
    
    echo ""
    echo "  🤖 RAG增强评估结果:"
    RAG_EVAL_DIR="$DB_RESULT_DIR/rerun_with_rag"
    if [ -d "$RAG_EVAL_DIR" ]; then
        echo "    ✅ $RAG_EVAL_DIR"
        ls -la "$RAG_EVAL_DIR" | grep $REPORT_ID | head -2 || echo "    (暂无该报告的RAG增强评估结果)"
    else
        echo "    ❌ $RAG_EVAL_DIR 不存在"
    fi
    
else
    echo "  ❌ $DB_RESULT_DIR 不存在"
fi

echo ""
echo "========================================"
echo "📋 存储逻辑总结:"
echo "  🔄 Baseline结果: 所有数据库共享 → final_result/baseline_results/"
echo "  🔍 RAG检索结果: 按数据库分开 → final_result/{db_type}_results/rag_search_output/"
echo "  🤖 RAG评估结果: 按数据库分开 → final_result/{db_type}_results/rerun_with_rag/"
echo "  📊 对比分析结果: 按数据库分开 → final_result/{db_type}_results/rerun_comparisons/"
echo "========================================"
