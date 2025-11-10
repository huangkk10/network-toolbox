# iPXE 日誌自動同步功能# iPXE 日誌自動同步功能



## 📚 文檔導航## 📋 概述



- **[README.md](./README.md)**（本文）- 完整技術文檔本功能為 Network Toolbox 提供 **iPXE Server 日誌自動同步機制**，確保：

- **[QUICKSTART.md](./QUICKSTART.md)** - 5 分鐘快速上手指南

- **[SOLUTION_SUMMARY.md](./SOLUTION_SUMMARY.md)** - 問題解決方案總結1. ✅ **新增 iPXE Server 自動開始日誌收集**（30 秒內啟動）

2. ✅ **定期自動同步所有伺服器日誌**（每 10 分鐘）

## 🎯 功能概述3. ✅ **自動管理伺服器狀態**（online/offline）

4. ✅ **完整的錯誤處理和重試機制**

本功能實現 iPXE Server 日誌的完全自動化收集和同步，確保：

1. ✅ 新增伺服器 30 秒後自動開始收集**與 DHCP 日誌同步保持架構一致性**，使用相同的設計模式。

2. ✅ 每 10 分鐘自動同步所有在線伺服器

3. ✅ 失敗自動重試（最多 3 次）---

4. ✅ 與 DHCP 自動同步功能完全對齊

## 🏗️ 系統架構

## 🏗️ 系統架構

### 組件說明

```

┌─────────────────────────────────────────┐```

│  前端：iPXE 分析頁面                     │┌─────────────────────────────────────────────────────────────────┐

│  - 選擇伺服器                            ││                        iPXE 日誌同步架構                           │

│  - 查看日誌統計                          │└─────────────────────────────────────────────────────────────────┘

│  - 即時數據展示                          │

└─────────────────────────────────────────┘┌──────────────────┐

                   ↓│  IPXEServer      │  ──┐

┌─────────────────────────────────────────┐│  (Django Model)  │    │ 觸發 Signal

│  Django Models                          │└──────────────────┘    │

│  - IPXEServer                           │                        ↓

│  - IPXELog (log_type: mac/boot)        │┌──────────────────────────────────────────────┐

└─────────────────────────────────────────┘│  Django Signals (api/signals.py)             │

                   ↓│  ┌────────────────────────────────────────┐  │

┌─────────────────────────────────────────┐│  │ @receiver(post_save, sender=IPXEServer)│  │

│  Django Signals (自動觸發層)             ││  │ def ipxe_server_post_save()            │  │

│  - ipxe_server_post_save               ││  │   - 新建伺服器：觸發首次日誌收集(30s)   │  │

│  - trigger_ipxe_logs_sync_for_server() ││  │   - 更新為 online 且無日誌：補充收集    │  │

└─────────────────────────────────────────┘│  └────────────────────────────────────────┘  │

                   ↓└──────────────────────────────────────────────┘

┌─────────────────────────────────────────┐                        ↓

│  Celery Tasks (任務執行層)               │┌──────────────────────────────────────────────┐

│  - sync_ipxe_logs_task()               ││  Celery Tasks (api/tasks.py)                 │

│  - sync_all_ipxe_logs_task()           ││  ┌────────────────────────────────────────┐  │

└─────────────────────────────────────────┘│  │ @shared_task                           │  │

                   ↓│  │ def sync_ipxe_logs_task(server_id)     │  │

┌─────────────────────────────────────────┐│  │   - 單一伺服器日誌收集                  │  │

│  IPXEService (業務邏輯層)                ││  │   - 錯誤處理和重試（3 次）              │  │

│  - connect_ssh()                        ││  └────────────────────────────────────────┘  │

│  - sync_logs_to_db()                   ││  ┌────────────────────────────────────────┐  │

│  - collect_logs_from_container()       ││  │ @shared_task                           │  │

└─────────────────────────────────────────┘│  │ def sync_all_ipxe_logs_task()          │  │

                   ↓│  │   - 批次同步所有在線伺服器               │  │

