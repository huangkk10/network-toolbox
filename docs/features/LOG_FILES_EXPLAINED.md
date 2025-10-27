# 日誌文件說明

## 📁 日誌文件結構

本專案使用多個日誌文件來分類記錄不同類型的訊息：

```
logs/
├── django.log                 # Django 應用程式所有日誌（保留 30 天）
├── django_error.log           # Django 錯誤日誌（保留 60 天）
├── dhcp_operations.log        # ⭐ DHCP Server 真實操作日誌（保留 15 天）
├── api_access.log             # API 訪問記錄（保留 7 天）
└── README.md                  # 日誌目錄說明
```

## 🎯 各日誌文件用途

### 1. `django.log` - Django 應用程式日誌

**內容**：Django 框架和應用程式的所有操作記錄

**包含**：
- Django 啟動/關閉訊息
- 資料庫查詢記錄（DEBUG 模式）
- 中間件處理記錄
- API 服務層的操作記錄（如 `api.services` 的日誌）
- 一般 INFO 級別訊息

**適用場景**：
- 排查 Django 應用程式問題
- 追蹤 Python 代碼執行流程
- 查看服務啟動過程

**範例**：
```
[INFO] 2025-10-27 12:25:04,525 | api.services | get_local_logs | Line 525 | 讀取本地日誌: 200 筆
[INFO] 2025-10-27 12:26:37,635 | api.views | dhcp_analytics_logs | Line 350 | 日誌請求: server=all, source=local
```

---

### 2. `django_error.log` - Django 錯誤日誌

**內容**：所有 ERROR 和 CRITICAL 級別的錯誤

**包含**：
- Python 異常和堆疊追蹤
- 資料庫連接錯誤
- API 調用失敗
- 未預期的錯誤

**適用場景**：
- 🔴 **緊急排錯**
- 系統穩定性監控
- 生產環境錯誤追蹤

**保留時間**：60 天（比其他日誌更久，方便長期追蹤問題）

**範例**：
```
[ERROR] 2025-10-27 10:30:15,123 | api.services | DHCPDataService.sync_leases_to_db | Line 280 | 同步租約失敗: Connection refused
Traceback (most recent call last):
  File "/app/api/services.py", line 278, in sync_leases_to_db
    ...
```

---

### 3. ⭐ `dhcp_operations.log` - DHCP Server 操作日誌

**內容**：**只包含真實的 DHCP Server 事件日誌**

**重要**：此文件不包含 Django 自身的日誌！

**包含**：
- DHCP 租約事件（DISCOVER, OFFER, REQUEST, ACK, RELEASE, NAK）
- IP 池狀態變化
- 租約過期記錄
- DHCP Server 配置變更
- MAC 地址衝突
- 遠端 DHCP Server 的 syslog 日誌

**來源**：
1. **模擬的 DHCP 事件**（開發/測試用）
2. **遠端 DHCP Server** 透過 SSH 讀取的真實日誌（如 `/var/log/dhcpd.log`）

**適用場景**：
- 📊 **LogsTab 頁面顯示**
- DHCP 事件監控
- 租約分配追蹤
- 網路問題排查
- 客戶端連接歷史

**格式**：
```
[LEVEL] YYYY-MM-DD HH:MM:SS | message
```

**範例**：
```
[INFO] 2025-10-27 10:15:23 | DHCP server started successfully
[INFO] 2025-10-27 10:16:10 | DHCPDISCOVER from 00:1a:2b:3c:4d:5e via eth0
[INFO] 2025-10-27 10:16:10 | DHCPOFFER on 192.168.1.100 to 00:1a:2b:3c:4d:5e via eth0
[INFO] 2025-10-27 10:16:11 | DHCPREQUEST for 192.168.1.100 from 00:1a:2b:3c:4d:5e via eth0
[INFO] 2025-10-27 10:16:11 | DHCPACK on 192.168.1.100 to 00:1a:2b:3c:4d:5e via eth0
[WARN] 2025-10-27 10:25:30 | Address pool is 80% full (160/200 addresses in use)
[ERROR] 2025-10-27 10:35:22 | Failed to assign address: pool exhausted
```

