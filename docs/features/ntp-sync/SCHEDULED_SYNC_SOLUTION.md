# NTP 定時自動同步功能 - 完整方案

## 🎯 您的需求

> "你可以幫我規畫一段時間就去 sync 嗎?"

**已完成！** ✅

---

## 📦 交付成果

### 1. 新增 Celery 定時任務

**任務名稱**：`sync_ntp_time_task`  
**執行頻率**：每天凌晨 3:00  
**功能**：
- ✅ 智能檢查時間偏移（> 200ms 才同步）
- ✅ 防護機制（30 分鐘內不重複同步）
- ✅ 自動執行 `ntpdate` 同步時間
- ✅ 記錄所有操作到資料庫

**程式碼位置**：
- `backend/api/tasks.py` → `sync_ntp_time_task()`
- `backend/api/ntp_service.py` → `NTPSyncService`

### 2. 新增資料模型

**模型名稱**：`NTPSyncOperation`  
**用途**：記錄每次 NTP 時間同步操作

**欄位**：
- 同步前/後偏移量
- 改善量
- 執行時間
- 狀態（成功/失敗）
- 錯誤訊息

### 3. 設置腳本

| 腳本 | 用途 |
|------|------|
| `backend/setup_ntp_sync_task.py` | 設置定時任務 |
| `scripts/setup_ntp_auto_sync.sh` | 一鍵完整設置（主機 + 應用） |

### 4. 完整文檔（4 份）

| 文檔 | 說明 |
|------|------|
| `AUTO_SYNC_FEATURE.md` | 自動同步功能詳細說明 ⭐ |
| `HOST_NTP_SETUP_GUIDE.md` | 主機層級同步指南 |
| `SUDO_PERMISSION_SETUP.md` | Sudo 權限配置 |
| `README.md` | 功能總覽和快速開始 |

---

## 🚀 使用方式

### 方式 1：完整自動化設置（推薦）

**一行命令搞定**：

```bash
sudo ./scripts/setup_ntp_auto_sync.sh
```

這會自動：
1. ✅ 設置主機層級 NTP 同步（systemd-timesyncd）
2. ✅ 設置應用層級定時任務（每天凌晨 3 點）
3. ✅ 驗證配置

### 方式 2：僅設置定時任務

```bash
# 進入容器執行
docker exec nt-django python backend/setup_ntp_sync_task.py
```

**注意**：需要額外配置 sudo 權限（參考 SUDO_PERMISSION_SETUP.md）

### 方式 3：組合使用（最佳實踐）✨

**推薦配置**：

```bash
# 1. 主機層級同步（穩定可靠）
sudo ./scripts/setup_ntp_sync.sh

# 2. 應用層級監控（僅檢測，不同步）
# check_ntp_sync_task 已預設啟用（每 5 分鐘）

# 3. 應用層級自動同步（停用，作為備用）
docker exec nt-django python backend/setup_ntp_sync_task.py
# 然後停用任務（交給主機處理）
```

---

## 📊 工作原理

### 智能決策流程

```
每天凌晨 3:00
    ↓
檢查是否允許同步？
（距離上次同步 ≥ 30 分鐘）
    ↓ Yes
檢查是否需要同步？
（時間偏移 > 200ms）
    ↓ Yes
執行 ntpdate 同步
    ↓
記錄操作結果
（NTPSyncOperation）
    ↓
完成
```

### 智能決策邏輯

**條件 1：允許同步**
- ✅ 距離上次同步 ≥ 30 分鐘
- ❌ 有其他同步操作正在進行中

**條件 2：需要同步**
- ✅ 最近 3 筆檢測的平均偏移 > 200ms
- ❌ 偏移在可接受範圍內（< 200ms）

**只有兩個條件都滿足，才會實際執行同步**

---

## 🔍 監控與查詢

### 1. 查看定時任務狀態

```bash
docker exec nt-django python manage.py shell -c "
from django_celery_beat.models import PeriodicTask

tasks = PeriodicTask.objects.filter(name__icontains='NTP')
for task in tasks:
    print(f'{task.name}: {\"啟用\" if task.enabled else \"停用\"}')
"
```

### 2. 查看最新同步操作

```bash
docker exec nt-django python manage.py shell -c "
from api.models import NTPSyncOperation

op = NTPSyncOperation.objects.order_by('-timestamp').first()
if op:
    print(f'操作時間: {op.timestamp}')
    print(f'狀態: {op.status}')
    print(f'改善量: {op.improvement:.3f} ms')
"
```

### 3. 前端查看

訪問「系統監控」頁面 → 查看「NTP 時間自動同步」任務執行記錄

---

## ⚙️ 配置調整

### 修改執行時間

**預設**：每天凌晨 3:00

**修改為凌晨 2:00**：

```bash
docker exec nt-django python manage.py shell -c "
from django_celery_beat.models import PeriodicTask, CrontabSchedule

schedule = CrontabSchedule.objects.create(
    minute='0', hour='2', day_of_week='*',
    day_of_month='*', month_of_year='*'
)

task = PeriodicTask.objects.get(name='NTP 時間自動同步（每天凌晨）')
task.crontab = schedule
task.save()
print('已修改為每天凌晨 2:00')
"
```

### 修改偏移閾值

**預設**：200ms

**修改方式**：編輯 `backend/api/tasks.py`，找到 `sync_ntp_time_task`，修改：

```python
should_sync, reason, avg_offset = sync_service.should_sync(
    threshold_ms=100.0  # 改為 100ms
)
```

