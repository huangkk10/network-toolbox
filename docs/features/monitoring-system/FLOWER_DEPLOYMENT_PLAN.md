# Flower 監控部署計畫（第一階段）

**創建日期**：2025-11-25  
**狀態**：✅ **Flower 已存在，本計畫為優化與驗證**  
**預計時間**：30-45 分鐘（優化）

---

## 📋 現況分析

### ✅ 已完成的配置

經檢查發現，**Flower 服務已經在運行中**！

**docker-compose.yml 現有配置**：
```yaml
celery_flower:
  build:
    context: ./backend
    dockerfile: Dockerfile
  container_name: nt-celery-flower
  restart: unless-stopped
  command: celery -A network_toolbox flower --port=5555
  environment:
    - TZ=Asia/Taipei
    - REDIS_HOST=redis
    - REDIS_PORT=6379
  ports:
    - "5555:5555"
  depends_on:
    - redis
    - celery_worker
  networks:
    - nt_network
```

**Celery 配置（backend/network_toolbox/settings.py）**：
```python
CELERY_BROKER_URL = f'redis://{REDIS_HOST}:{REDIS_PORT}/1'  # ✅ 已使用 Redis
```

**Celery 應用配置（backend/network_toolbox/celery.py）**：
```python
app.conf.update(
    task_track_started=True,      # ✅ 已啟用任務追蹤
    task_send_sent_event=True,    # ✅ 已啟用任務事件發送
)
```

### ⚠️ 發現的問題

1. **缺少基本認證**：Flower 沒有配置帳號密碼，任何人都可以訪問
2. **缺少持久化配置**：任務歷史記錄不會保存
3. **缺少完整的事件配置**：可能缺少 `worker_send_task_events` 配置

---

## 🎯 優化計畫（30-45 分鐘）

### 階段 1：驗證 Flower 是否正常運行（5 分鐘）

#### 步驟 1.1：檢查服務狀態

```bash
# 1. 檢查 Flower 容器狀態
docker compose ps celery_flower

# 2. 查看 Flower 日誌
docker compose logs celery_flower --tail 50

# 3. 驗證端口監聽
docker exec nt-celery-flower netstat -tlnp | grep 5555

# 4. 檢查 Redis 連接
docker exec nt-celery-flower redis-cli -h redis ping
```

**預期結果**：
- ✅ 容器狀態：`Up`
- ✅ 日誌顯示：`Starting Flower on port 5555`
- ✅ 端口監聽：`0.0.0.0:5555`
- ✅ Redis 連接：`PONG`

#### 步驟 1.2：訪問 Flower Web UI

```bash
# 在瀏覽器訪問
http://localhost:5555
```

**檢查項目**：
- [ ] 首頁是否正常顯示
- [ ] Dashboard 是否顯示 Worker 狀態
- [ ] Tasks 頁面是否顯示任務列表
- [ ] Workers 頁面是否顯示 Worker 資訊

**如果無法訪問**：
```bash
# 重啟 Flower 服務
docker compose restart celery_flower

# 查看詳細錯誤
docker compose logs celery_flower -f
```

---

### 階段 2：添加基本認證（10 分鐘）

**目的**：防止未授權訪問，保護監控數據

#### 步驟 2.1：配置環境變數

**編輯文件**：`docker-compose.yml`

**修改位置**：`celery_flower` 服務的 `environment` 部分

**添加配置**：
```yaml
celery_flower:
  # ... 現有配置 ...
  environment:
    - TZ=Asia/Taipei
    - REDIS_HOST=redis
    - REDIS_PORT=6379
    # 🆕 添加基本認證（帳號:密碼）
    - FLOWER_BASIC_AUTH=admin:NetworkToolbox@2025
    # 🆕 設定 Flower 持久化（保存任務歷史）
    - FLOWER_PERSISTENT=True
    - FLOWER_DB=/data/flower.db
    - FLOWER_STATE_SAVE_INTERVAL=5000  # 每 5000 個任務保存一次狀態
  # 🆕 添加數據持久化 Volume
  volumes:
    - flower_data:/data
```

