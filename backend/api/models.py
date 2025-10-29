from django.db import models


class DHCPServer(models.Model):
    """DHCP Server 模型"""
    
    STATUS_CHOICES = [
        ('online', 'Online'),
        ('offline', 'Offline'),
        ('warning', 'Warning'),
    ]
    
    name = models.CharField(max_length=200, verbose_name='伺服器名稱')
    ip_address = models.GenericIPAddressField(verbose_name='IP 位址')
    description = models.TextField(blank=True, verbose_name='描述')
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='offline',
        verbose_name='狀態'
    )
    pool_usage = models.FloatField(default=0.0, verbose_name='池使用率 (%)')
    total_leases = models.IntegerField(default=0, verbose_name='總租約數')
    active_leases = models.IntegerField(default=0, verbose_name='活動租約數')
    
    # SSH 連接設定
    ssh_port = models.IntegerField(default=22, verbose_name='SSH 連接埠')
    ssh_username = models.CharField(max_length=100, default='root', verbose_name='SSH 使用者名稱')
    ssh_password = models.CharField(max_length=255, blank=True, verbose_name='SSH 密碼')
    ssh_key_file = models.CharField(max_length=500, blank=True, verbose_name='SSH 金鑰檔案路徑')
    
    # DHCP 設定檔路徑
    dhcp_leases_path = models.CharField(
        max_length=500, 
        default='/var/lib/dhcp/dhcpd.leases',
        verbose_name='DHCP Leases 檔案路徑'
    )
    dhcp_config_path = models.CharField(
        max_length=500,
        default='/etc/dhcp/dhcpd.conf',
        verbose_name='DHCP 設定檔路徑'
    )
    
    # 元數據
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='建立時間')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新時間')
    last_sync_at = models.DateTimeField(null=True, blank=True, verbose_name='上次同步時間')
    
    class Meta:
        verbose_name = 'DHCP 伺服器'
        verbose_name_plural = 'DHCP 伺服器'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.name} ({self.ip_address})"


class DHCPLease(models.Model):
    """DHCP 租約模型"""
    
    server = models.ForeignKey(
        DHCPServer,
        on_delete=models.CASCADE,
        related_name='leases',
        verbose_name='所屬伺服器'
    )
    ip_address = models.GenericIPAddressField(verbose_name='IP 位址')
    mac_address = models.CharField(max_length=17, verbose_name='MAC 位址')
    hostname = models.CharField(max_length=255, blank=True, verbose_name='主機名稱')
    lease_start = models.DateTimeField(verbose_name='租約開始時間')
    lease_end = models.DateTimeField(verbose_name='租約結束時間')
    is_active = models.BooleanField(default=True, verbose_name='是否活動')
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='建立時間')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新時間')
    
    class Meta:
        verbose_name = 'DHCP 租約'
        verbose_name_plural = 'DHCP 租約'
        ordering = ['-lease_start']
    
    def __str__(self):
        return f"{self.ip_address} - {self.mac_address}"


class DHCPScope(models.Model):
    """DHCP Scope 模型 - 儲存 IP 範圍和使用率資訊"""
    
    STATE_CHOICES = [
        ('Active', '啟用'),
        ('Inactive', '停用'),
    ]
    
    server = models.ForeignKey(
        DHCPServer,
        on_delete=models.CASCADE,
        related_name='scopes',
        verbose_name='所屬伺服器'
    )
    scope_id = models.CharField(max_length=45, verbose_name='Scope ID')  # IPv4/IPv6 地址字串
    name = models.CharField(max_length=255, verbose_name='Scope 名稱')
    subnet_mask = models.CharField(max_length=45, verbose_name='子網路遮罩')
    start_range = models.CharField(max_length=45, verbose_name='起始 IP')
    end_range = models.CharField(max_length=45, verbose_name='結束 IP')
    state = models.CharField(
        max_length=20,
        choices=STATE_CHOICES,
        default='Active',
        verbose_name='狀態'
    )
    lease_duration = models.CharField(max_length=50, blank=True, verbose_name='租約期限')
    
    # 使用率統計
    total_addresses = models.IntegerField(default=0, verbose_name='總 IP 數')
    in_use_addresses = models.IntegerField(default=0, verbose_name='已使用 IP 數')
    available_addresses = models.IntegerField(default=0, verbose_name='可用 IP 數')
    usage_percentage = models.FloatField(default=0.0, verbose_name='使用率 (%)')
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='建立時間')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新時間')
    
    class Meta:
        verbose_name = 'DHCP Scope'
        verbose_name_plural = 'DHCP Scopes'
        unique_together = ['server', 'scope_id']  # 同一 Server 下 Scope ID 唯一
        ordering = ['server', 'scope_id']
        indexes = [
            models.Index(fields=['server', 'scope_id'], name='idx_server_scope'),
            models.Index(fields=['state'], name='idx_scope_state'),
        ]
    
    def __str__(self):
        return f"{self.scope_id} - {self.name} ({self.usage_percentage:.1f}%)"


