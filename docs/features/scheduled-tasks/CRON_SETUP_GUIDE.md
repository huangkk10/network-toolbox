# 📅 Cron 定時任務設置指南

## 🎯 目標

設置自動化定時任務，實現：
- ✅ **每 5 分鐘**同步一次 DHCP 日誌到資料庫
- ✅ **每天凌晨 3 點**清理 7 天前的舊日誌
- ✅ 7 天後達到完整的 7 天滾動日誌視窗

---

## 📋 前置需求

### 1. 確認 Docker 服務正常運行

```bash
# 檢查容器狀態
docker compose ps

# 應該看到 nt-django 容器狀態為 Up
# NAME        IMAGE                    STATUS
# nt-django   network-toolbox-django   Up XX hours
```

### 2. 測試管理命令

```bash
# 測試同步命令（同步 100 筆日誌）
docker exec nt-django python manage.py sync_dhcp_logs --server 1 --limit 100

# 測試清理命令（dry-run 模式，不會實際刪除）
docker exec nt-django python manage.py clean_old_logs --days 7 --dry-run
```

如果命令執行成功，就可以繼續設置 Cron。

---

## ⚙️ Cron 設置步驟

### 步驟 1：編輯 Crontab

```bash
# 開啟 crontab 編輯器
crontab -e
```

**第一次執行會詢問選擇編輯器**：
- 選擇 `nano`（簡單好用）或 `vim`（進階）
- 推薦初學者選擇 `nano`（通常是選項 1）

### 步驟 2：添加 Cron 任務

在開啟的編輯器中，**在檔案最下方**添加以下兩行：

```cron
# DHCP 日誌自動同步（每 5 分鐘執行一次）
*/5 * * * * docker exec nt-django python manage.py sync_dhcp_logs --server 1 --limit 500 >> /home/owner/Codes/network-toolbox/logs/cron_sync.log 2>&1

# DHCP 日誌自動清理（每天凌晨 3 點執行）
0 3 * * * docker exec nt-django python manage.py clean_old_logs --days 7 >> /home/owner/Codes/network-toolbox/logs/cron_cleanup.log 2>&1
```

**📝 參數說明**：

| 參數 | 說明 |
|------|------|
| `*/5 * * * *` | 每 5 分鐘執行一次 |
| `0 3 * * *` | 每天凌晨 3:00 執行 |
| `--server 1` | 同步 Server ID = 1 的日誌 |
| `--limit 500` | 每次最多同步 500 筆新日誌 |
| `--days 7` | 刪除 7 天前的日誌 |
| `>> .../cron_sync.log` | 將輸出追加到日誌檔案 |
| `2>&1` | 將錯誤訊息也記錄到日誌檔案 |

### 步驟 3：保存並退出

- **nano 編輯器**：
  - 按 `Ctrl + O`（寫入檔案）
  - 按 `Enter`（確認檔名）
  - 按 `Ctrl + X`（退出）

- **vim 編輯器**：
  - 按 `Esc` 鍵
  - 輸入 `:wq` 並按 `Enter`

保存成功後，會看到類似訊息：
```
crontab: installing new crontab
```

### 步驟 4：驗證 Cron 任務已安裝

```bash
# 查看已安裝的 cron 任務
crontab -l
```

應該會看到剛才添加的兩行任務。

---

## ✅ 驗證 Cron 是否正常運行

### 1. 檢查 Cron 服務狀態

```bash
# 確認 cron 服務正在運行（Ubuntu/Debian）
sudo systemctl status cron

# 或者（CentOS/RHEL）
sudo systemctl status crond
```

應該看到 `Active: active (running)` 狀態。

### 2. 等待 5 分鐘後檢查日誌

```bash
# 查看同步日誌（等待 5 分鐘後執行）
tail -f logs/cron_sync.log

# 應該會看到類似輸出：
# 同步伺服器: Windows DHCP Server (10.250.50.1)
#   - 讀取: 500 筆 | 新增: 15 筆 | 跳過: 485 筆 | 錯誤: 0 筆
```

### 3. 查看資料庫日誌增長情況

```bash
# 查詢資料庫日誌數量
docker exec nt-django python manage.py shell << 'EOF'
from api.models import DHCPLog
from django.db.models.functions import TruncDate
from django.db.models import Count

logs = DHCPLog.objects.annotate(
    date=TruncDate('timestamp')
).values('date').annotate(
    count=Count('id')
).order_by('date')

print("\n資料庫日誌日期分佈:")
for item in logs:
    print(f"  {item['date']}: {item['count']} 筆")

print(f"\n總計: {DHCPLog.objects.count()} 筆")
EOF
```

