# Celery 服務持久化運行方案 - Supervisor 實作

## 📋 問題分析

### 之前的問題

在之前的實作中，我們在 `entrypoint.sh` 中使用了 `--detach` 選項來啟動 Celery：

```bash
celery -A network_toolbox worker --loglevel=info --detach
celery -A network_toolbox beat --loglevel=info --detach
exec python manage.py runserver 0.0.0.0:8000
```

**這種方式存在以下問題：**

1. **進程管理不當**
   - `--detach` 會將 Celery 進程放到背景執行
   - 容器的主進程是 `python manage.py runserver`
   - 背景進程可能被 Docker 容器終止或無法監控

2. **沒有日誌輸出**
   - `--detach` 模式不會輸出日誌到標準輸出
   - 無法通過 `docker compose logs` 查看 Celery 狀態
   - 調試困難

3. **進程無法監控和自動重啟**
   - Celery 進程崩潰時不會自動重啟
   - 無法查看進程狀態
   - 沒有健康檢查機制

4. **Beat 排程器未正常工作**
   - 雖然 Worker 在運行，但 Beat 沒有正常調度任務
   - `celery inspect scheduled` 顯示 empty
   - NAS 上的文件沒有自動更新

### 診斷過程

```bash
# ✅ Worker 確實在運行
$ docker compose exec django celery -A network_toolbox inspect ping
->  celery@066fd1b522a3: OK pong
->  celery@29d149bf52e6: OK pong
2 nodes online.

# ❌ 但沒有排程任務
$ docker compose exec django celery -A network_toolbox inspect scheduled
->  celery@29d149bf52e6: OK - empty -
->  celery@066fd1b522a3: OK - empty -

# ❌ Beat 的 schedule 文件不存在
$ find /app -name 'celerybeat*'
(沒有結果)

# ❌ NAS 文件沒有更新
$ find /mnt/mdt/.../jenkins_test_storage/ -type f -mmin -30
(0 files)
```

## 🔧 解決方案：使用 Supervisor 進程管理工具

### 什麼是 Supervisor？

Supervisor 是一個 Python 編寫的進程管理工具，可以：
- **同時管理多個進程**
- **自動監控進程健康狀態**
- **進程崩潰時自動重啟**
- **統一管理日誌輸出**
- **提供進程控制接口**

### 實作步驟

#### 1. 創建 Supervisor 配置文件

**文件位置**：`backend/supervisord.conf`

```ini
[supervisord]
nodaemon=true
logfile=/var/log/supervisor/supervisord.log
pidfile=/var/run/supervisord.pid
user=root

[program:celery-worker]
command=celery -A network_toolbox worker --loglevel=info
directory=/app
stdout_logfile=/app/logs/celery_worker.log
stderr_logfile=/app/logs/celery_worker_error.log
autostart=true
autorestart=true
startsecs=10
stopwaitsecs=600
killasgroup=true
priority=998

[program:celery-beat]
command=celery -A network_toolbox beat --loglevel=info
directory=/app
stdout_logfile=/app/logs/celery_beat.log
stderr_logfile=/app/logs/celery_beat_error.log
autostart=true
autorestart=true
startsecs=10
priority=999

[program:django]
command=python manage.py runserver 0.0.0.0:8000
directory=/app
stdout_logfile=/dev/stdout
stdout_logfile_maxbytes=0
stderr_logfile=/dev/stderr
stderr_logfile_maxbytes=0
autostart=true
autorestart=true
startsecs=5
priority=1000
```

**配置說明：**

- **nodaemon=true**：Supervisor 在前台運行（Docker 容器需要）
- **priority**：啟動順序（數字越大越晚啟動）
  - 998: Celery Worker 最先啟動
  - 999: Celery Beat 其次
  - 1000: Django 最後啟動
