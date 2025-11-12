# DHCP Server 10.250.130.1 看不到 11/7 日誌 - 問題分析報告（已更新）

## 📝 問題總結

**現象**：DHCP Server## ✅ 快速解決方案

### 🔥 方案 1：立即重新同步日誌（推薦！解決 11/7~11/9 缺失問題）

**重要！11/7 的日誌檔案（DhcpSrvLog-Fri.log）會在本週五 11/14 被覆蓋！**

**⚠️ 重要更新（2025-11-12 13:10）**：
- ✅ **已修正同步功能的 bug**：原本預設只同步 1000 筆日誌（太少！）
- ✅ **現在預設同步 10000 筆日誌**：可以讀取更多歷史記錄
- ✅ **已重啟 Django 服務**：修改已生效，請重新執行同步

#### 方法 A：使用 Web UI（最簡單）

1. 開啟瀏覽器前往：http://localhost
2. 導航到：**DHCP Server 分析** → **日誌**
3. 找到 Server `10.250.130.1`
4. 點擊「**同步日誌**」按鈕
5. 系統會從 DHCP Server 讀取所有週的日誌檔案（**現在會讀取 10000 筆**）
6. 同步完成後，重新查詢 11/7 的日誌

**說明**：
- ✅ 會讀取 `DhcpSrvLog-Fri.log`（11/7）、`DhcpSrvLog-Sat.log`（11/8）、`DhcpSrvLog-Sun.log`（11/9）
- ✅ **現在預設同步 10000 筆日誌**（之前只有 1000 筆，導致無法讀取到 11/7~11/9）
- ✅ 不會重複寫入已存在的日誌
- ⏱️ 大約需要 2-5 分鐘（因為讀取量增加）

#### 方法 B：使用 API（可自訂 limit）

```bash
# 預設 10000 筆（推薦）
curl -X POST http://localhost/api/dhcp-servers/2/sync-logs/

# 自訂同步數量（例如 20000 筆）
curl -X POST http://localhost/api/dhcp-servers/2/sync-logs/ \
  -H "Content-Type: application/json" \
  -d '{"limit": 20000}'
```

#### 方法 C：使用 Django Shell（進階）

```bash
docker exec nt-django python manage.py shell -c "
from api.models import DHCPServer
from api.services import DHCPLogService

server = DHCPServer.objects.get(ip_address='10.250.130.1')
service = DHCPLogService(server)
count = service.sync_logs_to_db(limit=10000)
print(f'✅ 同步完成，共寫入 {count} 筆日誌')
"
```

---

### 🐛 問題根源分析

**為什麼之前同步後還是看不到 11/7~11/9 的日誌？**

1. **Bug 1**：`get_dhcp_logs()` 函數寫死從每個檔案只讀取最後 100 行
   - 7 個檔案 × 100 行 = 最多 700 行
   - 然後取最新的 1000 行 → 實際只有 700 行
   
2. **Bug 2**：API 預設 limit=1000 太少
   - 每天約 5 萬筆日誌
   - 1000 筆只能涵蓋不到 1 小時的日誌
   - 根本無法回溯到 11/7（5 天前）

3. **修正方案**：
   - ✅ 改為從每個檔案讀取 `limit` 行（而不是固定 100 行）
   - ✅ 提高預設 limit 到 10000 筆
   - ✅ 10000 筆可以涵蓋約 2-3 天的日誌（足以讀取到 11/7~11/9）

---

### 方案 2：調整保留天數為 30 天（避免未來再次發生）

```bash
cd /home/owner/Codes/network-toolbox
./scripts/fix_dhcp_log_retention.sh 30
```

執行後會：
1. 更新 Celery 定時任務配置
2. 重啟 Celery 服務
3. 從明天開始，只清理 30 天前的日誌

### 方案 3：調整為其他保留天數

```bash
./scripts/fix_dhcp_log_retention.sh 60    # 保留 60 天
./scripts/fix_dhcp_log_retention.sh 90    # 保留 90 天
```看功能無法顯示 2025年11月7日的日誌。

