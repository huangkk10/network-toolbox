#!/usr/bin/env python
"""
創建測試用的 GitLab 連線失敗記錄
用於測試圖表上的失敗標記功能
"""
import os
import sys
import django
from datetime import datetime, timedelta

# 設置 Django 環境
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'network_toolbox.settings')
django.setup()

from api.models import GitLabConnection
from django.utils import timezone

def create_test_failures():
    """創建多個測試失敗記錄"""
    now = timezone.now()
    
    # 創建 5 個不同時間的失敗記錄
    failure_times = [
        now - timedelta(hours=2),
        now - timedelta(hours=5),
        now - timedelta(hours=8),
        now - timedelta(hours=12),
        now - timedelta(hours=18),
    ]
    
    created_count = 0
    for failure_time in failure_times:
        # 創建失敗記錄
        GitLabConnection.objects.create(
            checked_at=failure_time,
            status='failed',
            is_reachable=False,
            ping_latency=None,
            http_response_time=None,
            http_status_code=None,
            packet_loss=100.0,
            error_message='Connection error: HTTPConnectionPool(host=\'10.252.170.11\', port=80): Max retries exceeded with url'
        )
        created_count += 1
        print(f'✓ 創建失敗記錄: {failure_time.strftime("%Y-%m-%d %H:%M")}')
    
    print(f'\n成功創建 {created_count} 筆測試失敗記錄！')
    print('請刷新前端頁面查看圖表上的紅色失敗標記。')

if __name__ == '__main__':
    create_test_failures()
