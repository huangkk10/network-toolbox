# 在 DHCP Server 日誌中增加「當前租約名稱」功能 - 實作規劃

## 📋 需求分析

### 目標
在 **DHCP Server 分析** 頁面的日誌顯示中，額外顯示該 MAC 地址的**現在的租約主機名稱**（查詢時的最新狀態）。

### 使用場景
根據之前的分析（`DHCP_LOG_HOSTNAME_MISMATCH_ANALYSIS.md`），我們發現：
- **日誌中的 Hostname**：記錄該日誌時刻的歷史名稱（如：`PC-SSD-4632`）
- **現在的租約 Hostname**：顯示現在查詢時該 MAC 的最新名稱（如：`minint-xxxxx`）

⚠️ **重要概念釐清**：
- 「現在的租約名稱」= 您查看日誌頁面**當下**，該 MAC 在 `DHCPLease` 表中的最新值
- **不是**日誌記錄時間點的租約名稱
- 隨著時間推移，同一筆日誌顯示的「現在的租約名稱」可能會不同

增加此功能可以讓使用者：
1. ✅ **快速了解設備當前狀態**：不需要切換到租約管理頁面
2. ✅ **發現名稱變化**：對比歷史日誌與當前狀態，發現設備是否重新部署
3. ✅ **追蹤設備生命週期**：了解設備從 WinPE → 正式系統的變化軌跡
4. ✅ **異常偵測**：如果正式系統名稱又變回 minint-，可能正在重裝

### 視覺示意

**目前的日誌顯示：**
```
┌────────────────────────────────────────────────────────────┐
│ 2025-11-12 13:39:05  [INFO]  Operating System             │
│ DHCPREQUEST for 10.250.71.22 from cc28aa86c37f [Windows]  │
│ Vendor Class: MSFT 5.0                                     │
│ ───────────────────────────────────────────────────────── │
│ 11,11/12/25,13:39:05,Renew,10.250.71.22,PC-SSD-4632,...   │
└────────────────────────────────────────────────────────────┘
```

**增加後的顯示：**
```
┌────────────────────────────────────────────────────────────┐
│ 2025-11-12 13:39:05  [INFO]  Operating System             │
│ DHCPREQUEST for 10.250.71.22 from cc28aa86c37f [Windows]  │
│ Vendor Class: MSFT 5.0                                     │
│                                                            │
│ ╭─ 主機名稱追蹤 ────────────────────────────────╮         │
│ │ 📅 當時 (13:39): PC-SSD-4632                 │         │
│ │ 🔄 現在: minint-uca1cpe  ⚠️ 名稱已變更        │         │
│ ╰────────────────────────────────────────────╯         │
│ ───────────────────────────────────────────────────────── │
│ 11,11/12/25,13:39:05,Renew,10.250.71.22,PC-SSD-4632,...   │
└────────────────────────────────────────────────────────────┘

說明：
• "當時" = 日誌記錄的那個時間點（2025-11-12 13:39）
• "現在" = 您查看日誌的當下，該 MAC 在租約表中的最新名稱
• 如果兩者不同，顯示 "⚠️ 名稱已變更" 標籤
```

## 🔍 可行性分析

### ✅ 完全可行

**原因：**
1. **資料庫已有租約表**：`DHCPLease` 模型包含 `hostname` 欄位
2. **日誌已有 MAC 地址**：可從 `raw` 欄位解析出 MAC 地址
3. **關聯查詢簡單**：透過 `mac_address` 欄位即可關聯

### 技術挑戰

#### 挑戰 1：從日誌 raw 欄位提取 MAC 地址

**問題：**
- `DHCPLog` 模型沒有獨立的 `mac_address` 欄位
- MAC 地址存在於 `raw` 欄位中（CSV 格式的第 7 個欄位）

**解決方案：**
- 在序列化器或 API 層面解析 `raw` 欄位
- 或者在前端解析（不推薦，因為格式可能不一致）

#### 挑戰 2：性能考量

**問題：**
- 每條日誌都需要查詢一次 `DHCPLease` 表
- 如果一次顯示 100 條日誌 = 100 次查詢（N+1 問題）

**解決方案：**
- 使用批量查詢（一次性查詢所有 MAC 地址的租約）
- 在後端 API 層面優化，避免前端多次請求

#### 挑戰 3：租約可能不存在

**問題：**
- 某些日誌的 MAC 地址可能沒有對應的租約記錄（已過期或刪除）

**解決方案：**
- 顯示為 "無租約記錄" 或 "N/A"
- 不影響其他日誌的顯示

## 🏗️ 實作方案

