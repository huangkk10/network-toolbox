# 如何在 iPXE 功能中加入新的 Celery 定期任務

## 📚 目錄

1. [概述](#概述)
2. [完整步驟](#完整步驟)
3. [實際範例](#實際範例)
4. [測試與驗證](#測試與驗證)
5. [常見問題](#常見問題)

---

## 概述

本文檔將指導您如何在 iPXE 功能中加入新的 Celery 定期任務來自動抓取資料。

### 前置條件

- ✅ Celery 服務已經運行（redis, celery_beat, celery_worker）
- ✅ 了解基本的 Django 和 Celery 概念
- ✅ 準備好要抓取的資料來源（API、資料庫、檔案等）

### 系統架構

```
┌─────────────────────────────────────────┐
│  Celery Beat (排程器)                    │
│  - 讀取 celery.py 的排程配置              │
│  - 每 X 分鐘觸發任務                      │
└─────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────┐
│  Redis (訊息佇列)                        │
│  - 接收任務請求                           │
│  - 分發給 Worker                         │
└─────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────┐
│  Celery Worker (執行器)                  │
│  - 從 api/tasks.py 讀取任務定義           │
│  - 執行實際的資料抓取邏輯                  │
└─────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────┐
│  PostgreSQL (資料庫)                     │
│  - 儲存抓取的資料                         │
└─────────────────────────────────────────┘
```

---

## 完整步驟

### 步驟 1：定義資料模型（如果需要新的資料表）

**檔案位置**：`backend/api/models.py`

```python
from django.db import models

class IPXEBootRecord(models.Model):
    """iPXE 開機記錄（範例）"""
    server = models.ForeignKey('IPXEServer', on_delete=models.CASCADE)
    mac_address = models.CharField(max_length=17)
    ip_address = models.GenericIPAddressField()
    boot_time = models.DateTimeField(auto_now_add=True)
    boot_status = models.CharField(max_length=20)
    error_message = models.TextField(blank=True, null=True)
    
    class Meta:
        db_table = 'ipxe_boot_records'
        ordering = ['-boot_time']
        indexes = [
            models.Index(fields=['mac_address']),
            models.Index(fields=['boot_time']),
        ]
    
    def __str__(self):
        return f"{self.mac_address} - {self.boot_time}"
```

**執行資料庫遷移**：
```bash
docker exec nt-django python manage.py makemigrations
docker exec nt-django python manage.py migrate
```

---

### 步驟 2：創建資料抓取服務

**檔案位置**：`backend/library/services/ipxe_boot_service.py`（新建）

```python
"""
iPXE 開機記錄抓取服務

提供從各種來源抓取 iPXE 開機記錄的功能
"""

import logging
import requests
from typing import Dict, List, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class IPXEBootService:
    """iPXE 開機記錄服務"""
    
    def __init__(self, server_id: int):
        """
        初始化服務
        
        Args:
            server_id: IPXEServer ID
        """
        self.server_id = server_id
        self.server = None
    
    def fetch_boot_records(self) -> Dict:
        """
        抓取開機記錄
        
        Returns:
            dict: {
                'success': bool,
                'records': List[dict],
                'count': int,
                'error_message': str
            }
        """
        try:
            # 1. 獲取伺服器資訊
            from api.models import IPXEServer
            
            self.server = IPXEServer.objects.get(id=self.server_id)
            logger.info(f'開始抓取 iPXE 開機記錄 - Server: {self.server.name}')
            
            # 2. 從資料來源抓取資料
            records = self._fetch_from_api()
            # 或者使用其他方式：
            # records = self._fetch_from_ssh()
            # records = self._fetch_from_log_file()
            
            # 3. 儲存到資料庫
            saved_count = self._save_records(records)
            
            logger.info(
                f'iPXE 開機記錄抓取完成 - '
                f'Server: {self.server.name} | '
                f'抓取: {len(records)} 筆 | '
                f'儲存: {saved_count} 筆'
            )
            
            return {
                'success': True,
                'records': records,
                'count': len(records),
                'saved_count': saved_count,
                'error_message': ''
            }
            
        except Exception as e:
            logger.error(f'抓取 iPXE 開機記錄失敗: {e}', exc_info=True)
            return {
                'success': False,
                'records': [],
                'count': 0,
                'saved_count': 0,
                'error_message': str(e)
            }
    
    def _fetch_from_api(self) -> List[Dict]:
        """
        從 API 抓取資料（範例）
        
        Returns:
            List[dict]: 開機記錄列表
        """
        try:
            # 假設 iPXE 伺服器提供 API
            api_url = f"http://{self.server.ip_address}/api/boot-records"
            
            # 設定查詢參數（例如：只抓取最近 1 小時的記錄）
            params = {
                'since': (datetime.now() - timedelta(hours=1)).isoformat(),
                'limit': 100
            }
            
            # 發送 HTTP 請求
            response = requests.get(
                api_url,
                params=params,
                timeout=30
            )
            
            response.raise_for_status()
            data = response.json()
            
            logger.info(f'從 API 抓取到 {len(data)} 筆記錄')
            return data
            
        except requests.RequestException as e:
            logger.error(f'API 請求失敗: {e}')
            return []
    
    def _fetch_from_ssh(self) -> List[Dict]:
        """
        從 SSH 抓取日誌檔案（範例）
        
        Returns:
            List[dict]: 開機記錄列表
        """
        try:
            from library.services.ssh_service import SSHService
            
            # 建立 SSH 連接
            ssh = SSHService(
                host=self.server.ip_address,
                port=self.server.ssh_port,
                username=self.server.ssh_username,
                password=self.server.ssh_password
            )
            
            if not ssh.connect():
                return []
            
            # 讀取日誌檔案
            command = "tail -n 100 /var/log/ipxe/boot.log"
            stdout, stderr = ssh.execute_command(command)
            
            ssh.close()
            
            # 解析日誌
            records = self._parse_log_lines(stdout.split('\n'))
            
            logger.info(f'從 SSH 抓取到 {len(records)} 筆記錄')
            return records
            
        except Exception as e:
            logger.error(f'SSH 抓取失敗: {e}')
            return []
    
    def _parse_log_lines(self, lines: List[str]) -> List[Dict]:
        """
        解析日誌行（範例）
        
        Args:
            lines: 日誌行列表
            
        Returns:
            List[dict]: 解析後的記錄
        """
        records = []
        
        for line in lines:
            if not line.strip():
                continue
            
            try:
                # 假設日誌格式：2025-11-01 08:00:00 | MAC: AA:BB:CC:DD:EE:FF | IP: 192.168.1.100 | Status: success
                parts = line.split(' | ')
                
                if len(parts) >= 4:
                    record = {
                        'boot_time': parts[0].strip(),
                        'mac_address': parts[1].split(': ')[1].strip(),
                        'ip_address': parts[2].split(': ')[1].strip(),
                        'boot_status': parts[3].split(': ')[1].strip(),
                    }
                    records.append(record)
                    
            except Exception as e:
                logger.warning(f'解析日誌行失敗: {line} - {e}')
                continue
        
        return records
    
    def _save_records(self, records: List[Dict]) -> int:
        """
        儲存記錄到資料庫
        
        Args:
            records: 記錄列表
            
        Returns:
            int: 成功儲存的數量
        """
        from api.models import IPXEBootRecord
        
        saved_count = 0
        
        for record in records:
            try:
                # 檢查是否已存在（避免重複）
                exists = IPXEBootRecord.objects.filter(
                    server=self.server,
                    mac_address=record['mac_address'],
                    boot_time=record['boot_time']
                ).exists()
                
                if not exists:
                    IPXEBootRecord.objects.create(
                        server=self.server,
                        mac_address=record['mac_address'],
                        ip_address=record['ip_address'],
                        boot_time=record['boot_time'],
                        boot_status=record.get('boot_status', 'unknown'),
                        error_message=record.get('error_message', '')
                    )
                    saved_count += 1
                    
            except Exception as e:
                logger.warning(f'儲存記錄失敗: {record} - {e}')
                continue
        
        return saved_count


def collect_ipxe_boot_records(server_id: int) -> bool:
    """
    收集 iPXE 開機記錄（快捷函數）
    
    Args:
        server_id: IPXEServer ID
        
    Returns:
        bool: 是否成功
    """
    service = IPXEBootService(server_id)
    result = service.fetch_boot_records()
    return result['success']
```

---

### 步驟 3：創建 Celery 任務

**檔案位置**：`backend/api/tasks.py`

在檔案末尾添加新任務：

```python
@shared_task(
    bind=True,
    name='api.tasks.collect_ipxe_boot_records_task',
    max_retries=2,
    default_retry_delay=60,  # 失敗後 1 分鐘重試
    time_limit=300,  # 硬限制 5 分鐘
    soft_time_limit=270  # 軟限制 4.5 分鐘
)
def collect_ipxe_boot_records_task(self, server_id):
    """
    收集 iPXE 開機記錄定時任務
    
    Args:
        server_id: IPXEServer ID
    
    Returns:
        dict: {
            'success': bool,
            'server_id': int,
            'server_name': str,
            'records_count': int,
            'saved_count': int,
            'error_message': str,
            'timestamp': str
        }
    """
    try:
        logger.info(f'[Celery] 開始收集 iPXE 開機記錄 - Server ID: {server_id}')
        
        # 使用服務執行資料抓取
        from library.services.ipxe_boot_service import IPXEBootService
        from .models import IPXEServer
        
        service = IPXEBootService(server_id)
        result = service.fetch_boot_records()
        
        # 獲取伺服器資訊
        try:
            server = IPXEServer.objects.get(id=server_id)
            server_name = server.name
        except IPXEServer.DoesNotExist:
            logger.error(f'[Celery] IPXE Server ID {server_id} 不存在')
            return {
                'success': False,
                'server_id': server_id,
                'server_name': 'Unknown',
                'records_count': 0,
                'saved_count': 0,
                'error_message': f'IPXE Server ID {server_id} 不存在',
                'timestamp': timezone.now().isoformat()
            }
        
        # 構建返回結果
        task_result = {
            'success': result['success'],
            'server_id': server_id,
            'server_name': server_name,
            'records_count': result['count'],
            'saved_count': result.get('saved_count', 0),
            'error_message': result.get('error_message', ''),
            'timestamp': timezone.now().isoformat(),
        }
        
        logger.info(
            f'[Celery] iPXE 開機記錄收集完成 - '
            f'Server: {server_name} | '
            f'抓取: {task_result["records_count"]} 筆 | '
            f'儲存: {task_result["saved_count"]} 筆'
        )
        
        return task_result
        
    except Exception as exc:
        logger.error('[Celery] 收集 iPXE 開機記錄失敗', exc_info=True)
        
        # 自動重試（最多 2 次）
        try:
            raise self.retry(exc=exc, countdown=60)
        except self.MaxRetriesExceededError:
            logger.error('[Celery] 收集 iPXE 開機記錄重試次數已達上限')
            return {
                'success': False,
                'server_id': server_id,
                'server_name': 'Unknown',
                'records_count': 0,
                'saved_count': 0,
                'error_message': str(exc),
                'timestamp': timezone.now().isoformat()
            }
```

---

### 步驟 4：配置定時排程

**檔案位置**：`backend/network_toolbox/celery.py`

在 `app.conf.beat_schedule` 字典中添加新任務：

```python
app.conf.beat_schedule = {
    # ... 現有任務 ...
    
    # 任務 8：iPXE 開機記錄收集（每 15 分鐘）
    'collect-ipxe-boot-records-every-15-minutes': {
        'task': 'api.tasks.collect_ipxe_boot_records_task',
        'schedule': crontab(minute='*/15'),  # 每 15 分鐘執行一次
        'kwargs': {
            'server_id': 1,    # IPXE Server ID
        },
        'options': {
            'expires': 810,    # 任務超時 13.5 分鐘（避免與下次重疊）
        }
    },
}
```

**常用的排程設定**：

```python
# 每 5 分鐘
'schedule': crontab(minute='*/5')

# 每 10 分鐘
'schedule': crontab(minute='*/10')

# 每小時
'schedule': crontab(minute=0)

# 每天凌晨 2 點
'schedule': crontab(hour=2, minute=0)

# 每週一早上 8 點
'schedule': crontab(day_of_week=1, hour=8, minute=0)

# 每月 1 號凌晨 3 點
'schedule': crontab(day_of_month=1, hour=3, minute=0)
```

---

### 步驟 5：重啟 Celery 服務

```bash
# 重啟 Celery Beat（排程器）
docker compose restart celery_beat

# 重啟 Celery Worker（執行器）
docker compose restart celery_worker

# 查看日誌確認任務已加載
docker logs nt-celery-beat --tail 20
docker logs nt-celery-worker --tail 20
```

**成功的日誌範例**：
```
[2025-11-01 08:00:00,001: INFO/MainProcess] Scheduler: Sending due task collect-ipxe-boot-records-every-15-minutes (api.tasks.collect_ipxe_boot_records_task)
[2025-11-01 08:00:00,012: INFO/ForkPoolWorker-1] [Celery] 開始收集 iPXE 開機記錄 - Server ID: 1
[2025-11-01 08:00:03,456: INFO/ForkPoolWorker-1] [Celery] iPXE 開機記錄收集完成 - Server: IPXE Server 50 | 抓取: 25 筆 | 儲存: 25 筆
```

---

## 實際範例

### 範例 1：從 API 抓取 iPXE 啟動統計

**服務檔案**：`backend/library/services/ipxe_stats_service.py`

```python
import requests
import logging

logger = logging.getLogger(__name__)

class IPXEStatsService:
    """iPXE 統計資料服務"""
    
    def __init__(self, server_id: int):
        self.server_id = server_id
    
    def fetch_daily_stats(self) -> dict:
        """抓取每日統計"""
        try:
            from api.models import IPXEServer, IPXEDailyStats
            
            server = IPXEServer.objects.get(id=self.server_id)
            
            # 從 API 獲取統計資料
            response = requests.get(
                f"http://{server.ip_address}/api/stats/daily",
                timeout=30
            )
            response.raise_for_status()
            data = response.json()
            
            # 儲存到資料庫
            stats, created = IPXEDailyStats.objects.update_or_create(
                server=server,
                date=timezone.now().date(),
                defaults={
                    'boot_count': data['boot_count'],
                    'success_count': data['success_count'],
                    'failed_count': data['failed_count'],
                    'unique_macs': data['unique_macs'],
                }
            )
            
            logger.info(f'iPXE 統計資料更新完成: {stats}')
            return {'success': True, 'stats': stats}
            
        except Exception as e:
            logger.error(f'抓取統計資料失敗: {e}', exc_info=True)
            return {'success': False, 'error': str(e)}

def fetch_ipxe_stats(server_id: int) -> bool:
    """快捷函數"""
    service = IPXEStatsService(server_id)
    result = service.fetch_daily_stats()
    return result['success']
```

**任務檔案**：`backend/api/tasks.py`

```python
@shared_task(bind=True, name='api.tasks.fetch_ipxe_stats_task')
def fetch_ipxe_stats_task(self, server_id):
    """每小時抓取一次統計資料"""
    from library.services.ipxe_stats_service import fetch_ipxe_stats
    
    try:
        success = fetch_ipxe_stats(server_id)
        return {'success': success, 'server_id': server_id}
    except Exception as exc:
        raise self.retry(exc=exc, countdown=300)  # 5 分鐘後重試
```

**排程配置**：
```python
'fetch-ipxe-stats-hourly': {
    'task': 'api.tasks.fetch_ipxe_stats_task',
    'schedule': crontab(minute=0),  # 每小時
    'kwargs': {'server_id': 1},
}
```

---

### 範例 2：從日誌檔案解析開機事件

**服務檔案**：`backend/library/services/ipxe_log_parser.py`

```python
import re
from datetime import datetime
from typing import List, Dict

class IPXELogParser:
    """iPXE 日誌解析器"""
    
    # 日誌格式範例：
    # 2025-11-01 08:30:15 [INFO] Boot request from MAC: AA:BB:CC:DD:EE:FF, IP: 192.168.1.100
    LOG_PATTERN = re.compile(
        r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) \[(\w+)\] Boot request from MAC: ([0-9A-Fa-f:]+), IP: ([\d.]+)'
    )
    
    def parse_log_file(self, log_content: str) -> List[Dict]:
        """
        解析日誌內容
        
        Args:
            log_content: 日誌文件內容
            
        Returns:
            List[dict]: 解析後的記錄
        """
        records = []
        
        for line in log_content.split('\n'):
            match = self.LOG_PATTERN.match(line)
            if match:
                timestamp, level, mac, ip = match.groups()
                
                records.append({
                    'timestamp': datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S'),
                    'level': level,
                    'mac_address': mac,
                    'ip_address': ip,
                })
        
        return records
```

---

## 測試與驗證

### 1. 手動測試任務

```bash
# 進入 Django Shell
docker exec -it nt-django python manage.py shell

# 手動執行任務
from api.tasks import collect_ipxe_boot_records_task
result = collect_ipxe_boot_records_task.apply(kwargs={'server_id': 1})
print(result.get())
```

### 2. 查看任務執行記錄

```bash
# 查看 Celery Worker 日誌
docker logs nt-celery-worker --tail 100 -f

# 查看 Celery Beat 排程日誌
docker logs nt-celery-beat --tail 50 -f

# 查看 Django 應用日誌
tail -f logs/django.log
```

### 3. 使用 Flower 監控

訪問：`http://localhost:5555`

- **Tasks**：查看所有已註冊的任務
- **Workers**：查看 Worker 狀態
- **Tasks (Runtime)**：查看正在執行的任務
- **Tasks (History)**：查看歷史執行記錄

### 4. 驗證資料庫記錄

```bash
docker exec -it nt-django python manage.py shell

# 查詢最新記錄
from api.models import IPXEBootRecord
records = IPXEBootRecord.objects.order_by('-boot_time')[:10]
for r in records:
    print(f"{r.boot_time} | {r.mac_address} | {r.boot_status}")
```

### 5. 檢查排程是否生效

```python
# Django Shell
from django_celery_beat.models import PeriodicTask
tasks = PeriodicTask.objects.filter(enabled=True)
for task in tasks:
    print(f"{task.name}: {task.crontab}")
```

---

## 常見問題

### Q1: 任務沒有執行？

**檢查清單**：
```bash
# 1. 確認 Celery Beat 正在運行
docker compose ps | grep celery_beat

# 2. 確認任務已加載
docker logs nt-celery-beat | grep "collect-ipxe-boot-records"

# 3. 確認 Worker 正在運行
docker compose ps | grep celery_worker

# 4. 檢查排程配置是否正確
docker exec nt-django python manage.py shell -c "from network_toolbox.celery import app; print(app.conf.beat_schedule.keys())"
```

### Q2: 任務失敗一直重試？

**解決方案**：
```python
# 在任務裝飾器中設定最大重試次數
@shared_task(
    bind=True,
    max_retries=3,           # 最多重試 3 次
    default_retry_delay=60,  # 每次重試間隔 60 秒
    autoretry_for=(Exception,),  # 遇到任何異常都重試
)
def my_task(self):
    pass
```

### Q3: 如何暫時停用某個任務？

**方法 1：修改 celery.py**
```python
# 註釋掉不需要的任務
# 'collect-ipxe-boot-records-every-15-minutes': {
#     'task': 'api.tasks.collect_ipxe_boot_records_task',
#     ...
# },
```

**方法 2：使用 Django Admin**
```bash
# 訪問 http://localhost/admin/django_celery_beat/periodictask/
# 找到對應任務，取消勾選 "Enabled"
```

### Q4: 如何設定任務執行時間限制？

```python
@shared_task(
    time_limit=300,        # 硬限制 5 分鐘（強制終止）
    soft_time_limit=270,   # 軟限制 4.5 分鐘（拋出異常）
)
def my_task():
    pass
```

### Q5: 如何讓任務在特定時間執行？

```python
from celery.schedules import crontab

# 每天早上 8 點
'schedule': crontab(hour=8, minute=0)

# 每週一、三、五早上 9 點
'schedule': crontab(hour=9, minute=0, day_of_week='1,3,5')

# 每月 1 號和 15 號
'schedule': crontab(hour=0, minute=0, day_of_month='1,15')
```

### Q6: 如何監控任務執行時間？

```bash
# 使用 Flower 查看（推薦）
http://localhost:5555

# 或查看資料庫
docker exec -it nt-django python manage.py shell

from django_celery_results.models import TaskResult
results = TaskResult.objects.order_by('-date_done')[:10]
for r in results:
    duration = (r.date_done - r.date_created).total_seconds()
    print(f"{r.task_name}: {duration:.2f}s")
```

---

## 完整範例：iPXE 裝置清單同步

### 模型定義

```python
# backend/api/models.py
class IPXEDevice(models.Model):
    """iPXE 註冊裝置"""
    server = models.ForeignKey('IPXEServer', on_delete=models.CASCADE)
    mac_address = models.CharField(max_length=17, unique=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    hostname = models.CharField(max_length=255, null=True, blank=True)
    device_type = models.CharField(max_length=50, null=True, blank=True)
    last_boot = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'ipxe_devices'
        ordering = ['-last_boot']
```

### 服務實現

```python
# backend/library/services/ipxe_device_sync_service.py
import requests
import logging
from typing import Dict, List
from datetime import datetime

logger = logging.getLogger(__name__)

class IPXEDeviceSyncService:
    """iPXE 裝置同步服務"""
    
    def __init__(self, server_id: int):
        self.server_id = server_id
    
    def sync_devices(self) -> Dict:
        """同步裝置清單"""
        try:
            from api.models import IPXEServer, IPXEDevice
            
            server = IPXEServer.objects.get(id=self.server_id)
            
            # 從 API 獲取裝置清單
            response = requests.get(
                f"http://{server.ip_address}/api/devices",
                timeout=30,
                headers={'Authorization': f'Bearer {server.api_token}'}
            )
            response.raise_for_status()
            devices = response.json()
            
            # 更新資料庫
            updated = 0
            created = 0
            
            for device_data in devices:
                device, was_created = IPXEDevice.objects.update_or_create(
                    mac_address=device_data['mac'],
                    defaults={
                        'server': server,
                        'ip_address': device_data.get('ip'),
                        'hostname': device_data.get('hostname'),
                        'device_type': device_data.get('type'),
                        'last_boot': device_data.get('last_boot'),
                    }
                )
                
                if was_created:
                    created += 1
                else:
                    updated += 1
            
            logger.info(
                f'iPXE 裝置同步完成 - '
                f'Server: {server.name} | '
                f'總計: {len(devices)} | '
                f'新增: {created} | '
                f'更新: {updated}'
            )
            
            return {
                'success': True,
                'total': len(devices),
                'created': created,
                'updated': updated,
            }
            
        except Exception as e:
            logger.error(f'同步裝置清單失敗: {e}', exc_info=True)
            return {'success': False, 'error': str(e)}
```

### 任務定義

```python
# backend/api/tasks.py
@shared_task(
    bind=True,
    name='api.tasks.sync_ipxe_devices_task',
    max_retries=2,
    default_retry_delay=120,
    time_limit=300,
    soft_time_limit=270
)
def sync_ipxe_devices_task(self, server_id):
    """同步 iPXE 裝置清單"""
    try:
        from library.services.ipxe_device_sync_service import IPXEDeviceSyncService
        
        service = IPXEDeviceSyncService(server_id)
        result = service.sync_devices()
        
        return result
        
    except Exception as exc:
        raise self.retry(exc=exc)
```

### 排程配置

```python
# backend/network_toolbox/celery.py
'sync-ipxe-devices-hourly': {
    'task': 'api.tasks.sync_ipxe_devices_task',
    'schedule': crontab(minute=0),  # 每小時同步一次
    'kwargs': {'server_id': 1},
}
```

---

## 最佳實踐

### 1. 錯誤處理

```python
@shared_task(bind=True)
def my_task(self):
    try:
        # 主要邏輯
        pass
    except SpecificException as e:
        # 特定異常不重試
        logger.error(f'任務失敗: {e}')
        return {'success': False, 'error': str(e)}
    except Exception as exc:
        # 其他異常重試
        raise self.retry(exc=exc, countdown=60, max_retries=3)
```

### 2. 日誌記錄

```python
import logging
logger = logging.getLogger(__name__)

@shared_task
def my_task():
    logger.info('[Celery] 任務開始')
    try:
        # 邏輯
        logger.info('[Celery] 任務完成')
    except Exception as e:
        logger.error('[Celery] 任務失敗', exc_info=True)
```

### 3. 進度追蹤（長時間任務）

```python
@shared_task(bind=True)
def long_running_task(self):
    total = 100
    for i in range(total):
        # 更新進度
        self.update_state(
            state='PROGRESS',
            meta={'current': i, 'total': total}
        )
        # 執行工作
        time.sleep(1)
```

### 4. 任務鏈（Task Chain）

```python
from celery import chain

# 依序執行多個任務
result = chain(
    task1.s(),
    task2.s(),
    task3.s()
).apply_async()
```

### 5. 避免資料庫連接洩漏

```python
from django.db import connection

@shared_task
def my_task():
    try:
        # 資料庫操作
        pass
    finally:
        connection.close()  # 確保關閉連接
```

---

## 總結

✅ **完整流程回顧**：

1. 定義資料模型（`models.py`）
2. 創建資料抓取服務（`library/services/`）
3. 創建 Celery 任務（`api/tasks.py`）
4. 配置定時排程（`network_toolbox/celery.py`）
5. 重啟 Celery 服務
6. 測試與驗證

📚 **相關文檔**：

- [Celery 實現指南](./CELERY_IMPLEMENTATION_GUIDE.md)
- [Cron 設定指南](./CRON_SETUP_GUIDE.md)
- [日誌同步指南](./LOGS_SYNC_GUIDE.md)

🎯 **下一步**：

- 訪問 Flower 監控：`http://localhost:5555`
- 查看 Django Admin：`http://localhost/admin/django_celery_beat/`
- 檢查執行日誌：`docker logs nt-celery-worker -f`

---

**最後更新**：2025-11-01  
**作者**：Network Toolbox Team
