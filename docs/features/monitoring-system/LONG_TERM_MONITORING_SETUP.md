# Network Toolbox 長期監控系統實施方案

**創建日期**：2025-11-25  
**目的**：建立完整的任務監控、告警和數據分析系統  
**適用階段**：長期優化（中期優化完成後）

---

## 📊 方案概述

### 核心目標

1. **可視化監控**：實時查看 17 個定時任務的執行狀態
2. **主動告警**：CPU、記憶體、任務失敗自動通知
3. **性能分析**：長期趨勢分析，預測性維護
4. **問題追蹤**：快速定位問題根源

### 技術棧選擇

| 組件 | 用途 | 優勢 | 部署方式 |
|------|------|------|---------|
| **Celery Flower** | Celery 任務監控 | 專為 Celery 設計，即插即用 | Docker 容器 |
| **Prometheus** | 指標收集 | 時間序列數據庫，強大的查詢能力 | Docker 容器 |
| **Grafana** | 數據視覺化 | 豐富的圖表，自訂儀表板 | Docker 容器 |
| **AlertManager** | 告警管理 | 靈活的告警規則，多種通知方式 | Docker 容器 |

---

## 🔧 階段一：Celery Flower 監控（最簡單，1 小時）

### 1.1 什麼是 Flower？

Flower 是 Celery 的官方監控工具，提供：
- ✅ 即時查看任務執行狀態（成功/失敗/執行中）
- ✅ 任務執行時間統計
- ✅ Worker 狀態監控
- ✅ 任務重試和撤銷功能
- ✅ Web UI（易於使用）

### 1.2 Docker Compose 配置

**文件**：`docker-compose.yml`

```yaml
services:
  # ... 現有服務 ...

  # Flower 監控服務
  flower:
    image: mher/flower:latest
    container_name: nt-flower
    command: celery --broker=redis://redis:6379/0 flower --port=5555
    ports:
      - "5555:5555"
    networks:
      - nt_network
    depends_on:
      - redis
      - django
    environment:
      - CELERY_BROKER_URL=redis://redis:6379/0
      - CELERY_RESULT_BACKEND=redis://redis:6379/0
      - FLOWER_BASIC_AUTH=admin:your_secure_password  # 設定登入帳號密碼
    restart: unless-stopped

  # Redis（如果尚未配置）
  redis:
    image: redis:7-alpine
    container_name: nt-redis
    ports:
      - "6379:6379"
    networks:
      - nt_network
    volumes:
      - redis_data:/data
    restart: unless-stopped

volumes:
  redis_data:
```

### 1.3 Celery 配置調整

**文件**：`backend/network_toolbox/celery.py`

```python
from celery import Celery
import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'network_toolbox.settings')

app = Celery('network_toolbox')

# 使用 Redis 作為 Broker 和 Result Backend（Flower 需要）
app.config_from_object('django.conf:settings', namespace='CELERY')

# 🆕 啟用任務事件（Flower 需要）
app.conf.worker_send_task_events = True
app.conf.task_send_sent_event = True

# 🆕 設定 Result Backend 過期時間
app.conf.result_expires = 3600  # 1 小時

app.autodiscover_tasks()
```

**文件**：`backend/network_toolbox/settings.py`

```python
# Celery 配置
CELERY_BROKER_URL = 'redis://redis:6379/0'  # 改用 Redis
CELERY_RESULT_BACKEND = 'redis://redis:6379/0'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'Asia/Taipei'

# 🆕 啟用任務事件
CELERY_WORKER_SEND_TASK_EVENTS = True
CELERY_TASK_SEND_SENT_EVENT = True
```

### 1.4 啟動 Flower

```bash
# 1. 更新 Docker Compose
docker compose up -d flower redis

# 2. 重啟 Django（應用 Celery 配置）
docker compose restart django

# 3. 訪問 Flower
# http://localhost:5555
# 帳號：admin
# 密碼：your_secure_password
```

### 1.5 Flower 使用指南

**主要功能**：

1. **Dashboard（儀表板）**
   - 查看當前活躍任務數量
   - Worker 狀態（在線/離線）
   - 任務成功率

2. **Tasks（任務列表）**
   - 查看所有已執行的任務
   - 過濾：成功/失敗/執行中
   - 查看任務參數和結果

