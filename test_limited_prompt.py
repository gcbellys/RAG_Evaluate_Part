#!/usr/bin/env python3
"""测试限制器官数量后的prompt效果"""

import sys
sys.path.append('src')
from api_manager import APIManager

# 读取修改后的prompt
with open('prompt/rag_enhanced_prompt.txt', 'r', encoding='utf-8') as f:
    prompt_content = f.read()

# 模拟一个简单的测试
test_symptom = "headache"
test_rag_context = """
参考信息：
1. 器官：Brain，位置：Cerebral Cortex, Meninges
2. 器官：Artery (Arteria)，位置：Cerebral arteries, Meningeal arteries
"""

# 构建完整prompt
full_prompt = f"""
{prompt_content}

症状: {test_symptom}
{test_rag_context}

请根据上述症状和参考信息，预测相关器官和解剖位置。记住：限制输出为1-3个最相关的器官。
"""

print("=== 修改后的Prompt测试 ===")
print("症状:", test_symptom)
print("\n关键指令:")
print("- 限制输出为1-3个器官最多")
print("- 优先选择最直接相关的器官")
print("- 避免过度预测边缘相关的器官")

print(f"\n完整prompt长度: {len(full_prompt)} 字符")
print("\n✅ Prompt已更新，准备测试实际效果")
