# DHCP 日誌自動同步功能說明

## 📋 功能概述

系統會**自動定時同步所有 DHCP Server 的日誌**，無需手動點擊「同步日誌」按鈕。

---

## 🚀 自動同步機制

### 定時任務配置

**任務名稱**：`sync-all-dhcp-logs-every-10-minutes`

**執行頻率**：每 10 分鐘自動執行一次

**同步範圍**：所有狀態為 `online` 的 DHCP Server

**同步數量**：每個伺服器最多同步 500 條最新日誌

**執行時間**：
- 每小時的第 0、10、20、30、40、50 分鐘
- 例如：00:00、00:10、00:20、00:30...

---

## 📊 同步內容

每次自動同步會執行：

1. **掃描所有在線伺服器**
   - 查詢所有 `status='online'` 的 DHCP Server
   - 跳過 `offline` 或 `warning` 狀態的伺服器

2. **逐一同步日誌**
   - 連接 Windows DHCP Server (透過 SSH)
   - 讀取最新的 500 條日誌
   - 解析 DHCP 事件、客戶端類型、iPXE 資訊
   - 存入資料庫（跳過重複日誌）

3. **記錄同步結果**
   - 成功/失敗的伺服器數量
   - 每個伺服器新增的日誌數
   - 錯誤訊息（如果有）

---

## 🛠️ 啟動定時任務

### 方式 1：使用 Docker Compose（推薦）

定時任務已經包含在 Docker Compose 中，啟動服務即可：

```bash
# 啟動所有服務（包含 Celery Worker 和 Beat）
docker compose up -d

# 查看 Celery 容器狀態
docker compose ps | grep celery

# 應該看到兩個容器：
# - nt-celery-worker  (執行任務)
# - nt-celery-beat    (排程任務)
```

### 方式 2：手動啟動（開發環境）

如果需要手動啟動 Celery：

```bash
# 終端 1：啟動 Celery Worker
cd backend
celery -A network_toolbox worker --loglevel=info

# 終端 2：啟動 Celery Beat（排程器）
cd backend
celery -A network_toolbox beat --loglevel=info
```

---

## 📝 查看同步日誌

### 1. 查看 Celery Worker 日誌

```bash
# Docker 環境
docker compose logs celery-worker -f --tail 100

# 看到類似輸出：
# [Celery] 開始批次同步所有 DHCP Server 的日誌 (limit=500)
# [Celery] 找到 3 個在線的 DHCP Server
# [Celery] 正在同步 Server 日誌: DHCP Server 10.250.71.1 (10.250.71.1)
# [Celery] Server DHCP Server 10.250.71.1 日誌同步成功 - 讀取: 500 筆 | 新增: 150 筆 | 跳過: 350 筆
# [Celery] 批次日誌同步完成 - 伺服器總計: 3 | 成功: 3 | 失敗: 0 | 總共新增日誌: 450 筆
```

### 2. 查看 Celery Beat 日誌

```bash
# Docker 環境
docker compose logs celery-beat -f --tail 50

# 看到類似輸出：
# Scheduler: Sending due task sync-all-dhcp-logs-every-10-minutes
# Task api.tasks.sync_all_dhcp_logs_task sent
```

### 3. 查看 Django 應用日誌

```bash
# 查看 Django 日誌（包含同步詳細資訊）
tail -f logs/django.log | grep Celery

# 或查看錯誤日誌
tail -f logs/django_error.log | grep Celery
```

---

## 🔧 調整同步頻率

如果您想調整同步頻率，修改 `backend/network_toolbox/celery.py`：

### 範例 1：每 5 分鐘同步一次（更頻繁）

```python
'sync-all-dhcp-logs-every-5-minutes': {
    'task': 'api.tasks.sync_all_dhcp_logs_task',
    'schedule': crontab(minute='*/5'),  # 改為每 5 分鐘
    'kwargs': {
        'limit': 300       # 減少每次同步的數量
    },
},
```

