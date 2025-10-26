# Network Toolbox - GitHub Copilot 指導說明

## 專案概述

Network Toolbox 是一個 DHCP 伺服器管理平台，採用前後端分離架構：
- **前端**：React 18.2 + Ant Design 5.x（純白極簡風格）
- **後端**：Django 4.2 + Django REST Framework
- **資料庫**：PostgreSQL（本機，非 Docker 容器）
- **部署**：Docker Compose（Nginx 反向代理）

## 架構參考

本專案仿效 [huangkk10/ai-platform-web](https://github.com/huangkk10/ai-platform-web) 的架構設計：
- 完整的 Docker 部署方式
- 前後端分離架構
- 統一的日誌管理系統
- 模組化的程式碼結構

## 專案結構

```
network-toolbox/
├── frontend/              # React 前端
│   ├── src/
│   │   ├── components/   # 共用組件
│   │   │   ├── Sidebar.js      # 側邊欄（純白主題）
│   │   │   ├── TopHeader.js    # 頂部導航
│   │   │   └── Logo.js         # NT Logo
│   │   ├── pages/        # 頁面組件
│   │   │   ├── DashboardPage.js
│   │   │   ├── DHCPServerPage.js
│   │   │   ├── UserManagementPage.js
│   │   │   └── SystemSettingsPage.js
│   │   └── App.js
│   └── package.json
├── backend/              # Django 後端
│   ├── network_toolbox/  # 專案設定
│   │   ├── settings.py   # Django 設定（包含完整日誌配置）
│   │   ├── urls.py
│   │   └── wsgi.py
│   ├── api/              # API 應用
│   │   ├── models.py     # DHCPServer, DHCPLease, User
│   │   ├── serializers.py # UserSerializer, DHCP serializers
│   │   ├── views.py      # API ViewSets
│   │   └── urls.py
│   └── requirements.txt
├── nginx/                # Nginx 反向代理配置
├── library/              # 共用函式庫（未來擴充）
├── logs/                 # 日誌目錄（掛載到容器）
│   ├── django.log        # 一般應用程式日誌
│   ├── django_error.log  # 錯誤日誌
│   ├── dhcp_operations.log
│   └── api_access.log
├── scripts/              # 工具腳本
│   ├── analyze_logs.sh   # 日誌分析
│   └── clean_old_logs.sh # 日誌清理
└── docker-compose.yml
```

## 設計風格指南

### 前端 UI 設計
- **主題**：純白極簡風格
- **背景色**：`#ffffff`（純白）
- **主色調**：`#2196f3`（藍色）
- **側邊欄**：白色背景，藍色選中高亮
- **品牌名稱**：NT（Network Toolbox）
- **圖示庫**：Ant Design Icons

### 代碼風格
- **前端**：
  - 使用函數式組件和 Hooks
  - 使用 Ant Design 組件庫
  - API 請求使用 axios
  - 路由使用 React Router v6
  
- **後端**：
  - 使用 Django REST Framework ViewSet
  - 遵循 Django 最佳實踐
  - API 命名使用 RESTful 風格
  - 詳細的日誌記錄

## 技術細節

### 資料庫連接
- **重要**：使用本機 PostgreSQL，非 Docker 容器
- Django 連接使用 `host.docker.internal`
- 資料庫名稱：`network_toolbox`
- 用戶：`postgres` / 密碼：`postgres123`

### 日誌系統
參考 ai-platform-web 的日誌配置：
- 按日期輪替（每天午夜）
- 不同類型日誌保留不同天數
- 詳細的日誌格式（包含模組、函數、行號）
- 專用 logger 配置

### Docker 服務
- `nginx`：80 端口，反向代理
- `react`：3000 端口，開發服務器
- `django`：8000 端口，Django runserver
- `adminer`：9090 端口，資料庫管理（host 模式）
- `postgres`：使用 profile，預設不啟動（使用本機 PostgreSQL）

## 開發指導原則

### 1. 添加新功能時
- 前端：在 `frontend/src/pages/` 創建新頁面
- 後端：在 `backend/api/` 添加 models, serializers, views
- 更新路由：前端 `App.js`，後端 `api/urls.py`
- 添加到側邊欄：更新 `Sidebar.js`

### 2. API 開發
- 使用 ViewSet 而非單獨的 APIView
- 禁用分頁時設置 `pagination_class = None`
- 開發階段使用 `AllowAny`，生產環境使用 `IsAuthenticated`
- 添加適當的日誌記錄

### 3. 前端開發
- 使用 Ant Design 組件
- 保持純白主題風格
- 使用 `message.success/error` 顯示操作結果
- 使用 `Modal` 進行數據編輯
- 使用 `Table` 展示列表數據

### 4. 數據模型
現有模型：
- `DHCPServer`：DHCP 伺服器資訊
- `DHCPLease`：DHCP 租約記錄
- `User`：使用 Django 內建 User 模型

### 5. 環境配置
- 使用 `python-decouple` 管理環境變數
- 重要配置通過環境變數設定
- `ALLOWED_HOSTS` 設為 `*`（開發環境）
- CORS 配置允許 localhost

### 6. 日誌記錄
在代碼中使用日誌：
```python
import logging
logger = logging.getLogger(__name__)

# 在函數中記錄
logger.info('操作成功')
logger.error('發生錯誤', exc_info=True)
```

### 7. 錯誤處理
- 使用 try-except 捕獲異常
- 記錄詳細的錯誤資訊到日誌
- 返回友好的錯誤訊息給前端
- 前端顯示錯誤提示（Ant Design message）

## 常見任務

### 添加新的 API 端點
1. 在 `models.py` 定義模型
2. 在 `serializers.py` 創建序列化器
3. 在 `views.py` 創建 ViewSet
4. 在 `urls.py` 註冊路由
5. 執行遷移：`docker exec nt-django python manage.py makemigrations && python manage.py migrate`

### 添加新的前端頁面
1. 在 `pages/` 創建頁面組件
2. 在 `App.js` 添加路由
3. 在 `Sidebar.js` 添加菜單項
4. 實作 API 調用和狀態管理

### 查看日誌
```bash
# 即時查看
tail -f logs/django.log

# 分析日誌
./scripts/analyze_logs.sh

# 清理舊日誌
./scripts/clean_old_logs.sh 30
```

### 重啟服務
```bash
docker compose restart django    # 重啟 Django
docker compose restart react     # 重啟 React
docker compose restart nginx     # 重啟 Nginx
docker compose restart           # 重啟所有服務
```

## 安全注意事項

- 生產環境必須修改 `SECRET_KEY`
- 生產環境設置 `DEBUG=False`
- 限制 `ALLOWED_HOSTS` 為實際域名
- 使用環境變數管理敏感資訊
- API 權限設置為 `IsAuthenticated`
- 定期更新依賴套件

## 測試指南

### 後端測試
```bash
docker exec nt-django python manage.py test
```

### 前端測試
```bash
cd frontend
npm test
```

### API 測試
```bash
# 使用 curl 測試
curl http://localhost/api/users/
curl http://localhost/api/dhcp-servers/

# 或使用 Django Admin
http://localhost/admin/
```

## 部署說明

### 開發環境
```bash
docker compose up -d
```

### 訪問服務
- 前端：http://localhost
- API：http://localhost/api/
- Django Admin：http://localhost/admin/
- Adminer：http://localhost:9090

## 命名規範

- **檔案名稱**：PascalCase（React 組件）、snake_case（Python）
- **組件名稱**：PascalCase
- **函數名稱**：camelCase（JS）、snake_case（Python）
- **變數名稱**：camelCase（JS）、snake_case（Python）
- **常數**：UPPER_SNAKE_CASE
- **API 端點**：kebab-case（`/api/dhcp-servers/`）
- **資料庫表名**：snake_case

## 相關資源

- [Django 文件](https://docs.djangoproject.com/)
- [Django REST Framework](https://www.django-rest-framework.org/)
- [React 文件](https://react.dev/)
- [Ant Design](https://ant.design/)
- [參考專案 ai-platform-web](https://github.com/huangkk10/ai-platform-web)

## 未來規劃

- [ ] DHCP Server 監控功能
- [ ] 租約自動續約功能
- [ ] IP 池使用率圖表
- [ ] 用戶權限細分
- [ ] 多租戶支援
- [ ] RESTful API 文件（Swagger）
- [ ] 單元測試覆蓋率提升
- [ ] 前端 E2E 測試

---

**最後更新**：2025-10-27  
**維護者**：Network Toolbox Team
