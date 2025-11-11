# Ansible 配置查看器 - Hostname 過濾功能更新

## 📋 更新日期
2025-11-09

## 🎯 更新內容

### 1. 功能變更
**原需求**：配置按鈕在 Job row，顯示所有主機（例如 Test-KVM01 job 顯示全部 21 個主機）

**新需求**：
- 配置按鈕移至 **Build row**（與「日誌」、「詳情」按鈕並列）
- 只顯示與 **Job Name 匹配的主機**（例如 Test-KVM01 job → 只顯示 Test-KVM01 主機）

### 2. 代碼變更

#### 2.1 RVTAnalysisPage.js

**狀態定義**：
```javascript
const [ansibleConfigDrawer, setAnsibleConfigDrawer] = useState({
    visible: false,
    jobId: null,
    jobName: null,
    buildNumber: null,
    hostname: null,  // 新增：用於過濾主機
});
```

**按鈕位置變更**：
```javascript
// 原位置：Job row (type === 'job')
// 新位置：Build row (type !== 'job')
{
    title: '操作',
    key: 'action',
    width: 250,  // 從 200 增加到 250
    render: (text, record) => {
        if (record.type === 'job') {
            // Job row 不顯示按鈕
            return null;
        }
        
        // Build row 顯示按鈕
        return (
            <Space>
                <Button 
                    type="link" 
                    size="small" 
                    onClick={() => handleViewLogs(record)}
                >
                    日誌
                </Button>
                <Button 
                    type="link" 
                    size="small" 
                    onClick={() => handleViewDetails(record)}
                >
                    詳情
                </Button>
                <Button 
                    type="link" 
                    size="small" 
                    icon={<SettingOutlined />}
                    onClick={() => handleViewAnsibleConfig(record)}
                >
                    配置
                </Button>
            </Space>
        );
    }
}
```

**處理函數更新**：
```javascript
const handleViewAnsibleConfig = (record) => {
    setAnsibleConfigDrawer({
        visible: true,
        jobId: record.job_id,
        jobName: record.job_name,
        buildNumber: record.build_number,
        hostname: record.job_name,  // 新增：傳遞 job_name 作為要過濾的 hostname
    });
};
```

**Drawer 組件調用**：
```javascript
<AnsibleConfigDrawer
    visible={ansibleConfigDrawer.visible}
    onClose={() => setAnsibleConfigDrawer({ ...ansibleConfigDrawer, visible: false })}
    jobId={ansibleConfigDrawer.jobId}
    jobName={ansibleConfigDrawer.jobName}
    buildNumber={ansibleConfigDrawer.buildNumber}
    hostname={ansibleConfigDrawer.hostname}  // 新增：傳遞 hostname prop
/>
```

#### 2.2 AnsibleConfigDrawer.jsx

**Props 定義**：
```javascript
const AnsibleConfigDrawer = ({ 
    visible, 
    onClose, 
    jobId, 
    jobName, 
    buildNumber,
    hostname  // 新增：用於過濾顯示的主機名稱
}) => {
```

**過濾邏輯**：
```javascript
// 解析資料
let hostList = parseInventoryToHostList(response);
let tree = parseInventoryToGroupTree(response);

// 如果提供了 hostname，則過濾只顯示匹配的主機
if (hostname) {
    hostList = hostList.filter(h => h.hostname === hostname);
    
    // 過濾 tree，只保留包含該主機的 group
    tree = tree.map(group => ({
        ...group,
        children: group.children.filter(child => 
            child.hostname === hostname
        )
    })).filter(group => group.children.length > 0);
}

setHosts(hostList);
setGroupsTree(tree);
```

**配置詳情標籤自動選擇**：
```javascript
<HostConfigTab 
    jobId={jobId}
    hosts={hosts}
    initialHostname={hostname || selectedHostForConfig}  // 優先使用 hostname
/>
```

## 🧪 測試步驟

### 1. 基本功能測試

#### 測試 1：按鈕位置正確
1. 前往 RVT 分析頁面
2. 展開任一 Job（例如 Test-KVM01）
3. **驗證**：
   - ✅ Job row **沒有**「配置」按鈕
   - ✅ Build row **有**「配置」、「日誌」、「詳情」三個按鈕
   - ✅ 按鈕排列整齊，沒有溢出

#### 測試 2：Hostname 過濾功能
1. 展開 `Test-KVM01` Job
2. 點擊任一 Build 的「配置」按鈕
3. **驗證**：
   - ✅ Drawer 標題顯示：`Ansible 配置 - Test-KVM01 #[Build號]`
   - ✅ **主機列表** 標籤只顯示 **1 個主機**（Test-KVM01）
   - ✅ **群組** 標籤只顯示包含 Test-KVM01 的群組
   - ✅ **配置詳情** 標籤自動選擇 Test-KVM01
   - ✅ 底部顯示：`共 1 個主機 / X 個群組`

