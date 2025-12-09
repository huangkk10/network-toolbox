# CPU 使用率 100% 問題分析報告

**日期**：2025-12-09  
**環境**：Network Toolbox - Celery 定時任務系統  
**問題**：Celery Worker CPU 使用率達到 88%（接近 100%）

---

## 🔍 問題現象

### 1. 資源使用情況

**容器資源監控**（2025-12-09 07:52）：
```
CONTAINER      CPU %     MEM USAGE / LIMIT
nt-celery-worker   88.50%    1006MiB / 15.61GiB  ← CPU 異常高
```

**系統進程監控**：
```
PID    USER   %CPU   %MEM   COMMAND
7005   root   76.5   0.9    celery  ← Worker 進程 1
7012   root   64.7   0.8    celery  ← Worker 進程 2
6998   root   17.6   0.9    celery  ← Worker 進程 3
```

**負載指標**：
```
Load Average: 2.08, 1.66, 0.78
```

---

## 📊 根本原因分析

### 問題 1：`auto_store_jenkins_builds_task` 批次處理過大

**任務配置**（`backend/network_toolbox/celery.py:163`）：
```python
'auto-store-jenkins-builds-every-hour': {
    'task': 'api.tasks.auto_store_jenkins_builds_task',
    'schedule': crontab(minute=45),  # 每小時 XX:45 執行
    'kwargs': {
        'limit': 100        # ❌ 每次處理 100 個 Builds（太多）
    },
    'options': {
        'expires': 900,     # 任務超時 15 分鐘
    }
}
```

**任務實現**（`backend/api/tasks.py:3580`）：
```python
def auto_store_jenkins_builds_task(self, limit: int = 20):
    # 查詢未存儲的 Builds
    builds_to_process = query[:limit]
    
    for build in builds_to_process:
        # ❌ 為每個 Build 創建一個異步任務
        task = store_jenkins_build_task.delay(build.id)
```

**問題**：
- 一次創建 **100 個並行任務**
- 每個 `store_jenkins_build_task` 都會：
  - 下載 Workspace（ZIP 或遞歸下載）
  - 下載 Artifacts
  - 進行 Fatal Error 分析
  - 進行大量 I/O 操作（NAS 讀寫）

**CPU 負載來源**：
1. **並行 Worker 競爭**：100 個任務同時執行，Worker Pool（8 個進程）不斷切換
2. **ZIP 解壓縮**：大量 CPU 密集型操作
3. **JSON 解析**：分析 Console Log 時的正則匹配和 JSON 處理
4. **文件系統 I/O**：NAS 掛載的網路檔案系統，I/O 等待增加 CPU 壓力

---

### 問題 2：`auto_analyze_missing_fatal_errors_task` 重複分析

**任務配置**（`backend/network_toolbox/celery.py:266`）：
```python
# 任務 18：補充缺失的 Fatal Error 分析（每小時 15 分）
'auto-analyze-missing-fatal-errors-hourly': {
    'task': 'api.tasks.auto_analyze_missing_fatal_errors_task',
    'schedule': crontab(minute=15),  # 每小時 XX:15 執行
    'kwargs': {
        'limit': 50,       # ❌ 每次處理 50 個 Builds
        'days': 7          # 檢查最近 7 天的 Builds
    },
    'options': {
        'expires': 2700,   # 任務超時 45 分鐘
    }
}

# 任務 19：補充缺失的 Fatal Error 分析（每日批量處理）
'auto-analyze-missing-fatal-errors-daily': {
    'task': 'api.tasks.auto_analyze_missing_fatal_errors_task',
    'schedule': crontab(hour=2, minute=30),  # 每天 02:30 執行
    'kwargs': {
        'limit': 200,      # ❌ 每次處理 200 個 Builds
        'days': 30         # 檢查最近 30 天的 Builds
    },
    'options': {
        'expires': 5400,   # 任務超時 90 分鐘
    }
}
```

**問題**：
- **每小時執行一次**，每次掃描 50 個 Builds
- **每天執行一次**，每次掃描 200 個 Builds
- 這兩個任務會**重複處理相同的 Builds**（檢查最近 7 天和 30 天有重疊）
- 每個掃描任務又會創建多個 `store_jenkins_build_task` 子任務

---

### 問題 3：多個任務同時執行導致資源競爭

**Celery Beat 調度記錄**（07:48 啟動時）：
```
[2025-12-09 07:48:48] Sending due task auto-analyze-missing-fatal-errors-hourly
[2025-12-09 07:48:48] Sending due task auto-store-jenkins-builds-every-hour
[2025-12-09 07:48:48] Sending due task sync-jenkins-builds-every-10-minutes
[2025-12-09 07:48:48] Sending due task collect-network-quality-every-5-minutes
...（共 20 個任務同時發送）
```