**預期結果時間線**：

| 時間點 | 資料庫狀態 |
|--------|-----------|
| **今天（10/28）** | 只有 1 天數據（996 筆） |
| **明天（10/29）** | 2 天數據（約 2000 筆） |
| **第 7 天（11/3）** | 7 天數據（完整視窗） |
| **第 8 天起** | 保持 7 天滾動視窗 |

---

## 🔧 調整與優化

### 修改同步頻率

如果覺得 5 分鐘太頻繁或太慢，可以調整：

```bash
crontab -e
```

**常見時間設定**：

| Cron 表達式 | 執行頻率 |
|-------------|----------|
| `*/5 * * * *` | 每 5 分鐘 |
| `*/10 * * * *` | 每 10 分鐘 |
| `*/15 * * * *` | 每 15 分鐘 |
| `*/30 * * * *` | 每 30 分鐘 |
| `0 * * * *` | 每小時（整點） |
| `0 */2 * * *` | 每 2 小時 |

### 修改同步數量

如果日誌產生速度很快，可以增加 `--limit` 參數：

```cron
# 每次同步 1000 筆（適合高流量環境）
*/5 * * * * docker exec nt-django python manage.py sync_dhcp_logs --server 1 --limit 1000 >> ...
```

### 修改保留天數

如果想保留更多天數的日誌：

```cron
# 保留 30 天的日誌
0 3 * * * docker exec nt-django python manage.py clean_old_logs --days 30 >> ...
```

---

## 🛠️ 故障排查

### 問題 1：Cron 沒有執行

**檢查步驟**：

1. **確認 Cron 服務運行**：
   ```bash
   sudo systemctl status cron
   ```

2. **查看系統日誌**：
   ```bash
   grep CRON /var/log/syslog | tail -20
   ```

3. **檢查 Crontab 語法**：
   ```bash
   crontab -l
   ```

### 問題 2：命令執行失敗

**檢查 Cron 日誌**：

```bash
# 查看同步日誌
cat logs/cron_sync.log

# 查看清理日誌
cat logs/cron_cleanup.log
```

**常見錯誤**：

| 錯誤訊息 | 原因 | 解決方法 |
|---------|------|---------|
| `No such container: nt-django` | 容器名稱錯誤 | 檢查 `docker compose ps` 確認容器名稱 |
| `django.db.utils.OperationalError` | 資料庫連接失敗 | 檢查 PostgreSQL 是否運行 |
| `Permission denied` | 權限不足 | 檢查日誌目錄權限：`chmod 755 logs/` |

### 問題 3：Docker 容器重啟後 Cron 失效

**原因**：容器名稱可能改變（例如 `nt-django` → `nt-django_1`）

**解決方法 1**（推薦）：使用容器服務名稱

```bash
# 修改 crontab 使用 docker compose 命令
crontab -e

# 改為：
*/5 * * * * cd /home/owner/Codes/network-toolbox && docker compose exec -T django python manage.py sync_dhcp_logs --server 1 --limit 500 >> logs/cron_sync.log 2>&1
```

**解決方法 2**：鎖定容器名稱

在 `docker-compose.yml` 中明確指定容器名稱（已經設定好）：
```yaml
services:
  django:
    container_name: nt-django  # 固定名稱
```

---

## 📊 監控與維護

### 每日檢查（建議前 7 天）

```bash
# 檢查資料庫增長
docker exec nt-django python manage.py shell -c "
from api.models import DHCPLog
print(f'總日誌數: {DHCPLog.objects.count()}')
"

# 查看今天的同步情況
tail -50 logs/cron_sync.log
```

### 磁碟空間監控

```bash
# 查看日誌目錄大小
du -sh logs/

# 查看資料庫大小
docker exec nt-django python manage.py shell -c "
from django.db import connection
cursor = connection.cursor()
cursor.execute('''
    SELECT pg_size_pretty(pg_total_relation_size('api_dhcplog'));
''')
print(f'DHCPLog 表大小: {cursor.fetchone()[0]}')
"
```

**預期大小**：
- 7 天日誌：約 1.74 MB
- 30 天日誌：約 7.5 MB

### 週期性維護（可選）

```bash
# 手動觸發真空清理（優化資料庫空間）
docker exec nt-django python manage.py shell -c "
from django.db import connection
cursor = connection.cursor()
cursor.execute('VACUUM ANALYZE api_dhcplog;')
print('資料庫真空清理完成')
"
```

