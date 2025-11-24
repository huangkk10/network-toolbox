# NTP 自動時間校正系統 - 實施指南（選項 A：sudo 方案）

**實施日期**：2025-11-23  
**方案選擇**：選項 A - sudo 無密碼執行 ntpdate  
**狀態**：📋 實施中

---

## 🎯 實施概要

本文檔詳細說明如何使用 **sudo 無密碼執行 ntpdate** 的方式實施 NTP 自動時間校正系統。

### 為什麼選擇選項 A？

✅ **優點**：
- **安全性高**：只授權特定命令（ntpdate），不開放完整 root 權限
- **實施簡單**：只需配置 sudoers 檔案
- **調試容易**：可以直接在容器內測試命令
- **符合最佳實踐**：生產環境推薦方案

❌ **其他方案的問題**：
- 選項 B（privileged）：過度開放權限，安全風險高
- 選項 C（CAP_SYS_TIME）：需要修改 docker-compose.yml，重啟所有容器

---

## 📋 實施步驟

### Step 1: 安裝 ntpdate（如果尚未安裝）

```bash
# 進入 Django 容器
docker exec -it nt-django bash

# 安裝 ntpdate
apt-get update
apt-get install -y ntpdate

# 驗證安裝
which n## 🚧 部署檢查清單

- [x] **Step 1**: 安裝 ntpdate ✅ (完成於 2025-11-23 14:00)
- [x] **Step 2**: 配置 sudo 權限 ✅ (完成於 2025-11-23 14:00)
- [x] **Step 3**: 更新 Dockerfile 並重建 ✅ (完成於 2025-11-23 14:07)
- [ ] **Step 4**: 創建資料模型 ⏳
- [ ] **Step 5**: 更新 NTPService ⏳
- [ ] **Step 6**: 測試時間同步功能 ⏳
- [ ] **Step 7**: 創建 Celery 任務 ⏳
- [ ] **Step 8**: 註冊 Celery Beat 排程 ⏳
- [ ] **Step 9**: 監控和驗證 ⏳顯示: /usr/sbin/ntpdate
```

---

### Step 2: 配置 sudo 無密碼執行

**2.1 創建 sudoers 配置檔案**

```bash
# 在容器內執行
docker exec -it nt-django bash

# 創建 sudoers.d 目錄（如果不存在）
mkdir -p /etc/sudoers.d

# 創建 ntpdate 專用配置
cat > /etc/sudoers.d/ntpdate << 'EOF'
# Allow Django user to run ntpdate without password
# Created: 2025-11-23
# Purpose: NTP auto sync system

# Django 用戶可以無密碼執行 ntpdate
django ALL=(ALL) NOPASSWD: /usr/sbin/ntpdate

# 或者如果使用 root 用戶運行 Django
root ALL=(ALL) NOPASSWD: /usr/sbin/ntpdate
EOF

# 設置正確的權限（必須是 0440）
chmod 0440 /etc/sudoers.d/ntpdate

# 驗證配置
visudo -c
# 應該顯示: /etc/sudoers.d/ntpdate: parsed OK
```

**2.2 測試 sudo 權限**

```bash
# 在容器內測試（不需要密碼）
sudo ntpdate -q 10.10.10.51

# 應該顯示類似：
# server 10.10.10.51, stratum 3, offset -5.122450, delay 0.02587
# 23 Nov 13:45:30 ntpdate[12345]: adjust time server 10.10.10.51 offset -5.122450 sec
```

**⚠️ 如果遇到 "sudo: no tty present" 錯誤**：

```bash
# 在 /etc/sudoers.d/ntpdate 中添加：
Defaults:django !requiretty
```

---

### Step 3: 持久化配置（修改 Dockerfile）

**3.1 更新 Django Dockerfile**

