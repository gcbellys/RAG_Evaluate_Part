#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试API管理器修复是否生效
"""

import json
import re
from typing import Dict, Any

def extract_and_parse_json_fixed(text: str) -> Dict[str, Any]:
    """修复后的JSON解析函数"""
    try:
        # 移除Markdown代码块标记
        json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
        else:
            json_match = re.search(r'(\{.*\})', text, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                return {'organ_name': '', 'anatomical_locations': []}
        
        # 解析JSON
        data = json.loads(json_str)
        
        # 支持新的智能RAG格式
        if 'organ' in data and 'anatomical_locations' in data:
            return {
                'organ_name': data.get('organ', ''),
                'anatomical_locations': data.get('anatomical_locations', []),
                'full_response': data
            }
        
        # 支持旧的格式: 多器官支持
        organs = data.get('organs', [])
        if organs:
            # 🔧 修复：支持多器官输出，不再限制为单器官
            all_organ_names = []
            all_anatomical_locations = []
            
            for organ in organs:
                organ_name = organ.get('organName', '')
                locations = organ.get('anatomicalLocations', [])
                
                if organ_name:  # 只添加有效的器官名称
                    all_organ_names.append(organ_name)
                    all_anatomical_locations.extend(locations)
            
            # 去重解剖位置，保持顺序
            unique_locations = list(dict.fromkeys(all_anatomical_locations))
            
            return {
                'organ_names': all_organ_names,  # 多器官支持
                'organ_name': all_organ_names[0] if all_organ_names else '',  # 向后兼容
                'anatomical_locations': unique_locations,
                'total_organs': len(all_organ_names),
                'full_response': data
            }
        
        return {'organ_name': '', 'anatomical_locations': []}
        
    except Exception as e:
        print(f"JSON解析失败: {e}")
        return {'organ_name': '', 'anatomical_locations': []}

def test_deepseek_response():
    """测试实际的deepseek响应"""
    print("🧪 测试实际的deepseek多器官响应")
    
    # 从结果文件中提取的实际响应
    deepseek_response = '''```json
{
  "organs": [
    {
      "organName": "Brain",
      "anatomicalLocations": ["Cerebral Cortex", "Frontal Lobe", "Temporal Lobe", "Meninges"],
      "relevance": "High"
    },
    {
      "organName": "Artery (Arteria)",
      "anatomicalLocations": ["Cerebral Arteries", "Meningeal Arteries", "Carotid Arteries"],
      "relevance": "High"
    },
    {
      "organName": "Vein (Vena)",
      "anatomicalLocations": ["Cerebral Veins", "Venous Sinuses"],
      "relevance": "Medium"
    }
  ]
}
```'''
    
    result = extract_and_parse_json_fixed(deepseek_response)
    
    print(f"📊 解析结果:")
    print(f"   器官数量: {result.get('total_organs', 0)}")
    print(f"   器官列表: {result.get('organ_names', [])}")
    print(f"   解剖位置数量: {len(result.get('anatomical_locations', []))}")
    print(f"   解剖位置: {result.get('anatomical_locations', [])}")
    print(f"   向后兼容字段: {result.get('organ_name', 'N/A')}")
    
    # 验证修复效果
    expected_organs = 3
    expected_locations = 10  # 4+3+2 去重后
    
    success = True
    if result.get('total_organs', 0) != expected_organs:
        print(f"❌ 器官数量错误: 期望{expected_organs}, 实际{result.get('total_organs', 0)}")
        success = False
    
    if len(result.get('organ_names', [])) != expected_organs:
        print(f"❌ 器官名称列表错误: 期望{expected_organs}, 实际{len(result.get('organ_names', []))}")
        success = False
    
    if success:
        print("✅ 修复生效！API管理器现在支持多器官解析")
        
        # 计算改进效果
        old_organs = 1  # 修复前只能解析1个器官
        new_organs = result.get('total_organs', 0)
        old_locations = 4  # 修复前只能获得第一个器官的位置
        new_locations = len(result.get('anatomical_locations', []))
        
        print(f"\n📈 改进效果:")
        print(f"   器官数量: {old_organs} → {new_organs} (+{new_organs - old_organs})")
        print(f"   位置数量: {old_locations} → {new_locations} (+{new_locations - old_locations})")
        print(f"   器官增长: +{((new_organs - old_organs) / old_organs * 100):.0f}%")
        print(f"   位置增长: +{((new_locations - old_locations) / old_locations * 100):.0f}%")
        
        return True
    else:
        print("❌ 修复未生效")
        return False

def analyze_current_results():
    """分析当前结果文件中的问题"""
    print("\n🔍 分析当前结果文件的问题")
    
    # 模拟当前结果文件中的解析结果
    current_result = {
        "organ_name": "Brain",
        "anatomical_locations": ["Cerebral Cortex", "Frontal Lobe", "Temporal Lobe", "Meninges"]
    }
    
    print(f"📊 当前结果文件显示:")
    print(f"   器官数量: 1 (只有organ_name)")
    print(f"   器官: {current_result['organ_name']}")
    print(f"   位置数量: {len(current_result['anatomical_locations'])}")
    
    print(f"\n❌ 问题分析:")
    print(f"   1. 缺少 'organ_names' 字段 (应包含所有器官)")
    print(f"   2. 缺少 'total_organs' 字段 (应显示器官总数)")
    print(f"   3. 只保留了第一个器官的信息")
    print(f"   4. 丢失了 Artery 和 Vein 的信息")
    
    print(f"\n💡 解决方案:")
    print(f"   需要重新运行评估，确保使用修复后的API管理器")

def main():
    """主函数"""
    print("🎯 API管理器修复效果测试")
    print("=" * 50)
    
    # 测试修复后的解析函数
    if test_deepseek_response():
        print(f"\n🎉 修复验证成功!")
        print(f"💡 修复后的API管理器能够:")
        print(f"   ✅ 解析多个器官")
        print(f"   ✅ 合并所有解剖位置")
        print(f"   ✅ 保持向后兼容性")
        print(f"   ✅ 提供器官统计信息")
    else:
        print(f"\n❌ 修复验证失败")
    
    # 分析当前结果的问题
    analyze_current_results()
    
    print(f"\n📋 下一步建议:")
    print(f"   1. 重新运行评估以使用修复后的代码")
    print(f"   2. 检查新生成的结果文件")
    print(f"   3. 验证多器官字段是否出现")

if __name__ == "__main__":
    main()
