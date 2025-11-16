# Build 資訊取得方法比較分析

**分析日期**: 2025-11-16  
**對比對象**: Build 配置檢查頁面 vs Build 配置頁面

---

## 📊 概述

本文檔比較「Build 配置檢查」(Build Config Validator) 和「Build 配置頁面」(Ansible Inventory 顯示) 這兩個功能如何取得 Build 資訊的差異。

---

## 🔍 方法一：Build 配置檢查 (BuildConfigValidator)

### 使用場景
- 驗證 Build 的 HOST_IP、HOST_MAC、UART_IP 是否有效
- 檢查配置是否存在於 DHCP 資料庫中

### 數據流程

```
前端 (BuildConfigValidatorPage.js)
    ↓ Step 1: 取得 Build 基本資訊
    GET /api/jenkins-builds/{buildId}/
    ← JenkinsBuild 資料（id, job_id, build_number, parameters, ansible_config）
    ↓ Step 2: 執行配置驗證
    POST /api/jenkins-builds/{buildId}/validate_config/
    ↓
後端 (BuildConfigValidator)
    ↓ Step 3: 載入 Build
    JenkinsBuild.objects.filter(id=build_id).first()
    ← self.build (包含 job FK 關聯)
    ↓ Step 4: 呼叫 Ansible Inventory API
    GET http://localhost:8000/api/jenkins-jobs/{job_id}/ansible-inventory/?use_cache=true
    ← Ansible Inventory JSON（_meta.hostvars 包含所有主機配置）
    ↓ Step 5: 從 hostvars 中選擇主機
    if job_name in hostvars:
        config = hostvars[job_name]  # 精確匹配
    else:
        config = hostvars[first_hostname]  # 備用第一個主機
    ↓ Step 6: 欄位映射
    ansible_host → HOST_IP
    macaddress   → HOST_MAC
    uart_host    → UART_IP (if valid IP)
    ↓ Step 7: DHCP 驗證
    DHCPLease.objects.filter(ip_address=HOST_IP, server_id__in=dhcp_server_ids)
    ← 租約記錄（mac_address, hostname, lease_start, lease_end）
    ↓
返回驗證結果
```

### 關鍵代碼

**1. 取得 Build 資料（資料庫查詢）**
```python
# library/services/build_config_validator.py: Line 98
from api.models import JenkinsBuild

self.build = JenkinsBuild.objects.filter(id=self.build_id).first()
# 取得：
# - self.build.id
# - self.build.job (ForeignKey 關聯)
# - self.build.parameters (JSON 欄位)
# - self.build.ansible_config (JSON 欄位)
```

**2. 呼叫 Ansible Inventory API（內部 API 請求）**
```python
# library/services/build_config_validator.py: Line 177
import requests

job_id = self.build.job.id
api_url = f"http://localhost:8000/api/jenkins-jobs/{job_id}/ansible-inventory/"
response = requests.get(api_url, params={'use_cache': True}, timeout=10)

# 回應結構：
{
    'success': True,
    'data': {
        '_meta': {
            'hostvars': {
                'Test-KVM01': {
                    'ansible_host': '10.250.71.22',
                    'macaddress': 'CC:28:AA:86:C3:7F',
                    'uart_host': '10.250.71.65',
                    # ...其他 39 個參數
                },
                'SAF1318_KVM02': { ... },
                # ...共 21 個主機
            }
        }
    }
}
```

**3. 主機名稱匹配邏輯**
```python
# library/services/build_config_validator.py: Line 195-209
hostvars = data['data']['_meta'].get('hostvars', {})
job_name = self.build.job.name  # 例如：'Test-KVM01'

# 策略 1: 精確匹配 job name
if job_name and job_name in hostvars:
    target_hostname = job_name
    target_config = hostvars[job_name]
    logger.info(f"✅ Found exact match for job name: {job_name}")

# 策略 2: 使用第一個主機（備用方案）
if not target_config:
    target_hostname = list(hostvars.keys())[0]
    target_config = hostvars[target_hostname]
    logger.warning(f"⚠️ No exact match, using first host: {target_hostname}")
```

