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
    
    # DHCP Option 82 (Relay Agent Information) 欄位
    relay_agent_info = models.TextField(blank=True, verbose_name='Relay Agent Info (Option 82)')
    circuit_id = models.CharField(max_length=255, blank=True, verbose_name='Circuit ID (Switch Port)')
    remote_id = models.CharField(max_length=255, blank=True, verbose_name='Remote ID (Switch MAC/ID)')
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='建立時間')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新時間')
    
    class Meta:
        verbose_name = 'DHCP 租約'
        verbose_name_plural = 'DHCP 租約'
        ordering = ['-lease_start']
        indexes = [
            models.Index(fields=['server', 'is_active'], name='idx_lease_server_active'),
            models.Index(fields=['remote_id'], name='idx_lease_remote_id'),
            models.Index(fields=['circuit_id'], name='idx_lease_circuit_id'),
        ]
    
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
    
    # DHCP Option 82 (Relay Agent Information) 欄位
    relay_agent_info = models.TextField(blank=True, verbose_name='Relay Agent Info (Option 82)')
    circuit_id = models.CharField(max_length=255, blank=True, verbose_name='Circuit ID (Switch Port)')
    remote_id = models.CharField(max_length=255, blank=True, verbose_name='Remote ID (Switch MAC/ID)')
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='建立時間')
    
    class Meta:
        verbose_name = 'DHCP 日誌'
        verbose_name_plural = 'DHCP 日誌'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['server', '-timestamp'], name='idx_server_time'),
            models.Index(fields=['-timestamp'], name='idx_timestamp'),
            models.Index(fields=['level'], name='idx_level'),
            models.Index(fields=['remote_id'], name='idx_log_remote_id'),
            models.Index(fields=['circuit_id'], name='idx_log_circuit_id'),
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
        ('error', 'Error'),  # 新增：SSH 連接失敗或其他錯誤
        ('active', 'Active'),  # 新增：伺服器運行正常
    ]
    
    CONNECTION_STATUS_CHOICES = [
        ('pending', 'Pending'),  # 等待驗證
        ('verifying', 'Verifying'),  # 驗證中
        ('connected', 'Connected'),  # 已連接
        ('failed', 'Failed'),  # 連接失敗
        ('no_containers', 'No Containers'),  # 無容器
        ('error', 'Error'),  # 錯誤
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
    connection_status = models.CharField(
        max_length=20,
        choices=CONNECTION_STATUS_CHOICES,
        default='pending',
        verbose_name='連接狀態'
    )
    last_error = models.TextField(blank=True, null=True, verbose_name='最後錯誤訊息')
    
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


class NetworkSwitch(models.Model):
    """網路交換器模型 - 從 DHCP Option 82 識別"""
    
    STATUS_CHOICES = [
        ('active', '活躍'),
        ('inactive', '非活躍'),
        ('unknown', '未知'),
    ]
    
    # 基本資訊（從 Option 82 Remote ID 提取）
    remote_id = models.CharField(max_length=255, unique=True, verbose_name='Remote ID (識別碼)')
    name = models.CharField(max_length=200, blank=True, verbose_name='Switch 名稱')
    mac_address = models.CharField(max_length=17, blank=True, verbose_name='Switch MAC 地址')
    ip_address = models.GenericIPAddressField(null=True, blank=True, verbose_name='Switch IP 地址')
    
    # 位置資訊
    location = models.CharField(max_length=255, blank=True, verbose_name='實體位置')
    building = models.CharField(max_length=100, blank=True, verbose_name='建築物')
    floor = models.CharField(max_length=50, blank=True, verbose_name='樓層')
    
    # 狀態資訊
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='unknown',
        verbose_name='狀態'
    )
    
    # 統計資訊
    total_ports = models.IntegerField(default=0, verbose_name='總端口數')
    active_ports = models.IntegerField(default=0, verbose_name='活動端口數')
    connected_devices = models.IntegerField(default=0, verbose_name='連接設備數')
    
    # 關聯的 DHCP Server
    dhcp_server = models.ForeignKey(
        DHCPServer,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='switches',
        verbose_name='所屬 DHCP Server'
    )
    
    # 元數據
    first_seen = models.DateTimeField(auto_now_add=True, verbose_name='首次發現時間')
    last_seen = models.DateTimeField(auto_now=True, verbose_name='最後活動時間')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='建立時間')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新時間')
    
    class Meta:
        verbose_name = '網路交換器'
        verbose_name_plural = '網路交換器'
        ordering = ['-last_seen']
        indexes = [
            models.Index(fields=['remote_id'], name='idx_switch_remote_id'),
            models.Index(fields=['mac_address'], name='idx_switch_mac'),
            models.Index(fields=['status'], name='idx_switch_status'),
            models.Index(fields=['dhcp_server'], name='idx_switch_server'),
        ]
    
    def __str__(self):
        if self.name:
            return f"{self.name} ({self.remote_id})"
        return f"Switch {self.remote_id}"
    
    def update_statistics(self):
        """更新 Switch 統計資訊"""
        from django.db.models import Count, Q
        from datetime import datetime, timedelta
        
        # 計算最近 24 小時內活躍的設備
        recent_time = datetime.now() - timedelta(hours=24)
        
        # 統計活躍租約
        active_leases = DHCPLease.objects.filter(
            remote_id=self.remote_id,
            is_active=True,
            updated_at__gte=recent_time
        )
        
        self.connected_devices = active_leases.count()
        
        # 統計不同的 circuit_id（端口）
        active_circuits = active_leases.values('circuit_id').distinct().count()
        self.active_ports = active_circuits
        
        # 如果狀態是 unknown，根據活動更新狀態
        if self.status == 'unknown':
            self.status = 'active' if self.connected_devices > 0 else 'inactive'
        
        self.save()


