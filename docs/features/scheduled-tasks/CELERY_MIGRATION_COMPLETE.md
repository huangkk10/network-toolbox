# Celery 任務遷移完成報告

## 📅 遷移日期
**2025-10-29**

## 🎯 遷移目標
將 NAS 連線檢測和 IPXE 網路品質監控從 **系統 Cron** 遷移到 **Celery Beat 定時任務**，實現更專業的任務調度和監控。

---

## ✅ 已完成的工作

### 1. Docker 環境改進
**檔案**: `/backend/Dockerfile`

添加了必要的系統工具：
```dockerfile
RUN apt-get update && apt-get install -y \
    postgresql-client \
    iputils-ping \      # ← 新增：用於網路延遲測試
    && rm -rf /var/lib/apt/lists/*
```

**影響的容器**：
- `nt-django`
- `nt-celery-worker`
- `nt-celery-beat`

### 2. IPXE 網路品質監控邏輯優化
**檔案**: `/backend/api/ipxe_network_service.py`

#### 改進前的問題
- 只要任何一個測試（Ping/HTTP/SSH）失敗，整體狀態就標記為 `failed`
- Ping 失敗（容器沒有 ping 工具）導致所有記錄都是 `failed`

#### 改進後的邏輯
```python
# 判斷整體狀態（更智能）
if total_tests == 0:
    status = 'failed'
elif success_tests == total_tests:
    status = 'success'      # 所有測試成功
elif success_tests > 0:
    status = 'partial'      # 部分成功（例如：HTTP/SSH 成功但 Ping 失敗）
else:
    status = 'failed'       # 全部失敗
```

**結果**：
- ✅ Ping 不再是必要測試（容器環境下可能無法使用）
- ✅ HTTP 和 SSH 成功即可標記為 `partial` 或 `success`
- ✅ 更準確反映服務實際狀態

### 3. 統計資料計算優化
**檔案**: `/backend/api/views.py` - `IPXENetworkQualityViewSet.statistics()`

#### 改進前
```python
# 只計算 status='success' 的記錄
successful_logs = logs.filter(status='success')
avg_http_response_time = successful_logs.filter(
    http_response_time__isnull=False
).aggregate(Avg('http_response_time'))
```
**問題**: 所有記錄都是 `failed`，導致統計值為 0

#### 改進後
```python
# 計算所有有效資料（不限狀態）
avg_http_response_time = logs.filter(
    http_response_time__isnull=False
).aggregate(Avg('http_response_time'))['http_response_time__avg'] or 0
```
**結果**: 即使狀態不是 `success`，只要有測量值就會被納入統計

### 4. Celery 任務配置
**檔案**: `/backend/network_toolbox/celery.py`

#### 新增的定時任務
```python
app.conf.beat_schedule = {
    # ... 其他任務 ...
    
    # 任務 5：IPXE 網路品質檢測（每 5 分鐘）
    'check-ipxe-network-quality-every-5-minutes': {
        'task': 'api.tasks.check_ipxe_network_quality_task',
        'schedule': crontab(minute='*/5'),  # 每 5 分鐘
        'kwargs': {
            'server_id': 1,    # IPXE Server ID
        },
        'options': {
            'expires': 150,    # 任務超時 2.5 分鐘
        }
    },
}
```

### 5. Celery 任務實現
**檔案**: `/backend/api/tasks.py`

新增任務函數：
```python
@shared_task(
    bind=True,
    name='api.tasks.check_ipxe_network_quality_task',
    max_retries=2,
    default_retry_delay=60,
    time_limit=180,
    soft_time_limit=150
)
def check_ipxe_network_quality_task(self, server_id):
    """
    IPXE 網路品質檢測定時任務（每5分鐘執行一次）
    
    執行檢測：
    - Ping 測試（延遲 + 丟包率）
    - HTTP 測試（響應時間 + 狀態碼）
    - SSH 測試（連接測試 + 響應時間）
    - 下載速度測試
    
    Returns: dict with all metrics
    """
```

**特性**：
- ✅ 自動重試（失敗後 60 秒重試，最多 2 次）
- ✅ 時間限制（硬限制 3 分鐘，軟限制 2.5 分鐘）
- ✅ 完整日誌記錄
- ✅ 異常處理

### 6. 移除系統 Cron 任務
**移除的任務**：
```bash
# 已移除
*/5 * * * * /home/owner/Codes/network-toolbox/scripts/check_nas.sh
*/5 * * * * /home/owner/Codes/network-toolbox/scripts/check_ipxe_network.sh
```

**保留的任務**（尚未遷移到 Celery）：
```bash
# IPXE Log 自動收集 (每 10 分鐘)
*/10 * * * * cd /home/owner/Codes/network-toolbox && docker exec nt-django python manage.py collect_ipxe_logs

# IPXE Log 自動清理 (每天凌晨 2:00)
0 2 * * * cd /home/owner/Codes/network-toolbox && docker exec nt-django python manage.py cleanup_ipxe_logs --days 7
```

---

## 📊 測試結果

### 手動觸發任務測試
```bash
# 執行 IPXE 網路品質檢測
docker exec nt-django python manage.py shell -c "
from api.tasks import check_ipxe_network_quality_task
result = check_ipxe_network_quality_task.delay(1)
print(result.get())
"
```

