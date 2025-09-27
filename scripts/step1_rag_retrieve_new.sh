#!/usr/bin/env bash
set -euo pipefail

# 使用新构建的数据库索引进行RAG检索
# 用法：
#   bash scripts/step1_rag_retrieve_new.sh <start_id> <end_id> [top_k] [db_type]
# 示例：
#   bash scripts/step1_rag_retrieve_new.sh 4000 4002 3 sequential-block

START_ID=${1:-4000}
END_ID=${2:-4000}
TOP_K=${3:-3}
DB_TYPE=${4:-sequential-block}

# 路径配置
TEST_DIR="/home/duojiechen/Central_Data/Testset_0_43000-43508/diagnostic_results_normalized"
INDEX_DIR="/home/duojiechen/projects/Rag_system/Rag_Build/${DB_TYPE}_indexes"
OUT_DIR="/home/duojiechen/projects/Rag_system/Rag_Evaluate_feature/final_result/rag_search_output"
mkdir -p "${OUT_DIR}"

# 检查测试集目录是否存在
if [ ! -d "${TEST_DIR}" ]; then
    echo "错误：测试集目录不存在: ${TEST_DIR}"
    exit 1
fi

# 检查索引目录是否存在
if [ ! -d "${INDEX_DIR}" ]; then
    echo "错误：索引目录不存在: ${INDEX_DIR}"
    echo "可用的数据库类型："
    ls -d /home/duojiechen/projects/Rag_system/Rag_Build/*_indexes 2>/dev/null | xargs -n1 basename | sed 's/_indexes$//' || echo "  (没有找到任何索引)"
    exit 1
fi

# 激活RAG_ws环境
source /usr/local/miniconda/etc/profile.d/conda.sh
conda activate RAG_ws

echo "🔧 当前Python环境: $(which python)"
echo "🔧 当前Conda环境: $CONDA_DEFAULT_ENV"

echo "========================================"
echo "🔍 新RAG检索系统"
echo "========================================"
echo "📊 报告范围: ${START_ID} - ${END_ID}"
echo "🔍 Top-K: ${TOP_K}"
echo "🗄️  数据库类型: ${DB_TYPE}"
echo "📁 索引目录: ${INDEX_DIR}"
echo "📁 输出目录: ${OUT_DIR}"
echo "========================================"

for ((i=${START_ID}; i<=${END_ID}; i++)); do
  FILE="${TEST_DIR}/diagnostic_${i}.json"
  if [ ! -f "${FILE}" ]; then
    echo "⚠️  跳过：未找到文件 ${FILE}"
    continue
  fi
  
  echo "🔍 检索 diagnostic_${i}.json (TopK=${TOP_K}, DB=${DB_TYPE})..."
  
  python /home/duojiechen/projects/Rag_system/Rag_Build/scripts/search_with_new_indexes.py \
    --file "${FILE}" \
    --index_dir "${INDEX_DIR}" \
    --db_type "${DB_TYPE}" \
    --top_k "${TOP_K}" \
    --search_type "symptom" \
    --out_dir "${OUT_DIR}"
  
  if [ $? -eq 0 ]; then
    echo "✅ diagnostic_${i}.json 检索完成"
  else
    echo "❌ diagnostic_${i}.json 检索失败"
    exit 1  # 如果有任何文件检索失败，立即退出
  fi
done

echo "========================================"
echo "🎉 RAG检索完成!"
echo "📁 结果保存在: ${OUT_DIR}"
echo "🗄️  使用数据库: ${DB_TYPE}"
echo "========================================"
exit 0  # 明确表示成功完成
