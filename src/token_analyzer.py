#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Token使用统计分析器

功能：
1. 分析每个报告的token使用情况
2. 生成token使用汇总报告
3. 计算API调用成本
4. 提供性能优化建议
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
import pandas as pd


class TokenAnalyzer:
    """Token使用分析器"""
    
    # API定价信息 (每1K tokens的价格，单位：美元) - 2024年12月最新定价
    API_PRICING = {
        'openai': {
            'gpt-4': {'input': 0.03, 'output': 0.06},  # 旧版GPT-4: $30/$60 per 1M tokens
            'gpt-4o': {'input': 0.0025, 'output': 0.01},  # GPT-4o: $2.50/$10.00 per 1M tokens
            'gpt-4-turbo': {'input': 0.01, 'output': 0.03},
            'gpt-3.5-turbo': {'input': 0.0015, 'output': 0.002}
        },
        'anthropic': {
            'claude-3-5-sonnet-20241022': {'input': 0.003, 'output': 0.015},  # Claude 3.5 Sonnet: $3/$15 per 1M tokens
            'claude-3-5-sonnet': {'input': 0.003, 'output': 0.015},
            'claude-3-opus': {'input': 0.015, 'output': 0.075},
            'claude-3-sonnet': {'input': 0.003, 'output': 0.015}
        },
        'moonshot': {
            'moonshot-v1-8k': {'input': 0.001, 'output': 0.001},
            'moonshot-v1-32k': {'input': 0.002, 'output': 0.002}
        },
        'deepseek': {
            'deepseek-chat': {'input': 0.0001, 'output': 0.0002},
            'deepseek-coder': {'input': 0.0001, 'output': 0.0002}
        },
        'gemini': {
            'gemini-pro': {'input': 0.00025, 'output': 0.0005},
            'gemini-1.5-pro': {'input': 0.00125, 'output': 0.005},
            'gemini-2.0-flash': {'input': 0.00025, 'output': 0.0005}  # 估算定价
        }
    }
    
    def __init__(self):
        self.report_stats = {}
        self.total_stats = {
            'total_tokens': 0,
            'total_cost': 0.0,
            'api_breakdown': {},
            'model_breakdown': {}
        }
    
    def analyze_report_file(self, file_path: str) -> Dict[str, Any]:
        """分析单个报告文件的token使用情况"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            report_stats = {
                'file_path': file_path,
                'symptoms_count': 0,
                'total_tokens': 0,
                'total_cost': 0.0,
                'api_stats': {},
                'symptom_details': []
            }
            
            # 分析每个症状
            for symptom_key, symptom_data in data.items():
                if isinstance(symptom_data, dict) and 'api_responses' in symptom_data:
                    report_stats['symptoms_count'] += 1
                    symptom_stats = self._analyze_symptom(symptom_key, symptom_data)
                    report_stats['symptom_details'].append(symptom_stats)
                    
                    # 累计统计
                    report_stats['total_tokens'] += symptom_stats['total_tokens']
                    report_stats['total_cost'] += symptom_stats['total_cost']
                    
                    # API统计
                    for api_name, api_stats in symptom_stats['api_stats'].items():
                        if api_name not in report_stats['api_stats']:
                            report_stats['api_stats'][api_name] = {
                                'calls': 0,
                                'total_tokens': 0,
                                'total_cost': 0.0,
                                'avg_tokens': 0
                            }
                        
                        report_stats['api_stats'][api_name]['calls'] += 1
                        report_stats['api_stats'][api_name]['total_tokens'] += api_stats['total_tokens']
                        report_stats['api_stats'][api_name]['total_cost'] += api_stats['cost']
            
            # 计算平均值
            for api_name in report_stats['api_stats']:
                api_stat = report_stats['api_stats'][api_name]
                if api_stat['calls'] > 0:
                    api_stat['avg_tokens'] = api_stat['total_tokens'] / api_stat['calls']
            
            return report_stats
            
        except Exception as e:
            print(f"❌ 分析文件失败 {file_path}: {e}")
            return None
    
    def _analyze_symptom(self, symptom_key: str, symptom_data: Dict) -> Dict[str, Any]:
        """分析单个症状的token使用情况"""
        symptom_stats = {
            'symptom': symptom_key,
            'total_tokens': 0,
            'total_cost': 0.0,
            'api_stats': {}
        }
        
        api_responses = symptom_data.get('api_responses', {})
        
        for api_name, response_data in api_responses.items():
            if 'usage' in response_data and response_data['usage']:
                usage = response_data['usage']
                model = response_data.get('model', 'unknown')
                
                # 提取token信息
                prompt_tokens = usage.get('prompt_tokens', 0)
                completion_tokens = usage.get('completion_tokens', 0)
                total_tokens = usage.get('total_tokens', prompt_tokens + completion_tokens)
                
                # 计算成本
                cost = self._calculate_cost(api_name, model, prompt_tokens, completion_tokens)
                
                symptom_stats['api_stats'][api_name] = {
                    'model': model,
                    'prompt_tokens': prompt_tokens,
                    'completion_tokens': completion_tokens,
                    'total_tokens': total_tokens,
                    'cost': cost,
                    'cached_tokens': usage.get('cached_tokens', 0),
                    'cache_hit_tokens': usage.get('prompt_cache_hit_tokens', 0)
                }
                
                symptom_stats['total_tokens'] += total_tokens
                symptom_stats['total_cost'] += cost
        
        return symptom_stats
    
    def _calculate_cost(self, api_name: str, model: str, prompt_tokens: int, completion_tokens: int) -> float:
        """计算API调用成本"""
        try:
            # 标准化API名称
            api_name = api_name.lower()
            
            # 查找定价信息
            if api_name in self.API_PRICING:
                api_pricing = self.API_PRICING[api_name]
                
                # 查找具体模型定价
                model_pricing = None
                for model_key, pricing in api_pricing.items():
                    if model_key in model.lower():
                        model_pricing = pricing
                        break
                
                if not model_pricing:
                    # 使用默认定价（第一个模型的定价）
                    model_pricing = list(api_pricing.values())[0]
                
                # 计算成本 (价格是每1K tokens)
                input_cost = (prompt_tokens / 1000) * model_pricing['input']
                output_cost = (completion_tokens / 1000) * model_pricing['output']
                
                return input_cost + output_cost
            
            return 0.0
            
        except Exception as e:
            print(f"⚠️ 计算成本失败 {api_name}/{model}: {e}")
            return 0.0
    
    def analyze_directory(self, directory_path: str, file_pattern: str = "*.json") -> Dict[str, Any]:
        """分析目录中的所有报告文件"""
        directory = Path(directory_path)
        
        if not directory.exists():
            raise FileNotFoundError(f"目录不存在: {directory_path}")
        
        # 查找所有匹配的文件
        json_files = list(directory.glob(file_pattern))
        
        if not json_files:
            print(f"⚠️ 在 {directory_path} 中未找到匹配的文件")
            return {}
        
        print(f"📁 找到 {len(json_files)} 个文件进行分析...")
        
        all_reports = {}
        
        for file_path in json_files:
            print(f"🔍 分析文件: {file_path.name}")
            report_stats = self.analyze_report_file(str(file_path))
            
            if report_stats:
                report_id = file_path.stem
                all_reports[report_id] = report_stats
        
        return all_reports
    
    def generate_summary_report(self, reports_data: Dict[str, Any], output_file: str = None) -> str:
        """生成token使用汇总报告"""
        
        # 计算总体统计
        total_reports = len(reports_data)
        total_symptoms = sum(report['symptoms_count'] for report in reports_data.values())
        total_tokens = sum(report['total_tokens'] for report in reports_data.values())
        total_cost = sum(report['total_cost'] for report in reports_data.values())
        
        # API统计汇总
        api_summary = {}
        for report in reports_data.values():
            for api_name, api_stats in report['api_stats'].items():
                if api_name not in api_summary:
                    api_summary[api_name] = {
                        'total_calls': 0,
                        'total_tokens': 0,
                        'total_cost': 0.0,
                        'avg_tokens_per_call': 0
                    }
                
                api_summary[api_name]['total_calls'] += api_stats['calls']
                api_summary[api_name]['total_tokens'] += api_stats['total_tokens']
                api_summary[api_name]['total_cost'] += api_stats['total_cost']
        
        # 计算平均值
        for api_stats in api_summary.values():
            if api_stats['total_calls'] > 0:
                api_stats['avg_tokens_per_call'] = api_stats['total_tokens'] / api_stats['total_calls']
        
        # 生成报告内容
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        report_content = f"""
# 🔢 Token使用统计汇总报告

