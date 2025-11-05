# iPXE Celery 任務快速參考

## 🚀 5 分鐘快速新增任務

### 步驟 1：創建服務函數（30 秒）

**檔案**：`backend/library/services/ipxe_xxx_service.py`

```python
import logging
logger = logging.getLogger(__name__)

def fetch_ipxe_data(server_id: int) -> bool:
    """抓取 iPXE 資料（快捷函數）"""
    try:
        from api.models import IPXEServer
        
        server = IPXEServer.objects.get(id=server_id)
        logger.info(f'開始抓取資料: {server.name}')
        
        # TODO: 在這裡實現你的資料抓取邏輯
        # 例如：從 API 抓取、從 SSH 讀取日誌、從資料庫查詢等
        
        logger.info('資料抓取完成')
        return True
        
    except Exception as e:
        logger.error(f'資料抓取失敗: {e}', exc_info=True)
        return False
```

---

### 步驟 2：創建 Celery 任務（1 分鐘）

**檔案**：`backend/api/tasks.py`（在檔案末尾添加）

```python
@shared_task(
    bind=True,
    name='api.tasks.fetch_ipxe_data_task',  # 任務名稱（唯一）
    max_retries=2,                           # 最多重試 2 次
    default_retry_delay=60,                  # 失敗後 60 秒重試
    time_limit=300,                          # 硬限制 5 分鐘
    soft_time_limit=270                      # 軟限制 4.5 分鐘
)
def fetch_ipxe_data_task(self, server_id):
    """抓取 iPXE 資料定時任務"""
    try:
        logger.info(f'[Celery] 開始執行任務 - Server ID: {server_id}')
        
        from library.services.ipxe_xxx_service import fetch_ipxe_data
        
        success = fetch_ipxe_data(server_id)
        
        result = {
            'success': success,
            'server_id': server_id,
            'timestamp': timezone.now().isoformat()
        }
        
        logger.info(f'[Celery] 任務完成 - Success: {success}')
        return result
        
    except Exception as exc:
        logger.error('[Celery] 任務失敗', exc_info=True)
        raise self.retry(exc=exc, countdown=60)
```

---

### 步驟 3：配置排程（1 分鐘）

**檔案**：`backend/network_toolbox/celery.py`

在 `app.conf.beat_schedule` 字典中添加：

```python
app.conf.beat_schedule = {
    # ... 現有任務 ...
    
    # 新任務：每 10 分鐘執行一次
    'fetch-ipxe-data-every-10-minutes': {
        'task': 'api.tasks.fetch_ipxe_data_task',
        'schedule': crontab(minute='*/10'),  # 每 10 分鐘
        'kwargs': {
            'server_id': 1,  # iPXE Server ID
        },
        'options': {
            'expires': 540,  # 任務超時 9 分鐘
        }
    },
}
```

**常用排程配置**：
```python
crontab(minute='*/5')         # 每 5 分鐘
crontab(minute='*/10')        # 每 10 分鐘
crontab(minute='*/15')        # 每 15 分鐘
crontab(minute=0)             # 每小時
crontab(hour=2, minute=0)     # 每天凌晨 2 點
```

---

### 步驟 4：重啟服務（1 分鐘）

```bash
# 重啟 Celery Beat（必須）
docker compose restart celery_beat

# 重啟 Celery Worker（建議）
docker compose restart celery_worker

# 查看日誌確認
docker logs nt-celery-beat --tail 10
```

---

### 步驟 5：驗證（2 分鐘）

```bash
# 方法 1：查看 Flower 監控
# 訪問 http://localhost:5555

# 方法 2：查看 Celery Beat 日誌
docker logs nt-celery-beat | grep "fetch-ipxe-data"

# 方法 3：手動執行測試
docker exec -it nt-django python manage.py shell
>>> from api.tasks import fetch_ipxe_data_task
>>> result = fetch_ipxe_data_task.apply(kwargs={'server_id': 1})
>>> print(result.get())

# 方法 4：查看 Worker 日誌
docker logs nt-celery-worker --tail 50 -f
```

---

## 📋 實際範例模板

### 範例 1：從 API 抓取資料

```python
# backend/library/services/ipxe_api_service.py
import requests
import logging

logger = logging.getLogger(__name__)

def fetch_from_ipxe_api(server_id: int) -> bool:
    """從 iPXE API 抓取資料"""
    try:
        from api.models import IPXEServer, IPXEData
        
        server = IPXEServer.objects.get(id=server_id)
        
        # 發送 API 請求
        response = requests.get(
            f"http://{server.ip_address}/api/data",
            timeout=30
        )
        response.raise_for_status()
        data = response.json()
        
        # 儲存到資料庫
        for item in data:
            IPXEData.objects.update_or_create(
                server=server,
                record_id=item['id'],
                defaults={
                    'value': item['value'],
                    'timestamp': item['timestamp']
                }
            )
        
        logger.info(f'成功儲存 {len(data)} 筆資料')
        return True
        
    except Exception as e:
        logger.error(f'API 抓取失敗: {e}', exc_info=True)
        return False
```

---

### 範例 2：從 SSH 讀取日誌

