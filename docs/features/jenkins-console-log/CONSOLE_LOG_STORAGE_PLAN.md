# Jenkins Console Log 存儲功能實施計劃

**文檔版本**: v1.0  
**創建日期**: 2025-11-24  
**狀態**: 📋 規劃中（尚未執行）

---

## 📊 現狀分析

### 當前實現狀態

| 功能模組 | 狀態 | 說明 |
|---------|------|------|
| Workspace 存儲 | ✅ 已實現 | `store_workspace()` 正常運作 |
| Artifacts 存儲 | ✅ 已實現 | `store_artifacts()` 正常運作 |
| **Console Log 存儲** | ❌ **未實現** | 資料庫欄位存在但功能缺失 |
| **Config.xml 存儲** | ❌ **未實現** | 資料庫欄位存在但功能缺失 |
| Console Log API 讀取 | ⚠️ 部分實現 | 只能從 Jenkins API 讀取，無法從 NAS 讀取 |

### 資料庫欄位（已存在）

```python
class JenkinsBuild(models.Model):
    # 文件路徑（NAS 上的路徑）
    log_file_path = models.CharField(max_length=1000, blank=True, verbose_name='日誌文件路徑')
    config_file_path = models.CharField(max_length=1000, blank=True, verbose_name='配置文件路徑')
    
    # 已實現的欄位
    workspace_path = models.CharField(...)
    is_workspace_stored = models.BooleanField(...)
    artifacts_path = models.CharField(...)
    is_artifacts_stored = models.BooleanField(...)
```

**問題**：`log_file_path` 和 `config_file_path` 始終為空字串。

---

## 🎯 實施目標

### Phase 1：Console Log 存儲（優先級：高）

**目標**：實現 Console Log 的下載、存儲和讀取功能

**預期效果**：
- ✅ Console Log 自動下載到 NAS
- ✅ 可從 NAS 快速讀取歷史日誌
- ✅ 減少對 Jenkins API 的依賴
- ✅ 支援日誌搜尋和分析

### Phase 2：Config.xml 存儲（優先級：中）

**目標**：實現 Build 配置文件的存儲

**預期效果**：
- ✅ 保留每個 Build 的完整配置
- ✅ 可追溯配置變更歷史

---

## 📋 詳細實施計劃

---

## 🔧 Step 1: 擴展 JenkinsClient

**檔案**: `library/services/jenkins_client.py`

### 1.1 添加 `get_console_log()` 方法

```python
def get_console_log(self, job_name: str, build_number: int) -> str:
    """
    獲取 Build 的 Console Log
    
    Args:
        job_name: Job 名稱
        build_number: Build 編號
        
    Returns:
        str: Console Log 內容
        
    Raises:
        requests.RequestException: 請求失敗
    """
    url = f"{self.base_url}/job/{job_name}/{build_number}/consoleText"
    
    try:
        response = self._make_request('GET', url)
        log_content = response.text
        
        logger.info(
            f"獲取 Console Log 成功: {job_name} #{build_number} "
            f"({len(log_content)} bytes)"
        )
        
        return log_content
        
    except requests.RequestException as e:
        logger.error(
            f"獲取 Console Log 失敗: {job_name} #{build_number} - {e}",
            exc_info=True
        )
        raise
```

### 1.2 添加 `get_build_config()` 方法（可選）

```python
def get_build_config(self, job_name: str, build_number: int) -> str:
    """
    獲取 Build 的 config.xml
    
    Args:
        job_name: Job 名稱
        build_number: Build 編號
        
    Returns:
        str: Config XML 內容
    """
    url = f"{self.base_url}/job/{job_name}/{build_number}/config.xml"
    
    try:
        response = self._make_request('GET', url)
        return response.text
    except requests.RequestException as e:
        logger.error(f"獲取 Config 失敗: {e}")
        raise
```

### 1.3 添加錯誤處理

```python
# 在 _make_request 中添加特殊處理
def _make_request(self, method: str, url: str, **kwargs) -> requests.Response:
    """發送 HTTP 請求（增強版）"""
    try:
        kwargs.setdefault('timeout', self.timeout)
        response = self.session.request(method, url, **kwargs)
        
        # 特殊處理：404 錯誤
        if response.status_code == 404:
            logger.warning(f"資源不存在: {url}")
            raise requests.HTTPError(f"404 Not Found: {url}", response=response)
        
        response.raise_for_status()
        return response
        
    except requests.RequestException as e:
        logger.error(f"Jenkins API 請求失敗: {url}", exc_info=True)
        raise
```

**預估代碼量**: ~60 行  
**預估時間**: 30 分鐘  
**風險**: 低（純新增，不影響現有功能）

---

## 🗄️ Step 2: 擴展 JenkinsStorageService

**檔案**: `library/services/jenkins_storage_service.py`

### 2.1 添加 `store_console_log()` 方法

