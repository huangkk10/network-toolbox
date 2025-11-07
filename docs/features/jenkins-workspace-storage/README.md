# Jenkins Workspace 自動存儲到 NAS - 完整功能規劃

## 📋 功能概述

實現 Jenkins Build Workspace 自動或手動存儲到 NAS 的完整解決方案，支援批量存儲、自動化策略、存儲管理等功能。

**目標**：將 Jenkins 構建產生的 Workspace 文件持久化存儲到 NAS，便於追溯、分析和長期保存。

---

## 🎯 已完成功能

### ✅ Phase 1: 數據庫結構 (Completed)
- **JenkinsBuild Model** 已添加 Workspace 存儲相關欄位：
  - `workspace_path` (TextField) - 存儲路徑
  - `workspace_size` (BigIntegerField) - 文件大小（bytes）
  - `workspace_stored_at` (DateTimeField) - 存儲時間
  - `is_workspace_stored` (BooleanField) - 是否已存儲

### ✅ Phase 2: 後端服務 (Completed)
- **JenkinsStorageService** (`library/services/jenkins_storage_service.py`)
  - ✅ `store_workspace()` - 下載並存儲 Workspace
  - ✅ `check_storage_path_accessible()` - 檢查 NAS 路徑可訪問性
  - ✅ 支援 Jenkins 認證（username + API token）
  - ✅ 自動解壓縮 workspace.zip
  - ✅ 計算存儲大小和文件數量

### ✅ Phase 3: API 端點 (Completed)
- **REST API** (`backend/api/views/jenkins.py`)
  - ✅ `POST /api/jenkins-builds/{id}/store_workspace/` - 存儲單個 Build

### ✅ Phase 4: 前端 UI (Completed)
- **RVT 分析頁面** (`frontend/src/pages/RVTAnalysisPage.js`)
  - ✅ "Workspace" 按鈕（SaveOutlined 圖標）
  - ✅ 確認對話框（顯示 Job 名稱、Build 編號、存儲路徑）
  - ✅ 成功/失敗訊息提示
  - ✅ 存儲後自動重新載入數據

### ✅ Phase 5: URL 狀態持久化 (Completed)
- ✅ Server 和 View 篩選條件存儲在 URL
- ✅ 頁面刷新後篩選條件保持不變
- ✅ 支援 URL 分享（帶篩選條件）

---

## 🚀 待實現功能

### 🔧 Phase 6: NAS 掛載配置

**目標**：配置 Docker 容器訪問 NAS 存儲路徑

#### 6.1 配置 NAS 掛載
```yaml
# docker-compose.yml
services:
  django:
    volumes:
      - /mnt/mdt:/mnt/mdt  # 掛載 NAS 到容器
```

#### 6.2 檢查 NAS 可用性
```bash
# 測試 NAS 路徑
ls -la /mnt/mdt/jenkins_test_storage/

# 測試寫入權限
touch /mnt/mdt/jenkins_test_storage/.test_write && rm /mnt/mdt/jenkins_test_storage/.test_write
```

#### 6.3 創建測試端點
```python
# backend/api/views/jenkins.py
@action(detail=False, methods=['GET'])
def check_nas_status(self, request):
    """檢查 NAS 存儲狀態"""
    service = JenkinsStorageService('test', 'test', 1)
    result = service.check_storage_path_accessible()
    return Response(result)
```

---

### 🤖 Phase 7: 自動存儲策略

**目標**：根據規則自動存儲 Workspace（無需手動點擊）

#### 7.1 自動存儲規則配置

**新增 Model**: `JenkinsStoragePolicy`

