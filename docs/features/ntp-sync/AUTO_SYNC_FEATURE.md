# NTP 定時自動同步功能說明

## 📋 功能概述

新增 **NTP 時間自動同步** 定時任務，實現智能化的時間同步管理。

---

## ⭐ 新增功能

### Celery 定時任務：`sync_ntp_time_task`

**執行頻率**：每天凌晨 3:00

**智能決策機制**：

1. **前置檢查**：
   - ✅ 檢查是否允許同步（距離上次同步 ≥ 30 分鐘）
   - ✅ 檢查是否需要同步（時間偏移 > 200ms）

2. **執行同步**：
   - ✅ 只有通過兩項檢查才會實際執行
   - ✅ 使用 `ntpdate -u 10.10.10.51` 命令
   - ✅ 記錄同步前後的時間偏移量

3. **記錄操作**：
   - ✅ 所有同步操作記錄到 `NTPSyncOperation` 表
   - ✅ 包含：偏移量、改善量、執行時間、狀態等

---

## 🎯 使用場景

### 場景 1：獨立使用（需配置 sudo 權限）

**適用**：開發/測試環境

```bash
# 設置定時任務
docker exec nt-django python backend/setup_ntp_sync_task.py

# 配置 sudo 權限（參考 SUDO_PERMISSION_SETUP.md）
# 修改 Dockerfile 和 docker-compose.yml
# 重建容器
```

**優點**：
- ✅ 完全在 Docker 環境內管理
- ✅ 可從 Django 應用內觸發同步

**缺點**：
- ⚠️ 需要配置容器 sudo 權限
- ⚠️ 只影響容器內時間（如果時間命名空間獨立）

### 場景 2：配合主機同步使用（推薦）✨

**適用**：生產環境

```bash
# 1. 設置主機層級同步（一次性）
sudo ./scripts/setup_ntp_sync.sh

# 2. （可選）設置應用層級監控任務
docker exec nt-django python backend/setup_ntp_sync_task.py

# 3. 停用應用層級的實際同步（改為監控模式）
docker exec nt-django python manage.py shell -c "
from django_celery_beat.models import PeriodicTask
task = PeriodicTask.objects.get(name='NTP 時間自動同步（每天凌晨）')
task.enabled = False
task.save()
print('已停用應用層級自動同步')
"
```

**優點**：
- ✅ 主機層級同步穩定可靠
- ✅ 應用層級提供監控和記錄
- ✅ 不需要容器 sudo 權限
- ✅ 所有容器自動繼承主機時間

**工作流程**：
1. `systemd-timesyncd` 在主機層級持續同步時間
2. `check_ntp_sync_task` 每 5 分鐘檢測並記錄（監控）
3. `sync_ntp_time_task` 停用（或僅在極端情況下觸發）

---

## 📊 資料模型

### NTPSyncOperation（新增）

記錄每次 NTP 時間同步操作：

| 欄位 | 類型 | 說明 |
|------|------|------|
| id | Integer | 主鍵 |
| timestamp | DateTime | 操作時間 |
| ntp_server | IPAddress | NTP 伺服器地址 |
| sync_method | String | 同步方法（ntpdate/chrony） |
| triggered_by | String | 觸發方式（auto/manual/alert） |
| status | String | 狀態（pending/success/failed） |
| offset_before | Float | 同步前偏移（ms） |
| offset_after | Float | 同步後偏移（ms） |
| improvement | Float | 改善量（ms） |
| duration | Float | 執行時間（秒） |
| command_output | Text | 命令輸出 |
| error_message | Text | 錯誤訊息 |
| reason | Text | 執行原因 |

### NTPSyncLog（既有）

記錄每次 NTP 檢測：

| 欄位 | 類型 | 說明 |
|------|------|------|
| timestamp | DateTime | 檢測時間 |
| status | String | 狀態（success/failed） |
| ntp_server | IPAddress | NTP 伺服器地址 |
| response_time | Float | 響應時間（ms） |
| offset | Float | 時間偏移（ms） |
| stratum | Integer | Stratum 層級 |
| jitter | Float | 時間抖動（ms） |
| error_message | Text | 錯誤訊息 |

---

## 🛠️ API 說明

### NTPSyncService 類別（擴展）

新增方法：

```python
# 檢查是否允許同步
can_sync, reason = sync_service.can_sync_now()

# 檢查是否需要同步
should_sync, reason, avg_offset = sync_service.should_sync(threshold_ms=200.0)

# 執行系統時間同步
result = sync_service.sync_system_time(method='ntpdate', triggered_by='auto')
```

### Celery 任務

```python
from api.tasks import sync_ntp_time_task

# 手動執行（測試用）
result = sync_ntp_time_task()

# 定時任務會自動執行（每天凌晨 3:00）
```

---

## 🔍 監控與查詢

### 查詢最新同步操作