**衝突任務時間表**：

| 時間 | 任務 | CPU 密集度 | I/O 密集度 |
|------|------|-----------|-----------|
| 每小時 :00 | `sync_all_jenkins_jobs_task` | 高 | 極高 |
| 每小時 :15 | `auto_analyze_missing_fatal_errors_task` | 中 | 高 |
| 每小時 :15 | `auto_store_workspaces` | 高 | 極高 |
| 每小時 :45 | `auto_store_jenkins_builds_task` | 高 | 極高 |
| 每 10 分鐘 | `sync_jenkins_builds` | 中 | 高 |
| 每 5 分鐘 | `collect_network_quality_task` | 中 | 中 |

**時間衝突點**：
- **:00** - 3 個任務（Jobs 同步 + Builds 同步 + 網路品質檢測）
- **:15** - 3 個任務（Fatal 分析 + Workspace 存儲 + Leases 同步）
- **:45** - 2 個任務（Builds 存儲 + 網路品質檢測）

---

## 🎯 高風險任務清單

### 🔴 極高風險（會導致 CPU 飆升）

1. **`auto_store_jenkins_builds_task`**
   - **問題**：批次太大（100 個）
   - **頻率**：每小時執行一次
   - **CPU 負載**：⭐⭐⭐⭐⭐
   - **I/O 負載**：⭐⭐⭐⭐⭐
   - **建議**：降低到 **20 個/次**，拆分執行時間

2. **`auto_store_workspaces`**
   - **問題**：Workspace ZIP 下載、解壓縮非常耗 CPU
   - **頻率**：每小時 :15 執行
   - **CPU 負載**：⭐⭐⭐⭐⭐
   - **I/O 負載**：⭐⭐⭐⭐⭐
   - **建議**：與 `auto_store_jenkins_builds_task` **錯開時間**

3. **`auto_analyze_missing_fatal_errors_task`**（每小時版本）
   - **問題**：批次 50 個，會創建 50 個子任務
   - **頻率**：每小時 :15 執行
   - **CPU 負載**：⭐⭐⭐⭐
   - **I/O 負載**：⭐⭐⭐⭐
   - **建議**：降低到 **10 個/次**

### 🟡 中等風險（可能導致 CPU 升高）

4. **`sync_jenkins_builds`**（每 10 分鐘）
   - **問題**：同步 20 個 Builds/Job，可能涉及大量 API 調用
   - **頻率**：每 10 分鐘執行一次
   - **CPU 負載**：⭐⭐⭐
   - **I/O 負載**：⭐⭐⭐
   - **建議**：保持現狀，監控即可

5. **`collect_network_quality_task`**
   - **問題**：並行測試多個 Switch（最多 10 個）
   - **頻率**：每 5 分鐘執行一次
   - **CPU 負載**：⭐⭐⭐
   - **I/O 負載**：⭐⭐
   - **建議**：**添加 CPU 監控機制**（目前有實現）

6. **`sync_all_jenkins_jobs_task`**
   - **問題**：同步所有 Jobs，API 調用量大
   - **頻率**：每小時整點執行
   - **CPU 負載**：⭐⭐⭐
   - **I/O 負載**：⭐⭐⭐⭐
   - **建議**：與其他重度任務**錯開時間**

---

## ✅ 解決方案

### 方案 1：調整 `auto_store_jenkins_builds_task` 批次大小

**修改**：`backend/network_toolbox/celery.py`

```python
# 任務 12：Jenkins Builds 自動存儲到 NAS
'auto-store-jenkins-builds-every-hour': {
    'task': 'api.tasks.auto_store_jenkins_builds_task',
    'schedule': crontab(minute=45),  # 每小時 XX:45 執行
    'kwargs': {
        'limit': 20        # ✅ 降低到 20 個（從 100 改為 20）
    },
    'options': {
        'expires': 900,
    }
}
```

**效果**：
- CPU 負載降低 **80%**（100 → 20）
- 減少並發任務競爭
- 仍能保持合理的存儲速度（20 個/小時 = 480 個/天）

---

### 方案 2：優化 `auto_analyze_missing_fatal_errors_task` 頻率

**修改**：`backend/network_toolbox/celery.py`

