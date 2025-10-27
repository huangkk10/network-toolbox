# DHCP Analytics - SSH 整合使用說明

## 📖 概述

本系統已整合 SSH 連接功能，可以從遠端 DHCP Server 獲取真實的租約資料。

## 🔧 系統架構

```
前端 (React)
    ↓ API 請求
後端 (Django)
    ↓ SSH 連接
DHCP Server (遠端)
    ↓ 讀取檔案
/var/lib/dhcp/dhcpd.leases
```

## 📝 配置 DHCP Server

### 1. 在 Django Admin 中新增 DHCP Server

訪問：`http://localhost/admin/api/dhcpserver/`

必填欄位：
- **名稱**：Server 的識別名稱（如：主機房 DHCP-01）
- **IP 位址**：DHCP Server 的 IP（如：10.250.50.1）
- **SSH 連接埠**：預設 22
- **SSH 使用者名稱**：預設 root
- **SSH 密碼**：登入密碼（或使用 SSH 金鑰）
- **DHCP Leases 檔案路徑**：
  - CentOS/RHEL: `/var/lib/dhcpd/dhcpd.leases`
  - Debian/Ubuntu: `/var/lib/dhcp/dhcpd.leases`
  - FreeBSD: `/var/db/dhcpd.leases`

### 2. 測試 SSH 連接

執行以下指令測試連接：

```bash
# 進入 Django 容器
docker exec -it nt-django bash

# 測試 SSH 連接
ssh root@10.250.50.1

# 測試讀取租約檔案
ssh root@10.250.50.1 "cat /var/lib/dhcp/dhcpd.leases"
```

## 🔄 同步租約資料

### 方式一：使用 API 手動同步

```bash
# 同步指定 Server 的租約（假設 Server ID 為 1）
curl -X POST http://localhost/api/dhcp-servers/1/sync-leases/
```

### 方式二：使用 Django Shell 同步

```bash
docker exec -it nt-django python manage.py shell
```

```python
from api.models import DHCPServer
from api.services import DHCPDataService

# 獲取第一個 Server
server = DHCPServer.objects.first()

# 創建服務並同步
service = DHCPDataService(server)
result = service.sync_leases_to_db()

print(f"同步結果: {result}")
```

### 方式三：自動定時同步（建議）

在 `settings.py` 中配置定時任務（需要安裝 celery）：

```python
# 每 5 分鐘同步一次所有 Server 的租約
CELERY_BEAT_SCHEDULE = {
    'sync-dhcp-leases': {
        'task': 'api.tasks.sync_all_servers',
        'schedule': 300.0,  # 5 分鐘
    },
}
```

## 📊 前端使用

### 查看資料

1. 訪問：`http://localhost/dhcp-analytics`
2. 在頂部選擇要查看的 Server
3. 系統會自動載入以下真實資料：
   - **總覽統計**：總租約數、活躍租約、已過期租約、IP 使用率
   - **租約趨勢**：最近 7 天的趨勢圖
   - **狀態分佈**：租約狀態的圓餅圖
   - **最近租約**：最新的 10 筆租約記錄

### 重新整理資料

點擊右上角的「重新整理」按鈕，系統會重新從後端 API 獲取資料。

## 🔐 SSH 安全建議

### 1. 使用 SSH 金鑰（推薦）

```bash
# 在 Django 容器內生成金鑰
docker exec -it nt-django bash
ssh-keygen -t rsa -b 4096 -f /app/keys/dhcp_server_key

# 複製公鑰到 DHCP Server
ssh-copy-id -i /app/keys/dhcp_server_key.pub root@10.250.50.1

# 在 Django Admin 中設定金鑰路徑
SSH 金鑰檔案路徑: /app/keys/dhcp_server_key
```

### 2. 加密密碼存儲

目前密碼以明文存儲在資料庫中，建議使用 Django 的加密功能：

```python
from django.contrib.auth.hashers import make_password, check_password

# 存儲時加密
server.ssh_password = make_password('actual_password')

# 使用時解密（需要修改 services.py）
```

### 3. 限制 SSH 使用者權限

在 DHCP Server 上創建專用使用者，僅授予讀取租約檔案的權限：

```bash
# 在 DHCP Server 上執行
useradd -m dhcp_reader
chmod 644 /var/lib/dhcp/dhcpd.leases
usermod -aG dhcpd dhcp_reader  # 根據系統調整群組
```

## 🐛 故障排除

### 問題：SSH 連接失敗

**檢查清單：**
1. ✅ 確認 DHCP Server IP 可以 ping 通
2. ✅ 確認 SSH 服務正在運行：`systemctl status sshd`
3. ✅ 確認防火牆允許 SSH：`firewall-cmd --list-all`
4. ✅ 確認密碼或金鑰正確

**查看日誌：**
```bash
# 查看 Django 錯誤日誌
tail -f logs/django_error.log

# 查看 DHCP 操作日誌
tail -f logs/dhcp_operations.log
```

### 問題：無法讀取租約檔案

**檢查清單：**
1. ✅ 確認檔案路徑正確
2. ✅ 確認檔案存在：`ls -la /var/lib/dhcp/dhcpd.leases`
3. ✅ 確認有讀取權限：`chmod 644 /var/lib/dhcp/dhcpd.leases`

### 問題：租約解析失敗

**檢查清單：**
1. ✅ 確認租約檔案格式正確
2. ✅ 查看 Django 日誌中的解析錯誤
3. ✅ 手動檢查租約檔案內容

## 📈 效能優化

### 1. 批次同步

建議在低峰時段進行批次同步，避免影響系統效能。

### 2. 快取機制

在 `views.py` 中添加快取：

```python
from django.core.cache import cache

@api_view(['GET'])
def dhcp_analytics_overview(request):
    cache_key = f'overview_{server_id}'
    cached_data = cache.get(cache_key)
    
    if cached_data:
        return Response(cached_data)
    
    # 計算統計...
    cache.set(cache_key, data, timeout=300)  # 快取 5 分鐘
    return Response(data)
```

### 3. 僅同步變更

修改 `sync_leases_to_db()` 僅同步有變化的租約。

## 📚 API 端點列表

| 端點 | 方法 | 說明 |
|------|------|------|
| `/api/dhcp-analytics/overview/` | GET | 總覽統計 |
| `/api/dhcp-analytics/trend/` | GET | 租約趨勢 |
| `/api/dhcp-analytics/status-distribution/` | GET | 狀態分佈 |
| `/api/dhcp-analytics/recent-leases/` | GET | 最近租約 |
| `/api/dhcp-servers/<id>/sync-leases/` | POST | 同步租約 |

## 🔄 升級說明

從模擬資料升級到真實資料的步驟：

1. ✅ 已安裝 `paramiko` SSH 套件
2. ✅ 已執行資料庫遷移（新增 SSH 欄位）
3. ✅ 已更新 `OverviewTab.js`（使用 API）
4. ✅ 已建立 `services.py`（SSH 連接和解析）
5. ✅ 已新增 API 端點

**下一步：**
- 在 Django Admin 中新增 DHCP Server
- 配置 SSH 連接資訊
- 執行首次同步測試

## 📞 支援

如有問題，請查看：
- Django 日誌：`logs/django.log`
- DHCP 操作日誌：`logs/dhcp_operations.log`
- 錯誤日誌：`logs/django_error.log`

---

**建立日期**：2025-10-27  
**版本**：1.0.0
