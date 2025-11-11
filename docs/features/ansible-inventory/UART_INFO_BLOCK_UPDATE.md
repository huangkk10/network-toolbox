# Ansible 配置查看器 - UART 資訊區塊更新

## 📋 更新日期
2025-11-11

## 🎯 更新內容

### 需求背景
用戶希望將 UART 相關的連接資訊獨立成一個顯眼的區塊，便於快速查看主機的 UART 連接配置。

### 實現功能
在「配置詳情」標籤頁中，新增 **UART 連接資訊** 獨立卡片區塊，包含：

| 欄位 | 說明 | 範例值 |
|------|------|--------|
| UART ID | UART 設備識別碼 | KVM01 |
| UART 主機 | UART 集線器主機名稱 | UART-HUB00 |
| 使用者 | 連接使用的帳號 | administrator |
| 密碼 | 連接使用的密碼 | 1.a |

### UI 設計特點

1. **獨立卡片**：與「基本資訊」、「Ansible 變數」並列
2. **顯眼標識**：
   - 藍色邊框 (`borderColor: #1890ff`)
   - 淡藍色陰影 (`boxShadow: rgba(24, 144, 255, 0.1)`)
   - 圖標：`<DesktopOutlined />`
3. **密碼特殊樣式**：
   - 紅色文字 (`color: #ff4d4f`)
   - 等寬字體 (`fontFamily: monospace`)
4. **可複製**：所有欄位都支援點擊複製按鈕

## 🔧 代碼變更

### 1. HostConfigTab.jsx

#### 1.1 過濾邏輯更新

**UART 資訊過濾**：
```javascript
// UART 相關配置（根據 key 或 label 識別）
const uartItems = configItems.filter(item => {
    // 根據 key 識別
    const uartKeys = ['uart_id', 'uart_host', 'ansible_user', 'ansible_password'];
    if (uartKeys.includes(item.key)) return true;
    
    // 根據 label 識別（中文）
    const uartLabels = ['UART ID', 'UART 主機', '使用者', '密碼'];
    if (uartLabels.includes(item.label)) return true;
    
    return false;
});
```

**Ansible 變數過濾（排除 UART 相關）**：
```javascript
const ansibleItems = configItems.filter(item => {
    // 排除已在 UART 區塊顯示的欄位
    const excludeKeys = ['ansible_host', 'ansible_user', 'ansible_password', 'uart_id', 'uart_host'];
    if (excludeKeys.includes(item.key)) return false;
    
    // 只保留 ansible_ 開頭的欄位
    return item.key.startsWith('ansible_');
});
```

**其他配置過濾（排除基本資訊和 UART）**：
```javascript
const otherItems = configItems.filter(item => {
    // 排除基本資訊
    const basicKeys = ['ansible_host', 'device_number', 'sample_number', 'macaddress'];
    if (basicKeys.includes(item.key)) return false;
    
    // 排除 UART 資訊
    const uartKeys = ['uart_id', 'uart_host', 'ansible_user', 'ansible_password'];
    if (uartKeys.includes(item.key)) return false;
    
    // 排除 Ansible 變數
    if (item.key.startsWith('ansible_')) return false;
    
    return true;
});
```

#### 1.2 UI 組件新增

在「基本資訊卡片」後、「Ansible 變數」前插入：

```jsx
{/* UART 資訊卡片 */}
{uartItems.length > 0 && (
    <Card 
        title={
            <Space>
                <DesktopOutlined />
                UART 連接資訊
            </Space>
        }
        size="small"
        style={{ 
            borderColor: '#1890ff',
            boxShadow: '0 2px 8px rgba(24, 144, 255, 0.1)'
        }}
    >
        <Descriptions 
            column={2} 
            bordered
            size="small"
        >
            {uartItems.map(item => (
                <Descriptions.Item 
                    key={item.key} 
                    label={<Text strong>{item.label}</Text>}
                >
                    <Text 
                        copyable={item.value !== 'N/A'}
                        style={{ 
                            color: item.label === '密碼' ? '#ff4d4f' : undefined,
                            fontFamily: item.label === '密碼' ? 'monospace' : undefined
                        }}
                    >
                        {item.value}
                    </Text>
                </Descriptions.Item>
            ))}
        </Descriptions>
    </Card>
)}
```

