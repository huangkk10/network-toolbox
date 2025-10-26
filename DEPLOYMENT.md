# Docker 部署完整指南

## 🚀 快速部署

### 使用啟動腳本（推薦）

```bash
# 一鍵啟動
./start.sh
```

這個腳本會自動完成：
1. 建構 Docker 映像
2. 啟動所有服務
3. 等待資料庫就緒
4. 執行資料庫遷移
5. 顯示訪問網址

### 手動部署

如果您想要手動控制每個步驟：

```bash
# 1. 建構映像
docker compose build

# 2. 啟動服務
docker compose up -d

# 3. 等待資料庫啟動（約10秒）
sleep 10

# 4. 執行遷移
docker compose exec django python manage.py migrate

# 5. 建立超級使用者
docker compose exec django python manage.py createsuperuser

# 6. 檢查服務狀態
docker compose ps
```

## 📦 容器架構

### 服務列表

| 服務名稱 | 容器名稱 | 端口 | 說明 |
|---------|---------|------|------|
| nginx | nt-nginx | 80 | Nginx 反向代理 |
| react | nt-react | 3000 | React 前端開發服務器 |
| django | nt-django | 8000 | Django API 後端 |
| postgres | nt-postgres | 5432 | PostgreSQL 資料庫 |
| adminer | nt-adminer | 9090 | 資料庫管理介面 |
| portainer | nt-portainer | 9000, 9443 | Docker 容器管理 |

### 網路架構

```
                    ┌─────────────────┐
                    │   瀏覽器訪問     │
                    │  localhost:80   │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │   nt-nginx      │
                    │   Port 80       │
                    └────────┬────────┘
                             │
              ┌──────────────┴──────────────┐
              │                             │
     ┌────────▼────────┐          ┌────────▼────────┐
     │   nt-react      │          │   nt-django     │
     │   Port 3000     │          │   Port 8000     │
     └─────────────────┘          └────────┬────────┘
                                           │
                                  ┌────────▼────────┐
                                  │  nt-postgres    │
                                  │   Port 5432     │
                                  └─────────────────┘
```

## 🔧 配置說明

### Docker Compose 配置

**docker-compose.yml** 主要配置項：

```yaml
services:
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: network_toolbox
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres123  # 生產環境請修改
      
  django:
    build: ./backend
    environment:
      DEBUG: 1  # 生產環境改為 0
      DB_HOST: postgres
      DB_NAME: network_toolbox
      
  react:
    build: ./frontend
    environment:
      CHOKIDAR_USEPOLLING: true  # Docker 環境熱重載
      
  nginx:
    build: ./nginx
    depends_on:
      - django
      - react
```

### Nginx 配置

**nginx/nginx.conf** 主要配置：

- `/api/` → Django 後端 (8000)
- `/admin/` → Django Admin (8000)
- `/` → React 前端 (3000)
- WebSocket 支援（React Hot Reload）

### Django 配置

**backend/network_toolbox/settings.py** 重要設定：

```python
# 資料庫連接
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'HOST': 'postgres',  # Docker 服務名
        'NAME': 'network_toolbox',
    }
}

# CORS 設定
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://localhost",
]
```

## 🌐 訪問服務

部署完成後，可以通過以下網址訪問：

### 主要服務
- **主網站**: http://localhost
- **API Root**: http://localhost/api/
- **Django Admin**: http://localhost/admin/

### 管理工具
- **Adminer** (資料庫管理): http://localhost:9090
  - 系統: PostgreSQL
  - 伺服器: postgres
  - 使用者: postgres
  - 密碼: postgres123
  - 資料庫: network_toolbox

- **Portainer** (容器管理): http://localhost:9000
  - 首次訪問需設定管理員密碼

## 📊 服務管理

### 啟動/停止服務

```bash
# 啟動所有服務
docker compose up -d

# 停止所有服務
docker compose down

# 停止所有服務並刪除數據
docker compose down -v
```

### 查看服務狀態

```bash
# 查看所有服務狀態
docker compose ps

# 查看特定服務狀態
docker compose ps django
```

### 查看日誌

```bash
# 查看所有服務日誌
docker compose logs -f

# 查看特定服務日誌
docker compose logs -f django
docker compose logs -f nginx
docker compose logs -f react

# 查看最近100行日誌
docker compose logs --tail=100 django
```

### 重啟服務

```bash
# 重啟特定服務
docker compose restart django
docker compose restart nginx

# 重啟所有服務
docker compose restart
```

## 🔍 除錯與監控

### 進入容器

```bash
# 進入 Django 容器
docker compose exec django bash

# 進入 React 容器
docker compose exec react sh

# 進入 PostgreSQL 容器
docker compose exec postgres bash
```

### 執行 Django 命令