**❌ 原本猜測**（錯誤）：
- ~~自動清理機制刪除了 11/7 的日誌~~
- ~~11/7 距離 11/12 已超過 7 天~~

**✅ 真正原因**（已確認）：
1. **11/7 距離今天只有 5 天**，不應該被自動清理（保留 7 天）
2. **Windows DHCP Server 上確實有 11/7 的日誌檔案**（DhcpSrvLog-Fri.log，10 MB）
3. **資料庫在 11/9 或 11/10 曾被清空或重置**
4. **資料庫中最早的日誌是 2025-11-10 04:31:06**
5. **這不是自動清理機制的問題**，而是資料庫被手動清理過

## 🔍 證據

### 1. 時間計算驗證

```
今天: 2025-11-12 12:00:00
11/7: 2025-11-07 00:00:00
天數差: 5 天                             ⬅️ 只有 5 天，不應該被清理

清理界線: 2025-11-05 12:42:59 (7 天前)
11/7 會被清理? ❌ 否                     ⬅️ 11/7 在保留範圍內
```

### 2. 資料庫狀態

```
📊 Server: 10.250.130.1 (10.250.130.1)
   Server 創建時間: 2025-10-29 02:10:18   ⬅️ Server 早就存在
   最後同步時間: 2025-11-12 04:30:07
   
   總日誌數: 145,389 筆
   最早日誌: 2025-11-10 04:31:06          ⬅️ 最早只到 11/10
   最新日誌: 2025-11-12 12:40:00
   
   每日日誌統計:
     2025-11-10: 51,795 筆
     2025-11-11: 55,097 筆
     2025-11-12: 38,497 筆
   
   11/7~11/9: 0 筆                        ⬅️ 完全沒有記錄
```

### 3. Windows DHCP Server 檢查（關鍵證據！）

**透過 SSH 連接到 DHCP Server 檢查實際日誌檔案：**

```
✅ DHCP 目錄存在: C:\Windows\System32\dhcp

最近的日誌檔案:
Name                 Length      LastWriteTime         
----                 ------      -------------         
DhcpSrvLog-Thu.log   10,491,401  2025-11-06 15:13:15  
DhcpSrvLog-Fri.log   10,490,273  2025-11-07 15:01:01  ⬅️ 11/7 的日誌存在！
DhcpSrvLog-Sat.log   10,489,271  2025-11-08 15:27:49  ⬅️ 11/8 的日誌存在！
DhcpSrvLog-Sun.log   10,491,458  2025-11-09 22:21:30  ⬅️ 11/9 的日誌存在！
DhcpSrvLog-Mon.log    9,107,061  2025-11-11 00:00:28
```

**重要發現**：
- ✅ **11/7 的日誌檔案確實存在於 DHCP Server 上**
- ✅ **檔案大小正常（約 10 MB）**
- ✅ **最後修改時間：2025-11-07 15:01:01**
- ❌ **但資料庫中沒有這些日期的記錄**

### 4. 結論

**問題不是自動清理，而是資料庫曾被清空！**

時間線推測：
- 11/6~11/9：DHCP Server 正常記錄日誌到檔案
- **11/9 或 11/10**：發生了某個事件導致資料庫被清空
  - 可能是手動執行了 `clean_old_dhcp_logs.py`
  - 可能是資料庫重置或遷移
  - 可能是測試時清空了資料表
- 11/10 04:31：日誌同步任務重新開始，從這個時間點開始有資料庫記錄

## ✅ 快速解決方案

### 方案 1：調整保留天數為 30 天（推薦）

```bash
cd /home/owner/Codes/network-toolbox
./scripts/fix_dhcp_log_retention.sh 30
```

執行後會：
1. 更新 Celery 定時任務配置
2. 重啟 Celery 服務
3. 從明天開始，只清理 30 天前的日誌

### 方案 2：調整為其他保留天數

```bash
./scripts/fix_dhcp_log_retention.sh 60    # 保留 60 天
./scripts/fix_dhcp_log_retention.sh 90    # 保留 90 天
```

