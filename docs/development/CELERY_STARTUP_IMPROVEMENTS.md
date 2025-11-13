# Celery 啟動問題分析與改善方案

## 🔍 問題根本原因分析

### 為什麼之前 Celery Beat 沒有運行？

#### 1. **容器啟動腳本不完整**

**問題**：`backend/entrypoint.sh` 原本只啟動了 Django 開發伺服器：

```bash
# 舊版 entrypoint.sh
#!/bin/bash
echo "🚀 啟動 Django 開發伺服器..."
exec python manage.py runserver 0.0.0.0:8000
```

**缺少的組件**：
- ❌ Celery Worker（任務處理器）
- ❌ Celery Beat（定時任務調度器）

**結果**：
- Django 可以正常運行，API 可以訪問
- 但所有後台任務和定時任務都無法執行

#### 2. **開發習慣問題**

**常見誤區**：
1. **手動啟動 Celery**：開發時在終端手動運行 `celery worker`，但忘記添加到啟動腳本
2. **測試時正常**：手動測試時 Celery 在運行，但容器重啟後就失效
3. **Docker 環境特性**：容器重啟後，所有未在 `entrypoint.sh` 中定義的進程都會消失

#### 3. **缺乏監控機制**

**問題**：
- 沒有自動檢測 Celery 服務狀態
- 沒有在 Celery 停止時發出告警
- 發現問題時已經過了很久（文件停止更新才發現）

#### 4. **文檔不足**

**問題**：
- 開發文檔沒有明確說明 Celery 的啟動要求
- 部署檢查清單中沒有包含 Celery 驗證步驟

## ✅ 已實施的改善方案

### 改善 1：完整的啟動腳本

**新版 `backend/entrypoint.sh`**：

```bash
#!/bin/bash
# Django 容器啟動腳本
# 1. 掛載 NAS
# 2. 啟動 Celery Worker
# 3. 啟動 Celery Beat
# 4. 啟動 Django 開發伺服器

set -e

echo "========================================="
echo "Django 容器啟動中..."
echo "========================================="

# 執行 NAS 掛載
if [ -f "/app/mount_nas.sh" ]; then
    echo "🔗 執行 NAS 掛載..."
    bash /app/mount_nas.sh || echo "⚠️  NAS 掛載失敗，繼續啟動服務..."
else
    echo "⚠️  找不到 mount_nas.sh，跳過 NAS 掛載"
fi

echo ""
echo "🚀 啟動 Celery Worker..."
celery -A network_toolbox worker --loglevel=info --detach

echo "🚀 啟動 Celery Beat（定時任務調度器）..."
celery -A network_toolbox beat --loglevel=info --detach

echo "🚀 啟動 Django 開發伺服器..."
exec python manage.py runserver 0.0.0.0:8000
```

**改善效果**：
- ✅ 容器啟動時自動啟動所有必要服務
- ✅ 容器重啟後服務自動恢復
- ✅ 開發和生產環境保持一致

## 🚀 進階改善方案

### 改善 2：使用 Supervisor 管理多進程

**為什麼需要 Supervisor？**

當前的 `--detach` 方式有以下問題：
1. ❌ 如果 Celery Worker 崩潰，不會自動重啟
2. ❌ 無法查看 Celery 的實時日誌（需要查找日誌文件）
3. ❌ 難以管理多個進程的生命週期

**解決方案：安裝 Supervisor**

#### 步驟 1：修改 Dockerfile

```dockerfile
# backend/Dockerfile
FROM python:3.11-slim

# ... 其他配置 ...

# 安裝 Supervisor
RUN apt-get update && apt-get install -y supervisor && rm -rf /var/lib/apt/lists/*

# 複製 Supervisor 配置
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# ... 其他配置 ...
```

#### 步驟 2：創建 Supervisor 配置

```ini
# backend/supervisord.conf
[supervisord]
nodaemon=true
user=root
logfile=/var/log/supervisor/supervisord.log
pidfile=/var/run/supervisord.pid

[program:celery_worker]
command=celery -A network_toolbox worker --loglevel=info
directory=/app
user=root
autostart=true
autorestart=true
stopasgroup=true
killasgroup=true
redirect_stderr=true
stdout_logfile=/app/logs/celery_worker.log
stdout_logfile_maxbytes=50MB
stdout_logfile_backups=10
stopwaitsecs=600

[program:celery_beat]
command=celery -A network_toolbox beat --loglevel=info
directory=/app
user=root
autostart=true
autorestart=true
stopasgroup=true
killasgroup=true
redirect_stderr=true
stdout_logfile=/app/logs/celery_beat.log
stdout_logfile_maxbytes=10MB
stdout_logfile_backups=10

[program:django]
command=python manage.py runserver 0.0.0.0:8000
directory=/app
user=root
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/app/logs/django.log
stdout_logfile_maxbytes=50MB
stdout_logfile_backups=10
```

