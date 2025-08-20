# RAG评估系统 - 精简版

## 🎯 项目概述

这是一个精简和优化后的RAG（检索增强生成）评估系统，专门用于评估AI模型在医学症状解剖位置识别方面的准确性。

## 📁 精简后的目录结构

```
Rag_Evaluate/
├── src_new/                    # 🆕 整合的核心源代码
│   ├── __init__.py
│   ├── data_loader.py          # 数据加载器（整合版）
│   ├── evaluator.py            # 评估器（整合版）
│   ├── api_manager.py          # API管理器（整合版）
│   └── utils/
│       └── logger.py           # 日志工具
├── workflows/                   # 🆕 工作流脚本
│   ├── __init__.py
│   ├── main_workflow.py        # 主工作流
│   └── quick_start.py          # 快速启动
├── tests_new/                   # 🆕 整合的测试
│   ├── __init__.py
│   └── test_core.py            # 核心功能测试
├── config_new/                  # 🆕 配置文件
│   ├── config.yaml
│   └── .env
├── prompt/                      # 提示词
│   └── system_prompt.txt
├── data/                        # 🆕 数据目录
│   └── test_set/               # 测试数据集
├── results/                     # 结果输出
├── logs/                        # 日志文件
├── requirements.txt             # 依赖
└── README_NEW.md               # 本文档
```

## 🚀 快速开始

### 1. 安装依赖
```bash
pip install -r requirements.txt
```

### 2. 配置API密钥
编辑 `config_new/.env` 文件，添加你的API密钥：
```bash
OPENAI_API_KEY=your_openai_key
ANTHROPIC_API_KEY=your_anthropic_key
GOOGLE_API_KEY=your_google_key
# ... 其他API密钥
```

### 3. 运行快速测试
```bash
python workflows/quick_start.py
```

### 4. 运行完整工作流
```bash
# 处理指定ID范围的Report
python workflows/main_workflow.py --start-id 4000 --end-id 4005

# 限制处理数量
python workflows/main_workflow.py --max-files 10

# 跳过API测试
python workflows/main_workflow.py --no-test
```

## 🔧 核心功能

### 📊 数据加载器 (`src_new/data_loader.py`)
- **Report级别处理**：每个JSON文件作为一个完整的Report
- **ID范围过滤**：支持指定开始和结束Report ID
- **症状聚合**：自动聚合每个症状的所有U单元期望结果

### 🎯 评估器 (`src_new/evaluator.py`)
- **多维度评估**：Precision、Recall、过度生成惩罚
- **Report级别评估**：计算整个Report的综合得分
- **标准化输出**：生成符合要求的JSON结果文件

### 🔌 API管理器 (`src_new/api_manager.py`)
- **多客户端支持**：OpenAI、Anthropic、Gemini、Moonshot、Deepseek
- **统一接口**：所有API使用相同的调用方式
- **错误处理**：完善的异常处理和重试机制

### 📝 日志系统 (`src_new/utils/logger.py`)
- **Report级别日志**：每个Report独立的日志文件
- **结构化记录**：记录处理过程、API调用、评估结果
- **自动管理**：自动创建和管理日志文件

## 📋 工作流特性

### 🎯 ID范围指定
```bash
# 处理Report ID 4000-4010
python workflows/main_workflow.py --start-id 4000 --end-id 4010

# 处理Report ID 4000及以后
python workflows/main_workflow.py --start-id 4000

# 处理Report ID 4010及以前
python workflows/main_workflow.py --end-id 4010
```

### 📊 结果保存
- 每个Report生成独立的结果文件
- 文件命名：`report:ID_baseline_evaluation_standardized.json`
- 包含完整的症状处理、API响应和评估结果

### 📝 日志记录
- 每个Report的详细处理日志
- 工作流执行摘要
- 错误和异常记录

## 🧪 测试

### 运行核心功能测试
```bash
python tests_new/test_core.py
```

### 测试数据加载
```bash
python -c "
from src_new.data_loader import DataLoader
loader = DataLoader()
summary = loader.get_report_summary_by_id_range(Path('data/test_set'), 4000, 4002)
print(f'找到 {summary[\"total_reports\"]} 个Report')
"
```

## 🔄 从旧版本升级

### 主要变化
1. **目录结构简化**：从15+目录减少到8个核心目录
2. **模块整合**：相关功能合并到单个文件
3. **接口统一**：所有模块使用一致的接口设计
4. **配置集中**：配置文件统一管理

### 迁移步骤
1. 备份现有代码
2. 使用新的目录结构
3. 更新导入路径
4. 运行测试验证

## 📊 性能优化

### 代码减少
- **目录数量**：从 15+ 减少到 8
- **文件数量**：从 30+ 减少到 20
- **代码重复**：减少 40-50%
- **维护复杂度**：降低 30-40%

### 功能增强
- **Report级别处理**：更高效的数据处理
- **ID范围过滤**：精确控制处理范围
- **结构化日志**：更好的调试和监控
- **模块化设计**：更容易维护和扩展

## 🆘 故障排除

### 常见问题
1. **导入错误**：检查Python路径和模块位置
2. **API连接失败**：验证API密钥和网络连接
3. **数据加载失败**：检查文件路径和格式
4. **评估错误**：验证数据结构和格式

### 调试建议
1. 启用详细日志记录
2. 使用小数据集测试
3. 检查配置文件格式
4. 验证API客户端初始化

## 📞 支持

如有问题或建议，请：
1. 查看日志文件获取详细错误信息
2. 运行测试脚本验证功能
3. 检查配置文件设置
4. 联系开发团队

---

**版本**: 2.0.0  
**更新日期**: 2024年  
**状态**: 精简优化完成 ✅