### 停用/啟用任務

```bash
# 停用
docker exec nt-django python manage.py shell -c "
from django_celery_beat.models import PeriodicTask
task = PeriodicTask.objects.get(name='NTP 時間自動同步（每天凌晨）')
task.enabled = False
task.save()
print('已停用')
"

# 啟用
docker exec nt-django python manage.py shell -c "
from django_celery_beat.models import PeriodicTask
task = PeriodicTask.objects.get(name='NTP 時間自動同步（每天凌晨）')
task.enabled = True
task.save()
print('已啟用')
"
```

---

## 🎯 推薦部署策略

### 生產環境 ✨

```
┌────────────────────────────────────────┐
│  主機層級（systemd-timesyncd）           │
│  - 持續同步（每 32~1024 秒）             │
│  - 穩定可靠，開機自動啟動                 │
└────────────────────────────────────────┘
              ↓ (Docker 容器自動繼承)
┌────────────────────────────────────────┐
│  應用層級（Django Celery）               │
│  - check_ntp_sync_task（每 5 分鐘）     │
│    → 檢測並記錄時間偏移                  │
│  - sync_ntp_time_task（停用）           │
│    → 僅作備用，交給主機處理               │
└────────────────────────────────────────┘
```

**優點**：
- ✅ 雙重保障（主機同步 + 應用監控）
- ✅ 不需要容器 sudo 權限
- ✅ 所有容器時間一致

### 開發/測試環境

```
┌────────────────────────────────────────┐
│  應用層級（Django Celery）               │
│  - check_ntp_sync_task（每 5 分鐘）     │
│    → 檢測並記錄時間偏移                  │
│  - sync_ntp_time_task（每天凌晨 3:00）  │
│    → 自動同步時間                        │
└────────────────────────────────────────┘
```

**需求**：
- ⚠️ 配置容器 sudo 權限
- ⚠️ 修改 Dockerfile 和 docker-compose.yml

---

## ✅ 驗證清單

### 初次設置後驗證

- [ ] 定時任務已創建：查詢 `PeriodicTask` 表
- [ ] 任務狀態為啟用：`enabled=True`
- [ ] 執行時間正確：凌晨 3:00
- [ ] Celery Worker 正常運行：`docker compose logs django | grep celery`

### 首次執行後驗證（隔天凌晨 3:00 後）

- [ ] `NTPSyncOperation` 表有新記錄
- [ ] 系統監控頁面顯示任務執行記錄
- [ ] 如果時間偏移 > 200ms，應該有同步操作
- [ ] 同步後時間偏移明顯改善

### 持續監控

- [ ] 每週檢查同步操作記錄
- [ ] 每月檢查任務執行統計
- [ ] 關注失敗記錄，及時處理

---

## 🆘 故障排查

### 問題 1：任務沒有執行

**檢查項目**：
```bash
# 1. Celery Worker 是否運行
docker compose logs django | grep -i celery

# 2. 任務是否啟用
docker exec nt-django python manage.py shell -c "
from django_celery_beat.models import PeriodicTask
task = PeriodicTask.objects.get(name='NTP 時間自動同步（每天凌晨）')
print(f'啟用狀態: {task.enabled}')
"

# 3. Celery Beat 是否運行
docker exec nt-django pgrep -f celery
```

### 問題 2：同步失敗

**檢查項目**：
```bash
# 1. 查看最新操作記錄
docker exec nt-django python manage.py shell -c "
from api.models import NTPSyncOperation
op = NTPSyncOperation.objects.order_by('-timestamp').first()
if op and op.status == 'failed':
    print(f'錯誤訊息: {op.error_message}')
"

# 2. 檢查 sudo 權限
docker exec nt-django sudo -l

# 3. 手動測試同步
docker exec nt-django sudo ntpdate -u 10.10.10.51
```

### 問題 3：時間偏移沒有改善

**可能原因**：
- 主機層級的 `systemd-timesyncd` 已經在同步（正常）
- 時間偏移 < 200ms，任務判斷不需要同步（正常）
- Docker 容器使用主機時間，容器內同步無效（需使用主機層級同步）

---

## 📚 相關文檔

- [AUTO_SYNC_FEATURE.md](./AUTO_SYNC_FEATURE.md) - 功能詳細說明
- [HOST_NTP_SETUP_GUIDE.md](./HOST_NTP_SETUP_GUIDE.md) - 主機同步指南
- [SUDO_PERMISSION_SETUP.md](./SUDO_PERMISSION_SETUP.md) - Sudo 權限配置
- [README.md](./README.md) - 功能總覽

---

## 🎉 總結

✅ **已完成您的需求**：定時自動同步 NTP 時間

**交付物**：
- ✅ Celery 定時任務（每天凌晨 3:00）
- ✅ 智能決策機制（偏移 > 200ms 才同步）
- ✅ 防護機制（30 分鐘內不重複同步）
- ✅ 完整記錄（NTPSyncOperation 資料表）
- ✅ 自動化設置腳本
- ✅ 完整文檔（4 份）

**推薦使用方式**：
1. 主機層級同步（穩定可靠） ⭐
2. 應用層級監控（記錄偏移）
3. 應用層級自動同步（備用）

**一鍵設置**：
```bash
sudo ./scripts/setup_ntp_auto_sync.sh
```

---

**文檔版本**：v1.0  
**完成日期**：2025-11-25  
**作者**：GitHub Copilot  
**審核者**：Network Toolbox Team
