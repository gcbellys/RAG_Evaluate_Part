# 项目清理报告

## 📅 清理日期
2025-08-26

## 📁 已移动到 remove/ 文件夹的内容

### 🗂️ 旧的工作流文件
- `compare_workflow.py` - 旧版本的对比工作流，已被新脚本替代
- `quick_start.py` - 快速启动脚本，不再使用
- `debug_json_format.py` - JSON格式调试脚本
- `faiss_retriever.py` - 早期的FAISS检索器，已集成到新系统

### 🛠️ 调试和开发工具 (tools/ 文件夹)
- `check_api_keys.py` - API密钥检查工具
- `client_creation_debug.py` - 客户端创建调试
- `debug_api_manager.py` - API管理器调试
- `debug_api_response.py` - API响应调试
- `debug_full_workflow.py` - 完整工作流调试
- `debug_raw_response.py` - 原始响应调试
- `debug_workflow.py` - 工作流调试
- `detailed_debug.py` - 详细调试
- `env_debug.py` - 环境调试
- `force_test_api.py` - 强制API测试
- `quick_test.py` - 快速测试
- `test_anthropic.py` - Anthropic测试
- `test_fixed_system.py` - 固定系统测试
- `test_individual_clients.py` - 单独客户端测试
- `test_json_extraction.py` - JSON提取测试

### 📊 旧的结果和日志 
- `results/` 文件夹 - 包含大量旧的评估结果文件（约79个文件）
- `logs/` 文件夹 - 包含21个旧的日志文件
- `rag_search_output/` 文件夹 - 根目录版本，现使用 final_result/rag_search_output/

### 📄 示例和文档文件
- `corrected_expected_format_example.json` - 修正的期望格式示例
- `example_user_format_output.json` - 用户格式输出示例
- `expected_organs_analysis.md` - 期望器官分析文档
- `用户期望格式说明.md` - 中文格式说明文档

### 🧹 旧的脚本文件
- `step2_eval_with_rag.sh` - 旧的bash脚本，已被 rerun_with_rag.py 替代
- `step2_rewrite.py` - 重写脚本，已被 rerun_with_rag.py 替代

### 💾 缓存文件
- `__pycache__/` - Python缓存文件夹
- `src_pycache/` - src目录缓存文件
- `utils_pycache/` - utils目录缓存文件

### 📁 空文件夹
- `output/` - 空的输出文件夹

## ✅ 保留的核心文件

### 🚀 主要脚本
- `main_workflow.py` - 基础工作流（不含RAG）
- `comparision_workflow.py` - 对比工作流（可能还需要）
- `rerun_with_rag.py` - 新的主要RAG评估脚本 ⭐
- `run_full_pipeline.py` - 一键运行管道脚本 ⭐

### 📁 核心目录
- `src/` - 核心源代码模块
- `api_clients/` - API客户端实现
- `config/` - 配置文件
- `prompt/` - 提示词模板
- `scripts/` - 有用的脚本（step1, run_rag_pipeline）
- `final_result/` - 新的统一结果目录 ⭐
- `tests/` - 测试代码

### 📋 重要文件
- `requirements.txt` - 项目依赖
- `README.md` - 项目文档

## 🎯 建议

### 可以安全删除
- 所有 `__pycache__` 文件夹（缓存文件）
- `logs/` 文件夹（旧日志）
- `tools/` 文件夹（调试脚本）
- `output/` 空文件夹

### 需要谨慎考虑
- `results/` 文件夹 - 包含历史评估数据，如果不需要对比历史结果可删除
- `rag_search_output/` - 旧版本的RAG输出，已有新版本
- 示例文件 - 如果不需要参考可删除

### 建议保留（短期内）
- `compare_workflow.py` - 可能作为参考
- `quick_start.py` - 可能包含有用的快速启动逻辑
- 文档文件 - 包含项目演进的历史信息

## 📊 清理统计
- 移动的文件夹：8个
- 移动的主要文件：约15个单独文件
- 移动的日志文件：21个
- 移动的结果文件：约79个
- 移动的调试脚本：15个

总计：移动了约130个文件和8个文件夹到 remove/ 目录。

项目目录现在更加整洁，核心功能集中在少数几个主要脚本中。
