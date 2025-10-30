# iPXE 檢測功能實作報告

## 📅 實作日期
**2025-10-29**

## 🎯 實作目標
在 DHCP Server 日誌分析中實現 iPXE 網路開機檢測功能，能夠區分不同的啟動階段（PXE, iPXE, WinPE, OS）。

---

## ✅ 完成項目

### 1. 數據庫模型擴展
**檔案**: `backend/api/models.py`

在 `DHCPLog` 模型中添加以下欄位：
```python
CLIENT_TYPE_CHOICES = [
    ('iPXE', 'iPXE'),
    ('PXE', 'PXE (BIOS)'),
    ('WinPE', 'Windows PE'),
    ('OS', 'Operating System'),
    ('Unknown', 'Unknown'),
]

client_type = models.CharField(
    max_length=20,
    choices=CLIENT_TYPE_CHOICES,
    default='Unknown',
    verbose_name='客戶端類型',
    db_index=True
)
boot_stage = models.CharField(max_length=50, blank=True, verbose_name='啟動階段')
vendor_class = models.CharField(max_length=500, blank=True, verbose_name='Vendor Class (Option 60)')
user_class = models.CharField(max_length=200, blank=True, verbose_name='User Class (Option 77)')
```

### 2. DHCP 日誌解析器擴展
**檔案**: `backend/api/services.py`

#### 2.1 新增 `identify_client_type()` 方法
```python
@staticmethod
def identify_client_type(fields):
    """
    識別客戶端類型（iPXE, PXE, WinPE, OS）
    
    根據 Windows DHCP 日誌的欄位 13-16：
    - 欄位 13-14: VendorClass (Option 60)
    - 欄位 15-16: UserClass (Option 77)
    """
```

**識別邏輯**：
- **iPXE**: User Class 或 Vendor Class 包含 "iPXE" 字樣
- **PXE**: Vendor Class 包含 "PXEClient" 或 "PXE"
- **WinPE**: Vendor Class 包含 "MSFT" 或主機名以 "minint-" 開頭
- **OS**: 有主機名但沒有 DHCP Options
- **Unknown**: 無法識別

#### 2.2 擴展 `parse_log_lines()` 方法
- 解析 Windows DHCP 日誌的完整欄位（原本只解析 0-6，現在包含 13-16）
- 調用 `identify_client_type()` 識別客戶端類型
- 在訊息中標示客戶端類型（例如：`[iPXE]`）

#### 2.3 更新 `get_db_logs()` 方法
- 添加 `client_type` 參數支援篩選
- 返回數據包含新欄位：`client_type`, `boot_stage`, `vendor_class`, `user_class`

### 3. API 序列化器
**檔案**: `backend/api/serializers.py`

創建 `DHCPLogSerializer`：
```python
class DHCPLogSerializer(serializers.ModelSerializer):
    server_name = serializers.CharField(source='server.name', read_only=True)
    server_ip = serializers.CharField(source='server.ip_address', read_only=True)
    client_type_display = serializers.CharField(source='get_client_type_display', read_only=True)
    
    class Meta:
        model = DHCPLog
        fields = '__all__'
        read_only_fields = ('created_at',)
```

### 4. API 視圖更新
**檔案**: `backend/api/views.py`

在 `dhcp_analytics_logs()` 視圖中：
- 添加 `client_type` 查詢參數
- 支援按客戶端類型篩選
- 在資料庫查詢中添加 `client_type` 條件

### 5. 前端組件更新
**檔案**: `frontend/src/components/dhcp-analytics/LogsTab.js`

#### 5.1 新增狀態和篩選
```javascript
const [clientType, setClientType] = useState('ALL');  // 客戶端類型篩選
```

#### 5.2 新增客戶端類型標籤函數
```javascript
const getClientTypeTag = (clientType) => {
    // 返回彩色標籤：iPXE (cyan), PXE (blue), WinPE (purple), OS (green)
}
```

#### 5.3 添加客戶端類型篩選器
```javascript
<Select value={clientType} onChange={...}>
    <Option value="ALL">全部</Option>
    <Option value="iPXE">iPXE</Option>
    <Option value="PXE">PXE (BIOS)</Option>
    <Option value="WinPE">Windows PE</Option>
    <Option value="OS">Operating System</Option>
    <Option value="Unknown">Unknown</Option>
</Select>
```

