#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
增强版RAG_3DB检索适配器 - 基于高质量代码的改进版本

主要改进：
1. 医学文本预处理和标准化
2. 多阶段搜索策略（粗排+精排+过滤）
3. 智能RAG质量评估和过滤
4. 医学领域特定的相似度计算
5. 结果重排序和多样性保证

基于 rerun_with_rag.py 和 RAG_Search.py 的优秀设计
作者: AI Assistant
日期: 2025-09-24
"""

import os
import sys
import json
import faiss
import numpy as np
import pymongo
import argparse
import re
from typing import List, Dict, Any, Tuple, Optional, Set
from pathlib import Path
from datetime import datetime
from sentence_transformers import SentenceTransformer
from collections import defaultdict, Counter

# 添加RAG_3DB路径
sys.path.append('/home/duojiechen/projects/Rag_system/RAG_3DB/src')

class MedicalTextPreprocessor:
    """医学文本预处理器"""
    
    def __init__(self):
        # 医学缩写词典
        self.medical_abbreviations = {
            'PSA': 'prostate specific antigen',
            'BP': 'blood pressure',
            'HR': 'heart rate',
            'ECG': 'electrocardiogram',
            'EKG': 'electrocardiogram',
            'CT': 'computed tomography',
            'MRI': 'magnetic resonance imaging',
            'CBC': 'complete blood count',
            'BUN': 'blood urea nitrogen',
            'LDL': 'low density lipoprotein',
            'HDL': 'high density lipoprotein',
            'MI': 'myocardial infarction',
            'CHF': 'congestive heart failure',
            'COPD': 'chronic obstructive pulmonary disease',
            'UTI': 'urinary tract infection',
            'DVT': 'deep vein thrombosis',
            'PE': 'pulmonary embolism',
            'CAD': 'coronary artery disease',
            'CABG': 'coronary artery bypass graft',
            'PCI': 'percutaneous coronary intervention',
            'AVR': 'aortic valve replacement',
            'MVR': 'mitral valve replacement',
            'LVEF': 'left ventricular ejection fraction',
            'EF': 'ejection fraction',
            'SBP': 'systolic blood pressure',
            'DBP': 'diastolic blood pressure',
            'RUL': 'right upper lobe',
            'RML': 'right middle lobe',
            'RLL': 'right lower lobe',
            'LUL': 'left upper lobe',
            'LLL': 'left lower lobe'
        }
        
        # 医学同义词
        self.medical_synonyms = {
            'dyspnea': ['shortness of breath', 'breathing difficulty', 'breathlessness'],
            'chest pain': ['thoracic pain', 'chest discomfort', 'precordial pain'],
            'elevated': ['increased', 'high', 'raised'],
            'decreased': ['reduced', 'low', 'diminished'],
            'hypertension': ['high blood pressure', 'elevated blood pressure'],
            'hypotension': ['low blood pressure', 'decreased blood pressure'],
            'tachycardia': ['rapid heart rate', 'fast heart rate'],
            'bradycardia': ['slow heart rate', 'low heart rate'],
            'arrhythmia': ['irregular heartbeat', 'cardiac rhythm disorder'],
            'edema': ['swelling', 'fluid retention'],
            'fatigue': ['tiredness', 'weakness', 'exhaustion'],
            'nausea': ['queasiness', 'sick feeling'],
            'vomiting': ['emesis', 'throwing up'],
            'headache': ['cephalgia', 'head pain'],
            'dizziness': ['vertigo', 'lightheadedness'],
            'syncope': ['fainting', 'loss of consciousness']
        }
        
        # 器官系统映射
        self.organ_systems = {
            'cardiovascular': ['heart', 'cardiac', 'aortic', 'mitral', 'tricuspid', 'pulmonary valve', 'coronary', 'artery', 'vein'],
            'respiratory': ['lung', 'pulmonary', 'bronchus', 'trachea', 'pleura', 'respiratory'],
            'gastrointestinal': ['stomach', 'liver', 'pancreas', 'intestine', 'colon', 'rectum', 'gallbladder'],
            'genitourinary': ['kidney', 'bladder', 'prostate', 'urethra', 'ureter'],
            'neurological': ['brain', 'cerebral', 'spinal', 'nerve', 'neurological'],
            'musculoskeletal': ['bone', 'muscle', 'joint', 'spine', 'skeletal'],
            'endocrine': ['thyroid', 'diabetes', 'hormone', 'endocrine']
        }
    
    def expand_abbreviations(self, text: str) -> str:
        """展开医学缩写"""
        words = text.split()
        expanded_words = []
        
        for word in words:
            # 移除标点符号进行匹配
            clean_word = re.sub(r'[^\w]', '', word.upper())
            if clean_word in self.medical_abbreviations:
                expanded = self.medical_abbreviations[clean_word]
                # 保持原始的标点符号
                expanded_word = re.sub(r'[A-Za-z]+', expanded, word, flags=re.IGNORECASE)
                expanded_words.append(expanded_word)
            else:
                expanded_words.append(word)
        
        return ' '.join(expanded_words)
    
    def add_synonyms(self, text: str) -> List[str]:
        """为文本添加同义词变体"""
        variants = [text]
        text_lower = text.lower()
        
        for term, synonyms in self.medical_synonyms.items():
            if term in text_lower:
                for synonym in synonyms:
                    variant = text_lower.replace(term, synonym)
                    if variant != text_lower:
                        variants.append(variant)
        
        return list(set(variants))  # 去重
    
    def identify_organ_system(self, text: str) -> Optional[str]:
        """识别文本涉及的器官系统"""
        text_lower = text.lower()
        
        for system, keywords in self.organ_systems.items():
            for keyword in keywords:
                if keyword in text_lower:
                    return system
        
        return None
    
    def preprocess(self, text: str) -> Dict[str, Any]:
        """完整的医学文本预处理"""
        # 1. 基础清理
        cleaned_text = text.strip().lower()
        
        # 2. 展开缩写
        expanded_text = self.expand_abbreviations(text)
        
        # 3. 生成同义词变体
        variants = self.add_synonyms(expanded_text)
        
        # 4. 识别器官系统
        organ_system = self.identify_organ_system(expanded_text)
        
        # 5. 提取关键医学术语
        medical_terms = self._extract_medical_terms(expanded_text)
        
        return {
            'original': text,
            'cleaned': cleaned_text,
            'expanded': expanded_text,
            'variants': variants,
            'organ_system': organ_system,
            'medical_terms': medical_terms
        }
    
    def _extract_medical_terms(self, text: str) -> List[str]:
        """提取医学术语"""
        terms = []
        text_lower = text.lower()
        
        # 提取所有已知的医学术语
        all_terms = set()
        all_terms.update(self.medical_abbreviations.values())
        all_terms.update(self.medical_synonyms.keys())
        for synonyms in self.medical_synonyms.values():
            all_terms.update(synonyms)
        
        for term in all_terms:
            if term in text_lower:
                terms.append(term)
        
        return terms


class EnhancedRAG3DBSearchAdapter:
    """增强版RAG_3DB检索适配器"""
    
    def __init__(self, 
                 rag_db_type: str = 'uniform',
                 model_path: str = '/home/duojiechen/Central_Data/DataBase/models/sapbert',
                 base_index_path: str = '/home/duojiechen/projects/Rag_system/RAG_3DB/faiss_indexes'):
        """
        初始化增强版RAG_3DB检索适配器
        """
        self.rag_db_type = rag_db_type
        self.model_path = model_path
        self.base_index_path = base_index_path
        
        # 初始化预处理器
        self.preprocessor = MedicalTextPreprocessor()
        
        # 配置映射
        self.db_configs = {
            'uniform': {
                'index_path': f'{base_index_path}/rag_uniform_db/',
                'mongo_db': 'rag_uniform_db',
                'collection': 'sdu_collection',
                'description': 'Uniform Random Unit Database'
            },
            'report_context': {
                'index_path': f'{base_index_path}/rag_report_context_db/',
                'mongo_db': 'rag_report_context_db', 
                'collection': 'report_sdu_collection',
                'description': 'Report Context Database'
            },
            'sequential_block': {
                'index_path': f'{base_index_path}/rag_sequential_block_db/',
                'mongo_db': 'rag_sequential_block_db',
                'collection': 'sequential_sdu_collection', 
                'description': 'Sequential Block Database'
            }
        }
        
        # 初始化组件
        self.encoder = None
        self.faiss_index = None
        self.id_map = None
        self.mongo_client = None
        self.collection = None
        self.index_distance_mode = "ip"
        
        print(f"🚀 初始化增强版RAG_3DB检索适配器 - {self.db_configs[rag_db_type]['description']}")
        self._initialize()
        
    def _initialize(self):
        """初始化所有组件"""
        self._load_model()
        self._load_faiss_index()
        self._connect_mongodb()
        print("✅ 增强版RAG_3DB检索适配器初始化完成！")
    
    def _load_model(self):
        """加载SentenceTransformer模型"""
        try:
            print(f"📥 加载SapBERT模型: {self.model_path}")
            self.encoder = SentenceTransformer(self.model_path)
            print("✅ 模型加载成功")
        except Exception as e:
            raise Exception(f"模型加载失败: {e}")
    
    def _load_faiss_index(self):
        """加载Faiss索引"""
        try:
            config = self.db_configs[self.rag_db_type]
            index_path = config['index_path']
            
            # 优先加载余弦内积索引
            cosine_index_file = os.path.join(index_path, 'index_cosine.faiss')
            cosine_id_map_file = os.path.join(index_path, 'faiss_to_mongo_id_map_cosine.json')
            default_index_file = os.path.join(index_path, 'index.faiss')
            default_id_map_file = os.path.join(index_path, 'faiss_to_mongo_id_map.json')

            if os.path.exists(cosine_index_file) and os.path.exists(cosine_id_map_file):
                index_file = cosine_index_file
                id_map_file = cosine_id_map_file
                self.index_distance_mode = "ip"
            else:
                index_file = default_index_file
                id_map_file = default_id_map_file
                self.index_distance_mode = "l2"
            
            print(f"📥 加载Faiss索引: {index_file}")
            self.faiss_index = faiss.read_index(index_file)
            print(f"✅ Faiss索引加载成功，包含 {self.faiss_index.ntotal} 个向量")
            
            # 加载ID映射
            with open(id_map_file, 'r', encoding='utf-8') as f:
                self.id_map = json.load(f)
            print(f"✅ ID映射加载成功，包含 {len(self.id_map)} 个映射")
                
        except Exception as e:
            raise Exception(f"Faiss索引加载失败: {e}")
    
    def _connect_mongodb(self):
        """连接MongoDB"""
        try:
            config = self.db_configs[self.rag_db_type]
            mongo_uri = 'mongodb://localhost:27017/'
            
            print(f"🔗 连接MongoDB: {mongo_uri}")
            self.mongo_client = pymongo.MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
            
            # 测试连接
            self.mongo_client.server_info()
            
            db = self.mongo_client[config['mongo_db']]
            self.collection = db[config['collection']]
            
            doc_count = self.collection.count_documents({})
            print(f"✅ MongoDB连接成功，集合包含 {doc_count:,} 个文档")
            
        except Exception as e:
            raise Exception(f"MongoDB连接失败: {e}")
    
    def _multi_stage_search(self, symptom: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """多阶段搜索策略"""
        print(f"🔍 多阶段搜索: {symptom[:50]}...")
        
        # 阶段1: 预处理症状文本
        preprocessed = self.preprocessor.preprocess(symptom)
        print(f"  📝 预处理完成，生成 {len(preprocessed['variants'])} 个变体")
        
        # 阶段2: 粗排 - 使用多个查询变体进行搜索
        coarse_results = self._coarse_ranking(preprocessed, top_k * 3)  # 获取更多候选
        print(f"  🔍 粗排完成，获得 {len(coarse_results)} 个候选")
        
        # 阶段3: 精排 - 基于医学知识重排序
        refined_results = self._fine_ranking(coarse_results, preprocessed, top_k * 2)
        print(f"  🎯 精排完成，筛选出 {len(refined_results)} 个结果")
        
        # 阶段4: 质量过滤和多样性保证
        final_results = self._quality_filter_and_diversify(refined_results, top_k)
        print(f"  ✅ 最终获得 {len(final_results)} 个高质量结果")
        
        return final_results
    
    def _coarse_ranking(self, preprocessed: Dict[str, Any], top_k: int) -> List[Dict[str, Any]]:
        """粗排阶段：使用多个查询变体"""
        all_candidates = {}  # 使用字典避免重复
        
        # 搜索主查询
        main_results = self._vector_search(preprocessed['expanded'], top_k)
        for result in main_results:
            doc_id = result['document_id']
            if doc_id not in all_candidates or result['cosine_similarity'] > all_candidates[doc_id]['cosine_similarity']:
                all_candidates[doc_id] = result
        
        # 搜索同义词变体（权重稍低）
        for variant in preprocessed['variants'][:3]:  # 限制变体数量
            if variant != preprocessed['expanded']:
                variant_results = self._vector_search(variant, top_k // 2)
                for result in variant_results:
                    doc_id = result['document_id']
                    # 对变体结果稍微降权
                    result['cosine_similarity'] *= 0.9
                    if doc_id not in all_candidates or result['cosine_similarity'] > all_candidates[doc_id]['cosine_similarity']:
                        all_candidates[doc_id] = result
        
        # 按相似度排序
        candidates = list(all_candidates.values())
        candidates.sort(key=lambda x: x['cosine_similarity'], reverse=True)
        
        return candidates[:top_k]
    
    def _vector_search(self, query: str, top_k: int) -> List[Dict[str, Any]]:
        """基础向量搜索"""
        try:
            # 编码查询
            raw_query_vec = self.encoder.encode([query])
            raw_query_vec = raw_query_vec.astype('float32')
            norm_query_vec = raw_query_vec.copy()
            faiss.normalize_L2(norm_query_vec)

            # 根据索引类型选择搜索向量
            if self.index_distance_mode == "ip":
                search_vec = norm_query_vec
            else:
                search_vec = raw_query_vec

            # 搜索
            distances, indices = self.faiss_index.search(search_vec, top_k)
            
            # 构建结果
            results = []
            for j, (dist, idx) in enumerate(zip(distances[0], indices[0])):
                if idx == -1:
                    continue
                
                # 获取MongoDB文档ID
                if isinstance(self.id_map, list):
                    if 0 <= int(idx) < len(self.id_map):
                        mongo_id = self.id_map[int(idx)]
                    else:
                        continue
                elif isinstance(self.id_map, dict):
                    mongo_id = self.id_map.get(str(idx)) or self.id_map.get(int(idx))
                else:
                    continue
                
                if not mongo_id:
                    continue
                
                # 从MongoDB获取文档
                doc = self.collection.find_one({"_id": mongo_id})
                if not doc:
                    continue
                
                # 计算相似度
                cosine_similarity_value = None
                if self.index_distance_mode == "ip":
                    cosine_similarity_value = float(dist)
                else:
                    # 从MongoDB向量计算余弦相似度
                    try:
                        db_vec = np.array(doc.get('vector'), dtype=np.float32)
                        if db_vec.size > 0:
                            norm = np.linalg.norm(db_vec)
                            if norm > 0:
                                db_vec = db_vec / norm
                                cosine_similarity_value = float(np.dot(norm_query_vec[0], db_vec))
                    except Exception:
                        cosine_similarity_value = 1 / (1 + float(dist))  # 备用计算
                
                # 数值稳定性
                if cosine_similarity_value is not None:
                    cosine_similarity_value = max(-1.0, min(1.0, cosine_similarity_value))
                
                # 构建结果项
                result_item = {
                    'rank': j + 1,
                    'document_id': mongo_id,
                    'symptom': doc.get('s_symptom', ''),
                    'metadata': doc.get('metadata', {}),
                    'cosine_similarity': cosine_similarity_value or 0.0,
                    'source_info': {
                        'mongo_id': mongo_id,
                        'faiss_index': int(idx),
                        'database_type': self.rag_db_type
                    }
                }
                
                results.append(result_item)
            
            return results
            
        except Exception as e:
            print(f"    ❌ 向量搜索失败: {e}")
            return []
    
    def _fine_ranking(self, candidates: List[Dict[str, Any]], preprocessed: Dict[str, Any], top_k: int) -> List[Dict[str, Any]]:
        """精排阶段：基于医学知识重排序"""
        if not candidates:
            return []
        
        # 为每个候选结果计算医学相关性分数
        for candidate in candidates:
            medical_score = self._calculate_medical_relevance(candidate, preprocessed)
            # 结合向量相似度和医学相关性
            candidate['combined_score'] = (
                candidate['cosine_similarity'] * 0.7 + 
                medical_score * 0.3
            )
            candidate['medical_relevance'] = medical_score
        
        # 按综合分数重排序
        candidates.sort(key=lambda x: x['combined_score'], reverse=True)
        
        return candidates[:top_k]
    
    def _calculate_medical_relevance(self, candidate: Dict[str, Any], preprocessed: Dict[str, Any]) -> float:
        """计算医学相关性分数"""
        score = 0.0
        
        # 获取候选结果的医学信息
        metadata = candidate.get('metadata', {})
        u_unit_set = metadata.get('U_unit_set', [])
        
        if not u_unit_set:
            return 0.0
        
        # 器官系统匹配
        query_organ_system = preprocessed.get('organ_system')
        if query_organ_system:
            for unit in u_unit_set:
                u_unit = unit.get('u_unit', {})
                organ = u_unit.get('o_organ', {})
                organ_name = organ.get('organName', '').lower()
                
                # 检查器官系统是否匹配
                candidate_system = self.preprocessor.identify_organ_system(organ_name)
                if candidate_system == query_organ_system:
                    score += 0.4
                    break
        
        # 医学术语匹配
        query_terms = set(preprocessed.get('medical_terms', []))
        if query_terms:
            for unit in u_unit_set:
                u_unit = unit.get('u_unit', {})
                diagnosis = u_unit.get('d_diagnosis', '').lower()
                
                # 检查医学术语重叠
                candidate_terms = set(self.preprocessor._extract_medical_terms(diagnosis))
                overlap = len(query_terms & candidate_terms)
                if overlap > 0:
                    score += min(0.3, overlap * 0.1)
        
        # 诊断文本质量
        for unit in u_unit_set:
            u_unit = unit.get('u_unit', {})
            diagnosis = u_unit.get('d_diagnosis', '')
            
            # 诊断文本长度和详细程度
            if len(diagnosis) > 50:
                score += 0.1
            if any(keyword in diagnosis.lower() for keyword in ['diagnosis', 'condition', 'disease']):
                score += 0.1
        
        return min(1.0, score)
    
    def _quality_filter_and_diversify(self, candidates: List[Dict[str, Any]], top_k: int) -> List[Dict[str, Any]]:
        """质量过滤和多样性保证"""
        if not candidates:
            return []
        
        # 阶段1: 质量过滤
        quality_threshold = 0.3  # 最低质量阈值
        quality_candidates = [c for c in candidates if c['combined_score'] >= quality_threshold]
        
        if not quality_candidates:
            # 如果没有达到质量阈值的结果，返回原始结果
            return candidates[:top_k]
        
        # 阶段2: 多样性保证
        final_results = []
        used_organs = set()
        used_diagnoses = set()
        
        for candidate in quality_candidates:
            if len(final_results) >= top_k:
                break
            
            # 检查多样性
            metadata = candidate.get('metadata', {})
            u_unit_set = metadata.get('U_unit_set', [])
            
            is_diverse = True
            candidate_organs = set()
            candidate_diagnoses = set()
            
            for unit in u_unit_set:
                u_unit = unit.get('u_unit', {})
                organ = u_unit.get('o_organ', {})
                organ_name = organ.get('organName', '')
                diagnosis = u_unit.get('d_diagnosis', '')
                
                if organ_name:
                    candidate_organs.add(organ_name)
                if diagnosis:
                    # 使用诊断的前50个字符作为多样性检查
                    diagnosis_key = diagnosis[:50]
                    candidate_diagnoses.add(diagnosis_key)
            
            # 如果是前几个结果，或者提供了新的器官/诊断信息，则接受
            if (len(final_results) < 2 or  # 前两个结果总是接受
                not (candidate_organs & used_organs) or  # 新器官
                not (candidate_diagnoses & used_diagnoses)):  # 新诊断
                
                final_results.append(candidate)
                used_organs.update(candidate_organs)
                used_diagnoses.update(candidate_diagnoses)
        
        # 如果多样性过滤后结果不足，补充高质量结果
        if len(final_results) < top_k:
            for candidate in quality_candidates:
                if candidate not in final_results and len(final_results) < top_k:
                    final_results.append(candidate)
        
        return final_results
    
    def search_symptoms(self, symptoms: List[str], top_k: int = 3) -> Dict[str, List[Dict[str, Any]]]:
        """增强版症状搜索"""
        print(f"🔍 开始增强版检索 {len(symptoms)} 个症状 (top_k={top_k})")
        
        results = {}
        
        for i, symptom in enumerate(symptoms):
            print(f"\n--- 检索症状 {i+1}/{len(symptoms)}: {symptom[:50]}... ---")
            
            try:
                # 使用多阶段搜索
                similar_symptoms = self._multi_stage_search(symptom, top_k)
                results[symptom] = similar_symptoms
                
                print(f"✅ 症状检索完成，获得 {len(similar_symptoms)} 个高质量结果")
                
                # 显示结果质量信息
                if similar_symptoms:
                    avg_similarity = sum(r['cosine_similarity'] for r in similar_symptoms) / len(similar_symptoms)
                    avg_medical_relevance = sum(r.get('medical_relevance', 0) for r in similar_symptoms) / len(similar_symptoms)
                    print(f"  📊 平均相似度: {avg_similarity:.3f}, 平均医学相关性: {avg_medical_relevance:.3f}")
                
            except Exception as e:
                print(f"    ❌ 症状检索失败: {e}")
                results[symptom] = []
        
        return results
    
    def search_file_symptoms(self, file_path: str, top_k: int = 3, output_dir: str = None) -> str:
        """检索文件中所有症状并保存结果"""
        print(f"📄 处理文件: {file_path}")
        
        # 加载诊断文件
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                diagnostic_data = json.load(f)
        except Exception as e:
            raise Exception(f"文件加载失败: {e}")
        
        # 提取症状
        symptoms = []
        for item in diagnostic_data:
            if isinstance(item, dict) and 's_symptom' in item:
                symptom_text = item['s_symptom'].strip()
                if symptom_text:
                    symptoms.append(symptom_text)
        
        if not symptoms:
            raise Exception("文件中未找到有效症状")
        
        print(f"📋 提取到 {len(symptoms)} 个症状")
        
        # 使用增强版搜索
        search_results = self.search_symptoms(symptoms, top_k)
        
        # 生成输出文件名
        file_name = Path(file_path).stem
        report_id = file_name.replace('diagnostic_', '')
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if output_dir is None:
            output_dir = '/home/duojiechen/projects/Rag_system/Rag_Evaluate/Evaluate_output/rag_search_output'
        
        os.makedirs(output_dir, exist_ok=True)
        output_file = os.path.join(output_dir, f"report_{report_id}_enhanced_ragoutcome_{self.rag_db_type}_{timestamp}.jsonl")
        
        # 保存结果
        with open(output_file, 'w', encoding='utf-8') as f:
            for symptom, results in search_results.items():
                result_entry = {
                    'symptom': symptom,
                    'query': symptom,
                    'rag_results': results,
                    'database_type': self.rag_db_type,
                    'database_description': self.db_configs[self.rag_db_type]['description'],
                    'search_method': 'enhanced_multi_stage',
                    'top_k': top_k,
                    'timestamp': datetime.now().isoformat()
                }
                f.write(json.dumps(result_entry, ensure_ascii=False) + '\n')
        
        print(f"💾 增强版检索结果已保存: {output_file}")
        return output_file
    
    def close(self):
        """关闭连接"""
        if self.mongo_client:
            self.mongo_client.close()
            print("🔒 MongoDB连接已关闭")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="增强版RAG_3DB检索适配器")
    parser.add_argument("--file", required=True, help="诊断文件路径")
    parser.add_argument("--rag_db_type", default="uniform", 
                       choices=['uniform', 'report_context', 'sequential_block'],
                       help="RAG数据库类型")
    parser.add_argument("--top_k", type=int, default=3, help="返回top-k个相似症状")
    parser.add_argument("--output_dir", help="输出目录")
    
    args = parser.parse_args()
    
    try:
        # 初始化增强版适配器
        adapter = EnhancedRAG3DBSearchAdapter(rag_db_type=args.rag_db_type)
        
        # 检索文件症状
        output_file = adapter.search_file_symptoms(
            file_path=args.file,
            top_k=args.top_k,
            output_dir=args.output_dir
        )
        
        print(f"✅ 增强版检索完成！输出文件: {output_file}")
        
    except Exception as e:
        print(f"❌ 检索失败: {e}")
        sys.exit(1)
    finally:
        if 'adapter' in locals():
            adapter.close()


if __name__ == "__main__":
    main()
