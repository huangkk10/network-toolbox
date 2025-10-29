"""
DHCP Server SSH 連接和資料擷取服務
"""
import paramiko
import re
import logging
from datetime import datetime, timedelta
from django.utils import timezone

logger = logging.getLogger(__name__)


class DHCPServerSSH:
    """SSH 連接管理器"""
    
    def __init__(self, host, port=22, username='root', password=None, key_file=None):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.key_file = key_file
        self.client = None
    
    def connect(self):
        """建立 SSH 連接"""
        try:
            self.client = paramiko.SSHClient()
            self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            if self.key_file:
                self.client.connect(
                    self.host,
                    port=self.port,
                    username=self.username,
                    key_filename=self.key_file,
                    timeout=10
                )
            else:
                self.client.connect(
                    self.host,
                    port=self.port,
                    username=self.username,
                    password=self.password,
                    timeout=10
                )
            
            logger.info(f'成功連接到 DHCP Server: {self.host}')
            return True
        except Exception as e:
            logger.error(f'SSH 連接失敗 ({self.host}): {str(e)}', exc_info=True)
            return False
    
    def execute_command(self, command):
        """執行 SSH 指令"""
        try:
            if not self.client:
                if not self.connect():
                    return None, f'SSH 連接失敗: {self.host}'
            
            stdin, stdout, stderr = self.client.exec_command(command, timeout=30)
            output = stdout.read().decode('utf-8')
            error = stderr.read().decode('utf-8')
            
            if error:
                logger.warning(f'指令執行警告 ({command}): {error}')
            
            logger.info(f'成功執行指令: {command}')
            return output, None
        except Exception as e:
            error_msg = f'執行指令失敗 ({command}): {str(e)}'
            logger.error(error_msg, exc_info=True)
            return None, error_msg
    
    def close(self):
        """關閉 SSH 連接"""
        if self.client:
            self.client.close()
            logger.info(f'關閉 SSH 連接: {self.host}')
    
    def __enter__(self):
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


class DHCPLeaseParser:
    """DHCP Lease 資料解析器"""
    
    @staticmethod
    def parse_leases_file(content):
        """
        解析 dhcpd.leases 檔案內容
        
        範例格式：
        lease 192.168.1.100 {
          starts 6 2025/10/26 14:30:22;
          ends 0 2025/10/27 14:30:22;
          hardware ethernet 00:1a:2b:3c:4d:5e;
          client-hostname "desktop-001";
        }
        """
        leases = []
        
        # 使用正則表達式解析每個 lease 區塊
        lease_pattern = re.compile(
            r'lease\s+([\d.]+)\s*\{([^}]+)\}',
            re.MULTILINE | re.DOTALL
        )
        
        for match in lease_pattern.finditer(content):
            ip_address = match.group(1)
            lease_block = match.group(2)
            
            # 解析租約詳細資訊
            lease_info = {
                'ip_address': ip_address,
                'mac_address': '',
                'hostname': '',
                'lease_start': None,
                'lease_end': None,
                'is_active': False,
            }
            
            # 提取 MAC 位址
            mac_match = re.search(r'hardware\s+ethernet\s+([\da-fA-F:]+)', lease_block)
            if mac_match:
                lease_info['mac_address'] = mac_match.group(1).lower()
            
            # 提取主機名稱
            hostname_match = re.search(r'client-hostname\s+"([^"]+)"', lease_block)
            if hostname_match:
                lease_info['hostname'] = hostname_match.group(1)
            
            # 提取開始時間
            starts_match = re.search(r'starts\s+\d+\s+([\d/]+)\s+([\d:]+)', lease_block)
            if starts_match:
                date_str = starts_match.group(1).replace('/', '-')
                time_str = starts_match.group(2)
                try:
                    lease_info['lease_start'] = datetime.strptime(
                        f'{date_str} {time_str}', '%Y-%m-%d %H:%M:%S'
                    )
                except ValueError:
                    pass
            
            # 提取結束時間
            ends_match = re.search(r'ends\s+\d+\s+([\d/]+)\s+([\d:]+)', lease_block)
            if ends_match:
                date_str = ends_match.group(1).replace('/', '-')
                time_str = ends_match.group(2)
                try:
                    lease_info['lease_end'] = datetime.strptime(
                        f'{date_str} {time_str}', '%Y-%m-%d %H:%M:%S'
                    )
                except ValueError:
                    pass
            
            # 判斷是否活躍
            if lease_info['lease_end']:
                lease_info['is_active'] = lease_info['lease_end'] > datetime.now()
            
            # 檢查是否為 binding state active
            if 'binding state active' in lease_block:
                lease_info['is_active'] = True
            
            leases.append(lease_info)
        
        logger.info(f'解析到 {len(leases)} 個租約')
        return leases
    
    @staticmethod
    def parse_dhcp_status(content):
        """
        解析 DHCP Server 狀態資訊
        （可根據實際使用的 DHCP 軟體調整）
        """
        status_info = {
            'is_running': False,
            'total_pools': 0,
            'pool_details': [],
        }
        
        # 檢查服務是否運行
        if 'active (running)' in content.lower() or 'is running' in content.lower():
            status_info['is_running'] = True
        
        return status_info


