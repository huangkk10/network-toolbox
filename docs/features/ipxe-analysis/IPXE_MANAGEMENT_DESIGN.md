# IPXE 管理功能設計文檔

## 📋 概述

基於現有的 DHCP Server 管理架構，設計一個完全仿效的 **IPXE 管理** 功能模組。

### 核心需求
- ✅ 管理多台 IPXE 伺服器（10.250.x.2）
- ✅ 透過 SSH + Docker 命令收集日誌
- ✅ 前端顯示最近 1 週的日誌
- ✅ 每 10 分鐘自動更新
- ✅ 自動清理超過 1 週的舊資料
- ✅ 完全仿效 DHCP Server 管理的架構

---

## 🏗️ 系統架構

### 已發現的 IPXE 伺服器資訊

**測試伺服器：10.250.50.2**
- **使用者名稱**：rvt
- **密碼**：1.a
- **SSH 端口**：22
- **Docker 容器**：
  1. `ipxe_mac-flask` - IPXE MAC 地址管理服務（Port 9000）
  2. `ipxe` - IPXE HTTP 服務（Port 8080）

**其他伺服器**：
- 10.250.51.2
- 10.250.52.2
- 10.250.53.2
- 10.250.54.2
- ...等（需要確認實際部署的伺服器）

### 日誌格式分析

#### 1. `ipxe_mac-flask` 容器日誌格式

**典型日誌行**：
```
10.252.170.188 - - [28/Oct/2025:10:18:24 +0000] "GET /iPxeMac/Set?MAC=10:FF:E0:E2:91:56&BOOT=1 HTTP/1.1" 200 7 "-" "ansible-httpget"
10.250.53.25 - - [28/Oct/2025:10:18:53 +0000] "GET /iPxeMac/Get?MAC=10:ff:e0:e2:96:db HTTP/1.1" 200 111 "-" "iPXE/1.21.1+ (g83449)"
```

**格式解析**：
```
{IP} - - [{Timestamp}] "{Method} {URL} {Protocol}" {StatusCode} {BytesSent} "-" "{UserAgent}"
```

**提取欄位**：
- `client_ip`：客戶端 IP（10.252.170.188）
- `timestamp`：日誌時間（28/Oct/2025:10:18:24 +0000）
- `method`：HTTP 方法（GET）
- `url`：請求 URL（/iPxeMac/Set?MAC=...&BOOT=1）
- `action`：操作類型（Set/Get）
- `mac_address`：MAC 地址（從 URL 參數提取）
- `boot_flag`：BOOT 參數（0/1，從 URL 參數提取）
- `status_code`：HTTP 狀態碼（200）
- `bytes_sent`：傳輸位元組數（7）
- `user_agent`：客戶端類型（ansible-httpget / iPXE/1.21.1+）

#### 2. `ipxe` 容器日誌格式

**典型日誌行**：
```
10.250.53.25 - - [28/Oct/2025:10:18:57 +0000] "GET /boot.ipxe HTTP/1.1" 200 116 "-" "iPXE/1.21.1+ (g83449)" "-"
10.250.53.25 - - [28/Oct/2025:10:18:57 +0000] "GET /wimboot HTTP/1.1" 200 62440 "-" "iPXE/1.21.1+ (g83449)" "-"
10.250.53.25 - - [28/Oct/2025:10:19:01 +0000] "GET /LiteTouchPE_x64.wim HTTP/1.1" 200 576926332 "-" "iPXE/1.21.1+ (g83449)" "-"
```

**格式解析**：
```
{IP} - - [{Timestamp}] "{Method} {URL} {Protocol}" {StatusCode} {BytesSent} "-" "{UserAgent}" "-"
```

**提取欄位**：
- `client_ip`：客戶端 IP
- `timestamp`：日誌時間
- `method`：HTTP 方法（GET）
- `file_requested`：請求的檔案（boot.ipxe, wimboot, BCD, boot.sdi, LiteTouchPE_x64.wim）
- `status_code`：HTTP 狀態碼（200）
- `bytes_sent`：傳輸位元組數（表示檔案大小）
- `user_agent`：客戶端版本（iPXE/1.21.1+）

---

## 📊 資料庫設計

### 模型 1：IPXEServer（仿效 DHCPServer）

