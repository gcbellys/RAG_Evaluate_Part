#!/usr/bin/env bash
set -euo pipefail

# 一键执行：
# 1) 运行 RAG 检索（step1），将缓存写入 final_result/rag_search_output/
# 2) 对每个报告运行评估（step2），导出 withRag / baseline / comparison 三类结果
#
# 用法：
#   bash scripts/run_rag_pipeline.sh <start_id> <end_id> [top_k]
# 示例：
#   bash scripts/run_rag_pipeline.sh 4000 4002 3

if [ $# -lt 2 ]; then
  echo "用法: bash scripts/run_rag_pipeline.sh <start_id> <end_id> [top_k]" >&2
  exit 1
fi

START_ID=${1}
END_ID=${2}
TOP_K=${3:-3}

BASE_DIR="/home/duojiechen/Projects/Rag_system/Rag_Evaluate"
STEP1="${BASE_DIR}/scripts/step1_rag_retrieve.sh"
STEP2="${BASE_DIR}/scripts/step2_eval_with_rag.sh"

OUT_RAG_DIR="${BASE_DIR}/final_result/rag_search_output"
OUT_WITH_DIR="${BASE_DIR}/final_result/api_output_withRag"
OUT_BASE_DIR="${BASE_DIR}/final_result/api_output_withoutRag"
OUT_COMP_DIR="${BASE_DIR}/final_result/rag_search_output/comparisons"
mkdir -p "${OUT_RAG_DIR}" "${OUT_WITH_DIR}" "${OUT_BASE_DIR}" "${OUT_COMP_DIR}"

echo "[1/2] 运行 RAG 检索: ${START_ID}-${END_ID} (TopK=${TOP_K})"
bash "${STEP1}" "${START_ID}" "${END_ID}" "${TOP_K}"

echo "[2/2] 运行评估并导出 API 结果与对比"
for ((rid=${START_ID}; rid<=${END_ID}; rid++)); do
  cache=$(ls -1t "${OUT_RAG_DIR}/report_${rid}_ragoutcome:"*.jsonl 2>/dev/null | head -n1 || true)
  if [ -z "${cache}" ]; then
    echo "  - 跳过 ${rid}: 未找到缓存（请检查 step1 输出）" >&2
    continue
  fi
  echo "  - 评估 report ${rid} (cache=$(basename "${cache}"))"
  bash "${STEP2}" "${rid}" "${cache}"
done

echo "\n完成。输出位置："
echo "  RAG 缓存: ${OUT_RAG_DIR}"
echo "  使用 RAG 的 API 输出: ${OUT_WITH_DIR}"
echo "  不使用 RAG 的 API 输出: ${OUT_BASE_DIR}"
echo "  前后对比: ${OUT_COMP_DIR}"


