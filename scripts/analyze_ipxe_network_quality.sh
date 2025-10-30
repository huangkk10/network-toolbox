#!/bin/bash

# iPXE 網路品質分析腳本
# 日期: 2025-10-30

echo "=========================================="
echo "iPXE 網路品質數據分析"
echo "=========================================="
echo ""

# 進入 Django 容器執行查詢
docker exec nt-django python manage.py shell <<EOF

from api.models import IPXENetworkQuality, IPXEServer
from django.utils import timezone
from datetime import timedelta
import json

print("📊 iPXE 網路品質統計分析\n")
print("=" * 60)

# 1. 查詢最近 7 天的記錄
seven_days_ago = timezone.now() - timedelta(days=7)
recent_logs = IPXENetworkQuality.objects.filter(
    timestamp__gte=seven_days_ago
).order_by('timestamp')

print(f"\n1️⃣  最近 7 天記錄數：{recent_logs.count()} 筆")

# 2. 按日期統計記錄數
from django.db.models import Count
from django.db.models.functions import TruncDate

daily_counts = IPXENetworkQuality.objects.filter(
    timestamp__gte=seven_days_ago
).annotate(
    date=TruncDate('timestamp')
).values('date').annotate(
    count=Count('id')
).order_by('date')

print("\n2️⃣  每日記錄數統計：")
print("-" * 40)
for item in daily_counts:
    print(f"   {item['date']}: {item['count']} 筆")

# 3. 10/29 前後的數據對比
oct_28 = timezone.datetime(2025, 10, 28, tzinfo=timezone.get_current_timezone())
oct_29 = timezone.datetime(2025, 10, 29, tzinfo=timezone.get_current_timezone())
oct_30 = timezone.datetime(2025, 10, 30, tzinfo=timezone.get_current_timezone())

before_oct29 = IPXENetworkQuality.objects.filter(
    timestamp__lt=oct_29
).exclude(
    ping_latency__isnull=True,
    http_response_time__isnull=True,
    ssh_response_time__isnull=True
)

after_oct29 = IPXENetworkQuality.objects.filter(
    timestamp__gte=oct_29
)

print(f"\n3️⃣  10/29 前後數據對比：")
print("-" * 40)
print(f"   10/29 之前有效記錄：{before_oct29.count()} 筆")
print(f"   10/29 之後記錄：{after_oct29.count()} 筆")

# 4. 分析 Ping 延遲
from django.db.models import Avg, Max, Min

ping_stats_before = before_oct29.exclude(
    ping_latency__isnull=True
).aggregate(
    avg=Avg('ping_latency'),
    max=Max('ping_latency'),
    min=Min('ping_latency'),
    count=Count('id')
)

ping_stats_after = after_oct29.exclude(
    ping_latency__isnull=True
).aggregate(
    avg=Avg('ping_latency'),
    max=Max('ping_latency'),
    min=Min('ping_latency'),
    count=Count('id')
)

print(f"\n4️⃣  Ping 延遲統計：")
print("-" * 40)
print(f"   10/29 之前：")
print(f"      記錄數：{ping_stats_before['count']}")
if ping_stats_before['avg']:
    print(f"      平均：{ping_stats_before['avg']:.2f} ms")
    print(f"      最大：{ping_stats_before['max']:.2f} ms")
    print(f"      最小：{ping_stats_before['min']:.2f} ms")
else:
    print(f"      無有效數據")

print(f"   10/29 之後：")
print(f"      記錄數：{ping_stats_after['count']}")
if ping_stats_after['avg']:
    print(f"      平均：{ping_stats_after['avg']:.2f} ms")
    print(f"      最大：{ping_stats_after['max']:.2f} ms")
    print(f"      最小：{ping_stats_after['min']:.2f} ms")

# 5. 分析 HTTP 響應時間
http_stats_before = before_oct29.exclude(
    http_response_time__isnull=True
).aggregate(
    avg=Avg('http_response_time'),
    max=Max('http_response_time'),
    min=Min('http_response_time'),
    count=Count('id')
)

http_stats_after = after_oct29.exclude(
    http_response_time__isnull=True
).aggregate(
    avg=Avg('http_response_time'),
    max=Max('http_response_time'),
    min=Min('http_response_time'),
    count=Count('id')
)

