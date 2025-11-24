# Ansible Inventory MDT Web 檢查功能實施計劃

**計劃日期**：2025-11-24  
**負責人員**：開發團隊  
**狀態**：📋 規劃中

---

## 📋 需求背景

在 Ansible Inventory 配置檢查功能中，需要新增 **MDT Web 檢查**，用於驗證：

1. **MDT Web IP 地址正確性**
   - 根據 DHCP Server IP 自動計算 MDT Web IP
   - 規則：前 3 碼與 DHCP Server 相同，最後一碼固定為 `2`
   - 範例：DHCP Server = `10.250.10.1` → MDT Web = `10.250.10.2`

2. **MDT Web 網站可訪問性**
   - 檢查 MDT Web 服務是否正常運行
   - 測試 HTTP/HTTPS 連線和 API 回應

3. **設備資訊一致性**
   - 根據 Inventory 中的 `device_number` 查詢 MDT Web
   - 比對 IP 地址、MAC 地址等配置
   - 提供詳細的差異報告

---

## 🎯 實施方案：整合到配置驗證器

### 架構設計

```
Ansible Inventory 配置檢查流程
├── 1. 語法驗證                    [已實現]
├── 2. 結構完整性檢查              [已實現]
├── 3. 主機配置檢查                [已實現]
├── 4. IP 地址驗證（含 DHCP 比對）  [已實現]
├── 5. MAC 地址驗證（含 DHCP 比對） [已實現]
├── 6. UART SSH 連線檢查           [已實現]
├── 7. NAS 連線檢查                [已實現]
└── 8. MDT Web 檢查                [新增] ← 本次實施
    ├── Step 1: DHCP Server IP 檢測
    ├── Step 2: MDT Web IP 計算與驗證
    ├── Step 3: MDT Web 可訪問性測試
    └── Step 4: 設備資訊一致性驗證
```

---

## 🛠️ 實施步驟

### 步驟 1：創建 MDT Web 服務模組（必需）

**檔案**：`backend/library/services/mdt_web_service.py`

**功能**：
- MDT Web API 連接管理
- 設備資訊查詢
- 配置一致性驗證

**核心類別**：

