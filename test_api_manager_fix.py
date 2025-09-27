#!/usr/bin/env python3
import sys
sys.path.append('src')
from api_manager import APIManager

# 测试多器官解析
test_response = '''```json
{
  "organs": [
    {
      "organName": "Brain",
      "anatomicalLocations": ["Cerebral Cortex", "Meninges"],
      "relevance": "High"
    },
    {
      "organName": "Artery (Arteria)",
      "anatomicalLocations": ["Cerebral arteries", "Meningeal arteries"],
      "relevance": "High"
    }
  ]
}
```'''

api_manager = APIManager()
result = api_manager._extract_and_parse_json(test_response)
print('=== 测试结果 ===')
print(f'organ_names: {result.get("organ_names", "NOT_FOUND")}')
print(f'total_organs: {result.get("total_organs", "NOT_FOUND")}')
print(f'organ_name: {result.get("organ_name", "NOT_FOUND")}')
print(f'anatomical_locations: {result.get("anatomical_locations", "NOT_FOUND")}')
