# 租約列表「製造商」欄位更新 - 快速指南

## 🎯 更新內容

在 **DHCP Server 分析 → 組約管理** 頁面的租約列表中新增「製造商」欄位。

## 📸 更新前後對比

### ❌ 更新前

```
┌─────────────┬─────────────────┬───────────────┬────────┬──────────────┐
│ IP 位址     │ MAC 位址        │ 主機名稱      │ 狀態   │ 開始時間     │
├─────────────┼─────────────────┼───────────────┼────────┼──────────────┤
│ 10.250.55.34│ 58:11:22:c8:b9:3c│ ubuntu-pp-... │ 活躍中 │ 2025-10-28...│
│ 10.250.55.31│ 60:cf:84:dc:b1:57│ PC-SSD-5830   │ 活躍中 │ 2025-10-28...│
│ 10.250.55.30│ 48:21:0b:35:bc:26│ DESKTOP-O12...│ 活躍中 │ 2025-10-28...│
└─────────────┴─────────────────┴───────────────┴────────┴──────────────┘
```

### ✅ 更新後

```
┌─────────────┬─────────────────┬──────────────────────┬───────────────┬────────┐
│ IP 位址     │ MAC 位址        │ 製造商 ⭐ NEW        │ 主機名稱      │ 狀態   │
├─────────────┼─────────────────┼──────────────────────┼───────────────┼────────┤
│ 10.250.55.34│ 58:11:22:c8:b9:3c│ ASUSTek COMPUTER INC.│ ubuntu-pp-... │ 活躍中 │
│ 10.250.55.31│ 60:cf:84:dc:b1:57│ Realtek Semiconductor│ PC-SSD-5830   │ 活躍中 │
│ 10.250.55.30│ 48:21:0b:35:bc:26│ Intel Corporate      │ DESKTOP-O12...│ 活躍中 │
└─────────────┴─────────────────┴──────────────────────┴───────────────┴────────┘
```

## 🚀 立即體驗

### 方法 1：網頁瀏覽

1. **訪問**：http://localhost
2. **進入**：DHCP Server 分析
3. **點擊**：組約管理標籤
4. **查看**：新的「製造商」欄位（藍色 Tag）

### 方法 2：測試 API

```bash
# 獲取租約數據（包含 vendor 欄位）
curl http://localhost/api/dhcp-leases/ | jq '.results[] | {ip_address, mac_address, vendor}'
```

**預期輸出**：
```json
{
  "ip_address": "10.250.55.34",
  "mac_address": "58:11:22:c8:b9:3c",
  "vendor": "ASUSTek COMPUTER INC."
}
{
  "ip_address": "10.250.55.31",
  "mac_address": "60:cf:84:dc:b1:57",
  "vendor": "Realtek Semiconductor"
}
```

## 🎨 UI 特性

### Tag 顏色

| 狀態 | 顏色 | 範例 |
|------|------|------|
| 已識別製造商 | 藍色 | <span style="background:#2196f3;color:white;padding:2px 8px;border-radius:4px;">Cisco Systems, Inc</span> |
| 未識別設備 | 灰色 | <span style="background:#d9d9d9;color:#666;padding:2px 8px;border-radius:4px;">Unknown</span> |

### 功能

- ✅ **排序**：點擊欄位標題可排序
- ✅ **篩選**：可篩選 "Unknown" 設備
- ✅ **匯出**：CSV 包含製造商欄位

## 📊 常見製造商

您可能會在租約列表中看到這些製造商：

| MAC 前綴 | 製造商 | 常見設備類型 |
|----------|--------|--------------|
| 58:11:22 | ASUSTek COMPUTER INC. | ASUS 電腦/主機板 |
| 60:cf:84 | Realtek Semiconductor | 網路卡 |
| 48:21:0b | Intel Corporate | Intel 網路介面 |
| 80:09:02 | Keysight Technologies | 測試設備 |
| 00:50:BA | D-Link Corporation | D-Link 網路設備 |
| CC:46:D6 | Cisco Systems, Inc | Cisco 網路設備 |
| 48:AD:08 | HUAWEI TECHNOLOGIES CO.,LTD | 華為設備 |
| 3C:D9:2B | Hewlett Packard | HP 設備 |

## 🔍 實用技巧

### 1. 快速找出特定廠商的設備

1. 點擊「製造商」欄位標題排序
2. 相同廠商的設備會聚集在一起
3. 方便統計和管理

### 2. 識別未知設備

1. 點擊篩選圖標
2. 選擇「Unknown」
3. 只顯示無法識別的設備
4. 可能是虛擬機、容器或自定義 MAC

### 3. 匯出設備清單

1. 點擊「匯出 CSV」
2. 打開 Excel
3. 按製造商分組
4. 生成設備分佈報表

## 💡 使用場景

### 場景 1：網路設備盤點

**需求**：統計網路中有多少 Cisco 設備

**操作**：
1. 點擊「製造商」欄位排序
2. 找到所有 "Cisco Systems, Inc"
3. 記錄數量和 IP

### 場景 2：異常設備檢測

**需求**：找出不常見的設備

**操作**：
1. 瀏覽製造商欄位
2. 注意不熟悉的廠商名稱
3. 查看詳細資訊確認

### 場景 3：採購分析

**需求**：分析現有設備品牌分佈

**操作**：
1. 匯出 CSV
2. 使用 Excel 樞紐分析表
3. 按製造商統計數量

## 📈 資料準確性

- **識別率**：~95%
- **資料來源**：IEEE Official OUI Database
- **資料量**：38,254 筆 OUI 記錄
- **更新頻率**：每月 1 號自動更新

## 🔧 故障排查

### 問題 1：所有設備顯示 "Unknown"

**原因**：OUI 資料庫未載入

**解決**：
```bash
# 重新載入資料庫
docker exec nt-django python manage.py shell -c "from api.utils.mac_vendor import reload_oui_database; reload_oui_database()"

# 重啟 Django
docker compose restart django
```

### 問題 2：看不到「製造商」欄位

**原因**：前端緩存

**解決**：
```bash
# 清除瀏覽器緩存
Ctrl + Shift + R (Windows)
Cmd + Shift + R (Mac)

# 或重啟 React
docker compose restart react
```

## 📚 相關文檔

- [完整功能說明](./LEASES_VENDOR_COLUMN.md)
- [MAC 廠商識別](./MAC_VENDOR_IDENTIFICATION.md)
- [OUI 自動更新](./OUI_AUTO_UPDATE.md)

---

**立即體驗**：http://localhost → DHCP Server 分析 → 組約管理

**更新時間**：2025-10-29  
**版本**：v1.0