**4. 欄位映射**
```python
# library/services/build_config_validator.py: Line 215-226
mapped_config = {}
mapped_config.update(target_config)  # 保留所有原始欄位

# 映射特定欄位
if 'ansible_host' in target_config:
    mapped_config['HOST_IP'] = target_config['ansible_host']

if 'macaddress' in target_config:
    mapped_config['HOST_MAC'] = target_config['macaddress']

if 'uart_host' in target_config:
    if self._is_valid_ip(target_config['uart_host']):
        mapped_config['UART_IP'] = target_config['uart_host']
```

**5. DHCP 驗證**
```python
# library/services/build_config_validator.py: Line 441-463
from api.models import DHCPLease

query = DHCPLease.objects.filter(ip_address=ip_address)
if self.dhcp_server_ids:
    query = query.filter(server_id__in=self.dhcp_server_ids)

lease = query.first()
# 返回：
{
    'ip_address': '10.250.71.22',
    'mac_address': 'cc:28:aa:86:c3:7f',
    'hostname': 'minint-o7gopl6',
    'dhcp_server': '10.250.71.1',
    'lease_start': '2025-11-15T23:45:05...',
    'lease_end': '2025-11-21T06:26:05...',
    'is_active': True
}
```

### 配置來源優先順序

```python
# library/services/build_config_validator.py: Line 115-154
# Priority 1: Ansible Inventory API (首選)
config_from_api = self._fetch_config_from_ansible_api()
if config_from_api:
    self.config = config_from_api
    self.config_source = 'ansible_inventory'  # ← 實際使用
    return True

# Priority 2: Database JenkinsBuild.parameters (備用)
if self.build.parameters:
    self.config.update(self.build.parameters)
    
# Priority 3: Database JenkinsBuild.ansible_config (備用)
if self.build.ansible_config:
    self.config.update(self.build.ansible_config)

self.config_source = 'database'  # 只有當 API 失敗時才使用
```

### 數據來源
- **主要來源**: Ansible Inventory API → 從 NAS 儲存的 `inventory/hosts` 檔案解析
- **備用來源**: JenkinsBuild 資料庫的 `parameters` 和 `ansible_config` 欄位
- **驗證來源**: DHCPLease 資料庫

---

## 🎯 方法二：Build 配置頁面 (Ansible Inventory 顯示)

### 使用場景
- 顯示完整的 Ansible Inventory 資料
- 查看所有主機的詳細配置
- 瀏覽 Groups、Variables、Hostvars

### 數據流程

```
前端 (RVTAnalysisPage.js)
    ↓ Step 1: 取得所有 Builds 列表
    GET /api/jenkins-builds/
    ← builds 陣列（id, job_id, job_name, build_number, status...）
    ↓ Step 2: 使用者點擊「配置」按鈕
    handleViewAnsibleConfig(record)
    設置：jobId=record.job_id, jobName=record.job_name, buildNumber=record.build_number
    ↓ Step 3: Drawer 組件呼叫 Ansible Inventory API
    (AnsibleInventoryDrawer.js)
    GET /api/jenkins-jobs/{jobId}/ansible-inventory/?use_cache=true
    ↓
後端 (JenkinsJobViewSet.ansible_inventory)
    ↓ Step 4: 找到最新的 Build
    latest_build = job.builds.filter(is_artifacts_stored=True).order_by('-build_number').first()
    ↓ Step 5: 構建 inventory 檔案路徑
    artifacts_path = Path(latest_build.artifacts_path)
    inventory_path = artifacts_path / 'inventory' / 'hosts'
    # 例如：/mnt/nas/jenkins_test_storage/10.252.170.171/Test-KVM01/148/inventory/hosts
    ↓ Step 6: 解析 Ansible Inventory 檔案
    (AnsibleInventoryService)
    parser.read(inventory_path)
    解析 INI 格式：[groups], [host:vars], 等等
    ↓ Step 7: 生成 JSON 格式
    {
        '_meta': {
            'hostvars': { ... }  # 所有主機變數
        },
        'group1': ['host1', 'host2'],
        'group2': ['host3'],
        ...
    }
    ↓
返回完整 Inventory JSON
```

### 關鍵代碼

**1. 前端點擊「配置」按鈕**
```javascript
// frontend/src/pages/RVTAnalysisPage.js: Line 392
const handleViewAnsibleConfig = (record) => {
    // record 來自 /api/jenkins-builds/ 的回應
    setAnsibleConfigDrawer({
        visible: true,
        jobId: record.job_id,      // ← 使用 job_id，不是 build_id
        jobName: record.job_name,
        buildNumber: record.build_number,
        hostname: record.job_name,  // 只顯示與 job_name 相同的主機
    });
};
```

