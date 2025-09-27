# 🚀 OpenAI Batch API 快速开始指南

## 🎯 你现在拥有的功能

✅ **完整的批处理RAG评估系统**，包含：
- 原有的 `full` 模式（传统逐条调用）
- 新增的 `full_batch` 模式（**推荐**，完整流程 + 批处理优化）
- 新增的 `batch` 模式（纯批处理API评估）

## 🏃‍♂️ 立即开始

### 1. 检查环境
```bash
# 确认OpenAI版本（你已经有1.101.0，完美支持）
python -c "import openai; print(f'OpenAI version: {openai.__version__}')"

# 确认环境变量
echo $OPENAI_API_KEY
```

### 2. 运行测试（可选）
```bash
# 运行功能测试
python test_batch.py
```

### 3. 开始使用

#### 🌟 推荐：完整RAG评估 + 批处理优化
```bash
# 单个报告，OpenAI成本降低50%
python start_evaluation.py full_batch 4000

# 批量报告
python start_evaluation.py full_batch 4000 4002

# 强制批处理（忽略阈值）
python start_evaluation.py full_batch 4000 --force-batch
```

#### 🔄 传统模式（如需对比）
```bash
# 原有的完整流程
python start_evaluation.py full 4000
```

#### ⚡ 纯批处理模式（仅API评估）
```bash
# 不含RAG流程，仅API评估
python start_evaluation.py batch 4000
```

## 📊 模式选择指南

| 需求 | 推荐模式 | 命令 |
|------|----------|------|
| **完整RAG评估 + 省钱** | `full_batch` | `python start_evaluation.py full_batch 4000` |
| **传统完整评估** | `full` | `python start_evaluation.py full 4000` |
| **大规模API测试** | `batch` | `python start_evaluation.py batch 4000` |
| **基础评估省钱** | `baseline` + 批处理 | `python workflows/main_workflow_batch.py --start_id 4000 --end_id 4000` |

## 💰 成本对比

假设处理100个症状：

```
传统 full 模式:
- OpenAI: 200次调用 × $0.03/1K = $6.00
- 其他API: 200次调用 × $0.02/1K = $4.00
- 总计: $10.00

新 full_batch 模式:
- OpenAI: 2次批处理 × $0.015/1K = $3.00 (省50%)
- 其他API: 200次调用 × $0.02/1K = $4.00
- 总计: $7.00 (省30%)

纯 batch 模式:
- OpenAI: 1次批处理 × $0.015/1K = $1.50 (省50%)
- 其他API: 100次调用 × $0.02/1K = $2.00
- 总计: $3.50 (省65%)
```

## 📁 输出文件结构

### `full_batch` 模式输出：
```
final_result/
├── rag_search_output/              # RAG检索缓存
├── baseline_results_batch/         # 基础评估结果（批处理优化）
├── rerun_with_rag_batch/          # RAG增强结果（批处理优化）
├── rerun_comparisons/             # 对比分析
└── tokens/                        # Token使用统计

batch_processing/                   # 批处理工作文件
├── batch_input_*.jsonl            # 输入文件
└── batch_results_*.json           # 原始结果
```

### `batch` 模式输出：
```
results/batch_results/              # 纯批处理结果
├── report_*_detailed_*.json       # 详细结果
├── report_*_summary_*.json        # 摘要结果
└── overall_summary_*.json         # 总体统计
```

## 🔧 高级配置

### 批处理参数调优
```bash
# 自定义批处理阈值（默认10个症状）
python start_evaluation.py full_batch 4000 --batch-threshold 5

# 强制所有任务使用批处理
python start_evaluation.py full_batch 4000 --force-batch

# 禁用批处理（回退到传统模式）
python start_evaluation.py full_batch 4000 --disable-batch
```

### 监控批处理状态
批处理作业会自动轮询状态，你会看到：
```
⏳ 开始轮询批处理作业状态: batch_abc123def456
📊 [0030s] 状态: in_progress
   进度: 5/15 (33.3%)
📊 [0060s] 状态: in_progress  
   进度: 12/15 (80.0%)
✅ 批处理作业完成!
```

## 🚨 注意事项

1. **批处理延迟**：批处理作业通常在24小时内完成，具体时间取决于队列长度
2. **阈值控制**：默认症状数≥10才启用批处理，可通过 `--batch-threshold` 调整
3. **自动回退**：批处理失败时会自动回退到传统逐条调用
4. **文件清理**：系统会自动清理7天前的批处理文件

## 🎉 你已经准备好了！

现在你可以：
- ✅ 使用 `full_batch` 获得完整RAG评估 + 50%成本节省
- ✅ 使用 `batch` 进行大规模API测试
- ✅ 保持原有 `full` 模式作为对比基准
- ✅ 享受智能阈值控制和自动回退机制

**推荐第一次运行：**
```bash
python start_evaluation.py full_batch 4000 --force-batch
```

这将给你完整的RAG评估体验，同时享受批处理带来的成本优势！
