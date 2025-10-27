"""
使用 WinRM (Windows Remote Management) 連接 Windows DHCP Server
適用於 Windows Server 內建的遠程管理功能
"""
import json
import logging
from datetime import datetime, timedelta
from django.utils import timezone

logger = logging.getLogger(__name__)

# 注意：需要安裝 pywinrm
# pip install pywinrm

try:
    import winrm
    WINRM_AVAILABLE = True
except ImportError:
    WINRM_AVAILABLE = False
    logger.warning('pywinrm 未安裝，WinRM 功能不可用。請執行: pip install pywinrm')


class WindowsWinRMService:
    """Windows WinRM 服務"""
    
    def __init__(self, dhcp_server):
        """
        初始化服務
        
        Args:
            dhcp_server: DHCPServer 模型實例
        """
        if not WINRM_AVAILABLE:
            raise ImportError('pywinrm 未安裝，請執行: pip install pywinrm')
        
        self.dhcp_server = dhcp_server
        self.host = dhcp_server.ip_address
        self.username = dhcp_server.ssh_username  # 重用 SSH 使用者名稱欄位
        self.password = dhcp_server.ssh_password  # 重用 SSH 密碼欄位
        self.session = None
    
    def connect(self):
        """建立 WinRM 連接"""
        try:
            # WinRM 預設端口：HTTP 5985, HTTPS 5986
            endpoint = f'http://{self.host}:5985/wsman'
            
            self.session = winrm.Session(
                endpoint,
                auth=(self.username, self.password),
                transport='ntlm'  # 使用 NTLM 認證
            )
            
            # 測試連接
            result = self.session.run_ps('Get-Date')
            if result.status_code == 0:
                logger.info(f'成功連接到 Windows Server: {self.host}')
                return True
            else:
                logger.error(f'WinRM 連接測試失敗: {result.std_err}')
                return False
        
        except Exception as e:
            logger.error(f'WinRM 連接失敗 ({self.host}): {str(e)}', exc_info=True)
            return False
    
    def execute_powershell(self, command):
        """
        執行 PowerShell 命令
        
        Args:
            command: PowerShell 命令
        
        Returns:
            (output, error) 元組
        """
        try:
            if not self.session:
                if not self.connect():
                    return None, 'WinRM 連接失敗'
            
            logger.info(f'執行 PowerShell: {command[:100]}...')
            
            result = self.session.run_ps(command)
            
            output = result.std_out.decode('utf-8', errors='ignore')
            error = result.std_err.decode('utf-8', errors='ignore')
            
            if result.status_code != 0:
                logger.warning(f'PowerShell 執行返回錯誤碼: {result.status_code}')
            
            return output, error
        
        except Exception as e:
            error_msg = f'執行 PowerShell 失敗: {str(e)}'
            logger.error(error_msg, exc_info=True)
            return None, error_msg
    
    def get_dhcp_leases(self, scope_id=None):
        """獲取 DHCP 租約（與 SSH 版本相同）"""
        try:
            if scope_id:
                ps_command = f"""
Get-DhcpServerv4Lease -ComputerName localhost -ScopeId {scope_id} | 
Select-Object @{{Name='IPAddress'; Expression={{$_.IPAddress.ToString()}}}}, 
              @{{Name='ClientId'; Expression={{$_.ClientId}}}}, 
              @{{Name='HostName'; Expression={{$_.HostName}}}}, 
              @{{Name='AddressState'; Expression={{$_.AddressState.ToString()}}}}, 
              @{{Name='LeaseExpiryTime'; Expression={{$_.LeaseExpiryTime.ToString('yyyy-MM-dd HH:mm:ss')}}}}, 
              @{{Name='ScopeId'; Expression={{$_.ScopeId.ToString()}}}} | 
ConvertTo-Json -Compress
"""
            else:
                ps_command = """
Get-DhcpServerv4Scope -ComputerName localhost | ForEach-Object {
    Get-DhcpServerv4Lease -ComputerName localhost -ScopeId $_.ScopeId
} | Select-Object @{Name='IPAddress'; Expression={$_.IPAddress.ToString()}}, 
                  @{Name='ClientId'; Expression={$_.ClientId}}, 
                  @{Name='HostName'; Expression={$_.HostName}}, 
                  @{Name='AddressState'; Expression={$_.AddressState.ToString()}}, 
                  @{Name='LeaseExpiryTime'; Expression={$_.LeaseExpiryTime.ToString('yyyy-MM-dd HH:mm:ss')}}, 
                  @{Name='ScopeId'; Expression={$_.ScopeId.ToString()}} | 
ConvertTo-Json -Compress
"""
            
            output, error = self.execute_powershell(ps_command.strip())
            
            if not output:
                logger.error(f'未獲取到租約資料，錯誤: {error}')
                return []
            
            try:
                data = json.loads(output)
                if isinstance(data, dict):
                    data = [data]
                
                logger.info(f'成功獲取 {len(data)} 筆租約資料')
                return data
            
            except json.JSONDecodeError as e:
                logger.error(f'JSON 解析失敗: {str(e)}', exc_info=True)
                return []
        
        except Exception as e:
            logger.error(f'獲取 DHCP 租約失敗: {str(e)}', exc_info=True)
            return []
    
    def parse_client_id(self, client_id):
        """解析 ClientId（與 SSH 版本相同）"""
        if not client_id:
            return None
        
        try:
            parts = client_id.split('-')
            if len(parts) > 1:
                mac_parts = parts[1:7] if len(parts) >= 7 else parts[1:]
            else:
                mac_parts = parts
            
            mac_address = ':'.join(mac_parts).lower()
            
            if len(mac_address.split(':')) == 6:
                return mac_address
            else:
                logger.warning(f'無效的 MAC 地址格式: {client_id}')
                return None
        
        except Exception as e:
            logger.error(f'MAC 地址解析失敗 ({client_id}): {str(e)}')
            return None
    
    def parse_lease_expiry(self, expiry_str):
        """解析租約到期時間"""
        if not expiry_str:
            return timezone.now() + timedelta(hours=24)
        
        try:
            dt = datetime.strptime(expiry_str, '%Y-%m-%d %H:%M:%S')
            return timezone.make_aware(dt)
        
        except Exception as e:
            logger.error(f'租約到期時間解析失敗: {str(e)}')
            return timezone.now() + timedelta(hours=24)
    
    def sync_leases_to_db(self):
        """同步租約到資料庫（與 SSH 版本相同）"""
        from .models import DHCPLease
        
        stats = {
            'total': 0,
            'created': 0,
            'updated': 0,
            'skipped': 0,
            'errors': 0,
        }
        
        try:
            lease_data_list = self.get_dhcp_leases()
            stats['total'] = len(lease_data_list)
            
            if not lease_data_list:
                logger.warning('未獲取到任何租約資料')
                return stats
            
            for lease_data in lease_data_list:
                try:
                    client_id = lease_data.get('ClientId', '')
                    mac_address = self.parse_client_id(client_id)
                    
                    if not mac_address:
                        logger.warning(f'跳過無效的 MAC 地址: {client_id}')
                        stats['skipped'] += 1
                        continue
                    
                    ip_address = lease_data.get('IPAddress', '')
                    hostname = lease_data.get('HostName', '') or ''
                    state = lease_data.get('AddressState', '').lower()
                    
                    lease_expiry_str = lease_data.get('LeaseExpiryTime', '')
                    lease_end = self.parse_lease_expiry(lease_expiry_str)
                    lease_start = timezone.now()
                    
                    is_active = (state == 'active' and lease_end > timezone.now())
                    
                    lease, created = DHCPLease.objects.update_or_create(
                        server=self.dhcp_server,
                        mac_address=mac_address,
                        defaults={
                            'ip_address': ip_address,
                            'hostname': hostname,
                            'lease_start': lease_start,
                            'lease_end': lease_end,
                            'is_active': is_active,
                        }
                    )
                    
                    if created:
                        stats['created'] += 1
                        logger.debug(f'新增租約: {ip_address} ({mac_address}) - {hostname}')
                    else:
                        stats['updated'] += 1
                        logger.debug(f'更新租約: {ip_address} ({mac_address}) - {hostname}')
                
                except Exception as e:
                    stats['errors'] += 1
                    logger.error(f'處理租約失敗: {str(e)}', exc_info=True)
            
            # 更新 Server 統計
            self.dhcp_server.total_leases = DHCPLease.objects.filter(
                server=self.dhcp_server
            ).count()
            self.dhcp_server.active_leases = DHCPLease.objects.filter(
                server=self.dhcp_server,
                is_active=True
            ).count()
            self.dhcp_server.last_sync_at = timezone.now()
            self.dhcp_server.save()
            
            logger.info(f'租約同步完成: {stats}')
            return stats
        
        except Exception as e:
            logger.error(f'同步租約失敗: {str(e)}', exc_info=True)
            stats['errors'] = stats['total']
            return stats
