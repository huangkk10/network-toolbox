#!/bin/bash
###############################################################################
# DHCP 日誌狀態檢查腳本
#
# 用途：快速檢查各 DHCP Server 的日誌保留情況和清理配置
#
# 使用方式：
#   ./check_dhcp_log_status.sh
#
# 作者：Network Toolbox Team
# 日期：2025-11-12
###############################################################################

# 顏色定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# 顯示標題
echo ""
echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║            DHCP 日誌狀態檢查工具                            ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo ""

# 檢查 Docker 容器
echo -e "${BLUE}[1/4]${NC} 檢查 Docker 容器狀態..."
if ! docker ps | grep -q "nt-django"; then
    echo -e "${RED}✗${NC} Django 容器未運行"
    exit 1
fi
echo -e "${GREEN}✓${NC} Docker 容器運行中"
echo ""

# 檢查 Celery 定時任務配置
echo -e "${BLUE}[2/4]${NC} 檢查 Celery 定時任務配置..."
echo "────────────────────────────────────────────────────────────────"

docker exec nt-django python manage.py shell -c "
from django_celery_beat.models import PeriodicTask
import json
from datetime import datetime
import pytz

try:
    task = PeriodicTask.objects.get(name='cleanup-old-dhcp-logs-daily')
    kwargs = json.loads(task.kwargs) if task.kwargs else {}
    days = kwargs.get('days', '未設定（預設 15）')
    
    print(f'任務名稱: {task.name}')
    print(f'保留天數: {days} 天')
    print(f'啟用狀態: {\"✅ 啟用\" if task.enabled else \"❌ 禁用\"}')
    print(f'Cron 排程: {task.crontab}')
    
    if task.last_run_at:
        tz = pytz.timezone('Asia/Taipei')
        last_run_taipei = task.last_run_at.astimezone(tz)
        print(f'最後執行: {last_run_taipei.strftime(\"%Y-%m-%d %H:%M:%S\")}')
    else:
        print('最後執行: 從未執行')
    
    print(f'總執行次數: {task.total_run_count}')
    
except PeriodicTask.DoesNotExist:
    print('❌ 定時任務不存在')
except Exception as e:
    print(f'❌ 錯誤: {e}')
"

echo "────────────────────────────────────────────────────────────────"
echo ""

# 檢查各 Server 的日誌統計
echo -e "${BLUE}[3/4]${NC} 檢查各 DHCP Server 的日誌統計..."
echo "────────────────────────────────────────────────────────────────"

docker exec nt-django python manage.py shell -c "
from api.models import DHCPLog, DHCPServer
from django.db.models import Count, Min, Max
from django.db.models.functions import TruncDate

servers = DHCPServer.objects.all().order_by('name')

for server in servers:
    logs = DHCPLog.objects.filter(server=server)
    total = logs.count()
    
    print(f'\\n📊 Server: {server.name} ({server.ip_address})')
    print(f'   總日誌數: {total:,} 筆')
    
    if total > 0:
        earliest = logs.aggregate(Min('timestamp'))['timestamp__min']
        latest = logs.aggregate(Max('timestamp'))['timestamp__max']
        
        if earliest and latest:
            from django.utils import timezone
            
            # 轉換為 Taipei 時區
            tz_taipei = timezone.get_current_timezone()
            earliest_taipei = timezone.localtime(earliest, tz_taipei)
            latest_taipei = timezone.localtime(latest, tz_taipei)
            
            days_covered = (latest - earliest).days
            
            print(f'   最早日誌: {earliest_taipei.strftime(\"%Y-%m-%d %H:%M:%S\")}')
            print(f'   最新日誌: {latest_taipei.strftime(\"%Y-%m-%d %H:%M:%S\")}')
            print(f'   涵蓋天數: {days_covered} 天')
            
            # 每日統計（最近 7 天）
            daily_counts = logs.annotate(
                date=TruncDate('timestamp')
            ).values('date').annotate(count=Count('id')).order_by('-date')[:7]
            
            print('   最近 7 天日誌量:')
            for item in daily_counts:
                print(f'     - {item[\"date\"]}: {item[\"count\"]:,} 筆')
    else:
        print('   ⚠️  沒有日誌數據')

print()
"

echo "────────────────────────────────────────────────────────────────"
echo ""

# 計算清理預估
echo -e "${BLUE}[4/4]${NC} 計算下次清理預估..."
echo "────────────────────────────────────────────────────────────────"

docker exec nt-django python manage.py shell -c "
from django_celery_beat.models import PeriodicTask
from api.models import DHCPLog
from django.utils import timezone
from datetime import timedelta, datetime
import json
import pytz

try:
    # 獲取配置
    task = PeriodicTask.objects.get(name='cleanup-old-dhcp-logs-daily')
    kwargs = json.loads(task.kwargs) if task.kwargs else {}
    days = kwargs.get('days', 15)
    
    # 計算清理界線
    now = timezone.now()
    cutoff_date = now - timedelta(days=days)
    
    # 統計將被清理的日誌
    to_delete_count = DHCPLog.objects.filter(timestamp__lt=cutoff_date).count()
    will_keep_count = DHCPLog.objects.filter(timestamp__gte=cutoff_date).count()
    
    # 轉換為 Taipei 時區顯示
    tz = pytz.timezone('Asia/Taipei')
    now_taipei = now.astimezone(tz)
    cutoff_taipei = cutoff_date.astimezone(tz)
    
    # 計算下次執行時間（明天凌晨 3:00）
    tomorrow = now_taipei.replace(hour=3, minute=0, second=0, microsecond=0)
    if tomorrow <= now_taipei:
        tomorrow += timedelta(days=1)
    
    print(f'當前時間: {now_taipei.strftime(\"%Y-%m-%d %H:%M:%S\")}')
    print(f'清理界線: {cutoff_taipei.strftime(\"%Y-%m-%d %H:%M:%S\")} （{days} 天前）')
    print()
    print(f'現有日誌: {will_keep_count:,} 筆（將保留）')
    
    if to_delete_count > 0:
        print(f'過期日誌: {to_delete_count:,} 筆（將在下次清理時刪除）')
    else:
        print(f'過期日誌: 無（所有日誌都在保留期內）')
    
    print()
    print(f'下次清理: {tomorrow.strftime(\"%Y-%m-%d %H:%M:%S\")}')
    
    hours_until = (tomorrow - now_taipei).total_seconds() / 3600
    print(f'距離下次清理: {hours_until:.1f} 小時')
    
except Exception as e:
    print(f'❌ 錯誤: {e}')
"

echo "────────────────────────────────────────────────────────────────"
echo ""

# 顯示建議
echo "╔═══════════════════════════════════════════════════════════════╗"
echo -e "║  ${CYAN}建議與操作${NC}                                               ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo ""
echo "調整保留天數："
echo "  ./scripts/fix_dhcp_log_retention.sh 30    # 改為 30 天"
echo "  ./scripts/fix_dhcp_log_retention.sh 60    # 改為 60 天"
echo ""
echo "查看詳細文檔："
echo "  docs/troubleshooting/DHCP_LOG_CLEANUP_ISSUE.md"
echo ""
echo "手動清理日誌："
echo "  docker exec nt-django python /app/clean_old_dhcp_logs.py"
echo ""
echo "查看 Celery 日誌："
echo "  docker compose logs celery_beat -f"
echo ""

exit 0