- **autostart/autorestart**：自動啟動和崩潰重啟
- **startsecs**：啟動後等待多少秒才認為啟動成功
- **stopwaitsecs**：停止時最多等待多少秒（Celery 需要較長時間處理任務）
- **killasgroup**：停止時殺死整個進程組（Celery Worker 會創建子進程）

#### 2. 修改 Dockerfile

在 `backend/Dockerfile` 中安裝 Supervisor：

```dockerfile
# 安裝系統依賴（添加 supervisor）
RUN apt-get update && apt-get install -y \
    postgresql-client \
    iputils-ping \
    cifs-utils \
    p7zip-full \
    gcc \
    libffi-dev \
    libssl-dev \
    python3-dev \
    supervisor \
    && rm -rf /var/lib/apt/lists/*

# 建立 Supervisor 日誌目錄
RUN mkdir -p /var/log/supervisor

# 複製 Supervisor 配置
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf
```

#### 3. 修改 entrypoint.sh

簡化啟動腳本，讓 Supervisor 管理所有進程：

```bash
#!/bin/bash
# Django 容器啟動腳本
# 1. 掛載 NAS
# 2. 使用 Supervisor 啟動所有服務

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
echo "🚀 使用 Supervisor 啟動所有服務..."
echo "   - Celery Worker（異步任務處理）"
echo "   - Celery Beat（定時任務調度器）"
echo "   - Django 開發伺服器"
echo ""

# 啟動 Supervisor（管理所有進程）
exec /usr/bin/supervisord -c /etc/supervisor/conf.d/supervisord.conf
```

## 📦 部署步驟

### 1. 重建 Django 容器

```bash
cd /home/owner/Codes/network-toolbox

# 停止容器
docker compose down

# 重建 Django 容器
docker compose build django

# 啟動所有服務
docker compose up -d
```

### 2. 驗證服務狀態

```bash
# 查看容器日誌
docker compose logs django -f

# 檢查 Celery Worker
docker compose exec django celery -A network_toolbox inspect ping

# 檢查 Beat 排程任務
docker compose exec django celery -A network_toolbox inspect scheduled

# 查看 Supervisor 管理的進程
docker compose exec django supervisorctl status

# 查看 Celery 日誌
docker compose exec django tail -f /app/logs/celery_worker.log
docker compose exec django tail -f /app/logs/celery_beat.log
```

### 3. 手動控制服務

```bash
# 重啟 Celery Worker
docker compose exec django supervisorctl restart celery-worker

# 重啟 Celery Beat
docker compose exec django supervisorctl restart celery-beat

# 重啟 Django
docker compose exec django supervisorctl restart django

# 查看所有進程狀態
docker compose exec django supervisorctl status
```

## 🎯 改進效果

### 之前 vs 現在

| 項目 | 之前（--detach） | 現在（Supervisor） |
|-----|----------------|------------------|
| 進程管理 | ❌ 無管理 | ✅ 統一管理 |
| 自動重啟 | ❌ 不支持 | ✅ 自動重啟 |
| 日誌輸出 | ❌ 無日誌 | ✅ 獨立日誌文件 |
| 狀態監控 | ❌ 無法監控 | ✅ supervisorctl status |
| Beat 調度 | ❌ 未運行 | ✅ 正常運行 |
| 調試便利性 | ❌ 困難 | ✅ 方便 |

### 新的日誌文件

```
backend/logs/
├── celery_worker.log          # Worker 正常輸出
├── celery_worker_error.log    # Worker 錯誤輸出
├── celery_beat.log            # Beat 正常輸出
├── celery_beat_error.log      # Beat 錯誤輸出
├── django.log                 # Django 應用日誌
├── django_error.log           # Django 錯誤日誌
└── ... (其他日誌)
```

## 🔍 監控和調試

### 查看進程狀態

