#!/bin/bash
###############################################################################
# DHCP 日誌保留天數調整腳本
#
# 用途：將 DHCP 日誌保留天數從 7 天調整為指定天數
#
# 使用方式：
#   ./fix_dhcp_log_retention.sh 30       # 調整為 30 天
#   ./fix_dhcp_log_retention.sh 60       # 調整為 60 天
#
# 作者：Network Toolbox Team
# 日期：2025-11-12
###############################################################################

set -e  # 遇到錯誤立即退出

# 顏色定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日誌函數
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 顯示標題
print_header() {
    echo "╔═══════════════════════════════════════════════════════════════╗"
    echo "║         DHCP 日誌保留天數調整工具                           ║"
    echo "╚═══════════════════════════════════════════════════════════════╝"
    echo ""
}

# 檢查參數
if [ $# -eq 0 ]; then
    print_header
    log_error "請指定保留天數"
    echo ""
    echo "使用方式："
    echo "  $0 <天數>"
    echo ""
    echo "範例："
    echo "  $0 30    # 保留 30 天"
    echo "  $0 60    # 保留 60 天"
    echo "  $0 90    # 保留 90 天"
    echo ""
    exit 1
fi

RETENTION_DAYS=$1

# 驗證輸入是否為數字
if ! [[ "$RETENTION_DAYS" =~ ^[0-9]+$ ]]; then
    log_error "保留天數必須是正整數"
    exit 1
fi

# 驗證範圍
if [ "$RETENTION_DAYS" -lt 1 ] || [ "$RETENTION_DAYS" -gt 365 ]; then
    log_error "保留天數必須在 1-365 天之間"
    exit 1
fi

print_header

log_info "目標保留天數: ${RETENTION_DAYS} 天"
echo ""

# 檢查 Docker 容器是否運行
log_info "檢查 Docker 容器狀態..."
if ! docker ps | grep -q "nt-django"; then
    log_error "Django 容器未運行，請先啟動服務"
    echo "執行：docker compose up -d"
    exit 1
fi
log_success "Docker 容器運行中"
echo ""

# 顯示當前配置
log_info "查詢當前配置..."
CURRENT_CONFIG=$(docker exec nt-django python manage.py shell -c "
from django_celery_beat.models import PeriodicTask
import json

try:
    task = PeriodicTask.objects.get(name='cleanup-old-dhcp-logs-daily')
    kwargs = json.loads(task.kwargs) if task.kwargs else {}
    current_days = kwargs.get('days', '未設定（預設 15 天）')
    print(f'{current_days}')
except PeriodicTask.DoesNotExist:
    print('任務不存在')
except Exception as e:
    print(f'錯誤: {e}')
" 2>&1)

if [[ "$CURRENT_CONFIG" == *"錯誤"* ]] || [[ "$CURRENT_CONFIG" == *"任務不存在"* ]]; then
    log_warning "無法讀取當前配置: $CURRENT_CONFIG"
else
    log_info "當前保留天數: ${CURRENT_CONFIG}"
fi
echo ""

# 詢問確認
echo "────────────────────────────────────────────────────────────────"
log_warning "即將修改日誌保留天數為 ${RETENTION_DAYS} 天"
echo ""
echo "影響範圍："
echo "  - 所有 DHCP Server 的日誌"
echo "  - 超過 ${RETENTION_DAYS} 天的日誌將被自動清理（每天凌晨 3 點）"
echo ""
read -p "是否確認修改？(yes/no): " -r CONFIRM
echo ""

if [[ ! "$CONFIRM" =~ ^[Yy][Ee][Ss]$ ]]; then
    log_warning "操作已取消"
    exit 0
fi

# 執行修改
log_info "正在更新 Celery 定時任務配置..."

UPDATE_RESULT=$(docker exec nt-django python manage.py shell -c "
from django_celery_beat.models import PeriodicTask
import json

try:
    task = PeriodicTask.objects.get(name='cleanup-old-dhcp-logs-daily')
    task.kwargs = json.dumps({'days': ${RETENTION_DAYS}})
    task.save()
    
    # 驗證更新
    task.refresh_from_db()
    kwargs = json.loads(task.kwargs)
    actual_days = kwargs.get('days')
    
    if actual_days == ${RETENTION_DAYS}:
        print('SUCCESS')
    else:
        print(f'FAILED: 期望 ${RETENTION_DAYS}，實際 {actual_days}')
except PeriodicTask.DoesNotExist:
    print('FAILED: 任務不存在')
except Exception as e:
    print(f'FAILED: {e}')
" 2>&1)

if [[ "$UPDATE_RESULT" == "SUCCESS" ]]; then
    log_success "配置更新成功"
else
    log_error "配置更新失敗: $UPDATE_RESULT"
    exit 1
fi
echo ""

# 重啟 Celery 服務
log_info "重啟 Celery 服務以載入新配置..."
docker compose restart celery_worker celery_beat > /dev/null 2>&1

# 等待服務啟動
log_info "等待服務啟動（10 秒）..."
sleep 10

# 檢查 Celery 狀態
CELERY_STATUS=$(docker exec nt-django celery -A network_toolbox inspect active 2>&1)
if [[ "$CELERY_STATUS" == *"Error"* ]]; then
    log_warning "Celery Worker 可能未正常啟動，請檢查日誌"
else
    log_success "Celery 服務重啟完成"
fi
echo ""

# 驗證最終配置
log_info "驗證最終配置..."
FINAL_CONFIG=$(docker exec nt-django python manage.py shell -c "
from django_celery_beat.models import PeriodicTask
import json

task = PeriodicTask.objects.get(name='cleanup-old-dhcp-logs-daily')
kwargs = json.loads(task.kwargs)
print(f'保留天數: {kwargs.get(\"days\")} 天')
print(f'啟用狀態: {\"啟用\" if task.enabled else \"禁用\"}')
print(f'執行時間: 每天凌晨 3:00')
print(f'最後執行: {task.last_run_at or \"從未執行\"}')
print(f'總執行次數: {task.total_run_count}')
" 2>&1)

echo "────────────────────────────────────────────────────────────────"
echo "$FINAL_CONFIG"
echo "────────────────────────────────────────────────────────────────"
echo ""

# 顯示日誌統計
log_info "查詢當前日誌統計..."
LOG_STATS=$(docker exec nt-django python manage.py shell -c "
from api.models import DHCPLog
from django.db.models import Min, Max

logs = DHCPLog.objects.all()
total = logs.count()
earliest = logs.aggregate(Min('timestamp'))['timestamp__min']
latest = logs.aggregate(Max('timestamp'))['timestamp__max']

print(f'總日誌數: {total:,} 筆')
if earliest and latest:
    days_covered = (latest - earliest).days
    print(f'最早日誌: {earliest.strftime(\"%Y-%m-%d %H:%M:%S\")}')
    print(f'最新日誌: {latest.strftime(\"%Y-%m-%d %H:%M:%S\")}')
    print(f'涵蓋天數: {days_covered} 天')
else:
    print('目前沒有日誌數據')
" 2>&1)

echo "$LOG_STATS"
echo ""

# 完成
echo "╔═══════════════════════════════════════════════════════════════╗"
log_success "配置修改完成！"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo ""
echo "後續動作："
echo "  ✅ Celery 定時任務已更新為保留 ${RETENTION_DAYS} 天"
echo "  ✅ 每天凌晨 3:00 會自動清理超過 ${RETENTION_DAYS} 天的日誌"
echo "  ⏳ 下次清理時間：明天凌晨 3:00"
echo ""
echo "注意事項："
echo "  - 現有的舊日誌不會被立即刪除"
echo "  - 只有在下次定時清理時才會按新規則執行"
echo "  - 如需立即清理，請手動執行清理任務"
echo ""
echo "相關命令："
echo "  查看日誌: docker compose logs celery_beat -f"
echo "  檢查任務: docker exec nt-django celery -A network_toolbox inspect active"
echo ""

exit 0
