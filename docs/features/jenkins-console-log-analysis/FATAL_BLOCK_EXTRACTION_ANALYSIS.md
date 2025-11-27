# Fatal Task Block 提取規劃與分析

> **文檔版本**: 1.0  
> **創建日期**: 2025-11-27  
> **狀態**: 規劃階段

---

## 📋 目標

驗證並完善 Fatal Task Block 的提取演算法，確保能夠準確識別和提取包含 "fatal" 關鍵字的完整 Ansible Task 範圍。

---

## 🔍 測試案例

基於您提供的實際 console.log 文件：

1. **測試文件 1**:  
   `\\10.250.0.1\mdt\Team\PQ1-3\tool\jenkins_test_storage\10.252.170.187\SAF3211_KVM04\51\console.log`

2. **測試文件 2**:  
   `\\10.250.0.1\mdt\Team\PQ1-3\tool\jenkins_test_storage\10.252.170.187\SAF3214_KVM02\17\console.log`

---

## 📐 Ansible Console Log 格式分析

### 標準 Ansible Task 格式

基於 Ansible 輸出的標準格式，Console Log 中的 Task 通常具有以下結構：

```
HH:MM:SS  TASK [role_name : task_description] ****************************************
HH:MM:SS  task path: /path/to/playbook.yml:line_number
HH:MM:SS  ok: [host_name] => {
HH:MM:SS      "msg": "Task output..."
HH:MM:SS  }
...
HH:MM:SS  fatal: [host_name]: FAILED! => {
HH:MM:SS      "assertion": "condition",
HH:MM:SS      "changed": false,
HH:MM:SS      "evaluated_to": false,
HH:MM:SS      "msg": "Error message"
HH:MM:SS  }
HH:MM:SS  
HH:MM:SS  PLAY RECAP ******************************************************************
```

### 關鍵識別模式

#### 1. Task 開始標記 (Task Header)

**模式**：
```regex
^(\d{2}:\d{2}:\d{2})\s+TASK\s+\[(.*?)\]\s+\*+
```

**範例**：
```
13:20:22  TASK [test : Validate test case STC-551] ***************************************
14:35:10  TASK [common : Install dependencies] *******************************************
09:15:33  TASK [Gathering Facts] *********************************************************
```

**提取資訊**：
- 時間戳：`13:20:22`
- Task 名稱：`test : Validate test case STC-551`

#### 2. Fatal 錯誤標記

**模式**：
```regex
\bfatal\b  # 不區分大小寫，完整單詞匹配
```

**常見 Fatal 格式**：
```
fatal: [hostname]: FAILED! => {
fatal: [hostname] => (item=xxx) => {
fatal: [hostname]: UNREACHABLE! => {
```

#### 3. Task 結束標記

**方式 1**：下一個 TASK 標記（最常見）
```
HH:MM:SS  TASK [next_task] ***************
```

**方式 2**：PLAY RECAP（最後一個 Task）
```
HH:MM:SS  PLAY RECAP ******************
```

**方式 3**：文件結尾（如果是最後一個 Task 且沒有 RECAP）

---

## 🧮 提取演算法設計

### 核心邏輯流程