3. **Workers（工作器）**
   - 查看每個 Worker 的負載
   - CPU 和記憶體使用率
   - 活躍任務數量

4. **Monitor（即時監控）**
   - 任務執行即時圖表
   - 任務執行時間分佈

**關鍵指標監控**：

| 指標 | 正常範圍 | 警告閾值 | 行動建議 |
|------|---------|---------|---------|
| **任務失敗率** | < 5% | > 10% | 檢查日誌，修復問題 |
| **任務執行時間** | < 5 分鐘 | > 10 分鐘 | 優化任務邏輯 |
| **Worker CPU** | < 50% | > 80% | 增加 Worker 或優化任務 |
| **隊列積壓** | < 10 個 | > 50 個 | 增加 Worker 並發數 |

---

## 📈 階段二：Prometheus + Grafana 監控（進階，2-3 小時）

### 2.1 為什麼需要 Prometheus + Grafana？

Flower 提供了即時監控，但缺少：
- ❌ 歷史數據分析（只保留短期數據）
- ❌ 自訂告警規則
- ❌ 多維度數據關聯（CPU + 任務執行時間）
- ❌ 美觀的儀表板

**Prometheus + Grafana 可以：**
- ✅ 長期存儲監控數據（數週/數月）
- ✅ 強大的查詢語言（PromQL）
- ✅ 自訂告警規則（CPU > 80% 持續 5 分鐘）
- ✅ 關聯分析（任務執行時間 vs CPU 使用率）
- ✅ 多種視覺化圖表（折線圖、熱圖、儀表盤）

### 2.2 Docker Compose 配置

**文件**：`docker-compose.yml`

```yaml
services:
  # ... 現有服務 ...

  # Prometheus 指標收集
  prometheus:
    image: prom/prometheus:latest
    container_name: nt-prometheus
    ports:
      - "9090:9090"
    networks:
      - nt_network
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--storage.tsdb.retention.time=30d'  # 保留 30 天數據
    restart: unless-stopped

  # Grafana 視覺化
  grafana:
    image: grafana/grafana:latest
    container_name: nt-grafana
    ports:
      - "3001:3000"  # 避免與 React 的 3000 衝突
    networks:
      - nt_network
    volumes:
      - grafana_data:/var/lib/grafana
      - ./monitoring/grafana/dashboards:/etc/grafana/provisioning/dashboards
      - ./monitoring/grafana/datasources:/etc/grafana/provisioning/datasources
    environment:
      - GF_SECURITY_ADMIN_USER=admin
      - GF_SECURITY_ADMIN_PASSWORD=your_grafana_password
      - GF_USERS_ALLOW_SIGN_UP=false
    restart: unless-stopped
    depends_on:
      - prometheus

  # Redis Exporter（導出 Redis 指標）
  redis-exporter:
    image: oliver006/redis_exporter:latest
    container_name: nt-redis-exporter
    ports:
      - "9121:9121"
    networks:
      - nt_network
    environment:
      - REDIS_ADDR=redis:6379
    restart: unless-stopped
    depends_on:
      - redis

  # PostgreSQL Exporter（導出資料庫指標）
  postgres-exporter:
    image: prometheuscommunity/postgres-exporter:latest
    container_name: nt-postgres-exporter
    ports:
      - "9187:9187"
    networks:
      - nt_network
    environment:
      - DATA_SOURCE_NAME=postgresql://your_user:your_password@host.docker.internal:5432/network_toolbox?sslmode=disable
    restart: unless-stopped

volumes:
  prometheus_data:
  grafana_data:
```

### 2.3 Prometheus 配置

**創建文件**：`monitoring/prometheus.yml`

```yaml
global:
  scrape_interval: 15s  # 每 15 秒收集一次指標
  evaluation_interval: 15s

# 告警規則
rule_files:
  - '/etc/prometheus/alerts/*.yml'

# 抓取目標
scrape_configs:
  # 1. Prometheus 自身
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']

  # 2. Django 應用（需要安裝 django-prometheus）
  - job_name: 'django'
    static_configs:
      - targets: ['django:8000']
    metrics_path: '/metrics'

  # 3. Redis
  - job_name: 'redis'
    static_configs:
      - targets: ['redis-exporter:9121']

  # 4. PostgreSQL
  - job_name: 'postgresql'
    static_configs:
      - targets: ['postgres-exporter:9187']

  # 5. Node Exporter（系統指標 - 可選）
  - job_name: 'node'
    static_configs:
      - targets: ['host.docker.internal:9100']  # 需要在主機上安裝 node_exporter
```