#### 步驟 3：修改 entrypoint.sh

```bash
#!/bin/bash
# Django 容器啟動腳本（使用 Supervisor）

set -e

echo "========================================="
echo "Django 容器啟動中（Supervisor 模式）..."
echo "========================================="

# 執行 NAS 掛載
if [ -f "/app/mount_nas.sh" ]; then
    echo "🔗 執行 NAS 掛載..."
    bash /app/mount_nas.sh || echo "⚠️  NAS 掛載失敗，繼續啟動服務..."
fi

echo ""
echo "🚀 啟動 Supervisor（管理 Django、Celery Worker、Celery Beat）..."
exec /usr/bin/supervisord -c /etc/supervisor/conf.d/supervisord.conf
```

**Supervisor 的優勢**：
- ✅ **自動重啟**：進程崩潰時自動重啟
- ✅ **日誌管理**：統一的日誌輪替機制
- ✅ **進程監控**：可以查看所有進程狀態
- ✅ **優雅停止**：支持 graceful shutdown

#### 步驟 4：管理命令

```bash
# 查看所有進程狀態
docker compose exec django supervisorctl status

# 重啟 Celery Worker
docker compose exec django supervisorctl restart celery_worker

# 查看 Celery 日誌
docker compose exec django supervisorctl tail -f celery_worker

# 停止所有服務
docker compose exec django supervisorctl stop all
```

### 改善 3：健康檢查機制

#### 3.1 Docker Compose 健康檢查

**修改 `docker-compose.yml`**：

```yaml
services:
  django:
    # ... 其他配置 ...
    healthcheck:
      test: ["CMD", "python", "-c", "
        import requests;
        import sys;
        from celery import Celery;
        
        # 檢查 Django
        try:
            r = requests.get('http://localhost:8000/api/health/', timeout=5);
            r.raise_for_status();
        except:
            print('Django health check failed');
            sys.exit(1);
        
        # 檢查 Celery
        try:
            app = Celery('network_toolbox');
            app.config_from_object('django.conf:settings', namespace='CELERY');
            i = app.control.inspect();
            if not i.ping():
                raise Exception('No Celery workers');
        except:
            print('Celery health check failed');
            sys.exit(1);
        
        print('All services healthy');
      "]
      interval: 1m
      timeout: 10s
      retries: 3
      start_period: 40s
```

#### 3.2 創建健康檢查 API

**在 `backend/api/views.py` 添加**：

```python
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from celery import Celery
from django.conf import settings

@api_view(['GET'])
@permission_classes([AllowAny])
def health_check(request):
    """系統健康檢查端點"""
    
    health_status = {
        'django': 'ok',
        'celery_worker': 'unknown',
        'celery_beat': 'unknown',
        'database': 'unknown',
        'nas': 'unknown',
    }
    
    # 檢查 Celery
    try:
        app = Celery('network_toolbox')
        app.config_from_object('django.conf:settings', namespace='CELERY')
        
        inspect = app.control.inspect()
        
        # 檢查 Worker
        active_workers = inspect.active()
        if active_workers:
            health_status['celery_worker'] = 'ok'
        else:
            health_status['celery_worker'] = 'no_workers'
        
        # 檢查 Beat（通過查看 scheduled tasks）
        scheduled = inspect.scheduled()
        if scheduled:
            health_status['celery_beat'] = 'ok'
        else:
            health_status['celery_beat'] = 'no_schedule'
            
    except Exception as e:
        health_status['celery_worker'] = f'error: {str(e)}'
        health_status['celery_beat'] = f'error: {str(e)}'
    
    # 檢查資料庫
    try:
        from django.db import connection
        connection.ensure_connection()
        health_status['database'] = 'ok'
    except Exception as e:
        health_status['database'] = f'error: {str(e)}'
    
    # 檢查 NAS
    try:
        import os
        nas_path = settings.JENKINS_STORAGE_BASE_PATH
        if os.path.exists(nas_path) and os.access(nas_path, os.W_OK):
            health_status['nas'] = 'ok'
        else:
            health_status['nas'] = 'not_accessible'
    except Exception as e:
        health_status['nas'] = f'error: {str(e)}'
    
    # 判斷整體狀態
    all_ok = all(v == 'ok' for v in health_status.values())
    status_code = 200 if all_ok else 503
    
    return Response({
        'status': 'healthy' if all_ok else 'unhealthy',
        'services': health_status
    }, status=status_code)
```