```python
class MDTWebService:
    """
    MDT Web API 服務
    
    負責與 MDT Web 系統交互，查詢設備資訊並驗證配置
    """
    
    def __init__(self, mdt_web_ip: str, timeout: int = 10):
        """
        初始化服務
        
        Args:
            mdt_web_ip: MDT Web 伺服器 IP 地址
            timeout: HTTP 請求超時時間（秒）
        """
        self.base_url = f"http://{mdt_web_ip}"
        self.timeout = timeout
        self.session = requests.Session()
    
    def check_connection(self) -> Tuple[bool, Optional[str]]:
        """
        檢查 MDT Web 是否可訪問
        
        Returns:
            Tuple[is_accessible, error_message]
            - is_accessible: 是否可訪問
            - error_message: 錯誤訊息（成功時為 None）
        """
        try:
            response = self.session.get(
                f"{self.base_url}/",
                timeout=self.timeout,
                verify=False  # 如果是內部網路，可忽略 SSL 驗證
            )
            
            if response.status_code == 200:
                logger.info(f"✓ MDT Web accessible: {self.base_url}")
                return True, None
            else:
                error_msg = f"HTTP {response.status_code}"
                logger.warning(f"⚠ MDT Web returned error: {error_msg}")
                return False, error_msg
                
        except requests.exceptions.Timeout:
            error_msg = f"連線超時（{self.timeout}秒）"
            logger.error(f"✗ MDT Web timeout: {self.base_url}")
            return False, error_msg
            
        except requests.exceptions.ConnectionError:
            error_msg = "無法連接到伺服器"
            logger.error(f"✗ MDT Web connection failed: {self.base_url}")
            return False, error_msg
            
        except Exception as e:
            error_msg = f"未知錯誤: {str(e)}"
            logger.error(f"✗ MDT Web check failed: {e}", exc_info=True)
            return False, error_msg
    
    def get_device(self, device_number: str) -> Optional[Dict]:
        """
        根據 device_number 查詢設備資訊
        
        Args:
            device_number: 設備號碼（如 PC-SSD-4052）
        
        Returns:
            設備資訊字典，如果未找到則返回 None
            
        範例回應：
        {
            'name': 'PC-SSD-4052',
            'uuid': '49dd0707-02b6-abcb-7996-e89c2594ef72',
            'os_build': 'AUTOMP',
            'comment': '測試設備',
            'info': {
                'vendor': 'ASUS',
                'model': 'System Product Name',
                'product': 'ROG STRIX Z790-E GAMING WIFI II',
                'ip': '10.250.11.21',
                'mac': 'E8:9C:25:94:EF:72',
                'gateway': '10.250.11.254'
            },
            'monitor': {
                'deployment_status': 1,
                'step_name': 'Gather local only',
                'last_time': '2025-11-21T12:03:42+00:00'
            }
        }
        """
        try:
            # MDT Web API 端點：使用 search 參數查詢
            url = f"{self.base_url}/api/devices"
            params = {
                'search': device_number
            }
            
            logger.debug(f"Querying MDT Web: {url}?search={device_number}")
            
            response = self.session.get(
                url,
                params=params,
                timeout=self.timeout
            )
            response.raise_for_status()
            
            devices = response.json()
            
            if not isinstance(devices, list):
                logger.error(f"Unexpected response format: {type(devices)}")
                return None
            
            # 精確匹配設備名稱（API 可能返回多個相似結果）
            for device in devices:
                if device.get('name') == device_number:
                    logger.info(f"✓ Found device in MDT Web: {device_number}")
                    return device
            
            logger.warning(f"⚠ Device not found in MDT Web: {device_number}")
            return None
                
        except Exception as e:
            logger.error(f"✗ Failed to get device {device_number}: {e}", exc_info=True)
            return None
    
    def validate_device_config(
        self, 
        device_number: str, 
        expected_config: Dict
    ) -> Dict:
        """
        驗證設備配置是否一致
        
        Args:
            device_number: 設備號碼
            expected_config: 期望的配置（從 Inventory 讀取）
                {
                    'hostname': 'Test-Device',
                    'ansible_host': '10.250.11.21',
                    'mac_address': 'E8:9C:25:94:EF:72',
                    ...
                }
        
        Returns:
            驗證結果字典：
            {
                'device_found': bool,           # 是否找到設備
                'config_matches': bool,         # 配置是否一致
                'differences': List[Dict],      # 差異列表
                'mdt_web_data': Dict           # MDT Web 中的設備資料
            }
        """
        result = {
            'device_found': False,
            'config_matches': False,
            'differences': [],
            'mdt_web_data': None
        }
        
        # 查詢設備
        mdt_device = self.get_device(device_number)
        
        if not mdt_device:
            logger.warning(f"⚠ Device not found in MDT Web: {device_number}")
            return result
        
        result['device_found'] = True
        result['mdt_web_data'] = mdt_device
        
        # 比對配置
        differences = []
        
        # 比對 IP 地址
        inventory_ip = expected_config.get('ansible_host')
        mdt_ip = mdt_device.get('info', {}).get('ip')
        
        if inventory_ip and mdt_ip and inventory_ip != mdt_ip:
            differences.append({
                'field': 'ip_address',
                'inventory_value': inventory_ip,
                'mdt_web_value': mdt_ip
            })
        
        # 比對 MAC 地址（標準化後比對）
        inventory_mac = expected_config.get('mac_address', '').lower().replace('-', ':')
        mdt_mac = mdt_device.get('info', {}).get('mac', '').lower().replace('-', ':')
        
        if inventory_mac and mdt_mac and inventory_mac != mdt_mac:
            differences.append({
                'field': 'mac_address',
                'inventory_value': inventory_mac,
                'mdt_web_value': mdt_mac
            })
        
        # 比對 Hostname（選用）
        inventory_hostname = expected_config.get('hostname')
        mdt_hostname = mdt_device.get('name')
        
        if inventory_hostname and mdt_hostname and inventory_hostname != mdt_hostname:
            differences.append({
                'field': 'hostname',
                'inventory_value': inventory_hostname,
                'mdt_web_value': mdt_hostname
            })
        
        result['differences'] = differences
        result['config_matches'] = len(differences) == 0
        
        if result['config_matches']:
            logger.info(f"✓ Device config matches: {device_number}")
        else:
            logger.warning(f"⚠ Device config mismatch: {device_number} ({len(differences)} differences)")
        
        return result
```

**依賴套件**：
```python
import requests
import logging
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)
```

---

### 步驟 2：在配置驗證器中添加 MDT Web 檢查

**檔案**：`backend/library/services/inventory_config_validator.py`

**修改位置**：在 `validate()` 方法中添加 MDT Web 檢查