### 2. ansibleService.js

#### 2.1 欄位顯示順序調整

在 `formatConfigForDisplay` 函數中，調整 `importantFields` 的順序：

```javascript
const importantFields = {
    // 基本資訊
    ansible_host: 'IP 地址',
    device_number: '設備號',
    sample_number: '樣品號',
    macaddress: 'MAC 地址',
    
    // UART 連接資訊（獨立區塊）
    uart_id: 'UART ID',
    uart_host: 'UART 主機',
    ansible_user: '使用者',
    ansible_password: '密碼',
    
    // 其他 Ansible 變數
    ansible_shell_type: 'Shell 類型',
    testcase_set: '測試案例集',
    platform_install_vnc: 'VNC 安裝',
    mailto: '郵件通知',
};
```

**重點**：
- 將 `uart_id`, `uart_host`, `ansible_user`, `ansible_password` 歸為一組
- 通過註釋明確標識這是 UART 連接資訊區塊

## 📸 UI 效果

### 顯示位置
```
┌─────────────────────────────────────────┐
│  選擇主機: [Test-KVM01 ▼]               │
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│  📟 Test-KVM01         [複製 JSON]      │
├─────────────────────────────────────────┤
│  IP 地址       │ 10.252.170.252         │
│  設備號        │ KVM01                  │
│  樣品號        │ testcases_demo         │
│  MAC 地址      │ N/A                    │
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐  ← 新增區塊
│  💻 UART 連接資訊                       │  ← 藍色邊框
├─────────────────────────────────────────┤
│  UART ID      │ KVM01          📋       │
│  UART 主機    │ UART-HUB00     📋       │
│  使用者       │ administrator  📋       │
│  密碼         │ 1.a            📋       │  ← 紅色等寬字體
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│  Ansible 變數                           │
├─────────────────────────────────────────┤
│  Shell 類型    │ cmd                    │
│  ...                                     │
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│  其他配置                               │
├─────────────────────────────────────────┤
│  ...                                     │
└─────────────────────────────────────────┘
```

### 視覺特點

1. **顏色區分**：
   - UART 區塊：藍色邊框 + 淡藍色陰影
   - 基本資訊/Ansible 變數：預設灰色邊框
   
2. **標籤加粗**：
   - UART 區塊的標籤使用 `<Text strong>` 加粗
   - 其他區塊使用預設樣式

