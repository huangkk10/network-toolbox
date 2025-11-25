# 主機 NTP 時間同步設置指南

## 📋 現況分析

### 當前狀態（2025-11-25）

```bash
# 系統時間狀態
System clock synchronized: no          # ❌ 未同步
NTP service: active                    # ✅ 服務運行中
Server: 10.10.10.51                    # ✅ 已配置內部 NTP
Packet count: 0                        # ❌ 未成功同步過

# 錯誤訊息
Server has too large root distance. Disconnecting.
```

### 問題診斷

**Root Distance 過大**表示：
- NTP server 的時間源品質不夠好
- 或者時間偏移太大（目前偏移約 -5.6 秒）
- `systemd-timesyncd` 預設拒絕 root distance > 5 秒的 server

### 驗證結果

✅ **網路連線正常**：
```
PING 10.10.10.51: 0.696~3.84 ms (良好)
```

✅ **NTP 協議正常**：
```
Django 應用可以成功查詢 NTP (Stratum 1)
響應時間: 1.59~1.89 ms
時間偏移: -5585 ms (-5.6 秒)
```

❌ **同步失敗原因**：
- `systemd-timesyncd` 的 Root Distance 檢查過於嚴格
- 初始時間偏移超過預設容忍範圍

---

## 🎯 解決方案規劃

### 方案 A：調整 systemd-timesyncd 配置（推薦）

**優點**：
- 使用系統內建服務，簡單穩定
- 自動在背景持續同步
- Docker 容器自動繼承主機時間

**缺點**：
- 首次同步可能需要手動介入（時間偏移太大）

### 方案 B：改用 Chrony（備選）

**優點**：
- 更靈活的配置選項
- 更好的時間偏移處理能力
- 更詳細的同步狀態資訊

**缺點**：
- 需要額外安裝
- 與 systemd-timesyncd 衝突（需擇一）

---

## 🛠️ 實施步驟

### 步驟 1️⃣：修改 systemd-timesyncd 配置

編輯配置文件以放寬限制：

```bash
sudo nano /etc/systemd/timesyncd.conf
```

修改為：

```ini
[Time]
# 主要 NTP 伺服器（內部）
NTP=10.10.10.51

# 備用 NTP 伺服器（公開）
FallbackNTP=time.google.com time.cloudflare.com

# 放寬最大根距離限制（預設 5 秒，調整為 10 秒）
RootDistanceMaxSec=10

# 縮短輪詢間隔（加快同步速度）
PollIntervalMinSec=32
PollIntervalMaxSec=1024
```

### 步驟 2️⃣：強制手動同步（解決初始偏移）

由於目前時間偏移 -5.6 秒，需要先手動同步一次：

```bash
# 停止 systemd-timesyncd
sudo systemctl stop systemd-timesyncd

# 使用 ntpdate 強制同步（一次性）
sudo ntpdate -u 10.10.10.51

# 重新啟動 timesyncd
sudo systemctl restart systemd-timesyncd

# 啟用服務（確保開機自動啟動）
sudo systemctl enable systemd-timesyncd
```

### 步驟 3️⃣：驗證同步狀態

```bash
# 檢查服務狀態
systemctl status systemd-timesyncd

# 檢查時間同步詳情
timedatectl timesync-status

# 應該看到：
# Server: 10.10.10.51
# Poll interval: 32s (或其他值)
# Packet count: > 0  ✅
```

預期結果：

```bash
timedatectl status

# 應該顯示：
System clock synchronized: yes  ✅
NTP service: active            ✅
```

### 步驟 4️⃣：驗證 Docker 容器時間

```bash
# 檢查 Django 容器時間
docker exec nt-django date

# 檢查主機時間
date

# 兩者應該一致（容器繼承主機時間）
```

---

## 🔍 監控與驗證

### 持續監控（使用現有的 Django 應用）

系統已有 NTP 檢測任務每 5 分鐘執行：

1. **前端查看**：
   - 訪問「系統監控」頁面
   - 查看「NTP 時間同步檢測」任務執行結果
   - 時間偏移應該 < 100ms

2. **後端查詢**：
```bash
docker exec nt-django python manage.py shell -c "
from api.models import NTPSyncLog

# 查詢最新記錄
latest = NTPSyncLog.objects.order_by('-timestamp').first()
print(f'最新同步狀態: {latest.status}')
print(f'時間偏移: {latest.offset:.3f} ms')
print(f'Stratum: {latest.stratum}')
"
```

### 手動檢查命令

```bash
# 查看同步狀態
timedatectl timesync-status

# 查看服務日誌（最近 20 行）
journalctl -u systemd-timesyncd -n 20

# 查看完整日誌（檢查錯誤）
journalctl -u systemd-timesyncd --since "1 hour ago"
```

---

## 📊 預期效果

### 同步前（目前狀態）

