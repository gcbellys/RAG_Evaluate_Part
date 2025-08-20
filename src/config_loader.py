import yaml
import os
from pathlib import Path
from typing import Dict, Any

class ConfigLoader:
    """配置加载器"""
    
    def __init__(self, config_path: str = "config/config.yaml", load_env: bool = True):
        self.config_path = Path(config_path)
        self.config = self._load_config()
        if load_env:
            self._load_env_vars()
    
    def _load_config(self) -> Dict[str, Any]:
        """加载YAML配置文件"""
        if not self.config_path.exists():
            raise FileNotFoundError(f"配置文件不存在: {self.config_path}")
            
        with open(self.config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    
    def _load_env_vars(self):
        """加载环境变量"""
        env_file = self.config_path.parent / ".env"
        if env_file.exists():
            with open(env_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        os.environ[key] = value
    
    def get_api_config(self, provider: str) -> Dict[str, Any]:
        """获取指定API提供商的配置"""
        if provider not in self.config['api_config']:
            raise ValueError(f"不支持的API提供商: {provider}")
            
        api_config = self.config['api_config'][provider].copy()
        
        # 从环境变量获取API密钥
        env_key = f"{provider.upper()}_API_KEY"
        api_config['api_key'] = os.getenv(env_key)
        
        if not api_config['api_key']:
            raise ValueError(f"未找到API密钥: {env_key}")
            
        return api_config
    
    def get_path(self, path_name: str) -> str:
        """获取路径配置"""
        if path_name not in self.config['paths']:
            raise ValueError(f"未找到路径配置: {path_name}")
        return self.config['paths'][path_name]
    
    def get_evaluation_config(self) -> Dict[str, Any]:
        """获取评估配置"""
        return self.config['evaluation']
    
    def get_metrics(self) -> list:
        """获取评估指标列表"""
        return self.config['metrics']
    
    def get_all_api_providers(self) -> list:
        """获取所有支持的API提供商"""
        return list(self.config['api_config'].keys())