### 方案 1：後端序列化器增強（推薦）

**優點：**
- ✅ 性能最佳（可使用 `select_related` 或 `prefetch_related` 優化）
- ✅ 邏輯集中在後端
- ✅ 前端改動最小

**缺點：**
- ❌ 需要修改後端序列化器和 API

**實作步驟：**

#### 步驟 1：增強 `DHCPLog` 模型（可選）

**位置：** `backend/api/models.py`

**選項 A：添加方法（不修改資料庫結構）**
```python
class DHCPLog(models.Model):
    # ...現有欄位...
    
    @property
    def mac_address(self):
        """從 raw 欄位提取 MAC 地址"""
        if self.raw:
            fields = self.raw.split(',')
            if len(fields) > 6:
                mac = fields[6].strip()
                # 格式化為標準格式（xx:xx:xx:xx:xx:xx）
                mac = mac.replace('-', ':').lower()
                return mac if mac else None
        return None
    
    @property
    def log_hostname(self):
        """從 raw 欄位提取日誌中的主機名稱"""
        if self.raw:
            fields = self.raw.split(',')
            if len(fields) > 5:
                hostname = fields[5].strip()
                return hostname if hostname else None
        return None
    
    def get_current_lease_hostname(self):
        """獲取當前租約的主機名稱"""
        mac = self.mac_address
        if mac:
            try:
                lease = DHCPLease.objects.filter(
                    server=self.server,
                    mac_address=mac
                ).first()
                return lease.hostname if lease else None
            except DHCPLease.DoesNotExist:
                return None
        return None
```

**選項 B：添加資料庫欄位（推薦，更高效）**
```python
class DHCPLog(models.Model):
    # ...現有欄位...
    
    # 新增欄位
    mac_address = models.CharField(
        max_length=17, 
        blank=True, 
        verbose_name='MAC 位址',
        db_index=True  # 加速查詢
    )
    ip_address = models.GenericIPAddressField(
        blank=True, 
        null=True, 
        verbose_name='IP 位址'
    )
    log_hostname = models.CharField(
        max_length=255, 
        blank=True, 
        verbose_name='日誌主機名稱'
    )
    
    class Meta:
        # ...現有設定...
        indexes = [
            # ...現有索引...
            models.Index(fields=['mac_address'], name='idx_log_mac'),
        ]
```

**注意：** 選項 B 需要執行資料庫遷移：
```bash
docker exec nt-django python manage.py makemigrations
docker exec nt-django python manage.py migrate
```

#### 步驟 2：修改序列化器

**位置：** `backend/api/serializers.py`