```python
def store_console_log(
    self,
    log_content: str,
    filename: str = 'console.log'
) -> Dict[str, Any]:
    """
    存儲 Console Log 到 NAS
    
    Args:
        log_content: Console Log 內容
        filename: 檔案名稱（默認：console.log）
        
    Returns:
        dict: {
            'success': bool,
            'log_path': str,
            'log_size': int,
            'error': str (如果失敗)
        }
    """
    try:
        # 確保目錄存在
        self.build_storage_path.mkdir(parents=True, exist_ok=True)
        
        # 構建檔案路徑
        log_path = self.build_storage_path / filename
        
        # 寫入檔案
        logger.info(f"開始存儲 Console Log: {log_path}")
        
        with open(log_path, 'w', encoding='utf-8', errors='replace') as f:
            f.write(log_content)
        
        log_size = len(log_content.encode('utf-8'))
        
        logger.info(
            f"Console Log 存儲成功: {log_path} ({log_size} bytes)"
        )
        
        return {
            'success': True,
            'log_path': str(log_path),
            'log_size': log_size
        }
        
    except Exception as e:
        logger.error(f"存儲 Console Log 失敗: {e}", exc_info=True)
        return {
            'success': False,
            'error': str(e)
        }
```

### 2.2 添加 `store_config_file()` 方法（可選）

```python
def store_config_file(
    self,
    config_content: str,
    filename: str = 'config.xml'
) -> Dict[str, Any]:
    """
    存儲 Config XML 到 NAS
    
    Args:
        config_content: Config XML 內容
        filename: 檔案名稱（默認：config.xml）
        
    Returns:
        dict: 存儲結果
    """
    try:
        self.build_storage_path.mkdir(parents=True, exist_ok=True)
        config_path = self.build_storage_path / filename
        
        with open(config_path, 'w', encoding='utf-8') as f:
            f.write(config_content)
        
        config_size = len(config_content.encode('utf-8'))
        
        logger.info(f"Config 存儲成功: {config_path}")
        
        return {
            'success': True,
            'config_path': str(config_path),
            'config_size': config_size
        }
        
    except Exception as e:
        logger.error(f"存儲 Config 失敗: {e}")
        return {
            'success': False,
            'error': str(e)
        }
```

### 2.3 添加 `read_console_log()` 方法（用於從 NAS 讀取）

```python
def read_console_log(
    self,
    filename: str = 'console.log',
    tail_lines: Optional[int] = None
) -> Dict[str, Any]:
    """
    從 NAS 讀取 Console Log
    
    Args:
        filename: 檔案名稱
        tail_lines: 只返回最後 N 行（可選）
        
    Returns:
        dict: {
            'success': bool,
            'log_content': str,
            'log_size': int,
            'error': str (如果失敗)
        }
    """
    try:
        log_path = self.build_storage_path / filename
        
        if not log_path.exists():
            return {
                'success': False,
                'error': f'Console Log 不存在: {log_path}'
            }
        
        with open(log_path, 'r', encoding='utf-8', errors='replace') as f:
            log_content = f.read()
        
        # 如果指定了 tail_lines
        if tail_lines:
            lines = log_content.split('\n')
            log_content = '\n'.join(lines[-tail_lines:])
        
        return {
            'success': True,
            'log_content': log_content,
            'log_size': len(log_content.encode('utf-8'))
        }
        
    except Exception as e:
        logger.error(f"讀取 Console Log 失敗: {e}")
        return {
            'success': False,
            'error': str(e)
        }
```

**預估代碼量**: ~120 行  
**預估時間**: 45 分鐘  
**風險**: 低（獨立功能，不影響現有代碼）

---

## 🔄 Step 3: 修改 `store_jenkins_build_task`

**檔案**: `backend/api/tasks.py`

### 3.1 整合到現有的存儲流程

**修改位置**: Line 3208 之後（Workspace 存儲成功後）