```python
def validate(self) -> Dict:
    """執行完整驗證流程"""
    try:
        logger.info(f"🔍 Starting validation for Inventory ID: {self.inventory_id}")
        
        # 1. 載入 Inventory
        if not self._load_inventory():
            return self._create_error_result("Failed to load inventory")
        
        # 2. 語法驗證
        self._check_syntax()
        
        # 3. 結構完整性檢查
        self._check_structure()
        
        # 4. 主機配置檢查
        self._check_host_config()
        
        # 5. IP 地址驗證（包含 DHCP 租約比對）
        self._check_ip_addresses()
        
        # 6. MAC 地址驗證（包含 DHCP 租約比對）
        self._check_mac_addresses()
        
        # 7. UART SSH 連接檢查
        self._check_uart_ssh_connections()
        
        # 8. NAS 連線檢查
        self._check_nas_connection()
        
        # 9. MDT Web 檢查（新增）
        self._check_mdt_web()
        
        # 10. 網路連線測試（可選）
        if self.check_connectivity:
            self._check_network_connectivity()
        
        # 11. 計算總體狀態
        self._calculate_overall_status()
        
        logger.info(f"✅ Validation complete. Status: {self.validation_results['overall_status']}")
        
        return self.validation_results
        
    except Exception as e:
        logger.error(f"❌ Validation error: {e}", exc_info=True)
        return self._create_error_result(f"Validation exception: {str(e)}")
```

**新增方法**：`_check_mdt_web()`

```python
def _check_mdt_web(self):
    """
    MDT Web 檢查
    
    檢查項目：
    1. DHCP Server IP 檢測
    2. MDT Web IP 正確性（前3碼相同，最後一碼為2）
    3. MDT Web 服務可訪問性
    4. 設備資訊一致性（device_number、IP、MAC）
    """
    try:
        logger.info("🔍 Checking MDT Web configuration...")
        
        result = {
            'status': 'unknown',
            'message': '',
            'value': 'N/A',
            'details': {},
            'suggestions': []
        }
        
        # Step 1: 檢測 DHCP Server IP
        dhcp_server_ip = self._get_dhcp_server_ip()
        
        if not dhcp_server_ip:
            result['status'] = 'warning'
            result['message'] = '未找到 DHCP Server IP，無法驗證 MDT Web'
            result['suggestions'] = ['請在系統中配置至少一個 DHCP Server']
            self.validation_results['checks']['mdt_web'] = result
            logger.warning("⚠ No DHCP Server configured, skipping MDT Web check")
            return
        
        # Step 2: 計算預期的 MDT Web IP
        expected_mdt_web_ip = self._calculate_mdt_web_ip(dhcp_server_ip)
        
        result['details'] = {
            'dhcp_server_ip': dhcp_server_ip,
            'expected_mdt_web_ip': expected_mdt_web_ip
        }
        
        logger.info(f"DHCP Server: {dhcp_server_ip}, Expected MDT Web: {expected_mdt_web_ip}")
        
        # Step 3: 檢查 MDT Web 可訪問性
        from library.services.mdt_web_service import MDTWebService
        
        mdt_service = MDTWebService(expected_mdt_web_ip, timeout=10)
        is_accessible, error_msg = mdt_service.check_connection()
        
        if not is_accessible:
            result['status'] = 'error'
            result['message'] = f'MDT Web ({expected_mdt_web_ip}) 無法訪問'
            result['value'] = '✗ 無法連線'
            result['details']['connection_error'] = error_msg
            result['suggestions'] = [
                f'檢查 MDT Web 是否運行在 {expected_mdt_web_ip}',
                '檢查網路連線和防火牆設置',
                f'錯誤：{error_msg}'
            ]
            self.validation_results['checks']['mdt_web'] = result
            logger.error(f"✗ MDT Web not accessible: {expected_mdt_web_ip}")
            return
        
        logger.info(f"✓ MDT Web accessible: {expected_mdt_web_ip}")
        
        # Step 4: 驗證設備資訊一致性
        devices_validated = []
        devices_mismatched = []
        devices_not_found = []
        
        hosts = self._get_inventory_hosts_with_device_number()
        
        if not hosts:
            result['status'] = 'warning'
            result['message'] = 'Inventory 中沒有設定 device_number 的主機'
            result['value'] = '0 個設備'
            result['suggestions'] = ['在 Inventory 中為主機添加 device_number 變數']
            self.validation_results['checks']['mdt_web'] = result
            logger.warning("⚠ No hosts with device_number found")
            return
        
        logger.info(f"Validating {len(hosts)} devices with device_number...")
        
        for host in hosts:
            device_number = host['device_number']
            
            validation_result = mdt_service.validate_device_config(
                device_number,
                host
            )
            
            if not validation_result['device_found']:
                devices_not_found.append({
                    'device_number': device_number,
                    'hostname': host['hostname']
                })
                logger.warning(f"⚠ Device not found in MDT Web: {device_number}")
                
            elif not validation_result['config_matches']:
                devices_mismatched.append({
                    'device_number': device_number,
                    'hostname': host['hostname'],
                    'differences': validation_result['differences']
                })
                logger.warning(f"⚠ Config mismatch for {device_number}: {len(validation_result['differences'])} differences")
                
            else:
                devices_validated.append(device_number)
                logger.debug(f"✓ Device validated: {device_number}")
        
        # 判斷狀態
        total_devices = len(devices_validated) + len(devices_mismatched) + len(devices_not_found)
        
        if devices_not_found:
            result['status'] = 'error'
            result['message'] = f'{len(devices_not_found)} 個設備在 MDT Web 中找不到'
            result['value'] = f'{len(devices_validated)}/{total_devices} 通過'
        elif devices_mismatched:
            result['status'] = 'warning'
            result['message'] = f'{len(devices_mismatched)} 個設備配置不一致'
            result['value'] = f'{len(devices_validated)}/{total_devices} 通過'
        else:
            result['status'] = 'success'
            result['message'] = f'所有 {total_devices} 個設備配置一致'
            result['value'] = f'✓ {total_devices}/{total_devices} 通過'
        
        result['details'].update({
            'mdt_web_accessible': True,
            'total_devices': total_devices,
            'validated': len(devices_validated),
            'mismatched': len(devices_mismatched),
            'not_found': len(devices_not_found),
            'devices_not_found': devices_not_found[:5],  # 最多顯示5個
            'devices_mismatched': devices_mismatched[:5]
        })
        
        result['suggestions'] = self._generate_mdt_web_suggestions(
            devices_not_found,
            devices_mismatched
        )
        
        self.validation_results['checks']['mdt_web'] = result
        logger.info(f"✓ MDT Web check complete: {result['status']}")
        
    except Exception as e:
        logger.error(f"❌ MDT Web check exception: {e}", exc_info=True)
        self.validation_results['checks']['mdt_web'] = self._create_error_check('mdt_web', str(e))
```