┌─────────────────────────────────────────┐│  │   - 定期任務（每 10 分鐘）              │  │

│  iPXE Server (目標伺服器)                ││  └────────────────────────────────────────┘  │

│  - Docker Container: ipxe_mac-flask    │└──────────────────────────────────────────────┘

│  - Docker Container: ipxe              │                        ↓

│  - 日誌檔案                              │┌──────────────────────────────────────────────┐

└─────────────────────────────────────────┘│  IPXEService (api/ipxe_service.py)           │

```│  ┌────────────────────────────────────────┐  │

│  │ def sync_logs_to_db(limit=1000)        │  │

## 🚀 快速開始│  │   1. SSH 連接 iPXE Server              │  │

│  │   2. 從 MAC 容器讀取日誌                │  │

### 新增 iPXE Server│  │   3. 從 IPXE 容器讀取日誌               │  │

│  │   4. 解析並存入資料庫                   │  │

```python│  │   5. 更新 last_sync_at                 │  │

# 透過 Django Admin 或 API 創建│  └────────────────────────────────────────┘  │

IPXEServer.objects.create(└──────────────────────────────────────────────┘

    name='10.250.120.2',                        ↓

    ip_address='10.250.120.2',┌──────────────────────────────────────────────┐

    ssh_username='rvt',│  Database (PostgreSQL)                       │

    ssh_password='your_password',│  - IPXELog (日誌記錄)                        │

    docker_container_mac='ipxe_mac-flask',│  - IPXEServer (伺服器狀態)                   │

    docker_container_ipxe='ipxe',└──────────────────────────────────────────────┘

    status='online'```

)

---

# 30 秒後自動開始收集日誌 ✅

# 之後每 10 分鐘自動更新 ✅## 🔧 技術實現

```

### 1. Celery 任務定義

### 查看同步狀態

#### `sync_ipxe_logs_task` - 單一伺服器同步

```bash

docker exec nt-django python manage.py shell -c "**位置**：`backend/api/tasks.py`

from api.models import IPXEServer, IPXELog

**功能**：

server = IPXEServer.objects.get(id=4)- 收集指定 iPXE Server 的日誌

log_count = IPXELog.objects.filter(server=server).count()- 支援自定義日誌數量限制

- 自動錯誤處理和重試（最多 3 次）

print(f'Server: {server.name}')

print(f'Status: {server.status}')**參數**：

print(f'Last Sync: {server.last_sync_at}')```python

print(f'Total Logs: {log_count}')def sync_ipxe_logs_task(server_id, limit=1000):

"    """

```    Args:

        server_id: IPXEServer ID

### 手動立即同步        limit: 每個容器收集的日誌數量（預設: 1000）

    

```bash    Returns:

docker exec nt-django python manage.py shell -c "        dict: {

from api.signals import trigger_ipxe_logs_sync_for_server            'server_id': int,

            'server_name': str,

# 立即為 Server 4 收集 2000 條日誌            'mac_logs': int,    # MAC 管理日誌數

task_id = trigger_ipxe_logs_sync_for_server(            'boot_logs': int,   # 開機日誌數

    server_id=4,            'total': int,       # 總日誌數

    delay_seconds=0,            'errors': int       # 錯誤數

    limit=2000        }

)    """

print(f'Task ID: {task_id}')```

"

```**配置**：

- `max_retries`: 3

## 📊 核心組件- `default_retry_delay`: 60 秒

- `time_limit`: 240 秒（4 分鐘）

### 1. Celery 任務 (`backend/api/tasks.py`)- `soft_time_limit`: 210 秒（3.5 分鐘）



#### `sync_ipxe_logs_task(server_id, limit=1000)`#### `sync_all_ipxe_logs_task` - 批次同步



同步單一 iPXE Server 的日誌。**功能**：

- 批次同步所有在線的 iPXE Server

**參數**：- 用於定期任務（每 10 分鐘執行）

- `server_id`: IPXEServer ID- 彙總所有伺服器的同步結果

- `limit`: 每個容器收集的日誌數量（預設 1000）

**配置**：

**特性**：- `max_retries`: 2

- ⏱️ 時間限制：4 分鐘硬限制，3.5 分鐘軟限制- `default_retry_delay`: 300 秒（5 分鐘）

- 🔄 失敗重試：最多 3 次，間隔 60 秒- `time_limit`: 1800 秒（30 分鐘）

- 📝 詳細日誌記錄- `soft_time_limit`: 1650 秒（27.5 分鐘）



**返回值**：### 2. Django Signals 自動化

```python

{**位置**：`backend/api/signals.py`

    'server_id': 4,

    'server_name': '10.250.120.2',#### Signal: `ipxe_server_post_save`

    'mac_logs': 997,      # MAC 管理日誌

    'boot_logs': 1000,    # 開機日誌**觸發條件**：

    'total': 1997,        # 總計1. **新建 IPXEServer**（`created=True`）

    'errors': 02. **更新為 online 狀態且無日誌**

}

```**行為**：



#### `sync_all_ipxe_logs_task(limit=1000)````python

@receiver(post_save, sender=IPXEServer)

批次同步所有在線 iPXE Server 的日誌（定期任務使用）。def ipxe_server_post_save(sender, instance, created, **kwargs):

    if created:

**參數**：        # 新建伺服器 - 延遲 30 秒後執行首次日誌收集

- `limit`: 每個伺服器每個容器的日誌數量        sync_ipxe_logs_task.apply_async(

            args=[instance.id],

**特性**：            kwargs={'limit': 1000},

- ⏱️ 時間限制：30 分鐘硬限制            countdown=30,  # 30 秒延遲

- 🔄 失敗重試：最多 2 次，間隔 5 分鐘            retry=True,

- 🔀 並行處理多個伺服器            retry_policy={

                'max_retries': 3,

**返回值**：                'interval_start': 60,

```python                'interval_step': 60,

{            }

    'total_servers': 4,        )

    'success_count': 4,```

    'failed_count': 0,

    'total_logs_created': 392,**為什麼延遲 30 秒？**

    'results': [...]- 給用戶時間配置完整的 SSH 憑證和容器名稱

}- 確保資料庫事務完全提交

```- 避免立即執行可能失敗的任務



### 2. Django Signals (`backend/api/signals.py`)#### 手動觸發函數



#### `ipxe_server_post_save` Signal**位置**：`backend/api/signals.py`



**觸發時機**：IPXEServer 創建或更新```python

def trigger_ipxe_logs_sync_for_server(server_id, delay_seconds=5, limit=1000):

**創建時行為**：    """