**添加 Volume 定義**（在文件最後）：
```yaml
volumes:
  postgres_data:
  static_files:
  media_files:
  redis_data:
  flower_data:  # 🆕 Flower 數據持久化
```

#### 步驟 2.2：應用配置

```bash
# 1. 停止 Flower
docker compose stop celery_flower

# 2. 創建 Volume
docker volume create network-toolbox_flower_data

# 3. 重新啟動 Flower
docker compose up -d celery_flower

# 4. 查看日誌確認啟動成功
docker compose logs celery_flower --tail 20
```

#### 步驟 2.3：驗證認證

```bash
# 訪問 Flower（應該會要求輸入帳號密碼）
http://localhost:5555

# 登入資訊：
# 帳號：admin
# 密碼：NetworkToolbox@2025
```

**預期結果**：
- ✅ 瀏覽器彈出登入對話框
- ✅ 輸入帳號密碼後可以正常訪問
- ✅ 無法直接訪問（未登入時拒絕訪問）

---

### 階段 3：完善 Celery 事件配置（10 分鐘）

**目的**：確保 Flower 可以接收所有任務事件

#### 步驟 3.1：檢查當前配置

```bash
# 進入 Django Shell 查看 Celery 配置
docker exec -it nt-django python manage.py shell
```

```python
from network_toolbox.celery import app

# 查看事件相關配置
print("task_track_started:", app.conf.task_track_started)
print("task_send_sent_event:", app.conf.task_send_sent_event)
print("worker_send_task_events:", app.conf.worker_send_task_events)

# 退出
exit()
```

#### 步驟 3.2：更新 Celery 配置（如需要）

**文件**：`backend/network_toolbox/celery.py`

**在 `app.conf.update()` 中添加**（如果缺少）：
```python
app.conf.update(
    # 時區設置
    timezone='Asia/Taipei',
    enable_utc=False,
    
    # 任務結果過期時間（1 天）
    result_expires=86400,
    
    # 任務序列化格式
    task_serializer='json',
    result_serializer='json',
    accept_content=['json'],
    
    # Worker 配置
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=50,
    
    # ✅ 任務追蹤（Flower 需要）
    task_track_started=True,
    task_send_sent_event=True,
    
    # 🆕 Worker 事件發送（Flower 需要）
    worker_send_task_events=True,  # ← 如果缺少，添加這行
)
```

#### 步驟 3.3：更新 settings.py（如需要）

**文件**：`backend/network_toolbox/settings.py`

**添加或確認存在**：
```python
# Celery 配置
CELERY_BROKER_URL = f'redis://{REDIS_HOST}:{REDIS_PORT}/1'
CELERY_RESULT_BACKEND = f'redis://{REDIS_HOST}:{REDIS_PORT}/1'  # 🆕 確保有 Result Backend
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'Asia/Taipei'

# 🆕 Flower 需要的事件配置
CELERY_WORKER_SEND_TASK_EVENTS = True
CELERY_TASK_SEND_SENT_EVENT = True
CELERY_TASK_TRACK_STARTED = True
```

#### 步驟 3.4：重啟服務應用配置

```bash
# 1. 重啟 Celery Worker 和 Beat
docker compose restart celery_worker celery_beat

# 2. 重啟 Flower
docker compose restart celery_flower

# 3. 等待 30 秒讓服務完全啟動
sleep 30

# 4. 查看日誌
docker compose logs celery_worker --tail 20
docker compose logs celery_flower --tail 20
```

---

### 階段 4：測試與驗證（15 分鐘）

#### 步驟 4.1：手動執行測試任務

```bash
docker exec -it nt-django python manage.py shell
```

```python
# 測試輕量級任務
from api.tasks import check_nas_connection_task

# 執行任務
result = check_nas_connection_task.delay()

print(f"任務 ID: {result.id}")
print(f"任務狀態: {result.status}")

# 等待任務完成
import time
for i in range(10):
    time.sleep(1)
    print(f"{i+1}s: {result.status}")
    if result.ready():
        print(f"結果: {result.result}")
        break

exit()
```

#### 步驟 4.2：在 Flower 中查看任務

