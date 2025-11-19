# RVT 分析頁面 - Job 最新 Build 時間顯示

## 📝 功能概述

在 RVT 分析頁面的 Job 列表中新增「最新 Build 時間」欄位，顯示每個 Job 的最後一次構建時間。

## ✨ 功能特性

### 1. 智能時間顯示

時間顯示會根據距離現在的時長自動選擇最合適的格式：

| 時間差 | 顯示格式 | 範例 |
|--------|---------|------|
| < 1 分鐘 | 剛剛 | 剛剛 |
| < 1 小時 | N 分鐘前 | 25 分鐘前 |
| < 1 天 | N 小時前 | 3 小時前 |
| < 7 天 | N 天前 | 5 天前 |
| ≥ 7 天 | 完整日期 | 2025/11/12 |

### 2. 視覺提示

- **正常顏色**（灰色）：7 天內有更新的 Job
- **警告顏色**（紅色）：超過 7 天未更新的 Job
- **無數據**：顯示「無 Build 記錄」

### 3. Tooltip 懸停顯示

將鼠標懸停在時間上，會顯示完整的日期時間：
```
2025/11/19 下午3:26:30
```

## 🔧 技術實現

### 前端修改

#### 文件：`frontend/src/pages/RVTAnalysisPage.js`

**修改的表格欄位：**
```javascript
{
    title: '最新 Build 時間',
    dataIndex: 'last_build_time',
    key: 'time',
    width: 200,
    render: (text, record) => {
        if (record.type === 'job') {
            // Job 行：顯示最新 Build 時間
            if (!text || text === 'N/A') {
                return <span style={{ color: '#999' }}>無 Build 記錄</span>;
            }
            
            // 計算相對時間
            const buildTime = new Date(text);
            const now = new Date();
            const diffMs = now - buildTime;
            const diffDays = Math.floor(diffMs / 86400000);
            
            // 根據天數顯示不同顏色
            return (
                <Tooltip title={buildTime.toLocaleString('zh-TW')}>
                    <span style={{ color: diffDays > 7 ? '#ff4d4f' : '#666' }}>
                        {relativeTime}
                    </span>
                </Tooltip>
            );
        } else {
            // Build 行：顯示構建開始時間
            return <span>{record.build_timestamp}</span>;
        }
    },
}
```

### 後端修改

#### 1. 模型欄位

**文件：`backend/api/models.py`**

`JenkinsJob` 模型已有的欄位：
```python
class JenkinsJob(models.Model):
    # ...
    last_build_number = models.IntegerField(null=True, blank=True)
    last_build_status = models.CharField(max_length=50, blank=True)
    last_build_time = models.DateTimeField(null=True, blank=True)  # ← 關鍵欄位
```

#### 2. 數據初始化腳本

**文件：`backend/update_job_last_build_time.py`** (新建)

用於一次性更新所有現有 Job 的 `last_build_time`：

```python
def update_all_jobs_last_build_time():
    """更新所有 Jobs 的 last_build_time"""
    jobs = JenkinsJob.objects.all()
    
    for job in jobs:
        latest_build = job.builds.order_by('-build_number').first()
        
        if latest_build and latest_build.build_timestamp:
            job.last_build_time = latest_build.build_timestamp
            job.last_build_number = latest_build.build_number
            job.last_build_status = latest_build.result
            job.save(update_fields=['last_build_time', 'last_build_number', 'last_build_status'])
```

**執行方式：**
```bash
docker exec nt-django python update_job_last_build_time.py
```

**執行結果：**
```
總共 756 個 Jobs 需要處理
已更新: 566 個
無 Build 數據: 190 個
```

#### 3. 自動同步更新

**文件：`backend/api/tasks.py`**

修改 `sync_jenkins_builds` 任務，在創建新 Build 時自動更新 Job 的 `last_build_time`：

```python
# 創建 Build 記錄
build = JenkinsBuild.objects.create(...)
builds_created += 1

# 🆕 更新 Job 的 last_build_time（如果這個 Build 更新）
if not job.last_build_time or build_timestamp > job.last_build_time:
    job.last_build_time = build_timestamp
    job.last_build_number = build_number
    job.last_build_status = result or 'UNKNOWN'
    job.save(update_fields=['last_build_time', 'last_build_number', 'last_build_status'])
```

## 📊 數據統計

### 當前狀態

```
總 Jobs: 756
有 last_build_time 數據: 566 個 (74.9%)
無 Build 記錄: 190 個 (25.1%)
```

### 最新更新的 Jobs