**輔助方法**：

```python
def _get_dhcp_server_ip(self) -> Optional[str]:
    """
    獲取 DHCP Server IP
    
    優先順序：
    1. 狀態為 'online' 的 DHCP Server
    2. 任意一個 DHCP Server
    
    Returns:
        DHCP Server IP 地址，如果沒有則返回 None
    """
    from api.models import DHCPServer
    
    # 優先取第一個在線的 DHCP Server
    server = DHCPServer.objects.filter(status='online').first()
    if server:
        logger.info(f"Found online DHCP Server: {server.name} ({server.ip_address})")
        return server.ip_address
    
    # 如果沒有在線的，取任意一個
    server = DHCPServer.objects.first()
    if server:
        logger.info(f"Found DHCP Server: {server.name} ({server.ip_address})")
        return server.ip_address
    
    logger.warning("No DHCP Server found in database")
    return None

def _calculate_mdt_web_ip(self, dhcp_server_ip: str) -> str:
    """
    計算 MDT Web IP
    
    規則：前3碼與 DHCP Server 相同，最後一碼固定為 2
    
    Args:
        dhcp_server_ip: DHCP Server IP（如 10.250.10.1）
    
    Returns:
        MDT Web IP（如 10.250.10.2）
    
    範例：
        10.250.10.1 → 10.250.10.2
        192.168.1.1 → 192.168.1.2
    """
    import ipaddress
    
    ip_obj = ipaddress.IPv4Address(dhcp_server_ip)
    octets = str(ip_obj).split('.')
    octets[-1] = '2'  # 最後一碼固定為 2
    
    mdt_web_ip = '.'.join(octets)
    logger.debug(f"Calculated MDT Web IP: {dhcp_server_ip} → {mdt_web_ip}")
    
    return mdt_web_ip

def _get_inventory_hosts_with_device_number(self) -> List[Dict]:
    """
    獲取所有有 device_number 的主機
    
    Returns:
        主機列表，每個主機包含：
        - hostname
        - device_number
        - ansible_host
        - mac_address
        - other_vars
    """
    from api.models import AnsibleHostConfig
    
    hosts = AnsibleHostConfig.objects.filter(
        inventory_id=self.inventory_id
    ).exclude(other_vars__device_number__isnull=True)
    
    result = []
    for host in hosts:
        device_number = host.other_vars.get('device_number')
        if device_number:
            result.append({
                'hostname': host.hostname,
                'device_number': device_number,
                'ansible_host': host.ansible_host,
                'mac_address': host.mac_address,
                'other_vars': host.other_vars
            })
    
    logger.info(f"Found {len(result)} hosts with device_number")
    return result

def _generate_mdt_web_suggestions(
    self,
    not_found: List[Dict],
    mismatched: List[Dict]
) -> List[str]:
    """
    生成 MDT Web 檢查建議
    
    Args:
        not_found: 在 MDT Web 中找不到的設備列表
        mismatched: 配置不一致的設備列表
    
    Returns:
        建議列表
    """
    suggestions = []
    
    if not_found:
        suggestions.append(f'⚠️ {len(not_found)} 個設備在 MDT Web 中找不到')
        suggestions.append('請檢查 device_number 是否正確')
        suggestions.append('確認設備是否已在 MDT Web 中註冊')
        
        # 顯示前3個未找到的設備
        if len(not_found) <= 3:
            for device in not_found:
                suggestions.append(f"  - {device['device_number']} (主機: {device['hostname']})")
    
    if mismatched:
        suggestions.append(f'⚠️ {len(mismatched)} 個設備配置與 MDT Web 不一致')
        suggestions.append('檢查 IP、MAC 地址是否正確')
        suggestions.append('可能需要更新 Inventory 或 MDT Web 中的配置')
        
        # 顯示前3個不一致的設備
        if len(mismatched) <= 3:
            for device in mismatched:
                diff_fields = [d['field'] for d in device['differences']]
                suggestions.append(f"  - {device['device_number']}: {', '.join(diff_fields)} 不一致")
    
    if not suggestions:
        suggestions.append('✅ 所有設備配置與 MDT Web 一致')
    
    return suggestions
```

