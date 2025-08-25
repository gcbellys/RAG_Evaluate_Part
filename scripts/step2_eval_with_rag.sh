#!/usr/bin/env bash
set -euo pipefail

# 使用缓存的 RAG 结果，运行 comparision_workflow 进行带RAG增强的评估
# 用法：
#   bash scripts/step2_eval_with_rag.sh <report_id> [cache_jsonl]
# 示例：
#   bash scripts/step2_eval_with_rag.sh 4000 \
#     /home/duojiechen/Projects/Rag_system/Rag_Build/rag_output/diagnostic_4000_search_results.jsonl

REPORT_ID=${1:-4000}
CACHE_FILE=${2:-"/home/duojiechen/Projects/Rag_system/Rag_Build/rag_output/diagnostic_${REPORT_ID}_search_results.jsonl"}

# 激活评估环境（此环境只需能跑 LLM 与 Python 依赖，不依赖 faiss-gpu）
source /home/duojiechen/miniconda3/etc/profile.d/conda.sh
conda activate rag5090 || true

python /home/duojiechen/Projects/Rag_system/Rag_Evaluate/comparision_workflow.py \
  --config /home/duojiechen/Projects/Rag_system/Rag_Evaluate/config/config.yaml \
  --start_id ${REPORT_ID} \
  --end_id ${REPORT_ID} \
  --rag_cache "${CACHE_FILE}"

echo "评估完成，结果在: /home/duojiechen/Projects/Rag_system/Rag_Evaluate/results"