```python
@shared_task(
    bind=True,
    name='api.tasks.store_jenkins_build_task',
    max_retries=3,
    default_retry_delay=120
)
def store_jenkins_build_task(self, build_id: int) -> Dict[str, Any]:
    """存儲單個 Jenkins Build 到 NAS（增強版）"""
    
    try:
        # ... 現有代碼 ...
        
        # 存儲 Workspace（現有邏輯）
        workspace_result = storage_service.store_workspace(...)
        
        stored_items = []
        total_size = 0
        
        if workspace_result['success']:
            stored_items.append('workspace')
            total_size += workspace_result['workspace_size']
            
            # 更新 Workspace 欄位（現有邏輯）
            build.workspace_path = workspace_result['workspace_path']
            build.workspace_size = workspace_result['workspace_size']
            build.workspace_stored_at = timezone.now()
            build.is_workspace_stored = True
            
            # ===== 🆕 新增：存儲 Console Log =====
            logger.info(f'[Celery] 📝 開始存儲 Console Log - {build.job.name} #{build.build_number}')
            
            try:
                # 從 Jenkins API 獲取 Console Log
                client = JenkinsClient(
                    base_url=server.url,
                    username=server.username,
                    api_token=server.api_token
                )
                
                try:
                    log_content = client.get_console_log(
                        build.job.name,
                        build.build_number
                    )
                    
                    # 存儲到 NAS
                    log_result = storage_service.store_console_log(log_content)
                    
                    if log_result['success']:
                        stored_items.append('console_log')
                        total_size += log_result['log_size']
                        
                        # 更新資料庫
                        build.log_file_path = log_result['log_path']
                        
                        logger.info(
                            f'[Celery] ✅ Console Log 存儲成功 - '
                            f'{log_result["log_size"]} bytes'
                        )
                    else:
                        logger.warning(
                            f'[Celery] ⚠️  Console Log 存儲失敗: '
                            f'{log_result.get("error")}'
                        )
                        
                finally:
                    client.close()
                    
            except Exception as e:
                # Console Log 存儲失敗不影響整體流程
                logger.warning(
                    f'[Celery] ⚠️  Console Log 處理失敗: {e}',
                    exc_info=True
                )
            
            # ===== 🆕 新增：存儲 Config (可選) =====
            # if storage_policy.get('store_config', False):
            #     try:
            #         config_content = client.get_build_config(...)
            #         config_result = storage_service.store_config_file(config_content)
            #         if config_result['success']:
            #             stored_items.append('config')
            #             build.config_file_path = config_result['config_path']
            #     except Exception as e:
            #         logger.warning(f'[Celery] Config 存儲失敗: {e}')
            
            # 保存所有欄位
            build.save(update_fields=[
                'workspace_path', 'workspace_size', 
                'workspace_stored_at', 'is_workspace_stored',
                'log_file_path',  # 🆕 新增
                # 'config_file_path',  # 🆕 新增（如果實現）
            ])
            
            logger.info(
                f'[Celery] ✅ Build 存儲完成 - {build.job.name} #{build.build_number} | '
                f'Items: {stored_items} | Total: {total_size} bytes'
            )
            
            return {
                'success': True,
                'build_id': build_id,
                'job_name': build.job.name,
                'build_number': build.build_number,
                'stored_items': stored_items,  # ['workspace', 'console_log']
                'total_size': total_size
            }
        
        # ... 其餘代碼保持不變 ...
        
    except Exception as exc:
        # ... 錯誤處理邏輯保持不變 ...
        pass
```

### 3.2 關鍵設計決策

**問題 1**: Console Log 下載失敗是否應該中斷整個任務？

**決策**: ❌ **不應該中斷**

**原因**:
- Workspace 是核心資料，Console Log 是輔助資料
- Console Log 可能因為 Jenkins 清理策略而不存在（404）
- Console Log 失敗不影響 Workspace 的存儲價值

**實現方式**:
```python
try:
    # 存儲 Console Log
    ...
except Exception as e:
    # ⚠️  只記錄警告，不拋出異常
    logger.warning(f'Console Log 處理失敗: {e}')
    # 繼續執行後續邏輯
```

---

**問題 2**: 是否需要檢查 Console Log 大小？

**決策**: ❌ **不檢查大小限制**

**原因**:
- Console Log 是重要的調試資訊，不應該因為大小而跳過
- 即使超過 50MB 的日誌，也可能包含關鍵錯誤資訊
- NAS 空間足夠，不需要嚴格限制單個文件大小
- 如果確實需要控制，應該在後續實現壓縮功能，而非跳過存儲

**實現方式**:
```python
# ❌ 不檢查大小，直接下載和存儲
# 所有 Console Log 都會被存儲，無論大小

# 只在日誌中記錄大小資訊
try:
    log_content = client.get_console_log(job_name, build_number)
    log_size_mb = len(log_content) / (1024 * 1024)
    
    if log_size_mb > 50:
        logger.info(
            f'Console Log 較大: {log_size_mb:.2f} MB，正常存儲'
        )
except Exception as e:
    logger.error(f'下載 Console Log 失敗: {e}')
    raise
```

---

**問題 3**: 是否與現有的 `store_jenkins_artifacts_task` 整合？

**決策**: ❌ **不整合**

**原因**:
- `store_jenkins_build_task` 負責 Workspace + Console Log（Build 基本資料）
- `store_jenkins_artifacts_task` 負責 Artifacts（產出物）
- 兩者觸發時機不同，功能獨立

**任務分工**:
```
store_jenkins_build_task:
  ├── Workspace      (現有)
  ├── Console Log    (新增)
  └── Config         (新增，可選)

store_jenkins_artifacts_task:
  └── Artifacts      (現有)
```

**預估代碼量**: ~80 行（新增代碼）  
**預估時間**: 45 分鐘  
**風險**: 中（修改現有任務，需要充分測試）

---

## 🌐 Step 4: 修改 API 視圖

**檔案**: `backend/api/views/jenkins.py`