---

### 步驟 3：更新前端 UI 顯示（選用）

**檔案**：`frontend/src/components/AnsibleInventory/ConfigValidation.jsx`

**修改**：在檢查項目列表中添加 MDT Web 檢查的顯示

```javascript
const checkItemLabels = {
    syntax: '語法驗證',
    structure: '結構完整性',
    host_config: '主機配置檢查',
    ip_addresses: 'IP 地址驗證',
    mac_addresses: 'MAC 地址驗證',
    uart_ssh: 'UART SSH 連線檢查',
    nas_connection: 'NAS 連線檢查',
    mdt_web: 'MDT Web 檢查'  // 新增
};
```

**渲染邏輯**：與其他檢查項目保持一致即可，系統會自動從 API 回應中讀取 `mdt_web` 的檢查結果。

---

### 步驟 4：創建測試腳本

**檔案**：`backend/test_mdt_web_check.py`

```python
"""
測試 Ansible Inventory MDT Web 檢查功能

執行方式：
    python manage.py shell < test_mdt_web_check.py
    
或：
    docker exec nt-django python manage.py shell < test_mdt_web_check.py
"""

import os
import sys
import django

# Django setup
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'network_toolbox.settings')
django.setup()

from library.services.mdt_web_service import MDTWebService
from library.services.inventory_config_validator import InventoryConfigValidator
from api.models import AnsibleInventoryImport


def test_mdt_web_service():
    """測試 MDT Web 服務基本功能"""
    print("\n" + "="*60)
    print("測試 1: MDT Web 服務基本功能")
    print("="*60)
    
    # 使用預期的 MDT Web IP
    mdt_web_ip = "10.250.10.2"
    
    print(f"\n1. 測試 MDT Web 連線: {mdt_web_ip}")
    service = MDTWebService(mdt_web_ip)
    is_accessible, error_msg = service.check_connection()
    
    if is_accessible:
        print(f"   ✓ MDT Web 可訪問")
    else:
        print(f"   ✗ MDT Web 無法訪問: {error_msg}")
        return False
    
    print(f"\n2. 測試設備查詢")
    device_number = "PC-SSD-4052"
    device_data = service.get_device(device_number)
    
    if device_data:
        print(f"   ✓ 找到設備: {device_number}")
        print(f"   - IP: {device_data.get('info', {}).get('ip')}")
        print(f"   - MAC: {device_data.get('info', {}).get('mac')}")
        print(f"   - OS Build: {device_data.get('os_build')}")
        print(f"   - Status: {device_data.get('monitor', {}).get('step_name')}")
    else:
        print(f"   ⚠ 設備未找到: {device_number}")
    
    print(f"\n3. 測試配置驗證")
    expected_config = {
        'hostname': 'Test-Device',
        'ansible_host': '10.250.11.21',
        'mac_address': 'E8:9C:25:94:EF:72'
    }
    
    validation_result = service.validate_device_config(device_number, expected_config)
    
    print(f"   - 設備找到: {validation_result['device_found']}")
    print(f"   - 配置匹配: {validation_result['config_matches']}")
    
    if validation_result['differences']:
        print(f"   - 差異數量: {len(validation_result['differences'])}")
        for diff in validation_result['differences']:
            print(f"     • {diff['field']}: {diff['inventory_value']} ≠ {diff['mdt_web_value']}")
    else:
        print(f"   ✓ 配置完全一致")
    
    return True


def test_inventory_validation():
    """測試完整的 Inventory 驗證流程"""
    print("\n" + "="*60)
    print("測試 2: 完整 Inventory 驗證（含 MDT Web 檢查）")
    print("="*60)
    
    # 獲取第一個 Inventory
    inventory = AnsibleInventoryImport.objects.first()
    
    if not inventory:
        print("   ⚠ 沒有找到 Inventory，跳過測試")
        return False
    
    print(f"\n使用 Inventory: {inventory.id} ({inventory.nas_path})")
    
    # 執行驗證
    print(f"\n執行完整驗證...")
    validator = InventoryConfigValidator(
        inventory_id=inventory.id,
        check_connectivity=False,
        check_dhcp=False
    )
    
    result = validator.validate()
    
    # 顯示結果
    print(f"\n總體狀態: {result['overall_status'].upper()}")
    print(f"總檢查項: {result['summary']['total_checks']}")
    print(f"通過: {result['summary']['passed']}")
    print(f"警告: {result['summary']['warnings']}")
    print(f"錯誤: {result['summary']['errors']}")
    
    # 重點顯示 MDT Web 檢查結果
    if 'mdt_web' in result['checks']:
        print("\n" + "-"*60)
        print("MDT Web 檢查詳細結果")
        print("-"*60)
        
        mdt_check = result['checks']['mdt_web']
        
        print(f"\n狀態: {mdt_check['status'].upper()}")
        print(f"訊息: {mdt_check['message']}")
        print(f"檢查值: {mdt_check['value']}")
        
        if 'details' in mdt_check:
            details = mdt_check['details']
            print(f"\n詳細資訊:")
            print(f"  - DHCP Server IP: {details.get('dhcp_server_ip', 'N/A')}")
            print(f"  - 預期 MDT Web IP: {details.get('expected_mdt_web_ip', 'N/A')}")
            print(f"  - MDT Web 可訪問: {details.get('mdt_web_accessible', 'N/A')}")
            print(f"  - 總設備數: {details.get('total_devices', 0)}")
            print(f"  - 驗證通過: {details.get('validated', 0)}")
            print(f"  - 配置不一致: {details.get('mismatched', 0)}")
            print(f"  - 設備未找到: {details.get('not_found', 0)}")
            
            # 顯示未找到的設備
            if details.get('devices_not_found'):
                print(f"\n未找到的設備:")
                for device in details['devices_not_found']:
                    print(f"  • {device['device_number']} (主機: {device['hostname']})")
            
            # 顯示配置不一致的設備
            if details.get('devices_mismatched'):
                print(f"\n配置不一致的設備:")
                for device in details['devices_mismatched']:
                    print(f"  • {device['device_number']} (主機: {device['hostname']})")
                    for diff in device['differences']:
                        print(f"    - {diff['field']}: {diff['inventory_value']} ≠ {diff['mdt_web_value']}")
        
        if 'suggestions' in mdt_check and mdt_check['suggestions']:
            print(f"\n建議:")
            for suggestion in mdt_check['suggestions']:
                print(f"  {suggestion}")
    else:
        print("\n⚠ 找不到 MDT Web 檢查結果")
    
    return True


if __name__ == '__main__':
    print("\n" + "="*60)
    print("Ansible Inventory MDT Web 檢查功能測試")
    print("="*60)
    
    try:
        # 測試 1: MDT Web 服務
        if test_mdt_web_service():
            print("\n✓ 測試 1 完成")
        else:
            print("\n✗ 測試 1 失敗")
        
        # 測試 2: 完整驗證流程
        if test_inventory_validation():
            print("\n✓ 測試 2 完成")
        else:
            print("\n✗ 測試 2 失敗")
        
        print("\n" + "="*60)
        print("測試完成")
        print("="*60 + "\n")
        
    except Exception as e:
        print(f"\n✗ 測試失敗: {e}")
        import traceback
        traceback.print_exc()
```

