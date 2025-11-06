# 📊 日誌系統說明

## 📁 日誌檔案說明

| 檔案名稱 | 用途 | 保留天數 | 級別 |
|---------|------|---------|------|
| `django.log` | 一般應用程式日誌 | 30 天 | INFO+ |
| `django_error.log` | 錯誤和異常日誌 | 60 天 | ERROR+ |
| `dhcp_operations.log` | DHCP 伺服器操作記錄 | 15 天 | INFO+ |
| `api_access.log` | API 訪問記錄 | 7 天 | INFO+ |
| `celery_health.log` | Celery 健康檢查記錄 | 手動管理 | INFO+ |

## 🩺 Celery 健康檢查

### 健康檢查腳本

專案包含一個自動化的 Celery 健康檢查腳本，用於監控和修復 Task 註冊問題。

**腳本位置：** `/home/owner/Codes/network-toolbox/scripts/check_celery_health.sh`

### 功能說明

✅ **自動檢測問題**：
- 檢查 Celery Worker 和 Beat 容器是否運行
- 檢查已註冊的 `api.tasks` 數量（預期 ≥15 個）
- 檢查最近 2 小時的 Task 執行記錄

🔧 **自動修復**：
- 容器未運行 → 自動啟動
- Task 註冊異常 → 自動重啟服務
- 重啟後再次驗證修復結果

📝 **日誌記錄**：
- 所有檢查和修復操作記錄到 `logs/celery_health.log`
- 包含時間戳、狀態、錯誤訊息和修復結果

### 使用方式

#### **手動執行檢查**

當您懷疑 Celery 有問題時，可以手動執行：

```bash
# 執行健康檢查
/home/owner/Codes/network-toolbox/scripts/check_celery_health.sh

# 或從專案根目錄執行
cd /home/owner/Codes/network-toolbox
./scripts/check_celery_health.sh
```

#### **查看檢查結果**

```bash
# 查看最近的健康檢查記錄
tail -50 logs/celery_health.log

# 即時監控健康檢查
tail -f logs/celery_health.log

# 查看今天的檢查記錄
grep "$(date +%Y-%m-%d)" logs/celery_health.log

# 查看所有異常記錄
grep "❌" logs/celery_health.log
```

### 檢查結果說明

**✅ 正常狀態**：
```
✅ 容器運行中
當前註冊的 api.tasks 數量：16
✅ Celery Tasks 狀態正常（16 個已註冊）
✅ 最近的 auto_store_workspaces 執行：[時間] SUCCESS
```

**❌ 異常狀態**：
```
❌ Celery Tasks 註冊異常！
   預期：至少 15 個 tasks
   實際：只有 8 個 tasks
🔧 正在重啟 Celery 服務...
```

**⚠️  警告狀態**：
```
⚠️  警告：最近 2 小時內未發現 auto_store_workspaces 執行記錄
   這可能是正常的（如果系統剛啟動）或表示 Beat 調度問題
```

### 何時使用

建議在以下情況手動執行健康檢查：

1. **發現功能異常**
   - Jenkins Workspace 沒有自動備份
   - DHCP 資料同步失敗
   - 定時任務沒有執行

2. **服務重啟後**
   - Docker 容器重啟
   - 伺服器重新開機
   - 代碼更新部署

3. **定期檢查**
   - 每天早上檢查一次
   - 部署新功能後
   - 發現系統效能異常

4. **問題排查**
   - 查看日誌發現錯誤
   - 用戶回報功能問題
   - 監控告警觸發

### 常見問題處理

**問題 1：Task 註冊數量為 0**
```bash
# 檢查 Worker 日誌
docker compose logs celery_worker --tail 50

# 查看是否有代碼錯誤
grep "ERROR\|Exception" logs/django.log | tail -20

# 手動重啟服務
docker compose restart celery_worker celery_beat
```

**問題 2：重啟後仍然異常**
```bash
# 完全停止並重建容器
docker compose down
docker compose up -d

# 等待 30 秒後再次檢查
sleep 30 && ./scripts/check_celery_health.sh
```