```python
# backend/api/models.py
class JenkinsStoragePolicy(models.Model):
    """Jenkins Workspace 自動存儲策略"""
    
    # 適用範圍
    server = models.ForeignKey(JenkinsServer, on_delete=models.CASCADE, null=True, blank=True)
    job_name_pattern = models.CharField(max_length=500, blank=True)  # Job 名稱匹配模式（支援萬用字元）
    view_name = models.CharField(max_length=255, blank=True)  # View 名稱
    
    # 觸發條件
    auto_store_on_success = models.BooleanField(default=False)  # 成功時自動存儲
    auto_store_on_failure = models.BooleanField(default=False)  # 失敗時自動存儲
    auto_store_on_unstable = models.BooleanField(default=False)  # 不穩定時自動存儲
    
    # 存儲選項
    store_workspace = models.BooleanField(default=True)  # 存儲 Workspace
    store_console_log = models.BooleanField(default=False)  # 存儲 Console Log
    store_build_info = models.BooleanField(default=False)  # 存儲 Build 資訊
    
    # 保留策略
    max_storage_days = models.IntegerField(default=90)  # 最大保留天數（0 = 永久）
    max_storage_count = models.IntegerField(default=0)  # 最大保留數量（0 = 無限制）
    
    # 優先級
    priority = models.IntegerField(default=0)  # 數字越大優先級越高
    
    # 狀態
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'jenkins_storage_policy'
        verbose_name = 'Jenkins 存儲策略'
        verbose_name_plural = 'Jenkins 存儲策略'
        ordering = ['-priority', '-created_at']
```

#### 7.2 策略匹配引擎

**新增 Service**: `JenkinsStoragePolicyService`

```python
# library/services/jenkins_storage_policy_service.py
class JenkinsStoragePolicyService:
    """Jenkins 存儲策略服務"""
    
    @staticmethod
    def find_matching_policy(build):
        """
        查找匹配的存儲策略
        
        Args:
            build: JenkinsBuild 實例
            
        Returns:
            JenkinsStoragePolicy 或 None
        """
        from api.models import JenkinsStoragePolicy
        import fnmatch
        
        policies = JenkinsStoragePolicy.objects.filter(is_active=True)
        
        for policy in policies:
            # 檢查 Server 匹配
            if policy.server and policy.server.id != build.job.server_id:
                continue
            
            # 檢查 View 匹配
            if policy.view_name and policy.view_name != build.job.view_name:
                continue
            
            # 檢查 Job 名稱匹配（支援萬用字元）
            if policy.job_name_pattern:
                if not fnmatch.fnmatch(build.job.name, policy.job_name_pattern):
                    continue
            
            # 檢查 Build 結果匹配
            if build.result == 'SUCCESS' and not policy.auto_store_on_success:
                continue
            if build.result == 'FAILURE' and not policy.auto_store_on_failure:
                continue
            if build.result == 'UNSTABLE' and not policy.auto_store_on_unstable:
                continue
            
            # 找到匹配的策略
            return policy
        
        return None
    
    @staticmethod
    def apply_policy(build, policy):
        """
        應用存儲策略
        
        Args:
            build: JenkinsBuild 實例
            policy: JenkinsStoragePolicy 實例
        """
        from library.services.jenkins_storage_service import JenkinsStorageService
        import logging
        
        logger = logging.getLogger(__name__)
        logger.info(f"應用存儲策略 {policy.id} 到 Build {build.id}")
        
        # 檢查是否已存儲
        if build.is_workspace_stored:
            logger.info(f"Build {build.id} 已存儲，跳過")
            return
        
        # 創建存儲服務
        service = JenkinsStorageService(
            jenkins_server_ip=build.job.server.ip_address,
            job_name=build.job.name,
            build_number=build.build_number
        )
        
        # 執行存儲
        if policy.store_workspace:
            result = service.store_workspace(
                workspace_url=build.url,
                username=build.job.server.username,
                api_token=build.job.server.api_token
            )
            
            if result['success']:
                build.workspace_path = result['workspace_path']
                build.workspace_size = result['workspace_size']
                build.workspace_stored_at = result['stored_at']
                build.is_workspace_stored = True
                build.save()
                
                logger.info(f"Build {build.id} Workspace 存儲成功")
            else:
                logger.error(f"Build {build.id} Workspace 存儲失敗: {result.get('error')}")
```