```bash
# 1. 訪問 Flower
http://localhost:5555

# 2. 導航到 Tasks 頁面
# 3. 查找剛才執行的任務（按任務 ID）
# 4. 確認任務狀態、執行時間、結果等資訊
```

**檢查項目**：
- [ ] 任務是否出現在 Tasks 列表中
- [ ] 任務狀態是否正確（SUCCESS/FAILURE）
- [ ] 任務執行時間是否顯示
- [ ] 任務參數和結果是否顯示

#### 步驟 4.3：驗證所有 17 個定時任務

```bash
# 在 Flower 中導航到：
# Dashboard → Scheduled Tasks

# 應該看到所有 17 個定時任務：
# 1. sync-all-dhcp-logs-every-10-minutes
# 2. cleanup-old-dhcp-logs-daily
# 3. update-oui-database-monthly
# 4. check-nas-connection-every-5-minutes
# 5. check-all-ipxe-network-quality-every-5-minutes
# 6. sync-all-dhcp-scopes-daily
# 7. sync-all-dhcp-leases-every-15-minutes
# 8. auto-identify-switches-hourly
# 9. check-gitlab-connection-every-5-minutes
# 10. sync-jenkins-builds-every-10-minutes
# 10-1. sync-active-jenkins-builds-every-1-minute
# 11. auto-store-jenkins-workspaces-hourly
# 12. auto-store-jenkins-builds-every-hour
# 13. clean-expired-ansible-caches-daily
# 14. sync-jenkins-jobs-hourly
# 15. validate-jenkins-data-daily
# 16. cleanup-orphaned-jenkins-data-weekly
# 17. cleanup-old-jenkins-builds-monthly
```

**檢查項目**：
- [ ] 所有 17 個任務都可見
- [ ] 下次執行時間正確
- [ ] 任務配置參數正確

#### 步驟 4.4：查看 Worker 狀態

```bash
# 在 Flower 中導航到：
# Workers 頁面

# 檢查：
# - Worker 名稱
# - Worker 狀態（Online/Offline）
# - 當前執行的任務數
# - CPU 和記憶體使用率（如果可用）
```

**預期結果**：
- ✅ 至少看到 1 個 Worker（nt-celery-worker）
- ✅ Worker 狀態：Online
- ✅ 顯示 Worker 配置（concurrency: 8）

---

### 階段 5：配置 Nginx 反向代理（可選，10 分鐘）

**目的**：通過主域名訪問 Flower（http://localhost/flower/）

#### 步驟 5.1：更新 Nginx 配置

**文件**：`nginx/nginx.conf`

**添加 Flower 路由**（在 `location /api/` 之後）：
```nginx
server {
    listen 80;
    server_name localhost;

    # ... 現有配置 ...

    # 🆕 Flower 監控面板
    location /flower/ {
        proxy_pass http://celery_flower:5555/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket 支持（Flower 即時更新需要）
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        
        # 基本認證（如果需要在 Nginx 層面控制）
        # auth_basic "Flower Monitoring";
        # auth_basic_user_file /etc/nginx/.htpasswd;
    }

    # ... 其他配置 ...
}
```

#### 步驟 5.2：重啟 Nginx

```bash
# 1. 測試 Nginx 配置
docker exec nt-nginx nginx -t

# 2. 如果測試通過，重啟 Nginx
docker compose restart nginx

# 3. 訪問 Flower（通過 Nginx）
http://localhost/flower/
```

**注意**：如果使用 Nginx 反向代理，Flower 的基本認證仍然生效（雙重保護）。

---

## 📊 驗證檢查清單

### ✅ 基本功能驗證

- [ ] **服務狀態**
  - [ ] Flower 容器正常運行（`docker compose ps`）
  - [ ] 日誌無錯誤（`docker compose logs celery_flower`）
  - [ ] 端口正常監聽（5555）

- [ ] **Web UI 訪問**
  - [ ] 可以訪問 http://localhost:5555
  - [ ] 基本認證正常工作（需要輸入帳號密碼）
  - [ ] 所有頁面正常顯示（Dashboard, Tasks, Workers, Monitor）