### 2.4 Django 集成 Prometheus

**安裝依賴**：

```bash
# backend/requirements.txt
django-prometheus==2.3.1
```

```bash
docker exec nt-django pip install django-prometheus
```

**配置 Django**：

**文件**：`backend/network_toolbox/settings.py`

```python
INSTALLED_APPS = [
    'django_prometheus',  # 🆕 添加到最前面
    'django.contrib.admin',
    # ... 其他 apps ...
]

MIDDLEWARE = [
    'django_prometheus.middleware.PrometheusBeforeMiddleware',  # 🆕 最前面
    'django.middleware.security.SecurityMiddleware',
    # ... 其他 middleware ...
    'django_prometheus.middleware.PrometheusAfterMiddleware',  # 🆕 最後面
]
```

**文件**：`backend/network_toolbox/urls.py`

```python
from django.urls import path, include

urlpatterns = [
    # ... 現有路由 ...
    path('metrics/', include('django_prometheus.urls')),  # 🆕 Prometheus 指標端點
]
```

### 2.5 自訂 Celery 指標

**創建文件**：`backend/library/utils/celery_metrics.py`

```python
"""
Celery 任務自訂指標

為 Prometheus 導出 Celery 任務的執行時間、成功率等指標
"""

from prometheus_client import Counter, Histogram, Gauge
import logging

logger = logging.getLogger(__name__)

# 任務執行計數器
celery_task_total = Counter(
    'celery_task_total',
    'Total number of Celery tasks executed',
    ['task_name', 'status']  # 標籤：任務名稱、狀態（success/failure）
)

# 任務執行時間直方圖
celery_task_duration_seconds = Histogram(
    'celery_task_duration_seconds',
    'Celery task execution time in seconds',
    ['task_name'],
    buckets=(0.1, 0.5, 1.0, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0, 600.0)
)

# 當前執行中的任務數量
celery_task_running = Gauge(
    'celery_task_running',
    'Number of currently running Celery tasks',
    ['task_name']
)

# CPU 使用率（如果使用了智能監控）
system_cpu_percent = Gauge(
    'system_cpu_percent',
    'System CPU usage percentage'
)

def record_task_success(task_name: str, duration: float):
    """記錄任務成功"""
    celery_task_total.labels(task_name=task_name, status='success').inc()
    celery_task_duration_seconds.labels(task_name=task_name).observe(duration)
    logger.debug(f'[Metrics] Task {task_name} succeeded in {duration:.2f}s')

def record_task_failure(task_name: str, duration: float = None):
    """記錄任務失敗"""
    celery_task_total.labels(task_name=task_name, status='failure').inc()
    if duration:
        celery_task_duration_seconds.labels(task_name=task_name).observe(duration)
    logger.warning(f'[Metrics] Task {task_name} failed')

def record_task_start(task_name: str):
    """記錄任務開始"""
    celery_task_running.labels(task_name=task_name).inc()

def record_task_end(task_name: str):
    """記錄任務結束"""
    celery_task_running.labels(task_name=task_name).dec()

def update_cpu_metric(cpu_percent: float):
    """更新 CPU 指標"""
    system_cpu_percent.set(cpu_percent)
```

**在任務中使用指標**：

```python
# backend/api/tasks.py

from library.utils.celery_metrics import (
    record_task_success,
    record_task_failure,
    record_task_start,
    record_task_end
)
import time

@shared_task(bind=True, name='api.tasks.sync_jenkins_builds')
def sync_jenkins_builds(self, ...):
    task_name = 'sync_jenkins_builds'
    start_time = time.time()
    
    record_task_start(task_name)  # 🆕 記錄開始
    
    try:
        # ... 任務邏輯 ...
        
        duration = time.time() - start_time
        record_task_success(task_name, duration)  # 🆕 記錄成功
        return {...}
    
    except Exception as e:
        duration = time.time() - start_time
        record_task_failure(task_name, duration)  # 🆕 記錄失敗
        raise e
    
    finally:
        record_task_end(task_name)  # 🆕 記錄結束
```

### 2.6 Grafana 儀表板配置

**創建文件**：`monitoring/grafana/datasources/prometheus.yml`