```bash
# Django Shell
docker compose exec django python manage.py shell

# 檢查配置
docker compose exec django python manage.py check

# 查看遷移狀態
docker compose exec django python manage.py showmigrations

# 建立超級使用者
docker compose exec django python manage.py createsuperuser
```

### 資料庫操作

```bash
# 連接到 PostgreSQL
docker compose exec postgres psql -U postgres -d network_toolbox

# 查看資料庫列表
docker compose exec postgres psql -U postgres -c "\l"

# 查看表格列表
docker compose exec postgres psql -U postgres -d network_toolbox -c "\dt"
```

## 🛠️ 常見問題

### 1. 端口衝突

**問題**: 端口已被佔用

**解決**:
```bash
# 查看端口使用情況
sudo netstat -tulpn | grep :80
sudo netstat -tulpn | grep :5432

# 修改 docker-compose.yml 中的端口映射
ports:
  - "8080:80"  # 將 80 改為 8080
```

### 2. 容器無法啟動

**問題**: 服務啟動失敗

**解決**:
```bash
# 查看詳細錯誤訊息
docker compose logs [service_name]

# 重建容器
docker compose down
docker compose up -d --build
```

### 3. 資料庫連接失敗

**問題**: Django 無法連接到 PostgreSQL

**解決**:
```bash
# 確認 PostgreSQL 容器運行
docker compose ps postgres

# 檢查資料庫日誌
docker compose logs postgres

# 測試連接
docker compose exec django python manage.py check --database default
```

### 4. 前端無法訪問 API

**問題**: API 請求失敗 (CORS 錯誤)

**解決**:
1. 檢查 Nginx 配置是否正確
2. 確認 Django CORS 設定
3. 查看瀏覽器開發者工具的 Network 標籤
4. 檢查 Nginx 日誌

```bash
docker compose logs nginx
```

### 5. 熱重載不工作

**問題**: 修改代碼後沒有自動重載

**解決**:
- **前端**: 確認 `CHOKIDAR_USEPOLLING=true` 已設定
- **後端**: Django 開發服務器應該自動重載
- 檢查 volume 掛載是否正確

## 🔒 安全性建議

### 生產環境部署

1. **修改預設密碼**
   ```bash
   # 在 docker-compose.yml 中修改
   POSTGRES_PASSWORD: <強密碼>
   ```

2. **設定 Django SECRET_KEY**
   ```bash
   # 在 backend/.env 中設定
   SECRET_KEY=<隨機生成的密鑰>
   DEBUG=False
   ```

3. **配置 HTTPS**
   - 使用 Let's Encrypt 獲取 SSL 憑證
   - 更新 Nginx 配置支援 HTTPS

4. **限制外部訪問**
   ```yaml
   # 只允許本地訪問資料庫
   postgres:
     ports:
       - "127.0.0.1:5432:5432"
   ```

5. **設定防火牆規則**
   ```bash
   # 只允許特定 IP 訪問
   sudo ufw allow from <IP地址> to any port 80
   ```

## 📈 效能優化

### 生產環境建議

1. **使用 Gunicorn**
   ```dockerfile
   # backend/Dockerfile 修改
   CMD ["gunicorn", "--bind", "0.0.0.0:8000", "network_toolbox.wsgi:application"]
   ```

2. **React 建構優化**
   ```dockerfile
   # 使用多階段建構
   FROM node:18-alpine as build
   # ... 建構步驟
   
   FROM nginx:alpine
   COPY --from=build /app/build /usr/share/nginx/html
   ```

3. **設定資源限制**
   ```yaml
   django:
     deploy:
       resources:
         limits:
           memory: 512M
           cpus: '0.5'
   ```

## 🔄 更新與維護

### 更新應用

```bash
# 1. 拉取最新代碼
git pull

# 2. 重建容器
docker compose down
docker compose up -d --build

# 3. 執行遷移
docker compose exec django python manage.py migrate
```

### 備份

```bash
# 備份資料庫
docker compose exec postgres pg_dump -U postgres network_toolbox > backup_$(date +%Y%m%d).sql

# 備份 volumes
docker run --rm -v nt_postgres_data:/data -v $(pwd):/backup ubuntu tar czf /backup/postgres_data_backup.tar.gz /data
```

### 還原

```bash
# 還原資料庫
cat backup_20250120.sql | docker compose exec -T postgres psql -U postgres network_toolbox
```

## 📚 相關文檔

- [README.md](README.md) - 專案概述
- [DEVELOPMENT.md](DEVELOPMENT.md) - 開發指南
- [Docker 官方文檔](https://docs.docker.com/)
- [Docker Compose 文檔](https://docs.docker.com/compose/)

---

**維護者**: Kevin Huang  
**最後更新**: 2025-01-XX
