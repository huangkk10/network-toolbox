# Django 時區處理最佳實踐

本文件說明 Network Toolbox 專案中處理時區的標準做法。

---

## 🎯 核心原則

### 1. 永遠使用 `USE_TZ = True`

```python
# backend/network_toolbox/settings.py
USE_TZ = True
TIME_ZONE = 'Asia/Taipei'
```

**原因**：
- ✅ Django 官方強烈推薦
- ✅ 資料庫統一存儲 UTC
- ✅ 自動處理夏令時
- ✅ 支援國際化

---

## 📝 開發規範

### 情境 1：解析外部時間戳（無時區資訊）

**問題**：Windows DHCP 日誌時間是 Taipei 本地時間，但沒有時區標記。

**錯誤做法** ❌：
```python
from datetime import datetime

# 這會產生 naive datetime（無時區資訊）
dt = datetime.strptime('11/10/25 04:25:34', '%m/%d/%y %H:%M:%S')
# Django 會假設這是 UTC，導致錯誤！
```

**正確做法** ✅：
```python
from datetime import datetime
import pytz

# 1. 先解析為 naive datetime
dt_naive = datetime.strptime('11/10/25 04:25:34', '%m/%d/%y %H:%M:%S')

# 2. 使用 pytz.localize() 明確指定時區
taipei_tz = pytz.timezone('Asia/Taipei')
dt_aware = taipei_tz.localize(dt_naive)

# 3. 轉換為 ISO 8601 格式（帶時區）
timestamp_str = dt_aware.isoformat()  # "2025-11-10T04:25:34+08:00"
```

---

### 情境 2：解析 ISO 8601 格式（帶時區）

**正確做法** ✅：
```python
from dateutil import parser as date_parser
import pytz

# 解析帶時區的字串
timestamp_str = "2025-11-10T04:25:34+08:00"
dt = date_parser.isoparse(timestamp_str)

# 轉換為 UTC 存儲
if dt.tzinfo is not None:
    dt_utc = dt.astimezone(pytz.UTC)

# 存入資料庫
model.timestamp = dt_utc
model.save()
```

---

### 情境 3：從資料庫讀取時間並顯示

**方法 A：在 View/Service 中轉換**：
```python
from django.utils import timezone

# 從資料庫讀取（UTC）
log = DHCPLog.objects.first()

# 轉換為當前時區（settings.TIME_ZONE）
local_time = timezone.localtime(log.timestamp)

# 格式化輸出
time_str = local_time.strftime('%Y-%m-%d %H:%M:%S')
```

**方法 B：在 Serializer 中轉換**：
```python
from rest_framework import serializers
from django.utils import timezone

class MySerializer(serializers.ModelSerializer):
    timestamp = serializers.SerializerMethodField()
    
    def get_timestamp(self, obj):
        """將 UTC 轉換為當前時區"""
        if obj.timestamp:
            local_time = timezone.localtime(obj.timestamp)
            return local_time.strftime('%Y-%m-%d %H:%M:%S')
        return None
```

---

### 情境 4：比較時間

**正確做法** ✅：
```python
from django.utils import timezone
from datetime import timedelta

# 獲取當前時間（timezone-aware）
now = timezone.now()

# 計算時間差
one_hour_ago = now - timedelta(hours=1)

# 查詢資料庫
recent_logs = DHCPLog.objects.filter(timestamp__gte=one_hour_ago)
```

**錯誤做法** ❌：
```python
from datetime import datetime

# 這會產生 naive datetime，與資料庫的 timezone-aware 比較會出錯
now = datetime.now()  # ❌ 錯誤！
```

---

## 🔧 常用工具函數

### 1. 取得當前時間（Taipei）

```python
from django.utils import timezone

# 取得當前 UTC 時間
now_utc = timezone.now()

# 轉換為 Taipei 時間
now_taipei = timezone.localtime(now_utc)
```

### 2. 解析使用者輸入的時間

```python
from django.utils import timezone
from datetime import datetime

def parse_user_datetime(date_str):
    """
    解析使用者輸入的日期時間字串（假設為 Taipei 時區）
    
    Args:
        date_str: "2025-11-10 04:25:34"
    
    Returns:
        timezone-aware datetime (UTC)
    """
    # 解析為 naive datetime
    dt_naive = datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
    
    # 假設為當前時區（Taipei）
    dt_aware = timezone.make_aware(dt_naive)
    
    return dt_aware
```

### 3. 格式化時間輸出

```python
from django.utils import timezone

def format_datetime(dt, format_str='%Y-%m-%d %H:%M:%S'):
    """
    格式化 datetime 為字串（使用當前時區）
    
    Args:
        dt: timezone-aware datetime
        format_str: strftime 格式字串
    
    Returns:
        格式化後的字串
    """
    if not dt:
        return ''
    
    # 轉換為當前時區
    local_dt = timezone.localtime(dt)
    
    return local_dt.strftime(format_str)
```