print(f"\n5️⃣  HTTP 響應時間統計：")
print("-" * 40)
print(f"   10/29 之前：")
print(f"      記錄數：{http_stats_before['count']}")
if http_stats_before['avg']:
    print(f"      平均：{http_stats_before['avg']:.2f} ms")
    print(f"      最大：{http_stats_before['max']:.2f} ms")
    print(f"      最小：{http_stats_before['min']:.2f} ms")
else:
    print(f"      無有效數據")

print(f"   10/29 之後：")
print(f"      記錄數：{http_stats_after['count']}")
if http_stats_after['avg']:
    print(f"      平均：{http_stats_after['avg']:.2f} ms")
    print(f"      最大：{http_stats_after['max']:.2f} ms")
    print(f"      最小：{http_stats_after['min']:.2f} ms")

# 6. 分析 SSH 響應時間
ssh_stats_before = before_oct29.exclude(
    ssh_response_time__isnull=True
).aggregate(
    avg=Avg('ssh_response_time'),
    max=Max('ssh_response_time'),
    min=Min('ssh_response_time'),
    count=Count('id')
)

ssh_stats_after = after_oct29.exclude(
    ssh_response_time__isnull=True
).aggregate(
    avg=Avg('ssh_response_time'),
    max=Max('ssh_response_time'),
    min=Min('ssh_response_time'),
    count=Count('id')
)

print(f"\n6️⃣  SSH 響應時間統計：")
print("-" * 40)
print(f"   10/29 之前：")
print(f"      記錄數：{ssh_stats_before['count']}")
if ssh_stats_before['avg']:
    print(f"      平均：{ssh_stats_before['avg']:.2f} ms")
    print(f"      最大：{ssh_stats_before['max']:.2f} ms")
    print(f"      最小：{ssh_stats_before['min']:.2f} ms")
else:
    print(f"      無有效數據（可能監控未啟用）")

print(f"   10/29 之後：")
print(f"      記錄數：{ssh_stats_after['count']}")
if ssh_stats_after['avg']:
    print(f"      平均：{ssh_stats_after['avg']:.2f} ms")
    print(f"      最大：{ssh_stats_after['max']:.2f} ms")
    print(f"      最小：{ssh_stats_after['min']:.2f} ms")

# 7. 查詢第一筆和最後一筆記錄
first_log = IPXENetworkQuality.objects.order_by('timestamp').first()
last_log = IPXENetworkQuality.objects.order_by('-timestamp').first()

print(f"\n7️⃣  監控時間範圍：")
print("-" * 40)
if first_log:
    print(f"   首次記錄：{first_log.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"   最新記錄：{last_log.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
    duration = last_log.timestamp - first_log.timestamp
    print(f"   監控時長：{duration.days} 天 {duration.seconds // 3600} 小時")

# 8. 查詢 10/29 的首筆記錄
first_oct29 = IPXENetworkQuality.objects.filter(
    timestamp__gte=oct_29,
    timestamp__lt=oct_30
).order_by('timestamp').first()

print(f"\n8️⃣  10/29 首筆記錄詳情：")
print("-" * 40)
if first_oct29:
    print(f"   時間：{first_oct29.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"   狀態：{first_oct29.get_status_display()}")
    print(f"   Ping 延遲：{first_oct29.ping_latency} ms" if first_oct29.ping_latency else "   Ping 延遲：無數據")
    print(f"   HTTP 響應：{first_oct29.http_response_time} ms" if first_oct29.http_response_time else "   HTTP 響應：無數據")
    print(f"   SSH 響應：{first_oct29.ssh_response_time} ms" if first_oct29.ssh_response_time else "   SSH 響應：無數據")
    if first_oct29.error_message:
        print(f"   錯誤訊息：{first_oct29.error_message}")
else:
    print(f"   無 10/29 的記錄")

# 9. 查詢失敗記錄
failed_logs = IPXENetworkQuality.objects.filter(
    timestamp__gte=seven_days_ago,
    status='failed'
)

print(f"\n9️⃣  失敗記錄統計（最近 7 天）：")
print("-" * 40)
print(f"   失敗次數：{failed_logs.count()} 次")
if failed_logs.exists():
    print(f"   失敗記錄：")
    for log in failed_logs[:5]:  # 只顯示前 5 筆
        print(f"      - {log.timestamp.strftime('%Y-%m-%d %H:%M:%S')}: {log.error_message or '無錯誤訊息'}")

print("\n" + "=" * 60)
print("分析完成！")
print("")

EOF

echo ""
echo "=========================================="
echo "分析完成"
echo "=========================================="
