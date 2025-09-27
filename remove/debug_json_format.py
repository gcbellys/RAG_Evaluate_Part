import json
import sys
import os

def debug_report_format(report_path):
    """
    Loads a detailed report JSON and inspects the data types of API response fields.
    """
    if not os.path.exists(report_path):
        print(f"错误: 文件不存在 -> {report_path}", file=sys.stderr)
        sys.exit(1)

    with open(report_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    print(f"🔍 开始调试文件: {report_path}\n")

    symptoms = data.get('symptoms', [])
    if not symptoms:
        print("🟡 未在报告中找到 'symptoms' 列表。")
        return

    for i, symptom in enumerate(symptoms):
        s_name = symptom.get('diagnosis', f'Symptom_{i}')
        print(f"--- [Symptom {i+1}: {s_name}] ---")

        # Check the 'with_rag' responses
        with_rag_responses = symptom.get('api_responses_with_rag') or symptom.get('api_responses')
        if with_rag_responses is not None:
            print(f"  [With RAG]    类型: {type(with_rag_responses)}")
            print(f"  [With RAG]    内容: {json.dumps(with_rag_responses, ensure_ascii=False, indent=2)}")
        else:
            print("  [With RAG]    字段不存在")

        # Check the 'baseline' responses
        baseline_responses = symptom.get('api_responses_baseline')
        if baseline_responses is not None:
            print(f"  [Baseline]    类型: {type(baseline_responses)}")
            print(f"  [Baseline]    内容: {json.dumps(baseline_responses, ensure_ascii=False, indent=2)}")
        else:
            print("  [Baseline]    字段不存在")
        
        print("-" * (20 + len(s_name)) + "\n")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python debug_json_format.py <report_json_path>", file=sys.stderr)
        print("示例: python debug_json_format.py results/report_diagnostic_4000_evaluation_20250825_214135.json", file=sys.stderr)
        sys.exit(1)
    
    report_file = sys.argv[1]
    debug_report_format(report_file) 