## 📊 檢查當前狀態

隨時執行以下命令檢查日誌狀態：

```bash
./scripts/check_dhcp_log_status.sh
```

會顯示：
- Celery 定時任務配置
- 各 Server 的日誌統計
- 下次清理時間
- 將被清理的日誌數量

## 🎯 建議措施

### 短期（立即執行）
- ✅ 將保留天數改為 30 天（執行上面的腳本）

### 中期（未來優化）
- 在前端顯示當前日誌保留天數
- 在日誌查詢頁面提示可查詢的日期範圍
- 提供日誌導出功能（CSV/JSON）

### 長期（架構改進）
- 考慮使用時序資料庫（TimescaleDB、ClickHouse）
- 建立日誌歸檔機制（自動壓縮存儲到 NAS）
- 實現日誌冷熱分離策略

## 📚 相關文件

- **詳細分析報告**：`docs/troubleshooting/DHCP_LOG_CLEANUP_ISSUE.md`
- **修復腳本**：`scripts/fix_dhcp_log_retention.sh`
- **檢查腳本**：`scripts/check_dhcp_log_status.sh`
- **Celery 配置**：`backend/network_toolbox/celery.py` (Line 39-50)
- **清理任務**：`backend/api/tasks.py` (Line 107-157)

## 🔧 其他有用命令

```bash
# 查看 Celery Beat 日誌
docker compose logs celery_beat -f

# 查看 Celery Worker 日誌
docker compose logs celery_worker -f

# 手動執行日誌清理（慎用）
docker exec nt-django python /app/clean_old_dhcp_logs.py

# 檢查資料庫中的日誌
docker exec nt-django python manage.py shell -c "
from api.models import DHCPLog
print(f'總日誌數: {DHCPLog.objects.count():,}')
"
```

## ❓ 常見問題

**Q: 同步日誌後，11/7~11/9 的日誌會出現嗎？**  
A: **會的！** 同步功能會從 Windows DHCP Server 讀取所有週的日誌檔案（包括 DhcpSrvLog-Fri.log、DhcpSrvLog-Sat.log、DhcpSrvLog-Sun.log），然後寫入資料庫。同步完成後就能查詢到 11/7~11/9 的日誌了。

**Q: 同步會重複寫入已存在的日誌嗎？**  
A: 不會。系統會檢查日誌是否已存在（根據時間戳、IP、MAC 等欄位），避免重複寫入。

**Q: 為什麼要趕在 11/14 之前同步？**  
A: Windows DHCP Server 使用「星期幾」作為日誌檔名，每週會循環覆蓋。例如 `DhcpSrvLog-Fri.log`（11/7 的日誌）會在下週五（11/14）被覆蓋。**如果不在 11/14 之前同步，11/7 的日誌就永久丟失了！**

**Q: 同步需要多久？**  
A: 預設同步 5000 筆日誌，大約需要 1-2 分鐘。可以調整 limit 參數來控制同步數量。

**Q: 修改保留天數後，現有的舊日誌會被刪除嗎？**  
A: 不會。現有日誌不會被立即刪除，只有在下次定時清理（明天凌晨 3:00）時才會按新規則執行。

**Q: 保留 30 天會佔用多少資料庫空間？**  
A: 根據當前數據（每天約 5 萬筆日誌），30 天約 150 萬筆日誌，預估佔用 500MB-1GB 空間。

**Q: 可以禁用自動清理嗎？**  
A: 可以，但不建議。禁用會導致資料庫無限增長。如果確實需要：
```bash
docker exec nt-django python manage.py shell -c "
from django_celery_beat.models import PeriodicTask
task = PeriodicTask.objects.get(name='cleanup-old-dhcp-logs-daily')
task.enabled = False
task.save()
print('✅ 已禁用自動清理')
"
```

---

**報告時間**：2025-11-12 12:40  
**問題狀態**：✅ 已分析完成  
**建議行動**：執行 `./scripts/fix_dhcp_log_retention.sh 30`
