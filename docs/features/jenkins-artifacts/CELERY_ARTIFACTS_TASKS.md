# Jenkins Artifacts Celery 自動化任務

## 📋 功能概述

通過 Celery 定時任務實現 Jenkins Build Artifacts 的**完全自動化存儲**，無需手動操作。系統會自動掃描新的 Build，並將符合條件的 Artifacts 下載、解壓並存儲到 NAS。

## 🎯 核心任務

### 1. `store_jenkins_artifacts_task` - 單個存儲任務

**用途**：存儲指定 Build 的 Artifacts

**調用方式**：
```python
from api.tasks import store_jenkins_artifacts_task

# 手動觸發
store_jenkins_artifacts_task.delay(build_id=1048)
```

**參數**：
- `build_id` (int): JenkinsBuild 的 ID

**功能**：
- ✅ 下載 Artifacts 到 NAS
- ✅ 自動解壓縮（7z, zip, tar.*）
- ✅ 解壓成功後刪除原始壓縮檔
- ✅ 更新數據庫記錄
- ✅ 失敗自動重試（最多 3 次）

**返回結果**：
```python
{
    'success': True,
    'build_id': 1048,
    'build_number': 148,
    'job_name': 'Test-KVM01',
    'artifacts_count': 1,
    'artifacts_size': 57551432,
    'extracted_files': 20,
    'storage_time': 1.85  # 秒
}
```

---

### 2. `auto_store_jenkins_artifacts_task` - 批量自動存儲

**用途**：定期掃描新的 Build 並自動存儲 Artifacts

**調用方式**：
```python
from api.tasks import auto_store_jenkins_artifacts_task

# 手動觸發
auto_store_jenkins_artifacts_task.delay()
```

**執行邏輯**：
1. 掃描最近 7 天內的所有 Build
2. 篩選條件：
   - ✅ 有 Artifacts（artifacts_count > 0）
   - ✅ 尚未存儲（is_artifacts_stored = False）
   - ✅ Build 狀態為 SUCCESS
3. 批量存儲（每次最多處理 50 個）
4. 統計存儲結果

**返回結果**：
```python
{
    'success': True,
    'total_scanned': 245,      # 掃描的 Build 總數
    'eligible_builds': 15,     # 符合條件的 Build 數
    'processed': 15,           # 實際處理的數量
    'succeeded': 14,           # 存儲成功
    'failed': 1,               # 存儲失敗
    'skipped': 0,              # 跳過的數量
    'total_artifacts': 28,     # 總 Artifacts 數
    'total_size': 1523456789,  # 總大小（bytes）
    'execution_time': 125.6    # 執行時間（秒）
}
```

---

## ⏰ 定時任務配置

### 默認配置

任務已在 `setup_celery_tasks.py` 中註冊，默認配置：

```python
{
    'task': 'api.tasks.auto_store_jenkins_artifacts_task',
    'schedule': crontab(minute='*/30'),  # 每 30 分鐘執行一次
    'options': {
        'expires': 1500  # 任務過期時間 25 分鐘
    }
}
```

### 修改執行頻率

編輯 `backend/setup_celery_tasks.py`：

```python
# 每小時執行一次
'schedule': crontab(minute=0),

# 每天凌晨 2 點執行
'schedule': crontab(hour=2, minute=0),

# 每 15 分鐘執行一次
'schedule': crontab(minute='*/15'),

# 每週一早上 8 點執行
'schedule': crontab(day_of_week=1, hour=8, minute=0),
```

修改後需要重啟 Celery Beat：
```bash
docker compose restart celery_beat
```

---

## 🚀 快速開始

### 1. 註冊定時任務

```bash
# 進入 Django 容器
docker exec -it nt-django bash

# 執行 setup 腳本
cd /app
python setup_celery_tasks.py
```

**輸出示例**：
```
✅ 定時任務設置完成：
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 已註冊的定時任務：
  1. auto_store_jenkins_artifacts - 每 30 分鐘執行
  2. auto_store_workspace - 每 30 分鐘執行
  3. check_jenkins_servers_health - 每 5 分鐘執行
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### 2. 重啟 Celery 服務

```bash
docker compose restart celery_worker celery_beat
```

### 3. 查看任務執行狀態

```bash
# 查看 Celery Worker 日誌
docker logs -f nt-celery_worker