```
步驟 1: 掃描整個 console.log，找到所有包含 "fatal" 的行號
    └─> fatal_lines = [1245, 1246, 2103, ...]

步驟 2: 對每個 fatal_line，執行 Task Block 提取
    │
    ├─> 2.1 向上搜索 Task 起點 (task_start_line)
    │   │
    │   ├─> 從 fatal_line-1 開始向上掃描
    │   ├─> 查找符合 TASK_HEADER_PATTERN 的行
    │   ├─> 如果找到 -> 記錄行號
    │   └─> 如果到達文件開頭 (line 0) -> task_start_line = 0
    │
    ├─> 2.2 向下搜索 Task 終點 (task_end_line)
    │   │
    │   ├─> 從 fatal_line+1 開始向下掃描
    │   ├─> 查找下一個 TASK [...] 或 PLAY RECAP
    │   ├─> 如果找到 -> task_end_line = 該行號
    │   └─> 如果到達文件結尾 -> task_end_line = 最後一行
    │
    ├─> 2.3 提取 Task 內容
    │   │
    │   └─> task_content = log_lines[task_start_line:task_end_line]
    │
    ├─> 2.4 解析 Task 元數據
    │   │
    │   ├─> 提取 Task 名稱（從 task_start_line）
    │   ├─> 提取時間戳
    │   └─> 計算行範圍
    │
    └─> 2.5 收集 Fatal 上下文
        │
        ├─> 對每個 fatal_line，提取前後 3 行作為上下文
        └─> 構建 fatal_snippets 數據結構

步驟 3: 去重（同一個 Task 可能有多個 fatal）
    │
    ├─> 使用 task_start_line 作為唯一鍵
    ├─> 如果多個 fatal 屬於同一個 Task
    └─> 合併 fatal_line_numbers 和 fatal_snippets

步驟 4: 組織數據結構並保存為 JSON
    │
    └─> 生成符合規範的 JSON 格式
```

### 邊界情況處理

#### 情況 1: Fatal 在文件開頭（沒有前置 TASK）

**場景**：
```
Line 1: 10:00:00  Starting playbook...
Line 2: 10:00:01  fatal: Connection failed
Line 3: 10:00:02  TASK [First Task] ***********
```

**處理**：
- `task_start_line = 0`（文件開頭）
- `task_end_line = 3`（第一個 TASK 標記）
- Task 名稱：`"Pre-task error"` 或 `"Initialization"`

#### 情況 2: Fatal 在文件結尾（沒有後續 TASK）

**場景**：
```
Line 100: 15:30:00  TASK [Last Task] ***********
Line 101: 15:30:05  ok: [host1]
Line 102: 15:30:10  fatal: [host2]: FAILED!
Line 103: 15:30:11  (end of file)
```

**處理**：
- `task_start_line = 100`
- `task_end_line = 103`（文件結尾）

#### 情況 3: 同一個 Task 有多個 Fatal

**場景**：
```
Line 50:  TASK [Deploy to multiple hosts] ***********
Line 51:  ok: [host1]
Line 52:  fatal: [host2]: FAILED!
Line 53:  ok: [host3]
Line 54:  fatal: [host4]: FAILED!
Line 55:  TASK [Next Task] ***********
```

**處理**：
- 只創建一個 Task Block
- `fatal_line_numbers = [52, 54]`
- `fatal_count = 2`
- 兩個 fatal 都在 `fatal_snippets` 中

#### 情況 4: 連續的 TASK 標記（空 Task）

**場景**：
```
Line 20: TASK [Task A] ***********
Line 21: skipping: [host1]
Line 22: TASK [Task B] ***********
```

**處理**：
- Task A: task_start_line=20, task_end_line=22
- 正常提取，即使內容很少

#### 情況 5: PLAY RECAP 作為結束標記

**場景**：
```
Line 200: TASK [Final Task] ***********
Line 201: fatal: [host1]: FAILED!
Line 202: 
Line 203: PLAY RECAP ******************
Line 204: host1 : ok=10 changed=5 failed=1
```

**處理**：
- `task_end_line = 203`（PLAY RECAP 行）
- Task 內容包含到 RECAP 之前

---

## 🎯 正則表達式完整定義

### Python 實現

```python
import re

class ConsoleLogAnalyzer:
    """Jenkins Console Log Fatal Error 分析器"""
    
    # Task 標記模式（支援多種變體）
    TASK_HEADER_PATTERN = re.compile(
        r'^(\d{2}:\d{2}:\d{2})\s+TASK\s+\[(.*?)\]\s+\*+',
        re.IGNORECASE
    )
    
    # PLAY RECAP 標記（Task 結束標記之一）
    PLAY_RECAP_PATTERN = re.compile(
        r'^(\d{2}:\d{2}:\d{2})\s+PLAY\s+RECAP\s+\*+',
        re.IGNORECASE
    )
    
    # Fatal 關鍵字（完整單詞匹配，不區分大小寫）
    FATAL_PATTERN = re.compile(
        r'\bfatal\b',
        re.IGNORECASE
    )
    
    # 時間戳模式（用於提取任意行的時間戳）
    TIMESTAMP_PATTERN = re.compile(
        r'^(\d{2}:\d{2}:\d{2})'
    )
    
    # Task path 模式（可選，用於提取 playbook 路徑）
    TASK_PATH_PATTERN = re.compile(
        r'task\s+path:\s+(.+):(\d+)',
        re.IGNORECASE
    )
```