### 4.1 修改 `console_log` Action

**修改位置**: Line 914-970

```python
@action(detail=True, methods=['get'])
def console_log(self, request, pk=None):
    """
    獲取 Build 的控制台日誌（增強版）
    
    GET /api/jenkins-builds/{id}/console_log/
    
    支援參數：
    - from_nas: 是否從 NAS 讀取（默認 false）
    - tail: 返回最後 N 行（可選）
    - prefer_nas: 優先從 NAS 讀取，失敗則回退到 Jenkins API（默認 false）
    """
    build = self.get_object()
    from_nas = request.query_params.get('from_nas', 'false').lower() == 'true'
    prefer_nas = request.query_params.get('prefer_nas', 'false').lower() == 'true'
    tail_lines = request.query_params.get('tail')
    
    log_content = None
    source = None
    
    try:
        # ===== 🆕 修改：支援從 NAS 讀取 =====
        if from_nas or prefer_nas:
            # 檢查是否有 NAS 路徑
            if build.log_file_path:
                logger.info(f'嘗試從 NAS 讀取 Console Log: {build.log_file_path}')
                
                # 使用 JenkinsStorageService 讀取
                server = build.job.server
                server_ip = server.ip_address if server.ip_address else server.url.split('//')[1].split(':')[0]
                
                storage_service = JenkinsStorageService(
                    jenkins_server_ip=server_ip,
                    job_name=build.job.name,
                    build_number=build.build_number
                )
                
                # 轉換 tail_lines
                tail = int(tail_lines) if tail_lines else None
                
                log_result = storage_service.read_console_log(tail_lines=tail)
                
                if log_result['success']:
                    log_content = log_result['log_content']
                    source = 'nas'
                    logger.info(f'從 NAS 讀取成功: {log_result["log_size"]} bytes')
                else:
                    logger.warning(f'從 NAS 讀取失敗: {log_result.get("error")}')
                    
                    # 如果是 from_nas=true，直接返回錯誤
                    if from_nas:
                        return Response({
                            'success': False,
                            'message': f'從 NAS 讀取失敗: {log_result.get("error")}'
                        }, status=status.HTTP_404_NOT_FOUND)
            else:
                # NAS 路徑不存在
                if from_nas:
                    return Response({
                        'success': False,
                        'message': 'Console Log 尚未存儲到 NAS'
                    }, status=status.HTTP_404_NOT_FOUND)
        
        # ===== 如果 NAS 讀取失敗或未啟用，從 Jenkins API 獲取 =====
        if log_content is None:
            logger.info(f'從 Jenkins API 獲取 Console Log')
            
            client = JenkinsClient(
                base_url=build.job.server.url,
                username=build.job.server.username,
                api_token=build.job.server.api_token
            )
            
            try:
                log_content = client.get_console_log(
                    build.job.name,
                    build.build_number
                )
                source = 'jenkins_api'
                
                # 如果指定了 tail，處理
                if tail_lines:
                    try:
                        tail = int(tail_lines)
                        lines = log_content.split('\n')
                        log_content = '\n'.join(lines[-tail:])
                    except ValueError:
                        pass
                        
            finally:
                client.close()
        
        return Response({
            'success': True,
            'build_id': build.id,
            'job_name': build.job.name,
            'build_number': build.build_number,
            'log_content': log_content,
            'source': source,  # 'nas' 或 'jenkins_api'
            'nas_available': bool(build.log_file_path)  # 是否有 NAS 備份
        })
        
    except Exception as e:
        logger.error(f"獲取 Build 日誌失敗: {e}", exc_info=True)
        return Response({
            'success': False,
            'message': f'獲取日誌失敗: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
```

### 4.2 新增用法範例

```bash
# 1. 從 Jenkins API 讀取（現有行為）
GET /api/jenkins-builds/123/console_log/

# 2. 從 NAS 讀取（新功能）
GET /api/jenkins-builds/123/console_log/?from_nas=true

# 3. 優先從 NAS 讀取，失敗則回退到 API（推薦）
GET /api/jenkins-builds/123/console_log/?prefer_nas=true

# 4. 只返回最後 100 行
GET /api/jenkins-builds/123/console_log/?prefer_nas=true&tail=100
```

**預估代碼量**: ~60 行（修改現有代碼）  
**預估時間**: 30 分鐘  
**風險**: 低（向後兼容，默認行為不變）

---

## ⚙️ Step 5: 更新配置

**檔案**: `backend/network_toolbox/settings.py`

### 5.1 添加 Console Log 配置

