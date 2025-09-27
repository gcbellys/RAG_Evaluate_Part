#!/usr/bin/env python3
"""
测试JSON提取功能
"""

import re
import json

def test_json_extraction():
    """测试JSON提取"""
    print("🧪 测试JSON提取功能")
    print("=" * 50)
    
    # 测试文本（模拟API响应）
    test_text = '''```json
{
  "organs": [
    {
      "organName": "Heart (Cor)",
      "anatomicalLocations": [
        "Aortic Valve",
        "Left Ventricle (LV)",
        "Aortic Root & Ascending Aorta"
      ],
      "relevance": "High"
    }
  ]
}
```'''
    
    print("📝 测试文本:")
    print(test_text)
    print("\n" + "="*50)
    
    # 测试正则表达式
    print("🔍 测试正则表达式...")
    
    # 方法1: 移除Markdown代码块标记
    json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', test_text, re.DOTALL)
    if json_match:
        json_str = json_match.group(1)
        print(f"✅ 方法1成功: {json_str[:100]}...")
        
        # 尝试解析JSON
        try:
            data = json.loads(json_str)
            print(f"✅ JSON解析成功!")
            print(f"   器官名称: {data['organs'][0]['organName']}")
            print(f"   解剖位置: {data['organs'][0]['anatomicalLocations']}")
        except json.JSONDecodeError as e:
            print(f"❌ JSON解析失败: {e}")
    else:
        print("❌ 方法1失败")
    
    # 方法2: 直接查找JSON
    print("\n🔍 方法2: 直接查找JSON...")
    json_match2 = re.search(r'(\{.*\})', test_text, re.DOTALL)
    if json_match2:
        json_str2 = json_match2.group(1)
        print(f"✅ 方法2成功: {json_str2[:100]}...")
        
        # 尝试解析JSON
        try:
            data2 = json.loads(json_str2)
            print(f"✅ JSON解析成功!")
            print(f"   器官名称: {data2['organs'][0]['organName']}")
            print(f"   解剖位置: {data2['organs'][0]['anatomicalLocations']}")
        except json.JSONDecodeError as e:
            print(f"❌ JSON解析失败: {e}")
    else:
        print("❌ 方法2失败")

def test_with_real_response():
    """使用真实API响应测试"""
    print("\n🧪 使用真实API响应测试")
    print("=" * 50)
    
    real_response = '''```json
{
  "organs": [
    {
      "organName": "Heart (Cor)",
      "anatomicalLocations": [
        "Aortic Valve",
        "Left Ventricle (LV)",
        "Aortic Root & Ascending Aorta"
      ],
      "relevance": "High"
    },
    {
      "organName": "Artery (Arteria)",
      "anatomicalLocations": [
        "Aorta",
        "Ascending Aorta"
      ],
      "relevance": "Medium"
    }
  ]
}
```'''
    
    print("📝 真实API响应:")
    print(real_response)
    print("\n" + "="*50)
    
    # 测试提取
    json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', real_response, re.DOTALL)
    if json_match:
        json_str = json_match.group(1)
        print(f"✅ JSON提取成功!")
        
        try:
            data = json.loads(json_str)
            print(f"✅ JSON解析成功!")
            print(f"   找到 {len(data['organs'])} 个器官:")
            for i, organ in enumerate(data['organs']):
                print(f"   {i+1}. {organ['organName']}: {organ['anatomicalLocations']}")
        except json.JSONDecodeError as e:
            print(f"❌ JSON解析失败: {e}")
    else:
        print("❌ JSON提取失败")

if __name__ == "__main__":
    test_json_extraction()
    test_with_real_response()