```yaml
apiVersion: 1

datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
    editable: false
```

**創建文件**：`monitoring/grafana/dashboards/dashboard.yml`

```yaml
apiVersion: 1

providers:
  - name: 'Network Toolbox Dashboards'
    orgId: 1
    folder: ''
    type: file
    disableDeletion: false
    editable: true
    options:
      path: /etc/grafana/provisioning/dashboards
```

**創建儀表板**：`monitoring/grafana/dashboards/celery-tasks.json`

（這是一個 Grafana 儀表板 JSON 配置，建議從 Grafana UI 創建後導出）

**手動創建步驟**：

1. 訪問 Grafana：http://localhost:3001
2. 登入（admin / your_grafana_password）
3. 創建新 Dashboard
4. 添加 Panel，使用以下 PromQL 查詢：

**面板 1：任務執行次數（成功 vs 失敗）**
```promql
sum(rate(celery_task_total[5m])) by (status)
```

**面板 2：任務執行時間（P50, P95, P99）**
```promql
histogram_quantile(0.50, sum(rate(celery_task_duration_seconds_bucket[5m])) by (le, task_name))
histogram_quantile(0.95, sum(rate(celery_task_duration_seconds_bucket[5m])) by (le, task_name))
histogram_quantile(0.99, sum(rate(celery_task_duration_seconds_bucket[5m])) by (le, task_name))
```

**面板 3：當前執行中的任務數量**
```promql
sum(celery_task_running) by (task_name)
```

**面板 4：CPU 使用率**
```promql
system_cpu_percent
```

**面板 5：Redis 記憶體使用**
```promql
redis_memory_used_bytes / redis_memory_max_bytes * 100
```

**面板 6：PostgreSQL 連接數**
```promql
pg_stat_database_numbackends
```

---

## 🚨 階段三：告警系統（AlertManager，1-2 小時）

### 3.1 AlertManager 配置

**文件**：`docker-compose.yml`

```yaml
services:
  # ... 現有服務 ...

  # AlertManager 告警管理
  alertmanager:
    image: prom/alertmanager:latest
    container_name: nt-alertmanager
    ports:
      - "9093:9093"
    networks:
      - nt_network
    volumes:
      - ./monitoring/alertmanager.yml:/etc/alertmanager/alertmanager.yml
      - alertmanager_data:/alertmanager
    command:
      - '--config.file=/etc/alertmanager/alertmanager.yml'
      - '--storage.path=/alertmanager'
    restart: unless-stopped

volumes:
  alertmanager_data:
```

**創建文件**：`monitoring/alertmanager.yml`

```yaml
global:
  resolve_timeout: 5m
  
  # SMTP 配置（郵件通知）
  smtp_smarthost: 'smtp.gmail.com:587'
  smtp_from: 'your-email@gmail.com'
  smtp_auth_username: 'your-email@gmail.com'
  smtp_auth_password: 'your-app-password'  # Gmail App Password
  smtp_require_tls: true

# 路由配置
route:
  group_by: ['alertname', 'cluster', 'service']
  group_wait: 10s
  group_interval: 10s
  repeat_interval: 12h
  receiver: 'default-receiver'
  
  routes:
    # 高優先級告警（立即通知）
    - match:
        severity: critical
      receiver: 'critical-receiver'
      group_wait: 0s
      repeat_interval: 1h
    
    # 中優先級告警（10 分鐘內通知）
    - match:
        severity: warning
      receiver: 'warning-receiver'
      group_wait: 10m
      repeat_interval: 4h

# 接收器配置
receivers:
  - name: 'default-receiver'
    email_configs:
      - to: 'admin@example.com'
        headers:
          Subject: '[Network Toolbox] 告警通知'
  
  - name: 'critical-receiver'
    email_configs:
      - to: 'admin@example.com,ops@example.com'
        headers:
          Subject: '🚨 [CRITICAL] Network Toolbox 嚴重告警'
    # 可選：Slack 通知
    slack_configs:
      - api_url: 'https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK'
        channel: '#alerts'
        title: '🚨 Network Toolbox Critical Alert'
        text: '{{ range .Alerts }}{{ .Annotations.description }}{{ end }}'
  
  - name: 'warning-receiver'
    email_configs:
      - to: 'admin@example.com'
        headers:
          Subject: '⚠️  [WARNING] Network Toolbox 警告'

# 抑制規則（避免重複告警）
inhibit_rules:
  - source_match:
      severity: 'critical'
    target_match:
      severity: 'warning'
    equal: ['alertname', 'instance']
```

