# NAS 分析功能說明

## 📋 功能概述

NAS 分析功能用於監控和分析 NAS (Network Attached Storage) 的連線狀況，每 5 分鐘自動記錄一次連線測試，並保留最近 2 週的數據。

### 功能特性

- ✅ **自動連線檢測**：每 5 分鐘自動執行一次 NAS SMB 連線測試
- ✅ **效能測試**：記錄響應時間、上傳速度、下載速度
- ✅ **數據保留**：自動保留最近 2 週的數據，超過 2 週的舊數據自動刪除
- ✅ **視覺化分析**：提供圖表展示連線趨勢和統計資料
- ✅ **實時監控**：前端頁面每 30 秒自動刷新數據

## 🔧 NAS 配置資訊

```plaintext
IP 地址：     10.250.0.1
用戶名：      mdt
密碼：        p@ssw0rd
共享名稱：    mdt
測試路徑：    \\10.250.0.1\mdt\Script\chunwei_tset\nas_test
```

## 🏗️ 架構設計

### 後端架構

```
┌─────────────────────────────────────────────────┐
│  Celery Beat (定時任務調度器)                    │
│  - 每 5 分鐘觸發一次 NAS 連線檢測                │
└──────────────┬──────────────────────────────────┘
               │
               ↓
┌─────────────────────────────────────────────────┐
│  Celery Worker (任務執行器)                      │
│  - check_nas_connection_task                    │
│  - 調用 nas_service.py                          │
└──────────────┬──────────────────────────────────┘
               │
               ↓
┌─────────────────────────────────────────────────┐
│  NAS Service (nas_service.py)                   │
│  - check_nas_connection()    # SMB 連線測試     │
│  - test_upload_speed()       # 上傳速度測試     │
│  - test_download_speed()     # 下載速度測試     │
│  - record_nas_connection()   # 記錄到數據庫     │
│  - cleanup_old_records()     # 清理舊數據       │
└──────────────┬──────────────────────────────────┘
               │
               ↓
┌─────────────────────────────────────────────────┐
│  PostgreSQL Database                            │
│  - api_nasconnectionlog 表                      │
└─────────────────────────────────────────────────┘
```

### 前端架構

```
┌─────────────────────────────────────────────────┐
│  Sidebar.js                                     │
│  - 添加 "NAS 分析" 菜單項                       │
└──────────────┬──────────────────────────────────┘
               │
               ↓
┌─────────────────────────────────────────────────┐
│  App.js                                         │
│  - /nas-analytics 路由                          │
└──────────────┬──────────────────────────────────┘
               │
               ↓
┌─────────────────────────────────────────────────┐
│  NASAnalyticsPage.js                            │
│  - 統計卡片（成功率、響應時間等）               │
│  - 每日連線趨勢圖（LineChart）                  │
│  - 每小時統計圖（AreaChart）                    │
│  - 連線狀態分佈餅圖（PieChart）                 │
│  - 詳細記錄表格（Table）                        │
└──────────────┬──────────────────────────────────┘
               │
               ↓
┌─────────────────────────────────────────────────┐
│  Backend API                                    │
│  - GET /api/nas-logs/                           │
│  - GET /api/nas-logs/statistics/                │
└─────────────────────────────────────────────────┘
```

## 📊 數據模型

### NASConnectionLog 模型

```python
class NASConnectionLog(models.Model):
    timestamp         # 記錄時間
    status            # 連線狀態 (success/failed)
    nas_ip            # NAS IP 地址
    nas_share         # 共享名稱
    response_time     # 響應時間 (ms)
    upload_speed      # 上傳速度 (MB/s)
    download_speed    # 下載速度 (MB/s)
    error_message     # 錯誤訊息
    created_at        # 建立時間
```

### 索引優化

- `idx_nas_timestamp`：時間戳索引（用於快速查詢時間範圍）
- `idx_nas_status`：狀態索引（用於過濾成功/失敗）
- `idx_nas_time_status`：複合索引（時間+狀態）

## 🔌 API 端點

### 1. 獲取 NAS 連線記錄

```http
GET /api/nas-logs/?days=7
```

**查詢參數：**
- `days`（可選）：返回最近 N 天的數據，默認 14 天
- `status`（可選）：過濾狀態（success/failed）

**響應範例：**

```json
[
    {
        "id": 1,
        "timestamp": "2025-10-29T04:33:13.290134",
        "status": "success",
        "nas_ip": "10.250.0.1",
        "nas_share": "mdt",
        "response_time": 5.54,
        "upload_speed": 46.05,
        "download_speed": 56.52,
        "error_message": "",
        "created_at": "2025-10-29T04:33:13.300012"
    }
]
```

### 2. 獲取統計資料

```http
GET /api/nas-logs/statistics/?days=7
```

**響應範例：**

```json
{
    "total_records": 288,
    "success_count": 285,
    "failed_count": 3,
    "success_rate": 98.96,
    "avg_response_time": 12.45,
    "avg_upload_speed": 45.23,
    "avg_download_speed": 58.67,
    "daily_stats": [
        {
            "date": "2025-10-23",
            "total": 42,
            "success": 41,
            "failed": 1,
            "success_rate": 97.62
        }
    ],
    "hourly_stats": [
        {
            "hour": "2025-10-29 00:00",
            "total": 12,
            "success": 12,
            "failed": 0
        }
    ]
}
```

## ⏰ 定時任務配置

### Celery Beat 配置

在 `backend/network_toolbox/celery.py` 中配置：