class SwitchPort(models.Model):
    """Switch 端口模型 - 從 DHCP Option 82 Circuit ID 識別"""
    
    STATUS_CHOICES = [
        ('up', '啟用'),
        ('down', '停用'),
        ('unknown', '未知'),
    ]
    
    switch = models.ForeignKey(
        NetworkSwitch,
        on_delete=models.CASCADE,
        related_name='ports',
        verbose_name='所屬 Switch'
    )
    
    # 端口資訊（從 Circuit ID 提取）
    circuit_id = models.CharField(max_length=255, verbose_name='Circuit ID (端口識別碼)')
    port_number = models.CharField(max_length=50, blank=True, verbose_name='端口號')
    port_name = models.CharField(max_length=100, blank=True, verbose_name='端口名稱')
    
    # 狀態
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='unknown',
        verbose_name='狀態'
    )
    
    # 統計
    connected_devices = models.IntegerField(default=0, verbose_name='連接設備數')
    
    # 元數據
    first_seen = models.DateTimeField(auto_now_add=True, verbose_name='首次發現時間')
    last_seen = models.DateTimeField(auto_now=True, verbose_name='最後活動時間')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='建立時間')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新時間')
    
    class Meta:
        verbose_name = 'Switch 端口'
        verbose_name_plural = 'Switch 端口'
        unique_together = ['switch', 'circuit_id']
        ordering = ['switch', 'port_number']
        indexes = [
            models.Index(fields=['switch', 'circuit_id'], name='idx_port_switch_circuit'),
            models.Index(fields=['status'], name='idx_port_status'),
        ]
    
    def __str__(self):
        if self.port_name:
            return f"{self.switch.name} - {self.port_name}"
        return f"{self.switch.name} - {self.circuit_id}"
    
    def update_statistics(self):
        """更新端口統計資訊"""
        from datetime import datetime, timedelta
        
        recent_time = datetime.now() - timedelta(hours=24)
        
        # 統計此端口下活躍的設備
        active_count = DHCPLease.objects.filter(
            remote_id=self.switch.remote_id,
            circuit_id=self.circuit_id,
            is_active=True,
            updated_at__gte=recent_time
        ).count()
        
        self.connected_devices = active_count
        self.status = 'up' if active_count > 0 else 'down'
        self.save()


