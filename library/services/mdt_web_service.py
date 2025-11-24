"""cat: /home/owner/Codes/network-toolbox/backend/library/services/mdt_web_service.py: No such file or directory

MDT Web API 服務模組

提供與 MDT Web 系統交互的功能，包括：
- 連接檢查
- 設備資訊查詢
- 配置一致性驗證

MDT Web API 端點：
- Base URL: http://{mdt_web_ip}
- 設備查詢: GET /api/devices?search={device_number}
- 回應格式: JSON 陣列

作者：開發團隊
創建日期：2025-11-24
"""

import requests
import logging
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class MDTWebService:
    """
    MDT Web API 服務
    
    負責與 MDT Web 系統交互，查詢設備資訊並驗證配置
    """
    
    def __init__(self, mdt_web_ip: str, timeout: int = 10):
        """初始化 MDT Web 服務"""
        self.base_url = f"http://{mdt_web_ip}"
        self.mdt_web_ip = mdt_web_ip
        self.timeout = timeout
        self.session = requests.Session()
        logger.debug(f"Initialized MDTWebService: {self.base_url}")
    
    def check_connection(self) -> Tuple[bool, Optional[str]]:
        """檢查 MDT Web 是否可訪問"""
        try:
            response = self.session.get(
                f"{self.base_url}/",
                timeout=self.timeout,
                verify=False
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
        """根據 device_number 查詢設備資訊"""
        try:
            url = f"{self.base_url}/api/devices"
            params = {'search': device_number}
            
            logger.debug(f"Querying MDT Web: {url}?search={device_number}")
            
            response = self.session.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            
            data = response.json()
            
            # API 回應格式：{'rows': [...], 'total': 123}
            if isinstance(data, dict) and 'rows' in data:
                devices = data['rows']
            elif isinstance(data, list):
                devices = data
            else:
                logger.error(f"Unexpected response format: {type(data)}")
                return None
            
            # 精確匹配設備名稱
            for device in devices:
                if device.get('name') == device_number:
                    logger.info(f"✓ Found device in MDT Web: {device_number}")
                    return device
            
            logger.warning(f"⚠ Device not found in MDT Web: {device_number}")
            return None
                
        except Exception as e:
            logger.error(f"✗ Failed to get device {device_number}: {e}", exc_info=True)
            return None
    
    def validate_device_config(self, device_number: str, expected_config: Dict) -> Dict:
        """驗證設備配置是否與 MDT Web 一致"""
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
        inventory_mac = self._normalize_mac_address(expected_config.get('mac_address', ''))
        mdt_mac = self._normalize_mac_address(mdt_device.get('info', {}).get('mac', ''))
        
        if inventory_mac and mdt_mac and inventory_mac != mdt_mac:
            differences.append({
                'field': 'mac_address',
                'inventory_value': expected_config.get('mac_address', ''),
                'mdt_web_value': mdt_device.get('info', {}).get('mac', '')
            })
        
        # 注意：不比對 hostname，因為 Inventory 的 hostname 是自訂名稱（如 SAF7006_K01）
        # 而 MDT Web 的 name 就是 device_number（如 PC-SSD-2778）
        # 我們已經用 device_number 查詢到正確的設備，所以不需要再比對名稱
        
        result['differences'] = differences
        result['config_matches'] = len(differences) == 0
        
        if result['config_matches']:
            logger.info(f"✓ Device config matches: {device_number}")
        else:
            logger.warning(f"⚠ Device config mismatch: {device_number} ({len(differences)} differences)")
        
        return result
    
    def _normalize_mac_address(self, mac: str) -> str:
        """標準化 MAC 地址格式"""
        if not mac:
            return ''
        
        mac_clean = mac.lower().replace('-', '').replace(':', '').replace('.', '')
        
        if len(mac_clean) == 12:
            return ':'.join([mac_clean[i:i+2] for i in range(0, 12, 2)])
        
        return mac.lower()


def create_mdt_web_service(dhcp_server_ip: str, timeout: int = 10) -> MDTWebService:
    """根據 DHCP Server IP 創建 MDT Web 服務實例"""
    import ipaddress
    
    ip_obj = ipaddress.IPv4Address(dhcp_server_ip)
    octets = str(ip_obj).split('.')
    octets[-1] = '2'
    
    mdt_web_ip = '.'.join(octets)
    logger.info(f"Creating MDT Web service: DHCP {dhcp_server_ip} → MDT Web {mdt_web_ip}")
    
    return MDTWebService(mdt_web_ip, timeout)
