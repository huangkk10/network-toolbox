#!/usr/bin/env python3
"""
清理錯誤的唯一訪客統計數據
修正因 Session 問題導致的重複計數
"""
import os
import sys
import django
from datetime import datetime, timedelta

# 設置 Django 環境
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'network_toolbox.settings')
django.setup()

from django.utils import timezone
from django.contrib.auth.models import User
from api.models import WebsiteUsageStats


def analyze_and_fix_stats():
    """分析並修正統計數據"""
    print("=" * 80)
    print("🔍 分析唯一訪客統計數據")
    print("=" * 80)
    
    # 獲取所有統計記錄
    all_stats = WebsiteUsageStats.objects.all().order_by('date')
    total_users = User.objects.count()
    
    print(f"\n📊 系統總用戶數: {total_users}")
    print(f"📅 統計記錄數: {all_stats.count()}")
    print("")
    
    suspicious_records = []
    
    print("日期          | 唯一訪客 | 登入用戶 | 差異 | 狀態")
    print("-" * 70)
    
    for stat in all_stats:
        login_users_count = len(stat.top_users) if stat.top_users else 0
        difference = stat.unique_visitors - login_users_count
        
        # 判斷是否可疑（差異過大，超過合理範圍）
        # 假設未登入訪客不應該超過登入用戶的 2 倍
        is_suspicious = False
        if login_users_count > 0:
            if difference > login_users_count * 3:
                is_suspicious = True
        elif stat.unique_visitors > total_users:
            is_suspicious = True
        
        status = "⚠️ 可疑" if is_suspicious else "✅ 正常"
        
        print(f"{stat.date} | {stat.unique_visitors:8} | {login_users_count:8} | {difference:4} | {status}")
        
        if is_suspicious:
            suspicious_records.append({
                'stat': stat,
                'login_users': login_users_count,
                'difference': difference
            })
    
    print("")
    
    if suspicious_records:
        print(f"⚠️ 發現 {len(suspicious_records)} 筆可疑記錄")
        print("")
        
        # 詢問是否修正
        print("建議修正方式：")
        print("  1. 保守估計：唯一訪客 = 登入用戶數 + 1-2 位未登入訪客")
        print("  2. 合理估計：唯一訪客 = 登入用戶數 + (差異 / 10) 位未登入訪客")
        print("")
        
        choice = input("是否要修正這些記錄？(y/n): ")
        
        if choice.lower() == 'y':
            fix_method = input("選擇修正方式 (1=保守, 2=合理): ")
            
            for record in suspicious_records:
                stat = record['stat']
                login_users = record['login_users']
                
                if fix_method == '1':
                    # 保守估計
                    corrected_visitors = login_users + 2
                else:
                    # 合理估計
                    corrected_visitors = login_users + max(1, record['difference'] // 10)
                
                old_value = stat.unique_visitors
                stat.unique_visitors = corrected_visitors
                stat.save()
                
                print(f"✅ {stat.date}: {old_value} → {corrected_visitors}")
            
            print(f"\n✅ 已修正 {len(suspicious_records)} 筆記錄")
        else:
            print("❌ 取消修正")
    else:
        print("✅ 所有記錄看起來都正常")
    
    print("\n" + "=" * 80)
    print("✅ 分析完成")
    print("=" * 80)
    
    # 說明
    print("\n📖 說明：")
    print("  • 此腳本用於識別和修正因 Session 問題導致的重複計數")
    print("  • 修正後的數據僅用於顯示，不會影響實際功能")
    print("  • 新的中間件邏輯已修復，未來不會再出現此問題")


if __name__ == '__main__':
    try:
        analyze_and_fix_stats()
    except Exception as e:
        print(f"\n❌ 執行失敗: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