class GitLabConnection(models.Model):
    """GitLab 伺服器連線品質監控記錄"""
    
    STATUS_CHOICES = [
        ('success', 'Success'),
        ('failed', 'Failed'),
        ('timeout', 'Timeout'),
    ]
    
    # GitLab 伺服器資訊
    gitlab_url = models.CharField(max_length=200, verbose_name='GitLab 網址')
    gitlab_name = models.CharField(max_length=100, default='GitLab Server', verbose_name='伺服器名稱')
    
    # 網路連線指標
    ping_latency = models.FloatField(null=True, blank=True, verbose_name='Ping 延遲 (ms)')
    http_response_time = models.FloatField(null=True, blank=True, verbose_name='HTTP 回應時間 (秒)')
    http_status_code = models.IntegerField(null=True, blank=True, verbose_name='HTTP 狀態碼')
    
    # 連線狀態
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='failed',
        verbose_name='連線狀態'
    )
    is_reachable = models.BooleanField(default=False, verbose_name='是否可達')
    packet_loss = models.FloatField(default=0, verbose_name='封包遺失率 (%)')
    
    # 錯誤資訊
    error_message = models.TextField(blank=True, verbose_name='錯誤訊息')
    
    # 時間戳記
    checked_at = models.DateTimeField(auto_now_add=True, db_index=True, verbose_name='檢查時間')
    
    class Meta:
        verbose_name = 'GitLab 連線記錄'
        verbose_name_plural = 'GitLab 連線記錄'
        ordering = ['-checked_at']
        indexes = [
            models.Index(fields=['-checked_at'], name='idx_gitlab_checked'),
            models.Index(fields=['gitlab_url', '-checked_at'], name='idx_gitlab_url_time'),
            models.Index(fields=['status'], name='idx_gitlab_status'),
        ]
    
    def __str__(self):
        return f"{self.gitlab_name} - {self.status} @ {self.checked_at.strftime('%Y-%m-%d %H:%M')}"


# ==================== Jenkins 整合模型 ====================

class JenkinsServer(models.Model):
    """Jenkins 伺服器模型"""
    
    STATUS_CHOICES = [
        ('online', 'Online'),
        ('offline', 'Offline'),
        ('unreachable', 'Unreachable'),
    ]
    
    # 基本資訊
    name = models.CharField(max_length=200, unique=True, verbose_name='伺服器名稱')
    url = models.URLField(max_length=500, verbose_name='Jenkins URL')
    ip_address = models.GenericIPAddressField(null=True, blank=True, verbose_name='IP 位址')
    description = models.TextField(blank=True, verbose_name='描述')
    
    # 認證資訊
    username = models.CharField(max_length=100, blank=True, verbose_name='使用者名稱')
    api_token = models.CharField(max_length=500, blank=True, verbose_name='API Token')
    
    # 狀態
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='offline',
        verbose_name='狀態'
    )
    is_active = models.BooleanField(default=True, verbose_name='是否啟用')
    
    # 統計資訊
    total_jobs = models.IntegerField(default=0, verbose_name='Job 總數')
    total_builds = models.IntegerField(default=0, verbose_name='Build 總數')
    
    # 時間戳記
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='建立時間')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新時間')
    last_sync_at = models.DateTimeField(null=True, blank=True, verbose_name='上次同步時間')
    
    class Meta:
        verbose_name = 'Jenkins 伺服器'
        verbose_name_plural = 'Jenkins 伺服器'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status'], name='idx_jenkins_server_status'),
            models.Index(fields=['is_active'], name='idx_jenkins_server_active'),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.url})"


class JenkinsJob(models.Model):
    """Jenkins Job 模型"""
    
    # 關聯
    server = models.ForeignKey(
        JenkinsServer,
        on_delete=models.CASCADE,
        related_name='jobs',
        verbose_name='所屬伺服器'
    )
    
    # Job 資訊
    name = models.CharField(max_length=500, verbose_name='Job 名稱')
    full_name = models.CharField(max_length=1000, verbose_name='Job 完整路徑')
    url = models.URLField(max_length=1000, verbose_name='Job URL')
    description = models.TextField(blank=True, verbose_name='描述')
    view_name = models.CharField(max_length=200, blank=True, default='', verbose_name='所屬 View')
    
    # 狀態
    is_buildable = models.BooleanField(default=True, verbose_name='是否可構建')
    is_disabled = models.BooleanField(default=False, verbose_name='是否禁用')
    
    # 最後構建資訊
    last_build_number = models.IntegerField(null=True, blank=True, verbose_name='最後 Build 編號')
    last_build_status = models.CharField(max_length=50, blank=True, verbose_name='最後 Build 狀態')
    last_build_time = models.DateTimeField(null=True, blank=True, verbose_name='最後 Build 時間')
    
    # 統計
    total_builds = models.IntegerField(default=0, verbose_name='Build 總數')
    success_rate = models.FloatField(default=0.0, verbose_name='成功率 (%)')
    
    # 時間戳記
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='建立時間')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新時間')
    last_sync_at = models.DateTimeField(null=True, blank=True, verbose_name='上次同步時間')
    
    class Meta:
        verbose_name = 'Jenkins Job'
        verbose_name_plural = 'Jenkins Jobs'
        ordering = ['-last_build_time']
        unique_together = [['server', 'full_name']]
        indexes = [
            models.Index(fields=['server', 'name'], name='idx_jenkins_job_server_name'),
            models.Index(fields=['last_build_time'], name='idx_jenkins_job_build_time'),
        ]
    
    def __str__(self):
        return f"{self.server.name} - {self.name}"