class DHCPDataService:
    """DHCP 資料服務 - 整合 SSH 和解析功能"""
    
    def __init__(self, dhcp_server):
        """
        初始化服務
        
        Args:
            dhcp_server: DHCPServer 模型實例
        """
        self.server = dhcp_server
        self.ssh = None
    
    def get_leases(self):
        """
        從 DHCP Server 獲取租約資料
        
        Returns:
            list: 租約列表
        """
        try:
            # 建立 SSH 連接（需要在 DHCPServer 模型中儲存 SSH 憑證）
            # 這裡假設使用 password 認證，實際可能需要使用 key file
            self.ssh = DHCPServerSSH(
                host=self.server.ip_address,
                username='root',  # 從設定中讀取
                password='your_password'  # 從加密儲存中讀取
            )
            
            if not self.ssh.connect():
                return []
            
            # 讀取 dhcpd.leases 檔案（路徑可能需要調整）
            leases_file_paths = [
                '/var/lib/dhcpd/dhcpd.leases',  # CentOS/RHEL
                '/var/lib/dhcp/dhcpd.leases',   # Debian/Ubuntu
                '/var/db/dhcpd.leases',         # FreeBSD
            ]
            
            content = None
            for path in leases_file_paths:
                output, error = self.ssh.execute_command(f'cat {path}')
                if output and not error:
                    content = output
                    logger.info(f'成功讀取租約檔案: {path}')
                    break
            
            if not content:
                logger.warning(f'無法讀取任何租約檔案 ({self.server.ip_address})')
                return []
            
            # 解析租約資料
            leases = DHCPLeaseParser.parse_leases_file(content)
            
            return leases
        
        except Exception as e:
            logger.error(f'獲取租約資料失敗: {str(e)}', exc_info=True)
            return []
        
        finally:
            if self.ssh:
                self.ssh.close()
    
    def get_server_status(self):
        """
        獲取 DHCP Server 狀態
        
        Returns:
            dict: 狀態資訊
        """
        try:
            self.ssh = DHCPServerSSH(
                host=self.server.ip_address,
                username='root',
                password='your_password'
            )
            
            if not self.ssh.connect():
                return {'status': 'offline', 'is_running': False}
            
            # 檢查 DHCP 服務狀態（根據不同的 DHCP 軟體調整指令）
            commands = [
                'systemctl status dhcpd',      # CentOS/RHEL
                'systemctl status isc-dhcp-server',  # Debian/Ubuntu
                'service dhcpd status',
            ]
            
            status_output = None
            for cmd in commands:
                output, error = self.ssh.execute_command(cmd)
                if output:
                    status_output = output
                    break
            
            if status_output:
                status_info = DHCPLeaseParser.parse_dhcp_status(status_output)
                return {
                    'status': 'online' if status_info['is_running'] else 'offline',
                    'is_running': status_info['is_running'],
                }
            
            return {'status': 'unknown', 'is_running': False}
        
        except Exception as e:
            logger.error(f'獲取服務狀態失敗: {str(e)}', exc_info=True)
            return {'status': 'offline', 'is_running': False}
        
        finally:
            if self.ssh:
                self.ssh.close()
    
    def sync_leases_to_db(self):
        """
        同步租約資料到資料庫
        
        Returns:
            dict: 同步結果統計
        """
        from .models import DHCPLease
        
        leases = self.get_leases()
        
        stats = {
            'total': len(leases),
            'created': 0,
            'updated': 0,
            'errors': 0,
        }
        
        for lease_data in leases:
            try:
                # 使用 update_or_create 來新增或更新租約
                lease, created = DHCPLease.objects.update_or_create(
                    server=self.server,
                    ip_address=lease_data['ip_address'],
                    mac_address=lease_data['mac_address'],
                    defaults={
                        'hostname': lease_data.get('hostname', ''),
                        'lease_start': lease_data.get('lease_start'),
                        'lease_end': lease_data.get('lease_end'),
                        'is_active': lease_data.get('is_active', False),
                    }
                )
                
                if created:
                    stats['created'] += 1
                else:
                    stats['updated'] += 1
            
            except Exception as e:
                logger.error(f'同步租約失敗 ({lease_data.get("ip_address")}): {str(e)}')
                stats['errors'] += 1
        
        logger.info(f'租約同步完成: {stats}')
        return stats


