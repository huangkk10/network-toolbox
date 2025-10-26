# Network Toolbox - AI 開發指導說明

## 🐳 重要：Docker 容器架構

### 本專案使用完整的 Docker Container 架構部署

**所有服務都在 Docker 容器中運行：**

```yaml
服務架構：
┌─────────────────────────────────────────┐
│  nginx (nt-nginx)        Port: 80       │  ← 反向代理
│  ├── / → React (3000)                   │
│  └── /api/ → Django (8000)              │
└─────────────────────────────────────────┘
┌─────────────────────────────────────────┐
│  React (nt-react)        Port: 3000     │  ← 前端服務
│  - 開發服務器模式                        │
│  - 熱重載啟用                            │
└─────────────────────────────────────────┘
┌─────────────────────────────────────────┐
│  Django (nt-django)      Port: 8000     │  ← 後端服務
│  - 連接到本機 PostgreSQL                 │
│  - 使用 host.docker.internal            │
│  - 日誌掛載到主機                        │
└─────────────────────────────────────────┘
┌─────────────────────────────────────────┐
│  Adminer (nt-adminer)    Port: 9090     │  ← 資料庫管理
│  - Host 網路模式                         │
│  - 可訪問本機 PostgreSQL                 │
└─────────────────────────────────────────┘
┌─────────────────────────────────────────┐
│  PostgreSQL (本機運行，非容器)            │  ← 資料庫
│  - Port: 5432 (本機)                     │
│  - 避免端口衝突                          │
└─────────────────────────────────────────┘
```

### Docker Compose 配置要點

1. **Volume 掛載**：
   - `./backend:/app` - 後端代碼掛載（熱重載）
   - `./frontend:/app` - 前端代碼掛載（熱重載）
   - `./logs:/app/logs` - **日誌目錄掛載（重要）**
   - `./library:/app/library` - 共用函式庫
   - `static_files:/app/static` - 靜態檔案
   - `media_files:/app/media` - 媒體檔案

2. **網路配置**：
   - 自訂網路：`nt_network`
   - Django 使用 `host.docker.internal` 連接本機 PostgreSQL
   - Adminer 使用 `network_mode: "host"` 訪問本機資料庫

3. **環境變數**：
   ```
   DB_HOST=host.docker.internal
   DB_PORT=5432
   DB_NAME=network_toolbox
   TZ=Asia/Taipei
   ```

## 📊 後端日誌系統

### 日誌存放位置

**主機路徑（開發時查看）：**
```bash
./logs/                          # 專案根目錄的 logs 資料夾
├── django.log                   # 一般應用程式日誌（保留 30 天）
├── django_error.log             # 錯誤日誌（保留 60 天）
├── dhcp_operations.log          # DHCP 操作記錄（保留 15 天）
├── api_access.log               # API 訪問記錄（保留 7 天）
├── django.log.2025-10-26        # 舊日誌（按日期輪替）
└── README.md                    # 日誌使用說明
```

**容器內路徑：**
```bash
/app/logs/                       # Django 容器內的路徑
```

**透過 Volume 掛載實現：**
```yaml
# docker-compose.yml
volumes:
  - ./logs:/app/logs             # 主機 ./logs 對應容器 /app/logs
```

### 日誌配置詳情

**Django settings.py 日誌配置：**
- **輪替機制**：TimedRotatingFileHandler（每天午夜輪替）
- **日誌格式**：
  - Verbose：`[級別] 時間 | 模組 | 函數 | 行號 | 訊息`
  - Simple：`[級別] 時間 模組: 訊息`
  - Detailed：包含 PID 和 Thread ID

**日誌級別分佈：**
- `django.log` - INFO 以上所有訊息
- `django_error.log` - ERROR 和 CRITICAL（保留更久）
- `dhcp_operations.log` - DHCP 相關操作（api.services）
- `api_access.log` - API 請求記錄（django.request）

### 查看日誌的方式

**1. 直接查看主機檔案：**
```bash
# 即時查看
tail -f logs/django.log

# 查看錯誤
tail -f logs/django_error.log

# 搜尋特定內容
grep "ERROR" logs/django.log
```

**2. 使用分析腳本：**
```bash
./scripts/analyze_logs.sh        # 生成完整分析報告
./scripts/clean_old_logs.sh 30   # 清理 30 天前的日誌
```

**3. 從容器內查看：**
```bash
docker exec nt-django tail -f /app/logs/django.log
docker exec nt-django ls -la /app/logs/
```

**4. 查看容器標準輸出：**
```bash
docker compose logs django -f     # 查看容器 stdout
docker compose logs nginx -f      # 查看 nginx 日誌
```

### 日誌自動管理

- ✅ **自動輪替**：每天午夜自動輪替，舊檔案加上日期後綴
- ✅ **自動清理**：超過保留天數的日誌自動刪除
- ✅ **持久化**：日誌存在主機，容器重啟不會丟失
- ✅ **即時同步**：容器寫入的日誌立即出現在主機

