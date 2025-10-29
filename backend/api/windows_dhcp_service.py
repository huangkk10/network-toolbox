"""
Windows DHCP Server 租約同步服務
支援從 Windows DHCP Server 透過 PowerShell 遠程獲取租約資訊
"""
import json
import logging
from datetime import datetime
from django.utils import timezone
from library.utils.mac_utils import parse_windows_client_id
from library.utils.datetime_utils import parse_windows_lease_expiry
from .models import DHCPLease, DHCPServer

logger = logging.getLogger(__name__)


class WindowsDHCPService:
    """Windows DHCP Server 租約同步服務"""
    
    def __init__(self, dhcp_server):
        """
        初始化服務
        
        Args:
            dhcp_server: DHCPServer 模型實例
        """
        self.dhcp_server = dhcp_server
        self.server_ip = dhcp_server.ip_address
    
    def get_powershell_command(self, scope_id=None):
        """
        生成 PowerShell 命令獲取 DHCP 租約
        
        Args:
            scope_id: Scope ID (例如: 10.250.53.0)，如果為 None 則獲取所有 Scope
        
        Returns:
            PowerShell 命令字串
        """
        if scope_id:
            # 獲取單一 Scope 的租約
            cmd = f"""
Get-DhcpServerv4Lease -ComputerName {self.server_ip} -ScopeId {scope_id} | 
Select-Object IPAddress, ClientId, HostName, AddressState, LeaseExpiryTime, ScopeId | 
ConvertTo-Json -Compress
"""
        else:
            # 獲取所有 Scope 的租約
            cmd = f"""
Get-DhcpServerv4Scope -ComputerName {self.server_ip} | 
ForEach-Object {{
    Get-DhcpServerv4Lease -ComputerName {self.server_ip} -ScopeId $_.ScopeId
}} | 
Select-Object IPAddress, ClientId, HostName, AddressState, LeaseExpiryTime, ScopeId | 
ConvertTo-Json -Compress
"""
        
        return cmd.strip()
    
    def get_all_scopes(self):
        """
        獲取所有 Scope 資訊
        
        Returns:
            PowerShell 命令字串
        """
        cmd = f"""
Get-DhcpServerv4Scope -ComputerName {self.server_ip} | 
Select-Object ScopeId, Name, SubnetMask, StartRange, EndRange, State, LeaseDuration | 
ConvertTo-Json -Compress
"""
        return cmd.strip()
    
    def parse_lease_data(self, json_data):
        """
        解析從 PowerShell 獲取的 JSON 格式租約資料
        
        Args:
            json_data: JSON 格式的租約資料
        
        Returns:
            解析後的租約列表
        """
        try:
            data = json.loads(json_data)
            
            # 如果只有一筆資料，PowerShell 返回字典而非列表
            if isinstance(data, dict):
                data = [data]
            
            leases = []
            for item in data:
                # 解析租約資料
                lease_info = {
                    'ip_address': item.get('IPAddress', {}).get('IPAddressToString', ''),
                    'mac_address': self._parse_client_id(item.get('ClientId', '')),
                    'hostname': item.get('HostName', '') or None,
                    'scope_id': item.get('ScopeId', {}).get('IPAddressToString', ''),
                    'state': item.get('AddressState', ''),
                    'lease_expiry': item.get('LeaseExpiryTime', ''),
                }
                
                # 只添加有效的租約
                if lease_info['ip_address'] and lease_info['mac_address']:
                    leases.append(lease_info)
            
            logger.info(f'成功解析 {len(leases)} 筆租約資料')
            return leases
        
        except json.JSONDecodeError as e:
            logger.error(f'JSON 解析失敗: {str(e)}', exc_info=True)
            return []
        except Exception as e:
            logger.error(f'租約資料解析失敗: {str(e)}', exc_info=True)
            return []
    
    def _parse_client_id(self, client_id):
        """
        解析 ClientId 為標準 MAC 地址格式
        
        [已棄用] 使用 library.utils.mac_utils.parse_windows_client_id() 代替
        保留此方法以保持向後兼容性
        
        Args:
            client_id: Windows DHCP ClientId
        
        Returns:
            標準 MAC 地址格式 (aa:bb:cc:dd:ee:ff)
        """
        return parse_windows_client_id(client_id)
    
    def _parse_lease_expiry(self, expiry_str):
        """
        解析租約到期時間
        
        [已棄用] 使用 library.utils.datetime_utils.parse_windows_lease_expiry() 代替
        保留此方法以保持向後兼容性
        
        Args:
            expiry_str: 時間字串
        
        Returns:
            datetime 對象
        """
        return parse_windows_lease_expiry(expiry_str)
    
    def sync_leases_to_db(self, lease_data_list):
        """
        將租約資料同步到資料庫
        
        Args:
            lease_data_list: 租約資料列表
        
        Returns:
            同步統計資訊
        """
        stats = {
            'total': len(lease_data_list),
            'created': 0,
            'updated': 0,
            'skipped': 0,
            'errors': 0,
        }
        
        for lease_data in lease_data_list:
            try:
                ip_address = lease_data['ip_address']
                mac_address = lease_data['mac_address']
                
                if not ip_address or not mac_address:
                    stats['skipped'] += 1
                    continue
                
                # 解析租約到期時間
                lease_end = self._parse_lease_expiry(lease_data.get('lease_expiry'))
                lease_start = timezone.now()
                
                # 判斷是否活躍
                is_active = (
                    lease_data.get('state', '').lower() == 'active' and
                    lease_end > timezone.now()
                )
                
                # 查找或創建租約
                lease, created = DHCPLease.objects.update_or_create(
                    server=self.dhcp_server,
                    mac_address=mac_address,
                    defaults={
                        'ip_address': ip_address,
                        'hostname': lease_data.get('hostname') or '',
                        'lease_start': lease_start,
                        'lease_end': lease_end,
                        'is_active': is_active,
                    }
                )
                
                if created:
                    stats['created'] += 1
                    logger.info(f'新增租約: {ip_address} ({mac_address})')
                else:
                    stats['updated'] += 1
                    logger.info(f'更新租約: {ip_address} ({mac_address})')
            
            except Exception as e:
                stats['errors'] += 1
                logger.error(f'同步租約失敗: {str(e)}', exc_info=True)
        
        # 更新 Server 統計資訊
        self.dhcp_server.total_leases = DHCPLease.objects.filter(server=self.dhcp_server).count()
        self.dhcp_server.active_leases = DHCPLease.objects.filter(
            server=self.dhcp_server,
            is_active=True
        ).count()
        self.dhcp_server.last_sync_at = timezone.now()
        self.dhcp_server.save()
        
        logger.info(f'租約同步完成: {stats}')
        return stats