class DHCPLogParser:
    """
    DHCP 日誌解析器
    
    .. deprecated:: 2025-10-30
        請使用 `library.utils.log_parser.DHCPLogParser` 代替。
        此類別將在未來版本中移除。
        
        遷移範例::
        
            # 舊方式
            from api.services import DHCPLogParser
            logs = DHCPLogParser.parse_log_file(content, limit=1000)
            
            # 新方式
            from library.utils import parse_dhcp_log
            logs = parse_dhcp_log(content, limit=1000)
    """
    
    # 日誌等級對應
    LOG_LEVELS = {
        'INFO': 'INFO',
        'WARN': 'WARN',
        'WARNING': 'WARN',
        'ERROR': 'ERROR',
        'ERR': 'ERROR',
        'DEBUG': 'DEBUG',
        'NOTICE': 'INFO',
    }
    
    @staticmethod
    def parse_dhcp_log_line(line):
        """
        解析單行 DHCP 日誌
        
        支援的格式：
        - syslog: Oct 27 14:30:22 dhcpd[1234]: DHCP DISCOVER from ...
        - dhcpd.log: 2025-10-27 14:30:22 INFO DHCP DISCOVER from ...
        - 本地日誌: [INFO] 2025-10-27 14:30:22 | DHCP DISCOVER from ...
        """
        log_entry = {
            'timestamp': None,
            'level': 'INFO',
            'message': '',
            'raw': line.strip(),
        }
        
        # 嘗試多種日誌格式
        patterns = [
            # 格式 1: [LEVEL] YYYY-MM-DD HH:MM:SS | message
            r'\[(\w+)\]\s+(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})\s+\|\s+(.+)',
            
            # 格式 2: YYYY-MM-DD HH:MM:SS LEVEL message
            r'(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})\s+(\w+)\s+(.+)',
            
            # 格式 3: syslog - Oct 27 14:30:22 hostname dhcpd[pid]: message
            r'(\w+\s+\d+\s+\d{2}:\d{2}:\d{2})\s+\S+\s+\S+:\s+(.+)',
            
            # 格式 4: 簡單格式 - timestamp message
            r'(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})\s+(.+)',
        ]
        
        for pattern in patterns:
            match = re.match(pattern, line)
            if match:
                groups = match.groups()
                
                if len(groups) == 3:
                    # 包含等級的格式
                    if pattern == patterns[0]:  # [LEVEL] timestamp | message
                        log_entry['level'] = groups[0].upper()
                        log_entry['timestamp'] = groups[1]
                        log_entry['message'] = groups[2]
                    else:  # timestamp LEVEL message
                        log_entry['timestamp'] = groups[0]
                        log_entry['level'] = groups[1].upper()
                        log_entry['message'] = groups[2]
                elif len(groups) == 2:
                    # 不包含等級的格式
                    log_entry['timestamp'] = groups[0]
                    log_entry['message'] = groups[1]
                    # 根據關鍵字推測等級
                    log_entry['level'] = DHCPLogParser._infer_log_level(groups[1])
                
                break
        
        # 如果沒有匹配到任何格式，直接使用原始內容
        if not log_entry['message']:
            log_entry['message'] = line.strip()
            log_entry['level'] = DHCPLogParser._infer_log_level(line)
        
        # 標準化日誌等級
        log_entry['level'] = DHCPLogParser.LOG_LEVELS.get(
            log_entry['level'], 
            'INFO'
        )
        
        return log_entry
    
    @staticmethod
    def _infer_log_level(message):
        """根據訊息內容推測日誌等級"""
        message_lower = message.lower()
        
        if any(keyword in message_lower for keyword in ['error', 'failed', 'fail', 'conflict']):
            return 'ERROR'
        elif any(keyword in message_lower for keyword in ['warn', 'warning', 'threshold']):
            return 'WARN'
        elif any(keyword in message_lower for keyword in ['debug', 'checking']):
            return 'DEBUG'
        else:
            return 'INFO'
    
    @staticmethod
    def parse_log_file(content, limit=1000):
        """
        解析日誌檔案內容
        
        Args:
            content: 日誌檔案內容
            limit: 最多返回幾行（從最後往前取）
        
        Returns:
            list: 解析後的日誌條目列表
        """
        lines = content.strip().split('\n')
        
        # 從最後往前取指定數量的行
        lines = lines[-limit:] if len(lines) > limit else lines
        
        log_entries = []
        for i, line in enumerate(lines, 1):
            if line.strip():
                entry = DHCPLogParser.parse_dhcp_log_line(line)
                entry['id'] = i
                log_entries.append(entry)
        
        return log_entries