**註冊路由**：

```python
# backend/api/urls.py
urlpatterns = [
    # ... 其他路由 ...
    path('health/', views.health_check, name='health_check'),
]
```

#### 3.3 前端監控儀表板

**創建系統狀態組件**：

```javascript
// frontend/src/components/SystemHealthStatus.js
import React, { useState, useEffect } from 'react';
import { Alert, Badge, Card, Space } from 'antd';
import axios from 'axios';

const SystemHealthStatus = () => {
    const [health, setHealth] = useState(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const checkHealth = async () => {
            try {
                const response = await axios.get('/api/health/');
                setHealth(response.data);
            } catch (error) {
                console.error('Health check failed:', error);
                setHealth({ status: 'unhealthy', services: {} });
            } finally {
                setLoading(false);
            }
        };

        checkHealth();
        const interval = setInterval(checkHealth, 60000); // 每分鐘檢查

        return () => clearInterval(interval);
    }, []);

    if (loading) return null;

    const getStatusColor = (status) => {
        if (status === 'ok') return 'success';
        if (status === 'unknown') return 'default';
        return 'error';
    };

    return (
        <Card size="small" style={{ marginBottom: 16 }}>
            <Space>
                <span>系統狀態：</span>
                {Object.entries(health?.services || {}).map(([service, status]) => (
                    <Badge 
                        key={service}
                        status={getStatusColor(status)}
                        text={service}
                    />
                ))}
            </Space>
            {health?.status === 'unhealthy' && (
                <Alert
                    message="系統服務異常"
                    description="部分服務未正常運行，請檢查系統狀態"
                    type="warning"
                    showIcon
                    style={{ marginTop: 8 }}
                />
            )}
        </Card>
    );
};

export default SystemHealthStatus;
```

### 改善 4：自動化監控與告警

#### 4.1 創建監控腳本

```bash
#!/bin/bash
# scripts/monitor_celery.sh
# Celery 服務監控腳本

LOG_FILE="/var/log/celery_monitor.log"
ALERT_EMAIL="admin@example.com"

echo "[$(date)] 開始檢查 Celery 服務..." >> "$LOG_FILE"

# 檢查 Celery Worker
if ! docker compose exec -T django celery -A network_toolbox inspect ping > /dev/null 2>&1; then
    echo "[$(date)] ❌ Celery Worker 未運行！嘗試重啟..." >> "$LOG_FILE"
    
    # 發送告警（可選）
    # echo "Celery Worker 停止運行" | mail -s "Celery Alert" "$ALERT_EMAIL"
    
    # 嘗試重啟
    docker compose exec -T django celery -A network_toolbox worker --loglevel=info --detach
    
    # 再次檢查
    sleep 5
    if docker compose exec -T django celery -A network_toolbox inspect ping > /dev/null 2>&1; then
        echo "[$(date)] ✅ Celery Worker 已成功重啟" >> "$LOG_FILE"
    else
        echo "[$(date)] ❌ Celery Worker 重啟失敗！" >> "$LOG_FILE"
    fi
else
    echo "[$(date)] ✅ Celery Worker 運行正常" >> "$LOG_FILE"
fi

# 檢查 Celery Beat（通過檢查最近的任務執行記錄）
LAST_TASK_TIME=$(docker compose exec -T django python manage.py shell -c "
from django_celery_beat.models import PeriodicTask
from django.utils import timezone
from datetime import timedelta
recent = PeriodicTask.objects.filter(last_run_at__gte=timezone.now() - timedelta(minutes=10)).count()
print(recent)
" 2>/dev/null)

if [ "$LAST_TASK_TIME" -eq 0 ]; then
    echo "[$(date)] ⚠️  Celery Beat 可能未運行（最近 10 分鐘無任務執行）" >> "$LOG_FILE"
else
    echo "[$(date)] ✅ Celery Beat 運行正常（最近 10 分鐘執行了 $LAST_TASK_TIME 個任務）" >> "$LOG_FILE"
fi

echo "[$(date)] 檢查完成" >> "$LOG_FILE"
echo "---" >> "$LOG_FILE"
```