```python
app.conf.beat_schedule = {
    'check-nas-connection-every-5-minutes': {
        'task': 'api.tasks.check_nas_connection_task',
        'schedule': crontab(minute='*/5'),  # 每 5 分鐘執行
        'options': {
            'expires': 150,  # 任務超時 2.5 分鐘
        }
    },
}
```

### 任務執行流程

1. **Celery Beat** 每 5 分鐘觸發任務
2. **Celery Worker** 接收任務並執行
3. **NAS Service** 執行 SMB 連線測試
4. **記錄結果** 到 PostgreSQL 數據庫
5. **自動清理** 超過 2 週的舊數據

## 🎨 前端功能

### 頁面組件

1. **NAS 配置資訊卡片**
   - 顯示 NAS IP、共享名稱、測試路徑
   - 提示自動檢測頻率

2. **統計卡片（4 個）**
   - 總記錄數
   - 成功率
   - 平均響應時間
   - 平均下載速度

3. **每日連線統計趨勢圖**
   - 折線圖顯示最近 7 天
   - 成功/失敗/總計三條線

4. **連線狀態分佈餅圖**
   - 成功 vs 失敗比例

5. **每小時連線統計圖**
   - 面積圖顯示最近 24 小時
   - 堆疊顯示成功和失敗數量

6. **詳細記錄表格**
   - 支持排序、篩選、分頁
   - 顯示完整的連線資訊

### 自動刷新

前端頁面每 30 秒自動刷新數據：

```javascript
useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 30000);
    return () => clearInterval(interval);
}, [timeRange]);
```

## 🧪 測試結果

### 後端測試

執行測試腳本：

```bash
docker exec nt-django python test_nas_connection.py
```

**測試結果：**

```
✓ NAS 連線測試完成
  - 狀態: success
  - 響應時間: 13.21 ms
  - 上傳速度: 29.34 MB/s
  - 下載速度: 57.87 MB/s

✓ NAS 連線記錄成功寫入數據庫
✓ 數據庫查詢成功
✓ 統計資料獲取成功
```

### API 測試

```bash
# 測試記錄端點
curl http://localhost/api/nas-logs/ | jq

# 測試統計端點
curl http://localhost/api/nas-logs/statistics/ | jq
```

## 📝 使用說明

### 訪問 NAS 分析頁面

1. 登入 Network Toolbox
2. 點擊左側菜單的 "NAS 分析"
3. 查看連線統計和趨勢圖表

### 時間範圍選擇

頁面提供時間範圍選項：
- 最近 1 天
- 最近 3 天
- 最近 7 天（默認）
- 最近 14 天

### 查看詳細記錄

表格支持：
- **排序**：點擊欄位標題排序
- **篩選**：過濾成功/失敗狀態
- **分頁**：每頁顯示 20 筆記錄

## 🔍 故障排查

### 問題 1：NAS 連線失敗

**症狀：** 狀態顯示 "失敗"

**解決方法：**

1. 檢查 NAS 是否在線：
   ```bash
   ping 10.250.0.1
   ```

2. 檢查 SMB 端口（445）：
   ```bash
   telnet 10.250.0.1 445
   ```

3. 檢查用戶名/密碼是否正確（在 `nas_service.py` 中）

### 問題 2：定時任務未執行

**症狀：** 數據長時間沒有更新

**解決方法：**

1. 檢查 Celery Beat 狀態：
   ```bash
   docker logs nt-celery-beat --tail 50
   ```

2. 檢查 Celery Worker 狀態：
   ```bash
   docker logs nt-celery-worker --tail 50
   ```

3. 重啟 Celery 服務：
   ```bash
   docker compose restart celery_beat celery_worker
   ```

### 問題 3：前端頁面無法載入

**症狀：** 訪問 `/nas-analytics` 顯示錯誤

**解決方法：**

1. 檢查 React 容器狀態：
   ```bash
   docker logs nt-react --tail 50
   ```

2. 重啟 React 服務：
   ```bash
   docker compose restart react
   ```

3. 檢查 Nginx 代理配置：
   ```bash
   docker exec nt-nginx nginx -t
   ```

## 📈 效能指標

### 預期效能

- **響應時間**：< 20 ms（LAN 環境）
- **上傳速度**：30-100 MB/s（取決於網路環境）
- **下載速度**：50-120 MB/s（取決於網路環境）
- **成功率**：> 99%（正常情況下）

### 數據量估算

- **每 5 分鐘記錄一次**
- **每小時 12 筆記錄**
- **每天 288 筆記錄**
- **2 週約 4,032 筆記錄**

## 🔐 安全性考慮

1. **密碼保護**：
   - NAS 密碼存儲在 `nas_service.py` 中
   - 生產環境應使用環境變數或 Django settings

2. **訪問控制**：
   - API 端點目前設置為 `AllowAny`
   - 生產環境應改為 `IsAuthenticated`

3. **數據加密**：
   - SMB 連線使用 NTLMv2 認證
   - 傳輸層使用 SMB2 協議

## 🚀 未來改進

- [ ] 支持多個 NAS 設備監控
- [ ] 添加告警功能（連線失敗時發送通知）
- [ ] 支持更多效能指標（IOPS、延遲等）
- [ ] 導出報表功能（Excel、PDF）
- [ ] 自定義監控頻率（從 5 分鐘調整為其他間隔）

## 📚 相關文件

- [Celery 定時任務配置](../CELERY_SETUP_GUIDE.md)
- [API 文檔](../../api/API_REFERENCE.md)
- [部署指南](../../deployment/DEPLOYMENT.md)

---

**最後更新**：2025-10-29  
**版本**：1.0.0  
**作者**：Network Toolbox Team
