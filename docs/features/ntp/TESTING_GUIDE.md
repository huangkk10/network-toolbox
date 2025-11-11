# NTP 時間同步分析 - 快速測試指南

## ✅ 功能測試清單

### 1. 前端頁面測試

#### 訪問頁面
- [ ] 打開瀏覽器訪問：`http://localhost`
- [ ] 登入系統
- [ ] 側邊欄點擊「NTP 分析」（在 IPXE 分析下方）
- [ ] 頁面正常載入，顯示 NTP 圖標

#### 統計卡片測試
- [ ] 4 個統計卡片顯示正常
  - [ ] 總記錄數（藍色，時鐘圖標）
  - [ ] 同步成功率（綠色，勾選圖標）
  - [ ] 平均響應時間（橙色，閃電圖標）
  - [ ] 平均時間偏移（紫色，同步圖標）
- [ ] 數值正確顯示（不為 0）

#### 圖表測試
- [ ] **同步統計圖**
  - [ ] 「每日統計」標籤可切換
  - [ ] 「每小時統計」標籤可切換
  - [ ] 折線圖顯示正常，有數據點
  - [ ] 滑鼠懸停顯示 Tooltip
  
- [ ] **同步狀態分佈（餅圖）**
  - [ ] 餅圖顯示成功/失敗比例
  - [ ] 顯示百分比標籤
  
- [ ] **時間偏移趨勢圖**
  - [ ] 折線圖顯示偏移量變化
  - [ ] Y 軸標籤正確（偏移量 ms）
  - [ ] X 軸時間標籤清晰
  
- [ ] **響應時間趨勢圖**
  - [ ] 折線圖顯示響應時間變化
  - [ ] 數據點連續（沒有大段空白）

#### 表格測試
- [ ] 表格顯示記錄列表
- [ ] 列標題正確
  - [ ] 時間、狀態、NTP Server
  - [ ] 響應時間、時間偏移、Stratum
  - [ ] 錯誤訊息
- [ ] **排序功能**
  - [ ] 點擊「時間」列排序
  - [ ] 點擊「響應時間」列排序
  - [ ] 點擊「時間偏移」列排序
- [ ] **篩選功能**
  - [ ] 點擊「狀態」列的篩選圖標
  - [ ] 選擇「成功」，只顯示成功記錄
  - [ ] 選擇「失敗」，只顯示失敗記錄
- [ ] **分頁功能**
  - [ ] 底部顯示分頁器
  - [ ] 顯示總筆數
  - [ ] 可切換每頁顯示數量

#### 時間範圍選擇測試
- [ ] 右上角下拉選單顯示
- [ ] 切換到「最近 1 天」，數據更新
- [ ] 切換到「最近 3 天」，數據更新
- [ ] 切換到「最近 7 天」，數據更新
- [ ] 切換到「最近 14 天」，數據更新

#### 自動刷新測試
- [ ] 等待 30 秒，頁面自動刷新
- [ ] 統計卡片數值可能變化
- [ ] 圖表數據可能更新

### 2. 後端 API 測試

#### API 端點測試

```bash
# 測試記錄列表 API
curl http://localhost/api/ntp-logs/ | jq

# 測試統計 API
curl http://localhost/api/ntp-logs/statistics/?days=7 | jq

# 測試過濾（只看成功記錄）
curl http://localhost/api/ntp-logs/?status=success | jq

# 測試時間範圍（最近1天）
curl http://localhost/api/ntp-logs/?days=1 | jq
```

**預期結果**：
- [ ] 返回 JSON 格式數據
- [ ] 包含完整的欄位（timestamp, status, response_time等）
- [ ] `statistics` 端點包含統計數據

#### 數據庫測試

```bash
# 檢查記錄數量
docker exec nt-django python manage.py shell -c "
from api.models import NTPSyncLog
print('總記錄數:', NTPSyncLog.objects.count())
print('成功記錄:', NTPSyncLog.objects.filter(status='success').count())
print('失敗記錄:', NTPSyncLog.objects.filter(status='failed').count())
"

# 查看最新記錄
docker exec nt-django python manage.py shell -c "
from api.models import NTPSyncLog
latest = NTPSyncLog.objects.order_by('-timestamp').first()
if latest:
    print(f'最新記錄: {latest.timestamp} - {latest.status}')
    print(f'NTP Server: {latest.ntp_server}')
    print(f'響應時間: {latest.response_time} ms')
"
```

**預期結果**：
- [ ] 顯示記錄數量（應該有數據）
- [ ] 最新記錄在最近 5 分鐘內

### 3. NTP 服務測試

```bash
# 執行 NTP 測試
docker exec nt-django python test_ntp.py

# 創建樣本數據
docker exec nt-django python test_ntp.py --sample
```

**預期結果**：
- [ ] 同步成功，顯示響應時間
- [ ] 顯示時間偏移、Stratum
- [ ] 記錄成功創建到資料庫