#### 4.2 設置 Cron 定期監控

```bash
# 編輯 crontab
crontab -e

# 添加每 5 分鐘檢查一次
*/5 * * * * /home/owner/Codes/network-toolbox/scripts/monitor_celery.sh
```

### 改善 5：完善的部署檢查清單

**創建 `docs/deployment/DEPLOYMENT_CHECKLIST.md`**：

```markdown
# 部署檢查清單

## 🚀 部署前檢查

- [ ] 代碼已提交到 Git
- [ ] 環境變數已配置（.env 文件）
- [ ] 資料庫遷移已完成
- [ ] 靜態文件已收集

## 🔧 服務啟動檢查

### 1. 容器啟動
```bash
docker compose up -d
docker compose ps  # 確認所有容器都是 Up 狀態
```

### 2. Django 檢查
```bash
curl http://localhost/api/health/
# 應該返回 200 OK
```

### 3. Celery Worker 檢查
```bash
docker compose exec django celery -A network_toolbox inspect ping
# 應該返回 pong 回應
```

### 4. Celery Beat 檢查
```bash
docker compose exec django celery -A network_toolbox inspect scheduled
# 應該顯示排程的任務列表
```

### 5. NAS 掛載檢查
```bash
docker compose exec django ls -la /mnt/mdt/
# 應該能看到 NAS 目錄內容
```

### 6. 資料庫連接檢查
```bash
docker compose exec django python manage.py dbshell
# 應該能連接到資料庫
```

## 📊 功能驗證

- [ ] 前端頁面可以正常訪問
- [ ] API 端點正常響應
- [ ] DHCP 日誌同步功能正常
- [ ] Jenkins 自動同步功能正常
- [ ] 定時任務正常執行

## 🔍 持續監控

- [ ] 設置 Cron 監控任務
- [ ] 配置健康檢查端點
- [ ] 設置日誌輪替
- [ ] 配置磁碟空間告警
```

## 📊 改善效果對比

| 指標 | 改善前 | 改善後 |
|-----|-------|-------|
| **服務自動啟動** | ❌ 需手動啟動 | ✅ 容器啟動時自動 |
| **進程崩潰恢復** | ❌ 需手動重啟 | ✅ Supervisor 自動重啟 |
| **健康檢查** | ❌ 無 | ✅ 每分鐘自動檢查 |
| **監控告警** | ❌ 無 | ✅ 自動監控+告警 |
| **日誌管理** | ⚠️ 散落各處 | ✅ 統一管理+輪替 |
| **部署檢查** | ❌ 憑經驗 | ✅ 標準化清單 |
| **問題發現** | ❌ 用戶報告後 | ✅ 主動發現 |
| **故障恢復時間** | ⚠️ 數小時到數天 | ✅ 幾分鐘內自動 |

## 🎯 實施優先級

### 階段 1：立即實施（已完成）✅
- [x] 修改 `entrypoint.sh` 添加 Celery 啟動
- [x] 驗證服務正常運行
- [x] 創建故障排查文檔

### 階段 2：短期改善（建議 1 週內完成）
- [ ] 安裝 Supervisor 管理進程
- [ ] 創建健康檢查 API
- [ ] 設置基本監控腳本

### 階段 3：中期改善（建議 1 個月內完成）
- [ ] 完善前端監控儀表板
- [ ] 實施自動化告警
- [ ] 完善部署文檔

### 階段 4：長期優化（持續改進）
- [ ] 整合更專業的監控系統（如 Prometheus + Grafana）
- [ ] 實施分布式追蹤（如 Jaeger）
- [ ] 建立完整的 SRE 流程

## 📚 相關文檔

- [Celery 週期性任務修復報告](../troubleshooting/CELERY_PERIODIC_TASKS_FIX.md)
- [Supervisor 官方文檔](http://supervisord.org/)
- [Docker Compose 健康檢查](https://docs.docker.com/compose/compose-file/compose-file-v3/#healthcheck)
- [Celery 監控最佳實踐](https://docs.celeryproject.org/en/stable/userguide/monitoring.html)

## 🤝 貢獻

如果您有更好的改善建議，歡迎提交 Pull Request 或 Issue。

---

**文檔版本**：v1.0  
**創建日期**：2025-11-14  
**維護者**：Network Toolbox Team
