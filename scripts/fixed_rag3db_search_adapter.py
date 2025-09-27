#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修复版RAG_3DB检索适配器 - 修复相似度计算错误

主要修复：
1. 正确的余弦相似度计算
2. 验证索引映射正确性
3. 添加详细的调试信息
4. 修复数据传递链路问题

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
from typing import List, Dict, Any, Tuple, Optional
from pathlib import Path
from datetime import datetime
from sentence_transformers import SentenceTransformer

# 添加RAG_3DB路径
sys.path.append('/home/duojiechen/projects/Rag_system/RAG_3DB/src')

class FixedRAG3DBSearchAdapter:
    """修复版RAG_3DB检索适配器"""
    
    def __init__(self, 
                 rag_db_type: str = 'uniform',
                 model_path: str = '/home/duojiechen/Central_Data/DataBase/models/sapbert',
                 base_index_path: str = '/home/duojiechen/projects/Rag_system/RAG_3DB/faiss_indexes',
                 debug: bool = True):
        """
        初始化修复版RAG_3DB检索适配器
        """
        self.rag_db_type = rag_db_type
        self.model_path = model_path
        self.base_index_path = base_index_path
        self.debug = debug
        
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
        self.index_distance_mode = "l2"  # 默认L2
        self.vectors_normalized = False  # 索引向量是否已归一化
        
        print(f"🔧 初始化修复版RAG_3DB检索适配器 - {self.db_configs[rag_db_type]['description']}")
        self._initialize()
        
    def _initialize(self):
        """初始化所有组件"""
        self._load_model()
        self._load_faiss_index()
        self._connect_mongodb()
        self._verify_index_mapping()
        print("✅ 修复版RAG_3DB检索适配器初始化完成！")
    
    def _load_model(self):
        """加载SentenceTransformer模型"""
        try:
            print(f"📥 加载SapBERT模型: {self.model_path}")
            self.encoder = SentenceTransformer(self.model_path)
            print("✅ 模型加载成功")
        except Exception as e:
            raise Exception(f"模型加载失败: {e}")
    
    def _load_faiss_index(self):
        """加载Faiss索引并确定距离模式"""
        try:
            config = self.db_configs[self.rag_db_type]
            index_path = config['index_path']
            
            # 检查可用的索引文件
            cosine_index_file = os.path.join(index_path, 'index_cosine.faiss')
            cosine_id_map_file = os.path.join(index_path, 'faiss_to_mongo_id_map_cosine.json')
            default_index_file = os.path.join(index_path, 'index.faiss')
            default_id_map_file = os.path.join(index_path, 'faiss_to_mongo_id_map.json')

            if os.path.exists(cosine_index_file) and os.path.exists(cosine_id_map_file):
                index_file = cosine_index_file
                id_map_file = cosine_id_map_file
                self.index_distance_mode = "ip"
                self.vectors_normalized = True
                print("🎯 使用余弦相似度索引 (内积)")
            else:
                index_file = default_index_file
                id_map_file = default_id_map_file
                self.index_distance_mode = "l2"
                self.vectors_normalized = False
                print("📏 使用L2距离索引")
            
            print(f"📥 加载Faiss索引: {index_file}")
            if not os.path.exists(index_file):
                raise FileNotFoundError(f"Faiss索引文件不存在: {index_file}")
                
            self.faiss_index = faiss.read_index(index_file)
            print(f"✅ Faiss索引加载成功，包含 {self.faiss_index.ntotal} 个向量")
            
            # 加载ID映射
            if not os.path.exists(id_map_file):
                raise FileNotFoundError(f"ID映射文件不存在: {id_map_file}")
                
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
    
    def _verify_index_mapping(self):
        """验证索引映射正确性"""
        print("🔍 验证索引映射正确性...")
        
        # 随机选择几个索引进行验证
        test_indices = [0, 100, 1000] if self.faiss_index.ntotal > 1000 else [0, min(100, self.faiss_index.ntotal-1)]
        
        for faiss_idx in test_indices:
            if faiss_idx >= self.faiss_index.ntotal:
                continue
                
            # 获取MongoDB ID
            if isinstance(self.id_map, list):
                if faiss_idx < len(self.id_map):
                    mongo_id = self.id_map[faiss_idx]
                else:
                    print(f"⚠️  Faiss索引 {faiss_idx} 超出ID映射范围")
                    continue
            elif isinstance(self.id_map, dict):
                mongo_id = self.id_map.get(str(faiss_idx))
                if not mongo_id:
                    print(f"⚠️  Faiss索引 {faiss_idx} 在ID映射中不存在")
                    continue
            else:
                print(f"❌ ID映射格式错误: {type(self.id_map)}")
                continue
            
            # 验证MongoDB文档存在
            doc = self.collection.find_one({"_id": mongo_id})
            if doc:
                symptom = doc.get('s_symptom', '')
                print(f"✅ 索引 {faiss_idx} → MongoDB {mongo_id} → '{symptom[:50]}...'")
            else:
                print(f"❌ 索引 {faiss_idx} → MongoDB {mongo_id} → 文档不存在!")
        
        print("✅ 索引映射验证完成")
    
    def _calculate_cosine_similarity(self, query_vec: np.ndarray, db_vec: np.ndarray) -> float:
        """正确计算余弦相似度"""
        try:
            # 确保向量是1D
            if query_vec.ndim > 1:
                query_vec = query_vec.flatten()
            if db_vec.ndim > 1:
                db_vec = db_vec.flatten()
            
            # 计算向量范数
            query_norm = np.linalg.norm(query_vec)
            db_norm = np.linalg.norm(db_vec)
            
            if query_norm == 0 or db_norm == 0:
                return 0.0
            
            # 计算余弦相似度
            cosine_sim = np.dot(query_vec, db_vec) / (query_norm * db_norm)
            
            # 数值稳定性：裁剪到[-1, 1]
            return float(np.clip(cosine_sim, -1.0, 1.0))
            
        except Exception as e:
            if self.debug:
                print(f"⚠️  余弦相似度计算失败: {e}")
            return 0.0
    
    def search_symptoms(self, symptoms: List[str], top_k: int = 3) -> Dict[str, List[Dict[str, Any]]]:
        """修复版症状搜索"""
        print(f"🔍 开始修复版检索 {len(symptoms)} 个症状 (top_k={top_k})")
        
        results = {}
        
        for i, symptom in enumerate(symptoms):
            print(f"\n--- 检索症状 {i+1}/{len(symptoms)}: {symptom[:50]}... ---")
            
            try:
                # 编码查询症状
                query_vector = self.encoder.encode([symptom])
                query_vector = query_vector.astype('float32')
                
                if self.debug:
                    print(f"🧮 查询向量形状: {query_vector.shape}")
                
                # 根据索引类型准备搜索向量
                if self.index_distance_mode == "ip":
                    # 内积索引：需要归一化查询向量
                    search_vector = query_vector.copy()
                    faiss.normalize_L2(search_vector)
                    if self.debug:
                        print("🎯 使用归一化向量进行内积搜索")
                else:
                    # L2索引：使用原始向量
                    search_vector = query_vector
                    if self.debug:
                        print("📏 使用原始向量进行L2搜索")
                
                # 执行Faiss搜索
                distances, indices = self.faiss_index.search(search_vector, top_k)
                
                if self.debug:
                    print(f"🔍 Faiss搜索结果: distances={distances[0][:3]}, indices={indices[0][:3]}")
                
                # 处理搜索结果
                similar_symptoms = []
                for j, (dist, idx) in enumerate(zip(distances[0], indices[0])):
                    if idx == -1:  # Faiss返回-1表示无效索引
                        continue
                    
                    # 获取MongoDB文档ID
                    if isinstance(self.id_map, list):
                        if 0 <= int(idx) < len(self.id_map):
                            mongo_id = self.id_map[int(idx)]
                        else:
                            if self.debug:
                                print(f"⚠️  索引 {idx} 超出范围")
                            continue
                    elif isinstance(self.id_map, dict):
                        mongo_id = self.id_map.get(str(idx)) or self.id_map.get(int(idx))
                    else:
                        if self.debug:
                            print(f"❌ ID映射格式错误")
                        continue
                    
                    if not mongo_id:
                        if self.debug:
                            print(f"⚠️  索引 {idx} 无对应MongoDB ID")
                        continue
                    
                    # 从MongoDB获取文档
                    doc = self.collection.find_one({"_id": mongo_id})
                    if not doc:
                        if self.debug:
                            print(f"⚠️  MongoDB文档 {mongo_id} 不存在")
                        continue
                    
                    # 计算正确的相似度
                    cosine_similarity = None
                    l2_distance = None
                    
                    if self.index_distance_mode == "ip":
                        # 内积索引：Faiss返回的就是余弦相似度
                        cosine_similarity = float(dist)
                        if self.debug:
                            print(f"📊 内积索引相似度: {cosine_similarity:.4f}")
                    else:
                        # L2索引：需要重新计算余弦相似度
                        l2_distance = float(dist)
                        
                        # 从MongoDB获取存储的向量
                        db_vector = doc.get('vector')
                        if db_vector and isinstance(db_vector, list):
                            db_vector = np.array(db_vector, dtype=np.float32)
                            cosine_similarity = self._calculate_cosine_similarity(
                                query_vector[0], db_vector
                            )
                            if self.debug:
                                print(f"📊 L2距离: {l2_distance:.4f}, 计算余弦相似度: {cosine_similarity:.4f}")
                        else:
                            # 备用：使用L2距离转换（不准确但总比没有好）
                            cosine_similarity = 1.0 / (1.0 + l2_distance)
                            if self.debug:
                                print(f"⚠️  使用L2距离转换: {cosine_similarity:.4f}")
                    
                    # 数值稳定性
                    if cosine_similarity is not None:
                        cosine_similarity = max(-1.0, min(1.0, cosine_similarity))
                    
                    # 获取症状文本和元数据
                    symptom_text = doc.get('s_symptom', '')
                    metadata = doc.get('metadata', {})
                    
                    # 构建结果项
                    result_item = {
                        'rank': j + 1,
                        'document_id': mongo_id,
                        'symptom': symptom_text,
                        'metadata': metadata,
                        'cosine_similarity': cosine_similarity or 0.0,
                        'source_info': {
                            'mongo_id': mongo_id,
                            'faiss_index': int(idx),
                            'database_type': self.rag_db_type,
                            'search_method': 'fixed_calculation'
                        }
                    }
                    
                    # 可选：添加L2距离信息
                    if l2_distance is not None:
                        result_item['l2_distance'] = l2_distance
                    
                    similar_symptoms.append(result_item)
                    
                    if self.debug:
                        print(f"✅ 结果 {j+1}: '{symptom_text[:30]}...' (相似度: {cosine_similarity:.4f})")
                
                results[symptom] = similar_symptoms
                print(f"✅ 症状检索完成，获得 {len(similar_symptoms)} 个结果")
                
            except Exception as e:
                print(f"❌ 症状检索失败: {e}")
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
        
        # 使用修复版搜索
        search_results = self.search_symptoms(symptoms, top_k)
        
        # 生成输出文件名
        file_name = Path(file_path).stem
        report_id = file_name.replace('diagnostic_', '')
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if output_dir is None:
            output_dir = '/home/duojiechen/projects/Rag_system/Rag_Evaluate/Evaluate_output/rag_search_output'
        
        os.makedirs(output_dir, exist_ok=True)
        output_file = os.path.join(output_dir, f"report_{report_id}_FIXED_ragoutcome_{self.rag_db_type}_{timestamp}.jsonl")
        
        # 保存结果
        with open(output_file, 'w', encoding='utf-8') as f:
            for symptom, results in search_results.items():
                result_entry = {
                    'symptom': symptom,
                    'query': symptom,
                    'rag_results': results,
                    'database_type': self.rag_db_type,
                    'database_description': self.db_configs[self.rag_db_type]['description'],
                    'search_method': 'FIXED_similarity_calculation',
                    'top_k': top_k,
                    'timestamp': datetime.now().isoformat()
                }
                f.write(json.dumps(result_entry, ensure_ascii=False) + '\n')
        
        print(f"💾 修复版检索结果已保存: {output_file}")
        return output_file
    
    def close(self):
        """关闭连接"""
        if self.mongo_client:
            self.mongo_client.close()
            print("🔒 MongoDB连接已关闭")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="修复版RAG_3DB检索适配器")
    parser.add_argument("--file", required=True, help="诊断文件路径")
    parser.add_argument("--rag_db_type", default="uniform", 
                       choices=['uniform', 'report_context', 'sequential_block'],
                       help="RAG数据库类型")
    parser.add_argument("--top_k", type=int, default=3, help="返回top-k个相似症状")
    parser.add_argument("--output_dir", help="输出目录")
    parser.add_argument("--debug", action="store_true", help="启用调试模式")
    
    args = parser.parse_args()
    
    try:
        # 初始化修复版适配器
        adapter = FixedRAG3DBSearchAdapter(
            rag_db_type=args.rag_db_type,
            debug=args.debug
        )
        
        # 检索文件症状
        output_file = adapter.search_file_symptoms(
            file_path=args.file,
            top_k=args.top_k,
            output_dir=args.output_dir
        )
        
        print(f"✅ 修复版检索完成！输出文件: {output_file}")
        
    except Exception as e:
        print(f"❌ 检索失败: {e}")
        sys.exit(1)
    finally:
        if 'adapter' in locals():
            adapter.close()


if __name__ == "__main__":
    main()