---

## 📊 預期結果

### 成功案例

```
MDT Web 檢查

狀態：✓ 成功
訊息：所有 119 個設備配置一致
檢查值：✓ 119/119 通過

詳細資訊：
- DHCP Server IP: 10.250.10.1
- 預期 MDT Web IP: 10.250.10.2
- MDT Web 狀態: 可訪問
- 總設備數: 119
- 驗證通過: 119
- 配置不一致: 0
- 設備未找到: 0

建議：
✅ 所有設備配置與 MDT Web 一致
```

### 警告案例（配置不一致）

```
MDT Web 檢查

狀態：⚠️ 警告
訊息：3 個設備配置不一致
檢查值：116/119 通過

詳細資訊：
- DHCP Server IP: 10.250.10.1
- 預期 MDT Web IP: 10.250.10.2
- MDT Web 狀態: 可訪問
- 總設備數: 119
- 驗證通過: 116
- 配置不一致: 3
- 設備未找到: 0

配置不一致的設備：
1. PC-SSD-4052 (主機: Test-KVM01)
   - IP Address: 10.250.11.21 ≠ 10.250.11.22
   
2. PC-SSD-4053 (主機: Test-KVM02)
   - MAC Address: e8:9c:25:94:ef:72 ≠ e8:9c:25:94:ef:73

建議：
⚠️ 3 個設備配置與 MDT Web 不一致
- 檢查 IP、MAC 地址是否正確
- 可能需要更新 Inventory 或 MDT Web 中的配置
```

