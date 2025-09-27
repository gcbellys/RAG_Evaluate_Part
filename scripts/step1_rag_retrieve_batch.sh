#!/usr/bin/env bash
set -euo pipefail

# 批量RAG检索脚本 - 优化版
# 一次初始化FAISS索引，然后批量处理多个报告文件
# 用法：
#   bash scripts/step1_rag_retrieve_batch.sh <start_id> <end_id> [top_k] [config_path] [--data-dir <data_dir>]
# 示例：
#   bash scripts/step1_rag_retrieve_batch.sh 18001 18050 3 config/config_openai.yaml
#   bash scripts/step1_rag_retrieve_batch.sh 17500 17600 3 config/config.yaml --data-dir diag_data_normalized

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

INDEX_DIR="/home/duojiechen/Projects/Central_Data/RAG_System/enhanced_faiss_indexes_17000"

# 获取配置文件中的输出路径
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FULL_CONFIG_PATH="${SCRIPT_DIR}/../${CONFIG_PATH}"
OUT_DIR=$(python "${SCRIPT_DIR}/get_output_path.py" "${FULL_CONFIG_PATH}")

echo "批量RAG检索 (优化版) - 报告范围: ${START_ID}-${END_ID} (TopK=${TOP_K}, DataDir=${DATA_DIR})"
echo "一次初始化FAISS索引，避免重复加载开销..."

# 激活 RAG_Build 环境
source /home/duojiechen/miniconda3/etc/profile.d/conda.sh
conda activate RAG_Build

# 调用优化的批量处理脚本
python "${SCRIPT_DIR}/batch_rag_retrieve.py" \
    --start_id "${START_ID}" \
    --end_id "${END_ID}" \
    --data_dir "${DATA_DIR}" \
    --index_dir "${INDEX_DIR}" \
    --output_dir "${OUT_DIR}" \
    --top_k "${TOP_K}"

echo "批量RAG检索完成。缓存保存在: ${OUT_DIR}"