#### 7.3 自動觸發機制

**方式 1: 在 Build 同步時觸發**

```python
# backend/api/views/jenkins.py
@action(detail=True, methods=['POST'])
def sync_builds(self, request, pk=None):
    """同步 Jenkins Builds"""
    job = self.get_object()
    
    # ... 同步 Builds 邏輯 ...
    
    # 【新增】自動應用存儲策略
    from library.services.jenkins_storage_policy_service import JenkinsStoragePolicyService
    
    for build in new_builds:  # 新同步的 Builds
        policy = JenkinsStoragePolicyService.find_matching_policy(build)
        if policy:
            JenkinsStoragePolicyService.apply_policy(build, policy)
    
    return Response({'message': 'Builds 同步完成'})
```

**方式 2: 使用 Celery 定時任務**

```python
# backend/api/tasks.py
from celery import shared_task

@shared_task
def auto_store_workspaces():
    """
    定時任務：自動存儲符合策略的 Workspaces
    """
    from api.models import JenkinsBuild
    from library.services.jenkins_storage_policy_service import JenkinsStoragePolicyService
    import logging
    
    logger = logging.getLogger(__name__)
    logger.info("開始執行自動存儲任務")
    
    # 查找最近 24 小時內的 Builds（未存儲）
    from django.utils import timezone
    from datetime import timedelta
    
    yesterday = timezone.now() - timedelta(days=1)
    builds = JenkinsBuild.objects.filter(
        is_workspace_stored=False,
        build_timestamp__gte=yesterday
    )
    
    stored_count = 0
    for build in builds:
        policy = JenkinsStoragePolicyService.find_matching_policy(build)
        if policy:
            try:
                JenkinsStoragePolicyService.apply_policy(build, policy)
                stored_count += 1
            except Exception as e:
                logger.error(f"自動存儲失敗 Build {build.id}: {e}", exc_info=True)
    
    logger.info(f"自動存儲任務完成，已存儲 {stored_count} 個 Workspaces")
    return {'stored_count': stored_count}
```

**Celery Beat 配置**:

```python
# backend/network_toolbox/celery.py
from celery.schedules import crontab

app.conf.beat_schedule = {
    'auto-store-workspaces': {
        'task': 'api.tasks.auto_store_workspaces',
        'schedule': crontab(hour='*/6'),  # 每 6 小時執行一次
    },
}
```

---

### 📊 Phase 8: 存儲管理界面

**目標**：提供 Workspace 存儲管理的完整界面

#### 8.1 存儲策略管理頁面

**新增頁面**: `StoragePolicyPage.js`

功能：
- ✅ 策略列表（Table）
- ✅ 新增策略（Modal）
- ✅ 編輯策略（Modal）
- ✅ 刪除策略（Confirm）
- ✅ 啟用/禁用策略（Switch）

**UI 結構**:
```
┌─────────────────────────────────────────────┐
│  存儲策略管理                     [+ 新增策略]  │
├─────────────────────────────────────────────┤
│  Table:                                     │
│  ├─ 策略名稱                                 │
│  ├─ 適用範圍 (Server, View, Job Pattern)    │
│  ├─ 觸發條件 (Success/Failure/Unstable)     │
│  ├─ 優先級                                   │
│  ├─ 狀態 (啟用/禁用)                         │
│  └─ 操作 (編輯/刪除)                         │
└─────────────────────────────────────────────┘
```

#### 8.2 存儲狀態監控

**擴展現有頁面**: `RVTAnalysisPage.js`

新增功能：
- ✅ 顯示 Workspace 存儲狀態（Build 列表）
  - 🟢 已存儲（顯示大小、時間）
  - ⚪ 未存儲
  - 🔴 存儲失敗