### 測試用正則表達式

```python
# 測試案例
test_lines = [
    "13:20:22  TASK [test : Validate test case STC-551] ***************************************",
    "14:35:10  TASK [Gathering Facts] *********************************************************",
    "15:00:00  PLAY RECAP ******************************************************************",
    "13:20:25  fatal: [Test-KVM01]: FAILED! => {",
    "13:20:26  fatal: [backup-host] => (item=config.yml) => {",
    "13:20:27  task path: /workspace/playbooks/validate.yml:45",
]

# 預期匹配結果
# Line 0: TASK_HEADER_PATTERN -> Match, groups=('13:20:22', 'test : Validate test case STC-551')
# Line 1: TASK_HEADER_PATTERN -> Match, groups=('14:35:10', 'Gathering Facts')
# Line 2: PLAY_RECAP_PATTERN -> Match
# Line 3: FATAL_PATTERN -> Match
# Line 4: FATAL_PATTERN -> Match
# Line 5: TASK_PATH_PATTERN -> Match, groups=('/workspace/playbooks/validate.yml', '45')
```

---

## 🔧 核心方法實現概要

### 1. `find_fatal_lines()`

```python
def find_fatal_lines(self) -> List[int]:
    """
    掃描所有行，找到包含 fatal 的行號
    
    Returns:
        List[int]: 包含 fatal 的行號列表（0-based index）
    """
    fatal_lines = []
    
    for line_num, line in enumerate(self.log_lines):
        if self.FATAL_PATTERN.search(line):
            fatal_lines.append(line_num)
            logger.debug(f'發現 fatal 在 Line {line_num + 1}: {line.strip()[:80]}...')
    
    logger.info(f'總共找到 {len(fatal_lines)} 個 fatal 關鍵字')
    return fatal_lines
```

### 2. `find_task_boundary()`

```python
def find_task_boundary(self, start_from: int, direction: str = 'up') -> Optional[int]:
    """
    從指定行號開始，向上或向下查找 TASK 標記
    
    Args:
        start_from: 起始行號（0-based）
        direction: 'up' 向上搜索，'down' 向下搜索
        
    Returns:
        int: TASK 標記的行號，找不到則返回 None
    """
    if direction == 'up':
        # 向上搜索：從 start_from-1 到 0
        for line_num in range(start_from - 1, -1, -1):
            line = self.log_lines[line_num]
            
            if self.TASK_HEADER_PATTERN.match(line):
                logger.debug(f'向上找到 TASK 標記在 Line {line_num + 1}')
                return line_num
        
        # 沒找到，返回文件開頭
        logger.debug('向上搜索到文件開頭，未找到 TASK 標記')
        return None  # 表示從文件開頭開始
    
    elif direction == 'down':
        # 向下搜索：從 start_from+1 到文件結尾
        for line_num in range(start_from + 1, self.total_lines):
            line = self.log_lines[line_num]
            
            # 檢查是否為 TASK 標記或 PLAY RECAP
            if self.TASK_HEADER_PATTERN.match(line):
                logger.debug(f'向下找到 TASK 標記在 Line {line_num + 1}')
                return line_num
            
            if self.PLAY_RECAP_PATTERN.match(line):
                logger.debug(f'向下找到 PLAY RECAP 在 Line {line_num + 1}')
                return line_num
        
        # 沒找到，返回文件結尾
        logger.debug('向下搜索到文件結尾，未找到 TASK 標記')
        return None  # 表示到文件結尾
    
    else:
        raise ValueError(f'無效的 direction: {direction}，應為 "up" 或 "down"')
```