```python
# Jenkins 自動存儲策略配置
JENKINS_STORAGE_POLICY = {
    # 基本開關
    'auto_store': True,
    
    # 存儲內容選擇
    'store_workspace': True,
    'store_console_log': True,       # 🆕 新增：存儲 Console Log（默認：是）
    'store_config': False,            # 🆕 修改：存儲 config.xml（默認：否）
    
    # Console Log 特定配置
    # 'max_console_log_size_mb': 50, # ❌ 已移除：不限制大小
    'console_log_encoding': 'utf-8', # 🆕 新增：編碼格式
    
    # 存儲條件過濾
    'store_results': ['SUCCESS', 'FAILURE', 'UNSTABLE', 'ABORTED'],
    
    # 容量限制
    'max_workspace_size_mb': 500,
    'retention_days': 90,
    
    # ... 其他配置保持不變 ...
}
```

**預估代碼量**: ~10 行  
**預估時間**: 5 分鐘  
**風險**: 無

---

## 🧪 Step 6: 測試驗證

### 6.1 單元測試

**新增檔案**: `tests/unit/backend/test_console_log_storage.py`

```python
from django.test import TestCase
from library.services.jenkins_client import JenkinsClient
from library.services.jenkins_storage_service import JenkinsStorageService
from api.models import JenkinsBuild

class ConsoleLogStorageTest(TestCase):
    """Console Log 存儲功能測試"""
    
    def test_get_console_log_from_jenkins(self):
        """測試從 Jenkins API 獲取 Console Log"""
        client = JenkinsClient('http://10.252.170.171:8080')
        log = client.get_console_log('Test-KVM01', 168)
        
        self.assertIsNotNone(log)
        self.assertIsInstance(log, str)
        self.assertGreater(len(log), 0)
    
    def test_store_console_log_to_nas(self):
        """測試存儲 Console Log 到 NAS"""
        service = JenkinsStorageService(
            jenkins_server_ip='10.252.170.171',
            job_name='Test-KVM01',
            build_number=168
        )
        
        test_log = "Build started\nBuild finished\n"
        result = service.store_console_log(test_log)
        
        self.assertTrue(result['success'])
        self.assertIn('log_path', result)
        self.assertGreater(result['log_size'], 0)
    
    def test_read_console_log_from_nas(self):
        """測試從 NAS 讀取 Console Log"""
        service = JenkinsStorageService(
            jenkins_server_ip='10.252.170.171',
            job_name='Test-KVM01',
            build_number=168
        )
        
        # 先存儲
        test_log = "Test log content\n"
        service.store_console_log(test_log)
        
        # 再讀取
        result = service.read_console_log()
        
        self.assertTrue(result['success'])
        self.assertEqual(result['log_content'], test_log)
```

### 6.2 整合測試

**新增檔案**: `tests/integration/test_console_log_workflow.py`

```python
from django.test import TestCase
from api.models import JenkinsBuild, JenkinsJob, JenkinsServer
from api.tasks import store_jenkins_build_task

class ConsoleLogWorkflowTest(TestCase):
    """Console Log 完整流程測試"""
    
    def test_full_storage_workflow(self):
        """測試完整的存儲流程"""
        # 1. 獲取測試 Build
        build = JenkinsBuild.objects.filter(
            job__name='Test-KVM01',
            build_number=168
        ).first()
        
        # 2. 執行存儲任務
        result = store_jenkins_build_task(build.id)
        
        # 3. 驗證結果
        self.assertTrue(result['success'])
        self.assertIn('console_log', result['stored_items'])
        
        # 4. 重新獲取 Build，檢查資料庫
        build.refresh_from_db()
        self.assertIsNotNone(build.log_file_path)
        self.assertTrue(len(build.log_file_path) > 0)
        
        # 5. 測試從 NAS 讀取
        from library.services.jenkins_storage_service import JenkinsStorageService
        
        server_ip = build.job.server.ip_address
        service = JenkinsStorageService(
            jenkins_server_ip=server_ip,
            job_name=build.job.name,
            build_number=build.build_number
        )
        
        read_result = service.read_console_log()
        self.assertTrue(read_result['success'])
        self.assertGreater(len(read_result['log_content']), 0)
```

### 6.3 手動測試清單

```bash
# 1. 測試 JenkinsClient.get_console_log()
docker exec nt-django python manage.py shell -c "
from library.services.jenkins_client import JenkinsClient
client = JenkinsClient('http://10.252.170.171:8080')
log = client.get_console_log('Test-KVM01', 168)
print(f'Log length: {len(log)} bytes')
print(log[:500])  # 顯示前 500 字元
"

# 2. 測試 JenkinsStorageService.store_console_log()
docker exec nt-django python manage.py shell -c "
from library.services.jenkins_storage_service import JenkinsStorageService
service = JenkinsStorageService('10.252.170.171', 'Test-KVM01', 168)
result = service.store_console_log('Test log content')
print(result)
"

# 3. 測試完整流程（新 Build）
docker exec nt-django python manage.py shell -c "
from api.tasks import store_jenkins_build_task
from api.models import JenkinsBuild

# 找一個未存儲的 Build
build = JenkinsBuild.objects.filter(is_workspace_stored=False).first()
if build:
    result = store_jenkins_build_task(build.id)
    print(result)
"

# 4. 測試 API 端點
curl "http://localhost/api/jenkins-builds/123/console_log/?prefer_nas=true"

# 5. 檢查 NAS 檔案
docker exec nt-django ls -lh /mnt/mdt/Team/PQ1-3/tool/jenkins_test_storage/10.252.170.171/Test-KVM01/168/
# 應該看到 console.log
```