```python
class IPXEServer(models.Model):
    """IPXE 伺服器模型"""
    
    STATUS_CHOICES = [
        ('online', 'Online'),
        ('offline', 'Offline'),
        ('warning', 'Warning'),
    ]
    
    # 基本資訊
    name = models.CharField(max_length=200, verbose_name='伺服器名稱')
    ip_address = models.GenericIPAddressField(verbose_name='IP 位址', unique=True)
    description = models.TextField(blank=True, verbose_name='描述')
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='offline',
        verbose_name='狀態'
    )
    
    # 統計資訊
    total_requests_today = models.IntegerField(default=0, verbose_name='今日請求總數')
    mac_registrations = models.IntegerField(default=0, verbose_name='MAC 註冊數')
    boot_requests = models.IntegerField(default=0, verbose_name='開機請求數')
    
    # SSH 連接設定
    ssh_port = models.IntegerField(default=22, verbose_name='SSH 連接埠')
    ssh_username = models.CharField(max_length=100, default='rvt', verbose_name='SSH 使用者名稱')
    ssh_password = models.CharField(max_length=255, verbose_name='SSH 密碼')  # 建議加密
    
    # Docker 容器設定
    docker_container_mac = models.CharField(
        max_length=100,
        default='ipxe_mac-flask',
        verbose_name='MAC 管理容器名稱'
    )
    docker_container_ipxe = models.CharField(
        max_length=100,
        default='ipxe',
        verbose_name='IPXE HTTP 容器名稱'
    )
    
    # 元數據
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='建立時間')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新時間')
    last_sync_at = models.DateTimeField(null=True, blank=True, verbose_name='上次同步時間')
    
    class Meta:
        verbose_name = 'IPXE 伺服器'
        verbose_name_plural = 'IPXE 伺服器'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['ip_address'], name='idx_ipxe_server_ip'),
            models.Index(fields=['status'], name='idx_ipxe_server_status'),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.ip_address})"
```

### 模型 2：IPXELog（仿效 DHCPLog）

```python
class IPXELog(models.Model):
    """IPXE 日誌模型 - 7天滾動視窗"""
    
    LOG_TYPE_CHOICES = [
        ('mac', 'MAC 管理'),
        ('boot', 'IPXE 開機'),
    ]
    
    ACTION_CHOICES = [
        ('Set', 'Set'),
        ('Get', 'Get'),
        ('boot.ipxe', 'boot.ipxe'),
        ('wimboot', 'wimboot'),
        ('BCD', 'BCD'),
        ('boot.sdi', 'boot.sdi'),
        ('wim_file', 'WIM File'),
        ('other', 'Other'),
    ]
    
    server = models.ForeignKey(
        IPXEServer,
        on_delete=models.CASCADE,
        related_name='logs',
        verbose_name='所屬伺服器'
    )
    
    # 日誌基本資訊
    timestamp = models.DateTimeField(verbose_name='日誌時間', db_index=True)
    log_type = models.CharField(
        max_length=10,
        choices=LOG_TYPE_CHOICES,
        verbose_name='日誌類型',
        db_index=True
    )
    client_ip = models.GenericIPAddressField(verbose_name='客戶端 IP')
    
    # HTTP 請求資訊
    method = models.CharField(max_length=10, default='GET', verbose_name='HTTP 方法')
    url = models.CharField(max_length=500, verbose_name='請求 URL')
    action = models.CharField(
        max_length=20,
        choices=ACTION_CHOICES,
        verbose_name='操作類型',
        db_index=True
    )
    status_code = models.IntegerField(verbose_name='HTTP 狀態碼')
    bytes_sent = models.BigIntegerField(verbose_name='傳輸位元組數')
    user_agent = models.CharField(max_length=200, verbose_name='User Agent')
    
    # MAC 管理專屬欄位
    mac_address = models.CharField(max_length=17, blank=True, verbose_name='MAC 位址')
    boot_flag = models.IntegerField(null=True, blank=True, verbose_name='BOOT 旗標')  # 0/1
    
    # IPXE 開機專屬欄位
    file_requested = models.CharField(max_length=200, blank=True, verbose_name='請求的檔案')
    
    # 原始日誌
    raw = models.TextField(verbose_name='原始日誌')
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='建立時間')
    
    class Meta:
        verbose_name = 'IPXE 日誌'
        verbose_name_plural = 'IPXE 日誌'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['server', '-timestamp'], name='idx_ipxe_log_server_time'),
            models.Index(fields=['-timestamp'], name='idx_ipxe_log_timestamp'),
            models.Index(fields=['log_type'], name='idx_ipxe_log_type'),
            models.Index(fields=['client_ip'], name='idx_ipxe_log_client_ip'),
            models.Index(fields=['mac_address'], name='idx_ipxe_log_mac'),
        ]
    
    def __str__(self):
        return f"[{self.log_type}] {self.timestamp} - {self.client_ip} - {self.action}"
```

