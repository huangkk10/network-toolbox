# NTP 時間偏移分析報告

## 📊 問題描述

在 Web 介面的 NTP 分析頁面中，顯示的時間偏移（Offset）約為 **-5840 ~ -5844 ms**（約 -5.8 秒），這表示 Docker 容器的系統時間比 NTP 伺服器快了約 5.8 秒。

## 🔍 根本原因分析

### 1. 實際測試結果

通過直接使用 `ntplib` 測試 NTP 伺服器 `10.10.10.51`：

```
NTP 伺服器時間: Thu Nov 13 04:45:25 2025
本機時間:       Thu Nov 13 04:45:31 2025
時間偏移 (秒):   -5.844733953475952
時間偏移 (毫秒): -5844.733953475952
Stratum: 1
```

### 2. 系統時鐘同步狀態

```bash
$ timedatectl status
               Local time: 四 2025-11-13 04:46:04 CST
           Universal time: 三 2025-11-12 20:46:04 UTC
                 RTC time: 三 2025-11-12 20:46:00
                Time zone: Asia/Taipei (CST, +0800)
System clock synchronized: no        # ← 關鍵問題：系統時鐘未同步
              NTP service: active
          RTC in local TZ: no
```

### 3. 問題總結

**這個偏移量是真實的，不是計算錯誤**：

- ✅ **NTP 服務正常**：Stratum 1 表示 NTP 伺服器是一級時間源（直接連接到參考時鐘）
- ✅ **響應時間正常**：1.6 ~ 2.6 ms 的響應時間屬於正常範圍
- ❌ **系統時鐘未同步**：`System clock synchronized: no`
- ❌ **持續漂移**：偏移量從 -5835 ms 持續增長到 -5844 ms（每小時約漂移 1-2 ms）

## 🎯 NTP Offset 的意義

### 什麼是 NTP Offset？

**NTP Offset（時間偏移）** 表示本機時鐘與 NTP 伺服器標準時間之間的差異：

- **負值（-5844 ms）**：表示本機時間**快於** NTP 伺服器時間 5.844 秒
- **正值（+100 ms）**：表示本機時間**慢於** NTP 伺服器時間 0.1 秒
- **零值（0 ms）**：表示本機時間與 NTP 伺服器完全同步（理想狀態）

### 正常的 Offset 範圍

| Offset 範圍 | 狀態 | 說明 |
|------------|------|------|
| **0 ~ ±50 ms** | ✅ 優秀 | 時間同步非常準確，適合精密應用 |
| **±50 ~ ±200 ms** | ✅ 良好 | 時間同步正常，一般應用可接受 |
| **±200 ~ ±1000 ms** | ⚠️ 警告 | 時間偏移較大，建議調整時鐘 |
| **> ±1000 ms** | ❌ 錯誤 | 時間嚴重偏移，需要立即同步 |

### 當前狀態

- **當前 Offset**：-5844 ms（-5.844 秒）
- **狀態**：❌ **嚴重偏移**
- **影響**：
  - 日誌時間戳不準確（會比實際時間快 5.8 秒）
  - DHCP 租約時間判斷可能出錯
  - SSL 憑證驗證可能失敗（時間差過大）
  - 與其他系統的時間協調會出現問題

## 🔧 解決方案

### 方案 1：立即同步系統時間（推薦）

使用 `chrony` 或 `systemd-timesyncd` 強制同步：

```bash
# 方法 1：使用 chronyc（如果已安裝 chrony）
sudo chronyc -a makestep

# 方法 2：重啟 systemd-timesyncd 服務
sudo systemctl restart systemd-timesyncd

# 方法 3：使用 ntpdate（需要先停止 NTP 服務）
sudo systemctl stop systemd-timesyncd
sudo ntpdate 10.10.10.51
sudo systemctl start systemd-timesyncd
```

### 方案 2：配置自動時間同步

編輯 `/etc/systemd/timesyncd.conf`：

```ini
[Time]
NTP=10.10.10.51
FallbackNTP=time.google.com time.cloudflare.com
```

然後重啟服務：

```bash
sudo systemctl restart systemd-timesyncd
sudo systemctl enable systemd-timesyncd
```

