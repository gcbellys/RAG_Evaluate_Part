#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
完整的RAG评估workflow - 使用修复后的系统和新的平衡版prompt
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path
import argparse

def run_command(cmd: str, description: str) -> bool:
    """运行命令并显示结果"""
    print(f"\n🚀 {description}")
    print(f"💻 命令: {cmd}")
    print("=" * 80)
    
    try:
        result = subprocess.run(cmd, shell=True, check=True, text=True)
        print("=" * 80)
        print(f"✅ {description} - 成功完成")
        return True
    except subprocess.CalledProcessError as e:
        print("=" * 80)
        print(f"❌ {description} - 失败 (退出码: {e.returncode})")
        return False

def backup_original_prompt():
    """备份原始prompt"""
    original_prompt = Path("prompt/rag_enhanced_prompt.txt")
    backup_prompt = Path("prompt/rag_enhanced_prompt_original_backup.txt")
    
    if original_prompt.exists() and not backup_prompt.exists():
        shutil.copy2(original_prompt, backup_prompt)
        print(f"✅ 已备份原始prompt: {backup_prompt}")
        return True
    return False

def use_balanced_prompt():
    """使用平衡版prompt替换原始prompt"""
    balanced_prompt = Path("prompt/rag_enhanced_prompt_balanced.txt")
    target_prompt = Path("prompt/rag_enhanced_prompt.txt")
    
    if balanced_prompt.exists():
        # 备份原始prompt
        backup_original_prompt()
        
        # 复制平衡版prompt
        shutil.copy2(balanced_prompt, target_prompt)
        print(f"✅ 已启用平衡版prompt: {target_prompt}")
        return True
    else:
        print(f"❌ 平衡版prompt不存在: {balanced_prompt}")
        return False

def restore_original_prompt():
    """恢复原始prompt"""
    backup_prompt = Path("prompt/rag_enhanced_prompt_original_backup.txt")
    target_prompt = Path("prompt/rag_enhanced_prompt.txt")
    
    if backup_prompt.exists():
        shutil.copy2(backup_prompt, target_prompt)
        print(f"✅ 已恢复原始prompt: {target_prompt}")
        return True
    return False

def run_complete_rag_evaluation(report_id: int, 
                               rag_db_type: str = "uniform",
                               top_k: int = 3,
                               config_file: str = "config/config_rag3db.yaml",
                               data_dir: str = "/home/duojiechen/Central_Data/Testset_0_43000-43508/diagnostic_results_normalized",
                               use_balanced_prompt_flag: bool = True) -> bool:
    """运行完整的RAG评估流程"""
    
    print("🎯 完整RAG评估流程 - 使用修复后的系统")
    print("=" * 80)
    print(f"📊 报告ID: {report_id}")
    print(f"🗃️  RAG数据库: {rag_db_type}")
    print(f"🔍 Top-K: {top_k}")
    print(f"⚙️  配置文件: {config_file}")
    print(f"📁 数据目录: {data_dir}")
    print(f"🎯 使用平衡版prompt: {use_balanced_prompt_flag}")
    print("=" * 80)
    
    success = True
    
    try:
        # Step 0: 切换到平衡版prompt（如果需要）
        if use_balanced_prompt_flag:
            print("\n🔧 Step 0: 启用平衡版prompt")
            if not use_balanced_prompt():
                print("⚠️  无法启用平衡版prompt，使用原始prompt继续")
        
        # Step 1: RAG检索
        print(f"\n🔍 Step 1: RAG检索阶段")
        rag_cmd = f"bash scripts/step1_rag3db_retrieve.sh {report_id} {report_id} {top_k} {rag_db_type} {config_file} --data-dir {data_dir}"
        
        if not run_command(rag_cmd, f"RAG检索 ({rag_db_type})"):
            print("❌ RAG检索失败，无法继续")
            return False
        
        # Step 2: 基线评估（如果不存在）
        print(f"\n📊 Step 2: 基线评估阶段")
        baseline_cmd = f"python workflows/rerun_with_rag.py {report_id} --config {config_file} --data_dir {data_dir} --baseline_only"
        
        if not run_command(baseline_cmd, "基线评估"):
            print("⚠️  基线评估失败，但继续RAG评估")
        
        # Step 3: RAG增强评估
        print(f"\n🚀 Step 3: RAG增强评估阶段")
        
        # 根据RAG数据库类型设置缓存目录
        rag_cache_dir = f"results/rag_output_{rag_db_type}"
        
        rag_eval_cmd = f"python workflows/rerun_with_rag.py {report_id} --config {config_file} --data_dir {data_dir} --rag_cache_dir {rag_cache_dir}"
        
        if not run_command(rag_eval_cmd, "RAG增强评估"):
            print("❌ RAG增强评估失败")
            success = False
        
        # Step 4: 结果分析
        print(f"\n📈 Step 4: 结果分析")
        print("✅ 评估完成，结果文件位置:")
        
        # 检查结果文件
        result_dirs = [
            f"results/baseline_results",
            f"results/rerun_with_rag", 
            f"results/rerun_comparisons",
            f"results/rag_output_{rag_db_type}"
        ]
        
        for result_dir in result_dirs:
            if os.path.exists(result_dir):
                files = list(Path(result_dir).glob(f"*{report_id}*"))
                if files:
                    print(f"   📁 {result_dir}: {len(files)} 个文件")
                    for file in files[:3]:  # 显示前3个文件
                        print(f"      • {file.name}")
                    if len(files) > 3:
                        print(f"      • ... 还有 {len(files)-3} 个文件")
        
        if success:
            print(f"\n🎉 报告 {report_id} 完整评估成功!")
            print(f"💡 使用了修复后的系统特性:")
            print(f"   ✅ 多器官支持 (API管理器修复)")
            print(f"   ✅ 多器官簇RAG预处理")
            print(f"   ✅ 优化的参数设置")
            if use_balanced_prompt_flag:
                print(f"   ✅ 平衡版prompt (精准但全面)")
        
    except Exception as e:
        print(f"❌ 评估过程异常: {e}")
        success = False
    
    finally:
        # 恢复原始prompt（如果修改了）
        if use_balanced_prompt_flag:
            print(f"\n🔄 恢复原始prompt设置")
            restore_original_prompt()
    
    return success

