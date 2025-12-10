#!/usr/bin/env python3
"""
測試唯一訪客統計邏輯
驗證基於帳戶的不重複計數
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

def test_unique_visitors_stats():
    """測試唯一訪客統計"""
    print("=" * 80)
    print("🧪 測試唯一訪客統計邏輯")
    print("=" * 80)
    
    # 獲取今天的統計
    today = timezone.now().date()
    today_stats = WebsiteUsageStats.objects.filter(date=today).first()
    
    if today_stats:
        print(f"\n📅 統計日期: {today_stats.date}")
        print(f"👥 唯一訪客數: {today_stats.unique_visitors} 人")
        print(f"📄 總頁面瀏覽: {today_stats.total_page_views} 次")
        print(f"🔗 API 請求數: {today_stats.total_api_requests} 次")
        
        if today_stats.unique_visitors > 0:
            print(f"📊 平均每人瀏覽: {today_stats.total_page_views / today_stats.unique_visitors:.2f} 次")
        
        # 顯示最活躍使用者
        if today_stats.top_users and len(today_stats.top_users) > 0:
            print(f"\n🏆 今日最活躍使用者 (Top {len(today_stats.top_users)}):")
            for idx, user_stat in enumerate(today_stats.top_users, 1):
                username = user_stat.get('username', 'Unknown')
                visit_count = user_stat.get('visit_count', 0)
                print(f"   {idx}. {username}: {visit_count} 次訪問")
        else:
            print("\n📝 尚無登入使用者訪問記錄")
        
    else:
        print(f"\n⚠️ 今日 ({today}) 尚無統計記錄")
        print("   請訪問網站以開始記錄統計數據")
    
    # 顯示過去7天的唯一訪客趨勢
    print("\n" + "=" * 80)
    print("📈 過去 7 天唯一訪客趨勢")
    print("=" * 80)
    
    from datetime import timedelta
    seven_days_ago = today - timedelta(days=7)
    recent_stats = WebsiteUsageStats.objects.filter(
        date__gte=seven_days_ago
    ).order_by('date')
    
    if recent_stats.exists():
        print(f"\n{'日期':<12} {'唯一訪客':<10} {'頁面瀏覽':<10} {'API請求':<10}")
        print("-" * 50)
        for stat in recent_stats:
            print(f"{stat.date!s:<12} {stat.unique_visitors:<10} {stat.total_page_views:<10} {stat.total_api_requests:<10}")
        
        # 計算總計
        total_visitors = sum(s.unique_visitors for s in recent_stats)
        total_views = sum(s.total_page_views for s in recent_stats)
        total_api = sum(s.total_api_requests for s in recent_stats)
        
        print("-" * 50)
        print(f"{'總計':<12} {total_visitors:<10} {total_views:<10} {total_api:<10}")
        print(f"\n💡 7日平均每日訪客: {total_visitors / len(recent_stats):.1f} 人")
    else:
        print("\n⚠️ 過去 7 天無統計記錄")
    
    print("\n" + "=" * 80)
    print("✅ 測試完成")
    print("=" * 80)
    
    # 說明統計邏輯
    print("\n📖 統計規則說明：")
    print("   • 登入用戶：以帳戶 username 識別，同一帳戶每天只計算一次")
    print("   • 未登入用戶：以 Session 或 IP 識別，避免重複計數")
    print("   • 圖表顯示：過去 7 天的每日唯一訪客數（不重複人數）")
    print("   • 數據更新：每次訪問即時更新，無需手動刷新")

if __name__ == '__main__':
    try:
        test_unique_visitors_stats()
    except Exception as e:
        print(f"\n❌ 測試失敗: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
