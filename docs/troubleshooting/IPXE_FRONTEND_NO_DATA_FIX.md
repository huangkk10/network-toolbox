# iPXE 前端顯示無資料問題修復報告

## 📋 問題描述

**問題現象**：
- 用戶反映 iPXE 伺服器 10.250.120.2 的前端頁面顯示「無資料」
- 前端顯示：總租賃數: 0, 網口數量: 0, MAC 管理請求: 0, BOOT 請求: 0
- 後端資料庫實際有 2400+ 筆日誌記錄
- Celery 自動同步任務正常運行

**影響範圍**：
- iPXE 分析頁面 (iPXE分析) 完全無法顯示數據
- 用戶無法查看已成功收集的 iPXE 日誌統計資訊

**發生時間**：2025-11-07

---

## 🔍 根本原因分析

### API 設計錯誤

**問題根源**：`ipxe_analytics_overview` API 查詢了錯誤的資料表

**錯誤代碼位置**：`backend/api/views/ipxe_analytics.py`

#### 錯誤的實現 ❌

```python
# 第 40-46 行（修復前）
logs_query = DHCPLog.objects.filter(
    timestamp__gte=cutoff_time,
    client_type__in=['PXE', 'iPXE', 'WinPE']
)
if server_id:
    logs_query = logs_query.filter(server_id=server_id)
```

**問題分析**：
1. **查詢錯誤的表**：iPXE 日誌存儲在 `IPXELog` 表，但 API 卻查詢 `DHCPLog` 表
2. **欄位不匹配**：
   - `DHCPLog` 使用 `client_type` 欄位區分日誌類型
   - `IPXELog` 使用 `log_type` 欄位 ('MAC' 或 'BOOT')
3. **統計方式錯誤**：
   - 使用 `message__icontains='MAC'` 從訊息內容分析
   - 實際應使用 `log_type='MAC'` 直接查詢
4. **伺服器模型錯誤**：
   - 使用 `DHCPServer` 模型
   - 實際應使用 `IPXEServer` 模型

#### 正確的實現 ✅

```python
# 修復後
logs_query = IPXELog.objects.filter(
    timestamp__gte=cutoff_time
)
if server_id:
    logs_query = logs_query.filter(server_id=server_id)
```

---

## 🛠️ 修復步驟

### 1. 驗證資料庫狀態

```bash
# 確認資料庫中有日誌記錄
docker exec nt-django python manage.py shell -c "
from api.models import IPXEServer, IPXELog
server = IPXEServer.objects.get(ip_address='10.250.120.2')
print(f'Server ID: {server.id}')
print(f'Total logs: {server.ipxelog_set.count()}')
print(f'MAC logs: {server.ipxelog_set.filter(log_type=\"MAC\").count()}')
print(f'BOOT logs: {server.ipxelog_set.filter(log_type=\"BOOT\").count()}')
print(f'Last sync: {server.last_sync_at}')
"
```

**結果**：
- Server ID: 4
- Total logs: 2422
- MAC logs: 1262
- BOOT logs: 1160
- Last sync: 2025-11-07 02:20:04

✅ 資料庫狀態正常

### 2. 測試 API 問題

```bash
# 測試 API 響應
curl -s http://localhost/api/ipxe-analytics/overview/?server_id=4
```

**結果**（修復前）：
```json
{
  "summary": {
    "total_logs": 0,
    "mac_logs": 0,
    "boot_logs": 0,
    ...
  }
}
```

❌ API 返回全部為 0，確認 API 層問題

### 3. 修改 API 實現

修改檔案：`backend/api/views/ipxe_analytics.py`

#### 修改 1：基礎查詢（第 40-46 行）
```python
# 修復前
logs_query = DHCPLog.objects.filter(
    timestamp__gte=cutoff_time,
    client_type__in=['PXE', 'iPXE', 'WinPE']
)

# 修復後
logs_query = IPXELog.objects.filter(
    timestamp__gte=cutoff_time
)
```

#### 修改 2：統計計算（第 49-69 行）
```python
# 修復前
mac_logs_count = logs_query.filter(message__icontains='MAC').count()
boot_logs_count = logs_query.count()  # 錯誤：所有日誌都算 BOOT
mac_set_operations = logs_query.filter(
    Q(message__icontains='MAC') & Q(message__icontains='SET')
).count()

# 修復後
mac_logs_count = logs_query.filter(log_type='MAC').count()
boot_logs_count = logs_query.filter(log_type='BOOT').count()
mac_set_operations = logs_query.filter(
    log_type='MAC',
    action='SET'
).count()
```

