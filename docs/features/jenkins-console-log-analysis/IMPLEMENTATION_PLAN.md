# Jenkins Console Log Fatal Error 分析功能 - 實作計畫

> **文檔版本**: 2.0  
> **創建日期**: 2025-11-27  
> **最後更新**: 2025-11-27  
> **狀態**: Phase 1 & 2 已完成 ✅ | Phase 3 & 4 可選 ⏸️

---

## 📋 目錄

- [功能概述](#功能概述)
- [現有機制分析](#現有機制分析)
- [整合方案設計](#整合方案設計)
- [技術實現規劃](#技術實現規劃)
- [數據結構設計](#數據結構設計)
- [實施步驟](#實施步驟)
- [測試計畫](#測試計畫)

---

## 🎯 功能概述

### 核心需求

從已存儲的 Jenkins Console Log 中自動提取包含 "fatal" 關鍵字的 Ansible Task 範圍，並將結果保存為 JSON 文件到 NAS。

### 關鍵特性

1. **自動觸發**：僅當 Jenkins Build 狀態為 `FAILURE` 時才執行分析
2. **智能整合**：與現有的 Console Log 下載流程無縫整合
3. **精準定位**：自動識別 fatal 錯誤所屬的完整 Ansible Task 範圍
4. **結構化存儲**：分析結果以 JSON 格式存儲到 NAS 對應目錄

---

## 🔍 現有機制分析

### 1. Console Log 下載流程

**主要任務**: `store_jenkins_build_task`（位於 `backend/api/tasks.py`）

#### 執行流程

```
store_jenkins_build_task (單個 Build 存儲任務)
│
├─ 1️⃣ 獲取 Build 記錄（JenkinsBuild 模型）
├─ 2️⃣ 檢查是否已存儲（workspace + console log）
├─ 3️⃣ 檢查 Build 狀態（跳過正在構建中的）
├─ 4️⃣ 初始化 JenkinsStorageService
├─ 5️⃣ 存儲 Workspace（如果未存儲）
│
├─ 6️⃣ 存儲 Console Log（核心部分）
│   ├─ 透過 JenkinsClient.get_console_log() 獲取日誌內容
│   ├─ 透過 JenkinsStorageService.store_console_log() 存儲到 NAS
│   └─ 更新 JenkinsBuild.log_file_path
│
└─ 7️⃣ 保存 Build 記錄到資料庫
```

#### 關鍵代碼位置

**文件**: `backend/api/tasks.py`  
**行號**: Line 3100-3334（`store_jenkins_build_task` 函數）  
**Console Log 處理**: Line 3235-3292

```python
# 現有代碼片段（Line 3235-3261）
logger.info(f'[Celery] 📝 開始存儲 Console Log - {build.job.name} #{build.build_number}')

try:
    from library.services.jenkins_client import JenkinsClient
    
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
                f'{log_result["log_size"] / (1024**2):.2f} MB'
            )
            
            # 🎯 整合點：在這裡添加 Fatal Error 分析邏輯
            
        else:
            logger.warning(...)
```

### 2. 觸發時機分析

**主要觸發方式**：

1. **自動掃描**：`auto_store_jenkins_builds_task` 定時任務
   - 每 X 分鐘掃描未存儲的 Builds
   - 過濾條件：`is_workspace_stored=False`, `is_building=False`
   - 可配置只存儲特定結果（SUCCESS, FAILURE, UNSTABLE）

2. **手動觸發**：透過 API 端點手動存儲特定 Build

### 3. Build 狀態判斷

**Build.result 欄位的可能值**：
- `SUCCESS` - 成功
- `FAILURE` - 失敗 ⭐（需要分析的情況）
- `UNSTABLE` - 不穩定
- `ABORTED` - 中止
- `NOT_BUILT` - 未構建
- `BUILDING` - 構建中

**現有的 FAILURE 處理**（Line 1931-1962, 2004-2028）：
```python
# 當檢測到 FAILURE 時，會獲取 Pipeline Stages
if result == 'FAILURE':
    from django.core.cache import cache
    
    cache_key = f'failed_stages:{job.id}:{build_number}'
    failed_stages = cache.get(cache_key)
    
    if not failed_stages:
        try:
            failed_stages = client.get_failed_stages(job.name, build_number)
            if failed_stages:
                cache.set(cache_key, failed_stages, timeout=86400)
        except Exception as e:
            logger.error(...)
    
    if failed_stages:
        build.pipeline_stages = failed_stages
        build.failed_stage = first_failed.get('stage_name')
        build.save(update_fields=['pipeline_stages', 'failed_stage'])
```

---

## 🔗 整合方案設計

### 方案：在 Console Log 存儲成功後立即觸發分析

**優點**：
✅ 與現有流程無縫整合  
✅ 避免重複讀取 Console Log（內容已在記憶體中）  
✅ 失敗狀態判斷簡單明確（`build.result == 'FAILURE'`）  
✅ 單一任務完成所有操作（下載 → 分析 → 存儲）  

**整合位置**：
- **文件**：`backend/api/tasks.py`
- **函數**：`store_jenkins_build_task`
- **行號**：Line 3261 之後（Console Log 存儲成功的判斷區塊內）

**整合邏輯**：
```python
# 在 Console Log 存儲成功後
if log_result['success']:
    stored_items.append('console_log')
    total_size += log_result['log_size']
    build.log_file_path = log_result['log_path']
    
    logger.info(...)
    
    # ===== 🎯 新增：Fatal Error 分析（僅針對 FAILURE 狀態） =====
    if build.result == 'FAILURE':
        logger.info(
            f'[Celery] 🔍 開始分析 Console Log Fatal Errors - '
            f'{build.job.name} #{build.build_number}'
        )
        
        try:
            from library.utils.console_log_analyzer import ConsoleLogAnalyzer
            
            # 初始化分析器（直接使用已下載的 log_content）
            analyzer = ConsoleLogAnalyzer(
                log_content=log_content,  # 重用已下載的內容
                jenkins_server=server_ip,
                job_name=build.job.name,
                build_number=build.build_number
            )
            
            # 執行分析
            analysis_result = analyzer.analyze_fatal_errors()
            
            if analysis_result['success']:
                # 保存分析結果到 NAS（與 console.log 同一目錄）
                json_path = analyzer.save_analysis_to_json(
                    output_dir=str(storage_service.build_storage_path)
                )
                
                # 更新資料庫（如果擴展了模型）
                build.console_log_analyzed = True
                build.fatal_errors_count = analysis_result['summary']['total_fatal_tasks']
                build.analysis_file_path = json_path
                build.analyzed_at = timezone.now()
                
                logger.info(
                    f'[Celery] ✅ Fatal Error 分析完成 - '
                    f'找到 {analysis_result["summary"]["total_fatal_tasks"]} 個 Fatal Tasks | '
                    f'結果已存儲: {json_path}'
                )
            else:
                logger.warning(
                    f'[Celery] ⚠️  Fatal Error 分析失敗: '
                    f'{analysis_result.get("error")}'
                )
                
        except Exception as e:
            # 分析失敗不影響整體流程
            logger.error(
                f'[Celery] ❌ Console Log 分析失敗: {e}',
                exc_info=True
            )
    else:
        logger.debug(
            f'[Celery] ℹ️  Build 狀態為 {build.result}，跳過 Fatal Error 分析'
        )
```

---

## 🛠️ 技術實現規劃

### 1. 創建核心分析模組

**位置**：`backend/library/utils/console_log_analyzer.py`

**類別設計**：`ConsoleLogAnalyzer`

#### 初始化方法

```python
class ConsoleLogAnalyzer:
    """Jenkins Console Log Fatal Error 分析器"""
    
    def __init__(
        self,
        log_content: Optional[str] = None,
        log_file_path: Optional[str] = None,
        jenkins_server: str = '',
        job_name: str = '',
        build_number: int = 0
    ):
        """
        初始化分析器
        
        Args:
            log_content: Console Log 內容（優先使用）
            log_file_path: Console Log 文件路徑（備選）
            jenkins_server: Jenkins 伺服器 IP
            job_name: Job 名稱
            build_number: Build 編號
        """
        self.jenkins_server = jenkins_server
        self.job_name = job_name
        self.build_number = build_number
        
        # 讀取 log 內容
        if log_content:
            self.log_lines = log_content.split('\n')
        elif log_file_path and Path(log_file_path).exists():
            with open(log_file_path, 'r', encoding='utf-8', errors='replace') as f:
                self.log_lines = f.readlines()
        else:
            raise ValueError('必須提供 log_content 或有效的 log_file_path')
        
        self.total_lines = len(self.log_lines)
        logger.info(f'Console Log 已載入: {self.total_lines} 行')
```

#### 核心方法

**1. `analyze_fatal_errors()` - 主要分析方法**
```python
def analyze_fatal_errors(self) -> Dict[str, Any]:
    """
    分析 Console Log，提取所有包含 fatal 的 Task
    
    Returns:
        dict: {
            'success': bool,
            'build_info': {...},
            'summary': {
                'total_fatal_tasks': int,
                'total_log_lines': int,
                'fatal_keywords_found': int
            },
            'fatal_tasks': [...]
        }
    """
```

**2. `find_fatal_lines()` - 查找 fatal 關鍵字**
```python
def find_fatal_lines(self) -> List[int]:
    """
    查找所有包含 'fatal' 的行號（不區分大小寫）
    
    Returns:
        List[int]: 包含 fatal 的行號列表
    """
```

**3. `extract_task_block()` - 提取 Task 完整範圍**
```python
def extract_task_block(self, fatal_line: int) -> Optional[Dict[str, Any]]:
    """
    根據 fatal 行號，提取完整的 Task 區塊
    
    Args:
        fatal_line: 包含 fatal 的行號
        
    Returns:
        dict: {
            'task_name': str,
            'task_start_time': str,
            'task_start_line': int,
            'task_end_line': int,
            'fatal_line_numbers': List[int],
            'task_content': str,
            'fatal_snippets': [...]
        }
    """
```

**4. `find_task_boundary()` - 查找 Task 邊界**
```python
def find_task_boundary(self, start_from: int, direction: str = 'up') -> Optional[int]:
    """
    從指定行號開始，向上或向下查找 TASK 標記
    
    Args:
        start_from: 起始行號
        direction: 'up' 或 'down'
        
    Returns:
        int: Task 標記的行號，找不到則返回 None
    """
```

**5. `parse_task_header()` - 解析 Task 標題**
```python
def parse_task_header(self, line: str) -> Dict[str, str]:
    """
    解析 TASK 標記行，提取時間和 Task 名稱
    
    範例輸入:
        "13:20:22  TASK [test : Validate test case STC-551] *******"
    
    Returns:
        dict: {
            'timestamp': '13:20:22',
            'task_name': 'test : Validate test case STC-551'
        }
    """
```

**6. `save_analysis_to_json()` - 保存分析結果**
```python
def save_analysis_to_json(self, output_dir: str) -> str:
    """
    保存分析結果為 JSON 文件
    
    Args:
        output_dir: 輸出目錄路徑
        
    Returns:
        str: JSON 文件完整路徑
    """
```

### 2. 正則表達式模式

```python
import re

class ConsoleLogAnalyzer:
    # Ansible Task 標記（起點）
    # 範例: "13:20:22  TASK [test : Validate test case STC-551] *******"
    TASK_HEADER_PATTERN = re.compile(
        r'^(\d{2}:\d{2}:\d{2})\s+TASK\s+\[(.*?)\]\s+\*+',
        re.IGNORECASE
    )
    
    # Fatal 關鍵字（不區分大小寫）
    FATAL_PATTERN = re.compile(r'\bfatal\b', re.IGNORECASE)
    
    # 時間戳提取（用於其他行）
    TIMESTAMP_PATTERN = re.compile(r'^(\d{2}:\d{2}:\d{2})')
```

### 3. 演算法流程

```
1. 載入 Console Log（from memory or file）
   └─ 分割為行陣列（self.log_lines）

2. 掃描所有行，找到包含 "fatal" 的行號
   └─ 使用正則 FATAL_PATTERN.search(line)
   └─ 記錄所有 fatal_lines: [1245, 1246, ...]

3. 對每個 fatal_line 提取對應的 Task Block
   ├─ 3a. 向上搜索最近的 TASK [...] 標記（task_start）
   │     └─ 從 fatal_line-1 開始向上，直到找到或到達檔案開頭
   │
   ├─ 3b. 向下搜索下一個 TASK [...] 標記（task_end）
   │     └─ 從 fatal_line+1 開始向下，直到找到或到達檔案結尾
   │
   ├─ 3c. 提取 task_start 到 task_end 之間的所有行
   │     └─ task_content = '\n'.join(log_lines[task_start:task_end])
   │
   ├─ 3d. 解析 Task 名稱和時間戳
   │     └─ 使用 TASK_HEADER_PATTERN.match(log_lines[task_start])
   │
   └─ 3e. 提取 fatal 行的上下文（前後各 3 行）

4. 去重相同的 Task（同一個 Task 可能有多個 fatal）
   └─ 使用 task_start_line 作為唯一 key
   └─ 合併同一 Task 的所有 fatal_line_numbers

5. 組織數據結構
   └─ build_info + summary + fatal_tasks[]

6. 保存為 JSON 文件
   └─ 文件名: console_log_analysis.json
   └─ 路徑: {NAS_PATH}/{server_ip}/{job_name}/{build_number}/
```

---

## 📊 數據結構設計

### 分析結果 JSON 格式

**文件名**：`console_log_analysis.json`

**路徑範例**：
```
\\10.250.0.1\mdt\Team\PQ1-3\tool\jenkins_test_storage\
  └── 10.252.170.171/
      └── Test-KVM01/
          └── 166/
              ├── console.log
              ├── console_log_analysis.json  ← 新增
              └── workspace/
```

**JSON 結構**：
```json
{
  "build_info": {
    "jenkins_server": "10.252.170.171",
    "job_name": "Test-KVM01",
    "build_number": 166,
    "log_path": "\\\\10.250.0.1\\mdt\\Team\\PQ1-3\\tool\\jenkins_test_storage\\10.252.170.171\\Test-KVM01\\166\\console.log",
    "analyzed_at": "2025-11-27T10:30:15.123456"
  },
  
  "summary": {
    "total_fatal_tasks": 2,
    "total_log_lines": 15234,
    "fatal_keywords_found": 5,
    "analysis_duration_ms": 234
  },
  
  "fatal_tasks": [
    {
      "task_index": 1,
      "task_name": "test : Validate test case STC-551",
      "task_start_time": "13:20:22",
      "task_start_line": 1234,
      "task_end_line": 1256,
      "task_total_lines": 22,
      "fatal_line_numbers": [1245, 1246],
      "fatal_count": 2,
      
      "task_content": "13:20:22  TASK [test : Validate test case STC-551] ***************************************\n13:20:22  task path: /workspace/playbooks/validate.yml:45\n...\n13:20:22  fatal: [Test-KVM01]: FAILED! => {\n13:20:22      \"assertion\": \"test_status in ['PASS', 'CONDITIONAL_PASS', 'CHECK']\",\n13:20:22      \"changed\": false,\n13:20:22      \"evaluated_to\": false,\n13:20:22      \"msg\": \"No explicit error message from test logic\"\n13:20:22  }\n...",
      
      "fatal_snippets": [
        {
          "line_number": 1245,
          "content": "13:20:22  fatal: [Test-KVM01]: FAILED! => {",
          "context_before": [
            "13:20:21  ok: [Test-KVM01] => {",
            "13:20:22      \"msg\": \"Executing test case STC-551\"",
            "13:20:22  }"
          ],
          "context_after": [
            "13:20:22      \"assertion\": \"test_status in ['PASS', 'CONDITIONAL_PASS', 'CHECK']\",",
            "13:20:22      \"changed\": false,",
            "13:20:22      \"evaluated_to\": false"
          ]
        },
        {
          "line_number": 1246,
          "content": "13:20:22  fatal: [backup-node]: FAILED! => {...}",
          "context_before": [...],
          "context_after": [...]
        }
      ]
    },
    {
      "task_index": 2,
      "task_name": "test : Another failed task",
      "task_start_time": "13:25:10",
      "task_start_line": 2100,
      "task_end_line": 2145,
      "task_total_lines": 45,
      "fatal_line_numbers": [2120, 2122, 2125],
      "fatal_count": 3,
      "task_content": "...",
      "fatal_snippets": [...]
    }
  ]
}
```

### 數據庫模型擴展（可選）

**位置**：`backend/api/models.py`

**在 `JenkinsBuild` 模型添加欄位**：
```python
class JenkinsBuild(models.Model):
    # ... 現有欄位 ...
    
    # ===== Console Log 分析相關欄位 =====
    console_log_analyzed = models.BooleanField(
        default=False, 
        verbose_name='Console Log 是否已分析'
    )
    fatal_errors_count = models.IntegerField(
        default=0, 
        verbose_name='Fatal 錯誤 Task 數量'
    )
    analysis_file_path = models.CharField(
        max_length=1000, 
        blank=True, 
        verbose_name='分析結果 JSON 路徑'
    )
    analyzed_at = models.DateTimeField(
        null=True, 
        blank=True, 
        verbose_name='Console Log 分析時間'
    )
```

**Migration 命令**：
```bash
python manage.py makemigrations api
python manage.py migrate api
```

---

## 📝 實施步驟

### Phase 1: 核心分析模組開發 ✅

**目標**：創建獨立、可測試的分析工具

**步驟**：

1. **創建分析器模組**
   - [x] 創建文件：`backend/library/utils/console_log_analyzer.py`
   - [x] 實現 `ConsoleLogAnalyzer` 類
   - [x] 實現所有核心方法（6 個）

2. **編寫單元測試**
   - [x] 創建測試文件：`tests/unit/backend/test_console_log_analyzer.py`
   - [x] 準備測試用 Console Log 範例（包含 fatal）
   - [x] 測試各個方法的功能
   - [x] 邊界情況測試（無 fatal、多個 fatal、文件開頭/結尾）

3. **測試驗證**
   ```bash
   # 執行單元測試
   python manage.py test tests.unit.backend.test_console_log_analyzer
   
   # 使用真實 Console Log 測試
   python backend/library/utils/console_log_analyzer.py \
       --log-file /path/to/console.log \
       --output-dir /tmp/test_output
   ```

**產出**：
- ✅ `backend/library/utils/console_log_analyzer.py`
- ✅ `tests/unit/backend/test_console_log_analyzer.py`
- ✅ 測試通過報告

---

### Phase 2: 整合到 Celery Task ✅

**目標**：將分析功能整合到現有的 Console Log 下載流程

**步驟**：

1. **（可選）擴展數據庫模型**
   ```python
   # backend/api/models.py
   # 在 JenkinsBuild 模型添加分析相關欄位
   console_log_analyzed = models.BooleanField(default=False)
   fatal_errors_count = models.IntegerField(default=0)
   analysis_file_path = models.CharField(max_length=1000, blank=True)
   analyzed_at = models.DateTimeField(null=True, blank=True)
   ```

2. **執行 Migration**（如果擴展了模型）
   ```bash
   cd backend
   python manage.py makemigrations api
   python manage.py migrate api
   ```

3. **修改 `store_jenkins_build_task`**
   - 位置：`backend/api/tasks.py`, Line 3261 之後
   - 添加條件判斷：`if build.result == 'FAILURE':`
   - 調用分析器並保存結果
   - 更新資料庫欄位

4. **測試整合**
   ```bash
   # 觸發一個失敗的 Build 存儲任務
   python manage.py shell
   >>> from api.tasks import store_jenkins_build_task
   >>> from api.models import JenkinsBuild
   >>> build = JenkinsBuild.objects.filter(result='FAILURE').first()
   >>> result = store_jenkins_build_task(build.id)
   ```

**產出**：
- ✅ 修改後的 `backend/api/tasks.py`
- ✅ Migration 文件（如果有）
- ✅ 整合測試通過

---

### Phase 3: API 端點和前端展示（可選）

**目標**：提供 UI 查看分析結果

**步驟**：

1. **創建 API 端點**
   ```python
   # backend/api/views/jenkins.py
   
   @action(detail=True, methods=['get'])
   def console_log_analysis(self, request, pk=None):
       """
       獲取 Console Log 分析結果
       
       GET /api/jenkins/builds/{id}/console-log-analysis/
       """
       build = self.get_object()
       
       if not build.console_log_analyzed:
           return Response({
               'analyzed': False,
               'message': 'Console Log 尚未分析'
           })
       
       # 讀取 JSON 文件
       if build.analysis_file_path and Path(build.analysis_file_path).exists():
           with open(build.analysis_file_path, 'r') as f:
               analysis_data = json.load(f)
           
           return Response({
               'analyzed': True,
               'data': analysis_data
           })
       else:
           return Response({
               'analyzed': True,
               'error': '分析文件不存在'
           }, status=404)
   
   @action(detail=True, methods=['post'])
   def trigger_console_log_analysis(self, request, pk=None):
       """
       手動觸發 Console Log 分析
       
       POST /api/jenkins/builds/{id}/trigger-console-log-analysis/
       """
       build = self.get_object()
       
       if build.result != 'FAILURE':
           return Response({
               'success': False,
               'message': '只能分析失敗的 Build'
           }, status=400)
       
       if not build.log_file_path:
           return Response({
               'success': False,
               'message': 'Console Log 文件不存在'
           }, status=404)
       
       # 執行分析
       try:
           from library.utils.console_log_analyzer import ConsoleLogAnalyzer
           
           analyzer = ConsoleLogAnalyzer(
               log_file_path=build.log_file_path,
               jenkins_server=build.job.server.ip_address,
               job_name=build.job.name,
               build_number=build.build_number
           )
           
           result = analyzer.analyze_fatal_errors()
           
           if result['success']:
               json_path = analyzer.save_analysis_to_json(
                   output_dir=str(Path(build.log_file_path).parent)
               )
               
               # 更新資料庫
               build.console_log_analyzed = True
               build.fatal_errors_count = result['summary']['total_fatal_tasks']
               build.analysis_file_path = json_path
               build.analyzed_at = timezone.now()
               build.save()
               
               return Response({
                   'success': True,
                   'fatal_tasks_count': result['summary']['total_fatal_tasks'],
                   'analysis_file': json_path
               })
           else:
               return Response({
                   'success': False,
                   'error': result.get('error')
               }, status=500)
               
       except Exception as e:
           return Response({
               'success': False,
               'error': str(e)
           }, status=500)
   ```

2. **前端頁面展示**
   - 在 Jenkins Build 詳情頁面添加「Fatal Errors」Tab
   - 顯示 fatal_tasks 列表
   - 提供 Task 內容查看（折疊/展開）
   - 高亮顯示 fatal 關鍵字

3. **前端組件範例**
   ```javascript
   // frontend/src/components/JenkinsBuild/FatalErrorsTab.js
   
   import React, { useState, useEffect } from 'react';
   import { Card, Table, Tag, Collapse, Button, message } from 'antd';
   import { WarningOutlined, ReloadOutlined } from '@ant-design/icons';
   import axios from 'axios';
   
   const FatalErrorsTab = ({ buildId }) => {
       const [loading, setLoading] = useState(false);
       const [analyzed, setAnalyzed] = useState(false);
       const [analysisData, setAnalysisData] = useState(null);
       
       const fetchAnalysis = async () => {
           setLoading(true);
           try {
               const response = await axios.get(
                   `/api/jenkins/builds/${buildId}/console-log-analysis/`
               );
               
               if (response.data.analyzed) {
                   setAnalyzed(true);
                   setAnalysisData(response.data.data);
               }
           } catch (error) {
               message.error('載入分析結果失敗');
           } finally {
               setLoading(false);
           }
       };
       
       const triggerAnalysis = async () => {
           setLoading(true);
           try {
               const response = await axios.post(
                   `/api/jenkins/builds/${buildId}/trigger-console-log-analysis/`
               );
               
               if (response.data.success) {
                   message.success('分析完成！');
                   fetchAnalysis();
               }
           } catch (error) {
               message.error('分析失敗：' + error.message);
           } finally {
               setLoading(false);
           }
       };
       
       useEffect(() => {
           fetchAnalysis();
       }, [buildId]);
       
       if (!analyzed) {
           return (
               <Card>
                   <p>Console Log 尚未分析</p>
                   <Button 
                       type="primary" 
                       icon={<ReloadOutlined />}
                       onClick={triggerAnalysis}
                       loading={loading}
                   >
                       立即分析
                   </Button>
               </Card>
           );
       }
       
       const columns = [
           {
               title: 'Task #',
               dataIndex: 'task_index',
               width: 80,
           },
           {
               title: 'Task 名稱',
               dataIndex: 'task_name',
               ellipsis: true,
           },
           {
               title: '時間',
               dataIndex: 'task_start_time',
               width: 100,
           },
           {
               title: 'Fatal 數量',
               dataIndex: 'fatal_count',
               width: 100,
               render: (count) => (
                   <Tag color="red" icon={<WarningOutlined />}>
                       {count}
                   </Tag>
               )
           },
           {
               title: '行範圍',
               key: 'line_range',
               width: 120,
               render: (_, record) => (
                   `${record.task_start_line}-${record.task_end_line}`
               )
           }
       ];
       
       return (
           <div>
               <Card 
                   title={`Fatal Errors 分析 (${analysisData?.summary.total_fatal_tasks} 個)`}
                   extra={
                       <Button 
                           icon={<ReloadOutlined />}
                           onClick={fetchAnalysis}
                           loading={loading}
                       >
                           重新載入
                       </Button>
                   }
               >
                   <Table
                       columns={columns}
                       dataSource={analysisData?.fatal_tasks}
                       rowKey="task_index"
                       pagination={false}
                       expandable={{
                           expandedRowRender: (record) => (
                               <pre style={{ 
                                   backgroundColor: '#f5f5f5',
                                   padding: '16px',
                                   borderRadius: '4px',
                                   overflow: 'auto',
                                   maxHeight: '400px'
                               }}>
                                   {record.task_content}
                               </pre>
                           )
                       }}
                   />
               </Card>
           </div>
       );
   };
   
   export default FatalErrorsTab;
   ```

**產出**：
- ✅ API 端點實現
- ✅ 前端組件實現
- ✅ UI/UX 測試通過

---

### Phase 4: 批量處理和管理命令（可選）

**目標**：批量分析歷史 Console Logs

**步驟**：

1. **創建 Management Command**
   ```python
   # backend/api/management/commands/analyze_console_logs.py
   
   from django.core.management.base import BaseCommand
   from api.models import JenkinsBuild
   from library.utils.console_log_analyzer import ConsoleLogAnalyzer
   from pathlib import Path
   import logging
   
   logger = logging.getLogger(__name__)
   
   class Command(BaseCommand):
       help = '批量分析 Jenkins Console Logs 的 Fatal Errors'
       
       def add_arguments(self, parser):
           parser.add_argument(
               '--limit',
               type=int,
               default=100,
               help='處理的最大 Build 數量'
           )
           parser.add_argument(
               '--force',
               action='store_true',
               help='重新分析已分析過的 Builds'
           )
           parser.add_argument(
               '--build-id',
               type=int,
               help='分析特定 Build ID'
           )
       
       def handle(self, *args, **options):
           limit = options['limit']
           force = options['force']
           build_id = options.get('build_id')
           
           # 查詢條件
           if build_id:
               builds = JenkinsBuild.objects.filter(id=build_id)
           else:
               query = JenkinsBuild.objects.filter(
                   result='FAILURE',
                   log_file_path__isnull=False
               )
               
               if not force:
                   query = query.filter(console_log_analyzed=False)
               
               builds = query[:limit]
           
           total = builds.count()
           self.stdout.write(f'找到 {total} 個待分析的 Builds')
           
           success_count = 0
           error_count = 0
           
           for i, build in enumerate(builds, 1):
               self.stdout.write(
                   f'\n[{i}/{total}] 分析 {build.job.name} #{build.build_number}'
               )
               
               try:
                   if not Path(build.log_file_path).exists():
                       self.stdout.write(
                           self.style.WARNING(
                               f'  ⚠️  Console Log 文件不存在: {build.log_file_path}'
                           )
                       )
                       error_count += 1
                       continue
                   
                   analyzer = ConsoleLogAnalyzer(
                       log_file_path=build.log_file_path,
                       jenkins_server=build.job.server.ip_address,
                       job_name=build.job.name,
                       build_number=build.build_number
                   )
                   
                   result = analyzer.analyze_fatal_errors()
                   
                   if result['success']:
                       json_path = analyzer.save_analysis_to_json(
                           output_dir=str(Path(build.log_file_path).parent)
                       )
                       
                       build.console_log_analyzed = True
                       build.fatal_errors_count = result['summary']['total_fatal_tasks']
                       build.analysis_file_path = json_path
                       build.analyzed_at = timezone.now()
                       build.save()
                       
                       self.stdout.write(
                           self.style.SUCCESS(
                               f'  ✅ 分析完成: {result["summary"]["total_fatal_tasks"]} 個 Fatal Tasks'
                           )
                       )
                       success_count += 1
                   else:
                       self.stdout.write(
                           self.style.ERROR(f'  ❌ 分析失敗: {result.get("error")}')
                       )
                       error_count += 1
                   
               except Exception as e:
                   self.stdout.write(
                       self.style.ERROR(f'  ❌ 處理失敗: {e}')
                   )
                   error_count += 1
           
           # 總結
           self.stdout.write('\n' + '='*50)
           self.stdout.write(self.style.SUCCESS(f'✅ 成功: {success_count}'))
           self.stdout.write(self.style.ERROR(f'❌ 失敗: {error_count}'))
           self.stdout.write(f'📊 總計: {total}')
   ```

2. **使用範例**
   ```bash
   # 分析最近 50 個失敗的 Builds
   python manage.py analyze_console_logs --limit 50
   
   # 重新分析所有（包括已分析的）
   python manage.py analyze_console_logs --force --limit 1000
   
   # 分析特定 Build
   python manage.py analyze_console_logs --build-id 12345
   ```

**產出**：
- ✅ Management Command 實現
- ✅ 批量處理測試通過

---

## 🧪 測試計畫

### 單元測試

**測試文件**：`tests/unit/backend/test_console_log_analyzer.py`

**測試案例**：

1. **基本功能測試**
   - [x] 測試初始化（log_content vs log_file_path）
   - [x] 測試 fatal 行查找（包含/不包含 fatal）
   - [x] 測試 Task 邊界查找（向上/向下）
   - [x] 測試 Task 標題解析

2. **完整流程測試**
   - [x] 測試完整分析流程（有 fatal）
   - [x] 測試無 fatal 的情況
   - [x] 測試多個 fatal 在同一 Task
   - [x] 測試多個不同 Task 都有 fatal

3. **邊界情況測試**
   - [x] fatal 在文件開頭（沒有前一個 TASK）
   - [x] fatal 在文件結尾（沒有下一個 TASK）
   - [x] 只有一個 TASK 的 log
   - [x] 空文件或無效格式

4. **JSON 輸出測試**
   - [x] 測試 JSON 格式正確性
   - [x] 測試文件保存成功
   - [x] 測試覆蓋已存在文件

### 整合測試

**測試文件**：`tests/integration/api/test_console_log_analysis_integration.py`

**測試案例**：

1. **Celery Task 整合**
   - [x] 測試 FAILURE Build 自動觸發分析
   - [x] 測試 SUCCESS Build 不觸發分析
   - [x] 測試分析結果正確保存到 NAS
   - [x] 測試資料庫欄位正確更新

2. **API 端點測試**（如果實現）
   - [x] 測試獲取分析結果 API
   - [x] 測試手動觸發分析 API
   - [x] 測試錯誤處理

### 性能測試

**測試場景**：

1. **大文件處理**
   - 測試 10MB Console Log
   - 測試 50MB Console Log
   - 測試 100MB Console Log

2. **複雜情況**
   - 測試包含 100+ fatal 的 log
   - 測試包含 1000+ Tasks 的 log

**性能指標**：
- 分析時間 < 5 秒（10MB log）
- 記憶體使用 < 500MB
- JSON 文件大小合理（< 原始 log 的 10%）

---

## 📚 相關文檔

### 創建的文檔

1. **實作計畫**（本文檔）
   - 路徑：`docs/features/jenkins-console-log-analysis/IMPLEMENTATION_PLAN.md`
   - 用途：完整的功能規劃和實施指南

2. **API 使用手冊**（待創建）
   - 路徑：`docs/features/jenkins-console-log-analysis/API_USAGE.md`
   - 內容：API 端點說明、前端整合範例

3. **故障排查指南**（待創建）
   - 路徑：`docs/features/jenkins-console-log-analysis/TROUBLESHOOTING.md`
   - 內容：常見問題、錯誤處理、日誌查看

### 更新的文檔

1. **主 README**
   - 路徑：`docs/features/jenkins-console-log-analysis/README.md`
   - 更新：添加功能導航

---

## ✅ 總結

### 核心設計決策

1. **觸發時機**：僅在 Build 狀態為 `FAILURE` 時執行分析
2. **整合方式**：在 Console Log 下載成功後立即觸發（同一 Task 內）
3. **內容重用**：重用已下載的 `log_content`，避免重複讀取
4. **模組化設計**：核心分析邏輯獨立於 `library/utils/`，便於測試和維護
5. **容錯處理**：分析失敗不影響 Console Log 下載流程
6. **數據持久化**：JSON 結果存儲到 NAS，資料庫記錄元數據

### 優勢

✅ **無縫整合**：與現有流程完美配合，無需額外調度  
✅ **性能優化**：重用已下載內容，避免重複 I/O  
✅ **精準過濾**：只分析失敗的 Build，節省資源  
✅ **易於維護**：模組化設計，獨立測試  
✅ **可擴展性**：可輕鬆添加更多關鍵字分析  

### 下一步行動

1. ✅ **Phase 1**：開發核心分析模組（1-2 天）
2. ✅ **Phase 2**：整合到 Celery Task（1 天）
3. ⏸️ **Phase 3**：API 和前端（可選，2-3 天）
4. ⏸️ **Phase 4**：批量處理（可選，1 天）

---

**文檔維護者**：Network Toolbox Team  
**最後更新**：2025-11-27  
**版本**：1.0
