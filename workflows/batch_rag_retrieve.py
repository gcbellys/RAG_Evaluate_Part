#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量RAG检索（单进程、单模型预热，避免重复初始化）

- 复用 Rag_Build 中的搜索引擎与解析逻辑，不改动检索实现：
  from search_with_new_indexes import NewDatabaseSearchEngine, load_symptoms_from_file

- 按给定范围 [start_id, end_id] 与 db_type、top_k 一次性完成检索
  输出与 step1_rag_retrieve_new.sh 相同：
    final_result/{db_type}_results/rag_search_output/report_{id}_ragoutcome:YYYYmmdd_HHMMSS.jsonl
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path


def import_engine():
    rag_build_scripts = "/home/duojiechen/projects/Rag_system/Rag_Build/scripts"
    if rag_build_scripts not in sys.path:
        sys.path.append(rag_build_scripts)
    # 惰性导入，避免路径污染
    from search_with_new_indexes import NewDatabaseSearchEngine, load_symptoms_from_file  # type: ignore
    return NewDatabaseSearchEngine, load_symptoms_from_file


def main():
    parser = argparse.ArgumentParser(description="批量RAG检索（单进程、跨报告预热）")
    parser.add_argument("start_id", type=int, help="开始报告ID")
    parser.add_argument("end_id", type=int, help="结束报告ID（包含）")
    parser.add_argument("--db_type", choices=["sequential-block", "report-context", "uniform-random"],
                        default="sequential-block", help="数据库类型")
    parser.add_argument("--top_k", type=int, default=3, help="每个症状返回Top-K")
    parser.add_argument("--test_dir", type=str,
                        default="/home/duojiechen/Central_Data/Testset_0_43000-43508/diagnostic_results_normalized",
                        help="测试集目录")
    parser.add_argument("--index_root", type=str,
                        default="/home/duojiechen/projects/Rag_system/Rag_Build",
                        help="索引根目录（将自动拼接 {db_type}_indexes")
    parser.add_argument("--out_root", type=str,
                        default=str(Path(__file__).parent.parent / "final_result"),
                        help="输出根目录（将自动拼接 {db_type}_results/rag_search_output")

    args = parser.parse_args()

    start_id = args.start_id
    end_id = args.end_id

    test_dir = Path(args.test_dir)
    if not test_dir.is_dir():
        raise FileNotFoundError(f"测试集目录不存在: {test_dir}")

    index_dir = Path(args.index_root) / f"{args.db_type}_indexes"
    if not index_dir.is_dir():
        raise FileNotFoundError(f"索引目录不存在: {index_dir}")

    out_dir = Path(args.out_root) / f"{args.db_type}_results" / "rag_search_output"
    out_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 40)
    print("🔍 批量RAG检索（单进程预热）")
    print("=" * 40)
    print(f"📋 报告范围: {start_id} - {end_id}")
    print(f"🗄️  数据库类型: {args.db_type}")
    print(f"🔍 Top-K: {args.top_k}")
    print(f"📁 索引目录: {index_dir}")
    print(f"📁 输出目录: {out_dir}")

    NewDatabaseSearchEngine, load_symptoms_from_file = import_engine()

    # 单次初始化模型与索引
    print("初始化搜索引擎与索引（一次）...")
    engine = NewDatabaseSearchEngine(str(index_dir), args.db_type)
    print("✅ 预热完成，开始批量检索")

    success = 0
    total = end_id - start_id + 1
    for report_id in range(start_id, end_id + 1):
        file_path = test_dir / f"diagnostic_{report_id}.json"
        if not file_path.exists():
            print(f"⚠️  跳过：未找到 {file_path}")
            continue

        # 生成每个报告的输出文件名（含时间戳，避免覆盖）
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        output_path = out_dir / f"report_{report_id}_ragoutcome:{timestamp}.jsonl"

        print(f"加载症状自: {file_path}")
        symptoms_info = load_symptoms_from_file(str(file_path))
        print(f"共 {len(symptoms_info)} 条症状")

        written = 0
        with open(output_path, 'w', encoding='utf-8') as out_f:
            for info in symptoms_info:
                symptom = info['symptom']
                search_result = engine.comprehensive_search(
                    query=symptom,
                    top_k=args.top_k,
                    search_type="symptom",
                )
                record = {
                    'query': symptom,
                    'expected_organs': info.get('organs', []),
                    'expected_locations': info.get('a_locations', []),
                    'rag_results': search_result,
                    'timestamp': datetime.now().isoformat(),
                }
                out_f.write(json.dumps(record, ensure_ascii=False) + '\n')
                written += 1

        # 简单的统计文件
        stats_file = str(output_path).replace('.jsonl', '_stats.json')
        with open(stats_file, 'w', encoding='utf-8') as f:
            json.dump({
                'total_symptoms': written,
                'db_type': args.db_type,
                'top_k': args.top_k,
                'timestamp': datetime.now().isoformat(),
                'output_file': str(output_path),
            }, f, ensure_ascii=False, indent=2)

        print(f"检索完成! 结果保存到: {output_path}")
        success += 1

    print("=" * 40)
    print(f"🎉 批量检索结束：成功 {success}/{total}")
    print(f"📁 输出目录: {out_dir}")


if __name__ == "__main__":
    main()