class DHCPLog(models.Model):
    """DHCP 日誌模型 - 15天滾動視窗"""
    
    LEVEL_CHOICES = [
        ('INFO', 'Information'),
        ('WARN', 'Warning'),
        ('ERROR', 'Error'),
        ('DEBUG', 'Debug'),
    ]
    
    CLIENT_TYPE_CHOICES = [
        ('iPXE', 'iPXE'),
        ('PXE', 'PXE (BIOS)'),
        ('WinPE', 'Windows PE'),
        ('OS', 'Operating System'),
        ('Unknown', 'Unknown'),
    ]
    
    server = models.ForeignKey(
        DHCPServer,
        on_delete=models.CASCADE,
        related_name='logs',
        verbose_name='所屬伺服器'
    )
    timestamp = models.DateTimeField(verbose_name='日誌時間', db_index=True)
    level = models.CharField(
        max_length=10,
        choices=LEVEL_CHOICES,
        default='INFO',
        verbose_name='日誌等級',
        db_index=True
    )
    event = models.CharField(max_length=30, blank=True, verbose_name='事件類型')
    message = models.CharField(max_length=200, verbose_name='訊息')
    raw = models.TextField(verbose_name='原始日誌')
    
    # iPXE 識別相關欄位
    client_type = models.CharField(
        max_length=20,
        choices=CLIENT_TYPE_CHOICES,
        default='Unknown',
        verbose_name='客戶端類型',
        db_index=True
    )
    boot_stage = models.CharField(max_length=50, blank=True, verbose_name='啟動階段')
    vendor_class = models.CharField(max_length=500, blank=True, verbose_name='Vendor Class (Option 60)')
    user_class = models.CharField(max_length=200, blank=True, verbose_name='User Class (Option 77)')
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='建立時間')
    
    class Meta:
        verbose_name = 'DHCP 日誌'
        verbose_name_plural = 'DHCP 日誌'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['server', '-timestamp'], name='idx_server_time'),
            models.Index(fields=['-timestamp'], name='idx_timestamp'),
            models.Index(fields=['level'], name='idx_level'),
        ]
    
    def __str__(self):
        return f"[{self.level}] {self.timestamp} - {self.message[:50]}"


class NASConnectionLog(models.Model):
    """NAS 連線記錄模型 - 每5分鐘記錄一次，保留2週數據"""
    
    STATUS_CHOICES = [
        ('success', '成功'),
        ('failed', '失敗'),
    ]
    
    timestamp = models.DateTimeField(verbose_name='記錄時間', db_index=True)
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        verbose_name='連線狀態',
        db_index=True
    )
    
    # 連線資訊
    nas_ip = models.GenericIPAddressField(verbose_name='NAS IP')
    nas_share = models.CharField(max_length=100, verbose_name='共享名稱')
    
    # 效能測試結果（可選）
    response_time = models.FloatField(null=True, blank=True, verbose_name='響應時間 (ms)')
    upload_speed = models.FloatField(null=True, blank=True, verbose_name='上傳速度 (MB/s)')
    download_speed = models.FloatField(null=True, blank=True, verbose_name='下載速度 (MB/s)')
    
    # 錯誤訊息
    error_message = models.TextField(blank=True, verbose_name='錯誤訊息')
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='建立時間')
    
    class Meta:
        verbose_name = 'NAS 連線記錄'
        verbose_name_plural = 'NAS 連線記錄'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['-timestamp'], name='idx_nas_timestamp'),
            models.Index(fields=['status'], name='idx_nas_status'),
            models.Index(fields=['timestamp', 'status'], name='idx_nas_time_status'),
        ]
    
    def __str__(self):
        return f"[{self.status}] {self.timestamp} - {self.nas_ip}/{self.nas_share}"


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
    ssh_password = models.CharField(max_length=255, verbose_name='SSH 密碼')
    
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


class IPXELog(models.Model):
    """IPXE 日誌模型 - 15天滾動視窗"""
    
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
    boot_flag = models.IntegerField(null=True, blank=True, verbose_name='BOOT 旗標')
    
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


class IPXENetworkQuality(models.Model):
    """IPXE 伺服器網路品質監控記錄 - 每5分鐘記錄一次，保留2週數據"""
    
    STATUS_CHOICES = [
        ('success', '成功'),
        ('failed', '失敗'),
    ]
    
    server = models.ForeignKey(
        IPXEServer,
        on_delete=models.CASCADE,
        related_name='network_quality_logs',
        verbose_name='所屬伺服器'
    )
    
    timestamp = models.DateTimeField(verbose_name='記錄時間', db_index=True)
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        verbose_name='連線狀態',
        db_index=True
    )
    
    # Ping 測試結果
    ping_latency = models.FloatField(null=True, blank=True, verbose_name='Ping 延遲 (ms)')
    ping_packet_loss = models.FloatField(null=True, blank=True, verbose_name='丟包率 (%)')
    
    # HTTP 測試結果
    http_response_time = models.FloatField(null=True, blank=True, verbose_name='HTTP 響應時間 (ms)')
    http_status_code = models.IntegerField(null=True, blank=True, verbose_name='HTTP 狀態碼')
    
    # SSH 測試結果（可選）
    ssh_response_time = models.FloatField(null=True, blank=True, verbose_name='SSH 響應時間 (ms)')
    ssh_connected = models.BooleanField(default=False, verbose_name='SSH 連線成功')
    
    # 下載速度測試
    download_speed = models.FloatField(null=True, blank=True, verbose_name='下載速度 (MB/s)')
    
    # 錯誤訊息
    error_message = models.TextField(blank=True, verbose_name='錯誤訊息')
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='建立時間')
    
    class Meta:
        verbose_name = 'IPXE 網路品質記錄'
        verbose_name_plural = 'IPXE 網路品質記錄'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['-timestamp'], name='idx_ipxe_nq_timestamp'),
            models.Index(fields=['server', '-timestamp'], name='idx_ipxe_nq_server_time'),
            models.Index(fields=['status'], name='idx_ipxe_nq_status'),
        ]
    
    def __str__(self):
        return f"[{self.status}] {self.timestamp} - {self.server.name} (Ping: {self.ping_latency}ms)"
