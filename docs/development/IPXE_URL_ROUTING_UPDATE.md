# iPXE 分析頁面 URL 路由更新

## 📝 更新說明

將 iPXE 分析頁面改為使用 URL 參數來管理不同的 Server 和 Tab，與 DHCP Server 分析頁面的做法一致。

## 🔄 更新內容

### 1. URL 路由模式

**之前**：
- 所有狀態都在組件內部管理（useState）
- URL 固定為 `/ipxe-analytics`
- 無法直接分享特定 Server 或 Tab 的連結
- 瀏覽器前進/後退按鈕無法正常工作

**現在**：
- 使用 URL 參數管理狀態
- 支援多種 URL 格式：
  - `/ipxe-analytics` - 預設（所有 Server，概覽 Tab）
  - `/ipxe-analytics/logs` - 所有 Server，日誌 Tab
  - `/ipxe-analytics/statistics` - 所有 Server，統計 Tab
  - `/ipxe-analytics/network-quality` - 所有 Server，網路品質 Tab
  - `/ipxe-analytics/server/1/overview` - Server 1，概覽 Tab
  - `/ipxe-analytics/server/1/logs` - Server 1，日誌 Tab
  - `/ipxe-analytics/server/2/statistics` - Server 2，統計 Tab

### 2. 路由配置（App.js）

```javascript
{/* iPXE Analytics 路由 - 支援子路由 */}
<Route path="/ipxe-analytics" element={<IPXEAnalyticsPage />} />
<Route path="/ipxe-analytics/:tab" element={<IPXEAnalyticsPage />} />
<Route path="/ipxe-analytics/server/:serverId/:tab" element={<IPXEAnalyticsPage />} />
```

### 3. 組件更新（IPXEAnalyticsPage.js）

#### 使用 React Router Hooks
```javascript
import { useParams, useNavigate, useSearchParams, Link } from 'react-router-dom';

// 從 URL 獲取參數
const { serverId: urlServerId, tab: urlTab } = useParams();
const [searchParams] = useSearchParams();
const navigate = useNavigate();

// 從 URL 決定當前狀態
const activeTab = urlTab || 'overview';
const selectedServer = urlServerId || searchParams.get('server') || 'all';
```

#### Server 切換處理
```javascript
const handleServerChange = (serverId) => {
    if (serverId === 'all') {
        // 切換到彙總視圖
        navigate(`/ipxe-analytics/${activeTab}`);
    } else {
        // 切換到特定 Server
        navigate(`/ipxe-analytics/server/${serverId}/${activeTab}`);
    }
};
```

#### Tab 切換處理
```javascript
const handleTabChange = (key) => {
    if (selectedServer === 'all') {
        // 彙總視圖
        navigate(`/ipxe-analytics/${key}`);
    } else {
        // 特定 Server
        navigate(`/ipxe-analytics/server/${selectedServer}/${key}`);
    }
};
```

#### 動態頁面標題
```javascript
useEffect(() => {
    const serverInfo = servers.find(s => s.id.toString() === selectedServer);
    const serverName = serverInfo ? 
        `${serverInfo.ip_address} (${serverInfo.name})` : 
        selectedServer === 'all' ? '所有 Server' : 'Server';
    
    const tabName = {
        'overview': '概覽',
        'logs': '日誌查看',
        'statistics': '統計分析',
        'network-quality': '網路品質',
    }[activeTab] || '概覽';
    
    document.title = `${tabName} - ${serverName} | iPXE 分析`;
}, [activeTab, selectedServer, servers]);
```

### 4. 側邊欄更新（Sidebar.js）

#### 動態選中菜單項
```javascript
import { useNavigate, useLocation } from 'react-router-dom';

const location = useLocation();

const getSelectedKey = () => {
    const pathname = location.pathname;
    
    // 處理 DHCP Analytics 子路由
    if (pathname.startsWith('/dhcp-analytics')) {
        return 'dhcp-analytics';
    }
    
    // 處理 iPXE Analytics 子路由
    if (pathname.startsWith('/ipxe-analytics')) {
        return 'ipxe-analytics';
    }
    
    // ... 其他路由
    
    return 'dashboard';
};

// 在 Menu 組件中使用
<Menu
    selectedKeys={[getSelectedKey()]}
    // ... 其他 props
/>
```

## ✨ 改進效果

### 1. 可分享的 URL
現在可以直接複製 URL 分享給他人，對方會看到完全相同的頁面狀態：
```
https://your-domain/ipxe-analytics/server/1/network-quality
```

### 2. 瀏覽器歷史記錄
- ✅ 瀏覽器的前進/後退按鈕正常工作
- ✅ 每次切換 Server 或 Tab 都會在歷史記錄中留下記錄

### 3. 書籤友好
- ✅ 可以將特定的 Server + Tab 組合加入書籤
- ✅ 下次打開書籤會直接跳到對應的頁面

### 4. SEO 友好
- ✅ 每個 Server + Tab 組合都有獨特的 URL
- ✅ 搜尋引擎可以索引不同的頁面