#### 修改 3：每日趨勢統計（第 72-90 行）
```python
# 修復前
'mac_logs': day_logs.filter(message__icontains='MAC').count(),
'boot_logs': day_logs.count(),

# 修復後
'mac_logs': day_logs.filter(log_type='MAC').count(),
'boot_logs': day_logs.filter(log_type='BOOT').count(),
```

#### 修改 4：每小時統計（第 95-108 行）
```python
# 修復前
'mac_logs': hour_logs.filter(message__icontains='MAC').count(),
'boot_logs': hour_logs.count(),

# 修復後
'mac_logs': hour_logs.filter(log_type='MAC').count(),
'boot_logs': hour_logs.filter(log_type='BOOT').count(),
```

#### 修改 5：伺服器統計（第 110-145 行）
```python
# 修復前
try:
    server = DHCPServer.objects.get(id=sid)
    server_name = server.name
    server_ip = server.ip_address
except DHCPServer.DoesNotExist:
    server_name = f'Server {sid}'
    server_ip = 'N/A'

server_stats.append({
    'total_logs': server_logs.count(),
    'mac_logs': server_logs.filter(message__icontains='MAC').count(),
    'last_sync': None,
})

# 修復後
try:
    server = IPXEServer.objects.get(id=sid)
    server_name = server.name
    server_ip = server.ip_address
    last_sync = server.last_sync_at.isoformat() if server.last_sync_at else None
except IPXEServer.DoesNotExist:
    server_name = f'Server {sid}'
    server_ip = 'N/A'
    last_sync = None

server_stats.append({
    'total_logs': server_logs.count(),
    'mac_logs': server_logs.filter(log_type='MAC').count(),
    'boot_logs': server_logs.filter(log_type='BOOT').count(),
    'last_sync': last_sync,
})
```

#### 修改 6：Top MAC 地址統計（第 141-148 行）
```python
# 修復前
top_mac_addresses = []  # 因為 DHCPLog 的 MAC 在 message 中，無法統計

# 修復後
top_mac_data = logs_query.filter(
    mac_address__isnull=False
).exclude(mac_address='').values('mac_address').annotate(
    count=Count('id')
).order_by('-count')[:10]

top_mac_addresses = [
    {'mac': item['mac_address'], 'count': item['count']}
    for item in top_mac_data
]
```

### 4. 重啟服務

```bash
# 重啟 Django 容器以應用更改
docker compose restart django

# 等待服務啟動
sleep 5
```

### 5. 驗證修復

```bash
# 再次測試 API
curl -s http://localhost/api/ipxe-analytics/overview/?server_id=4 | python3 -m json.tool
```

**結果**（修復後）：
```json
{
  "summary": {
    "total_servers": 1,
    "total_logs": 2422,
    "mac_logs": 1262,
    "boot_logs": 1160,
    "mac_set_operations": 123,
    "mac_get_operations": 1139,
    "time_range_days": 7
  },
  "server_stats": [
    {
      "server_id": 4,
      "server_name": "10.250.120.2",
      "server_ip": "10.250.120.2",
      "total_logs": 2422,
      "mac_logs": 1262,
      "boot_logs": 1160,
      "last_sync": "2025-11-07T02:20:04.864345+00:00"
    }
  ],
  "top_mac_addresses": [
    {
      "mac": "a0:ad:9f:1a:40:f3",
      "count": 320
    },
    {
      "mac": "60:cf:84:64:9c:98",
      "count": 251
    },
    ...
  ]
}
```

✅ **API 修復成功！所有統計數據正確顯示**

---

## 📊 修復結果對比

| 項目 | 修復前 | 修復後 | 狀態 |
|------|--------|--------|------|
| 總日誌數 | 0 | 2422 | ✅ |
| MAC 日誌 | 0 | 1262 | ✅ |
| BOOT 日誌 | 0 | 1160 | ✅ |
| MAC SET 操作 | 0 | 123 | ✅ |
| MAC GET 操作 | 0 | 1139 | ✅ |
| 伺服器統計 | 空陣列 | 包含伺服器資訊 | ✅ |
| Top MAC 地址 | 空陣列 | Top 10 活躍 MAC | ✅ |
| 最後同步時間 | None | 2025-11-07 02:20:04 | ✅ |

