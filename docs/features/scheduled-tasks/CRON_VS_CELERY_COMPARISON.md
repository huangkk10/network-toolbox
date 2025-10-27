# 📅 定時任務方案比較：主機 Cron vs 容器 Celery Beat

## 🎯 目標
為 Network Toolbox 的 DHCP 日誌自動同步選擇最佳的定時任務方案。

---

## 📊 兩種方案對比

### 方案 A：主機 Cron（當前建議方案）

```
┌─────────────────────────────────────────┐
│  Ubuntu 主機 (您的系統)                   │
│  ┌─────────────────────────────────┐   │
│  │  Cron 服務 (系統級)              │   │
│  │  - 每 5 分鐘執行                  │   │
│  │  - 透過 docker exec 調用容器命令  │   │
│  └─────────────────────────────────┘   │
│         ↓ docker exec                  │
│  ┌─────────────────────────────────┐   │
│  │  nt-django 容器                  │   │
│  │  - 執行 Django 管理命令           │   │
│  │  - 同步日誌到資料庫               │   │
│  └─────────────────────────────────┘   │
└─────────────────────────────────────────┘
```

**設定方式**：
```bash
# 1. 編輯 crontab
crontab -e

# 2. 添加任務
*/5 * * * * docker exec nt-django python manage.py sync_dhcp_logs --server 1 --limit 500 >> /home/owner/Codes/network-toolbox/logs/cron_sync.log 2>&1
0 3 * * * docker exec nt-django python manage.py clean_old_logs --days 7 >> /home/owner/Codes/network-toolbox/logs/cron_cleanup.log 2>&1
```

**✅ 優點**：
- ⚡ **極簡實現**：只需 2 行 crontab 配置
- 🎯 **零依賴**：不需要額外服務（Redis、Celery）
- 💪 **穩定可靠**：Cron 是 Linux 系統級服務，久經考驗
- 🔧 **易於管理**：`crontab -e` 即可編輯，`crontab -l` 查看
- 📊 **日誌清晰**：直接輸出到主機檔案，方便查看
- 💾 **資源節省**：不需要額外容器和記憶體
- 🚀 **即時生效**：修改後立即生效，無需重啟容器

**❌ 缺點**：
- 🔄 **容器重啟影響**：如果容器名稱變更需要更新 crontab
- 📱 **無 GUI 監控**：需要查看日誌檔案，沒有 Web 界面
- 🌐 **單機限制**：無法在多主機間分佈任務（本專案不需要）

---

### 方案 B：容器 Celery Beat（ai-platform-web 方案）

```
┌─────────────────────────────────────────────────────────┐
│  Docker Compose 環境                                     │
│                                                          │
│  ┌──────────────────────┐    ┌──────────────────────┐  │
│  │ nt-celery-beat       │    │ nt-redis             │  │
│  │ - 定時任務排程器      │◄──►│ - 消息佇列           │  │
│  │ - 解析 crontab       │    │ - 任務結果存儲       │  │
│  └──────────────────────┘    └──────────────────────┘  │
│            ↓ 推送任務到 Redis                ↓ 取出任務  │
│  ┌──────────────────────┐    ┌──────────────────────┐  │
│  │ nt-celery-worker     │◄──►│ nt-django            │  │
│  │ - 執行定時任務        │    │ - 主應用服務         │  │
│  │ - 調用 library 函數   │    │ - 提供 API           │  │
│  └──────────────────────┘    └──────────────────────┘  │
│            ↓ 存儲結果                                     │
│  ┌──────────────────────┐                              │
│  │ PostgreSQL           │                              │
│  │ - 日誌資料           │                              │
│  └──────────────────────┘                              │
└─────────────────────────────────────────────────────────┘
```

**設定方式**：

#### 1. 安裝依賴
```bash
# requirements.txt
celery==5.3.4
redis==5.0.1
django-celery-beat==2.5.0
django-celery-results==2.5.1
```

#### 2. 配置 Celery (`backend/network_toolbox/celery.py`)
```python
import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'network_toolbox.settings')

app = Celery('network_toolbox')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

# 定時任務配置
app.conf.beat_schedule = {
    'sync-dhcp-logs-every-5-minutes': {
        'task': 'api.tasks.sync_dhcp_logs_task',
        'schedule': crontab(minute='*/5'),
        'kwargs': {'server_id': 1, 'limit': 500}
    },
    'cleanup-old-logs-daily': {
        'task': 'api.tasks.cleanup_old_logs_task',
        'schedule': crontab(hour=3, minute=0),
        'kwargs': {'days': 7}
    }
}
```

#### 3. 創建 Celery 任務 (`backend/api/tasks.py`)
```python
from celery import shared_task
from .services import DHCPLogService

@shared_task
def sync_dhcp_logs_task(server_id, limit=500):
    """同步 DHCP 日誌任務"""
    from .models import DHCPServer
    server = DHCPServer.objects.get(id=server_id)
    service = DHCPLogService(server)
    result = service.sync_logs_to_db(limit=limit)
    return result

@shared_task
def cleanup_old_logs_task(days=7):
    """清理舊日誌任務"""
    # 實現清理邏輯
    pass
```

