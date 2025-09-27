#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RAG_3DB检索适配器 - 连接RAG_3DB系统与Rag_Evaluate系统

功能：
1. 支持三种RAG数据库的检索：Uniform Random Unit, Report Context, Sequential Block
2. 与Rag_Evaluate系统兼容的输出格式
3. 自动选择最佳的RAG数据库
4. 支持批量检索和缓存

作者: AI Assistant
日期: 2025-09-23
"""

import os
import sys
import json
import faiss
import numpy as np
import pymongo
import argparse
from typing import List, Dict, Any, Tuple, Optional
from pathlib import Path
from datetime import datetime
from sentence_transformers import SentenceTransformer

# 添加RAG_3DB路径
sys.path.append('/home/duojiechen/projects/Rag_system/RAG_3DB/src')

class RAG3DBSearchAdapter:
    """RAG_3DB检索适配器类"""
    
    def __init__(self, 
                 rag_db_type: str = 'uniform',
                 model_path: str = '/home/duojiechen/Central_Data/DataBase/models/sapbert',
                 base_index_path: str = '/home/duojiechen/projects/Rag_system/RAG_3DB/faiss_indexes'):
        """
        初始化RAG_3DB检索适配器
        
        Args:
            rag_db_type: RAG数据库类型 ('uniform', 'report_context', 'sequential_block')
            model_path: SapBERT模型路径
            base_index_path: Faiss索引基础路径
        """
        self.rag_db_type = rag_db_type
        self.model_path = model_path
        self.base_index_path = base_index_path
        
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
        self.index_distance_mode = "ip"  # ip or l2
        self.base_vectors_normalized: bool | None = None
        
        print(f"🚀 初始化RAG_3DB检索适配器 - {self.db_configs[rag_db_type]['description']}")
        self._initialize()
        
    def _initialize(self):
        """初始化所有组件"""
        self._load_model()
        self._load_faiss_index()
        self._connect_mongodb()
        print("✅ RAG_3DB检索适配器初始化完成！")
    
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
            
            # 优先加载余弦内积索引（若存在）
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
                # 从元数据推断距离模式
                metadata_file = os.path.join(index_path, 'index_metadata.json')
                if os.path.exists(metadata_file):
                    try:
                        with open(metadata_file, 'r', encoding='utf-8') as mf:
                            meta = json.load(mf)
                            idx_type = (meta.get('index_type') or '').lower()
                            if 'l2' in idx_type:
                                self.index_distance_mode = "l2"
                            elif 'ip' in idx_type:
                                self.index_distance_mode = "ip"
                    except Exception:
                        pass
            print(f"📥 加载Faiss索引: {index_file}")
            
            if not os.path.exists(index_file):
                raise FileNotFoundError(f"Faiss索引文件不存在: {index_file}")
                
            self.faiss_index = faiss.read_index(index_file)
            print(f"✅ Faiss索引加载成功，包含 {self.faiss_index.ntotal} 个向量")
            
            # 加载ID映射（根据选择的索引对应映射文件）
            if os.path.exists(id_map_file):
                with open(id_map_file, 'r', encoding='utf-8') as f:
                    self.id_map = json.load(f)
                print(f"✅ ID映射加载成功，包含 {len(self.id_map)} 个映射")
            else:
                raise FileNotFoundError(f"ID映射文件不存在: {id_map_file}")
                
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
    
    def search_symptoms(self, symptoms: List[str], top_k: int = 3) -> Dict[str, List[Dict[str, Any]]]:
        """
        检索症状的相似症状
        
        Args:
            symptoms: 症状列表
            top_k: 返回top-k个相似症状
            
        Returns:
            症状检索结果字典
        """
        print(f"🔍 开始检索 {len(symptoms)} 个症状 (top_k={top_k})")
        
        results = {}
        
        for i, symptom in enumerate(symptoms):
            print(f"  检索症状 {i+1}/{len(symptoms)}: {symptom[:50]}...")
            
            try:
                # 编码症状（保留原始与归一化两份）
                raw_query_vec = self.encoder.encode([symptom])
                raw_query_vec = raw_query_vec.astype('float32')
                norm_query_vec = raw_query_vec.copy()
                faiss.normalize_L2(norm_query_vec)

                # 根据索引类型选择检索用向量
                if self.index_distance_mode == "ip":
                    search_vec = norm_query_vec
                else:  # l2
                    search_vec = raw_query_vec

                # 搜索相似向量
                distances, indices = self.faiss_index.search(search_vec, top_k)
                
                # 获取MongoDB文档
                similar_symptoms = []
                for j, (dist, idx) in enumerate(zip(distances[0], indices[0])):
                    if idx == -1:  # Faiss返回-1表示无效索引
                        continue
                    l2_distance_value: float | None = None
                    cosine_similarity_value: float | None = None
                    # 计算相似度：
                    # - L2 索引：提供 l2_distance，并使用Mongo向量计算余弦相似度
                    # - IP 索引（归一化向量）：Faiss返回的即为余弦相似度
                    if self.index_distance_mode == "l2":
                        l2_distance_value = float(dist)
                    else:
                        cosine_similarity_value = float(dist)
                        
                    # 获取MongoDB文档ID（兼容列表或字典两种映射格式）
                    if isinstance(self.id_map, list):
                        # 列表情况下，索引即为映射位置
                        if 0 <= int(idx) < len(self.id_map):
                            mongo_id = self.id_map[int(idx)]
                        else:
                            mongo_id = None
                    elif isinstance(self.id_map, dict):
                        mongo_id = self.id_map.get(str(idx)) or self.id_map.get(int(idx))
                    else:
                        mongo_id = None
                    if not mongo_id:
                        continue
                    
                    # 从MongoDB获取文档
                    doc = self.collection.find_one({"_id": mongo_id})
                    if not doc:
                        continue
                    
                    # 处理不同的文档结构
                    symptom_text = ""
                    diagnosis_units = []
                    
                    if isinstance(doc, dict):
                        # 尝试不同的字段名
                        symptom_text = doc.get('symptom_text', '') or doc.get('s_symptom', '')
                        diagnosis_units = doc.get('diagnosis_units', []) or doc.get('U_unit_set', [])
                        
                        # 如果diagnosis_units是列表，提取诊断信息
                        if isinstance(diagnosis_units, list) and diagnosis_units:
                            # 如果是字典列表，提取诊断文本
                            processed_units = []
                            for unit in diagnosis_units:
                                if isinstance(unit, dict):
                                    diagnosis = unit.get('diagnosis', '') or unit.get('U_unit', '')
                                    if diagnosis:
                                        processed_units.append(diagnosis)
                                elif isinstance(unit, str):
                                    processed_units.append(unit)
                            diagnosis_units = processed_units
                    
                    # 余弦相似度（当索引为L2时需要从Mongo向量计算）
                    if cosine_similarity_value is None:
                        try:
                            db_vec = np.array(doc.get('vector'), dtype=np.float32)
                            if db_vec.size > 0:
                                # 归一化Mongo向量
                                norm = np.linalg.norm(db_vec)
                                if norm > 0:
                                    db_vec = db_vec / norm
                                    # 使用归一化的查询向量
                                    cosine_similarity_value = float(np.dot(norm_query_vec[0], db_vec))
                        except Exception:
                            pass

                    # 数值稳定：将余弦相似度裁剪到[-1, 1]
                    if isinstance(cosine_similarity_value, float):
                        if cosine_similarity_value > 1.0:
                            cosine_similarity_value = 1.0
                        elif cosine_similarity_value < -1.0:
                            cosine_similarity_value = -1.0

                    # 优先使用 s_symptom 显示症状文本
                    display_symptom = doc.get('s_symptom', '') or doc.get('symptom_text', '') or symptom_text

                    # 按RAG_Search_Fixed风格组织返回字段
                    result_item = {
                        'rank': j + 1,
                        'document_id': mongo_id,
                        'symptom': display_symptom,
                        'metadata': doc.get('metadata', {}),
                    }
                    if cosine_similarity_value is not None:
                        result_item['cosine_similarity'] = cosine_similarity_value
                    if l2_distance_value is not None:
                        result_item['l2_distance'] = l2_distance_value

                    # 附带源信息
                    result_item['source_info'] = {
                        'mongo_id': mongo_id,
                        'faiss_index': int(idx),
                        'database_type': self.rag_db_type
                    }

                    similar_symptoms.append(result_item)
                
                results[symptom] = similar_symptoms
                print(f"    找到 {len(similar_symptoms)} 个相似症状")
                
            except Exception as e:
                print(f"    ❌ 症状检索失败: {e}")
                results[symptom] = []
        
        return results
    
    def search_file_symptoms(self, file_path: str, top_k: int = 3, output_dir: str = None) -> str:
        """
        检索文件中所有症状并保存结果（兼容Rag_Evaluate格式）
        
        Args:
            file_path: 诊断文件路径
            top_k: 返回top-k个相似症状
            output_dir: 输出目录
            
        Returns:
            输出文件路径
        """
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
        
        # 检索症状
        search_results = self.search_symptoms(symptoms, top_k)
        
        # 生成输出文件名（兼容Rag_Evaluate格式）
        file_name = Path(file_path).stem  # 例如: diagnostic_4000
        report_id = file_name.replace('diagnostic_', '')
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if output_dir is None:
            output_dir = '/home/duojiechen/projects/Rag_system/Rag_Evaluate/Evaluate_output/rag_search_output'
        
        # 确保输出目录不会重复创建子目录
        if output_dir.endswith('/rag_search_output/rag_search_output'):
            output_dir = output_dir.replace('/rag_search_output/rag_search_output', '/rag_search_output')
        
        os.makedirs(output_dir, exist_ok=True)
        output_file = os.path.join(output_dir, f"report_{report_id}_ragoutcome_{self.rag_db_type}_{timestamp}.jsonl")
        
        # 保存结果（JSONL格式，兼容Rag_Evaluate）
        with open(output_file, 'w', encoding='utf-8') as f:
            for symptom, results in search_results.items():
                result_entry = {
                    'symptom': symptom,
                    'query': symptom,
                    'rag_results': results,
                    'database_type': self.rag_db_type,
                    'database_description': self.db_configs[self.rag_db_type]['description'],
                    'top_k': top_k,
                    'timestamp': datetime.now().isoformat()
                }
                f.write(json.dumps(result_entry, ensure_ascii=False) + '\n')
        
        print(f"💾 检索结果已保存: {output_file}")
        return output_file
    
    def close(self):
        """关闭连接"""
        if self.mongo_client:
            self.mongo_client.close()
            print("🔒 MongoDB连接已关闭")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="RAG_3DB检索适配器")
    parser.add_argument("--file", required=True, help="诊断文件路径")
    parser.add_argument("--rag_db_type", default="uniform", 
                       choices=['uniform', 'report_context', 'sequential_block'],
                       help="RAG数据库类型")
    parser.add_argument("--top_k", type=int, default=3, help="返回top-k个相似症状")
    parser.add_argument("--output_dir", help="输出目录")
    
    args = parser.parse_args()
    
    try:
        # 初始化适配器
        adapter = RAG3DBSearchAdapter(rag_db_type=args.rag_db_type)
        
        # 检索文件症状
        output_file = adapter.search_file_symptoms(
            file_path=args.file,
            top_k=args.top_k,
            output_dir=args.output_dir
        )
        
        print(f"✅ 检索完成！输出文件: {output_file}")
        
    except Exception as e:
        print(f"❌ 检索失败: {e}")
        sys.exit(1)
    finally:
        if 'adapter' in locals():
            adapter.close()


if __name__ == "__main__":
    main()
