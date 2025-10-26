from django.contrib import admin
from .models import DHCPServer

@admin.register(DHCPServer)
class DHCPServerAdmin(admin.ModelAdmin):
    list_display = ('name', 'ip_address', 'status', 'pool_usage', 'total_leases', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('name', 'ip_address', 'description')
    readonly_fields = ('created_at', 'updated_at')
