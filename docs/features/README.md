# Network Toolbox - 功能文檔索引

本目錄包含 Network Toolbox 各項功能的詳細說明文檔。

## 📋 功能清單

### 🌐 DHCP 管理

- [**DHCP SSH 整合**](./DHCP_SSH_INTEGRATION.md) - SSH 連接到 DHCP 伺服器並同步數據
- [**租約真實數據轉換**](./LEASES_TAB_REAL_DATA_CONVERSION.md) - 租約數據的處理和展示

### 🔍 設備識別

- [**MAC 廠商識別**](./MAC_VENDOR_IDENTIFICATION.md) ⭐ **NEW** - 使用 IEEE OUI 資料庫識別設備製造商
  - 📖 [快速開始](./MAC_VENDOR_QUICKSTART.md)
- [**客戶端類型檢測 V2**](./CLIENT_TYPE_DETECTION_V2.md) - 改進的設備類型識別
- [**客戶端類型檢測**](./CLIENT_TYPE_DETECTION.md) - 基礎設備類型識別
- [**交換機檢測方法**](./SWITCH_DETECTION_METHODS.md) - 網路交換機的識別方法

### 📊 日誌管理

- [**日誌實作完成**](./LOGS_IMPLEMENTATION_COMPLETE.md) - 完整的日誌系統說明
- [**日誌 API 實作**](./LOGS_API_IMPLEMENTATION.md) - 日誌 API 端點
- [**日誌分頁更新**](./LOGS_PAGINATION_UPDATE.md) - 日誌分頁功能
- [**日誌時間範圍篩選**](./LOGS_TIME_RANGE_FILTER.md) - 時間範圍篩選
- [**日誌檔案說明**](./LOG_FILES_EXPLAINED.md) - 日誌檔案結構
- [**日誌頁面使用**](./LOGS_TAB_USAGE.md) - 前端日誌頁面使用指南

### 🚀 進階功能

- [**iPXE 分析與實作**](./IPXE_ANALYSIS_AND_IMPLEMENTATION.md) - iPXE 網路啟動
- [**iPXE Stage 1 指南**](./IPXE_STAGE1_GUIDE.md) - iPXE 第一階段實作

### ⏰ 定時任務

- [**定時任務功能**](./scheduled-tasks/) - Cron 和 Celery 定時任務實作

## 🆕 最新更新

### 2025-10-29: MAC 廠商識別功能

新增完整的 IEEE OUI 資料庫支援，可自動識別 23,000+ 個製造商的設備。

**主要特性**：
- ✅ 23,475 筆 OUI 記錄
- ✅ 16,778 個唯一製造商
- ✅ < 1 毫秒查詢速度
- ✅ 自動更新機制
- ✅ Dashboard 廠商分佈圖

**快速開始**：
```bash
# 測試功能
docker exec nt-django python /app/test_mac_vendor_simple.py

# 更新資料庫
docker exec nt-django python manage.py update_oui
```

**文檔**：
- [完整文檔](./MAC_VENDOR_IDENTIFICATION.md) - 詳細說明、API 使用、故障排查
- [快速開始](./MAC_VENDOR_QUICKSTART.md) - 5 分鐘快速上手

## 📚 文檔分類

### 開發相關
- 位置：`docs/development/`
- 內容：開發環境、開發規範、技術決策

### 部署相關
- 位置：`docs/deployment/`
- 內容：Docker 部署、生產環境配置

### API 文檔
- 位置：`docs/api/`
- 內容：API 端點說明、測試報告

### 故障排查
- 位置：`docs/troubleshooting/`
- 內容：常見問題、錯誤處理

## 🔧 文檔撰寫規範

每個功能文檔應包含：

1. **概述** - 功能簡介
2. **特性** - 主要功能列表
3. **使用方法** - 代碼示例
4. **API 說明** - 相關 API 端點
5. **故障排查** - 常見問題
6. **參考資料** - 相關連結

## 📖 相關文檔

- [專案主 README](../../README.md)
- [開發指南](../development/DEVELOPMENT.md)
- [部署指南](../deployment/DEPLOYMENT.md)

---

**維護者**：Network Toolbox Team  
**最後更新**：2025-10-29
