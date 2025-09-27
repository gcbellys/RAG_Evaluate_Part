#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量RAG检索脚本 - 优化版
一次初始化FAISS索引，然后批量处理多个报告文件
避免重复初始化的时间开销
"""

import os
import json
import argparse
import sys
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 添加RAG_Build路径
sys.path.append('/home/duojiechen/Projects/Rag_system/Rag_Build/src')
from enhanced_search_engine import EnhancedMedicalSearchEngine


def load_symptoms_from_file(file_path: str) -> List[Dict[str, Any]]:
    """从诊断文件中提取所有症状及其元数据"""
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    records = data if isinstance(data, list) else [data]
    items = []
    
    for rec in records:
        s = rec.get('s_symptom', '')
        if not s:
            continue
            
        organs_set = set()
        locs_set = set()
        
        for unit_wrapper in rec.get('U_unit_set', []) or []:
            u = unit_wrapper.get('u_unit', {}) if isinstance(unit_wrapper, dict) else {}
            organ_info = u.get('o_organ', {}) if isinstance(u, dict) else {}
            
            if isinstance(organ_info, dict):
                org_name = organ_info.get('organName')
                if org_name:
                    organs_set.add(org_name)
                    
                for loc in organ_info.get('anatomicalLocations', []) or []:
                    if isinstance(loc, str) and loc:
                        locs_set.add(loc)
        
        items.append({
            'symptom': s,
            'organs': sorted(list(organs_set)),
            'a_locations': sorted(list(locs_set))
        })
    
    return items


def process_single_file(search_engine: EnhancedMedicalSearchEngine, 
                       file_path: str, 
                       report_id: str,
                       top_k: int, 
                       output_dir: Path) -> bool:
    """处理单个报告文件"""
    try:
        print(f"  📄 处理报告 {report_id}...")
        
        # 加载症状
        symptoms_data = load_symptoms_from_file(file_path)
        if not symptoms_data:
            print(f"    ⚠️  文件 {file_path} 中没有找到有效症状")
            return False
        
        print(f"    📊 共 {len(symptoms_data)} 条症状")
        
        # 执行检索
        all_results = []
        for i, item in enumerate(symptoms_data):
            symptom = item['symptom']
            print(f"    🔍 检索症状 {i+1}/{len(symptoms_data)}: {symptom[:50]}...")
            
            try:
                # 执行检索
                search_result = search_engine.comprehensive_search(symptom, top_k=top_k)
                logger.info(f"检索结果类型: {type(search_result)}")
                logger.info(f"检索结果键: {search_result.keys() if isinstance(search_result, dict) else 'Not a dict'}")
                
                results = search_result.get('primary_results', [])
                logger.info(f"Primary results 数量: {len(results)}")
                
                # 按照原来的格式构建结果
                s_map = {}
                for rank_idx, item_result in enumerate(results[:top_k], 1):
                    logger.info(f"处理结果 {rank_idx}: {type(item_result)}")
                    data = item_result.get('data', {}) if isinstance(item_result, dict) else {}
                    
                    # 构建格子单元
                    units_grid = []
                    sid = data.get('s_id') if isinstance(data, dict) else None
                    logger.info(f"症状ID: {sid}")
                    
                    if sid and hasattr(search_engine, 'enhanced_units') and isinstance(search_engine.enhanced_units, list):
                        logger.info(f"Enhanced units 数量: {len(search_engine.enhanced_units)}")
                        for unit in search_engine.enhanced_units:
                            if unit.get('parent_s_id') == sid:
                                # 统一提取 organ 结构
                                o_struct = {'organName': '', 'anatomicalLocations': []}
                                name = None
                                locs = None
                                og = unit.get('o_organ')
                                if isinstance(og, dict):
                                    name = og.get('organName') or og.get('name')
                                    locs = og.get('anatomicalLocations') or og.get('locations')
                                if name is None:
                                    og2 = unit.get('organ')
                                    if isinstance(og2, dict):
                                        name = og2.get('organName') or og2.get('name')
                                        locs = og2.get('anatomicalLocations') or og2.get('locations')
                                    elif isinstance(og2, str):
                                        name = og2
                                if locs is None:
                                    locs = unit.get('anatomicalLocations') or unit.get('locations') or unit.get('anatomical_locations')
                                if isinstance(locs, list):
                                    o_struct['anatomicalLocations'] = [str(x) for x in locs if isinstance(x, str)]
                                if isinstance(name, str):
                                    o_struct['organName'] = name
                                units_grid.append({
                                    'u_id': unit.get('u_id'),
                                    'u_unit': {
                                        'd_diagnosis': unit.get('d_diagnosis') or unit.get('diagnosis_text') or '',
                                        'o_organ': o_struct,
                                        'b_textual_basis': {
                                            'medicalInference': unit.get('basis_text') or ''
                                        }
                                    }
                                })
                    
                    logger.info(f"Units grid 数量: {len(units_grid)}")
                    
                    # 构建症状条目
                    entry = {
                        's_text': item_result.get('symptom_text') or item_result.get('diagnosis_text') or item_result.get('basis_text', ''),
                        'units': units_grid
                    }
                    s_map[f'rag_s_{rank_idx}_id'] = entry
                
                # 构建完整记录（包含query字段）
                record = {
                    'query': symptom,
                    'expected_organs': item['organs'],
                    'expected_a_locations': item['a_locations'],
                    's': s_map
                }
                
                logger.info(f"构建的记录: {json.dumps(record, ensure_ascii=False, indent=2)[:500]}...")
                all_results.append(record)
                
            except Exception as e:
                logger.error(f"❌ 症状检索失败: {e}", exc_info=True)
                # 即使失败也要保持格式一致
                record = {
                    'query': symptom,
                    'expected_organs': item['organs'],
                    'expected_a_locations': item['a_locations'],
                    's': {}
                }
                all_results.append(record)
        
        # 保存结果
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = output_dir / f"report_{report_id}_ragoutcome:{timestamp}.jsonl"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            for result in all_results:
                f.write(json.dumps(result, ensure_ascii=False) + '\n')
        
        print(f"    ✅ 完成。输出: {output_file}")
        return True
        
    except Exception as e:
        print(f"    ❌ 处理文件 {file_path} 失败: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="批量RAG检索 - 优化版")
    parser.add_argument("--start_id", type=int, required=True, help="开始报告ID")
    parser.add_argument("--end_id", type=int, required=True, help="结束报告ID")
    parser.add_argument("--data_dir", type=str, default="test_set", help="数据目录")
    parser.add_argument("--index_dir", type=str, required=True, help="FAISS索引目录")
    parser.add_argument("--output_dir", type=str, required=True, help="输出目录")
    parser.add_argument("--top_k", type=int, default=3, help="检索Top-K")
    
    args = parser.parse_args()
    
    print("=" * 80)
    print("🚀 批量RAG检索 - 优化版")
    print("=" * 80)
    print(f"📋 报告范围: {args.start_id} - {args.end_id}")
    print(f"📁 数据目录: {args.data_dir}")
    print(f"🔍 检索参数: top_k={args.top_k}")
    print(f"📂 索引目录: {args.index_dir}")
    print(f"💾 输出目录: {args.output_dir}")
    print("=" * 80)
    
    # 确保输出目录存在
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 一次性初始化搜索引擎
    print("\n🔧 初始化搜索引擎...")
    try:
        search_engine = EnhancedMedicalSearchEngine(args.index_dir)
        print("✅ 搜索引擎初始化完成")
    except Exception as e:
        print(f"❌ 搜索引擎初始化失败: {e}")
        sys.exit(1)
    
    # 批量处理文件
    print(f"\n📊 开始批量处理 {args.end_id - args.start_id + 1} 个报告...")
    
    success_count = 0
    total_count = 0
    data_base_dir = f"/home/duojiechen/Projects/Central_Data/RAG_System/{args.data_dir}"
    
    for report_id in range(args.start_id, args.end_id + 1):
        file_path = f"{data_base_dir}/diagnostic_{report_id}.json"
        
        if not os.path.exists(file_path):
            print(f"  ⚠️  跳过：未找到文件 {file_path}")
            continue
        
        total_count += 1
        if process_single_file(search_engine, file_path, str(report_id), args.top_k, output_dir):
            success_count += 1
    
    # 最终统计
    print("\n" + "=" * 80)
    print("🏁 批量RAG检索完成")
    print("=" * 80)
    print(f"📊 处理统计:")
    print(f"   总计: {total_count} 个文件")
    print(f"   成功: {success_count} 个")
    print(f"   失败: {total_count - success_count} 个")
    print(f"   成功率: {success_count/total_count*100:.1f}%" if total_count > 0 else "   成功率: 0%")
    print(f"💾 结果保存在: {output_dir}")
    print("=" * 80)
    
    # 返回适当的退出码
    sys.exit(0 if success_count == total_count else 1)


if __name__ == "__main__":
    main()
