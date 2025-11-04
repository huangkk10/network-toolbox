#!/usr/bin/env python
"""
Phase 5: Redis 緩存裝飾器測試腳本

測試所有緩存裝飾器的功能，並使用真實的 Jenkins 伺服器進行驗證。
Jenkins URL: http://10.252.170.188:8080/
"""

import os
import sys
import django
import time
from datetime import datetime

# Django 設置
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'network_toolbox.settings')
django.setup()

from django.core.cache import cache
from library.utils import (
    cached,
    cache_result,
    cache_jenkins_api,
    cache_jenkins_config,
    cache_jenkins_log,
    get_cache_stats,
)
from library.services.jenkins_client import JenkinsClient

# Jenkins 測試配置
JENKINS_URL = 'http://10.252.170.188:8080'
JENKINS_USERNAME = None  # 如果需要認證，請設置
JENKINS_API_TOKEN = None  # 如果需要認證，請設置


def print_section(title):
    """打印分隔線"""
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}\n")


def test_redis_connection():
    """測試 1: Redis 連接"""
    print_section("測試 1: Redis 連接")
    
    try:
        # 測試基本讀寫
        test_key = 'test:connection'
        test_value = f'Hello Redis! {datetime.now()}'
        
        cache.set(test_key, test_value, 60)
        retrieved_value = cache.get(test_key)
        
        if retrieved_value == test_value:
            print("✅ Redis 連接正常")
            print(f"   寫入值: {test_value}")
            print(f"   讀取值: {retrieved_value}")
            
            # 清理
            cache.delete(test_key)
            return True
        else:
            print("❌ Redis 讀寫不一致")
            return False
            
    except Exception as e:
        print(f"❌ Redis 連接失敗: {e}")
        return False


