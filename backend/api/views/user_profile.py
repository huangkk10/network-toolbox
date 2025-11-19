"""
用戶個人資料管理 ViewSet
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
import logging

logger = logging.getLogger(__name__)


class UserProfileViewSet(viewsets.ViewSet):
    """用戶個人資料管理 ViewSet"""
    
    # 暫時使用 AllowAny，在方法內部檢查認證
    permission_classes = [AllowAny]
    
    @action(detail=False, methods=['get'], url_path='me')
    def get_profile(self, request):
        """
        獲取當前用戶資料
        
        GET /api/user-profile/me/
        
        Response: {
            "id": 1,
            "username": "chunwei",
            "email": "chunwei@example.com",
            "first_name": "春偉",
            "last_name": "黃",
            "date_joined": "2025-01-01T00:00:00Z",
            "last_login": "2025-11-19T08:00:00Z"
        }
        """
        # 檢查用戶是否已登入（從 localStorage）
        if not request.user or not request.user.is_authenticated:
            return Response(
                {'error': '請先登入'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        user = request.user
        return Response({
            'id': user.id,
            'username': user.username,
            'email': user.email or '',
            'first_name': user.first_name or '',
            'last_name': user.last_name or '',
            'date_joined': user.date_joined,
            'last_login': user.last_login,
        })
    
    @action(detail=False, methods=['put'], url_path='update-profile')
    def update_profile(self, request):
        """
        更新用戶基本資料
        
        PUT /api/user-profile/update-profile/
        Body: {
            "email": "new_email@example.com",
            "first_name": "新名字",
            "last_name": "新姓氏"
        }
        """
        # 檢查用戶是否已登入
        if not request.user or not request.user.is_authenticated:
            return Response(
                {'error': '請先登入'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        user = request.user
        
        # 更新允許的欄位
        if 'email' in request.data:
            user.email = request.data['email']
        if 'first_name' in request.data:
            user.first_name = request.data['first_name']
        if 'last_name' in request.data:
            user.last_name = request.data['last_name']
        
        user.save()
        logger.info(f"User {user.username} updated profile")
        
        return Response({
            'message': '個人資料更新成功',
            'user': {
                'username': user.username,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
            }
        })
    
    @action(detail=False, methods=['post'], url_path='change-password')
    def change_password(self, request):
        """
        修改密碼
        
        POST /api/user-profile/change-password/
        Body: {
            "old_password": "舊密碼",
            "new_password": "新密碼",
            "confirm_password": "確認新密碼"
        }
        
        Response (成功): {
            "message": "密碼修改成功"
        }
        
        Response (失敗): {
            "error": "錯誤訊息"
        }
        """
        # 檢查用戶是否已登入
        if not request.user or not request.user.is_authenticated:
            return Response(
                {'error': '請先登入'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        user = request.user
        old_password = request.data.get('old_password')
        new_password = request.data.get('new_password')
        confirm_password = request.data.get('confirm_password')
        
        # 驗證必要欄位
        if not all([old_password, new_password, confirm_password]):
            return Response(
                {'error': '所有欄位都是必填的'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 驗證舊密碼
        if not user.check_password(old_password):
            logger.warning(f"User {user.username} failed to change password: incorrect old password")
            return Response(
                {'error': '舊密碼不正確'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 驗證新密碼和確認密碼是否一致
        if new_password != confirm_password:
            return Response(
                {'error': '新密碼和確認密碼不一致'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 驗證新密碼不能與舊密碼相同
        if old_password == new_password:
            return Response(
                {'error': '新密碼不能與舊密碼相同'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Django 密碼強度驗證
        try:
            validate_password(new_password, user)
        except ValidationError as e:
            error_messages = list(e.messages)
            logger.warning(f"User {user.username} password validation failed: {error_messages}")
            return Response(
                {'error': error_messages},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 設置新密碼
        user.set_password(new_password)
        user.save()
        
        logger.info(f"User {user.username} changed password successfully")
        
        return Response({
            'message': '密碼修改成功，請使用新密碼重新登入'
        })