3. **密碼特殊處理**：
   - 紅色警示色 (#ff4d4f)
   - 等寬字體（方便識別字元）

4. **複製功能**：
   - 所有欄位都有複製按鈕
   - 點擊即可複製到剪貼簿

## 🧪 測試步驟

### 測試 1：UART 區塊顯示
1. 前往 RVT 分析頁面
2. 展開 `Test-KVM01` Job
3. 點擊任一 Build 的「配置」按鈕
4. 切換到「配置詳情」標籤
5. 在主機下拉選單中選擇 `Test-KVM01`

**驗證**：
- ✅ 看到「UART 連接資訊」卡片（藍色邊框）
- ✅ 卡片位於「基本資訊」和「Ansible 變數」之間
- ✅ 顯示 4 個欄位：UART ID、UART 主機、使用者、密碼
- ✅ 標籤文字加粗
- ✅ 密碼為紅色等寬字體

### 測試 2：複製功能
1. 在 UART 區塊中，點擊任一欄位的複製按鈕
2. 貼到文字編輯器中

**驗證**：
- ✅ 成功複製對應的值
- ✅ 顯示「已複製」提示訊息

### 測試 3：不同主機
測試沒有 UART 資訊的主機（如果有）：

**驗證**：
- ✅ 如果沒有 UART 相關欄位，則不顯示「UART 連接資訊」卡片
- ✅ 其他區塊正常顯示

### 測試 4：Ansible 變數不重複
檢查「Ansible 變數」卡片：

**驗證**：
- ✅ 不包含 `ansible_user` 和 `ansible_password`（已移到 UART 區塊）
- ✅ 只顯示其他 Ansible 變數（如 `ansible_shell_type`）

### 測試 5：JSON 檢視
1. 點擊「複製 JSON」按鈕
2. 展開「完整配置 (JSON)」折疊面板

**驗證**：
- ✅ JSON 中仍包含完整的 UART 資訊
- ✅ 複製的 JSON 完整無誤

## 📊 測試檢查表

| 測試項目 | 狀態 | 備註 |
|---------|------|------|
| UART 區塊顯示 | ⬜ | 藍色邊框、4 個欄位 |
| UART 區塊位置正確 | ⬜ | 在基本資訊和 Ansible 變數之間 |
| 標籤加粗 | ⬜ | UART 區塊標籤為粗體 |
| 密碼紅色等寬字體 | ⬜ | 紅色 + monospace |
| 複製功能正常 | ⬜ | 所有欄位可複製 |
| 無 UART 資訊時不顯示 | ⬜ | 區塊自動隱藏 |
| Ansible 變數不重複 | ⬜ | 不包含 user/password |
| JSON 檢視完整 | ⬜ | 包含所有 UART 欄位 |

## 🐛 已知問題

無

## 📝 設計決策

### 為什麼獨立 UART 區塊？

1. **業務重要性**：UART 連接資訊是測試環境的關鍵配置
2. **頻繁查看**：用戶經常需要快速找到 UART 連接資訊
3. **安全提示**：密碼使用紅色警示色，提醒用戶注意保護
4. **視覺區隔**：藍色邊框讓 UART 區塊更顯眼

### 欄位識別邏輯

使用雙重識別機制：
```javascript
// 1. 根據 key 識別（英文欄位名）
const uartKeys = ['uart_id', 'uart_host', 'ansible_user', 'ansible_password'];

// 2. 根據 label 識別（中文顯示名）
const uartLabels = ['UART ID', 'UART 主機', '使用者', '密碼'];
```

**原因**：
- 兼容不同的 Ansible inventory 格式
- 確保即使 key 命名不同，仍能正確識別
- 支援中英文混合顯示

### 為什麼不使用獨立 API？

現有的 `formatConfigForDisplay` 函數已經處理了所有欄位，只需在前端進行分類過濾：

**優點**：
- 不增加後端複雜度
- 前端靈活控制顯示邏輯
- 快取機制依然有效

**實現**：
- `formatConfigForDisplay` 返回所有欄位
- 前端根據 key/label 分類到不同區塊

## 🔗 相關文檔

- [功能總覽](./README.md)
- [測試指南](./TESTING_GUIDE.md)
- [Hostname 過濾更新](./HOSTNAME_FILTER_UPDATE.md)

## 📌 總結

此次更新實現了：
1. ✅ 獨立 UART 連接資訊區塊
2. ✅ 藍色邊框 + 淡藍色陰影，視覺顯眼
3. ✅ 密碼紅色等寬字體，安全提示
4. ✅ 標籤加粗，提升可讀性
5. ✅ 所有欄位可複製，便於使用
6. ✅ 自動隱藏機制（無 UART 資訊時）
7. ✅ 雙重識別邏輯（key + label）

**改善的用戶體驗**：
- 快速找到 UART 連接資訊
- 視覺層次更清晰
- 關鍵資訊（密碼）有安全提示
- 便於複製使用

**技術優勢**：
- 純前端實現，不影響後端 API
- 兼容現有快取機制
- 代碼可讀性高，易於維護
- 支援多種 inventory 格式
