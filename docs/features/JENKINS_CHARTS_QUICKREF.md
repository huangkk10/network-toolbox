# Jenkins 圖表功能 - 快速參考

## 🎯 功能概述

在 RVT Analysis 頁面新增了三種 Jenkins Build 趨勢圖表：

1. **Build 趨勢線圖** - 成功/失敗/總數趨勢
2. **成功率面積圖** - 成功率百分比變化
3. **Build 數量堆疊圖** - 成功/失敗構建分佈

## 📊 查看圖表

1. 前往 RVT Analysis 頁面
2. 選擇 **Overview** 標籤
3. 使用時間範圍選擇器：
   - 今日 (每小時)
   - 最近 7 天 (每日)
   - 最近 14 天 (每日)
   - 最近 30 天 (每日)
   - 全部時間 (每日)

## 🔧 API 端點

```bash
# 基本用法
GET /api/jenkins-analytics/build-trend/?time_range=today

# 完整參數
GET /api/jenkins-analytics/build-trend/?time_range=week&granularity=daily&server_id=1
```

### 參數說明

| 參數 | 可選值 | 預設值 | 說明 |
|------|--------|--------|------|
| `time_range` | `today`, `week`, `2weeks`, `month`, `all` | `today` | 時間範圍 |
| `granularity` | `hourly`, `daily` | 自動 | 數據粒度 |
| `server_id` | 數字 或 `all` | `all` | Jenkins 伺服器 |

### 響應範例

```json
[
  {
    "time": "11/17 14:00",
    "total_builds": 45,
    "success_count": 32,
    "failure_count": 13,
    "success_rate": 71.1
  }
]
```

## 🛠️ 修改的檔案

### 後端 (3 個檔案)
- `backend/api/views/jenkins.py` - 新增 `jenkins_build_trend()` 函數
- `backend/api/views/__init__.py` - 導出函數
- `backend/api/urls.py` - 新增 URL 路由

### 前端 (2 個檔案)
- `frontend/src/components/jenkins/JenkinsStatisticsCharts.js` - **新建**圖表組件
- `frontend/src/pages/RVTAnalysisPage.js` - 整合圖表

## 🧪 測試命令

```bash
# 測試 API (今日數據)
docker exec nt-django python manage.py shell -c "
import requests
r = requests.get('http://localhost:8000/api/jenkins-analytics/build-trend/?time_range=today')
print(f'Status: {r.status_code}, Points: {len(r.json())}')
"

# 測試 API (週數據)
docker exec nt-django python manage.py shell -c "
import requests, json
r = requests.get('http://localhost:8000/api/jenkins-analytics/build-trend/?time_range=week')
data = r.json()
print(f'Points: {len(data)}')
with_data = [d for d in data if d['total_builds'] > 0]
if with_data: print(json.dumps(with_data[0], indent=2))
"
```

## 📝 使用範例

### 前端組件使用

```jsx
import JenkinsStatisticsCharts from '../components/jenkins/JenkinsStatisticsCharts';

// 基本用法
<JenkinsStatisticsCharts timeRange="today" serverId="all" />

// 指定伺服器
<JenkinsStatisticsCharts timeRange="week" serverId={12} />
```

### API 調用

```javascript
// 使用 axios
import axios from 'axios';

const fetchTrendData = async (timeRange = 'today') => {
  const response = await axios.get('/api/jenkins-analytics/build-trend/', {
    params: { time_range: timeRange }
  });
  return response.data;
};
```

## 🔍 故障排除

### 問題: 圖表顯示空狀態

**原因**: 選擇的時間範圍內沒有構建數據

**解決方案**: 
1. 切換到有數據的時間範圍 (例如: 最近 7 天)
2. 檢查 Jenkins 是否有執行構建

### 問題: API 返回 500 錯誤

**原因**: 可能是資料庫查詢錯誤

**解決方案**:
```bash
# 檢查 Django 日誌
docker logs nt-django --tail 50

# 重啟 Django 容器
docker restart nt-django
```

### 問題: 圖表不更新

**原因**: 前端緩存或狀態問題

**解決方案**:
1. 刷新頁面 (F5)
2. 清除瀏覽器緩存
3. 檢查瀏覽器 Console 是否有錯誤

## 📈 數據說明

### 成功率計算

```python
success_rate = (success_count / total_builds) * 100 if total_builds > 0 else 0
```

### 粒度選擇邏輯

- **今日**: 自動使用 `hourly` (每小時)
- **其他**: 自動使用 `daily` (每日)

### 時間格式

- **每小時**: `MM/DD HH:MM` (例: `11/17 14:00`)
- **每日**: `MM/DD` (例: `11/17`)

## 🎨 圖表配色

| 項目 | 顏色 | 用途 |
|------|------|------|
| 成功 | `#52c41a` | 綠色 - 成功構建 |
| 失敗 | `#ff4d4f` | 紅色 - 失敗構建 |
| 總計 | `#1890ff` | 藍色 - 總構建數 (虛線) |

## 💡 提示

1. **最佳實踐**: 使用「最近 7 天」查看趨勢，使用「今日」監控當前狀態
2. **性能**: 避免頻繁切換時間範圍，數據會自動緩存
3. **視覺效果**: 圖表支援響應式設計，自動適配螢幕尺寸

## 📚 相關文件

- [完整功能文檔](./JENKINS_CHARTS_FEATURE.md)
- [API 文檔](../api/)
- [Recharts 官方文檔](https://recharts.org/)

---

**最後更新**: 2025-11-19  
**版本**: 1.0.0