## 專案概述

Network Toolbox 是一個 DHCP 伺服器管理平台，採用前後端分離架構：
- **前端**：React 18.2 + Ant Design 5.x（純白極簡風格）
- **後端**：Django 4.2 + Django REST Framework
- **資料庫**：PostgreSQL（本機，非 Docker 容器）
- **部署**：Docker Compose（完整容器化）
- **反向代理**：Nginx

## 開發工作流程

### 啟動開發環境

```bash
# 1. 確保本機 PostgreSQL 正在運行
sudo systemctl status postgresql

# 2. 啟動所有 Docker 服務
docker compose up -d

# 3. 查看服務狀態
docker compose ps

# 4. 查看日誌
docker compose logs -f
```

### 訪問服務

- **前端**：http://localhost
- **API**：http://localhost/api/
- **Django Admin**：http://localhost/admin/
- **Adminer**：http://localhost:9090

### 開發時的熱重載

- **前端**：修改 `frontend/src/` 下的檔案會自動重載
- **後端**：修改 `backend/` 下的檔案，Django 會自動重啟
- **日誌**：即時寫入 `./logs/` 目錄

### 常用 Docker 命令

```bash
# 重啟服務
docker compose restart django
docker compose restart react
docker compose restart nginx

# 查看日誌
docker compose logs django --tail 50
docker compose logs -f                  # 所有服務

# 進入容器
docker exec -it nt-django bash
docker exec -it nt-react sh

# 執行 Django 命令
docker exec nt-django python manage.py migrate
docker exec nt-django python manage.py createsuperuser
docker exec nt-django python manage.py makemigrations

# 重建容器
docker compose up -d --build django
docker compose up -d --build react
```

## 設計風格指南

### 前端 UI 設計
- **主題**：純白極簡風格
- **背景色**：#ffffff（純白）
- **主色調**：#2196f3（藍色）
- **側邊欄**：白色背景，藍色選中高亮
- **品牌名稱**：NT（Network Toolbox）

### 代碼風格
- **前端**：函數式組件 + Hooks，Ant Design，axios，React Router v6
- **後端**：ViewSet，RESTful API，詳細日誌記錄

## 數據模型

現有模型：
- `DHCPServer`：DHCP 伺服器資訊
- `DHCPLease`：DHCP 租約記錄
- `User`：Django 內建 User 模型

## 開發指導原則

### 添加新功能時

1. **前端頁面**：
   - 在 `frontend/src/pages/` 創建
   - 更新 `App.js` 路由
   - 更新 `Sidebar.js` 菜單

2. **後端 API**：
   - `models.py` 定義模型
   - `serializers.py` 創建序列化器
   - `views.py` 創建 ViewSet
   - `urls.py` 註冊路由
   - 執行遷移

3. **日誌記錄**：
   ```python
   import logging
   logger = logging.getLogger(__name__)
   
   logger.info('操作成功')
   logger.error('發生錯誤', exc_info=True)
   ```

### API 開發規範

- 使用 ViewSet
- 禁用分頁：`pagination_class = None`
- 開發環境：`AllowAny`
- 生產環境：`IsAuthenticated`

### 錯誤處理

- try-except 捕獲異常
- 記錄到日誌（包含 stack trace）
- 返回友好錯誤訊息
- 前端使用 Ant Design message 提示

## 故障排查

### 容器無法啟動

```bash
# 查看詳細錯誤
docker compose logs django

# 檢查端口佔用
sudo netstat -tlnp | grep :80
sudo netstat -tlnp | grep :8000

# 重建容器
docker compose down
docker compose up -d --build
```

### 資料庫連接失敗

```bash
# 檢查本機 PostgreSQL
sudo systemctl status postgresql

# 測試連接
docker exec nt-django python manage.py dbshell

# 查看環境變數
docker exec nt-django env | grep DB_
```

### 日誌未生成

```bash
# 檢查容器內目錄
docker exec nt-django ls -la /app/logs/

# 檢查掛載
docker inspect nt-django | grep -A 10 Mounts

# 檢查權限
ls -la logs/
```

### 前端無法訪問 API

```bash
# 檢查 Nginx 配置
docker exec nt-nginx nginx -t

# 查看 Nginx 日誌
docker compose logs nginx

# 測試 API
curl http://localhost/api/
```

## 命名規範

- **檔案**：PascalCase（React）、snake_case（Python）
- **組件**：PascalCase
- **函數**：camelCase（JS）、snake_case（Python）
- **變數**：camelCase（JS）、snake_case（Python）
- **API 端點**：kebab-case

## 相關資源

- Django：https://docs.djangoproject.com/
- DRF：https://www.django-rest-framework.org/
- React：https://react.dev/
- Ant Design：https://ant.design/
- Docker Compose：https://docs.docker.com/compose/

---

**最後更新**：2025-10-27  
**維護者**：Network Toolbox Team  
**架構**：完整 Docker 容器化部署