#### 5.4 增強日誌顯示
每筆日誌顯示：
- 時間戳
- 日誌等級標籤 (INFO/WARN/ERROR)
- 事件類型標籤
- **客戶端類型標籤** (新增)
- **啟動階段標籤** (新增)
- 訊息內容
- **Vendor Class** (折疊顯示，新增)
- **User Class** (折疊顯示，新增)

### 6. 數據庫遷移
**遷移檔案**: `backend/api/migrations/0009_dhcplog_boot_stage_dhcplog_client_type_and_more.py`

執行操作：
```bash
docker exec nt-django python manage.py makemigrations
docker exec nt-django python manage.py migrate
```

---

## 🧪 測試驗證

### 測試腳本
**檔案**: `test_ipxe_detection.py`

測試了 5 種日誌類型：
1. **iPXE 階段** - User Class 包含 "iPXE"
2. **PXE 階段** - Vendor Class 包含 "PXEClient"
3. **WinPE 階段** - Vendor Class 包含 "MSFT 5.0"
4. **OS 階段** - 正常主機名，無 DHCP Options
5. **iPXE 變體** - Vendor Class 和 User Class 都有資訊

### 測試結果
```
✓ 所有測試通過！iPXE 檢測功能正常運作！

測試結果統計:
  iPXE: 2 筆
  PXE: 1 筆
  WinPE: 1 筆
  OS: 1 筆
```

---

## 📊 Windows DHCP 日誌欄位對應

根據 Microsoft 官方文檔，完整的日誌格式：

```
ID, Date, Time, Description, IP Address, Host Name, MAC Address, User Name,
TransactionID, QResult, Probationtime, CorrelationID, Dhcid,
VendorClass(Hex), VendorClass(ASCII), UserClass(Hex), UserClass(ASCII),
RelayAgentInformation, DnsRegError
```

**關鍵欄位**（本次實作新增解析）：
- **欄位 13**: `VendorClass(Hex)` - DHCP Option 60 的十六進制
- **欄位 14**: `VendorClass(ASCII)` - DHCP Option 60 的 ASCII（**識別 PXE/WinPE 的關鍵**）
- **欄位 15**: `UserClass(Hex)` - DHCP Option 77 的十六進制
- **欄位 16**: `UserClass(ASCII)` - DHCP Option 77 的 ASCII（**識別 iPXE 的關鍵**）

---

## 🔍 實際案例分析

### 案例 1: iPXE 啟動
```
11,10/18/25,15:32:59,Renew,10.250.132.27,,BCFCE73A61C9,,727830406,0,,,,
0x505845436C69656E74...PXEClient:Arch:00007:UNDI:003010,0x69505845,iPXE
                                                          ↑           ↑
                                                    Option 77      明確的 "iPXE"
```
**識別結果**：
- 客戶端類型：`iPXE`
- 啟動階段：`iPXE Loading`
- Vendor Class：`0x69505845`
- User Class：`iPXE`

### 案例 2: BIOS PXE ROM
```
11,10/18/25,15:32:54,Renew,10.250.132.27,,BCFCE73A61C9,,610079976,0,,,,
0x505845436C69656E74...PXEClient:Arch:00007:UNDI:003016
↑
包含 "PXEClient"
```
**識別結果**：
- 客戶端類型：`PXE`
- 啟動階段：`BIOS PXE`
- Vendor Class：`PXEClient:Arch:00007:UNDI:003016`

### 案例 3: Windows PE
```
11,10/18/25,15:35:55,Renew,10.250.132.27,minint-pkc1vk8,BCFCE73A61C9,,313489413,0,,,,
0x4D53465420352E30,MSFT 5.0
↑                  ↑
Option 60          "MSFT 5.0"
```
**識別結果**：
- 客戶端類型：`WinPE`
- 啟動階段：`Windows PE`
- Vendor Class：`MSFT 5.0`
- 主機名：`minint-pkc1vk8`（WinPE 臨時主機名）

### 案例 4: 正常 OS
```
11,10/18/25,15:41:52,Renew,10.250.132.27,pynvme-pc,BCFCE73A61C9,,2837896269,0,,,,,,,,,0
                                        ↑
                                   正常主機名，無 DHCP Options
```
**識別結果**：
- 客戶端類型：`OS`
- 啟動階段：`Operating System`
- 主機名：`pynvme-pc`