# 查看 Celery Beat 日誌
docker logs -f nt-celery_beat
```

---

## 📊 使用場景

### 場景 1：手動存儲單個 Build

```python
# Django Shell
docker exec -it nt-django python manage.py shell

from api.tasks import store_jenkins_artifacts_task
from api.models import JenkinsBuild

# 查找需要存儲的 Build
build = JenkinsBuild.objects.get(id=1048)
print(f"Build: {build.job.name} #{build.build_number}")

# 觸發存儲任務
result = store_jenkins_artifacts_task.delay(build_id=build.id)
print(f"Task ID: {result.id}")
```

### 場景 2：批量存儲特定 Job 的 Artifacts

```python
from api.tasks import store_jenkins_artifacts_task
from api.models import JenkinsBuild

# 找出特定 Job 未存儲的 Build
job_name = "Test-KVM01"
builds = JenkinsBuild.objects.filter(
    job__name=job_name,
    is_artifacts_stored=False,
    artifacts_count__gt=0
)

# 批量觸發
for build in builds[:10]:  # 限制數量
    store_jenkins_artifacts_task.delay(build_id=build.id)
    print(f"✓ 已觸發: {build.job.name} #{build.build_number}")
```

### 場景 3：查看自動存儲統計

```python
from api.models import JenkinsBuild
from django.db.models import Count, Sum

# 已存儲 Artifacts 的統計
stored = JenkinsBuild.objects.filter(is_artifacts_stored=True).aggregate(
    count=Count('id'),
    total_size=Sum('artifacts_size'),
    total_artifacts=Sum('artifacts_count')
)

print(f"""
已存儲統計：
- Build 數量: {stored['count']}
- 總 Artifacts: {stored['total_artifacts']}
- 總大小: {stored['total_size'] / (1024**3):.2f} GB
""")
```

---

## 🔧 進階配置

### 自定義存儲條件

編輯 `backend/api/tasks.py` 中的 `auto_store_jenkins_artifacts_task`：

```python
# 只存儲特定 Job
eligible_builds = JenkinsBuild.objects.filter(
    job__name__in=['Test-KVM01', 'Production-Deploy'],  # 指定 Job
    is_artifacts_stored=False,
    artifacts_count__gt=0,
    result='SUCCESS',
    timestamp__gte=seven_days_ago
)

# 只存儲大於 10MB 的 Artifacts
eligible_builds = JenkinsBuild.objects.filter(
    is_artifacts_stored=False,
    artifacts_count__gt=0,
    result='SUCCESS',
    timestamp__gte=seven_days_ago
).exclude(
    artifacts_size__lt=10485760  # 10 MB
)

# 排除特定 Job
eligible_builds = JenkinsBuild.objects.filter(
    is_artifacts_stored=False,
    artifacts_count__gt=0,
    result='SUCCESS',
    timestamp__gte=seven_days_ago
).exclude(
    job__name__in=['Test-Debug', 'Temporary-Build']
)
```

### 調整批量處理數量

```python
# 預設每次處理 50 個，可以調整
MAX_BUILDS_PER_RUN = 100  # 改為 100

for build in eligible_builds[:MAX_BUILDS_PER_RUN]:
    # ...
```

### 添加通知功能

```python
def auto_store_jenkins_artifacts_task():
    # ... 存儲邏輯 ...
    
    # 發送通知（需要配置 Email/Slack）
    if summary['failed'] > 0:
        send_alert(
            title='Artifacts 存儲失敗警告',
            message=f"有 {summary['failed']} 個 Build 存儲失敗",
            details=failed_builds
        )
```

---

## 📈 監控和日誌

### Celery 任務監控

使用 Flower 監控 Celery 任務：

```bash
# 安裝 Flower（如果還沒有）
pip install flower

# 啟動 Flower
celery -A network_toolbox flower --port=5555
```

訪問：http://localhost:5555

### 日誌查看

```bash
# 實時查看 Worker 日誌
docker logs -f nt-celery_worker | grep "store_jenkins_artifacts"

# 查看最近 100 行
docker logs --tail 100 nt-celery_worker

# 查看 Beat 調度日誌
docker logs -f nt-celery_beat | grep "auto_store_jenkins_artifacts"
```

### 數據庫查詢統計

```sql
-- 查看存儲統計
SELECT 
    DATE(artifacts_stored_at) as date,
    COUNT(*) as builds_count,
    SUM(artifacts_count) as total_artifacts,
    SUM(artifacts_size) / 1024 / 1024 / 1024 as total_gb
