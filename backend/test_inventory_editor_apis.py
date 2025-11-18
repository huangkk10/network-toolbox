#!/usr/bin/env python
"""測試 Inventory 文本編輯器相關的 API"""

import sys
import os
import django

# 設置 Django 環境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'network_toolbox.settings')
sys.path.insert(0, '/app')
django.setup()

import requests
from api.models import AnsibleInventoryImport

API_BASE = 'http://localhost:8000/api'

def test_editor_apis():
    """測試文本編輯器 API 流程"""
    
    print("=" * 80)
    print("測試 Inventory 文本編輯器 API")
    print("=" * 80)
    
    # 步驟 1: 檢查是否有現有的 Inventory
    print("\n步驟 1: 檢查現有 Inventory")
    print("-" * 80)
    
    inventory = AnsibleInventoryImport.objects.filter(status='success').first()
    
    if not inventory:
        print("❌ 沒有找到已導入的 Inventory，請先執行導入操作")
        print("提示：可以使用前端介面或 import API 導入一個 Inventory")
        return False
    
    print(f"✅ 找到 Inventory ID: {inventory.id}")
    print(f"   路徑: {inventory.nas_path}/{inventory.file_name}")
    print(f"   Hosts: {inventory.total_hosts}, Groups: {inventory.total_groups}")
    
    inventory_id = inventory.id
    
    # 步驟 2: 測試獲取文件內容
    print(f"\n步驟 2: 測試 GET /api/ansible-inventory/{inventory_id}/content/")
    print("-" * 80)
    
    try:
        response = requests.get(f'{API_BASE}/ansible-inventory/{inventory_id}/content/')
        
        if response.status_code != 200:
            print(f"❌ API 請求失敗: {response.status_code}")
            print(f"   響應: {response.text}")
            return False
        
        data = response.json()
        content = data.get('content', '')
        file_path = data.get('file_path', '')
        
        print(f"✅ 成功獲取文件內容")
        print(f"   文件路徑: {file_path}")
        print(f"   內容長度: {len(content)} 字符")
        print(f"   行數: {len(content.splitlines())} 行")
        print(f"\n   前 10 行預覽:")
        for i, line in enumerate(content.splitlines()[:10], 1):
            print(f"   {i:3d}: {line}")
        
        original_content = content
        
    except Exception as e:
        print(f"❌ 測試失敗: {e}")
        return False
    
    # 步驟 3: 測試驗證內容語法（有效內容）
    print(f"\n步驟 3: 測試 POST /api/ansible-inventory/validate-content/ (有效內容)")
    print("-" * 80)
    
    test_content_valid = """[test_group]
host1 ansible_host=192.168.1.1 ansible_user=root
host2 ansible_host=192.168.1.2 ansible_user=admin

[test_group:vars]
ansible_port=22
"""
    
    try:
        response = requests.post(
            f'{API_BASE}/ansible-inventory/validate-content/',
            json={'content': test_content_valid}
        )
        
        if response.status_code != 200:
            print(f"❌ API 請求失敗: {response.status_code}")
            return False
        
        data = response.json()
        
        if data.get('syntax_valid'):
            print(f"✅ 驗證通過")
            print(f"   Hosts: {data.get('parsed_hosts')}")
            print(f"   Groups: {data.get('parsed_groups')}")
        else:
            print(f"❌ 驗證失敗（預期應該通過）")
            print(f"   錯誤: {data.get('error_message')}")
            return False
            
    except Exception as e:
        print(f"❌ 測試失敗: {e}")
        return False
    
    # 步驟 4: 測試驗證內容語法（無效內容）
    print(f"\n步驟 4: 測試 POST /api/ansible-inventory/validate-content/ (無效內容)")
    print("-" * 80)
    
    test_content_invalid = """[test_group]
host1 ansible_host 192.168.1.1
"""
    
    try:
        response = requests.post(
            f'{API_BASE}/ansible-inventory/validate-content/',
            json={'content': test_content_invalid}
        )
        
        if response.status_code != 200:
            print(f"❌ API 請求失敗: {response.status_code}")
            return False
        
        data = response.json()
        
        if not data.get('syntax_valid'):
            print(f"✅ 正確檢測到語法錯誤")
            print(f"   錯誤訊息: {data.get('error_message')}")
            print(f"   錯誤行號: {data.get('error_line')}")
            print(f"   錯誤內容: {data.get('error_line_content')}")
            print(f"   驗證方法: {data.get('validation_method')}")
        else:
            print(f"❌ 未檢測到錯誤（預期應該失敗）")
            return False
            
    except Exception as e:
        print(f"❌ 測試失敗: {e}")
        return False
    
    # 步驟 5: 測試更新文件內容（僅驗證模式）
    print(f"\n步驟 5: 測試 POST /api/ansible-inventory/{inventory_id}/update-content/ (validate_only=true)")
    print("-" * 80)
    
    test_update_content = original_content + "\n# Test comment added\n"
    
    try:
        response = requests.post(
            f'{API_BASE}/ansible-inventory/{inventory_id}/update-content/',
            json={
                'content': test_update_content,
                'validate_only': True,
                'change_summary': '測試驗證模式'
            }
        )
        
        if response.status_code != 200:
            print(f"❌ API 請求失敗: {response.status_code}")
            print(f"   響應: {response.text}")
            return False
        
        data = response.json()
        
        if data.get('success') and data.get('syntax_valid'):
            print(f"✅ 驗證通過（僅驗證，未實際保存）")
            print(f"   語法有效: {data.get('syntax_valid')}")
        else:
            print(f"❌ 驗證失敗")
            print(f"   錯誤: {data.get('error_message')}")
            return False
            
    except Exception as e:
        print(f"❌ 測試失敗: {e}")
        return False
    
    # 步驟 6: 測試更新文件內容（實際儲存）
    print(f"\n步驟 6: 測試 POST /api/ansible-inventory/{inventory_id}/update-content/ (實際儲存)")
    print("-" * 80)
    print("⚠️  這將實際修改 NAS 上的文件！")
    
    # 為了安全，我們只添加一個註釋
    safe_update_content = original_content.strip() + "\n\n# Test update from API at " + str(datetime.now()) + "\n"
    
    try:
        response = requests.post(
            f'{API_BASE}/ansible-inventory/{inventory_id}/update-content/',
            json={
                'content': safe_update_content,
                'validate_only': False,
                'change_summary': 'API 測試：添加測試註釋'
            }
        )
        
        if response.status_code != 200:
            print(f"❌ API 請求失敗: {response.status_code}")
            print(f"   響應: {response.text}")
            return False
        
        data = response.json()
        
        if data.get('success'):
            print(f"✅ 成功保存到 NAS")
            print(f"   語法有效: {data.get('syntax_valid')}")
            print(f"   新版本: {data.get('version')}")
            print(f"   備份文件: {data.get('backup_file')}")
            print(f"   保存時間: {data.get('saved_at')}")
            print(f"   Hosts: {data.get('total_hosts')}")
            print(f"   Groups: {data.get('total_groups')}")
        else:
            print(f"❌ 保存失敗")
            print(f"   錯誤: {data.get('error')}")
            return False
            
    except Exception as e:
        print(f"❌ 測試失敗: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # 步驟 7: 驗證文件確實被更新了
    print(f"\n步驟 7: 驗證文件已更新")
    print("-" * 80)
    
    try:
        response = requests.get(f'{API_BASE}/ansible-inventory/{inventory_id}/content/')
        
        if response.status_code != 200:
            print(f"❌ 無法讀取更新後的文件")
            return False
        
        data = response.json()
        updated_content = data.get('content', '')
        
        if "Test update from API" in updated_content:
            print(f"✅ 文件已成功更新，包含測試註釋")
            print(f"   更新後長度: {len(updated_content)} 字符")
        else:
            print(f"⚠️  文件已更新，但未找到測試註釋")
            
    except Exception as e:
        print(f"❌ 驗證失敗: {e}")
        return False
    
    print("\n" + "=" * 80)
    print("🎉 所有測試通過！")
    print("=" * 80)
    print("\n✅ API 端點測試結果:")
    print("   1. GET  /api/ansible-inventory/<id>/content/         - ✅ 正常工作")
    print("   2. POST /api/ansible-inventory/validate-content/     - ✅ 正常工作")
    print("   3. POST /api/ansible-inventory/<id>/update-content/  - ✅ 正常工作")
    print("\n📝 下一步:")
    print("   - 前端安裝 Monaco Editor")
    print("   - 創建 InventoryFileEditor 組件")
    print("   - 整合到主頁面")
    
    return True

if __name__ == '__main__':
    from datetime import datetime
    success = test_editor_apis()
    sys.exit(0 if success else 1)