```dockerfile
# backend/Dockerfile

FROM python:3.11-slim

# ... 現有內容 ...

# ============================================================================
# 安裝 ntpdate 和配置 sudo
# ============================================================================
RUN apt-get update && apt-get install -y \
    ntpdate \
    sudo \
    && rm -rf /var/lib/apt/lists/*

# 創建 sudoers 配置（允許無密碼執行 ntpdate）
RUN echo "root ALL=(ALL) NOPASSWD: /usr/sbin/ntpdate" > /etc/sudoers.d/ntpdate && \
    chmod 0440 /etc/sudoers.d/ntpdate && \
    visudo -c

# ... 現有內容 ...
```

**3.2 重建 Django 容器**

```bash
# 在專案根目錄執行
docker compose up -d --build django

# 驗證容器啟動成功
docker compose ps django

# 進入容器測試
docker exec -it nt-django sudo ntpdate -q 10.10.10.51
```

---

### Step 4: 創建資料模型

**4.1 創建 NTPSyncOperation 模型**

```bash
# 創建遷移檔案
docker exec nt-django python manage.py shell -c "
# 測試模型定義（先不執行遷移）
from django.db import models
print('✅ 準備創建 NTPSyncOperation 模型')
"
```

在 `backend/api/models.py` 中添加（我會在後續步驟中處理）。

**4.2 執行遷移**

```bash
# 創建遷移
docker exec nt-django python manage.py makemigrations api

# 查看遷移計劃
docker exec nt-django python manage.py sqlmigrate api 0028

# 執行遷移
docker exec nt-django python manage.py migrate

# 驗證
docker exec nt-django python manage.py shell -c "
from api.models import NTPSyncOperation
print(f'✅ NTPSyncOperation 模型已創建')
print(f'   Table: {NTPSyncOperation._meta.db_table}')
"
```

---

### Step 5: 更新 NTPService

**5.1 測試當前 NTPService**

```bash
docker exec nt-django python manage.py shell -c "
from api.ntp_service import NTPService

service = NTPService()
result = service.check_sync()

print(f'NTP Server: {service.ntp_server}')
print(f'Status: {result[\"status\"]}')
print(f'Offset: {result[\"offset\"]:.2f} ms')
print(f'Stratum: {result.get(\"stratum\", \"N/A\")}')
"
```

**5.2 添加 NTPSyncService 類**

在 `backend/api/ntp_service.py` 中添加（詳見設計文檔）。

---

### Step 6: 測試時間同步功能

**6.1 手動測試同步命令**

```bash
# 測試 1: 查詢模式（不修改時間）
docker exec nt-django sudo ntpdate -q 10.10.10.51

# 測試 2: 實際同步（會修改系統時間）
docker exec nt-django sudo ntpdate -u 10.10.10.51

# 測試 3: 驗證同步結果
docker exec nt-django python manage.py shell -c "
from api.ntp_service import NTPService
service = NTPService()
result = service.check_sync()
print(f'同步後偏移: {result[\"offset\"]:.2f} ms')
"
```

**6.2 測試 Python 代碼調用**

```bash
docker exec nt-django python manage.py shell -c "
import subprocess

# 測試 sudo 調用
cmd = ['sudo', 'ntpdate', '-u', '10.10.10.51']
print(f'執行命令: {\" \".join(cmd)}')

result = subprocess.run(
    cmd,
    capture_output=True,
    text=True,
    timeout=30
)

print(f'Return Code: {result.returncode}')
print(f'Output: {result.stdout}')
print(f'Error: {result.stderr}')

if result.returncode == 0:
    print('✅ 時間同步成功')
else:
    print('❌ 時間同步失敗')
"
```

---

### Step 7: 創建 Celery 任務

**7.1 添加 auto_sync_ntp_time_task**

在 `backend/api/tasks.py` 中添加（詳見設計文檔）。

**7.2 手動測試任務**