#### 4. Django Settings 配置
```python
# settings.py
INSTALLED_APPS = [
    # ...
    'django_celery_beat',
    'django_celery_results',
]

# Redis 配置
REDIS_HOST = 'redis'
REDIS_PORT = 6379

# Celery 配置
CELERY_BROKER_URL = f'redis://{REDIS_HOST}:{REDIS_PORT}/1'
CELERY_RESULT_BACKEND = f'redis://{REDIS_HOST}:{REDIS_PORT}/2'
CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'
CELERY_TIMEZONE = 'Asia/Taipei'
```

#### 5. Docker Compose 配置
```yaml
# docker-compose.yml
services:
  redis:
    image: redis:7-alpine
    container_name: nt-redis
    restart: unless-stopped
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data
    networks:
      - nt_network

  celery_beat:
    build: ./backend
    container_name: nt-celery-beat
    command: celery -A network_toolbox beat --loglevel=info --scheduler django_celery_beat.schedulers:DatabaseScheduler
    volumes:
      - ./backend:/app
      - ./logs:/app/logs
    depends_on:
      - redis
      - postgres
      - django
    networks:
      - nt_network
    environment:
      - DB_HOST=host.docker.internal
      - REDIS_HOST=redis

  celery_worker:
    build: ./backend
    container_name: nt-celery-worker
    command: celery -A network_toolbox worker --loglevel=info --concurrency=2
    volumes:
      - ./backend:/app
      - ./logs:/app/logs
    depends_on:
      - redis
      - postgres
      - django
    networks:
      - nt_network
    environment:
      - DB_HOST=host.docker.internal
      - REDIS_HOST=redis

  celery_flower:  # 可選：Web 監控界面
    build: ./backend
    container_name: nt-celery-flower
    command: celery -A network_toolbox flower --port=5555
    ports:
      - "5555:5555"
    depends_on:
      - redis
      - celery_worker
    networks:
      - nt_network

volumes:
  redis_data:
```

#### 6. 初始化資料庫表
```bash
docker exec nt-django python manage.py migrate django_celery_beat
docker exec nt-django python manage.py migrate django_celery_results
```

**✅ 優點**：
- 🎨 **Web 監控**：Flower 提供美觀的任務監控界面（http://localhost:5555）
- 📊 **任務追蹤**：每次執行結果都存入資料庫，可查詢歷史
- 🔄 **動態調整**：可透過 Django Admin 修改排程，無需重啟
- 🚀 **高級功能**：支援任務鏈、任務組、分佈式執行
- 🔧 **專業架構**：適合複雜的定時任務需求
- 📱 **API 控制**：可透過 API 動態觸發、暫停、恢復任務

**❌ 缺點**：
- 🔧 **複雜度高**：需要配置 5 個額外檔案
- 📦 **依賴增加**：需要 Redis + 4 個 Python 套件
- 💾 **資源消耗**：額外 3 個容器（Beat, Worker, Redis）
- 🐌 **啟動時間**：容器啟動需要 5-10 秒
- 📚 **學習曲線**：需要理解 Celery 架構和概念
- 🔨 **維護成本**：更多服務需要監控和管理

---

## 🎯 專案需求分析

### Network Toolbox 定時任務需求

| 需求 | 方案 A (Cron) | 方案 B (Celery) |
|------|---------------|-----------------|
| **任務數量** | 2 個（同步、清理） | ✅ 適合 | ⚠️ 過度設計 |
| **複雜度** | 簡單、獨立任務 | ✅ 完美 | ⚠️ 不需要 |
| **任務依賴** | 無依賴關係 | ✅ 不需要 | ⚠️ 用不到 |
| **動態調整** | 不需要頻繁修改 | ✅ 足夠 | ⚠️ 過度 |
| **監控需求** | 日誌檔案即可 | ✅ 足夠 | ❌ 不必要 |
| **資源限制** | 低資源消耗優先 | ✅ **最佳** | ❌ 浪費 |
| **維護人力** | 小團隊/個人 | ✅ **最佳** | ❌ 複雜 |
| **學習成本** | 無需學習 | ✅ **最低** | ❌ 高 |

---

## 💡 建議選擇

### 🏆 **強烈建議：方案 A（主機 Cron）**

#### 理由：

1. **符合 KISS 原則**（Keep It Simple, Stupid）
   - 2 行 crontab 配置 vs 5+ 檔案修改
   - 0 個額外服務 vs 3 個額外容器

2. **資源效率**
   ```
   方案 A 資源消耗:
   - 記憶體: 0 MB（使用系統 Cron）
   - 容器數量: 4 個（現有）
   
   方案 B 資源消耗:
   - 記憶體: +200 MB（Redis + 2 個 Celery 容器）
   - 容器數量: 7 個（+3 個新容器）
   ```