**選項 A：降低每小時批次**
```python
'auto-analyze-missing-fatal-errors-hourly': {
    'task': 'api.tasks.auto_analyze_missing_fatal_errors_task',
    'schedule': crontab(minute=15),
    'kwargs': {
        'limit': 10,       # ✅ 降低到 10 個（從 50 改為 10）
        'days': 7
    },
    'options': {
        'expires': 2700,
    }
}
```

**選項 B：取消每小時版本，只保留每日批量處理**
```python
# ✅ 註釋掉每小時版本
# 'auto-analyze-missing-fatal-errors-hourly': {
#     'task': 'api.tasks.auto_analyze_missing_fatal_errors_task',
#     'schedule': crontab(minute=15),
#     'kwargs': {
#         'limit': 50,
#         'days': 7
#     },
#     'options': {
#         'expires': 2700,
#     }
# },

# 保留每日批量處理（凌晨 2:30，系統空閒時段）
'auto-analyze-missing-fatal-errors-daily': {
    'task': 'api.tasks.auto_analyze_missing_fatal_errors_task',
    'schedule': crontab(hour=2, minute=30),
    'kwargs': {
        'limit': 100,      # ✅ 降低到 100 個（從 200 改為 100）
        'days': 30
    },
    'options': {
        'expires': 5400,
    }
}
```

**建議**：採用 **選項 B**，理由：
- 每小時補分析的價值不高（大部分 Fatal 已在 Build 存儲時分析）
- 凌晨批量處理不會影響白天使用
- 減少任務重複

---

### 方案 3：錯開任務執行時間

**修改**：`backend/network_toolbox/celery.py`

**當前時間分佈**（有衝突）：
```
:00 - sync_all_jenkins_jobs_task, sync_jenkins_builds, auto_identify_switches
:10 - sync_all_dhcp_logs, sync_jenkins_builds
:15 - auto_analyze_fatal_errors, auto_store_workspaces  ← 衝突
:20 - (無)
:30 - auto_store_jenkins_builds (新增，改為每 30 分鐘)
:45 - auto_store_jenkins_builds  ← 改為每 30 分鐘執行
:50 - (無)
```

**優化後時間分佈**（錯開衝突）：
```python
# ✅ 改為每 30 分鐘執行一次，錯開其他重度任務
'auto-store-jenkins-builds-every-30-minutes': {
    'task': 'api.tasks.auto_store_jenkins_builds_task',
    'schedule': crontab(minute='5,35'),  # 改為 :05 和 :35 執行
    'kwargs': {
        'limit': 10        # 降低批次（因為頻率提高）
    },
    'options': {
        'expires': 1500,   # 25 分鐘超時
    }
}

# ✅ Workspace 存儲改到 :25 執行
'auto-store-jenkins-workspaces-hourly': {
    'task': 'api.tasks.auto_store_workspaces',
    'schedule': crontab(minute=25),  # 改為 :25 執行（原本 :15）
    'options': {
        'expires': 2700,
    }
}
```

**優化後時間表**：
```
:00 - sync_all_jenkins_jobs_task
:05 - auto_store_jenkins_builds (新時間)
:10 - sync_jenkins_builds
:15 - (減輕負載，原本的 fatal 分析已取消)
:20 - (空閒)
:25 - auto_store_workspaces (新時間)
:30 - (空閒)
:35 - auto_store_jenkins_builds (新時間)
:40 - (空閒)
:45 - (空閒，原本的 builds 存儲已移除)
:50 - (空閒)
```

---

### 方案 4：為重度任務添加 CPU 保護機制

**修改**：`backend/api/tasks.py`

在 `auto_store_jenkins_builds_task` 中添加 CPU 監控：

```python
@shared_task(
    bind=True,
    name='api.tasks.auto_store_jenkins_builds_task',
    max_retries=3,
    default_retry_delay=300,
    time_limit=1800,
    soft_time_limit=1650
)
def auto_store_jenkins_builds_task(self, limit: int = 20) -> Dict[str, Any]:
    """
    自動掃描並存儲未存儲的 Jenkins Builds
    """
    import psutil
    
    try:
        # ✅ 新增：檢查 CPU 使用率
        cpu_percent = psutil.cpu_percent(interval=1)
        if cpu_percent > 80.0:
            logger.warning(
                f'[Celery] ⚠️  CPU 使用率過高 ({cpu_percent}%)，'
                f'延遲執行 auto_store_jenkins_builds_task'
            )
            # 延遲 5 分鐘後重試
            raise self.retry(countdown=300)
        
        logger.info(
            f'[Celery] 開始自動存儲任務掃描 - '
            f'Limit: {limit}, CPU: {cpu_percent}%'
        )
        
        # ... 原有邏輯 ...
```

