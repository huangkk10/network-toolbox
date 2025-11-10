# DHCP 日誌時區修復記錄

**問題日期**：2025-11-10  
**修復狀態**：✅ 已完成  
**影響範圍**：DHCP Server 分析 → 日誌查看

---

## 🐛 問題描述

### 症狀
Web 介面顯示的 DHCP 日誌時間與 Raw Log 的時間**相差 8 小時**：

- **Web 顯示**：`2025-11-09 20:25:34`
- **Raw Log**：`31,11/10/25,04:25:34,...`（Taipei 時間）
- **時差**：-8 小時（顯示為 UTC 時間）

### 根本原因

1. **Windows DHCP 日誌格式**：
   - 日誌檔案已經是 **Taipei 本地時間**（UTC+8）
   - 格式：`MM/DD/YY,HH:MM:SS`（無時區資訊）

2. **Parser 問題**：
   - 原本的 `WindowsDHCPLogParser` 解析後返回 **naive datetime**（無時區資訊）
   - Django 假設 naive datetime 是 **UTC**，導致錯誤

3. **序列化問題**：
   - DRF 的 `DateTimeField` 預設輸出 **UTC 時間**
   - `get_db_logs()` 方法沒有進行時區轉換

---

## 🔧 修復方案

### 架構原則

**保持 `USE_TZ = True`**（Django 最佳實踐）：
- ✅ 資料庫統一存儲 **UTC** 時間
- ✅ 顯示時自動轉換為 **當前時區**（`TIME_ZONE = 'Asia/Taipei'`）
- ✅ 支援國際化，未來易於擴展

### 修改檔案清單

#### 1. `library/utils/log_parser.py`

**修改內容**：
```python
# 添加 pytz 支援
import pytz

class WindowsDHCPLogParser:
    def parse_line(self, line):
        # ...解析 CSV...
        
        # ✅ 將 naive datetime 轉換為 timezone-aware
        taipei_tz = pytz.timezone('Asia/Taipei')
        dt = taipei_tz.localize(dt_naive)  # 明確指定為 Taipei 時區
        
        # 返回 ISO 8601 格式（帶時區）
        timestamp_str = dt.isoformat()  # "2025-11-10T04:25:34+08:00"
```

**關鍵點**：
- 使用 `pytz.timezone('Asia/Taipei').localize()` 而非 `replace(tzinfo=...)`
- 返回 ISO 8601 格式，包含時區偏移（`+08:00`）

---

#### 2. `backend/api/services.py`

**A. `sync_logs_to_db()` 方法**：

```python
from dateutil import parser as date_parser
import pytz

# ✅ 解析 ISO 8601 格式（帶時區）
timestamp = date_parser.isoparse(timestamp_str)

# ✅ 轉換為 UTC 存儲
if timestamp.tzinfo is not None:
    utc_tz = pytz.UTC
    timestamp = timestamp.astimezone(utc_tz)

# 存入資料庫
DHCPLog.objects.create(
    timestamp=timestamp,  # UTC datetime
    # ...
)
```

**B. `get_db_logs()` 方法**：

```python
from django.utils import timezone

for log in logs_qs:
    # ✅ 將 UTC 轉換為當前時區（Asia/Taipei）
    local_timestamp = timezone.localtime(log.timestamp)
    
    logs.append({
        'timestamp': local_timestamp.strftime('%Y-%m-%d %H:%M:%S'),
        # ...
    })
```

---

#### 3. `backend/api/serializers.py`

```python
from django.utils import timezone as django_timezone

class DHCPLogSerializer(serializers.ModelSerializer):
    # ✅ 自訂序列化方法
    timestamp = serializers.SerializerMethodField()
    
    def get_timestamp(self, obj):
        """將 UTC 時間轉換為當前時區（Asia/Taipei）"""
        if obj.timestamp:
            local_time = django_timezone.localtime(obj.timestamp)
            return local_time.strftime('%Y-%m-%d %H:%M:%S')
        return None
```

---

#### 4. `backend/network_toolbox/settings.py`

```python
REST_FRAMEWORK = {
    # ...
    'DATETIME_FORMAT': '%Y-%m-%d %H:%M:%S',
    'DATETIME_INPUT_FORMATS': ['iso-8601'],
}
```

---

## 🔄 資料流程

### 修復後的完整流程