| 項目 | 數值 |
|------|------|
| System clock synchronized | ❌ no |
| Packet count | 0 |
| 時間偏移 | -5585 ms (-5.6 秒) |
| 錯誤訊息 | "too large root distance" |

### 同步後（預期）

| 項目 | 數值 |
|------|------|
| System clock synchronized | ✅ yes |
| Packet count | > 0 |
| 時間偏移 | < 100 ms (< 0.1 秒) |
| 錯誤訊息 | 無 |

---

## ⚠️ 注意事項

### 1. 時間跳變的影響

**首次手動同步時，系統時間會向前跳 5.6 秒**，可能影響：

- ✅ **Docker 容器**：自動繼承，無需重啟
- ⚠️ **資料庫時間戳**：新記錄時間會突然跳變（正常現象）
- ⚠️ **日誌時間**：可能出現時間倒退（短暫）
- ⚠️ **定時任務**：Celery Beat 可能需要幾分鐘適應

**建議**：選擇**非高峰時段**執行（如凌晨或午夜）

### 2. 服務衝突

確保沒有其他 NTP 服務同時運行：

```bash
# 檢查 NTP daemon（舊版 Ubuntu）
systemctl status ntp 2>/dev/null

# 檢查 Chrony
systemctl status chronyd 2>/dev/null

# 如果有運行，需要停用其一
sudo systemctl stop ntp
sudo systemctl disable ntp
```

### 3. 防火牆規則

確保 NTP 端口（UDP 123）未被阻擋：

```bash
# 檢查防火牆狀態
sudo ufw status

# 如果需要，允許 NTP
sudo ufw allow ntp
```

### 4. 虛擬機特殊考量

如果是虛擬機（VM）環境：

- 確保 VMware Tools / VirtualBox Guest Additions 的時間同步**已停用**
- 避免 Hypervisor 和 OS 層級的時間同步衝突

```bash
# VMware: 停用時間同步
vmware-toolbox-cmd timesync disable

# VirtualBox: 在 VM 設定中停用「Guest Additions Time Sync」
```

---

## 🔧 故障排查

### 問題 1：仍然出現 "root distance" 錯誤

**解決方法**：
```bash
# 檢查 NTP server 的 Stratum
ntpdate -q 10.10.10.51

# 如果 Stratum > 3，考慮使用公開 NTP
sudo nano /etc/systemd/timesyncd.conf
# 將 time.google.com 設為主要 NTP
```

### 問題 2：Packet count 一直是 0

**解決方法**：
```bash
# 重置 systemd-timesyncd
sudo systemctl stop systemd-timesyncd
sudo rm /var/lib/systemd/timesync/clock
sudo systemctl start systemd-timesyncd

# 強制立即同步
sudo systemctl restart systemd-timesyncd
```

### 問題 3：時間偏移沒有改善

**解決方法**：
```bash
# 檢查硬體時鐘（RTC）
sudo hwclock --show

# 同步系統時間到硬體時鐘
sudo hwclock --systohc

# 或反向：從硬體時鐘讀取
sudo hwclock --hctosys
```

---

## 📚 相關資源

### 官方文檔
- [systemd-timesyncd 手冊](https://www.freedesktop.org/software/systemd/man/systemd-timesyncd.service.html)
- [timedatectl 手冊](https://www.freedesktop.org/software/systemd/man/timedatectl.html)

### 配置文件位置
- 主配置：`/etc/systemd/timesyncd.conf`
- 狀態文件：`/var/lib/systemd/timesync/clock`
- 服務文件：`/lib/systemd/system/systemd-timesyncd.service`

### 日誌查看
```bash
# 即時查看（追蹤模式）
journalctl -u systemd-timesyncd -f

# 查看特定時間範圍
journalctl -u systemd-timesyncd --since "2025-11-25 00:00:00"

# 只顯示錯誤
journalctl -u systemd-timesyncd -p err
```

---

## ✅ 執行檢查清單

完成以下步驟後，打勾確認：

- [ ] 備份現有配置：`sudo cp /etc/systemd/timesyncd.conf /etc/systemd/timesyncd.conf.bak`
- [ ] 修改 `/etc/systemd/timesyncd.conf`（調整 RootDistanceMaxSec）
- [ ] 停止 systemd-timesyncd 服務
- [ ] 執行手動同步：`sudo ntpdate -u 10.10.10.51`
- [ ] 重啟 systemd-timesyncd 服務
- [ ] 驗證同步狀態：`timedatectl status` 顯示 "synchronized: yes"
- [ ] 檢查 Packet count > 0：`timedatectl timesync-status`
- [ ] 驗證 Docker 容器時間一致：`docker exec nt-django date`
- [ ] 檢查 Django NTP 日誌：時間偏移 < 100ms
- [ ] 查看服務日誌無錯誤：`journalctl -u systemd-timesyncd -n 50`

---

**文檔版本**：v1.0  
**最後更新**：2025-11-25  
**作者**：Network Toolbox Team
