# 并发RAG评估系统指南

## 🎯 概述

本系统现在支持**并发运行多个配置**的RAG评估，您可以同时使用不同的API密钥配置运行不同范围的报告评估。

## ⚙️ 配置说明

### 配置文件对比

| 配置文件 | API密钥环境变量 | 报告范围 | 用途 |
|---------|----------------|----------|------|
| `config.yaml` | `MOONSHOT_API_KEY`<br>`DEEPSEEK_API_KEY` | 4000-4100 | 主要配置 |
| `config_cn.yaml` | `MOONSHOT_API_KEY_2`<br>`DEEPSEEK_API_KEY_2` | 4050-4200 | 中文配置 |

### 环境变量设置

请确保设置了以下4个环境变量：

```bash
# 主要配置的API密钥
export MOONSHOT_API_KEY="your_moonshot_key_1"
export DEEPSEEK_API_KEY="your_deepseek_key_1"

# 中文配置的API密钥
export MOONSHOT_API_KEY_2="your_moonshot_key_2"
export DEEPSEEK_API_KEY_2="your_deepseek_key_2"
```

## 🚀 使用方法

### 方法1：并发评估（推荐）

使用专门的并发脚本，同时运行两个配置：

```bash
# 完整RAG评估流程（并发）
python run_concurrent_evaluation.py

# 或指定工作流程
python run_concurrent_evaluation.py --workflow full
python run_concurrent_evaluation.py --workflow baseline
python run_concurrent_evaluation.py --workflow rag-only
```

**并发任务**：
- **Task 1**: 使用 `config.yaml` 评估报告 4000-4100
- **Task 2**: 使用 `config_cn.yaml` 评估报告 4050-4200

### 方法2：单独运行（指定配置）

使用主启动脚本，指定配置文件：

```bash
# 使用主要配置评估4000-4100
python start_evaluation.py full 4000 4100 --config config/config.yaml

# 使用中文配置评估4050-4200
python start_evaluation.py full 4050 4200 --config config/config_cn.yaml

# 基础评估
python start_evaluation.py baseline 4000 4100 --config config/config.yaml
```

### 方法3：直接调用工作流

```bash
# 使用指定配置的完整流程
python workflows/run_full_pipeline.py 4000 4100 --config config/config.yaml

# 使用指定配置的基础评估
python workflows/main_workflow.py --start_id 4000 --end_id 4100 --config config/config.yaml

# 使用指定配置的RAG增强评估
python workflows/rerun_with_rag.py 4000 --config config/config.yaml
```

## 📊 输出结果

### 并发运行的结果管理

当使用并发评估时，两个任务的结果会混合在相同的目录中，但可以通过时间戳区分：

```
final_result/
├── rag_search_output/          # RAG检索缓存（两个任务共享）
├── baseline_results/           # 基础评估结果
├── rerun_with_rag/            # RAG增强结果
└── rerun_comparisons/         # 对比分析结果
```

### 并发执行日志

并发运行会产生详细的日志文件：

```
concurrent_logs/
├── task1_default_20250826_143000.log    # Task 1 详细日志
├── task2_cn_20250826_143000.log          # Task 2 详细日志
└── concurrent_summary_20250826_143000.txt # 总结报告
```

### 监控并发进度

并发执行时，终端会显示实时进度：

```
🚀 [Task1_Config_Default] 开始执行
🚀 [Task2_Config_CN] 开始执行
[Task1_Config_Default] 正在处理报告 4000...
[Task2_Config_CN] 正在处理报告 4050...
✅ [Task1_Config_Default] 执行成功
✅ [Task2_Config_CN] 执行成功
```

## 🛠️ 故障排除

### 1. 环境变量问题

**错误**: `❌ 缺少必要的环境变量`

**解决**: 确保设置了所有4个API密钥环境变量

```bash
# 检查环境变量
echo $MOONSHOT_API_KEY
echo $DEEPSEEK_API_KEY
echo $MOONSHOT_API_KEY_2
echo $DEEPSEEK_API_KEY_2
```

### 2. API配额冲突

如果两个配置使用相同的API密钥，可能会遇到API调用频率限制。

**解决**: 确保使用不同的API密钥，或者错开执行时间

### 3. 资源冲突

两个任务可能会竞争相同的文件资源。

**解决**: 并发脚本已经内置了启动延迟（2秒），通常能避免大部分冲突

### 4. 部分任务失败

**排查方法**:
1. 查看 `concurrent_logs/` 中的详细日志
2. 检查总结报告中的错误信息
3. 单独运行失败的任务进行调试

## 💡 最佳实践

### 1. 推荐的并发配置

- **不同API密钥**: 避免API调用冲突
- **重叠范围**: 4000-4100 和 4050-4200 有重叠，便于对比分析
- **错峰运行**: 如果API有频率限制，考虑错峰运行

### 2. 监控和管理

```bash
# 查看系统资源使用
htop

# 监控并发日志
tail -f concurrent_logs/task1_*.log
tail -f concurrent_logs/task2_*.log

# 查看结果文件
ls -la final_result/*/
```

### 3. 结果分析

```bash
# 查看并发总结报告
cat concurrent_logs/concurrent_summary_*.txt

# 对比两个配置的结果
python -c "
import json
from pathlib import Path

# 分析结果差异的脚本可以在这里添加
"
```

## 🚀 快速开始示例

1. **设置环境变量**：
   ```bash
   export MOONSHOT_API_KEY="your_key_1"
   export DEEPSEEK_API_KEY="your_key_1"
   export MOONSHOT_API_KEY_2="your_key_2"  
   export DEEPSEEK_API_KEY_2="your_key_2"
   ```

2. **运行并发评估**：
   ```bash
   python run_concurrent_evaluation.py --workflow full
   ```

3. **监控进度**：
   - 观察终端输出
   - 查看 `concurrent_logs/` 中的日志文件

4. **分析结果**：
   - 查看 `final_result/rerun_comparisons/` 中的对比结果
   - 阅读 `concurrent_logs/concurrent_summary_*.txt` 总结报告

## 📈 性能考虑

- **并行度**: 目前支持2个并发任务，可以根据需要扩展
- **内存使用**: 两个任务会同时加载模型和数据，确保有足够内存
- **磁盘空间**: 结果文件会较多，确保有足够磁盘空间
- **网络带宽**: 两个任务会同时调用API，可能会影响网络使用

## 🔮 高级用法

### 自定义并发配置

您可以修改 `run_concurrent_evaluation.py` 中的任务配置：

```python
tasks = [
    {
        'name': 'Custom_Task_1',
        'command': f'python start_evaluation.py {workflow} 4000 4050 --config config/custom1.yaml',
        'log_file': log_dir / f'custom1_{timestamp}.log'
    },
    {
        'name': 'Custom_Task_2', 
        'command': f'python start_evaluation.py {workflow} 4051 4100 --config config/custom2.yaml',
        'log_file': log_dir / f'custom2_{timestamp}.log'
    }
]
```

这样您就可以完全自定义并发评估的配置和范围了！