FROM api_jenkinsbuild
WHERE is_artifacts_stored = true
GROUP BY DATE(artifacts_stored_at)
ORDER BY date DESC
LIMIT 30;

-- 查看待存儲的 Build
SELECT 
    job.name,
    build.build_number,
    build.artifacts_count,
    build.artifacts_size / 1024 / 1024 as size_mb
FROM api_jenkinsbuild as build
JOIN api_jenkinsjob as job ON build.job_id = job.id
WHERE build.is_artifacts_stored = false
  AND build.artifacts_count > 0
ORDER BY build.timestamp DESC
LIMIT 20;
```

---

## ⚠️ 注意事項

### 1. 磁盤空間管理

自動存儲會消耗大量磁盤空間，建議：

- 定期清理舊的 Artifacts
- 設置存儲保留期限
- 監控 NAS 可用空間

```bash
# 檢查 NAS 空間
df -h /mnt/mdt/Team/PQ1-3/tool/jenkins_test_storage
```

### 2. 網絡負載

批量下載會產生網絡負載，建議：

- 在非高峰時段執行（如：凌晨）
- 調整批量處理數量
- 設置任務優先級

### 3. Celery Worker 配置

確保有足夠的 Worker 處理任務：

```bash
# 查看 Worker 狀態
docker exec nt-celery_worker celery -A network_toolbox inspect active

# 查看 Worker 數量
docker exec nt-celery_worker celery -A network_toolbox inspect stats
```

### 4. 失敗重試

任務失敗會自動重試 3 次：
- 第 1 次：延遲 5 分鐘
- 第 2 次：延遲 10 分鐘
- 第 3 次：延遲 15 分鐘

可以在 `@shared_task` 裝飾器中調整：

```python
@shared_task(
    bind=True,
    max_retries=5,              # 最多重試 5 次
    default_retry_delay=300     # 默認延遲 5 分鐘
)
```

---

## 🐛 故障排查

### 問題 1：任務沒有執行

**檢查步驟**：
```bash
# 1. 確認 Beat 服務運行
docker ps | grep celery_beat

# 2. 查看 Beat 日誌
docker logs --tail 50 nt-celery_beat

# 3. 確認任務已註冊
docker exec nt-django python manage.py shell -c "
from django_celery_beat.models import PeriodicTask
print(PeriodicTask.objects.filter(name__contains='artifacts'))
"
```

### 問題 2：任務執行失敗

**檢查步驟**：
```bash
# 查看錯誤日誌
docker logs nt-celery_worker | grep -A 10 "ERROR"

# 查看特定任務日誌
docker logs nt-celery_worker | grep "store_jenkins_artifacts_task"
```

**常見原因**：
- ❌ NAS 目錄不可寫
- ❌ Jenkins Server 連接失敗
- ❌ 數據庫記錄不存在
- ❌ 磁盤空間不足

### 問題 3：任務執行太慢

**優化方案**：
```python
# 1. 減少批量處理數量
MAX_BUILDS_PER_RUN = 20  # 從 50 降到 20

# 2. 增加 Worker 數量
# 在 docker-compose.yml 中調整：
celery_worker:
  command: celery -A network_toolbox worker --concurrency=8  # 增加並發

# 3. 設置任務超時
@shared_task(time_limit=600)  # 10 分鐘超時
```

---

## 📚 相關文檔

- [ARTIFACTS_AUTO_EXTRACT.md](./ARTIFACTS_AUTO_EXTRACT.md) - 自動解壓縮功能說明
- [TEST_ARTIFACTS_AUTO_DELETE.md](./TEST_ARTIFACTS_AUTO_DELETE.md) - 自動刪除測試報告
- [QUICKSTART_JENKINS_AUTO_STORAGE.md](./QUICKSTART_JENKINS_AUTO_STORAGE.md) - Workspace 自動存儲（參考）

---

## 🎉 總結

通過 Celery 自動化任務，你可以：

- ✅ **完全自動化**：無需手動操作，系統自動處理
- ✅ **批量處理**：一次處理多個 Build
- ✅ **失敗重試**：自動重試失敗的任務
- ✅ **定時執行**：按配置的時間自動執行
- ✅ **靈活配置**：可根據需求調整執行策略

現在你可以放心地讓系統自動管理 Jenkins Artifacts 了！🚀

---

**最後更新**: 2025-11-10  
**版本**: 1.0.0  
**測試狀態**: ✅ 通過