### 模型 3：IPXEStatistics（統計資訊）

```python
class IPXEStatistics(models.Model):
    """IPXE 統計資訊（每小時更新）"""
    
    server = models.ForeignKey(
        IPXEServer,
        on_delete=models.CASCADE,
        related_name='statistics',
        verbose_name='所屬伺服器'
    )
    
    timestamp = models.DateTimeField(verbose_name='統計時間', db_index=True)
    
    # 請求統計
    total_requests = models.IntegerField(default=0, verbose_name='總請求數')
    mac_set_count = models.IntegerField(default=0, verbose_name='MAC Set 數量')
    mac_get_count = models.IntegerField(default=0, verbose_name='MAC Get 數量')
    boot_ipxe_count = models.IntegerField(default=0, verbose_name='boot.ipxe 請求數')
    wim_download_count = models.IntegerField(default=0, verbose_name='WIM 下載數')
    
    # 傳輸統計
    total_bytes_sent = models.BigIntegerField(default=0, verbose_name='總傳輸位元組')
    avg_bytes_per_request = models.FloatField(default=0, verbose_name='平均每請求位元組')
    
    # 客戶端統計
    unique_clients = models.IntegerField(default=0, verbose_name='唯一客戶端數')
    unique_macs = models.IntegerField(default=0, verbose_name='唯一 MAC 數')
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='建立時間')
    
    class Meta:
        verbose_name = 'IPXE 統計'
        verbose_name_plural = 'IPXE 統計'
        ordering = ['-timestamp']
        unique_together = ['server', 'timestamp']
        indexes = [
            models.Index(fields=['server', '-timestamp'], name='idx_ipxe_stats_server_time'),
        ]
    
    def __str__(self):
        return f"{self.server.name} - {self.timestamp} ({self.total_requests} requests)"
```

---

## 🔧 後端服務設計

### 1. IPXEService（日誌收集服務）

檔案：`backend/api/ipxe_service.py`

```python
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
        
        格式：10.252.170.188 - - [28/Oct/2025:10:18:24 +0000] "GET /iPxeMac/Set?MAC=10:FF:E0:E2:91:56&BOOT=1 HTTP/1.1" 200 7 "-" "ansible-httpget"
        """
        pattern = r'(\d+\.\d+\.\d+\.\d+) - - \[([^\]]+)\] "([A-Z]+) ([^\s]+) ([^"]+)" (\d+) (\d+) "-" "([^"]+)"'
        match = re.match(pattern, line)
        
        if not match:
            return None
        
        client_ip, timestamp_str, method, url, protocol, status_code, bytes_sent, user_agent = match.groups()
        
        # 解析時間
        try:
            timestamp = datetime.strptime(timestamp_str, '%d/%b/%Y:%H:%M:%S %z')
        except:
            return None
        
        # 解析 URL 參數
        mac_address = None
        boot_flag = None
        action = None
        
        if '/iPxeMac/Set' in url:
            action = 'Set'
            mac_match = re.search(r'MAC=([0-9A-Fa-f:]+)', url)
            boot_match = re.search(r'BOOT=(\d)', url)
            if mac_match:
                mac_address = mac_match.group(1).lower()
            if boot_match:
                boot_flag = int(boot_match.group(1))
        elif '/iPxeMac/Get' in url:
            action = 'Get'
            mac_match = re.search(r'MAC=([0-9A-Fa-f:]+)', url)
            if mac_match:
                mac_address = mac_match.group(1).lower()
        
        return {
            'log_type': 'mac',
            'timestamp': timestamp,
            'client_ip': client_ip,
            'method': method,
            'url': url,
            'action': action or 'other',
            'status_code': int(status_code),
            'bytes_sent': int(bytes_sent),
            'user_agent': user_agent,
            'mac_address': mac_address or '',
            'boot_flag': boot_flag,
            'file_requested': '',
            'raw': line,
        }
    
    def parse_ipxe_log(self, line: str) -> dict:
        """
        解析 ipxe 容器日誌
        
        格式：10.250.53.25 - - [28/Oct/2025:10:18:57 +0000] "GET /boot.ipxe HTTP/1.1" 200 116 "-" "iPXE/1.21.1+ (g83449)" "-"
        """
        pattern = r'(\d+\.\d+\.\d+\.\d+) - - \[([^\]]+)\] "([A-Z]+) ([^\s]+) ([^"]+)" (\d+) (\d+) "-" "([^"]+)"'
        match = re.match(pattern, line)
        
        if not match:
            return None
        
        client_ip, timestamp_str, method, url, protocol, status_code, bytes_sent, user_agent = match.groups()
        
        # 解析時間
        try:
            timestamp = datetime.strptime(timestamp_str, '%d/%b/%Y:%H:%M:%S %z')
        except:
            return None
        
        # 解析請求的檔案
        file_requested = url.lstrip('/')
        
        # 判斷 action
        action = 'other'
        if 'boot.ipxe' in file_requested:
            action = 'boot.ipxe'
        elif 'wimboot' in file_requested:
            action = 'wimboot'
        elif 'BCD' in file_requested:
            action = 'BCD'
        elif 'boot.sdi' in file_requested:
            action = 'boot.sdi'
        elif '.wim' in file_requested.lower():
            action = 'wim_file'
        
        return {
            'log_type': 'boot',
            'timestamp': timestamp,
            'client_ip': client_ip,
            'method': method,
            'url': url,
            'action': action,
            'status_code': int(status_code),
            'bytes_sent': int(bytes_sent),
            'user_agent': user_agent,
            'mac_address': '',
            'boot_flag': None,
            'file_requested': file_requested,
            'raw': line,
        }
    
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
                if log_type == 'mac':
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
```

