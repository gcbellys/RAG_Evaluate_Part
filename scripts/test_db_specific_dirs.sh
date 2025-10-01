#!/bin/bash

# 测试数据库特定目录结构的脚本

echo "🧪 测试数据库特定目录结构"
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

# 1. 测试RAG检索（使用统一的rag_search_output目录）
echo "🔍 步骤1: RAG检索测试"
bash /home/duojiechen/projects/Rag_system/Rag_Evaluate_feature/scripts/step1_rag_retrieve_new.sh $REPORT_ID $REPORT_ID 3 $DB_TYPE

if [ $? -eq 0 ]; then
    echo "✅ RAG检索测试成功"
else
    echo "❌ RAG检索测试失败"
    exit 1
fi

echo ""

# 2. 测试RAG增强评估（使用数据库特定目录）
echo "🤖 步骤2: RAG增强评估测试"
python /home/duojiechen/projects/Rag_system/Rag_Evaluate_feature/workflows/rerun_with_rag.py $REPORT_ID --config config/config_cn.yaml --db_type $DB_TYPE

if [ $? -eq 0 ]; then
    echo "✅ RAG增强评估测试成功"
else
    echo "❌ RAG增强评估测试失败"
    exit 1
fi

echo ""

# 3. 检查生成的目录结构
echo "📁 步骤3: 检查目录结构"
echo ""
echo "📂 统一RAG检索输出目录:"
ls -la /home/duojiechen/projects/Rag_system/Rag_Evaluate_feature/final_result/rag_search_output/ | grep $REPORT_ID | tail -3

echo ""
echo "📂 数据库特定结果目录:"
DB_RESULT_DIR="/home/duojiechen/projects/Rag_system/Rag_Evaluate_feature/final_result/${DB_TYPE}_results"
if [ -d "$DB_RESULT_DIR" ]; then
    echo "  ✅ $DB_RESULT_DIR 目录已创建"
    echo "  📁 子目录结构:"
    ls -la "$DB_RESULT_DIR"
    
    echo ""
    echo "  📄 生成的结果文件:"
    find "$DB_RESULT_DIR" -name "*$REPORT_ID*" -type f | head -5
else
    echo "  ❌ $DB_RESULT_DIR 目录不存在"
fi

echo ""
echo "========================================"
echo "🎉 测试完成!"
echo "========================================"
