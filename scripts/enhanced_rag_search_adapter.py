#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
增强版RAG搜索适配器 - 实现多种搜索强化策略

主要增强功能：
1. 查询扩展和重写
2. 多层次检索策略
3. 结果重排序和过滤
4. 自适应Top-K调整
5. 语义多样性增强

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
from collections import defaultdict
import random

# 添加RAG_3DB路径
sys.path.append('/home/duojiechen/projects/Rag_system/RAG_3DB/src')

class EnhancedRAGSearchAdapter:
    """增强版RAG搜索适配器"""
    
    def __init__(self, 
                 rag_db_type: str = 'uniform',
                 model_path: str = '/home/duojiechen/Central_Data/DataBase/models/sapbert',
                 base_index_path: str = '/home/duojiechen/projects/Rag_system/RAG_3DB/faiss_indexes',
                 enhancement_config: Dict[str, Any] = None,
                 debug: bool = True):
        """
        初始化增强版RAG搜索适配器
        """
        self.rag_db_type = rag_db_type
        self.model_path = model_path
        self.base_index_path = base_index_path
        self.debug = debug
        
        # 增强配置
        self.config = enhancement_config or self._get_default_config()
        
        # 基础组件
        self.model = None
        self.faiss_index = None
        self.id_map = None
        self.collection = None
        self.index_distance_mode = None
        
        # 查询扩展词典
        self.symptom_synonyms = self._load_symptom_synonyms()
        self.medical_abbreviations = self._load_medical_abbreviations()
        
        # 初始化
        self._initialize_components()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """获取默认增强配置"""
        return {
            'query_expansion': {
                'enabled': True,
                'synonym_expansion': True,
                'abbreviation_expansion': True,
                'medical_term_expansion': True,
                'max_expansions': 3
            },
            'retrieval_strategy': {
                'multi_query': True,
                'adaptive_top_k': True,
                'base_top_k': 5,
                'max_top_k': 15,
                'similarity_threshold': 0.6
            },
            'result_enhancement': {
                'diversity_filtering': True,
                'semantic_reranking': True,
                'relevance_scoring': True,
                'max_results': 3
            },
            'quality_control': {
                'min_similarity': 0.5,
                'max_duplicate_ratio': 0.3,
                'content_length_filter': True
            }
        }
    
    def _load_symptom_synonyms(self) -> Dict[str, List[str]]:
        """加载症状同义词词典"""
        # 这里可以从外部文件加载，现在使用内置词典
        return {
            'headache': ['head pain', 'cephalgia', 'cranial pain', 'migraine'],
            'nausea': ['feeling sick', 'queasiness', 'stomach upset'],
            'vomiting': ['emesis', 'throwing up', 'regurgitation'],
            'dyspnea': ['shortness of breath', 'breathing difficulty', 'breathlessness'],
            'chest pain': ['thoracic pain', 'chest discomfort', 'precordial pain'],
            'abdominal pain': ['stomach pain', 'belly pain', 'gastric pain'],
            'fatigue': ['tiredness', 'exhaustion', 'weakness'],
            'dizziness': ['vertigo', 'lightheadedness', 'giddiness'],
            'falls': ['falling', 'drop attacks', 'balance problems'],
            'ataxia': ['coordination problems', 'unsteady gait', 'balance disorder']
        }
    
    def _load_medical_abbreviations(self) -> Dict[str, str]:
        """加载医学缩写词典"""
        return {
            'sob': 'shortness of breath',
            'cp': 'chest pain',
            'abd': 'abdominal',
            'ha': 'headache',
            'n/v': 'nausea and vomiting',
            'doe': 'dyspnea on exertion',
            'pnd': 'paroxysmal nocturnal dyspnea',
            'cad': 'coronary artery disease',
            'chf': 'congestive heart failure',
            'copd': 'chronic obstructive pulmonary disease',
            'dm': 'diabetes mellitus',
            'htn': 'hypertension',
            'mi': 'myocardial infarction',
            'cva': 'cerebrovascular accident',
            'tia': 'transient ischemic attack'
        }
    
    def _initialize_components(self):
        """初始化所有组件"""
        if self.debug:
            print("🔧 初始化增强版RAG搜索适配器")
        
        # 加载SapBERT模型
        if self.debug:
            print(f"📥 加载SapBERT模型: {self.model_path}")
        self.model = SentenceTransformer(self.model_path)
        if self.debug:
            print("✅ 模型加载成功")
        
        # 设置索引路径
        index_dir = Path(self.base_index_path) / f"rag_{self.rag_db_type}_db"
        
        # 加载Faiss索引
        index_path = index_dir / "index_cosine.faiss"
        if self.debug:
            print(f"📥 加载Faiss索引: {index_path}")
        self.faiss_index = faiss.read_index(str(index_path))
        self.index_distance_mode = "ip"  # 余弦相似度索引
        if self.debug:
            print(f"✅ Faiss索引加载成功，包含 {self.faiss_index.ntotal} 个向量")
        
        # 加载ID映射
        id_map_path = index_dir / "faiss_to_mongo_id_map_cosine.json"
        with open(id_map_path, 'r', encoding='utf-8') as f:
            self.id_map = json.load(f)
        if self.debug:
            print(f"✅ ID映射加载成功，包含 {len(self.id_map)} 个映射")
        
        # 连接MongoDB
        if self.debug:
            print("🔗 连接MongoDB: mongodb://localhost:27017/")
        client = pymongo.MongoClient("mongodb://localhost:27017/")
        db = client["rag_uniform_db"]
        self.collection = db["sdu_collection"]
        if self.debug:
            doc_count = self.collection.count_documents({})
            print(f"✅ MongoDB连接成功，集合包含 {doc_count:,} 个文档")
        
        if self.debug:
            print("✅ 增强版RAG搜索适配器初始化完成！")
    
    def _expand_query(self, query: str) -> List[str]:
        """查询扩展"""
        if not self.config['query_expansion']['enabled']:
            return [query]
        
        expanded_queries = [query]
        query_lower = query.lower()
        
        # 同义词扩展
        if self.config['query_expansion']['synonym_expansion']:
            for term, synonyms in self.symptom_synonyms.items():
                if term in query_lower:
                    for synonym in synonyms[:2]:  # 限制数量
                        expanded_query = query_lower.replace(term, synonym)
                        if expanded_query != query_lower:
                            expanded_queries.append(expanded_query)
        
        # 缩写扩展
        if self.config['query_expansion']['abbreviation_expansion']:
            for abbr, full_form in self.medical_abbreviations.items():
                if abbr in query_lower:
                    expanded_query = query_lower.replace(abbr, full_form)
                    if expanded_query != query_lower:
                        expanded_queries.append(expanded_query)
        
        # 医学术语扩展
        if self.config['query_expansion']['medical_term_expansion']:
            expanded_queries.extend(self._generate_medical_variants(query))
        
        # 限制扩展数量
        max_expansions = self.config['query_expansion']['max_expansions']
        return expanded_queries[:max_expansions + 1]
    
    def _generate_medical_variants(self, query: str) -> List[str]:
        """生成医学术语变体"""
        variants = []
        
        # 添加常见医学后缀
        medical_suffixes = ['pain', 'ache', 'discomfort', 'syndrome', 'disorder']
        for suffix in medical_suffixes:
            if suffix not in query.lower():
                variants.append(f"{query} {suffix}")
        
        # 添加解剖学相关词汇
        anatomical_terms = ['left', 'right', 'bilateral', 'chronic', 'acute', 'severe']
        for term in anatomical_terms:
            if term not in query.lower():
                variants.append(f"{term} {query}")
        
        return variants[:2]  # 限制数量
    
    def _multi_query_search(self, queries: List[str], top_k: int) -> List[Dict[str, Any]]:
        """多查询检索"""
        all_results = []
        seen_ids = set()
        
        for query in queries:
            # 编码查询
            query_vector = self.model.encode([query], convert_to_numpy=True)
            query_vector = query_vector.astype(np.float32)
            
            # 归一化（用于余弦相似度）
            if self.index_distance_mode == "ip":
                query_vector = query_vector / np.linalg.norm(query_vector, axis=1, keepdims=True)
            
            # 执行搜索
            distances, indices = self.faiss_index.search(query_vector, top_k * 2)  # 搜索更多结果
            
            # 处理结果
            for dist, idx in zip(distances[0], indices[0]):
                if idx == -1 or idx in seen_ids:
                    continue
                
                seen_ids.add(idx)
                
                # 获取MongoDB文档
                if isinstance(self.id_map, list):
                    if 0 <= int(idx) < len(self.id_map):
                        mongo_id = self.id_map[int(idx)]
                    else:
                        continue
                else:
                    continue
                
                doc = self.collection.find_one({"_id": mongo_id})
                if not doc:
                    continue
                
                # 计算相似度
                cosine_similarity = float(dist) if self.index_distance_mode == "ip" else None
                
                if cosine_similarity and cosine_similarity >= self.config['retrieval_strategy']['similarity_threshold']:
                    result_item = {
                        "rank": len(all_results) + 1,
                        "document_id": mongo_id,
                        "symptom": doc.get('s_symptom', ''),
                        "metadata": doc.get('metadata', {}),
                        "cosine_similarity": cosine_similarity,
                        "source_info": {
                            "mongo_id": mongo_id,
                            "faiss_index": int(idx),
                            "database_type": self.rag_db_type,
                            "search_method": "enhanced_multi_query",
                            "query_variant": query
                        }
                    }
                    all_results.append(result_item)
        
        return all_results
    
    def _semantic_reranking(self, results: List[Dict[str, Any]], original_query: str) -> List[Dict[str, Any]]:
        """语义重排序"""
        if not self.config['result_enhancement']['semantic_reranking'] or len(results) <= 1:
            return results
        
        # 计算与原始查询的语义相似度
        original_embedding = self.model.encode([original_query], convert_to_numpy=True)[0]
        
        for result in results:
            symptom_text = result.get('symptom', '')
            if symptom_text:
                symptom_embedding = self.model.encode([symptom_text], convert_to_numpy=True)[0]
                
                # 计算语义相似度
                semantic_sim = np.dot(original_embedding, symptom_embedding) / (
                    np.linalg.norm(original_embedding) * np.linalg.norm(symptom_embedding)
                )
                result['semantic_similarity'] = float(semantic_sim)
            else:
                result['semantic_similarity'] = 0.0
        
        # 综合排序（原始相似度 + 语义相似度）
        for result in results:
            combined_score = (
                result.get('cosine_similarity', 0) * 0.7 + 
                result.get('semantic_similarity', 0) * 0.3
            )
            result['combined_score'] = combined_score
        
        return sorted(results, key=lambda x: x.get('combined_score', 0), reverse=True)
    
    def _diversity_filtering(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """多样性过滤"""
        if not self.config['result_enhancement']['diversity_filtering']:
            return results
        
        filtered_results = []
        seen_symptoms = set()
        
        for result in results:
            symptom = result.get('symptom', '').lower().strip()
            
            # 检查是否过于相似
            is_duplicate = False
            for seen in seen_symptoms:
                if self._calculate_text_similarity(symptom, seen) > 0.8:
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                filtered_results.append(result)
                seen_symptoms.add(symptom)
        
        return filtered_results
    
    def _calculate_text_similarity(self, text1: str, text2: str) -> float:
        """计算文本相似度"""
        if not text1 or not text2:
            return 0.0
        
        # 简单的词汇重叠相似度
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))
        
        return intersection / union if union > 0 else 0.0
    
    def _adaptive_top_k(self, query: str) -> int:
        """自适应Top-K调整"""
        if not self.config['retrieval_strategy']['adaptive_top_k']:
            return self.config['retrieval_strategy']['base_top_k']
        
        base_k = self.config['retrieval_strategy']['base_top_k']
        max_k = self.config['retrieval_strategy']['max_top_k']
        
        # 根据查询复杂度调整
        query_complexity = len(query.split())
        
        if query_complexity <= 2:
            return base_k
        elif query_complexity <= 5:
            return min(base_k + 2, max_k)
        else:
            return max_k
    
    def search_symptoms(self, symptoms: List[str], top_k: int = None) -> Dict[str, List[Dict[str, Any]]]:
        """增强版症状搜索"""
        if self.debug:
            print(f"🔍 开始增强版检索 {len(symptoms)} 个症状")
        
        results = {}
        
        for i, symptom in enumerate(symptoms):
            if self.debug:
                print(f"\n--- 检索症状 {i+1}/{len(symptoms)}: {symptom[:50]}... ---")
            
            # 自适应Top-K
            adaptive_k = top_k or self._adaptive_top_k(symptom)
            
            # 查询扩展
            expanded_queries = self._expand_query(symptom)
            if self.debug and len(expanded_queries) > 1:
                print(f"🔄 查询扩展: {len(expanded_queries)} 个变体")
            
            # 多查询检索
            raw_results = self._multi_query_search(expanded_queries, adaptive_k)
            
            # 语义重排序
            reranked_results = self._semantic_reranking(raw_results, symptom)
            
            # 多样性过滤
            diverse_results = self._diversity_filtering(reranked_results)
            
            # 最终结果选择
            max_results = self.config['result_enhancement']['max_results']
            final_results = diverse_results[:max_results]
            
            # 重新编号
            for j, result in enumerate(final_results):
                result['rank'] = j + 1
            
            results[symptom] = final_results
            
            if self.debug:
                print(f"✅ 症状检索完成，获得 {len(final_results)} 个增强结果")
        
        return results
    
    def save_results(self, results: Dict[str, List[Dict[str, Any]]], output_file: str):
        """保存检索结果"""
        output_data = []
        
        for symptom, symptom_results in results.items():
            result_entry = {
                "symptom": symptom,
                "query": symptom,
                "rag_results": symptom_results,
                "database_type": self.rag_db_type,
                "database_description": "Uniform Random Unit Database (Enhanced)",
                "search_method": "ENHANCED_multi_query_semantic_reranking",
                "enhancement_config": self.config,
                "top_k": len(symptom_results),
                "timestamp": datetime.now().isoformat()
            }
            output_data.append(result_entry)
        
        # 保存为JSONL格式
        with open(output_file, 'w', encoding='utf-8') as f:
            for entry in output_data:
                f.write(json.dumps(entry, ensure_ascii=False) + '\n')
        
        if self.debug:
            print(f"💾 增强版检索结果已保存: {output_file}")

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="增强版RAG_3DB检索适配器")
    parser.add_argument("--file", required=True, help="输入的诊断文件路径")
    parser.add_argument("--top_k", type=int, default=3, help="返回的top-k结果数量")
    parser.add_argument("--output_dir", required=True, help="输出目录")
    parser.add_argument("--rag_db_type", default="uniform", help="RAG数据库类型")
    
    args = parser.parse_args()
    
    # 增强配置
    enhancement_config = {
        'query_expansion': {
            'enabled': True,
            'synonym_expansion': True,
            'abbreviation_expansion': True,
            'medical_term_expansion': True,
            'max_expansions': 3
        },
        'retrieval_strategy': {
            'multi_query': True,
            'adaptive_top_k': True,
            'base_top_k': args.top_k,
            'max_top_k': args.top_k * 3,
            'similarity_threshold': 0.5
        },
        'result_enhancement': {
            'diversity_filtering': True,
            'semantic_reranking': True,
            'relevance_scoring': True,
            'max_results': args.top_k
        }
    }
    
    # 初始化增强版适配器
    adapter = EnhancedRAGSearchAdapter(
        rag_db_type=args.rag_db_type,
        enhancement_config=enhancement_config,
        debug=True
    )
    
    # 读取输入文件
    with open(args.file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # 提取症状
    symptoms = []
    if isinstance(data, list):
        for item in data:
            if isinstance(item, dict) and 's_symptom' in item:
                symptoms.append(item['s_symptom'])
    
    print(f"📋 提取到 {len(symptoms)} 个症状")
    
    # 执行增强检索
    results = adapter.search_symptoms(symptoms, args.top_k)
    
    # 保存结果
    input_filename = Path(args.file).stem
    output_filename = f"{input_filename}_ENHANCED_ragoutcome_{args.rag_db_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jsonl"
    output_path = Path(args.output_dir) / output_filename
    
    adapter.save_results(results, str(output_path))
    
    print(f"✅ 增强版检索完成！输出文件: {output_path}")

if __name__ == "__main__":
    main()