### 5. 側邊欄高亮
- ✅ 無論在哪個 Tab 或 Server，側邊欄的 "iPXE 分析" 選項都會保持高亮
- ✅ 與 DHCP 分析頁面的行為一致

## 📊 URL 結構對比

### DHCP Analytics
```
/dhcp-analytics                              → 所有 Server, overview
/dhcp-analytics/logs                         → 所有 Server, logs
/dhcp-analytics/server/1/overview            → Server 1, overview
/dhcp-analytics/server/2/statistics          → Server 2, statistics
```

### iPXE Analytics（更新後）
```
/ipxe-analytics                              → 所有 Server, overview
/ipxe-analytics/logs                         → 所有 Server, logs
/ipxe-analytics/server/1/overview            → Server 1, overview
/ipxe-analytics/server/2/network-quality     → Server 2, network-quality
```

## 🔧 技術細節

### 狀態管理
- **之前**：使用 `useState` 管理 `selectedServer` 和 `activeTab`
- **現在**：URL 為唯一真實來源（Single Source of Truth）

### 導航方式
- **之前**：使用 `setState` 更新狀態
- **現在**：使用 `navigate()` 更新 URL

### 初始狀態
- **之前**：硬編碼預設值（`all`, `overview`）
- **現在**：從 URL 讀取，無 URL 參數時才使用預設值

## 🧪 測試建議

### 1. 基本功能測試
```bash
# 訪問不同的 URL
http://localhost/ipxe-analytics
http://localhost/ipxe-analytics/logs
http://localhost/ipxe-analytics/statistics
http://localhost/ipxe-analytics/network-quality
http://localhost/ipxe-analytics/server/1/overview
http://localhost/ipxe-analytics/server/1/network-quality
```

### 2. 切換測試
- ✅ 切換 Server：檢查 URL 是否更新，Tab 是否保持不變
- ✅ 切換 Tab：檢查 URL 是否更新，Server 是否保持不變
- ✅ 瀏覽器前進/後退：檢查狀態是否正確恢復

### 3. 書籤測試
- ✅ 將特定頁面加入書籤
- ✅ 關閉瀏覽器後重新打開書籤
- ✅ 檢查是否跳轉到正確的 Server 和 Tab

### 4. 分享測試
- ✅ 複製 URL 並在新分頁打開
- ✅ 複製 URL 並在隱私瀏覽模式打開
- ✅ 檢查是否顯示相同的內容

## 📝 注意事項

### 1. Tab Key 命名
iPXE 的 Tab 使用 kebab-case：
- `overview`
- `logs`
- `statistics`
- `network-quality`（注意：使用連字符）

### 2. Server ID
- 使用數字 ID（如 `1`, `2`, `3`）
- 特殊值 `all` 表示所有 Server

### 3. 預設值
當 URL 沒有指定參數時：
- 預設 Tab：`overview`
- 預設 Server：`all`

## 🎯 後續建議

### 1. 添加查詢參數（可選）
如果需要更多過濾功能，可以使用查詢參數：
```javascript
/ipxe-analytics/logs?date=2025-11-01&status=success
```

### 2. URL 參數驗證
添加參數驗證邏輯：
```javascript
// 驗證 Server ID
if (urlServerId && !servers.find(s => s.id.toString() === urlServerId)) {
    // 重定向到預設頁面或顯示錯誤
    navigate('/ipxe-analytics');
}

// 驗證 Tab Key
const validTabs = ['overview', 'logs', 'statistics', 'network-quality'];
if (urlTab && !validTabs.includes(urlTab)) {
    navigate('/ipxe-analytics');
}
```

### 3. 麵包屑導航
添加更詳細的麵包屑：
```javascript
Home > iPXE 分析 > Server 10.250.50.2 > 網路品質
```

## 🔗 相關文件

- `frontend/src/App.js` - 路由配置
- `frontend/src/pages/IPXEAnalyticsPage.js` - 主要頁面組件
- `frontend/src/components/Sidebar.js` - 側邊欄組件
- `frontend/src/pages/DHCPAnalyticsPage.js` - DHCP 分析頁面（參考實現）

## 📊 影響範圍

### 修改的檔案
- ✅ `frontend/src/App.js` - 添加 iPXE 路由
- ✅ `frontend/src/pages/IPXEAnalyticsPage.js` - 重構狀態管理
- ✅ `frontend/src/components/Sidebar.js` - 添加動態選中邏輯

### 未修改的檔案
- ✅ Tab 組件（OverviewTab, LogsTab, StatisticsTab, NetworkQualityTab）
- ✅ 後端 API
- ✅ 其他頁面

## ✅ 完成狀態

- [x] 更新 App.js 路由配置
- [x] 更新 IPXEAnalyticsPage 使用 URL 參數
- [x] 更新 Sidebar 動態選中邏輯
- [x] 添加動態頁面標題
- [x] 處理 DHCP 和 iPXE 子路由的高亮邏輯

---

**最後更新**：2025-11-01  
**作者**：Network Toolbox Team  
**版本**：v2.0
