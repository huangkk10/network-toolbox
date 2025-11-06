# 方案 B 實施計畫：改為 Taipei 時區

**警告：此方案不建議實施，僅供參考**

---

## 📋 目錄

1. [總覽](#總覽)
2. [Jenkins 修改](#jenkins-修改)
3. [Django 後端修改](#django-後端修改)
4. [資料庫修改](#資料庫修改)
5. [前端修改](#前端修改)
6. [測試項目](#測試項目)
7. [部署步驟](#部署步驟)
8. [回滾計畫](#回滾計畫)
9. [風險評估](#風險評估)

---

## 總覽

### 修改範圍統計

| 類別 | 檔案數量 | 代碼行數 | 預估工時 |
|------|----------|----------|----------|
| Jenkins 配置 | 1 | 5 行 | 2 小時 |
| Django 設定 | 1 | 3 行 | 0.5 小時 |
| Django Models | 3 | 50 行 | 4 小時 |
| Django Tasks | 5 | 200 行 | 8 小時 |
| Django Views | 10 | 150 行 | 6 小時 |
| 資料庫遷移 | 1 | 100 行 | 4 小時 |
| 測試腳本 | 5 | 300 行 | 8 小時 |
| 文檔更新 | 10 | - | 4 小時 |
| **總計** | **36** | **808+** | **36.5 小時** |

### 影響範圍

```
修改影響樹狀圖：

Jenkins Server (JVM 參數)
  └─ 需要重啟 Jenkins
      └─ 影響所有使用者
          └─ 需要停機時間：30-60 分鐘

Django Backend (USE_TZ=False)
  ├─ settings.py
  ├─ models.py (所有 DateTimeField)
  ├─ tasks.py (所有時間處理)
  ├─ views.py (API 響應)
  ├─ serializers.py (時間序列化)
  └─ utils (時間工具函數)

PostgreSQL Database
  ├─ 遷移腳本 (375 筆 Builds)
  ├─ 遷移腳本 (其他帶時間的記錄)
  └─ 備份 (必須！)

Frontend (React)
  ├─ 移除時區轉換邏輯
  └─ 調整顯示格式

測試系統
  ├─ 單元測試 (50+ 個)
  ├─ 整合測試 (20+ 個)
  └─ E2E 測試 (10+ 個)
```

---

## Jenkins 修改

### 1. Jenkins JVM 參數修改

**檔案位置**：Jenkins 伺服器（非本專案內）

**修改內容**：

#### 方法 A：修改 systemd service（Linux）

**檔案**：`/etc/systemd/system/jenkins.service` 或 `/usr/lib/systemd/system/jenkins.service`

```bash
# 找到 Jenkins service 檔案
sudo systemctl status jenkins | grep "Loaded:"

# 編輯 service 檔案
sudo vim /etc/systemd/system/jenkins.service
```

**修改**：
```ini
[Service]
# 在 Environment 或 ExecStart 中添加
Environment="JAVA_OPTS=-Duser.timezone=Asia/Taipei"

# 或在 ExecStart 行添加
ExecStart=/usr/bin/java -Duser.timezone=Asia/Taipei -jar /usr/share/jenkins/jenkins.war
```

**重新載入並重啟**：
```bash
sudo systemctl daemon-reload
sudo systemctl restart jenkins

# 等待 Jenkins 啟動（約 2-5 分鐘）
sudo systemctl status jenkins
```

#### 方法 B：修改 Jenkins 配置檔（Docker）

**檔案**：`docker-compose.yml` 或 Jenkins Dockerfile

```yaml
# docker-compose.yml
services:
  jenkins:
    image: jenkins/jenkins:lts
    environment:
      - JAVA_OPTS=-Duser.timezone=Asia/Taipei
      - TZ=Asia/Taipei
```

#### 驗證修改

```bash
# 方法 1：通過 Jenkins Script Console
# 訪問：http://jenkins-server/script
System.getProperty("user.timezone")
// 應該返回：Asia/Taipei

# 方法 2：檢查 Jenkins 系統日誌
# 訪問：http://jenkins-server/systemInfo
# 查找 user.timezone
```

### 2. Jenkins 修改影響

- ✅ **優點**：Jenkins UI 顯示台北時間
- ❌ **缺點**：
  - 需要重啟 Jenkins（影響所有使用者）
  - 違反業界慣例（CI/CD 系統通常使用 UTC）
  - 可能影響其他依賴 UTC 的 Jenkins Job
  - Jenkins API 返回的 timestamp 仍是 Unix timestamp（不受時區影響）

**停機時間**：30-60 分鐘

**影響範圍**：所有使用 Jenkins 的用戶和系統

---

## Django 後端修改

### 1. Django Settings 修改

**檔案**：`backend/network_toolbox/settings.py`

```python
# ============================================================
# 修改前（方案 A - 目前配置）
# ============================================================
TIME_ZONE = config('TZ', default='Asia/Taipei')
USE_TZ = True  # 啟用時區支援，資料庫儲存 UTC

# ============================================================
# 修改後（方案 B）
# ============================================================
TIME_ZONE = config('TZ', default='Asia/Taipei')
USE_TZ = False  # ⚠️ 停用時區支援，資料庫儲存 naive datetime（Taipei）
```

**影響**：
- Django 不再自動轉換時區
- 所有 `datetime.now()` 返回 naive datetime
- 資料庫儲存不含時區資訊的 datetime

### 2. Models 修改

需要檢查所有使用 `DateTimeField` 的 Model：

**檔案**：`backend/api/models.py`

```python
# ============================================================
# 需要檢查的 Models
# ============================================================

class JenkinsBuild(models.Model):
    # 這些欄位不需要修改定義，但需要確保輸入的是 naive datetime
    build_timestamp = models.DateTimeField()          # ⚠️ 檢查
    workspace_stored_at = models.DateTimeField(null=True, blank=True)  # ⚠️ 檢查
    created_at = models.DateTimeField(auto_now_add=True)  # ✅ auto_now_add 自動處理
    updated_at = models.DateTimeField(auto_now=True)      # ✅ auto_now 自動處理

class DHCPLease(models.Model):
    lease_start = models.DateTimeField()              # ⚠️ 檢查
    lease_end = models.DateTimeField()                # ⚠️ 檢查
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class IPXEBoot(models.Model):
    boot_time = models.DateTimeField()                # ⚠️ 檢查
    created_at = models.DateTimeField(auto_now_add=True)

# ... 其他含有 DateTimeField 的 Model
```

**修改數量**：約 15 個 Model，50+ 個 DateTimeField

### 3. Tasks 修改（Celery）

**檔案**：`backend/api/tasks.py`

#### 修改點 1：sync_jenkins_builds

```python
# ============================================================
# 修改前（方案 A）
# ============================================================
from django.utils import timezone
import pytz

@shared_task(bind=True)
def sync_jenkins_builds(self, max_age_days=30):
    # 使用 aware datetime
    cutoff_time = datetime.now(pytz.UTC) - timedelta(days=max_age_days)
    
    # Jenkins timestamp 轉換
    timestamp = build_data.get('timestamp', 0) / 1000
    build_timestamp = datetime.fromtimestamp(timestamp, tz=pytz.UTC)
    
    # 比較（aware vs aware）
    if build_timestamp < cutoff_time:
        continue

# ============================================================
# 修改後（方案 B）
# ============================================================
from datetime import datetime, timedelta

@shared_task(bind=True)
def sync_jenkins_builds(self, max_age_days=30):
    # 使用 naive datetime（Taipei 時間）
    cutoff_time = datetime.now() - timedelta(days=max_age_days)
    
    # Jenkins timestamp 轉換（⚠️ 需要手動加上 Taipei offset）
    timestamp = build_data.get('timestamp', 0) / 1000
    # Unix timestamp 是 UTC，需要轉換為 Taipei
    build_timestamp = datetime.fromtimestamp(timestamp) + timedelta(hours=8)
    
    # 比較（naive vs naive）
    if build_timestamp < cutoff_time:
        continue
    
    # ⚠️ 問題：夏令時間如何處理？
    # ⚠️ 問題：如果 Jenkins 在其他時區，如何處理？
```

#### 修改點 2：auto_store_workspaces

```python
# ============================================================
# 修改前（方案 A）
# ============================================================
@shared_task(bind=True)
def auto_store_workspaces(self):
    # 使用 timezone-aware datetime
    cutoff_time = timezone.now() - timedelta(days=3)
    builds = JenkinsBuild.objects.filter(
        build_timestamp__gte=cutoff_time,
        workspace_stored_at__isnull=True
    )

# ============================================================
# 修改後（方案 B）
# ============================================================
@shared_task(bind=True)
def auto_store_workspaces(self):
    # 使用 naive datetime
    cutoff_time = datetime.now() - timedelta(days=3)
    builds = JenkinsBuild.objects.filter(
        build_timestamp__gte=cutoff_time,
        workspace_stored_at__isnull=True
    )
    
    # 儲存時間
    build.workspace_stored_at = datetime.now()  # ⚠️ naive datetime
    build.save()
```

#### 修改點 3：所有定時任務

```python
# 需要修改的 Tasks（共 16 個）：
# 1. sync_jenkins_servers
# 2. sync_jenkins_jobs  
# 3. sync_jenkins_builds ⚠️ 重要
# 4. auto_store_workspaces ⚠️ 重要
# 5. check_workspace_storage
# 6. sync_dhcp_leases
# 7. check_dhcp_service
# 8. cleanup_old_logs
# 9. sync_ipxe_boots
# 10. check_nas_connection
# ... 等等
```

**修改數量**：約 5 個主要 Task 檔案，200+ 行代碼

### 4. Serializers 修改

**檔案**：`backend/api/serializers.py`

```python
# ============================================================
# 修改前（方案 A）
# ============================================================
class JenkinsBuildSerializer(serializers.ModelSerializer):
    class Meta:
        model = JenkinsBuild
        fields = '__all__'
    
    # Django 自動將 UTC 轉換為 TIME_ZONE (Taipei)
    # API 響應：2025-11-06T07:00:00+08:00

# ============================================================
# 修改後（方案 B）
# ============================================================
class JenkinsBuildSerializer(serializers.ModelSerializer):
    # 需要自訂欄位處理
    build_timestamp = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S')
    
    class Meta:
        model = JenkinsBuild
        fields = '__all__'
    
    # API 響應：2025-11-06 07:00:00 (無時區資訊)
    # ⚠️ 問題：前端無法判斷是哪個時區
```

**修改數量**：約 10 個 Serializer 檔案，50+ 行代碼

### 5. Views 修改

**檔案**：`backend/api/views.py` 及其他 view 檔案

```python
# ============================================================
# 修改前（方案 A）
# ============================================================
from django.utils import timezone

class BuildViewSet(viewsets.ModelViewSet):
    def get_queryset(self):
        # 使用 timezone-aware datetime
        start_date = timezone.now() - timedelta(days=7)
        return JenkinsBuild.objects.filter(
            build_timestamp__gte=start_date
        )

# ============================================================
# 修改後（方案 B）
# ============================================================
from datetime import datetime

class BuildViewSet(viewsets.ModelViewSet):
    def get_queryset(self):
        # 使用 naive datetime
        start_date = datetime.now() - timedelta(days=7)
        return JenkinsBuild.objects.filter(
            build_timestamp__gte=start_date
        )
```

**修改數量**：約 10 個 ViewSet 檔案，100+ 行代碼

### 6. Utils 工具函數修改

**檔案**：`backend/library/utils/` 下的所有時間處理函數

```python
# backend/library/utils/date_time.py

# ============================================================
# 需要修改的函數
# ============================================================

def format_datetime(dt):
    """格式化 datetime"""
    # 移除時區轉換邏輯
    pass

def parse_datetime(dt_string):
    """解析 datetime 字串"""
    # 移除時區處理邏輯
    pass

def get_date_range(start, end):
    """取得日期範圍"""
    # 移除時區轉換邏輯
    pass
```

**修改數量**：約 5 個工具檔案，50+ 行代碼

---

## 資料庫修改

### 1. 資料遷移腳本

**需要創建**：`backend/api/migrations/XXXX_convert_to_naive_datetime.py`

```python
# backend/api/migrations/XXXX_convert_to_naive_datetime.py

from django.db import migrations
import pytz
from datetime import datetime

def convert_utc_to_taipei_naive(apps, schema_editor):
    """
    將資料庫中所有 UTC aware datetime 轉換為 Taipei naive datetime
    
    步驟：
    1. 讀取 UTC aware datetime
    2. 轉換為 Taipei 時區
    3. 移除時區資訊（變成 naive）
    4. 更新資料庫
    """
    JenkinsBuild = apps.get_model('api', 'JenkinsBuild')
    DHCPLease = apps.get_model('api', 'DHCPLease')
    IPXEBoot = apps.get_model('api', 'IPXEBoot')
    # ... 其他 Model
    
    taipei_tz = pytz.timezone('Asia/Taipei')
    
    # 轉換 JenkinsBuild
    print("轉換 JenkinsBuild 記錄...")
    total = JenkinsBuild.objects.count()
    print(f"總共 {total} 筆記錄")
    
    for i, build in enumerate(JenkinsBuild.objects.all(), 1):
        if i % 100 == 0:
            print(f"進度：{i}/{total}")
        
        # build_timestamp
        if build.build_timestamp:
            # UTC aware → Taipei aware → Naive
            taipei_aware = build.build_timestamp.astimezone(taipei_tz)
            build.build_timestamp = taipei_aware.replace(tzinfo=None)
        
        # workspace_stored_at
        if build.workspace_stored_at:
            taipei_aware = build.workspace_stored_at.astimezone(taipei_tz)
            build.workspace_stored_at = taipei_aware.replace(tzinfo=None)
        
        # created_at, updated_at
        if build.created_at:
            taipei_aware = build.created_at.astimezone(taipei_tz)
            build.created_at = taipei_aware.replace(tzinfo=None)
        
        if build.updated_at:
            taipei_aware = build.updated_at.astimezone(taipei_tz)
            build.updated_at = taipei_aware.replace(tzinfo=None)
        
        build.save()
    
    print("✅ JenkinsBuild 轉換完成")
    
    # 轉換 DHCPLease
    print("\n轉換 DHCPLease 記錄...")
    total = DHCPLease.objects.count()
    for i, lease in enumerate(DHCPLease.objects.all(), 1):
        if i % 100 == 0:
            print(f"進度：{i}/{total}")
        
        if lease.lease_start:
            taipei_aware = lease.lease_start.astimezone(taipei_tz)
            lease.lease_start = taipei_aware.replace(tzinfo=None)
        
        if lease.lease_end:
            taipei_aware = lease.lease_end.astimezone(taipei_tz)
            lease.lease_end = taipei_aware.replace(tzinfo=None)
        
        # created_at, updated_at
        if lease.created_at:
            taipei_aware = lease.created_at.astimezone(taipei_tz)
            lease.created_at = taipei_aware.replace(tzinfo=None)
        
        if lease.updated_at:
            taipei_aware = lease.updated_at.astimezone(taipei_tz)
            lease.updated_at = taipei_aware.replace(tzinfo=None)
        
        lease.save()
    
    print("✅ DHCPLease 轉換完成")
    
    # ... 其他 Model

def reverse_taipei_naive_to_utc(apps, schema_editor):
    """
    回滾：將 Taipei naive datetime 轉換回 UTC aware datetime
    """
    # 類似邏輯，但反向操作
    pass

class Migration(migrations.Migration):
    dependencies = [
        ('api', 'PREVIOUS_MIGRATION'),  # 替換為實際的前一個 migration
    ]
    
    operations = [
        migrations.RunPython(
            convert_utc_to_taipei_naive,
            reverse_taipei_naive_to_utc
        ),
    ]
```

### 2. 執行遷移前的備份

```bash
# 1. 備份整個資料庫
pg_dump -U postgres -h localhost network_toolbox > backup_before_timezone_migration_$(date +%Y%m%d_%H%M%S).sql

# 2. 驗證備份
ls -lh backup_before_timezone_migration_*.sql

# 3. 測試還原（在測試環境）
createdb network_toolbox_test
psql -U postgres -h localhost network_toolbox_test < backup_before_timezone_migration_YYYYMMDD_HHMMSS.sql
```

### 3. 執行遷移

```bash
# 1. 先在開發環境測試
docker exec nt-django python manage.py migrate --plan

# 2. 確認無誤後執行
docker exec nt-django python manage.py migrate

# 3. 驗證資料
docker exec nt-django python manage.py shell
>>> from api.models import JenkinsBuild
>>> build = JenkinsBuild.objects.first()
>>> build.build_timestamp.tzinfo  # 應該是 None（naive）
```

**預估時間**：
- 備份：5-10 分鐘
- 遷移執行：15-30 分鐘（375 筆 Builds + 其他記錄）
- 驗證：10 分鐘

**風險**：
- ⚠️ 遷移過程中資料庫鎖定，無法寫入
- ⚠️ 遷移失敗可能導致資料損壞
- ⚠️ 遷移時間過長可能影響服務

---

## 前端修改

### 1. 移除時區轉換邏輯

**檔案**：`frontend/src/utils/dateUtils.js`（如果存在）

```javascript
// ============================================================
// 修改前（方案 A）
// ============================================================
import moment from 'moment-timezone';

export const formatDateTime = (dateString) => {
  // API 返回：2025-11-06T07:00:00+08:00
  // 自動處理時區
  return moment(dateString).format('YYYY-MM-DD HH:mm:ss');
};

export const formatDateTimeUTC = (dateString) => {
  // 轉換為 UTC 顯示
  return moment(dateString).utc().format('YYYY-MM-DD HH:mm:ss');
};

// ============================================================
// 修改後（方案 B）
// ============================================================
export const formatDateTime = (dateString) => {
  // API 返回：2025-11-06 07:00:00（無時區資訊）
  // 直接顯示，不需要轉換
  return dateString;
};

// 移除 UTC 轉換函數（不再需要）
```

### 2. 更新組件

**檔案**：`frontend/src/components/` 下的所有顯示時間的組件

```javascript
// 範例：frontend/src/components/BuildTable.js

// ============================================================
// 修改前（方案 A）
// ============================================================
const columns = [
  {
    title: 'Build Time',
    dataIndex: 'build_timestamp',
    key: 'build_timestamp',
    render: (text) => (
      <div>
        <div>{moment(text).format('YYYY-MM-DD HH:mm:ss')}</div>
        <div style={{ fontSize: '12px', color: '#888' }}>
          UTC: {moment(text).utc().format('YYYY-MM-DD HH:mm:ss')}
        </div>
      </div>
    ),
  },
];

// ============================================================
// 修改後（方案 B）
// ============================================================
const columns = [
  {
    title: 'Build Time',
    dataIndex: 'build_timestamp',
    key: 'build_timestamp',
    render: (text) => (
      <div>
        {text} {/* 直接顯示，無時區資訊 */}
      </div>
    ),
  },
];
```

**修改數量**：約 15 個組件檔案，100+ 行代碼

### 3. 移除時區相關套件（可選）

```bash
# 如果不再需要時區處理
npm uninstall moment-timezone
# 或
npm uninstall date-fns-tz
```

---

## 測試項目

### 1. 單元測試修改

需要更新所有涉及時間的單元測試：

```python
# tests/unit/backend/test_models.py

# ============================================================
# 修改前（方案 A）
# ============================================================
from django.utils import timezone

class JenkinsBuildModelTest(TestCase):
    def test_build_creation(self):
        build_time = timezone.now()
        build = JenkinsBuild.objects.create(
            build_timestamp=build_time
        )
        self.assertEqual(build.build_timestamp.tzinfo, pytz.UTC)

# ============================================================
# 修改後（方案 B）
# ============================================================
from datetime import datetime

class JenkinsBuildModelTest(TestCase):
    def test_build_creation(self):
        build_time = datetime.now()  # naive
        build = JenkinsBuild.objects.create(
            build_timestamp=build_time
        )
        self.assertIsNone(build.build_timestamp.tzinfo)  # naive
```

**修改數量**：約 50+ 個測試案例

### 2. 整合測試修改

```python
# tests/integration/api/test_jenkins_sync.py

# 需要更新所有時間比較測試
# 需要確保 naive datetime 的比較邏輯正確
```

**修改數量**：約 20+ 個測試案例

### 3. 新增測試案例

```python
# tests/integration/test_timezone_migration.py

class TimezoneMigrationTest(TestCase):
    """測試時區遷移的正確性"""
    
    def test_utc_to_taipei_conversion(self):
        """測試 UTC 轉 Taipei 是否正確（+8 小時）"""
        pass
    
    def test_naive_datetime_comparison(self):
        """測試 naive datetime 比較"""
        pass
    
    def test_cross_midnight_handling(self):
        """測試跨午夜處理"""
        pass
```

---

## 部署步驟

### 階段 1：準備工作（1-2 天）

```bash
# 1. 創建功能分支
git checkout -b feature/timezone-to-taipei

# 2. 備份生產資料庫
pg_dump -U postgres network_toolbox > prod_backup_$(date +%Y%m%d).sql

# 3. 設置測試環境
docker-compose -f docker-compose.test.yml up -d

# 4. 通知所有使用者（Jenkins + Network Toolbox）
```

### 階段 2：Jenkins 修改（停機時間）

```bash
# 1. 選擇低流量時段（例如：週末凌晨）
# 2. 通知所有使用者

# 3. 修改 Jenkins JVM 參數
sudo vim /etc/systemd/system/jenkins.service
# 添加：-Duser.timezone=Asia/Taipei

# 4. 重啟 Jenkins
sudo systemctl daemon-reload
sudo systemctl restart jenkins

# 5. 等待啟動（5-10 分鐘）
sudo systemctl status jenkins

# 6. 驗證時區設置
# 訪問：http://jenkins/script
# 執行：System.getProperty("user.timezone")
# 預期：Asia/Taipei

# 停機時間：30-60 分鐘
```

### 階段 3：Django 代碼部署

```bash
# 1. 修改所有代碼（見上述各節）
# 2. 執行所有測試
python manage.py test

# 3. 提交代碼
git add .
git commit -m "feat: Change timezone from UTC to Taipei"
git push origin feature/timezone-to-taipei

# 4. 創建 Pull Request
# 5. Code Review
# 6. 合併到 main
```

### 階段 4：資料庫遷移（停機時間）

```bash
# 1. 停止 Celery（避免新資料寫入）
docker-compose stop celery_worker celery_beat

# 2. 備份資料庫（最新）
docker exec nt-django python manage.py dumpdata > backup_before_migration.json

# 3. 執行遷移
docker exec nt-django python manage.py migrate

# 4. 驗證資料
docker exec nt-django python manage.py shell
# 檢查 tzinfo 是否為 None

# 5. 重啟所有服務
docker-compose restart

# 停機時間：30-60 分鐘
```

### 階段 5：驗證與監控（1-2 天）

```bash
# 1. 功能測試
# - 測試 Jenkins 同步
# - 測試 Workspace 儲存
# - 測試時間顯示

# 2. 監控日誌
tail -f logs/django.log
tail -f logs/django_error.log

# 3. 檢查 Celery 任務
docker exec nt-celery-worker celery -A network_toolbox inspect active

# 4. 使用者驗收測試
```

---

## 回滾計畫

### 緊急回滾步驟

```bash
# 1. 停止所有服務
docker-compose down

# 2. 還原資料庫
psql -U postgres network_toolbox < prod_backup_YYYYMMDD.sql

# 3. 回滾代碼
git revert COMMIT_HASH
git push origin main

# 4. 回滾 Jenkins
sudo vim /etc/systemd/system/jenkins.service
# 移除 -Duser.timezone=Asia/Taipei
sudo systemctl daemon-reload
sudo systemctl restart jenkins

# 5. 重啟服務
docker-compose up -d

# 回滾時間：30-45 分鐘
```

---

## 風險評估

### 高風險項目（🔴）

1. **Jenkins 重啟影響所有使用者**
   - 風險：30-60 分鐘停機時間
   - 影響：所有 CI/CD Pipeline 暫停
   - 緩解：選擇低流量時段，提前通知

2. **資料庫遷移失敗**
   - 風險：資料損壞或遺失
   - 影響：系統無法運作
   - 緩解：完整備份、測試環境演練

3. **Naive datetime 導致的 bug**
   - 風險：時間比較錯誤、夏令時問題
   - 影響：功能異常、資料錯誤
   - 緩解：完整測試、監控日誌

### 中風險項目（🟡）

4. **與其他系統整合問題**
   - 風險：如果其他系統使用 UTC，可能出現不一致
   - 影響：資料同步錯誤
   - 緩解：檢查所有整合點

5. **前端顯示混亂**
   - 風險：無時區資訊，使用者不知道是哪個時區
   - 影響：使用者體驗差
   - 緩解：清楚標示時區

### 低風險項目（🟢）

6. **效能影響**
   - 風險：遷移過程中效能下降
   - 影響：輕微延遲
   - 緩解：選擇低流量時段

---

## 總結

### 修改範圍總覽

| 類別 | 檔案數量 | 代碼行數 | 風險等級 |
|------|----------|----------|----------|
| Jenkins | 1 | 5 | 🔴 高 |
| Django Settings | 1 | 3 | 🔴 高 |
| Django Models | 3 | 50 | 🟡 中 |
| Django Tasks | 5 | 200 | 🔴 高 |
| Django Views | 10 | 150 | 🟡 中 |
| Django Serializers | 10 | 50 | 🟡 中 |
| Django Utils | 5 | 50 | 🟡 中 |
| 資料庫遷移 | 1 | 100 | 🔴 高 |
| 前端組件 | 15 | 100 | 🟢 低 |
| 測試案例 | 50+ | 300+ | 🟡 中 |
| 文檔 | 10+ | - | 🟢 低 |

### 成本估算

- **開發時間**：36.5 小時（約 5 個工作天）
- **測試時間**：16 小時（約 2 個工作天）
- **部署時間**：4 小時
- **停機時間**：1-2 小時（Jenkins + 資料庫遷移）
- **總成本**：約 7-10 個工作天

### 強烈建議

**❌ 不建議實施方案 B**

原因：
1. 成本高（7-10 天工作量）
2. 風險高（資料遷移、Jenkins 重啟）
3. 違反國際慣例
4. 難以維護
5. 無法國際化
6. 效益低（僅改善顯示一致性）

**✅ 建議保持方案 A（目前配置）**

原因：
1. 成本 0
2. 風險低
3. 符合國際標準
4. 易於維護
5. 支援國際化
6. 只需改善前端 UI 標示

---

**文檔版本**：1.0  
**創建日期**：2025-11-06  
**最後更新**：2025-11-06  
**維護者**：Network Toolbox Team