**方案 A：使用 `SerializerMethodField`（不修改資料庫）**
```python
class DHCPLogSerializer(serializers.ModelSerializer):
    """DHCP 日誌序列化器"""
    
    server_name = serializers.CharField(source='server.name', read_only=True)
    server_ip = serializers.CharField(source='server.ip_address', read_only=True)
    client_type_display = serializers.CharField(source='get_client_type_display', read_only=True)
    
    # ✅ 新增：從 raw 欄位提取的資訊
    mac_address = serializers.SerializerMethodField()
    log_hostname = serializers.SerializerMethodField()
    ip_address = serializers.SerializerMethodField()
    
    # ✅ 新增：當前租約資訊
    current_lease_hostname = serializers.SerializerMethodField()
    lease_updated_at = serializers.SerializerMethodField()  # 租約最後更新時間
    hostname_changed = serializers.SerializerMethodField()
    
    def get_mac_address(self, obj):
        """提取 MAC 地址"""
        if obj.raw:
            fields = obj.raw.split(',')
            if len(fields) > 6:
                mac = fields[6].strip().replace('-', ':').lower()
                return mac if mac else None
        return None
    
    def get_log_hostname(self, obj):
        """提取日誌中的主機名稱"""
        if obj.raw:
            fields = obj.raw.split(',')
            if len(fields) > 5:
                hostname = fields[5].strip()
                return hostname if hostname else None
        return None
    
    def get_ip_address(self, obj):
        """提取 IP 地址"""
        if obj.raw:
            fields = obj.raw.split(',')
            if len(fields) > 4:
                ip = fields[4].strip()
                return ip if ip else None
        return None
    
    def get_current_lease_hostname(self, obj):
        """
        獲取當前租約的主機名稱（現在查詢時的最新值）
        
        注意：這是「現在」的租約名稱，不是日誌時間點的名稱
        """
        mac = self.get_mac_address(obj)
        if mac:
            # 使用 context 傳遞的預先查詢結果（避免 N+1 問題）
            leases_dict = self.context.get('leases_dict', {})
            if leases_dict:
                lease = leases_dict.get(mac)
                return lease.hostname if lease else None
            
            # 備用方案：直接查詢（性能較差）
            try:
                lease = DHCPLease.objects.filter(
                    server=obj.server,
                    mac_address=mac
                ).first()
                return lease.hostname if lease else None
            except:
                return None
        return None
    
    def get_lease_updated_at(self, obj):
        """
        獲取租約的最後更新時間
        用於說明「現在」的租約名稱是何時更新的
        """
        mac = self.get_mac_address(obj)
        if mac:
            leases_dict = self.context.get('leases_dict', {})
            if leases_dict:
                lease = leases_dict.get(mac)
                if lease and lease.updated_at:
                    local_time = django_timezone.localtime(lease.updated_at)
                    return local_time.strftime('%Y-%m-%d %H:%M:%S')
            
            # 備用方案
            try:
                lease = DHCPLease.objects.filter(
                    server=obj.server,
                    mac_address=mac
                ).first()
                if lease and lease.updated_at:
                    local_time = django_timezone.localtime(lease.updated_at)
                    return local_time.strftime('%Y-%m-%d %H:%M:%S')
            except:
                pass
        return None
    
    def get_hostname_changed(self, obj):
        """
        判斷主機名稱是否已變更
        對比「日誌時的名稱」vs「現在的租約名稱」
        """
        log_hostname = self.get_log_hostname(obj)
        current_hostname = self.get_current_lease_hostname(obj)
        
        # 如果兩者都存在且不同，則標記為已變更
        if log_hostname and current_hostname:
            return log_hostname != current_hostname
        return False
    
    # 時間戳轉換
    timestamp = serializers.SerializerMethodField()
    
    def get_timestamp(self, obj):
        """將 UTC 時間轉換為當前時區（Asia/Taipei）"""
        if obj.timestamp:
            local_time = django_timezone.localtime(obj.timestamp)
            return local_time.strftime('%Y-%m-%d %H:%M:%S')
        return None
    
    class Meta:
        model = DHCPLog
        fields = '__all__'
        read_only_fields = ('created_at',)
```

**方案 B：使用模型欄位（修改資料庫後）**
```python
class DHCPLogSerializer(serializers.ModelSerializer):
    """DHCP 日誌序列化器"""
    
    server_name = serializers.CharField(source='server.name', read_only=True)
    server_ip = serializers.CharField(source='server.ip_address', read_only=True)
    client_type_display = serializers.CharField(source='get_client_type_display', read_only=True)
    
    # ✅ 直接使用模型欄位（性能更好）
    # mac_address, ip_address, log_hostname 已在模型中定義
    
    # ✅ 新增：當前租約資訊
    current_lease_hostname = serializers.SerializerMethodField()
    hostname_changed = serializers.SerializerMethodField()
    
    def get_current_lease_hostname(self, obj):
        """獲取當前租約的主機名稱"""
        if obj.mac_address:
            # 使用 context 傳遞的預先查詢結果
            leases_dict = self.context.get('leases_dict', {})
            if leases_dict:
                lease = leases_dict.get(obj.mac_address)
                return lease.hostname if lease else None
        return None
    
    def get_hostname_changed(self, obj):
        """判斷主機名稱是否已變更"""
        if obj.log_hostname and obj.mac_address:
            current_hostname = self.get_current_lease_hostname(obj)
            if current_hostname:
                return obj.log_hostname != current_hostname
        return False
    
    timestamp = serializers.SerializerMethodField()
    
    def get_timestamp(self, obj):
        if obj.timestamp:
            local_time = django_timezone.localtime(obj.timestamp)
            return local_time.strftime('%Y-%m-%d %H:%M:%S')
        return None
    
    class Meta:
        model = DHCPLog
        fields = '__all__'
        read_only_fields = ('created_at',)
```

#### 步驟 3：優化 API 視圖（解決 N+1 問題）

**位置：** `backend/api/views/dhcp_logs.py`