```
┌─────────────────────────────────────────────────┐
│ Windows DHCP Server                             │
│ Log: "31,11/10/25,04:25:34,..."                │
│ 時區：Taipei (已是本地時間)                      │
└────────────────┬────────────────────────────────┘
                 │
                 ↓
┌─────────────────────────────────────────────────┐
│ WindowsDHCPLogParser.parse_line()               │
│ ✅ 使用 pytz.timezone('Asia/Taipei').localize() │
│ 輸出："2025-11-10T04:25:34+08:00" (ISO 8601)    │
└────────────────┬────────────────────────────────┘
                 │
                 ↓
┌─────────────────────────────────────────────────┐
│ WindowsDHCPService.sync_logs_to_db()            │
│ ✅ date_parser.isoparse() 解析帶時區的字串       │
│ ✅ astimezone(pytz.UTC) 轉換為 UTC               │
│ 存儲：2025-11-09 20:25:34+00:00 (UTC)           │
└────────────────┬────────────────────────────────┘
                 │
                 ↓
┌─────────────────────────────────────────────────┐
│ PostgreSQL Database                             │
│ timestamp (timestamptz)                         │
│ 值：2025-11-09 20:25:34+00:00 (UTC)             │
└────────────────┬────────────────────────────────┘
                 │
                 ↓
┌─────────────────────────────────────────────────┐
│ get_db_logs() / DHCPLogSerializer               │
│ ✅ timezone.localtime() 轉換為 Taipei            │
│ 輸出："2025-11-10 04:25:34"                     │
└────────────────┬────────────────────────────────┘
                 │
                 ↓
┌─────────────────────────────────────────────────┐
│ API Response (JSON)                             │
│ "timestamp": "2025-11-10 04:25:34"              │
└────────────────┬────────────────────────────────┘
                 │
                 ↓
┌─────────────────────────────────────────────────┐
│ React Frontend                                  │
│ 顯示：2025-11-10 04:25:34                       │
│ ✅ 與 Raw Log 時間一致！                         │
└─────────────────────────────────────────────────┘
```

---

## 📦 部署步驟

### 1. 安裝依賴套件

```bash
docker exec nt-django pip install pytz python-dateutil
```

### 2. 重啟服務

```bash
docker compose restart django
```

### 3. 清理舊資料（可選）

```bash
# 清除舊的日誌（時區錯誤的資料）
docker exec nt-django python manage.py shell -c "
from api.models import DHCPLog
DHCPLog.objects.filter(server_id=<server_id>).delete()
"
```

### 4. 重新同步日誌

在 Web 介面：
- 進入「DHCP Server 分析」→「日誌查看」
- 點擊「同步日誌」按鈕
- 等待同步完成

---

## ✅ 驗證結果

### 測試方法

**1. 檢查 API 返回**：
```bash
curl -s "http://localhost/api/dhcp-analytics/logs/?server=6&limit=1" | python3 -m json.tool
```

**預期輸出**：
```json
{
    "logs": [
        {
            "timestamp": "2025-11-10 04:25:34",
            "raw": "31,11/10/25,04:25:34,DNS Update Failed,...",
            ...
        }
    ]
}
```

**2. 檢查 Web 顯示**：
- Web 時間：`2025-11-10 04:25:34`
- Raw Log：`31,11/10/25,04:25:34,...`
- ✅ **完全一致！**

---

## 📚 技術要點

### 為什麼使用 `USE_TZ = True`

| 項目 | USE_TZ = True ✅ | USE_TZ = False ❌ |
|------|------------------|-------------------|
| **資料庫存儲** | UTC（統一標準） | 混亂（無時區資訊） |
| **國際化支援** | 簡單（改設定即可） | 困難（需改資料） |
| **Django 建議** | **強烈推薦** | 不推薦 |
| **夏令時問題** | 無 | 可能有問題 |
| **時區轉換** | 自動處理 | 手動處理 |
| **資料遷移** | 容易 | 困難 |

### pytz vs dateutil

- **pytz**：用於創建 timezone-aware datetime
- **dateutil**：用於解析 ISO 8601 格式字串
- 兩者配合使用，確保時區資訊正確

### Django 時區處理最佳實踐

1. **始終使用 timezone-aware datetime**
2. **資料庫統一存儲 UTC**
3. **顯示時轉換為當前時區**
4. **使用 `timezone.localtime()` 而非手動計算**

---

## 🔍 故障排查

### 如果時間還是不對

1. **檢查 Parser 輸出**：
```bash
docker exec nt-django python -c "
from library.utils.log_parser import WindowsDHCPLogParser
parser = WindowsDHCPLogParser()
result = parser.parse_line('31,11/10/25,04:25:34,DNS Update Failed,...')
print('Timestamp:', result['timestamp'])
print('Type:', type(result['timestamp']))
"
```

2. **檢查資料庫時區**：
```bash
docker exec nt-django python manage.py shell -c "
from api.models import DHCPLog
log = DHCPLog.objects.first()
print('DB timestamp:', log.timestamp)
print('Timezone:', log.timestamp.tzinfo)
"
```

3. **檢查 API 輸出**：
```bash
curl -s "http://localhost/api/dhcp-analytics/logs/?server=6&limit=1"
```

---

## 📝 相關文件

- [Django Timezone Documentation](https://docs.djangoproject.com/en/4.2/topics/i18n/timezones/)
- [pytz Documentation](https://pypi.org/project/pytz/)
- [python-dateutil Documentation](https://dateutil.readthedocs.io/)
- [DRF DateTimeField](https://www.django-rest-framework.org/api-guide/fields/#datetimefield)

---

## 🎯 結論

透過正確處理時區資訊，確保：
1. ✅ 資料庫統一使用 UTC 存儲
2. ✅ API 返回當前時區時間（Asia/Taipei）
3. ✅ Web 顯示與 Raw Log 完全一致
4. ✅ 符合 Django 最佳實踐
5. ✅ 支援未來國際化需求

**修復完成日期**：2025-11-10  
**修復確認者**：User  
**狀態**：✅ 已驗證通過
