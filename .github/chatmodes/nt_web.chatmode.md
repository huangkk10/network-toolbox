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

### UI 組件庫：Ant Design（預設使用）

**本專案預設使用 Ant Design 5.x 作為 UI 組件庫**

#### 常用組件清單

**佈局組件**：
- `Layout`, `Header`, `Sider`, `Content`, `Footer` - 頁面佈局
- `Row`, `Col` - 網格系統（響應式佈局）
- `Space` - 間距組件
- `Divider` - 分隔線

**數據展示**：
- `Table` - 數據表格（支援排序、篩選、分頁）
- `Card` - 卡片容器
- `Statistic` - 統計數值展示
- `Tag` - 標籤
- `Badge` - 徽標
- `Descriptions` - 描述列表
- `Timeline` - 時間軸
- `Tree` - 樹形控件

**數據輸入**：
- `Form`, `Form.Item` - 表單容器
- `Input`, `Input.Password`, `Input.TextArea` - 輸入框
- `Select`, `Select.Option` - 下拉選擇
- `DatePicker`, `RangePicker` - 日期選擇
- `Checkbox`, `Radio` - 選擇器
- `Switch` - 開關
- `Slider` - 滑動輸入條
- `Upload` - 文件上傳

**操作反饋**：
- `Button` - 按鈕（type: primary, default, dashed, text, link）
- `Modal` - 對話框
- `message` - 全局提示訊息
- `notification` - 通知提醒框
- `Popconfirm` - 氣泡確認框
- `Drawer` - 抽屜
- `Progress` - 進度條
- `Spin` - 載入中

**導航**：
- `Menu` - 導航菜單
- `Dropdown` - 下拉菜單
- `Breadcrumb` - 麵包屑
- `Pagination` - 分頁
- `Steps` - 步驟條

**圖表組件（使用 recharts）**：
- `LineChart` - 折線圖
- `AreaChart` - 面積圖
- `BarChart` - 柱狀圖
- `PieChart` - 圓餅圖
- `ResponsiveContainer` - 響應式容器

#### 組件使用規範

1. **顏色使用**：
   ```javascript
   // 狀態顏色
   success: '#52c41a'  // 成功、活躍
   warning: '#faad14'  // 警告、即將過期
   error: '#ff4d4f'    // 錯誤、已過期
   info: '#2196f3'     // 資訊、主色調
   ```

2. **按鈕規範**：
   ```javascript
   // 主要操作
   <Button type="primary">確定</Button>
   
   // 次要操作
   <Button>取消</Button>
   
   // 危險操作
   <Button type="primary" danger>刪除</Button>
   
   // 圖標按鈕
   <Button icon={<PlusOutlined />}>新增</Button>
   ```

3. **表格規範**：
   ```javascript
   <Table
       columns={columns}
       dataSource={data}
       rowKey="id"              // 必須指定 rowKey
       loading={loading}        // 載入狀態
       pagination={{            // 分頁配置
           pageSize: 10,
           showSizeChanger: true,
           showTotal: (total) => `共 ${total} 筆`
       }}
       size="middle"            // small, middle, large
   />
   ```

4. **表單規範**：
   ```javascript
   <Form
       form={form}
       layout="vertical"        // horizontal, vertical, inline
       onFinish={handleSubmit}
   >
       <Form.Item
           label="欄位名稱"
           name="fieldName"
           rules={[
               { required: true, message: '請輸入欄位名稱' }
           ]}
       >
           <Input placeholder="請輸入..." />
       </Form.Item>
   </Form>
   ```

5. **訊息提示規範**：
   ```javascript
   import { message } from 'antd';
   
   message.success('操作成功！');
   message.error('操作失敗！');
   message.warning('請注意！');
   message.info('提示訊息');
   ```

6. **Modal 對話框規範**：
   ```javascript
   <Modal
       title="對話框標題"
       open={visible}           // v5 使用 open 代替 visible
       onOk={handleOk}
       onCancel={handleCancel}
       okText="確定"
       cancelText="取消"
   >
       {/* 內容 */}
   </Modal>
   ```

7. **響應式佈局**：
   ```javascript
   <Row gutter={[16, 16]}>
       <Col xs={24} sm={12} md={8} lg={6}>
           {/* xs: 手機, sm: 平板, md: 小桌面, lg: 大桌面 */}
       </Col>
   </Row>
   ```

#### 圖標使用（@ant-design/icons）

常用圖標：
```javascript
import {
    UserOutlined,
    SettingOutlined,
    LogoutOutlined,
    PlusOutlined,
    EditOutlined,
    DeleteOutlined,
    SearchOutlined,
    ReloadOutlined,
    CheckCircleOutlined,
    CloseCircleOutlined,
    BarChartOutlined,
    GlobalOutlined,
} from '@ant-design/icons';
```

