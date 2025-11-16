# Jenkins Build 配置檢查器功能規劃

> **狀態**: 規劃中 🚧  
> **創建日期**: 2025-11-15  
> **最後更新**: 2025-11-15  
> **負責人**: Network Toolbox Team

---

## 📋 目錄

1. [功能概述](#功能概述)
2. [業務需求](#業務需求)
3. [技術架構設計](#技術架構設計)
4. [資料庫設計](#資料庫設計)
5. [API 端點設計](#api-端點設計)
6. [前端頁面設計](#前端頁面設計)
7. [檢查邏輯設計](#檢查邏輯設計)
8. [開發階段規劃](#開發階段規劃)
9. [測試計劃](#測試計劃)
10. [未來擴展計劃](#未來擴展計劃)

---

## 功能概述

### 目標
在 RVT Assistant 頁面的 Jenkins Build 資料中，新增一個「配置檢查」按鈕，點擊後跳轉到獨立的檢查頁面，自動驗證該 Build 的配置參數是否正確。

### 核心功能
1. **配置提取**: 從 `JenkinsBuild.parameters` 和 `ansible_config` 欄位讀取配置
2. **多項檢查**: 逐項檢查 Host IP、Host MAC、UART IP 等配置
3. **DHCP 驗證**: 與 DHCP Server 的租約記錄進行對照
4. **格式驗證**: 檢查 MAC 地址格式（必須為 Linux 格式，如 `30:C5:99:55:C9:D3`）
5. **結果展示**: 以清晰的視覺化方式展示檢查結果和錯誤提示

### 使用場景
- **Build 失敗排查**: 快速定位配置錯誤導致的 Build 失敗
- **配置審核**: 在執行 Build 前預先檢查配置正確性
- **問題診斷**: 協助開發人員快速找到配置問題的根因

---

## 業務需求

### 檢查項目（Phase 1）

#### 1️⃣ Host IP 檢查
- **檢查目標**: `parameters['host_ip']` 或 `ansible_config['host_ip']`
- **檢查邏輯**:
  - ✅ IP 格式是否正確
  - ✅ 是否在 DHCP Server 的租約記錄中存在
  - ✅ 租約是否處於活動狀態（`is_active=True`）
  - ✅ 租約是否已過期（`lease_end` > 當前時間）
- **檢查結果**:
  - ✅ **通過**: IP 存在且租約有效
  - ⚠️ **警告**: IP 存在但租約即將過期（< 24 小時）
  - ❌ **失敗**: IP 格式錯誤、不存在租約或租約已過期

#### 2️⃣ Host MAC 地址檢查
- **檢查目標**: `parameters['host_mac']` 或 `ansible_config['host_mac']`
- **檢查邏輯**:
  - ✅ MAC 格式是否正確（必須為 Linux 格式：`AA:BB:CC:DD:EE:FF`）
  - ✅ 是否在 DHCP Server 的租約記錄中存在
  - ✅ 租約是否處於活動狀態
  - ✅ MAC 對應的 IP 是否與 `host_ip` 一致
- **檢查結果**:
  - ✅ **通過**: MAC 格式正確、存在租約且與 Host IP 一致
  - ⚠️ **警告**: MAC 格式正確但對應的 IP 與配置不一致
  - ❌ **失敗**: MAC 格式錯誤、不存在租約或租約已過期

#### 3️⃣ UART IP 檢查
- **檢查目標**: `parameters['uart_ip']` 或 `ansible_config['uart_ip']`
- **檢查邏輯**:
  - ✅ IP 格式是否正確
  - ✅ 是否在 DHCP Server 的租約記錄中存在
  - ✅ 租約是否處於活動狀態
  - ✅ 租約是否已過期
- **檢查結果**:
  - ✅ **通過**: IP 存在且租約有效
  - ⚠️ **警告**: IP 存在但租約即將過期（< 24 小時）
  - ❌ **失敗**: IP 格式錯誤、不存在租約或租約已過期

### 未來擴展檢查項目（Phase 2+）

#### 4️⃣ Switch IP/Port 檢查
- 檢查 Switch 是否在線
- 檢查 Port 是否為 Trunk Mode
- 檢查 VLAN 配置是否正確

#### 5️⃣ Jenkins Job 參數完整性檢查
- 檢查必填參數是否存在
- 檢查參數類型是否正確

#### 6️⃣ Ansible Playbook 檔案檢查
- 檢查 Playbook 檔案是否存在
- 檢查 Inventory 是否正確

#### 7️⃣ NAS 存儲路徑檢查
- 檢查 Workspace 路徑是否存在
- 檢查存儲空間是否充足

---

## 技術架構設計

### 系統架構圖

```
┌─────────────────────────────────────────────────────────┐
│  前端（React + Ant Design）                              │
├─────────────────────────────────────────────────────────┤
│  RVTAnalysisPage (主頁面)                                │
│    └─ Build Table                                       │
│        └─ [檢查配置] 按鈕                                 │
│            ↓                                            │
│  BuildConfigValidatorPage (獨立檢查頁面)                 │
│    ├─ 配置概覽卡片                                       │
│    ├─ 檢查項目列表（Steps）                              │
│    ├─ 檢查結果展示                                       │
│    └─ 錯誤提示與修正建議                                  │
└─────────────────────────────────────────────────────────┘
                        ↓ HTTP API
┌─────────────────────────────────────────────────────────┐
│  後端（Django REST Framework）                           │
├─────────────────────────────────────────────────────────┤
│  API 端點:                                               │
│    /api/jenkins-builds/{id}/validate-config/           │
│    /api/dhcp-leases/check-ip/                          │
│    /api/dhcp-leases/check-mac/                         │
│                                                         │
│  Service 層:                                            │
│    - BuildConfigValidatorService                       │
│    - DHCPLeaseCheckerService                           │
│    - MACAddressValidator                               │
│                                                         │
│  Models:                                                │
│    - JenkinsBuild (現有)                                │
│    - DHCPLease (現有)                                   │
│    - DHCPServer (現有)                                  │
│    - (可選) BuildConfigValidationLog (新增)              │
└─────────────────────────────────────────────────────────┘
                        ↓ Database Query
┌─────────────────────────────────────────────────────────┐
│  PostgreSQL 資料庫                                       │
├─────────────────────────────────────────────────────────┤
│  - api_jenkinsbuild (現有)                              │
│  - api_dhcplease (現有)                                 │
│  - api_dhcpserver (現有)                                │
│  - api_buildconfigvalidationlog (可選，新增)             │
└─────────────────────────────────────────────────────────┘
```

### 技術棧

**前端**:
- React 18.2
- Ant Design 5.x（Steps, Result, Descriptions, Tag）
- Axios（HTTP 請求）
- React Router v6（頁面路由）

**後端**:
- Django 4.2
- Django REST Framework
- PostgreSQL
- Python 3.x

**檢查流程**:
1. 前端發送 Build ID 到後端
2. 後端從 `JenkinsBuild` 提取 `parameters` 和 `ansible_config`
3. 逐項執行檢查邏輯
4. 查詢 DHCP Lease 資料進行驗證
5. 返回檢查結果（JSON 格式）
6. 前端以視覺化方式展示結果

---

## 資料庫設計

### 現有模型（無需修改）

#### JenkinsBuild
```python
class JenkinsBuild(models.Model):
    job = models.ForeignKey(JenkinsJob, ...)
    build_number = models.IntegerField(...)
    
    # ✅ 已有的配置欄位（直接使用）
    parameters = models.JSONField(default=dict, blank=True)
    ansible_config = models.JSONField(default=dict, blank=True)
    environment_vars = models.JSONField(default=dict, blank=True)
    
    # 範例數據結構
    # parameters = {
    #     'host_ip': '192.168.1.100',
    #     'host_mac': '30:C5:99:55:C9:D3',
    #     'uart_ip': '192.168.1.200',
    #     'build_type': 'full',
    #     'environment': 'production'
    # }
    #
    # ansible_config = {
    #     'playbook': 'deploy.yml',
    #     'inventory': 'production',
    #     'extra_vars': {
    #         'host_ip': '192.168.1.100',
    #         'host_mac': '30:C5:99:55:C9:D3'
    #     }
    # }
```

#### DHCPLease
```python
class DHCPLease(models.Model):
    server = models.ForeignKey(DHCPServer, ...)
    ip_address = models.GenericIPAddressField(...)
    mac_address = models.CharField(max_length=17, ...)  # ← 驗證目標
    hostname = models.CharField(max_length=255, blank=True, ...)
    lease_start = models.DateTimeField(...)
    lease_end = models.DateTimeField(...)
    is_active = models.BooleanField(default=True, ...)
```

### 可選的新增模型（用於記錄檢查歷史）

```python
class BuildConfigValidationLog(models.Model):
    """Build 配置檢查記錄（可選）"""
    
    VALIDATION_STATUS_CHOICES = [
        ('passed', '全部通過'),
        ('warning', '有警告'),
        ('failed', '檢查失敗'),
    ]
    
    build = models.ForeignKey(
        JenkinsBuild,
        on_delete=models.CASCADE,
        related_name='validation_logs',
        verbose_name='所屬 Build'
    )
    
    status = models.CharField(
        max_length=20,
        choices=VALIDATION_STATUS_CHOICES,
        verbose_name='檢查狀態'
    )
    
    # 檢查結果（JSON 格式）
    validation_results = models.JSONField(
        default=dict,
        verbose_name='檢查結果詳情'
    )
    # 範例結構:
    # {
    #     'host_ip': {'status': 'passed', 'message': 'IP 存在且租約有效'},
    #     'host_mac': {'status': 'failed', 'message': 'MAC 格式錯誤'},
    #     'uart_ip': {'status': 'warning', 'message': '租約即將過期'}
    # }
    
    checked_by = models.CharField(max_length=100, verbose_name='檢查人')
    checked_at = models.DateTimeField(auto_now_add=True, verbose_name='檢查時間')
    
    class Meta:
        verbose_name = 'Build 配置檢查記錄'
        verbose_name_plural = 'Build 配置檢查記錄'
        ordering = ['-checked_at']
```

**決策**: 
- ✅ Phase 1 **不創建**此模型，直接返回即時檢查結果
- ⏭️ Phase 2 可選擇性新增，用於檢查歷史記錄和統計分析

---

## API 端點設計

### 1. 檢查 Build 配置（主要端點）

**端點**: `POST /api/jenkins-builds/{id}/validate-config/`

**請求**:
```json
{
    "check_items": ["host_ip", "host_mac", "uart_ip"],  // 可選，指定檢查項目
    "dhcp_server_id": 1  // 可選，指定 DHCP Server
}
```

**響應**:
```json
{
    "build_id": 123,
    "job_name": "RVT-Build-Backend",
    "build_number": 45,
    "overall_status": "warning",  // passed, warning, failed
    "check_results": [
        {
            "item": "host_ip",
            "status": "passed",
            "value": "192.168.1.100",
            "message": "IP 存在且租約有效",
            "details": {
                "lease_found": true,
                "lease_active": true,
                "lease_end": "2025-12-01T10:00:00Z",
                "hostname": "test-host-01",
                "dhcp_server": "DHCP Server 1"
            }
        },
        {
            "item": "host_mac",
            "status": "failed",
            "value": "30-C5-99-55-C9-D3",
            "message": "MAC 地址格式錯誤，必須使用冒號分隔（:）",
            "details": {
                "expected_format": "30:C5:99:55:C9:D3",
                "suggestion": "請修正為 Linux MAC 格式"
            }
        },
        {
            "item": "uart_ip",
            "status": "warning",
            "value": "192.168.1.200",
            "message": "租約即將在 12 小時後過期",
            "details": {
                "lease_found": true,
                "lease_active": true,
                "lease_end": "2025-11-15T22:00:00Z",
                "hours_remaining": 12
            }
        }
    ],
    "checked_at": "2025-11-15T10:00:00Z"
}
```

**錯誤響應**:
```json
{
    "error": "Build not found",
    "code": "BUILD_NOT_FOUND"
}
```

---

### 2. 檢查 IP 是否存在於 DHCP 租約（輔助端點）

**端點**: `GET /api/dhcp-leases/check-ip/?ip={ip_address}`

**請求參數**:
- `ip`: IP 地址（必填）
- `server_id`: DHCP Server ID（可選）

**響應**:
```json
{
    "ip_address": "192.168.1.100",
    "exists": true,
    "lease": {
        "id": 1234,
        "mac_address": "30:C5:99:55:C9:D3",
        "hostname": "test-host-01",
        "lease_start": "2025-11-01T10:00:00Z",
        "lease_end": "2025-12-01T10:00:00Z",
        "is_active": true,
        "dhcp_server_name": "DHCP Server 1"
    }
}
```

---

### 3. 檢查 MAC 地址是否存在於 DHCP 租約（輔助端點）

**端點**: `GET /api/dhcp-leases/check-mac/?mac={mac_address}`

**請求參數**:
- `mac`: MAC 地址（必填，支持多種格式）
- `server_id`: DHCP Server ID（可選）

**響應**:
```json
{
    "mac_address": "30:C5:99:55:C9:D3",
    "format_valid": true,
    "normalized_mac": "30:c5:99:55:c9:d3",
    "exists": true,
    "lease": {
        "id": 1234,
        "ip_address": "192.168.1.100",
        "hostname": "test-host-01",
        "lease_start": "2025-11-01T10:00:00Z",
        "lease_end": "2025-12-01T10:00:00Z",
        "is_active": true,
        "dhcp_server_name": "DHCP Server 1"
    }
}
```

---

### 4. 驗證 MAC 地址格式（輔助端點）

**端點**: `POST /api/utils/validate-mac/`

**請求**:
```json
{
    "mac_address": "30-C5-99-55-C9-D3"
}
```

**響應**:
```json
{
    "original": "30-C5-99-55-C9-D3",
    "is_valid": true,
    "normalized": "30:c5:99:55:c9:d3",
    "format": "windows",  // windows, linux, cisco
    "linux_format": "30:C5:99:55:C9:D3",
    "message": "格式錯誤，應使用冒號分隔（:）"
}
```

---

## 前端頁面設計

### 頁面結構

```
BuildConfigValidatorPage (獨立頁面)
├─ Header
│   ├─ 返回按鈕
│   ├─ Build 資訊（Job 名稱、Build 編號）
│   └─ 總體狀態標籤（通過/警告/失敗）
├─ Configuration Overview Card (配置概覽)
│   ├─ parameters 顯示
│   └─ ansible_config 顯示
├─ Validation Steps (檢查步驟，使用 Ant Design Steps 組件)
│   ├─ Step 1: Host IP 檢查
│   ├─ Step 2: Host MAC 檢查
│   ├─ Step 3: UART IP 檢查
│   └─ (未來) Step 4+: 其他檢查
└─ Results Section (檢查結果區域)
    ├─ Success Items (通過項目)
    ├─ Warning Items (警告項目)
    └─ Failed Items (失敗項目，附帶修正建議)
```

### 路由設計

**URL**: `/rvt-analytics/build-config-validator/:buildId`

**範例**: `/rvt-analytics/build-config-validator/123`

### UI 組件選用（Ant Design）

1. **Steps 組件**: 顯示檢查進度
   ```javascript
   <Steps current={currentStep} status={stepStatus}>
       <Step title="Host IP" description="檢查 IP 租約" />
       <Step title="Host MAC" description="檢查 MAC 格式" />
       <Step title="UART IP" description="檢查 IP 租約" />
   </Steps>
   ```

2. **Result 組件**: 顯示總體檢查結果
   ```javascript
   <Result
       status="success"  // success, warning, error
       title="配置檢查通過"
       subTitle="所有檢查項目均通過驗證"
   />
   ```

3. **Descriptions 組件**: 顯示配置詳情
   ```javascript
   <Descriptions title="Build 配置" bordered>
       <Descriptions.Item label="Host IP">192.168.1.100</Descriptions.Item>
       <Descriptions.Item label="Host MAC">30:C5:99:55:C9:D3</Descriptions.Item>
   </Descriptions>
   ```

4. **Tag 組件**: 顯示檢查狀態
   ```javascript
   <Tag color="success">通過</Tag>
   <Tag color="warning">警告</Tag>
   <Tag color="error">失敗</Tag>
   ```

5. **Alert 組件**: 顯示錯誤訊息和修正建議
   ```javascript
   <Alert
       message="MAC 地址格式錯誤"
       description="應使用 Linux 格式：30:C5:99:55:C9:D3"
       type="error"
       showIcon
   />
   ```

### 顏色方案

```javascript
const statusColors = {
    passed: '#52c41a',    // 綠色（成功）
    warning: '#faad14',   // 橙色（警告）
    failed: '#ff4d4f',    // 紅色（失敗）
    checking: '#1890ff',  // 藍色（檢查中）
};
```

### 互動流程

1. **在 RVTAnalysisPage 的 Build Table 中新增按鈕**:
   ```javascript
   <Button 
       icon={<CheckCircleOutlined />} 
       onClick={() => navigate(`/rvt-analytics/build-config-validator/${build.build_id}`)}
   >
       檢查配置
   </Button>
   ```

2. **點擊後跳轉到獨立檢查頁面**:
   - 顯示載入動畫
   - 載入系統中的 DHCP Server 列表（status='online'）
   - 提供可選的 DHCP Server 選擇器
   - 自動開始檢查（調用 API）
   - 逐步更新檢查結果

3. **DHCP Server 選擇器（可選功能）**:
   ```javascript
   const BuildConfigValidatorPage = () => {
       const [selectedServerId, setSelectedServerId] = useState(null);
       const [dhcpServers, setDhcpServers] = useState([]);
       
       // 載入 DHCP Server 列表（只顯示 online 狀態）
       useEffect(() => {
           axios.get('/api/dhcp-servers/?status=online').then(response => {
               setDhcpServers(response.data);
           });
       }, []);
       
       const handleValidate = async () => {
           setLoading(true);
           try {
               const response = await axios.post(
                   `/api/jenkins-builds/${buildId}/validate-config/`,
                   {
                       dhcp_server_id: selectedServerId,  // 可選，不選則查詢所有 online 的
                       check_items: ['host_ip', 'host_mac', 'uart_ip']
                   }
               );
               setValidationResult(response.data);
           } catch (error) {
               message.error('檢查失敗：' + error.message);
           } finally {
               setLoading(false);
           }
       };
       
       return (
           <div style={{ padding: '24px' }}>
               <Card title="配置檢查設定">
                   {/* DHCP Server 選擇器（可選） */}
                   <Space direction="vertical" style={{ width: '100%' }}>
                       <div>
                           <Text strong>DHCP Server：</Text>
                           <Text type="secondary">
                               （可選，留空則自動從所有在線 DHCP Server 查詢）
                           </Text>
                       </div>
                       <Select
                           placeholder="選擇 DHCP Server（可選）"
                           allowClear
                           style={{ width: '100%' }}
                           value={selectedServerId}
                           onChange={setSelectedServerId}
                       >
                           {dhcpServers.map(server => (
                               <Option key={server.id} value={server.id}>
                                   <Space>
                                       <Badge 
                                           status={server.status === 'online' ? 'success' : 'default'} 
                                       />
                                       {server.name} ({server.ip_address})
                                   </Space>
                               </Option>
                           ))}
                       </Select>
                       
                       <Button 
                           type="primary" 
                           icon={<CheckCircleOutlined />}
                           onClick={handleValidate}
                           loading={loading}
                       >
                           開始檢查
                       </Button>
                   </Space>
               </Card>
               
               {/* 檢查結果展示區域 */}
               {validationResult && (
                   <Card title="檢查結果" style={{ marginTop: 16 }}>
                       {/* Steps, Result, Alert 等組件 */}
                   </Card>
               )}
           </div>
       );
   };
   ```

4. **顯示檢查結果**:
   - 使用 Steps 組件顯示進度
   - 每個檢查項顯示狀態圖標（✅ ⚠️ ❌）
   - 失敗或警告項目展開顯示詳細訊息
   - 如果 DHCP Server offline，顯示特殊警告

5. **提供操作選項**:
   - 返回 RVT Analysis 頁面
   - 重新檢查（可重新選擇 DHCP Server）
   - 導出檢查報告（PDF/JSON）
   - 查看 DHCP Server 狀態（跳轉到 DHCP 管理頁面）

---

### DHCP Server 查詢流程圖

```
開始檢查配置
    ↓
前端：用戶可選擇特定 DHCP Server（或留空）
    ↓
後端：BuildConfigValidator 初始化
    ├─ dhcp_server_id 有值？
    │   ├─ 是 → 只查詢指定的 DHCP Server
    │   └─ 否 → 繼續檢查
    │
    ├─ Build 配置中有 dhcp_server_id？
    │   ├─ 是 → 只查詢配置指定的 DHCP Server
    │   └─ 否 → 繼續檢查
    │
    └─ 查詢所有 status='online' 的 DHCP Server
        ├─ 找到租約 → ✅ 檢查通過
        └─ 沒找到 → 嘗試查詢所有 DHCP Server（包含 offline）
            ├─ 找到租約 → ⚠️ 警告（DHCP Server 離線）
            └─ 沒找到 → ❌ 失敗（租約不存在）
```

---

## 檢查邏輯設計

### DHCP Server 查詢策略

**利用系統現有的 DHCP Server 管理功能，智能查詢租約記錄：**

```python
查詢優先級：
1. API 請求參數指定的 dhcp_server_id（手動指定）
   ↓ (如果沒有)
2. Build 配置中的 dhcp_server_id（配置指定）
   ↓ (如果沒有)
3. 只查詢 status='online' 的 DHCP Server（智能過濾 ⭐ 推薦）
   ↓ (如果沒找到)
4. 嘗試查詢所有 DHCP Server（包含 offline，用於提示）
```

**優勢**：
- ✅ 自動過濾 offline 的 DHCP Server
- ✅ 減少不必要的查詢
- ✅ 提供有意義的錯誤提示
- ✅ 支持手動指定特定 DHCP Server

---

### Service 層架構

```python
# backend/library/services/build_config_validator.py

class BuildConfigValidator:
    """Build 配置檢查器"""
    
    def __init__(self, build: JenkinsBuild, dhcp_server_id: Optional[int] = None):
        self.build = build
        self.dhcp_server_id = dhcp_server_id  # 可選指定 DHCP Server
        self.results = []
        
    def validate_all(self) -> Dict[str, Any]:
        """執行所有檢查"""
        self.results = []
        
        # 1. Host IP 檢查
        self._check_host_ip()
        
        # 2. Host MAC 檢查
        self._check_host_mac()
        
        # 3. UART IP 檢查
        self._check_uart_ip()
        
        # 計算總體狀態
        overall_status = self._calculate_overall_status()
        
        return {
            'build_id': self.build.id,
            'job_name': self.build.job.name,
            'build_number': self.build.build_number,
            'overall_status': overall_status,
            'check_results': self.results,
            'checked_at': timezone.now().isoformat()
        }
    
    def _check_host_ip(self):
        """檢查 Host IP"""
        # 1. 從 parameters 或 ansible_config 提取 host_ip
        host_ip = self._extract_config_value('host_ip')
        
        if not host_ip:
            self.results.append({
                'item': 'host_ip',
                'status': 'failed',
                'value': None,
                'message': '配置中未找到 host_ip',
                'details': {}
            })
            return
        
        # 2. 驗證 IP 格式
        if not self._is_valid_ip(host_ip):
            self.results.append({
                'item': 'host_ip',
                'status': 'failed',
                'value': host_ip,
                'message': 'IP 地址格式錯誤',
                'details': {}
            })
            return
        
        # 3. 查詢 DHCP Lease（智能過濾）
        lease = self._query_dhcp_lease_by_ip(host_ip)
        
        if not lease:
            # 沒找到租約，嘗試從所有 DHCP Server（包含 offline）查詢
            all_lease = DHCPLease.objects.filter(
                ip_address=host_ip,
                is_active=True
            ).first()
            
            if all_lease:
                # 找到了，但 DHCP Server 是 offline 狀態
                self.results.append({
                    'item': 'host_ip',
                    'status': 'warning',
                    'value': host_ip,
                    'message': f'找到租約，但 DHCP Server ({all_lease.server.name}) 狀態為 {all_lease.server.get_status_display()}',
                    'details': {
                        'dhcp_server': all_lease.server.name,
                        'dhcp_server_ip': all_lease.server.ip_address,
                        'dhcp_server_status': all_lease.server.status,
                        'lease_end': all_lease.lease_end.isoformat(),
                        'hostname': all_lease.hostname,
                        'suggestion': '請檢查 DHCP Server 連線狀態'
                    }
                })
            else:
                # 真的沒找到
                online_servers = DHCPServer.objects.filter(status='online')
                self.results.append({
                    'item': 'host_ip',
                    'status': 'failed',
                    'value': host_ip,
                    'message': '未在任何 DHCP Server 中找到該 IP 的租約',
                    'details': {
                        'checked_servers': list(online_servers.values_list('name', flat=True)),
                        'online_servers_count': online_servers.count()
                    }
                })
            return
        
        # 4. 檢查租約是否過期
        now = timezone.now()
        if lease.lease_end < now:
            self.results.append({
                'item': 'host_ip',
                'status': 'failed',
                'value': host_ip,
                'message': '租約已過期',
                'details': {
                    'lease_end': lease.lease_end.isoformat(),
                    'hostname': lease.hostname,
                    'dhcp_server': lease.server.name
                }
            })
            return
        
        # 5. 檢查租約是否即將過期（< 24 小時）
        time_remaining = lease.lease_end - now
        if time_remaining.total_seconds() < 86400:  # 24 小時
            hours_remaining = int(time_remaining.total_seconds() / 3600)
            self.results.append({
                'item': 'host_ip',
                'status': 'warning',
                'value': host_ip,
                'message': f'租約即將在 {hours_remaining} 小時後過期',
                'details': {
                    'lease_found': True,
                    'lease_active': True,
                    'lease_end': lease.lease_end.isoformat(),
                    'hours_remaining': hours_remaining,
                    'hostname': lease.hostname,
                    'dhcp_server': lease.server.name
                }
            })
            return
        
        # 6. 檢查通過
        self.results.append({
            'item': 'host_ip',
            'status': 'passed',
            'value': host_ip,
            'message': 'IP 存在且租約有效',
            'details': {
                'lease_found': True,
                'lease_active': True,
                'lease_end': lease.lease_end.isoformat(),
                'hostname': lease.hostname,
                'dhcp_server': lease.server.name
            }
        })
    
    def _check_host_mac(self):
        """檢查 Host MAC 地址"""
        # 1. 從 parameters 或 ansible_config 提取 host_mac
        host_mac = self._extract_config_value('host_mac')
        
        if not host_mac:
            self.results.append({
                'item': 'host_mac',
                'status': 'failed',
                'value': None,
                'message': '配置中未找到 host_mac',
                'details': {}
            })
            return
        
        # 2. 驗證 MAC 格式（必須為 Linux 格式）
        if not self._is_linux_mac_format(host_mac):
            # 檢查是否為其他格式（Windows: 30-C5-99-55-C9-D3）
            if '-' in host_mac:
                correct_format = host_mac.replace('-', ':')
                self.results.append({
                    'item': 'host_mac',
                    'status': 'failed',
                    'value': host_mac,
                    'message': 'MAC 地址格式錯誤，必須使用冒號分隔（:）',
                    'details': {
                        'expected_format': correct_format,
                        'suggestion': f'請修正為 {correct_format}'
                    }
                })
            else:
                self.results.append({
                    'item': 'host_mac',
                    'status': 'failed',
                    'value': host_mac,
                    'message': 'MAC 地址格式錯誤',
                    'details': {}
                })
            return
        
        # 3. 正規化 MAC 地址（轉為小寫）
        normalized_mac = host_mac.lower()
        
        # 4. 查詢 DHCP Lease（智能過濾）
        lease = self._query_dhcp_lease_by_mac(normalized_mac)
        
        if not lease:
            self.results.append({
                'item': 'host_mac',
                'status': 'failed',
                'value': host_mac,
                'message': '未在 DHCP Server 中找到該 MAC 的租約',
                'details': {}
            })
            return
        
        # 5. 檢查 MAC 對應的 IP 是否與 host_ip 一致
        host_ip = self._extract_config_value('host_ip')
        if host_ip and lease.ip_address != host_ip:
            self.results.append({
                'item': 'host_mac',
                'status': 'warning',
                'value': host_mac,
                'message': f'MAC 對應的 IP ({lease.ip_address}) 與配置的 host_ip ({host_ip}) 不一致',
                'details': {
                    'lease_ip': lease.ip_address,
                    'config_ip': host_ip,
                    'hostname': lease.hostname,
                    'dhcp_server': lease.server.name
                }
            })
            return
        
        # 6. 檢查通過
        self.results.append({
            'item': 'host_mac',
            'status': 'passed',
            'value': host_mac,
            'message': 'MAC 地址格式正確且存在租約',
            'details': {
                'lease_found': True,
                'lease_active': True,
                'lease_ip': lease.ip_address,
                'hostname': lease.hostname,
                'dhcp_server': lease.server.name
            }
        })
    
    def _check_uart_ip(self):
        """檢查 UART IP（邏輯類似 _check_host_ip）"""
        # 實現邏輯與 _check_host_ip 相同
        pass
    
    def _extract_config_value(self, key: str) -> Optional[str]:
        """從 parameters 或 ansible_config 提取配置值"""
        # 優先從 parameters 提取
        if key in self.build.parameters:
            return self.build.parameters[key]
        
        # 從 ansible_config 提取
        if key in self.build.ansible_config:
            return self.build.ansible_config[key]
        
        # 從 ansible_config.extra_vars 提取
        if 'extra_vars' in self.build.ansible_config:
            if key in self.build.ansible_config['extra_vars']:
                return self.build.ansible_config['extra_vars'][key]
        
        return None
    
    @staticmethod
    def _is_valid_ip(ip: str) -> bool:
        """驗證 IP 格式"""
        try:
            ipaddress.ip_address(ip)
            return True
        except ValueError:
            return False
    
    @staticmethod
    def _is_linux_mac_format(mac: str) -> bool:
        """驗證 Linux MAC 格式（AA:BB:CC:DD:EE:FF）"""
        import re
        pattern = r'^([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}$'
        return bool(re.match(pattern, mac))
    
    def _calculate_overall_status(self) -> str:
        """計算總體狀態"""
        if any(r['status'] == 'failed' for r in self.results):
            return 'failed'
        elif any(r['status'] == 'warning' for r in self.results):
            return 'warning'
        else:
            return 'passed'
    
    def _query_dhcp_lease_by_ip(self, ip: str) -> Optional[DHCPLease]:
        """
        查詢 DHCP Lease（按 IP）
        
        查詢優先級：
        1. API 指定的 dhcp_server_id
        2. Build 配置中的 dhcp_server_id
        3. 只查詢 online 的 DHCP Server
        """
        query = DHCPLease.objects.filter(
            ip_address=ip,
            is_active=True
        )
        
        # 1. 優先使用 API 傳入的 dhcp_server_id
        if self.dhcp_server_id:
            query = query.filter(server_id=self.dhcp_server_id)
        # 2. 從 Build 配置中讀取
        else:
            config_server_id = self._extract_config_value('dhcp_server_id')
            if config_server_id:
                query = query.filter(server_id=config_server_id)
            # 3. 只查詢 online 的 DHCP Server
            else:
                query = query.filter(server__status='online')
        
        return query.first()
    
    def _query_dhcp_lease_by_mac(self, mac: str) -> Optional[DHCPLease]:
        """
        查詢 DHCP Lease（按 MAC）
        
        查詢邏輯同 _query_dhcp_lease_by_ip
        """
        query = DHCPLease.objects.filter(
            mac_address__iexact=mac,
            is_active=True
        )
        
        # 查詢優先級同上
        if self.dhcp_server_id:
            query = query.filter(server_id=self.dhcp_server_id)
        else:
            config_server_id = self._extract_config_value('dhcp_server_id')
            if config_server_id:
                query = query.filter(server_id=config_server_id)
            else:
                query = query.filter(server__status='online')
        
        return query.first()
```

---

### DHCP Server 狀態處理

**系統會自動處理不同狀態的 DHCP Server**：

| DHCP Server 狀態 | 查詢行為 | 結果處理 |
|-----------------|---------|---------|
| `online` | ✅ 優先查詢 | 正常檢查租約 |
| `offline` | ⚠️ 跳過（預設） | 如果找到，返回警告狀態 |
| `warning` | ⚠️ 跳過（預設） | 如果找到，返回警告狀態 |

**智能錯誤提示**：
```json
// 範例：DHCP Server offline 時的警告
{
    "item": "host_ip",
    "status": "warning",
    "value": "192.168.1.100",
    "message": "找到租約，但 DHCP Server (DHCP-Server-01) 狀態為 Offline",
    "details": {
        "dhcp_server": "DHCP-Server-01",
        "dhcp_server_ip": "10.10.10.1",
        "dhcp_server_status": "offline",
        "suggestion": "請檢查 DHCP Server 連線狀態"
    }
}
```

---
```

### MAC 地址格式處理

**支持的格式**:
- ✅ **Linux 格式**（推薦）: `30:C5:99:55:C9:D3`
- ❌ **Windows 格式**: `30-C5-99-55-C9-D3` → 需要轉換
- ❌ **Cisco 格式**: `30c5.9955.c9d3` → 需要轉換

**正規化邏輯**:
```python
def normalize_mac(mac: str) -> str:
    """正規化 MAC 地址為 Linux 格式"""
    # 移除所有分隔符
    clean_mac = mac.replace(':', '').replace('-', '').replace('.', '')
    
    # 驗證長度
    if len(clean_mac) != 12:
        raise ValueError('Invalid MAC address length')
    
    # 轉為小寫
    clean_mac = clean_mac.lower()
    
    # 每兩個字符插入冒號
    formatted_mac = ':'.join([clean_mac[i:i+2] for i in range(0, 12, 2)])
    
    return formatted_mac
```

---

## 開發階段規劃

### Phase 1: 核心功能（優先實現）

**時程**: 2-3 週

#### 後端開發
1. ✅ 創建 `BuildConfigValidator` Service
2. ✅ 實現 Host IP 檢查邏輯
3. ✅ 實現 Host MAC 檢查邏輯
4. ✅ 實現 UART IP 檢查邏輯
5. ✅ 創建 API 端點 `/api/jenkins-builds/{id}/validate-config/`
6. ✅ 編寫單元測試

#### 前端開發
1. ✅ 創建 `BuildConfigValidatorPage` 頁面
2. ✅ 在 RVTAnalysisPage 新增「檢查配置」按鈕
3. ✅ 實現檢查結果展示（Steps + Result）
4. ✅ 實現配置概覽卡片（Descriptions）
5. ✅ 實現錯誤提示和修正建議（Alert）

#### 測試與文檔
1. ✅ 編寫整合測試
2. ✅ 編寫使用文檔
3. ✅ 內部測試與優化

---

### Phase 2: 擴展功能（未來計劃）

**時程**: 1-2 週

1. ✅ 新增 Switch IP/Port 檢查
2. ✅ 新增 Ansible Playbook 檔案檢查
3. ✅ 新增檢查歷史記錄功能（`BuildConfigValidationLog` 模型）
4. ✅ 新增批量檢查功能（同時檢查多個 Build）
5. ✅ 新增檢查報告導出功能（PDF/JSON）

---

### Phase 3: 優化與統計（長期計劃）

1. ✅ 新增檢查統計儀表板
2. ✅ 新增配置錯誤趨勢分析
3. ✅ 新增自動修正建議功能
4. ✅ 整合 Jenkins API 自動更新配置

---

## 測試計劃

### 單元測試（Unit Tests）

**位置**: `tests/unit/backend/test_build_config_validator.py`

```python
class BuildConfigValidatorTestCase(TestCase):
    
    def setUp(self):
        # 創建測試數據
        self.server = JenkinsServer.objects.create(...)
        self.job = JenkinsJob.objects.create(...)
        self.build = JenkinsBuild.objects.create(
            job=self.job,
            parameters={
                'host_ip': '192.168.1.100',
                'host_mac': '30:C5:99:55:C9:D3',
                'uart_ip': '192.168.1.200'
            }
        )
        
        self.dhcp_server = DHCPServer.objects.create(...)
        self.lease = DHCPLease.objects.create(
            server=self.dhcp_server,
            ip_address='192.168.1.100',
            mac_address='30:c5:99:55:c9:d3',
            is_active=True,
            lease_end=timezone.now() + timedelta(days=7)
        )
    
    def test_check_host_ip_success(self):
        """測試 Host IP 檢查通過"""
        validator = BuildConfigValidator(self.build)
        validator._check_host_ip()
        
        self.assertEqual(len(validator.results), 1)
        self.assertEqual(validator.results[0]['status'], 'passed')
    
    def test_check_host_mac_format_error(self):
        """測試 MAC 格式錯誤"""
        self.build.parameters['host_mac'] = '30-C5-99-55-C9-D3'
        self.build.save()
        
        validator = BuildConfigValidator(self.build)
        validator._check_host_mac()
        
        self.assertEqual(validator.results[0]['status'], 'failed')
        self.assertIn('格式錯誤', validator.results[0]['message'])
```

### 整合測試（Integration Tests）

**位置**: `tests/integration/api/test_build_config_api.py`

```python
class BuildConfigValidationAPITest(APITestCase):
    
    def test_validate_config_api(self):
        """測試配置檢查 API"""
        response = self.client.post(
            f'/api/jenkins-builds/{self.build.id}/validate-config/'
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertIn('overall_status', response.data)
        self.assertIn('check_results', response.data)
```

### E2E 測試（End-to-End Tests）

**位置**: `tests/e2e/test_build_config_workflow.py`

**測試流程**:
1. 用戶在 RVT Analysis 頁面點擊「檢查配置」按鈕
2. 跳轉到檢查頁面
3. 自動執行檢查
4. 顯示檢查結果
5. 返回 RVT Analysis 頁面

---

## 未來擴展計劃

### 第一階段擴展（已規劃）
- ✅ Switch IP/Port 檢查
- ✅ Ansible Playbook 檔案檢查
- ✅ NAS 存儲路徑檢查

### 第二階段擴展（待討論）
- 🔄 自動修正配置錯誤
- 🔄 與 Jenkins API 整合，直接修改 Job 參數
- 🔄 配置模板管理（預設配置、配置繼承）
- 🔄 配置差異對比（比較不同 Build 的配置差異）

### 第三階段擴展（長期計劃）
- 🔄 AI 輔助配置建議
- 🔄 配置錯誤預測（基於歷史數據）
- 🔄 自動化配置審核流程

---

## 附錄

### A. MAC 地址格式轉換對照表

| 格式類型 | 範例 | 說明 |
|---------|------|------|
| Linux (推薦) | `30:C5:99:55:C9:D3` | 使用冒號分隔，大寫 |
| Windows | `30-C5-99-55-C9-D3` | 使用連字號分隔 |
| Cisco | `30c5.9955.c9d3` | 使用點號分隔，每 4 個字符一組 |
| 無分隔符 | `30C59955C9D3` | 連續 12 個字符 |

### B. 檢查狀態對照表

| 狀態 | 圖標 | 顏色 | 說明 |
|-----|------|------|------|
| `passed` | ✅ | 綠色 | 檢查通過 |
| `warning` | ⚠️ | 橙色 | 有警告，但不影響執行 |
| `failed` | ❌ | 紅色 | 檢查失敗，需要修正 |
| `checking` | 🔄 | 藍色 | 檢查中 |

### C. 常見錯誤訊息

| 錯誤類型 | 訊息 | 修正建議 |
|---------|------|---------|
| IP 格式錯誤 | "IP 地址格式錯誤" | 請檢查 IP 格式是否正確（如 192.168.1.100） |
| 租約不存在 | "未在 DHCP Server 中找到該 IP 的租約" | 請確認 IP 是否已分配或檢查 DHCP Server |
| 租約已過期 | "租約已過期" | 請重新申請租約或延長租約時間 |
| MAC 格式錯誤 | "MAC 地址格式錯誤" | 必須使用 Linux 格式（如 30:C5:99:55:C9:D3） |
| IP/MAC 不一致 | "MAC 對應的 IP 與配置不一致" | 請檢查 Host IP 和 Host MAC 是否對應同一設備 |

---

## 更新記錄

| 日期 | 版本 | 更新內容 | 作者 |
|-----|------|---------|------|
| 2025-11-15 | 1.0 | 初版規劃文檔 | Network Toolbox Team |

---

**文檔結束** 📄