**2. 後端找到最新 Build 的 inventory 檔案**
```python
# backend/api/views/jenkins.py: Line 454-487
def _get_latest_build_inventory_path(self, job: 'JenkinsJob') -> Optional[str]:
    """
    獲取最新 Build 的 inventory/hosts 文件路徑
    """
    # 找到最新有 artifacts 的 Build
    latest_build = job.builds.filter(
        is_artifacts_stored=True
    ).order_by('-build_number').first()
    
    if not latest_build:
        return None
    
    # 構建路徑：{artifacts_path}/inventory/hosts
    artifacts_path = Path(latest_build.artifacts_path)
    # 例如：/mnt/nas/jenkins_test_storage/10.252.170.171/Test-KVM01/148
    
    inventory_path = artifacts_path / 'inventory' / 'hosts'
    # 完整路徑：/mnt/nas/.../148/inventory/hosts
    
    if not inventory_path.exists():
        return None
    
    return str(inventory_path)
```

**3. API 端點回應**
```python
# backend/api/views/jenkins.py: Line 489-556
@action(detail=True, methods=['get'], url_path='ansible-inventory')
def ansible_inventory(self, request, pk=None):
    """
    GET /api/jenkins-jobs/{id}/ansible-inventory/
    """
    job = self.get_object()  # 透過 job_id 取得 JenkinsJob
    
    # 取得 inventory 檔案路徑
    inventory_path = self._get_latest_build_inventory_path(job)
    
    # 使用 AnsibleInventoryService 解析
    service = AnsibleInventoryService(inventory_path)
    result = service.get_full_inventory(use_cache=True)
    
    # 取得 Build 資訊
    latest_build = job.builds.filter(
        is_artifacts_stored=True
    ).order_by('-build_number').first()
    
    return Response({
        'success': True,
        'job_id': job.id,
        'job_name': job.name,
        'build_number': latest_build.build_number,  # ← 回傳最新 Build 編號
        'cached': result['cached'],
        'data': result['data']  # 完整 Inventory JSON
    })
```

### 數據來源
- **Build 列表**: `/api/jenkins-builds/` → JenkinsBuild 資料庫
- **Inventory 資料**: 從 NAS 儲存的最新 Build 的 `inventory/hosts` 檔案
- **解析服務**: AnsibleInventoryService (支援快取)

---

## 🔄 關鍵差異比較

| 比較項目 | Build 配置檢查 | Build 配置頁面 |
|---------|--------------|--------------|
| **入口參數** | `build_id` | `job_id` |
| **查詢方式** | `JenkinsBuild.objects.get(id=build_id)` | `JenkinsJob.objects.get(id=job_id)` |
| **Build 選擇** | 使用指定的 Build | **自動選擇最新 Build** |
| **API 路徑** | `/api/jenkins-builds/{build_id}/validate_config/` | `/api/jenkins-jobs/{job_id}/ansible-inventory/` |
| **內部 API 呼叫** | ✅ 是（validator 呼叫 ansible-inventory API）| ❌ 否（直接讀取檔案）|
| **主機篩選** | 根據 `job_name` 精確匹配 | 回傳**所有主機**（前端可篩選）|
| **欄位映射** | 映射到 `HOST_IP`, `HOST_MAC`, `UART_IP` | 保持原始 Ansible 欄位名稱 |
| **DHCP 驗證** | ✅ 驗證 IP/MAC 是否存在於 DHCP 租約 | ❌ 不驗證 |
| **回傳資料** | 驗證結果（status, checks, suggestions）| 完整 Inventory JSON |
| **使用場景** | 配置**驗證與檢查** | 配置**查看與瀏覽** |

---

## 📝 詳細流程圖

### Build 配置檢查流程

