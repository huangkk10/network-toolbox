# DHCP 租約自動同步功能說明

## 📋 功能概述

本功能實現了 DHCP 租約的**自動定時同步**，無需再手動點擊「同步租約」按鈕。系統會自動定期從所有在線的 DHCP Server 獲取最新租約資訊並同步到資料庫。

### 自動同步機制

- ⏰ **同步頻率**：每 15 分鐘自動執行一次
- 🌐 **同步範圍**：所有狀態為 `online` 的 DHCP Server
- 📊 **同步內容**：租約資訊（IP、MAC、主機名、租約時間、狀態等）
- 🔄 **自動更新**：新增租約、更新現有租約、統計活躍租約數

### 與手動同步的區別

| 項目 | 手動同步 | 自動同步 |
|------|---------|---------|
| 觸發方式 | 點擊「同步租約」按鈕 | 定時自動執行 |
| 同步頻率 | 按需手動觸發 | 每 15 分鐘 |
| 同步範圍 | 單一伺服器 | 所有在線伺服器 |
| 工作量 | 需要逐個伺服器操作 | 完全自動化 |
| 適用場景 | 立即需要最新數據 | 日常維護、監控 |

---

## 🚀 啟動自動同步

### 方法 1：使用 Docker Compose（推薦）

**最簡單的方式，適合生產環境：**

```bash
# 1. 進入專案目錄
cd /home/owner/Codes/network-toolbox

# 2. 啟動所有服務（包含 Celery）
docker compose up -d

# 3. 確認服務狀態
docker compose ps

# 應該看到以下容器運行中：
# - nt-celery-worker   # Celery 工作進程
# - nt-celery-beat     # Celery 排程器
# - nt-django          # Django 後端
# - nt-react           # React 前端
# - nt-nginx           # Nginx 反向代理
```

### 方法 2：使用啟動腳本

**快速測試和檢查：**

```bash
# 執行啟動腳本（會自動重啟服務並測試）
./start_auto_sync_leases.sh

# 腳本會執行以下操作：
# 1. 檢查 Docker 服務狀態
# 2. 重啟 celery-worker 和 celery-beat
# 3. 顯示已配置的定時任務
# 4. 手動觸發一次測試同步
# 5. 顯示即時日誌（20 秒）
```

### 方法 3：手動啟動 Celery 服務

**開發環境或調試時使用：**

```bash
# 啟動 Celery Worker（背景任務執行者）
docker compose up -d celery-worker

# 啟動 Celery Beat（定時任務排程器）
docker compose up -d celery-beat

# 或者一起啟動
docker compose up -d celery-worker celery-beat
```

---

## 📊 查看同步日誌

### 查看 Celery Worker 日誌

**即時查看租約同步過程：**

```bash
# 查看最新 50 行日誌
docker compose logs celery-worker --tail 50

# 即時追蹤日誌（Ctrl+C 停止）
docker compose logs celery-worker -f

# 搜尋租約相關日誌
docker compose logs celery-worker | grep "租約同步"
```

**日誌輸出範例：**

```
celery-worker    | [INFO] [Celery] 開始批次同步所有 DHCP Server 的租約
celery-worker    | [INFO] [Celery] 找到 2 個在線的 DHCP Server
celery-worker    | [INFO] [Celery] 正在同步 Server 租約: Server01 (10.250.71.1)
celery-worker    | [INFO] [Celery] Server Server01 租約同步成功 - 總計: 150 筆 | 新增: 5 筆 | 更新: 145 筆 | 活躍: 142 筆
celery-worker    | [INFO] [Celery] 正在同步 Server 租約: Server02 (10.250.72.1)
celery-worker    | [INFO] [Celery] Server Server02 租約同步成功 - 總計: 98 筆 | 新增: 3 筆 | 更新: 95 筆 | 活躍: 90 筆
celery-worker    | [INFO] [Celery] 批次租約同步完成 - 伺服器總計: 2 | 成功: 2 | 失敗: 0 | 總共新增租約: 8 筆 | 總共更新租約: 240 筆
```

### 查看 Celery Beat 日誌

**確認定時任務是否正常排程：**

```bash
# 查看排程器日誌
docker compose logs celery-beat --tail 30

# 即時追蹤排程日誌
docker compose logs celery-beat -f
```

**日誌輸出範例：**

```
celery-beat      | [INFO] Scheduler: Sending due task sync-all-dhcp-leases-every-15-minutes (api.tasks.sync_all_dhcp_leases_task)
celery-beat      | [INFO] Task sync-all-dhcp-leases-every-15-minutes sent to queue
```

### 查看 Django 應用程式日誌

**查看 Django 層級的租約同步記錄：**

```bash
# 查看租約操作日誌（容器內路徑）
docker exec nt-django tail -f /app/logs/dhcp_operations.log

# 或從主機查看（透過 Volume 掛載）
tail -f logs/dhcp_operations.log

# 搜尋租約同步記錄
grep "租約同步" logs/dhcp_operations.log
```

---

## ⚙️ 調整同步頻率

如需修改同步頻率，編輯 Celery 配置文件：

**文件位置：** `backend/network_toolbox/celery.py`