class JenkinsBuild(models.Model):
    """Jenkins Build 記錄模型"""
    
    RESULT_CHOICES = [
        ('SUCCESS', 'Success'),
        ('FAILURE', 'Failure'),
        ('UNSTABLE', 'Unstable'),
        ('ABORTED', 'Aborted'),
        ('NOT_BUILT', 'Not Built'),
        ('BUILDING', 'Building'),
    ]
    
    # 關聯
    job = models.ForeignKey(
        JenkinsJob,
        on_delete=models.CASCADE,
        related_name='builds',
        verbose_name='所屬 Job'
    )
    
    # Build 資訊
    build_number = models.IntegerField(verbose_name='Build 編號')
    display_name = models.CharField(max_length=200, verbose_name='顯示名稱')
    url = models.URLField(max_length=1000, verbose_name='Build URL')
    
    # 狀態
    result = models.CharField(
        max_length=20,
        choices=RESULT_CHOICES,
        default='BUILDING',
        verbose_name='構建結果'
    )
    is_building = models.BooleanField(default=False, verbose_name='是否正在構建')
    duration = models.BigIntegerField(default=0, verbose_name='構建時長 (ms)')
    
    # Build 參數和配置（使用 JSONField 儲存）
    parameters = models.JSONField(default=dict, blank=True, verbose_name='Build 參數')
    ansible_config = models.JSONField(default=dict, blank=True, verbose_name='Ansible 配置')
    environment_vars = models.JSONField(default=dict, blank=True, verbose_name='環境變數')
    
    # Pipeline Stage 資訊（Blue Ocean）
    pipeline_stages = models.JSONField(default=list, blank=True, null=True, verbose_name='Pipeline Stages')
    failed_stage = models.CharField(max_length=200, blank=True, null=True, verbose_name='失敗的 Stage')
    
    # 文件路徑（NAS 上的路徑）
    config_file_path = models.CharField(max_length=1000, blank=True, verbose_name='配置文件路徑')
    log_file_path = models.CharField(max_length=1000, blank=True, verbose_name='日誌文件路徑')
    workspace_path = models.CharField(max_length=1000, blank=True, verbose_name='Workspace 存儲路徑')
    
    # Workspace 存儲資訊
    workspace_size = models.BigIntegerField(default=0, verbose_name='Workspace 大小 (bytes)')
    workspace_stored_at = models.DateTimeField(null=True, blank=True, verbose_name='Workspace 存儲時間')
    is_workspace_stored = models.BooleanField(default=False, verbose_name='是否已存儲 Workspace')
    
    # Artifacts 存儲資訊
    artifacts_path = models.CharField(max_length=1000, blank=True, verbose_name='Artifacts 存儲路徑')
    artifacts_size = models.BigIntegerField(default=0, verbose_name='Artifacts 總大小 (bytes)')
    artifacts_count = models.IntegerField(default=0, verbose_name='Artifacts 檔案數量')
    artifacts_list = models.JSONField(default=list, blank=True, verbose_name='Artifacts 檔案清單')
    artifacts_stored_at = models.DateTimeField(null=True, blank=True, verbose_name='Artifacts 存儲時間')
    is_artifacts_stored = models.BooleanField(default=False, verbose_name='是否已存儲 Artifacts')
    
    # 時間戳記
    build_timestamp = models.DateTimeField(verbose_name='構建時間')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='記錄建立時間')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='記錄更新時間')
    
    class Meta:
        verbose_name = 'Jenkins Build'
        verbose_name_plural = 'Jenkins Builds'
        ordering = ['-build_timestamp']
        unique_together = [['job', 'build_number']]
        indexes = [
            models.Index(fields=['job', '-build_number'], name='idx_jenkins_build_job_num'),
            models.Index(fields=['result'], name='idx_jenkins_build_result'),
            models.Index(fields=['-build_timestamp'], name='idx_jenkins_build_time'),
            models.Index(fields=['is_workspace_stored'], name='idx_jenkins_build_ws_stored'),
            models.Index(fields=['is_artifacts_stored'], name='idx_jenkins_build_art_stored'),
        ]
    
    def __str__(self):
        return f"{self.job.name} #{self.build_number} - {self.result}"
    
    @property
    def duration_seconds(self):
        """獲取構建時長（秒）"""
        return self.duration / 1000 if self.duration else 0


