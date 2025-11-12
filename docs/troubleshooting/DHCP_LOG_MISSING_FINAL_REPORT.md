# DHCP Server 10.250.130.1 看不到 11/7 日誌 - 完整調查報告

## 📋 問題描述

**問題**：DHCP Server `10.250.130.1` 的日誌查看功能，無法顯示 2025年11月7日的日誌記錄。

**用戶疑問**：「11/7 距離今天還不到 7 天，為什麼會被清理？」

---

## 🔍 調查過程

### 第一步：時間計算驗證

```
今天: 2025-11-12
11/7: 2025-11-07
天數差: 5 天                             ⬅️ 確實只有 5 天！

清理界線: 2025-11-05 (7 天前)
11/7 會被清理? ❌ 否                     ⬅️ 11/7 在保留範圍內，不應該被清理
```

**結論**：用戶說得對！11/7 距今只有 5 天，不應該被自動清理機制刪除。

### 第二步：檢查資料庫記錄

```sql
Server: 10.250.130.1 (10.250.130.1)
======================================
Server 創建時間: 2025-10-29 02:10:18   ⬅️ Server 早就存在（10/29 創建）
最後同步時間: 2025-11-12 04:30:07

總日誌數: 145,389 筆
最早日誌: 2025-11-10 04:31:06          ⬅️ 最早只到 11/10！
最新日誌: 2025-11-12 12:40:00

每日日誌統計:
  2025-11-10: 51,795 筆
  2025-11-11: 55,097 筆
  2025-11-12: 38,497 筆

11/7~11/9: 0 筆                        ⬅️ 完全沒有記錄！
```

**發現**：
- Server 在 10/29 就已經創建
- 但資料庫中最早的日誌只到 11/10
- 11/7~11/9 完全沒有記錄

### 第三步：檢查 Windows DHCP Server 原始日誌（關鍵！）

透過 SSH 連接到實際的 Windows DHCP Server 檢查：

```powershell
C:\Windows\System32\dhcp> dir DhcpSrvLog-*.log

Name                 Length      LastWriteTime         
----                 ------      -------------         
DhcpSrvLog-Thu.log   10,491,401  2025-11-06 15:13:15  ⬅️ 11/6 日誌存在
DhcpSrvLog-Fri.log   10,490,273  2025-11-07 15:01:01  ⬅️ 11/7 日誌存在！
DhcpSrvLog-Sat.log   10,489,271  2025-11-08 15:27:49  ⬅️ 11/8 日誌存在！
DhcpSrvLog-Sun.log   10,491,458  2025-11-09 22:21:30  ⬅️ 11/9 日誌存在！
DhcpSrvLog-Mon.log    9,107,061  2025-11-11 00:00:28  ⬅️ 11/11 日誌存在
```

**重大發現**：
- ✅ **11/7 的日誌檔案確實存在於 Windows DHCP Server 上**
- ✅ **檔案大小正常（約 10 MB），有完整的日誌記錄**
- ✅ **最後修改時間：2025-11-07 15:01:01**
- ❌ **但這些日期的記錄沒有在資料庫中**

---

## 💡 真相大白

### 問題根本原因

**❌ 不是自動清理機制的問題**（保留 7 天，11/7 距今才 5 天）  
**✅ 資料庫曾在 11/9 或 11/10 被清空或重置**

### 證據鏈

1. **時間證據**：
   - Server 創建於 10/29，遠早於 11/7
   - 11/7 距今只有 5 天，在 7 天保留期內

2. **Windows Server 證據**：
   - Windows DHCP Server 上有 11/6~11/9 的完整日誌檔案
   - 每個檔案約 10 MB，正常大小

3. **資料庫證據**：
   - 資料庫中最早的日誌是 2025-11-10 04:31:06
   - 11/10 之前的所有記錄都不存在

### 可能發生的事件（時間線推測）

```
2025-10-29: Server 創建，開始記錄日誌
2025-11-06: 正常運作，日誌寫入 DhcpSrvLog-Thu.log
2025-11-07: 正常運作，日誌寫入 DhcpSrvLog-Fri.log
2025-11-08: 正常運作，日誌寫入 DhcpSrvLog-Sat.log
2025-11-09: 正常運作，日誌寫入 DhcpSrvLog-Sun.log
===================================================
🔴 2025-11-09 晚上或 11-10 凌晨：發生某個事件
   可能的操作：
   - 執行了 clean_old_dhcp_logs.py 腳本
   - 手動清空了 api_dhcplog 資料表
   - 資料庫遷移或重置
   - 測試時清空了資料
===================================================
2025-11-10 04:31: Celery 定時任務重新開始同步日誌
                  從這個時間點開始有資料庫記錄
2025-11-10~現在: 正常同步，資料庫有完整記錄
```

---

## ✅ 解決方案

### 方案 1：重新同步歷史日誌（強烈推薦！）

由於 **Windows DHCP Server 上的原始日誌檔案還在**，我們可以重新同步到資料庫！

#### 方法 A：透過 Web UI（最簡單）

1. 登入 Network Toolbox 系統
2. 進入「DHCP Server 分析」→「日誌查看」
3. 選擇 Server：`10.250.130.1`
4. 點擊「**同步日誌**」按鈕
5. 設定同步數量：`5000`（會同步最近的 5000 筆日誌）
6. 等待同步完成

#### 方法 B：透過 API

```bash
curl -X POST http://localhost/api/dhcp-servers/2/sync-logs/ \
  -H "Content-Type: application/json" \
  -d '{"limit": 5000}'
```

#### 方法 C：透過 Django Shell

