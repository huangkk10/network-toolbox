"""
iPXE 日誌管理 Views
從 DHCPLog 表讀取 iPXE 相關日誌（PXE, iPXE, WinPE）
"""

from rest_framework import viewsets, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.utils import timezone
from django.db.models import Q
from datetime import timedelta
from ..models import DHCPLog
from ..serializers import DHCPLogSerializer
import logging
import re

logger = logging.getLogger(__name__)


class IPXELogViewSet(viewsets.ReadOnlyModelViewSet):
    """IPXE 日誌查詢 API ViewSet（只讀）- 從 DHCPLog 表讀取 iPXE 相關日誌"""
    queryset = DHCPLog.objects.filter(
        client_type__in=['PXE', 'iPXE', 'WinPE']
    ).order_by('-timestamp')
    serializer_class = DHCPLogSerializer
    permission_classes = [AllowAny]
    pagination_class = None  # 禁用分頁

    def get_queryset(self):
        """支援篩選參數"""
        # 基礎查詢：只查詢 iPXE 相關的日誌（PXE, iPXE, WinPE）
        queryset = DHCPLog.objects.filter(
            client_type__in=['PXE', 'iPXE', 'WinPE']
        ).select_related('server')
        
        # 依 server_id 篩選
        server_id = self.request.query_params.get('server_id', None)
        if server_id and server_id != 'all':
            queryset = queryset.filter(server_id=server_id)
        
        # 依 log_type 篩選（映射到 client_type）
        log_type = self.request.query_params.get('log_type', None)
        if log_type:
            if log_type == 'BOOT':
                queryset = queryset.filter(client_type__in=['PXE', 'iPXE', 'WinPE'])
        
        # 搜尋功能（支援 message、raw）
        search = self.request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                Q(message__icontains=search) |
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

    def list(self, request, *args, **kwargs):
        """列出 IPXE 日誌 - 從 DHCPLog 讀取並轉換格式"""
        try:
            queryset = self.get_queryset()
            
            # 轉換 DHCPLog 格式為前端需要的格式
            logs_data = []
            for log in queryset:
                # 提取 IP 和 MAC（從 message 或 raw 中）
                client_ip = ''
                mac_address = ''
                
                # 嘗試從 message 提取 IP
                ip_match = re.search(r'\b(?:\d{1,3}\.){3}\d{1,3}\b', log.message)
                if ip_match:
                    client_ip = ip_match.group(0)
                
                # 嘗試從 raw 提取 MAC 地址
                mac_match = re.search(r'\b(?:[0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}\b', log.raw)
                if mac_match:
                    mac_address = mac_match.group(0)
                
                logs_data.append({
                    'id': log.id,
                    'timestamp': log.timestamp,
                    'log_type': 'BOOT',  # iPXE 相關都歸類為 BOOT
                    'action': log.client_type.lower(),  # PXE, iPXE, WinPE
                    'client_ip': client_ip,
                    'mac_address': mac_address,
                    'status_code': 200 if log.level == 'INFO' else 500,
                    'raw': log.raw,
                    'server_ip': log.server.ip_address,
                    'server_name': log.server.name,
                    'message': log.message,
                    'client_type': log.client_type,
                    'boot_stage': log.boot_stage,
                })
            
            logger.info(f'成功獲取 {len(logs_data)} 條 IPXE 日誌（從 DHCPLog）')
            return Response(logs_data)
        except Exception as e:
            logger.error(f'獲取 IPXE 日誌失敗: {str(e)}', exc_info=True)
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