class NTPSyncLog(models.Model):
    """NTP 時間同步記錄模型 - 每5分鐘記錄一次，保留2週數據"""
    
    STATUS_CHOICES = [
        ('success', '成功'),
        ('failed', '失敗'),
    ]
    
    timestamp = models.DateTimeField(verbose_name='記錄時間', db_index=True)
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        verbose_name='同步狀態',
        db_index=True
    )
    
    # NTP 伺服器資訊
    ntp_server = models.GenericIPAddressField(verbose_name='NTP Server', default='10.10.10.51')
    
    # 同步結果
    response_time = models.FloatField(null=True, blank=True, verbose_name='響應時間 (ms)')
    offset = models.FloatField(null=True, blank=True, verbose_name='時間偏移 (ms)')
    stratum = models.IntegerField(null=True, blank=True, verbose_name='Stratum 層級')
    jitter = models.FloatField(null=True, blank=True, verbose_name='時間抖動 (ms)')
    
    # 錯誤訊息
    error_message = models.TextField(blank=True, verbose_name='錯誤訊息')
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='建立時間')
    
    class Meta:
        verbose_name = 'NTP 同步記錄'
        verbose_name_plural = 'NTP 同步記錄'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['-timestamp'], name='idx_ntp_timestamp'),
            models.Index(fields=['status'], name='idx_ntp_status'),
            models.Index(fields=['timestamp', 'status'], name='idx_ntp_time_status'),
        ]
    
    def __str__(self):
        return f"[{self.status}] {self.timestamp} - {self.ntp_server}"


class AnsibleInventoryImport(models.Model):
    """Ansible Inventory 導入記錄"""
    
    STATUS_CHOICES = [
        ('pending', '等待導入'),
        ('importing', '導入中'),
        ('success', '導入成功'),
        ('failed', '導入失敗'),
    ]
    
    # 基本資訊
    nas_path = models.CharField(max_length=500, verbose_name='NAS 路徑')
    file_name = models.CharField(max_length=255, default='hosts', verbose_name='檔案名稱')
    
    # 導入狀態
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name='狀態'
    )
    
    # 語法驗證結果
    syntax_valid = models.BooleanField(default=False, verbose_name='語法有效')
    syntax_error = models.TextField(blank=True, null=True, verbose_name='語法錯誤訊息')
    
    # 統計資訊
    total_hosts = models.IntegerField(default=0, verbose_name='總 Host 數量')
    total_groups = models.IntegerField(default=0, verbose_name='總 Group 數量')
    
    # 編輯鎖定（防止多人同時編輯）
    is_locked = models.BooleanField(default=False, verbose_name='編輯鎖定')
    locked_by = models.ForeignKey(
        'auth.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='locked_inventories',
        verbose_name='鎖定者'
    )
    locked_at = models.DateTimeField(null=True, blank=True, verbose_name='鎖定時間')
    
    # 當前版本
    current_version = models.IntegerField(default=1, verbose_name='當前版本號')
    
    # 時間戳記
    imported_at = models.DateTimeField(auto_now_add=True, verbose_name='導入時間')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新時間')
    imported_by = models.ForeignKey(
        'auth.User',
        on_delete=models.SET_NULL,
        null=True,
        related_name='imported_inventories',
        verbose_name='導入者'
    )
    
    class Meta:
        db_table = 'ansible_inventory_import'
        verbose_name = 'Ansible Inventory 導入'
        verbose_name_plural = 'Ansible Inventory 導入記錄'
        ordering = ['-imported_at']
    
    def __str__(self):
        return f"{self.nas_path}/{self.file_name} - {self.status}"