**生成时间**: {timestamp}

## 📊 总体统计

- **分析报告数**: {total_reports:,}
- **总症状数**: {total_symptoms:,}
- **总Token使用量**: {total_tokens:,}
- **总预估成本**: ${total_cost:.4f}
- **平均每报告Token数**: {total_tokens/total_reports if total_reports > 0 else 0:,.0f}
- **平均每症状Token数**: {total_tokens/total_symptoms if total_symptoms > 0 else 0:,.0f}

## 🔌 API使用统计

"""
        
        for api_name, stats in sorted(api_summary.items()):
            percentage = (stats['total_cost'] / total_cost * 100) if total_cost > 0 else 0
            report_content += f"""
### {api_name.upper()}
- **调用次数**: {stats['total_calls']:,}
- **Token使用量**: {stats['total_tokens']:,}
- **预估成本**: ${stats['total_cost']:.4f} ({percentage:.1f}%)
- **平均每次调用Token数**: {stats['avg_tokens_per_call']:.0f}
"""
        
        # 详细报告统计
        report_content += f"""

## 📋 详细报告统计

| 报告ID | 症状数 | 总Token数 | 预估成本 | 平均每症状Token数 |
|--------|--------|-----------|----------|-------------------|
"""
        
        for report_id, report_data in sorted(reports_data.items()):
            avg_tokens_per_symptom = report_data['total_tokens'] / report_data['symptoms_count'] if report_data['symptoms_count'] > 0 else 0
            report_content += f"| {report_id} | {report_data['symptoms_count']} | {report_data['total_tokens']:,} | ${report_data['total_cost']:.4f} | {avg_tokens_per_symptom:.0f} |\n"
        
        # 优化建议
        report_content += f"""