#### 測試 3：不同 Job 的過濾
1. 測試其他 Job（例如 Test-ESXi01）
2. 點擊「配置」按鈕
3. **驗證**：
   - ✅ 只顯示 Test-ESXi01 主機
   - ✅ 不會顯示其他主機（如 Test-KVM01）

### 2. 邊界情況測試

#### 測試 4：Job Name 與 Hostname 不匹配
如果某個 Job 的 name 在 Ansible Inventory 中找不到對應的主機：
- **預期行為**：
  - 主機列表：顯示空表格，提示「暫無資料」
  - 群組：顯示空樹，提示「暫無資料」
  - 配置詳情：下拉選單為空

#### 測試 5：特殊字元 Hostname
測試包含特殊字元的 Job Name（例如 `Test-KVM-01`、`Test_KVM_01`）：
- **驗證**：過濾邏輯正常工作

### 3. UI/UX 測試

#### 測試 6：載入狀態
1. 點擊「配置」按鈕
2. **驗證**：
   - ✅ 顯示載入動畫
   - ✅ 載入完成後顯示過濾後的資料
   - ✅ 顯示成功訊息（快取或最新資料）

#### 測試 7：Tab 切換
1. 打開 Drawer
2. 切換三個標籤頁
3. **驗證**：
   - ✅ 每個標籤頁都只顯示過濾後的資料
   - ✅ 標籤頁數量標籤正確（主機數、群組數）

#### 測試 8：重新載入
1. 打開 Drawer
2. 點擊右上角「重新載入」按鈕
3. **驗證**：
   - ✅ 重新獲取資料
   - ✅ 過濾邏輯依然生效
   - ✅ 只顯示匹配的主機

## 📊 測試檢查表

| 測試項目 | 狀態 | 備註 |
|---------|------|------|
| 按鈕在 Build row 顯示 | ⬜ | |
| 按鈕在 Job row 不顯示 | ⬜ | |
| 主機列表只顯示匹配主機 | ⬜ | |
| 群組樹只顯示相關群組 | ⬜ | |
| 配置詳情自動選擇主機 | ⬜ | |
| 底部統計數字正確 | ⬜ | |
| 不同 Job 過濾正確 | ⬜ | |
| 載入狀態顯示正常 | ⬜ | |
| 重新載入功能正常 | ⬜ | |
| 無匹配主機時顯示正常 | ⬜ | |

## 🐛 已知問題

無

## 📝 開發筆記

### 設計決策

1. **為什麼過濾而不是修改 API？**
   - API 返回完整的 Ansible Inventory（所有主機）
   - 前端根據 `hostname` prop 過濾顯示
   - 優點：API 保持通用性，前端靈活控制顯示邏輯

2. **為什麼使用 job_name 作為 hostname？**
   - Jenkins Job Name 通常與主機名稱相同（例如 Test-KVM01）
   - 提供了天然的對應關係
   - 用戶體驗直觀：點擊 Test-KVM01 job 看到 Test-KVM01 主機配置

3. **過濾邏輯位置選擇**
   - 在 `AnsibleConfigDrawer.jsx` 的 `fetchInventoryData()` 函數中過濾
   - 早期過濾可減少不必要的狀態更新
   - 三個子組件（Tab）都自動獲得過濾後的資料

### 實現細節

**HostList 過濾**：
```javascript
hostList = hostList.filter(h => h.hostname === hostname);
```

**Tree 過濾（兩步）**：
```javascript
tree = tree.map(group => ({
    ...group,
    children: group.children.filter(child => 
        child.hostname === hostname
    )
})).filter(group => group.children.length > 0);
```
- 第一步：過濾每個 group 的 children，只保留匹配的主機
- 第二步：移除沒有任何主機的空 group

**自動選擇配置詳情**：
```javascript
initialHostname={hostname || selectedHostForConfig}
```
- 優先使用傳入的 `hostname`（從 Build row 點擊）
- 如果沒有，使用用戶在其他 Tab 選擇的主機

## 🔗 相關文檔

- [功能總覽](./README.md)
- [測試指南](./TESTING_GUIDE.md)
- [API 說明](../../api/ansible-inventory.md)

## 📌 總結

此次更新實現了：
1. ✅ 將「配置」按鈕從 Job row 移至 Build row
2. ✅ 根據 Job Name 過濾顯示匹配的主機
3. ✅ 三個標籤頁（主機列表、群組、配置詳情）都只顯示過濾後的資料
4. ✅ 自動選擇匹配的主機在配置詳情標籤
5. ✅ 保持 API 的通用性，過濾邏輯在前端實現

**改善的用戶體驗**：
- 從 21 個主機減少到 1 個主機（針對性查看）
- 減少干擾資訊，提高查看效率
- 符合用戶工作流程：查看特定 Build 的配置

**技術實現**：
- 最小化變更範圍（只修改 2 個檔案）
- 保持代碼可讀性和可維護性
- 兼容原有的「查看所有主機」功能（不傳 hostname 則顯示全部）