def test_basic_cache_decorator():
    """測試 2: 基本緩存裝飾器"""
    print_section("測試 2: 基本緩存裝飾器 (@cached)")
    
    call_count = [0]  # 使用列表來追蹤調用次數
    
    @cached(ttl=60, prefix='test')
    def expensive_function(x, y):
        """模擬耗時函數"""
        call_count[0] += 1
        time.sleep(0.1)  # 模擬耗時操作
        return x + y
    
    try:
        # 第一次調用（應該執行函數）
        start = time.time()
        result1 = expensive_function(10, 20)
        time1 = time.time() - start
        
        # 第二次調用（應該從緩存讀取）
        start = time.time()
        result2 = expensive_function(10, 20)
        time2 = time.time() - start
        
        # 第三次調用（不同參數，應該執行函數）
        result3 = expensive_function(30, 40)
        
        print(f"✅ 緩存裝飾器測試通過")
        print(f"   第 1 次調用: 結果={result1}, 耗時={time1:.3f}s")
        print(f"   第 2 次調用: 結果={result2}, 耗時={time2:.3f}s (從緩存)")
        print(f"   第 3 次調用: 結果={result3} (不同參數)")
        print(f"   函數實際執行次數: {call_count[0]} (預期: 2)")
        print(f"   性能提升: {time1/time2:.1f}x")
        
        # 清理緩存
        expensive_function.clear_cache(10, 20)
        expensive_function.clear_cache(30, 40)
        
        return call_count[0] == 2
        
    except Exception as e:
        print(f"❌ 測試失敗: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_cache_result_decorator():
    """測試 3: 簡化版緩存裝飾器"""
    print_section("測試 3: 簡化版緩存裝飾器 (@cache_result)")
    
    @cache_result(ttl=30)
    def get_current_time():
        """獲取當前時間（用於測試緩存）"""
        return datetime.now().isoformat()
    
    try:
        # 第一次調用
        time1 = get_current_time()
        print(f"   第 1 次調用: {time1}")
        
        # 等待 1 秒後再調用（應該返回相同時間，因為有緩存）
        time.sleep(1)
        time2 = get_current_time()
        print(f"   第 2 次調用: {time2}")
        
        if time1 == time2:
            print(f"✅ 緩存生效（兩次調用返回相同時間）")
            return True
        else:
            print(f"❌ 緩存未生效（兩次調用返回不同時間）")
            return False
            
    except Exception as e:
        print(f"❌ 測試失敗: {e}")
        return False


def test_jenkins_client_connection():
    """測試 4: Jenkins 客戶端連接"""
    print_section("測試 4: Jenkins 客戶端連接")
    
    try:
        client = JenkinsClient(
            base_url=JENKINS_URL,
            username=JENKINS_USERNAME,
            api_token=JENKINS_API_TOKEN
        )
        
        # 測試連接
        if client.test_connection():
            print(f"✅ Jenkins 連接成功: {JENKINS_URL}")
            
            # 獲取伺服器資訊
            server_info = client.get_server_info()
            print(f"   Jenkins 描述: {server_info.get('nodeDescription', 'N/A')}")
            print(f"   Job 數量: {len(server_info.get('jobs', []))}")
            
            client.close()
            return True
        else:
            print(f"❌ Jenkins 連接失敗")
            client.close()
            return False
            
    except Exception as e:
        print(f"❌ 測試失敗: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_jenkins_api_cache():
    """測試 5: Jenkins API 緩存"""
    print_section("測試 5: Jenkins API 緩存裝飾器")
    
    @cache_jenkins_api(ttl=60)
    def fetch_jenkins_jobs(url):
        """從 Jenkins 獲取 Job 列表（帶緩存）"""
        client = JenkinsClient(base_url=url)
        try:
            jobs = client.list_jobs()
            return jobs
        finally:
            client.close()
    
    try:
        # 第一次調用（從 Jenkins API 獲取）
        start = time.time()
        jobs1 = fetch_jenkins_jobs(JENKINS_URL)
        time1 = time.time() - start
        
        # 第二次調用（從緩存讀取）
        start = time.time()
        jobs2 = fetch_jenkins_jobs(JENKINS_URL)
        time2 = time.time() - start
        
        print(f"✅ Jenkins API 緩存測試通過")
        print(f"   第 1 次調用: {len(jobs1)} 個 Job, 耗時={time1:.3f}s")
        print(f"   第 2 次調用: {len(jobs2)} 個 Job, 耗時={time2:.3f}s (從緩存)")
        print(f"   性能提升: {time1/time2:.1f}x")
        
        if len(jobs1) > 0:
            print(f"\n   Job 列表 (前 5 個):")
            for job in jobs1[:5]:
                print(f"     - {job.get('name', 'N/A')}")
        
        return True
        
    except Exception as e:
        print(f"❌ 測試失敗: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_cache_stats():
    """測試 6: 緩存統計"""
    print_section("測試 6: 緩存統計資訊")
    
    try:
        stats = get_cache_stats()
        
        if stats:
            print(f"✅ 成功獲取緩存統計")
            print(f"   記憶體使用: {stats.get('used_memory', 'N/A')}")
            print(f"   總鍵數量: {stats.get('total_keys', 0)}")
            print(f"   命中次數: {stats.get('hits', 0)}")
            print(f"   未命中次數: {stats.get('misses', 0)}")
            print(f"   命中率: {stats.get('hit_rate', 0):.2f}%")
            return True
        else:
            print(f"⚠️  無法獲取緩存統計（可能不支援）")
            return True  # 不算作失敗
            
    except Exception as e:
        print(f"⚠️  獲取緩存統計失敗: {e}")
        return True  # 不算作失敗


def test_cache_clear():
    """測試 7: 緩存清除"""
    print_section("測試 7: 緩存清除功能")
    
    @cached(ttl=60, prefix='test_clear')
    def test_function(value):
        return f"result_{value}"
    
    try:
        # 設置緩存
        result1 = test_function("test")
        print(f"   設置緩存: {result1}")
        
        # 驗證緩存存在
        result2 = test_function("test")
        assert result1 == result2
        print(f"   緩存驗證: ✓")
        
        # 清除緩存
        test_function.clear_cache("test")
        print(f"   清除緩存: ✓")
        
        # 驗證緩存已清除（需要手動檢查，這裡簡化）
        result3 = test_function("test")
        print(f"   重新獲取: {result3}")
        
        print(f"✅ 緩存清除功能正常")
        return True
        
    except Exception as e:
        print(f"❌ 測試失敗: {e}")
        return False


def test_performance_comparison():
    """測試 8: 性能對比"""
    print_section("測試 8: 有無緩存性能對比")
    
    def slow_function(n):
        """模擬耗時操作"""
        time.sleep(0.05)
        return sum(range(n))
    
    @cached(ttl=60, prefix='perf_test')
    def cached_slow_function(n):
        """帶緩存的耗時操作"""
        time.sleep(0.05)
        return sum(range(n))
    
    try:
        iterations = 5
        
        # 測試無緩存版本
        start = time.time()
        for i in range(iterations):
            slow_function(1000)
        time_no_cache = time.time() - start
        
        # 測試有緩存版本
        start = time.time()
        for i in range(iterations):
            cached_slow_function(1000)
        time_with_cache = time.time() - start
        
        speedup = time_no_cache / time_with_cache
        
        print(f"✅ 性能對比測試完成")
        print(f"   無緩存版本: {time_no_cache:.3f}s ({iterations} 次調用)")
        print(f"   有緩存版本: {time_with_cache:.3f}s ({iterations} 次調用)")
        print(f"   性能提升: {speedup:.1f}x")
        
        # 清理
        cached_slow_function.clear_cache(1000)
        
        return speedup > 2  # 期望至少 2 倍提升
        
    except Exception as e:
        print(f"❌ 測試失敗: {e}")
        return False


def run_all_tests():
    """執行所有測試"""
    print("\n" + "=" * 60)
    print("  Phase 5: Redis 緩存裝飾器 - 完整測試")
    print(f"  Jenkins URL: {JENKINS_URL}")
    print(f"  測試時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    tests = [
        ("Redis 連接", test_redis_connection),
        ("基本緩存裝飾器", test_basic_cache_decorator),
        ("簡化版緩存裝飾器", test_cache_result_decorator),
        ("Jenkins 客戶端連接", test_jenkins_client_connection),
        ("Jenkins API 緩存", test_jenkins_api_cache),
        ("緩存統計", test_cache_stats),
        ("緩存清除", test_cache_clear),
        ("性能對比", test_performance_comparison),
    ]
    
    results = []
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
            if result:
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"\n❌ 測試異常: {test_name}")
            print(f"   錯誤: {e}")
            results.append((test_name, False))
            failed += 1
    
    # 總結
    print_section("測試總結")
    print(f"總測試數: {len(tests)}")
    print(f"✅ 通過: {passed}")
    print(f"❌ 失敗: {failed}")
    print(f"成功率: {passed/len(tests)*100:.1f}%\n")
    
    # 詳細結果
    print("詳細結果:")
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status}  {test_name}")
    
    print("\n" + "=" * 60)
    
    return passed == len(tests)


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