### 3. `extract_task_block()`

```python
def extract_task_block(self, fatal_line: int) -> Optional[Dict[str, Any]]:
    """
    根據 fatal 行號，提取完整的 Task 區塊
    
    Args:
        fatal_line: 包含 fatal 的行號（0-based）
        
    Returns:
        dict: Task Block 資訊，如果無法提取則返回 None
    """
    # 1. 向上查找 Task 起點
    task_start_line = self.find_task_boundary(fatal_line, direction='up')
    
    if task_start_line is None:
        # 從文件開頭開始
        task_start_line = 0
        task_name = 'Pre-task error'
        task_start_time = self._extract_timestamp(self.log_lines[fatal_line])
    else:
        # 解析 Task 標題
        task_header = self.parse_task_header(self.log_lines[task_start_line])
        task_name = task_header['task_name']
        task_start_time = task_header['timestamp']
    
    # 2. 向下查找 Task 終點
    task_end_line = self.find_task_boundary(fatal_line, direction='down')
    
    if task_end_line is None:
        # 到文件結尾
        task_end_line = self.total_lines
    
    # 3. 提取 Task 內容
    task_content = '\n'.join(
        self.log_lines[task_start_line:task_end_line]
    )
    
    # 4. 查找這個 Task 範圍內所有的 fatal 行
    fatal_line_numbers = []
    for line_num in range(task_start_line, task_end_line):
        if self.FATAL_PATTERN.search(self.log_lines[line_num]):
            fatal_line_numbers.append(line_num)
    
    # 5. 提取 fatal 上下文
    fatal_snippets = []
    for fatal_line_num in fatal_line_numbers:
        snippet = self._extract_fatal_context(fatal_line_num)
        fatal_snippets.append(snippet)
    
    # 6. 構建結果
    return {
        'task_name': task_name,
        'task_start_time': task_start_time,
        'task_start_line': task_start_line + 1,  # 轉為 1-based
        'task_end_line': task_end_line,  # 1-based
        'task_total_lines': task_end_line - task_start_line,
        'fatal_line_numbers': [num + 1 for num in fatal_line_numbers],  # 1-based
        'fatal_count': len(fatal_line_numbers),
        'task_content': task_content,
        'fatal_snippets': fatal_snippets
    }
```

### 4. `_extract_fatal_context()`

```python
def _extract_fatal_context(
    self, 
    fatal_line_num: int, 
    context_lines: int = 3
) -> Dict[str, Any]:
    """
    提取 fatal 行的上下文（前後各 N 行）
    
    Args:
        fatal_line_num: fatal 行號（0-based）
        context_lines: 上下文行數（默認 3）
        
    Returns:
        dict: {
            'line_number': int,
            'content': str,
            'context_before': List[str],
            'context_after': List[str]
        }
    """
    # 計算上下文範圍
    start = max(0, fatal_line_num - context_lines)
    end = min(self.total_lines, fatal_line_num + context_lines + 1)
    
    # 提取上下文
    context_before = [
        self.log_lines[i].rstrip()
        for i in range(start, fatal_line_num)
    ]
    
    context_after = [
        self.log_lines[i].rstrip()
        for i in range(fatal_line_num + 1, end)
    ]
    
    return {
        'line_number': fatal_line_num + 1,  # 1-based
        'content': self.log_lines[fatal_line_num].rstrip(),
        'context_before': context_before,
        'context_after': context_after
    }
```

### 5. `parse_task_header()`

```python
def parse_task_header(self, line: str) -> Dict[str, str]:
    """
    解析 TASK 標記行，提取時間和 Task 名稱
    
    Args:
        line: TASK 標記行
        
    Returns:
        dict: {
            'timestamp': str,
            'task_name': str
        }
    """
    match = self.TASK_HEADER_PATTERN.match(line)
    
    if match:
        return {
            'timestamp': match.group(1),  # HH:MM:SS
            'task_name': match.group(2)   # Task 名稱
        }
    else:
        # 備用方案：嘗試提取時間戳
        timestamp_match = self.TIMESTAMP_PATTERN.match(line)
        return {
            'timestamp': timestamp_match.group(1) if timestamp_match else 'Unknown',
            'task_name': 'Unknown Task'
        }
```