### 3.2 告警規則定義

**創建文件**：`monitoring/alerts/celery_alerts.yml`

```yaml
groups:
  - name: celery_tasks
    interval: 30s
    rules:
      # 規則 1：任務失敗率過高
      - alert: HighTaskFailureRate
        expr: |
          (
            sum(rate(celery_task_total{status="failure"}[5m]))
            /
            sum(rate(celery_task_total[5m]))
          ) > 0.10
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Celery task failure rate is high"
          description: "Task failure rate is {{ $value | humanizePercentage }} (threshold: 10%)"
      
      # 規則 2：任務執行時間過長
      - alert: TaskExecutionTooSlow
        expr: |
          histogram_quantile(0.95,
            sum(rate(celery_task_duration_seconds_bucket[5m])) by (le, task_name)
          ) > 600
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "Celery task {{ $labels.task_name }} is too slow"
          description: "95th percentile execution time is {{ $value }}s (threshold: 600s)"
      
      # 規則 3：任務堆積
      - alert: TaskQueueBacklog
        expr: |
          sum(celery_task_running) > 50
        for: 15m
        labels:
          severity: warning
        annotations:
          summary: "Celery task queue has backlog"
          description: "{{ $value }} tasks are currently running (threshold: 50)"
      
      # 規則 4：CPU 使用率過高
      - alert: HighCPUUsage
        expr: |
          system_cpu_percent > 85
        for: 10m
        labels:
          severity: critical
        annotations:
          summary: "System CPU usage is critically high"
          description: "CPU usage is {{ $value }}% (threshold: 85%)"
      
      # 規則 5：Worker 離線
      - alert: CeleryWorkerDown
        expr: |
          up{job="celery"} == 0
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "Celery worker is down"
          description: "Worker {{ $labels.instance }} has been down for more than 5 minutes"

  - name: redis_alerts
    interval: 30s
    rules:
      # 規則 6：Redis 記憶體使用率過高
      - alert: RedisHighMemory
        expr: |
          (redis_memory_used_bytes / redis_memory_max_bytes) * 100 > 80
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "Redis memory usage is high"
          description: "Memory usage is {{ $value }}% (threshold: 80%)"
      
      # 規則 7：Redis 連接數過多
      - alert: RedisTooManyConnections
        expr: |
          redis_connected_clients > 100
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Too many Redis connections"
          description: "{{ $value }} clients connected (threshold: 100)"

  - name: postgresql_alerts
    interval: 30s
    rules:
      # 規則 8：PostgreSQL 連接數過多
      - alert: PostgreSQLTooManyConnections
        expr: |
          pg_stat_database_numbackends > 50
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Too many PostgreSQL connections"
          description: "{{ $value }} connections (threshold: 50)"
      
      # 規則 9：PostgreSQL 慢查詢
      - alert: PostgreSQLSlowQueries
        expr: |
          rate(pg_stat_statements_mean_exec_time[5m]) > 1000
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "PostgreSQL has slow queries"
          description: "Average query execution time is {{ $value }}ms (threshold: 1000ms)"
```

### 3.3 更新 Prometheus 配置

**文件**：`monitoring/prometheus.yml`

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

# 🆕 添加告警配置
alerting:
  alertmanagers:
    - static_configs:
        - targets:
            - 'alertmanager:9093'

# 🆕 添加告警規則
rule_files:
  - '/etc/prometheus/alerts/*.yml'

# ... 其餘配置保持不變 ...
```

**掛載告警規則到 Prometheus**：

**文件**：`docker-compose.yml`

```yaml
services:
  prometheus:
    # ... 現有配置 ...
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml
      - ./monitoring/alerts:/etc/prometheus/alerts  # 🆕 掛載告警規則
      - prometheus_data:/prometheus
```

---

## 📋 完整部署步驟

### 步驟 1：準備監控配置文件（15 分鐘）

```bash
# 創建監控目錄結構
cd /home/owner/Codes/network-toolbox
mkdir -p monitoring/{alerts,grafana/{dashboards,datasources}}

