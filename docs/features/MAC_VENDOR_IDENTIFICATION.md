# MAC 地址製造商識別功能

## 📋 功能概述

本功能使用 **IEEE OUI (Organizationally Unique Identifier) 資料庫**來識別 DHCP 伺服器上設備的製造商。通過分析 MAC 地址的前 6 位（OUI），系統可以自動識別出 23,000+ 個製造商的設備。

## 🎯 主要特性

### 1. **完整的 IEEE OUI 資料庫**
- ✅ 支援 **38,254** 筆 OUI 記錄（從 IEEE 官方下載）
- ✅ 涵蓋 **19,776** 個唯一製造商
- ✅ 資料來源：[IEEE Official OUI Database](https://standards-oui.ieee.org/oui/oui.txt)
- ✅ **每月自動更新**（Celery Beat 定時任務）

### 2. **自動更新機制** ⭐ NEW
- ✅ **每月 1 號凌晨 2:00** 自動更新
- ✅ 自動備份現有資料庫
- ✅ 失敗自動重試（最多 3 次）
- ✅ 詳細更新日誌記錄
- 📖 [自動更新文檔](./OUI_AUTO_UPDATE.md)

### 2. **高效的查詢性能**
- ✅ **內存緩存**：首次載入後緩存，後續查詢速度極快
- ✅ **性能指標**：1000 次查詢 < 1 秒（平均 < 1 毫秒/次）
- ✅ **自動載入**：首次使用時自動載入，無需手動初始化
- ✅ **大資料庫支援**：38,000+ OUI 記錄，查詢速度不受影響

### 3. **多種 MAC 格式支援**
- ✅ `xx:xx:xx:xx:xx:xx` - 標準格式（冒號分隔）
- ✅ `xx-xx-xx-xx-xx-xx` - Windows 格式（連字符分隔）
- ✅ `xxxxxxxxxxxx` - 無分隔符格式

### 4. **自動更新機制** ⭐ NEW
- ✅ **Celery Beat 定時任務**：每月自動更新
- ✅ 從 IEEE 官方網站下載最新資料
- ✅ 自動備份 + 失敗重試
- ✅ 詳細日誌記錄
- 📖 [完整配置說明](./OUI_AUTO_UPDATE.md)

## 📂 檔案結構

```
backend/api/utils/
├── mac_vendor.py              # MAC 廠商識別模組
├── ieee-oui.txt               # IEEE OUI 資料庫（23,475 筆）
└── __init__.py

backend/api/management/commands/
└── update_oui.py              # OUI 資料庫更新命令

backend/
└── test_mac_vendor_simple.py  # 測試腳本
```

## 🚀 使用方法

### 1. 基本查詢

```python
from api.utils.mac_vendor import get_vendor_from_mac

# 查詢製造商
vendor = get_vendor_from_mac('00:50:BA:11:22:33')
print(vendor)  # 輸出: D-Link Corporation

# 支援多種格式
vendor1 = get_vendor_from_mac('CC:46:D6:AA:BB:CC')  # Cisco Systems, Inc
vendor2 = get_vendor_from_mac('48-AD-08-11-22-33')  # HUAWEI TECHNOLOGIES CO.,LTD
vendor3 = get_vendor_from_mac('3CD92B445566')       # Hewlett Packard
```

### 2. 獲取資料庫統計資訊

```python
from api.utils.mac_vendor import get_vendor_stats

stats = get_vendor_stats()
print(f"總 OUI 記錄: {stats['total_oui_entries']:,}")
print(f"唯一製造商: {stats['unique_vendors']:,}")
```

### 3. 獲取所有製造商列表

```python
from api.utils.mac_vendor import get_all_vendors

vendors = get_all_vendors()
print(f"共有 {len(vendors)} 個製造商")
for vendor in vendors[:10]:
    print(vendor)
```

### 4. 重新載入資料庫

```python
from api.utils.mac_vendor import reload_oui_database

# 更新 OUI 資料庫後重新載入
success = reload_oui_database()
```

## 🔧 更新 OUI 資料庫

### 使用管理命令更新

```bash
# 在容器內執行
docker exec nt-django python manage.py update_oui

# 使用備份選項
docker exec nt-django python manage.py update_oui --backup

# 選擇不同資料來源
docker exec nt-django python manage.py update_oui --source 0  # Gist Mirror (預設)
docker exec nt-django python manage.py update_oui --source 1  # IEEE Official
```

### 資料來源說明

| 來源索引 | 名稱 | URL | OUI 數量 | 推薦 |
|---------|------|-----|---------|------|
| 0 | **IEEE Official HTTPS** | https://standards-oui.ieee.org/oui/oui.txt | **38,254** | ✅ **預設（自動更新使用）** |
| 1 | IEEE Official HTTP | http://standards-oui.ieee.org/oui/oui.txt | 38,254 | 備用 |
| 2 | Gist Mirror | https://gist.githubusercontent.com/... | 23,475 | 歷史備份 |

**推薦使用來源 0（IEEE Official HTTPS）**：
- 資料最完整（38,254 筆）
- 每週更新
- 官方權威來源

## 📊 實際測試結果

### 測試案例

```
============================================================
OUI 資料庫狀態
============================================================
total_oui_entries: 23,475
unique_vendors: 16,778
database_loaded: True
file_exists: True

============================================================
測試 MAC 地址識別
============================================================
MAC: 00:50:BA:11:22:33    => Vendor: D-Link Corporation
MAC: CC:46:D6:AA:BB:CC    => Vendor: Cisco Systems, Inc
MAC: 48:AD:08:11:22:33    => Vendor: HUAWEI TECHNOLOGIES CO.,LTD
MAC: 3C:D9:2B:44:55:66    => Vendor: Hewlett Packard
MAC: 58:11:22:33:44:55    => Vendor: Unknown
MAC: 80:09:02:11:22:33    => Vendor: Keysight Technologies, Inc.
MAC: FF:FF:FF:AA:BB:CC    => Vendor: Unknown
```

### 性能測試

- **查詢次數**：1,000 次
- **總耗時**：< 1 秒
- **平均每次查詢**：< 1 毫秒
- **每秒查詢數**：> 1,000 次

## 🔌 API 整合

### 在 ViewSet 中使用

```python
from rest_framework import viewsets
from api.utils.mac_vendor import get_vendor_from_mac

class DHCPLeaseViewSet(viewsets.ModelViewSet):
    def list(self, request, *args, **kwargs):
        leases = DHCPLease.objects.all()
        
        # 為每個租約添加廠商資訊
        for lease in leases:
            lease.vendor = get_vendor_from_mac(lease.mac_address)
        
        serializer = self.get_serializer(leases, many=True)
        return Response(serializer.data)
```

### 在序列化器中使用

```python
from rest_framework import serializers
from api.utils.mac_vendor import get_vendor_from_mac

class DHCPLeaseSerializer(serializers.ModelSerializer):
    vendor = serializers.SerializerMethodField()
    
    def get_vendor(self, obj):
        return get_vendor_from_mac(obj.mac_address)
    
    class Meta:
        model = DHCPLease
        fields = ['ip_address', 'mac_address', 'vendor', ...]
```

## 📈 Dashboard 統計圖表

### 廠商分佈圖（已整合）

系統已在 `views.py` 中整合廠商統計功能：

```python
from collections import Counter
from api.utils.mac_vendor import get_vendor_from_mac

# 在 DashboardStatsView 中
vendor_counter = Counter()

for lease in active_leases:
    mac = lease.get('mac_address', '')
    vendor = get_vendor_from_mac(mac)
    if vendor and vendor != 'Unknown':
        vendor_counter[vendor] += 1
    else:
        vendor_counter['其他'] += 1

# 生成廠商分佈數據
vendor_data = []
top_vendors = vendor_counter.most_common(4)
other_count = sum(count for vendor, count in vendor_counter.items() 
                  if vendor not in [v[0] for v in top_vendors])

for i, (vendor, count) in enumerate(top_vendors):
    vendor_data.append({
        'name': vendor,
        'value': count,
        'color': COLORS[i]
    })

if other_count > 0:
    vendor_data.append({
        'name': '其他',
        'value': other_count,
        'color': COLORS[4]
    })
```

## 🧪 測試

### 運行測試腳本

```bash
# 在容器內運行
docker exec nt-django python /app/test_mac_vendor_simple.py
```

### 測試內容

1. ✅ OUI 資料庫載入狀態
2. ✅ MAC 地址解析（多種格式）
3. ✅ 廠商識別準確性
4. ✅ 查詢性能測試
5. ✅ 製造商列表功能

## 🔍 故障排查

### 問題 1：OUI 資料庫未載入

**症狀**：`file_exists: False`

**解決方法**：
```bash
# 手動下載 OUI 資料庫
docker exec nt-django python manage.py update_oui
```

### 問題 2：所有查詢返回 "Unknown"

**症狀**：`total_oui_entries: 0`

**解決方法**：
```bash
# 檢查檔案是否存在
docker exec nt-django ls -la /app/api/utils/ieee-oui.txt

# 重新下載
docker exec nt-django python manage.py update_oui --backup
```

### 問題 3：性能緩慢

**症狀**：首次查詢很慢

**原因**：首次載入資料庫需要時間（約 30ms）

**解決方法**：這是正常的，後續查詢會使用緩存，速度極快。

## 📚 技術細節

### OUI 資料格式

IEEE OUI 資料庫使用以下格式：

```
# ieee-oui.txt 格式
E043DB<TAB>Shenzhen ViewAt Technology Co.,Ltd.
0050BA<TAB>D-Link Corporation
CC46D6<TAB>Cisco Systems, Inc
48AD08<TAB>HUAWEI TECHNOLOGIES CO.,LTD
```

### 內存緩存機制

```python
# 全局緩存變數
_OUI_CACHE = None

def _load_oui_database():
    global _OUI_CACHE
    
    if _OUI_CACHE is not None:
        return _OUI_CACHE  # 直接返回緩存
    
    # 首次載入
    oui_map = {}
    with open(OUI_FILE, 'r') as f:
        for line in f:
            # 解析並存入字典
            ...
    
    _OUI_CACHE = oui_map
    return _OUI_CACHE
```

### MAC 地址標準化

```python
def get_vendor_from_mac(mac_address):
    # 1. 移除所有分隔符
    mac_clean = mac_address.replace(':', '').replace('-', '').upper()
    
    # 2. 提取前 6 位（OUI）
    oui_hex = mac_clean[:6]
    
    # 3. 轉換為標準格式（XX:XX:XX）
    oui_formatted = ':'.join([oui_hex[i:i+2] for i in range(0, 6, 2)])
    
    # 4. 查詢資料庫
    vendor = oui_db.get(oui_formatted, 'Unknown')
    return vendor
```

## 🎨 前端整合建議

### 1. 在租約列表中顯示廠商

```javascript
// Leases.js
const columns = [
    {
        title: 'MAC 地址',
        dataIndex: 'mac_address',
        key: 'mac_address',
    },
    {
        title: '製造商',
        dataIndex: 'vendor',
        key: 'vendor',
        render: (vendor) => (
            <Tag color={vendor === 'Unknown' ? 'default' : 'blue'}>
                {vendor}
            </Tag>
        ),
    },
    // ...其他欄位
];
```

### 2. 廠商篩選器

```javascript
const [selectedVendor, setSelectedVendor] = useState('all');

const filteredLeases = leases.filter(lease => 
    selectedVendor === 'all' || lease.vendor === selectedVendor
);
```

### 3. 廠商統計圖表

```javascript
import { PieChart, Pie, Cell, Legend } from 'recharts';

<PieChart width={400} height={400}>
    <Pie
        data={vendorData}
        cx="50%"
        cy="50%"
        labelLine={false}
        label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
        outerRadius={80}
        fill="#8884d8"
        dataKey="value"
    >
        {vendorData.map((entry, index) => (
            <Cell key={`cell-${index}`} fill={entry.color} />
        ))}
    </Pie>
    <Legend />
</PieChart>
```

## 🔄 定期維護

### 自動更新（已配置） ✅

系統已配置為 **每月 1 號凌晨 2:00** 自動更新 OUI 資料庫。

**查看自動更新配置**：
```bash
# 查看 Celery Beat 排程
docker exec nt-celery-beat celery -A network_toolbox inspect scheduled

# 查看更新任務狀態
docker compose logs celery_beat -f | grep update-oui
```

**詳細配置文檔**：[OUI_AUTO_UPDATE.md](./OUI_AUTO_UPDATE.md)

### 手動更新

如需立即更新，可使用以下命令：

```bash
# 從 IEEE 官方來源更新（推薦）
docker exec nt-django python manage.py update_oui --source 0 --backup

# 查看更新結果
docker exec nt-django python manage.py shell -c "from api.utils.mac_vendor import get_vendor_stats; print(get_vendor_stats())"
```

### 建議更新頻率

- **自動更新**：已配置為每月更新 ✅
- **手動更新**：有新設備無法識別時
- **資料來源**：IEEE 官方（每週更新）

### 監控更新狀態

```bash
# 查看 OUI 檔案修改時間
docker exec nt-django ls -lh /app/api/utils/ieee-oui.txt

# 查看資料庫統計
docker exec nt-django python /app/test_mac_vendor_simple.py
```

## 📖 參考資料

- [IEEE OUI Database (Official)](http://standards-oui.ieee.org/)
- [Wireshark OUI Lookup](https://www.wireshark.org/tools/oui-lookup.html)
- [arp-scan OUI Database](https://github.com/royhills/arp-scan)

## 🎉 總結

通過整合完整的 IEEE OUI 資料庫，Network Toolbox 現在可以：

- ✅ 自動識別 23,000+ 個製造商的設備
- ✅ 在 Dashboard 上顯示廠商分佈統計
- ✅ 在租約列表中顯示設備製造商
- ✅ 支援多種 MAC 地址格式
- ✅ 高效查詢（< 1 毫秒/次）
- ✅ 可自動更新資料庫

這將大大提升 DHCP 管理的可視化和設備識別能力！

---

**最後更新**：2025-10-29  
**版本**：1.0  
**維護者**：Network Toolbox Team