1. 檢查 SSH 配置是否完整    手動觸發特定 iPXE Server 的日誌收集任務

2. 延遲 30 秒後執行首次日誌收集    

3. 配置自動重試機制（3 次，間隔 60 秒）    用途：

    - 手動補充收集日誌

**更新時行為**：    - 故障排查和測試

- 如果狀態變為 online 且無日誌，執行一次同步    - 立即同步特定伺服器

    

#### `trigger_ipxe_logs_sync_for_server()` 函數    Returns:

        str: Celery Task ID

手動觸發特定伺服器的日誌收集。    """

```

**範例**：

```python**使用範例**：

from api.signals import trigger_ipxe_logs_sync_for_server```python

from api.signals import trigger_ipxe_logs_sync_for_server

# 立即收集 2000 條日誌

task_id = trigger_ipxe_logs_sync_for_server(# 立即為 Server ID=4 收集 2000 條日誌

    server_id=4,task_id = trigger_ipxe_logs_sync_for_server(

    delay_seconds=0,    server_id=4,

    limit=2000    delay_seconds=0,

)    limit=2000

```)

```

### 3. 定期任務 (Celery Beat)

### 3. Celery Beat 定期任務

**任務名稱**：`sync-all-ipxe-logs-every-10-minutes`

**任務配置**：

**配置**：

- **任務**：`api.tasks.sync_all_ipxe_logs_task`| 屬性 | 值 |

- **排程**：每 10 分鐘（Crontab: `*/10 * * * *`）|-----|---|

- **參數**：`{"limit": 1000}`| **任務名稱** | `sync-all-ipxe-logs-every-10-minutes` |

- **時區**：Asia/Taipei| **Celery Task** | `api.tasks.sync_all_ipxe_logs_task` |

- **狀態**：已啟用 ✅| **排程** | `*/10 * * * *`（每 10 分鐘） |

| **啟用** | ✅ True |

## 📝 工作流程| **參數** | `{"limit": 1000}` |

| **說明** | 每 10 分鐘自動同步所有 iPXE Server 的日誌 |

### 新增伺服器流程

**查看定期任務**：

```mermaid```bash

graph TDdocker exec nt-django python manage.py shell -c "

    A[用戶創建 IPXEServer] --> B[Django Signal 偵測]from django_celery_beat.models import PeriodicTask

    B --> C{檢查 SSH 配置}task = PeriodicTask.objects.get(name='sync-all-ipxe-logs-every-10-minutes')

    C -->|完整| D[延遲 30 秒]print(task.crontab)  # */10 * * * * (m/h/dM/MY/d) Asia/Taipei

    C -->|缺失| E[跳過自動同步]"

    D --> F[提交 Celery 任務]```

    F --> G[Celery Worker 執行]

    G --> H[SSH 連接目標伺服器]### 4. IPXEService 核心邏輯

    H --> I[收集容器日誌]

    I --> J[解析並寫入資料庫]**位置**：`backend/api/ipxe_service.py`

    J --> K[更新 last_sync_at]

    K --> L[之後每 10 分鐘自動同步]**核心方法**：`sync_logs_to_db(limit=1000)`

```

**執行流程**：

### 定期同步流程

```python

```def sync_logs_to_db(self, limit: int = 1000) -> dict:

1. Celery Beat 每 10 分鐘觸發    """

   ↓    1. SSH 連接到 iPXE Server