# 創建所有配置文件（參考上面的內容）
touch monitoring/prometheus.yml
touch monitoring/alertmanager.yml
touch monitoring/alerts/celery_alerts.yml
touch monitoring/grafana/datasources/prometheus.yml
touch monitoring/grafana/dashboards/dashboard.yml
```

### 步驟 2：更新 Docker Compose（10 分鐘）

```bash
# 備份現有配置
cp docker-compose.yml docker-compose.yml.backup

# 編輯 docker-compose.yml
# 添加：prometheus, grafana, alertmanager, redis-exporter, postgres-exporter
```

### 步驟 3：安裝 Django Prometheus 集成（10 分鐘）

```bash
# 1. 添加依賴
echo "django-prometheus==2.3.1" >> backend/requirements.txt

# 2. 安裝依賴
docker exec nt-django pip install django-prometheus

# 3. 修改 settings.py 和 urls.py（參考上面）
```

### 步驟 4：添加自訂指標（20 分鐘）

```bash
# 創建指標模組
touch backend/library/utils/celery_metrics.py

# 編輯文件（參考上面的代碼）
# 在任務中添加指標記錄（參考上面的範例）
```

### 步驟 5：啟動監控服務（10 分鐘）

```bash
# 1. 啟動所有服務
docker compose up -d

# 2. 檢查服務狀態
docker compose ps

# 3. 查看日誌
docker compose logs -f prometheus
docker compose logs -f grafana
docker compose logs -f alertmanager
```

### 步驟 6：配置 Grafana 儀表板（30 分鐘）

```bash
# 1. 訪問 Grafana
# http://localhost:3001
# 帳號：admin
# 密碼：your_grafana_password

# 2. 驗證 Prometheus 數據源
# 導航到：Configuration → Data Sources → Prometheus
# 測試連接（應該顯示 "Data source is working"）

# 3. 創建儀表板
# 導航到：Create → Dashboard
# 添加 Panel（參考上面的 PromQL 查詢）

# 4. 導出儀表板
# Dashboard Settings → JSON Model
# 複製 JSON，保存到 monitoring/grafana/dashboards/celery-tasks.json
```

### 步驟 7：測試告警（15 分鐘）

```bash
# 1. 訪問 Prometheus
# http://localhost:9090

# 2. 查看告警規則
# 導航到：Alerts
# 應該看到所有定義的告警規則

# 3. 測試告警觸發
# 方式 1：模擬 CPU 過載
docker exec nt-django python -c "
import multiprocessing
def stress_cpu():
    while True:
        pass
for i in range(4):
    p = multiprocessing.Process(target=stress_cpu)
    p.start()
"

# 方式 2：停止 Worker（測試 Worker 離線告警）
docker exec nt-django supervisorctl stop celery-worker

# 4. 查看 AlertManager
# http://localhost:9093
# 應該看到觸發的告警