### 錯誤案例（MDT Web 無法訪問）

```
MDT Web 檢查

狀態：✗ 錯誤
訊息：MDT Web (10.250.10.2) 無法訪問
檢查值：✗ 無法連線

詳細資訊：
- DHCP Server IP: 10.250.10.1
- 預期 MDT Web IP: 10.250.10.2
- 連線錯誤: 連線超時（10秒）

建議：
- 檢查 MDT Web 是否運行在 10.250.10.2
- 檢查網路連線和防火牆設置
- 錯誤：連線超時（10秒）
```

---

## 📝 實施檢查清單

### 階段 1：核心功能實現

- [ ] 創建 `mdt_web_service.py` 服務模組
  - [ ] 實現 `MDTWebService` 類別
  - [ ] 實現 `check_connection()` 方法
  - [ ] 實現 `get_device()` 方法
  - [ ] 實現 `validate_device_config()` 方法
  - [ ] 添加完整的錯誤處理和日誌

- [ ] 在 `inventory_config_validator.py` 添加 MDT Web 檢查
  - [ ] 在 `validate()` 方法中調用 `_check_mdt_web()`
  - [ ] 實現 `_check_mdt_web()` 主要檢查邏輯
  - [ ] 實現 `_get_dhcp_server_ip()` 輔助方法
  - [ ] 實現 `_calculate_mdt_web_ip()` 輔助方法
  - [ ] 實現 `_get_inventory_hosts_with_device_number()` 輔助方法
  - [ ] 實現 `_generate_mdt_web_suggestions()` 輔助方法

### 階段 2：測試與驗證

- [ ] 創建測試腳本 `test_mdt_web_check.py`
  - [ ] 測試 MDT Web 連線
  - [ ] 測試設備查詢
  - [ ] 測試配置驗證
  - [ ] 測試完整驗證流程

- [ ] 手動測試
  - [ ] 測試 DHCP Server IP 檢測
  - [ ] 測試 MDT Web IP 計算
  - [ ] 測試 MDT Web 可訪問性
  - [ ] 測試設備資訊一致性驗證

### 階段 3：前端整合（選用）

- [ ] 更新前端顯示邏輯
  - [ ] 在檢查項目列表添加 MDT Web 檢查
  - [ ] 確認檢查結果正確渲染
  - [ ] 測試展開/收起功能

### 階段 4：文檔與優化

- [ ] 更新 API 文檔
- [ ] 添加使用說明
- [ ] 性能優化（如需要）
- [ ] 錯誤處理增強

---

## ⚙️ 配置要求

### MDT Web API 端點確認結果

**✅ 已確認資訊**（2025-11-24 測試結果）：

1. **MDT Web 基本資訊**
   - **URL**: `http://10.250.10.2`
   - **狀態**: ✅ 可訪問（HTTP 200）
   - **技術棧**: jQuery + Bootstrap（傳統 Web 應用）
   - **頁面標題**: "MDT Manager"
   - **認證方式**: 待確認（目前首頁可直接訪問）

2. **✅ API 端點測試結果**（已確認可用）

   **正確的 API 端點**：
   ```
   GET http://10.250.10.2/api/devices?search={device_number}
   ```

   **範例請求**：
   ```bash
   curl "http://10.250.10.2/api/devices?search=PC-SSD-4052"
   ```

   **回應格式**：JSON 陣列，包含符合搜尋條件的所有設備
   ```json
   [
       {
           "name": "PC-SSD-4052",
           "uuid": "49dd0707-02b6-abcb-7996-e89c2594ef72",
           "os_build": "AUTOMP",
           "comment": "測試設備",
           "info": {
               "vendor": "ASUS",
               "model": "System Product Name",
               "product": "ROG STRIX Z790-E GAMING WIFI II",
               "ip": "10.250.11.21",
               "mac": "E8:9C:25:94:EF:72",
               "gateway": "10.250.11.254"
           },
           "monitor": {
               "deployment_status": 1,
               "step_name": "Gather local only",
               "last_time": "2025-11-21T12:03:42+00:00"
           }
       }
   ]
   ```

   **重要欄位說明**：
   - `name`: 設備編號（對應 Inventory 的 `device_number`）
   - `info.ip`: IP 地址（對應 Inventory 的 `ansible_host`）
   - `info.mac`: MAC 地址（對應 Inventory 的 `mac_address`）
   - `info.vendor`: 製造商
   - `info.product`: 產品型號
   - `monitor.deployment_status`: 部署狀態
   - `monitor.step_name`: 當前執行步驟

