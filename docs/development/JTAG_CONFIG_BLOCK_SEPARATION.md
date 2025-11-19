# JTAG 配置獨立顯示實施記錄

## 📋 需求說明

根據用戶反饋，需要將 JTAG 相關的參數獨立成一個單獨的區塊（Block），類似於 UART 連接資訊和測試案例配置的顯示方式。

### 涉及的參數

以下參數從「其他配置」移至獨立的「JTAG 配置」區塊：

| 參數名稱 | 顯示標籤 | 說明 |
|---------|---------|------|
| `enable_jtag_dump` | 啟用 JTAG Dump | 是否啟用 JTAG 數據轉儲 |
| `jtag_serial` | JTAG 序列號 | JTAG 設備序列號 |
| `firmware_sku_keyword` | Firmware SKU 關鍵字 | 韌體 SKU 識別關鍵字 |
| `jtag_dump_upload_dir` | JTAG Dump 上傳目錄 | JTAG 數據上傳目錄路徑 |
| `firmware_polling_dir` | Firmware 輪詢目錄 | 韌體輪詢目錄路徑 |

---

## 🛠️ 實施內容

### 1. 前端組件修改

**檔案**：`frontend/src/components/AnsibleConfig/HostConfigTab.jsx`

#### 1.1 新增 JTAG 配置項目過濾

```javascript
// JTAG 相關配置（根據 key 識別）
const jtagItems = configItems.filter(item => {
    const jtagKeys = [
        'enable_jtag_dump', 
        'jtag_serial', 
        'firmware_sku_keyword',
        'jtag_dump_upload_dir',
        'firmware_polling_dir'
    ];
    return jtagKeys.includes(item.key);
});
```

#### 1.2 更新 Ansible 變數過濾規則

排除 JTAG 相關欄位，避免重複顯示：

```javascript
const ansibleItems = configItems.filter(item => {
    // ... 其他排除邏輯
    
    // 排除已在 JTAG 區塊顯示的欄位
    const jtagKeys = ['enable_jtag_dump', 'jtag_serial', 'firmware_sku_keyword', 'jtag_dump_upload_dir', 'firmware_polling_dir'];
    if (jtagKeys.includes(item.key)) return false;
    
    // ...
});
```

#### 1.3 更新「其他配置」過濾規則

```javascript
const otherItems = configItems.filter(item => {
    // ... 其他排除邏輯
    
    // 排除 JTAG 資訊
    const jtagKeys = ['enable_jtag_dump', 'jtag_serial', 'firmware_sku_keyword', 'jtag_dump_upload_dir', 'firmware_polling_dir'];
    if (jtagKeys.includes(item.key)) return false;
    
    // ...
});
```

#### 1.4 新增 JTAG 配置卡片渲染

在 UART 連接資訊卡片後新增：

```jsx
{/* JTAG 配置卡片 */}
{jtagItems.length > 0 && (
    <Card 
        title={
            <Space>
                <CodeOutlined />
                JTAG 配置
            </Space>
        }
        size="small"
        style={{ 
            borderColor: '#722ed1',
            boxShadow: '0 2px 8px rgba(114, 46, 209, 0.1)'
        }}
    >
        <Descriptions 
            column={2} 
            bordered
            size="small"
        >
            {jtagItems.map(item => (
                <Descriptions.Item 
                    key={item.key} 
                    label={<Text strong>{item.label}</Text>}
                >
                    <Text copyable={item.value !== 'N/A'}>
                        {item.value}
                    </Text>
                </Descriptions.Item>
            ))}
        </Descriptions>
    </Card>
)}
```

---

### 2. 服務層修改

**檔案**：`frontend/src/services/ansibleService.js`

#### 2.1 新增 JTAG 參數標籤定義

在 `formatConfigForDisplay()` 函數的 `importantFields` 中新增：

```javascript
const importantFields = {
    // ... 其他欄位
    
    // JTAG 配置（獨立區塊）
    enable_jtag_dump: '啟用 JTAG Dump',
    jtag_serial: 'JTAG 序列號',
    firmware_sku_keyword: 'Firmware SKU 關鍵字',
    jtag_dump_upload_dir: 'JTAG Dump 上傳目錄',
    firmware_polling_dir: 'Firmware 輪詢目錄',
    
    // ... 其他欄位
};
```

---

## 🎨 UI 設計

### 顯示順序

主機配置頁面的區塊顯示順序為：

1. **基本資訊** 
   - IP 地址、設備號、樣品號、MAC 地址