class WindowsDHCPLogParser:
    """
    Windows DHCP Server 日誌解析器
    
    .. deprecated:: 2025-10-30
        請使用 `library.utils.log_parser.WindowsDHCPLogParser` 代替。
        此類別將在未來版本中移除。
        
        遷移範例::
        
            # 舊方式
            from api.services import WindowsDHCPLogParser
            logs = WindowsDHCPLogParser.parse_log_lines(lines, limit=1000)
            
            # 新方式
            from library.utils import parse_windows_dhcp_log
            logs = parse_windows_dhcp_log(content, limit=1000)
    
    Windows DHCP 日誌格式範例（完整版）：
    ID,Date,Time,Description,IP,Hostname,MAC,Username,TransactionID,QResult,Probationtime,CorrelationID,Dhcid,
    VendorClass(Hex),VendorClass(ASCII),UserClass(Hex),UserClass(ASCII),RelayAgentInfo,DnsRegError
    
    範例：
    10,10/27/25,14:24:02,Assign,192.168.7.199,host-name,aa:bb:cc:dd:ee:ff,0
    11,10/18/25,15:32:59,Renew,10.250.132.27,,BCFCE73A61C9,,727830406,0,,,,0x505845436C69656E74...PXEClient:Arch:00007:UNDI:003010,0x69505845,iPXE
    """
    
    # Windows DHCP 事件代碼對應
    EVENT_TYPES = {
        '00': 'Start',          # 日誌開始
        '01': 'Stop',           # 日誌停止
        '02': 'Temporary',      # 臨時日誌停止
        '10': 'Assign',         # 新租約分配
        '11': 'Renew',          # 租約更新
        '12': 'Release',        # 租約釋放
        '13': 'Deny',           # 拒絕請求
        '14': 'Conflict',       # IP 衝突
        '15': 'Delete',         # 刪除租約
        '20': 'DNS',            # DNS 記錄更新
        '24': 'Cleanup',        # 清理過期租約
        '25': 'DHCPREQUEST',    # DHCP Request
        '30': 'NAP',            # 網路訪問保護
    }
    
    @staticmethod
    def identify_client_type(fields):
        """
        識別客戶端類型（iPXE, PXE, WinPE, OS）
        
        Args:
            fields: 日誌欄位列表
        
        Returns:
            tuple: (client_type, boot_stage, vendor_class, user_class)
        """
        # 提取關鍵欄位
        hostname = fields[5].strip() if len(fields) > 5 else ''
        vendor_class_hex = fields[13].strip() if len(fields) > 13 else ''
        vendor_class_ascii = fields[14].strip() if len(fields) > 14 else ''
        user_class_hex = fields[15].strip() if len(fields) > 15 else ''
        user_class_ascii = fields[16].strip() if len(fields) > 16 else ''
        
        # 合併 Vendor Class（取 ASCII 版本，若不存在則用 Hex）
        vendor_class = vendor_class_ascii if vendor_class_ascii else vendor_class_hex
        user_class = user_class_ascii if user_class_ascii else user_class_hex
        
        # 識別客戶端類型和啟動階段
        if 'iPXE' in user_class or 'iPXE' in vendor_class:
            # 明確的 iPXE 標識（通常在 User Class Option 77）
            client_type = 'iPXE'
            boot_stage = 'iPXE Loading'
        elif 'PXEClient' in vendor_class or 'PXE' in vendor_class:
            # BIOS PXE ROM（在 Vendor Class Option 60）
            client_type = 'PXE'
            boot_stage = 'BIOS PXE'
        elif 'MSFT' in vendor_class or 'Microsoft' in vendor_class or hostname.lower().startswith('minint-'):
            # Windows PE（Vendor Class 包含 "MSFT" 或主機名以 "minint-" 開頭）
            client_type = 'WinPE'
            boot_stage = 'Windows PE'
        elif hostname and hostname != '-' and not vendor_class and not user_class:
            # 正常 OS（有主機名，但沒有 DHCP Options）
            client_type = 'OS'
            boot_stage = 'Operating System'
        else:
            # 無法識別
            client_type = 'Unknown'
            boot_stage = ''
        
        return client_type, boot_stage, vendor_class, user_class
    
    @staticmethod
    def parse_log_lines(lines, limit=1000):
        """
        解析 Windows DHCP 日誌行
        
        Args:
            lines: 日誌行列表
            limit: 返回數量限制
        
        Returns:
            list: 解析後的日誌條目
        """
        logs = []
        
        for line in lines:
            line = line.strip()
            
            # 跳過空行和註釋行
            if not line or line.startswith('#'):
                continue
            
            try:
                # 分割欄位（用逗號分隔）
                fields = line.split(',')
                
                if len(fields) < 3:
                    continue
                
                event_id = fields[0].strip()
                date_str = fields[1].strip() if len(fields) > 1 else ''
                time_str = fields[2].strip() if len(fields) > 2 else ''
                
                # 解析事件類型
                event_type = WindowsDHCPLogParser.EVENT_TYPES.get(event_id, f'Unknown({event_id})')
                
                # 根據事件類型解析不同的欄位
                client_type = 'Unknown'
                boot_stage = ''
                vendor_class = ''
                user_class = ''
                
                if event_id in ['10', '11', '12', '13']:  # Assign, Renew, Release, Deny
                    ip_address = fields[4].strip() if len(fields) > 4 else '-'
                    hostname = fields[5].strip() if len(fields) > 5 else '-'
                    mac_address = fields[6].strip() if len(fields) > 6 else '-'
                    
                    # 格式化 MAC 地址（轉換為標準格式）
                    if mac_address and mac_address != '-':
                        mac_address = mac_address.replace('-', ':').lower()
                    
                    # 識別客戶端類型（iPXE, PXE, WinPE, OS）
                    client_type, boot_stage, vendor_class, user_class = WindowsDHCPLogParser.identify_client_type(fields)
                    
                    # 優化訊息格式（包含客戶端類型資訊）
                    if event_id == '10':  # Assign
                        message = f'DHCPOFFER of {ip_address} from ad:0d:10:73:dd:d5 via eth0'
                    elif event_id == '11':  # Renew
                        if client_type != 'Unknown' and client_type != 'OS':
                            message = f'DHCPREQUEST for {ip_address} from {mac_address} [{client_type}] via eth0'
                        else:
                            message = f'DHCPREQUEST for {ip_address} from {mac_address} via eth0'
                    elif event_id == '12':  # Release
                        message = f'DHCPRELEASE of {ip_address} from {mac_address} ({hostname})'
                    elif event_id == '13':  # Deny
                        message = f'DHCPDENY {ip_address} from {mac_address} ({hostname})'
                    
                    # 判斷日誌等級
                    if event_id == '13':  # Deny
                        level = 'WARN'
                    else:
                        level = 'INFO'
                
                elif event_id == '14':  # IP Conflict
                    ip_address = fields[4].strip() if len(fields) > 4 else '-'
                    message = f'IP conflict detected: {ip_address}'
                    level = 'ERROR'
                
                elif event_id in ['20', '30', '31']:  # DNS operations
                    ip_address = fields[4].strip() if len(fields) > 4 else '-'
                    hostname = fields[5].strip() if len(fields) > 5 else '-'
                    
                    if event_id == '20':
                        message = f'DNS record updated for {hostname} ({ip_address})'
                        level = 'DEBUG'
                    elif event_id == '30':
                        message = f'DNS Update Request for {hostname} ({ip_address})'
                        level = 'DEBUG'
                    elif event_id == '31':
                        message = f'DNS Update Failed for {hostname} ({ip_address})'
                        level = 'WARN'
                
                else:
                    # 其他事件類型，顯示原始內容
                    message = ' '.join(fields[3:]) if len(fields) > 3 else event_type
                    level = 'INFO'
                
                # 解析時間戳（Windows 格式: MM/DD/YY HH:MM:SS）
                try:
                    timestamp = f'{date_str} {time_str}'
                    # 轉換為標準格式
                    dt = datetime.strptime(timestamp, '%m/%d/%y %H:%M:%S')
                    timestamp = dt.strftime('%Y-%m-%d %H:%M:%S')
                except:
                    timestamp = f'{date_str} {time_str}'
                
                logs.append({
                    'timestamp': timestamp,
                    'level': level,
                    'event': event_type,
                    'message': message,
                    'raw': line,
                    'client_type': client_type,
                    'boot_stage': boot_stage,
                    'vendor_class': vendor_class,
                    'user_class': user_class,
                })
            
            except Exception as e:
                logger.debug(f'解析日誌行失敗: {line} - {str(e)}')
                continue
        
        # 限制返回數量
        if len(logs) > limit:
            logs = logs[-limit:]
        
        return logs


