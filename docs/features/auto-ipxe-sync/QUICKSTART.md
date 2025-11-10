# iPXE 日誌自動同步 - 快速開始指南# iPXE 日誌自動同步 - 快速開始指南



## 🚀 5 分鐘快速上手## 🎯 目標



### 功能說明讓您在 **5 分鐘內**：

1. ✅ 了解如何新增 iPXE Server

當您新增一個 iPXE Server 時，系統會**自動**：2. ✅ 確認自動同步功能正常工作

1. ✅ **30 秒後**開始首次日誌收集3. ✅ 查看收集到的日誌

2. ✅ **每 10 分鐘**自動同步最新日誌

3. ✅ **失敗自動重試**（最多 3 次）---



**您不需要做任何額外操作！**## 🚀 步驟 1：新增 iPXE Server



## 📝 使用場景### 方法 A：通過 Django Admin（推薦）



### 場景 1：新增 iPXE Server1. **訪問 Django Admin**：

   ```

**步驟**：   http://localhost/admin/api/ipxeserver/

1. 在管理後台創建 IPXEServer   ```

2. 填寫必要資訊（IP、SSH 帳密、容器名稱）

3. 儲存2. **點擊「新增 IPXE Server」**



**結果**：3. **填寫表單**：

- 30 秒後自動開始收集日誌   ```

- 可在「iPXE 日誌查看」頁面看到數據   名稱: 10.250.120.2

   IP 地址: 10.250.120.2

**範例**：   SSH 使用者名稱: rvt

```python   SSH 密碼: your_password

# 透過 Django Admin 或 API 創建   Docker 容器 (MAC): ipxe_mac-flask

