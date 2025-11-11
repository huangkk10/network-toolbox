# DHCP 租約自動同步 - 快速入門指南

## 🚀 一鍵啟動

```bash
# 執行啟動腳本
./start_auto_sync_leases.sh
```

**這個腳本會自動完成：**
1. ✅ 檢查 Docker 服務狀態
2. ✅ 重啟 Celery Worker 和 Beat 服務
3. ✅ 顯示定時任務配置
4. ✅ 手動觸發一次測試同步
5. ✅ 顯示即時日誌（20 秒）

---

## 📋 功能說明

### 自動同步特性

- **同步頻率**：每 15 分鐘自動執行一次
- **同步範圍**：所有狀態為 `online` 的 DHCP Server
- **同步內容**：租約資訊（IP、MAC、主機名、租約時間、狀態等）
- **自動統計**：更新活躍租約數、總租約數、最後同步時間

### 與手動同步的區別

| 對比項目 | 手動同步 | 自動同步 |
|---------|---------|---------|
| 觸發方式 | 點擊「同步租約」按鈕 | 定時自動執行 |
| 同步頻率 | 需要時手動觸發 | 每 15 分鐘 |
| 同步範圍 | 單一伺服器 | 所有在線伺服器 |
| 操作負擔 | 需要逐個操作 | 完全自動化 |
| 適用場景 | 緊急查詢最新數據 | 日常監控維護 |

---

## 🔍 查看同步狀態

### 快速檢查命令

```bash
# 1. 確認服務運行中
docker compose ps | grep celery

# 2. 查看最近同步日誌（最新 50 行）
docker compose logs celery-worker --tail 50 | grep "租約"

# 3. 即時追蹤日誌
docker compose logs celery-worker -f

# 4. 查看排程器狀態
docker compose logs celery-beat --tail 20
```

### 查看伺服器最後同步時間

```bash
# 進入 Django Shell
docker exec -it nt-django python manage.py shell

# 執行以下代碼
from api.models import DHCPServer
for server in DHCPServer.objects.filter(status='online'):
    print(f"{server.name}: 最後同步 {server.last_sync_at}, 活躍租約 {server.active_leases} 筆")
```

---

## 🛠️ 常用操作

### 重啟服務

```bash
# 重啟 Celery Worker（執行租約同步的工作進程）
docker compose restart celery-worker

# 重啟 Celery Beat（定時任務排程器）
docker compose restart celery-beat

# 一起重啟
docker compose restart celery-worker celery-beat
```

### 停止/啟動服務

```bash
# 停止自動同步（保留手動同步功能）
docker compose stop celery-beat

# 恢復自動同步
docker compose start celery-beat

# 完全停止 Celery
docker compose stop celery-worker celery-beat

# 啟動 Celery
docker compose up -d celery-worker celery-beat
```

### 手動觸發同步

```bash
# 方法 1：使用 Python 腳本
cat > /tmp/test_sync_leases.py << 'EOF'
import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'network_toolbox.settings')
django.setup()
from api.tasks import sync_all_dhcp_leases_task
print('📡 觸發租約批次同步...')
result = sync_all_dhcp_leases_task.delay()
print(f'✅ Task ID: {result.id}')
EOF

docker exec nt-django python /tmp/test_sync_leases.py

# 方法 2：使用 Celery 命令
docker exec nt-django celery -A network_toolbox call api.tasks.sync_all_dhcp_leases_task
```

---

## ⚙️ 調整同步頻率

**文件位置：** `backend/network_toolbox/celery.py`

### 預設：每 15 分鐘

```python
'sync-all-dhcp-leases-every-15-minutes': {
    'task': 'api.tasks.sync_all_dhcp_leases_task',
    'schedule': crontab(minute='*/15'),  # ⬅️ 修改這裡
    'options': {'expires': 810}
},
```

### 常用配置

| 頻率 | crontab 表達式 | expires 值 |
|-----|---------------|-----------|
| 每 10 分鐘 | `minute='*/10'` | 540 |
| 每 15 分鐘 | `minute='*/15'` | 810 |
| 每 20 分鐘 | `minute='*/20'` | 1080 |
| 每 30 分鐘 | `minute='*/30'` | 1620 |
| 每小時 | `minute=0` | 3300 |

**修改後重啟服務：**

```bash
docker compose restart celery-worker celery-beat
```

---

## 🐛 故障排查

### 問題 1：服務沒有運行

```bash
# 檢查容器狀態
docker compose ps celery-worker celery-beat

# 如果未運行，啟動服務
docker compose up -d celery-worker celery-beat
```

### 問題 2：看不到同步日誌

```bash
# 檢查 Beat 排程器是否發送任務
docker compose logs celery-beat | grep "sync-all-dhcp-leases"

# 檢查 Worker 是否接收任務
docker compose logs celery-worker | grep "sync_all_dhcp_leases_task"

# 如果沒有日誌，重啟服務
docker compose restart celery-worker celery-beat
```

### 問題 3：同步失敗