2. 查詢所有 status='online' 的 IPXEServer    2. 從 MAC 管理容器收集日誌

   ↓    3. 從 IPXE 開機容器收集日誌

3. 對每個伺服器執行同步    4. 解析日誌並存入 IPXELog 資料庫

   ├── Server 1: SSH → Docker logs → 解析 → 寫入    5. 更新 IPXEServer.last_sync_at

   ├── Server 2: SSH → Docker logs → 解析 → 寫入    6. 設定 status='online'

   └── Server N: SSH → Docker logs → 解析 → 寫入    

   ↓    Returns:

4. 更新每個伺服器的狀態        {

   ↓            'mac_logs': int,   # MAC 日誌數

5. 記錄彙總統計            'boot_logs': int,  # BOOT 日誌數

```            'total': int       # 總計

        }

## 🧪 測試驗證    """

```

### 自動化測試腳本

**容器日誌讀取**：

```bash```bash

# 執行完整測試# MAC 管理容器日誌

./test_auto_ipxe_sync.shdocker logs --tail {limit} {docker_container_mac}



# 測試項目：# IPXE 開機容器日誌

# ✅ Celery 任務註冊docker logs --tail {limit} {docker_container_ipxe}

# ✅ 定期任務配置```

# ✅ Signal 配置

# ✅ Celery 服務狀態---

# ✅ 伺服器同步狀態

# ✅ 手動觸發功能## 📊 資料模型

# ✅ 日誌記錄

```### IPXEServer



### 手動測試**關鍵欄位**：

```python

#### 1. 測試新增伺服器自動同步class IPXEServer(models.Model):

    name = CharField(max_length=100)

```bash    ip_address = GenericIPAddressField(unique=True)

# 創建測試伺服器    ssh_username = CharField(max_length=50)

docker exec nt-django python manage.py shell -c "    ssh_password = CharField(max_length=255)

from api.models import IPXEServer    docker_container_mac = CharField(max_length=100)    # MAC 管理容器名

    docker_container_ipxe = CharField(max_length=100)   # IPXE 開機容器名

server = IPXEServer.objects.create(    status = CharField(max_length=20)                   # online/offline

    name='Test Server',    last_sync_at = DateTimeField(null=True, blank=True) # 最後同步時間

    ip_address='10.250.120.100',```

    ssh_username='admin',

    ssh_password='password',### IPXELog

    docker_container_mac='ipxe_mac-flask',

    docker_container_ipxe='ipxe'**關鍵欄位**：

)```python

print(f'Server ID: {server.id}')class IPXELog(models.Model):

"    server = ForeignKey(IPXEServer)

    log_type = CharField(max_length=10)     # 'mac' or 'boot'

# 等待 35 秒    timestamp = DateTimeField()

sleep 35    client_ip = GenericIPAddressField()

    action = CharField(max_length=50)       # 例如: 'get_mac', 'register_mac'

# 檢查日誌    raw_log = TextField()

grep "Server: Test Server" logs/django.log```