---

### 4. `api_access.log` - API 訪問記錄

**內容**：HTTP 請求訪問記錄

**包含**：
- API 端點訪問
- 請求方法（GET, POST, PUT, DELETE）
- 響應狀態碼
- 請求時間

**適用場景**：
- API 使用率分析
- 性能監控
- 安全審計

**保留時間**：7 天（高頻日誌，短期保留）

**範例**：
```
[INFO] 2025-10-27 10:30:45 | GET /api/dhcp-analytics/overview/ 200 OK
[WARNING] 2025-10-27 10:31:20 | POST /api/dhcp-sync-leases/ 500 Internal Server Error
```

---

## 🔧 日誌配置（Django settings.py）

### 修改歷史

**之前的配置問題**：
```python
'api.services': {
    'handlers': ['console', 'dhcp_operations_file', 'daily_error_file'],  # ❌ 錯誤
    'level': 'INFO',
    'propagate': False,
},
```

**問題**：Django 的 `api.services` 模組日誌也被寫入 `dhcp_operations.log`，導致：
- LogsTab 顯示混雜了 Django 內部操作日誌
- 難以區分真實 DHCP 事件和應用程式日誌
- 用戶看到類似 `[INFO] 2025-10-27 12:25:04,525 | api.services | get_local_logs | Line 525 | 讀取本地日誌: 200 筆` 的內容

**修正後的配置**：
```python
'api.services': {
    'handlers': ['console', 'daily_file', 'daily_error_file'],  # ✅ 正確
    'level': 'INFO',
    'propagate': False,
},
```

**結果**：
- ✅ `dhcp_operations.log` 只包含真實的 DHCP Server 日誌
- ✅ Django 應用程式日誌寫入 `django.log`
- ✅ LogsTab 顯示乾淨的 DHCP 事件

---

## 📊 LogsTab 顯示說明

### 「顯示: X 行 / 最多 Y 行」的意思

在 LogsTab 頁面頂部，你會看到統計資訊：

```
顯示: 200 行 / 最多 200 行 | INFO: 100 | WARN: 34 | ERROR: 54 | DEBUG: 12
```

**解釋**：

| 欄位 | 說明 |
|------|------|
| **顯示: 200 行** | 當前實際顯示的日誌行數 |
| **最多 200 行** | 你在「顯示筆數」下拉選單中選擇的限制 |
| **INFO: 100** | 當前顯示的日誌中，INFO 級別有 100 條 |
| **WARN: 34** | WARN 級別有 34 條 |
| **ERROR: 54** | ERROR 級別有 54 條 |
| **DEBUG: 12** | DEBUG 級別有 12 條 |

### 為什麼實際顯示可能少於限制？

1. **文件內容不足**：
   ```
   日誌文件只有 150 行，但你選擇「200 筆」
   → 實際顯示: 150 行 / 最多 200 行
   ```

2. **篩選條件限制**：
   ```
   選擇「ERROR」級別，共 200 行日誌中只有 54 條 ERROR
   → 實際顯示: 54 行 / 最多 200 行
   ```

3. **關鍵字搜尋**：
   ```
   搜尋 "pool"，200 行中只有 8 行包含此關鍵字
   → 實際顯示: 8 行 / 最多 200 行
   ```

4. **組合篩選**：
   ```
   選擇「WARN」+ 搜尋 "pool"
   → 實際顯示: 8 行 / 最多 200 行
   ```

### 顯示筆數選項

| 選項 | 說明 | 適用場景 |
|------|------|---------|
| **50 筆** | 快速預覽 | 查看最新事件 |
| **100 筆** | 一般監控 | 日常使用 |
| **200 筆**（預設）| 詳細查看 | 排查問題 |
| **500 筆** | 大量數據 | 深入分析 |
| **1000 筆** | 完整歷史 | 生成報告 |