**預估測試時間**: 2 小時  
**風險**: 中（需要真實環境測試）

---

## 📊 資源評估

### 存儲空間影響

**單個 Console Log 大小估算**:
- 小型 Build（< 1 分鐘）: ~10-50 KB
- 中型 Build（1-10 分鐘）: ~50-500 KB
- 大型 Build（> 10 分鐘）: ~500 KB - 5 MB
- 超大型 Build（編譯類）: 5-50 MB

**總容量估算**:
```
當前狀態：
- 8 個 Jenkins Servers
- 1,214 個 Jobs
- 平均每個 Job 保留 20 Builds
- 總 Builds: ~24,280

預估 Console Log 總容量：
- 假設平均每個 Log 2 MB
- 24,280 × 2 MB = 48.5 GB

加上現有的 Workspace 和 Artifacts：
- Workspace: 估計 200 GB
- Artifacts: 估計 100 GB
- Console Logs: 48.5 GB
- 總計: ~348.5 GB
```

### 性能影響

**網路流量增加**:
```
現有：
- sync_jenkins_builds: 1,243 API calls / 10 min
- 每個 call 平均 ~10 KB

新增 Console Log 下載：
- 每個 Build +1 次 API call
- 每個 call 平均 ~2 MB（Console Log 大小）

預估增加：
- 假設每次同步平均創建 5 個新 Builds
- 5 × 2 MB = 10 MB / 10 min
- = 1 MB/min = 60 MB/hour

評估：✅ 可接受（網路頻寬足夠）
```

**任務執行時間增加**:
```
現有 store_jenkins_build_task:
- Workspace 下載: 5-30 秒（視大小而定）

新增 Console Log:
- 下載時間: 0.5-5 秒（視大小而定）
- 存儲時間: < 1 秒

總增加時間: 1-6 秒

評估：✅ 影響很小
```

### API 調用頻率

```
現有：
- sync_jenkins_builds: 1,243 calls / 10 min (207 calls/min)

新增：
- get_console_log: 每個新 Build 1 次
- 假設每 10 分鐘創建 5 個新 Builds
- +5 calls / 10 min (+0.5 calls/min)

總計：
- 1,248 calls / 10 min (208 calls/min)

Jenkins Server 負載：
- 每個 Server 平均: 208 / 8 = 26 calls/min
- = 1 call every 2.3 seconds

評估：✅ 遠低於安全閾值（< 100 calls/min per server）
```

---

## 🎯 實施時程規劃

### Phase 1: 基礎功能（2-3 小時）

| 步驟 | 工作項目 | 預估時間 | 依賴 |
|------|---------|---------|------|
| 1.1 | JenkinsClient.get_console_log() | 30 min | 無 |
| 1.2 | JenkinsStorageService.store_console_log() | 30 min | 無 |
| 1.3 | JenkinsStorageService.read_console_log() | 15 min | 1.2 |
| 1.4 | 單元測試（基礎） | 45 min | 1.1, 1.2, 1.3 |
| **小計** | | **2 小時** | |

### Phase 2: Task 整合（1.5-2 小時）

| 步驟 | 工作項目 | 預估時間 | 依賴 |
|------|---------|---------|------|
| 2.1 | 修改 store_jenkins_build_task | 45 min | Phase 1 |
| 2.2 | 更新配置 (settings.py) | 5 min | 無 |
| 2.3 | 錯誤處理和日誌 | 20 min | 2.1 |
| 2.4 | 整合測試 | 30 min | 2.1, 2.2 |
| **小計** | | **1.5-2 小時** | |

### Phase 3: API 視圖（1 小時）

| 步驟 | 工作項目 | 預估時間 | 依賴 |
|------|---------|---------|------|
| 3.1 | 修改 console_log API | 30 min | Phase 1 |
| 3.2 | API 測試 | 20 min | 3.1 |
| 3.3 | 文檔更新 | 10 min | 3.1 |
| **小計** | | **1 小時** | |

### Phase 4: 驗證部署（1-2 小時）

| 步驟 | 工作項目 | 預估時間 | 依賴 |
|------|---------|---------|------|
| 4.1 | 手動測試（單個 Build） | 20 min | Phase 1-3 |
| 4.2 | 整合測試（10 個 Builds） | 30 min | 4.1 |
| 4.3 | 性能測試 | 20 min | 4.2 |
| 4.4 | 錯誤場景測試 | 20 min | 4.2 |
| 4.5 | 文檔更新 | 10 min | 4.1-4.4 |
| **小計** | | **1.5 小時** | |

### **總計**: 5.5-7 小時