---

## 📈 完整的啟動生命週期

根據實際日誌，一台機器的完整啟動流程：

```
時間軸                    階段           特徵                         識別方式
════════════════════════════════════════════════════════════════════════════════
15:32:54  →  BIOS PXE ROM    VendorClass: PXEClient:Arch:00007    檢查 Option 60
15:32:59  →  iPXE Loading    UserClass: iPXE                      檢查 Option 77 ← 關鍵！
15:34:08  →  正常 OS          hostname: pynvme-pc                  無 Options
15:35:11  →  iPXE (再次)     UserClass: iPXE                      檢查 Option 77
15:35:55  →  Windows PE       VendorClass: MSFT 5.0                檢查 Option 60
                             hostname: minint-xxx
15:41:52  →  Windows OS       hostname: pynvme-pc                  無 Options
```

---

## 🎨 前端 UI 增強

### 新增的視覺元素

1. **客戶端類型標籤**：
   - iPXE: 青色 (Cyan)
   - PXE: 藍色 (Geekblue)
   - WinPE: 紫色 (Purple)
   - OS: 綠色 (Green)

2. **啟動階段標籤**：
   - 金色 (Gold) 顯示具體階段

3. **詳細資訊展開**：
   - Vendor Class（DHCP Option 60）
   - User Class（DHCP Option 77）

4. **篩選器**：
   - 客戶端類型下拉選單（全部/iPXE/PXE/WinPE/OS/Unknown）

---

## 🔧 技術要點

### 後端關鍵實作
1. **欄位解析**：從原本的 7 個欄位擴展到解析 19 個欄位
2. **智能識別**：綜合判斷 VendorClass、UserClass 和 hostname
3. **資料庫索引**：`client_type` 欄位添加索引以提升查詢效能

### 前端關鍵實作
1. **響應式標籤**：根據客戶端類型動態顯示不同顏色標籤
2. **條件渲染**：只在有資料時顯示 Vendor/User Class
3. **篩選整合**：客戶端類型篩選器與現有篩選器（等級、時間、關鍵字）無縫整合

---

## 📚 相關文檔

- **分析報告**: `docs/features/DHCP_LOG_IPXE_DETECTION_ANALYSIS.md`
- **Microsoft 官方文檔**: Windows DHCP 日誌格式
- **RFC 2132**: DHCP Option 60 (Vendor Class Identifier)
- **RFC 3004**: DHCP Option 77 (User Class)

---

## 🚀 使用方式

### 1. 同步 DHCP 日誌
在前端 **DHCP Server 分析 → 日誌** 頁面點擊「同步日誌」按鈕。

### 2. 篩選 iPXE 記錄
使用「客戶端類型」下拉選單選擇 **iPXE**，即可查看所有 iPXE 開機記錄。

### 3. 查看詳細資訊
每筆日誌會顯示：
- 客戶端類型標籤（iPXE/PXE/WinPE/OS）
- 啟動階段（如「iPXE Loading」）
- 展開顯示 Vendor Class 和 User Class（若有）

### 4. 追蹤機器啟動流程
根據 MAC 地址搜尋，可以看到同一台機器從 PXE → iPXE → WinPE → OS 的完整啟動過程。

---

## ✨ 實作成果

### 解決的問題
✅ 可以明確區分 iPXE 網路開機階段  
✅ 可以追蹤機器的完整啟動生命週期  
✅ 可以快速篩選所有 iPXE 啟動記錄  
✅ 可以識別 Windows PE 部署階段  
✅ 可以統計各種客戶端類型的比例  

### 技術亮點
- **完整的欄位解析**：支援 Windows DHCP 日誌的 19 個欄位
- **智能識別邏輯**：綜合多種特徵準確判斷客戶端類型
- **友好的視覺呈現**：彩色標籤和詳細資訊展示
- **高效能查詢**：數據庫索引優化
- **全棧實作**：從數據庫、後端到前端的完整功能

---

**實作者**: GitHub Copilot  
**審核者**: Network Toolbox Team  
**狀態**: ✅ 完成並測試通過  
**最後更新**: 2025-10-29