### 範例 2：每 30 分鐘同步一次（較少）

```python
'sync-all-dhcp-logs-every-30-minutes': {
    'task': 'api.tasks.sync_all_dhcp_logs_task',
    'schedule': crontab(minute='*/30'),  # 改為每 30 分鐘
    'kwargs': {
        'limit': 1000      # 增加每次同步的數量
    },
},
```

### 範例 3：每小時整點同步

```python
'sync-all-dhcp-logs-hourly': {
    'task': 'api.tasks.sync_all_dhcp_logs_task',
    'schedule': crontab(minute=0),  # 每小時 00 分
    'kwargs': {
        'limit': 1000
    },
},
```

**修改後需要重啟 Celery**：
```bash
docker compose restart celery-worker celery-beat
```

---

## 🧪 手動測試同步任務

### 方式 1：使用 Django Shell

```bash
# 進入 Django Shell
docker exec -it nt-django python manage.py shell

# 執行同步任務
from api.tasks import sync_all_dhcp_logs_task
result = sync_all_dhcp_logs_task.delay(limit=500)

# 查看任務 ID
print(result.id)

# 查看任務狀態（需要等待幾秒）
print(result.status)

# 獲取任務結果
print(result.get(timeout=300))
```

### 方式 2：使用 Celery CLI

```bash
# 手動觸發同步任務
docker exec nt-django celery -A network_toolbox call api.tasks.sync_all_dhcp_logs_task --args='[]' --kwargs='{"limit":500}'
```

### 方式 3：使用測試腳本

```bash
# 創建測試腳本
cat > test_celery_sync.py << 'EOF'
from api.tasks import sync_all_dhcp_logs_task
import time

print("開始執行 DHCP 日誌同步任務...")
result = sync_all_dhcp_logs_task.delay(limit=500)
print(f"任務 ID: {result.id}")

# 等待任務完成
print("等待任務完成...")
try:
    output = result.get(timeout=300)
    print("\n同步結果:")
    print(f"  總伺服器數: {output['total_servers']}")
    print(f"  成功: {output['success_count']}")
    print(f"  失敗: {output['failed_count']}")
    print(f"  總共新增日誌: {output['total_logs_created']} 筆")
    
    print("\n各伺服器詳細結果:")
    for res in output['results']:
        print(f"  - {res['server_name']}:")
        print(f"    讀取: {res['total']} 筆, 新增: {res['created']} 筆, 跳過: {res['skipped']} 筆")
        
except Exception as e:
    print(f"錯誤: {e}")
EOF

# 執行測試
docker exec -it nt-django python test_celery_sync.py
```

---

## 📊 監控同步狀態

### 1. 查看最近的同步記錄

```bash
# 進入 Django Shell
docker exec -it nt-django python manage.py shell

# 查看最近同步的日誌
from api.models import DHCPLog
from django.utils import timezone
from datetime import timedelta

# 最近 10 分鐘新增的日誌
recent_logs = DHCPLog.objects.filter(
    created_at__gte=timezone.now() - timedelta(minutes=10)
).count()

print(f"最近 10 分鐘新增的日誌: {recent_logs} 筆")
```

### 2. 檢查伺服器最後同步時間

```bash
# 查看所有伺服器的最後同步時間
from api.models import DHCPServer

for server in DHCPServer.objects.filter(status='online'):
    print(f"{server.name}: {server.last_sync_at}")
```

### 3. 使用 Celery Flower（Web UI）

如果已安裝 Flower，可以透過瀏覽器監控：

```bash
# 啟動 Flower
docker exec -d nt-django celery -A network_toolbox flower --port=5555

# 訪問 Web UI
http://localhost:5555
```

---

## ❓ 常見問題

### Q1: 為什麼日誌沒有自動更新？

**檢查步驟**：

1. **確認 Celery 服務運行中**：
   ```bash
   docker compose ps | grep celery
   # 應該看到 celery-worker 和 celery-beat 都在運行
   ```

