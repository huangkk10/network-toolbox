"""
使用者活動記錄 Middleware
自動記錄每個 API 請求的使用者活動統計
"""
import logging
from django.utils import timezone
from django.db import transaction

logger = logging.getLogger(__name__)


class UserActivityMiddleware:
    """
    記錄使用者 API 請求活動的中間件
    每天為每個使用者創建一條記錄，統計當天的請求次數、方法分佈、錯誤次數等
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        # 需要排除的路徑（高頻請求，避免過度記錄）
        self.excluded_paths = [
            '/api/dashboard/stats/',  # Dashboard 輪詢
            '/api/static/',           # 靜態檔案
            '/api/media/',            # 媒體檔案
        ]
    
    def __call__(self, request):
        # 處理請求前的邏輯
        response = self.get_response(request)
        
        # 處理請求後的邏輯 - 記錄活動
        if self.should_record(request):
            self.record_activity(request, response)
        
        return response
    
    def should_record(self, request):
        """判斷是否應該記錄此請求"""
        # 只記錄 API 請求
        if not request.path.startswith('/api/'):
            return False
        
        # 排除高頻請求路徑
        for excluded in self.excluded_paths:
            if request.path.startswith(excluded):
                return False
        
        # 只記錄已登入使用者
        if not request.user.is_authenticated:
            return False
        
        return True
    
    def record_activity(self, request, response):
        """記錄使用者活動"""
        try:
            # 延遲導入避免循環依賴
            from api.models import UserActivity
            
            username = request.user.username
            today = timezone.now().date()
            method = request.method.upper()
            path = request.path
            is_error = response.status_code >= 400
            
            # 使用 atomic 確保資料一致性
            with transaction.atomic():
                # 取得或創建今天的活動記錄
                activity, created = UserActivity.objects.select_for_update().get_or_create(
                    username=username,
                    date=today,
                    defaults={
                        'total_requests': 0,
                        'get_requests': 0,
                        'post_requests': 0,
                        'put_requests': 0,
                        'delete_requests': 0,
                        'error_count': 0,
                        'top_paths': {}
                    }
                )
                
                # 更新總請求數
                activity.total_requests += 1
                
                # 更新方法統計
                if method == 'GET':
                    activity.get_requests += 1
                elif method == 'POST':
                    activity.post_requests += 1
                elif method == 'PUT':
                    activity.put_requests += 1
                elif method == 'DELETE':
                    activity.delete_requests += 1
                
                # 更新錯誤統計
                if is_error:
                    activity.error_count += 1
                
                # 更新路徑統計 (top_paths 是 JSON 欄位)
                if not activity.top_paths:
                    activity.top_paths = {}
                
                if path in activity.top_paths:
                    activity.top_paths[path] += 1
                else:
                    activity.top_paths[path] = 1
                
                # 儲存更新
                activity.save(update_fields=[
                    'total_requests', 
                    'get_requests', 
                    'post_requests', 
                    'put_requests', 
                    'delete_requests', 
                    'error_count', 
                    'top_paths'
                ])
                
                if created:
                    logger.info(f"創建新的使用者活動記錄: {username} - {today}")
                
        except Exception as e:
            # 記錄錯誤但不影響正常請求處理
            logger.error(f"記錄使用者活動時發生錯誤: {e}", exc_info=True)
