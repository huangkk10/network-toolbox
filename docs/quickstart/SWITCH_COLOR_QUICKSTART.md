# Switch 紅色標記功能 - 快速指南

## 🎯 功能說明

在租約列表的「製造商」欄位中，**Switch 設備會以紅色標籤顯示**，方便快速識別網路基礎設施。

## 🎨 顏色編碼

| 顏色 | 設備類型 | 範例製造商 |
|------|----------|-----------|
| 🔴 **紅色** | Switch / 網路設備 | Cisco, Zyxel, HP, Juniper |
| 🔵 **藍色** | 一般設備 | ASUSTek, Intel, Realtek |
| ⚪ **灰色** | 未知設備 | Unknown |

## 📸 視覺效果

### 更新前
```
┌──────────────┬──────────────────┬────────────────────────────┐
│ IP 位址      │ MAC 位址         │ 製造商                     │
├──────────────┼──────────────────┼────────────────────────────┤
│ 10.250.54.12 │ 50:e0:39:fe:57:0d│ Zyxel Communications  🔵   │  全部藍色
│ 10.250.55.34 │ 58:11:22:c8:b9:3c│ ASUSTek COMPUTER INC. 🔵   │
│ 10.250.55.30 │ 48:21:0b:35:bc:26│ Intel Corporate       🔵   │
└──────────────┴──────────────────┴────────────────────────────┘
```

### ✅ 更新後
```
┌──────────────┬──────────────────┬────────────────────────────┐
│ IP 位址      │ MAC 位址         │ 製造商                     │
├──────────────┼──────────────────┼────────────────────────────┤
│ 10.250.54.12 │ 50:e0:39:fe:57:0d│ Zyxel Communications  🔴   │  ← Switch (紅色)
│ 10.250.55.34 │ 58:11:22:c8:b9:3c│ ASUSTek COMPUTER INC. 🔵   │  ← 電腦 (藍色)
│ 10.250.55.30 │ 48:21:0b:35:bc:26│ Intel Corporate       🔵   │  ← 網卡 (藍色)
└──────────────┴──────────────────┴────────────────────────────┘
```

## 🔍 識別的 Switch 製造商清單

### 專業網路設備廠商（高信賴度）

✅ 這些製造商的設備會顯示**紅色標籤**：

| 製造商 | 常見型號/產品線 |
|--------|----------------|
| **Cisco Systems** | Catalyst, Nexus, Meraki |
| **Juniper Networks** | EX, QFX, SRX 系列 |
| **Extreme Networks** | Summit, VSP 系列 |
| **Brocade** | FastIron, ICX 系列 |
| **Allied Telesis** | x-series |
| **Zyxel Communications** | GS 系列（如 GS1915） |
| **Aruba** | 2530, 2540, CX 系列 |
| **HP / Hewlett Packard** | ProCurve 系列 |
| **H3C** | S5120, S5130 系列 |
| **Huawei Technologies** | S5700, S6720 系列 |
| **D-Link Corporation** | DGS, DES 系列 |
| **TP-Link** | TL-SG, T-series |
| **Netgear** | GS, MS 系列 |
| **Ubiquiti** | UniFi Switch |

## 📊 您的網路實際數據

**統計時間**：2025-10-29  
**測試範圍**：100 筆租約

### 識別結果

- 🔴 **Switch 設備**：6 台（6%）
- 🔵 **一般設備**：94 台（94%）
- ⚪ **未知設備**：0 台（0%）

### 識別出的 Switch 清單

| IP 位址 | 主機名稱 | 製造商 | 標籤顏色 |
|---------|----------|--------|----------|
| 10.250.54.12 | GS1915 | Zyxel Communications | 🔴 紅色 |
| 10.250.53.21 | GS1915 | Zyxel Communications | 🔴 紅色 |
| 10.250.53.12 | GS1915 | Zyxel Communications | 🔴 紅色 |
| 10.250.52.23 | GS1915 | Zyxel Communications | 🔴 紅色 |
| 10.250.53.60 | VN27KYC0BV | Hewlett Packard Enterprise | 🔴 紅色 * |
| 10.250.53.32 | VN51KYC224 | Hewlett Packard Enterprise | 🔴 紅色 * |

**註**：標記 * 的 HP 設備可能是印表機（從 Hostname "VN..." 判斷），但因製造商在白名單中仍標記為紅色。

## 💡 使用技巧

### 1️⃣ 快速盤點 Switch

**方法**：點擊「製造商」欄位排序
- 所有紅色標籤會聚集在一起
- 方便統計網路設備數量

### 2️⃣ 識別異常設備

**觀察**：
- ✅ 預期的 Switch（如 Zyxel GS1915）顯示紅色 → 正常
- ⚠️ 陌生的紅色標籤設備 → 可能是未授權的網路設備
- ❓ Switch 顯示藍色 → 製造商不在白名單中，需要更新

### 3️⃣ 匯出網路設備清單

1. 點擊「匯出 CSV」
2. 在 Excel 中篩選紅色標籤設備
3. 生成網路設備盤點報告

## 🚀 立即體驗

1. **訪問**：http://localhost
2. **進入**：DHCP Server 分析 → 租約管理
3. **觀察**：製造商欄位的顏色變化

**預期看到**：
- Zyxel Communications → 🔴 紅色標籤
- ASUSTek COMPUTER INC. → 🔵 藍色標籤
- Unknown → ⚪ 灰色標籤

## 🔧 技術細節

### 判斷邏輯

```javascript
// 如果製造商在這個清單中 → 顯示紅色
const SWITCH_VENDORS = [
    'Cisco Systems, Inc',
    'Juniper Networks',
    'Zyxel Communications Corporation',
    'Aruba',
    'HP',
    // ... 更多
];

// 判斷函數
const isSwitchVendor = (vendor) => {
    return SWITCH_VENDORS.some(sv => 
        vendor.includes(sv) || sv.includes(vendor)
    );
};
```

### 顏色設置

```javascript
let color = 'default';  // 預設灰色
if (vendor !== 'Unknown') {
    color = isSwitchVendor(vendor) ? 'red' : 'blue';
}
```

## 📚 相關文檔

- [完整功能說明](./SWITCH_VENDOR_COLOR_CODING.md)
- [Switch 識別方法](./SWITCH_DETECTION_METHODS.md)
- [製造商欄位說明](./LEASES_VENDOR_COLUMN.md)

---

**更新時間**：2025-10-29  
**功能狀態**：✅ 已上線  
**版本**：v1.0
