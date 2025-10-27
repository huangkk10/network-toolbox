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
