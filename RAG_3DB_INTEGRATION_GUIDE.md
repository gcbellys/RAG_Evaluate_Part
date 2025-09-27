# RAG_3DB与Rag_Evaluate系统整合指南

## 🎯 概述

本指南介绍如何使用新构建的三个RAG数据库（RAG_3DB）与Rag_Evaluate评估系统进行整合，实现基于不同采样策略的医疗症状检索与评估。

## 🗃️ 三个RAG数据库

### 1. Uniform Random Unit Database
- **采样策略**: 纯随机采样
- **数据规模**: 43,000个症状-诊断单元(SDU)
- **特点**: 最大数据多样性，无上下文偏差
- **适用场景**: 基础性能评估，数据多样性测试

### 2. Report Context Database  
- **采样策略**: 报告级采样
- **数据规模**: 43,000个症状-诊断单元(SDU)
- **特点**: 保持完整报告上下文，症状关联性强
- **适用场景**: 上下文相关性评估，报告级诊断

### 3. Sequential Block Database
- **采样策略**: 顺序采样
- **数据规模**: 43,000个症状-诊断单元(SDU)  
- **特点**: 保持时间顺序，反映数据演变
- **适用场景**: 时序分析，数据演变趋势研究

## 🚀 快速开始

### 1. 环境准备

```bash
# 激活RAG_ws环境（用于RAG_3DB系统）
conda activate RAG_ws

# 确保MongoDB服务运行
sudo systemctl start mongod
sudo systemctl status mongod
```

### 2. 系统测试

```bash
# 进入Rag_Evaluate目录
cd /home/duojiechen/projects/Rag_system/Rag_Evaluate

# 运行整合测试
python test_rag3db_integration.py
```

### 3. 基本使用

#### 单数据库评估
```bash
# 使用Uniform Random Unit数据库评估单个报告
python start_evaluation.py rag3db 4000 --rag_db_type uniform

# 使用Report Context数据库评估报告范围
python start_evaluation.py rag3db 4000 4002 --rag_db_type report_context

# 使用Sequential Block数据库评估，指定top-k
python start_evaluation.py rag3db 4000 --rag_db_type sequential_block --top_k 5
```

#### 多数据库对比评估
```bash
# 对比所有三个数据库（推荐）
python start_evaluation.py rag3db_compare 4000 4002

# 对比评估单个报告
python start_evaluation.py rag3db_compare 4000
```

## 📊 工作流程详解

### 完整评估流程

1. **RAG检索阶段**
   - 使用指定的RAG数据库进行症状检索
   - 生成top-k相似症状缓存
   - 保存结构化检索结果(.jsonl格式)

2. **基础评估阶段**
   - 如果不存在baseline结果，自动生成
   - 使用标准提示词进行症状解剖位置识别
   - 调用配置的所有API进行评估

3. **RAG增强评估阶段**
   - 加载RAG检索缓存
   - 构建增强型提示词（包含相似症状知识）
   - 重新调用API进行增强评估

4. **对比分析阶段**
   - 生成baseline vs RAG增强的性能对比
   - 计算精确率、召回率、F1分数等指标
   - 生成详细的分析报告

## 🔧 配置选项

### 主要参数

- `--rag_db_type`: RAG数据库类型
  - `uniform`: Uniform Random Unit Database
  - `report_context`: Report Context Database  
  - `sequential_block`: Sequential Block Database

- `--top_k`: 检索返回的相似症状数量（默认：3）

- `--data_dir`: 输入数据目录（默认：test_set）

- `--config`: 配置文件路径（默认：config/config_rag3db.yaml）

### 配置文件

使用专用配置文件 `config/config_rag3db.yaml`，包含：
- API配置（支持多个LLM提供商）
- RAG_3DB系统配置
- 数据库连接配置
- 评估参数配置

## 📁 输出结果

评估结果保存在 `Evaluate_output/` 目录下：

