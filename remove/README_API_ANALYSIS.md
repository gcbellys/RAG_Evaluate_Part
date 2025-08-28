# API评分分析脚本使用说明

## 📁 脚本文件

1. **`api_score_analyzer.py`** - 主要的API评分分析器
2. **`test_moonshot_analysis.py`** - Moonshot API专项测试脚本
3. **`README_API_ANALYSIS.md`** - 本文档

## 🚀 快速开始

### 1. 分析所有API

```bash
cd /home/duojiechen/Projects/Rag_system/Rag_Evaluate/final_result
python api_score_analyzer.py
```

这将分析所有支持的API（moonshot、deepseek、openai、anthropic、gemini）的评分情况。

### 2. 只分析Moonshot API

```bash
python test_moonshot_analysis.py
```

这将只分析Moonshot API的评分情况，适合快速测试。

## 📊 输出格式

脚本会生成两种输出：

### 1. 控制台输出
```
🎯 API评分分析摘要
================================================================================

📊 MOONSHOT:
  症状总数: 150
  无RAG平均分: 45.67
  有RAG平均分: 52.34
  RAG提升比例: 60.0% (90个)
  RAG下降比例: 20.0% (30个)
  无变化比例: 20.0% (30个)
  平均提升分数: 8.45
  平均下降分数: -3.21
```

### 2. JSON报告文件
生成 `api_score_analysis_report.json` 文件，包含详细的统计数据。

## 🔍 数据结构说明

### 输入数据源
- **baseline_results/** - 无RAG增强的评估结果
- **rerun_with_rag/** - 使用RAG增强的评估结果  
- **rerun_comparisons/** - 对比分析结果（主要数据源）

### 评分指标
每个API的评分包含以下指标：
- `overall_score` - 综合评分
- `precision` - 精确度
- `recall` - 召回率
- `f1_score` - F1分数
- `overgeneration_penalty` - 过度生成惩罚

## 📈 统计指标

### 核心统计
- **s_numbers**: 总症状数量
- **scores_without_rag**: 无RAG时的评分统计
- **scores_with_rag**: 有RAG时的评分统计
- **improvement_ratio**: RAG增强有提升的比例
- **decline_ratio**: RAG增强有下降的比例
- **no_change_ratio**: RAG增强无变化的比例

### 详细统计
- **improvement_count**: 提升的症状数量
- **decline_count**: 下降的症状数量
- **no_change_count**: 无变化的症状数量

## 🛠️ 自定义配置

### 修改API列表
在 `api_score_analyzer.py` 中修改：
```python
self.apis = ["moonshot", "deepseek", "openai", "anthropic", "gemini"]
```

### 修改数据目录
```python
analyzer = APIScoreAnalyzer("/path/to/your/data")
```

### 修改输出文件名
```python
analyzer.generate_report("custom_report_name.json")
```

## 🔧 故障排除

### 常见问题

1. **无数据错误**
   - 检查 `rerun_comparisons/` 目录是否存在
   - 确认文件名格式正确（`*_comparison_*.json`）

2. **API名称不匹配**
   - 检查comparison文件中的API名称格式
   - 确保API名称与脚本中的名称一致

3. **评分字段缺失**
   - 检查JSON文件中的 `metrics` 字段
   - 确认 `overall_score` 字段存在

### 调试模式
在脚本中添加更多打印语句：
```python
print(f"DEBUG: 处理症状 {symptom_id}")
print(f"DEBUG: API {api} 的评分数据: {baseline_metrics}")
```

## 📋 使用示例

### 示例1: 完整分析
```python
from api_score_analyzer import APIScoreAnalyzer

analyzer = APIScoreAnalyzer()
stats = analyzer.run_analysis()

# 获取特定API的统计
moonshot_stats = stats.get("moonshot", {})
print(f"Moonshot提升率: {moonshot_stats.get('improvement_ratio', 0)}%")
```

### 示例2: 自定义分析
```python
analyzer = APIScoreAnalyzer()
analyzer.apis = ["moonshot", "deepseek"]  # 只分析两个API
stats = analyzer.run_analysis()
```

## 📊 结果解读

### 提升率解读
- **>50%**: RAG增强效果显著
- **30-50%**: RAG增强效果良好
- **10-30%**: RAG增强效果一般
- **<10%**: RAG增强效果有限

### 平均分变化
- **正数**: RAG增强提升了性能
- **负数**: RAG增强降低了性能
- **接近0**: RAG增强无明显影响

## 🔄 更新和维护

### 添加新的API
1. 在 `self.apis` 列表中添加新API名称
2. 确保comparison文件中有对应的评分数据
3. 测试脚本运行是否正常

### 修改评分逻辑
在 `_process_api_scores` 方法中修改评分提取逻辑，适应不同的数据结构。

---

**版本**: 1.0.0  
**更新日期**: 2025-08-27  
**状态**: 功能完整 ✅
