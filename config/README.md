# 配置文件说明

## 1. 创建 .env 文件

请在 `config/` 目录下创建一个名为 `.env` 的文件，内容如下：

```bash
# API密钥配置
OPENAI_API_KEY=your_openai_api_key_here
ANTHROPIC_API_KEY=your_anthropic_api_key_here
GEMINI_API_KEY=your_gemini_api_key_here
MOONSHOT_API_KEY=your_moonshot_api_key_here
DEEPSEEK_API_KEY=your_deepseek_api_key_here
```

请将 `your_xxx_api_key_here` 替换为您的实际API密钥。

## 2. config.yaml 配置说明

- **api_config**: 包含5个API提供商的URL地址和模型信息
- **paths**: 包含系统提示词、输入数据、输出结果的路径
- **evaluation**: 评估相关配置参数
- **metrics**: 评估指标列表

## 3. 注意事项

- `.env` 文件包含敏感信息，请确保不要提交到版本控制系统
- 所有路径都是相对于项目根目录的相对路径
- API密钥会通过环境变量自动加载
