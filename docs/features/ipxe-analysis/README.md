# IPXE 分析功能

## 📋 功能概述

IPXE 管理功能用於監控和分析多台 IPXE 伺服器（10.250.x.2）的日誌，提供統一的管理界面和自動化日誌收集。

### 核心特性
- ✅ 管理多台 IPXE 伺服器
- ✅ 自動收集 Docker 容器日誌（透過 SSH）
- ✅ 顯示最近 7 天的日誌
- ✅ 每 10 分鐘自動更新
- ✅ 自動清理舊資料
- ✅ 仿效 DHCP Server 管理的用戶體驗

---

## 📊 IPXE 伺服器架構

### 伺服器列表（範例）
- **10.250.50.2** - 測試伺服器（已驗證）
- **10.250.51.2**
- **10.250.52.2**
- **10.250.53.2**
- **10.250.54.2**

### 每台伺服器的組成

```
IPXE 伺服器 (10.250.x.2)
├── Docker 容器 1: ipxe_mac-flask (Port 9000)
│   └── MAC 地址管理服務
│       ├── Set 操作：設置 MAC 的 BOOT 旗標
│       └── Get 操作：查詢 MAC 的配置
│
└── Docker 容器 2: ipxe (Port 8080)
    └── IPXE HTTP 服務
        ├── boot.ipxe - 開機腳本
        ├── wimboot - Windows 啟動器
        ├── BCD - 啟動配置數據
        ├── boot.sdi - 系統部署映像
        └── LiteTouchPE_x64.wim - Windows PE 映像
```

### SSH 訪問資訊

**預設配置**（10.250.50.2 測試）：
- **使用者名稱**：rvt
- **密碼**：1.a（需要各伺服器實際密碼）
- **SSH 端口**：22
- **Sudo 權限**：需要密碼

**訪問命令範例**：
```bash
# 連接到伺服器
ssh rvt@10.250.50.2

# 查看 Docker 容器
sudo docker ps

# 查看 MAC 管理日誌
sudo docker logs ipxe_mac-flask --tail 100

# 查看 IPXE 開機日誌
sudo docker logs ipxe --tail 100
```

---

## 📝 日誌格式說明

### 1. MAC 管理日誌（ipxe_mac-flask）

**日誌範例**：
```
10.252.170.188 - - [28/Oct/2025:10:18:24 +0000] "GET /iPxeMac/Set?MAC=10:FF:E0:E2:91:56&BOOT=1 HTTP/1.1" 200 7 "-" "ansible-httpget"
10.250.53.25 - - [28/Oct/2025:10:18:53 +0000] "GET /iPxeMac/Get?MAC=10:ff:e0:e2:96:db HTTP/1.1" 200 111 "-" "iPXE/1.21.1+ (g83449)"
```

**解析欄位**：
- `10.252.170.188` - 客戶端 IP
- `28/Oct/2025:10:18:24 +0000` - 時間戳記
- `GET` - HTTP 方法
- `/iPxeMac/Set?MAC=...&BOOT=1` - 請求 URL
  - `Set` - 設置 MAC 配置
  - `Get` - 查詢 MAC 配置
  - `MAC=10:FF:E0:E2:91:56` - MAC 地址
  - `BOOT=1` - 開機旗標（1=啟用 PXE，0=停用 PXE）
- `200` - HTTP 狀態碼
- `7` - 傳輸位元組數
- `ansible-httpget` - 客戶端類型（自動化工具）
- `iPXE/1.21.1+` - IPXE 客戶端版本

### 2. IPXE 開機日誌（ipxe）

**日誌範例**：
```
10.250.53.25 - - [28/Oct/2025:10:18:57 +0000] "GET /boot.ipxe HTTP/1.1" 200 116 "-" "iPXE/1.21.1+ (g83449)" "-"
10.250.53.25 - - [28/Oct/2025:10:18:57 +0000] "GET /wimboot HTTP/1.1" 200 62440 "-" "iPXE/1.21.1+ (g83449)" "-"
10.250.53.25 - - [28/Oct/2025:10:19:01 +0000] "GET /LiteTouchPE_x64.wim HTTP/1.1" 200 576926332 "-" "iPXE/1.21.1+ (g83449)" "-"
```

**解析欄位**：
- `10.250.53.25` - 客戶端 IP
- `28/Oct/2025:10:18:57 +0000` - 時間戳記
- `GET` - HTTP 方法
- `/boot.ipxe` - 請求的檔案
  - `boot.ipxe` - 開機腳本（116 bytes）
  - `wimboot` - Windows 啟動器（62,440 bytes）
  - `BCD` - 啟動配置（12,288 bytes）
  - `boot.sdi` - 系統映像（3,170,304 bytes）
  - `LiteTouchPE_x64.wim` - Windows PE（576,926,332 bytes ≈ 550 MB）
- `200` - HTTP 狀態碼
- `576926332` - 傳輸位元組數（檔案大小）
- `iPXE/1.21.1+ (g83449)` - IPXE 客戶端版本

**典型開機流程**：
```
1. GET /boot.ipxe         → 讀取開機腳本
2. GET /wimboot          → 下載 Windows 啟動器
3. GET /BCD              → 讀取啟動配置
4. GET /boot.sdi         → 下載系統映像
5. GET /LiteTouchPE_x64.wim → 下載 Windows PE（約 550 MB）
```

---

## 📖 相關文檔

### 設計文檔
- [IPXE 管理功能完整設計](./IPXE_MANAGEMENT_DESIGN.md) - 詳細的架構設計和實現方案

### 參考文檔
- [DHCP Server 管理](../../development/DEVELOPMENT.md) - 仿效的參考架構
- [定時任務設置](../scheduled-tasks/CRON_SETUP_GUIDE.md) - 自動同步配置
- [SSH 服務設計](../../SSH_WINDOWS_DHCP_SYNC.md) - SSH 連接參考

---

## 🚀 快速開始

### 1. 查看設計文檔
```bash
cat docs/features/ipxe-analysis/IPXE_MANAGEMENT_DESIGN.md
```

### 2. 測試 SSH 連接
```bash
python3 test_ipxe_connection.py
```

### 3. 手動收集日誌（實現後）
```bash
docker exec nt-django python manage.py collect_ipxe_logs --server 1
```

### 4. 訪問管理頁面（實現後）
- **伺服器管理**：http://localhost/admin/ipxe-management
- **日誌分析**：http://localhost/ipxe-analytics

---

## ⚙️ 配置檢查清單

開始實現前需要確認的資訊：

- [ ] 確認所有 IPXE 伺服器的 IP 列表（10.250.x.2）
- [ ] 確認各伺服器的 SSH 使用者名稱和密碼
- [ ] 確認各伺服器的 Docker 容器名稱
- [ ] 測試 SSH 連接和 Docker 命令執行
- [ ] 確認日誌格式是否一致

---

**最後更新**：2025-10-29  
**狀態**：設計完成，待實現