# 5. 檢查郵件
# 查看配置的郵箱是否收到告警郵件
```

---

## 🎯 使用指南

### 日常監控檢查清單

**每日檢查（5 分鐘）**：
- [ ] 訪問 Flower（http://localhost:5555）
  - 檢查昨日任務失敗次數（應該 < 5%）
  - 檢查任務執行時間（應該穩定）
  - 檢查 Worker 狀態（應該全部在線）

- [ ] 訪問 Grafana（http://localhost:3001）
  - 查看 CPU 使用率趨勢（應該 < 50%）
  - 查看任務執行時間趨勢（應該穩定）
  - 查看 Redis/PostgreSQL 狀態

**每週檢查（15 分鐘）**：
- [ ] 審查過去 7 天的告警記錄
- [ ] 分析任務失敗原因（Flower → Tasks → Failed）
- [ ] 檢查磁盤空間（Prometheus/Grafana 數據）
- [ ] 優化慢任務（執行時間 > 5 分鐘）

**每月檢查（30 分鐘）**：
- [ ] 生成月度報告（Grafana → Dashboard → Export）
- [ ] 分析長期趨勢（CPU、任務執行時間、失敗率）
- [ ] 調整告警閾值（根據實際情況）
- [ ] 規劃容量（是否需要增加資源）

### 告警響應流程

**告警等級**：

| 等級 | 響應時間 | 處理人 | 行動 |
|------|---------|--------|------|
| **Critical** | 15 分鐘內 | On-call 工程師 | 立即修復，必要時回滾 |
| **Warning** | 1 小時內 | 值班工程師 | 調查原因，制定修復計劃 |
| **Info** | 1 天內 | 開發團隊 | 記錄問題，計劃優化 |

**告警處理步驟**：

1. **收到告警通知**
   - 郵件/Slack 通知
   - 記錄告警時間和描述

2. **初步診斷**
   - 訪問 Grafana 查看相關指標
   - 訪問 Flower 查看任務狀態
   - 查看 Docker 日誌

3. **定位問題**
   - CPU 過高：檢查正在執行的任務
   - 任務失敗：查看錯誤日誌
   - 隊列堆積：檢查 Worker 狀態

4. **採取行動**
   - 緊急：重啟服務、暫停任務
   - 非緊急：調整配置、優化代碼

5. **驗證修復**
   - 等待告警自動恢復
   - 手動確認指標恢復正常

6. **文檔記錄**
   - 記錄問題原因
   - 記錄修復步驟
   - 更新運維文檔

---

## 📊 預期效果

### 短期效果（1 週內）

- ✅ **可視化所有任務執行狀態**：一目了然
- ✅ **即時發現問題**：CPU 過高、任務失敗立即知道
- ✅ **減少人工檢查時間**：從每天 30 分鐘降低至 5 分鐘

### 中期效果（1 個月內）

- ✅ **主動預防問題**：根據趨勢提前優化
- ✅ **快速定位故障**：平均修復時間從 2 小時降低至 30 分鐘
- ✅ **數據驅動決策**：根據實際數據優化任務排程

### 長期效果（3 個月以上）

- ✅ **系統穩定性提升**：任務成功率 > 95%
- ✅ **性能持續優化**：根據歷史數據不斷改進
- ✅ **預測性維護**：提前發現潛在問題

---

## 🔧 維護與優化

### 定期維護任務

**每月維護**：
```bash
# 1. 清理過期的 Prometheus 數據（自動執行，檢查即可）
docker exec nt-prometheus du -sh /prometheus

# 2. 清理 Grafana 快取
docker exec nt-grafana grafana-cli admin reset-admin-password new_password

# 3. 備份配置文件
tar -czf monitoring_backup_$(date +%Y%m%d).tar.gz monitoring/
```

**每季度優化**：
- 審查並調整告警規則（減少誤報）
- 優化 Grafana 儀表板（添加新指標）
- 升級監控組件版本

### 故障排查

**問題 1：Prometheus 無法抓取指標**
```bash
# 診斷
docker logs nt-prometheus | grep -i error

# 解決
# 1. 檢查目標服務是否在線
docker compose ps

# 2. 檢查網路連接
docker exec nt-prometheus wget -O- http://django:8000/metrics

# 3. 檢查配置文件
docker exec nt-prometheus cat /etc/prometheus/prometheus.yml
```

**問題 2：Grafana 無法連接 Prometheus**
```bash
# 診斷
docker logs nt-grafana | grep -i prometheus

# 解決
# 1. 驗證 Prometheus 運行正常
curl http://localhost:9090/-/healthy

# 2. 重新添加數據源
# Grafana UI → Configuration → Data Sources → Add → Prometheus
# URL: http://prometheus:9090
```

**問題 3：告警未觸發**
```bash
# 診斷
docker logs nt-alertmanager | grep -i error

# 解決
# 1. 檢查告警規則語法
docker exec nt-prometheus promtool check rules /etc/prometheus/alerts/celery_alerts.yml

# 2. 測試告警觸發
# Prometheus UI → Alerts → 點擊規則查看詳情

# 3. 檢查 AlertManager 配置
docker exec nt-alertmanager amtool config show
```

---

## 📚 參考資源

- **Prometheus 文檔**：https://prometheus.io/docs/
- **Grafana 文檔**：https://grafana.com/docs/
- **Flower 文檔**：https://flower.readthedocs.io/
- **Django Prometheus**：https://github.com/korfuri/django-prometheus
- **AlertManager 文檔**：https://prometheus.io/docs/alerting/latest/alertmanager/

---

**最後更新**：2025-11-25  
**狀態**：詳細實施方案已完成  
**預計實施時間**：  
- 階段一（Flower）：1 小時  
- 階段二（Prometheus + Grafana）：2-3 小時  
- 階段三（AlertManager）：1-2 小時  
- **總計**：4-6 小時

**下一步行動**：等待用戶確認後開始部署
