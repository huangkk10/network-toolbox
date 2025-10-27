# LogsTab 使用說明

## 概覽

LogsTab 是 DHCP Server 分析頁面的「日誌查看」功能模組，提供實時日誌查看、過濾和下載功能。

## 功能特性

### ✅ 已實現功能

1. **多來源日誌讀取**
   - 本地日誌：讀取 `/app/logs/dhcp_operations.log`
   - 遠端 SSH：通過 SSH 連接讀取 DHCP Server 的日誌文件

2. **日誌過濾**
   - 按級別過濾：ALL / INFO / WARN / ERROR / DEBUG
   - 關鍵字搜尋：支持模糊匹配
   - 可調整顯示筆數：50 / 100 / 200 / 500 / 1000 筆

3. **實時更新**
   - 自動刷新：每 3 秒自動載入最新日誌
   - 手動刷新：點擊「重新載入」按鈕

4. **日誌操作**
   - 清除螢幕：清空當前顯示的日誌
   - 下載日誌：將當前日誌導出為 .txt 文件

5. **統計資訊**
   - 顯示總行數
   - 顯示各級別日誌數量（INFO / WARN / ERROR / DEBUG）

## 界面說明

### 控制列（第一行）

```
┌────────────────────────────────────────────────────────────┐
│ [本地日誌] [遠端SSH]  [日誌等級▼]  [🔍搜尋關鍵字...]        │
│ [顯示筆數▼]  自動更新: [○]  [🔄重新載入] [清除] [下載]      │
└────────────────────────────────────────────────────────────┘
```

#### 1. 日誌來源選擇

- **本地日誌**（預設）：
  - 讀取 Docker 容器內的 `/app/logs/dhcp_operations.log`
  - 包含 Django 應用層面的操作記錄
  - 總是可用

- **遠端 SSH**：
  - 通過 SSH 連接到選定的 DHCP Server
  - 讀取伺服器上的 `/var/log/dhcpd.log` 等文件
  - 需要在 Server 設定中配置 SSH 憑證
  - 當選擇「所有 Server」時此選項不可用

#### 2. 日誌等級篩選

| 等級 | 說明 | 顏色標籤 |
|------|------|---------|
| ALL | 顯示所有等級 | - |
| INFO | 一般資訊訊息 | 藍色 |
| WARN | 警告訊息 | 橙色 |
| ERROR | 錯誤訊息 | 紅色 |
| DEBUG | 除錯訊息 | 灰色 |

#### 3. 關鍵字搜尋

- 輸入任意關鍵字（不區分大小寫）
- 支持模糊匹配
- 例如：搜尋 "DHCPOFFER" 可找到所有 OFFER 事件
- 可與日誌等級組合使用

#### 4. 顯示筆數

- 預設：200 筆
- 可選：50 / 100 / 200 / 500 / 1000 筆
- 從日誌文件末尾往前取指定數量

#### 5. 自動更新

- 開啟後每 3 秒自動刷新日誌
- 適合監控實時日誌流
- 自動滾動到最新日誌

#### 6. 操作按鈕

- **重新載入**：手動刷新日誌
- **清除螢幕**：清空當前顯示的日誌（不影響文件）
- **下載日誌**：下載當前篩選後的日誌為 TXT 文件

### 統計區域（第二行）

顯示當前顯示的日誌統計：

```
總計: 200 行 | INFO: 91 | WARN: 36 | ERROR: 57 | DEBUG: 16
```

### 日誌內容區

以類似終端的樣式顯示日誌：

```
2025-01-26 10:15:23   INFO    DHCP server started successfully
2025-01-26 10:16:10   INFO    DHCPDISCOVER from 00:1a:2b:3c:4d:5e via eth0
2025-01-26 10:25:30   WARN    Address pool is 80% full (160/200 addresses in use)
2025-01-26 10:35:22   ERROR   Failed to assign address: pool exhausted
```

## API 端點

### `/api/dhcp-analytics/logs/`

**方法**: GET

**參數**:

| 參數 | 類型 | 必填 | 預設值 | 說明 |
|------|------|------|--------|------|
| server | string | ✅ | - | Server ID 或 "all" |
| source | string | ❌ | local | 日誌來源：local / remote |
| limit | int | ❌ | 100 | 返回最多幾筆 |
| level | string | ❌ | - | 日誌等級篩選 |
| keyword | string | ❌ | - | 關鍵字搜尋 |

**範例請求**:

```bash
# 讀取本地 200 筆日誌
GET /api/dhcp-analytics/logs/?server=1&source=local&limit=200

# 只顯示 ERROR 級別
GET /api/dhcp-analytics/logs/?server=1&level=ERROR

# 搜尋包含 "pool" 的 WARN 日誌
GET /api/dhcp-analytics/logs/?server=1&level=WARN&keyword=pool
```

**回應格式**:

```json
[
  {
    "id": 1,
    "timestamp": "2025-01-26 10:15:23",
    "level": "INFO",
    "message": "DHCP server started successfully",
    "raw": "[INFO] 2025-01-26 10:15:23 | DHCP server started successfully"
  },
  ...
]
```

## 日誌格式支持

後端日誌解析器支持多種格式：

### 1. 標準格式（推薦）

```
[LEVEL] timestamp | message
```