```bash
# 測試任務（不實際同步）
docker exec nt-django python manage.py shell -c "
from api.tasks import auto_sync_ntp_time_task

print('⏳ 執行 NTP 自動同步任務（測試模式）...')
result = auto_sync_ntp_time_task(force=False, threshold_ms=200)

print(f'✅ 任務執行完成')
print(f'   Checked: {result[\"checked\"]}')
print(f'   Synced: {result[\"synced\"]}')
print(f'   Decision: {result[\"decision\"]}')
print(f'   Reason: {result[\"reason\"]}')
"
```

---

### Step 8: 註冊 Celery Beat 排程

**8.1 使用 DatabaseScheduler 註冊**

```bash
docker exec nt-django python manage.py shell -c "
from django_celery_beat.models import PeriodicTask, IntervalSchedule
from django.utils import timezone

# 創建 15 分鐘間隔
interval, created = IntervalSchedule.objects.get_or_create(
    every=15,
    period='minutes'
)

print(f'Interval: every {interval.every} {interval.period}')
if created:
    print('✅ 創建新的間隔排程')

# 創建定時任務
task, created = PeriodicTask.objects.update_or_create(
    name='auto-sync-ntp-time-every-15-minutes',
    defaults={
        'task': 'api.tasks.auto_sync_ntp_time_task',
        'interval': interval,
        'enabled': True,
        'start_time': timezone.now(),
        'description': 'NTP 自動時間校正（每 15 分鐘檢查，偏移 >200ms 時同步）',
        'kwargs': '{\"threshold_ms\": 200}',
    }
)

if created:
    print('✅ 創建新的定時任務')
else:
    print('✅ 更新現有定時任務')

print(f'Task ID: {task.id}')
print(f'Task Name: {task.name}')
print(f'Enabled: {task.enabled}')
print(f'Next Run: {task.last_run_at or \"首次執行\"}')
"
```

**8.2 驗證任務註冊**

```bash
# 查看 Celery Beat 排程
docker exec nt-django python manage.py shell -c "
from django_celery_beat.models import PeriodicTask

ntp_tasks = PeriodicTask.objects.filter(
    name__icontains='ntp'
).values('name', 'task', 'enabled', 'interval__every', 'interval__period')

for task in ntp_tasks:
    print(f'任務: {task[\"name\"]}')
    print(f'  Task: {task[\"task\"]}')
    print(f'  Enabled: {task[\"enabled\"]}')
    print(f'  Interval: every {task[\"interval__every\"]} {task[\"interval__period\"]}')
    print()
"
```

---

### Step 9: 監控和驗證

**9.1 查看 Celery Beat 日誌**

```bash
# 實時監控 Celery Beat 日誌
docker exec nt-django tail -f logs/django.log | grep -E "auto_sync_ntp|NTP"

# 查看最近的 NTP 任務執行
docker exec nt-django python manage.py shell -c "
from api.models import NTPSyncOperation

recent = NTPSyncOperation.objects.order_by('-timestamp')[:5]

print('最近 5 次 NTP 同步操作:')
print('=' * 80)

for op in recent:
    status_icon = '✅' if op.status == 'success' else '❌'
    print(f'{status_icon} {op.timestamp.strftime(\"%Y-%m-%d %H:%M:%S\")}')
    print(f'   偏移（前）: {op.offset_before:.2f} ms')
    if op.offset_after is not None:
        improvement = abs(op.offset_before) - abs(op.offset_after)
        print(f'   偏移（後）: {op.offset_after:.2f} ms')
        print(f'   改善: {improvement:.2f} ms')
    print(f'   狀態: {op.status}')
    print(f'   觸發: {op.triggered_by}')
    print()
"
```

**9.2 創建監控腳本**

