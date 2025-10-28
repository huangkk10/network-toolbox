# OUI 資料庫自動更新配置

## 📋 概述

Network Toolbox 已配置為 **每月自動更新 IEEE OUI 資料庫**，確保設備製造商識別資料保持最新。

## 🔄 自動更新機制

### Celery Beat 定時任務

系統使用 **Celery Beat** 調度器自動執行 OUI 資料庫更新：

**任務配置**：
```python
# backend/network_toolbox/celery.py

'update-oui-database-monthly': {
    'task': 'api.tasks.update_oui_database_task',
    'schedule': crontab(day_of_month='1', hour=2, minute=0),  # 每月 1 號 02:00
    'kwargs': {
        'source': 0,       # IEEE Official HTTPS
        'backup': True     # 自動備份
    },
}
```

**執行時間**：每月 1 號凌晨 2:00 AM（避開業務高峰時段）

### 資料來源

**預設使用 IEEE 官方來源**：
- **URL**: https://standards-oui.ieee.org/oui/oui.txt
- **資料量**: ~38,000+ OUI 記錄
- **製造商數**: ~19,000+
- **更新頻率**: IEEE 每週更新

**備用來源**（source=1 或 2）：
1. IEEE Official HTTP (fallback)
2. Gist Mirror (歷史備份)

## 📊 資料庫比較

| 來源 | OUI 記錄數 | 唯一製造商 | 檔案大小 | 推薦 |
|------|-----------|-----------|---------|------|
| IEEE Official (HTTPS) | 38,254 | 19,776 | ~2.5 MB | ✅ **預設** |
| Gist Mirror | 23,475 | 16,778 | ~673 KB | 備用 |

**提升幅度**：
- OUI 記錄數 **+63%** (23,475 → 38,254)
- 製造商數 **+18%** (16,778 → 19,776)

## 🛠️ 手動更新方法

### 方法 1：使用 Django 管理命令（推薦）

```bash
# 使用 IEEE 官方來源（預設）
docker exec nt-django python manage.py update_oui --source 0 --backup

# 查看幫助
docker exec nt-django python manage.py update_oui --help
```

### 方法 2：觸發 Celery 任務

```bash
# 進入 Django Shell
docker exec -it nt-django python manage.py shell

# 執行更新任務
from api.tasks import update_oui_database_task
result = update_oui_database_task.delay(source=0, backup=True)

# 查看任務狀態
result.status  # 'PENDING', 'SUCCESS', 'FAILURE'
result.result  # 任務結果
```

### 方法 3：使用 Celery Flower 管理介面

1. 訪問 http://localhost:5555
2. 進入 "Tasks" 頁面
3. 執行 `api.tasks.update_oui_database_task`

## 📅 定時任務排程

查看所有已排程的定時任務：

```bash
# 查看 Celery Beat 排程
docker exec nt-celery-beat celery -A network_toolbox beat --loglevel=info
```

當前排程：

| 任務名稱 | 執行頻率 | 功能 |
|---------|---------|------|
| sync-dhcp-logs-every-5-minutes | 每 5 分鐘 | DHCP 日誌同步 |
| cleanup-old-dhcp-logs-daily | 每天 03:00 | 清理舊日誌 |
| **update-oui-database-monthly** | **每月 1 號 02:00** | **OUI 資料庫更新** |

## 🔍 監控更新狀態

### 查看最後更新時間

```bash
# 查看 OUI 資料庫檔案修改時間
docker exec nt-django ls -lh /app/api/utils/ieee-oui.txt

# 查看檔案內容的更新時間戳
docker exec nt-django head -10 /app/api/utils/ieee-oui.txt
```

### 查看更新日誌

```bash
# Django 日誌
docker exec nt-django tail -f /app/logs/django.log | grep OUI

# Celery Worker 日誌
docker compose logs celery_worker -f | grep OUI

# Celery Beat 日誌
docker compose logs celery_beat -f | grep update-oui
```

### 查看資料庫統計

```python
# Django Shell
docker exec -it nt-django python manage.py shell

from api.utils.mac_vendor import get_vendor_stats
stats = get_vendor_stats()
print(f"總 OUI: {stats['total_oui_entries']:,}")
print(f"製造商: {stats['unique_vendors']:,}")
```

## ⚙️ 自定義配置

### 修改更新頻率

