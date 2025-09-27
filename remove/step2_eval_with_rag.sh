#!/usr/bin/env bash
set -euo pipefail

# 使用缓存的 RAG 结果运行 comparision_workflow，并导出三类文件：
# 1) 使用 RAG 的 API 输出 -> final_result/api_output_withRag/
# 2) 不使用 RAG（基线）的 API 输出 -> final_result/api_output_withoutRag/
# 3) 同一 API 同一症状的前后对比 -> final_result/rag_search_output/comparisons/
# 用法：
#   bash scripts/step2_eval_with_rag.sh <report_id> [cache_jsonl]

REPORT_ID=${1:-4000}

# 若未显式提供缓存，则自动在 final_result/rag_search_output 下选择该报告最新的缓存
if [ $# -ge 2 ]; then
  CACHE_FILE="$2"
else
  CACHE_FILE=$(ls -1t /home/duojiechen/Projects/Rag_system/Rag_Evaluate/final_result/rag_search_output/report_${REPORT_ID}_ragoutcome:*.jsonl 2>/dev/null | head -n1 || true)
fi

WITH_DIR="/home/duojiechen/Projects/Rag_system/Rag_Evaluate/final_result/api_output_withRag"
WITHOUT_DIR="/home/duojiechen/Projects/Rag_system/Rag_Evaluate/final_result/api_output_withoutRag"
COMP_DIR="/home/duojiechen/Projects/Rag_system/Rag_Evaluate/final_result/rag_search_output/comparisons"
mkdir -p "${WITH_DIR}" "${WITHOUT_DIR}" "${COMP_DIR}"

# 激活评估环境（此环境只需能跑 LLM 与 Python 依赖，不依赖 faiss-gpu）
source /home/duojiechen/miniconda3/etc/profile.d/conda.sh
conda activate rag5090 || true

# 运行对比工作流（带 RAG 缓存）。该运行会同时包含基线与 with-RAG 的结果
if [ -z "${CACHE_FILE}" ]; then
  echo "未找到 report_${REPORT_ID} 的 RAG 缓存，请先运行 step1_rag_retrieve.sh" >&2
  exit 1
fi

python /home/duojiechen/Projects/Rag_system/Rag_Evaluate/comparision_workflow.py \
  --config /home/duojiechen/Projects/Rag_system/Rag_Evaluate/config/config.yaml \
  --start_id ${REPORT_ID} \
  --end_id ${REPORT_ID} \
  --rag_cache "${CACHE_FILE}"

# 抽取最新的详细结果 JSON
DETAIL=$(ls -1t /home/duojiechen/Projects/Rag_system/Rag_Evaluate/results/report_diagnostic_${REPORT_ID}_evaluation_*.json | head -n1)
if [ -z "${DETAIL}" ]; then
  echo "未找到评估输出 JSON" >&2
  exit 1
fi

# 由详细结果拆分导出：withRag / withoutRag 两个 API 输出，以及 per-API 对比
export DETAIL
export WITH_DIR
export WITHOUT_DIR
export COMP_DIR
export REPORT_ID

python - <<'PY'
import json, os, sys, time
report_path = os.environ.get('DETAIL')
with_dir = os.environ.get('WITH_DIR')
without_dir = os.environ.get('WITHOUT_DIR')
comp_dir = os.environ.get('COMP_DIR')
rid = os.environ.get('REPORT_ID')
ts = time.strftime('%Y%m%d_%H%M%S')

with open(report_path, 'r', encoding='utf-8') as f:
    data = json.load(f)

# 组装简洁 API 输出（避免重复的评估字段）
def pack_api(api_responses):
    # api_responses 应当是字典 {'api_name': {...}}
    if not isinstance(api_responses, dict):
        # 若传入了错误类型（例如列表），则返回空字典，避免崩溃
        print(f"警告: pack_api 收到非字典类型: {type(api_responses)}", file=sys.stderr)
        return {}

    out = {}
    for api_name, resp in api_responses.items():
        out[api_name] = {
            'organ': resp.get('organ_name', ''),
            'a_position': resp.get('anatomical_locations', []),
            'evaluation': resp.get('evaluation', {})
        }
    return out

withrag = {}
baseline = {}
comparisons = {}
for i, s in enumerate(data.get('symptoms', [])):
    sname = s.get('diagnosis') or s.get('symptom') or s.get('text')
    if not sname:
        sname = f"symptom_{i}" # Fallback name

    # 兼容旧版与新版字段
    with_rag_responses = s.get('api_responses_with_rag') or s.get('api_responses') or {}
    baseline_responses = s.get('api_responses_baseline', {})

    # --- FIX: Handle case where responses are accidentally wrapped in a list ---
    if isinstance(with_rag_responses, list) and len(with_rag_responses) > 0:
        if len(with_rag_responses) == 1 and isinstance(with_rag_responses[0], dict):
            # If it's a list containing a single dictionary, unwrap it.
            print(f"--- [修正] 在处理 '{sname}' 时发现 'with_rag_responses' 是一个列表, 已自动解包.", file=sys.stderr)
            with_rag_responses = with_rag_responses[0]
    # --- END FIX ---

    withrag[sname] = pack_api(with_rag_responses)
    baseline[sname] = pack_api(baseline_responses)
    comparisons[sname] = s.get('comparison', {})

with_path = os.path.join(with_dir, f'report_{rid}_apis_withrag_{ts}.json')
base_path = os.path.join(without_dir, f'report_{rid}_apis_baseline_{ts}.json')
comp_path = os.path.join(comp_dir, f'report_{rid}_api_comparison_{ts}.json')

with open(with_path, 'w', encoding='utf-8') as f:
    json.dump(withrag, f, ensure_ascii=False, indent=2)
with open(base_path, 'w', encoding='utf-8') as f:
    json.dump(baseline, f, ensure_ascii=False, indent=2)
with open(comp_path, 'w', encoding='utf-8') as f:
    json.dump(comparisons, f, ensure_ascii=False, indent=2)

print('WITH_RAG ->', with_path)
print('BASELINE ->', base_path)
print('COMPARISON ->', comp_path)
PY

