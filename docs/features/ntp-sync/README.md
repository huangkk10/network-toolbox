# NTP 時間同步功能文檔

本目錄包含 Network Toolbox 專案的 NTP 時間同步相關文檔。

## 📁 文檔結構

```
docs/features/ntp-sync/
├── README.md                      # 本文件（導航索引）
├── HOST_NTP_SETUP_GUIDE.md        # 主機層級 NTP 同步設置指南
├── AUTO_SYNC_FEATURE.md           # 應用層級自動同步功能說明 ⭐
└── SUDO_PERMISSION_SETUP.md       # Django 容器 Sudo 權限配置（可選）
```

## 🎯 功能概述

Network Toolbox 提供三層的 NTP 時間同步功能：

### 1️⃣ 應用層檢測（已實現）

**功能**：
- ✅ 每 5 分鐘自動檢測 NTP server 狀態
- ✅ 記錄時間偏移、響應時間、Stratum 等資訊
- ✅ 在「系統監控」頁面顯示檢測結果
- ✅ 提供歷史記錄和統計資料

**實現方式**：
- Celery 定時任務：`api.tasks.check_ntp_sync_task`
- 資料模型：`NTPSyncLog`
- 前端頁面：系統監控 → NTP 時間同步檢測

**限制**：
- ❌ **不會**實際調整系統時間（僅檢測）

### 2️⃣ 主機層級同步（推薦方案）

**功能**：
- ✅ 使用 `systemd-timesyncd` 持續同步系統時間
- ✅ Docker 容器自動繼承主機時間
- ✅ 開機自動啟動，背景持續運行
- ✅ 支援備用 NTP server（公開 NTP）

**實現方式**：
- Linux 系統服務：`systemd-timesyncd`
- 配置文件：`/etc/systemd/timesyncd.conf`
- 自動化腳本：`scripts/setup_ntp_sync.sh`

**優點**：
- ✅ 系統層級解決方案，最穩定
- ✅ 不需要 Django 應用層的 sudo 權限
- ✅ 所有 Docker 容器自動同步

### 3️⃣ 應用層自動同步（新增功能）⭐

**功能**：
- ✅ 每天凌晨 3 點自動檢查並同步時間
- ✅ 智能決策：只有偏移 > 200ms 才同步
- ✅ 防護機制：距離上次同步至少 30 分鐘
- ✅ 記錄同步操作到資料庫（`NTPSyncOperation`）

**實現方式**：
- Celery 定時任務：`api.tasks.sync_ntp_time_task`
- 資料模型：`NTPSyncOperation`
- 設置腳本：`backend/setup_ntp_sync_task.py`

**需求**：
- ⚠️ 需要配置 Django 容器的 sudo 權限（參考 SUDO_PERMISSION_SETUP.md）
- ⚠️ 或結合主機層級同步使用（僅用於監控）

---

## 🚀 快速開始

### 選項 1：主機層級同步（推薦）⭐

**一鍵設置 NTP 同步**：

```bash
# 進入專案目錄
cd /home/owner/Codes/network-toolbox

# 執行設置腳本（需要 sudo 權限）
sudo ./scripts/setup_ntp_sync.sh
```

這會自動配置主機的 `systemd-timesyncd`，所有 Docker 容器會自動繼承主機時間。

### 選項 2：應用層自動同步（需額外配置）

**步驟 1：設置定時任務**

```bash
# 進入容器
docker exec nt-django python backend/setup_ntp_sync_task.py
```

**步驟 2：配置 Sudo 權限**

參考 [SUDO_PERMISSION_SETUP.md](./SUDO_PERMISSION_SETUP.md) 配置 Django 容器的 sudo 權限。

**步驟 3：驗證**

```bash
# 手動測試執行
docker exec nt-django python -c "
from api.tasks import sync_ntp_time_task
result = sync_ntp_time_task()
print(result)
"
```

### 選項 3：組合使用（最佳實踐）✨

**推薦配置**：
1. ✅ 主機層級：使用 `systemd-timesyncd` 持續同步（選項 1）
2. ✅ 應用層級：只啟用 `check_ntp_sync_task` 監控（每 5 分鐘檢測）
3. ❌ 應用層級：**不啟用** `sync_ntp_time_task`（交給主機處理）

這樣既有穩定的時間同步，又有完整的監控記錄。

---

## 📊 當前狀態分析

### 問題診斷（2025-11-25）

```bash
# 執行檢查
timedatectl status

# 當前問題：
System clock synchronized: no          # ❌ 未同步
NTP service: active                    # ✅ 服務運行
Server: 10.10.10.51                    # ✅ 已配置
Packet count: 0                        # ❌ 未成功同步

# 錯誤訊息：
Server has too large root distance. Disconnecting.
```

### 根本原因

1. **時間偏移過大**：當前系統時間落後 NTP server 約 **5.6 秒**
2. **Root Distance 檢查失敗**：`systemd-timesyncd` 預設拒絕 root distance > 5 秒
3. **從未成功同步**：Packet count = 0 表示從未成功連接

### 解決方案

參考 [HOST_NTP_SETUP_GUIDE.md](./HOST_NTP_SETUP_GUIDE.md) 中的步驟：
1. 調整 `RootDistanceMaxSec` 配置（5 → 10 秒）
2. 使用 `ntpdate` 強制首次同步
3. 重啟 `systemd-timesyncd` 服務