```bash
# 方式 1：Supervisor 控制台
docker compose exec django supervisorctl status

# 輸出範例：
# celery-beat                      RUNNING   pid 123, uptime 0:05:30
# celery-worker                    RUNNING   pid 124, uptime 0:05:30
# django                           RUNNING   pid 125, uptime 0:05:29
```

### 查看 Celery 健康狀態

```bash
# Ping Workers
docker compose exec django celery -A network_toolbox inspect ping

# 查看活動任務
docker compose exec django celery -A network_toolbox inspect active

# 查看排程任務
docker compose exec django celery -A network_toolbox inspect scheduled

# 查看已註冊任務
docker compose exec django celery -A network_toolbox inspect registered

# 查看 Worker 統計
docker compose exec django celery -A network_toolbox inspect stats
```

### 監控 Beat 排程

```bash
# 查看 Beat 日誌（查看定時任務觸發記錄）
docker compose exec django tail -f /app/logs/celery_beat.log

# 應該看到類似輸出：
# [2025-11-14 14:00:00,000: INFO/MainProcess] Scheduler: Sending due task sync-jenkins-jobs-hourly (api.tasks.sync_all_jenkins_jobs_task)
# [2025-11-14 15:00:00,000: INFO/MainProcess] Scheduler: Sending due task sync-dhcp-logs-every-5min (api.tasks.sync_dhcp_logs_task)
```

### 驗證 NAS 文件更新

```bash
# 查看最近 30 分鐘內更新的文件
docker compose exec django find /mnt/mdt/Team/PQ1-3/tool/jenkins_test_storage/ -type f -mmin -30

# 查看特定 Jenkins Server 的最新文件
docker compose exec django ls -lt /mnt/mdt/Team/PQ1-3/tool/jenkins_test_storage/jenkins_182/ | head -20
```

## 🚨 故障排查

### Beat 沒有觸發任務

```bash
# 1. 檢查 Beat 進程狀態
docker compose exec django supervisorctl status celery-beat

# 2. 查看 Beat 日誌
docker compose exec django tail -100 /app/logs/celery_beat.log

# 3. 檢查 schedule 文件
docker compose exec django ls -la /app/celerybeat-schedule*

# 4. 重啟 Beat
docker compose exec django supervisorctl restart celery-beat
```

### Worker 沒有處理任務

```bash
# 1. 檢查 Worker 狀態
docker compose exec django supervisorctl status celery-worker

# 2. 查看 Worker 日誌
docker compose exec django tail -100 /app/logs/celery_worker.log

# 3. Ping Worker
docker compose exec django celery -A network_toolbox inspect ping

# 4. 重啟 Worker
docker compose exec django supervisorctl restart celery-worker
```

### 進程頻繁重啟

```bash
# 1. 查看 Supervisor 日誌
docker compose exec django tail -100 /var/log/supervisor/supervisord.log

# 2. 查看具體進程的錯誤日誌
docker compose exec django tail -100 /app/logs/celery_worker_error.log
docker compose exec django tail -100 /app/logs/celery_beat_error.log
```

### 完全重置服務

```bash
# 1. 停止容器
docker compose down

# 2. 清理舊的 schedule 文件
rm -f backend/celerybeat-schedule*

# 3. 重建容器
docker compose build django

# 4. 啟動服務
docker compose up -d

# 5. 驗證
docker compose exec django supervisorctl status
```

## 📚 相關資源

- [Supervisor 官方文檔](http://supervisord.org/)
- [Celery 官方文檔 - Daemonization](https://docs.celeryq.dev/en/stable/userguide/daemonizing.html)
- [Docker 容器內運行多個進程的最佳實踐](https://docs.docker.com/config/containers/multi-service_container/)

## 📝 版本歷史

- **2025-11-14**：實作 Supervisor 進程管理方案，解決 Celery Beat 未運行問題
- **2025-11-13**：首次嘗試使用 `--detach` 啟動 Celery（存在問題）

---

**文檔維護**：Network Toolbox Team  
**最後更新**：2025-11-14
