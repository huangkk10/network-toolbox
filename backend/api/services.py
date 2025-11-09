"""
DHCP Server SSH 連接和資料擷取服務
"""
import paramiko
import re
import logging
from datetime import datetime, timedelta
from django.utils import timezone
from dateutil import parser as date_parser

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
        
        範例格式:
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
        (可根據實際使用的 DHCP 軟體調整)
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


class DHCPConfigParser:
    """DHCP 配置文件解析器 - 解析 dhcpd.conf"""
    
    @staticmethod
    def parse_config_file(content):
        """
        解析 dhcpd.conf 配置文件，提取 subnet 和 range 資訊
        
        範例格式:
        subnet 192.168.1.0 netmask 255.255.255.0 {
            range 192.168.1.10 192.168.1.100;
            option routers 192.168.1.1;
            option domain-name-servers 8.8.8.8, 8.8.4.4;
        }
        
        Returns:
            list: subnet 配置列表
        """
        import ipaddress
        
        subnets = []
        
        # 使用正則表達式匹配 subnet 區塊
        subnet_pattern = re.compile(
            r'subnet\s+([\d.]+)\s+netmask\s+([\d.]+)\s*\{([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}',
            re.MULTILINE | re.DOTALL
        )
        
        for match in subnet_pattern.finditer(content):
            subnet_ip = match.group(1)
            netmask = match.group(2)
            subnet_block = match.group(3)
            
            # 計算網路範圍
            try:
                network = ipaddress.IPv4Network(f"{subnet_ip}/{netmask}", strict=False)
                network_cidr = str(network)
            except Exception:
                network_cidr = f"{subnet_ip}/{netmask}"
            
            subnet_info = {
                'subnet_id': subnet_ip,
                'name': f'Subnet {subnet_ip}',
                'subnet_mask': netmask,
                'network_range': network_cidr,
                'ranges': [],
                'total_addresses': 0,
                'state': 'Active'
            }
            
            # 提取 range 定義
            range_pattern = re.compile(r'range\s+([\d.]+)\s+([\d.]+)\s*;')
            for range_match in range_pattern.finditer(subnet_block):
                start_ip = range_match.group(1)
                end_ip = range_match.group(2)
                
                # 計算範圍內的 IP 數量
                try:
                    start = ipaddress.IPv4Address(start_ip)
                    end = ipaddress.IPv4Address(end_ip)
                    range_size = int(end) - int(start) + 1
                except Exception:
                    range_size = 0
                
                range_info = {
                    'start_range': start_ip,
                    'end_range': end_ip,
                    'size': range_size
                }
                
                subnet_info['ranges'].append(range_info)
                subnet_info['total_addresses'] += range_size
            
            subnets.append(subnet_info)
        
        logger.info(f'解析到 {len(subnets)} 個 subnet 配置')
        return subnets
    
    @staticmethod
    def calculate_ip_usage(subnets, active_leases):
        """
        根據 subnet 配置和活躍租約計算 IP 使用率
        
        Args:
            subnets: subnet 配置列表
            active_leases: 活躍租約列表
            
        Returns:
            dict: 使用率統計
        """
        import ipaddress
        
        total_ips = sum(subnet['total_addresses'] for subnet in subnets)
        used_ips = len(active_leases)
        
        usage_percentage = (used_ips / total_ips * 100) if total_ips > 0 else 0
        
        # 為每個 subnet 計算詳細使用率
        for subnet in subnets:
            subnet_leases = []
            
            # 找出屬於這個 subnet 的租約
            for lease in active_leases:
                try:
                    lease_ip = ipaddress.IPv4Address(lease.get('ip_address', ''))
                    
                    # 檢查是否在任何 range 內
                    for range_info in subnet['ranges']:
                        start = ipaddress.IPv4Address(range_info['start_range'])
                        end = ipaddress.IPv4Address(range_info['end_range'])
                        
                        if start <= lease_ip <= end:
                            subnet_leases.append(lease)
                            break
                            
                except Exception:
                    continue
            
            subnet_used = len(subnet_leases)
            subnet_total = subnet['total_addresses']
            subnet_usage = (subnet_used / subnet_total * 100) if subnet_total > 0 else 0
            
            subnet.update({
                'in_use_addresses': subnet_used,
                'available_addresses': subnet_total - subnet_used,
                'usage_percentage': round(subnet_usage, 2)
            })
        
        return {
            'total_addresses': total_ips,
            'used_addresses': used_ips,
            'available_addresses': total_ips - used_ips,
            'usage_percentage': round(usage_percentage, 2),
            'subnets': subnets
        }
    
    @staticmethod
    def parse_dhcpd_conf(content):
        """
        解析 dhcpd.conf 配置文件 (Linux DHCP Server)
        
        Returns:
            list: Scope 配置列表
        """
        scopes = []
        
        # 移除註釋行
        lines = []
        for line in content.split('\n'):
            # 移除 # 開頭的註釋
            if '#' in line:
                line = line[:line.index('#')]
            line = line.strip()
            if line:
                lines.append(line)
        
        cleaned_content = ' '.join(lines)
        
        # 使用正則表達式解析 subnet 區塊
        subnet_pattern = re.compile(
            r'subnet\s+([\d.]+)\s+netmask\s+([\d.]+)\s*\{([^}]*(?:\{[^}]*\}[^{}]*)*)\}',
            re.MULTILINE | re.DOTALL
        )
        
        for match in subnet_pattern.finditer(cleaned_content):
            subnet_id = match.group(1)
            netmask = match.group(2)
            subnet_block = match.group(3)
            
            # 初始化 scope 資訊
            scope_info = {
                'scope_id': subnet_id,
                'subnet_mask': netmask,
                'name': subnet_id.split('.')[-2],  # 使用倒數第二段作為名稱
                'ranges': [],
                'options': {},
                'state': 'Active',
            }
            
            # 提取 range 定義
            range_pattern = re.compile(r'range\s+([\d.]+)\s+([\d.]+)\s*;')
            for range_match in range_pattern.finditer(subnet_block):
                start_ip = range_match.group(1)
                end_ip = range_match.group(2)
                scope_info['ranges'].append({
                    'start': start_ip,
                    'end': end_ip,
                })
            
            # 提取常見選項
            option_patterns = {
                'routers': r'option\s+routers\s+([\d.,\s]+);',
                'domain-name-servers': r'option\s+domain-name-servers\s+([\d.,\s]+);',
                'domain-name': r'option\s+domain-name\s+"([^"]+)";',
                'broadcast-address': r'option\s+broadcast-address\s+([\d.]+);',
            }
            
            for option_name, pattern in option_patterns.items():
                option_match = re.search(pattern, subnet_block)
                if option_match:
                    scope_info['options'][option_name] = option_match.group(1).strip()
            
            # 提取租約時間
            lease_time_match = re.search(r'default-lease-time\s+(\d+);', subnet_block)
            if lease_time_match:
                scope_info['lease_duration'] = f"{int(lease_time_match.group(1)) // 3600}h"
            
            max_lease_time_match = re.search(r'max-lease-time\s+(\d+);', subnet_block)
            if max_lease_time_match:
                scope_info['max_lease_duration'] = f"{int(max_lease_time_match.group(1)) // 3600}h"
            
            # 如果有 range 定義才添加
            if scope_info['ranges']:
                scopes.append(scope_info)
                logger.info(f"解析到 Scope: {subnet_id} with {len(scope_info['ranges'])} range(s)")
        
        logger.info(f'從配置文件解析到 {len(scopes)} 個 Scope')
        return scopes
    
    @staticmethod
    def calculate_ip_count(start_ip, end_ip):
        """
        計算 IP 範圍內的 IP 數量
        
        Args:
            start_ip: 起始 IP (str)
            end_ip: 結束 IP (str)
            
        Returns:
            int: IP 數量
        """
        try:
            import ipaddress
            start = ipaddress.IPv4Address(start_ip)
            end = ipaddress.IPv4Address(end_ip)
            return int(end) - int(start) + 1
        except Exception as e:
            logger.error(f'計算 IP 數量失敗 ({start_ip} - {end_ip}): {str(e)}')
            return 0


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
            # 建立 SSH 連接
            self.ssh = DHCPServerSSH(
                host=self.server.ip_address,
                username='root',
                password='your_password'
            )
            
            if not self.ssh.connect():
                return []
            
            # 讀取 dhcpd.leases 檔案
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
            
            # 檢查 DHCP 服務狀態
            commands = [
                'systemctl status dhcpd',
                'systemctl status isc-dhcp-server',
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
        Please use library.utils.log_parser.DHCPLogParser instead.
        This class will be removed in future versions.
    """
    
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
        
        支援的格式:
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
            r'\[(\w+)\]\s+(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})\s+\|\s+(.+)',
            r'(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})\s+(\w+)\s+(.+)',
            r'(\w+\s+\d+\s+\d{2}:\d{2}:\d{2})\s+\S+\s+\S+:\s+(.+)',
            r'(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})\s+(.+)',
        ]
        
        for pattern in patterns:
            match = re.match(pattern, line)
            if match:
                groups = match.groups()
                
                if len(groups) == 3:
                    if pattern == patterns[0]:
                        log_entry['level'] = groups[0].upper()
                        log_entry['timestamp'] = groups[1]
                        log_entry['message'] = groups[2]
                    else:
                        log_entry['timestamp'] = groups[0]
                        log_entry['level'] = groups[1].upper()
                        log_entry['message'] = groups[2]
                elif len(groups) == 2:
                    log_entry['timestamp'] = groups[0]
                    log_entry['message'] = groups[1]
                    log_entry['level'] = DHCPLogParser._infer_log_level(groups[1])
                
                break
        
        if not log_entry['message']:
            log_entry['message'] = line.strip()
            log_entry['level'] = DHCPLogParser._infer_log_level(line)
        
        log_entry['level'] = DHCPLogParser.LOG_LEVELS.get(log_entry['level'], 'INFO')
        
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
            limit: 最多返回幾行 (從最後往前取)
        
        Returns:
            list: 解析後的日誌條目列表
        """
        lines = content.strip().split('\n')
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
        請使用 library.utils.log_parser.WindowsDHCPLogParser 代替。
        此類別將在未來版本中移除。
    """
    
    EVENT_TYPES = {
        '00': 'Start',
        '01': 'Stop',
        '02': 'Temporary',
        '10': 'Assign',
        '11': 'Renew',
        '12': 'Release',
        '13': 'Deny',
        '14': 'Conflict',
        '15': 'Delete',
        '20': 'DNS',
        '24': 'Cleanup',
        '25': 'DHCPREQUEST',
        '30': 'NAP',
    }
    
    @staticmethod
    def identify_client_type(fields):
        """
        識別客戶端類型 (iPXE, PXE, WinPE, OS)
        
        Args:
            fields: 日誌欄位列表
        
        Returns:
            tuple: (client_type, boot_stage, vendor_class, user_class)
        """
        hostname = fields[5].strip() if len(fields) > 5 else ''
        vendor_class_hex = fields[13].strip() if len(fields) > 13 else ''
        vendor_class_ascii = fields[14].strip() if len(fields) > 14 else ''
        user_class_hex = fields[15].strip() if len(fields) > 15 else ''
        user_class_ascii = fields[16].strip() if len(fields) > 16 else ''
        
        vendor_class = vendor_class_ascii if vendor_class_ascii else vendor_class_hex
        user_class = user_class_ascii if user_class_ascii else user_class_hex
        
        if 'iPXE' in user_class or 'iPXE' in vendor_class:
            client_type = 'iPXE'
            boot_stage = 'iPXE Loading'
        elif 'PXEClient' in vendor_class or 'PXE' in vendor_class:
            client_type = 'PXE'
            boot_stage = 'BIOS PXE'
        elif 'MSFT' in vendor_class or 'Microsoft' in vendor_class or hostname.lower().startswith('minint-'):
            client_type = 'WinPE'
            boot_stage = 'Windows PE'
        elif hostname and hostname != '-' and not vendor_class and not user_class:
            client_type = 'OS'
            boot_stage = 'Operating System'
        else:
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
            
            if not line or line.startswith('#'):
                continue
            
            try:
                fields = line.split(',')
                
                if len(fields) < 3:
                    continue
                
                event_id = fields[0].strip()
                date_str = fields[1].strip() if len(fields) > 1 else ''
                time_str = fields[2].strip() if len(fields) > 2 else ''
                
                event_type = WindowsDHCPLogParser.EVENT_TYPES.get(event_id, f'Unknown({event_id})')
                
                client_type = 'Unknown'
                boot_stage = ''
                vendor_class = ''
                user_class = ''
                
                if event_id in ['10', '11', '12', '13']:
                    ip_address = fields[4].strip() if len(fields) > 4 else '-'
                    hostname = fields[5].strip() if len(fields) > 5 else '-'
                    mac_address = fields[6].strip() if len(fields) > 6 else '-'
                    
                    if mac_address and mac_address != '-':
                        mac_address = mac_address.replace('-', ':').lower()
                    
                    client_type, boot_stage, vendor_class, user_class = WindowsDHCPLogParser.identify_client_type(fields)
                    
                    if event_id == '10':
                        message = f'DHCPOFFER of {ip_address} from ad:0d:10:73:dd:d5 via eth0'
                    elif event_id == '11':
                        if client_type != 'Unknown' and client_type != 'OS':
                            message = f'DHCPREQUEST for {ip_address} from {mac_address} [{client_type}] via eth0'
                        else:
                            message = f'DHCPREQUEST for {ip_address} from {mac_address} via eth0'
                    elif event_id == '12':
                        message = f'DHCPRELEASE of {ip_address} from {mac_address} ({hostname})'
                    elif event_id == '13':
                        message = f'DHCPDENY {ip_address} from {mac_address} ({hostname})'
                    
                    if event_id == '13':
                        level = 'WARN'
                    else:
                        level = 'INFO'
                
                elif event_id == '14':
                    ip_address = fields[4].strip() if len(fields) > 4 else '-'
                    message = f'IP conflict detected: {ip_address}'
                    level = 'ERROR'
                
                elif event_id in ['20', '30', '31']:
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
                    message = ' '.join(fields[3:]) if len(fields) > 3 else event_type
                    level = 'INFO'
                
                try:
                    timestamp = f'{date_str} {time_str}'
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
            with WindowsSSHPowerShellService(self.server) as service:
                log_lines = service.get_dhcp_logs(limit=limit)
                
                if not log_lines:
                    logger.warning(f'無法讀取 Windows DHCP 日誌 ({self.server.ip_address})')
                    return stats
                
                from library.utils import parse_windows_dhcp_log
                content = '\n'.join(log_lines)
                logs = parse_windows_dhcp_log(content, limit=limit)
                stats['total'] = len(logs)
                
                for log_data in logs:
                    try:
                        # ✅ 解析 ISO 8601 格式的時間戳（包含時區資訊）
                        # 格式：2025-11-10T03:25:33+08:00
                        timestamp_str = log_data['timestamp']
                        
                        # 嘗試解析 ISO 8601 格式（timezone-aware）
                        try:
                            timestamp = date_parser.isoparse(timestamp_str)
                            # 轉換為 Django 的 TIME_ZONE 設定的時區
                            # 這樣可以確保時區對象一致
                            if timestamp.tzinfo is not None:
                                # 轉換為 UTC，然後讓 Django 處理時區
                                import pytz
                                utc_tz = pytz.UTC
                                timestamp = timestamp.astimezone(utc_tz)
                        except (ValueError, ImportError, AttributeError):
                            # 如果是舊格式（YYYY-MM-DD HH:MM:SS），手動加上時區
                            try:
                                timestamp_naive = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
                                # 假設是 Taipei 時區
                                import pytz
                                taipei_tz = pytz.timezone('Asia/Taipei')
                                timestamp = taipei_tz.localize(timestamp_naive)
                                # 轉換為 UTC 存儲
                                timestamp = timestamp.astimezone(pytz.UTC)
                            except ValueError:
                                logger.warning(f'無法解析時間戳: {timestamp_str}')
                                continue
                        
                        exists = DHCPLog.objects.filter(
                            server=self.server,
                            timestamp=timestamp,
                            raw=log_data['raw']
                        ).exists()
                        
                        if exists:
                            stats['skipped'] += 1
                            continue
                        
                        DHCPLog.objects.create(
                            server=self.server,
                            timestamp=timestamp,  # timezone-aware datetime (UTC)
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
        從資料庫讀取日誌 (支援分頁和篩選)
        
        Args:
            limit: 每頁數量
            page: 頁碼 (從 1 開始)
            level: 日誌等級篩選
            client_type: 客戶端類型篩選
            keyword: 關鍵字篩選
            start_time: 開始時間
            end_time: 結束時間
        
        Returns:
            dict: 日誌數據和分頁資訊
        """
        from .models import DHCPLog
        from django.db.models import Q
        
        if not self.server:
            logger.error('未指定 DHCP Server')
            return {'logs': [], 'total': 0, 'page': 1, 'page_size': limit, 'total_pages': 0}
        
        try:
            queryset = DHCPLog.objects.filter(server=self.server)
            
            if level and level != 'ALL':
                queryset = queryset.filter(level=level)
            
            if client_type and client_type != 'ALL':
                queryset = queryset.filter(client_type=client_type)
            
            if keyword:
                queryset = queryset.filter(
                    Q(message__icontains=keyword) | 
                    Q(event__icontains=keyword) |
                    Q(vendor_class__icontains=keyword) |
                    Q(user_class__icontains=keyword)
                )
            
            if start_time:
                queryset = queryset.filter(timestamp__gte=start_time)
            if end_time:
                queryset = queryset.filter(timestamp__lte=end_time)
            
            queryset = queryset.order_by('-timestamp')
            
            total = queryset.count()
            total_pages = (total + limit - 1) // limit if total > 0 else 0
            
            offset = (page - 1) * limit
            logs_qs = queryset[offset:offset + limit]
            
            logs = []
            for log in logs_qs:
                # ✅ 將 UTC 時間轉換為當前時區（Asia/Taipei）
                local_timestamp = timezone.localtime(log.timestamp)
                
                logs.append({
                    'id': log.id,
                    'timestamp': local_timestamp.strftime('%Y-%m-%d %H:%M:%S'),  # 使用本地時間
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
            start_time: 開始時間
            end_time: 結束時間
        
        Returns:
            list: 日誌條目列表
        """
        import os
        from datetime import datetime
        
        try:
            if not log_file.startswith('/'):
                log_file = os.path.join('/app', log_file)
            
            if not os.path.exists(log_file):
                logger.warning(f'日誌檔案不存在: {log_file}')
                return []
            
            with open(log_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            from library.utils import parse_dhcp_log
            logs = parse_dhcp_log(content, limit=limit * 2)
            
            if level and level != 'ALL':
                logs = [log for log in logs if log['level'] == level]
            
            if keyword:
                keyword_lower = keyword.lower()
                logs = [log for log in logs if keyword_lower in log['message'].lower()]
            
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
                        filtered_logs.append(log)
                
                logs = filtered_logs
            
            logs = logs[-limit:] if len(logs) > limit else logs
            
            logger.info(f'讀取本地日誌: {len(logs)} 筆')
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
            start_time: 開始時間
            end_time: 結束時間
        
        Returns:
            list: 日誌條目列表
        """
        from datetime import datetime
        from .ssh_powershell_service import WindowsSSHPowerShellService
        
        if not self.server:
            logger.error('未指定 DHCP Server')
            return []
        
        try:
            with WindowsSSHPowerShellService(self.server) as service:
                log_lines = service.get_dhcp_logs(limit=limit * 3)
                
                if not log_lines:
                    logger.warning(f'無法讀取 Windows DHCP 日誌 ({self.server.ip_address})')
                    return []
                
                from library.utils import parse_windows_dhcp_log
                content = '\n'.join(log_lines)
                logs = parse_windows_dhcp_log(content, limit=limit * 3)
                
                if level and level != 'ALL':
                    logs = [log for log in logs if log['level'] == level]
                
                if keyword:
                    keyword_lower = keyword.lower()
                    logs = [log for log in logs if keyword_lower in log['message'].lower()]
                
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
                            filtered_logs.append(log)
                    
                    logs = filtered_logs
                
                logs = logs[-limit:] if len(logs) > limit else logs
                
                logger.info(f'讀取 Windows DHCP 遠端日誌: {len(logs)} 筆')
                return logs
        
        except Exception as e:
            logger.error(f'讀取遠端日誌失敗: {str(e)}', exc_info=True)
            return []


class LinuxDHCPConfigService:
    """Linux DHCP 配置同步服務"""
    
    def __init__(self, dhcp_server):
        """
        初始化服務
        
        Args:
            dhcp_server: DHCPServer 模型實例
        """
        self.server = dhcp_server
        self.ssh = None
    
    def __enter__(self):
        """Context manager 支援"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager 支援 - 關閉 SSH 連接"""
        if self.ssh:
            self.ssh.close()
    
    def sync_config_to_db(self):
        """
        從 dhcpd.conf 同步配置到資料庫,創建 DHCPScope 記錄
        
        Returns:
            dict: 同步結果統計
        """
        from .models import DHCPScope, DHCPLease
        from django.utils import timezone
        
        try:
            self.ssh = DHCPServerSSH(
                host=self.server.ip_address,
                port=self.server.ssh_port,
                username=self.server.ssh_username,
                password=self.server.ssh_password,
                key_file=self.server.ssh_key_file if self.server.ssh_key_file else None
            )
            
            if not self.ssh.connect():
                raise Exception(f'無法連接到 DHCP Server: {self.server.ip_address}')
            
            config_path = self.server.dhcp_config_path
            logger.info(f'讀取配置文件: {config_path}')
            
            command = f'cat {config_path}'
            output, error = self.ssh.execute_command(command)
            
            if error or not output:
                raise Exception(f'讀取配置文件失敗: {error}')
            
            scopes = DHCPConfigParser.parse_config_file(output)
            
            if not scopes:
                logger.warning(f'配置文件中未找到 subnet 定義: {self.server.name}')
                return {
                    'success': True,
                    'scopes_found': 0,
                    'scopes_created': 0,
                    'scopes_updated': 0,
                    'message': '未找到 subnet 定義'
                }
            
            stats = {
                'scopes_found': len(scopes),
                'scopes_created': 0,
                'scopes_updated': 0,
                'scopes_with_leases': 0,
            }
            
            for scope_data in scopes:
                scope_id = scope_data['scope_id']
                
                total_addresses = 0
                start_range = None
                end_range = None
                
                for ip_range in scope_data['ranges']:
                    range_count = DHCPConfigParser.calculate_ip_count(
                        ip_range['start'],
                        ip_range['end']
                    )
                    total_addresses += range_count
                    
                    if start_range is None:
                        start_range = ip_range['start']
                        end_range = ip_range['end']
                
                in_use_addresses = DHCPLease.objects.filter(
                    server=self.server,
                    is_active=True,
                    ip_address__gte=start_range,
                    ip_address__lte=end_range
                ).count()
                
                available_addresses = total_addresses - in_use_addresses
                usage_percentage = (in_use_addresses / total_addresses * 100) if total_addresses > 0 else 0
                
                scope, created = DHCPScope.objects.update_or_create(
                    server=self.server,
                    scope_id=scope_id,
                    defaults={
                        'name': scope_data['name'],
                        'subnet_mask': scope_data['subnet_mask'],
                        'start_range': start_range,
                        'end_range': end_range,
                        'state': scope_data.get('state', 'Active'),
                        'lease_duration': scope_data.get('lease_duration', ''),
                        'total_addresses': total_addresses,
                        'in_use_addresses': in_use_addresses,
                        'available_addresses': available_addresses,
                        'usage_percentage': round(usage_percentage, 2),
                    }
                )
                
                if created:
                    stats['scopes_created'] += 1
                    logger.info(f'創建 Scope: {scope_id} ({total_addresses} IPs, {usage_percentage:.1f}% used)')
                else:
                    stats['scopes_updated'] += 1
                    logger.info(f'更新 Scope: {scope_id} ({total_addresses} IPs, {usage_percentage:.1f}% used)')
                
                if in_use_addresses > 0:
                    stats['scopes_with_leases'] += 1
            
            all_scopes = DHCPScope.objects.filter(server=self.server)
            if all_scopes.exists():
                avg_usage = sum(s.usage_percentage for s in all_scopes) / all_scopes.count()
                self.server.pool_usage = round(avg_usage, 2)
                self.server.last_sync_at = timezone.now()
                self.server.save()
                logger.info(f'更新伺服器 pool_usage: {avg_usage:.2f}%')
            
            stats['success'] = True
            stats['message'] = f'成功同步 {stats["scopes_created"] + stats["scopes_updated"]} 個 Scope'
            
            return stats
        
        except Exception as e:
            logger.error(f'同步配置失敗: {str(e)}', exc_info=True)
            return {
                'success': False,
                'error': str(e),
                'scopes_found': 0,
                'scopes_created': 0,
                'scopes_updated': 0,
            }
        finally:
            if self.ssh:
                self.ssh.close()