IPXEServer.objects.create(   Docker 容器 (IPXE): ipxe

    name='10.250.120.2',   狀態: online

    ip_address='10.250.120.2',   ```

    ssh_username='rvt',

    ssh_password='your_password',4. **點擊「儲存」**

    docker_container_mac='ipxe_mac-flask',

    docker_container_ipxe='ipxe',### 方法 B：通過 Python Shell

    status='online'

)```bash

docker exec -it nt-django python manage.py shell

# 30 秒後自動開始收集日誌 ✅```

```

```python

### 場景 2：查看同步狀態from api.models import IPXEServer



**方法 1：透過 Django Admin**server = IPXEServer.objects.create(

1. 進入「iPXE Servers」列表    name='10.250.120.2',

2. 查看「Last Sync At」欄位    ip_address='10.250.120.2',

3. 查看「Status」是否為 online    ssh_username='rvt',

    ssh_password='your_password',

**方法 2：透過 Shell**    docker_container_mac='ipxe_mac-flask',

```bash    docker_container_ipxe='ipxe',

docker exec nt-django python manage.py shell -c "    status='online'

from api.models import IPXEServer, IPXELog)



server = IPXEServer.objects.get(id=4)print(f'✅ 創建成功！Server ID: {server.id}')

log_count = IPXELog.objects.filter(server=server).count()```



print(f'Server: {server.name}')---

print(f'Status: {server.status}')

print(f'Last Sync: {server.last_sync_at}')## ⏰ 步驟 2：等待自動同步（30 秒）

print(f'Total Logs: {log_count}')

"創建伺服器後：

```

1. **Django Signal 自動觸發**（立即）

**方法 3：查看前端頁面**2. **首次日誌收集排程**（30 秒延遲）

- 進入「iPXE 分析」頁面3. **任務開始執行**（約 30-60 秒後完成）

- 選擇伺服器

- 切換到「iPXE日誌查看」標籤**為什麼要等待？**

- 給您時間確認 SSH 憑證正確

### 場景 3：手動立即同步- 確保資料庫事務完全提交

- 避免立即執行可能失敗的任務

如果您不想等待 30 秒或 10 分鐘，可以手動觸發：

**可以喝杯咖啡或查看日誌** ☕

```bash

# 方法 1：使用 Signal 函數（推薦）---

docker exec nt-django python manage.py shell -c "

from api.signals import trigger_ipxe_logs_sync_for_server## 📊 步驟 3：查看同步結果



# 立即為 Server 4 收集 2000 條日誌### 快速檢查（推薦）

task_id = trigger_ipxe_logs_sync_for_server(

    server_id=4,```bash

    delay_seconds=0,docker exec nt-django python manage.py shell -c "

    limit=2000from api.models import IPXEServer, IPXELog

)

# 替換成您的 Server ID

print(f'任務已提交，Task ID: {task_id}')server = IPXEServer.objects.get(id=4)

print('請等待 30-60 秒查看結果')

"# 統計日誌

mac_logs = IPXELog.objects.filter(server=server, log_type='MAC').count()

# 方法 2：使用管理命令boot_logs = IPXELog.objects.filter(server=server, log_type='BOOT').count()

docker exec nt-django python manage.py collect_ipxe_logs --server 4 --limit 2000 --verbosetotal = IPXELog.objects.filter(server=server).count()

```

print(f'📊 Server: {server.name}')

## ⚙️ 配置調整print(f'   Status: {server.status}')

print(f'   Last Sync: {server.last_sync_at}')

### 調整收集頻率print(f'   MAC 日誌: {mac_logs} 條')

print(f'   BOOT 日誌: {boot_logs} 條')

**預設**：每 10 分鐘print(f'   總計: {total} 條')

"

**如何修改**：```

```bash

docker exec nt-django python manage.py shell -c "**預期輸出**：

from django_celery_beat.models import PeriodicTask, CrontabSchedule```

📊 Server: 10.250.120.2

# 創建新的排程（例如：每 15 分鐘）   Status: online

schedule, _ = CrontabSchedule.objects.get_or_create(   Last Sync: 2025-11-07 00:50:05+00:00

    minute='*/15',   MAC 日誌: 997 條

    hour='*',   BOOT 日誌: 1000 條

    timezone='Asia/Taipei'   總計: 1997 條

)```



# 更新任務排程### 查看最新日誌

task = PeriodicTask.objects.get(name='sync-all-ipxe-logs-every-10-minutes')

task.crontab = schedule```bash

task.save()docker exec nt-django python manage.py shell -c "

from api.models import IPXELog

print('已更新為每 15 分鐘執行')

"# 最近 10 條日誌

```logs = IPXELog.objects.filter(server_id=4).order_by('-timestamp')[:10]



### 調整收集數量print('📋 最近 10 條日誌:')

for log in logs:

**預設**：每次每個容器收集 1000 條日誌    print(f'   [{log.log_type}] {log.timestamp} | {log.client_ip} | {log.action}')

"

**如何修改**：```

```bash

docker exec nt-django python manage.py shell -c "### 通過 Django Admin 查看

from django_celery_beat.models import PeriodicTask

import json訪問：

```

task = PeriodicTask.objects.get(name='sync-all-ipxe-logs-every-10-minutes')http://localhost/admin/api/ipxelog/?server__id=4

task.kwargs = json.dumps({'limit': 2000})  # 改為 2000```

task.save()

---

print('已更新為每次收集 2000 條')

"## 🔄 步驟 4：驗證定期同步

```

### 確認定期任務已啟用

### 停用自動同步

```bash

如果需要暫時停用：docker exec nt-django python manage.py shell -c "

```bashfrom django_celery_beat.models import PeriodicTask

docker exec nt-django python manage.py shell -c "

from django_celery_beat.models import PeriodicTasktask = PeriodicTask.objects.get(name='sync-all-ipxe-logs-every-10-minutes')



task = PeriodicTask.objects.get(name='sync-all-ipxe-logs-every-10-minutes')print(f'📋 定期任務狀態:')

task.enabled = Falseprint(f'   名稱: {task.name}')

task.save()print(f'   排程: {task.crontab}')

print(f'   啟用: {task.enabled}')

print('自動同步已停用')print(f'   參數: {task.kwargs}')

""

```

# 重新啟用

docker exec nt-django python manage.py shell -c "**預期輸出**：

from django_celery_beat.models import PeriodicTask```

📋 定期任務狀態:

task = PeriodicTask.objects.get(name='sync-all-ipxe-logs-every-10-minutes')   名稱: sync-all-ipxe-logs-every-10-minutes

task.enabled = True   排程: */10 * * * * (m/h/dM/MY/d) Asia/Taipei

task.save()   啟用: True

   參數: {"limit": 1000}

print('自動同步已啟用')```

"

```### 查看最近執行記錄



## 🔍 監控和檢查```bash

docker exec nt-django python manage.py shell -c "

### 查看最近同步記錄from django_celery_results.models import TaskResult



```bash# 最近 5 次執行

# 查看日誌results = TaskResult.objects.filter(

tail -f logs/django.log | grep "iPXE 日誌同步"    task_name='api.tasks.sync_all_ipxe_logs_task'

).order_by('-date_done')[:5]

# 查看 Celery 任務執行歷史

docker exec nt-django python manage.py shell -c "print('📜 最近 5 次執行記錄:')

from django_celery_results.models import TaskResultfor r in results:

    status_icon = '✅' if r.status == 'SUCCESS' else '❌'

results = TaskResult.objects.filter(    print(f'   {status_icon} {r.date_done} | {r.status}')

    task_name='api.tasks.sync_all_ipxe_logs_task'"

).order_by('-date_done')[:5]```



for result in results:---

    print(f'Time: {result.date_done}')

    print(f'Status: {result.status}')## ✅ 成功標準

    print(f'Result: {result.result[:200]}')

    print('---')### 檢查清單

"

```- [ ] **伺服器已創建**：`IPXEServer.objects.get(id=4)` 存在

- [ ] **首次同步完成**：`last_sync_at` 不為 `None`

### 檢查定期任務狀態- [ ] **日誌已收集**：`IPXELog.objects.filter(server_id=4).count() > 0`

- [ ] **定期任務啟用**：`PeriodicTask` 的 `enabled=True`

```bash- [ ] **Celery Worker 運行中**：`docker compose ps celery_worker`

docker exec nt-django python manage.py shell -c "

from django_celery_beat.models import PeriodicTask### 一鍵驗證腳本



task = PeriodicTask.objects.get(name='sync-all-ipxe-logs-every-10-minutes')創建 `test_ipxe_auto_sync.sh`：



print(f'任務名稱: {task.name}')```bash

print(f'啟用狀態: {task.enabled}')#!/bin/bash

print(f'上次執行: {task.last_run_at}')

print(f'總執行次數: {task.total_run_count}')echo "🔍 檢查 iPXE 自動同步功能..."

print(f'下次執行: 查看 Celery Beat 日誌')echo ""

"

# 檢查伺服器

# 查看 Celery Beat 日誌echo "1️⃣ 檢查伺服器狀態..."

docker compose logs celery_beat --tail 20docker exec nt-django python manage.py shell -c "

```from api.models import IPXEServer

servers = IPXEServer.objects.all()

### 查看所有伺服器狀態print(f'   找到 {servers.count()} 個 iPXE Server')

for s in servers:

```bash    print(f'   - {s.name} ({s.ip_address}) | Status: {s.status} | Last Sync: {s.last_sync_at}')

docker exec nt-django python manage.py shell -c ""

from api.models import IPXEServer, IPXELog

from django.db.models import Countecho ""

echo "2️⃣ 檢查日誌數量..."

servers = IPXEServer.objects.annotate(docker exec nt-django python manage.py shell -c "

    log_count=Count('logs')from api.models import IPXELog

).order_by('ip_address')from collections import Counter



print('📊 所有 iPXE Server 狀態:\n')servers_logs = IPXELog.objects.values('server__name').annotate(count=Count('id'))

for server in servers:for item in servers_logs:

    print(f'{server.name} ({server.ip_address})')    print(f'   - {item[\"server__name\"]}: {item[\"count\"]} 條日誌')

    print(f'  Status: {server.status}')"

    print(f'  Last Sync: {server.last_sync_at}')

    print(f'  Total Logs: {server.log_count}')echo ""

    print()echo "3️⃣ 檢查定期任務..."

"docker exec nt-django python manage.py shell -c "

```from django_celery_beat.models import PeriodicTask

task = PeriodicTask.objects.get(name='sync-all-ipxe-logs-every-10-minutes')

## ⚠️ 常見問題print(f'   任務: {task.name}')

print(f'   啟用: {\"✅\" if task.enabled else \"❌\"}')

### Q1：新增伺服器後沒有自動收集日誌print(f'   排程: {task.crontab}')

"

**檢查清單**：

1. ✅ 確認 SSH 密碼已設定echo ""

2. ✅ 確認容器名稱正確echo "4️⃣ 檢查 Celery 服務..."

3. ✅ 確認 Celery Worker 正在運行：`docker compose ps celery_worker`docker compose ps celery_worker celery_beat

4. ✅ 查看日誌：`grep "偵測到新建 iPXE Server" logs/django.log`

echo ""

**解決方法**：echo "✅ 檢查完成！"

```bash```

# 手動觸發一次

docker exec nt-django python manage.py shell -c "執行：

from api.signals import trigger_ipxe_logs_sync_for_server```bash

trigger_ipxe_logs_sync_for_server(server_id=YOUR_SERVER_ID, delay_seconds=0)chmod +x test_ipxe_auto_sync.sh

"./test_ipxe_auto_sync.sh

``````



### Q2：日誌收集失敗---



**可能原因**：## 🎓 常見問題

1. SSH 連接失敗（密碼錯誤、網路問題）

2. Docker 容器名稱錯誤### Q1: 為什麼等了 30 秒還沒有日誌？

3. 容器內沒有日誌檔案

**A**: 可能原因：

**排查步驟**：1. SSH 憑證錯誤 → 檢查 `ssh_password` 是否正確

```bash2. 容器名稱錯誤 → 確認 Docker 容器名稱

# 1. 測試 SSH 連接3. Celery Worker 未運行 → 執行 `docker compose ps celery_worker`

ssh rvt@10.250.120.2

**排查方法**：

# 2. 檢查容器是否存在```bash

ssh rvt@10.250.120.2 "docker ps | grep ipxe"# 查看 Celery Worker 日誌

docker compose logs celery_worker --tail 50 | grep -i ipxe

# 3. 手動執行命令查看詳細錯誤

docker exec nt-django python manage.py collect_ipxe_logs --server 4 --verbose# 查看 Django 錯誤日誌

```tail -f logs/django_error.log

```

### Q3：定期任務沒有執行

### Q2: 可以立即執行同步，不要等 30 秒嗎？

**檢查步驟**：

```bash**A**: 可以！使用手動觸發：

# 1. 確認 Celery Beat 運行

docker compose ps celery_beat```python

from api.signals import trigger_ipxe_logs_sync_for_server

# 2. 確認任務已啟用

docker exec nt-django python manage.py shell -c "# 立即執行（delay=0）

from django_celery_beat.models import PeriodicTasktask_id = trigger_ipxe_logs_sync_for_server(

task = PeriodicTask.objects.get(name='sync-all-ipxe-logs-every-10-minutes')    server_id=4,

print(f'Enabled: {task.enabled}')    delay_seconds=0,

"    limit=2000

)

# 3. 重啟 Celery Beat```

docker compose restart celery_beat

```### Q3: 如何增加收集的日誌數量？



## 📚 進階操作**A**: 修改定期任務的 `limit` 參數：



### 批次處理多個伺服器```bash

docker exec nt-django python manage.py shell -c "

```bashfrom django_celery_beat.models import PeriodicTask

# 一次性為所有伺服器收集日誌import json

docker exec nt-django python manage.py collect_ipxe_logs --verbose

```task = PeriodicTask.objects.get(name='sync-all-ipxe-logs-every-10-minutes')

task.kwargs = json.dumps({'limit': 2000})  # 增加到 2000

### 查看特定時間範圍的日誌task.save()



```pythonprint('✅ 已更新 limit 為 2000')

# 透過 Django Shell"

from api.models import IPXELog```

from django.utils import timezone

from datetime import timedelta### Q4: 日誌會一直累積嗎？需要清理嗎？



# 最近 1 小時的日誌**A**: 是的，日誌會累積。可以使用清理命令：

one_hour_ago = timezone.now() - timedelta(hours=1)

recent_logs = IPXELog.objects.filter(```bash

    timestamp__gte=one_hour_ago# 清理 15 天前的舊日誌（預設）

).count()docker exec nt-django python manage.py cleanup_ipxe_logs



print(f'最近 1 小時的日誌: {recent_logs} 條')# 清理 7 天前的日誌

```docker exec nt-django python manage.py cleanup_ipxe_logs --days 7



### 清理舊日誌# 清理特定伺服器的日誌

docker exec nt-django python manage.py cleanup_ipxe_logs --server 4 --days 7

```bash```

# 清理 15 天前的日誌

docker exec nt-django python manage.py cleanup_ipxe_logs --days 15---

```

## 🔗 下一步

## 🎯 最佳實踐

- 📖 閱讀[完整技術文檔](./README.md)了解詳細架構

1. **新增伺服器時**：- 🧪 閱讀[測試指南](./TESTING_GUIDE.md)學習如何測試

   - 確保 SSH 資訊正確- 📝 查看[解決方案總結](./SOLUTION_SUMMARY.md)了解問題解決過程

   - 使用有意義的名稱（如 IP 地址）

   - 等待 30 秒後檢查是否有日誌---



2. **監控建議**：**最後更新**：2025-11-07  

   - 每天查看一次 `last_sync_at`**預估完成時間**：5 分鐘  

   - 定期檢查 `logs/django_error.log`**難度**：⭐⭐☆☆☆（簡單）

   - 使用前端頁面監控日誌數量

3. **性能優化**：
   - 如果伺服器多，可增加 `limit` 減少執行頻率
   - 定期清理舊日誌釋放空間
   - 錯峰執行（與 DHCP 同步錯開）

## 📞 需要幫助？

- 查看完整技術文檔：[README.md](./README.md)
- 查看測試指南：[TESTING_GUIDE.md](./TESTING_GUIDE.md)
- 查看日誌：`tail -f logs/django.log`

---

**版本**：1.0.0  
**更新日期**：2025-11-07
