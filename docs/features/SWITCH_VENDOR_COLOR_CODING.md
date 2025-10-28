# Switch 設備顏色標記功能

> **功能**：在租約列表的「製造商」欄位中，自動識別 Switch 設備並以紅色標籤顯示

## 📋 目錄

- [功能概述](#功能概述)
- [識別方法](#識別方法)
- [顏色編碼](#顏色編碼)
- [識別結果](#識別結果)
- [技術實現](#技術實現)
- [使用說明](#使用說明)

---

## 功能概述

在 DHCP 租約管理頁面中，系統會自動識別網路設備製造商，並根據設備類型使用不同顏色的標籤：

- **🔴 紅色**：Switch / 網路交換機（專業網路設備廠商）
- **🔵 藍色**：一般設備（電腦、手機、印表機等）
- **⚪ 灰色**：未知設備（Unknown）

這樣可以快速在租約列表中識別出網路基礎設施設備。

---

## 識別方法

### 方法一：製造商白名單（已採用）

**原理**：基於製造商是否為專業網路設備廠商來判斷

**Switch 製造商白名單**：

| 製造商 | 信賴度 | 說明 |
|--------|--------|------|
| **Cisco Systems, Inc** | ⭐⭐⭐⭐⭐ | 全球最大網路設備廠商 |
| **Juniper Networks** | ⭐⭐⭐⭐⭐ | 企業級網路設備 |
| **Extreme Networks** | ⭐⭐⭐⭐⭐ | 專業交換機廠商 |
| **Brocade** | ⭐⭐⭐⭐⭐ | 數據中心交換機 |
| **Allied Telesis** | ⭐⭐⭐⭐⭐ | 專業網路設備 |
| **Zyxel Communications** | ⭐⭐⭐⭐ | 中小企業交換機 |
| **Aruba** | ⭐⭐⭐⭐ | HP 旗下無線/交換機品牌 |
| **HP / Hewlett Packard** | ⭐⭐⭐⭐ | ProCurve 系列交換機 |
| **H3C** | ⭐⭐⭐⭐ | 華為旗下企業網路設備 |
| **Huawei Technologies** | ⭐⭐⭐ | 企業級網路設備 |
| **D-Link Corporation** | ⭐⭐⭐ | SMB 交換機 |
| **TP-Link** | ⭐⭐⭐ | 家用/SMB 交換機 |
| **Netgear** | ⭐⭐⭐ | 家用/SMB 交換機 |
| **Ubiquiti** | ⭐⭐⭐ | UniFi 系列交換機 |

**判斷邏輯**：
```javascript
// 檢查製造商名稱是否包含白名單中的任一廠商
const isSwitchVendor = (vendor) => {
    return SWITCH_VENDORS.some(switchVendor => 
        vendor.includes(switchVendor) || switchVendor.includes(vendor)
    );
};
```

**優點**：
- ✅ 簡單直觀，維護容易
- ✅ 準確度高（專業網路設備廠商）
- ✅ 性能好（前端判斷，無需 API 請求）

**限制**：
- ⚠️ HP 設備可能包含印表機（但 HP 印表機通常有 "VN" 主機名稱）
- ⚠️ Huawei 設備可能包含手機/路由器
- ⚠️ 需要定期更新白名單（新廠商）

---

## 顏色編碼

### 顏色規則

| 顏色 | Ant Design Tag | 適用條件 | 範例 |
|------|----------------|----------|------|
| 🔴 **紅色** | `<Tag color="red">` | 製造商在 Switch 白名單中 | Cisco Systems, Inc<br>Zyxel Communications |
| 🔵 **藍色** | `<Tag color="blue">` | 已識別，但非 Switch 廠商 | ASUSTek COMPUTER INC.<br>Intel Corporate |
| ⚪ **灰色** | `<Tag color="default">` | 未識別（Unknown） | Unknown |

### 視覺效果

```
┌──────────────┬──────────────────┬────────────────────────────┐
│ IP 位址      │ MAC 位址         │ 製造商                     │
├──────────────┼──────────────────┼────────────────────────────┤
│ 10.250.54.12 │ 50:e0:39:fe:57:0d│ 🔴 Zyxel Communications    │  ← Switch (紅色)
│ 10.250.55.34 │ 58:11:22:c8:b9:3c│ 🔵 ASUSTek COMPUTER INC.   │  ← 電腦 (藍色)
│ 10.250.55.30 │ 48:21:0b:35:bc:26│ 🔵 Intel Corporate         │  ← 網卡 (藍色)
│ 10.250.55.99 │ aa:bb:cc:dd:ee:ff│ ⚪ Unknown                 │  ← 未知 (灰色)
└──────────────┴──────────────────┴────────────────────────────┘
```

---

## 識別結果

### 本專案實際數據（2025-10-29）

**測試範圍**：100 筆租約  
**識別結果**：

- 🔴 **Switch 設備**：6 台（6%）
- 🔵 **一般設備**：94 台（94%）
- ⚪ **未知設備**：0 台（0%）

### 識別出的 Switch 設備清單

| IP 位址 | MAC 位址 | 主機名稱 | 製造商 | 判斷 |
|---------|----------|----------|--------|------|
| 10.250.54.12 | 50:e0:39:fe:57:0d | GS1915 | Zyxel Communications | ✅ Switch |
| 10.250.53.21 | 50:e0:39:fe:58:5f | GS1915 | Zyxel Communications | ✅ Switch |
| 10.250.53.12 | 50:e0:39:fe:58:79 | GS1915 | Zyxel Communications | ✅ Switch |
| 10.250.52.23 | d4:1a:d1:fb:7c:2e | GS1915 | Zyxel Communications | ✅ Switch |
| 10.250.53.60 | 0c:97:5f:64:b5:c0 | VN27KYC0BV | Hewlett Packard | ⚠️ 可能是印表機 |
| 10.250.53.32 | 34:c5:15:c0:ca:a0 | VN51KYC224 | Hewlett Packard | ⚠️ 可能是印表機 |

**分析**：
- ✅ Zyxel GS1915 系列：**確定是 Switch**（從主機名稱可確認）
- ⚠️ HP VN... 系列：**可能是印表機**（HP 命名規則）

---

## 技術實現

### 前端代碼（React）

**檔案**：`frontend/src/components/dhcp-analytics/LeasesTab.js`

#### 1. 定義 Switch 白名單

```javascript
const LeasesTab = ({ serverId }) => {
    // Switch 製造商白名單（方法一：高信賴度廠商）
    const SWITCH_VENDORS = [
        'Cisco Systems, Inc',
        'Cisco Systems',
        'Juniper Networks',
        'Extreme Networks',
        'Brocade',
        'Allied Telesis',
        'Zyxel Communications Corporation',
        'Zyxel',
        'Aruba',
        'HP',
        'Hewlett Packard Enterprise',
        'H3C',
        'Huawei Technologies',
        'D-Link Corporation',
        'TP-Link',
        'Netgear',
        'Ubiquiti',
    ];

    // ...
};
```

#### 2. 判斷函數

```javascript
// 判斷是否為 Switch
const isSwitchVendor = (vendor) => {
    if (!vendor || vendor === 'Unknown') return false;
    
    // 檢查製造商是否在白名單中（部分匹配）
    return SWITCH_VENDORS.some(switchVendor => 
        vendor.includes(switchVendor) || switchVendor.includes(vendor)
    );
};
```

#### 3. 表格欄位渲染

```javascript
{
    title: '製造商',
    dataIndex: 'vendor',
    key: 'vendor',
    sorter: (a, b) => a.vendor.localeCompare(b.vendor),
    render: (vendor) => {
        // 判斷是否為 Switch
        const isSwitch = isSwitchVendor(vendor);
        
        // 根據類型設置顏色
        let color = 'default';  // Unknown 預設灰色
        if (vendor !== 'Unknown') {
            color = isSwitch ? 'red' : 'blue';  // Switch 紅色，其他藍色
        }
        
        return (
            <Tag color={color}>
                {vendor}
            </Tag>
        );
    },
    // ...
}
```

### 資料來源

**後端 API**：`/api/dhcp-leases/`

**回應格式**：
```json
{
    "count": 603,
    "results": [
        {
            "id": 1,
            "ip_address": "10.250.54.12",
            "mac_address": "50:e0:39:fe:57:0d",
            "hostname": "GS1915",
            "vendor": "Zyxel Communications Corporation",
            "is_active": true,
            "lease_start": "2025-10-28T10:30:00Z",
            "lease_end": "2025-10-29T10:30:00Z"
        }
    ]
}
```

**vendor 欄位來源**：
- 由後端 `DHCPLeaseSerializer` 的 `get_vendor()` 方法產生
- 使用 `api.utils.mac_vendor.get_vendor_from_mac()` 查詢 IEEE OUI 資料庫
- 資料庫包含 38,254 筆 OUI 記錄

---

## 使用說明

### 如何查看

1. **訪問**：http://localhost
2. **進入**：DHCP Server 分析
3. **點擊**：租約管理標籤
4. **觀察**：製造商欄位的顏色

### 顏色含義

- **看到紅色標籤**：這是一台 Switch 或網路設備（Zyxel, Cisco, HP 等）
- **看到藍色標籤**：這是一般設備（電腦、手機、印表機等）
- **看到灰色標籤**：無法識別製造商（可能是虛擬機、自定義 MAC）

### 實用技巧

#### 1. 快速找出所有 Switch

1. 點擊「製造商」欄位標題排序
2. 紅色標籤會聚集在一起
3. 方便清點網路基礎設施

#### 2. 識別異常設備

- 如果看到不熟悉的紅色標籤 → 可能有未授權的網路設備
- 如果 Switch 顯示為藍色 → 可能製造商不在白名單中，需要更新

#### 3. 網路設備盤點

1. 篩選出所有紅色標籤設備
2. 匯出 CSV
3. 與網路拓撲圖對照

---

## 未來改進

### 階段 2：結合 Hostname 關鍵字

**目標**：提高 HP 設備的識別準確度

**方法**：
```javascript
const isSwitchDevice = (vendor, hostname) => {
    // 先判斷製造商
    if (!isSwitchVendor(vendor)) return false;
    
    // HP 設備需要額外判斷 Hostname
    if (vendor.includes('Hewlett Packard')) {
        // VN... 通常是印表機
        if (hostname && hostname.startsWith('VN')) return false;
        
        // ProCurve, Aruba, 5120 等是 Switch
        const switchKeywords = ['ProCurve', 'Aruba', '5120', '5130', 'Switch'];
        return switchKeywords.some(kw => hostname.includes(kw));
    }
    
    return true;
};
```

### 階段 3：設備類型圖標

**目標**：除了顏色，還顯示設備類型圖標

| 設備類型 | 圖標 | 顏色 |
|----------|------|------|
| Switch | 🔀 | 紅色 |
| Router | 🌐 | 橙色 |
| AP | 📡 | 紫色 |
| Printer | 🖨️ | 綠色 |
| PC | 💻 | 藍色 |

### 階段 4：自動學習

**目標**：根據網路行為自動學習設備類型

**方法**：
- 分析 ARP 表（高流量設備可能是 Switch）
- 分析 LLDP/CDP 協定（設備主動宣告）
- 分析連接埠數量（Switch 通常有多個 MAC 通過）

---

## 相關文檔

- [Switch 設備識別方法大全](./SWITCH_DETECTION_METHODS.md) - 各種 Switch 識別方法
- [MAC 廠商識別](./MAC_VENDOR_IDENTIFICATION.md) - OUI 資料庫說明
- [租約列表製造商欄位](./LEASES_VENDOR_COLUMN.md) - 製造商欄位完整說明

---

## 變更記錄

| 日期 | 版本 | 變更內容 |
|------|------|----------|
| 2025-10-29 | v1.0 | 初版：實現方法一（製造商白名單） |

---

**更新時間**：2025-10-29  
**作者**：Network Toolbox Team  
**功能狀態**：✅ 已上線