範例：
```
[INFO] 2025-01-26 10:15:23 | DHCP server started successfully
[ERROR] 2025-01-26 10:35:22 | Failed to assign address: pool exhausted
```

### 2. Syslog 格式

```
timestamp hostname process[pid]: LEVEL: message
```

範例：
```
Jan 26 10:15:23 dhcp-server dhcpd[1234]: INFO: DHCPDISCOVER from 00:1a:2b:3c:4d:5e
```

### 3. 簡單格式

```
timestamp LEVEL message
```

範例：
```
2025-01-26 10:15:23 INFO DHCP server started
```

### 4. 純時間戳格式

```
timestamp message
```

範例：
```
2025-01-26 10:15:23 DHCPDISCOVER from 00:1a:2b:3c:4d:5e via eth0
```

> **注意**：如果日誌行不包含明確的級別，系統會根據關鍵字自動推斷：
> - 包含 "error", "failed", "fail" → ERROR
> - 包含 "warn", "warning" → WARN
> - 包含 "debug" → DEBUG
> - 其他 → INFO

## 使用場景

### 場景 1：監控 DHCP 服務狀態

1. 選擇「本地日誌」
2. 設定「顯示筆數」為 200
3. 開啟「自動更新」
4. 觀察日誌流

### 場景 2：排查 IP 池耗盡問題

1. 選擇日誌等級：ERROR
2. 輸入關鍵字：pool
3. 點擊「搜尋」
4. 查看結果，找出問題時間點

### 場景 3：追蹤特定 MAC 地址

1. 輸入關鍵字：00:1a:2b:3c:4d:5e
2. 查看該設備的所有 DHCP 事件
3. 下載日誌以供分析

### 場景 4：生成日誌報告

1. 設定時間範圍（透過選擇 Server）
2. 選擇要包含的等級（如只看 ERROR + WARN）
3. 點擊「下載日誌」
4. 獲得 TXT 文件用於報告

## 故障排查

### 問題：日誌數量很少（< 50 行）

**可能原因**：
1. 日誌文件本身內容不多
2. 篩選條件太嚴格（等級 + 關鍵字）
3. 顯示筆數設定太小

**解決方法**：
1. 檢查實際日誌文件：
   ```bash
   docker exec nt-django wc -l /app/logs/dhcp_operations.log
   ```
2. 移除篩選條件，設定等級為「ALL」
3. 增加顯示筆數到 500 或 1000

### 問題：無法讀取遠端日誌

**可能原因**：
1. 未配置 SSH 憑證
2. SSH 連接失敗
3. 遠端日誌文件路徑錯誤

**解決方法**：
1. 到「Server 設定」Tab 配置 SSH 資訊
2. 測試 SSH 連接：
   ```bash
   docker exec nt-django python manage.py shell
   >>> from api.services import DHCPServerSSH
   >>> ssh = DHCPServerSSH('192.168.1.1', 'root', 'password')
   >>> ssh.connect()
   ```
3. 查看後端日誌：
   ```bash
   docker exec nt-django tail -f /app/logs/django.log
   ```

### 問題：日誌混雜 Django 自身日誌

**說明**：
- 這是正常行為，Django 的日誌也會寫入 `dhcp_operations.log`
- Django 日誌格式：`[INFO] 2025-10-27 12:26:26,460 | api.services | ...`
- DHCP 日誌格式：`[INFO] 2025-01-26 10:15:23 | DHCP server started...`

**解決方法**（可選）：
- 使用關鍵字篩選排除 Django 日誌：搜尋 "DHCP"
- 或者修改 Django settings.py 將自身日誌寫到其他文件

## 技術細節

### 前端組件

**位置**: `frontend/src/components/dhcp-analytics/LogsTab.js`

**主要狀態**:
- `logs`: 日誌列表
- `loading`: 載入狀態
- `logLevel`: 選中的日誌等級
- `keyword`: 搜尋關鍵字
- `autoRefresh`: 自動更新開關
- `source`: 日誌來源 (local/remote)
- `limit`: 顯示筆數

**主要方法**:
- `loadLogs()`: 從 API 載入日誌
- `handleClear()`: 清除螢幕
- `handleDownload()`: 下載日誌

### 後端服務

**位置**: `backend/api/services.py`

**類別**:

1. **DHCPLogParser**: 日誌解析器
   - `parse_dhcp_log_line()`: 解析單行日誌
   - `parse_log_file()`: 解析整個文件
   - `_infer_log_level()`: 推斷日誌等級

2. **DHCPLogService**: 日誌服務
   - `get_local_logs()`: 讀取本地日誌
   - `get_remote_logs()`: 讀取遠端日誌

### API 視圖

**位置**: `backend/api/views.py`

**函數**: `dhcp_analytics_logs()`

## 未來改進計畫

- [ ] 日誌即時串流（WebSocket）
- [ ] 日誌搜尋歷史記錄
- [ ] 日誌高亮（語法著色）
- [ ] 日誌時間範圍篩選
- [ ] 日誌導出為 CSV / JSON
- [ ] 日誌分析統計圖表
- [ ] 日誌告警規則設定

---

**最後更新**: 2025-10-27  
**版本**: 1.0  
**維護者**: Network Toolbox Team
