#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
获取配置文件中的输出路径
用于bash脚本调用
"""
import sys
from pathlib import Path

# 添加src目录到Python路径
sys.path.append(str(Path(__file__).resolve().parent.parent / "src"))

from config_loader import ConfigLoader

def get_output_path(config_path: str = "config/config.yaml") -> str:
    """获取输出路径"""
    try:
        project_root = Path(__file__).resolve().parent.parent
        
        # 如果config_path是绝对路径，直接使用；否则相对于项目根目录
        if Path(config_path).is_absolute():
            full_config_path = config_path
        else:
            full_config_path = str(project_root / config_path)
            
        config = ConfigLoader(full_config_path)
        output_base = config.get_path('output_results')
        
        # 如果output_base是绝对路径，直接使用；否则相对于项目根目录
        if Path(output_base).is_absolute():
            full_path = Path(output_base) / "rag_search_output"
        else:
            full_path = project_root / output_base / "rag_search_output"
            
        return str(full_path)
    except Exception as e:
        # 如果出错，返回默认路径
        project_root = Path(__file__).resolve().parent.parent
        return str(project_root / "final_result" / "rag_search_output")

if __name__ == "__main__":
    config_path = sys.argv[1] if len(sys.argv) > 1 else "config/config.yaml"
    print(get_output_path(config_path))
