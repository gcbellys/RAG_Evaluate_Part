#!/usr/bin/env python3
"""
API连通性和系统提示词测试脚本
测试5个API的连通性以及系统提示词读取功能
"""

import os
import sys
import json
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from config_loader import ConfigLoader
from api_clients.openai_client import OpenAIClient
from api_clients.anthropic_client import AnthropicClient
from api_clients.google_client import GeminiClient
from api_clients.moonshot_client import MoonshotClient
from api_clients.deepseek_client import DeepseekClient

class APITester:
    """API测试器"""
    
    def __init__(self):
        # 先加载环境变量
        self._load_env_vars()
        # 初始化配置，但不重复加载环境变量
        self.config = ConfigLoader(load_env=False)
        self.system_prompt = self.load_system_prompt()
        self.clients = {}
        self.test_symptom = "chest pain"
        
    def _load_env_vars(self):
        """手动加载环境变量"""
        from pathlib import Path
        env_file = Path("config/.env")
        if env_file.exists():
            with open(env_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            for line in lines:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip().strip('"').strip("'")
                    os.environ[key] = value
        
    def load_system_prompt(self) -> str:
        """加载系统提示词"""
        try:
            prompt_path = self.config.get_path('system_prompt')
            with open(prompt_path, 'r', encoding='utf-8') as f:
                content = f.read()
            print(f"✅ 成功读取系统提示词 ({len(content)} 字符)")
            return content
        except Exception as e:
            print(f"❌ 读取系统提示词失败: {e}")
            return ""
    
    def check_env_variables(self):
        """检查环境变量"""
        print("=== 检查环境变量 ===")
        required_keys = [
            'OPENAI_API_KEY',
            'ANTHROPIC_API_KEY', 
            'GEMINI_API_KEY',
            'MOONSHOT_API_KEY',
            'DEEPSEEK_API_KEY'
        ]
        
        missing_keys = []
        for key in required_keys:
            value = os.getenv(key)
            if value:
                # 只显示前4位和后4位
                masked_value = f"{value[:4]}...{value[-4:]}" if len(value) > 8 else "****"
                print(f"✅ {key}: {masked_value}")
            else:
                print(f"❌ {key}: 未设置")
                missing_keys.append(key)
        
        if missing_keys:
            print(f"\n⚠️  缺少环境变量: {', '.join(missing_keys)}")
            print("请在 config/.env 文件中设置这些API密钥")
            return False
        
        print("✅ 所有环境变量都已设置")
        return True
    
    def initialize_clients(self):
        """初始化所有API客户端"""
        print("\n=== 初始化API客户端 ===")
        
        # OpenAI
        try:
            config = self.config.get_api_config('openai')
            self.clients['openai'] = OpenAIClient(
                api_key=config['api_key'],
                base_url=config.get('base_url'),
                model=config['model']
            )
            print(f"✅ OpenAI客户端初始化成功 (模型: {config['model']})")
        except Exception as e:
            print(f"❌ OpenAI客户端初始化失败: {e}")
        
        # Anthropic
        try:
            config = self.config.get_api_config('anthropic')
            self.clients['anthropic'] = AnthropicClient(
                api_key=config['api_key'],
                model=config['model']
            )
            print(f"✅ Anthropic客户端初始化成功 (模型: {config['model']})")
        except Exception as e:
            print(f"❌ Anthropic客户端初始化失败: {e}")
        
        # Gemini
        try:
            config = self.config.get_api_config('gemini')
            self.clients['gemini'] = GeminiClient(
                api_key=config['api_key'],
                model=config['model']
            )
            print(f"✅ Gemini客户端初始化成功 (模型: {config['model']})")
        except Exception as e:
            print(f"❌ Gemini客户端初始化失败: {e}")
        
        # Moonshot
        try:
            config = self.config.get_api_config('moonshot')
            self.clients['moonshot'] = MoonshotClient(
                api_key=config['api_key'],
                base_url=config['base_url'],
                model=config['model']
            )
            print(f"✅ Moonshot客户端初始化成功 (模型: {config['model']})")
        except Exception as e:
            print(f"❌ Moonshot客户端初始化失败: {e}")
        
        # Deepseek
        try:
            config = self.config.get_api_config('deepseek')
            self.clients['deepseek'] = DeepseekClient(
                api_key=config['api_key'],
                base_url=config['base_url'],
                model=config['model']
            )
            print(f"✅ Deepseek客户端初始化成功 (模型: {config['model']})")
        except Exception as e:
            print(f"❌ Deepseek客户端初始化失败: {e}")
        
        print(f"\n📊 共初始化 {len(self.clients)} 个API客户端")
        return len(self.clients) > 0
    
    def test_api_connectivity(self):
        """测试API连通性"""
        print("\n=== 测试API连通性 ===")
        
        if not self.system_prompt:
            print("❌ 系统提示词为空，跳过API测试")
            return False
        
        results = {}
        
        for client_name, client in self.clients.items():
            print(f"\n🔍 测试 {client_name.upper()} API...")
            
            try:
                result = client.generate_response(
                    system_prompt=self.system_prompt,
                    user_prompt=self.test_symptom,
                    max_tokens=500
                )
                
                if result['success']:
                    response = result['response']
                    print(f"✅ {client_name} 连接成功")
                    print(f"📝 响应长度: {len(response)} 字符")
                    
                    # 尝试解析JSON响应
                    try:
                        # 清理响应文本
                        clean_response = response.strip()
                        if clean_response.startswith('```json'):
                            clean_response = clean_response[7:]
                        if clean_response.endswith('```'):
                            clean_response = clean_response[:-3]
                        
                        parsed = json.loads(clean_response.strip())
                        
                        if 'organName' in parsed and 'anatomicalLocations' in parsed:
                            print(f"✅ JSON格式正确")
                            print(f"   器官: {parsed['organName']}")
                            print(f"   解剖位置: {parsed['anatomicalLocations'][:2]}...")
                            results[client_name] = {'status': 'success', 'parsed': True}
                        else:
                            print(f"⚠️  JSON格式不完整")
                            results[client_name] = {'status': 'success', 'parsed': False}
                            
                    except json.JSONDecodeError as e:
                        print(f"⚠️  JSON解析失败: {e}")
                        print(f"   原始响应: {response[:100]}...")
                        results[client_name] = {'status': 'success', 'parsed': False}
                    
                    # 显示token使用情况
                    if result.get('usage'):
                        usage = result['usage']
                        print(f"📊 Token使用: {usage}")
                        
                else:
                    print(f"❌ {client_name} 请求失败: {result.get('error', '未知错误')}")
                    results[client_name] = {'status': 'failed', 'error': result.get('error')}
                    
            except Exception as e:
                print(f"❌ {client_name} 连接异常: {e}")
                results[client_name] = {'status': 'error', 'error': str(e)}
        
        return results
    
    def generate_test_report(self, results):
        """生成测试报告"""
        print("\n" + "="*50)
        print("📊 测试报告总结")
        print("="*50)
        
        successful = [name for name, result in results.items() if result['status'] == 'success']
        failed = [name for name, result in results.items() if result['status'] != 'success']
        parsed_correctly = [name for name, result in results.items() 
                          if result['status'] == 'success' and result.get('parsed')]
        
        print(f"✅ 连接成功: {len(successful)}/5")
        if successful:
            print(f"   {', '.join(successful)}")
        
        print(f"❌ 连接失败: {len(failed)}/5")
        if failed:
            print(f"   {', '.join(failed)}")
        
        print(f"📝 JSON解析成功: {len(parsed_correctly)}/5")
        if parsed_correctly:
            print(f"   {', '.join(parsed_correctly)}")
        
        if len(successful) == 5:
            print("\n🎉 所有API连接测试通过！系统准备就绪。")
        elif len(successful) >= 3:
            print(f"\n⚠️  部分API可用，可以进行评估测试。")
        else:
            print(f"\n❌ 大部分API不可用，请检查配置和网络连接。")
        
        return len(successful) >= 3
    
    def run_full_test(self):
        """运行完整测试"""
        print("🧪 开始API连通性和系统提示词测试")
        print("="*60)
        
        # 1. 检查环境变量
        if not self.check_env_variables():
            return False
        
        # 2. 初始化客户端
        if not self.initialize_clients():
            print("❌ 没有成功初始化任何API客户端")
            return False
        
        # 3. 测试连通性
        results = self.test_api_connectivity()
        
        # 4. 生成报告
        success = self.generate_test_report(results)
        
        print("\n" + "="*60)
        print("🏁 测试完成")
        
        return success

def main():
    """主函数"""
    tester = APITester()
    success = tester.run_full_test()
    
    if success:
        print("\n下一步：运行 'python run_baseline_evaluation.py --preview' 查看数据统计")
        exit(0)
    else:
        print("\n请修复上述问题后重新运行测试")
        exit(1)

if __name__ == "__main__":
    main()
