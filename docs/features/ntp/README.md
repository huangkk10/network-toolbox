# NTP 時間同步分析功能

## 📋 更新日期
2025-11-11

## 🎯 功能概述

新增 **NTP 時間同步分析** 頁面，用於監控和分析系統與 NTP 伺服器的時間同步狀況。

## 🌟 主要功能

### 1. 前端頁面（NTP 分析）

**位置**：側邊欄 → IPXE 分析下方 → NTP 分析

**功能特點**：
- 📊 **實時統計卡片**
  - 總記錄數
  - 同步成功率
  - 平均響應時間
  - 平均時間偏移

- 📈 **多維度圖表**
  - 每日同步統計（折線圖）
  - 每小時同步統計（面積圖）
  - 同步狀態分佈（餅圖）
  - 時間偏移趨勢（折線圖）
  - 響應時間趨勢（折線圖）

- 📝 **詳細記錄表格**
  - 時間、狀態、NTP Server
  - 響應時間、時間偏移、Stratum
  - 錯誤訊息
  - 支援排序、篩選、分頁

- ⏱️ **時間範圍選擇**
  - 最近 1 天
  - 最近 3 天
  - 最近 7 天
  - 最近 14 天

- 🔄 **自動刷新**
  - 每 30 秒自動更新數據

### 2. 後端實現

#### 2.1 數據模型（NTPSyncLog）

```python
class NTPSyncLog(models.Model):
    timestamp = DateTimeField()          # 記錄時間
    status = CharField()                 # 'success' | 'failed'
    ntp_server = GenericIPAddressField() # NTP 伺服器 IP
    response_time = FloatField()         # 響應時間 (ms)
    offset = FloatField()                # 時間偏移 (ms)
    stratum = IntegerField()             # Stratum 層級
    jitter = FloatField()                # 時間抖動 (ms)
    error_message = TextField()          # 錯誤訊息
```

**索引優化**：
- 時間戳索引（用於快速查詢）
- 狀態索引（用於統計）
- 組合索引（時間+狀態）

#### 2.2 NTP 服務（ntp_service.py）

**核心功能**：
```python
class NTPService:
    def check_sync() -> Dict:
        """檢查 NTP 時間同步狀態"""
        - 發送 NTP 請求
        - 計算響應時間
        - 獲取時間偏移
        - 獲取 Stratum 層級
        - 處理錯誤
```

**使用 ntplib 庫**：
- NTP v4 協議
- UDP Port 123
- 5 秒超時

#### 2.3 API 端點

**ViewSet**: `NTPSyncLogViewSet`

**端點**：
- `GET /api/ntp-logs/` - 獲取記錄列表
  - 查詢參數：`days` (時間範圍), `status` (狀態過濾)
  
- `GET /api/ntp-logs/statistics/` - 獲取統計資料
  - 返回：基本統計、每日統計、每小時統計、趨勢數據

**數據示例**：
```json
{
  "total_records": 289,
  "success_count": 260,
  "failed_count": 29,
  "success_rate": 89.97,
  "avg_response_time": 29.45,
  "avg_offset": -0.823,
  "avg_jitter": 2.456,
  "daily_stats": [...],
  "hourly_stats": [...],
  "offset_trends": [...],
  "response_trends": [...]
}
```

#### 2.4 Celery 定時任務

**任務名稱**：`api.tasks.check_ntp_sync_task`

**執行頻率**：每 5 分鐘

**任務流程**：
1. 調用 NTP 服務檢查同步狀態
2. 記錄結果到數據庫
3. 記錄日誌（成功/失敗）
4. 自動重試（最多 2 次）

**重試策略**：
- 失敗後 60 秒重試
- 最多重試 2 次

## 🛠️ 技術棧

### 前端
- **React** 18.2
- **Ant Design** 5.x
- **recharts** - 圖表庫
- **axios** - HTTP 客戶端

### 後端
- **Django** 4.2
- **Django REST Framework** 3.14
- **ntplib** 0.4.0 - NTP 協議客戶端
- **Celery** 5.3.4 - 定時任務
- **PostgreSQL** - 數據庫

## 📦 安裝依賴

### 後端依賴

```bash
# requirements.txt
ntplib>=0.4.0  # NTP 協議客戶端
```

### 安裝命令

```bash
# 在 Django 容器中
docker exec nt-django pip install ntplib

# 或重建容器
docker compose up -d --build django
```

## 🚀 部署步驟

### 1. 資料庫遷移

```bash
# 創建遷移
docker exec nt-django python manage.py makemigrations

# 執行遷移
docker exec nt-django python manage.py migrate
```

### 2. 設置定時任務

```bash
# 執行設置腳本
docker exec nt-django python setup_ntp_tasks.py
```

### 3. 創建測試數據（可選）

```bash
# 執行 NTP 測試
docker exec nt-django python test_ntp.py

# 創建樣本數據（過去24小時）
docker exec nt-django python test_ntp.py --sample
```

