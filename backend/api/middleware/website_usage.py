"""
網站使用統計中間件
統計整個網站的總體使用次數和活動資訊
"""
import logging
from datetime import datetime
from django.utils.deprecation import MiddlewareMixin
from django.utils import timezone
from django.db import transaction
from api.models import WebsiteUsageStats

logger = logging.getLogger(__name__)


class WebsiteUsageMiddleware(MiddlewareMixin):
    """
    網站使用統計中間件
    
    統計內容：
    1. 總頁面瀏覽次數
    2. 唯一訪客數（基於 IP）
    3. API 請求次數（按 HTTP 方法分類）
    4. 各頁面訪問次數（Dashboard、DHCP、iPXE、Jenkins、Ansible）
    5. 功能使用次數（DHCP 同步、iPXE 操作、Jenkins Build、Ansible 執行）
    6. 錯誤統計（4xx、5xx）
    7. 熱門頁面和 API 端點
    """
    
    # 排除不需要統計的路徑
    EXCLUDED_PATHS = [
        '/static/',
        '/media/',
        '/favicon.ico',
    ]
    
    # 頁面路徑映射
    PAGE_MAPPING = {
        '/': 'dashboard',
        '/dhcp': 'dhcp_page',
        '/ipxe': 'ipxe_page',
        '/jenkins': 'jenkins_page',
        '/ansible': 'ansible_page',
    }
    
    # 功能操作映射
    OPERATION_MAPPING = {
        '/api/dhcp-servers/': 'dhcp_sync',
        '/api/dhcp/sync/': 'dhcp_sync',
        '/api/ipxe/': 'ipxe_operations',
        '/api/jenkins/': 'jenkins_builds',
        '/api/ansible/': 'ansible_executions',
    }
    
    def process_request(self, request):
        """記錄請求開始時間"""
        request.start_time = datetime.now()
        return None
    
    def process_response(self, request, response):
        """統計請求資訊"""
        path = request.path
        
        # 跳過排除的路徑
        if any(path.startswith(excluded) for excluded in self.EXCLUDED_PATHS):
            return response
        
        try:
            # 獲取今天的統計記錄（或創建新記錄）- 使用 Django 時區
            today = timezone.now().date()
            
            stats, created = WebsiteUsageStats.objects.get_or_create(
                date=today,
                defaults={
                    'total_page_views': 0,
                    'unique_visitors': 0,
                    'total_api_requests': 0,
                    'get_requests': 0,
                    'post_requests': 0,
                    'put_requests': 0,
                    'delete_requests': 0,
                    'dashboard_visits': 0,
                    'dhcp_page_visits': 0,
                    'ipxe_page_visits': 0,
                    'jenkins_page_visits': 0,
                    'ansible_page_visits': 0,
                    'dhcp_sync_count': 0,
                    'ipxe_operations': 0,
                    'jenkins_builds': 0,
                    'ansible_executions': 0,
                    'error_count': 0,
                    'error_4xx': 0,
                    'error_5xx': 0,
                    'top_pages': {},
                    'top_api_endpoints': {},
                    'top_users': [],
                }
            )
            
            with transaction.atomic():
                # 1. 總頁面瀏覽次數
                stats.total_page_views += 1
                
                # 2. 唯一訪客數（基於 session 或 IP）
                if not request.session.get(f'visited_today_{today}'):
                    stats.unique_visitors += 1
                    request.session[f'visited_today_{today}'] = True
                
                # 3. API 請求統計
                if path.startswith('/api/'):
                    stats.total_api_requests += 1
                    
                    # 按 HTTP 方法統計
                    method = request.method.upper()
                    if method == 'GET':
                        stats.get_requests += 1
                    elif method == 'POST':
                        stats.post_requests += 1
                    elif method == 'PUT':
                        stats.put_requests += 1
                    elif method == 'DELETE':
                        stats.delete_requests += 1
                    
                    # 統計熱門 API 端點
                    if isinstance(stats.top_api_endpoints, dict):
                        stats.top_api_endpoints[path] = stats.top_api_endpoints.get(path, 0) + 1
                        # 只保留前10名
                        if len(stats.top_api_endpoints) > 10:
                            stats.top_api_endpoints = dict(
                                sorted(stats.top_api_endpoints.items(), key=lambda x: x[1], reverse=True)[:10]
                            )
                
                # 4. 頁面訪問統計
                for page_path, field_name in self.PAGE_MAPPING.items():
                    if path == page_path or path.startswith(page_path + '/'):
                        if field_name == 'dashboard':
                            stats.dashboard_visits += 1
                        elif field_name == 'dhcp_page':
                            stats.dhcp_page_visits += 1
                        elif field_name == 'ipxe_page':
                            stats.ipxe_page_visits += 1
                        elif field_name == 'jenkins_page':
                            stats.jenkins_page_visits += 1
                        elif field_name == 'ansible_page':
                            stats.ansible_page_visits += 1
                        
                        # 統計熱門頁面
                        if isinstance(stats.top_pages, dict):
                            stats.top_pages[path] = stats.top_pages.get(path, 0) + 1
                            # 只保留前10名
                            if len(stats.top_pages) > 10:
                                stats.top_pages = dict(
                                    sorted(stats.top_pages.items(), key=lambda x: x[1], reverse=True)[:10]
                                )
                        break
                
                # 5. 功能操作統計
                for operation_path, operation_type in self.OPERATION_MAPPING.items():
                    if path.startswith(operation_path) and request.method == 'POST':
                        if operation_type == 'dhcp_sync':
                            stats.dhcp_sync_count += 1
                        elif operation_type == 'ipxe_operations':
                            stats.ipxe_operations += 1
                        elif operation_type == 'jenkins_builds':
                            stats.jenkins_builds += 1
                        elif operation_type == 'ansible_executions':
                            stats.ansible_executions += 1
                        break
                
                # 6. 錯誤統計
                status_code = response.status_code
                if status_code >= 400:
                    stats.error_count += 1
                    if 400 <= status_code < 500:
                        stats.error_4xx += 1
                    elif 500 <= status_code < 600:
                        stats.error_5xx += 1
                
                # 儲存更新
                stats.save()
            
        except Exception as e:
            logger.error(f'網站使用統計記錄失敗: {e}', exc_info=True)
        
        return response