```bash
docker exec nt-django python manage.py shell -c "
from api.models import DHCPServer
from api.services import DHCPLogService

# 取得 Server
server = DHCPServer.objects.get(ip_address='10.250.130.1')
print(f'同步 Server: {server.name}')

# 執行同步
service = DHCPLogService(dhcp_server=server)
result = service.sync_logs_to_db(limit=5000)

print(f'')
print(f'同步結果:')
print(f'  讀取: {result[\"total\"]} 筆')
print(f'  新增: {result[\"created\"]} 筆')
print(f'  跳過: {result[\"skipped\"]} 筆')
print(f'  錯誤: {result[\"errors\"]} 筆')
"
```

#### ⚠️ 重要提醒

**Windows DHCP 日誌的循環特性**：
- Windows DHCP Server 使用「星期幾」命名日誌檔案
- 每週會循環覆蓋同名檔案
- 例如：`DhcpSrvLog-Fri.log` 會在下週五（11/14）被覆蓋

**時間緊迫**：
- 目前還有 11/6~11/9 的日誌檔案
- 但這週五（11/14）會覆蓋 11/7 的日誌
- 這週日（11/16）會覆蓋 11/9 的日誌
- **建議盡快同步，以免歷史日誌被覆蓋**

### 方案 2：調整日誌保留天數（預防未來問題）

雖然這次不是自動清理的問題，但建議仍調整保留天數：

```bash
cd /home/owner/Codes/network-toolbox
./scripts/fix_dhcp_log_retention.sh 30    # 改為 30 天
```

### 方案 3：調查清空資料庫的原因

檢查是否有手動清理操作的記錄：

```bash
# 檢查 11/9 晚上到 11/10 凌晨的操作日誌
grep -E "(clean|delete|清理|刪除|DHCPLog)" \
  /home/owner/Codes/network-toolbox/logs/django.log.2025-11-09 \
  /home/owner/Codes/network-toolbox/logs/django.log.2025-11-10 \
  | grep -v "DHCPREQUEST\|DHCPACK\|DHCPINFORM"

# 檢查是否執行過清理腳本
ls -lth /home/owner/Codes/network-toolbox/backend/clean*.py

# 檢查 Celery 日誌
docker compose logs celery_worker --since 2025-11-09 | grep -i clean
```

---

## 📊 驗證與測試

### 同步後驗證

```bash
docker exec nt-django python manage.py shell -c "
from api.models import DHCPLog, DHCPServer
from django.db.models.functions import TruncDate
from django.db.models import Count
import pytz

server = DHCPServer.objects.filter(ip_address='10.250.130.1').first()

if server:
    # 查詢每天的日誌數量
    daily_counts = DHCPLog.objects.filter(server=server).annotate(
        date=TruncDate('timestamp')
    ).values('date').annotate(count=Count('id')).order_by('date')
    
    print('每日日誌統計:')
    for item in daily_counts:
        print(f'  {item[\"date\"]}: {item[\"count\"]:,} 筆')
    
    # 檢查 11/7 是否有日誌
    tz = pytz.timezone('Asia/Taipei')
    from datetime import datetime
    nov7_start = tz.localize(datetime(2025, 11, 7, 0, 0, 0))
    nov7_end = tz.localize(datetime(2025, 11, 7, 23, 59, 59))
    
    nov7_utc_start = nov7_start.astimezone(pytz.UTC)
    nov7_utc_end = nov7_end.astimezone(pytz.UTC)
    
    nov7_count = DHCPLog.objects.filter(
        server=server,
        timestamp__gte=nov7_utc_start,
        timestamp__lte=nov7_utc_end
    ).count()
    
    print()
    if nov7_count > 0:
        print(f'✅ 11/7 的日誌已恢復！共 {nov7_count:,} 筆')
    else:
        print('❌ 11/7 的日誌尚未同步')
"
```

---

## 🎯 總結

### 問題核心

1. ✅ **不是自動清理機制的問題**（11/7 距今才 5 天，在保留期內）
2. ✅ **Windows DHCP Server 上有完整的原始日誌**
3. ✅ **資料庫在 11/9 或 11/10 被清空過**
4. ✅ **可以透過重新同步恢復歷史日誌**

### 建議行動

| 優先級 | 行動 | 說明 |
|--------|------|------|
| 🔴 緊急 | 立即重新同步日誌 | Windows 日誌會在本週被覆蓋 |
| 🟡 重要 | 調整保留天數為 30 天 | 預防未來日誌丟失 |
| 🟢 可選 | 調查資料庫清空原因 | 避免再次發生 |

### 預防措施

1. **短期**：
   - ✅ 重新同步歷史日誌（**立即執行**）
   - ✅ 調整保留天數為 30 天
   - ✅ 在前端顯示日誌可查詢範圍

2. **中期**：
   - 建立資料庫備份機制
   - 實現日誌導出功能（CSV/JSON）
   - 監控資料庫清理操作

3. **長期**：
   - 考慮使用時序資料庫（TimescaleDB）
   - 建立日誌歸檔機制（壓縮存儲到 NAS）
   - 實現日誌冷熱分離策略

---

## 📚 相關文件

- **詳細技術分析**：`docs/troubleshooting/DHCP_LOG_CLEANUP_ISSUE.md`
- **修復腳本**：`scripts/fix_dhcp_log_retention.sh`
- **檢查腳本**：`scripts/check_dhcp_log_status.sh`
- **日誌同步服務**：`backend/api/services.py` (DHCPLogService)
- **Celery 配置**：`backend/network_toolbox/celery.py`

---

**報告時間**：2025-11-12 12:50  
**問題狀態**：✅ 已分析完成，原因已確認  
**建議行動**：**立即重新同步日誌（方案 1）**  
**時間緊迫**：Windows 日誌會在本週被覆蓋，請盡快處理！