### 2. Serializers（序列化器）

檔案：`backend/api/serializers.py`

```python
from rest_framework import serializers
from .models import IPXEServer, IPXELog, IPXEStatistics

class IPXEServerSerializer(serializers.ModelSerializer):
    """IPXE 伺服器序列化器"""
    
    class Meta:
        model = IPXEServer
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at', 'last_sync_at')
        extra_kwargs = {
            'ssh_password': {'write_only': True}  # 密碼只寫不讀
        }

class IPXELogSerializer(serializers.ModelSerializer):
    """IPXE 日誌序列化器"""
    
    server_name = serializers.CharField(source='server.name', read_only=True)
    server_ip = serializers.CharField(source='server.ip_address', read_only=True)
    
    class Meta:
        model = IPXELog
        fields = '__all__'
        read_only_fields = ('created_at',)

class IPXEStatisticsSerializer(serializers.ModelSerializer):
    """IPXE 統計序列化器"""
    
    server_name = serializers.CharField(source='server.name', read_only=True)
    
    class Meta:
        model = IPXEStatistics
        fields = '__all__'
        read_only_fields = ('created_at',)
```

### 3. Views（API 視圖）

檔案：`backend/api/views.py`（新增以下內容）

```python
from rest_framework import viewsets, status
from rest_framework.decorators import api_view, action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.utils import timezone
from datetime import timedelta
from .models import IPXEServer, IPXELog, IPXEStatistics
from .serializers import IPXEServerSerializer, IPXELogSerializer, IPXEStatisticsSerializer
from .ipxe_service import IPXEService
import logging

logger = logging.getLogger(__name__)

class IPXEServerViewSet(viewsets.ModelViewSet):
    """IPXE 伺服器 API ViewSet"""
    queryset = IPXEServer.objects.all()
    serializer_class = IPXEServerSerializer
    permission_classes = [AllowAny]
    pagination_class = None

class IPXELogViewSet(viewsets.ReadOnlyModelViewSet):
    """IPXE 日誌 API ViewSet（只讀）"""
    queryset = IPXELog.objects.all()
    serializer_class = IPXELogSerializer
    permission_classes = [AllowAny]
    
    def get_queryset(self):
        """過濾查詢（最近7天）"""
        queryset = IPXELog.objects.all()
        
        # 伺服器過濾
        server_id = self.request.query_params.get('server', None)
        if server_id and server_id != 'all':
            queryset = queryset.filter(server_id=server_id)
        
        # 時間範圍過濾（預設7天）
        days = int(self.request.query_params.get('days', 7))
        start_time = timezone.now() - timedelta(days=days)
        queryset = queryset.filter(timestamp__gte=start_time)
        
        # 日誌類型過濾
        log_type = self.request.query_params.get('type', None)
        if log_type:
            queryset = queryset.filter(log_type=log_type)
        
        # 操作類型過濾
        action = self.request.query_params.get('action', None)
        if action:
            queryset = queryset.filter(action=action)
        
        # 客戶端 IP 過濾
        client_ip = self.request.query_params.get('client_ip', None)
        if client_ip:
            queryset = queryset.filter(client_ip=client_ip)
        
        # MAC 地址過濾
        mac_address = self.request.query_params.get('mac', None)
        if mac_address:
            queryset = queryset.filter(mac_address__icontains=mac_address)
        
        return queryset.order_by('-timestamp')

@api_view(['POST'])
@permission_classes([AllowAny])
def ipxe_sync_logs(request, server_id):
    """
    同步指定 IPXE Server 的日誌
    """
    try:
        server = IPXEServer.objects.get(id=server_id)
        service = IPXEService(server)
        
        # 執行同步
        limit = int(request.data.get('limit', 1000)) if request.data else 1000
        result = service.sync_logs_to_db(limit=limit)
        
        if 'error' in result:
            return Response(
                {'error': result['error']},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        logger.info(f'成功同步 IPXE Server {server.name} 的日誌: {result}')
        
        return Response({
            'message': '同步成功',
            'stats': result,
            'server': {
                'name': server.name,
                'ip': server.ip_address,
                'last_sync': server.last_sync_at.strftime('%Y-%m-%d %H:%M:%S') if server.last_sync_at else None,
            }
        })
    
    except IPXEServer.DoesNotExist:
        return Response(
            {'error': 'IPXE Server 不存在'},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        logger.error(f'同步日誌失敗: {e}', exc_info=True)
        return Response(
            {'error': f'同步失敗: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['GET'])
@permission_classes([AllowAny])
def ipxe_analytics_overview(request):
    """
    IPXE 分析 - 總覽統計
    """
    server_id = request.query_params.get('server', 'all')
    
    try:
        # 根據 server_id 篩選日誌
        if server_id == 'all':
            logs = IPXELog.objects.all()
            servers = IPXEServer.objects.all()
        else:
            logs = IPXELog.objects.filter(server_id=server_id)
            servers = IPXEServer.objects.filter(id=server_id)
        
        # 時間範圍：最近7天
        seven_days_ago = timezone.now() - timedelta(days=7)
        logs = logs.filter(timestamp__gte=seven_days_ago)
        
        # 基本統計
        total_requests = logs.count()
        mac_operations = logs.filter(log_type='mac').count()
        boot_requests = logs.filter(log_type='boot').count()
        unique_clients = logs.values('client_ip').distinct().count()
        
        # 今天的請求數
        today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
        today_requests = logs.filter(timestamp__gte=today_start).count()
        
        # 計算趨勢（與昨天相比）
        yesterday_start = today_start - timedelta(days=1)
        yesterday_requests = logs.filter(
            timestamp__gte=yesterday_start,
            timestamp__lt=today_start
        ).count()
        
        trend = 0
        if yesterday_requests > 0:
            trend = ((today_requests - yesterday_requests) / yesterday_requests) * 100
        elif today_requests > 0:
            trend = 100
        
        return Response({
            'total_requests': total_requests,
            'mac_operations': mac_operations,
            'boot_requests': boot_requests,
            'unique_clients': unique_clients,
            'today_requests': today_requests,
            'trend': round(trend, 1),
        })
    
    except Exception as e:
        logger.error(f'獲取總覽統計失敗: {e}', exc_info=True)
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
```