- ✅ 批量存儲按鈕（選擇多個 Builds 批量存儲）
- ✅ 存儲進度顯示（Progress Bar）

**Table 新增欄位**:
```javascript
{
    title: 'Workspace',
    key: 'workspace_status',
    width: 150,
    render: (_, record) => {
        if (record.is_workspace_stored) {
            return (
                <Space direction="vertical" size={0}>
                    <Tag color="success">✅ 已存儲</Tag>
                    <span style={{ fontSize: 11, color: '#999' }}>
                        {(record.workspace_size / (1024**2)).toFixed(2)} MB
                    </span>
                </Space>
            );
        } else {
            return <Tag color="default">⚪ 未存儲</Tag>;
        }
    }
}
```

#### 8.3 存儲空間統計

**新增 API**: `GET /api/jenkins-storage/statistics/`

返回數據：
```json
{
    "total_stored_builds": 150,
    "total_storage_size": 25769803776,  // 24 GB
    "storage_by_server": [
        {
            "server_name": "Server 1",
            "builds_count": 80,
            "storage_size": 15032385536
        }
    ],
    "storage_by_status": {
        "SUCCESS": 120,
        "FAILURE": 20,
        "UNSTABLE": 10
    },
    "recent_30_days_trend": [
        { "date": "2025-11-01", "count": 5, "size": 1073741824 },
        // ...
    ]
}
```

**前端展示**: 在 "概觀" Tab 添加存儲統計卡片

```javascript
<Card>
    <Statistic
        title="已存儲 Workspaces"
        value={statistics.total_stored_builds}
        prefix={<SaveOutlined />}
        suffix="個"
        valueStyle={{ color: '#52c41a' }}
    />
    <div style={{ marginTop: 8, fontSize: 12, color: '#999' }}>
        總大小: {(statistics.total_storage_size / (1024**3)).toFixed(2)} GB
    </div>
</Card>
```

---

### 🗑️ Phase 9: 存儲清理策略

**目標**：自動清理過期的 Workspace，節省 NAS 空間

#### 9.1 清理規則

```python
# backend/api/tasks.py
@shared_task
def cleanup_old_workspaces():
    """
    定時任務：清理過期的 Workspaces
    """
    from api.models import JenkinsBuild, JenkinsStoragePolicy
    from django.utils import timezone
    from datetime import timedelta
    import shutil
    import logging
    
    logger = logging.getLogger(__name__)
    logger.info("開始執行 Workspace 清理任務")
    
    cleaned_count = 0
    freed_space = 0
    
    # 獲取所有已存儲的 Builds
    builds = JenkinsBuild.objects.filter(is_workspace_stored=True)
    
    for build in builds:
        # 查找適用的策略
        policy = JenkinsStoragePolicyService.find_matching_policy(build)
        
        if policy and policy.max_storage_days > 0:
            # 檢查是否超過保留天數
            expiry_date = build.workspace_stored_at + timedelta(days=policy.max_storage_days)
            
            if timezone.now() > expiry_date:
                # 刪除 Workspace 文件
                if build.workspace_path and os.path.exists(build.workspace_path):
                    try:
                        # 計算釋放空間
                        freed_space += build.workspace_size
                        
                        # 刪除目錄
                        shutil.rmtree(os.path.dirname(build.workspace_path))
                        
                        # 更新數據庫
                        build.is_workspace_stored = False
                        build.workspace_path = None
                        build.workspace_size = None
                        build.workspace_stored_at = None
                        build.save()
                        
                        cleaned_count += 1
                        logger.info(f"已清理 Build {build.id} 的 Workspace")
                    except Exception as e:
                        logger.error(f"清理失敗 Build {build.id}: {e}", exc_info=True)
    
    logger.info(f"清理任務完成，已清理 {cleaned_count} 個 Workspaces，釋放 {freed_space / (1024**3):.2f} GB")
    return {'cleaned_count': cleaned_count, 'freed_space': freed_space}
```