---

## ✅ 驗證步驟

### 測試計畫

#### 階段 1: 基礎正則測試

```python
# 測試腳本：test_regex_patterns.py

import re

# 定義模式
TASK_HEADER_PATTERN = re.compile(
    r'^(\d{2}:\d{2}:\d{2})\s+TASK\s+\[(.*?)\]\s+\*+',
    re.IGNORECASE
)

# 測試案例
test_cases = [
    "13:20:22  TASK [test : Validate test case STC-551] ***************************************",
    "14:00:00  TASK [Gathering Facts] *********************************************************",
    "15:30:45  TASK [common : Install packages] **********************************************",
    "09:00:00  task [lowercase test] ********************************************************",  # 測試大小寫
    "10:00:00  TASK [] **********************************************************************",  # 空名稱
    "Not a task line",  # 負面測試
]

for line in test_cases:
    match = TASK_HEADER_PATTERN.match(line)
    if match:
        print(f"✓ MATCH: {line[:60]}...")
        print(f"  Time: {match.group(1)}, Task: {match.group(2)}")
    else:
        print(f"✗ NO MATCH: {line[:60]}...")
```

#### 階段 2: 實際文件測試

```python
# 測試兩個實際文件

test_files = [
    "/mnt/mdt/Team/PQ1-3/tool/jenkins_test_storage/10.252.170.187/SAF3211_KVM04/51/console.log",
    "/mnt/mdt/Team/PQ1-3/tool/jenkins_test_storage/10.252.170.187/SAF3214_KVM02/17/console.log",
]

for log_file in test_files:
    print(f"\n{'='*60}")
    print(f"測試文件: {log_file}")
    print('='*60)
    
    analyzer = ConsoleLogAnalyzer(
        log_file_path=log_file,
        jenkins_server='10.252.170.187',
        job_name=Path(log_file).parent.name,
        build_number=int(Path(log_file).parent.parent.name)
    )
    
    # 執行分析
    result = analyzer.analyze_fatal_errors()
    
    # 驗證結果
    print(f"\n分析結果:")
    print(f"  ✓ 成功: {result['success']}")
    print(f"  ✓ Fatal Tasks: {result['summary']['total_fatal_tasks']}")
    print(f"  ✓ Fatal 關鍵字: {result['summary']['fatal_keywords_found']}")
    print(f"  ✓ 總行數: {result['summary']['total_log_lines']}")
    
    # 顯示每個 Fatal Task 的詳情
    for task in result['fatal_tasks']:
        print(f"\n  Task {task['task_index']}: {task['task_name']}")
        print(f"    - 時間: {task['task_start_time']}")
        print(f"    - 行範圍: {task['task_start_line']}-{task['task_end_line']}")
        print(f"    - Fatal 數量: {task['fatal_count']}")
        print(f"    - Fatal 行號: {task['fatal_line_numbers']}")
```

#### 階段 3: JSON 輸出驗證

```python
# 驗證生成的 JSON 格式

import json

for log_file in test_files:
    analyzer = ConsoleLogAnalyzer(log_file_path=log_file, ...)
    result = analyzer.analyze_fatal_errors()
    
    if result['success']:
        # 保存 JSON
        json_path = analyzer.save_analysis_to_json(
            output_dir=str(Path(log_file).parent)
        )
        
        # 驗證 JSON 可讀性
        with open(json_path, 'r') as f:
            data = json.load(f)
        
        # 檢查必要欄位
        assert 'build_info' in data
        assert 'summary' in data
        assert 'fatal_tasks' in data
        
        print(f"✓ JSON 驗證通過: {json_path}")
```

---

## 📊 預期輸出範例

### SAF3211_KVM04/51/console.log