```bash
# 創建 NTP 監控腳本
cat > scripts/check_ntp_sync_status.sh << 'EOF'
#!/bin/bash
# ============================================================================
# NTP 自動同步系統監控腳本
# 用途：檢查 NTP 時間校正系統的運作狀態
# 創建日期：2025-11-23
# ============================================================================

set -e

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo "========================================================================"
echo "🕐 NTP 自動時間校正系統監控"
echo "========================================================================"
echo ""

# 1. 當前時間偏移
echo -e "${BLUE}📊 1. 當前時間偏移狀態${NC}"
docker exec nt-django python manage.py shell -c "
from api.models import NTPSyncLog

latest = NTPSyncLog.objects.order_by('-timestamp').first()
if latest:
    print(f'最新檢測時間: {latest.timestamp.strftime(\"%Y-%m-%d %H:%M:%S\")}')
    print(f'當前偏移: {latest.offset:.2f} ms')
    print(f'NTP Server: {latest.ntp_server}')
    print(f'Stratum: {latest.stratum}')
    
    if abs(latest.offset) < 50:
        print('狀態: ✅ 正常')
    elif abs(latest.offset) < 100:
        print('狀態: 🟢 良好')
    elif abs(latest.offset) < 200:
        print('狀態: 🟡 警告')
    else:
        print('狀態: 🔴 需要同步')
"
echo ""

# 2. 最近同步記錄
echo -e "${BLUE}🔄 2. 最近 3 次同步操作${NC}"
docker exec nt-django python manage.py shell -c "
from api.models import NTPSyncOperation

ops = NTPSyncOperation.objects.order_by('-timestamp')[:3]

for op in ops:
    icon = '✅' if op.status == 'success' else '❌'
    print(f'{icon} {op.timestamp.strftime(\"%m-%d %H:%M\")} - {op.status}')
    print(f'   偏移: {op.offset_before:.2f}ms → {op.offset_after or \"N/A\"}ms')
"
echo ""

# 3. Celery Beat 任務狀態
echo -e "${BLUE}⏰ 3. Celery Beat 任務狀態${NC}"
docker exec nt-django python manage.py shell -c "
from django_celery_beat.models import PeriodicTask

task = PeriodicTask.objects.get(name='auto-sync-ntp-time-every-15-minutes')

print(f'任務名稱: {task.name}')
print(f'啟用狀態: {\"✅ 已啟用\" if task.enabled else \"❌ 已停用\"}')
print(f'上次執行: {task.last_run_at.strftime(\"%Y-%m-%d %H:%M:%S\") if task.last_run_at else \"尚未執行\"}')
print(f'總執行次數: {task.total_run_count}')
"
echo ""

echo "========================================================================"
echo -e "${GREEN}✅ 監控檢查完成${NC}"
echo "========================================================================"
EOF

chmod +x scripts/check_ntp_sync_status.sh

# 執行監控腳本
./scripts/check_ntp_sync_status.sh
```

---

## ✅ 驗收測試

### 測試 1: sudo 權限測試

```bash
# 進入容器
docker exec -it nt-django bash

# 測試 sudo（應該不需要密碼）
sudo ntpdate -q 10.10.10.51
# ✅ 成功：顯示 NTP 查詢結果
# ❌ 失敗：提示需要密碼或權限不足

exit
```

### 測試 2: 時間同步測試

```bash
# 手動觸發同步（強制模式）
docker exec nt-django python manage.py shell -c "
from api.tasks import auto_sync_ntp_time_task

print('⏳ 執行強制同步測試...')
result = auto_sync_ntp_time_task(force=True, threshold_ms=0)

print(f'✅ 測試完成')
print(f'   同步狀態: {result[\"synced\"]}')
print(f'   偏移（前）: {result[\"offset_before\"]:.2f} ms')
print(f'   偏移（後）: {result[\"offset_after\"]:.2f} ms' if result['offset_after'] else '   偏移（後）: N/A')
"
```

### 測試 3: 自動排程測試

```bash
# 等待 15 分鐘後，檢查任務是否自動執行
sleep 900

# 查看執行記錄
docker exec nt-django python manage.py shell -c "
from django_celery_beat.models import PeriodicTask

task = PeriodicTask.objects.get(name='auto-sync-ntp-time-every-15-minutes')
print(f'上次執行: {task.last_run_at}')
print(f'總執行次數: {task.total_run_count}')
# 應該看到次數增加
"
```