## 💡 优化建议

### 成本优化
1. **API选择**: DeepSeek成本最低，适合大批量处理
2. **缓存利用**: DeepSeek显示了良好的缓存命中率，可节省成本
3. **Prompt优化**: 减少不必要的上下文信息

### 性能优化
1. **批量处理**: 考虑批量API调用减少网络开销
2. **并发控制**: 合理设置并发数避免API限制
3. **结果缓存**: 对相似症状使用缓存结果

### 质量优化
1. **模型选择**: 根据任务复杂度选择合适的模型
2. **Prompt工程**: 优化提示词提高输出质量
3. **结果验证**: 增加结果一致性检查
"""
        
        # 保存报告
        if output_file:
            output_path = Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(report_content)
            
            print(f"✅ Token统计报告已保存: {output_file}")
        
        return report_content
    
    def export_to_csv(self, reports_data: Dict[str, Any], output_file: str):
        """导出详细数据到CSV"""
        rows = []
        
        for report_id, report_data in reports_data.items():
            for symptom_detail in report_data['symptom_details']:
                for api_name, api_stats in symptom_detail['api_stats'].items():
                    rows.append({
                        'report_id': report_id,
                        'symptom': symptom_detail['symptom'][:50] + '...' if len(symptom_detail['symptom']) > 50 else symptom_detail['symptom'],
                        'api_name': api_name,
                        'model': api_stats['model'],
                        'prompt_tokens': api_stats['prompt_tokens'],
                        'completion_tokens': api_stats['completion_tokens'],
                        'total_tokens': api_stats['total_tokens'],
                        'cost': api_stats['cost'],
                        'cached_tokens': api_stats.get('cached_tokens', 0),
                        'cache_hit_tokens': api_stats.get('cache_hit_tokens', 0)
                    })
        
        df = pd.DataFrame(rows)
        df.to_csv(output_file, index=False, encoding='utf-8')
        print(f"✅ 详细数据已导出到CSV: {output_file}")


def main():
    """主函数 - 命令行接口"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Token使用统计分析器")
    parser.add_argument("directory", help="包含结果文件的目录路径")
    parser.add_argument("--output", "-o", help="输出报告文件路径")
    parser.add_argument("--csv", help="导出CSV文件路径")
    parser.add_argument("--pattern", default="*.json", help="文件匹配模式 (默认: *.json)")
    
    args = parser.parse_args()
    
    # 创建分析器
    analyzer = TokenAnalyzer()
    
    try:
        # 分析目录
        print(f"🔍 开始分析目录: {args.directory}")
        reports_data = analyzer.analyze_directory(args.directory, args.pattern)
        
        if not reports_data:
            print("❌ 未找到有效的报告数据")
            return
        
        # 生成汇总报告
        output_file = args.output or f"token_analysis_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        report_content = analyzer.generate_summary_report(reports_data, output_file)
        
        # 导出CSV
        if args.csv:
            analyzer.export_to_csv(reports_data, args.csv)
        
        # 显示简要统计
        total_reports = len(reports_data)
        total_tokens = sum(report['total_tokens'] for report in reports_data.values())
        total_cost = sum(report['total_cost'] for report in reports_data.values())
        
        print(f"\n📊 分析完成!")
        print(f"   📋 分析报告数: {total_reports}")
        print(f"   🔢 总Token数: {total_tokens:,}")
        print(f"   💰 总预估成本: ${total_cost:.4f}")
        
    except Exception as e:
        print(f"❌ 分析失败: {e}")


if __name__ == "__main__":
    main()