---

## 🚀 進階配置

### 多伺服器同步

如果有多台 DHCP Server，可以添加多個任務：

```cron
# Server 1 - 每 5 分鐘
*/5 * * * * docker exec nt-django python manage.py sync_dhcp_logs --server 1 --limit 500 >> logs/cron_sync_server1.log 2>&1

# Server 2 - 每 5 分鐘（錯開 2 分鐘）
2-59/5 * * * * docker exec nt-django python manage.py sync_dhcp_logs --server 2 --limit 500 >> logs/cron_sync_server2.log 2>&1
```

### 錯誤告警（Email 通知）

安裝郵件工具：
```bash
sudo apt-get install mailutils
```

修改 Cron 任務添加錯誤通知：
```cron
MAILTO=your-email@example.com

*/5 * * * * docker exec nt-django python manage.py sync_dhcp_logs --server 1 --limit 500 || echo "DHCP 同步失敗！" | mail -s "Cron Error" your-email@example.com
```

---

## 📖 Cron 時間表達式速查表

```
 ┌────────── 分鐘 (0 - 59)
 │ ┌──────── 小時 (0 - 23)
 │ │ ┌────── 日期 (1 - 31)
 │ │ │ ┌──── 月份 (1 - 12)
 │ │ │ │ ┌── 星期 (0 - 7，0 和 7 都代表星期日)
 │ │ │ │ │
 * * * * * 要執行的命令
```

**常用範例**：

| 表達式 | 說明 |
|--------|------|
| `0 0 * * *` | 每天午夜 12:00 |
| `0 */6 * * *` | 每 6 小時 |
| `30 2 * * 0` | 每週日凌晨 2:30 |
| `0 0 1 * *` | 每月 1 號午夜 |
| `*/10 9-17 * * 1-5` | 週一到週五 9:00-17:00 每 10 分鐘 |

---

## ✅ 完成確認清單

設置完成後，請確認以下項目：

- [ ] Cron 服務正在運行（`systemctl status cron`）
- [ ] Crontab 已正確安裝（`crontab -l`）
- [ ] 等待 5 分鐘後有日誌輸出（`cat logs/cron_sync.log`）
- [ ] 資料庫日誌數量正在增長
- [ ] 日誌目錄權限正確（`ls -la logs/`）
- [ ] Docker 容器名稱正確（`docker compose ps`）

---

## 📚 參考資源

- **Cron 語法檢查器**：https://crontab.guru/
- **Django 管理命令文檔**：https://docs.djangoproject.com/en/4.2/howto/custom-management-commands/
- **Docker Exec 文檔**：https://docs.docker.com/engine/reference/commandline/exec/

---

## 💡 常見問題 FAQ

### Q1：為什麼選擇 5 分鐘同步一次？

**答**：平衡數據即時性與系統負載：
- **太頻繁**（例如 1 分鐘）：增加 SSH 連接負擔，可能被 Windows Server 限流
- **太稀疏**（例如 30 分鐘）：日誌延遲過高，可能遺漏問題
- **5 分鐘**：最佳平衡點，既能及時發現問題，又不會過度消耗資源

### Q2：同步失敗會怎麼樣？

**答**：下次同步會自動補齊：
- 每次同步讀取 Windows Server 上的**最新 N 筆日誌**
- 資料庫會自動跳過已存在的日誌（使用時間戳 + 內容去重）
- 即使漏掉幾次同步，只要 Windows 日誌還在（7 天內），就能補回來

### Q3：清理日誌會影響正在查看的前端嗎？

**答**：不會影響：
- 清理在凌晨 3 點執行（使用者少）
- 只刪除 7 天前的舊資料
- 前端查詢預設範圍是 1 天，不會受影響

### Q4：可以暫停同步嗎？

**答**：可以臨時停用 Cron：
```bash
# 編輯 crontab
crontab -e

# 在任務前加上 # 註解掉
# */5 * * * * docker exec nt-django python manage.py sync_dhcp_logs ...

# 或者完全移除 crontab
crontab -r
```

### Q5：伺服器重啟後 Cron 會繼續運行嗎？

**答**：會自動恢復：
- Cron 是系統服務，開機自動啟動
- Crontab 配置儲存在使用者帳戶下（`/var/spool/cron/crontabs/`）
- 只需確保 Docker 服務開機自啟：`sudo systemctl enable docker`

---

**最後更新**：2025-10-28  
**作者**：Network Toolbox Team  
**版本**：1.0