```
使用者選擇 Build #148
    ↓
buildId = 1048
    ↓
[資料庫] JenkinsBuild(id=1048)
    ├─ build.id = 1048
    ├─ build.job = JenkinsJob(id=269, name='Test-KVM01')
    ├─ build.build_number = 148
    ├─ build.parameters = {...}
    └─ build.ansible_config = {...}
    ↓
[內部 API] GET /api/jenkins-jobs/269/ansible-inventory/
    ↓
[後端查詢] latest_build = job.builds.filter(is_artifacts_stored=True).order_by('-build_number').first()
    ← Build #148 (最新的)
    ↓
[檔案系統] /mnt/nas/jenkins_test_storage/10.252.170.171/Test-KVM01/148/inventory/hosts
    ↓
[解析服務] AnsibleInventoryService
    ↓
回傳 21 個主機的 hostvars
    ↓
[BuildConfigValidator] 
    ├─ 檢查 job_name 是否在 hostvars 中
    ├─ 'Test-KVM01' in hostvars → ✅ 精確匹配
    ├─ config = hostvars['Test-KVM01']
    ├─ 映射：ansible_host → HOST_IP (10.250.71.22)
    ├─ 映射：macaddress → HOST_MAC (CC:28:AA:86:C3:7F)
    └─ 映射：uart_host → UART_IP
    ↓
[DHCP 驗證] DHCPLease.objects.filter(ip_address='10.250.71.22')
    ← 找到租約記錄
    ↓
返回驗證結果：
{
    "overall_status": "warning",
    "config_source": "ansible_inventory",
    "checks": {
        "host_ip": {
            "status": "success",
            "message": "HOST_IP found in DHCP lease: 10.250.71.22",
            ...
        },
        ...
    }
}
```

### Build 配置頁面流程

```
使用者點擊「配置」按鈕
    ↓
record = {
    build_id: 1048,
    job_id: 269,           ← 使用這個
    job_name: 'Test-KVM01',
    build_number: 148
}
    ↓
setAnsibleConfigDrawer({
    jobId: 269,           ← 傳遞 job_id，不是 build_id
    jobName: 'Test-KVM01',
    buildNumber: 148
})
    ↓
[前端] GET /api/jenkins-jobs/269/ansible-inventory/
    ↓
[後端] JenkinsJobViewSet.ansible_inventory(pk=269)
    ├─ job = JenkinsJob.objects.get(id=269)
    └─ latest_build = job.builds.filter(...).order_by('-build_number').first()
       ← 自動選擇 Build #148（最新）
    ↓
[檔案系統] /mnt/nas/.../Test-KVM01/148/inventory/hosts
    ↓
[解析服務] AnsibleInventoryService.get_full_inventory()
    ↓
回傳**完整** Inventory：
{
    "success": true,
    "job_id": 269,
    "job_name": "Test-KVM01",
    "build_number": 148,
    "cached": true,
    "data": {
        "_meta": {
            "hostvars": {
                "Test-KVM01": { ... },    ← 21 個主機全部回傳
                "SAF1318_KVM02": { ... },
                "Test-KVM03": { ... },
                ...
            }
        },
        "group1": [...],
        "group2": [...]
    }
}
    ↓
[前端] AnsibleInventoryDrawer 顯示
    ├─ 可選擇主機名稱（下拉選單）
    ├─ 顯示所有變數（table）
    └─ 支援搜尋和篩選
```

---

## 🎯 核心差異總結

### 1. **入口點差異**

**Build 配置檢查**：
- 從具體的 **Build ID** 開始
- 明確指定要檢查哪一個 Build
- 適合：「我要檢查這個 Build 的配置是否正確」

**Build 配置頁面**：
- 從 **Job ID** 開始
- 自動使用 Job 的**最新 Build**
- 適合：「我要查看這個 Job 的配置內容」

### 2. **Build 選擇邏輯**

```python
# Build 配置檢查
self.build = JenkinsBuild.objects.filter(id=build_id).first()
# ← 使用者指定的 Build（例如 #148）

# Build 配置頁面
latest_build = job.builds.filter(
    is_artifacts_stored=True
).order_by('-build_number').first()
# ← 自動選擇最新的 Build（也可能是 #148）
```

### 3. **API 呼叫層級**

```
Build 配置檢查（雙層 API）：
前端 → /api/jenkins-builds/{build_id}/validate_config/
         ↓ (內部)
         /api/jenkins-jobs/{job_id}/ansible-inventory/
         ↓ (檔案系統)
         inventory/hosts 檔案

Build 配置頁面（單層 API）：
前端 → /api/jenkins-jobs/{job_id}/ansible-inventory/
         ↓ (檔案系統)
         inventory/hosts 檔案
```

### 4. **資料處理方式**