```bash
docker exec nt-django python manage.py shell -c "
from api.models import NTPSyncOperation

# 最新的同步操作
latest = NTPSyncOperation.objects.order_by('-timestamp').first()

if latest:
    print(f'操作時間: {latest.timestamp}')
    print(f'狀態: {latest.status}')
    print(f'觸發方式: {latest.triggered_by}')
    print(f'同步前偏移: {latest.offset_before:.3f} ms')
    print(f'同步後偏移: {latest.offset_after:.3f} ms')
    print(f'改善量: {latest.improvement:.3f} ms')
    print(f'執行時間: {latest.duration:.2f} 秒')
else:
    print('尚無同步操作記錄')
"
```

### 查詢同步統計

```bash
docker exec nt-django python manage.py shell -c "
from api.models import NTPSyncOperation
from django.db.models import Count, Avg

# 統計
total = NTPSyncOperation.objects.count()
success = NTPSyncOperation.objects.filter(status='success').count()
failed = NTPSyncOperation.objects.filter(status='failed').count()

# 平均改善量
avg_improvement = NTPSyncOperation.objects.filter(
    status='success'
).aggregate(Avg('improvement'))['improvement__avg']

print(f'總操作次數: {total}')
print(f'成功次數: {success} ({success/total*100:.1f}%)' if total > 0 else 'N/A')
print(f'失敗次數: {failed}' if total > 0 else 'N/A')
print(f'平均改善量: {avg_improvement:.3f} ms' if avg_improvement else 'N/A')
"
```

### 前端查看

1. 訪問「系統監控」頁面
2. 查看「最近任務執行記錄」
3. 找到「NTP 時間自動同步」任務
4. 查看執行結果和歷史記錄

---

## ⚙️ 配置參數

### 時間偏移閾值

**預設值**：200ms

**修改方式**：
```python
# 在 tasks.py 的 sync_ntp_time_task 中
should_sync, reason, avg_offset = sync_service.should_sync(
    threshold_ms=200.0  # 修改這個值
)
```

### 最小同步間隔

**預設值**：30 分鐘

**修改方式**：
```python
# 在 ntp_service.py 的 NTPSyncService.can_sync_now() 中
min_interval = timedelta(minutes=30)  # 修改這個值
```

### 執行時間

**預設值**：每天凌晨 3:00

**修改方式**：
```bash
docker exec nt-django python manage.py shell -c "
from django_celery_beat.models import PeriodicTask, CrontabSchedule

# 修改排程（例如：改為凌晨 2:00）
schedule = CrontabSchedule.objects.create(
    minute='0',
    hour='2',
    day_of_week='*',
    day_of_month='*',
    month_of_year='*',
)

task = PeriodicTask.objects.get(name='NTP 時間自動同步（每天凌晨）')
task.crontab = schedule
task.save()
print('已修改為每天凌晨 2:00')
"
```

---

## 📝 執行檢查清單

### 初次設置

- [ ] 執行主機層級設置：`sudo ./scripts/setup_ntp_sync.sh`
- [ ] 驗證主機同步狀態：`timedatectl status`
- [ ] （可選）設置應用層級任務：`docker exec nt-django python backend/setup_ntp_sync_task.py`
- [ ] （可選）配置 sudo 權限：參考 `SUDO_PERMISSION_SETUP.md`

### 日常監控

- [ ] 每週檢查主機同步狀態：`timedatectl timesync-status`
- [ ] 查看 Django NTP 檢測記錄（前端或命令行）
- [ ] 查看應用層級同步操作記錄（如果啟用）

### 故障排查

- [ ] 檢查主機服務：`systemctl status systemd-timesyncd`
- [ ] 檢查 Celery 任務：`docker compose logs django | grep -i ntp`
- [ ] 檢查同步操作記錄：查詢 `NTPSyncOperation` 表
- [ ] 查看詳細日誌：`journalctl -u systemd-timesyncd -n 100`

---

## 🎉 總結

### 新增功能

✅ Celery 定時任務：`sync_ntp_time_task`  
✅ 資料模型：`NTPSyncOperation`  
✅ 智能決策機制（檢查偏移 + 同步間隔）  
✅ 自動化設置腳本：`setup_ntp_sync_task.py`  
✅ 完整文檔：3 份說明文檔  

### 推薦架構

**生產環境**：
1. 主機層級：`systemd-timesyncd` 持續同步 ✅
2. 應用層級：`check_ntp_sync_task` 每 5 分鐘監控 ✅
3. 應用層級：`sync_ntp_time_task` 停用（備用） ⭕

**開發環境**：
1. 應用層級：`check_ntp_sync_task` 每 5 分鐘監控 ✅
2. 應用層級：`sync_ntp_time_task` 每天凌晨同步 ✅
3. 配置容器 sudo 權限 ⚠️

---

**文檔版本**：v1.0  
**最後更新**：2025-11-25  
**作者**：Network Toolbox Team