```
Job: SAF3119_KVM05 | Server: 10.252.170.182 | Time: 2025-11-19 07:26:30
Job: SAF3119_KVM02 | Server: 10.252.170.182 | Time: 2025-11-19 07:20:13
Job: SAF7518_K05   | Server: 10.252.170.188 | Time: 2025-11-19 07:12:45
Job: SAF3108_KVM14 | Server: 10.252.170.182 | Time: 2025-11-19 06:55:07
Job: SAF3108_KVM13 | Server: 10.252.170.182 | Time: 2025-11-19 06:53:46
```

## 🎨 UI 展示

### Job 行顯示

| 情況 | 顯示內容 | 顏色 | 範例 |
|------|---------|------|------|
| 剛更新 | 「剛剛」 | 灰色 | 剛剛 |
| 幾分鐘前 | 「N 分鐘前」 | 灰色 | 25 分鐘前 |
| 幾小時前 | 「N 小時前」 | 灰色 | 3 小時前 |
| 幾天前 | 「N 天前」 | 灰色 | 5 天前 |
| 超過 7 天 | 完整日期 | **紅色** | 2025/11/12 |
| 無 Build | 「無 Build 記錄」 | 淺灰 | 無 Build 記錄 |

### Build 行顯示

Build 行顯示的是 `build_timestamp`（構建開始時間），格式：
```
2025-11-19 15:26:30
```

## 🧪 測試驗證

### 前端測試

1. **訪問頁面**：前往 RVT 分析 → Details 標籤
2. **檢查欄位**：確認「最新 Build 時間」欄位顯示正確
3. **懸停測試**：將鼠標懸停在時間上，檢查 Tooltip
4. **顏色測試**：確認超過 7 天的 Job 顯示紅色

### 後端測試

```bash
# 檢查數據
docker exec nt-django python manage.py shell -c "
from api.models import JenkinsJob

# 統計
total = JenkinsJob.objects.count()
with_time = JenkinsJob.objects.exclude(last_build_time__isnull=True).count()
print(f'總 Jobs: {total}')
print(f'有 last_build_time: {with_time} ({with_time/total*100:.1f}%)')

# 查看範例
jobs = JenkinsJob.objects.exclude(last_build_time__isnull=True).order_by('-last_build_time')[:3]
for job in jobs:
    print(f'{job.name}: {job.last_build_time}')
"
```

### 同步測試

```bash
# 手動觸發 Build 同步
docker exec nt-django python manage.py shell -c "
from api.tasks import sync_jenkins_builds_task
result = sync_jenkins_builds_task.delay()
print(f'Task ID: {result.id}')
"

# 檢查任務結果
docker logs nt-celery-worker --tail 50 | grep "Jenkins Builds"
```

## 🔄 未來增強

### 潛在改進

1. **排序功能**
   - 允許按最新 Build 時間排序
   - 快速找到最久沒更新的 Jobs

2. **篩選功能**
   - 篩選超過 N 天未更新的 Jobs
   - 篩選特定時間範圍內有更新的 Jobs

3. **警示功能**
   - 自動標記超過閾值未更新的 Jobs
   - 發送通知提醒管理員

4. **統計圖表**
   - Job 更新頻率分佈圖
   - 活躍度趨勢圖

## 📚 相關文件

- [RVT Analysis 頁面文檔](../features/)
- [Jenkins 圖表功能](./JENKINS_CHARTS_FEATURE.md)
- [Celery 同步任務](../troubleshooting/CELERY_QUEUE_CONFIGURATION_FIX.md)

## 🐛 故障排除

### 問題：顯示「N/A」或「無 Build 記錄」

**原因**：
1. Job 真的沒有 Build 記錄
2. `last_build_time` 欄位未初始化

**解決方案**：
```bash
# 執行初始化腳本
docker exec nt-django python update_job_last_build_time.py

# 或手動同步 Builds
docker exec nt-django python manage.py shell -c "
from api.tasks import sync_jenkins_builds_task
sync_jenkins_builds_task.delay(max_builds_per_job=50)
"
```

### 問題：時間顯示不正確

**原因**：時區問題

**解決方案**：
- 檢查 Django `TIME_ZONE` 設置（應為 `Asia/Taipei`）
- 確認 `USE_TZ = True`
- 檢查瀏覽器時區設置

### 問題：顏色顯示不正確

**原因**：CSS 樣式衝突

**解決方案**：
- 清除瀏覽器緩存
- 檢查瀏覽器開發者工具 Console 是否有錯誤

## 維護記錄

| 日期 | 版本 | 作者 | 變更說明 |
|------|------|------|---------|
| 2025-11-19 | 1.0.0 | GitHub Copilot | 初始實現：新增最新 Build 時間顯示功能 |
| 2025-11-19 | 1.0.1 | GitHub Copilot | 新增自動同步更新邏輯 |

---

**注意**: 此功能依賴於 Celery 定時任務 `sync-jenkins-builds-every-10-minutes` 自動更新數據。
