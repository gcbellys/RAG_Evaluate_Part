#!/usr/bin/env python3
"""
Report级别的日志记录器
为每个Report提供独立的日志文件
"""

import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List

class ReportLogger:
    """Report级别的日志记录器"""

    def __init__(self, log_dir: str = "logs"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.loggers = {}

    def get_logger(self, report_id: str) -> logging.Logger:
        """获取指定Report的日志记录器"""
        if report_id not in self.loggers:
            # 创建新的日志记录器
            logger = logging.getLogger(f"report_{report_id}")
            logger.setLevel(logging.INFO)

            # 避免重复添加处理器
            if not logger.handlers:
                # 创建文件处理器
                log_file = self.log_dir / f"report_{report_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
                file_handler = logging.FileHandler(log_file, encoding='utf-8')
                file_handler.setLevel(logging.INFO)

                # 创建控制台处理器
                console_handler = logging.StreamHandler(sys.stdout)
                console_handler.setLevel(logging.INFO)

                # 创建格式化器
                formatter = logging.Formatter(
                    '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S'
                )

                file_handler.setFormatter(formatter)
                console_handler.setFormatter(formatter)

                logger.addHandler(file_handler)
                logger.addHandler(console_handler)

            self.loggers[report_id] = logger

        return self.loggers[report_id]

    def log_report_start(self, report_id: str, report_data: Dict[str, Any]):
        """记录Report开始处理"""
        logger = self.get_logger(report_id)
        logger.info(f"🚀 开始处理Report {report_id}")
        logger.info(f"📄 文件路径: {report_data['file_path']}")
        logger.info(f"📊 总症状数: {report_data['total_symptoms']}")
        logger.info(f"✅ 有效症状数: {report_data['valid_symptoms']}")
        logger.info("-" * 50)

    def log_report_complete(self, report_id: str, report_results: Dict[str, Any], report_evaluation: Dict[str, Any]):
        """记录Report处理完成"""
        logger = self.get_logger(report_id)
        logger.info(f"✅ Report {report_id} 处理完成")
        logger.info(f"📊 评估摘要:")
        logger.info(f"   总API调用: {report_evaluation['summary']['total_api_calls']}")
        logger.info(f"   成功调用: {report_evaluation['summary']['successful_api_calls']}")
        logger.info(f"   失败调用: {report_evaluation['summary']['failed_api_calls']}")
        logger.info(f"   平均得分: {report_evaluation['summary']['average_overall_score']}")
        logger.info(f"   平均精确率: {report_evaluation['summary']['average_precision']}%")
        logger.info(f"   平均召回率: {report_evaluation['summary']['average_recall']}%")
        logger.info("-" * 50)

    def log_workflow_summary(self, results: List[Dict[str, Any]]):
        """记录工作流执行摘要"""
        # 创建工作流摘要日志
        workflow_logger = logging.getLogger("workflow_summary")
        workflow_logger.setLevel(logging.INFO)
        
        # 避免重复添加处理器
        if not workflow_logger.handlers:
            log_file = self.log_dir / f"workflow_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
            file_handler = logging.FileHandler(log_file, encoding='utf-8')
            file_handler.setLevel(logging.INFO)
            
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            file_handler.setFormatter(formatter)
            workflow_logger.addHandler(file_handler)
        
        workflow_logger.info("🎉 工作流执行完成")
        workflow_logger.info(f"📊 处理Report总数: {len(results)}")
        
        total_symptoms = sum(r['report_data']['valid_symptoms'] for r in results)
        total_api_calls = sum(r['report_evaluation']['summary']['total_api_calls'] for r in results)
        successful_api_calls = sum(r['report_evaluation']['summary']['successful_api_calls'] for r in results)
        
        workflow_logger.info(f"📝 处理症状总数: {total_symptoms}")
        workflow_logger.info(f"🔌 总API调用数: {total_api_calls}")
        workflow_logger.info(f"✅ 成功API调用数: {successful_api_calls}")
        
        if total_api_calls > 0:
            success_rate = (successful_api_calls / total_api_calls) * 100
            workflow_logger.info(f"📈 API成功率: {success_rate:.1f}%")
        
        # 计算平均分数
        all_scores = []
        for result in results:
            summary = result['report_evaluation']['summary']
            if summary['average_overall_score'] > 0:
                all_scores.append(summary['average_overall_score'])
        
        if all_scores:
            avg_score = sum(all_scores) / len(all_scores)
            workflow_logger.info(f"🎯 平均综合得分: {avg_score:.1f}")
        
        workflow_logger.info("-" * 50)

    def close_all_loggers(self):
        """关闭所有日志记录器"""
        for report_id, logger in self.loggers.items():
            for handler in logger.handlers[:]:
                handler.close()
                logger.removeHandler(handler)
        self.loggers.clear()
