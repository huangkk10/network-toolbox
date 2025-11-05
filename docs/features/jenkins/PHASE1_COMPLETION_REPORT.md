# Phase 1: 環境準備與基礎設施 - 完成報告

## 📋 任務概述

**目標**：設置 PostgreSQL 和 Redis 容器，配置 Docker Compose，建立基礎環境變數

**完成日期**：2025-11-04

---

## ✅ 已完成的任務

### 1. PostgreSQL 容器配置
- ✅ PostgreSQL 15 容器已存在於 `docker-compose.yml`
- ✅ 資料庫名稱：`network_toolbox`
- ✅ 端口：5432
- ✅ 健康檢查已配置
- ✅ 數據持久化：使用 `postgres_data` volume

### 2. Redis 容器配置
- ✅ Redis 7 容器已存在於 `docker-compose.yml`
- ✅ 端口：6379
- ✅ 數據持久化：使用 `redis_data` volume，啟用 AOF
- ✅ 健康檢查已配置

### 3. Django 容器環境變數更新
**新增的環境變數**：
```yaml
- REDIS_HOST=redis
- REDIS_PORT=6379
- REDIS_DB=0
- NAS_MOUNT_PATH=/mnt/mdt
```

**NAS 掛載準備**（已註釋，待確認實際路徑）：
```yaml
# - /mnt/mdt:/mnt/mdt:ro
```

### 4. Python 依賴套件更新
**在 `requirements.txt` 中新增**：
- `django-redis>=5.4.0` - Django Redis 緩存後端
- `beautifulsoup4>=4.12.0` - HTML 解析（Jenkins API）
- `lxml>=4.9.0` - XML/HTML 解析器

### 5. Django Settings 配置

#### Redis 緩存配置
```python
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': f'redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'CONNECTION_POOL_KWARGS': {
                'max_connections': 50,
                'retry_on_timeout': True,
            },
            'SOCKET_CONNECT_TIMEOUT': 5,
            'SOCKET_TIMEOUT': 5,
            'COMPRESSOR': 'django_redis.compressors.zlib.ZlibCompressor',
            'IGNORE_EXCEPTIONS': True,
        },
        'KEY_PREFIX': 'nt',
        'TIMEOUT': 3600,
    }
}
```

#### Session 配置
```python
SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
SESSION_CACHE_ALIAS = 'default'
```

#### Jenkins 整合配置
```python
NAS_MOUNT_PATH = config('NAS_MOUNT_PATH', default='/mnt/mdt')
JENKINS_STORAGE_BASE_PATH = os.path.join(NAS_MOUNT_PATH, 'jenkins_test_storage')
JENKINS_CONFIG_CACHE_TTL = 1800  # 30 分鐘
JENKINS_LOG_CACHE_TTL = 3600  # 1 小時
JENKINS_DB_QUERY_CACHE_TTL = 300  # 5 分鐘
JENKINS_API_TIMEOUT = 30
JENKINS_API_RETRY_TIMES = 3
```

### 6. 環境變數示例文件更新
更新 `backend/.env.example`，新增：
- Redis 連接配置
- NAS 掛載路徑
- Jenkins API 配置（可選）

---

## 🔧 部署與驗證

### 安裝新的依賴套件

```bash
# 方式 1：進入容器後安裝
docker exec -it nt-django bash
pip install -r requirements.txt

# 方式 2：重建 Django 容器
docker compose up -d --build django
```

### 驗證 Redis 連接

```bash
# 1. 測試 Redis 容器
docker exec -it nt-redis redis-cli ping
# 應該返回：PONG

# 2. 進入 Django Shell 測試緩存
docker exec -it nt-django python manage.py shell

# 在 Shell 中執行：
from django.core.cache import cache
cache.set('test_key', 'Hello Redis!', 60)
print(cache.get('test_key'))
# 應該輸出：Hello Redis!
```

### 驗證環境變數

```bash
docker exec nt-django env | grep -E "(REDIS|NAS)"
```

預期輸出：
```
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_DB=0
NAS_MOUNT_PATH=/mnt/mdt
```

---

## ⚠️ 待確認項目

### NAS 掛載配置
**目前狀態**：已在 `docker-compose.yml` 中準備掛載配置（已註釋）

**需要確認**：
1. 本機是否已經將 NAS 掛載到 `/mnt/mdt`？
2. 掛載點權限是否正確（容器內可讀）？
3. Jenkins 日誌存儲路徑是否為 `/mnt/mdt/jenkins_test_storage/`？

**啟用方式**：
如果確認上述條件，取消 `docker-compose.yml` 中的註釋：
```yaml
volumes:
  # ...其他 volume
  - /mnt/mdt:/mnt/mdt:ro  # 取消這行註釋
```

然後重啟容器：
```bash
docker compose down
docker compose up -d
```

**驗證掛載**：
```bash
# 檢查容器內是否能訪問 NAS
docker exec nt-django ls -la /mnt/mdt/
```

---

## 📊 配置參數說明

### Redis 緩存策略

| 配置項 | 值 | 說明 |
|--------|-----|------|
| `max_connections` | 50 | 連接池最大連接數 |
| `SOCKET_TIMEOUT` | 5s | Socket 超時時間 |
| `KEY_PREFIX` | `nt` | 緩存鍵前綴（避免衝突）|
| `TIMEOUT` | 3600s | 默認過期時間（1 小時）|
| `IGNORE_EXCEPTIONS` | True | 緩存失敗不影響主功能 |

### Jenkins 緩存時間

| 類型 | TTL | 說明 |
|------|-----|------|
| 配置文件 | 30 分鐘 | Ansible config 等靜態數據 |
| 日誌文件 | 1 小時 | Console logs |
| 資料庫查詢 | 5 分鐘 | Build 列表、統計數據 |

---

## 🎯 下一步

**Phase 1 已完成！** 可以開始 **Phase 2: Django 模型設計與遷移**

### Phase 2 預計任務：
1. 創建 `JenkinsServer` 模型
2. 創建 `JenkinsJob` 模型
3. 創建 `JenkinsBuild` 模型（含 JSONField 存儲配置）
4. 執行資料庫遷移
5. 在 Django Admin 註冊模型

---

## 📝 變更記錄

### 修改的文件
1. `docker-compose.yml` - 添加 Redis 環境變數和 NAS 掛載準備
2. `backend/requirements.txt` - 添加 `django-redis`, `beautifulsoup4`, `lxml`
3. `backend/network_toolbox/settings.py` - 添加 Redis 緩存配置和 Jenkins 配置
4. `backend/.env.example` - 添加 Redis 和 NAS 環境變數

### 新增的文件
- 無（本 Phase 主要是配置修改）

---

## 🔍 問題排查

### 問題 1：pip 安裝失敗
**解決方式**：重建容器
```bash
docker compose up -d --build django
```

### 問題 2：Redis 連接超時
**檢查**：
```bash
docker compose logs redis
docker exec nt-django ping -c 3 redis
```

### 問題 3：NAS 掛載權限問題
**解決方式**：調整本機掛載點權限
```bash
sudo chmod -R 755 /mnt/mdt/jenkins_test_storage
```

---

**完成者**：GitHub Copilot  
**審查者**：待審查  
**狀態**：✅ 完成，等待驗證
