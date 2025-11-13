# NTP 時間偏移問題 - 快速修復指南

## 🚨 問題描述

在 Web 介面的 **NTP 分析**頁面中，發現時間偏移（Offset）約為 **-5840 ms**（約 -5.8 秒），表示系統時鐘比 NTP 伺服器快了 5.8 秒。

這個問題的根本原因是：**系統時間同步服務配置了外部 NTP 伺服器（ntp.ubuntu.com），但因網路問題無法連接，導致系統時鐘一直無法同步。**

## ⚡ 快速修復（推薦）

### 方法 1：使用自動修復腳本

執行以下命令：

```bash
# 進入專案目錄
cd /home/owner/Codes/network-toolbox

# 執行修復腳本（需要 sudo 權限）
sudo ./scripts/fix_ntp_sync.sh
```

腳本會自動完成：
1. ✅ 備份原始配置
2. ✅ 配置內部 NTP 伺服器（10.10.10.51）
3. ✅ 重啟時間同步服務
4. ✅ 驗證同步狀態
5. ✅ 測試時間偏移

### 方法 2：手動修復

如果自動腳本無法執行，可以手動操作：

```bash
# 1. 編輯 timesyncd 配置
sudo nano /etc/systemd/timesyncd.conf

# 2. 修改以下內容：
[Time]
NTP=10.10.10.51
FallbackNTP=time.google.com time.cloudflare.com

# 3. 重啟服務
sudo systemctl restart systemd-timesyncd
sudo systemctl enable systemd-timesyncd

# 4. 等待 10-30 秒，然後驗證
timedatectl status
```

## 🔍 驗證修復結果

### 1. 檢查系統時鐘同步狀態

```bash
timedatectl status
```

**預期結果**：
```
System clock synchronized: yes  ← 應該是 yes
              NTP service: active
```

### 2. 檢查時間偏移

```bash
docker exec nt-django python -c "
import ntplib
c = ntplib.NTPClient()
response = c.request('10.10.10.51', version=4)
print(f'時間偏移: {response.offset * 1000:.2f} ms')
"
```

**預期結果**：
- ✅ **優秀**：-50 ~ +50 ms
- ✅ **良好**：-200 ~ +200 ms
- ⚠️ **警告**：-1000 ~ +1000 ms
- ❌ **錯誤**：> ±1000 ms

### 3. 在 Web 介面確認

1. 訪問：http://localhost/ntp-analysis
2. 查看「詳細同步記錄」表格
3. 確認最新的「時間偏移」列已降低到正常範圍

## 📊 問題根本原因

### 發現的問題

1. **系統時鐘未同步**：
   ```
   System clock synchronized: no  ← 問題所在
   ```

2. **timesyncd 一直超時**：
   ```
   Timed out waiting for reply from ntp.ubuntu.com
   ```

3. **實際測量的時間偏移**：
   ```
   本機時間：     Thu Nov 13 04:45:31 2025
   NTP 伺服器時間：Thu Nov 13 04:45:25 2025
   時間偏移：     -5844.73 ms（約 -5.8 秒）
   ```

### 為什麼會發生這個問題？

1. **Ubuntu 預設配置外部 NTP 伺服器**：
   - 系統預設使用 `ntp.ubuntu.com`
   - 如果網路環境無法連接外網，就會一直同步失敗

2. **系統時鐘持續漂移**：
   - 即使同步失敗，系統時鐘仍會繼續運行
   - 但會因為硬體時鐘誤差而逐漸偏移
   - 每小時約漂移 1-2 ms

3. **NTP 檢測正常，但顯示大偏移**：
   - NTP 檢測服務（ntplib）可以成功連接內部 NTP 伺服器
   - 但它測量的是「本機時間」與「NTP 伺服器時間」的差異
   - 由於本機時間不準確，所以偏移值很大

## 🎯 NTP Offset 的意義

### 什麼是 Offset？

**Offset（時間偏移）** = 本機時間 - NTP 伺服器時間