---

## 🚨 風險評估與應對

### 風險 1: Console Log 文件過大

**風險等級**: � 低（已調整）

**場景**: 某些 Build 的 Console Log 超過 50MB 甚至 100MB+

**影響**:
- 下載時間較長（可能 30-60 秒）
- 佔用較多 NAS 空間
- 可能接近任務 timeout（540 秒，仍有充足餘量）

**應對措施**:
```python
# ✅ 不設置大小限制，但記錄日誌以便監控
try:
    log_content = client.get_console_log(job_name, build_number)
    log_size_mb = len(log_content) / (1024 * 1024)
    
    logger.info(
        f'Console Log 下載成功: {job_name} #{build_number} '
        f'({log_size_mb:.2f} MB)'
    )
    
    # 如果超過 50MB，記錄警告（但仍然存儲）
    if log_size_mb > 50:
        logger.warning(
            f'Console Log 較大: {log_size_mb:.2f} MB，'
            f'下載時間可能較長'
        )
    
except Exception as e:
    logger.error(f'下載 Console Log 失敗: {e}')
    raise

# 後續可優化：實現壓縮功能
# if log_size_mb > 10:
#     compressed = gzip.compress(log_content.encode('utf-8'))
#     # 存儲為 console.log.gz
```

**監控建議**:
- 定期檢查最大的 Console Log 文件
- 評估是否需要實現壓縮功能
- 監控 NAS 空間使用趨勢

### 風險 2: Jenkins API 返回 404

**風險等級**: 🟢 低

**場景**: Console Log 已被 Jenkins 清理

**影響**: 無法獲取 Console Log

**應對措施**:
```python
try:
    log_content = client.get_console_log(job_name, build_number)
except requests.HTTPError as e:
    if e.response.status_code == 404:
        logger.info(f'Console Log 不存在（可能已被清理）')
        return {
            'success': False,
            'skipped': True,
            'reason': 'log_not_found'
        }
    raise
```

### 風險 3: NAS 空間不足

**風險等級**: 🟡 中

**場景**: NAS 空間接近滿載

**影響**: 無法寫入新文件

**應對措施**:
```python
def check_nas_space() -> bool:
    """檢查 NAS 剩餘空間"""
    import shutil
    
    stat = shutil.disk_usage(settings.JENKINS_STORAGE_BASE_PATH)
    free_gb = stat.free / (1024 ** 3)
    
    MIN_FREE_SPACE_GB = 50  # 最低保留 50GB
    
    if free_gb < MIN_FREE_SPACE_GB:
        logger.error(f'NAS 空間不足: 剩餘 {free_gb:.2f} GB')
        return False
    
    return True

# 在存儲前檢查
if not check_nas_space():
    raise Exception('NAS 空間不足，暫停存儲任務')
```

### 風險 4: 編碼問題

**風險等級**: 🟡 中

**場景**: Console Log 包含非 UTF-8 字元

**影響**: 讀寫文件時拋出異常

**應對措施**:
```python
# 寫入時使用 errors='replace'
with open(log_path, 'w', encoding='utf-8', errors='replace') as f:
    f.write(log_content)

# 讀取時同樣處理
with open(log_path, 'r', encoding='utf-8', errors='replace') as f:
    log_content = f.read()
```

### 風險 5: 向後兼容性

**風險等級**: 🟢 低

**場景**: 舊的 Builds 沒有 Console Log

**影響**: 前端需要判斷是否有 NAS 備份

**應對措施**:
```python
# API 返回時添加標記
return Response({
    'success': True,
    'log_content': log_content,
    'source': source,
    'nas_available': bool(build.log_file_path),  # 🆕 新增欄位
})

# 前端可以根據此欄位決定是否顯示「查看 NAS 日誌」按鈕
```

---

## 📈 監控指標

實施後需要監控的關鍵指標：

### 1. 存儲成功率

```python
# 在 task 結果中記錄
{
    'console_log_stored': True/False,
    'console_log_size': 12345,
    'console_log_error': 'error_message'
}

# 統計查詢
JenkinsBuild.objects.filter(
    log_file_path__isnull=False
).count() / JenkinsBuild.objects.count()
```

### 2. NAS 空間使用

```bash
# 每日監控腳本
du -sh /mnt/mdt/Team/PQ1-3/tool/jenkins_test_storage/

# 按 Server 統計
for server in $(ls /mnt/mdt/Team/PQ1-3/tool/jenkins_test_storage/); do
    echo "$server: $(du -sh /mnt/mdt/Team/PQ1-3/tool/jenkins_test_storage/$server)"
done
```

### 3. API 調用頻率

```python
# 在 Celery Task 日誌中記錄
logger.info(
    f'[Celery] Console Log 下載統計: '
    f'成功: {success_count}, 失敗: {failed_count}, 跳過: {skipped_count}'
)
```

### 4. 平均文件大小