**修改 `dhcp_analytics_logs` 函數：**
```python
@api_view(['GET'])
@permission_classes([AllowAny])
def dhcp_analytics_logs(request):
    """DHCP 分析 - 日誌查看"""
    # ...現有的參數解析...
    
    try:
        server = DHCPServer.objects.get(id=server_id)
        log_service = DHCPLogService(server)
        
        # ...現有的日誌查詢邏輯...
        
        if source == 'database':
            # 查詢資料庫
            logs_query = DHCPLog.objects.filter(server=server)
            
            # ...套用篩選條件...
            
            # 取得該頁的日誌
            page_logs = logs_query[start_idx:end_idx]
            
            # ✅ 批量查詢租約資訊（避免 N+1 問題）
            mac_addresses = []
            for log in page_logs:
                if log.raw:
                    fields = log.raw.split(',')
                    if len(fields) > 6:
                        mac = fields[6].strip().replace('-', ':').lower()
                        if mac:
                            mac_addresses.append(mac)
            
            # 一次性查詢所有相關租約
            leases = DHCPLease.objects.filter(
                server=server,
                mac_address__in=mac_addresses
            )
            
            # 建立 MAC -> Lease 的字典
            leases_dict = {lease.mac_address: lease for lease in leases}
            
            # 序列化時傳遞 leases_dict
            serializer = DHCPLogSerializer(
                page_logs, 
                many=True,
                context={'leases_dict': leases_dict}
            )
            
            return Response({
                'logs': serializer.data,
                'total': total,
                'page': page,
                'page_size': page_size,
                'total_pages': total_pages,
                'statistics': statistics,
            })
        
        # ...其他邏輯...
```

#### 步驟 4：修改前端顯示

**位置：** `frontend/src/components/dhcp-analytics/LogsTab.js`

**在日誌卡片中增加主機名稱比對資訊：**
```javascript
// 在現有的日誌顯示區塊中（約 410 行附近）

{logs.map((log, index) => (
    <div
        key={index}
        style={{
            marginBottom: '6px',
            padding: '6px 10px',
            background: '#fff',
            borderRadius: '4px',
            borderLeft: '4px solid ' + (/* 現有顏色邏輯 */),
        }}
    >
        {/* 現有的時間戳、等級、事件等 */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '4px' }}>
            {/* ...現有內容... */}
        </div>
        
        {/* 現有的訊息內容 */}
        <div style={{ paddingLeft: '12px' }}>
            <div style={{ color: '#262626', fontWeight: '500', wordBreak: 'break-all', marginBottom: '4px' }}>
                {log.message}
            </div>
            
            {/* ✅ 新增：主機名稱追蹤資訊 */}
            {(log.log_hostname || log.current_lease_hostname) && (
                <div style={{
                    fontSize: '12px',
                    marginTop: '8px',
                    padding: '10px',
                    background: log.hostname_changed ? '#fff7e6' : '#f0f5ff',
                    borderRadius: '4px',
                    border: `1px solid ${log.hostname_changed ? '#ffd591' : '#d6e4ff'}`,
                }}>
                    <div style={{ fontWeight: '600', marginBottom: '6px', color: '#595959' }}>
                        🏷️ 主機名稱追蹤
                    </div>
                    <Space direction="vertical" size="small" style={{ width: '100%' }}>
                        {log.log_hostname && (
                            <div>
                                <span style={{ fontWeight: '500' }}>� 當時: </span>
                                <span style={{ fontFamily: 'monospace', color: '#1890ff' }}>
                                    {log.log_hostname}
                                </span>
                                <span style={{ color: '#8c8c8c', fontSize: '11px', marginLeft: '8px' }}>
                                    ({formatTimestamp(log.timestamp)})
                                </span>
                            </div>
                        )}
                        {log.current_lease_hostname && (
                            <div>
                                <span style={{ fontWeight: '500' }}>🔄 現在: </span>
                                <span style={{ fontFamily: 'monospace', color: '#52c41a' }}>
                                    {log.current_lease_hostname}
                                </span>
                                {log.hostname_changed && (
                                    <Tag color="warning" style={{ marginLeft: '8px' }}>
                                        ⚠️ 名稱已變更
                                    </Tag>
                                )}
                                {log.lease_updated_at && (
                                    <div style={{ color: '#8c8c8c', fontSize: '11px', marginLeft: '30px', marginTop: '2px' }}>
                                        └─ 租約更新: {formatTimestamp(log.lease_updated_at)}
                                    </div>
                                )}
                            </div>
                        )}
                        {!log.current_lease_hostname && log.mac_address && (
                            <div style={{ color: '#8c8c8c', fontSize: '11px' }}>
                                ℹ️ 無當前租約記錄（MAC: {log.mac_address}）
                            </div>
                        )}
                    </Space>
                    <div style={{ 
                        marginTop: '8px', 
                        paddingTop: '6px', 
                        borderTop: '1px dashed #d9d9d9',
                        color: '#8c8c8c',
                        fontSize: '11px' 
                    }}>
                        💡 提示：「現在」指的是您查看此頁面時的租約狀態
                    </div>
                </div>
            )}
            
            {/* 現有的 Vendor Class 和 User Class */}
            {(log.vendor_class || log.user_class) && (
                <div style={{ fontSize: '12px', color: '#8c8c8c', marginTop: '4px' }}>
                    {/* ...現有內容... */}
                </div>
            )}
            
            {/* 現有的 raw 日誌 */}
            {log.raw && (
                <div style={{ /* ...現有樣式... */ }}>
                    {log.raw}
                </div>
            )}
        </div>
    </div>
))}
```

