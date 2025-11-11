# Ansible Inventory 配置查看器 - 功能文檔

## 📋 概述

在 Jenkins RVT 分析頁面添加「配置」按鈕，點擊後可以查看該 Job 的 Ansible Inventory 配置資訊。

**位置**: RVT 分析 → Jenkins 詳細 → Job 操作欄 → ⚙️ 配置

---

## 🎯 功能特性

### 1. **主機列表查看**
- 顯示所有主機的表格（支援排序、搜尋、分頁）
- 可複製 IP、設備號、主機名稱
- 點擊「查看配置」跳轉到詳細配置

### 2. **群組樹狀圖**
- 顯示群組階層結構
- 支援展開/收起、搜尋
- 點擊主機直接查看配置

### 3. **主機配置詳情**
- 顯示完整的主機配置（基本資訊、Ansible 變數、其他配置）
- 支援複製單個值或完整 JSON
- 展開查看格式化的 JSON

### 4. **快取機制**
- 首次獲取後快取 7 天
- 提升載入速度（10-30 倍）
- 支援強制重新載入

---

## 🏗️ 技術架構

### 前端組件

```
frontend/src/
├── services/
│   └── ansibleService.js          # API 封裝服務
└── components/
    └── AnsibleConfig/
        ├── AnsibleConfigDrawer.jsx  # 主 Drawer 組件
        ├── HostListTab.jsx          # 主機列表標籤
        ├── GroupTreeTab.jsx         # 群組樹標籤
        ├── HostConfigTab.jsx        # 配置詳情標籤
        └── index.js                 # 導出
```

### 後端 API（已存在）

| 端點 | 方法 | 說明 |
|------|------|------|
| `/api/jenkins-jobs/{id}/ansible-inventory/` | GET | 獲取完整 inventory |
| `/api/jenkins-jobs/{id}/ansible-inventory/hosts/` | GET | 獲取主機列表 |
| `/api/jenkins-jobs/{id}/ansible-inventory/hosts/{hostname}/` | GET | 獲取特定主機配置 |
| `/api/jenkins-jobs/{id}/ansible-inventory/cache/statistics/` | GET | 快取統計 |
| `/api/jenkins-jobs/{id}/ansible-inventory/cache/` | DELETE | 清除快取 |

---

## 📊 資料流程

```
1. 用戶點擊「配置」按鈕
   ↓
2. 打開 AnsibleConfigDrawer
   ↓
3. 調用 getAnsibleInventory(jobId)
   ↓
4. 後端檢查快取（7 天有效期）
   ↓
5. 返回資料（cached: true/false）
   ↓
6. 前端解析資料：
   - parseInventoryToHostList() → 主機列表
   - parseInventoryToGroupTree() → 群組樹
   ↓
7. 渲染三個標籤頁
```

---

## 🎨 UI 設計

### Drawer 佈局

```
┌─────────────────────────────────────────────────────────┐
│ Ansible Inventory - Test-KVM01 #148   [已快取] [重新載入] │
├─────────────────────────────────────────────────────────┤
│ [主機列表 21]  [群組 12]  [配置詳情]                      │
├─────────────────────────────────────────────────────────┤
│                                                           │
│  (標籤頁內容)                                              │
│                                                           │
│                                                           │
│                                                           │
│                                                           │
│                                                           │
│                                                           │
├─────────────────────────────────────────────────────────┤
│ 📊 共 21 個主機 | 📁 12 個群組 | ⚡ 使用快取資料          │
└─────────────────────────────────────────────────────────┘
```

### 主機列表表格

| 主機名稱 | IP 地址 | 設備號 | MAC 地址 | 使用者 | 群組 | 操作 |
|---------|--------|--------|---------|-------|------|------|
| Test-KVM01 | 10.250.71.22 [📋] | PC-SSD-4632 [📋] | ... | administrator | [PQ1_3][PQ1_3_K01] | [查看配置] |

### 群組樹狀圖

```
📁 PQ1_3 (7 個主機)
├─ 💻 Test-KVM03
├─ 💻 Test-KVM04
└─ 💻 Test-KVM05

📁 PQ1_3_K01 (1 個主機)
└─ 💻 Test-KVM01
```

### 配置詳情卡片

```
┌───────────────────────────────────────┐
│ 💻 Test-KVM01             [複製 JSON]  │
├───────────────────────────────────────┤
│ 基本資訊                               │
│ • IP 地址: 10.250.71.22    [📋]        │
│ • 設備號: PC-SSD-4632       [📋]        │
│ • MAC: 10:7C:61:45:F8:36   [📋]        │
└───────────────────────────────────────┘

┌───────────────────────────────────────┐
│ Ansible 變數                           │
│ • ansible_user: administrator   [📋]   │
│ • ansible_shell_type: sh        [📋]   │
└───────────────────────────────────────┘

┌───────────────────────────────────────┐
│ ▼ 完整配置 (JSON)                      │
│   {                                    │
│     "ansible_host": "10.250.71.22",    │
│     "device_number": "PC-SSD-4632",    │
│     ...                                │
│   }                                    │
└───────────────────────────────────────┘
```