- **負值（-5844 ms）**：本機時間**快於** NTP 伺服器 5.844 秒
- **正值（+100 ms）**：本機時間**慢於** NTP 伺服器 0.1 秒
- **零值（0 ms）**：完全同步（理想狀態）

### 正常的 Offset 範圍

| Offset 範圍 | 狀態 | 說明 |
|------------|------|------|
| **0 ~ ±50 ms** | ✅ 優秀 | 時間同步非常準確 |
| **±50 ~ ±200 ms** | ✅ 良好 | 時間同步正常 |
| **±200 ~ ±1000 ms** | ⚠️ 警告 | 時間偏移較大 |
| **> ±1000 ms** | ❌ 錯誤 | 時間嚴重偏移 |

### 當前狀態

- **修復前**：-5844 ms（❌ 嚴重偏移）
- **修復後預期**：< ±200 ms（✅ 正常）

## 🛠️ 故障排查

### 如果修復後仍然有問題

#### 1. 檢查 NTP 伺服器連接

```bash
# 測試網路連接
ping -c 3 10.10.10.51

# 測試 NTP 端口（UDP 123）
nc -u -z -v 10.10.10.51 123
```

#### 2. 查看服務日誌

```bash
# 查看 timesyncd 日誌
journalctl -u systemd-timesyncd -n 50 -f

# 查看系統日誌
journalctl -xe
```

#### 3. 手動強制同步

```bash
# 停止 timesyncd
sudo systemctl stop systemd-timesyncd

# 使用 ntpdate 手動同步（需要安裝）
sudo apt install ntpdate
sudo ntpdate 10.10.10.51

# 重啟 timesyncd
sudo systemctl start systemd-timesyncd
```

#### 4. 如果在虛擬機中運行

**VMware**：
```bash
# 啟用 VMware Tools 時間同步
sudo systemctl enable vmtoolsd
sudo systemctl start vmtoolsd
```

**VirtualBox**：
- 在虛擬機設置中啟用「Guest Additions」
- 啟用時間同步功能

#### 5. 檢查 Docker 容器時間

```bash
# 檢查容器時間
docker exec nt-django date
date

# 兩者應該一致（誤差 < 1 秒）
```

## 📈 長期監控建議

### 1. 設置定期檢查

創建 cron 任務：

```bash
# 編輯 crontab
sudo crontab -e

# 添加每小時檢查一次
0 * * * * /home/owner/Codes/network-toolbox/scripts/fix_ntp_sync.sh >> /var/log/ntp_check.log 2>&1
```

### 2. 添加告警通知

在前端添加告警邏輯（修改 `frontend/src/pages/NTPAnalysis.js`）：

```javascript
// 當 offset > 1000 ms 時顯示紅色警告
if (Math.abs(record.offset) > 1000) {
    return <Tag color="red">嚴重偏移</Tag>;
} else if (Math.abs(record.offset) > 200) {
    return <Tag color="orange">警告</Tag>;
} else {
    return <Tag color="green">正常</Tag>;
}
```

### 3. 監控趨勢

定期檢查 NTP 統計頁面：
- 觀察 Offset 趨勢圖
- 如果持續單向漂移，可能是硬體時鐘問題

## 📚 相關文檔

- **詳細分析報告**：`docs/troubleshooting/NTP_OFFSET_ANALYSIS.md`
- **NTP 功能文檔**：`docs/features/ntp/README.md`
- **自動修復腳本**：`scripts/fix_ntp_sync.sh`

## 🔗 外部資源

- [systemd-timesyncd 官方文檔](https://www.freedesktop.org/software/systemd/man/systemd-timesyncd.service.html)
- [NTP 協議（RFC 5905）](https://datatracker.ietf.org/doc/html/rfc5905)
- [Ubuntu 時間同步指南](https://ubuntu.com/server/docs/network-ntp)

---

**更新日期**：2025-11-13  
**問題狀態**：已識別，已提供解決方案  
**修復難度**：⭐ 簡單（執行一個腳本即可）
