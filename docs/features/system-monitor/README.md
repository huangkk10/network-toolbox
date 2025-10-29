# 系統監控功能

## 功能概述

系統監控功能提供即時監控伺服器系統資源使用狀況，包含：
- **磁碟空間**：總容量、已使用、可用空間及使用率
- **CPU 使用率**：即時 CPU 使用百分比及核心數
- **RAM 使用率**：總記憶體、已使用、可用記憶體及使用率

## 功能特點

### 1. 即時監控
- 每 5 秒自動刷新數據
- 可手動暫停/繼續自動刷新
- 支援手動立即刷新

### 2. 視覺化展示
- **統計卡片**：顯示當前使用率及詳細資訊
- **進度條**：直觀展示資源使用情況
- **顏色編碼**：
  - 綠色（< 60%）：正常
  - 黃色（60-80%）：警告
  - 紅色（> 80%）：危險

### 3. 歷史趨勢
- **面積圖**：展示最近 20 筆數據的趨勢
- **多維度對比**：同時顯示 CPU、RAM、磁碟使用率
- **即時更新**：隨自動刷新持續累積數據

## 技術實現

### 後端 API

**端點**：`/api/system/status/`

**使用技術**：
- `psutil`：獲取系統資源資訊
- `shutil`：獲取磁碟空間資訊

**響應格式**：
```json
{
    "disk": {
        "total": 250.43,
        "used": 79.94,
        "free": 157.7,
        "percent": 31.9
    },
    "cpu": {
        "percent": 1.1,
        "count": 16
    },
    "ram": {
        "total": 15.61,
        "used": 5.13,
        "available": 10.48,
        "percent": 32.9
    }
}
```

### 前端頁面

**位置**：`frontend/src/pages/SystemMonitorPage.js`

**使用組件**：
- `Card`：卡片容器
- `Row`, `Col`：響應式佈局
- `Statistic`：統計數值展示
- `Progress`：進度條
- `AreaChart`（recharts）：面積圖

**主要功能**：
1. 自動刷新機制（5 秒間隔）
2. 手動刷新控制
3. 歷史數據管理（保留最近 20 筆）
4. 動態顏色狀態

## 訪問方式

1. **側邊欄菜單**：點擊「系統監控」
2. **直接訪問**：http://localhost/system-monitor

## 安裝依賴

### 後端依賴

已添加到 `requirements.txt`：
```
psutil>=5.9.0
```

**安裝方式**（容器內）：
```bash
docker exec nt-django pip install psutil
```

**重啟容器**：
```bash
docker compose restart django
```

### 前端依賴

使用現有依賴：
- `antd`：UI 組件庫
- `recharts`：圖表庫
- `axios`：HTTP 客戶端

## 文件清單

### 後端
- `backend/api/views.py`：新增 `system_status` API 端點
- `backend/api/urls.py`：註冊 `/api/system/status/` 路由
- `backend/requirements.txt`：添加 `psutil` 依賴

### 前端
- `frontend/src/pages/SystemMonitorPage.js`：系統監控頁面
- `frontend/src/App.js`：添加路由配置
- `frontend/src/components/Sidebar.js`：添加菜單項

## 使用說明

### 自動刷新控制
- **暫停**：點擊右上角「暫停」按鈕
- **繼續**：點擊右上角「繼續」按鈕
- **手動刷新**：點擊「手動刷新」圖標

### 數據解讀

**磁碟空間**：
- 監控根目錄（`/`）的磁碟使用情況
- 包含 Docker 容器、日誌、數據庫等所有數據

**CPU 使用率**：
- 過去 1 秒的平均 CPU 使用率
- 顯示可用 CPU 核心數

**RAM 使用率**：
- 系統記憶體使用情況
- 包含已使用和可用記憶體詳情

## 注意事項

1. **資源消耗**：每 5 秒刷新會產生 API 請求，正常使用對系統影響極小
2. **權限要求**：無需特殊權限，所有用戶均可訪問
3. **數據準確性**：使用 `psutil` 獲取系統資訊，準確度高

## 未來擴展

可能的功能增強：
- [ ] 添加網路流量監控
- [ ] 添加磁碟 I/O 監控
- [ ] 支援多磁碟分區監控
- [ ] 添加報警功能（資源超過閾值時通知）
- [ ] 歷史數據持久化（儲存到資料庫）
- [ ] 匯出監控報告

---

**最後更新**：2025-10-29  
**維護者**：Network Toolbox Team