---

## 📚 DRF 設定

### REST Framework 時區配置

```python
# backend/network_toolbox/settings.py

REST_FRAMEWORK = {
    # 時區設定
    'DATETIME_FORMAT': '%Y-%m-%d %H:%M:%S',     # 輸出格式
    'DATETIME_INPUT_FORMATS': ['iso-8601'],     # 接受 ISO 8601 輸入
    # ... 其他設定
}
```

### Serializer 時區處理

**方法 1：使用 SerializerMethodField**（推薦）：
```python
class MySerializer(serializers.ModelSerializer):
    timestamp = serializers.SerializerMethodField()
    
    def get_timestamp(self, obj):
        from django.utils import timezone
        if obj.timestamp:
            local_time = timezone.localtime(obj.timestamp)
            return local_time.strftime('%Y-%m-%d %H:%M:%S')
        return None
```

**方法 2：自訂 DateTimeField**：
```python
class LocalizedDateTimeField(serializers.DateTimeField):
    """自訂 DateTimeField，自動轉換為當前時區"""
    
    def to_representation(self, value):
        from django.utils import timezone
        if value:
            value = timezone.localtime(value)
        return super().to_representation(value)

class MySerializer(serializers.ModelSerializer):
    timestamp = LocalizedDateTimeField(format='%Y-%m-%d %H:%M:%S')
```

---

## ⚠️ 常見錯誤

### 錯誤 1：使用 naive datetime

```python
# ❌ 錯誤
from datetime import datetime
now = datetime.now()  # naive datetime

# ✅ 正確
from django.utils import timezone
now = timezone.now()  # timezone-aware
```

### 錯誤 2：直接使用 replace(tzinfo=...)

```python
# ❌ 錯誤（可能導致夏令時問題）
import pytz
dt = datetime.now()
dt_aware = dt.replace(tzinfo=pytz.timezone('Asia/Taipei'))

# ✅ 正確
import pytz
dt = datetime.now()
taipei_tz = pytz.timezone('Asia/Taipei')
dt_aware = taipei_tz.localize(dt)
```

### 錯誤 3：混用不同時區物件

```python
# ❌ 錯誤
from dateutil import parser
dt = parser.isoparse("2025-11-10T04:25:34+08:00")
# dt.tzinfo 是 tzoffset，不是 pytz.timezone

# ✅ 正確（統一轉換為 pytz）
import pytz
dt_utc = dt.astimezone(pytz.UTC)
```

---

## 🧪 測試範例

### 測試時區轉換

```python
from django.test import TestCase
from django.utils import timezone
from datetime import datetime
import pytz

class TimezoneTest(TestCase):
    def test_datetime_conversion(self):
        """測試時區轉換"""
        # 創建 Taipei 時間
        taipei_tz = pytz.timezone('Asia/Taipei')
        dt_taipei = taipei_tz.localize(datetime(2025, 11, 10, 4, 25, 34))
        
        # 轉換為 UTC
        dt_utc = dt_taipei.astimezone(pytz.UTC)
        
        # 驗證（Taipei 04:25 = UTC 20:25 前一天）
        self.assertEqual(dt_utc.hour, 20)
        self.assertEqual(dt_utc.day, 9)
        
    def test_timezone_localtime(self):
        """測試 Django timezone.localtime"""
        # 創建 UTC 時間
        dt_utc = timezone.now()
        
        # 轉換為當前時區
        dt_local = timezone.localtime(dt_utc)
        
        # 驗證時區
        self.assertEqual(dt_local.tzinfo.zone, 'Asia/Taipei')
```

---

## 📖 參考資料

- [Django Time Zones](https://docs.djangoproject.com/en/4.2/topics/i18n/timezones/)
- [pytz Documentation](https://pypi.org/project/pytz/)
- [python-dateutil](https://dateutil.readthedocs.io/)
- [DRF DateTime Fields](https://www.django-rest-framework.org/api-guide/fields/#datetimefield)

---

## 🎯 檢查清單

在新增或修改時間相關代碼時，請確認：

- [ ] 所有 datetime 物件都是 **timezone-aware**
- [ ] 資料庫存儲使用 **UTC** 時間
- [ ] 顯示時轉換為 **當前時區**（`timezone.localtime()`）
- [ ] 使用 `timezone.now()` 而非 `datetime.now()`
- [ ] 使用 `pytz.localize()` 而非 `replace(tzinfo=...)`
- [ ] API 返回的時間格式一致
- [ ] 單元測試涵蓋時區轉換

---

**最後更新**：2025-11-10  
**維護者**：Network Toolbox Team