```
Evaluate_output/
├── rag_search_output/           # RAG检索缓存
│   └── report_4000_ragoutcome_uniform_*.jsonl
├── baseline_results/            # 基础评估结果
│   └── report_diagnostic_4000_evaluation_*.json
├── rerun_with_rag/             # RAG增强评估结果
│   └── rag_enhanced_report_4000_*.json
├── rerun_comparisons/          # 对比分析
│   └── report_4000_comparison_*.json
├── tokens/                     # Token使用统计
│   └── token_analysis_*.json
└── rag3db_evaluation_summary_*.json  # 总结报告
```

## 🔍 高级用法

### 1. 批量处理
```bash
# 批量处理多个报告
python start_evaluation.py rag3db 4000 4010 --rag_db_type uniform

# 大批量对比评估
python start_evaluation.py rag3db_compare 4000 4050
```

### 2. 自定义数据目录
```bash
# 使用不同的数据目录
python start_evaluation.py rag3db 17500 --data_dir diag_data_normalized
```

### 3. 调整检索参数
```bash
# 增加检索深度
python start_evaluation.py rag3db 4000 --top_k 10

# 使用不同配置文件
python start_evaluation.py rag3db 4000 --config config/custom_config.yaml
```

## 📊 性能对比

### 数据库特性对比

| 特性 | Uniform Random | Report Context | Sequential Block |
|------|----------------|----------------|------------------|
| 采样策略 | 纯随机 | 报告级 | 顺序 |
| 数据多样性 | 最高 | 中等 | 中等 |
| 上下文保持 | 无 | 强 | 中等 |
| 时序信息 | 无 | 无 | 强 |
| 适用场景 | 基础评估 | 上下文分析 | 时序分析 |

### 预期性能差异

- **Uniform Random**: 提供最广泛的症状覆盖，适合发现罕见症状模式
- **Report Context**: 在相关症状聚类方面表现更好，提高诊断准确性
- **Sequential Block**: 能够捕捉数据演变趋势，适合长期分析

## 🛠️ 故障排除

### 常见问题

1. **MongoDB连接失败**
   ```bash
   sudo systemctl start mongod
   sudo systemctl enable mongod
   ```

2. **Faiss索引文件不存在**
   - 确保RAG_3DB系统已正确构建
   - 检查索引文件路径是否正确

3. **SapBERT模型加载失败**
   - 确保模型路径正确
   - 检查conda环境是否激活

4. **API密钥未设置**
   ```bash
   export ANTHROPIC_API_KEY="your_key"
   export GEMINI_API_KEY="your_key"
   # 等等...
   ```

### 调试模式

```bash
# 运行测试脚本诊断问题
python test_rag3db_integration.py

# 查看详细日志
tail -f logs/rag3db_evaluation.log
```

## 📈 结果分析

### 评估指标

- **精确率 (Precision)**: 识别正确的解剖位置比例
- **召回率 (Recall)**: 覆盖所有相关解剖位置的比例  
- **F1分数**: 精确率和召回率的调和平均
- **过度生成惩罚**: 对不相关位置的惩罚

### 对比分析

系统会自动生成：
1. **数据库间性能对比**: 不同采样策略的效果差异
2. **症状级别分析**: 每个症状在不同数据库下的表现
3. **API性能对比**: 不同LLM在各数据库下的表现
4. **成本效益分析**: Token使用量和性能的权衡

## 🎯 最佳实践

1. **首次使用**: 先运行 `rag3db_compare` 了解三个数据库的特性
2. **大规模评估**: 使用批量处理模式提高效率
3. **特定场景**: 根据评估目标选择合适的数据库类型
4. **性能监控**: 定期查看Token使用统计控制成本
5. **结果验证**: 使用多个数据库交叉验证结果可靠性

## 🔗 相关文档

- [RAG_3DB系统文档](../RAG_3DB/README.md)
- [Rag_Evaluate系统文档](README.md)
- [API配置指南](config/README.md)
- [故障排除指南](TROUBLESHOOTING.md)

---

**版本**: 1.0.0  
**更新日期**: 2025-09-23  
**维护者**: AI Assistant
