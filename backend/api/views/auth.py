"""
用戶認證相關 Views
包含用戶註冊、登入、密碼重設
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.contrib.auth.models import User
from ..serializers import UserSerializer
import logging

logger = logging.getLogger(__name__)


class UserViewSet(viewsets.ModelViewSet):
    """用戶管理 API ViewSet"""
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [AllowAny]  # 開發階段允許所有請求，生產環境應改為 IsAdminUser
    pagination_class = None  # 禁用分頁，直接返回所有用戶
    
    @action(detail=False, methods=['post'], permission_classes=[AllowAny])
    def register(self, request):
        """用戶註冊"""
        username = request.data.get('username')
        email = request.data.get('email')
        password = request.data.get('password')
        
        # 驗證必填欄位
        if not username or not password:
            return Response(
                {'error': '用戶名和密碼為必填項'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 檢查用戶名是否已存在
        if User.objects.filter(username=username).exists():
            return Response(
                {'error': '該用戶名已被使用'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 檢查郵箱是否已存在
        if email and User.objects.filter(email=email).exists():
            return Response(
                {'error': '該郵箱已被使用'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 創建用戶
        try:
            user = User.objects.create_user(
                username=username,
                email=email or '',
                password=password
            )
            return Response({
                'message': '註冊成功！',
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'is_staff': user.is_staff
                }
            }, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response(
                {'error': f'註冊失敗：{str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['post'], permission_classes=[AllowAny])
    def login(self, request):
        """用戶登入"""
        from django.contrib.auth import authenticate
        
        username = request.data.get('username')
        password = request.data.get('password')
        
        if not username or not password:
            return Response(
                {'error': '用戶名和密碼為必填項'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 驗證用戶
        user = authenticate(username=username, password=password)
        
        if user is None:
            return Response(
                {'error': '用戶名或密碼錯誤'}, 
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        return Response({
            'message': '登入成功！',
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'is_staff': user.is_staff
            }
        })
    
    @action(detail=True, methods=['post'])
    def reset_password(self, request, pk=None):
        """重設用戶密碼"""
        user = self.get_object()
        new_password = request.data.get('password')
        if not new_password:
            return Response(
                {'error': '請提供新密碼'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        user.set_password(new_password)
        user.save()
        return Response({'message': '密碼重設成功'})
