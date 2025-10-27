# Network Toolbox 開發指南

## 📋 目錄

- [專案概述](#專案概述)
- [技術棧](#技術棧)
- [專案結構](#專案結構)
- [開發環境設置](#開發環境設置)
- [API 開發](#api-開發)
- [前端開發](#前端開發)
- [資料庫管理](#資料庫管理)
- [部署](#部署)

## 專案概述

Network Toolbox 是一個基於 Docker 的網路工具箱，專注於 DHCP Server 的分析與管理。

### 主要功能

- DHCP Server 監控
- DHCP 租約管理
- 伺服器狀態分析
- 使用率統計

## 技術棧

### 前端
- React 18.2
- Ant Design 5.x
- React Router 6
- Axios
- Recharts

### 後端
- Django 4.2
- Django REST Framework
- PostgreSQL 15

### 基礎設施
- Docker & Docker Compose
- Nginx (反向代理)
- Adminer (資料庫管理)
- Portainer (容器管理)

## 專案結構

```
network-toolbox/
├── frontend/                   # React 前端
│   ├── public/
│   ├── src/
│   │   ├── components/        # 可重用組件
│   │   │   ├── Logo.js
│   │   │   ├── Sidebar.js
│   │   │   └── TopHeader.js
│   │   ├── contexts/          # React Context
│   │   │   └── AuthContext.js
│   │   ├── pages/             # 頁面組件
│   │   │   ├── DashboardPage.js
│   │   │   ├── DHCPAnalyticsPage.js
│   │   │   ├── DHCPServerManagementPage.js
│   │   │   ├── UserManagementPage.js
│   │   │   └── SettingsPage.js
│   │   ├── App.js
│   │   ├── App.css
│   │   ├── index.js
│   │   └── index.css
│   ├── package.json
│   └── Dockerfile
│
├── backend/                    # Django 後端
│   ├── api/                   # API 應用
│   │   ├── models.py         # 資料模型
│   │   ├── serializers.py    # REST 序列化器
│   │   ├── views.py          # API 視圖
│   │   ├── urls.py           # API 路由
│   │   └── admin.py          # Admin 介面
│   ├── network_toolbox/       # Django 專案設定
│   │   ├── settings.py
│   │   ├── urls.py
│   │   └── wsgi.py
│   ├── requirements.txt
│   ├── manage.py
│   └── Dockerfile
│
├── nginx/                      # Nginx 配置
│   ├── nginx.conf
│   └── Dockerfile
│
├── library/                    # 共享程式庫
│
├── docker-compose.yml          # Docker Compose 配置
├── start.sh                   # 啟動腳本
├── stop.sh                    # 停止腳本
└── README.md                  # 專案說明
```

## 開發環境設置

### 前置需求

- Docker 20.10+
- Docker Compose v2
- Git

### 快速開始

1. **Clone 專案**
   ```bash
   git clone <repository-url>
   cd network-toolbox
   ```

2. **設定環境變數**
   ```bash
   cp backend/.env.example backend/.env
   # 編輯 .env 檔案修改設定
   ```

3. **啟動服務**
   ```bash
   ./start.sh
   ```

4. **建立超級使用者**
   ```bash
   docker compose exec django python manage.py createsuperuser
   ```

## API 開發

### 資料模型

#### DHCPServer
```python
class DHCPServer(models.Model):
    name = models.CharField(max_length=200)
    ip_address = models.GenericIPAddressField()
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    pool_usage = models.FloatField(default=0.0)
    total_leases = models.IntegerField(default=0)
    active_leases = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
```

#### DHCPLease
```python
class DHCPLease(models.Model):
    server = models.ForeignKey(DHCPServer, on_delete=models.CASCADE)
    ip_address = models.GenericIPAddressField()
    mac_address = models.CharField(max_length=17)
    hostname = models.CharField(max_length=255, blank=True)
    lease_start = models.DateTimeField()
    lease_end = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
```

### API 端點

| 端點 | 方法 | 說明 |
|------|------|------|
| `/api/` | GET | API 根端點 |
| `/api/dashboard/stats/` | GET | 儀表板統計 |
| `/api/dhcp-servers/` | GET, POST | DHCP 伺服器列表/建立 |
| `/api/dhcp-servers/{id}/` | GET, PUT, PATCH, DELETE | DHCP 伺服器詳情/更新/刪除 |
| `/api/dhcp-leases/` | GET, POST | DHCP 租約列表/建立 |
| `/api/dhcp-leases/{id}/` | GET, PUT, PATCH, DELETE | DHCP 租約詳情/更新/刪除 |

### 新增 API 端點

1. **在 `models.py` 中定義資料模型**
   ```python
   class NewModel(models.Model):
       # 定義欄位
       pass
   ```

2. **建立 Serializer**
   ```python
   class NewModelSerializer(serializers.ModelSerializer):
       class Meta:
           model = NewModel
           fields = '__all__'
   ```

3. **建立 ViewSet**
   ```python
   class NewModelViewSet(viewsets.ModelViewSet):
       queryset = NewModel.objects.all()
       serializer_class = NewModelSerializer
   ```

4. **註冊路由**
   ```python
   router.register(r'new-model', views.NewModelViewSet)
   ```

5. **執行遷移**
   ```bash
   docker compose exec django python manage.py makemigrations
   docker compose exec django python manage.py migrate
   ```

## 前端開發

### 組件結構

- **Sidebar**: 側邊導航欄
- **TopHeader**: 頂部標題欄
- **DashboardPage**: 儀表板頁面
- **其他頁面**: 各功能頁面

### 新增頁面

1. **建立頁面組件**
   ```jsx
   // src/pages/NewPage.js
   import React from 'react';
   import { Card } from 'antd';
   
   const NewPage = () => {
       return (
           <div style={{ padding: 24 }}>
               <Card title="New Page">
                   {/* 頁面內容 */}
               </Card>
           </div>
       );
   };
   
   export default NewPage;
   ```

2. **加入路由**
   ```jsx
   // src/App.js
   import NewPage from './pages/NewPage';
   
   <Route path="/new-page" element={<NewPage />} />
   ```

3. **更新側邊欄**
   ```jsx
   // src/components/Sidebar.js
   {
       key: 'new-page',
       icon: <IconComponent />,
       label: 'New Page',
       onClick: () => navigate('/new-page')
   }
   ```

### API 調用

```jsx
import axios from 'axios';

// GET 請求
const fetchData = async () => {
    try {
        const response = await axios.get('/api/dhcp-servers/');
        console.log(response.data);
    } catch (error) {
        console.error('Error:', error);
    }
};

// POST 請求
const createData = async (data) => {
    try {
        const response = await axios.post('/api/dhcp-servers/', data);
        console.log(response.data);
    } catch (error) {
        console.error('Error:', error);
    }
};
```

## 資料庫管理

### 使用 Adminer

1. 訪問 http://localhost:9090
2. 登入資訊：
   - 系統: PostgreSQL
   - 伺服器: postgres
   - 使用者: postgres
   - 密碼: postgres123
   - 資料庫: network_toolbox

### Django 遷移

```bash
# 建立遷移檔案
docker compose exec django python manage.py makemigrations

# 執行遷移
docker compose exec django python manage.py migrate

# 查看遷移狀態
docker compose exec django python manage.py showmigrations
```

### 資料庫備份與還原

```bash
# 備份
docker compose exec postgres pg_dump -U postgres network_toolbox > backup.sql

# 還原
cat backup.sql | docker compose exec -T postgres psql -U postgres network_toolbox
```

## 部署

### 開發環境

```bash
./start.sh
```

### 生產環境

1. **修改環境變數**
   - 設定 `DEBUG=False`
   - 更改 `SECRET_KEY`
   - 修改資料庫密碼
   - 設定 `ALLOWED_HOSTS`

2. **使用 HTTPS**
   - 配置 SSL 憑證
   - 更新 Nginx 配置

3. **收集靜態檔案**
   ```bash
   docker compose exec django python manage.py collectstatic --noinput
   ```

4. **啟動服務**
   ```bash
   docker compose up -d --build
   ```

## 常用命令速查

```bash
# 啟動服務
./start.sh

# 停止服務
./stop.sh

# 查看日誌
docker compose logs -f [service_name]

# 進入容器
docker compose exec [service_name] bash

# 重啟服務
docker compose restart [service_name]

# 重建容器
docker compose up -d --build [service_name]

# Django Shell
docker compose exec django python manage.py shell

# 建立超級使用者
docker compose exec django python manage.py createsuperuser
```

## 故障排除

### 前端無法連接後端

1. 檢查 Nginx 配置
2. 確認服務運行狀態
3. 查看瀏覽器開發者工具的 Network 標籤

### 資料庫連接失敗

1. 確認 PostgreSQL 容器運行
2. 檢查環境變數設定
3. 查看 Django 日誌

### Docker 容器無法啟動

1. 檢查 Docker 狀態
2. 查看容器日誌
3. 重建映像

---

**維護者**: Kevin Huang  
**最後更新**: 2025-01-XX
