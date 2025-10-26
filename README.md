# NT Network Toolbox

**DHCP Server Management Platform**

一個現代化的 DHCP 服務器監控和管理平台，提供直觀的界面來管理多台 DHCP 服務器。

## 🌟 特色功能

- 📊 **Dashboard** - 系統概覽，一目了然查看所有 DHCP 服務器狀態
- 📈 **# Network Toolbox - DHCP Server 分析管理平台

基於 Docker 的網路工具箱，專注於 DHCP Server 分析與管理。

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

### 使用指令列

```bash
# 連接到 PostgreSQL
docker compose exec postgres psql -U postgres -d network_toolbox

# 備份資料庫
docker compose exec postgres pg_dump -U postgres network_toolbox > backup.sql

# 還原資料庫
cat backup.sql | docker compose exec -T postgres psql -U postgres network_toolbox
```

## 🔒 安全性考量

### 生產環境建議

1. **修改預設密碼**
   - 資料庫密碼
   - Django SECRET_KEY
   - 管理員密碼

2. **設定環境變數**
   - 使用 `.env` 檔案
   - 不要提交敏感資訊到版本控制

3. **HTTPS 配置**
   - 使用 SSL 憑證
   - 配置 Nginx HTTPS

4. **防火牆規則**
   - 限制資料庫端口訪問
   - 設定 IP 白名單

## 📝 環境變數

複製 `.env.example` 為 `.env` 並修改相關設定：

```bash
cp backend/.env.example backend/.env
```

主要環境變數：
- `SECRET_KEY`: Django 密鑰
- `DEBUG`: 除錯模式（生產環境設為 False）
- `DB_PASSWORD`: 資料庫密碼
- `ALLOWED_HOSTS`: 允許的主機名稱

## 🐛 故障排除

### 容器無法啟動

```bash
# 檢查容器狀態
docker compose ps

# 查看錯誤日誌
docker compose logs [service_name]

# 重建容器
docker compose up -d --build
```

### 資料庫連線失敗

```bash
# 確認資料庫容器運行
docker compose ps postgres

# 檢查資料庫日誌
docker compose logs postgres

# 測試連線
docker compose exec django python manage.py check --database default
```

### 前端無法連接後端

1. 檢查 Nginx 配置
2. 確認 CORS 設定
3. 驗證 API 端點

## 📚 相關資源

- [Django 官方文件](https://docs.djangoproject.com/)
- [React 官方文件](https://react.dev/)
- [Docker Compose 參考](https://docs.docker.com/compose/)
- [PostgreSQL 文件](https://www.postgresql.org/docs/)

## 📄 授權

此專案採用 MIT 授權條款。

## 👨‍💻 維護者

Kevin Huang

---

**版本**: 1.0.0  
**最後更新**: 2025-01-XX** - 詳細的租約統計、趨勢分析和 IP 分佈
- 🖥️ **DHCP Server 管理** - 新增、編輯、刪除 DHCP 服務器配置
- 👤 **用戶管理** - 系統用戶和權限管理
- ⚙️ **系統設定** - 告警閾值、同步設定等

## 🎨 設計風格

- **明亮簡約風格** - 純白背景 + 藍色主題
- **響應式設計** - 支援桌面、平板、手機
- **Material Design** - 遵循 Google Material Design 規範

## 🏗️ 技術架構

### 前端
- **React 18.2** - UI 框架
- **Ant Design 5.x** - UI 組件庫
- **React Router 6** - 路由管理
- **Axios** - HTTP 客戶端
- **Recharts** - 圖表庫

### 後端
- **Django 4.x** - Web 框架
- **Django REST Framework** - API 框架
- **PostgreSQL** - 數據庫
- **Celery** - 異步任務隊列

## 📁 項目結構

```
network-toolbox/
├── frontend/                 # React 前端
│   ├── src/
│   │   ├── components/       # 可重用組件
│   │   │   ├── Sidebar.js    # 側邊欄 (明亮風格)
│   │   │   └── TopHeader.js  # 頂部導航欄
│   │   ├── pages/            # 頁面組件
│   │   │   ├── DashboardPage.js
│   │   │   ├── DHCPAnalyticsPage.js
│   │   │   ├── DHCPServerManagementPage.js
│   │   │   ├── UserManagementPage.js
│   │   │   └── SettingsPage.js
│   │   ├── contexts/         # React Context
│   │   │   └── AuthContext.js
│   │   ├── config/           # 配置文件
│   │   └── App.js            # 主應用組件
│   ├── public/
│   └── package.json
│
├── backend/                  # Django 後端
│   ├── api/                  # API 應用
│   └── network_toolbox/      # Django 項目設定
│
└── library/                  # 共享庫
    └── dhcp_analytics/       # DHCP 分析庫
```

## 🚀 快速開始

### 前端開發

```bash
cd frontend
npm install
npm start
```

應用將在 http://localhost:3000 啟動

### 後端開發

```bash
cd backend
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

API 將在 http://localhost:8000 啟動

## 🎨 配色方案

```css
--primary-color: #2196f3;        /* 藍色 - 主題色 */
--secondary-color: #1976d2;      /* 深藍 - 強調色 */
--success-color: #52c41a;        /* 綠色 - 成功 */
--warning-color: #ff9800;        /* 橙色 - 警告 */
--error-color: #f44336;          /* 紅色 - 錯誤 */

--bg-primary: #ffffff;           /* 白色 - 主背景 */
--bg-secondary: #f5f5f5;         /* 淺灰 - 次背景 */
--bg-sidebar: #ffffff;           /* 白色 - 側邊欄 */

--text-primary: #37474f;         /* 深灰 - 主文字 */
--text-secondary: #757575;       /* 中灰 - 次文字 */
--text-light: #9e9e9e;           /* 淡灰 - 輔助文字 */

--border-color: #e0e0e0;         /* 邊框色 */
```

## 📝 開發計劃

- [x] 項目架構設計
- [x] 前端基礎組件 (Sidebar, TopHeader)
- [x] Dashboard 頁面
- [ ] DHCP Analytics 頁面完整實現
- [ ] DHCP Server Management 頁面
- [ ] 後端 API 開發
- [ ] 數據庫模型設計
- [ ] 實時數據同步
- [ ] Docker 部署配置

## 👥 作者

huangkk10

## 📄 授權

MIT License