### 代碼風格

**前端開發規範**：
- **組件類型**：函數式組件 + Hooks（不使用 Class 組件）
- **UI 組件庫**：Ant Design 5.x（**預設使用**）
- **圖表庫**：recharts（用於數據視覺化）
- **HTTP 客戶端**：axios
- **路由**：React Router v6
- **狀態管理**：useState, useContext（小型專案不需要 Redux）

**後端開發規範**：
- **API 風格**：ViewSet + RESTful API
- **序列化**：Django REST Framework Serializers
- **日誌記錄**：詳細記錄操作和錯誤

## 數據模型

現有模型：
- `DHCPServer`：DHCP 伺服器資訊
- `DHCPLease`：DHCP 租約記錄
- `User`：Django 內建 User 模型

## 開發指導原則

### 測試文件管理規範

**所有測試文件必須放置在 `tests/` 目錄下，並按照功能分類組織**

#### 測試目錄結構

```
tests/
├── unit/                  # 單元測試
│   ├── backend/          # 後端單元測試
│   │   ├── test_models.py
│   │   ├── test_serializers.py
│   │   └── test_services.py
│   └── frontend/         # 前端單元測試
│       └── components/
├── integration/           # 整合測試
│   ├── api/              # API 整合測試
│   │   ├── test_dhcp_api.py
│   │   └── test_logs_api.py
│   └── services/         # 服務整合測試
│       ├── test_dhcp_ssh.py
│       └── test_nas_connection.py
├── e2e/                   # 端對端測試
│   └── test_workflows.py
├── performance/           # 性能測試
│   └── test_load.py
└── fixtures/              # 測試數據
    └── sample_data.json
```

#### 測試文件放置規則

1. **單元測試**（Unit Tests）
   - **位置**：`tests/unit/backend/` 或 `tests/unit/frontend/`
   - **適用於**：測試單一函數、類別或組件
   - **命名**：`test_<模組名稱>.py`
   - **範例**：`tests/unit/backend/test_models.py`

2. **整合測試**（Integration Tests）
   - **位置**：`tests/integration/`
   - **適用於**：測試多個組件之間的交互、API 測試、服務連接測試
   - **命名**：`test_<功能名稱>.py`
   - **範例**：`tests/integration/api/test_dhcp_api.py`

3. **端對端測試**（E2E Tests）
   - **位置**：`tests/e2e/`
   - **適用於**：測試完整的使用者流程
   - **命名**：`test_<流程名稱>.py`
   - **範例**：`tests/e2e/test_dhcp_workflow.py`

4. **性能測試**（Performance Tests）
   - **位置**：`tests/performance/`
   - **適用於**：負載測試、壓力測試、基準測試
   - **命名**：`test_<測試類型>.py`
   - **範例**：`tests/performance/test_api_load.py`

#### 測試文件命名規範

- **所有測試文件必須以 `test_` 開頭**
- **使用 snake_case**：`test_feature_name.py`
- **描述性命名**：清楚說明測試的內容
- **範例**：
  - ✅ `test_dhcp_lease_creation.py`
  - ✅ `test_user_authentication.py`
  - ❌ `dhcp_test.py`
  - ❌ `TestFile.py`

#### 測試代碼規範

**Django 後端測試**：
```python
# tests/unit/backend/test_models.py
from django.test import TestCase
from api.models import DHCPServer

class DHCPServerModelTest(TestCase):
    def setUp(self):
        """測試初始化"""
        self.server = DHCPServer.objects.create(
            name='Test Server',
            ip_address='192.168.1.1'
        )
    
    def test_server_creation(self):
        """測試伺服器創建"""
        self.assertEqual(self.server.name, 'Test Server')
        self.assertEqual(self.server.ip_address, '192.168.1.1')
    
    def tearDown(self):
        """測試清理"""
        self.server.delete()
```

**React 前端測試**：
```javascript
// tests/unit/frontend/components/DHCPTable.test.js
import { render, screen } from '@testing-library/react';
import DHCPTable from '@/components/DHCPTable';

describe('DHCPTable Component', () => {
    test('renders table with data', () => {
        const data = [
            { id: 1, name: 'Server 1', ip: '192.168.1.1' }
        ];
        
        render(<DHCPTable data={data} />);
        expect(screen.getByText('Server 1')).toBeInTheDocument();
    });
});
```

**整合測試**：
```python
# tests/integration/api/test_dhcp_api.py
from rest_framework.test import APITestCase
from rest_framework import status

class DHCPAPITest(APITestCase):
    def test_get_dhcp_servers(self):
        """測試獲取 DHCP 伺服器列表"""
        response = self.client.get('/api/dhcp-servers/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
```

