# ⏰ Django 時區設置說明

## 📋 目前配置

### Django Settings (`backend/network_toolbox/settings.py`)

```python
TIME_ZONE = 'Asia/Taipei'  # 台北時區 (UTC+8)
USE_TZ = True              # 啟用時區支持
CELERY_TIMEZONE = TIME_ZONE
```

## 🔄 時區處理流程

### 1. Jenkins API → Django

```
Jenkins Server
  └─ 返回 Unix timestamp (毫秒)
      └─ 例如: 1762252949883
          └─ 這是 UTC 時間的 Unix 時間戳
              └─ 無論 Jenkins Server 設置什麼時區，timestamp 都是 UTC 基準
```

**代碼處理：**
```python
# backend/api/tasks.py (sync_jenkins_builds)
timestamp = build_data.get('timestamp', 0) / 1000  # 毫秒轉秒
build_timestamp = datetime.fromtimestamp(timestamp, tz=pytz.UTC)  # 轉換為 UTC aware datetime
```

### 2. 資料庫儲存

```
PostgreSQL 資料庫
  └─ 儲存格式: timestamp without time zone
      └─ 實際儲存: UTC 時間
          └─ 例如: 2025-11-05 07:00:12.946000
```

**Django ORM 行為：**
- 當 `USE_TZ = True` 時，Django 會：
  - 儲存時：自動轉換為 UTC
  - 讀取時：自動加上 UTC 時區資訊
  - 比較時：可以與任何 aware datetime 安全比較

### 3. API 返回 → 前端

```
Django REST Framework Serializer
  └─ 讀取資料庫 (UTC)
      └─ 自動轉換為 TIME_ZONE (Asia/Taipei)
          └─ 返回 ISO 8601 格式: 2025-11-05T15:00:12.946000+08:00
              └─ 前端顯示: 2025-11-05 15:00:12 (台北時間)
```

**API 返回範例：**
```json
{
  "build_timestamp": "2025-11-05T15:00:12.946000+08:00",
  "workspace_stored_at": "2025-11-05T16:27:48.457461+08:00"
}
```

## 🎯 時區轉換示例

### UTC → 台北時間

```python
from datetime import datetime
import pytz

# UTC 時間
utc_time = datetime(2025, 11, 5, 7, 0, 0, tzinfo=pytz.UTC)
print(f'UTC: {utc_time}')
# 輸出: UTC: 2025-11-05 07:00:00+00:00

# 轉換為台北時間
taipei_tz = pytz.timezone('Asia/Taipei')
taipei_time = utc_time.astimezone(taipei_tz)
print(f'台北: {taipei_time}')
# 輸出: 台北: 2025-11-05 15:00:00+08:00
```

### 資料庫查詢

```python
from datetime import datetime, timedelta
from django.utils import timezone
import pytz

# 方法 1：使用 Django timezone (推薦)
now = timezone.now()  # 自動返回 aware datetime (UTC)
three_days_ago = now - timedelta(days=3)

# 方法 2：手動創建 aware datetime
now = datetime.now(pytz.UTC)
three_days_ago = now - timedelta(days=3)

# 查詢（Django 會自動處理時區）
recent_builds = JenkinsBuild.objects.filter(
    build_timestamp__gte=three_days_ago
)
```

## ⚠️  常見陷阱與解決方案

### 陷阱 1：混用 Naive 和 Aware Datetime

**錯誤示例：**
```python
from datetime import datetime
import pytz

# ❌ 錯誤：比較 naive 和 aware datetime
naive_dt = datetime.now()  # naive (無時區)
aware_dt = datetime.now(pytz.UTC)  # aware (有時區)

if naive_dt < aware_dt:  # TypeError: can't compare offset-naive and offset-aware datetimes
    pass
```

**正確做法：**
```python
from django.utils import timezone

# ✅ 正確：統一使用 aware datetime
aware_dt1 = timezone.now()  # aware (UTC)
aware_dt2 = timezone.now()  # aware (UTC)

if aware_dt1 < aware_dt2:  # OK
    pass
```

### 陷阱 2：直接使用 datetime.now()

