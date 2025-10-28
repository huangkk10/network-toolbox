# MAC 廠商識別 - 快速開始

## 🎯 這是什麼？

利用 **IEEE OUI 資料庫**自動識別 DHCP 租約中設備的製造商。

## ⚡ 快速測試

```bash
# 1. 在容器內測試
docker exec nt-django python /app/test_mac_vendor_simple.py

# 2. 查看資料庫狀態
docker exec nt-django python manage.py shell -c "from api.utils.mac_vendor import get_vendor_stats; print(get_vendor_stats())"

# 3. 測試單個 MAC 地址
docker exec nt-django python manage.py shell -c "from api.utils.mac_vendor import get_vendor_from_mac; print(get_vendor_from_mac('00:50:BA:11:22:33'))"
```

## 📊 查看效果

### Dashboard 廠商分佈圖

訪問 http://localhost 查看 Dashboard，您將看到：

- **設備廠商分佈圖**：自動統計並顯示前 4 大廠商
- 顏色編碼的圓餅圖
- 包含 "其他" 分類

### API 端點

```bash
# 獲取租約列表（包含廠商資訊）
curl http://localhost/api/leases/

# 回應範例
{
  "ip_address": "192.168.1.100",
  "mac_address": "00:50:BA:11:22:33",
  "vendor": "D-Link Corporation",  # ← 新增欄位
  ...
}
```

## 🔧 更新 OUI 資料庫

```bash
# 使用預設來源（Gist Mirror）
docker exec nt-django python manage.py update_oui

# 備份現有資料庫後更新
docker exec nt-django python manage.py update_oui --backup
```

## 💻 在代碼中使用

### Python (後端)

```python
from api.utils.mac_vendor import get_vendor_from_mac

vendor = get_vendor_from_mac('CC:46:D6:AA:BB:CC')
print(vendor)  # 輸出: Cisco Systems, Inc
```

### JavaScript (前端)

```javascript
// 租約數據已包含 vendor 欄位
const lease = {
    mac_address: "00:50:BA:11:22:33",
    vendor: "D-Link Corporation",  // API 自動提供
    ...
};

// 在 Table 中顯示
<Table.Column 
    title="製造商" 
    dataIndex="vendor" 
    key="vendor"
/>
```

## 📈 數據統計

- **總 OUI 記錄**：23,475 筆
- **唯一製造商**：16,778 個
- **查詢速度**：< 1 毫秒/次
- **支援格式**：`xx:xx:xx`, `xx-xx-xx`, `xxxxxx`

## ❓ 常見問題

**Q: 為什麼有些 MAC 顯示 "Unknown"？**  
A: 該 MAC 前綴不在 IEEE OUI 資料庫中（可能是虛擬 MAC 或本地分配）。

**Q: 如何新增自定義廠商？**  
A: 直接編輯 `backend/api/utils/ieee-oui.txt`，格式：`AABBCC<TAB>製造商名稱`

**Q: 多久更新一次資料庫？**  
A: 建議每季度更新一次，或當發現新設備無法識別時更新。

## 📚 完整文檔

詳細說明請參閱：[MAC_VENDOR_IDENTIFICATION.md](./MAC_VENDOR_IDENTIFICATION.md)

---

**最後更新**：2025-10-29  
**快速測試**：`docker exec nt-django python /app/test_mac_vendor_simple.py`