### 4. Celery 定時任務測試

#### 檢查任務配置

```bash
# 查看 NTP 定時任務
docker exec nt-django python manage.py shell -c "
from django_celery_beat.models import PeriodicTask
task = PeriodicTask.objects.filter(name__icontains='NTP').first()
if task:
    print(f'任務名稱: {task.name}')
    print(f'任務: {task.task}')
    print(f'間隔: {task.interval}')
    print(f'狀態: {\"啟用\" if task.enabled else \"停用\"}')
    print(f'上次執行: {task.last_run_at}')
else:
    print('未找到 NTP 任務')
"
```

**預期結果**：
- [ ] 顯示任務資訊
- [ ] 狀態：啟用
- [ ] 間隔：每 5 分鐘

#### 手動觸發任務

```bash
# 手動執行 NTP 檢測任務
docker exec nt-django python manage.py shell -c "
from api.tasks import check_ntp_sync_task
result = check_ntp_sync_task()
print('任務執行結果:', result)
"
```

**預期結果**：
- [ ] 任務成功執行
- [ ] 返回結果包含 success, timestamp 等欄位
- [ ] 資料庫新增一筆記錄

#### 查看 Celery 日誌

```bash
# 查看 Celery Worker 日誌
docker compose logs celery_worker --tail 50

# 查看 Celery Beat 日誌
docker compose logs celery_beat --tail 50
```

**預期結果**：
- [ ] 每 5 分鐘看到 NTP 檢測任務執行
- [ ] 日誌顯示成功或失敗資訊
- [ ] 沒有錯誤堆疊

### 5. 整合測試

#### 端到端測試

1. **等待 5 分鐘**
   - [ ] Celery Beat 自動觸發 NTP 檢測任務
   - [ ] 查看 Celery Worker 日誌，確認任務執行

2. **刷新前端頁面**
   - [ ] 總記錄數增加 1
   - [ ] 圖表更新最新數據點
   - [ ] 表格新增一筆記錄

3. **測試不同時間範圍**
   - [ ] 切換時間範圍，數據正確過濾
   - [ ] 統計數值相應變化

#### 壓力測試

```bash
# 快速創建多筆記錄（測試性能）
docker exec nt-django python -c "
import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'network_toolbox.settings')
django.setup()

from api.tasks import check_ntp_sync_task
for i in range(10):
    result = check_ntp_sync_task()
    print(f'{i+1}/10: {result.get(\"status\")}'  )
"
```

**預期結果**：
- [ ] 10 筆記錄成功創建
- [ ] 前端頁面載入速度正常
- [ ] 圖表渲染流暢

## 🐛 常見問題

### Q1: 前端顯示「暫無數據」

**解決方案**：
1. 檢查後端 API：`curl http://localhost/api/ntp-logs/`
2. 執行測試腳本創建樣本數據：`docker exec nt-django python test_ntp.py --sample`
3. 檢查瀏覽器 Console 錯誤

### Q2: NTP 同步一直失敗

**解決方案**：
1. 檢查網路連接：`docker exec nt-django ping 10.10.10.51`
2. 檢查 NTP 服務：`docker exec nt-django python test_ntp.py`
3. 檢查防火牆設置（UDP 123 端口）

### Q3: 定時任務不執行

**解決方案**：
1. 重啟 Celery：`docker compose restart celery_beat celery_worker`
2. 檢查任務配置：`docker exec nt-django python setup_ntp_tasks.py`
3. 查看 Celery 日誌

### Q4: 前端圖標未顯示

**解決方案**：
1. 檢查 Sidebar.js 是否正確導入 `ClockCircleOutlined`
2. 重啟 React：`docker compose restart react`
3. 清除瀏覽器緩存

## 📝 測試完成報告模板

```
NTP 時間同步分析功能測試報告
測試日期：2025-11-11
測試人員：[你的名字]

✅ 前端頁面測試：通過 / 失敗
   - 頁面載入：通過
   - 統計卡片：通過
   - 圖表顯示：通過
   - 表格功能：通過
   - 時間範圍：通過

✅ 後端 API 測試：通過 / 失敗
   - 記錄列表 API：通過
   - 統計 API：通過
   - 過濾功能：通過

✅ NTP 服務測試：通過 / 失敗
   - NTP 同步：通過
   - 數據記錄：通過

✅ Celery 任務測試：通過 / 失敗
   - 任務配置：通過
   - 自動執行：通過
   - 日誌記錄：通過

✅ 整合測試：通過 / 失敗
   - 端到端流程：通過
   - 自動刷新：通過

問題記錄：
1. [如有問題，在此記錄]

建議事項：
1. [如有建議，在此記錄]
```

## 🎉 測試完成

如果所有測試項目都通過，恭喜！NTP 時間同步分析功能已成功部署並正常運行。
