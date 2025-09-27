# OpenAI Batch API 批处理模式使用指南

本指南介绍如何使用新增的 OpenAI Batch API 批处理功能，实现更高效、更经济的大规模RAG评估。

## 🚀 快速开始

### 1. 安装与初始化

```bash
# 运行自动安装脚本
python setup_batch.py

# 或手动安装
pip install -U openai python-dotenv pyyaml
```

### 2. 配置环境变量

编辑 `config/.env` 文件：

```bash
# OpenAI API配置
OPENAI_API_KEY=sk-your-openai-api-key-here

# 其他API配置（可选）
ANTHROPIC_API_KEY=sk-ant-your-anthropic-key-here
GEMINI_API_KEY=your-gemini-api-key-here
```

### 3. 运行批处理评估

```bash
# 推荐：完整RAG评估流程 + 批处理优化
python start_evaluation.py full_batch 4000

# 批量完整评估 + 批处理优化
python start_evaluation.py full_batch 4000 4002

# 强制使用批处理（忽略阈值）
python start_evaluation.py full_batch 4000 --force-batch

# 纯批处理模式（仅API评估，不含RAG流程）
python start_evaluation.py batch 4000

# 禁用批处理，使用传统模式
python start_evaluation.py full_batch 4000 --disable-batch
```

## 📋 功能特性

### 批处理模式优势

1. **成本降低**: 批处理API比标准API便宜50%
2. **高效处理**: 异步处理大量请求，无需等待
3. **自动重试**: 内置错误处理和重试机制
4. **智能回退**: 批处理失败时自动回退到逐条调用

### 工作流程

```
1. 收集所有症状文本
2. 生成JSONL批处理文件
3. 上传文件并创建批处理作业
4. 轮询作业状态（24小时内完成）
5. 下载并解析结果
6. 整理为标准格式输出
```

## 🔧 配置选项

### 命令行参数

```bash
python start_evaluation.py batch [报告ID] [选项]

必需参数:
  报告ID                    开始报告ID
  
可选参数:
  结束ID                    结束报告ID（批量处理）
  --config PATH            配置文件路径（默认: config/config.yaml）
  --max_files N            最大处理文件数量
  
批处理选项:
  --disable-batch          禁用批处理模式
  --batch-threshold N      启用批处理的最小症状数量阈值（默认: 10）
  --force-batch           强制使用批处理，忽略阈值
```

### 配置文件设置

在 `config/config.yaml` 中：

```yaml
api_config:
  openai:
    base_url: "https://api.openai.com/v1"
    model: "gpt-4"  # 或 "gpt-4o-mini" 等
    api_key_env: "OPENAI_API_KEY"

evaluation:
  batch_size: 10
  timeout: 30
```

## 📊 使用示例

### 示例1: 完整RAG评估 + 批处理优化（推荐）

```bash
# 完整RAG评估流程，OpenAI使用批处理降低成本50%
python start_evaluation.py full_batch 4000
```

输出：
```
🎯 完整批处理RAG评估流程
📋 报告范围: 4000 - 4000
🔍 检索参数: top_k=3
🚀 批处理模式: OpenAI使用Batch API，其他API使用传统模式

==================== 步骤 1/4: RAG检索 ====================
🚀 RAG检索 - 从知识库检索相关信息
💻 执行: bash scripts/step1_rag_retrieve.sh 4000 4000 3
✅ RAG检索 - 从知识库检索相关信息 - 完成

==================== 步骤 2/4: 基础评估 ====================
🚀 基础评估 (使用批处理优化)
🔧 初始化批处理API管理器...
✅ OpenAI 客户端初始化成功 (支持批处理)
📦 执行 openai 批处理，15 个任务...
✅ 批处理作业完成!
✅ 基础评估 (使用批处理优化) - 完成

==================== 步骤 3/4: RAG增强评估 ====================
🚀 RAG增强评估 - 报告 4000 (使用批处理优化)
📦 执行 openai 批处理，15 个任务...
✅ RAG增强评估 - 报告 4000 (使用批处理优化) - 完成

==================== 步骤 4/4: 对比分析 ====================
✅ Token使用分析完成

🎉 完整批处理RAG评估流程执行成功!
💰 成本优化:
   • OpenAI API: 使用Batch API，成本降低50%
   • 其他API: 保持传统调用模式
```

### 示例2: 纯批处理模式

```bash
# 仅API评估，不含RAG流程
python start_evaluation.py batch 4000
```

输出：
```
🚀 批处理RAG评估系统
📋 报告范围: 4000 - 4000
🔧 批处理模式: 启用
📊 批处理阈值: 10

🔧 初始化批处理API管理器...
✅ OpenAI 客户端初始化成功 (支持批处理)

📦 执行 openai 批处理，15 个任务...
📝 生成批处理JSONL文件: batch_processing/batch_input_20241201_143022_a1b2c3d4.jsonl
📤 上传批处理文件...
🚀 批处理作业创建成功
   作业ID: batch_abc123def456
   状态: validating

⏳ 开始轮询批处理作业状态...
📊 [0030s] 状态: in_progress
   进度: 5/15 (33.3%)
📊 [0060s] 状态: in_progress
   进度: 12/15 (80.0%)
✅ 批处理作业完成!
   总耗时: 1247秒
   成功数: 15
   失败数: 0

📥 下载批处理结果...
✅ 结果解析完成: 15 成功, 0 失败
💾 结果已保存到: batch_processing/batch_results_batch_abc123def456_20241201_143542.json
```

### 示例2: 批量处理多个报告

```bash
# 批量评估报告4000-4005
python start_evaluation.py batch 4000 4005 --force-batch
```