### 4. URLs（路由配置）

檔案：`backend/api/urls.py`（新增以下內容）

```python
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
# ... 現有路由
router.register(r'ipxe-servers', views.IPXEServerViewSet, basename='ipxe-server')
router.register(r'ipxe-logs', views.IPXELogViewSet, basename='ipxe-log')

urlpatterns = [
    path('', include(router.urls)),
    # ... 現有路由
    path('ipxe-servers/<int:server_id>/sync-logs/', views.ipxe_sync_logs, name='ipxe-sync-logs'),
    path('ipxe-analytics/overview/', views.ipxe_analytics_overview, name='ipxe-analytics-overview'),
]
```

---

## 🎨 前端設計

### 1. 頁面：IPXEManagementPage.js

**位置**：`frontend/src/pages/IPXEManagementPage.js`

**完全仿效** `DHCPServerManagementPage.js` 的結構，包含：
- ✅ 伺服器列表表格（Table）
- ✅ 新增/編輯對話框（Modal + Form）
- ✅ 刪除確認（Popconfirm）
- ✅ 同步日誌按鈕
- ✅ 狀態標籤（Tag）

**主要欄位**：
- ID
- 伺服器名稱
- IP 位址
- 狀態（Online/Offline/Warning）
- 今日請求數
- MAC 註冊數
- 開機請求數
- 上次同步時間
- 操作（編輯/刪除/同步）