### 測試 4: 日誌記錄測試

```bash
# 查看日誌
tail -n 50 logs/django.log | grep -E "auto_sync_ntp|NTP"

# 應該看到類似：
# [INFO] [Celery] 開始執行 NTP 自動時間校正檢查
# [INFO] [Celery] 時間同步完成 - Before: -5122.48ms, After: -12.34ms, 改善: 5110.14ms
```

---

## 🔧 故障排查

### 問題 1: sudo: no tty present and no askpass program specified

**原因**：sudo 需要 tty 但容器沒有提供

**解決方案**：
```bash
# 在 /etc/sudoers.d/ntpdate 添加：
Defaults:root !requiretty
```

### 問題 2: ntpdate: command not found

**原因**：ntpdate 未安裝

**解決方案**：
```bash
docker exec nt-django apt-get update
docker exec nt-django apt-get install -y ntpdate
```

### 問題 3: Permission denied when running ntpdate

**原因**：sudoers 配置錯誤

**解決方案**：
```bash
# 檢查檔案權限
docker exec nt-django ls -l /etc/sudoers.d/ntpdate
# 應該是: -r--r----- (0440)

# 檢查配置語法
docker exec nt-django visudo -c
```

### 問題 4: 任務執行但沒有同步

**原因**：偏移量未超過閾值或距離上次同步未滿 30 分鐘

**解決方案**：
```bash
# 查看決策原因
docker exec nt-django python manage.py shell -c "
from api.ntp_service import NTPSyncService

service = NTPSyncService()

# 檢查是否應該同步
should, reason, offset = service.should_sync(threshold_ms=200)
print(f'應該同步: {should}')
print(f'原因: {reason}')
print(f'當前偏移: {offset:.2f} ms')

# 檢查是否可以同步
can, can_reason = service.can_sync_now()
print(f'可以同步: {can}')
print(f'原因: {can_reason}')
"
```

---

## 📝 配置檔案檢查清單

- [ ] **Dockerfile**: 已添加 ntpdate 和 sudo 安裝
- [ ] **sudoers.d/ntpdate**: 已創建並設置正確權限（0440）
- [ ] **models.py**: 已添加 NTPSyncOperation 模型
- [ ] **ntp_service.py**: 已添加 NTPSyncService 類
- [ ] **tasks.py**: 已添加 auto_sync_ntp_time_task
- [ ] **Celery Beat**: 已註冊定時任務
- [ ] **settings.py**: 已添加 NTP_AUTO_SYNC_CONFIG

---

## 🚀 部署檢查清單

- [ ] **Step 1**: 安裝 ntpdate ✅
- [ ] **Step 2**: 配置 sudo 權限 ✅
- [ ] **Step 3**: 更新 Dockerfile 並重建 ⏳
- [ ] **Step 4**: 創建資料模型 ⏳
- [ ] **Step 5**: 更新 NTPService ⏳
- [ ] **Step 6**: 測試時間同步功能 ⏳
- [ ] **Step 7**: 創建 Celery 任務 ⏳
- [ ] **Step 8**: 註冊 Celery Beat 排程 ⏳
- [ ] **Step 9**: 監控和驗證 ⏳

---

## 📞 下一步行動

1. **立即執行**：
   - [ ] 執行 Step 1-2（安裝 + 配置 sudo）
   - [ ] 測試 sudo 權限

2. **今天完成**：
   - [ ] 執行 Step 3-6（Dockerfile + 測試）
   - [ ] 創建 NTPSyncOperation 模型

3. **明天完成**：
   - [ ] 執行 Step 7-9（Celery 任務 + 監控）
   - [ ] 完整系統測試

---

**最後更新**：2025-11-23 13:50  
**實施狀態**：🚧 進行中（Step 1-2 準備就緒）  
**下一步**：執行 Step 1-2 安裝和配置