```

**日誌類型**：

#### 2. 測試定期任務- **MAC**：MAC 地址管理日誌（註冊、查詢等）

- **BOOT**：開機日誌（iPXE 啟動記錄）

```bash

# 查看任務狀態---

docker exec nt-django python manage.py shell -c "

from django_celery_beat.models import PeriodicTask## 🚀 使用指南



task = PeriodicTask.objects.get(name='sync-all-ipxe-logs-every-10-minutes')### 新增 iPXE Server

print(f'Enabled: {task.enabled}')

print(f'Last Run: {task.last_run_at}')1. **通過 Django Admin 或 API 創建**：

print(f'Total Runs: {task.total_run_count}')   ```python

"   from api.models import IPXEServer

```   

   server = IPXEServer.objects.create(

#### 3. 測試手動觸發       name='10.250.120.2',

       ip_address='10.250.120.2',

```bash       ssh_username='rvt',

docker exec nt-django python manage.py shell -c "       ssh_password='your_password',

from api.signals import trigger_ipxe_logs_sync_for_server       docker_container_mac='ipxe_mac-flask',

       docker_container_ipxe='ipxe',

task_id = trigger_ipxe_logs_sync_for_server(server_id=4, delay_seconds=0)       status='online'

print(f'Task ID: {task_id}')   )

"   ```

```

2. **自動發生的事情**：

## 🔧 配置管理   - ✅ Django Signal 自動觸發

   - ✅ 30 秒後開始首次日誌收集

### 調整收集頻率   - ✅ 日誌收集完成後，`last_sync_at` 更新

   - ✅ 之後每 10 分鐘自動同步一次

```bash

# 改為每 15 分鐘### 手動觸發同步

docker exec nt-django python manage.py shell -c "

from django_celery_beat.models import PeriodicTask, CrontabSchedule**方法 1：使用 Signal 輔助函數**

```python

schedule, _ = CrontabSchedule.objects.get_or_create(from api.signals import trigger_ipxe_logs_sync_for_server

    minute='*/15', hour='*', timezone='Asia/Taipei'

)# 立即同步 Server ID=4，收集 2000 條日誌

task_id = trigger_ipxe_logs_sync_for_server(

task = PeriodicTask.objects.get(name='sync-all-ipxe-logs-every-10-minutes')    server_id=4,

task.crontab = schedule    delay_seconds=0,

task.save()    limit=2000

")

``````



### 調整收集數量**方法 2：直接調用 Celery Task**

```python

```bashfrom api.tasks import sync_ipxe_logs_task

# 改為每次 2000 條

docker exec nt-django python manage.py shell -c "result = sync_ipxe_logs_task.apply_async(

from django_celery_beat.models import PeriodicTask    args=[4],

import json    kwargs={'limit': 1000},

    countdown=0

task = PeriodicTask.objects.get(name='sync-all-ipxe-logs-every-10-minutes'))

task.kwargs = json.dumps({'limit': 2000})```

task.save()

"**方法 3：使用 Django 管理命令**

``````bash

docker exec nt-django python manage.py collect_ipxe_logs --server 4 --limit 2000

### 停用/啟用自動同步```



```bash### 監控同步狀態

# 停用

docker exec nt-django python manage.py shell -c "**檢查伺服器狀態**：

from django_celery_beat.models import PeriodicTask```bash

task = PeriodicTask.objects.get(name='sync-all-ipxe-logs-every-10-minutes')docker exec nt-django python manage.py shell -c "

task.enabled = Falsefrom api.models import IPXEServer, IPXELog

task.save()

"server = IPXEServer.objects.get(id=4)

log_count = IPXELog.objects.filter(server=server).count()

# 啟用

docker exec nt-django python manage.py shell -c "print(f'Server: {server.name}')

from django_celery_beat.models import PeriodicTaskprint(f'Status: {server.status}')

task = PeriodicTask.objects.get(name='sync-all-ipxe-logs-every-10-minutes')print(f'Last Sync: {server.last_sync_at}')

task.enabled = Trueprint(f'Total Logs: {log_count}')

task.save()"

"```

```

**查看定期任務執行記錄**：

## 📝 日誌記錄```bash

docker exec nt-django python manage.py shell -c "

### 日誌位置from django_celery_results.models import TaskResult



- **容器內**：`/app/logs/django.log`# 最近 5 次 iPXE 同步任務

- **主機上**：`./logs/django.log`results = TaskResult.objects.filter(

    task_name='api.tasks.sync_all_ipxe_logs_task'

### 日誌範例).order_by('-date_done')[:5]



```logfor r in results:

[INFO] [Signal] 偵測到新建 iPXE Server: 10.250.120.2 (10.250.120.2)    print(f'{r.date_done} | {r.status} | {r.result[:100]}...')

[INFO] [Signal] 排程首次日誌收集任務 - Server ID: 4"

[INFO] [Signal] 首次日誌收集任務已排程 - Server: 10.250.120.2```



[INFO] [Celery] 開始同步 iPXE 日誌 - Server ID: 4, Limit: 1000---

[INFO] [Celery] iPXE 日誌同步完成 - Server: 10.250.120.2 | MAC 日誌: 997 條 | BOOT 日誌: 1000 條 | 總計: 1997 條

## 🔍 故障排查

[INFO] [Celery] 開始批次同步所有 iPXE Server 的日誌 (limit=1000)

[INFO] [Celery] 找到 4 個在線的 iPXE Server### 問題：新伺服器沒有收集到日誌

[INFO] [Celery] 批次同步完成 - 總計: 4 個 | 成功: 4 個 | 失敗: 0 個 | 新增日誌: 392 條

```**可能原因**：

1. SSH 憑證錯誤

### 查看日誌2. Docker 容器名稱錯誤

3. 容器內沒有日誌

```bash

# 即時查看**排查步驟**：

tail -f logs/django.log | grep "iPXE"

```bash

# 查看錯誤# 1. 檢查伺服器配置

grep "ERROR" logs/django_error.log | grep "iPXE"docker exec nt-django python manage.py shell -c "

from api.models import IPXEServer

# 查看最近同步記錄s = IPXEServer.objects.get(id=4)

grep "iPXE 日誌同步完成" logs/django.log | tail -10print(f'IP: {s.ip_address}')

```print(f'User: {s.ssh_username}')

print(f'MAC Container: {s.docker_container_mac}')

## 🔍 故障排查print(f'IPXE Container: {s.docker_container_ipxe}')

"

### 問題 1：新增伺服器後沒有自動同步

# 2. 測試 SSH 連接

**檢查步驟**：ssh rvt@10.250.120.2



1. 確認 Signal 是否觸發：# 3. 檢查容器是否存在

   ```bashdocker ps | grep -E "ipxe_mac|ipxe"

   grep "偵測到新建 iPXE Server" logs/django.log | tail -5

   ```# 4. 檢查容器日誌

docker logs --tail 10 ipxe_mac-flask

2. 確認任務是否提交：docker logs --tail 10 ipxe

   ```bash

   grep "排程首次日誌收集任務" logs/django.log | tail -5# 5. 查看 Celery 日誌

   ```docker compose logs celery_worker --tail 50

```

3. 確認 Celery Worker 運行：

   ```bash### 問題：定期任務未執行

   docker compose ps celery_worker

   docker compose logs celery_worker --tail 50**檢查步驟**：

   ```

```bash

**常見原因**：# 1. 確認定期任務已啟用

- SSH 密碼未設定docker exec nt-django python manage.py shell -c "

- Celery Worker 未運行from django_celery_beat.models import PeriodicTask

- 任務執行失敗（查看 error 日誌）task = PeriodicTask.objects.get(name='sync-all-ipxe-logs-every-10-minutes')

print(f'Enabled: {task.enabled}')

### 問題 2：定期任務沒有執行print(f'Schedule: {task.crontab}')

"

**檢查步驟**：

# 2. 檢查 Celery Beat 服務

1. 確認 Celery Beat 運行：docker compose ps celery_beat

   ```bash

   docker compose ps celery_beat# 3. 查看 Beat 日誌

   ```docker compose logs celery_beat --tail 50



2. 確認任務啟用：# 4. 重啟 Celery 服務

   ```bashdocker compose restart celery_worker celery_beat

   docker exec nt-django python manage.py shell -c "```

   from django_celery_beat.models import PeriodicTask

   task = PeriodicTask.objects.get(name='sync-all-ipxe-logs-every-10-minutes')### 問題：日誌重複或缺失

   print(f'Enabled: {task.enabled}')

   "**原因**：

   ```- IPXELog 沒有唯一性約束，可能重複收集

- 容器日誌輪替導致舊日誌丟失

3. 查看 Celery Beat 日誌：

   ```bash**解決方案**：

   docker compose logs celery_beat --tail 50```python

   ```# 在 IPXELog 模型添加唯一性約束（未來改進）

class Meta:

**解決方法**：    unique_together = ['server', 'timestamp', 'client_ip', 'action']

```bash```

# 重啟 Celery Beat

docker compose restart celery_beat---

```

## 📝 日誌記錄

### 問題 3：任務執行失敗

### 日誌位置

**檢查步驟**：

**容器內**：`/app/logs/`

1. 查看錯誤日誌：**主機**：`./logs/`

   ```bash

   grep "同步 iPXE 日誌失敗" logs/django_error.log | tail -10**相關日誌檔案**：

   ```- `django.log` - 一般應用程式日誌

- `django_error.log` - 錯誤日誌

2. 測試 SSH 連接：- `celery_health.log` - Celery 健康檢查

   ```bash

   ssh rvt@10.250.120.2### 日誌範例

   ```

**Signal 觸發**：

3. 檢查容器：```

   ```bash[INFO] api.signals: [Signal] 偵測到新建 iPXE Server: 10.250.120.2 (10.250.120.2)

   ssh rvt@10.250.120.2 "docker ps | grep ipxe"[INFO] api.signals: [Signal] 排程首次日誌收集任務 - Server ID: 4

   ```[INFO] api.signals: [Signal] 首次日誌收集任務已排程 - Server: 10.250.120.2

```

4. 手動執行測試：

   ```bash**任務執行**：

   docker exec nt-django python manage.py collect_ipxe_logs --server 4 --verbose```

   ```[INFO] api.tasks: [Celery] 開始同步 iPXE 日誌 - Server ID: 4, Limit: 1000

[INFO] api.tasks: [Celery] iPXE 日誌同步完成 - Server: 10.250.120.2 | MAC 日誌: 997 條 | BOOT 日誌: 1000 條 | 總計: 1997 條

**常見原因**：```

- SSH 連接失敗（密碼錯誤、網路問題）

- Docker 容器名稱錯誤**批次同步**：

- 容器內沒有日誌檔案```

[INFO] api.tasks: [Celery] 開始批次同步所有 iPXE Server 的日誌 (limit=1000)

## 🔄 與 DHCP 功能對比[INFO] api.tasks: [Celery] 找到 4 個在線的 iPXE Server

[INFO] api.tasks: [Celery] 批次同步完成 - 總計: 4 個 | 成功: 4 個 | 失敗: 0 個 | 新增日誌: 3542 條

| 功能 | DHCP | iPXE | 狀態 |```

|------|------|------|------|

| 定期任務 | ✅ 每 10 分鐘 | ✅ 每 10 分鐘 | 一致 |---

| 新增自動同步 | ✅ 延遲 10-60s | ✅ 延遲 30s | 一致 |

| 失敗重試 | ✅ 3 次 | ✅ 3 次 | 一致 |## 🔗 相關文件

| 日誌記錄 | ✅ 詳細 | ✅ 詳細 | 一致 |

| 手動觸發 | ✅ | ✅ | 一致 |- [快速開始指南](./QUICKSTART.md) - 如何快速使用此功能

| Celery 任務 | ✅ | ✅ | 一致 |- [測試指南](./TESTING_GUIDE.md) - 如何測試自動同步功能

| Django Signal | ✅ | ✅ | 一致 |- [解決方案總結](./SOLUTION_SUMMARY.md) - 問題解決過程記錄



## 📈 性能考量---



### 資源使用## 📌 注意事項



- **CPU**：SSH 連接和日誌解析（中等）1. **SSH 憑證安全**：

- **記憶體**：日誌暫存（每次約 1000-2000 條，低）   - 密碼存儲在資料庫中（未加密）

- **網路**：SSH 傳輸（低）   - 生產環境建議使用 SSH Key

- **資料庫**：批次寫入（中等）   - 考慮使用 Django 的 `EncryptedCharField`



### 優化建議2. **日誌數量限制**：

   - 預設每次收集 1000 條日誌

1. **調整收集數量**：   - 首次收集建議增加 limit（例如 2000）

   - 伺服器負載高 → 減少 `limit`   - 避免一次收集過多導致超時

   - 伺服器負載低 → 增加 `limit`

3. **容器名稱**：

2. **調整執行頻率**：   - 必須與實際 Docker 容器名稱一致

   - 日誌變化快 → 保持 10 分鐘   - 不同環境可能有不同命名（開發/生產）

   - 日誌變化慢 → 改為 15-30 分鐘

4. **時區設定**：

3. **錯峰執行**：   - 所有時間使用 `Asia/Taipei` 時區

   ```python   - 確保 Docker Compose 設定正確：`TZ=Asia/Taipei`

   # DHCP: 每 10 分鐘（00, 10, 20, ...）

   # iPXE: 改為偏移 5 分鐘（05, 15, 25, ...）5. **性能考量**：

   CrontabSchedule(minute='5,15,25,35,45,55', hour='*')   - 每 10 分鐘同步所有伺服器

   ```   - 如果伺服器數量很多，考慮增加間隔時間

   - 監控 Celery Worker 的負載

## 📚 相關文檔

---

- **[QUICKSTART.md](./QUICKSTART.md)** - 5 分鐘快速上手

- **[SOLUTION_SUMMARY.md](./SOLUTION_SUMMARY.md)** - 問題解決總結**最後更新**：2025-11-07  

- **[DHCP 自動同步](../auto-switch-sync/README.md)** - DHCP 功能參考**維護者**：Network Toolbox Team  

**版本**：1.0.0

## 🎯 未來優化

1. **監控增強**：
   - 連續失敗告警
   - 同步狀態儀表板

2. **數據清理**：
   - 自動清理舊日誌（30 天）
   - 定期彙總統計

3. **性能優化**：
   - 並行處理多個容器
   - 增量同步機制

---

**版本**：1.0.0  
**最後更新**：2025-11-07  
**維護者**：Network Toolbox Team