### 示例3: 混合模式（部分批处理）

```bash
# OpenAI使用批处理，其他API使用传统模式
python start_evaluation.py batch 4000 --batch-threshold 5
```

## 📁 输出文件结构

```
results/batch_results/
├── report_4000_detailed_20241201_143542.json    # 详细结果
├── report_4000_summary_20241201_143542.json     # 摘要结果
└── overall_summary_20241201_143600.json         # 总体摘要

batch_processing/
├── batch_input_20241201_143022_a1b2c3d4.jsonl   # 输入文件
└── batch_results_batch_abc123def456_20241201_143542.json  # 原始结果
```

## 🔍 监控与调试

### 查看批处理状态

批处理作业会自动轮询状态，你也可以手动检查：

```python
from api_clients.openai_batch_client import OpenAIBatchClient

client = OpenAIBatchClient(api_key="your-key")
batch_info = client.poll_batch_status("batch_abc123def456")
print(batch_info)
```

### 常见状态说明

- `validating`: 验证输入文件
- `in_progress`: 正在处理
- `completed`: 处理完成
- `failed`: 处理失败
- `expired`: 作业过期（24小时）
- `cancelled`: 作业被取消

### 错误处理

系统包含多层错误处理：

1. **输入验证**: 检查JSONL格式和内容
2. **上传重试**: 文件上传失败时重试
3. **状态监控**: 定期检查作业状态
4. **自动回退**: 批处理失败时回退到逐条调用
5. **结果验证**: 确保所有任务都有结果

## 💡 最佳实践

### 何时使用批处理

✅ **推荐使用批处理的场景:**
- 症状数量 >= 10
- 大规模评估任务
- 成本敏感的项目
- 非实时处理需求

❌ **不推荐使用批处理的场景:**
- 症状数量 < 5
- 需要实时结果
- 调试和测试阶段

### 性能优化建议

1. **合理设置阈值**: 根据实际需求调整 `--batch-threshold`
2. **批量处理**: 一次处理多个报告而不是单独处理
3. **错峰使用**: 避免在API高峰期提交大量批处理
4. **监控配额**: 注意API配额和限制

### 成本估算

```
传统API成本: $0.03/1K tokens (gpt-4)
批处理API成本: $0.015/1K tokens (gpt-4) - 节省50%

示例: 1000个症状，每个平均500 tokens
传统模式: 500K tokens × $0.03 = $15
批处理模式: 500K tokens × $0.015 = $7.5
节省: $7.5 (50%)
```

## 🛠️ 故障排除

### 常见问题

**Q: 批处理作业一直显示 "validating" 状态？**
A: 检查JSONL文件格式，确保每行都是有效的JSON对象。

**Q: 批处理失败，显示 "invalid_request_error"？**
A: 检查API密钥权限，确保有Batch API访问权限。

**Q: 结果文件中有些任务没有结果？**
A: 检查错误日志，可能是个别请求格式问题。系统会自动重试失败的任务。

**Q: 批处理速度比预期慢？**
A: 批处理通常在24小时内完成，具体时间取决于队列长度和任务复杂度。

### 调试模式

启用详细日志：

```bash
# 设置环境变量启用调试
export OPENAI_LOG_LEVEL=debug
python start_evaluation.py batch 4000 --force-batch
```

### 手动清理

清理旧的批处理文件：

```python
from api_clients.openai_batch_client import OpenAIBatchClient

client = OpenAIBatchClient(api_key="your-key")
client.cleanup_batch_files(keep_days=3)  # 保留3天内的文件
```

## 📈 模式对比

### 完整对比表

| 特性 | `full` | `full_batch` | `batch` |
|------|--------|-------------|---------|
| **RAG检索** | ✅ 是 | ✅ 是 | ❌ 否 |
| **基础评估** | ✅ 是 | ✅ 是 (批处理优化) | ❌ 否 |
| **RAG增强评估** | ✅ 是 | ✅ 是 (批处理优化) | ❌ 否 |
| **对比分析** | ✅ 是 | ✅ 是 | ❌ 否 |
| **纯API评估** | ❌ 否 | ❌ 否 | ✅ 是 (批处理优化) |
| **OpenAI成本** | 100% | 50% | 50% |
| **其他API成本** | 100% | 100% | 100% |
| **处理时间** | ~30分钟 | ~35分钟* | ~20分钟* |
| **实时性** | 实时 | 延迟 | 延迟 |
| **适用场景** | RAG效果对比 | 经济型RAG对比 | 大规模API测试 |

*包含批处理排队时间

### 性能对比（100症状示例）

| 模式 | OpenAI调用 | 其他API调用 | 总成本 | 预计耗时 |
|------|------------|-------------|--------|----------|
| `full` | 200次标准调用 | 200次标准调用 | 100% | 30分钟 |
| `full_batch` | 2次批处理作业 | 200次标准调用 | 75%** | 35分钟 |
| `batch` | 1次批处理作业 | 100次标准调用 | 62.5%** | 20分钟 |

**假设OpenAI占总成本的50%

## 🔄 版本兼容性

- **OpenAI库**: 需要 >= 1.3.0
- **Python**: 需要 >= 3.8
- **API版本**: 支持 `/v1/chat/completions` 端点
- **向后兼容**: 完全兼容现有工作流程

## 📞 技术支持

如有问题，请检查：

1. [OpenAI Batch API 官方文档](https://platform.openai.com/docs/guides/batch)
2. [OpenAI Cookbook 批处理示例](https://cookbook.openai.com/examples/batch_processing)
3. 项目 Issue 页面

---

*最后更新: 2024年12月*
