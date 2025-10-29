"""
測試 NAS 連線功能

這個腳本用於測試 NAS SMB 連線和 nas_service.py 的功能
"""
import os
import sys
import django

# 設置 Django 環境
sys.path.insert(0, '/app')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'network_toolbox.settings')
django.setup()

from api.nas_service import check_nas_connection, record_nas_connection, get_nas_statistics
from api.models import NASConnectionLog
from django.utils import timezone

print("=" * 60)
print("NAS 連線功能測試")
print("=" * 60)

# 測試 1：檢查 NAS 連線
print("\n[測試 1] 測試 NAS 連線...")
try:
    status, response_time, upload_speed, download_speed, error_message = check_nas_connection()
    print(f"✓ NAS 連線測試完成")
    print(f"  - 狀態: {status}")
    print(f"  - 響應時間: {response_time:.2f} ms" if response_time else "  - 響應時間: N/A")
    print(f"  - 上傳速度: {upload_speed:.2f} MB/s" if upload_speed else "  - 上傳速度: N/A")
    print(f"  - 下載速度: {download_speed:.2f} MB/s" if download_speed else "  - 下載速度: N/A")
    if error_message:
        print(f"  - 錯誤訊息: {error_message}")
except Exception as e:
    print(f"✗ NAS 連線測試失敗: {str(e)}")
    import traceback
    traceback.print_exc()

# 測試 2：記錄 NAS 連線到數據庫
print("\n[測試 2] 測試記錄 NAS 連線到數據庫...")
try:
    success = record_nas_connection()
    if success:
        print("✓ NAS 連線記錄成功寫入數據庫")
        
        # 查詢最新記錄
        latest_log = NASConnectionLog.objects.order_by('-timestamp').first()
        if latest_log:
            print(f"  - 最新記錄: {latest_log}")
            print(f"  - 時間: {latest_log.timestamp}")
            print(f"  - 狀態: {latest_log.status}")
            print(f"  - NAS IP: {latest_log.nas_ip}")
    else:
        print("✗ NAS 連線記錄失敗")
except Exception as e:
    print(f"✗ 記錄 NAS 連線失敗: {str(e)}")
    import traceback
    traceback.print_exc()

# 測試 3：查詢數據庫記錄數量
print("\n[測試 3] 查詢數據庫中的 NAS 連線記錄...")
try:
    total_count = NASConnectionLog.objects.count()
    success_count = NASConnectionLog.objects.filter(status='success').count()
    failed_count = NASConnectionLog.objects.filter(status='failed').count()
    
    print(f"✓ 數據庫查詢成功")
    print(f"  - 總記錄數: {total_count}")
    print(f"  - 成功: {success_count}")
    print(f"  - 失敗: {failed_count}")
except Exception as e:
    print(f"✗ 數據庫查詢失敗: {str(e)}")

# 測試 4：獲取統計資料
print("\n[測試 4] 測試獲取統計資料...")
try:
    stats = get_nas_statistics(days=7)
    print(f"✓ 統計資料獲取成功")
    print(f"  - 總記錄數: {stats['total_records']}")
    print(f"  - 成功率: {stats['success_rate']:.2f}%")
    print(f"  - 平均響應時間: {stats['avg_response_time']:.2f} ms")
    print(f"  - 平均上傳速度: {stats['avg_upload_speed']:.2f} MB/s")
    print(f"  - 平均下載速度: {stats['avg_download_speed']:.2f} MB/s")
except Exception as e:
    print(f"✗ 獲取統計資料失敗: {str(e)}")

print("\n" + "=" * 60)
print("測試完成！")
print("=" * 60)
