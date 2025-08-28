# 🧠 RAG_Evaluate - RAG评估系统

一个专业的RAG（检索增强生成）评估系统，专门用于评估AI模型在医学症状解剖位置识别方面的准确性。

## 📋 目录

- [概述](#概述)
- [功能特性](#功能特性)
- [系统架构](#系统架构)
- [安装说明](#安装说明)
- [使用方法](#使用方法)
- [目录结构](#目录结构)
- [配置说明](#配置说明)
- [API支持](#api支持)
- [工作流程](#工作流程)
- [贡献指南](#贡献指南)
- [许可证](#许可证)
- [故障排除](#故障排除)

## 🎯 概述

RAG_Evaluate是一个专业的医疗诊断评估系统，利用大语言模型（LLMs）和RAG（检索增强生成）技术来分析医疗报告。系统实现了多种评估方法：

- **基础评估**：传统的症状识别和评估
- **RAG增强评估**：集成知识检索的智能评估
- **对比分析**：多种方法的性能对比
- **并发评估**：高效的批量处理能力

## ✨ 功能特性

### 核心能力
- **多API支持**：兼容OpenAI、Anthropic、Gemini、Moonshot、DeepSeek APIs
- **智能评估**：多维度性能指标评估
- **RAG集成**：知识检索增强诊断准确性
- **综合评估**：详细的性能指标和对比分析
- **批量处理**：高效处理多个诊断报告
- **多种工作流**：灵活的工作流程选择

### 评估指标
- **总体评分**：所有维度的加权性能
- **精确度**：预测诊断的准确性
- **召回率**：症状识别的完整性
- **过度生成惩罚**：控制过度预测

## 🏗️ 系统架构

### 系统组件
```
┌─────────────────────────────────────────────────────────────┐
│                        RAG_Evaluate                         │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────────────┐ │
│  │   API       │  │   评估       │  │   RAG               │ │
│  │   客户端    │  │   引擎       │  │   集成               │ │
│  └─────────────┘  └──────────────┘  └─────────────────────┘ │
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────────────┐ │
│  │   工作流    │  │   数据       │  │   报告               │ │
│  │   管理      │  │   加载       │  │   系统               │ │
│  └─────────────┘  └──────────────┘  └─────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### 工作流程
1. **数据输入**：加载诊断报告（JSON格式）
2. **症状提取**：解析和识别医疗症状
3. **处理策略**：应用基础或RAG增强方法
4. **RAG增强**：检索相关医疗知识
5. **评估**：生成综合性能指标
6. **报告**：创建详细分析报告

## 🚀 安装说明

### 前置要求
- Python 3.8或更高版本
- pip包管理器
- 支持的LLM提供商的API密钥
- CUDA兼容GPU（推荐，用于最佳性能）

### 安装步骤
```bash
# 克隆仓库
git clone <仓库地址>
cd Rag_Evaluate

# 创建虚拟环境（推荐）
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 安装支持CUDA的PyTorch（如果可用）
pip install --pre torch torchvision torchaudio --index-url https://download.pytorch.org/whl/nightly/cu128

# 安装Faiss-GPU（如果CUDA可用）
conda install -y -c conda-forge "faiss-gpu=1.8.0=py310_*"

# 配置API密钥
cp config/config.yaml config/config_local.yaml
# 编辑config/config_local.yaml，添加您的API密钥
```

### 环境配置
```bash
# 设置环境变量
export OPENAI_API_KEY="您的openai密钥"
export ANTHROPIC_API_KEY="您的anthropic密钥"
export GOOGLE_API_KEY="您的google密钥"
export MOONSHOT_API_KEY="您的moonshot密钥"
export DEEPSEEK_API_KEY="您的deepseek密钥"
```

## 📖 使用方法

### 快速开始
```bash
# 激活环境
conda activate rag5090

# 完整RAG评估流程（推荐）
python start_evaluation.py full 4000

# 批量评估多个报告
python start_evaluation.py full 4000 4002

# 仅基础评估
python start_evaluation.py baseline 4000

# 仅RAG增强评估
python start_evaluation.py rag-only 4000

# 仅RAG检索
python start_evaluation.py retrieve 4000
```

### 高级用法
```bash
# 使用自定义配置
python start_evaluation.py full 4000 --config config/config_cn.yaml

# 限制处理文件数量
python start_evaluation.py full 4000 4010 --max_files 5

# 自定义RAG检索参数
python start_evaluation.py full 4000 --top_k 5

# 运行并发评估
python run_concurrent_evaluation.py --data_path test_set --max_workers 4

# 运行完整管道
python workflows/run_full_pipeline.py 4000 4002
```

### 工作流选择
- **`full`**：完整RAG评估流程（推荐）
- **`baseline`**：仅运行基础评估
- **`rag-only`**：仅运行RAG增强评估
- **`retrieve`**：仅运行RAG检索

## 🗂️ 目录结构

```
Rag_Evaluate/
├── api_clients/              # API客户端实现
│   ├── __init__.py
│   ├── anthropic_client.py
│   ├── deepseek_client.py
│   ├── gemini_client.py
│   ├── moonshot_client.py
│   └── openai_client.py
├── config/                   # 配置文件
│   ├── config.yaml
│   ├── config_cn.yaml
│   ├── organ_anatomy_config.py
│   └── README.md
├── data/                     # 数据目录
│   └── test_set/            # 测试数据集
├── final_result/             # 最终评估结果
│   ├── baseline_results/
│   ├── rag_search_output/
│   ├── results_of_apis/
│   └── smart_api_analyzer.py
├── prompt/                   # 系统提示词
│   ├── system_prompt.txt
│   ├── rag_enhanced_prompt.txt
│   └── smart_rag_prompt.txt
├── remove/                   # 已弃用/移除的文件
├── scripts/                  # 实用脚本
│   ├── run_rag_pipeline.sh
│   └── step1_rag_retrieve.sh
├── src/                      # 核心源代码
│   ├── api_manager.py
│   ├── config_loader.py
│   ├── data_loader.py
│   ├── evaluator.py
│   ├── test.py
│   └── utils/
│       └── logger.py
├── test_set/                 # 测试数据集
├── tests/                    # 测试文件
│   ├── __init__.py
│   └── test_core.py
├── workflows/                # 工作流实现
│   ├── comparision_workflow.py
│   ├── main_workflow.py
│   ├── rerun_with_rag.py
│   ├── run_full_pipeline.py
│   └── smart_rag_evaluator.py
├── batch_analysis_summary.py # 批量分析摘要
├── CONCURRENT_GUIDE.md       # 并发使用指南
├── run_concurrent_evaluation.py # 并发评估脚本
├── RAG_SYSTEM_ANALYSIS.md   # RAG系统分析报告
├── start_evaluation.py       # 主启动脚本
├── WORKFLOW_GUIDE.md         # 工作流指南
├── requirements.txt          # Python依赖
└── README.md                # 此文件
```

## 🔧 配置说明

### 核心配置文件
- **`config/config.yaml`**：主配置文件
- **`config/config_cn.yaml`**：中文配置文件
- **`config/organ_anatomy_config.py`**：器官解剖特定配置
- **`prompt/system_prompt*.txt`**：不同评估模式的系统提示词

### 自定义评估
修改配置文件以调整：
- API端点和密钥
- 处理策略
- 输出目录
- 评估参数

## 🔌 API支持

### 支持的LLM提供商
- **OpenAI**：GPT-4、GPT-3.5-turbo
- **Anthropic**：Claude-3模型
- **Google**：Gemini模型
- **Moonshot**：Moonshot模型
- **DeepSeek**：DeepSeek模型

### API客户端特性
- 自动重试机制
- 速率限制支持
- 错误处理和日志记录
- 响应验证

## 🧪 工作流程

### 完整评估流程
1. **RAG检索**：为指定报告检索相关知识
2. **基础评估**：运行标准评估流程
3. **RAG增强评估**：使用检索知识进行增强评估
4. **对比分析**：比较不同方法的结果

### 基础评估流程
- 传统的症状识别和评估
- 标准性能指标计算
- 结构化结果输出

### RAG增强流程
- 智能知识检索
- 上下文增强评估
- 提高诊断准确性

## 📊 结果和输出

### 输出结构
- **基础结果**：标准评估结果
- **RAG增强结果**：知识增强的评估结果
- **对比结果**：不同方法的性能对比
- **性能指标**：详细的评分和分析

### 报告格式
- JSON结构化数据
- Markdown摘要
- 性能分析表格
- API对比报告

## 🤝 贡献指南

我们欢迎对RAG_Evaluate的改进贡献！请按照以下步骤：

1. Fork仓库
2. 创建新分支（`git checkout -b feature-name`）
3. 进行更改
4. 提交更改（`git commit -am '添加新功能'`）
5. 推送到分支（`git push origin feature-name`）
6. 打开拉取请求

### 开发指南
- 遵循PEP 8编码标准
- 为新功能添加综合测试
- 更新API更改的文档
- 确保向后兼容性

## 📜 许可证

本项目采用MIT许可证 - 详情请参阅[LICENSE](LICENSE)文件。

## 🛠️ 故障排除

### 常见问题

#### 安装问题
- **错误：PyTorch CUDA不匹配**：安装与CUDA版本匹配的PyTorch版本
- **错误：Faiss安装失败**：GPU版本使用conda，CPU版本使用pip
- **错误：依赖未找到**：运行`pip install -r requirements.txt`

#### 运行时问题
- **错误：API密钥缺失**：确保在环境变量中设置API密钥
- **错误：CUDA内存不足**：减少批处理大小或使用CPU处理
- **错误：模型加载失败**：检查模型路径和权限

#### 性能问题
- **处理缓慢**：使用CUDA启用GPU加速
- **内存问题**：减少批处理大小
- **API速率限制**：实施适当的速率限制和重试逻辑

### 获取帮助
- 查看[WORKFLOW_GUIDE.md](WORKFLOW_GUIDE.md)获取工作流说明
- 查看[CONCURRENT_GUIDE.md](CONCURRENT_GUIDE.md)获取并发使用指南
- 查看[RAG_SYSTEM_ANALYSIS.md](RAG_SYSTEM_ANALYSIS.md)获取系统分析

## 🔗 相关项目

- **Rag_Evaluate_WholeReport**：完整报告评估系统
- **Rag_Build**：RAG系统构建工具
- **RAG_System**：主RAG系统实现

## 📈 性能特性

- **多种评估模式**：基础、RAG增强、对比分析
- **并发处理**：支持多进程并发评估
- **GPU加速**：使用CUDA实现性能提升
- **批量处理**：高效处理大量报告

---

详细使用说明请参阅：
- [WORKFLOW_GUIDE.md](WORKFLOW_GUIDE.md) - 工作流指南
- [CONCURRENT_GUIDE.md](CONCURRENT_GUIDE.md) - 并发使用指南
- [RAG_SYSTEM_ANALYSIS.md](RAG_SYSTEM_ANALYSIS.md) - 系统分析报告
