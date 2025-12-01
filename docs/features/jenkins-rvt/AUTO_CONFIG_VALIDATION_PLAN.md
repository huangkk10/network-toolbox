# Build 配置自動檢查功能規劃

**文件版本**：v1.0  
**建立日期**：2025-12-01  
**狀態**：規劃中  

---

## 目錄

1. [功能概述](#一功能概述)
2. [現狀分析](#二現狀分析)
3. [架構設計](#三架構設計)
4. [詳細規劃](#四詳細規劃)
5. [執行計畫](#五執行計畫)
6. [可配置項目](#六可配置項目)
7. [注意事項](#七注意事項)

---

## 一、功能概述

### 1.1 目標

當 Jenkins Build 執行完成後，系統自動執行配置檢查（Config Validation），並將結果存儲到 NAS 對應的 Build 目錄中，讓用戶點擊「檢查配置」時直接看到結果，無需手動觸發檢查。

### 1.2 預期效果

#### Before（現在）
```
用戶點擊「檢查配置」→ 進入頁面 → 點擊「開始檢查」→ 等待檢查 → 顯示結果
```

#### After（修改後）
```
Build 完成 → (5分鐘內) 自動執行配置檢查 → 結果存入 NAS (config_validation.json)
                                              ↓
用戶點擊「檢查配置」→ 進入頁面 → 直接顯示檢查結果
                                     ↓
                          （可選）點擊「重新檢查」更新結果
```

---

## 二、現狀分析

### 2.1 目前流程

1. 用戶在 **RVT 分析頁面** 點擊「檢查配置」按鈕
2. 進入 **BuildConfigValidatorPage** 頁面
3. 用戶手動點擊「開始檢查」按鈕
4. 系統調用 `POST /api/jenkins-builds/{id}/validate_config/` 執行檢查
5. 即時返回檢查結果（不存儲）

### 2.2 現有資源

| 資源 | 路徑 | 說明 |
|------|------|------|
| 後端驗證器 | `library/services/build_config_validator.py` | BuildConfigValidator 類別 |
| API 端點 | `POST /api/jenkins-builds/{id}/validate_config/` | 執行配置檢查 |
| 前端頁面 | `frontend/src/pages/BuildConfigValidatorPage.js` | 檢查結果展示頁面 |

### 2.3 現有 NAS 存儲結構

```
/mnt/mdt/Team/PQ1-3/tool/jenkins_test_storage/
└── {jenkins_server_ip}/           # 例如：10.252.170.171
    └── {job_name}/                # 例如：SAF7009_K09
        └── {build_number}/        # 例如：38
            ├── workspace/         # Workspace 存儲
            ├── artifacts/         # Artifacts 存儲
            ├── console.log        # Console 日誌
            └── fatal_analysis.json # Fatal Error 分析結果（已有）
```

### 2.4 類似功能參考：Fatal Analysis

系統已有類似的自動分析機制 (`fatal_analysis.json`)：

- **觸發時機**：Build 完成後，定時任務自動執行
- **存儲位置**：`{build_path}/fatal_analysis.json`
- **前端讀取**：`GET /api/jenkins-builds/{id}/fatal_analysis/`
- **檢查存在**：`GET /api/jenkins-builds/{id}/has_fatal_analysis/`

---

## 三、架構設計

### 3.1 存儲方案：NAS 檔案存儲

採用與 `fatal_analysis.json` 相同的設計模式：

```
/mnt/mdt/Team/PQ1-3/tool/jenkins_test_storage/
└── {jenkins_server_ip}/
    └── {job_name}/
        └── {build_number}/
            ├── workspace/
            ├── artifacts/
            ├── console.log
            ├── fatal_analysis.json      # 已有
            └── config_validation.json   # 新增 ⭐
```

### 3.2 JSON 檔案格式

**檔案名稱**：`config_validation.json`

**檔案內容**：
```json
{
    "build_info": {
        "build_id": 19696,
        "job_name": "SAF7009_K09",
        "build_number": 38,
        "build_result": "FAILURE",
        "validated_at": "2025-12-01T10:30:45+08:00",
        "auto_triggered": true
    },
    "overall_status": "warning",
    "config_source": "ansible_inventory",
    "summary": {
        "total_checks": 4,
        "passed": 3,
        "warnings": 1,
        "errors": 0
    },
    "checks": {
        "host_ip": {
            "status": "success",
            "message": "HOST_IP found in DHCP lease: 10.252.50.100",
            "value": "10.252.50.100",
            "details": {
                "ip_address": "10.252.50.100",
                "mac_address": "00:11:22:33:44:55",
                "hostname": "SAF7009_K09",
                "dhcp_server": "DHCP-Server-1",
                "lease_start": "2025-12-01T08:00:00",
                "lease_end": "2025-12-02T08:00:00"
            },
            "suggestions": []
        },
        "host_mac": {
            "status": "success",
            "message": "HOST_MAC matches DHCP lease",
            "value": "00:11:22:33:44:55",
            "details": {...},
            "suggestions": []
        },
        "uart_ip": {
            "status": "success",
            "message": "UART_IP found in DHCP lease",
            "value": "10.252.50.200",
            "details": {...},
            "suggestions": []
        },
        "uart_ssh": {
            "status": "warning",
            "message": "SSH connection timeout",
            "value": "10.252.50.200",
            "details": {
                "ip": "10.252.50.200",
                "user": "admin",
                "port": 22,
                "connected": false,
                "error": "Connection timeout"
            },
            "suggestions": [
                "Check if UART PC is powered on",
                "Check network connectivity"
            ]
        }
    }
}
```

### 3.3 系統流程圖

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        Build 配置自動檢查流程                                 │
└─────────────────────────────────────────────────────────────────────────────┘

                              Jenkins Build 完成
                                     │
                                     ▼
               ┌─────────────────────────────────────────┐
               │  sync_active_jenkins_builds (每 1 分鐘)  │
               │  - 更新 is_building = False              │
               │  - 更新 result = FAILURE/SUCCESS/...    │
               └─────────────────────────────────────────┘
                                     │
                                     ▼
               ┌─────────────────────────────────────────┐
               │  auto_validate_completed_builds         │
               │  (每 5 分鐘執行)                          │
               │                                         │
               │  篩選條件：                              │
               │  1. is_building = False                 │
               │  2. 無 config_validation.json           │
               │  3. 優先 FAILURE/ABORTED/UNSTABLE       │
               │  4. 最近 7 天內的 Build                  │
               └─────────────────────────────────────────┘
                                     │
                                     ▼
               ┌─────────────────────────────────────────┐
               │  BuildConfigValidator.validate()        │
               │                                         │
               │  檢查項目：                              │
               │  ✓ HOST_IP (DHCP 租約)                  │
               │  ✓ HOST_MAC (MAC 地址比對)              │
               │  ✓ UART_IP (DHCP 租約)                  │
               │  ✓ UART_SSH (SSH 連線測試)              │
               └─────────────────────────────────────────┘
                                     │
                                     ▼
               ┌─────────────────────────────────────────┐
               │  存儲結果到 NAS                          │
               │                                         │
               │  路徑：                                  │
               │  /mnt/mdt/Team/PQ1-3/tool/              │
               │    jenkins_test_storage/                │
               │      {server_ip}/{job}/{build}/         │
               │        config_validation.json           │
               └─────────────────────────────────────────┘
                                     │
                                     ▼
               ┌─────────────────────────────────────────┐
               │  用戶點擊「檢查配置」                     │
               │                                         │
               │  前端流程：                              │
               │  1. GET /api/.../has_config_validation/ │
               │  2. 如有結果 → 直接顯示                   │
               │  3. 如無結果 → 顯示「開始檢查」按鈕        │
               └─────────────────────────────────────────┘
```

---

## 四、詳細規劃

### 4.1 後端 API 修改

#### 4.1.1 新增 API：檢查是否有配置檢查結果

**端點**：`GET /api/jenkins-builds/{id}/has_config_validation/`

**實作位置**：`backend/api/views/jenkins.py`

```python
@action(detail=True, methods=['get'], url_path='has_config_validation')
def has_config_validation(self, request, pk=None):
    """
    檢查 Build 是否有配置檢查結果
    
    GET /api/jenkins-builds/{id}/has_config_validation/
    
    Returns:
        {
            'has_validation': bool,
            'overall_status': str | null,
            'validated_at': str | null,
            'file_path': str | null
        }
    """
    build = self.get_object()
    
    # 檢查 JSON 文件是否存在
    validation_path = self._get_config_validation_path(build)
    
    if validation_path and validation_path.exists():
        try:
            with open(validation_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            return Response({
                'has_validation': True,
                'overall_status': data.get('overall_status'),
                'validated_at': data.get('build_info', {}).get('validated_at'),
                'file_path': str(validation_path)
            })
        except Exception as e:
            logger.error(f'讀取 config_validation.json 失敗: {e}')
    
    return Response({
        'has_validation': False,
        'overall_status': None,
        'validated_at': None,
        'file_path': None
    })
```

#### 4.1.2 新增 API：獲取配置檢查結果

**端點**：`GET /api/jenkins-builds/{id}/config_validation/`

**實作位置**：`backend/api/views/jenkins.py`

```python
@action(detail=True, methods=['get'], url_path='config_validation')
def config_validation(self, request, pk=None):
    """
    獲取 Build 的配置檢查完整內容
    
    GET /api/jenkins-builds/{id}/config_validation/
    
    Returns:
        完整的 config_validation.json 內容
    """
    build = self.get_object()
    
    validation_path = self._get_config_validation_path(build)
    
    if not validation_path or not validation_path.exists():
        return Response({
            'error': 'Config validation file not found',
            'hint': 'Validation may not have been performed yet'
        }, status=status.HTTP_404_NOT_FOUND)
    
    try:
        with open(validation_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return Response(data)
    except Exception as e:
        logger.error(f'讀取 config_validation.json 失敗: {e}')
        return Response({
            'error': f'Failed to read validation file: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
```

#### 4.1.3 修改現有 API：validate_config

**端點**：`POST /api/jenkins-builds/{id}/validate_config/`

**修改內容**：執行檢查後，將結果存儲到 NAS

```python
@action(detail=True, methods=['post'])
def validate_config(self, request, pk=None):
    """
    檢查 Build 配置（支持手動觸發）
    
    修改：檢查完成後將結果存儲到 NAS
    """
    from library.services.build_config_validator import BuildConfigValidator
    
    build = self.get_object()
    dhcp_server_id = request.data.get('dhcp_server_id')
    dhcp_server_ids = [dhcp_server_id] if dhcp_server_id else None
    
    try:
        # 執行檢查
        validator = BuildConfigValidator(build.id, dhcp_server_ids=dhcp_server_ids)
        result = validator.validate()
        
        # 新增：存儲結果到 NAS
        self._save_config_validation_result(build, result, auto_triggered=False)
        
        logger.info(f"Build #{build.build_number} 配置檢查完成: {result['overall_status']}")
        
        return Response(result)
        
    except Exception as e:
        logger.error(f"配置檢查失敗: {e}", exc_info=True)
        return Response({
            'success': False,
            'message': f'檢查失敗: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
```

#### 4.1.4 輔助方法：路徑和存儲

```python
def _get_config_validation_path(self, build):
    """獲取 config_validation.json 的路徑"""
    from django.conf import settings
    from pathlib import Path
    
    if not build.job or not build.job.server:
        return None
    
    server_ip = build.job.server.ip_address
    job_name = build.job.name
    build_number = build.build_number
    
    base_path = Path(settings.JENKINS_STORAGE_BASE_PATH)
    validation_path = base_path / server_ip / job_name / str(build_number) / 'config_validation.json'
    
    return validation_path

def _save_config_validation_result(self, build, result, auto_triggered=False):
    """存儲配置檢查結果到 NAS"""
    from django.utils import timezone
    from pathlib import Path
    import json
    
    validation_path = self._get_config_validation_path(build)
    
    if not validation_path:
        logger.warning(f'無法獲取 Build #{build.id} 的存儲路徑')
        return False
    
    # 確保目錄存在
    validation_path.parent.mkdir(parents=True, exist_ok=True)
    
    # 添加 build_info
    result['build_info'] = {
        'build_id': build.id,
        'job_name': build.job.name if build.job else 'Unknown',
        'build_number': build.build_number,
        'build_result': build.result,
        'validated_at': timezone.now().isoformat(),
        'auto_triggered': auto_triggered
    }
    
    try:
        with open(validation_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        logger.info(f'✅ 配置檢查結果已存儲: {validation_path}')
        return True
    except Exception as e:
        logger.error(f'❌ 存儲配置檢查結果失敗: {e}', exc_info=True)
        return False
```

### 4.2 新增 Celery 定時任務

**任務名稱**：`auto_validate_completed_builds`

**實作位置**：`backend/api/tasks.py`

```python
@shared_task(
    bind=True,
    name='api.tasks.auto_validate_completed_builds',
    max_retries=2,
    time_limit=300  # 5 分鐘超時
)
def auto_validate_completed_builds(self, limit=50, days=7, priority_failed=True):
    """
    自動檢查已完成 Build 的配置
    
    【策略】
    1. 優先檢查 FAILURE/ABORTED/UNSTABLE 的 Build
    2. 其次檢查 SUCCESS 的 Build（可選）
    3. 只檢查尚未有檢查結果的 Build（檢查 config_validation.json 是否存在）
    4. 限制每次執行的數量（避免過載）
    
    【參數】
    - limit: 每次最多檢查的 Build 數量（預設 50）
    - days: 只檢查最近 N 天的 Build（預設 7 天）
    - priority_failed: 是否優先檢查失敗的 Build（預設 True）
    
    【返回】
    - success: 是否成功
    - total_checked: 檢查的 Build 數量
    - validated: 成功驗證的數量
    - skipped: 跳過的數量（已有結果）
    - errors: 錯誤數量
    - duration: 執行時間（秒）
    """
    import time
    from datetime import timedelta
    from django.utils import timezone
    from django.conf import settings
    from pathlib import Path
    from api.models import JenkinsBuild
    from library.services.build_config_validator import BuildConfigValidator
    
    start_time = time.time()
    logger.info('[Celery] 🚀 開始自動配置檢查任務')
    
    total_checked = 0
    validated = 0
    skipped = 0
    errors = 0
    
    try:
        # 計算時間範圍
        cutoff_date = timezone.now() - timedelta(days=days)
        
        # 查詢已完成的 Builds
        builds_query = JenkinsBuild.objects.filter(
            is_building=False,
            build_timestamp__gte=cutoff_date,
            job__server__is_active=True
        ).select_related('job', 'job__server')
        
        # 排序：優先失敗的 Build
        if priority_failed:
            # FAILURE, ABORTED, UNSTABLE 優先
            from django.db.models import Case, When, IntegerField
            builds_query = builds_query.annotate(
                priority=Case(
                    When(result='FAILURE', then=0),
                    When(result='ABORTED', then=1),
                    When(result='UNSTABLE', then=2),
                    default=3,
                    output_field=IntegerField()
                )
            ).order_by('priority', '-build_timestamp')
        else:
            builds_query = builds_query.order_by('-build_timestamp')
        
        # 限制數量
        builds = builds_query[:limit * 2]  # 多取一些，因為可能有部分會跳過
        
        base_path = Path(settings.JENKINS_STORAGE_BASE_PATH)
        
        for build in builds:
            if validated >= limit:
                break
            
            total_checked += 1
            
            try:
                # 檢查是否已有結果
                if not build.job or not build.job.server:
                    logger.warning(f'[Celery]   ⚠️ Build #{build.id} 缺少 Job 或 Server 資訊，跳過')
                    skipped += 1
                    continue
                
                server_ip = build.job.server.ip_address
                job_name = build.job.name
                build_number = build.build_number
                
                validation_path = base_path / server_ip / job_name / str(build_number) / 'config_validation.json'
                
                if validation_path.exists():
                    logger.debug(f'[Celery]   ⏭️ Build #{build.id} 已有檢查結果，跳過')
                    skipped += 1
                    continue
                
                # 執行配置檢查
                logger.info(f'[Celery]   🔍 檢查 Build: {job_name} #{build_number} (result={build.result})')
                
                validator = BuildConfigValidator(build.id)
                result = validator.validate()
                
                # 存儲結果
                validation_path.parent.mkdir(parents=True, exist_ok=True)
                
                result['build_info'] = {
                    'build_id': build.id,
                    'job_name': job_name,
                    'build_number': build_number,
                    'build_result': build.result,
                    'validated_at': timezone.now().isoformat(),
                    'auto_triggered': True
                }
                
                with open(validation_path, 'w', encoding='utf-8') as f:
                    json.dump(result, f, ensure_ascii=False, indent=2)
                
                validated += 1
                logger.info(f'[Celery]   ✅ {job_name} #{build_number}: {result["overall_status"]}')
                
            except Exception as e:
                errors += 1
                logger.error(f'[Celery]   ❌ Build #{build.id} 檢查失敗: {e}', exc_info=True)
        
        duration = time.time() - start_time
        
        logger.info('[Celery] ✅ 自動配置檢查任務完成')
        logger.info(f'[Celery]   - 總計檢查: {total_checked} 個')
        logger.info(f'[Celery]   - 成功驗證: {validated} 個')
        logger.info(f'[Celery]   - 跳過（已有結果）: {skipped} 個')
        logger.info(f'[Celery]   - 錯誤: {errors} 個')
        logger.info(f'[Celery]   - 耗時: {duration:.2f} 秒')
        
        return {
            'success': True,
            'total_checked': total_checked,
            'validated': validated,
            'skipped': skipped,
            'errors': errors,
            'duration': duration
        }
        
    except Exception as e:
        logger.error(f'[Celery] ❌ 自動配置檢查任務失敗: {e}', exc_info=True)
        return {
            'success': False,
            'error': str(e),
            'duration': time.time() - start_time
        }
```

### 4.3 Celery Beat 排程配置

**實作位置**：`backend/network_toolbox/celery.py`

```python
# 在 beat_schedule 中新增
'auto-validate-completed-builds-every-5-minutes': {
    'task': 'api.tasks.auto_validate_completed_builds',
    'schedule': crontab(minute='*/5'),  # 每 5 分鐘執行一次
    'kwargs': {
        'limit': 50,              # 每次最多檢查 50 個 Builds
        'days': 7,                # 只檢查最近 7 天的 Builds
        'priority_failed': True,  # 優先檢查失敗的 Build
    },
    'options': {
        'expires': 240,           # 任務超時 4 分鐘
    }
},
```

### 4.4 前端頁面修改

**實作位置**：`frontend/src/pages/BuildConfigValidatorPage.js`

#### 4.4.1 新增：獲取已有檢查結果

```javascript
// 新增狀態
const [hasExistingResult, setHasExistingResult] = useState(false);

// 修改 useEffect
useEffect(() => {
    if (buildId) {
        fetchBuildInfo();
        fetchExistingValidation();  // 新增：優先獲取已有結果
        fetchDhcpServers();
    }
}, [buildId]);

// 新增：獲取已有的檢查結果
const fetchExistingValidation = async () => {
    setLoading(true);
    try {
        // 先檢查是否有結果
        const checkResponse = await axios.get(`/api/jenkins-builds/${buildId}/has_config_validation/`);
        
        if (checkResponse.data.has_validation) {
            // 有結果，獲取完整內容
            const resultResponse = await axios.get(`/api/jenkins-builds/${buildId}/config_validation/`);
            setValidationResult(resultResponse.data);
            setValidationTime(new Date(resultResponse.data.build_info?.validated_at));
            setHasExistingResult(true);
            
            // 如果是自動觸發的，顯示提示
            if (resultResponse.data.build_info?.auto_triggered) {
                message.info('此檢查結果由系統自動生成');
            }
        }
    } catch (error) {
        // 沒有結果，顯示手動檢查按鈕
        console.log('No existing validation result, manual check required');
    } finally {
        setLoading(false);
    }
};
```

#### 4.4.2 修改：執行檢查區域

```javascript
{/* 執行檢查區域 - 僅在沒有結果時顯示 */}
{!validationResult && !loading && (
    <Card title="執行檢查" style={{ marginBottom: '24px' }}>
        <Space direction="vertical" style={{ width: '100%' }}>
            {buildInfo && (
                <Descriptions column={2} size="small">
                    <Descriptions.Item label="Job 名稱">
                        {buildInfo.job_name}
                    </Descriptions.Item>
                    <Descriptions.Item label="Build 編號">
                        #{buildInfo.build_number}
                    </Descriptions.Item>
                </Descriptions>
            )}
            <Divider />
            <div>
                <Text strong>指定 DHCP Server（可選）：</Text>
                <Select
                    placeholder="選擇 DHCP Server（留空則自動選擇）"
                    allowClear
                    style={{ width: '100%', marginTop: '8px' }}
                    value={selectedDhcpServer}
                    onChange={setSelectedDhcpServer}
                >
                    {dhcpServers.map((server) => (
                        <Option key={server.id} value={server.id}>
                            {server.name} ({server.ip_address})
                        </Option>
                    ))}
                </Select>
            </div>
            <Button
                type="primary"
                icon={<SyncOutlined />}
                onClick={handleValidate}
                loading={loading}
                size="large"
                block
            >
                開始檢查
            </Button>
        </Space>
    </Card>
)}
```

#### 4.4.3 修改：顯示自動檢查標記

```javascript
// 在 renderOverviewCard 中新增自動檢查標記
const renderOverviewCard = () => {
    if (!validationResult) return null;

    const { overall_status, config_source, summary, build_info } = validationResult;
    const progress = calculateProgress();

    return (
        <Card 
            title={
                <Space>
                    <span>📋 檢查總覽</span>
                    {build_info?.auto_triggered && (
                        <Tag color="blue">自動檢查</Tag>
                    )}
                </Space>
            }
            style={{ marginBottom: '24px' }}
        >
            {/* ... 現有內容 ... */}
        </Card>
    );
};
```

---

## 五、執行計畫

### 5.1 執行順序

| 步驟 | 內容 | 影響檔案 | 預計時間 |
|------|------|---------|---------|
| **1** | 在 JenkinsBuildViewSet 新增輔助方法 | `backend/api/views/jenkins.py` | 15 分鐘 |
| **2** | 新增 `has_config_validation` API | `backend/api/views/jenkins.py` | 10 分鐘 |
| **3** | 新增 `config_validation` API (GET) | `backend/api/views/jenkins.py` | 10 分鐘 |
| **4** | 修改 `validate_config` API，存儲結果 | `backend/api/views/jenkins.py` | 15 分鐘 |
| **5** | 新增 Celery Task | `backend/api/tasks.py` | 30 分鐘 |
| **6** | 在 celery.py 添加排程配置 | `backend/network_toolbox/celery.py` | 5 分鐘 |
| **7** | 修改前端頁面 | `frontend/src/pages/BuildConfigValidatorPage.js` | 30 分鐘 |
| **8** | 測試驗證 | - | 30 分鐘 |

**總預計時間**：約 2.5 小時

### 5.2 測試清單

- [ ] API 測試：`GET /api/jenkins-builds/{id}/has_config_validation/`
- [ ] API 測試：`GET /api/jenkins-builds/{id}/config_validation/`
- [ ] API 測試：`POST /api/jenkins-builds/{id}/validate_config/` (存儲功能)
- [ ] NAS 檔案測試：確認 `config_validation.json` 正確生成
- [ ] Celery 任務測試：手動觸發 `auto_validate_completed_builds`
- [ ] 前端測試：頁面載入時自動顯示已有結果
- [ ] 前端測試：無結果時顯示手動檢查按鈕
- [ ] 前端測試：重新檢查功能

---

## 六、可配置項目

| 配置項 | 預設值 | 說明 | 修改位置 |
|--------|--------|------|---------|
| 執行頻率 | 每 5 分鐘 | 可調整為 1-10 分鐘 | `celery.py` |
| 每批次數量 | 50 個 | 避免一次處理太多造成系統負載 | `celery.py` |
| 檢查範圍 | 最近 7 天 | 避免檢查過老的 Build | `celery.py` |
| 優先失敗 Build | True | FAILURE/ABORTED 優先於 SUCCESS | `celery.py` |
| 任務超時 | 4 分鐘 | 避免與下次任務重疊 | `celery.py` |
| SSH 連線超時 | 10 秒 | UART SSH 檢查超時 | `build_config_validator.py` |

---

## 七、注意事項

### 7.1 SSH 連線檢查

UART SSH 檢查會實際連線到 UART PC，需注意：

- **超時設定**：預設 10 秒，避免長時間等待
- **批量執行**：大量 Build 同時檢查可能造成網路負載
- **錯誤處理**：SSH 失敗不應影響其他檢查項目

### 7.2 Ansible Inventory API 快取

配置檢查依賴 Ansible Inventory API：

- **使用快取**：`use_cache=True`
- **快取檔案**：`ansible_inventory.json`
- **快取失效**：需確保快取更新機制正常運作

### 7.3 NAS 存儲

- **目錄權限**：確保 Django 容器有寫入 NAS 的權限
- **磁碟空間**：每個 JSON 約 2-5 KB，數千個 Build 約需 10-50 MB
- **檔案清理**：隨 Build 資料夾一起清理（現有機制）

### 7.4 向後相容

- **無資料庫變更**：不需要執行 migration
- **API 相容**：現有的 `validate_config` API 仍可正常使用
- **漸進式部署**：可先部署後端，再更新前端

---

## 附錄 A：相關檔案清單

| 檔案 | 說明 |
|------|------|
| `backend/api/views/jenkins.py` | Jenkins API ViewSet |
| `backend/api/tasks.py` | Celery 任務定義 |
| `backend/network_toolbox/celery.py` | Celery Beat 排程配置 |
| `backend/network_toolbox/settings.py` | Django 設定（含 NAS 路徑） |
| `library/services/build_config_validator.py` | 配置檢查核心邏輯 |
| `frontend/src/pages/BuildConfigValidatorPage.js` | 前端檢查結果頁面 |

## 附錄 B：類似功能參考

- **Fatal Analysis**：`fatal_analysis.json` - 分析 Console Log 中的 Fatal Error
- **Console Log Storage**：`console.log` - 存儲 Build 的 Console 輸出
- **Artifacts Storage**：`artifacts/` - 存儲 Build 的 Artifacts

---

**文件結束**
