#!/usr/bin/env python3
"""
整合的数据加载器
包含所有数据加载、处理和验证功能
"""

import json
import os
from typing import List, Dict, Any, Iterator
from pathlib import Path

class DataLoader:
    """整合的数据加载器 - 支持Report级别和症状级别处理"""
    
    def __init__(self):
        pass
    
    def get_diagnostic_files(self, data_path: Path, max_files: int = None) -> List[Path]:
        """获取并排序诊断文件列表"""
        all_files = sorted(list(data_path.glob("*.json")), key=lambda x: x.stem)
        if max_files:
            return all_files[:max_files]
        return all_files
    
    def get_reports_by_id_range(self, data_path: Path, start_id: int = None, end_id: int = None, max_files: int = None) -> List[Path]:
        """
        按Report ID范围获取文件
        start_id: 开始序号（包含）
        end_id: 结束序号（包含）
        max_files: 最大文件数量限制
        """
        all_files = sorted(list(data_path.glob("*.json")), key=lambda x: x.stem)
        
        # 过滤文件
        filtered_files = []
        for file_path in all_files:
            try:
                # 提取文件名中的数字ID
                file_id = int(file_path.stem.replace('diagnostic_', ''))
                
                # 应用ID范围过滤
                if start_id is not None and file_id < start_id:
                    continue
                if end_id is not None and file_id > end_id:
                    continue
                
                filtered_files.append(file_path)
                
            except ValueError:
                # 如果文件名格式不正确，跳过
                continue
        
        # 应用最大文件数量限制
        if max_files:
            filtered_files = filtered_files[:max_files]
        
        return filtered_files
    
    def load_report_data(self, file_path: Path) -> Dict[str, Any]:
        """
        加载单个Report文件的数据
        返回Report级别的结构化数据
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = json.load(f)
            
            report_data = {
                'report_id': file_path.stem,
                'file_path': str(file_path),
                'total_symptoms': len(content),
                'symptoms': []
            }
            
            # 处理每个症状S
            for symptom_index, symptom_item in enumerate(content):
                if isinstance(symptom_item, dict) and 's_symptom' in symptom_item and 'U_unit_set' in symptom_item:
                    symptom_text = symptom_item['s_symptom'].strip()
                    if not symptom_text:
                        continue
                    
                    # 收集所有U单元的期望结果
                    expected_results = []
                    for u_unit_item in symptom_item['U_unit_set']:
                        if 'u_unit' in u_unit_item and 'o_organ' in u_unit_item['u_unit']:
                            expected_result = u_unit_item['u_unit']['o_organ']
                            expected_results.append({
                                'organName': expected_result.get('organName'),
                                'anatomicalLocations': expected_result.get('anatomicalLocations', [])
                            })
                    
                    # 如果U单元为空，跳过这个症状
                    if not expected_results:
                        continue
                    
                    symptom_data = {
                        'symptom_id': f"{file_path.stem}_symptom_{symptom_index}",
                        'symptom_index': symptom_index,
                        'symptom_text': symptom_text,
                        'expected_results': expected_results,
                        'total_u_units': len(expected_results)
                    }
                    
                    report_data['symptoms'].append(symptom_data)
            
            report_data['valid_symptoms'] = len(report_data['symptoms'])
            return report_data
            
        except Exception as e:
            print(f"处理文件 {file_path.name} 时出错: {e}")
            return {
                'report_id': file_path.stem,
                'file_path': str(file_path),
                'error': str(e),
                'symptoms': []
            }
    
    def extract_symptom_unit_pairs(self, file_path: Path) -> List[Dict[str, Any]]:
        """
        从单个诊断文件中提取症状-单元对 (S-U pairs)。
        保持向后兼容性，但建议使用load_report_data
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = json.load(f)
            
            pairs = []
            if isinstance(content, list):
                for item in content:
                    if isinstance(item, dict) and 's_symptom' in item and 'U_unit_set' in item:
                        symptom = item['s_symptom'].strip()
                        if not symptom:
                            continue
                        
                        # 每个 u_unit 都是一个独立的 Ground Truth
                        for u_unit_item in item['U_unit_set']:
                            if 'u_unit' in u_unit_item and 'o_organ' in u_unit_item['u_unit']:
                                expected_result = u_unit_item['u_unit']['o_organ']
                                pairs.append({
                                    'file_id': file_path.stem,
                                    'symptom': symptom,
                                    'expected_result': {
                                        'organName': expected_result.get('organName'),
                                        'anatomicalLocations': expected_result.get('anatomicalLocations', [])
                                    }
                                })
            
            return pairs
        except Exception as e:
            print(f"处理文件 {file_path.name} 时出错: {e}")
            return []
    
    def get_report_summary(self, data_path: Path, max_files: int = None) -> Dict[str, Any]:
        """获取数据目录的Report摘要信息"""
        files = self.get_diagnostic_files(data_path, max_files)
        
        summary = {
            'total_reports': len(files),
            'reports': []
        }
        
        for file_path in files:
            report_data = self.load_report_data(file_path)
            if 'error' not in report_data:
                summary['reports'].append({
                    'report_id': report_data['report_id'],
                    'total_symptoms': report_data['total_symptoms'],
                    'valid_symptoms': report_data['valid_symptoms']
                })
        
        return summary
    
    def get_report_summary_by_id_range(self, data_path: Path, start_id: int = None, end_id: int = None, max_files: int = None) -> Dict[str, Any]:
        """按ID范围获取Report摘要信息"""
        files = self.get_reports_by_id_range(data_path, start_id, end_id, max_files)
        
        summary = {
            'start_id': start_id,
            'end_id': end_id,
            'max_files': max_files,
            'total_reports': len(files),
            'reports': []
        }
        
        for file_path in files:
            report_data = self.load_report_data(file_path)
            if 'error' not in report_data:
                summary['reports'].append({
                    'report_id': report_data['report_id'],
                    'total_symptoms': report_data['total_symptoms'],
                    'valid_symptoms': report_data['valid_symptoms']
                })
        
        return summary
