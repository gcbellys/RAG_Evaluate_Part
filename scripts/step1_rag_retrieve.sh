#!/usr/bin/env bash
set -euo pipefail

# 使用 RAG_Build 环境，对指定报告ID范围执行检索，写入结构化缓存(JSONL)
# 用法：
#   bash scripts/step1_rag_retrieve.sh <start_id> <end_id> [top_k]
# 示例：
#   bash scripts/step1_rag_retrieve.sh 4000 4002 3

START_ID=${1:-4000}
END_ID=${2:-4000}
TOP_K=${3:-3}

TEST_DIR="/home/duojiechen/Projects/Central_Data/RAG_System/test_set"
INDEX_DIR="/home/duojiechen/Projects/Rag_system/Rag_Build/enhanced_faiss_indexes"
OUT_DIR="/home/duojiechen/Projects/Rag_system/Rag_Evaluate/rag_search_output"
mkdir -p "${OUT_DIR}"

# 激活 RAG_Build 环境
source /home/duojiechen/miniconda3/etc/profile.d/conda.sh
conda activate RAG_Build

for ((i=${START_ID}; i<=${END_ID}; i++)); do
  FILE="${TEST_DIR}/diagnostic_${i}.json"
  if [ ! -f "${FILE}" ]; then
    echo "跳过：未找到文件 ${FILE}"
    continue
  fi
  echo "检索 diagnostic_${i}.json (TopK=${TOP_K})..."
  python /home/duojiechen/Projects/Rag_system/Rag_Build/scripts/search_file_symptoms.py \
    --file "${FILE}" \
    --index_dir "${INDEX_DIR}" \
    --top_k "${TOP_K}" \
    --out_dir "${OUT_DIR}"
done

echo "RAG 检索完成。缓存保存在: ${OUT_DIR}"

