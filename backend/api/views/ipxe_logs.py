"""
iPXE 日誌管理 Views
從 IPXELog 表讀取真正的 iPXE 容器日誌（Nginx access log 格式）
"""

from rest_framework import viewsets, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.utils import timezone
from django.db.models import Q
from datetime import timedelta
from ..models import IPXELog
from ..serializers import IPXELogSerializer
import logging

logger = logging.getLogger(__name__)


class IPXELogViewSet(viewsets.ReadOnlyModelViewSet):
    """IPXE 日誌查詢 API ViewSet（只讀）- 從 IPXELog 表讀取 iPXE 容器日誌"""
    queryset = IPXELog.objects.all().order_by('-timestamp')
    serializer_class = IPXELogSerializer
    permission_classes = [AllowAny]
    pagination_class = None  # 禁用分頁

    def get_queryset(self):
        """支援篩選參數"""
        # 基礎查詢：從 IPXELog 表讀取
        queryset = IPXELog.objects.all().select_related('server')
        
        # 依 server_id 篩選
        server_id = self.request.query_params.get('server_id', None)
        if server_id and server_id != 'all':
            queryset = queryset.filter(server_id=server_id)
        
        # 依 log_type 篩選（MAC 或 BOOT）
        log_type = self.request.query_params.get('log_type', None)
        if log_type:
            queryset = queryset.filter(log_type=log_type)
        
        # 搜尋功能（支援 client_ip、mac_address、raw）
        search = self.request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                Q(client_ip__icontains=search) |
                Q(mac_address__icontains=search) |
                Q(file_requested__icontains=search) |
                Q(raw__icontains=search)
            )
        
        # 依時間範圍篩選（預設 7 天）
        days = self.request.query_params.get('days', 7)
        try:
            days = int(days)
            cutoff_time = timezone.now() - timedelta(days=days)
            queryset = queryset.filter(timestamp__gte=cutoff_time)
        except ValueError:
            pass
        
        # 先排序再限制數量（重要：必須先 order_by 再切片）
        queryset = queryset.order_by('-timestamp')
        
        # 限制返回數量（防止一次返回過多資料）
        limit = self.request.query_params.get('limit', None)
        if limit:
            try:
                limit = int(limit)
                queryset = queryset[:limit]
            except ValueError:
                pass
        
        return queryset
