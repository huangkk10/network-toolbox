# Dashboard 使用者活動統計功能

## 📊 功能概述

在 Dashboard 中添加使用者活動統計功能，實時顯示每位使用者的 API 請求次數和活動情況。

## ✨ 主要功能

### 1. 自動記錄 API 訪問
- **自動記錄**：透過中間件自動記錄每個 API 請求
- **按日統計**：每天為每位使用者創建獨立的統計記錄
- **詳細分類**：
  - 總請求次數
  - 按 HTTP 方法分類（GET, POST, PUT, DELETE）
  - 錯誤統計
  - 熱門訪問路徑（TOP 10）

### 2. Dashboard 統計卡片

#### 今日統計
- **今日活躍使用者**：今天有 API 活動的使用者數量
- **今日 API 請求**：今天的總請求次數
- **平均請求/使用者**：今天每位使用者的平均請求數

#### 最活躍使用者排行（TOP 5）
顯示今日最活躍的前5位使用者：
- 排名和使用者名稱
- 總請求次數
- 按 HTTP 方法分類的請求統計
- 錯誤次數（如有）
- 請求佔比進度條

#### 過去7天活動趨勢
- 柱狀圖顯示每日 API 請求次數
- 顯示每日活躍使用者數量
- 雙 Y 軸設計，便於對比

## 🔧 技術實現

### 後端

#### 1. UserActivity 模型
```python
class UserActivity(models.Model):
    username = models.CharField(max_length=150)  # 使用者名稱
    date = models.DateField()                    # 統計日期
    total_requests = models.IntegerField()       # 總請求次數
    get_requests = models.IntegerField()         # GET 請求數
    post_requests = models.IntegerField()        # POST 請求數
    put_requests = models.IntegerField()         # PUT 請求數
    delete_requests = models.IntegerField()      # DELETE 請求數
    error_count = models.IntegerField()          # 錯誤次數
    top_paths = models.JSONField()               # 熱門路徑
```

#### 2. UserActivityMiddleware 中間件
自動記錄每個 API 請求：
- 僅記錄 `/api/` 開頭的請求
- 跳過高頻輪詢端點（如系統狀態查詢）
- 支援匿名使用者（記錄為 'anonymous'）
- 按日期自動彙總統計

#### 3. Dashboard API 增強
`/api/dashboard/stats/` 返回增加以下欄位：
```json
{
  "user_activity": {
    "active_users_today": 5,
    "total_requests_today": 553,
    "top_users_today": [...],
    "activity_trend": [...]
  }
}
```

### 前端

#### 更新的組件
- **DashboardPage.js**：添加使用者活動統計卡片和圖表
- 使用 Ant Design 的 `Statistic`、`List`、`Avatar` 組件
- 使用 Recharts 的 `BarChart` 顯示趨勢

## 📝 使用方式

### 查看統計
1. 訪問 Dashboard：`http://localhost/`
2. 自動顯示今日使用者活動統計
3. 查看最活躍使用者排行和趨勢圖表

### 測試功能
執行測試腳本生成模擬數據：
```bash
docker exec nt-django python generate_user_activity_test_data.py
```

## 📊 統計數據示例

### 今日統計
- 活躍使用者：5 人
- API 請求：553 次
- 平均請求：110.6 次/人

### TOP 使用者
1. 👑 testuser5 - 200 次（36%）
2. 🥈 testuser1 - 135 次（24%）
3. 🥉 testuser2 - 119 次（22%）

### 過去7天趨勢
- 2025-11-20: 5 人, 553 次
- 2025-11-19: 4 人, 246 次
- 2025-11-18: 2 人, 151 次
- ...

## 🔍 跳過記錄的端點

為避免過多無意義的記錄，以下端點不會被統計：
- `/api/dashboard/stats/` - Dashboard 統計本身
- `/api/system/status/` - 系統狀態查詢（頻繁輪詢）

可在 `UserActivityMiddleware` 中的 `skip_paths` 列表中添加更多需要跳過的端點。

## 🎯 未來擴展建議

1. **使用者詳情頁**
   - 點擊使用者名稱查看該使用者的詳細活動歷史
   - 顯示熱門訪問路徑、錯誤記錄等

2. **導出報告**
   - 支援導出 Excel/PDF 格式的活動報告
   - 按日期範圍篩選

3. **告警功能**
   - 當某使用者錯誤率過高時發送通知
   - 當 API 請求異常激增時告警

4. **API 使用分析**
   - 各 API 端點的使用頻率統計
   - 慢查詢分析和優化建議

5. **即時監控**
   - WebSocket 即時更新當前線上使用者
   - 即時顯示 API 請求流

## 📁 相關文件

- 模型：`backend/api/models.py` - `UserActivity`
- 中間件：`backend/library/middleware/user_activity.py`
- API：`backend/api/views/system.py` - `dashboard_stats()`
- 前端：`frontend/src/pages/DashboardPage.js`
- 測試：`backend/generate_user_activity_test_data.py`

## 🔄 資料庫遷移

已創建的遷移文件：
```
api/migrations/0025_useractivity.py
```

## ⚠️ 注意事項

1. **性能考量**
   - 中間件對每個請求都會執行，但操作很輕量
   - 使用 `update_or_create` 確保每天每使用者只有一筆記錄
   - 熱門路徑僅保留 TOP 10，避免 JSON 欄位過大

2. **匿名使用者**
   - 未登入的使用者會被記錄為 'anonymous'
   - 所有匿名請求會合併到同一個 'anonymous' 使用者下

3. **資料清理**
   - 建議定期清理過舊的活動記錄（如保留90天）
   - 可使用 Celery 定時任務自動清理

---

**更新日期**：2025-11-21  
**版本**：v1.0  
**狀態**：✅ 已實現並測試