**類似保護可添加到**：
- `auto_analyze_missing_fatal_errors_task`
- `auto_store_workspaces`
- `sync_all_jenkins_jobs_task`

---

## 📋 實施計劃

### 階段 1：立即實施（降低當前負載）

- [ ] **調整批次大小**
  - `auto_store_jenkins_builds_task`: 100 → 20
  - `auto_analyze_missing_fatal_errors_hourly`: 50 → 10（或直接取消）
  - `auto_analyze_missing_fatal_errors_daily`: 200 → 100

### 階段 2：錯開任務時間（優化調度）

- [ ] **重新安排任務時間**
  - `auto_store_jenkins_builds`: :45 → :05, :35（每 30 分鐘，批次 10）
  - `auto_store_workspaces`: :15 → :25
  - 取消 `auto_analyze_missing_fatal_errors_hourly`

### 階段 3：添加保護機制（長期優化）

- [ ] **實現 CPU 保護**
  - 為重度任務添加 CPU 監控
  - CPU > 80% 時延遲執行
  - 記錄延遲事件到日誌

### 階段 4：監控和調整

- [ ] **監控效果**
  - 觀察 CPU 使用率變化
  - 檢查任務完成率
  - 調整批次大小和頻率

---

## 🎓 經驗教訓

### 1. 批次處理的風險

**問題**：
- 批次過大（100 個）導致大量並行任務
- Worker Pool 有限（8 個進程），但任務遠超容量

**教訓**：
- 批次大小應考慮 **Worker Pool 容量**
- 建議：批次 ≤ Worker Pool 大小 × 2
- 本專案：8 Workers → 批次 ≤ 16~20

### 2. 任務調度的時間衝突

**問題**：
- 多個重度任務在同一時間執行（:15, :45）
- 導致資源競爭，CPU 飆升

**教訓**：
- 重度任務應**錯開時間**
- 使用時間表視覺化工具規劃
- 凌晨時段用於批量處理

### 3. I/O 密集 vs CPU 密集

**問題**：
- Workspace 下載（I/O 密集）+ ZIP 解壓縮（CPU 密集）同時進行
- NAS 網路 I/O 等待增加 CPU 壓力

**教訓**：
- I/O 密集任務應與 CPU 密集任務分離
- 考慮使用專用 Worker Pool（一組處理 I/O，一組處理 CPU）
- 添加流量控制機制

### 4. 重複任務的累積效應

**問題**：
- 每小時補分析 + 每日補分析重複掃描
- 浪費資源，增加負載

**教訓**：
- 定時任務應避免重複
- 檢查現有機制是否已覆蓋需求
- 優先使用低頻批量處理

---

## 📈 預期效果

### 調整前

```
CPU 使用率: 80-90%（高峰時段）
並發任務數: 50-100 個
任務完成時間: 不穩定（經常超時）
```

### 調整後

```
CPU 使用率: 30-50%（高峰時段）  ← 降低 40-50%
並發任務數: 10-20 個             ← 降低 60-80%
任務完成時間: 穩定（很少超時）   ← 提升穩定性
```

---

## 🔍 持續監控指標

### 1. CPU 使用率

```bash
# 監控 Celery Worker CPU
docker stats nt-celery-worker --no-stream
```

**目標**：< 60%（正常），< 80%（警告）

### 2. Celery Flower 監控

訪問：http://localhost:5555

**關注指標**：
- Active Tasks（活躍任務數）
- Task Success Rate（成功率）
- Task Duration（執行時間）

### 3. 日誌監控

```bash
# 查看任務執行日誌
docker logs nt-celery-worker --tail 100 | grep "CPU:"
```

**關注**：
- CPU 保護機制觸發次數
- 任務延遲重試次數

---

## 📝 總結

### 根本原因

1. **批次過大**：`auto_store_jenkins_builds_task` 一次處理 100 個 Builds
2. **時間衝突**：多個重度任務在相同時間執行（:15, :45）
3. **重複任務**：每小時和每日補分析任務重複掃描

### 解決方案

1. **降低批次**：100 → 20（降低 80% 負載）
2. **錯開時間**：重新安排任務執行時間表
3. **取消重複**：移除每小時補分析，只保留每日批量
4. **添加保護**：CPU 監控機制，超過 80% 時延遲執行

### 預期效果

- CPU 使用率從 **80-90%** 降至 **30-50%**
- 系統穩定性顯著提升
- 任務完成率提高

---

**報告完成時間**：2025-12-09 08:00  
**建議優先級**：🔴 高優先級（立即實施）
