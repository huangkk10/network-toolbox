"""
日誌解析工具模組

提供統一的日誌解析功能，支援多種格式：
- DHCP 日誌（Linux syslog, dhcpd 格式）
- Windows DHCP 日誌（CSV 格式）
- iPXE 日誌（Nginx access log 格式）
- NAS 日誌（各種格式）

作者：Network Toolbox Team
日期：2025-10-30
"""
import re
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any

logger = logging.getLogger(__name__)


class LogLevel:
    """日誌等級常量"""
    DEBUG = 'DEBUG'
    INFO = 'INFO'
    WARN = 'WARN'
    ERROR = 'ERROR'
    CRITICAL = 'CRITICAL'


class DHCPLogParser:
    """
    DHCP 日誌解析器
    
    支援格式：
    - syslog: Oct 27 14:30:22 dhcpd[1234]: DHCP DISCOVER from ...
    - dhcpd.log: 2025-10-27 14:30:22 INFO DHCP DISCOVER from ...
    - 本地日誌: [INFO] 2025-10-27 14:30:22 | DHCP DISCOVER from ...
    """
    
    # 日誌等級對應
    LOG_LEVELS = {
        'INFO': LogLevel.INFO,
        'WARN': LogLevel.WARN,
        'WARNING': LogLevel.WARN,
        'ERROR': LogLevel.ERROR,
        'ERR': LogLevel.ERROR,
        'DEBUG': LogLevel.DEBUG,
        'NOTICE': LogLevel.INFO,
        'CRITICAL': LogLevel.CRITICAL,
    }
    
    # 日誌格式正則表達式
    PATTERNS = [
        # 格式 1: [LEVEL] YYYY-MM-DD HH:MM:SS | message
        r'\[(\w+)\]\s+(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})\s+\|\s+(.+)',
        
        # 格式 2: YYYY-MM-DD HH:MM:SS LEVEL message
        r'(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})\s+(\w+)\s+(.+)',
        
        # 格式 3: syslog - Oct 27 14:30:22 hostname dhcpd[pid]: message
        r'(\w+\s+\d+\s+\d{2}:\d{2}:\d{2})\s+\S+\s+\S+:\s+(.+)',
        
        # 格式 4: 簡單格式 - timestamp message
        r'(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})\s+(.+)',
    ]
    
    @classmethod
    def parse_line(cls, line: str) -> Dict[str, Any]:
        """
        解析單行 DHCP 日誌
        
        Args:
            line: 日誌行文本
        
        Returns:
            dict: 解析後的日誌條目，包含 timestamp, level, message, raw
        """
        log_entry = {
            'timestamp': None,
            'level': LogLevel.INFO,
            'message': '',
            'raw': line.strip(),
        }
        
        # 嘗試多種日誌格式
        for i, pattern in enumerate(cls.PATTERNS):
            match = re.match(pattern, line)
            if match:
                groups = match.groups()
                
                if len(groups) == 3:
                    # 包含等級的格式
                    if i == 0:  # [LEVEL] timestamp | message
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
                    log_entry['level'] = cls._infer_log_level(groups[1])
                
                break
        
        # 如果沒有匹配到任何格式，直接使用原始內容
        if not log_entry['message']:
            log_entry['message'] = line.strip()
            log_entry['level'] = cls._infer_log_level(line)
        
        # 標準化日誌等級
        log_entry['level'] = cls.LOG_LEVELS.get(
            log_entry['level'], 
            LogLevel.INFO
        )
        
        return log_entry
    
    @classmethod
    def _infer_log_level(cls, message: str) -> str:
        """根據訊息內容推測日誌等級"""
        message_lower = message.lower()
        
        if any(keyword in message_lower for keyword in ['error', 'failed', 'fail', 'conflict']):
            return LogLevel.ERROR
        elif any(keyword in message_lower for keyword in ['warn', 'warning', 'threshold']):
            return LogLevel.WARN
        elif any(keyword in message_lower for keyword in ['debug', 'checking']):
            return LogLevel.DEBUG
        else:
            return LogLevel.INFO
    
    @classmethod
    def parse_file(cls, content: str, limit: int = 1000) -> List[Dict[str, Any]]:
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
                entry = cls.parse_line(line)
                entry['id'] = i
                log_entries.append(entry)
        
        return log_entries


