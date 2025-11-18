#!/usr/bin/env python
"""測試 API 是否正確處理 Jinja2 模板語法"""

import sys
import os
import django

# 設置 Django 環境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'network_toolbox.settings')
sys.path.insert(0, '/app')
django.setup()

import requests

API_BASE = 'http://localhost:8000/api'

def test_api_validate_jinja2():
    """測試 API 驗證含 Jinja2 模板的內容"""
    
    print("=" * 80)
    print("API 測試: Jinja2 模板語法驗證")
    print("=" * 80)
    
    # 測試案例：實際的第 132 行內容（需要先定義 uart 組）
    content = """[uart]
host1 ansible_host=192.168.1.1

[uart:vars]
ansible_user=administrator
saf_mode=beta
saf_comment=Andrews
saf_comment_full={{{{ firmware_sku_keyword }}}} - {{{{ sample_size }}}} - {{{{ saf_comment }}}}
"""
    
    print("\n測試內容:")
    print("-" * 80)
    for i, line in enumerate(content.split('\n'), 1):
        if line.strip():
            print(f"{i}: {line}")
    
    print("\n" + "-" * 80)
    print("發送 API 請求...")
    
    try:
        response = requests.post(
            f'{API_BASE}/ansible-inventory/validate-content/',
            json={'content': content},
            timeout=10
        )
        
        print(f"狀態碼: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            
            print("\nAPI 響應:")
            print("-" * 80)
            print(f"syntax_valid: {data.get('syntax_valid')}")
            print(f"error_message: {data.get('error_message')}")
            print(f"error_line: {data.get('error_line')}")
            print(f"error_line_content: {data.get('error_line_content')}")
            print(f"validation_method: {data.get('validation_method')}")
            
            if data.get('syntax_valid'):
                print("\n✅ 測試通過: Jinja2 模板語法被正確識別，沒有誤判為錯誤")
                return True
            else:
                print("\n❌ 測試失敗: 仍然誤判為錯誤")
                return False
        else:
            print(f"❌ API 請求失敗: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ 發生錯誤: {e}")
        return False

if __name__ == '__main__':
    success = test_api_validate_jinja2()
    print("\n" + "=" * 80)
    sys.exit(0 if success else 1)