3. **維護成本**
   - **方案 A**：修改排程 = `crontab -e`（30 秒）
   - **方案 B**：修改排程 = 編輯 celery.py → 重啟 3 個容器（5 分鐘）

4. **專案規模匹配**
   - Network Toolbox 是**中小型專案**
   - **2 個簡單定時任務**不需要 Celery 的複雜架構
   - **沒有分佈式需求**（單機運行）

5. **ai-platform-web 使用 Celery 的原因不適用**
   ```
   ai-platform-web 為什麼用 Celery:
   ✅ 複雜向量處理任務（每小時執行，計算密集）
   ✅ 多種任務類型（向量化、聚類、快取清理）
   ✅ 需要 Web 監控（團隊協作）
   ✅ 大型專案（多個 Library 模組）
   
   Network Toolbox 的需求:
   ❌ 簡單同步任務（讀取日誌 + 寫入資料庫）
   ❌ 只有 2 個任務
   ❌ 個人/小團隊使用（不需要 GUI）
   ❌ 中小型專案
   ```

---

## 📝 實施建議

### 採用方案 A（主機 Cron）的完整步驟

#### 步驟 1：設置 Cron 任務

```bash
# 1. 編輯 crontab
crontab -e

# 2. 添加以下兩行
*/5 * * * * docker exec nt-django python manage.py sync_dhcp_logs --server 1 --limit 500 >> /home/owner/Codes/network-toolbox/logs/cron_sync.log 2>&1
0 3 * * * docker exec nt-django python manage.py clean_old_logs --days 7 >> /home/owner/Codes/network-toolbox/logs/cron_cleanup.log 2>&1

# 3. 保存退出（Ctrl+O, Enter, Ctrl+X）

# 4. 驗證
crontab -l
```

#### 步驟 2：驗證任務執行

```bash
# 5 分鐘後查看同步日誌
tail -f logs/cron_sync.log

# 應該會看到：
# 同步伺服器: Windows DHCP Server (10.250.50.1)
#   - 讀取: 500 筆 | 新增: 15 筆 | 跳過: 485 筆 | 錯誤: 0 筆
```

#### 步驟 3：監控與維護

```bash
# 每日檢查資料庫增長
docker exec nt-django python manage.py shell -c "
from api.models import DHCPLog
from django.db.models.functions import TruncDate
from django.db.models import Count
logs = DHCPLog.objects.annotate(date=TruncDate('timestamp')).values('date').annotate(count=Count('id')).order_by('date')
for item in logs:
    print(f'{item[\"date\"]}: {item[\"count\"]} 筆')
"

# 查看系統 Cron 日誌（如果有問題）
grep CRON /var/log/syslog | tail -20
```

---

## 🔄 什麼時候應該升級到 Celery？

如果未來 Network Toolbox 出現以下需求，再考慮遷移到 Celery：

1. **任務數量 > 10 個**
2. **需要任務依賴關係**（例如：先同步再分析再產生報告）
3. **需要分佈式執行**（多台主機運行）
4. **需要 Web 監控界面**（團隊協作）
5. **需要動態調整排程**（不重啟系統）
6. **計算密集型任務**（需要佇列管理避免阻塞）

**目前 Network Toolbox 都不符合以上條件**，所以 Cron 是最佳選擇。

---

## 📚 參考文檔

- **Cron 設置指南**：`CRON_SETUP_GUIDE.md`
- **ai-platform-web Celery 架構**：
  - https://github.com/huangkk10/ai-platform-web/tree/main/docs/architecture/celery-beat-architecture-guide.md
- **Celery 官方文檔**：https://docs.celeryq.dev/

---

## ✅ 總結

| 項目 | 方案 A (Cron) | 方案 B (Celery) |
|------|---------------|-----------------|
| **實施時間** | 5 分鐘 | 2-3 小時 |
| **配置檔案** | 0 個（crontab） | 5+ 個 |
| **額外服務** | 0 個 | 3 個（Redis, Beat, Worker） |
| **記憶體消耗** | 0 MB | +200 MB |
| **學習成本** | 極低 | 高 |
| **維護成本** | 極低 | 中等 |
| **適合規模** | ✅ 中小型專案 | ❌ 大型專案 |
| **推薦度** | ⭐⭐⭐⭐⭐ | ⭐⭐ |

### 🎯 最終建議

**當前階段：使用方案 A（主機 Cron）**

優勢：
- ✅ 5 分鐘完成設置
- ✅ 零額外資源消耗
- ✅ 極低維護成本
- ✅ 完全滿足需求

**未來擴展：根據需求決定**

如果專案發展到需要複雜定時任務管理時，再考慮遷移到 Celery。

---

**最後更新**：2025-10-28  
**作者**：Network Toolbox Team  
**版本**：1.0