**問題 3：容器無法啟動**
```bash
# 檢查容器錯誤
docker compose logs celery_worker --tail 100

# 檢查磁碟空間
df -h

# 檢查 Docker 服務
sudo systemctl status docker
```

## 🔍 常用命令

### 即時查看日誌
```bash
# 查看一般日誌
tail -f logs/django.log

# 查看錯誤日誌
tail -f logs/django_error.log

# 查看 DHCP 操作日誌
tail -f logs/dhcp_operations.log

# 查看 API 訪問日誌
tail -f logs/api_access.log
```

### 搜尋日誌
```bash
# 搜尋錯誤
grep "ERROR" logs/django.log

# 搜尋特定用戶操作
grep "username" logs/django.log

# 搜尋最近 1 小時的錯誤
grep "ERROR" logs/django.log | grep "$(date +%Y-%m-%d\ %H)"
```

### 統計分析
```bash
# 統計錯誤數量
grep -c "ERROR" logs/django.log

# 查看日誌檔案大小
du -h logs/*

# 查看所有日誌總大小
du -sh logs/
```

## 📊 日誌格式

### Verbose 格式（主要日誌）
```
[INFO] 2025-10-27 12:00:00,000 | api.views | user_list | Line 45 | User list retrieved successfully
[ERROR] 2025-10-27 12:05:30,123 | django.request | get_response | Line 124 | Internal Server Error: /api/users/
```

### Simple 格式（API 訪問）
```
[INFO] 2025-10-27 12:00:00,000 django.request: GET /api/users/
[INFO] 2025-10-27 12:00:05,000 api.views: User created successfully
```

### Detailed 格式（詳細除錯）
```
[DEBUG] 2025-10-27 12:00:00,000 | PID:1234 | Thread:5678 | api.services | sync_dhcp_data | Line 89 | Starting DHCP data sync
```

## 🔄 日誌輪替機制

- **輪替時間**：每天午夜（00:00）自動輪替
- **命名規則**：檔案名後加上日期，如 `django.log.2025-10-27`
- **自動清理**：超過保留天數的舊日誌會自動刪除

## 📝 使用範例

### 查看今天的錯誤
```bash
grep "ERROR" logs/django.log
```

### 查看昨天的日誌
```bash
cat logs/django.log.$(date -d "yesterday" +%Y-%m-%d)
```

### 查看特定日期範圍的錯誤
```bash
# 查看 10/20 到 10/25 的錯誤
for date in {20..25}; do
    grep "ERROR" logs/django.log.2025-10-$date 2>/dev/null
done
```

### 統計每天的 API 請求數
```bash
# 統計今天的 API 請求
grep -c "GET\|POST\|PUT\|DELETE" logs/api_access.log
```

## 🛠️ 故障排查

### 日誌未生成
1. 檢查目錄權限：`ls -la logs/`
2. 檢查容器內掛載：`docker exec nt-django ls -la /app/logs/`
3. 重啟服務：`docker compose restart django`

### 磁碟空間不足
```bash
# 檢查日誌總大小
du -sh logs/

# 手動清理 30 天前的日誌
find logs/ -name "*.log.*" -mtime +30 -delete
```

## 💡 最佳實踐

1. **定期檢查錯誤日誌**
   ```bash
   tail -50 logs/django_error.log
   ```

2. **監控日誌大小**
   ```bash
   du -sh logs/ && df -h
   ```

3. **定期備份重要日誌**
   ```bash
   tar -czf logs_backup_$(date +%Y%m%d).tar.gz logs/*.log
   ```

4. **使用日誌分析工具**
   - 可使用 `awk`、`sed` 進行進階分析
   - 可整合 ELK Stack 或 Grafana Loki 進行視覺化監控

## 📌 注意事項

- 日誌檔案會隨時間增長，請定期監控磁碟空間
- 敏感資訊（如密碼）不應記錄在日誌中
- 生產環境建議將日誌級別調整為 WARNING 或 ERROR
- 建議定期備份重要日誌以便長期追蹤分析
