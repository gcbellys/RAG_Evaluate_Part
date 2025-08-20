#!/usr/bin/env python3
"""
FAISS检索器集成类
用于在RAG工作流中提供向量检索功能
"""

import os
import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class FAISSRetriever:
    """FAISS向量检索器"""
    
    def __init__(self, index_dir: str):
        """
        初始化检索器
        
        Args:
            index_dir: 增强索引目录路径
        """
        self.index_dir = Path(index_dir)
        self.enhanced_symptoms = None
        self.enhanced_units = None
        self.symptom_ids = None
        
        # 加载数据
        self._load_data()
    
    def _load_data(self):
        """加载索引数据"""
        try:
            logger.info("Loading FAISS index data...")
            
            # 加载增强症状数据
            symptoms_path = self.index_dir / "enhanced_symptoms.json"
            if symptoms_path.exists():
                with open(symptoms_path, 'r', encoding='utf-8') as f:
                    self.enhanced_symptoms = json.load(f)
                logger.info(f"Enhanced symptoms loaded: {len(self.enhanced_symptoms)} symptoms")
            
            # 加载增强单元数据
            units_path = self.index_dir / "enhanced_units.json"
            if units_path.exists():
                with open(units_path, 'r', encoding='utf-8') as f:
                    self.enhanced_units = json.load(f)
                logger.info(f"Enhanced units loaded: {len(self.enhanced_units)} units")
            
            # 加载症状ID映射
            symptom_ids_path = self.index_dir / "symptom_ids.json"
            if symptom_ids_path.exists():
                with open(symptom_ids_path, 'r', encoding='utf-8') as f:
                    self.symptom_ids = json.load(f)
                logger.info(f"Symptom IDs loaded: {len(self.symptom_ids)} mappings")
                
        except Exception as e:
            logger.error(f"Failed to load FAISS data: {e}")
            raise
    
    def search_similar_symptoms(self, query_symptom: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        搜索相似症状（基于症状文本的智能匹配）
        
        Args:
            query_symptom: 查询症状文本
            top_k: 返回结果数量
            
        Returns:
            相似症状列表
        """
        if not self.enhanced_symptoms:
            logger.warning("No enhanced symptoms data available")
            return []
        
        similar_symptoms = []
        
        # 提取查询中的医学关键词
        query_lower = query_symptom.lower()
        
        # 医学关键词权重系统
        medical_keywords = {
            'heart': 5, 'cardiac': 5, 'aortic': 5, 'valve': 4, 'ventricle': 4,
            'lung': 5, 'pulmonary': 5, 'breath': 4, 'dyspnea': 5, 'respiratory': 4,
            'brain': 5, 'cerebral': 5, 'consciousness': 4, 'neurological': 4,
            'eye': 5, 'visual': 4, 'blind': 4, 'retina': 4, 'optic': 4,
            'pain': 3, 'ache': 3, 'discomfort': 3, 'symptom': 2, 'condition': 2
        }
        
        for symptom in self.enhanced_symptoms:
            symptom_text = symptom.get('text', '').lower()
            
            # 计算医学相关性分数
            relevance_score = 0
            matched_keywords = []
            
            for keyword, weight in medical_keywords.items():
                if keyword in query_lower and keyword in symptom_text:
                    relevance_score += weight
                    matched_keywords.append(keyword)
            
            # 计算文本相似度（基于共同词汇）
            query_words = set(query_lower.split())
            symptom_words = set(symptom_text.split())
            common_words = query_words.intersection(symptom_words)
            text_similarity = len(common_words) / max(len(query_words), 1)
            
            # 综合分数
            total_score = relevance_score + (text_similarity * 10)
            
            if total_score > 3:  # 设置合理的阈值
                # 获取相关器官信息
                associated_organs = self._find_symptom_organs(symptom.get('s_id', ''))
                
                similar_symptoms.append({
                    'symptom_id': symptom.get('s_id', ''),
                    'symptom_text': symptom.get('text', ''),
                    'similarity_score': total_score / 20,  # 归一化到0-1
                    'matched_keywords': matched_keywords,
                    'text_similarity': text_similarity,
                    'associated_organs': associated_organs,
                    'organ_count': len(associated_organs)
                })
        
        # 按综合分数排序并返回top_k结果
        similar_symptoms.sort(key=lambda x: x['similarity_score'], reverse=True)
        return similar_symptoms[:top_k]
    
    def _find_symptom_organs(self, symptom_id: str) -> List[Dict[str, Any]]:
        """
        查找症状相关的器官信息
        
        Args:
            symptom_id: 症状ID
            
        Returns:
            器官信息列表
        """
        if not self.enhanced_units:
            return []
        
        organs = []
        organ_dict = {}
        
        # 查找所有与该症状相关的单元
        for unit in self.enhanced_units:
            if unit.get('parent_s_id') == symptom_id:
                organ_name = unit.get('organ', 'Unknown')
                diagnosis = unit.get('diagnosis_text', '')
                
                if organ_name not in organ_dict:
                    organ_dict[organ_name] = {
                        'organ_name': organ_name,
                        'diagnoses': [],
                        'unit_count': 0
                    }
                
                organ_dict[organ_name]['diagnoses'].append(diagnosis)
                organ_dict[organ_name]['unit_count'] += 1
        
        # 转换为列表并按单元数量排序
        organs = list(organ_dict.values())
        organs.sort(key=lambda x: x['unit_count'], reverse=True)
        
        return organs
    
    def format_search_results_for_prompt(self, search_results: List[Dict[str, Any]]) -> str:
        """
        将搜索结果格式化为提示词
        
        Args:
            search_results: 搜索结果列表
            
        Returns:
            格式化的提示词文本
        """
        if not search_results:
            return "No similar symptoms found in the knowledge base."
        
        prompt_text = "Vector Search Results from Medical Knowledge Base:\n\n"
        
        for i, result in enumerate(search_results, 1):
            prompt_text += f"Result {i}:\n"
            prompt_text += f"- Symptom: {result['symptom_text']}\n"
            prompt_text += f"- Similarity Score: {result['similarity_score']:.3f}\n"
            prompt_text += f"- Matched Keywords: {', '.join(result.get('matched_keywords', []))}\n"
            prompt_text += f"- Text Similarity: {result.get('text_similarity', 0):.3f}\n"
            prompt_text += f"- Associated Organs: {result['organ_count']}\n"
            
            if result['associated_organs']:
                prompt_text += "- Organ Details:\n"
                for organ in result['associated_organs']:
                    prompt_text += f"  * {organ['organ_name']} ({organ['unit_count']} diagnoses)\n"
                    # 显示前几个诊断
                    for diagnosis in organ['diagnoses'][:2]:
                        prompt_text += f"    - {diagnosis[:60]}...\n"
                    if len(organ['diagnoses']) > 2:
                        prompt_text += f"    ... and {len(organ['diagnoses']) - 2} more\n"
            
            prompt_text += "\n"
        
        return prompt_text


def create_rag_enhanced_prompt(system_prompt: str, user_symptom: str, search_results: List[Dict[str, Any]]) -> str:
    """
    创建RAG增强的提示词
    
    Args:
        system_prompt: 系统提示词
        user_symptom: 用户症状
        search_results: 搜索结果
        
        Returns:
            完整的RAG增强提示词
    """
    # 格式化搜索结果
    search_context = FAISSRetriever("").format_search_results_for_prompt(search_results)
    
    # 组合提示词
    enhanced_prompt = f"{system_prompt}\n\n{search_context}\n\nPatient Symptom: {user_symptom}\n\nPlease analyze the symptom and the search results above to provide your assessment."
    
    return enhanced_prompt