### 4. 重啟服務

```bash
# 重啟 Django
docker compose restart django

# 重啟 React
docker compose restart react

# 重啟 Celery Worker（如果需要）
docker compose restart celery-worker
docker compose restart celery-beat
```

## 📊 使用說明

### 訪問頁面

1. 登入 Network Toolbox
2. 側邊欄選擇「NTP 分析」
3. 查看實時統計和圖表

### 功能操作

**查看不同時間範圍**：
- 右上角選擇時間範圍（1天/3天/7天/14天）

**篩選記錄**：
- 在表格中使用「狀態」列的篩選器
- 點擊列標題進行排序

**查看詳細資訊**：
- 滑鼠懸停在圖表上查看具體數值
- 表格中查看完整錯誤訊息

## 🔧 配置說明

### NTP 伺服器配置

**當前配置**：`10.10.10.51`

**修改方式**：

1. **前端顯示**（`NTPAnalyticsPage.js`）：
```javascript
<Text>NTP Server: 10.10.10.51</Text>
```

2. **後端默認值**（`models.py`）：
```python
ntp_server = models.GenericIPAddressField(
    verbose_name='NTP Server', 
    default='10.10.10.51'
)
```

3. **Celery 任務**（`tasks.py`）：
```python
ntp_server = '10.10.10.51'
```

### 定時任務配置

**修改檢測頻率**：

```python
# setup_ntp_tasks.py
interval, created = IntervalSchedule.objects.get_or_create(
    every=5,  # 修改這個數字（分鐘）
    period=IntervalSchedule.MINUTES,
)
```

## 📈 性能優化

### 1. 數據庫索引

- 時間戳索引：快速查詢最近記錄
- 狀態索引：快速統計成功/失敗
- 組合索引：優化常用查詢

### 2. 數據保留策略

**建議配置**：
- 保留最近 2 週的詳細記錄
- 每天執行清理任務（Celery Beat）

**清理腳本示例**：
```python
from datetime import timedelta
from django.utils import timezone

# 刪除 14 天前的記錄
cutoff_date = timezone.now() - timedelta(days=14)
NTPSyncLog.objects.filter(timestamp__lt=cutoff_date).delete()
```

### 3. 前端優化

- 使用 `connectNulls={true}` 處理缺失數據
- 圖表自動調整採樣間隔（根據時間範圍）
- 30 秒自動刷新，避免過於頻繁

## 🐛 故障排查

### 問題 1：NTP 同步一直失敗

**可能原因**：
- NTP 伺服器不可達
- 防火牆阻擋 UDP 123 端口
- NTP 服務未啟動

**解決方案**：
```bash
# 測試 NTP 伺服器
docker exec nt-django python test_ntp.py

# 檢查網路連接
docker exec nt-django ping 10.10.10.51

# 檢查端口
docker exec nt-django nc -zvu 10.10.10.51 123
```

### 問題 2：定時任務未執行

**檢查步驟**：
```bash
# 檢查 Celery Worker 狀態
docker compose logs celery-worker --tail 50

# 檢查 Celery Beat 狀態
docker compose logs celery-beat --tail 50

# 檢查定時任務配置
docker exec nt-django python manage.py shell -c "
from django_celery_beat.models import PeriodicTask
print(PeriodicTask.objects.filter(name__icontains='NTP'))
"
```

### 問題 3：前端顯示空數據

**檢查步驟**：
1. 檢查後端 API：`http://localhost/api/ntp-logs/`
2. 檢查數據庫記錄數量
3. 查看瀏覽器 Console 錯誤
4. 檢查 Django 日誌

## 📝 待辦事項

- [ ] 添加多個 NTP 伺服器支持
- [ ] 添加告警功能（時間偏移過大時發送通知）
- [ ] 添加導出功能（CSV/Excel）
- [ ] 添加 Stratum 層級趨勢圖
- [ ] 添加比較功能（與其他時間段對比）

## 🔗 相關文檔

- [NTP 協議](https://tools.ietf.org/html/rfc5905)
- [ntplib 文檔](https://pypi.org/project/ntplib/)
- [Django Celery Beat](https://docs.celeryproject.org/en/stable/userguide/periodic-tasks.html)
- [Ant Design Charts](https://ant.design/components/overview/)
- [recharts 文檔](https://recharts.org/)

## 📌 總結

此次更新成功添加了 NTP 時間同步分析功能，包含：
- ✅ 完整的前端分析頁面
- ✅ 後端 API 和數據模型
- ✅ NTP 同步檢測服務
- ✅ Celery 定時任務（每 5 分鐘）
- ✅ 多維度統計圖表
- ✅ 詳細記錄表格
- ✅ 自動數據刷新
- ✅ 測試腳本和樣本數據

**使用者可以**：
- 實時監控 NTP 同步狀態
- 查看歷史趨勢
- 分析同步問題
- 評估時間準確性
