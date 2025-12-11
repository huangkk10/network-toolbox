#!/usr/bin/env python3
"""
測試唯一訪客統計修復
驗證基於 IP 地址的去重邏輯是否正常工作
"""
import os
import sys
import django
from datetime import datetime

# 設置 Django 環境
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'network_toolbox.settings')
django.setup()

from django.utils import timezone
from api.models import WebsiteUsageStats


def test_visitor_deduplication():
    """測試訪客去重邏輯"""
    print("=" * 80)
    print("🧪 測試唯一訪客去重邏輯")
    print("=" * 80)
    
    # 獲取今天的統計
    today = timezone.now().date()
    today_stats = WebsiteUsageStats.objects.filter(date=today).first()
    
    if today_stats:
        print(f"\n📅 統計日期: {today_stats.date}")
        print(f"👥 唯一訪客數: {today_stats.unique_visitors} 人")
        print(f"📄 總頁面瀏覽: {today_stats.total_page_views} 次")
        print(f"🔗 API 請求數: {today_stats.total_api_requests} 次")
        
        # 檢查 visitors_set
        if isinstance(today_stats.top_pages, dict) and '_visitors_set' in today_stats.top_pages:
            visitors_set = today_stats.top_pages['_visitors_set']
            print(f"\n🔍 Visitors Set 記錄數: {len(visitors_set)}")
            
            # 顯示前10個訪客識別碼
            print(f"\n前 10 個訪客識別碼:")
            for idx, visitor in enumerate(visitors_set[:10], 1):
                print(f"  {idx}. {visitor}")
            
            # 分析訪客類型
            user_visitors = [v for v in visitors_set if v.startswith('user_')]
            ip_visitors = [v for v in visitors_set if v.startswith('ip_')]
            
            print(f"\n📊 訪客類型統計:")
            print(f"  • 登入用戶: {len(user_visitors)} 人")
            print(f"  • 未登入訪客 (基於 IP): {len(ip_visitors)} 人")
            print(f"  • 總計: {len(visitors_set)} 人")
            
            # 驗證去重效果
            if len(visitors_set) == len(set(visitors_set)):
                print(f"\n✅ 去重邏輯正常：無重複記錄")
            else:
                duplicates = len(visitors_set) - len(set(visitors_set))
                print(f"\n⚠️ 發現重複記錄: {duplicates} 筆")
        else:
            print(f"\n⚠️ 尚未建立 visitors_set 記錄")
        
        # 顯示 top_users
        if today_stats.top_users and len(today_stats.top_users) > 0:
            print(f"\n🏆 今日最活躍使用者 (Top {len(today_stats.top_users)}):")
            for idx, user_stat in enumerate(today_stats.top_users, 1):
                username = user_stat.get('username', 'Unknown')
                visit_count = user_stat.get('visit_count', 0)
                print(f"   {idx}. {username}: {visit_count} 次訪問")
        else:
            print(f"\n📝 尚無登入使用者訪問記錄")
        
        # 計算平均瀏覽次數
        if today_stats.unique_visitors > 0:
            avg_views = today_stats.total_page_views / today_stats.unique_visitors
            print(f"\n📊 平均每人瀏覽: {avg_views:.2f} 次")
    else:
        print(f"\n⚠️ 今日 ({today}) 尚無統計記錄")
        print("   請訪問網站以開始記錄統計數據")
    
    print("\n" + "=" * 80)
    print("✅ 測試完成")
    print("=" * 80)
    
    # 說明修復內容
    print("\n📖 修復說明：")
    print("   • 問題：未登入用戶使用 Session 識別時，Session 未創建導致重複計數")
    print("   • 修復：改用 IP 地址識別未登入用戶（支援 X-Forwarded-For）")
    print("   • 存儲：使用資料庫欄位 top_pages._visitors_set 存儲訪客列表")
    print("   • 去重：每次請求檢查 visitor_key 是否已存在於列表中")


if __name__ == '__main__':
    try:
        test_visitor_deduplication()
    except Exception as e:
        print(f"\n❌ 測試失敗: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