```python
# 統計查詢
from django.db.models import Avg, Sum
from api.models import JenkinsBuild

# 注意：需要添加 log_size 欄位到模型
stats = JenkinsBuild.objects.filter(
    log_file_path__isnull=False
).aggregate(
    avg_size=Avg('log_size'),
    total_size=Sum('log_size'),
    count=Count('id')
)
```

---

## ✅ 驗收標準

### 功能驗收

- [ ] ✅ `JenkinsClient.get_console_log()` 可正常獲取日誌
- [ ] ✅ `JenkinsStorageService.store_console_log()` 可正常存儲
- [ ] ✅ `JenkinsStorageService.read_console_log()` 可正常讀取
- [ ] ✅ `store_jenkins_build_task` 會自動存儲 Console Log
- [ ] ✅ API `/console_log/` 支援 `from_nas` 和 `prefer_nas` 參數
- [ ] ✅ 資料庫 `log_file_path` 欄位正確更新
- [ ] ✅ NAS 檔案結構正確（`console.log` 與 `workspace/` 同層）

### 性能驗收

- [ ] ✅ 單個 Build 存儲時間 < 60 秒
- [ ] ✅ Console Log 下載時間 < 10 秒（< 10MB 文件）
- [ ] ✅ 從 NAS 讀取時間 < 2 秒
- [ ] ✅ 不影響現有 Workspace 存儲功能
- [ ] ✅ 錯誤場景不影響整體任務成功

### 穩定性驗收

- [ ] ✅ Console Log 不存在（404）時正常處理
- [ ] ✅ Console Log 超大文件（>100MB）正常存儲
- [ ] ✅ NAS 空間不足時正常報錯
- [ ] ✅ 編碼錯誤時正常處理（errors='replace'）
- [ ] ✅ 連續 100 個 Builds 存儲無報錯

### 向後兼容性驗收

- [ ] ✅ 現有 Builds（無 log_file_path）仍可正常使用
- [ ] ✅ API 默認行為不變（仍從 Jenkins API 獲取）
- [ ] ✅ 現有 Celery Tasks 不受影響
- [ ] ✅ 資料庫遷移順利（無數據丟失）

---

## 📚 後續優化方向

### Phase 2: Config.xml 存儲

- [ ] 實現 `get_build_config()` 方法
- [ ] 實現 `store_config_file()` 方法
- [ ] 整合到 `store_jenkins_build_task`
- [ ] 更新 API 視圖

### Phase 3: 日誌分析功能

- [ ] Console Log 關鍵字搜尋
- [ ] 錯誤自動提取和分類
- [ ] 統計報表（失敗原因 Top 10）
- [ ] 日誌對比功能

### Phase 4: 壓縮優化

- [ ] 大文件自動壓縮（> 10MB）
- [ ] 讀取時自動解壓
- [ ] 節省 NAS 空間

---

## 📝 文檔更新

需要更新的文檔：

1. **API 文檔** (`docs/api/JENKINS_API.md`)
   - 更新 `/console_log/` 端點說明
   - 添加 `from_nas` 和 `prefer_nas` 參數說明

2. **開發文檔** (`docs/development/JENKINS_STORAGE.md`)
   - 添加 Console Log 存儲架構說明
   - 添加存儲流程圖

3. **部署文檔** (`docs/deployment/CONFIGURATION.md`)
   - 添加 `JENKINS_STORAGE_POLICY` 配置說明
   - 添加 NAS 空間需求說明

4. **故障排查** (`docs/troubleshooting/JENKINS_ISSUES.md`)
   - 添加 Console Log 相關問題排查

---

## 🎓 總結

### 核心設計原則

1. **非侵入性**: 不破壞現有功能，向後兼容
2. **容錯性**: Console Log 失敗不影響 Workspace 存儲
3. **可配置性**: 通過 `JENKINS_STORAGE_POLICY` 靈活控制
4. **性能優先**: 優先從 NAS 讀取，減少 Jenkins 負載
5. **監控友好**: 完善的日誌和統計指標

### 預期收益

- ✅ **減少 Jenkins API 壓力**: 歷史日誌從 NAS 讀取
- ✅ **提升查詢速度**: NAS 讀取速度 > API 讀取
- ✅ **數據完整性**: 即使 Jenkins 清理，NAS 仍保留
- ✅ **支援離線分析**: 日誌可批量導出分析
- ✅ **空間利用合理**: 平均每個 Build +2MB，可接受

### 實施建議

1. **分階段實施**: 先完成 Phase 1，驗證無誤後再進行 Phase 2-3
2. **小範圍測試**: 先在單個 Server 上測試
3. **監控指標**: 密切觀察 NAS 空間和 API 調用頻率
4. **文檔先行**: 先完善文檔，確保團隊理解

---

**狀態**: 📋 規劃完成，等待批准實施

**預估總工時**: 5.5-7 小時  
**預估完成日期**: 實施批准後 1-2 個工作日

**最後更新**: 2025-11-24