2. **查看 Celery Beat 日誌**：
   ```bash
   docker compose logs celery-beat --tail 50
   # 應該看到定期的任務排程訊息
   ```

3. **查看 Worker 錯誤**：
   ```bash
   docker compose logs celery-worker | grep ERROR
   ```

4. **檢查 Redis 連接**：
   ```bash
   docker compose ps redis
   # Redis 應該在運行
   ```

### Q2: 如何暫停自動同步？

```bash
# 方式 1：停止 Celery Beat（保留 Worker）
docker compose stop celery-beat

# 方式 2：停止所有 Celery 服務
docker compose stop celery-worker celery-beat

# 恢復運行
docker compose start celery-worker celery-beat
```

### Q3: 如何修改同步的日誌數量？

修改 `backend/network_toolbox/celery.py`：

```python
'sync-all-dhcp-logs-every-10-minutes': {
    'task': 'api.tasks.sync_all_dhcp_logs_task',
    'schedule': crontab(minute='*/10'),
    'kwargs': {
        'limit': 1000      # 改為 1000 筆（預設 500）
    },
},
```

重啟 Celery：
```bash
docker compose restart celery-worker celery-beat
```

### Q4: 如何只同步特定伺服器？

目前的自動任務會同步所有 `online` 狀態的伺服器。如果您想排除某些伺服器：

1. 將該伺服器狀態改為 `offline`
2. 或創建自訂任務（修改 `tasks.py`）

### Q5: 手動同步和自動同步有什麼區別？

| 項目 | 手動同步 | 自動同步 |
|------|---------|---------|
| 觸發方式 | 點擊按鈕 | 定時自動執行 |
| 同步範圍 | 單一伺服器 | 所有在線伺服器 |
| 同步數量 | 可自訂（預設 1000） | 固定 500 筆 |
| 執行環境 | Django Web 進程 | Celery Worker |
| 是否阻塞 | 阻塞請求 | 背景執行 |

---

## 🔄 其他定時任務

除了日誌同步，系統還有其他定時任務：

### 1. DHCP Scope 自動同步
- **頻率**：每天凌晨 4 點
- **作用**：更新所有伺服器的 Scope 資訊和使用率

### 2. DHCP 日誌自動清理
- **頻率**：每天凌晨 3 點
- **作用**：刪除 15 天前的舊日誌

### 3. NAS 連線檢測
- **頻率**：每 5 分鐘
- **作用**：檢測 NAS 連線狀態和速度

### 4. IPXE 網路品質檢測
- **頻率**：每 5 分鐘
- **作用**：檢測 IPXE 伺服器的網路品質

### 5. OUI 資料庫更新
- **頻率**：每月 1 號凌晨 2 點
- **作用**：更新 MAC 地址製造商資料庫

---

## 📚 相關文檔

- [Celery 定時任務配置](backend/network_toolbox/celery.py)
- [任務定義](backend/api/tasks.py)
- [DHCP 日誌服務](backend/api/services.py)
- [Docker Compose 配置](docker-compose.yml)

---

## 🎯 總結

### 自動同步的優點

- ✅ **完全自動化** - 無需手動操作
- ✅ **定時更新** - 每 10 分鐘自動同步最新日誌
- ✅ **多伺服器支援** - 自動同步所有在線伺服器
- ✅ **背景執行** - 不阻塞 Web 請求
- ✅ **錯誤恢復** - 自動重試失敗的任務
- ✅ **詳細日誌** - 記錄所有同步細節

### 使用建議

1. **保持預設設定**：每 10 分鐘同步一次已經很合適
2. **監控日誌**：定期查看 Celery 日誌確認運作正常
3. **調整數量**：如果日誌量很大，可以增加 `limit` 參數
4. **手動補充**：如果需要立即同步，仍可使用手動同步按鈕

---

**文檔創建日期**: 2025-10-31  
**功能版本**: v1.2.0  
**作者**: Network Toolbox Team