def compare_multiple_databases(report_id: int,
                             config_file: str = "config/config_rag3db.yaml",
                             data_dir: str = "/home/duojiechen/Central_Data/Testset_0_43000-43508/diagnostic_results_normalized",
                             top_k: int = 3) -> bool:
    """对比所有三个RAG数据库"""
    
    print("🔄 多数据库对比评估")
    print("=" * 80)
    
    databases = ['uniform', 'report_context', 'sequential_block']
    success_count = 0
    
    for i, db_type in enumerate(databases, 1):
        print(f"\n📊 评估数据库 {i}/3: {db_type}")
        
        if run_complete_rag_evaluation(
            report_id=report_id,
            rag_db_type=db_type,
            top_k=top_k,
            config_file=config_file,
            data_dir=data_dir,
            use_balanced_prompt_flag=True
        ):
            success_count += 1
            print(f"✅ {db_type} 数据库评估成功")
        else:
            print(f"❌ {db_type} 数据库评估失败")
    
    print(f"\n📊 多数据库评估结果: {success_count}/{len(databases)} 成功")
    
    if success_count > 0:
        print(f"\n📋 建议下一步:")
        print(f"   1. 运行分析脚本对比结果")
        print(f"   2. 查看修复效果验证")
        print(f"   3. 生成性能对比报告")
    
    return success_count == len(databases)

def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="完整RAG评估workflow - 使用修复后的系统",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用修复后的系统特性:
  ✅ API管理器多器官支持
  ✅ RAG预处理多器官簇支持  
  ✅ 优化的默认参数
  ✅ 平衡版prompt (可选)

示例:
  python test_complete_workflow_fixed.py 43001
  python test_complete_workflow_fixed.py 43001 --rag_db_type report_context
  python test_complete_workflow_fixed.py 43001 --compare_all_dbs
  python test_complete_workflow_fixed.py 43001 --no_balanced_prompt
        """
    )
    
    parser.add_argument("report_id", type=int, help="报告ID")
    parser.add_argument("--rag_db_type", default="uniform",
                       choices=['uniform', 'report_context', 'sequential_block'],
                       help="RAG数据库类型")
    parser.add_argument("--top_k", type=int, default=3, help="RAG检索top_k")
    parser.add_argument("--config", default="config/config_rag3db.yaml", help="配置文件")
    parser.add_argument("--data_dir", 
                       default="/home/duojiechen/Central_Data/Testset_0_43000-43508/diagnostic_results_normalized",
                       help="数据目录")
    parser.add_argument("--compare_all_dbs", action="store_true", help="对比所有数据库")
    parser.add_argument("--no_balanced_prompt", action="store_true", help="不使用平衡版prompt")
    
    args = parser.parse_args()
    
    # 检查数据目录
    if not os.path.exists(args.data_dir):
        print(f"❌ 数据目录不存在: {args.data_dir}")
        return False
    
    # 检查配置文件
    if not os.path.exists(args.config):
        print(f"❌ 配置文件不存在: {args.config}")
        return False
    
    use_balanced = not args.no_balanced_prompt
    
    if args.compare_all_dbs:
        success = compare_multiple_databases(
            report_id=args.report_id,
            config_file=args.config,
            data_dir=args.data_dir,
            top_k=args.top_k
        )
    else:
        success = run_complete_rag_evaluation(
            report_id=args.report_id,
            rag_db_type=args.rag_db_type,
            top_k=args.top_k,
            config_file=args.config,
            data_dir=args.data_dir,
            use_balanced_prompt_flag=use_balanced
        )
    
    if success:
        print(f"\n🎉 完整workflow执行成功!")
        print(f"🚀 修复后的RAG系统已验证工作正常!")
    else:
        print(f"\n❌ workflow执行失败，请检查错误信息")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