class AnsibleHostConfig(models.Model):
    """Ansible Host 配置"""
    
    VALIDATION_STATUS_CHOICES = [
        ('not_checked', '未檢查'),
        ('passed', '通過'),
        ('failed', '失敗'),
        ('warning', '警告'),
    ]
    
    # 關聯到導入記錄
    inventory = models.ForeignKey(
        AnsibleInventoryImport,
        on_delete=models.CASCADE,
        related_name='hosts',
        verbose_name='所屬 Inventory'
    )
    
    # Host 基本資訊
    hostname = models.CharField(max_length=255, verbose_name='主機名稱')
    groups = models.JSONField(default=list, verbose_name='所屬 Groups')
    
    # Ansible 變數
    ansible_host = models.CharField(max_length=255, blank=True, null=True, verbose_name='IP 地址')
    ansible_user = models.CharField(max_length=100, blank=True, null=True, verbose_name='SSH 使用者')
    ansible_password = models.CharField(max_length=255, blank=True, null=True, verbose_name='SSH 密碼')
    ansible_port = models.IntegerField(default=22, verbose_name='SSH 端口')
    
    # 自訂變數
    mac_address = models.CharField(max_length=17, blank=True, null=True, verbose_name='MAC 地址')
    uart_host = models.CharField(max_length=255, blank=True, null=True, verbose_name='UART 主機')
    
    # 其他所有變數存為 JSON
    other_vars = models.JSONField(default=dict, verbose_name='其他變數')
    
    # 配置驗證結果
    validation_status = models.CharField(
        max_length=20,
        choices=VALIDATION_STATUS_CHOICES,
        default='not_checked',
        verbose_name='驗證狀態'
    )
    validation_results = models.JSONField(default=dict, verbose_name='驗證結果')
    
    # 最後驗證時間
    last_validated_at = models.DateTimeField(null=True, blank=True, verbose_name='最後驗證時間')
    
    # 時間戳記
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='創建時間')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新時間')
    
    class Meta:
        db_table = 'ansible_host_config'
        verbose_name = 'Ansible Host 配置'
        verbose_name_plural = 'Ansible Host 配置'
        ordering = ['hostname']
        unique_together = [['inventory', 'hostname']]
    
    def __str__(self):
        return f"{self.hostname} ({self.ansible_host})"


class InventoryVersion(models.Model):
    """Inventory 文件版本記錄"""
    
    # 關聯到導入記錄
    inventory = models.ForeignKey(
        AnsibleInventoryImport,
        on_delete=models.CASCADE,
        related_name='versions',
        verbose_name='所屬 Inventory'
    )
    
    # 版本資訊
    version_number = models.IntegerField(verbose_name='版本號')
    
    # 備份文件路徑
    backup_file_path = models.CharField(max_length=500, verbose_name='備份檔案路徑')
    
    # 文件內容快照（可選，用於快速預覽）
    content_snapshot = models.TextField(blank=True, null=True, verbose_name='內容快照')
    
    # 變更摘要
    change_summary = models.TextField(blank=True, null=True, verbose_name='變更摘要')
    
    # 時間和操作者
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='創建時間')
    created_by = models.ForeignKey(
        'auth.User',
        on_delete=models.SET_NULL,
        null=True,
        verbose_name='創建者'
    )
    
    class Meta:
        db_table = 'inventory_version'
        verbose_name = 'Inventory 版本'
        verbose_name_plural = 'Inventory 版本記錄'
        ordering = ['-version_number']
        unique_together = [['inventory', 'version_number']]
    
    def __str__(self):
        return f"{self.inventory.file_name} v{self.version_number}"


class InventoryEditLog(models.Model):
    """Inventory 編輯操作日誌"""
    
    ACTION_CHOICES = [
        ('import', '導入'),
        ('edit', '編輯'),
        ('save', '儲存'),
        ('rollback', '回滾'),
        ('validate', '驗證'),
    ]
    
    # 關聯
    inventory = models.ForeignKey(
        AnsibleInventoryImport,
        on_delete=models.CASCADE,
        related_name='edit_logs',
        verbose_name='所屬 Inventory'
    )
    
    host_config = models.ForeignKey(
        AnsibleHostConfig,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='edit_logs',
        verbose_name='相關 Host'
    )
    
    # 操作類型
    action = models.CharField(
        max_length=20,
        choices=ACTION_CHOICES,
        verbose_name='操作類型'
    )
    
    # 變更詳情
    changes = models.JSONField(default=dict, verbose_name='變更內容')
    
    # 操作結果
    success = models.BooleanField(default=True, verbose_name='操作成功')
    error_message = models.TextField(blank=True, null=True, verbose_name='錯誤訊息')
    
    # 時間和操作者
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='操作時間')
    created_by = models.ForeignKey(
        'auth.User',
        on_delete=models.SET_NULL,
        null=True,
        verbose_name='操作者'
    )
    
    # IP 地址（追蹤來源）
    ip_address = models.GenericIPAddressField(blank=True, null=True, verbose_name='來源 IP')
    
    class Meta:
        db_table = 'inventory_edit_log'
        verbose_name = 'Inventory 編輯日誌'
        verbose_name_plural = 'Inventory 編輯日誌'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.action} by {self.created_by} at {self.created_at}"