**預期分析結果**：
```json
{
  "build_info": {
    "jenkins_server": "10.252.170.187",
    "job_name": "SAF3211_KVM04",
    "build_number": 51,
    "log_path": "\\\\10.250.0.1\\mdt\\Team\\PQ1-3\\tool\\jenkins_test_storage\\10.252.170.187\\SAF3211_KVM04\\51\\console.log",
    "analyzed_at": "2025-11-27T..."
  },
  "summary": {
    "total_fatal_tasks": 1,  // 預期值（待實際文件驗證）
    "total_log_lines": 5000,  // 預期值
    "fatal_keywords_found": 2,  // 預期值
    "analysis_duration_ms": 150
  },
  "fatal_tasks": [
    {
      "task_index": 1,
      "task_name": "...",  // 待實際文件確認
      "task_start_time": "...",
      "task_start_line": 1234,
      "task_end_line": 1256,
      "fatal_count": 2,
      "task_content": "...",
      "fatal_snippets": [...]
    }
  ]
}
```

### SAF3214_KVM02/17/console.log

**預期分析結果**：
```json
{
  "build_info": {
    "jenkins_server": "10.252.170.187",
    "job_name": "SAF3214_KVM02",
    "build_number": 17,
    "log_path": "...",
    "analyzed_at": "2025-11-27T..."
  },
  "summary": {
    "total_fatal_tasks": 1,  // 待驗證
    "total_log_lines": 3500,
    "fatal_keywords_found": 1,
    "analysis_duration_ms": 120
  },
  "fatal_tasks": [...]
}
```

---

## 🎯 確認清單

在實際執行之前，需要確認以下事項：

### ✅ 正則表達式驗證

- [x] TASK_HEADER_PATTERN 能正確匹配標準 Task 標記
- [x] FATAL_PATTERN 能正確識別 fatal 關鍵字（不區分大小寫）
- [x] PLAY_RECAP_PATTERN 能識別 PLAY RECAP 標記
- [ ] 在實際文件上測試所有模式

### ✅ 邊界情況處理

- [x] Fatal 在文件開頭的處理邏輯
- [x] Fatal 在文件結尾的處理邏輯
- [x] 同一 Task 多個 Fatal 的去重邏輯
- [x] 空 Task 或極短 Task 的處理
- [x] PLAY RECAP 作為結束標記的處理

### ✅ 數據結構

- [x] JSON 輸出格式符合規範
- [x] 所有必要欄位都已定義
- [x] 1-based vs 0-based 行號轉換正確

### ✅ 性能考量

- [x] 大文件讀取策略（逐行 vs 一次全讀）
- [x] 正則表達式編譯（避免重複編譯）
- [x] 記憶體使用（避免複製大字串）

### ⏸️ 待實際文件驗證

- [ ] 實際讀取 SAF3211_KVM04/51/console.log
- [ ] 驗證 fatal 關鍵字的實際格式
- [ ] 確認 Task 標記的實際格式
- [ ] 測試完整的提取流程
- [ ] 驗證 JSON 輸出的正確性

---

## 🚀 下一步行動

1. **等待 NAS 掛載**（或提供替代訪問方式）
2. **讀取實際文件內容**（至少前 200 行和包含 fatal 的區域）
3. **驗證正則表達式**（確保能匹配實際格式）
4. **執行測試分析**（使用實際文件）
5. **調整演算法**（根據實際情況優化）
6. **完成實現**（Phase 1: ConsoleLogAnalyzer 類）

---

**問題與回答**：

**Q: 我是否已經了解如何抓取 fail task 的 string block？**

**A: 是的！核心邏輯如下**：

1. **找到所有 fatal 行** → 使用正則 `\bfatal\b`
2. **向上找 Task 起點** → 查找 `TASK [...]` 標記
3. **向下找 Task 終點** → 查找下一個 `TASK [...]` 或 `PLAY RECAP`
4. **提取完整範圍** → `log_lines[起點:終點]`
5. **去重並組織** → 同一 Task 的多個 fatal 合併
6. **保存為 JSON** → 結構化輸出

**準備就緒，等待實際文件訪問以進行驗證！**

---

**文檔維護者**：Network Toolbox Team  
**最後更新**：2025-11-27  
**版本**：1.0