```bash
# 查看錯誤日誌
docker compose logs celery-worker | grep "ERROR"
tail -f logs/django_error.log

# 檢查伺服器連線（手動測試 SSH）
ssh administrator@10.250.71.1

# 手動觸發單一伺服器同步測試
docker exec -it nt-django python manage.py shell
# 然後執行：
from api.models import DHCPServer
from api.ssh_powershell_service import WindowsSSHPowerShellService
server = DHCPServer.objects.get(id=1)
with WindowsSSHPowerShellService(server) as service:
    result = service.sync_leases_to_db()
print(result)
```

### 問題 4：同步很慢

```bash
# 檢查活躍任務
docker exec nt-django celery -A network_toolbox inspect active

# 查看 Worker 狀態
docker exec nt-django celery -A network_toolbox status

# 增加 Worker 並發數（在 docker-compose.yml 中修改）
# --concurrency=4  # 預設是 2
```

---

## 📊 監控與統計

### 查看任務執行歷史

```bash
# 查看所有已註冊的任務
docker exec nt-django celery -A network_toolbox inspect registered

# 查看定時任務配置
docker exec nt-django celery -A network_toolbox inspect scheduled

# 查看任務統計
docker exec nt-django celery -A network_toolbox inspect stats
```

### 前端查看

1. **租約管理頁面**：查看各伺服器的租約列表
2. **伺服器詳情**：查看 `last_sync_at`（最後同步時間）
3. **統計數據**：
   - `total_leases`：總租約數
   - `active_leases`：活躍租約數

### 使用 Flower 監控（可選）

```bash
# 啟動 Flower Web 監控介面
docker compose up -d flower

# 訪問監控頁面
http://localhost:5555
```

**Flower 提供：**
- 📈 任務執行趨勢圖表
- 📊 成功/失敗統計
- 🔍 任務詳細資訊
- ⚡ 即時性能監控

---

## 📖 典型使用場景

### 場景 1：首次啟用自動同步

```bash
# 1. 執行啟動腳本
./start_auto_sync_leases.sh

# 2. 等待腳本完成，查看測試結果

# 3. 確認定時任務已排程
docker compose logs celery-beat | grep "lease"

# 4. 等待 15 分鐘，檢查是否自動執行
docker compose logs celery-worker --tail 100 | grep "租約同步"
```

### 場景 2：新增 DHCP Server 後

**自動同步會自動發現新伺服器，無需額外配置！**

```bash
# 只需確保新伺服器狀態為 online
# 下次自動同步時會自動包含新伺服器
```

### 場景 3：緊急查詢最新租約

**自動同步不影響手動同步：**

```bash
# 前端操作：直接點擊「同步租約」按鈕
# 或手動觸發：
docker exec nt-django python /tmp/test_sync_leases.py
```

### 場景 4：調整同步頻率

```bash
# 1. 編輯配置文件
nano backend/network_toolbox/celery.py

# 2. 修改 crontab 表達式（例如改為每 20 分鐘）
#    'schedule': crontab(minute='*/20'),

# 3. 重啟服務
docker compose restart celery-worker celery-beat

# 4. 確認新配置
docker compose logs celery-beat --tail 20
```

---

## 🆚 自動同步 vs 手動同步對比

### 自動同步優勢

✅ **省時省力**：無需逐個伺服器操作  
✅ **持續更新**：定時自動執行，數據始終保持較新  
✅ **全面覆蓋**：所有在線伺服器統一同步  
✅ **錯誤恢復**：自動重試機制，失敗後自動重試  
✅ **日誌完整**：詳細記錄每次同步結果  

### 手動同步優勢

✅ **即時性**：立即獲取最新數據  
✅ **針對性**：可指定單一伺服器同步  
✅ **可控性**：按需執行，不消耗系統資源  

### 建議使用方式

- **日常維護**：依賴自動同步（每 15 分鐘）
- **緊急情況**：使用手動同步（即時更新）
- **新伺服器**：首次可手動同步，之後自動接管
- **故障排查**：手動同步單一伺服器進行測試

---

## 📚 更多資訊

- **詳細文檔**：[AUTO_SYNC_DHCP_LEASES.md](docs/features/AUTO_SYNC_DHCP_LEASES.md)
- **日誌自動同步**：[AUTO_SYNC_DHCP_LOGS.md](docs/features/AUTO_SYNC_DHCP_LOGS.md)
- **Celery 官方文檔**：https://docs.celeryproject.org/

---

## 🎯 總結

### 核心功能

- 🔄 **自動同步**：每 15 分鐘批次同步所有在線 DHCP Server 的租約
- 🎯 **智能發現**：自動包含新增的在線伺服器
- 📊 **統計更新**：自動更新租約統計（總數、活躍數）
- 🛡️ **可靠性**：自動重試、錯誤隔離、詳細日誌

### 立即開始

```bash
# 一鍵啟動
./start_auto_sync_leases.sh

# 查看日誌
docker compose logs celery-worker -f

# 就這麼簡單！
```

---

**維護者**：Network Toolbox Team  
**最後更新**：2025-10-31  
**版本**：1.0.0