#### 執行測試

```bash
# 執行所有測試
python manage.py test tests/

# 執行特定類型的測試
python manage.py test tests/unit/
python manage.py test tests/integration/

# 執行特定測試文件
python manage.py test tests/unit/backend/test_models.py

# 前端測試
npm test                    # 執行所有前端測試
npm test -- --watch         # 監聽模式
```

#### AI 創建測試文件時的說明

**當您要求 AI 創建測試文件時，請明確指定：**

- **測試類型**：單元測試、整合測試、E2E 測試等
- **測試目標**：要測試的功能或組件
- **測試範圍**：前端還是後端

**範例請求**：
- ✅ "為 DHCPServer 模型創建單元測試"（會自動放在 `tests/unit/backend/`）
- ✅ "創建 DHCP API 的整合測試"（會自動放在 `tests/integration/api/`）
- ✅ "創建使用者登入流程的 E2E 測試"（會自動放在 `tests/e2e/`）
- ❌ "創建一個測試文件"（不明確）

**AI 會自動：**
1. 根據測試類型選擇合適的 `tests/` 子目錄
2. 使用正確的命名規範（`test_` 前綴）
3. 生成符合專案規範的測試代碼
4. 包含必要的導入和設置代碼

### 添加新功能時

1. **前端頁面**：
   - 在 `frontend/src/pages/` 創建（使用 Ant Design 組件）
   - 更新 `App.js` 路由
   - 更新 `Sidebar.js` 菜單
   - **必須使用 Ant Design 組件**，不要使用原生 HTML 元素
   
   範例結構：
   ```javascript
   import React, { useState, useEffect } from 'react';
   import { Card, Table, Button, Modal, Form, Input, message } from 'antd';
   import { PlusOutlined } from '@ant-design/icons';
   
   const NewFeaturePage = () => {
       const [data, setData] = useState([]);
       const [loading, setLoading] = useState(false);
       const [modalVisible, setModalVisible] = useState(false);
       
       // 使用 Ant Design 組件構建 UI
       return (
           <div style={{ padding: '24px' }}>
               <Card 
                   title="頁面標題"
                   extra={<Button type="primary" icon={<PlusOutlined />}>新增</Button>}
               >
                   <Table 
                       dataSource={data} 
                       loading={loading}
                       // ...其他配置
                   />
               </Card>
           </div>
       );
   };
   ```

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

4. **前端數據請求**：
   ```javascript
   import axios from 'axios';
   import { message } from 'antd';
   
   const fetchData = async () => {
       setLoading(true);
       try {
           const response = await axios.get('/api/endpoint/');
           setData(response.data);
           message.success('載入成功');
       } catch (error) {
           console.error('Error:', error);
           message.error('載入失敗：' + error.message);
       } finally {
           setLoading(false);
       }
   };
   ```

### 前端開發最佳實踐

1. **永遠使用 Ant Design 組件**：
   - ✅ 使用 `<Button>`，不要用 `<button>`
   - ✅ 使用 `<Input>`，不要用 `<input>`
   - ✅ 使用 `<Table>`，不要用 `<table>`
   - ✅ 使用 `<Card>`，不要用 `<div className="card">`

2. **響應式設計**：
   ```javascript
   <Row gutter={[16, 16]}>
       <Col xs={24} sm={12} md={8} lg={6}>
           <Card>內容</Card>
       </Col>
   </Row>
   ```

3. **狀態管理**：
   - 使用 `useState` 管理組件狀態
   - 使用 `useEffect` 處理副作用（API 請求）
   - 複雜狀態使用 `useContext`

4. **錯誤處理統一使用 message**：
   ```javascript
   message.success('操作成功');
   message.error('操作失敗');
   message.warning('請注意');
   message.info('提示訊息');
   ```

### API 開發規範

- 使用 ViewSet
- 禁用分頁：`pagination_class = None`（除非需要分頁）
- 開發環境：`AllowAny`
- 生產環境：`IsAuthenticated`

### 錯誤處理

**後端**：
- try-except 捕獲異常
- 記錄到日誌（包含 stack trace）
- 返回友好錯誤訊息

**前端**：
- 使用 Ant Design `message` 顯示錯誤
- 使用 `loading` 狀態顯示載入動畫
- 表單驗證使用 Form.Item 的 rules

### 組件開發規範

