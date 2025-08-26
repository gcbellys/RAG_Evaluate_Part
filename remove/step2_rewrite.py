#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
一个全新的、稳健的评估流程脚本，用于替代 step2_eval_with_rag.sh
"""

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from glob import glob

# --- 1. 定义常量与路径 ---
# 脚本将自动定位项目目录，使其更具可移植性
try:
    PROJECT_DIR = Path(__file__).parent.parent.resolve()
except NameError:
    PROJECT_DIR = Path('.').resolve()

WITH_DIR = PROJECT_DIR / "final_result/api_output_withRag"
WITHOUT_DIR = PROJECT_DIR / "final_result/api_output_withoutRag"
COMP_DIR = PROJECT_DIR / "final_result/rag_search_output/comparisons"
RESULTS_DIR = PROJECT_DIR / "results"
# 修正：直接使用在其他脚本中被验证过的硬编码路径，放弃错误的自动推断
CONDA_ACTIVATE_SCRIPT = "/home/duojiechen/miniconda3/etc/profile.d/conda.sh"
CONDA_ENV = "rag5090"

def pack_api(api_responses: dict) -> dict:
    """
    从详细的API响应中，组装用于最终输出的简洁字典。
    这个函数是从旧脚本中移植过来的。
    """
    if not isinstance(api_responses, dict):
        # 这个问题是所有麻烦的根源，我们在这里处理它
        # 但理论上，在调用此函数之前，我们已经修正了数据
        return {}
    
    out = {}
    for api_name, resp in api_responses.items():
        out[api_name] = {
            'organ': resp.get('organ_name', ''),
            'a_position': resp.get('anatomical_locations', []),
            'evaluation': resp.get('evaluation', {})
        }
    return out

def process_and_save_results(report_path: str, report_id: int):
    """
    加载详细的JSON结果文件，拆分并保存三份最终报告。
    """
    print(f"\n--- 步骤 4: 处理JSON文件并拆分结果 ---")
    
    try:
        with open(report_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except (IOError, json.JSONDecodeError) as e:
        print(f"❌ 读取或解析JSON文件失败: {report_path}")
        print(f"   错误: {e}")
        sys.exit(1)

    withrag = {}
    baseline = {}
    comparisons = {}

    for i, s in enumerate(data.get('symptoms', [])):
        # 稳健地获取症状名称
        sname = s.get('diagnosis') or s.get('symptom') or s.get('text')
        if not sname:
            sname = f"symptom_{i}"

        # 获取数据字段
        with_rag_responses = s.get('api_responses_with_rag') or s.get('api_responses') or {}
        baseline_responses = s.get('api_responses_baseline', {})

        # --- 这是我们之前所有调试的核心修复逻辑 ---
        # 强制确保 'with_rag_responses' 是一个字典
        if isinstance(with_rag_responses, list):
            if len(with_rag_responses) == 1 and isinstance(with_rag_responses[0], dict):
                print(f"   [修正] 在处理 '{sname}' 时, 'with_rag_responses' 是一个列表, 已自动解包。")
                with_rag_responses = with_rag_responses[0]
            else:
                print(f"   [警告] 在处理 '{sname}' 时, 'with_rag_responses' 是一个无法处理的列表 (长度为 {len(with_rag_responses)}), 将其视为空数据。")
                with_rag_responses = {}
        
        # 确保 baseline_responses 也是一个字典
        if not isinstance(baseline_responses, dict):
             print(f"   [警告] 在处理 '{sname}' 时, 'baseline_responses' 不是字典 (类型为 {type(baseline_responses)}), 将其视为空数据。")
             baseline_responses = {}

        withrag[sname] = pack_api(with_rag_responses)
        baseline[sname] = pack_api(baseline_responses)
        comparisons[sname] = s.get('comparison', {})

    # 保存最终文件
    ts = time.strftime('%Y%m%d_%H%M%S')
    with_path = WITH_DIR / f'report_{report_id}_apis_withrag_{ts}.json'
    base_path = WITHOUT_DIR / f'report_{report_id}_apis_baseline_{ts}.json'
    comp_path = COMP_DIR / f'report_{report_id}_api_comparison_{ts}.json'

    with open(with_path, 'w', encoding='utf-8') as f:
        json.dump(withrag, f, ensure_ascii=False, indent=2)
    with open(base_path, 'w', encoding='utf-8') as f:
        json.dump(baseline, f, ensure_ascii=False, indent=2)
    with open(comp_path, 'w', encoding='utf-8') as f:
        json.dump(comparisons, f, ensure_ascii=False, indent=2)

    print("\n--- 步骤 5: 保存最终结果 ---")
    print(f"✅ WITH_RAG  -> {with_path}")
    print(f"✅ BASELINE  -> {base_path}")
    print(f"✅ COMPARISON-> {comp_path}")


def main(report_id: int, cache_file: str):
    """主执行函数"""
    print("=== 全新RAG评估流程 ===")
    
    # --- 步骤 1: 准备目录 ---
    print("\n--- 步骤 1: 创建输出目录 ---")
    WITH_DIR.mkdir(exist_ok=True)
    WITHOUT_DIR.mkdir(exist_ok=True)
    COMP_DIR.mkdir(exist_ok=True)
    print(f"  - 所有输出目录已准备就绪。")

    # --- 步骤 2: 运行核心工作流 ---
    print("\n--- 步骤 2: 运行核心评估工作流 (comparision_workflow.py) ---")
    workflow_script = PROJECT_DIR / "comparision_workflow.py"
    config_file = PROJECT_DIR / "config/config.yaml"

    command = (
        f"source {CONDA_ACTIVATE_SCRIPT} && "
        f"conda activate {CONDA_ENV} && "
        f"python {workflow_script} "
        f"--config {config_file} "
        f"--start_id {report_id} "
        f"--end_id {report_id} "
        f"--rag_cache \"{cache_file}\""
    )

    try:
        process = subprocess.run(
            command,
            shell=True,
            check=True,
            capture_output=True,
            text=True,
            executable='/bin/bash'
        )
        print("✅ 核心工作流成功完成。")
        # print("--- 工作流输出 ---")
        # print(process.stdout)
        # print("--------------------")
    except subprocess.CalledProcessError as e:
        print("❌ 核心工作流运行失败。")
        print(f"错误码: {e.returncode}")
        print("--- STDOUT ---")
        print(e.stdout)
        print("--- STDERR ---")
        print(e.stderr)
        sys.exit(1)

    # --- 步骤 3: 查找结果文件 ---
    print("\n--- 步骤 3: 查找最新的详细结果JSON文件 ---")
    search_pattern = str(RESULTS_DIR / f"report_diagnostic_{report_id}_evaluation_*.json")
    list_of_files = glob(search_pattern)
    
    # 修正：精确过滤，只选择我们需要的详细报告，排除standardized和user_format版本
    detailed_files = [
        f for f in list_of_files 
        if 'standardized' not in f and 'user_format' not in f
    ]

    if not detailed_files:
        print(f"❌ 错误: 在 '{RESULTS_DIR}' 中未找到报告ID {report_id} 的【详细】评估结果文件。")
        print(f"   (已排除 'standardized' 和 'user_format' 文件)")
        sys.exit(1)

    latest_file = max(detailed_files, key=os.path.getctime)
    print(f"✅ 找到文件: {latest_file}")
    
    # --- 步骤 4 & 5: 处理并保存 ---
    process_and_save_results(latest_file, report_id)
    
    print("\n=== 工作流全部完成 ===")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="一个全新的、稳健的评估流程脚本，用于替代 step2_eval_with_rag.sh",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("report_id", type=int, help="要处理的报告ID (例如: 4000)")
    parser.add_argument("cache_file", type=str, help="RAG检索结果的缓存JSONL文件路径")
    
    args = parser.parse_args()

    # 验证缓存文件是否存在
    if not Path(args.cache_file).is_file():
        print(f"❌ 错误: 缓存文件不存在 -> {args.cache_file}")
        sys.exit(1)
        
    main(args.report_id, args.cache_file) 