#### 9.2 Celery Beat 配置

```python
app.conf.beat_schedule = {
    'cleanup-old-workspaces': {
        'task': 'api.tasks.cleanup_old_workspaces',
        'schedule': crontab(hour=2, minute=0),  # 每天凌晨 2 點執行
    },
}
```

---

### 🔍 Phase 10: 進階功能

#### 10.1 Workspace 瀏覽器

**功能**：在網頁界面中瀏覽 Workspace 文件內容

- 📁 文件樹狀結構顯示
- 📄 文本文件預覽（支援語法高亮）
- 🖼️ 圖片文件預覽
- 📦 文件下載

#### 10.2 Workspace 比較

**功能**：比較兩個 Build 的 Workspace 差異

- 文件新增/刪除/修改對比
- 文件內容 Diff 顯示
- 大小變化對比

#### 10.3 存儲效能優化

- ✅ 增量存儲（只存儲變更部分）
- ✅ 壓縮存儲（減少空間佔用）
- ✅ 異步存儲（不阻塞 UI）
- ✅ 並行存儲（批量存儲時使用多線程）

---

## 📝 實施優先級

### 🔴 高優先級（立即實施）

1. **Phase 6: NAS 掛載配置** ⭐⭐⭐⭐⭐
   - 沒有這個，所有功能都無法運行
   - 預計時間：30 分鐘

2. **測試基本存儲功能** ⭐⭐⭐⭐⭐
   - 點擊 "Workspace" 按鈕測試存儲流程
   - 預計時間：15 分鐘

### 🟡 中優先級（短期實施）

3. **Phase 8.2: 存儲狀態顯示** ⭐⭐⭐⭐
   - 在 Table 中顯示存儲狀態
   - 預計時間：1 小時

4. **Phase 8.3: 存儲空間統計** ⭐⭐⭐⭐
   - 在概觀 Tab 顯示統計卡片
   - 預計時間：1.5 小時

### 🟢 低優先級（長期實施）

5. **Phase 7: 自動存儲策略** ⭐⭐⭐
   - 實現完整的策略引擎和管理界面
   - 預計時間：4-6 小時

6. **Phase 9: 存儲清理策略** ⭐⭐
   - 自動清理過期 Workspaces
   - 預計時間：2 小時

7. **Phase 10: 進階功能** ⭐
   - Workspace 瀏覽器、比較等
   - 預計時間：8-10 小時

---

## 🛠️ 下一步行動

### 立即可執行的任務：

1. **配置 NAS 掛載**
   ```bash
   # 檢查 NAS 路徑是否存在
   ls -la /mnt/mdt/
   
   # 修改 docker-compose.yml 添加 Volume
   # 重啟 Django 容器
   ```

2. **測試基本存儲**
   - 選擇一個 Build
   - 點擊 "Workspace" 按鈕
   - 確認存儲成功並檢查 NAS 路徑

3. **添加存儲狀態顯示**
   - 修改 Table columns
   - 添加存儲狀態標籤
   - 顯示文件大小和時間

---

## 📊 預期成果

### 短期目標（1-2 天）
- ✅ 手動存儲功能完全可用
- ✅ 存儲狀態可視化
- ✅ 基本統計報表

### 中期目標（1-2 週）
- ✅ 自動存儲策略運行
- ✅ 策略管理界面
- ✅ 批量存儲功能

### 長期目標（1 個月）
- ✅ 完整的存儲管理系統
- ✅ 自動清理策略
- ✅ 進階分析功能

---

**最後更新**：2025-11-05  
**維護者**：Network Toolbox Team  
**相關文檔**：
- [Jenkins Storage Service 開發指南](./DEVELOPMENT.md)
- [NAS 配置指南](./NAS_SETUP.md)
- [API 文檔](../../api/JENKINS_STORAGE_API.md)