**錯誤示例：**
```python
from datetime import datetime

# ❌ 錯誤：返回 naive datetime
now = datetime.now()
```

**正確做法：**
```python
from django.utils import timezone
import pytz

# ✅ 正確方法 1：使用 Django timezone
now = timezone.now()

# ✅ 正確方法 2：手動指定時區
now = datetime.now(pytz.UTC)
```

### 陷阱 3：時區設置不一致

**檢查清單：**
- [ ] `settings.py` 中 `USE_TZ = True`
- [ ] 所有 datetime 計算使用 `timezone.now()`
- [ ] Celery 設置 `CELERY_TIMEZONE = TIME_ZONE`
- [ ] 前端正確解析 ISO 8601 格式

## 🔧 故障排查

### 問題：出現 "can't compare offset-naive and offset-aware datetimes"

**診斷步驟：**

1. **檢查 Django 設置**
```bash
docker exec nt-django python -c "
from django.conf import settings
print(f'USE_TZ: {settings.USE_TZ}')
print(f'TIME_ZONE: {settings.TIME_ZONE}')
"
```

預期輸出：
```
USE_TZ: True
TIME_ZONE: Asia/Taipei
```

2. **檢查資料庫中的時區**
```bash
docker exec nt-django python -c "
import django, os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'network_toolbox.settings')
django.setup()
from api.models import JenkinsBuild

build = JenkinsBuild.objects.first()
print(f'Timestamp: {build.build_timestamp}')
print(f'Timezone: {build.build_timestamp.tzinfo}')
print(f'Is aware: {build.build_timestamp.tzinfo is not None}')
"
```

預期輸出：
```
Timestamp: 2025-11-05 07:00:12.946000+00:00
Timezone: UTC
Is aware: True
```

3. **檢查 API 返回格式**
```bash
curl -s http://localhost/api/jenkins-builds/ | python3 -m json.tool | grep timestamp | head -3
```

預期輸出：
```json
"build_timestamp": "2025-11-05T15:00:12.946000+08:00",
"workspace_stored_at": "2025-11-05T16:27:48.457461+08:00",
```

### 問題：時間顯示不正確

**可能原因：**
1. 前端沒有正確解析時區
2. `TIME_ZONE` 設置錯誤
3. 資料庫儲存的是錯誤時區

**解決方案：**
```bash
# 重啟服務使設置生效
docker compose restart django celery_worker celery_beat
```

## 📊 時區對照表

| 時區 | UTC 偏移 | 範例時間 (UTC 10:00) |
|------|----------|---------------------|
| UTC | +00:00 | 10:00:00 |
| Asia/Taipei | +08:00 | 18:00:00 |
| America/New_York | -05:00 | 05:00:00 |
| Europe/London | +00:00 | 10:00:00 |

## ✅ 最佳實踐

1. **統一使用 Aware Datetime**
   - 永遠使用 `timezone.now()` 或 `datetime.now(pytz.UTC)`
   - 不要使用 `datetime.now()` (naive)

2. **資料庫統一儲存 UTC**
   - 設置 `USE_TZ = True`
   - Django 會自動處理轉換

3. **前端顯示本地時間**
   - API 返回帶時區的 ISO 8601 格式
   - 前端根據用戶瀏覽器時區顯示

4. **日誌記錄使用 UTC**
   - 便於跨時區除錯
   - 避免夏令時問題

5. **定期驗證時區設置**
   ```bash
   # 使用健康檢查腳本
   ./scripts/check_celery_health.sh
   
   # 檢查時區設置
   docker exec nt-django python manage.py shell -c "
   from django.conf import settings
   print(f'USE_TZ: {settings.USE_TZ}')
   print(f'TIME_ZONE: {settings.TIME_ZONE}')
   "
   ```

## 🔗 相關文件

- [Django Time Zones](https://docs.djangoproject.com/en/4.2/topics/i18n/timezones/)
- [Python pytz Documentation](https://pythonhosted.org/pytz/)
- [ISO 8601 Standard](https://en.wikipedia.org/wiki/ISO_8601)
- [Unix Timestamp](https://en.wikipedia.org/wiki/Unix_time)

---

**最後更新**：2025-11-06  
**維護者**：Network Toolbox Team