**注意**：
- 較大的數值會增加載入時間
- 自動更新時建議使用較小的數值（50-200）
- 下載日誌時可以選擇最大值以獲得完整數據

---

## 🛠️ 維護指南

### 手動清理日誌

雖然日誌會自動輪替和刪除，但如果需要手動清理：

```bash
# 查看日誌文件大小
docker exec nt-django ls -lh /app/logs/

# 清理舊的備份日誌
docker exec nt-django find /app/logs/ -name "*.log.*" -mtime +30 -delete

# 清空特定日誌（保留文件）
docker exec nt-django sh -c "> /app/logs/dhcp_operations.log"
```

### 查看實時日誌

```bash
# Django 應用程式日誌
docker exec nt-django tail -f /app/logs/django.log

# DHCP 操作日誌
docker exec nt-django tail -f /app/logs/dhcp_operations.log

# 錯誤日誌
docker exec nt-django tail -f /app/logs/django_error.log

# 容器標準輸出（console handler）
docker compose logs django -f
```

### 生成測試日誌

如果需要生成測試 DHCP 日誌：

```bash
# 進入容器
docker exec -it nt-django bash

# 運行測試日誌生成腳本（如果有）
python manage.py shell
>>> from api.tests import generate_test_dhcp_logs
>>> generate_test_dhcp_logs(count=500)
```

或使用 Python 腳本（在主機上）：

```python
python3 << 'EOF'
import random
from datetime import datetime, timedelta

# 生成 DHCP 日誌
templates = [
    ("INFO", "DHCPDISCOVER from {mac} via eth0"),
    ("INFO", "DHCPOFFER on {ip} to {mac} via eth0"),
    # ...更多模板
]

# 生成並寫入文件
# ...
EOF
```

---

## 📈 日誌分析工具

### 使用內建腳本

```bash
# 分析日誌統計
./scripts/analyze_logs.sh

# 清理舊日誌
./scripts/clean_old_logs.sh 30  # 刪除 30 天前的日誌
```

### 使用命令行工具

```bash
# 統計各級別日誌數量
docker exec nt-django grep -c "\[INFO\]" /app/logs/dhcp_operations.log
docker exec nt-django grep -c "\[WARN\]" /app/logs/dhcp_operations.log
docker exec nt-django grep -c "\[ERROR\]" /app/logs/dhcp_operations.log

# 查找特定 MAC 地址的所有事件
docker exec nt-django grep "00:1a:2b:3c:4d:5e" /app/logs/dhcp_operations.log

# 查找 IP 池警告
docker exec nt-django grep "pool.*full" /app/logs/dhcp_operations.log

# 統計今天的錯誤數量
docker exec nt-django grep "\[ERROR\]" /app/logs/django_error.log | grep "$(date +%Y-%m-%d)" | wc -l
```

---

## ❓ 常見問題

### Q1: LogsTab 顯示的日誌混雜了 Django 自身的日誌？

**A**: 這個問題已在 2025-10-27 修正。確保：
1. Django settings.py 中 `api.services` 的 handlers 不包含 `dhcp_operations_file`
2. 重啟 Django 容器：`docker compose restart django`
3. 清理現有的混雜日誌（參考「手動清理日誌」章節）

### Q2: 為什麼顯示的日誌數量少於我選擇的筆數？

**A**: 可能原因：
- 日誌文件本身內容不足
- 有篩選條件（日誌等級或關鍵字）
- 檢查統計資訊：`顯示: X 行 / 最多 Y 行`

### Q3: 如何獲取更多歷史日誌？

**A**: 
1. 增加「顯示筆數」到 500 或 1000
2. 查看輪替的舊日誌：`docker exec nt-django ls /app/logs/*.log.*`
3. 如需更久的歷史，增加 `backupCount` 設定（需修改 settings.py）

### Q4: 日誌檔案太大怎麼辦？

**A**:
- 自動輪替會在每天午夜自動分割
- 超過保留天數的自動刪除
- 手動清理：參考「維護指南」章節

---

**最後更新**: 2025-10-27  
**維護者**: Network Toolbox Team
