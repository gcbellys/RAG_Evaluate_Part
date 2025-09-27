#!/usr/bin/env bash
set -euo pipefail

# 使用 RAG_Build 环境，对指定报告ID范围执行检索，写入结构化缓存(JSONL)
# 用法：
#   bash scripts/step1_rag_retrieve.sh <start_id> <end_id> [top_k] [config_path] [--data-dir <data_dir>]
# 示例：
#   bash scripts/step1_rag_retrieve.sh 4000 4002 3 config/config.yaml
#   bash scripts/step1_rag_retrieve.sh 17500 17600 3 config/config_openai.yaml --data-dir diag_data_normalized

START_ID=${1:-4000}
END_ID=${2:-4000}
TOP_K=${3:-3}
CONFIG_PATH=${4:-"config/config.yaml"}

# 解析可选参数
DATA_DIR="test_set"

# 检查是否有额外的参数
if [ $# -gt 4 ]; then
    # 处理 --data-dir 参数
    for ((i=5; i<=$#; i++)); do
        arg="${!i}"
        case $arg in
            --data-dir=*)
                DATA_DIR="${arg#*=}"
                ;;
            --data-dir)
                if [ $i -lt $# ]; then
                    next_i=$((i+1))
                    DATA_DIR="${!next_i}"
                    i=$next_i
                fi
                ;;
        esac
    done
fi

TEST_DIR="/home/duojiechen/Projects/Central_Data/RAG_System/${DATA_DIR}"
INDEX_DIR="/home/duojiechen/Projects/Central_Data/RAG_System/enhanced_faiss_indexes_17000"
# 获取配置文件中的输出路径
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FULL_CONFIG_PATH="${SCRIPT_DIR}/../${CONFIG_PATH}"
OUT_DIR=$(python "${SCRIPT_DIR}/get_output_path.py" "${FULL_CONFIG_PATH}")
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
  echo "检索 diagnostic_${i}.json (TopK=${TOP_K}, DataDir=${DATA_DIR})..."
  python /home/duojiechen/Projects/Rag_system/Rag_Build/scripts/search_file_symptoms.py \
    --file "${FILE}" \
    --index_dir "${INDEX_DIR}" \
    --top_k "${TOP_K}" \
    --out_dir "${OUT_DIR}"
done

echo "RAG 检索完成。缓存保存在: ${OUT_DIR}"

