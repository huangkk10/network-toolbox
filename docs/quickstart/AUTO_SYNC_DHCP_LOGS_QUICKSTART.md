# DHCP 日誌自動同步 - 快速開始指南

## 🚀 快速啟動

```bash
# 一鍵啟動自動同步服務
./start_auto_sync.sh
```

這個腳本會：
- ✅ 檢查 Docker 服務狀態
- ✅ 重啟 Celery Worker 和 Beat
- ✅ 顯示定時任務配置
- ✅ 手動測試一次同步
- ✅ 即時顯示同步日誌

---

## 📋 功能說明

### 自動同步

- **執行頻率**：每 10 分鐘自動執行一次
- **同步範圍**：所有狀態為 `online` 的 DHCP Server
- **同步數量**：每個伺服器最多 500 筆最新日誌
- **執行方式**：Celery 定時任務（背景執行）

### 不需要手動操作

添加 DHCP Server 後，系統會：
1. ✅ 創建時自動執行初始同步（Scopes + Leases + Logs）
2. ✅ 定時自動更新日誌（每 10 分鐘）
3. ✅ 自動清理舊日誌（每天凌晨 3 點，保留 15 天）

---

## 📊 查看同步狀態

### 即時查看日誌

```bash
# 查看 Celery Worker 日誌
docker compose logs celery-worker -f

# 查看 Celery Beat 日誌（排程器）
docker compose logs celery-beat -f

# 查看 Django 應用日誌
tail -f logs/django.log | grep Celery
```

### 檢查服務狀態

```bash
# 查看 Celery 容器狀態
docker compose ps | grep celery

# 應該看到：
# nt-celery-worker    Up
# nt-celery-beat      Up
```

---

## 🛠️ 常用命令

### 啟動/停止服務

```bash
# 啟動所有服務
docker compose up -d

# 只啟動 Celery
docker compose start celery-worker celery-beat

# 停止 Celery
docker compose stop celery-worker celery-beat

# 重啟 Celery（應用配置更改）
docker compose restart celery-worker celery-beat
```

### 手動觸發同步

```bash
# 方式 1：使用 shell 命令
docker exec nt-django python manage.py shell -c "from api.tasks import sync_all_dhcp_logs_task; result = sync_all_dhcp_logs_task.delay(); print(f'Task ID: {result.id}')"

# 方式 2：使用測試腳本
./start_auto_sync.sh
```

### 調整同步頻率

編輯 `backend/network_toolbox/celery.py`：

```python
# 每 5 分鐘（更頻繁）
'schedule': crontab(minute='*/5'),

# 每 15 分鐘（較少）
'schedule': crontab(minute='*/15'),

# 每小時整點
'schedule': crontab(minute=0),
```

修改後重啟：
```bash
docker compose restart celery-worker celery-beat
```

---

## ❓ 故障排查

### 問題 1：Celery 服務未啟動

```bash
# 檢查容器狀態
docker compose ps celery-worker celery-beat

# 如果未運行，啟動服務
docker compose up -d celery-worker celery-beat

# 查看錯誤日誌
docker compose logs celery-worker --tail 50
```

### 問題 2：日誌沒有自動更新

```bash
# 1. 檢查 Beat 是否正常排程
docker compose logs celery-beat --tail 20 | grep sync-all-dhcp-logs

# 2. 檢查 Worker 是否執行任務
docker compose logs celery-worker --tail 50 | grep "批次同步"

# 3. 檢查 DHCP Server 狀態（必須是 online）
docker exec nt-django python manage.py shell -c "from api.models import DHCPServer; print(list(DHCPServer.objects.values_list('name', 'status')))"
```

### 問題 3：Redis 連接失敗

```bash
# 檢查 Redis 狀態
docker compose ps redis

# 重啟 Redis
docker compose restart redis

# 重啟所有 Celery 服務
docker compose restart celery-worker celery-beat
```

---

## 📈 與手動同步的比較

| 項目 | 手動同步 | 自動同步 |
|------|---------|---------|
| 觸發方式 | 點擊按鈕 | 定時自動執行 |
| 同步範圍 | 單一伺服器 | 所有在線伺服器 |
| 執行頻率 | 按需執行 | 每 10 分鐘 |
| 同步數量 | 可自訂（預設 1000） | 固定 500 筆 |
| 執行環境 | Django Web | Celery Worker |
| 是否阻塞 | 阻塞請求 | 背景執行 |
| 使用場景 | 即時查看最新日誌 | 定期自動更新 |

**建議**：
- 平常讓自動同步運行即可
- 如需立即查看最新日誌，可使用手動同步

---

## 🎯 總結

### 改進前
- ❌ 需要手動點擊「同步日誌」按鈕
- ❌ 每個伺服器都要單獨同步
- ❌ 容易忘記更新
- ❌ 日誌不及時

### 改進後
- ✅ 完全自動化，無需手動操作
- ✅ 所有伺服器自動同步
- ✅ 定時更新（每 10 分鐘）
- ✅ 日誌始終保持最新
- ✅ 背景執行，不影響 Web 性能

---

## 📚 詳細文檔

- [完整功能說明](docs/features/AUTO_SYNC_DHCP_LOGS.md)
- [Celery 配置文件](backend/network_toolbox/celery.py)
- [任務定義](backend/api/tasks.py)

---

**功能版本**: v1.2.0  
**最後更新**: 2025-10-31  
**作者**: Network Toolbox Team