---

## 🎯 解決方案總結

### 問題根源
API 設計錯誤導致查詢了錯誤的資料表和欄位：
- 使用 `DHCPLog` 表而非 `IPXELog` 表
- 使用 `client_type` 欄位而非 `log_type` 欄位
- 使用 `message__icontains` 而非直接查詢結構化欄位
- 使用 `DHCPServer` 模型而非 `IPXEServer` 模型

### 修復方法
系統性地將所有查詢從 DHCP 相關模型和欄位更換為 iPXE 相關模型和欄位：

1. **資料表**：`DHCPLog` → `IPXELog`
2. **日誌類型**：`client_type__in=['PXE', 'iPXE', 'WinPE']` → `log_type in ['MAC', 'BOOT']`
3. **統計方式**：`message__icontains='MAC'` → `log_type='MAC'`
4. **操作統計**：`message__icontains='SET'` → `action='SET'`
5. **伺服器模型**：`DHCPServer` → `IPXEServer`
6. **MAC 地址**：無法統計 → `mac_address` 欄位統計

### 技術要點
- ✅ 使用正確的資料模型 (`IPXELog`, `IPXEServer`)
- ✅ 使用結構化欄位而非訊息內容分析
- ✅ 正確計算 BOOT 日誌（獨立統計，而非用全部日誌數）
- ✅ 添加最後同步時間顯示
- ✅ 實現 Top MAC 地址統計

---

## 📝 經驗教訓

### 1. 分層驗證的重要性
- ✅ **資料層**：先確認資料庫中有正確資料（2422 筆）
- ✅ **API 層**：測試 API 端點返回值（發現全為 0）
- ✅ **前端層**：確認問題在 API 而非前端

### 2. API 設計原則
- ❌ **反模式**：從訊息內容 (`message__icontains`) 分析結構化資料
- ✅ **最佳實踐**：使用專用欄位 (`log_type`, `action`) 存儲結構化資訊
- ✅ **正確做法**：iPXE 日誌有獨立的 `IPXELog` 表，應直接查詢而非從 `DHCPLog` 過濾

### 3. 代碼一致性
- 同一檔案中 `ipxe_analytics_statistics` API 正確使用 `IPXELog`
- 但 `ipxe_analytics_overview` API 錯誤使用 `DHCPLog`
- 應確保同類功能使用相同的資料來源

### 4. 錯誤檢測方法
- 後端正常（Celery 成功同步）不代表前端能看到資料
- 必須測試整個資料流：資料庫 → API → 前端
- 使用 `curl` 直接測試 API 端點可快速定位問題

---

## 🔧 相關檔案

### 修改的檔案
- `backend/api/views/ipxe_analytics.py` - iPXE 分析 API 視圖

### 相關檔案
- `backend/api/models.py` - IPXELog, IPXEServer 模型定義
- `backend/api/tasks.py` - Celery 同步任務
- `backend/api/signals.py` - 自動同步信號
- `docs/features/auto-ipxe-sync/` - iPXE 自動同步文檔

### 測試腳本
- `test_auto_ipxe_sync.sh` - iPXE 自動同步測試腳本

---

## ✅ 驗證清單

- [x] 資料庫中有正確的 iPXE 日誌記錄
- [x] API 返回正確的統計數據
- [x] MAC 日誌和 BOOT 日誌分別統計
- [x] MAC SET/GET 操作正確統計
- [x] 每日趨勢統計正確
- [x] 每小時統計正確
- [x] 伺服器統計包含正確資訊
- [x] Top MAC 地址統計正常
- [x] 最後同步時間正確顯示
- [ ] 前端頁面正確顯示數據（待用戶確認）

---

## 📞 下一步行動

1. **用戶驗證**：請用戶刷新前端頁面，確認是否能看到 iPXE 統計數據
2. **監控**：觀察 Celery 定時任務是否持續正常運行
3. **文檔更新**：將此次修復經驗添加到故障排查文檔

---

**修復完成時間**：2025-11-07  
**修復人員**：GitHub Copilot  
**驗證狀態**：API 修復完成，等待前端確認  
**相關文檔**：[iPXE 自動同步功能](../features/auto-ipxe-sync/README.md)