---

## 🔍 驗證與監控

### 1. 檢查主機同步狀態

```bash
# 查看時間同步狀態
timedatectl status

# 預期結果：
# System clock synchronized: yes  ✅
# NTP service: active            ✅

# 查看詳細同步資訊
timedatectl timesync-status

# 預期結果：
# Server: 10.10.10.51
# Poll interval: 32s ~ 1024s
# Packet count: > 0  ✅
```

### 2. 檢查 Django 應用記錄

```bash
# 查詢最新 NTP 檢測記錄
docker exec nt-django python manage.py shell -c "
from api.models import NTPSyncLog

latest = NTPSyncLog.objects.order_by('-timestamp').first()
print(f'狀態: {latest.status}')
print(f'時間偏移: {latest.offset:.3f} ms')
print(f'Stratum: {latest.stratum}')
"

# 預期結果：
# 狀態: success
# 時間偏移: < 100 ms  ✅
# Stratum: 1 或 2
```

### 3. 前端監控

訪問 Network Toolbox 前端：
1. 進入「**系統監控**」頁面
2. 查看「**最近任務執行記錄**」
3. 找到 `check_ntp_sync_task` 任務
4. 檢查執行結果（時間偏移應 < 100ms）

---

## 📚 相關文檔

### 本專案文檔

- [HOST_NTP_SETUP_GUIDE.md](./HOST_NTP_SETUP_GUIDE.md) - 主機 NTP 同步詳細指南
- [SUDO_PERMISSION_SETUP.md](./SUDO_PERMISSION_SETUP.md) - Django 容器 Sudo 權限配置
- [../scheduled-tasks/](../scheduled-tasks/) - Celery 定時任務說明

### 程式碼位置

- **檢測任務**：`backend/api/tasks.py` → `check_ntp_sync_task()`
- **同步任務**：`backend/api/tasks.py` → `sync_ntp_time_task()` ⭐ 新增
- **NTP 服務**：`backend/api/ntp_service.py` → `NTPService` / `NTPSyncService`
- **資料模型**：`backend/api/models.py` → `NTPSyncLog` / `NTPSyncOperation`
- **檢測任務設置**：`backend/setup_ntp_tasks.py`
- **同步任務設置**：`backend/setup_ntp_sync_task.py` ⭐ 新增

### 系統配置

- **配置文件**：`/etc/systemd/timesyncd.conf`
- **服務名稱**：`systemd-timesyncd.service`
- **狀態文件**：`/var/lib/systemd/timesync/clock`

### 外部資源

- [systemd-timesyncd 官方文檔](https://www.freedesktop.org/software/systemd/man/systemd-timesyncd.service.html)
- [NTP Pool Project](https://www.ntppool.org/)
- [Google Public NTP](https://developers.google.com/time)

---

## ⚠️ 重要注意事項

### 1. 時間跳變影響

首次同步時，系統時間會**向前跳躍 5.6 秒**，可能短暫影響：
- 資料庫時間戳
- 日誌時間順序
- Celery Beat 定時任務調度

**建議**：選擇**非高峰時段**執行（如凌晨 2-4 點）

### 2. Docker 容器時間

- ✅ Docker 容器會**自動繼承主機時間**
- ✅ 主機同步後，**無需重啟容器**
- ✅ 新建容器也會自動使用正確時間

### 3. 服務衝突

確保沒有多個 NTP 服務同時運行：
- `systemd-timesyncd` ⚔️ `ntp` (衝突)
- `systemd-timesyncd` ⚔️ `chrony` (衝突)

**只能選擇一個**，建議使用 `systemd-timesyncd`（Ubuntu 預設）

### 4. 虛擬機環境

如果是 VMware / VirtualBox 虛擬機：
- 需要**停用** Hypervisor 層級的時間同步
- 避免與 OS 層級的 NTP 同步衝突

---

## 🔧 故障排查

### 問題：執行腳本時出現權限錯誤

**解決方法**：
```bash
# 確保使用 sudo 執行
sudo ./scripts/setup_ntp_sync.sh
```

### 問題：仍然出現 "root distance" 錯誤

**解決方法**：
```bash
# 檢查 NTP server 是否正常
ntpdate -q 10.10.10.51

# 如果不通，使用公開 NTP
sudo nano /etc/systemd/timesyncd.conf
# 改為：NTP=time.google.com
```

### 問題：Docker 容器時間不同步

**解決方法**：
```bash
# 重啟容器
docker restart nt-django

# 或重建容器
docker compose restart
```

詳細故障排查請參考：[HOST_NTP_SETUP_GUIDE.md](./HOST_NTP_SETUP_GUIDE.md) → 故障排查章節

---

## 📞 獲取幫助

如有問題，請：

1. 查看詳細指南：[HOST_NTP_SETUP_GUIDE.md](./HOST_NTP_SETUP_GUIDE.md)
2. 檢查系統日誌：`journalctl -u systemd-timesyncd -n 50`
3. 查看 Django 日誌：`docker compose logs django | grep NTP`
4. 聯繫團隊：Network Toolbox Team

---

**最後更新**：2025-11-25  
**維護者**：Network Toolbox Team