### 2. 頁面：IPXEAnalyticsPage.js

**位置**：`frontend/src/pages/IPXEAnalyticsPage.js`

**完全仿效** `DHCPAnalyticsPage.js` 的結構，包含：
- ✅ 總覽統計卡片（Statistic）
- ✅ 日誌列表（Table with Pagination）
- ✅ 伺服器選擇器（Select）
- ✅ 日誌類型過濾（MAC 管理 / IPXE 開機）
- ✅ 時間範圍選擇器
- ✅ 自動刷新（每10分鐘）

**統計卡片**：
1. 總請求數
2. MAC 操作數
3. 開機請求數
4. 唯一客戶端數

**日誌表格欄位**：
- 時間
- 伺服器 IP
- 客戶端 IP
- 日誌類型（MAC/Boot）
- 操作（Set/Get/boot.ipxe/wim_file/...）
- MAC 地址（MAC 類型日誌）
- 檔案名稱（Boot 類型日誌）
- 狀態碼
- 傳輸量

### 3. 側邊欄更新

**檔案**：`frontend/src/components/Sidebar.js`

```javascript
const adminMenuItems = [
    {
        key: 'admin-group',
        type: 'group',
        label: '管理功能',
        children: [
            {
                key: 'dhcp-server-management',
                icon: <DatabaseOutlined />,
                label: 'DHCP Server 管理',
            },
            {
                key: 'ipxe-management',          // 新增
                icon: <CloudServerOutlined />,    // 新增
                label: 'IPXE 管理',               // 新增
            },
            {
                key: 'user-management',
                icon: <UserOutlined />,
                label: '用戶管理',
            },
        ],
    },
];
```

### 4. 路由配置

**檔案**：`frontend/src/App.js`

```javascript
import IPXEManagementPage from './pages/IPXEManagementPage';
import IPXEAnalyticsPage from './pages/IPXEAnalyticsPage';

// 路由添加
<Route path="/admin/ipxe-management" element={<IPXEManagementPage />} />
<Route path="/ipxe-analytics" element={<IPXEAnalyticsPage />} />
```

---

## ⏰ 定時任務設計

### 方案：使用 Cron（推薦）

**優點**：
- ✅ 簡單易用，不需額外服務
- ✅ 適合輕量級需求
- ✅ 與現有架構一致

### Management Commands

#### 1. collect_ipxe_logs.py

**位置**：`backend/api/management/commands/collect_ipxe_logs.py`

```python
from django.core.management.base import BaseCommand
from django.utils import timezone
from api.models import IPXEServer
from api.ipxe_service import IPXEService
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = '收集所有活躍 IPXE 伺服器的日誌'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--limit',
            type=int,
            default=1000,
            help='每個容器讀取的日誌行數（預設1000）'
        )
        parser.add_argument(
            '--server',
            type=int,
            help='指定伺服器 ID（可選）'
        )
    
    def handle(self, *args, **options):
        limit = options['limit']
        server_id = options.get('server')
        
        if server_id:
            servers = IPXEServer.objects.filter(id=server_id)
        else:
            servers = IPXEServer.objects.all()
        
        total_logs = 0
        success_count = 0
        
        for server in servers:
            self.stdout.write(f'正在同步 {server.name} ({server.ip_address})...')
            
            service = IPXEService(server)
            result = service.sync_logs_to_db(limit=limit)
            
            if 'error' in result:
                self.stdout.write(self.style.ERROR(f'  失敗: {result["error"]}'))
            else:
                total_logs += result['total']
                success_count += 1
                self.stdout.write(self.style.SUCCESS(
                    f'  成功: MAC={result["mac_logs"]}, Boot={result["boot_logs"]}'
                ))
        
        self.stdout.write(self.style.SUCCESS(
            f'\n完成！成功同步 {success_count}/{servers.count()} 台伺服器，共 {total_logs} 條日誌'
        ))
```

