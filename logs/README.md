# 📊 日誌系統說明

## 📁 日誌檔案說明

| 檔案名稱 | 用途 | 保留天數 | 級別 |
|---------|------|---------|------|
| `django.log` | 一般應用程式日誌 | 30 天 | INFO+ |
| `django_error.log` | 錯誤和異常日誌 | 60 天 | ERROR+ |
| `dhcp_operations.log` | DHCP 伺服器操作記錄 | 15 天 | INFO+ |
| `api_access.log` | API 訪問記錄 | 7 天 | INFO+ |

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