class WindowsDHCPLogParser:
    """
    Windows DHCP Server 日誌解析器
    
    Windows DHCP 日誌格式（CSV）：
    ID,Date,Time,Description,IP,Hostname,MAC,Username,TransactionID,QResult,Probationtime,CorrelationID,Dhcid,
    VendorClass(Hex),VendorClass(ASCII),UserClass(Hex),UserClass(ASCII),RelayAgentInfo,DnsRegError
    
    範例：
    10,10/27/25,14:24:02,Assign,192.168.7.199,host-name,aa:bb:cc:dd:ee:ff,0
    11,10/18/25,15:32:59,Renew,10.250.132.27,,BCFCE73A61C9,,727830406,0,,,,0x505845...PXEClient:Arch:00007,0x69505845,iPXE
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
    
    @classmethod
    def parse_line(cls, line: str) -> Optional[Dict[str, Any]]:
        """
        解析單行 Windows DHCP 日誌
        
        Args:
            line: 日誌行文本（CSV 格式）
        
        Returns:
            dict 或 None: 解析後的日誌條目
        """
        line = line.strip()
        
        # 跳過空行和註釋行
        if not line or line.startswith('#'):
            return None
        
        try:
            # 分割欄位（用逗號分隔）
            fields = line.split(',')
            
            if len(fields) < 3:
                return None
            
            event_id = fields[0].strip()
            date_str = fields[1].strip() if len(fields) > 1 else ''
            time_str = fields[2].strip() if len(fields) > 2 else ''
            
            # 解析事件類型
            event_type = cls.EVENT_TYPES.get(event_id, f'Unknown({event_id})')
            
            # 基本日誌條目
            log_entry = {
                'event_id': event_id,
                'event_type': event_type,
                'timestamp': f'{date_str} {time_str}',
                'raw': line,
            }
            
            # 根據事件類型解析不同的欄位
            if event_id in ['10', '11', '12', '13']:  # Assign, Renew, Release, Deny
                log_entry['ip_address'] = fields[4].strip() if len(fields) > 4 else '-'
                log_entry['hostname'] = fields[5].strip() if len(fields) > 5 else '-'
                log_entry['mac_address'] = cls._format_mac_address(fields[6].strip() if len(fields) > 6 else '-')
                
                # 識別客戶端類型（iPXE, PXE, WinPE, OS）
                client_info = cls.identify_client_type(fields)
                log_entry.update(client_info)
                
                # 構建訊息
                log_entry['message'] = cls._build_message(event_id, log_entry)
                
                # 判斷日誌等級
                log_entry['level'] = LogLevel.WARN if event_id == '13' else LogLevel.INFO
            
            elif event_id == '14':  # IP Conflict
                log_entry['ip_address'] = fields[4].strip() if len(fields) > 4 else '-'
                log_entry['message'] = f'IP conflict detected: {log_entry["ip_address"]}'
                log_entry['level'] = LogLevel.ERROR
            
            else:
                # 其他事件類型
                log_entry['message'] = f'{event_type}'
                log_entry['level'] = LogLevel.INFO
            
            return log_entry
        
        except Exception as e:
            logger.warning(f'解析 Windows DHCP 日誌失敗: {line[:50]}... - {e}')
            return None
    
    @classmethod
    def identify_client_type(cls, fields: List[str]) -> Dict[str, str]:
        """
        識別客戶端類型（iPXE, PXE, WinPE, OS）
        
        Args:
            fields: 日誌欄位列表
        
        Returns:
            dict: 包含 client_type, boot_stage, vendor_class, user_class
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
        
        return {
            'client_type': client_type,
            'boot_stage': boot_stage,
            'vendor_class': vendor_class,
            'user_class': user_class,
        }
    
    @classmethod
    def _format_mac_address(cls, mac: str) -> str:
        """格式化 MAC 地址為標準格式"""
        if mac and mac != '-':
            return mac.replace('-', ':').lower()
        return mac
    
    @classmethod
    def _build_message(cls, event_id: str, log_entry: Dict[str, Any]) -> str:
        """構建日誌訊息"""
        ip = log_entry.get('ip_address', '-')
        mac = log_entry.get('mac_address', '-')
        hostname = log_entry.get('hostname', '-')
        client_type = log_entry.get('client_type', 'Unknown')
        
        if event_id == '10':  # Assign
            return f'DHCPOFFER of {ip} from {mac} via eth0'
        elif event_id == '11':  # Renew
            if client_type not in ['Unknown', 'OS']:
                return f'DHCPREQUEST for {ip} from {mac} [{client_type}] via eth0'
            else:
                return f'DHCPREQUEST for {ip} from {mac} via eth0'
        elif event_id == '12':  # Release
            return f'DHCPRELEASE of {ip} from {mac} ({hostname})'
        elif event_id == '13':  # Deny
            return f'DHCPDENY {ip} from {mac} ({hostname})'
        else:
            return f'{log_entry.get("event_type", "Unknown")} {ip}'
    
    @classmethod
    def parse_file(cls, content: str, limit: int = 1000) -> List[Dict[str, Any]]:
        """
        解析 Windows DHCP 日誌檔案
        
        Args:
            content: 日誌檔案內容
            limit: 返回數量限制
        
        Returns:
            list: 解析後的日誌條目列表
        """
        lines = content.strip().split('\n')
        
        logs = []
        for line in lines:
            entry = cls.parse_line(line)
            if entry:
                logs.append(entry)
        
        # 從最後往前取指定數量
        return logs[-limit:] if len(logs) > limit else logs
    
    @classmethod
    def sort_by_timestamp(cls, lines: List[str]) -> List[str]:
        """
        按時間戳排序 Windows DHCP 日誌行
        
        Args:
            lines: 日誌行列表
        
        Returns:
            list: 排序後的日誌行列表
        """
        def parse_timestamp(line):
            try:
                parts = line.split(',')
                if len(parts) >= 3:
                    date_str = parts[1].strip()  # MM/DD/YY
                    time_str = parts[2].strip()  # HH:MM:SS
                    dt = datetime.strptime(f'{date_str} {time_str}', '%m/%d/%y %H:%M:%S')
                    return dt
            except:
                pass
            return datetime(1970, 1, 1)  # 無法解析的放最前面
        
        return sorted(lines, key=parse_timestamp)


