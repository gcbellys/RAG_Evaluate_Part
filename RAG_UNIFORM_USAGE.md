# RAG Uniform数据库评估系统使用指南

## 🎯 系统概述

本系统专门针对**Uniform Random Unit Database**进行RAG（检索增强生成）评估，使用修复后的高质量Faiss索引。

### ✨ 特点
- ✅ **修复后的索引**：使用正确的余弦相似度计算
- ✅ **高质量搜索**：IndexFlatIP + 向量归一化
- ✅ **专用流程**：针对Uniform数据库优化
- ✅ **清晰输出**：结果保存在 `Evaluate_output_uniform/` 目录

## 🚀 快速开始

### **1. 环境准备**
```bash
# 激活环境
conda activate RAG_ws

# 确保在正确目录
cd /home/duojiechen/projects/Rag_system/Rag_Evaluate
```

### **2. 单个报告测试**
```bash
# 测试单个报告（推荐先运行）
python workflows/rag_uniform_full_pipeline.py 43001
```

### **3. 批量评估**
```bash

# 评估报告范围 43001-43010（使用默认config_cn.yaml）
python workflows/rag_uniform_full_pipeline.py 43001 43010

# 使用更高的top_k
python workflows/rag_uniform_full_pipeline.py 43001 43010 --top_k 5

# 指定其他配置文件
python workflows/rag_uniform_full_pipeline.py 43001 43010 --config config/config_openai.yaml
```

## 📊 运行流程

### **Step 1: RAG检索阶段**
- 使用修复后的Faiss索引：`/home/duojiechen/projects/Rag_system/RAG_3DB/faiss_indexes/rag_uniform_db`
- 对每个诊断报告提取症状并进行RAG检索
- 生成RAG缓存文件到：`Evaluate_output_uniform/rag_search_output/`

### **Step 2: RAG增强评估阶段**
- 使用RAG检索结果增强LLM提示
- 生成RAG增强的评估结果
- 与基础评估结果进行对比

### **Step 3: 报告生成**
- 生成详细的评估总结报告
- 包含技术细节和性能指标

## 📁 输出结构

```
Evaluate_output_uniform/
├── rag_search_output/          # RAG检索缓存
│   ├── report_43001_ragoutcome_uniform_*.jsonl
│   └── report_43002_ragoutcome_uniform_*.jsonl
├── baseline_results/           # 基础评估结果
├── rerun_with_rag/            # RAG增强评估结果
├── rerun_comparisons/         # 对比分析结果
├── tokens/                    # Token使用统计
└── rag_uniform_evaluation_summary_*.json  # 总结报告
```

## ⚙️ 配置文件

### **默认配置：config_cn.yaml**
系统默认使用 `config/config_cn.yaml`，包含：
- **API配置**：Moonshot、DeepSeek等中文API
- **路径配置**：输入输出路径设置
- **评估配置**：批量大小、超时时间等
- **评估指标**：准确性、相关性、完整性、一致性

### **其他配置选项**
```bash
# 使用OpenAI配置
python workflows/rag_uniform_full_pipeline.py 43001 --config config/config_openai.yaml

# 使用RAG_3DB配置
python workflows/rag_uniform_full_pipeline.py 43001 --config config/config_rag3db.yaml
```

## 🔍 技术细节

### **索引信息**
- **索引类型**：IndexFlatIP（内积索引，用于余弦相似度）
- **向量维度**：768
- **总向量数**：43,000
- **相似度计算**：余弦相似度（修复后）
- **模型**：SapBERT (cambridgeltl/SapBERT-from-PubMedBERT-fulltext)

### **修复内容**
1. ✅ 向量归一化：存储时归一化为单位向量
2. ✅ 索引类型：使用IndexFlatIP而不是IndexFlatL2
3. ✅ 文件名匹配：正确的映射文件名
4. ✅ 相似度计算：准确的余弦相似度

## 📈 性能验证

修复后的系统性能：
- **存储向量 vs 实时编码一致性**：0.9999999（完美匹配）
- **Self-Recall@10**：94.5%（优秀）
- **搜索质量**：能正确匹配相关医学术语

## 🎉 使用示例

### **快速测试**
```bash
# 测试单个报告
python workflows/rag_uniform_full_pipeline.py 43002
```

### **小批量评估**
```bash
# 评估5个报告
python workflows/rag_uniform_full_pipeline.py 43001 43005
```

### **完整批量评估**
```bash
# 评估整个测试集
python workflows/rag_uniform_full_pipeline.py 43001 43010
```

## 📋 注意事项

1. **环境要求**：必须在 `RAG_ws` 环境中运行
2. **MongoDB**：确保MongoDB服务正在运行
3. **磁盘空间**：确保有足够空间存储结果
4. **内存**：建议至少8GB内存
5. **时间**：每个报告大约需要1-2分钟

## 🔧 故障排除

### **常见问题**
1. **MongoDB连接失败**：检查MongoDB服务状态
2. **索引加载失败**：确认索引文件路径正确
3. **内存不足**：减少batch_size或关闭其他程序
4. **权限问题**：确保对输出目录有写权限

### **检查命令**
```bash
# 检查MongoDB状态
sudo systemctl status mongod

# 检查索引文件
ls -la /home/duojiechen/projects/Rag_system/RAG_3DB/faiss_indexes/rag_uniform_db/

# 检查输出目录
ls -la Evaluate_output_uniform/
```

---

**🎯 现在RAG Uniform数据库评估系统已经完全修复并可以正常运行！**