2. **UART 連接資訊** 📱 (藍色邊框 `#1890ff`)
   - UART ID、UART 主機、UART IP、使用者、密碼

3. **JTAG 配置** 🔧 (紫色邊框 `#722ed1`) ✨ **NEW**
   - 啟用 JTAG Dump、JTAG 序列號、Firmware SKU 關鍵字、上傳目錄、輪詢目錄

4. **測試案例配置** 🧪 (綠色邊框 `#52c41a`)
   - testcase_set、測試項目配置

5. **Ansible 變數**
   - ansible_* 相關變數（排除已在其他區塊顯示的欄位）

6. **其他配置**
   - 未分類的其他參數

### 視覺特徵

- **圖標**：`<CodeOutlined />` (代碼圖標)
- **邊框顏色**：`#722ed1` (紫色)
- **陰影**：`0 2px 8px rgba(114, 46, 209, 0.1)` (淡紫色陰影)
- **佈局**：2 列表格佈局（與其他區塊一致）

---

## ✅ 功能驗證

### 驗證步驟

1. **查看主機配置**
   - 進入 Ansible Inventory 管理頁面
   - 選擇包含 JTAG 參數的主機
   - 查看配置詳情

2. **檢查 JTAG 區塊**
   - ✅ JTAG 配置顯示為獨立區塊
   - ✅ 所有 JTAG 相關參數都顯示在此區塊
   - ✅ 紫色邊框和陰影樣式正確
   - ✅ 參數標籤顯示為中文

3. **檢查其他區塊**
   - ✅ 「其他配置」區塊不再包含 JTAG 參數
   - ✅ 「Ansible 變數」區塊不再包含 JTAG 參數
   - ✅ 其他區塊顯示正常

4. **功能測試**
   - ✅ 複製功能正常
   - ✅ 區塊折疊/展開正常
   - ✅ 快取提示正常顯示

---

## 📝 相關檔案

| 檔案路徑 | 修改內容 |
|---------|---------|
| `frontend/src/components/AnsibleConfig/HostConfigTab.jsx` | 新增 JTAG 配置區塊渲染邏輯 |
| `frontend/src/services/ansibleService.js` | 新增 JTAG 參數標籤定義 |

---

## 🔄 相關功能

- [測試案例配置獨立顯示](./TESTCASE_BLOCK_SEPARATION_PLAN.md)
- [UART 連接資訊顯示](./UART_CONNECTION_INFO_DISPLAY.md)
- [主機配置分類顯示架構](./HOST_CONFIG_CATEGORIZATION.md)

---

## 📅 實施時間

- **需求提出**：2025-11-20
- **實施完成**：2025-11-20
- **實施者**：GitHub Copilot

---

## 💡 設計考量

### 為什麼選擇紫色邊框？

- 🔵 藍色 (`#1890ff`) 已用於 UART 連接資訊
- 🟢 綠色 (`#52c41a`) 已用於測試案例配置
- 🟣 紫色 (`#722ed1`) 可以區別於其他區塊，且與技術/調試相關

### 為什麼使用 `<CodeOutlined />` 圖標？

- JTAG 是低階的硬體調試介面
- 代碼圖標符合技術性和調試性質
- 與其他區塊圖標有明確區分

### 參數分組邏輯

JTAG 相關參數包括：
- **控制參數**：`enable_jtag_dump`（開關）
- **識別參數**：`jtag_serial`（設備識別）
- **配置參數**：`firmware_sku_keyword`（韌體識別）
- **路徑參數**：`jtag_dump_upload_dir`、`firmware_polling_dir`（檔案路徑）

這些參數都與 JTAG 調試和韌體管理相關，適合獨立為一個邏輯區塊。

---

## 🎯 後續改進建議

1. **條件渲染優化**
   - 如果沒有啟用 JTAG（`enable_jtag_dump` 為 false），可以考慮使用灰色樣式

2. **參數驗證**
   - 可以新增 `jtag_serial` 格式驗證
   - 可以新增路徑有效性檢查

3. **說明文字**
   - 為每個參數新增 Tooltip 說明其用途
   - 新增 JTAG 配置區塊的整體說明

4. **關聯顯示**
   - 顯示 JTAG 相關的日誌檔案
   - 顯示最近的 JTAG dump 記錄

---

## 📖 參考資料

- [Ant Design - Card 組件](https://ant.design/components/card/)
- [Ant Design - Descriptions 組件](https://ant.design/components/descriptions/)
- [JTAG 標準規範](https://en.wikipedia.org/wiki/JTAG)

---

**文檔版本**：v1.0  
**最後更新**：2025-11-20