class IPXELogParser:
    """
    iPXE 日誌解析器（Nginx access log 格式）
    
    支援格式：
    - MAC Flask: 10.252.170.188 - - [28/Oct/2025:10:18:24 +0000] "GET /iPxeMac/Set?MAC=... HTTP/1.1" 200 7 "-" "ansible-httpget"
    - iPXE Boot: 10.250.53.25 - - [28/Oct/2025:10:18:57 +0000] "GET /boot.ipxe HTTP/1.1" 200 116 "-" "iPXE/1.21.1+"
    """
    
    # Nginx access log 格式正則
    NGINX_PATTERN = r'(\d+\.\d+\.\d+\.\d+) - - \[([^\]]+)\] "([A-Z]+) ([^\s]+) ([^"]+)" (\d+) (\d+) "-" "([^"]+)"'
    
    @classmethod
    def parse_line(cls, line: str, log_type: str = 'BOOT') -> Optional[Dict[str, Any]]:
        """
        解析單行 iPXE 日誌
        
        Args:
            line: 日誌行文本
            log_type: 日誌類型（'MAC' 或 'BOOT'）
        
        Returns:
            dict 或 None: 解析後的日誌條目
        """
        match = re.match(cls.NGINX_PATTERN, line)
        
        if not match:
            return None
        
        client_ip, timestamp_str, method, url, protocol, status_code, bytes_sent, user_agent = match.groups()
        
        # 解析時間
        try:
            timestamp = datetime.strptime(timestamp_str, '%d/%b/%Y:%H:%M:%S %z')
        except:
            logger.warning(f'無法解析時間戳: {timestamp_str}')
            return None
        
        # 基本日誌條目
        log_entry = {
            'log_type': log_type,
            'timestamp': timestamp,
            'client_ip': client_ip,
            'method': method,
            'url': url,
            'protocol': protocol,
            'status_code': int(status_code),
            'bytes_sent': int(bytes_sent),
            'user_agent': user_agent,
            'raw': line,
        }
        
        # 根據日誌類型解析不同的資訊
        if log_type == 'MAC':
            cls._parse_mac_log(log_entry, url)
        else:  # BOOT
            cls._parse_boot_log(log_entry, url)
        
        return log_entry
    
    @classmethod
    def _parse_mac_log(cls, log_entry: Dict[str, Any], url: str):
        """解析 MAC Flask 日誌的 URL 參數"""
        log_entry['mac_address'] = ''
        log_entry['boot_flag'] = None
        log_entry['action'] = 'other'
        log_entry['file_requested'] = ''
        
        if '/iPxeMac/Set' in url:
            log_entry['action'] = 'set_mac'
            mac_match = re.search(r'MAC=([0-9A-Fa-f:]+)', url)
            boot_match = re.search(r'BOOT=(\d)', url)
            if mac_match:
                log_entry['mac_address'] = mac_match.group(1).lower()
            if boot_match:
                log_entry['boot_flag'] = int(boot_match.group(1))
        elif '/iPxeMac/Get' in url:
            log_entry['action'] = 'get_mac'
            mac_match = re.search(r'MAC=([0-9A-Fa-f:]+)', url)
            if mac_match:
                log_entry['mac_address'] = mac_match.group(1).lower()
    
    @classmethod
    def _parse_boot_log(cls, log_entry: Dict[str, Any], url: str):
        """解析 iPXE Boot 日誌的檔案請求"""
        log_entry['mac_address'] = ''
        log_entry['boot_flag'] = None
        log_entry['file_requested'] = url.lstrip('/')
        
        # 判斷 action
        file_requested = log_entry['file_requested']
        if 'boot.ipxe' in file_requested:
            log_entry['action'] = 'boot.ipxe'
        elif 'wimboot' in file_requested:
            log_entry['action'] = 'wimboot'
        elif 'BCD' in file_requested:
            log_entry['action'] = 'BCD'
        elif 'boot.sdi' in file_requested:
            log_entry['action'] = 'boot.sdi'
        elif '.wim' in file_requested.lower():
            log_entry['action'] = 'wim_file'
        else:
            log_entry['action'] = 'other'
    
    @classmethod
    def parse_file(cls, content: str, log_type: str = 'BOOT', limit: int = 1000) -> List[Dict[str, Any]]:
        """
        解析 iPXE 日誌檔案
        
        Args:
            content: 日誌檔案內容
            log_type: 日誌類型（'MAC' 或 'BOOT'）
            limit: 返回數量限制
        
        Returns:
            list: 解析後的日誌條目列表
        """
        lines = content.strip().split('\n')
        
        logs = []
        for line in lines:
            if line.strip():
                entry = cls.parse_line(line, log_type)
                if entry:
                    logs.append(entry)
        
        # 從最後往前取指定數量
        return logs[-limit:] if len(logs) > limit else logs


# 便捷函數
def parse_dhcp_log(content: str, limit: int = 1000) -> List[Dict[str, Any]]:
    """
    解析 DHCP 日誌（Linux/Unix）
    
    Args:
        content: 日誌內容
        limit: 返回數量限制
    
    Returns:
        list: 解析後的日誌條目
    """
    return DHCPLogParser.parse_file(content, limit)


def parse_windows_dhcp_log(content: str, limit: int = 1000) -> List[Dict[str, Any]]:
    """
    解析 Windows DHCP 日誌
    
    Args:
        content: 日誌內容
        limit: 返回數量限制
    
    Returns:
        list: 解析後的日誌條目
    """
    return WindowsDHCPLogParser.parse_file(content, limit)


def parse_ipxe_log(content: str, log_type: str = 'BOOT', limit: int = 1000) -> List[Dict[str, Any]]:
    """
    解析 iPXE 日誌
    
    Args:
        content: 日誌內容
        log_type: 日誌類型（'MAC' 或 'BOOT'）
        limit: 返回數量限制
    
    Returns:
        list: 解析後的日誌條目
    """
    return IPXELogParser.parse_file(content, log_type, limit)
