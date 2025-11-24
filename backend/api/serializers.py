from rest_framework import serializers
from django.contrib.auth.models import User
from django.utils import timezone as django_timezone
from .models import (
    DHCPServer, DHCPLease, DHCPLog, NASConnectionLog, NTPSyncLog, NTPSyncOperation,
    IPXEServer, IPXELog, IPXEStatistics, IPXENetworkQuality,
    NetworkSwitch, SwitchPort, GitLabConnection,
    JenkinsServer, JenkinsJob, JenkinsBuild,
    AnsibleInventoryImport, AnsibleHostConfig, InventoryVersion, InventoryEditLog
)



class UserSerializer(serializers.ModelSerializer):
    """用戶序列化器"""
    password = serializers.CharField(write_only=True, required=False)
    
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'first_name', 'last_name', 
                  'is_active', 'is_staff', 'is_superuser', 'date_joined', 'password')
        read_only_fields = ('date_joined',)
    
    def create(self, validated_data):
        password = validated_data.pop('password', None)
        user = User(**validated_data)
        if password:
            user.set_password(password)
        user.save()
        return user
    
    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if password:
            instance.set_password(password)
        instance.save()
        return instance


class DHCPServerSerializer(serializers.ModelSerializer):
    class Meta:
        model = DHCPServer
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at')


class DHCPLeaseSerializer(serializers.ModelSerializer):
    server_name = serializers.CharField(source='server.name', read_only=True)
    vendor = serializers.SerializerMethodField()
    
    def get_vendor(self, obj):
        """獲取 MAC 地址對應的製造商"""
        from .utils.mac_vendor import get_vendor_from_mac
        return get_vendor_from_mac(obj.mac_address)
    
    class Meta:
        model = DHCPLease
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at')


class DHCPLogSerializer(serializers.ModelSerializer):
    """DHCP 日誌序列化器"""
    
    server_name = serializers.CharField(source='server.name', read_only=True)
    server_ip = serializers.CharField(source='server.ip_address', read_only=True)
    
    # 添加客戶端類型的顯示名稱
    client_type_display = serializers.CharField(source='get_client_type_display', read_only=True)
    
    # ✅ 自訂序列化方法，將 UTC 轉換為 Taipei 時區
    timestamp = serializers.SerializerMethodField()
    
    def get_timestamp(self, obj):
        """將 UTC 時間轉換為當前時區（Asia/Taipei）"""
        if obj.timestamp:
            # 轉換為當前時區
            local_time = django_timezone.localtime(obj.timestamp)
            # 格式化輸出
            return local_time.strftime('%Y-%m-%d %H:%M:%S')
        return None
    
    class Meta:
        model = DHCPLog
        fields = '__all__'
        read_only_fields = ('created_at',)


class NASConnectionLogSerializer(serializers.ModelSerializer):
    """NAS 連線記錄序列化器"""
    
    # ✅ 自訂序列化方法，將 UTC 轉換為 Taipei 時區
    timestamp = serializers.SerializerMethodField()
    
    def get_timestamp(self, obj):
        """將 UTC 時間轉換為當前時區（Asia/Taipei）"""
        if obj.timestamp:
            # 轉換為當前時區
            local_time = django_timezone.localtime(obj.timestamp)
            # 格式化輸出
            return local_time.strftime('%Y-%m-%d %H:%M:%S')
        return None
    
    class Meta:
        model = NASConnectionLog
        fields = '__all__'
        read_only_fields = ('created_at',)


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


class IPXENetworkQualitySerializer(serializers.ModelSerializer):
    """IPXE 網路品質序列化器"""
    
    server_name = serializers.CharField(source='server.name', read_only=True)
    server_ip = serializers.CharField(source='server.ip_address', read_only=True)
    
    class Meta:
        model = IPXENetworkQuality
        fields = '__all__'
        read_only_fields = ('created_at',)