```python
# backend/library/services/ipxe_log_service.py
import logging

logger = logging.getLogger(__name__)

def fetch_ipxe_logs(server_id: int) -> bool:
    """從 SSH 讀取 iPXE 日誌"""
    try:
        from api.models import IPXEServer
        from library.services.ssh_service import SSHService
        
        server = IPXEServer.objects.get(id=server_id)
        
        # 建立 SSH 連接
        ssh = SSHService(
            host=server.ip_address,
            port=server.ssh_port,
            username=server.ssh_username,
            password=server.ssh_password
        )
        
        if not ssh.connect():
            return False
        
        # 讀取日誌
        stdout, stderr = ssh.execute_command("tail -n 100 /var/log/ipxe.log")
        ssh.close()
        
        # 解析並儲存日誌
        lines = stdout.split('\n')
        logger.info(f'讀取到 {len(lines)} 行日誌')
        
        # TODO: 解析並儲存到資料庫
        
        return True
        
    except Exception as e:
        logger.error(f'日誌讀取失敗: {e}', exc_info=True)
        return False
```

---

### 範例 3：資料庫查詢與統計

```python
# backend/library/services/ipxe_stats_service.py
import logging
from django.db.models import Count
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

def calculate_ipxe_stats(server_id: int) -> bool:
    """計算 iPXE 統計資料"""
    try:
        from api.models import IPXEServer, IPXEBootRecord, IPXEDailyStats
        
        server = IPXEServer.objects.get(id=server_id)
        today = datetime.now().date()
        
        # 統計今天的開機次數
        boot_count = IPXEBootRecord.objects.filter(
            server=server,
            boot_time__date=today
        ).count()
        
        # 統計唯一 MAC 地址數量
        unique_macs = IPXEBootRecord.objects.filter(
            server=server,
            boot_time__date=today
        ).values('mac_address').distinct().count()
        
        # 儲存統計結果
        IPXEDailyStats.objects.update_or_create(
            server=server,
            date=today,
            defaults={
                'boot_count': boot_count,
                'unique_macs': unique_macs
            }
        )
        
        logger.info(
            f'統計完成 - '
            f'開機次數: {boot_count} | '
            f'唯一 MAC: {unique_macs}'
        )
        return True
        
    except Exception as e:
        logger.error(f'統計計算失敗: {e}', exc_info=True)
        return False
```

---

## 🎯 關鍵要點

### ✅ DO（推薦做法）

1. **使用 logger 記錄日誌**
   ```python
   logger.info('[Celery] 任務開始')
   logger.error('[Celery] 任務失敗', exc_info=True)
   ```

2. **設定適當的超時時間**
   ```python
   time_limit=300,        # 5 分鐘硬限制
   soft_time_limit=270,   # 4.5 分鐘軟限制
   ```

3. **處理異常並重試**
   ```python
   except Exception as exc:
       raise self.retry(exc=exc, countdown=60)
   ```

4. **返回有意義的結果**
   ```python
   return {
       'success': True,
       'count': 123,
       'timestamp': timezone.now().isoformat()
   }
   ```

### ❌ DON'T（避免的做法）

1. **不要忘記關閉資源連接**
   ```python
   # ❌ 錯誤
   ssh.connect()
   ssh.execute_command(cmd)
   # 忘記 ssh.close()
   
   # ✅ 正確
   try:
       ssh.connect()
       ssh.execute_command(cmd)
   finally:
       ssh.close()
   ```

2. **不要無限重試**
   ```python
   # ❌ 錯誤
   max_retries=None  # 會無限重試
   
   # ✅ 正確
   max_retries=3  # 最多重試 3 次
   ```

3. **不要忽略異常**
   ```python
   # ❌ 錯誤
   try:
       risky_operation()
   except:
       pass  # 吞掉所有錯誤
   
   # ✅ 正確
   try:
       risky_operation()
   except Exception as e:
       logger.error(f'操作失敗: {e}', exc_info=True)
       raise
   ```

---

## 🔍 故障排查

### 任務沒有執行？

```bash
# 1. 檢查 Celery Beat 是否運行
docker compose ps | grep celery_beat

# 2. 檢查任務是否已註冊
docker logs nt-celery-beat | grep "fetch-ipxe-data"

# 3. 檢查 Worker 是否運行
docker compose ps | grep celery_worker

# 4. 查看錯誤日誌
docker logs nt-celery-worker --tail 100
```

### 任務一直失敗？

```bash
# 1. 查看 Worker 詳細日誌
docker logs nt-celery-worker -f

# 2. 查看應用程式日誌
tail -f logs/django.log

# 3. 手動執行測試
docker exec -it nt-django python manage.py shell
>>> from api.tasks import fetch_ipxe_data_task
>>> result = fetch_ipxe_data_task.apply(kwargs={'server_id': 1})
>>> print(result.get())
```

### 如何暫停任務？

```bash
# 方法 1：註釋掉 celery.py 中的排程配置
# 然後重啟 celery_beat

# 方法 2：使用 Flower 停用任務
# 訪問 http://localhost:5555/tasks
```

---

## 📚 相關文檔

- 詳細指南：[ADDING_NEW_CELERY_TASK_GUIDE.md](./ADDING_NEW_CELERY_TASK_GUIDE.md)
- Celery 實施：[CELERY_IMPLEMENTATION_GUIDE.md](./CELERY_IMPLEMENTATION_GUIDE.md)
- 監控面板：http://localhost:5555

---

**最後更新**：2025-11-01  
**適用版本**：Network Toolbox v2.0+