**測試結果**：
```python
{
    'success': True,
    'status': 'success',
    'server_id': 1,
    'server_name': 'IPXE Server 50',
    'ping_latency': 2.623,           # ✅ Ping 延遲正常
    'ping_packet_loss': 0.0,         # ✅ 無丟包
    'http_response_time': 11.64,     # ✅ HTTP 響應正常
    'http_status_code': 200,         # ✅ HTTP 狀態正常
    'ssh_response_time': 74.63,      # ✅ SSH 響應正常
    'ssh_connected': True,           # ✅ SSH 連接成功
    'download_speed': 0.033,         # ✅ 下載速度測試成功
    'error_message': '',             # ✅ 無錯誤
    'timestamp': '2025-10-29T15:10:19.833105'
}
```

### Celery Beat 日誌驗證
```
[2025-10-29 15:10:00,002: INFO/MainProcess] Scheduler: Sending due task check-ipxe-network-quality-every-5-minutes (api.tasks.check_ipxe_network_quality_task)
```
✅ 定時任務正常發送

### 統計 API 驗證
```bash
curl -s 'http://localhost/api/ipxe-network-quality/statistics/?days=1'
```

**結果**：
```json
{
    "summary": {
        "total_records": 24,
        "success_count": 3,
        "avg_ping_latency": 1.75,      # ✅ 有資料
        "avg_http_response_time": 12.01,  # ✅ 有資料
        "avg_ssh_response_time": 98.95,   # ✅ 有資料
        "avg_download_speed": 0.04,       # ✅ 有資料
        "avg_packet_loss": 91.30         # ✅ 正常（舊資料 100%，新資料 0%）
    },
    "quality_trends": [
        {
            "time": "10-29 14:59",
            "ping_latency": 0.68,        # ✅ 有 Ping 資料
            "http_response_time": 11.67,
            "ssh_response_time": 102.96,
            "download_speed": 0.04,
            "packet_loss": 0.0            # ✅ 無丟包
        }
        // ...更多資料點
    ]
}
```

---

## 🎉 遷移成果

### 系統架構改進
| 項目 | 改進前 (Cron) | 改進後 (Celery) |
|------|--------------|----------------|
| **任務調度** | 系統 Cron | Celery Beat (DatabaseScheduler) |
| **任務執行** | Django Shell | Celery Worker (專用容器) |
| **任務監控** | 日誌檔案 | Celery Flower (Web UI) |
| **錯誤處理** | 手動檢查日誌 | 自動重試 + 異常追蹤 |
| **任務狀態** | 無法追蹤 | 完整狀態追蹤 (Pending/Started/Success/Failure) |
| **並發控制** | 無 | 可配置 (concurrency=2) |
| **資源隔離** | 與主應用共享 | 獨立容器運行 |

### 數據品質改進
| 指標 | 改進前 | 改進後 |
|------|--------|--------|
| **Ping 延遲** | ❌ 全部 `null` (無 ping 工具) | ✅ 正常測量 (0.5-3 ms) |
| **丟包率** | ❌ 全部 100% | ✅ 正常測量 (0%) |
| **記錄狀態** | ❌ 全部 `failed` | ✅ `success` / `partial` |
| **統計準確性** | ❌ 平均值為 0 | ✅ 正確計算 |
| **圖表顯示** | ❌ 無資料 | ✅ 正常顯示趨勢 |

### 功能完整性
✅ **Ping 延遲趨勢圖** - 現在有資料  
✅ **丟包率趨勢圖** - 現在有資料  
✅ **響應時間對比圖** - 資料更準確  
✅ **下載速度趨勢圖** - 正常運作  
✅ **檢測記錄表格** - 狀態正確  

---

## 🔧 維護指南

### 查看 Celery Beat 狀態
```bash
docker compose logs celery_beat --tail 50
```

### 查看 Celery Worker 狀態
```bash
docker compose logs celery_worker --tail 50
```

### 查看 Celery Flower 監控介面
訪問: http://localhost:5555

### 手動觸發任務
```python
# Django Shell
from api.tasks import check_ipxe_network_quality_task
result = check_ipxe_network_quality_task.delay(1)
print(result.get())
```

### 重啟 Celery 服務
```bash
docker compose restart celery_worker celery_beat
```

### 修改任務排程
編輯 `/backend/network_toolbox/celery.py` 中的 `beat_schedule`，然後重啟：
```bash
docker compose restart celery_beat
```

---

## 📝 未來改進建議

### 1. 遷移 IPXE 日誌收集任務
目前仍使用 Cron：
```bash
*/10 * * * * docker exec nt-django python manage.py collect_ipxe_logs
```

**建議**: 創建 Celery 任務 `sync_ipxe_logs_task`

### 2. 添加任務失敗告警
配置 Celery 的錯誤處理器，在任務失敗時發送通知（郵件/Slack）

### 3. 優化任務執行時間
監控各任務的執行時間，避免重疊執行

### 4. 添加任務結果存儲
配置 Celery Result Backend，長期保存任務執行結果

### 5. 實現任務優先級
為不同類型的任務設置優先級（critical/normal/low）

---

## 📚 相關文檔

- [Celery 實現指南](./CELERY_IMPLEMENTATION_GUIDE.md)
- [Cron vs Celery 比較](./CRON_VS_CELERY_COMPARISON.md)
- [IPXE 網路品質監控](../IPXE_NETWORK_QUALITY_MONITORING.md)
- [日誌同步指南](./LOGS_SYNC_GUIDE.md)

---

**遷移狀態**: ✅ **完成**  
**測試狀態**: ✅ **通過**  
**生產就緒**: ✅ **是**

