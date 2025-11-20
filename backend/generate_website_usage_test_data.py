#!/usr/bin/env python
"""
生成網站使用統計測試數據
模擬過去7天的網站使用情況
"""

import os
import sys
import django
from datetime import date, timedelta
import random

# 設置 Django 環境
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'network_toolbox.settings')
django.setup()

from api.models import WebsiteUsageStats

def generate_test_data():
    """生成過去7天的測試數據"""
    
    print("🔄 開始生成網站使用統計測試數據...")
    
    # 刪除舊數據
    WebsiteUsageStats.objects.all().delete()
    print("✅ 已清除舊的測試數據")
    
    today = date.today()
    
    # 生成過去7天的數據
    for i in range(7, 0, -1):
        target_date = today - timedelta(days=i-1)
        
        # 隨機生成今日數據（數據隨日期遞增，模擬網站成長）
        base_multiplier = 1 + (7 - i) * 0.3  # 越接近今天，數據越大
        
        page_views = random.randint(200, 500) * base_multiplier
        unique_visitors = random.randint(30, 80)
        api_requests = random.randint(300, 800) * base_multiplier
        
        # 頁面訪問分佈
        dashboard_visits = int(page_views * random.uniform(0.3, 0.5))
        dhcp_page = int(page_views * random.uniform(0.15, 0.25))
        ipxe_page = int(page_views * random.uniform(0.1, 0.2))
        jenkins_page = int(page_views * random.uniform(0.1, 0.15))
        ansible_page = int(page_views * random.uniform(0.05, 0.15))
        
        # HTTP 方法分佈
        get_requests = int(api_requests * random.uniform(0.6, 0.75))
        post_requests = int(api_requests * random.uniform(0.15, 0.25))
        put_requests = int(api_requests * random.uniform(0.05, 0.1))
        delete_requests = api_requests - get_requests - post_requests - put_requests
        
        # 功能使用統計
        dhcp_sync = random.randint(5, 20)
        ipxe_ops = random.randint(10, 30)
        jenkins_builds = random.randint(3, 15)
        ansible_exec = random.randint(2, 10)
        
        # 錯誤統計
        errors = random.randint(5, 20)
        error_4xx = int(errors * random.uniform(0.6, 0.8))
        error_5xx = errors - error_4xx
        
        # 熱門頁面
        top_pages = {
            '/': dashboard_visits,
            '/dhcp/servers': random.randint(20, 50),
            '/dhcp/leases': random.randint(15, 40),
            '/ipxe/servers': random.randint(10, 30),
            '/jenkins/jobs': random.randint(8, 25),
        }
        
        # 熱門 API 端點
        top_api_endpoints = {
            '/api/dashboard/stats/': random.randint(50, 150),
            '/api/dhcp-servers/': random.randint(30, 80),
            '/api/dhcp-leases/': random.randint(25, 60),
            '/api/ipxe-servers/': random.randint(20, 50),
            '/api/jenkins/jobs/': random.randint(15, 40),
        }
        
        # 創建記錄
        stats = WebsiteUsageStats.objects.create(
            date=target_date,
            total_page_views=int(page_views),
            unique_visitors=int(unique_visitors),
            total_api_requests=int(api_requests),
            get_requests=int(get_requests),
            post_requests=int(post_requests),
            put_requests=int(put_requests),
            delete_requests=int(delete_requests),
            dashboard_visits=dashboard_visits,
            dhcp_page_visits=dhcp_page,
            ipxe_page_visits=ipxe_page,
            jenkins_page_visits=jenkins_page,
            ansible_page_visits=ansible_page,
            dhcp_sync_count=dhcp_sync,
            ipxe_operations=ipxe_ops,
            jenkins_builds=jenkins_builds,
            ansible_executions=ansible_exec,
            error_count=errors,
            error_4xx=error_4xx,
            error_5xx=error_5xx,
            top_pages=top_pages,
            top_api_endpoints=top_api_endpoints,
        )
        
        print(f"✅ {target_date}: 頁面瀏覽 {int(page_views)}, API請求 {int(api_requests)}, 訪客 {int(unique_visitors)}")
    
    # 顯示統計摘要
    total_stats = WebsiteUsageStats.objects.all()
    total_page_views = sum(s.total_page_views for s in total_stats)
    total_api_requests = sum(s.total_api_requests for s in total_stats)
    
    print("\n" + "="*60)
    print("📊 測試數據生成完成！")
    print("="*60)
    print(f"📅 生成天數: 7 天")
    print(f"📄 總頁面瀏覽: {total_page_views:,}")
    print(f"🔌 總 API 請求: {total_api_requests:,}")
    print(f"📈 今日頁面瀏覽: {total_stats.last().total_page_views}")
    print(f"📈 今日 API 請求: {total_stats.last().total_api_requests}")
    print(f"👥 今日訪客數: {total_stats.last().unique_visitors}")
    print("="*60)
    print("\n✨ 現在可以訪問 http://localhost/ 查看 Dashboard！")

if __name__ == '__main__':
    generate_test_data()
