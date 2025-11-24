from django.contrib import admin
from django.utils.html import format_html
from .models import DHCPServer, NASConnectionLog, NTPSyncLog, NTPSyncOperation

@admin.register(DHCPServer)
class DHCPServerAdmin(admin.ModelAdmin):
    list_display = ('name', 'ip_address', 'status', 'pool_usage', 'total_leases', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('name', 'ip_address', 'description')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(NASConnectionLog)
class NASConnectionLogAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'nas_ip', 'nas_share', 'status', 'response_time', 'upload_speed', 'download_speed')
    list_filter = ('status', 'timestamp')
    search_fields = ('nas_ip', 'nas_share', 'error_message')
    readonly_fields = ('created_at',)
    date_hierarchy = 'timestamp'


@admin.register(NTPSyncLog)
class NTPSyncLogAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'ntp_server', 'status', 'response_time', 'offset', 'stratum', 'jitter')
    list_filter = ('status', 'timestamp', 'ntp_server')
    search_fields = ('ntp_server', 'error_message')
    readonly_fields = ('created_at',)
    date_hierarchy = 'timestamp'


@admin.register(NTPSyncOperation)
class NTPSyncOperationAdmin(admin.ModelAdmin):
    """NTP 時間同步操作管理"""
    
    list_display = (
        'get_status_icon',
        'timestamp',
        'sync_method',
        'triggered_by',
        'offset_before',
        'offset_after',
        'get_improvement',
        'status',
        'duration',
    )
    
    list_filter = (
        'status',
        'sync_method',
        'triggered_by',
        'timestamp',
    )
    
    search_fields = (
        'ntp_server',
        'error_message',
        'sync_decision_reason',
    )
    
    readonly_fields = (
        'timestamp',
        'improvement',
        'get_improvement_percentage',
    )
    
    date_hierarchy = 'timestamp'
    
    ordering = ('-timestamp',)
    
    fieldsets = (
        ('基本資訊', {
            'fields': ('timestamp', 'ntp_server', 'sync_method', 'triggered_by')
        }),
        ('同步狀態', {
            'fields': ('status', 'offset_before', 'offset_after', 'improvement', 'get_improvement_percentage', 'duration')
        }),
        ('決策資訊', {
            'fields': ('sync_decision_reason',),
            'classes': ('collapse',)
        }),
        ('執行詳情', {
            'fields': ('command_output', 'error_message'),
            'classes': ('collapse',)
        }),
    )
    
    def get_status_icon(self, obj):
        """狀態圖標"""
        icons = {
            'success': '✅',
            'failed': '❌',
            'pending': '⏳',
        }
        return icons.get(obj.status, '❓')
    get_status_icon.short_description = '狀態'
    
    def get_improvement(self, obj):
        """改善量顯示"""
        if obj.improvement is not None:
            color = 'green' if obj.improvement > 0 else 'red'
            return format_html(
                '<span style="color: {}; font-weight: bold;">{:.2f} ms</span>',
                color,
                obj.improvement
            )
        return '-'
    get_improvement.short_description = '改善量'
    
    def get_improvement_percentage(self, obj):
        """改善百分比"""
        percentage = obj.improvement_percentage
        if percentage > 0:
            color = 'green' if percentage > 90 else 'orange' if percentage > 50 else 'red'
            return format_html(
                '<span style="color: {}; font-weight: bold;">{:.2f}%</span>',
                color,
                percentage
            )
        return '-'
    get_improvement_percentage.short_description = '改善率'