### 預設配置（每 15 分鐘）

```python
'sync-all-dhcp-leases-every-15-minutes': {
    'task': 'api.tasks.sync_all_dhcp_leases_task',
    'schedule': crontab(minute='*/15'),  # 每 15 分鐘
    'options': {
        'expires': 810,  # 任務超時 13.5 分鐘
    }
},
```

### 配置範例

#### 1. 每 10 分鐘同步（更頻繁）

```python
'sync-all-dhcp-leases-every-10-minutes': {
    'task': 'api.tasks.sync_all_dhcp_leases_task',
    'schedule': crontab(minute='*/10'),  # 每 10 分鐘
    'options': {
        'expires': 540,  # 任務超時 9 分鐘
    }
},
```

#### 2. 每 30 分鐘同步（降低頻率）

```python
'sync-all-dhcp-leases-every-30-minutes': {
    'task': 'api.tasks.sync_all_dhcp_leases_task',
    'schedule': crontab(minute='*/30'),  # 每 30 分鐘
    'options': {
        'expires': 1620,  # 任務超時 27 分鐘
    }
},
```

#### 3. 每小時同步（最低頻率）

```python
'sync-all-dhcp-leases-hourly': {
    'task': 'api.tasks.sync_all_dhcp_leases_task',
    'schedule': crontab(minute=0),  # 每小時整點
    'options': {
        'expires': 3300,  # 任務超時 55 分鐘
    }
},
```

#### 4. 特定時間同步（例如每天早上 8 點）

```python
'sync-all-dhcp-leases-daily-8am': {
    'task': 'api.tasks.sync_all_dhcp_leases_task',
    'schedule': crontab(hour=8, minute=0),  # 每天 08:00
    'options': {
        'expires': 3300,  # 任務超時 55 分鐘
    }
},
```

### 應用配置更改

**修改配置後，需要重啟 Celery 服務：**

```bash
# 重啟 Celery Beat（排程器）
docker compose restart celery-beat

# 重啟 Celery Worker（執行器）
docker compose restart celery-worker

# 或一起重啟
docker compose restart celery-worker celery-beat

# 確認服務狀態
docker compose ps celery-worker celery-beat
```

---

## 🧪 手動測試同步

### 方法 1：透過 Django Shell

```bash
# 進入 Django Shell
docker exec -it nt-django python manage.py shell

# 執行以下 Python 代碼
from api.tasks import sync_all_dhcp_leases_task
result = sync_all_dhcp_leases_task.delay()
print(f"Task ID: {result.id}")

# 等待幾秒後檢查結果
result.get(timeout=300)  # 最多等待 5 分鐘
```

### 方法 2：透過 Celery 命令

```bash
# 手動觸發租約同步任務
docker exec nt-django celery -A network_toolbox call api.tasks.sync_all_dhcp_leases_task

# 或使用 inspect 查看任務狀態
docker exec nt-django celery -A network_toolbox inspect active
```

### 方法 3：使用測試腳本

**創建測試腳本 `/tmp/test_sync_leases.py`：**

```python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'network_toolbox.settings')
django.setup()

from api.tasks import sync_all_dhcp_leases_task

print('📡 手動觸發 DHCP 租約批次同步任務...')
result = sync_all_dhcp_leases_task.delay()
print(f'✅ 任務已提交，Task ID: {result.id}')
print(f'📊 使用以下命令查看日誌：')
print(f'   docker compose logs celery-worker -f')
```

**執行測試：**

```bash
docker exec nt-django python /tmp/test_sync_leases.py
```

---

## 📈 監控與統計

### 查看任務執行狀態

```bash
# 查看 Celery 工作進程狀態
docker exec nt-django celery -A network_toolbox status

# 查看活躍任務
docker exec nt-django celery -A network_toolbox inspect active

# 查看已註冊的任務
docker exec nt-django celery -A network_toolbox inspect registered

# 查看定時任務配置
docker exec nt-django celery -A network_toolbox inspect scheduled
```

### 查看租約同步統計

**透過 Django Admin 或前端查看：**

1. **前端頁面**：租約管理 → 查看各伺服器的租約統計
2. **Django Admin**：http://localhost/admin/api/dhcpserver/
   - `total_leases`：總租約數
   - `active_leases`：活躍租約數
   - `last_sync_at`：最後同步時間

### 使用 Flower 監控（可選）

**Flower 是 Celery 的 Web 監控工具：**

```bash
# 啟動 Flower
docker compose up -d flower

# 訪問監控介面
http://localhost:5555
```

**Flower 功能：**
- 即時查看任務執行狀態
- 查看任務歷史記錄
- 監控 Worker 性能
- 查看任務成功率和失敗率

---

## ❓ 常見問題（FAQ）

### Q1: 自動同步與手動同步會衝突嗎？

**不會。** 兩種方式可以並存：
- 自動同步：每 15 分鐘在背景執行
- 手動同步：當您需要立即獲取最新數據時使用

### Q2: 如何確認自動同步正在運行？

**檢查方法：**