### 方案 3：配置 Docker 容器時間同步

確保 Docker 容器與主機時間同步，在 `docker-compose.yml` 中：

```yaml
services:
  django:
    volumes:
      - /etc/localtime:/etc/localtime:ro  # 同步時區
      - /etc/timezone:/etc/timezone:ro    # 同步時區設置
```

### 方案 4：禁用虛擬化時鐘漂移（如果在虛擬機中）

如果系統運行在虛擬機中（如 VMware、VirtualBox），可能需要配置虛擬機時鐘同步：

**VMware**：
```bash
sudo systemctl enable vmtoolsd
sudo systemctl start vmtoolsd
```

**VirtualBox**：
- 在虛擬機設置中啟用「Guest Additions」
- 啟用時間同步功能

## 📈 驗證修復結果

同步時間後，執行以下命令驗證：

```bash
# 1. 檢查系統時鐘同步狀態
timedatectl status
# 應該顯示：System clock synchronized: yes

# 2. 手動觸發 NTP 檢測任務
docker exec nt-django python manage.py shell -c "
from api.tasks import check_ntp_sync_task
result = check_ntp_sync_task()
print(f'Offset: {result[\"offset\"]} ms')
"

# 3. 查看最新的 NTP 記錄
docker exec nt-django python manage.py shell -c "
from api.models import NTPSyncLog
log = NTPSyncLog.objects.latest('timestamp')
print(f'Offset: {log.offset} ms')
"
```

**預期結果**：Offset 應該降低到 **±200 ms 以內**（理想狀態是 ±50 ms 以內）

## 🎓 NTP 相關概念

### 1. Stratum（層級）

- **Stratum 0**：原子鐘、GPS 時鐘等參考時鐘（不直接連接網路）
- **Stratum 1**：直接連接到 Stratum 0 的 NTP 伺服器（當前 10.10.10.51 是 Stratum 1）
- **Stratum 2-15**：從上一層級同步時間的 NTP 伺服器或客戶端
- **Stratum 16**：未同步狀態

**當前狀態**：Stratum 1（最高等級，時間源可靠）

### 2. Response Time（響應時間）

- **定義**：從發送 NTP 請求到收到回應的時間
- **當前值**：1.6 ~ 2.6 ms
- **評價**：✅ 優秀（< 10 ms 為良好，< 50 ms 為可接受）

### 3. Jitter（時間抖動）

- **定義**：連續多次測量的時間偏移的變化量（穩定性指標）
- **正常範圍**：< 50 ms
- **說明**：數值越小，時鐘越穩定

## 📝 監控建議

### 1. 設置告警閾值

在前端頁面添加告警邏輯：

```javascript
// 建議的告警閾值
const OFFSET_WARNING = 200;   // 200 ms
const OFFSET_CRITICAL = 1000; // 1000 ms

if (Math.abs(offset) > OFFSET_CRITICAL) {
    // 嚴重告警：紅色
    status = 'critical';
} else if (Math.abs(offset) > OFFSET_WARNING) {
    // 警告：黃色
    status = 'warning';
} else {
    // 正常：綠色
    status = 'success';
}
```

### 2. 定期檢查系統時鐘同步狀態

添加到監控腳本：

```bash
#!/bin/bash
# check_time_sync.sh

SYNC_STATUS=$(timedatectl status | grep "System clock synchronized" | awk '{print $4}')

if [ "$SYNC_STATUS" != "yes" ]; then
    echo "WARNING: System clock not synchronized!"
    sudo chronyc -a makestep
fi
```

### 3. 記錄長期趨勢

- 監控 Offset 的變化趨勢（每小時漂移量）
- 如果持續單向漂移，可能是硬體時鐘（RTC）有問題

## 🔗 相關資源

- [NTP 協議說明（RFC 5905）](https://datatracker.ietf.org/doc/html/rfc5905)
- [Chrony 官方文檔](https://chrony.tuxfamily.org/documentation.html)
- [systemd-timesyncd 配置](https://www.freedesktop.org/software/systemd/man/timesyncd.conf.html)

---

**分析日期**：2025-11-13  
**分析人員**：System Administrator  
**問題狀態**：已識別，待修復
