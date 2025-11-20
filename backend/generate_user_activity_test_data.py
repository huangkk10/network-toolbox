#!/usr/bin/env python
"""
生成使用者活動測試數據

用於測試 Dashboard 使用者活動統計功能
"""
import os
import sys
import django
import random
from datetime import datetime, timedelta

# 設置 Django 環境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'network_toolbox.settings')
django.setup()

from django.utils import timezone
from django.contrib.auth.models import User
from api.models import UserActivity


def generate_test_users(count=5):
    """創建測試使用者"""
    print(f"\n📝 創建 {count} 個測試使用者...")
    
    users = []
    for i in range(1, count + 1):
        username = f'testuser{i}'
        
        # 檢查使用者是否已存在
        user, created = User.objects.get_or_create(
            username=username,
            defaults={
                'email': f'{username}@example.com',
                'first_name': f'Test',
                'last_name': f'User {i}',
            }
        )
        
        if created:
            user.set_password('password123')
            user.save()
            print(f'  ✓ 創建使用者: {username}')
        else:
            print(f'  ➜ 使用者已存在: {username}')
        
        users.append(user)
    
    return users


def generate_activity_data(users, days=7):
    """生成過去N天的使用者活動數據"""
    print(f"\n📊 生成過去 {days} 天的活動數據...")
    
    today = timezone.now().date()
    total_created = 0
    
    for day_offset in range(days):
        date = today - timedelta(days=day_offset)
        
        print(f"\n  日期: {date}")
        
        for user in users:
            # 隨機決定是否有活動（80%機率）
            if random.random() > 0.2:
                # 生成隨機請求數
                total_requests = random.randint(10, 200)
                get_requests = int(total_requests * 0.6)
                post_requests = int(total_requests * 0.25)
                put_requests = int(total_requests * 0.1)
                delete_requests = total_requests - get_requests - post_requests - put_requests
                
                # 生成錯誤數（0-5個錯誤）
                error_count = random.randint(0, 5)
                
                # 生成熱門路徑
                paths = [
                    '/api/dhcp-servers/',
                    '/api/dhcp-leases/',
                    '/api/jenkins-jobs/',
                    '/api/ansible-inventory/',
                    '/api/ipxe-logs/',
                ]
                top_paths = {}
                for path in random.sample(paths, random.randint(3, 5)):
                    top_paths[path] = random.randint(5, 50)
                
                # 創建或更新活動記錄
                activity, created = UserActivity.objects.update_or_create(
                    username=user.username,
                    date=date,
                    defaults={
                        'user': user,
                        'total_requests': total_requests,
                        'get_requests': get_requests,
                        'post_requests': post_requests,
                        'put_requests': put_requests,
                        'delete_requests': delete_requests,
                        'error_count': error_count,
                        'top_paths': top_paths,
                    }
                )
                
                if created:
                    total_created += 1
                    print(f'    ✓ {user.username}: {total_requests} 次請求')
    
    print(f"\n✅ 完成！共創建 {total_created} 筆活動記錄")


def show_statistics():
    """顯示當前統計數據"""
    print("\n" + "="*80)
    print("📈 當前使用者活動統計")
    print("="*80)
    
    today = timezone.now().date()
    
    # 今日統計
    today_activities = UserActivity.objects.filter(date=today)
    print(f"\n今日 ({today}):")
    print(f"  活躍使用者: {today_activities.count()}")
    print(f"  總請求次數: {sum(a.total_requests for a in today_activities)}")
    
    if today_activities.exists():
        print(f"\n  今日TOP 3:")
        for i, activity in enumerate(today_activities.order_by('-total_requests')[:3], 1):
            print(f"    {i}. {activity.username}: {activity.total_requests} 次")
    
    # 過去7天統計
    seven_days_ago = today - timedelta(days=7)
    week_activities = UserActivity.objects.filter(date__gte=seven_days_ago)
    print(f"\n過去 7 天:")
    print(f"  總活動記錄: {week_activities.count()}")
    print(f"  總請求次數: {sum(a.total_requests for a in week_activities)}")
    
    # 按日期統計
    print(f"\n  每日活動:")
    for day_offset in range(7):
        date = today - timedelta(days=day_offset)
        day_activities = UserActivity.objects.filter(date=date)
        if day_activities.exists():
            total_req = sum(a.total_requests for a in day_activities)
            print(f"    {date}: {day_activities.count()} 人, {total_req} 次請求")


def main():
    print("="*80)
    print("🚀 使用者活動測試數據生成器")
    print("="*80)
    
    try:
        # 1. 創建測試使用者
        users = generate_test_users(count=5)
        
        # 2. 生成活動數據
        generate_activity_data(users, days=7)
        
        # 3. 顯示統計
        show_statistics()
        
        print("\n" + "="*80)
        print("✅ 測試數據生成完成！")
        print("="*80)
        print("\n💡 現在可以訪問 Dashboard 查看使用者活動統計")
        print("   URL: http://localhost/dashboard")
        
    except Exception as e:
        print(f"\n❌ 發生錯誤: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