def generate_powershell_export_script(server_ip, output_file='dhcp_leases.json'):
    """
    生成完整的 PowerShell 腳本用於導出 DHCP 租約
    
    這個腳本可以在 Windows DHCP Server 上直接執行
    
    Args:
        server_ip: DHCP Server IP 地址
        output_file: 輸出文件路徑
    
    Returns:
        PowerShell 腳本內容
    """
    script = f'''# Windows DHCP Server 租約導出腳本
# 生成時間: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
# 目標伺服器: {server_ip}

Write-Host "開始導出 DHCP 租約..." -ForegroundColor Green

try {{
    # 獲取所有 Scope
    $scopes = Get-DhcpServerv4Scope -ComputerName {server_ip}
    Write-Host "找到 $($scopes.Count) 個 Scope" -ForegroundColor Cyan
    
    # 獲取所有租約
    $allLeases = @()
    foreach ($scope in $scopes) {{
        Write-Host "  處理 Scope: $($scope.ScopeId) - $($scope.Name)" -ForegroundColor Yellow
        $leases = Get-DhcpServerv4Lease -ComputerName {server_ip} -ScopeId $scope.ScopeId
        $allLeases += $leases
    }}
    
    Write-Host "共找到 $($allLeases.Count) 筆租約" -ForegroundColor Cyan
    
    # 轉換為 JSON 並導出
    $exportData = $allLeases | Select-Object `
        @{{Name='IPAddress'; Expression={{$_.IPAddress.ToString()}}}}, `
        @{{Name='ClientId'; Expression={{$_.ClientId}}}}, `
        @{{Name='HostName'; Expression={{$_.HostName}}}}, `
        @{{Name='AddressState'; Expression={{$_.AddressState.ToString()}}}}, `
        @{{Name='LeaseExpiryTime'; Expression={{$_.LeaseExpiryTime.ToString("yyyy-MM-dd HH:mm:ss")}}}}, `
        @{{Name='ScopeId'; Expression={{$_.ScopeId.ToString()}}}}
    
    $exportData | ConvertTo-Json | Out-File -FilePath "{output_file}" -Encoding UTF8
    
    Write-Host "成功導出到: {output_file}" -ForegroundColor Green
    
}} catch {{
    Write-Host "錯誤: $_" -ForegroundColor Red
    exit 1
}}
'''
    return script
