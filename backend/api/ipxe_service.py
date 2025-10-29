"""
IPXE 日誌收集和管理服務
"""
import paramiko
import re
from datetime import datetime, timedelta
from django.utils import timezone
from .models import IPXEServer, IPXELog, IPXEStatistics
import logging

logger = logging.getLogger(__name__)


class IPXEService:
    """IPXE 日誌收集和管理服務"""
    
    def __init__(self, server: IPXEServer):
        self.server = server
        self.ssh_client = None
    
    def connect_ssh(self):
        """建立 SSH 連接"""
        try:
            self.ssh_client = paramiko.SSHClient()
            self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            self.ssh_client.connect(
                hostname=self.server.ip_address,
                port=self.server.ssh_port,
                username=self.server.ssh_username,
                password=self.server.ssh_password,
                timeout=10
            )
            
            logger.info(f'成功連接到 IPXE Server: {self.server.ip_address}')
            return True
            
        except Exception as e:
            logger.error(f'SSH 連接失敗 ({self.server.ip_address}): {e}', exc_info=True)
            return False
    
    def disconnect_ssh(self):
        """關閉 SSH 連接"""
        if self.ssh_client:
            self.ssh_client.close()
            self.ssh_client = None
    
    def execute_docker_command(self, container_name: str, command: str = "logs --tail 1000") -> str:
        """執行 Docker 命令"""
        try:
            full_command = f"sudo -S docker {command} {container_name}"
            
            stdin, stdout, stderr = self.ssh_client.exec_command(full_command, get_pty=True)
            stdin.write(self.server.ssh_password + "\n")
            stdin.flush()
            
            output = stdout.read().decode('utf-8')
            
            # 過濾掉 sudo 提示
            lines = output.split('\n')
            filtered_lines = [
                line for line in lines 
                if 'password' not in line.lower() and 'sudo' not in line.lower() and line.strip()
            ]
            
            return '\n'.join(filtered_lines)
            
        except Exception as e:
            logger.error(f'執行 Docker 命令失敗: {e}', exc_info=True)
            return ""
    
    def parse_mac_log(self, line: str) -> dict:
        """
        解析 ipxe_mac-flask 容器日誌
        
        使用 library.utils.log_parser.IPXELogParser 進行解析。
        
        格式：10.252.170.188 - - [28/Oct/2025:10:18:24 +0000] "GET /iPxeMac/Set?MAC=10:FF:E0:E2:91:56&BOOT=1 HTTP/1.1" 200 7 "-" "ansible-httpget"
        
        Returns:
            dict: 解析後的日誌資料，包含 timestamp, client_ip, mac_address, boot_flag 等欄位
        """
        from library.utils import IPXELogParser
        
        # 使用新的 Log Parser 模組
        result = IPXELogParser.parse_line(line, log_type='MAC')
        
        return result
    
    def parse_ipxe_log(self, line: str) -> dict:
        """
        解析 ipxe 容器日誌
        
        使用 library.utils.log_parser.IPXELogParser 進行解析。
        
        格式：10.250.53.25 - - [28/Oct/2025:10:18:57 +0000] "GET /boot.ipxe HTTP/1.1" 200 116 "-" "iPXE/1.21.1+ (g83449)" "-"
        
        Returns:
            dict: 解析後的日誌資料，包含 timestamp, client_ip, method, url, status_code 等欄位
        """
        from library.utils import IPXELogParser
        
        # 使用新的 Log Parser 模組
        result = IPXELogParser.parse_line(line, log_type='BOOT')
        
        return result
    
    def collect_logs_from_container(self, container_name: str, log_type: str, limit: int = 1000) -> int:
        """從指定容器收集日誌"""
        try:
            # 獲取日誌
            logs = self.execute_docker_command(container_name, f"logs --tail {limit}")
            
            if not logs:
                logger.warning(f'未獲取到日誌: {container_name}')
                return 0
            
            # 解析日誌
            lines = logs.split('\n')
            parsed_count = 0
            created_count = 0
            
            for line in lines:
                if not line.strip():
                    continue
                
                # 根據日誌類型選擇解析器
                if log_type.lower() == 'mac':
                    parsed = self.parse_mac_log(line)
                else:  # boot
                    parsed = self.parse_ipxe_log(line)
                
                if not parsed:
                    continue
                
                parsed_count += 1
                
                # 檢查是否已存在（避免重複）
                existing = IPXELog.objects.filter(
                    server=self.server,
                    timestamp=parsed['timestamp'],
                    raw=parsed['raw']
                ).exists()
                
                if not existing:
                    IPXELog.objects.create(
                        server=self.server,
                        **parsed
                    )
                    created_count += 1
            
            logger.info(f'容器 {container_name}: 解析 {parsed_count} 行，新增 {created_count} 條日誌')
            return created_count
            
        except Exception as e:
            logger.error(f'收集日誌失敗 ({container_name}): {e}', exc_info=True)
            return 0
    
    def sync_logs_to_db(self, limit: int = 1000) -> dict:
        """同步所有容器的日誌到資料庫"""
        try:
            if not self.connect_ssh():
                return {'error': 'SSH 連接失敗'}
            
            # 收集 MAC 管理日誌
            mac_count = self.collect_logs_from_container(
                self.server.docker_container_mac,
                'mac',
                limit
            )
            
            # 收集 IPXE 開機日誌
            boot_count = self.collect_logs_from_container(
                self.server.docker_container_ipxe,
                'boot',
                limit
            )
            
            self.disconnect_ssh()
            
            # 更新伺服器同步時間
            self.server.last_sync_at = timezone.now()
            self.server.status = 'online'
            self.server.save()
            
            return {
                'mac_logs': mac_count,
                'boot_logs': boot_count,
                'total': mac_count + boot_count,
            }
            
        except Exception as e:
            logger.error(f'同步日誌失敗: {e}', exc_info=True)
            self.server.status = 'offline'
            self.server.save()
            return {'error': str(e)}
    
    def cleanup_old_logs(self, days: int = 7) -> int:
        """清理超過指定天數的舊日誌"""
        try:
            cutoff_date = timezone.now() - timedelta(days=days)
            
            deleted_count, _ = IPXELog.objects.filter(
                server=self.server,
                created_at__lt=cutoff_date
            ).delete()
            
            logger.info(f'清理了 {deleted_count} 條超過 {days} 天的舊日誌')
            return deleted_count
            
        except Exception as e:
            logger.error(f'清理舊日誌失敗: {e}', exc_info=True)
            return 0
    
    def generate_statistics(self) -> dict:
        """生成統計資訊（最近1小時）"""
        try:
            one_hour_ago = timezone.now() - timedelta(hours=1)
            
            logs = IPXELog.objects.filter(
                server=self.server,
                timestamp__gte=one_hour_ago
            )
            
            stats = {
                'total_requests': logs.count(),
                'mac_set_count': logs.filter(action='Set').count(),
                'mac_get_count': logs.filter(action='Get').count(),
                'boot_ipxe_count': logs.filter(action='boot.ipxe').count(),
                'wim_download_count': logs.filter(action='wim_file').count(),
                'total_bytes_sent': sum(log.bytes_sent for log in logs),
                'unique_clients': logs.values('client_ip').distinct().count(),
                'unique_macs': logs.exclude(mac_address='').values('mac_address').distinct().count(),
            }
            
            if stats['total_requests'] > 0:
                stats['avg_bytes_per_request'] = stats['total_bytes_sent'] / stats['total_requests']
            else:
                stats['avg_bytes_per_request'] = 0
            
            # 保存統計資訊
            IPXEStatistics.objects.create(
                server=self.server,
                timestamp=timezone.now(),
                **stats
            )
            
            return stats
            
        except Exception as e:
            logger.error(f'生成統計失敗: {e}', exc_info=True)
            return {}