**頁面組件結構**：
```javascript
const PageComponent = () => {
    // 1. Hooks（useState, useEffect, etc.）
    const [data, setData] = useState([]);
    const [loading, setLoading] = useState(false);
    
    // 2. 數據請求函數
    const fetchData = async () => { /* ... */ };
    
    // 3. 事件處理函數
    const handleAdd = () => { /* ... */ };
    const handleEdit = (record) => { /* ... */ };
    const handleDelete = (id) => { /* ... */ };
    
    // 4. useEffect
    useEffect(() => {
        fetchData();
    }, []);
    
    // 5. 渲染配置（Table columns, etc.）
    const columns = [ /* ... */ ];
    
    // 6. 返回 JSX（使用 Ant Design 組件）
    return (
        <div style={{ padding: '24px' }}>
            <Card>
                <Table columns={columns} dataSource={data} />
            </Card>
        </div>
    );
};
```

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

## 📚 文檔管理規範

### 文檔目錄結構

本專案的所有文檔統一存放在 `docs/` 目錄下，按照以下結構組織：

```
docs/
├── features/              # 功能相關文檔
│   ├── scheduled-tasks/   # 定時任務功能
│   │   ├── README.md
│   │   ├── CELERY_IMPLEMENTATION_GUIDE.md
│   │   ├── CRON_SETUP_GUIDE.md
│   │   ├── CRON_VS_CELERY_COMPARISON.md
│   │   └── LOGS_SYNC_GUIDE.md
│   └── [其他功能]/
├── deployment/            # 部署相關文檔
│   ├── DEPLOYMENT.md
│   └── [其他部署文檔]
├── development/           # 開發相關文檔
│   ├── DEVELOPMENT.md
│   ├── DOCS_REORGANIZATION_REPORT.md
│   └── [其他開發文檔]
├── api/                   # API 文檔
│   └── [API 相關文檔]
└── troubleshooting/       # 故障排查文檔
    └── [故障排查文檔]
```

### 創建新文檔的指導原則

當需要創建新的說明文檔時，請遵循以下規則：

1. **功能文檔**（Feature Documentation）
   - **位置**：`docs/features/[功能名稱]/`
   - **適用於**：新功能說明、使用指南、配置教程
   - **範例**：定時任務功能的文檔在 `docs/features/scheduled-tasks/`
   - **建議**：每個功能目錄應包含 README.md 作為導航文件

2. **部署文檔**（Deployment Documentation）
   - **位置**：`docs/deployment/`
   - **適用於**：Docker 部署、生產環境配置、CI/CD 流程
   - **範例**：`DEPLOYMENT.md`、`DOCKER_SETUP.md`

3. **開發文檔**（Development Documentation）
   - **位置**：`docs/development/`
   - **適用於**：開發環境設置、開發規範、架構設計、技術決策記錄
   - **範例**：`DEVELOPMENT.md`、`DOCS_REORGANIZATION_REPORT.md`

4. **API 文檔**（API Documentation）
   - **位置**：`docs/api/`
   - **適用於**：API 端點說明、請求/響應格式、認證授權
   - **範例**：`API_REFERENCE.md`、`AUTHENTICATION.md`

5. **故障排查文檔**（Troubleshooting Documentation）
   - **位置**：`docs/troubleshooting/`
   - **適用於**：常見問題、錯誤處理、調試技巧
   - **範例**：`COMMON_ISSUES.md`、`DEBUG_GUIDE.md`

### 文檔命名規範

- **使用大寫字母和底線**：`FEATURE_NAME.md`（主要文檔）
- **使用小寫字母和連字符**：`feature-name-details.md`（次要文檔）
- **README 文件**：每個功能目錄應包含 `README.md` 作為導航入口

### 文檔內容規範

每個文檔應包含：

1. **清晰的標題**：說明文檔的目的
2. **目錄**：對於較長的文檔（使用 `[toc]` 或手動創建）
3. **概述**：簡短說明文檔涵蓋的內容
4. **詳細內容**：按邏輯順序組織
5. **範例**：提供實際的代碼或命令範例
6. **相關連結**：引用其他相關文檔
7. **更新日期**：文檔最後更新時間

### AI 協助創建文檔的說明

**當您要求 AI 創建新的說明文檔時，請明確指定：**

- **文檔類型**：功能說明、部署指南、故障排查等
- **目標位置**：根據上述規範，AI 會自動將文檔放置在適當的 `docs/` 子目錄中
- **文檔格式**：Markdown 格式（.md）

**範例請求**：
- ❌ "幫我寫一個 Celery 的說明文檔"（位置不明確）
- ✅ "在 docs/features/scheduled-tasks/ 創建 Celery 實現指南"（位置明確）
- ✅ "創建一個關於 Docker 部署的說明文檔"（AI 會自動放在 docs/deployment/）

**AI 會自動：**
1. 根據文檔性質選擇合適的 `docs/` 子目錄
2. 創建必要的目錄結構
3. 生成符合規範的文檔內容
4. 在相關的 README.md 中添加連結（如果需要）

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