- [ ] **任務監控**
  - [ ] Dashboard 顯示 Worker 狀態
  - [ ] Tasks 頁面顯示任務列表
  - [ ] 可以查看任務詳情（參數、結果、執行時間）
  - [ ] 可以過濾任務（成功/失敗/執行中）

- [ ] **定時任務**
  - [ ] 可以看到所有 17 個定時任務
  - [ ] 下次執行時間正確顯示
  - [ ] 任務歷史記錄可查看

### ✅ 進階功能驗證

- [ ] **數據持久化**
  - [ ] 重啟 Flower 後任務歷史仍然存在
  - [ ] Volume 正常掛載（`docker volume ls | grep flower`）

- [ ] **即時監控**
  - [ ] Monitor 頁面顯示即時任務執行圖表
  - [ ] WebSocket 連接正常（即時更新）

- [ ] **Worker 管理**
  - [ ] 可以查看 Worker 詳細資訊
  - [ ] 可以看到 Worker 的活躍任務
  - [ ] Worker 離線時會顯示（測試：停止 celery_worker）

### ✅ 效能指標

- [ ] **任務執行統計**
  - [ ] 任務成功率顯示正確
  - [ ] 任務執行時間統計正確
  - [ ] 任務失敗原因可追蹤

- [ ] **系統資源**
  - [ ] Flower 容器記憶體使用 < 200MB
  - [ ] Flower 容器 CPU 使用 < 5%
  - [ ] 不影響其他服務性能

---

## 🎯 Flower 使用指南

### 日常監控檢查（每日 5 分鐘）

**1. Dashboard 總覽**
```
訪問：http://localhost:5555

檢查項目：
✅ Worker 狀態：應該顯示 "Online"
✅ 任務成功率：應該 > 95%
✅ 當前執行任務：應該 < 5 個
✅ 失敗任務：應該 < 10 個/天
```

**2. Tasks 任務檢查**
```
導航：Tasks → Filter: Failed

檢查項目：
✅ 查看最近 24 小時的失敗任務
✅ 記錄失敗原因（點擊任務查看詳情）
✅ 確認是否需要手動重試
```

**3. Workers 狀態檢查**
```
導航：Workers

檢查項目：
✅ Worker 在線狀態
✅ 當前執行任務數
✅ Worker 負載（如果顯示）
```

### 問題排查流程

**問題 1：某個任務總是失敗**
```
步驟：
1. 導航到 Tasks 頁面
2. 過濾該任務名稱
3. 點擊失敗的任務查看詳情
4. 查看 Exception 欄位（錯誤訊息）
5. 查看 Traceback 欄位（完整堆疊）
6. 根據錯誤訊息修復代碼
7. 點擊 "Restart" 按鈕重試任務
```

**問題 2：Worker 離線**
```
步驟：
1. 導航到 Workers 頁面
2. 確認 Worker 狀態為 "Offline"
3. 執行：docker compose logs celery_worker --tail 50
4. 查找錯誤訊息
5. 重啟 Worker：docker compose restart celery_worker
6. 在 Flower 中確認 Worker 恢復在線
```

**問題 3：任務執行時間過長**
```
步驟：
1. 導航到 Tasks 頁面
2. 排序：按 Runtime 降序
3. 找出執行時間最長的任務
4. 點擊查看任務詳情
5. 分析任務參數和日誌
6. 優化任務代碼或調整參數
```

### 進階功能

**1. 手動執行任務**
```
步驟：
1. 導航到 Tasks 頁面
2. 點擊 "Execute Task" 按鈕
3. 選擇要執行的任務
4. 輸入任務參數（JSON 格式）
5. 點擊 "Execute" 執行
6. 在 Tasks 列表中查看執行結果
```

**2. 撤銷正在執行的任務**
```
步驟：
1. 導航到 Tasks 頁面
2. 找到正在執行的任務（State: RUNNING）
3. 點擊任務進入詳情頁
4. 點擊 "Revoke" 按鈕
5. 確認撤銷操作
6. 任務狀態變為 REVOKED
```