#### 2. cleanup_ipxe_logs.py

**位置**：`backend/api/management/commands/cleanup_ipxe_logs.py`

```python
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from api.models import IPXELog
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = '清理超過指定天數的 IPXE 日誌'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=7,
            help='保留天數（預設7天）'
        )
    
    def handle(self, *args, **options):
        days = options['days']
        cutoff_date = timezone.now() - timedelta(days=days)
        
        self.stdout.write(f'正在清理 {days} 天前的日誌（{cutoff_date}）...')
        
        deleted_count, _ = IPXELog.objects.filter(
            created_at__lt=cutoff_date
        ).delete()
        
        self.stdout.write(self.style.SUCCESS(
            f'成功清理 {deleted_count} 條舊日誌'
        ))
```

### Cron 配置

```bash
# 編輯 crontab
crontab -e

# 每 10 分鐘收集日誌
*/10 * * * * docker exec nt-django python manage.py collect_ipxe_logs --limit 1000

# 每天凌晨 2 點清理舊日誌
0 2 * * * docker exec nt-django python manage.py cleanup_ipxe_logs --days 7
```

---

## 📝 實現步驟（TODO）

### Phase 1：後端基礎架構
1. [ ] 創建數據模型（IPXEServer, IPXELog, IPXEStatistics）
2. [ ] 執行數據庫遷移
3. [ ] 創建 Serializers
4. [ ] 創建 IPXEService 服務類
5. [ ] 註冊 API 路由

### Phase 2：後端 API
1. [ ] 實現 IPXEServerViewSet
2. [ ] 實現 IPXELogViewSet
3. [ ] 實現同步日誌 API
4. [ ] 實現統計分析 API
5. [ ] 測試 SSH 連接和日誌解析

### Phase 3：定時任務
1. [ ] 創建 collect_ipxe_logs Management Command
2. [ ] 創建 cleanup_ipxe_logs Management Command
3. [ ] 配置 Cron 定時任務
4. [ ] 測試自動同步

### Phase 4：前端頁面
1. [ ] 創建 IPXEManagementPage.js
2. [ ] 創建 IPXEAnalyticsPage.js
3. [ ] 更新 Sidebar.js（添加菜單項）
4. [ ] 更新 App.js（添加路由）
5. [ ] 實現自動刷新（10分鐘）

### Phase 5：測試和優化
1. [ ] 測試完整流程
2. [ ] 性能優化
3. [ ] 錯誤處理完善
4. [ ] 日誌記錄完善
5. [ ] 文檔更新

---

## 📊 預期成果

### 功能清單
- ✅ 管理多台 IPXE 伺服器（CRUD）
- ✅ 透過 SSH + Docker 自動收集日誌
- ✅ 解析並存儲結構化日誌數據
- ✅ 前端顯示最近 7 天的日誌
- ✅ 每 10 分鐘自動更新日誌
- ✅ 自動清理超過 7 天的舊日誌
- ✅ 統計分析（請求量、MAC 操作、開機請求等）
- ✅ 完全仿效 DHCP Server 管理的用戶體驗

### 性能指標
- 日誌收集：每台伺服器 < 10 秒
- 日誌解析：1000 行/秒
- 頁面載入：< 2 秒
- 自動刷新：無感知

---

## 🔐 安全性考量

1. **SSH 密碼加密**：使用 Django 的加密機制存儲密碼
2. **API 權限控制**：管理功能僅限管理員
3. **SQL 注入防護**：使用 Django ORM
4. **XSS 防護**：前端輸入驗證
5. **日誌脫敏**：敏感資訊遮罩

---

## 📚 相關文檔

- [DHCP Server 管理實現](../../development/DEVELOPMENT.md)
- [定時任務配置](../scheduled-tasks/CRON_SETUP_GUIDE.md)
- [SSH 服務設計](../../SSH_WINDOWS_DHCP_SYNC.md)
- [日誌系統說明](../LOG_FILES_EXPLAINED.md)

---

**最後更新**：2025-10-29  
**狀態**：設計完成，待實現  
**估計工時**：8-12 小時
