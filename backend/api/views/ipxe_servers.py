"""
iPXE 伺服器管理 Views
包含 iPXE 伺服器的 CRUD 操作
"""

from rest_framework import viewsets, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from ..models import IPXEServer
from ..serializers import IPXEServerSerializer
import logging

logger = logging.getLogger(__name__)


class IPXEServerViewSet(viewsets.ModelViewSet):
    """IPXE 伺服器管理 API ViewSet"""
    queryset = IPXEServer.objects.all()
    serializer_class = IPXEServerSerializer
    permission_classes = [AllowAny]  # 開發階段允許所有請求，生產環境應改為 IsAuthenticated
    pagination_class = None  # 禁用分頁

    def list(self, request, *args, **kwargs):
        """列出所有 IPXE 伺服器"""
        try:
            queryset = self.get_queryset()
            serializer = self.get_serializer(queryset, many=True)
            logger.info(f'成功獲取 {len(serializer.data)} 個 IPXE 伺服器')
            return Response(serializer.data)
        except Exception as e:
            logger.error(f'獲取 IPXE 伺服器列表失敗: {str(e)}', exc_info=True)
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def create(self, request, *args, **kwargs):
        """創建新的 IPXE 伺服器"""
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            logger.info(f"成功創建 IPXE 伺服器: {serializer.data['name']}")
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except Exception as e:
            logger.error(f'創建 IPXE 伺服器失敗: {str(e)}', exc_info=True)
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    def update(self, request, *args, **kwargs):
        """更新 IPXE 伺服器資訊"""
        try:
            instance = self.get_object()
            serializer = self.get_serializer(instance, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)
            logger.info(f"成功更新 IPXE 伺服器: {serializer.data['name']}")
            return Response(serializer.data)
        except Exception as e:
            logger.error(f'更新 IPXE 伺服器失敗: {str(e)}', exc_info=True)
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    def destroy(self, request, *args, **kwargs):
        """刪除 IPXE 伺服器"""
        try:
            instance = self.get_object()
            server_name = instance.name
            self.perform_destroy(instance)
            logger.info(f'成功刪除 IPXE 伺服器: {server_name}')
            return Response(
                {'message': f'成功刪除 IPXE 伺服器: {server_name}'},
                status=status.HTTP_204_NO_CONTENT
            )
        except Exception as e:
            logger.error(f'刪除 IPXE 伺服器失敗: {str(e)}', exc_info=True)
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