**3. 查看任務執行趨勢**
```
步驟：
1. 導航到 Monitor 頁面
2. 查看任務執行圖表（即時更新）
3. 觀察任務執行頻率和峰值
4. 根據趨勢調整任務排程
```

---

## 🔧 故障排查

### 問題：Flower 無法啟動

**診斷**：
```bash
# 查看詳細錯誤
docker compose logs celery_flower --tail 50

# 常見錯誤：
# 1. Redis 連接失敗
# 2. 端口衝突
# 3. 權限問題
```

**解決方案**：
```bash
# 1. 檢查 Redis 是否運行
docker compose ps redis

# 2. 檢查端口是否被佔用
sudo netstat -tlnp | grep 5555

# 3. 重啟 Flower
docker compose restart celery_flower

# 4. 如果仍然失敗，重建容器
docker compose up -d --force-recreate celery_flower
```

### 問題：看不到任務歷史

**診斷**：
```bash
# 檢查 Flower 配置
docker exec nt-celery-flower env | grep FLOWER

# 檢查 Volume 掛載
docker volume ls | grep flower
docker volume inspect network-toolbox_flower_data
```

**解決方案**：
```bash
# 1. 確認 FLOWER_PERSISTENT=True
# 2. 確認 Volume 已創建並掛載
# 3. 重啟 Flower
docker compose restart celery_flower

# 4. 手動執行一個任務測試
docker exec -it nt-django python manage.py shell -c "
from api.tasks import check_nas_connection_task
check_nas_connection_task.delay()
"

# 5. 在 Flower 中查看是否出現
```

### 問題：無法看到定時任務

**診斷**：
```bash
# 檢查 Celery Beat 是否運行
docker compose ps celery_beat

# 查看 Beat 日誌
docker compose logs celery_beat --tail 50
```

**解決方案**：
```bash
# 1. 重啟 Celery Beat
docker compose restart celery_beat

# 2. 確認 Beat 配置正確
docker exec -it nt-django python manage.py shell -c "
from network_toolbox.celery import app
print(len(app.conf.beat_schedule))
"
# 應該輸出：17

# 3. 在 Flower 中導航到 Broker 頁面
# 應該可以看到定時任務排程
```

---

## 📚 參考資源

- **Flower 官方文檔**：https://flower.readthedocs.io/
- **Flower GitHub**：https://github.com/mher/flower
- **Celery 事件文檔**：https://docs.celeryq.dev/en/stable/userguide/monitoring.html

---

## 🎯 下一步行動

完成本階段（Flower 監控）後，可以考慮：

1. **階段二**：部署 Prometheus + Grafana（長期數據分析）
2. **階段三**：配置 AlertManager（自動告警）
3. **優化任務**：根據 Flower 監控數據優化慢任務
4. **容量規劃**：根據 Worker 負載決定是否增加資源

---

**最後更新**：2025-11-25  
**狀態**：計畫已完成，待執行優化  
**預計時間**：30-45 分鐘  
**風險等級**：🟢 低（Flower 已存在，只需優化配置）

---

## 📋 快速執行檢查清單

### 最小化驗證（5 分鐘）

如果只是想快速驗證 Flower 是否正常工作：

```bash
# 1. 檢查服務狀態
docker compose ps celery_flower

# 2. 訪問 Web UI
curl http://localhost:5555

# 3. 執行測試任務
docker exec -it nt-django python manage.py shell -c "
from api.tasks import check_nas_connection_task
result = check_nas_connection_task.delay()
print(f'任務 ID: {result.id}')
"

# 4. 在 Flower 中查看任務
# http://localhost:5555/tasks
```

**如果以上都正常，Flower 已經可用！**

### 完整優化（30-45 分鐘）

如果需要添加認證、持久化等功能：

- [ ] 階段 1：驗證 Flower 是否正常運行（5 分鐘）
- [ ] 階段 2：添加基本認證（10 分鐘）
- [ ] 階段 3：完善 Celery 事件配置（10 分鐘）
- [ ] 階段 4：測試與驗證（15 分鐘）
- [ ] 階段 5：配置 Nginx 反向代理（可選，10 分鐘）

**總計**：30-45 分鐘
