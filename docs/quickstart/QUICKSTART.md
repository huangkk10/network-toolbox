# 🚀 DHCP Analytics 快速開始指南

## 📌 當前狀態

✅ **已完成**：DHCP Analytics 頁面已從模擬資料改為使用真實 API 資料  
✅ **資料庫**：已有 450 筆測試租約（320 活躍 + 130 過期）  
✅ **API**：5 個端點全部正常運作  
✅ **前端**：OverviewTab 已使用真實資料渲染  

---

## 🎯 立即體驗

### 1. 訪問前端頁面
```
http://localhost/dhcp-analytics
```

### 2. 測試 API 端點
```bash
# 總覽統計
curl http://localhost/api/dhcp-analytics/overview/?server=all | jq

# 租約趨勢
curl http://localhost/api/dhcp-analytics/trend/?server=all | jq

# 狀態分佈
curl http://localhost/api/dhcp-analytics/status-distribution/?server=all | jq

# 最近租約
curl http://localhost/api/dhcp-analytics/recent-leases/?server=all | jq
```

---

## 🔄 重建測試資料

如果需要重新建立測試資料：

```bash
docker exec nt-django python create_test_data.py
```

---

## 🔧 連接真實 DHCP Server

### 步驟 1：配置 SSH 認證

訪問 Django Admin：
```
http://localhost/admin/api/dhcpserver/
```

編輯 Server，設定：
- **SSH 連接埠**：22
- **SSH 使用者名稱**：root
- **SSH 密碼**：（您的密碼）
- **DHCP Leases 路徑**：`/var/lib/dhcp/dhcpd.leases`

### 步驟 2：測試 SSH 連接

```bash
# 進入容器
docker exec -it nt-django bash

# 執行測試腳本
python test_dhcp_ssh.py
```

### 步驟 3：手動同步租約

```bash
# 方式 1：使用 API（Server ID = 1）
curl -X POST http://localhost/api/dhcp-servers/1/sync-leases/

# 方式 2：使用 Django Shell
docker exec -it nt-django python manage.py shell
```

```python
from api.models import DHCPServer
from api.services import DHCPDataService

server = DHCPServer.objects.first()
service = DHCPDataService(server)
result = service.sync_leases_to_db()
print(result)
```

---

## 📊 API 端點總覽

| 端點 | 方法 | 說明 | 參數 |
|------|------|------|------|
| `/api/dhcp-analytics/overview/` | GET | 總覽統計 | `?server=all` |
| `/api/dhcp-analytics/trend/` | GET | 租約趨勢 | `?server=all&days=7` |
| `/api/dhcp-analytics/status-distribution/` | GET | 狀態分佈 | `?server=all` |
| `/api/dhcp-analytics/recent-leases/` | GET | 最近租約 | `?server=all&limit=10` |
| `/api/dhcp-servers/<id>/sync-leases/` | POST | 同步租約 | - |

---

## 🐛 故障排除

### 問題：前端顯示 0 或空資料

**解決方法**：
```bash
# 檢查資料庫是否有資料
docker exec nt-django python manage.py shell -c "from api.models import DHCPLease; print(DHCPLease.objects.count())"

# 如果為 0，建立測試資料
docker exec nt-django python create_test_data.py
```

### 問題：API 返回錯誤

**解決方法**：
```bash
# 查看 Django 日誌
docker compose logs django --tail 50

# 查看錯誤日誌
tail -f logs/django_error.log
```

### 問題：SSH 連接失敗

**解決方法**：
```bash
# 測試網路連通性
docker exec nt-django ping -c 3 10.250.50.1

# 測試 SSH 連接
docker exec nt-django ssh root@10.250.50.1

# 查看 DHCP 操作日誌
tail -f logs/dhcp_operations.log
```

---

## 📚 相關文件

- **完整測試報告**：`docs/API_TEST_REPORT.md`
- **SSH 整合說明**：`docs/DHCP_SSH_INTEGRATION.md`
- **開發總結**：`SUMMARY.md`

---

## ✅ 驗證清單

- [x] 後端 API 端點已建立
- [x] 資料庫遷移已執行
- [x] SSH 服務模組已實作
- [x] 前端組件已更新
- [x] 測試資料已建立
- [x] API 測試已通過
- [x] 前端頁面正常顯示

---

**所有功能已完成！現在 DHCP Analytics 頁面使用的是真實資料！** 🎉

如有問題，請參考 `docs/` 目錄下的詳細文件。