---

## 🚀 使用場景

### 場景 1：查詢主機 IP
1. 點擊「配置」按鈕
2. 在主機列表搜尋主機名稱
3. 查看 IP 並複製

### 場景 2：查看群組結構
1. 點擊「配置」按鈕
2. 切換到「群組」標籤
3. 展開群組查看成員

### 場景 3：獲取完整配置
1. 點擊「配置」按鈕
2. 切換到「配置詳情」標籤
3. 選擇主機
4. 點擊「複製 JSON」

### 場景 4：調試 Ansible 變數
1. 點擊「配置」按鈕
2. 切換到「配置詳情」標籤
3. 選擇主機
4. 查看「Ansible 變數」卡片

---

## ⚡ 效能優化

### 快取策略
- **快取位置**: NAS 檔案系統 (`{build_dir}/cache/`)
- **快取期限**: 7 天
- **快取驗證**: 
  - 版本號匹配
  - 未過期
  - inventory 文件 mtime 未變更

### 延遲載入
- Drawer 打開時才載入資料
- 切換標籤不重複請求
- 配置詳情按需載入

### 資料分頁
- 主機列表：10 筆/頁（可調整）
- 搜尋結果即時過濾
- 樹狀圖虛擬滾動（大量資料時）

---

## 🎯 效能指標

| 指標 | 無快取 | 有快取 | 提升倍數 |
|------|--------|--------|----------|
| 完整 Inventory | 2-3 秒 | 0.1-0.2 秒 | 10-30x |
| 主機列表 | 2-3 秒 | 0.1-0.2 秒 | 10-30x |
| 主機配置 | 0.5-1 秒 | 0.05-0.1 秒 | 10-20x |

---

## 🔒 權限控制

- **訪問權限**: 僅 Admin 用戶
- **API 權限**: 由後端 `AllowAny` 控制（開發環境）
- **生產環境**: 應改為 `IsAuthenticated`

---

## 🐛 錯誤處理

### 前端錯誤處理

| 錯誤情況 | 處理方式 |
|---------|---------|
| API 返回 404 | 顯示「此 Build 沒有 Ansible Inventory 資料」 |
| API 返回 500 | 顯示「伺服器錯誤」+錯誤訊息 |
| 網路錯誤 | 顯示「載入失敗」+重試按鈕 |
| 快取失效 | 自動重新獲取 |

### 後端錯誤處理

| 錯誤情況 | 處理方式 |
|---------|---------|
| Inventory 文件不存在 | 返回 404 |
| Ansible 命令執行失敗 | 記錄日誌，返回 500 |
| 快取讀取失敗 | 自動重新生成 |

---

## 📝 開發指南

### 添加新的配置欄位

1. **後端**：已自動包含所有變數
2. **前端**：修改 `formatConfigForDisplay()` 中的 `importantFields`

```javascript
const importantFields = {
    ansible_host: 'IP 地址',
    device_number: '設備號',
    new_field: '新欄位',  // ← 添加新欄位
    // ...
};
```

### 自訂表格欄位

修改 `HostListTab.jsx` 的 `columns` 陣列：

```javascript
{
    title: '新欄位',
    dataIndex: 'new_field',
    key: 'new_field',
    width: 150,
    sorter: (a, b) => a.new_field.localeCompare(b.new_field),
}
```

### 修改快取期限

修改後端 `AnsibleInventoryService` 的 `CACHE_EXPIRY_DAYS`：

```python
CACHE_EXPIRY_DAYS = 7  # 改為其他天數
```

---

## 📚 相關文檔

- [測試指南](./TESTING_GUIDE.md)
- [Ansible Inventory Service](../../../backend/library/services/ansible_inventory_service.py)
- [API Views](../../../backend/api/views/jenkins.py)
- [Celery 清理任務](../../../backend/api/tasks.py)

---

## 🔄 更新日誌

### v1.0.0 (2025-11-11)
- ✅ 初始版本
- ✅ 主機列表、群組樹、配置詳情三個標籤
- ✅ 快取機制（7 天）
- ✅ 搜尋、排序、分頁功能
- ✅ 複製功能
- ✅ 錯誤處理

---

**維護者**: Network Toolbox Team  
**最後更新**: 2025-11-11
