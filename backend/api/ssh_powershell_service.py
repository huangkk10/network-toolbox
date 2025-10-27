"""
透過 SSH 連接 Windows DHCP Server 並執行 PowerShell 命令
適用於已安裝 OpenSSH Server 的 Windows Server
"""
import paramiko
import json
import logging
from django.utils import timezone
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class WindowsSSHPowerShellService:
    """Windows SSH + PowerShell 服務"""
    
    def __init__(self, dhcp_server):
        """
        初始化服務
        
        Args:
            dhcp_server: DHCPServer 模型實例
        """
        self.dhcp_server = dhcp_server
        self.host = dhcp_server.ip_address
        self.port = dhcp_server.ssh_port
        self.username = dhcp_server.ssh_username
        self.password = dhcp_server.ssh_password
        self.key_file = dhcp_server.ssh_key_file
        self.client = None
    
    def connect(self):
        """建立 SSH 連接到 Windows Server"""
        try:
            self.client = paramiko.SSHClient()
            self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            if self.key_file:
                # 使用 SSH 金鑰認證
                self.client.connect(
                    self.host,
                    port=self.port,
                    username=self.username,
                    key_filename=self.key_file,
                    timeout=10
                )
            else:
                # 使用密碼認證
                self.client.connect(
                    self.host,
                    port=self.port,
                    username=self.username,
                    password=self.password,
                    timeout=10
                )
            
            logger.info(f'成功連接到 Windows DHCP Server: {self.host}')
            return True
        
        except Exception as e:
            logger.error(f'SSH 連接失敗 ({self.host}): {str(e)}', exc_info=True)
            return False
    
    def execute_powershell(self, command):
        """
        透過 SSH 執行 PowerShell 命令
        
        Args:
            command: PowerShell 命令字串
        
        Returns:
            (output, error) 元組
        """
        try:
            if not self.client:
                if not self.connect():
                    return None, 'SSH 連接失敗'
            
            # 在 Windows SSH 中執行 PowerShell
            # 使用 powershell.exe -Command 來執行命令
            full_command = f'powershell.exe -Command "{command}"'
            
            logger.info(f'執行 PowerShell 命令: {command[:100]}...')
            
            stdin, stdout, stderr = self.client.exec_command(full_command, timeout=60)
            
            output = stdout.read().decode('utf-8', errors='ignore')
            error = stderr.read().decode('utf-8', errors='ignore')
            
            if error and 'WARNING' not in error:
                logger.warning(f'PowerShell 執行警告: {error}')
            
            logger.info(f'PowerShell 命令執行完成，輸出長度: {len(output)} 字元')
            return output, error
        
        except Exception as e:
            error_msg = f'執行 PowerShell 失敗: {str(e)}'
            logger.error(error_msg, exc_info=True)
            return None, error_msg
    
    def get_dhcp_leases(self, scope_id=None):
        """
        從 Windows DHCP Server 獲取租約資料
        
        Args:
            scope_id: Scope ID (例如: 10.250.53.0)，如果為 None 則獲取所有 Scope
        
        Returns:
            租約資料列表（JSON 格式）
        """
        try:
            # 簡化版 PowerShell 命令（直接使用屬性）
            if scope_id:
                # 獲取單一 Scope 的租約
                ps_command = f"Get-DhcpServerv4Lease -ComputerName localhost -ScopeId {scope_id} | ConvertTo-Json -Compress"
            else:
                # 獲取所有 Scope 的租約
                ps_command = "$scopes = Get-DhcpServerv4Scope -ComputerName localhost; $leases = @(); foreach ($scope in $scopes) { $leases += Get-DhcpServerv4Lease -ComputerName localhost -ScopeId $scope.ScopeId }; $leases | ConvertTo-Json -Compress"
            
            # 執行命令
            output, error = self.execute_powershell(ps_command.strip())
            
            if not output:
                logger.error(f'未獲取到租約資料，錯誤: {error}')
                return []
            
            # 解析 JSON
            try:
                data = json.loads(output)
                
                # 如果只有一筆資料，PowerShell 返回字典而非列表
                if isinstance(data, dict):
                    data = [data]
                
                logger.info(f'成功獲取 {len(data)} 筆租約資料')
                return data
            
            except json.JSONDecodeError as e:
                logger.error(f'JSON 解析失敗: {str(e)}', exc_info=True)
                logger.debug(f'原始輸出: {output[:500]}...')
                return []
        
        except Exception as e:
            logger.error(f'獲取 DHCP 租約失敗: {str(e)}', exc_info=True)
            return []
    
    def get_dhcp_scopes(self):
        """
        獲取所有 DHCP Scope 資訊
        
        Returns:
            Scope 資料列表
        """
        try:
            # 簡化版 PowerShell 命令（直接使用屬性，不用 @{} 語法）
            ps_command = "Get-DhcpServerv4Scope -ComputerName localhost | ConvertTo-Json -Compress"
            
            output, error = self.execute_powershell(ps_command.strip())
            
            if not output:
                logger.error(f'未獲取到 Scope 資料，錯誤: {error}')
                return []
            
            try:
                data = json.loads(output)
                if isinstance(data, dict):
                    data = [data]
                
                # 轉換屬性格式
                scopes = []
                for scope in data:
                    scopes.append({
                        'ScopeId': str(scope.get('ScopeId', '')),
                        'Name': scope.get('Name', ''),
                        'SubnetMask': str(scope.get('SubnetMask', '')),
                        'StartRange': str(scope.get('StartRange', '')),
                        'EndRange': str(scope.get('EndRange', '')),
                        'State': str(scope.get('State', '')),
                        'LeaseDuration': str(scope.get('LeaseDuration', '')),
                    })
                
                logger.info(f'成功獲取 {len(scopes)} 個 Scope')
                return scopes
            
            except json.JSONDecodeError as e:
                logger.error(f'JSON 解析失敗: {str(e)}', exc_info=True)
                return []
            
            output, error = self.execute_powershell(ps_command.strip())
            
            if not output:
                logger.error(f'未獲取到 Scope 資料，錯誤: {error}')
                return []
            
            try:
                data = json.loads(output)
                if isinstance(data, dict):
                    data = [data]
                
                logger.info(f'成功獲取 {len(data)} 個 Scope')
                return data
            
            except json.JSONDecodeError as e:
                logger.error(f'JSON 解析失敗: {str(e)}', exc_info=True)
                return []
        
        except Exception as e:
            logger.error(f'獲取 DHCP Scope 失敗: {str(e)}', exc_info=True)
            return []
    
    def parse_client_id(self, client_id):
        """
        解析 Windows DHCP ClientId 為標準 MAC 地址格式
        
        Windows DHCP ClientId 可能的格式：
        - 01-aa-bb-cc-dd-ee-ff (有類型前綴)
        - aa-bb-cc-dd-ee-ff (無前綴)
        
        Args:
            client_id: Windows DHCP ClientId
        
        Returns:
            標準 MAC 地址格式 (aa:bb:cc:dd:ee:ff)
        """
        if not client_id:
            return None
        
        try:
            # 分割 ClientId
            parts = client_id.split('-')
            
            # 判斷格式
            if len(parts) == 7:
                # 格式：01-aa-bb-cc-dd-ee-ff (跳過第一個字節)
                mac_parts = parts[1:7]
            elif len(parts) == 6:
                # 格式：aa-bb-cc-dd-ee-ff (直接使用)
                mac_parts = parts
            else:
                logger.warning(f'無效的 MAC 地址格式: {client_id}')
                return None
            
            # 轉換為標準格式（小寫，冒號分隔）
            mac_address = ':'.join(mac_parts).lower()
            
            # 驗證格式
            if len(mac_address.split(':')) == 6:
                return mac_address
            else:
                logger.warning(f'無效的 MAC 地址格式: {client_id}')
                return None
        
        except Exception as e:
            logger.error(f'MAC 地址解析失敗 ({client_id}): {str(e)}')
            return None
    
    def parse_lease_expiry(self, expiry_str):
        """
        解析租約到期時間
        支援兩種格式：
        1. Windows JSON 格式: /Date(1761993082644)/
        2. 標準格式: yyyy-MM-dd HH:mm:ss
        
        Args:
            expiry_str: 時間字串
        
        Returns:
            datetime 對象（帶時區）
        """
        if not expiry_str:
            return timezone.now() + timedelta(hours=24)
        
        try:
            # 處理 /Date(timestamp)/ 格式
            if isinstance(expiry_str, str) and expiry_str.startswith('/Date('):
                # 提取毫秒時間戳：/Date(1761993082644)/
                timestamp_str = expiry_str[6:-2]  # 移除 "/Date(" 和 ")/"
                timestamp_ms = int(timestamp_str)
                timestamp_sec = timestamp_ms / 1000.0
                
                # 從 UTC 時間戳創建 aware datetime
                from datetime import timezone as dt_timezone
                dt = datetime.fromtimestamp(timestamp_sec, tz=dt_timezone.utc)
                return dt
            
            # 處理標準格式: yyyy-MM-dd HH:mm:ss
            dt = datetime.strptime(str(expiry_str), '%Y-%m-%d %H:%M:%S')
            # 使用 Django timezone 使其 aware
            return timezone.make_aware(dt)
        
        except Exception as e:
            logger.error(f'租約到期時間解析失敗 ({expiry_str}): {str(e)}')
            return timezone.now() + timedelta(hours=24)
    
    def sync_leases_to_db(self):
        """
        同步租約資料到資料庫
        
        Returns:
            同步統計資訊
        """
        from .models import DHCPLease
        
        stats = {
            'total': 0,
            'created': 0,
            'updated': 0,
            'skipped': 0,
            'errors': 0,
        }
        
        try:
            # 獲取所有租約
            lease_data_list = self.get_dhcp_leases()
            stats['total'] = len(lease_data_list)
            
            if not lease_data_list:
                logger.warning('未獲取到任何租約資料')
                return stats
            
            # 處理每筆租約
            for lease_data in lease_data_list:
                try:
                    # 解析 MAC 地址
                    client_id = lease_data.get('ClientId', '')
                    mac_address = self.parse_client_id(client_id)
                    
                    if not mac_address:
                        logger.warning(f'跳過無效的 MAC 地址: {client_id}')
                        stats['skipped'] += 1
                        continue
                    
                    # 獲取 IP 地址（處理字典格式）
                    ip_data = lease_data.get('IPAddress', '')
                    if isinstance(ip_data, dict):
                        # PowerShell 回傳字典：{'IPAddressToString': '10.250.55.20', ...}
                        ip_address = ip_data.get('IPAddressToString', '')
                    else:
                        ip_address = str(ip_data)
                    
                    # 獲取其他欄位
                    hostname = lease_data.get('HostName', '') or ''
                    state = lease_data.get('AddressState', '').lower()
                    
                    # 解析租約到期時間
                    lease_expiry_str = lease_data.get('LeaseExpiryTime', '')
                    lease_end = self.parse_lease_expiry(lease_expiry_str)
                    lease_start = timezone.now()
                    
                    # 判斷是否活躍（直接比較，不檢查時區）
                    try:
                        is_active = (state == 'active' and lease_end > timezone.now())
                    except TypeError:
                        # 時區比較失敗，預設為 True
                        is_active = (state == 'active')
                    
                    # 更新或創建租約
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
            
            # 更新 Server 統計資訊
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
    
    def get_dhcp_logs(self, limit=100, log_date=None):
        """
        從 Windows DHCP Server 讀取日誌檔案
        
        Windows DHCP Server 日誌位置：C:\Windows\System32\dhcp\DhcpSrvLog-*.log
        
        Args:
            limit: 返回的日誌行數限制
            log_date: 指定日期 (格式: 'Mon' 或 'DhcpSrvLog-Mon.log')，預設為今天
        
        Returns:
            list: 日誌內容列表
        """
        try:
            # 如果沒有指定日期，使用今天的日誌
            if not log_date:
                # 獲取今天是星期幾（Mon, Tue, Wed, Thu, Fri, Sat, Sun）
                days_of_week = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
                today = datetime.now().weekday()  # 0=Monday, 6=Sunday
                log_date = days_of_week[today]
            
            # 確保格式正確
            if not log_date.startswith('DhcpSrvLog-'):
                log_file = f'DhcpSrvLog-{log_date}.log'
            else:
                log_file = log_date
            
            # Windows DHCP Server 日誌路徑
            log_path = f'C:\\Windows\\System32\\dhcp\\{log_file}'
            
            # 使用 PowerShell 讀取日誌（取最後 N 行）
            ps_command = f'Get-Content -Path "{log_path}" -Tail {limit} -ErrorAction SilentlyContinue'
            
            output, error = self.execute_powershell(ps_command)
            
            if not output:
                logger.warning(f'未獲取到 DHCP 日誌內容 ({log_file})')
                return []
            
            # 分割成行
            lines = output.strip().split('\n')
            
            logger.info(f'成功讀取 DHCP 日誌: {len(lines)} 行 ({log_file})')
            return lines
        
        except Exception as e:
            logger.error(f'讀取 DHCP 日誌失敗: {str(e)}', exc_info=True)
            return []
    
    def list_available_log_files(self):
        """
        列出所有可用的 DHCP 日誌檔案
        
        Returns:
            list: 日誌檔案名稱列表
        """
        try:
            log_dir = 'C:\\Windows\\System32\\dhcp'
            ps_command = f'Get-ChildItem -Path "{log_dir}" -Filter "DhcpSrvLog-*.log" | Select-Object Name, LastWriteTime, Length'
            
            output, error = self.execute_powershell(ps_command)
            
            if not output:
                logger.warning('未找到 DHCP 日誌檔案')
                return []
            
            # 簡單解析輸出
            files = []
            for line in output.strip().split('\n'):
                if 'DhcpSrvLog-' in line:
                    files.append(line.strip())
            
            logger.info(f'發現 {len(files)} 個 DHCP 日誌檔案')
            return files
        
        except Exception as e:
            logger.error(f'列出日誌檔案失敗: {str(e)}', exc_info=True)
            return []
    
    def close(self):
        """關閉 SSH 連接"""
        if self.client:
            self.client.close()
            logger.info(f'關閉 SSH 連接: {self.host}')
    
    def __enter__(self):
        """支援 with 語法"""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """支援 with 語法"""
        self.close()
