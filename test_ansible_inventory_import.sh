#!/bin/bash

# Ansible Inventory Manager 測試腳本

echo "============================================"
echo "Ansible Inventory Manager - 功能測試"
echo "============================================"
echo ""

# 測試 1: 檢查 API 端點是否可訪問
echo "📝 測試 1: 檢查 API 端點"
echo "-------------------------------------------"
response=$(curl -s http://localhost/api/ansible-inventory/)
if echo "$response" | grep -q "count"; then
    echo "✅ API 端點正常"
    echo "$response" | python3 -m json.tool
else
    echo "❌ API 端點異常"
    echo "$response"
fi
echo ""

# 測試 2: 嘗試導入一個不存在的路徑（應該返回錯誤）
echo "📝 測試 2: 導入不存在的路徑（預期失敗）"
echo "-------------------------------------------"
response=$(curl -s -X POST http://localhost/api/ansible-inventory/import/ \
    -H "Content-Type: application/json" \
    -d '{
        "nas_path": "\\\\10.250.0.1\\mdt\\test\\non-existent",
        "file_name": "hosts"
    }')
echo "$response" | python3 -m json.tool 2>/dev/null || echo "$response"
echo ""

# 測試 3: 顯示使用說明
echo "📝 測試 3: 真實測試步驟"
echo "-------------------------------------------"
echo "要測試實際導入功能，請執行："
echo ""
echo "curl -X POST http://localhost/api/ansible-inventory/import/ \\"
echo "  -H \"Content-Type: application/json\" \\"
echo "  -d '{"
echo "    \"nas_path\": \"\\\\\\\\10.250.0.1\\\\mdt\\\\Script\\\\chunwei_test\\\\26_7F_new\\\\inventory\","
echo "    \"file_name\": \"hosts\""
echo "  }'"
echo ""
echo "或者在瀏覽器中訪問："
echo "http://localhost/ansible-inventory-manager"
echo ""

# 測試 4: 檢查前端是否編譯成功
echo "📝 測試 4: 檢查前端服務"
echo "-------------------------------------------"
react_status=$(docker ps --filter "name=nt-react" --format "{{.Status}}")
if echo "$react_status" | grep -q "Up"; then
    echo "✅ React 前端服務運行中: $react_status"
else
    echo "❌ React 前端服務異常"
fi
echo ""

# 測試 5: 檢查資料庫表是否創建
echo "📝 測試 5: 檢查資料庫表"
echo "-------------------------------------------"
docker exec nt-django python manage.py shell -c "
from api.models import AnsibleInventoryImport, AnsibleHostConfig
print('✅ AnsibleInventoryImport 模型:', AnsibleInventoryImport.objects.count(), '筆記錄')
print('✅ AnsibleHostConfig 模型:', AnsibleHostConfig.objects.count(), '筆記錄')
"
echo ""

echo "============================================"
echo "測試完成！"
echo "============================================"
echo ""
echo "💡 下一步："
echo "1. 在瀏覽器打開: http://localhost/ansible-inventory-manager"
echo "2. 使用 Admin 帳號登入（需要 is_staff 權限）"
echo "3. 輸入真實的 NAS 路徑測試導入功能"
echo ""
