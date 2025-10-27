# Network Toolbox - DHCP Server 管理平台

**基於 Docker 的 DHCP 服務器監控和管理平台**

一個現代化的 DHCP 服務器分析與管理工具，提供直觀的 Web 界面來監控和管理多台 DHCP 服務器。

---

## 🌟 主要功能

- 📊 **Dashboard** - 系統概覽，實時監控所有 DHCP 服務器狀態
- 📈 **DHCP 分析** - 詳細的租約統計、趨勢分析、IP 分佈、實時日誌
- 🖥️ **Server 管理** - DHCP 服務器的 CRUD 操作和配置
- 👤 **用戶管理** - 系統用戶和權限管理
- ⚙️ **系統設定** - 告警閾值、同步設定等

## 🚀 快速開始

**5 分鐘快速部署**：

```bash
# 1. 啟動所有服務
docker compose up -d

# 2. 初始化資料庫
docker exec nt-django python manage.py migrate

# 3. 創建管理員
docker exec -it nt-django python manage.py createsuperuser

# 4. 訪問系統
# 打開瀏覽器：http://localhost
```

📚 **詳細指南**：查看 [快速開始文檔](docs/quickstart/QUICKSTART.md)

---

## 📚 文檔導覽

### 🎯 新手入門
- **[快速開始指南](docs/quickstart/QUICKSTART.md)** - 5 分鐘快速部署
- **[日誌功能快速開始](docs/quickstart/LOGS_QUICKSTART.md)** - 日誌查看功能上手

### 👨‍💻 開發人員
- **[開發指南](docs/development/DEVELOPMENT.md)** - 開發環境設置和規範
- **[真實數據轉換報告](docs/development/REAL_DATA_CONVERSION_REPORT.md)** - 從假數據到真實 API 的轉換過程

### 🚢 運維人員
- **[部署指南](docs/deployment/DEPLOYMENT.md)** - 生產環境部署步驟

### 📖 功能文檔
- **[LogsTab 使用指南](docs/features/LOGS_TAB_USAGE.md)** - 日誌查看功能使用說明
- **[日誌文件說明](docs/features/LOG_FILES_EXPLAINED.md)** - 日誌配置和維護
- **[DHCP SSH 集成](docs/features/DHCP_SSH_INTEGRATION.md)** - SSH 連接實作
- **[日誌 API 實作](docs/features/LOGS_API_IMPLEMENTATION.md)** - 日誌 API 技術細節
- **[日誌功能完成報告](docs/features/LOGS_IMPLEMENTATION_COMPLETE.md)** - 完整實作總結

### 🔌 API 文檔
- **[API 測試報告](docs/api/API_TEST_REPORT.md)** - 所有 API 端點測試結果

📂 **完整文檔目錄**：查看 [docs/README.md](docs/README.md)

---

## 🏗️ 系統架構

```
┌─────────────────┐    ┌──────────────┐    ┌─────────────────┐    ┌──────────────┐
│   瀏覽器客戶端    │    │    Nginx     │    │  React Frontend │    │   Django     │
│                 │◄──►│  Port 80     │◄──►│   Port 3000     │◄──►│  Backend     │
│   User Interface│    │ Reverse Proxy│    │  Development    │    │  Port 8000   │
└─────────────────┘    └──────────────┘    └─────────────────┘    └──────────────┘
                                                                           │
                                                                           ▼
                                                                   ┌──────────────┐
                                                                   │ PostgreSQL   │
                                                                   │  Port 5432   │
                                                                   └──────────────┘
```

## 📦 容器服務

- **nt-nginx**: Nginx 反向代理 (Port 80)
- **nt-react**: React 前端開發服務器 (Port 3000)
- **nt-django**: Django API 後端 (Port 8000)
- **nt-postgres**: PostgreSQL 資料庫 (Port 5432)
- **nt-adminer**: 資料庫管理介面 (Port 9090)
- **nt-portainer**: Docker 容器管理 (Port 9000/9443)

## 🚀 快速開始

### 前置需求

- Docker 20.10+
- Docker Compose v2

### 啟動服務

```bash
# 1. 啟動所有服務
docker compose up -d

# 2. 檢查服務狀態
docker compose ps

# 3. 查看日誌
docker compose logs -f
```

### 初次設置

```bash
# 1. 進入 Django 容器
docker compose exec django bash

# 2. 執行資料庫遷移
python manage.py migrate

# 3. 建立超級使用者
python manage.py createsuperuser

# 4. 收集靜態檔案（生產環境）
python manage.py collectstatic --noinput
```

## 🌐 訪問網址

- **主要網站**: http://localhost
- **API 文檔**: http://localhost/api/
- **管理後台**: http://localhost/admin/
- **資料庫管理**: http://localhost:9090
- **容器管理**: http://localhost:9000

## 📁 專案結構

```
network-toolbox/
├── frontend/                 # React 前端
│   ├── src/
│   │   ├── components/      # UI 組件
│   │   ├── pages/          # 頁面組件
│   │   └── contexts/       # Context 提供者
│   ├── public/
│   ├── package.json
│   └── Dockerfile
│
├── backend/                 # Django 後端
│   ├── api/                # API 應用
│   ├── network_toolbox/    # 主要設定
│   ├── requirements.txt
│   └── Dockerfile
│
├── nginx/                   # Nginx 配置
│   ├── nginx.conf
│   └── Dockerfile
│
├── library/                 # 共享程式庫
│
└── docker-compose.yml       # Docker Compose 配置
```

## 🛠️ 常用命令

### Docker Compose

```bash
# 啟動服務
docker compose up -d

# 停止服務
docker compose down

# 重啟服務
docker compose restart

# 查看日誌
docker compose logs -f [service_name]

# 進入容器
docker compose exec [service_name] bash
```

### Django 管理

```bash
# 執行遷移
docker compose exec django python manage.py migrate

# 建立遷移檔案
docker compose exec django python manage.py makemigrations

# 建立超級使用者
docker compose exec django python manage.py createsuperuser

# Django Shell
docker compose exec django python manage.py shell
```

### 前端開發

```bash
# 進入前端容器
docker compose exec react sh

# 安裝新套件
docker compose exec react npm install [package_name]

# 查看 React 日誌
docker compose logs -f react
```

## 🔧 開發環境

### 熱重載

- **前端**: React 自動熱重載（透過 CHOKIDAR_USEPOLLING）
- **後端**: Django 開發服務器自動重載

### 除錯

```bash
# 查看 Django 錯誤
docker compose logs -f django

# 查看 Nginx 錯誤
docker compose logs -f nginx

# 查看 React 錯誤
docker compose logs -f react
```

## 📊 資料庫管理

### 使用 Adminer

1. 訪問 http://localhost:9090
2. 輸入連線資訊：
   - **系統**: PostgreSQL
   - **伺服器**: postgres
   - **使用者**: postgres
   - **密碼**: postgres123
   - **資料庫**: network_toolbox

---

## � 文檔索引

完整文檔請查看 [docs/](docs/) 目錄：

```
docs/
├── quickstart/          # 快速開始指南
├── development/         # 開發文檔
├── deployment/          # 部署文檔
├── features/            # 功能實作文檔
└── api/                 # API 文檔
```

---

## �‍💻 維護者

**Network Toolbox Team**

## 📄 授權

MIT License

---

**版本**: 1.0.0  
**最後更新**: 2025-10-27