| 項目 | Build 配置檢查 | Build 配置頁面 |
|-----|--------------|--------------|
| **主機數量** | 1 個（精確匹配 job_name）| 21 個（全部主機）|
| **欄位名稱** | 映射為標準名稱（HOST_IP）| 保持原始名稱（ansible_host）|
| **額外處理** | DHCP 驗證、狀態判斷 | 無額外處理 |
| **回傳格式** | 驗證結果 + 建議 | 原始 Inventory JSON |

### 5. **實際範例對比**

#### Build 配置檢查的回傳：
```json
{
  "overall_status": "warning",
  "config_source": "ansible_inventory",
  "checks": {
    "host_ip": {
      "status": "success",
      "message": "HOST_IP found in DHCP lease: 10.250.71.22",
      "value": "10.250.71.22",
      "details": {
        "mac_address": "cc:28:aa:86:c3:7f",
        "dhcp_server": "10.250.71.1",
        "lease_end": "2025-11-21T06:26:05..."
      }
    },
    "host_mac": { ... },
    "uart_ip": { ... }
  },
  "summary": {
    "passed": 2,
    "warnings": 1,
    "errors": 0
  }
}
```

#### Build 配置頁面的回傳：
```json
{
  "success": true,
  "job_id": 269,
  "job_name": "Test-KVM01",
  "build_number": 148,
  "data": {
    "_meta": {
      "hostvars": {
        "Test-KVM01": {
          "ansible_host": "10.250.71.22",
          "macaddress": "CC:28:AA:86:C3:7F",
          "uart_host": "10.250.71.65",
          "device_number": "22",
          "... 其他 35 個參數 ..."
        },
        "SAF1318_KVM02": { ... },
        "... 其他 19 個主機 ..."
      }
    },
    "all": ["Test-KVM01", "SAF1318_KVM02", ...],
    "group1": [...],
    "group2": [...]
  }
}
```

---

## 💡 設計決策說明

### 為什麼 Build 配置檢查需要內部呼叫 API？

1. **資料一致性**: 
   - Ansible Inventory API 已經實現檔案解析、快取、錯誤處理
   - 避免重複實現相同邏輯

2. **自動化主機選擇**:
   - Inventory 可能包含多個主機（21 個）
   - 需要根據 `job_name` 自動選擇正確的主機配置

3. **欄位映射與驗證**:
   - `ansible_host` → `HOST_IP`：統一命名規範
   - 額外的 DHCP 驗證：檢查 IP 是否真的存在租約

4. **錯誤回退機制**:
   - 優先使用 Ansible Inventory API（實際配置）
   - 如果失敗，回退到資料庫的 `parameters` 欄位

### 為什麼 Build 配置頁面使用 Job ID？

1. **顯示最新資料**:
   - 使用者通常想看「這個 Job 目前的配置」
   - 自動使用最新 Build 的 inventory

2. **資料完整性**:
   - 顯示所有主機的完整配置（21 個主機）
   - 不需要過濾或映射

3. **UI 設計**:
   - 前端有主機名稱下拉選單，使用者可自行選擇要查看哪個主機
   - 不需要後端預先過濾

---

## 🚀 最佳實踐建議

### 當需要驗證配置時
```python
# 使用 BuildConfigValidator
validator = BuildConfigValidator(build_id=1048)
result = validator.validate()
# → 取得：驗證狀態、DHCP 租約、建議
```

### 當需要查看完整配置時
```python
# 使用 Ansible Inventory API
GET /api/jenkins-jobs/269/ansible-inventory/
# → 取得：所有主機、所有變數、Groups
```

### 當需要查詢特定主機時
```python
# 使用 Ansible Inventory Hosts API
GET /api/jenkins-jobs/269/ansible-inventory/hosts/Test-KVM01/
# → 取得：特定主機的所有變數
```

---

## 📚 相關文件

- `library/services/build_config_validator.py` - Build 配置驗證服務
- `backend/api/views/jenkins.py` - Jenkins API 視圖（包含 ansible-inventory 端點）
- `library/services/ansible_inventory_service.py` - Ansible Inventory 解析服務
- `frontend/src/pages/BuildConfigValidatorPage.js` - Build 配置檢查頁面
- `frontend/src/pages/RVTAnalysisPage.js` - RVT 分析頁面（包含「配置」按鈕）

---

**結論**: 兩個功能使用不同的資料取得策略，但最終都指向同一個資料來源（NAS 上的 `inventory/hosts` 檔案）。Build 配置檢查專注於**驗證與檢查**，而 Build 配置頁面專注於**查看與瀏覽**。
