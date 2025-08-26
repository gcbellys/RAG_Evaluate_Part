#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
并发RAG评估脚本

同时运行两个不同配置的评估任务：
1. config.yaml: 报告4000-4100
2. config_cn.yaml: 报告4050-4200

用法:
    python run_concurrent_evaluation.py
    python run_concurrent_evaluation.py --workflow full
    python run_concurrent_evaluation.py --workflow baseline
"""

import argparse
import subprocess
import sys
import threading
import time
from datetime import datetime
from pathlib import Path


class ConcurrentEvaluator:
    """并发评估管理器"""
    
    def __init__(self):
        self.results = {}
        self.start_time = None
        
    def run_task(self, task_name: str, command: str, log_file: str):
        """运行单个任务"""
        print(f"\n🚀 [{task_name}] 开始执行")
        print(f"💻 [{task_name}] 命令: {command}")
        print(f"📝 [{task_name}] 日志: {log_file}")
        
        try:
            with open(log_file, 'w', encoding='utf-8') as log:
                log.write(f"=== {task_name} 执行日志 ===\n")
                log.write(f"开始时间: {datetime.now().isoformat()}\n")
                log.write(f"命令: {command}\n")
                log.write("=" * 50 + "\n\n")
                log.flush()
                
                # 执行命令并实时写入日志
                process = subprocess.Popen(
                    command,
                    shell=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                    universal_newlines=True
                )
                
                # 实时输出和写入日志
                for line in iter(process.stdout.readline, ''):
                    print(f"[{task_name}] {line.rstrip()}")
                    log.write(line)
                    log.flush()
                
                process.wait()
                
                log.write(f"\n" + "=" * 50 + "\n")
                log.write(f"结束时间: {datetime.now().isoformat()}\n")
                log.write(f"返回码: {process.returncode}\n")
                
                if process.returncode == 0:
                    print(f"✅ [{task_name}] 执行成功")
                    self.results[task_name] = {'status': 'success', 'returncode': 0}
                else:
                    print(f"❌ [{task_name}] 执行失败 (返回码: {process.returncode})")
                    self.results[task_name] = {'status': 'failed', 'returncode': process.returncode}
                    
        except Exception as e:
            error_msg = f"执行异常: {str(e)}"
            print(f"❌ [{task_name}] {error_msg}")
            self.results[task_name] = {'status': 'error', 'error': error_msg}
            
            # 写入错误到日志
            try:
                with open(log_file, 'a', encoding='utf-8') as log:
                    log.write(f"\n错误: {error_msg}\n")
            except:
                pass
    
    def run_concurrent(self, workflow: str = "full"):
        """并发运行两个评估任务"""
        self.start_time = datetime.now()
        
        print("=" * 80)
        print("🎯 并发RAG评估系统")
        print("=" * 80)
        print(f"🕐 开始时间: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"🔄 工作流程: {workflow}")
        print("📋 任务配置:")
        print("   Task 1: config.yaml → 报告 4000-4100")
        print("   Task 2: config_cn.yaml → 报告 4050-4200")
        
        # 创建日志目录
        log_dir = Path("concurrent_logs")
        log_dir.mkdir(exist_ok=True)
        
        timestamp = self.start_time.strftime("%Y%m%d_%H%M%S")
        
        # 定义任务
        tasks = [
            {
                'name': 'Task1_Config_Default',
                'command': f'python start_evaluation.py {workflow} 4000 4100 --config config/config.yaml',
                'log_file': log_dir / f'task1_default_{timestamp}.log'
            },
            {
                'name': 'Task2_Config_CN',
                'command': f'python start_evaluation.py {workflow} 4050 4200 --config config/config_cn.yaml',
                'log_file': log_dir / f'task2_cn_{timestamp}.log'
            }
        ]
        
        # 创建线程
        threads = []
        for task in tasks:
            thread = threading.Thread(
                target=self.run_task,
                args=(task['name'], task['command'], str(task['log_file']))
            )
            threads.append(thread)
        
        # 启动所有线程
        print(f"\n🚀 启动 {len(threads)} 个并发任务...")
        for thread in threads:
            thread.start()
            time.sleep(2)  # 错开启动时间，避免资源冲突
        
        # 等待所有线程完成
        print("\n⏳ 等待所有任务完成...")
        for i, thread in enumerate(threads):
            thread.join()
            print(f"📊 任务 {i+1}/{len(threads)} 已完成")
        
        # 生成总结报告
        self.generate_summary_report(timestamp, workflow, log_dir)
    
    def generate_summary_report(self, timestamp: str, workflow: str, log_dir: Path):
        """生成总结报告"""
        end_time = datetime.now()
        duration = end_time - self.start_time
        
        print("\n" + "=" * 80)
        print("📈 并发评估总结报告")
        print("=" * 80)
        print(f"🕐 开始时间: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"🕐 结束时间: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"⏱️  总耗时: {duration}")
        print(f"🔄 工作流程: {workflow}")
        
        # 任务状态统计
        success_count = sum(1 for r in self.results.values() if r['status'] == 'success')
        failed_count = sum(1 for r in self.results.values() if r['status'] == 'failed')
        error_count = sum(1 for r in self.results.values() if r['status'] == 'error')
        
        print(f"\n📊 任务执行结果:")
        print(f"   ✅ 成功: {success_count}")
        print(f"   ❌ 失败: {failed_count}")
        print(f"   🚨 异常: {error_count}")
        
        print(f"\n📋 详细结果:")
        for task_name, result in self.results.items():
            status_icon = "✅" if result['status'] == 'success' else "❌"
            print(f"   {status_icon} {task_name}: {result['status']}")
            if 'returncode' in result:
                print(f"      返回码: {result['returncode']}")
            if 'error' in result:
                print(f"      错误: {result['error']}")
        
        # 生成总结报告文件
        summary_file = log_dir / f'concurrent_summary_{timestamp}.txt'
        with open(summary_file, 'w', encoding='utf-8') as f:
            f.write("并发RAG评估总结报告\n")
            f.write("=" * 50 + "\n\n")
            f.write(f"开始时间: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"结束时间: {end_time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"总耗时: {duration}\n")
            f.write(f"工作流程: {workflow}\n\n")
            
            f.write("任务配置:\n")
            f.write("Task 1: config.yaml → 报告 4000-4100\n")
            f.write("Task 2: config_cn.yaml → 报告 4050-4200\n\n")
            
            f.write("执行结果:\n")
            for task_name, result in self.results.items():
                f.write(f"- {task_name}: {result['status']}\n")
                if 'returncode' in result:
                    f.write(f"  返回码: {result['returncode']}\n")
                if 'error' in result:
                    f.write(f"  错误: {result['error']}\n")
        
        print(f"\n📄 详细日志文件:")
        for log_file in log_dir.glob(f'*_{timestamp}.log'):
            print(f"   📝 {log_file}")
        print(f"\n📄 总结报告: {summary_file}")
        
        # 结果文件位置提示
        print(f"\n📁 结果文件位置:")
        print("   🔍 RAG缓存: final_result/rag_search_output/")
        print("   📊 基础结果: final_result/baseline_results/")
        print("   🤖 RAG增强结果: final_result/rerun_with_rag/")
        print("   📈 对比分析: final_result/rerun_comparisons/")
        
        if success_count == len(self.results):
            print("\n🎉 所有任务执行成功！")
        else:
            print(f"\n⚠️  部分任务执行失败，请查看日志文件排查问题")
        
        print("=" * 80)


def main():
    parser = argparse.ArgumentParser(
        description="并发运行两个配置的RAG评估",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
任务配置:
  Task 1: config.yaml → 报告 4000-4100 (使用MOONSHOT_API_KEY, DEEPSEEK_API_KEY)
  Task 2: config_cn.yaml → 报告 4050-4200 (使用MOONSHOT_API_KEY_2, DEEPSEEK_API_KEY_2)

示例:
  python run_concurrent_evaluation.py                # 默认运行完整流程
  python run_concurrent_evaluation.py --workflow full      # 完整RAG评估
  python run_concurrent_evaluation.py --workflow baseline  # 仅基础评估
        """
    )
    
    parser.add_argument("--workflow", choices=["full", "baseline", "rag-only"], 
                        default="full", help="选择工作流程类型 (默认: full)")
    
    args = parser.parse_args()
    
    # 检查必要的环境变量
    import os
    required_env_vars = [
        'MOONSHOT_API_KEY', 'DEEPSEEK_API_KEY',
        'MOONSHOT_API_KEY_2', 'DEEPSEEK_API_KEY_2'
    ]
    
    missing_vars = [var for var in required_env_vars if not os.getenv(var)]
    if missing_vars:
        print("❌ 缺少必要的环境变量:")
        for var in missing_vars:
            print(f"   - {var}")
        print("\n请确保设置了所有必要的API密钥环境变量")
        sys.exit(1)
    
    # 创建评估器并运行
    evaluator = ConcurrentEvaluator()
    evaluator.run_concurrent(args.workflow)


if __name__ == "__main__":
    main()