編輯 `backend/network_toolbox/celery.py`:

```python
# 每週更新（每週一 02:00）
'schedule': crontab(day_of_week='monday', hour=2, minute=0)

# 每季度更新（1、4、7、10 月的 1 號）
'schedule': crontab(day_of_month='1', month_of_year='1,4,7,10', hour=2, minute=0)

# 每半年更新（1、7 月的 1 號）
'schedule': crontab(day_of_month='1', month_of_year='1,7', hour=2, minute=0)
```

### 修改資料來源

```python
'kwargs': {
    'source': 0,       # 0=IEEE HTTPS, 1=IEEE HTTP, 2=Gist
    'backup': True     # 是否備份
},
```

### 重啟 Celery Beat

修改配置後需要重啟：

```bash
docker compose restart celery_beat
```

## 🔧 故障排查

### 問題 1：更新任務未執行

**檢查 Celery Beat 是否運行**：
```bash
docker compose ps celery_beat
docker compose logs celery_beat --tail 50
```

**檢查排程配置**：
```bash
docker exec nt-celery-beat celery -A network_toolbox inspect scheduled
```

### 問題 2：下載失敗

**檢查網路連接**：
```bash
docker exec nt-django curl -I https://standards-oui.ieee.org/oui/oui.txt
```

**使用備用來源**：
```bash
docker exec nt-django python manage.py update_oui --source 2 --backup
```

### 問題 3：解析失敗

**查看錯誤日誌**：
```bash
docker compose logs django -f | grep ERROR
```

**檢查資料庫檔案**：
```bash
docker exec nt-django head -20 /app/api/utils/ieee-oui.txt
docker exec nt-django tail -20 /app/api/utils/ieee-oui.txt
```

## 📈 更新效果驗證

### 測試識別準確性

```bash
# 運行測試腳本
docker exec nt-django python /app/test_mac_vendor_simple.py
```

**預期輸出**：
```
============================================================
OUI 資料庫狀態
============================================================
total_oui_entries: 38,254  ✓ (更新前: 23,475)
unique_vendors: 19,776     ✓ (更新前: 16,778)

============================================================
測試 MAC 地址識別
============================================================
MAC: 58:11:22:33:44:55    => Vendor: ASUSTek COMPUTER INC. ✓
(之前顯示 "Unknown")
```

### 查看 Dashboard 廠商分佈

訪問 http://localhost 查看 Dashboard，廠商識別應該更準確。

## 🔒 備份管理

### 自動備份

更新時自動創建備份：
```
/app/api/utils/ieee-oui.txt.backup
```

### 手動恢復

```bash
# 恢復到備份版本
docker exec nt-django cp /app/api/utils/ieee-oui.txt.backup /app/api/utils/ieee-oui.txt

# 重新載入
docker exec nt-django python manage.py shell -c "from api.utils.mac_vendor import reload_oui_database; reload_oui_database()"
```

## 📊 性能影響

| 項目 | 更新前 | 更新後 | 影響 |
|------|-------|-------|------|
| OUI 記錄 | 23,475 | 38,254 | +63% |
| 檔案大小 | 673 KB | ~2.5 MB | +272% |
| 載入時間 | ~30 ms | ~60 ms | +100% |
| 查詢時間 | <1 ms | <1 ms | 無影響 ✓ |
| 記憶體佔用 | ~5 MB | ~12 MB | +140% |

**結論**：查詢性能不受影響，記憶體增加可接受。

## 🎯 最佳實踐

1. **定期檢查更新日誌**：確認每月更新是否成功
2. **監控資料庫大小**：避免檔案損壞
3. **保留備份**：至少保留一個舊版本
4. **測試新資料**：更新後運行測試腳本
5. **查看 Dashboard**：確認廠商識別準確性

## 📚 相關文檔

- [MAC 廠商識別完整文檔](./MAC_VENDOR_IDENTIFICATION.md)
- [MAC 廠商識別快速開始](./MAC_VENDOR_QUICKSTART.md)
- [定時任務文檔](./scheduled-tasks/)

---

**配置狀態**：✅ 已配置  
**自動更新**：✅ 啟用（每月 1 號 02:00）  
**資料來源**：IEEE Official (HTTPS)  
**備份機制**：✅ 啟用  

**最後更新**：2025-10-29  
**維護者**：Network Toolbox Team
