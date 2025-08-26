# RAG评估系统 - 工作流程指南

## 📁 项目结构

```
Rag_Evaluate/
├── 🚀 主启动脚本
│   └── start_evaluation.py      # 主入口，推荐使用
├── 📁 工作流程 (workflows/)
│   ├── main_workflow.py         # 基础评估（不含RAG）
│   ├── comparision_workflow.py  # 对比工作流（包含RAG）
│   ├── rerun_with_rag.py        # RAG增强评估主脚本
│   └── run_full_pipeline.py     # 完整流程管道
├── 📁 核心模块
│   ├── src/                     # 核心代码
│   ├── api_clients/             # API客户端
│   ├── config/                  # 配置文件
│   ├── scripts/                 # 辅助脚本
│   └── prompt/                  # 提示词模板
├── 📁 结果目录 (final_result/)
│   ├── rag_search_output/       # RAG检索缓存
│   ├── baseline_results/        # 基础评估结果
│   ├── rerun_with_rag/          # RAG增强结果
│   └── rerun_comparisons/       # 对比分析
└── 🗑️ remove/                  # 已清理的旧文件
```

## 🚀 快速开始

### 1. 推荐方式：使用主启动脚本

```bash
# 查看帮助
python start_evaluation.py --help

# 完整RAG评估流程（单个报告）
python start_evaluation.py full 4000

# 批量评估（范围）
python start_evaluation.py full 4000 4002

# 仅基础评估（不含RAG）
python start_evaluation.py baseline 4000

# 仅RAG增强评估（需要已有缓存）
python start_evaluation.py rag-only 4000
```

### 2. 直接使用工作流脚本

```bash
# 完整流程管道
python workflows/run_full_pipeline.py 4000

# 基础评估
python workflows/main_workflow.py --start_id 4000 --end_id 4000

# RAG增强评估
python workflows/rerun_with_rag.py 4000
```

## 📋 工作流程详解

### 🎯 完整RAG评估流程 (推荐)

**命令**: `python start_evaluation.py full 4000`

**步骤**:
1. **RAG检索** → 生成症状相关的医学知识缓存
2. **基础评估** → 运行不含RAG的基准测试（如果缺失）
3. **RAG增强评估** → 使用RAG知识增强的评估
4. **对比分析** → 生成详细的效果对比报告

**输出**:
- `final_result/rag_search_output/` - RAG检索缓存
- `final_result/baseline_results/` - 基础评估结果
- `final_result/rerun_with_rag/` - RAG增强结果
- `final_result/rerun_comparisons/` - 完整对比分析

### 🔍 仅基础评估

**命令**: `python start_evaluation.py baseline 4000`

**用途**: 获得不含RAG的基准结果，用于后续对比

### 🤖 仅RAG增强评估

**命令**: `python start_evaluation.py rag-only 4000`

**前提**: 已有RAG检索缓存
**功能**: 自动检查基础结果，缺失时自动补充

### 🔍 仅RAG检索

**命令**: `python start_evaluation.py retrieve 4000`

**用途**: 仅生成RAG检索缓存，不进行评估

## 📊 结果解读

### 对比分析结果

在 `final_result/rerun_comparisons/report_<id>_results_<timestamp>/` 中：

1. **evaluation_summary.json** - 简化的JSON格式结果
2. **rag_score_report.txt** - 人类可读的效果报告

### 详细指标

- **器官准确率**: 精确匹配/部分匹配/错误
- **解剖位置精确度**: 识别正确率
- **解剖位置召回率**: 覆盖完整度  
- **F1分数**: 精确度和召回率的调和平均
- **过度生成惩罚**: 识别冗余信息的惩罚

## ⚙️ 配置说明

### API配置
编辑 `config/config.yaml`:
```yaml
api_config:
  moonshot:    # 当前激活
  deepseek:    # 当前激活
  # openai:    # 已注释
  # anthropic: # 已注释
  # gemini:    # 已注释
```

### 路径配置
- RAG索引: `/home/duojiechen/Projects/Rag_system/Rag_Build/enhanced_faiss_indexes`
- 测试数据: `test_set/`
- 输出结果: `final_result/`

## 🛠️ 故障排除

### 常见问题

1. **RAG检索失败**
   - 检查 `Rag_Build` 环境是否正确配置
   - 确认 FAISS 索引文件存在

2. **API调用失败**
   - 检查API密钥环境变量
   - 确认API配置未被注释

3. **文件路径错误**
   - 确保在项目根目录执行命令
   - 检查 `final_result/` 目录权限

### 调试模式

```bash
# 添加详细输出
python start_evaluation.py full 4000 --verbose

# 限制文件数量
python workflows/main_workflow.py --start_id 4000 --end_id 4000 --max_files 1
```

## 📈 性能优化

- **并行处理**: 考虑批量处理多个报告
- **缓存利用**: 重复使用RAG检索缓存
- **API选择**: 根据速度需求选择合适的API

## 🔄 版本历史

- **v3.0**: 文件结构重组，统一启动脚本
- **v2.0**: RAG增强评估系统
- **v1.0**: 基础评估系统