class SwitchPortSerializer(serializers.ModelSerializer):
    """Switch 端口序列化器"""
    
    switch_name = serializers.CharField(source='switch.name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = SwitchPort
        fields = '__all__'
        read_only_fields = ('first_seen', 'last_seen', 'created_at', 'updated_at')


class NetworkSwitchSerializer(serializers.ModelSerializer):
    """網路交換器序列化器"""
    
    dhcp_server_name = serializers.CharField(source='dhcp_server.name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    ports_count = serializers.SerializerMethodField()
    
    def get_ports_count(self, obj):
        """獲取端口數量"""
        return obj.ports.count()
    
    class Meta:
        model = NetworkSwitch
        fields = '__all__'
        read_only_fields = ('first_seen', 'last_seen', 'created_at', 'updated_at')


class NetworkSwitchDetailSerializer(serializers.ModelSerializer):
    """網路交換器詳細資訊序列化器（包含端口列表）"""
    
    dhcp_server_name = serializers.CharField(source='dhcp_server.name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    ports = SwitchPortSerializer(many=True, read_only=True)
    
    # 統計資訊
    recent_devices = serializers.SerializerMethodField()
    
    def get_recent_devices(self, obj):
        """獲取最近 24 小時連接的設備列表"""
        from datetime import datetime, timedelta
        recent_time = datetime.now() - timedelta(hours=24)
        
        leases = DHCPLease.objects.filter(
            remote_id=obj.remote_id,
            is_active=True,
            updated_at__gte=recent_time
        ).select_related('server')
        
        return DHCPLeaseSerializer(leases, many=True).data
    
    class Meta:
        model = NetworkSwitch
        fields = '__all__'
        read_only_fields = ('first_seen', 'last_seen', 'created_at', 'updated_at')



class GitLabConnectionSerializer(serializers.ModelSerializer):
    """GitLab 連線品質記錄序列化器"""
    
    class Meta:
        model = GitLabConnection
        fields = '__all__'
        read_only_fields = ('checked_at',)


# ==================== Jenkins Serializers ====================

class JenkinsServerSerializer(serializers.ModelSerializer):
    """Jenkins 伺服器序列化器"""
    
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    jobs_count = serializers.SerializerMethodField()
    total_builds = serializers.SerializerMethodField()
    
    def get_jobs_count(self, obj):
        """獲取 Job 數量"""
        return obj.jobs.count()
    
    def get_total_builds(self, obj):
        """獲取總 Build 數量"""
        return JenkinsBuild.objects.filter(job__server=obj).count()
    
    class Meta:
        model = JenkinsServer
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at', 'last_sync_at')
        extra_kwargs = {
            'api_token': {'write_only': True},  # API Token 只寫不讀
        }


class JenkinsJobSerializer(serializers.ModelSerializer):
    """Jenkins Job 序列化器"""
    
    server_name = serializers.CharField(source='server.name', read_only=True)
    server_url = serializers.CharField(source='server.url', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    builds_count = serializers.SerializerMethodField()
    last_build_info = serializers.SerializerMethodField()
    last_build_time = serializers.DateTimeField(format='iso-8601', read_only=True)
    
    def get_builds_count(self, obj):
        """獲取 Build 數量"""
        return obj.builds.count()
    
    def get_last_build_info(self, obj):
        """獲取最後一次 Build 資訊"""
        last_build = obj.builds.order_by('-build_number').first()
        if last_build:
            return {
                'build_number': last_build.build_number,
                'status': last_build.result or 'UNKNOWN',
                'build_timestamp': last_build.build_timestamp,
                'duration': last_build.duration,
            }
        return None
    
    class Meta:
        model = JenkinsJob
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at')


class JenkinsBuildSerializer(serializers.ModelSerializer):
    """Jenkins Build 序列化器"""
    
    job_name = serializers.CharField(source='job.name', read_only=True)
    server_name = serializers.CharField(source='job.server.name', read_only=True)
    status = serializers.CharField(source='result', read_only=True)  # 使用 result 字段作為 status
    duration_formatted = serializers.SerializerMethodField()
    has_pipeline_stages = serializers.SerializerMethodField()
    failed_stages_count = serializers.SerializerMethodField()
    
    def get_duration_formatted(self, obj):
        """格式化執行時間"""
        if not obj.duration:
            return None
        
        seconds = int(obj.duration)
        if seconds < 60:
            return f"{seconds}s"
        elif seconds < 3600:
            minutes = seconds // 60
            secs = seconds % 60
            return f"{minutes}m {secs}s"
        else:
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            return f"{hours}h {minutes}m"
    
    def get_has_pipeline_stages(self, obj):
        """檢查是否有 Pipeline Stage 資訊"""
        stages = self._normalize_pipeline_stages(obj)
        return bool(stages and len(stages) > 0)
    
    def get_failed_stages_count(self, obj):
        """計算失敗的 Stage 數量"""
        stages = self._normalize_pipeline_stages(obj)
        if not stages:
            return 0
        return sum(1 for s in stages if s.get('result') in ['FAILURE', 'UNSTABLE', 'ABORTED'])
    
    def _normalize_pipeline_stages(self, obj):
        """
        將 pipeline_stages 標準化為 list（向後兼容舊資料）
        
        舊資料可能是 JSON 字串，需要解析
        """
        if not obj.pipeline_stages:
            return []
        
        # 如果是字串，嘗試解析為 JSON
        if isinstance(obj.pipeline_stages, str):
            try:
                import json
                return json.loads(obj.pipeline_stages)
            except:
                return []
        
        # 如果已經是 list，直接返回
        if isinstance(obj.pipeline_stages, list):
            return obj.pipeline_stages
        
        return []
    
    class Meta:
        model = JenkinsBuild
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at')


class JenkinsBuildDetailSerializer(JenkinsBuildSerializer):
    """Jenkins Build 詳細資訊序列化器（包含完整參數和配置）"""
    
    build_parameters_formatted = serializers.SerializerMethodField()
    ansible_config_formatted = serializers.SerializerMethodField()
    
    def get_build_parameters_formatted(self, obj):
        """格式化 Build 參數為易讀格式"""
        if not obj.parameters:
            return None
        
        # 將 JSON 轉換為易讀的列表格式
        params = obj.parameters
        if isinstance(params, dict):
            return [
                {'name': k, 'value': v}
                for k, v in params.items()
            ]
        return params
    
    def get_ansible_config_formatted(self, obj):
        """格式化 Ansible 配置為易讀格式"""
        if not obj.ansible_config:
            return None
        
        config = obj.ansible_config
        if isinstance(config, dict):
            return {
                'inventory': config.get('inventory'),
                'playbook': config.get('playbook'),
                'extra_vars': config.get('extra_vars'),
                'tags': config.get('tags'),
                'skip_tags': config.get('skip_tags'),
            }
        return config
    
    class Meta(JenkinsBuildSerializer.Meta):
        pass


class NTPSyncLogSerializer(serializers.ModelSerializer):
    """NTP 時間同步記錄序列化器"""
    
    # 自訂序列化方法，將 UTC 轉換為 Taipei 時區
    timestamp = serializers.SerializerMethodField()
    
    def get_timestamp(self, obj):
        """將 UTC 時間轉換為當前時區（Asia/Taipei）"""
        if obj.timestamp:
            # 轉換為當前時區
            local_time = django_timezone.localtime(obj.timestamp)
            # 格式化輸出
            return local_time.strftime('%Y-%m-%d %H:%M:%S')
        return None
    
    class Meta:
        model = NTPSyncLog
        fields = '__all__'
        read_only_fields = ('created_at',)


class NTPSyncOperationSerializer(serializers.ModelSerializer):
    """NTP 時間同步操作序列化器"""
    
    # 自訂序列化方法
    timestamp = serializers.SerializerMethodField()
    improvement_percentage = serializers.SerializerMethodField()
    status_display = serializers.SerializerMethodField()
    
    def get_timestamp(self, obj):
        """將 UTC 時間轉換為當前時區（Asia/Taipei）"""
        if obj.timestamp:
            local_time = django_timezone.localtime(obj.timestamp)
            return local_time.strftime('%Y-%m-%d %H:%M:%S')
        return None
    
    def get_improvement_percentage(self, obj):
        """獲取改善百分比"""
        return round(obj.improvement_percentage, 2)
    
    def get_status_display(self, obj):
        """獲取狀態顯示"""
        status_map = {
            'success': {'text': '成功', 'icon': '✅', 'color': 'green'},
            'failed': {'text': '失敗', 'icon': '❌', 'color': 'red'},
            'pending': {'text': '進行中', 'icon': '⏳', 'color': 'orange'},
        }
        return status_map.get(obj.status, {'text': obj.status, 'icon': '❓', 'color': 'gray'})
    
    class Meta:
        model = NTPSyncOperation
        fields = '__all__'
        read_only_fields = ('timestamp', 'improvement')


class AnsibleInventoryImportSerializer(serializers.ModelSerializer):
    """Ansible Inventory 導入記錄序列化器"""
    
    imported_by_username = serializers.CharField(source='imported_by.username', read_only=True)
    locked_by_username = serializers.CharField(source='locked_by.username', read_only=True)
    
    class Meta:
        model = AnsibleInventoryImport
        fields = '__all__'
        read_only_fields = (
            'imported_at', 'updated_at', 'status', 'syntax_valid',
            'syntax_error', 'total_hosts', 'total_groups',
            'current_version', 'is_locked', 'locked_by', 'locked_at'
        )


class AnsibleHostConfigSerializer(serializers.ModelSerializer):
    """Ansible Host 配置序列化器"""
    
    class Meta:
        model = AnsibleHostConfig
        fields = '__all__'
        read_only_fields = (
            'inventory', 'created_at', 'updated_at',
            'validation_status', 'validation_results', 'last_validated_at'
        )


class AnsibleHostConfigListSerializer(serializers.ModelSerializer):
    """Ansible Host 配置列表序列化器（簡化版）"""
    
    class Meta:
        model = AnsibleHostConfig
        fields = (
            'id', 'hostname', 'ansible_host', 'ansible_user', 'ansible_port',
            'mac_address', 'uart_host', 'groups',
            'validation_status', 'last_validated_at', 'updated_at'
        )
        read_only_fields = fields


class InventoryVersionSerializer(serializers.ModelSerializer):
    """Inventory 版本記錄序列化器"""
    
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)
    
    class Meta:
        model = InventoryVersion
        fields = '__all__'
        read_only_fields = ('created_at',)


class InventoryEditLogSerializer(serializers.ModelSerializer):
    """Inventory 編輯日誌序列化器"""
    
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)
    host_hostname = serializers.CharField(source='host_config.hostname', read_only=True)
    
    class Meta:
        model = InventoryEditLog
        fields = '__all__'
        read_only_fields = ('created_at',)