```bash
# 1. 確認 Celery 服務運行中
docker compose ps | grep celery

# 2. 查看最近的同步日誌
docker compose logs celery-worker --tail 50 | grep "租約同步"

# 3. 檢查 Server 的 last_sync_at 欄位
# 進入 Django Shell
docker exec -it nt-django python manage.py shell

# 執行
from api.models import DHCPServer
for server in DHCPServer.objects.filter(status='online'):
    print(f"{server.name}: {server.last_sync_at}")
```

### Q3: 租約同步失敗怎麼辦？

**故障排查步驟：**

1. **查看錯誤日誌**：
   ```bash
   docker compose logs celery-worker | grep "ERROR"
   tail -f logs/django_error.log
   ```

2. **檢查伺服器連線**：
   - 確認 DHCP Server 狀態為 `online`
   - 測試 SSH 連接：`ssh username@server_ip`
   - 檢查 PowerShell 權限

3. **手動測試單一伺服器**：
   ```python
   # Django Shell
   from api.models import DHCPServer
   from api.ssh_powershell_service import WindowsSSHPowerShellService
   
   server = DHCPServer.objects.get(id=1)
   with WindowsSSHPowerShellService(server) as service:
       result = service.sync_leases_to_db()
   print(result)
   ```

4. **重啟 Celery 服務**：
   ```bash
   docker compose restart celery-worker celery-beat
   ```

### Q4: 自動同步會影響系統性能嗎？

**不會。** 優化設計：
- ⏱️ 任務超時限制：防止長時間佔用資源
- 🔄 自動重試機制：失敗後自動重試 2 次
- 🧵 並行處理：Worker 可同時處理多個伺服器
- 📉 分散負載：錯開日誌同步（10分鐘）和租約同步（15分鐘）

### Q5: 如何停用自動同步？

**臨時停用（不修改代碼）：**

```bash
# 停止 Celery Beat（不會影響手動同步）
docker compose stop celery-beat

# 恢復自動同步
docker compose start celery-beat
```

**永久停用（修改配置）：**

編輯 `backend/network_toolbox/celery.py`，註釋掉租約同步任務：

```python
# 'sync-all-dhcp-leases-every-15-minutes': {
#     'task': 'api.tasks.sync_all_dhcp_leases_task',
#     'schedule': crontab(minute='*/15'),
#     'options': {
#         'expires': 810,
#     }
# },
```

然後重啟服務：

```bash
docker compose restart celery-beat
```

### Q6: 租約數據多久更新一次？

**更新頻率：**
- **自動同步**：每 15 分鐘
- **手動同步**：即時（點擊按鈕後立即執行）
- **前端顯示**：即時（重新載入頁面或 API 請求）

**資料時效性：**
- DHCP 租約通常以小時或天為單位
- 15 分鐘的更新頻率足以滿足大多數監控需求
- 緊急情況可使用手動同步獲取即時數據

### Q7: 自動同步會同步哪些伺服器？

**同步範圍：**
- ✅ 只同步狀態為 `online` 的伺服器
- ❌ 跳過 `offline` 或 `error` 狀態的伺服器
- 🔄 動態發現：新增伺服器會自動納入同步

**確認同步範圍：**

```python
# Django Shell
from api.models import DHCPServer
servers = DHCPServer.objects.filter(status='online')
for s in servers:
    print(f"✅ {s.name} ({s.ip_address})")
```

---

## 🔧 進階設定

### 自訂任務超時時間

**修改 `backend/api/tasks.py` 中的任務裝飾器：**

```python
@shared_task(
    bind=True,
    name='api.tasks.sync_all_dhcp_leases_task',
    max_retries=2,
    default_retry_delay=300,
    time_limit=1800,      # 硬限制（調整這裡）
    soft_time_limit=1650  # 軟限制（調整這裡）
)
```

### 調整重試策略

```python
@shared_task(
    bind=True,
    name='api.tasks.sync_all_dhcp_leases_task',
    max_retries=3,          # 最多重試 3 次（預設 2 次）
    default_retry_delay=600, # 重試延遲 10 分鐘（預設 5 分鐘）
    # ...
)
```

### 針對特定伺服器的同步策略

**在任務函數中添加過濾條件：**

```python
# 只同步特定 IP 範圍的伺服器
servers = DHCPServer.objects.filter(
    status='online',
    ip_address__startswith='10.250.'
)

# 或排除特定伺服器
servers = DHCPServer.objects.filter(
    status='online'
).exclude(name='TestServer')
```

---

## 📚 相關文檔

- [DHCP 日誌自動同步](./AUTO_SYNC_DHCP_LOGS.md) - 日誌同步功能說明
- [定時任務快速入門](../../QUICKSTART_AUTO_SYNC_LEASES.md) - 快速參考指南
- [Celery 定時任務](https://docs.celeryproject.org/en/stable/userguide/periodic-tasks.html) - 官方文檔

---

## 📝 更新記錄

- **2025-10-31**：初始版本，實現租約自動同步功能
- **同步頻率**：每 15 分鐘
- **同步範圍**：所有在線 DHCP Server
- **功能特性**：自動重試、錯誤處理、詳細日誌

---

**維護者**：Network Toolbox Team  
**最後更新**：2025-10-31
