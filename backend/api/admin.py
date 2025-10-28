from django.contrib import admin
from .models import DHCPServer, NASConnectionLog

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
