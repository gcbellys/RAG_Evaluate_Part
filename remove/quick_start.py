#!/usr/bin/env python3
"""
重构后的快速启动脚本
"""

from main_workflow import SimpleRAGWorkflow

def main():
    """快速启动"""
    print("🚀 重构后的RAG评估快速启动")
    print("=" * 50)
    
    # 创建工作流实例
    workflow = SimpleRAGWorkflow()
    
    # 运行工作流（测试范围）
    success = workflow.run(start_id=4000, end_id=4000)
    
    if success:
        print("\n✅ 快速启动成功！")
    else:
        print("\n❌ 快速启动失败！")

if __name__ == "__main__":
    main()