3. **實施方案**（✅ 已確定）

   **方案：使用 MDT Web REST API**
   
   由於已確認 MDT Web 提供 REST API，我們將直接使用 API 方式實現：

   ```python
   def get_device_from_mdt_web(device_number: str) -> Optional[Dict]:
       """
       通過 MDT Web API 獲取設備資訊
       
       Args:
           device_number: 設備編號（如 PC-SSD-4052）
       
       Returns:
           設備資訊字典，如果未找到則返回 None
       """
       url = "http://10.250.10.2/api/devices"
       params = {"search": device_number}
       
       try:
           response = requests.get(url, params=params, timeout=10)
           response.raise_for_status()
           
           devices = response.json()
           
           # API 返回陣列，精確匹配設備名稱
           for device in devices:
               if device.get('name') == device_number:
                   return device
           
           return None
           
       except Exception as e:
           logger.error(f"Failed to get device {device_number}: {e}")
           return None
   ```

   **優點**：
   - ✅ 使用標準 REST API，穩定可靠
   - ✅ JSON 格式回應，易於解析
   - ✅ 支援搜尋功能，查詢效率高
   - ✅ 無需解析 HTML，維護成本低

4. **網路要求**
   - ✅ Django 容器可以訪問 MDT Web IP（已驗證）
   - ✅ HTTP 連線正常（無需防火牆調整）

5. **預期回應資料結構**（✅ 已確認）
   ```json
   {
       "name": "PC-SSD-4052",
       "uuid": "49dd0707-02b6-abcb-7996-e89c2594ef72",
       "os_build": "AUTOMP",
       "driver_path": "",
       "script_path": "",
       "log_path": "",
       "automp_type": "NONE",
       "automp_path": "",
       "comment": "測試設備註解",
       "info": {
           "vendor": "ASUS",
           "model": "System Product Name",
           "product": "ROG STRIX Z790-E GAMING WIFI II",
           "wds_server": "",
           "ip": "10.250.11.21",
           "mac": "E8:9C:25:94:EF:72",
           "gateway": "10.250.11.254"
       },
       "monitor": {
           "percent_complete": 0,
           "deployment_status": 1,
           "start_time": "2025-11-21T12:03:42+00:00",
           "end_time": null,
           "device_id": null,
           "step_name": "Gather local only",
           "last_time": "2025-11-21T12:03:42+00:00",
           "dart_ip": "",
           "dart_port": "",
           "dart_ticket": ""
       }
   }
   ```

---

## 🔍 故障排查

### 問題 1：MDT Web 無法訪問

**症狀**：檢查結果顯示「MDT Web 無法訪問」

**排查步驟**：
```bash
# 1. 從 Django 容器測試連線
docker exec nt-django curl -I http://10.250.10.2

# 2. 檢查 DHCP Server IP 是否正確
docker exec nt-django python manage.py shell -c "
from api.models import DHCPServer
servers = DHCPServer.objects.all()
for s in servers:
    print(f'{s.name}: {s.ip_address} ({s.status})')
"

# 3. 檢查防火牆設置
# （在主機上執行）
sudo iptables -L -n | grep 10.250.10.2
```

### 問題 2：設備找不到

**症狀**：所有設備都顯示「在 MDT Web 中找不到」

**排查步驟**：
1. 確認 MDT Web API 端點格式正確
2. 檢查 `device_number` 格式是否與 MDT Web 一致
3. 手動測試 API：
   ```bash
   curl http://10.250.10.2/api/devices/PC-SSD-4052
   ```

### 問題 3：配置不一致

**症狀**：大量設備顯示配置不一致

**排查步驟**：
1. 檢查 MAC 地址格式（`:`  vs `-`）
2. 檢查 IP 地址是否已更新
3. 查看具體差異欄位：
   ```bash
   docker exec nt-django python manage.py shell -c "
   from library.services.inventory_config_validator import InventoryConfigValidator
   validator = InventoryConfigValidator(inventory_id=1)
   result = validator.validate()
   mdt_check = result['checks']['mdt_web']
   for device in mdt_check['details']['devices_mismatched'][:3]:
       print(f\"{device['device_number']}: {device['differences']}\")
   "
   ```

---

## 📞 聯絡資訊

**負責人**：開發團隊  
**規劃日期**：2025-11-24  
**文檔版本**：v1.0  
**狀態**：📋 規劃完成，待實施

---

## 附錄：相關文檔

| 文檔 | 路徑 |
|------|------|
| 配置驗證器 | `library/services/inventory_config_validator.py` |
| Ansible Inventory 服務 | `library/services/ansible_inventory_service.py` |
| API Views | `backend/api/views/ansible_inventory.py` |
| DHCP Server 模型 | `backend/api/models.py` (DHCPServer) |
| Jenkins 即時監控實施報告 | `docs/features/jenkins/REAL_TIME_MONITORING_IMPLEMENTATION.md` (參考範例) |

---

**最後更新**：2025-11-24  
**下一步**：確認 MDT Web API 端點格式後開始實施
