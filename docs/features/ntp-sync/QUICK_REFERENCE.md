# NTP 定時自動同步 - 快速參考

## 🚀 一鍵設置

```bash
sudo ./scripts/setup_ntp_auto_sync.sh
```

---

## 📋 核心功能

| 功能 | 說明 | 頻率 |
|------|------|------|
| **check_ntp_sync_task** | NTP 檢測（監控） | 每 5 分鐘 |
| **sync_ntp_time_task** | NTP 自動同步 ⭐ | 每天凌晨 3:00 |
| **systemd-timesyncd** | 主機層級同步 | 持續（32~1024秒） |

---

## 💡 智能決策

```
時間偏移 > 200ms ？
    ↓ Yes
距離上次同步 ≥ 30 分鐘 ？
    ↓ Yes
執行 ntpdate 同步
```

---

## 📊 快速查詢

### 查看定時任務

```bash
docker exec nt-django python manage.py shell -c "
from django_celery_beat.models import PeriodicTask
for t in PeriodicTask.objects.filter(name__icontains='NTP'):
    print(f'{t.name}: {\"啟用\" if t.enabled else \"停用\"}')"
```

### 查看最新同步

```bash
docker exec nt-django python manage.py shell -c "
from api.models import NTPSyncOperation
op = NTPSyncOperation.objects.order_by('-timestamp').first()
print(f'時間: {op.timestamp}')
print(f'狀態: {op.status}')
print(f'改善: {op.improvement:.3f}ms')"
```

### 手動測試

```bash
docker exec nt-django python -c "
from api.tasks import sync_ntp_time_task
result = sync_ntp_time_task()
print(result)"
```

---

## ⚙️ 常用操作

### 停用任務

```bash
docker exec nt-django python manage.py shell -c "
from django_celery_beat.models import PeriodicTask
t = PeriodicTask.objects.get(name='NTP 時間自動同步（每天凌晨）')
t.enabled = False
t.save()"
```

### 啟用任務

```bash
docker exec nt-django python manage.py shell -c "
from django_celery_beat.models import PeriodicTask
t = PeriodicTask.objects.get(name='NTP 時間自動同步（每天凌晨）')
t.enabled = True
t.save()"
```

### 修改執行時間

```bash
# 改為凌晨 2:00
docker exec nt-django python manage.py shell -c "
from django_celery_beat.models import PeriodicTask, CrontabSchedule
s = CrontabSchedule.objects.create(minute='0', hour='2', day_of_week='*')
t = PeriodicTask.objects.get(name='NTP 時間自動同步（每天凌晨）')
t.crontab = s
t.save()"
```

---

## 🎯 推薦配置

### 生產環境 ✨

```bash
# 1. 主機層級同步（穩定）
sudo ./scripts/setup_ntp_sync.sh

# 2. 應用層級監控（啟用）
# check_ntp_sync_task 預設已啟用

# 3. 應用層級同步（停用）
# 交給主機處理，更可靠
```

### 開發環境

```bash
# 1. 設置定時任務
docker exec nt-django python backend/setup_ntp_sync_task.py

# 2. 配置 sudo 權限
# 參考：docs/features/ntp-sync/SUDO_PERMISSION_SETUP.md

# 3. 重建容器
docker compose build django
docker compose up -d
```

---

## 📁 文檔索引

| 文檔 | 說明 |
|------|------|
| **SCHEDULED_SYNC_SOLUTION.md** | 完整方案總覽 ⭐ |
| **AUTO_SYNC_FEATURE.md** | 功能詳細說明 |
| **HOST_NTP_SETUP_GUIDE.md** | 主機同步指南 |
| **SUDO_PERMISSION_SETUP.md** | Sudo 權限配置 |
| **README.md** | 功能導航 |

---

## 🔍 監控位置

- **前端**：系統監控 → NTP 時間自動同步
- **後端**：`NTPSyncOperation` 資料表
- **日誌**：`docker compose logs django | grep -i ntp`

---

**快速參考 v1.0** | 2025-11-25