class DHCPLogService:
    """DHCP 日誌服務"""
    
    def __init__(self, dhcp_server=None):
        self.server = dhcp_server
        self.ssh = None
    
    def sync_logs_to_db(self, limit=1000):
        """
        同步遠端日誌到資料庫
        
        Args:
            limit: 每次同步的日誌數量
        
        Returns:
            dict: 同步結果統計
        """
        from .models import DHCPLog
        from datetime import datetime
        from .ssh_powershell_service import WindowsSSHPowerShellService
        
        if not self.server:
            logger.error('未指定 DHCP Server')
            return {'total': 0, 'created': 0, 'skipped': 0, 'errors': 0}
        
        stats = {
            'total': 0,
            'created': 0,
            'skipped': 0,
            'errors': 0,
        }
        
        try:
            # 從 Windows DHCP Server 讀取日誌
            with WindowsSSHPowerShellService(self.server) as service:
                log_lines = service.get_dhcp_logs(limit=limit)
                
                if not log_lines:
                    logger.warning(f'無法讀取 Windows DHCP 日誌 ({self.server.ip_address})')
                    return stats
                
                # 使用新的 Log Parser 模組解析日誌
                from library.utils import parse_windows_dhcp_log
                # 將 log_lines 列表轉換為字串（以換行符分隔）
                content = '\n'.join(log_lines)
                logs = parse_windows_dhcp_log(content, limit=limit)
                stats['total'] = len(logs)
                
                # 批次插入資料庫（避免重複）
                for log_data in logs:
                    try:
                        # 解析時間戳
                        timestamp = datetime.strptime(log_data['timestamp'], '%Y-%m-%d %H:%M:%S')
                        
                        # 檢查是否已存在（使用 server + timestamp + raw 作為唯一識別）
                        exists = DHCPLog.objects.filter(
                            server=self.server,
                            timestamp=timestamp,
                            raw=log_data['raw']
                        ).exists()
                        
                        if exists:
                            stats['skipped'] += 1
                            continue
                        
                        # 建立新日誌
                        DHCPLog.objects.create(
                            server=self.server,
                            timestamp=timestamp,
                            level=log_data['level'],
                            event=log_data.get('event', ''),
                            message=log_data['message'],
                            raw=log_data['raw'],
                            client_type=log_data.get('client_type', 'Unknown'),
                            boot_stage=log_data.get('boot_stage', ''),
                            vendor_class=log_data.get('vendor_class', ''),
                            user_class=log_data.get('user_class', ''),
                        )
                        stats['created'] += 1
                    
                    except Exception as e:
                        logger.error(f'插入日誌失敗: {str(e)}')
                        stats['errors'] += 1
                
                logger.info(f'日誌同步完成: {stats}')
                return stats
        
        except Exception as e:
            logger.error(f'同步日誌失敗: {str(e)}', exc_info=True)
            return stats
    
    def get_db_logs(self, limit=100, page=1, level=None, client_type=None, keyword=None, start_time=None, end_time=None):
        """
        從資料庫讀取日誌（支援分頁和篩選）
        
        Args:
            limit: 每頁數量
            page: 頁碼（從 1 開始）
            level: 日誌等級篩選
            client_type: 客戶端類型篩選（iPXE, PXE, WinPE, OS, Unknown）
            keyword: 關鍵字篩選
            start_time: 開始時間 (datetime 物件)
            end_time: 結束時間 (datetime 物件)
        
        Returns:
            dict: {
                'logs': [...],
                'total': 總數,
                'page': 當前頁碼,
                'page_size': 每頁數量,
                'total_pages': 總頁數
            }
        """
        from .models import DHCPLog
        from django.db.models import Q
        
        if not self.server:
            logger.error('未指定 DHCP Server')
            return {'logs': [], 'total': 0, 'page': 1, 'page_size': limit, 'total_pages': 0}
        
        try:
            # 建立查詢
            queryset = DHCPLog.objects.filter(server=self.server)
            
            # 篩選日誌等級
            if level and level != 'ALL':
                queryset = queryset.filter(level=level)
            
            # 篩選客戶端類型
            if client_type and client_type != 'ALL':
                queryset = queryset.filter(client_type=client_type)
            
            # 篩選關鍵字
            if keyword:
                queryset = queryset.filter(
                    Q(message__icontains=keyword) | 
                    Q(event__icontains=keyword) |
                    Q(vendor_class__icontains=keyword) |  # 新增：搜尋 Vendor Class
                    Q(user_class__icontains=keyword)      # 新增：搜尋 User Class
                )
            
            # 篩選時間範圍
            if start_time:
                queryset = queryset.filter(timestamp__gte=start_time)
            if end_time:
                queryset = queryset.filter(timestamp__lte=end_time)
            
            # 排序
            queryset = queryset.order_by('-timestamp')
            
            # 計算總數
            total = queryset.count()
            total_pages = (total + limit - 1) // limit if total > 0 else 0
            
            # 分頁
            offset = (page - 1) * limit
            logs_qs = queryset[offset:offset + limit]
            
            # 轉換為字典格式
            logs = []
            for log in logs_qs:
                logs.append({
                    'id': log.id,
                    'timestamp': log.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                    'level': log.level,
                    'event': log.event,
                    'message': log.message,
                    'raw': log.raw,
                    'client_type': log.client_type,
                    'boot_stage': log.boot_stage,
                    'vendor_class': log.vendor_class,
                    'user_class': log.user_class,
                })
            
            return {
                'logs': logs,
                'total': total,
                'page': page,
                'page_size': limit,
                'total_pages': total_pages,
            }
        
        except Exception as e:
            logger.error(f'讀取資料庫日誌失敗: {str(e)}', exc_info=True)
            return {'logs': [], 'total': 0, 'page': 1, 'page_size': limit, 'total_pages': 0}
    
    def get_local_logs(self, log_file='logs/dhcp_operations.log', limit=1000, level=None, keyword=None, start_time=None, end_time=None):
        """
        讀取本地日誌檔案
        
        Args:
            log_file: 日誌檔案路徑
            limit: 最多返回幾行
            level: 篩選日誌等級
            keyword: 篩選關鍵字
            start_time: 開始時間 (YYYY-MM-DD HH:mm:ss)
            end_time: 結束時間 (YYYY-MM-DD HH:mm:ss)
        
        Returns:
            list: 日誌條目列表
        """
        import os
        from datetime import datetime
        
        try:
            # 確保路徑是相對於專案根目錄
            if not log_file.startswith('/'):
                log_file = os.path.join('/app', log_file)
            
            if not os.path.exists(log_file):
                logger.warning(f'日誌檔案不存在: {log_file}')
                return []
            
            with open(log_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 使用新的 Log Parser 模組
            from library.utils import parse_dhcp_log
            logs = parse_dhcp_log(content, limit=limit * 2)  # 多讀一些以備篩選
            
            # 篩選日誌等級
            if level and level != 'ALL':
                logs = [log for log in logs if log['level'] == level]
            
            # 篩選關鍵字
            if keyword:
                keyword_lower = keyword.lower()
                logs = [
                    log for log in logs 
                    if keyword_lower in log['message'].lower()
                ]
            
            # 篩選時間範圍
            if start_time or end_time:
                filtered_logs = []
                for log in logs:
                    try:
                        # 解析日誌時間戳 (2025-10-27 12:44:02)
                        log_time = datetime.strptime(log['timestamp'], '%Y-%m-%d %H:%M:%S')
                        
                        # 檢查開始時間
                        if start_time:
                            start_dt = datetime.strptime(start_time, '%Y-%m-%d %H:%M:%S')
                            if log_time < start_dt:
                                continue
                        
                        # 檢查結束時間
                        if end_time:
                            end_dt = datetime.strptime(end_time, '%Y-%m-%d %H:%M:%S')
                            if log_time > end_dt:
                                continue
                        
                        filtered_logs.append(log)
                    except ValueError:
                        # 時間格式解析失敗，保留該日誌
                        filtered_logs.append(log)
                
                logs = filtered_logs
            
            # 限制返回數量
            logs = logs[-limit:] if len(logs) > limit else logs
            
            logger.info(f'讀取本地日誌: {len(logs)} 筆 (時間範圍: {start_time} ~ {end_time})')
            return logs
        
        except Exception as e:
            logger.error(f'讀取本地日誌失敗: {str(e)}', exc_info=True)
            return []
    
    def get_remote_logs(self, limit=1000, level=None, keyword=None, start_time=None, end_time=None):
        """
        透過 SSH 讀取遠端 Windows DHCP Server 日誌
        
        Args:
            limit: 返回數量限制
            level: 日誌等級篩選
            keyword: 關鍵字篩選
            start_time: 開始時間 (YYYY-MM-DD HH:mm:ss)
            end_time: 結束時間 (YYYY-MM-DD HH:mm:ss)
        
        Returns:
            list: 日誌條目列表
        """
        from datetime import datetime
        from .ssh_powershell_service import WindowsSSHPowerShellService
        
        if not self.server:
            logger.error('未指定 DHCP Server')
            return []
        
        try:
            # 使用 SSH + PowerShell 讀取 Windows DHCP 日誌
            with WindowsSSHPowerShellService(self.server) as service:
                # 讀取今天的 DHCP 日誌（讀取 limit * 3 以備篩選）
                log_lines = service.get_dhcp_logs(limit=limit * 3)
                
                if not log_lines:
                    logger.warning(f'無法讀取 Windows DHCP 日誌 ({self.server.ip_address})')
                    return []
                
                # 使用新的 Log Parser 模組解析 Windows DHCP 日誌（增加解析量以備篩選）
                from library.utils import parse_windows_dhcp_log
                content = '\n'.join(log_lines)
                logs = parse_windows_dhcp_log(content, limit=limit * 3)
                
                # 篩選日誌等級
                if level and level != 'ALL':
                    logs = [log for log in logs if log['level'] == level]
                
                # 篩選關鍵字
                if keyword:
                    keyword_lower = keyword.lower()
                    logs = [
                        log for log in logs 
                        if keyword_lower in log['message'].lower()
                    ]
                
                # 篩選時間範圍
                if start_time or end_time:
                    filtered_logs = []
                    for log in logs:
                        try:
                            log_time = datetime.strptime(log['timestamp'], '%Y-%m-%d %H:%M:%S')
                            
                            if start_time:
                                start_dt = datetime.strptime(start_time, '%Y-%m-%d %H:%M:%S')
                                if log_time < start_dt:
                                    continue
                            
                            if end_time:
                                end_dt = datetime.strptime(end_time, '%Y-%m-%d %H:%M:%S')
                                if log_time > end_dt:
                                    continue
                            
                            filtered_logs.append(log)
                        except ValueError:
                            # 時間格式解析失敗，保留該日誌
                            filtered_logs.append(log)
                    
                    logs = filtered_logs
                
                # 限制返回數量
                logs = logs[-limit:] if len(logs) > limit else logs
                
                logger.info(f'讀取 Windows DHCP 遠端日誌: {len(logs)} 筆')
                return logs
        
        except Exception as e:
            logger.error(f'讀取遠端日誌失敗: {str(e)}', exc_info=True)
            return []