## 📊 性能評估

### 方案比較

| 特性 | 方案 A（SerializerMethodField） | 方案 B（模型欄位 + 批量查詢） |
|------|----------------------------------|-------------------------------|
| **資料庫遷移** | ❌ 不需要 | ✅ 需要執行 migration |
| **查詢效率** | ⚠️ 中等（需解析 raw） | ✅ 高（直接查詢欄位） |
| **儲存空間** | ✅ 無額外儲存 | ❌ 增加 3 個欄位 |
| **維護成本** | ⚠️ 中等（每次都解析） | ✅ 低（一次寫入） |
| **即時性** | ✅ 即時解析 | ⚠️ 需要在寫入時填充 |
| **適用性** | ✅ 快速實作 | ✅ 長期使用 |

### 推薦方案

**短期實作（1-2 小時）：** 選擇 **方案 A**
- 不需要資料庫遷移
- 可以立即部署
- 適合快速驗證功能

**長期優化（3-4 小時）：** 升級到 **方案 B**
- 性能更好
- 查詢更直觀
- 可以在日誌解析時就填充欄位

## 🚀 部署步驟

### 方案 A 部署（快速實作）

```bash
# 1. 修改後端序列化器
# 編輯 backend/api/serializers.py

# 2. 修改 API 視圖
# 編輯 backend/api/views/dhcp_logs.py

# 3. 重啟 Django 容器
docker compose restart django

# 4. 修改前端組件
# 編輯 frontend/src/components/dhcp-analytics/LogsTab.js

# 5. 重啟 React 容器（自動熱重載）
docker compose restart react

# 6. 瀏覽器測試
# 訪問：http://localhost/dhcp-analytics/server/3/logs
```

### 方案 B 部署（完整實作）

```bash
# 1. 修改模型
# 編輯 backend/api/models.py

# 2. 執行資料庫遷移
docker exec nt-django python manage.py makemigrations
docker exec nt-django python manage.py migrate

# 3. 更新現有日誌的 MAC/IP/Hostname 欄位（一次性腳本）
docker exec nt-django python manage.py shell -c "
from api.models import DHCPLog

logs = DHCPLog.objects.all()
for log in logs:
    if log.raw:
        fields = log.raw.split(',')
        if len(fields) > 6:
            log.mac_address = fields[6].strip().replace('-', ':').lower()
        if len(fields) > 4:
            log.ip_address = fields[4].strip()
        if len(fields) > 5:
            log.log_hostname = fields[5].strip()
        log.save()
print('更新完成')
"

# 4. 修改序列化器
# 編輯 backend/api/serializers.py

# 5. 修改 API 視圖
# 編輯 backend/api/views/dhcp_logs.py

# 6. 修改日誌解析服務（寫入時填充新欄位）
# 編輯 backend/api/services.py 中的 DHCPLogService

# 7. 重啟容器
docker compose restart django react

# 8. 測試
# 訪問：http://localhost/dhcp-analytics/server/3/logs
```

## ✅ 驗證清單

- [ ] 後端 API 返回 `current_lease_hostname` 欄位
- [ ] 後端 API 返回 `hostname_changed` 欄位（布林值）
- [ ] 前端正確顯示「日誌主機名稱」和「當前租約名稱」
- [ ] 名稱變更時顯示警告標籤
- [ ] 無租約記錄時顯示提示訊息
- [ ] 性能測試：100 條日誌載入時間 < 2 秒
- [ ] 不影響現有功能（日誌篩選、搜尋、分頁等）

## 📚 相關文檔

- [主機名稱不一致問題分析](./DHCP_LOG_HOSTNAME_MISMATCH_ANALYSIS.md)
- [DHCP 日誌功能實作](../features/LOGS_API_IMPLEMENTATION.md)
- [Django 模型文檔](../development/DJANGO_MODELS.md)

---

**建立日期**：2025-11-13  
**功能類型**：日誌顯示增強  
**實作難度**：⭐⭐⭐ (中等)  
**預估時間**：方案 A: 1-2 小時 | 方案 B: 3-4 小時
