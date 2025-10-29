# IPXE 日誌自動化設置指南

## 📋 概述

本指南說明如何設置 IPXE 日誌的自動收集和清理任務。

---

## 🔧 方法 1: 使用自動化腳本（推薦）

```bash
# 執行設置腳本
./scripts/setup_ipxe_cron.sh
```

腳本會自動：
- ✅ 設置每 10 分鐘收集一次日誌
- ✅ 設置每天凌晨 2 點清理 7 天前的日誌
- ✅ 創建日誌檔案 `/var/log/ipxe_collect.log` 和 `/var/log/ipxe_cleanup.log`

---

## ⚙️ 方法 2: 手動設置 Cron

### 1. 編輯 Crontab

```bash
crontab -e
```

### 2. 添加以下任務

```cron
# IPXE 日誌自動化
*/10 * * * * docker exec nt-django python manage.py collect_ipxe_logs --limit 1000 >> /var/log/ipxe_collect.log 2>&1
0 2 * * * docker exec nt-django python manage.py cleanup_ipxe_logs --days 7 >> /var/log/ipxe_cleanup.log 2>&1
```

### 3. 創建日誌檔案

```bash
sudo touch /var/log/ipxe_collect.log
sudo touch /var/log/ipxe_cleanup.log
sudo chmod 666 /var/log/ipxe_collect.log
sudo chmod /666 /var/log/ipxe_cleanup.log
```

---

## 📊 任務說明

### 日誌收集任務

- **頻率**: 每 10 分鐘
- **命令**: `collect_ipxe_logs --limit 1000`
- **作用**: 從所有在線 IPXE 伺服器收集最新 1000 條日誌
- **日誌**: `/var/log/ipxe_collect.log`

### 日誌清理任務

- **頻率**: 每天凌晨 2:00
- **命令**: `cleanup_ipxe_logs --days 7`
- **作用**: 刪除超過 7 天的舊日誌
- **日誌**: `/var/log/ipxe_cleanup.log`

---

## 🔍 監控與管理

### 查看 Cron 任務

```bash
crontab -l
```

### 查看收集日誌輸出

```bash
tail -f /var/log/ipxe_collect.log
```

### 查看清理日誌輸出

```bash
tail -f /var/log/ipxe_cleanup.log
```

### 手動執行任務

```bash
# 手動收集日誌
docker exec nt-django python manage.py collect_ipxe_logs

# 手動清理日誌（測試模式）
docker exec nt-django python manage.py cleanup_ipxe_logs --dry-run --verbose

# 手動清理日誌（實際執行）
docker exec nt-django python manage.py cleanup_ipxe_logs --days 7
```

---

## ⚙️ 自訂設置

### 調整收集頻率

```cron
# 每 5 分鐘收集一次
*/5 * * * * docker exec nt-django python manage.py collect_ipxe_logs --limit 1000

# 每 30 分鐘收集一次
*/30 * * * * docker exec nt-django python manage.py collect_ipxe_logs --limit 1000

# 每小時收集一次
0 * * * * docker exec nt-django python manage.py collect_ipxe_logs --limit 1000
```

### 調整保留天數

```cron
# 保留 3 天
0 2 * * * docker exec nt-django python manage.py cleanup_ipxe_logs --days 3

# 保留 14 天
0 2 * * * docker exec nt-django python manage.py cleanup_ipxe_logs --days 14

# 保留 30 天
0 2 * * * docker exec nt-django python manage.py cleanup_ipxe_logs --days 30
```

### 只收集特定伺服器

```cron
# 只收集 Server ID = 1
*/10 * * * * docker exec nt-django python manage.py collect_ipxe_logs --server 1 --limit 1000
```

---

## 🛠️ 故障排查

### Cron 任務沒有執行

1. 檢查 Cron 服務狀態：
   ```bash
   sudo systemctl status cron
   ```

2. 檢查 Cron 日誌：
   ```bash
   grep CRON /var/log/syslog
   ```

3. 確認 Docker 容器正在運行：
   ```bash
   docker compose ps
   ```

### 日誌收集失敗

1. 檢查收集日誌輸出：
   ```bash
   tail -n 50 /var/log/ipxe_collect.log
   ```

2. 手動執行並查看錯誤：
   ```bash
   docker exec nt-django python manage.py collect_ipxe_logs --verbose
   ```

3. 檢查 Django 日誌：
   ```bash
   tail -f logs/django_error.log
   ```

### 日誌檔案權限問題

```bash
sudo chmod 666 /var/log/ipxe_collect.log
sudo chmod 666 /var/log/ipxe_cleanup.log
```

---

## 🗑️ 移除自動化任務

### 移除 Cron 任務

```bash
crontab -e
# 刪除包含 'collect_ipxe_logs' 和 'cleanup_ipxe_logs' 的行
```

### 刪除日誌檔案

```bash
sudo rm /var/log/ipxe_collect.log
sudo rm /var/log/ipxe_cleanup.log
```

---

## 📌 注意事項

1. **Docker 容器名稱**: 確保使用正確的容器名稱 `nt-django`
2. **時區**: Cron 使用系統時區，確認時區設置正確
3. **日誌輪替**: 考慮使用 `logrotate` 管理 Cron 輸出日誌
4. **資源使用**: 收集頻率過高可能影響性能，建議保持 10 分鐘
5. **保留時間**: 根據磁碟空間調整日誌保留天數

---

**最後更新**: 2025-10-29  
**維護者**: Network Toolbox Team
