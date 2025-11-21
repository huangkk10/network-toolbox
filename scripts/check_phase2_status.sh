#!/bin/bash
# ============================================================================
# Phase 2 監控檢查腳本
# 用途：快速檢查 Jenkins 資料一致性自動維護系統的運作狀態
# 創建日期：2025-11-21
# ============================================================================

set -e

# 顏色定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo "========================================================================"
echo "🔍 Phase 2 Jenkins 資料一致性監控檢查"
echo "========================================================================"
echo ""

# ============================================================================
# 1. 檢查 Celery Beat 服務狀態
# ============================================================================
echo -e "${BLUE}📊 1. 檢查 Celery Beat 服務狀態${NC}"
echo "------------------------------------------------------------------------"

CELERY_BEAT_STATUS=$(docker exec nt-django supervisorctl status celery-beat 2>&1 || echo "FAILED")

if echo "$CELERY_BEAT_STATUS" | grep -q "RUNNING"; then
    echo -e "${GREEN}✅ Celery Beat 服務運行中${NC}"
else
    echo -e "${RED}❌ Celery Beat 服務未運行！${NC}"
    echo "   狀態: $CELERY_BEAT_STATUS"
fi
echo ""

# ============================================================================
# 2. 檢查定時任務排程配置
# ============================================================================
echo -e "${BLUE}📅 2. 檢查 Phase 2 定時任務排程${NC}"
echo "------------------------------------------------------------------------"

SCHEDULE_CHECK=$(docker exec nt-django python manage.py shell -c "
from network_toolbox.celery import app
import json

beat_schedule = app.conf.beat_schedule

# 查找 Phase 2 相關任務
phase2_tasks = {
    k: {
        'schedule': str(v['schedule']),
        'auto_cleanup': v.get('kwargs', {}).get('auto_cleanup', 'N/A')
    }
    for k, v in beat_schedule.items()
    if 'validate-jenkins-data' in k or 'cleanup-orphaned-jenkins-data' in k
}

print(json.dumps(phase2_tasks, indent=2))
" 2>&1)

if echo "$SCHEDULE_CHECK" | grep -q "validate-jenkins-data-daily"; then
    echo -e "${GREEN}✅ 找到 Phase 2 定時任務${NC}"
    echo "$SCHEDULE_CHECK" | python3 -m json.tool 2>/dev/null || echo "$SCHEDULE_CHECK"
else
    echo -e "${RED}❌ 未找到 Phase 2 定時任務！${NC}"
fi
echo ""

# ============================================================================
# 3. 檢查最近的驗證/清理任務執行記錄
# ============================================================================
echo -e "${BLUE}📝 3. 檢查最近的任務執行記錄（最近 24 小時）${NC}"
echo "------------------------------------------------------------------------"

echo "🔍 驗證任務 (validate_jenkins_data):"
VALIDATE_LOGS=$(grep "validate_jenkins_data" logs/django.log 2>/dev/null | tail -5 || echo "尚無執行記錄")
if [ "$VALIDATE_LOGS" = "尚無執行記錄" ]; then
    echo -e "${YELLOW}   ⏳ 尚未執行（預計明天 03:00 首次執行）${NC}"
else
    echo "$VALIDATE_LOGS"
fi
echo ""

echo "🗑️  清理任務 (cleanup-orphaned-jenkins-data-weekly):"
CLEANUP_LOGS=$(grep "cleanup-orphaned-jenkins-data-weekly" logs/django.log 2>/dev/null | tail -5 || echo "尚無執行記錄")
if [ "$CLEANUP_LOGS" = "尚無執行記錄" ]; then
    echo -e "${YELLOW}   ⏳ 尚未執行（預計週日 04:00 首次執行）${NC}"
else
    echo "$CLEANUP_LOGS"
fi
echo ""

# ============================================================================
# 4. 手動執行驗證任務（乾運行模式）
# ============================================================================
echo -e "${BLUE}🧪 4. 手動執行驗證任務（檢查當前狀態）${NC}"
echo "------------------------------------------------------------------------"

MANUAL_CHECK=$(docker exec nt-django python manage.py shell -c "
from api.tasks import validate_jenkins_data
import json

print('⏳ 執行驗證任務（auto_cleanup=False）...')
result = validate_jenkins_data(auto_cleanup=False)

print(json.dumps({
    '檢查伺服器': result['servers_checked'],
    '檢查 Jobs': result['total_jobs_checked'],
    '檢查 Builds': result['total_builds_checked'],
    '孤立 Jobs': result['orphaned_jobs_found'],
    '孤立 Builds': result['orphaned_builds_found'],
    '受保護項目': result['skipped_recent'],
    '執行時間': f\"{result['duration']:.2f} 秒\"
}, indent=2, ensure_ascii=False))
" 2>&1)

echo "$MANUAL_CHECK"
echo ""

# ============================================================================
# 5. 檢查 Django 配置
# ============================================================================
echo -e "${BLUE}⚙️  5. 檢查 JENKINS_CLEANUP_CONFIG 配置${NC}"
echo "------------------------------------------------------------------------"

CONFIG_CHECK=$(docker exec nt-django python manage.py shell -c "
from django.conf import settings
import json

config = getattr(settings, 'JENKINS_CLEANUP_CONFIG', {})
print(json.dumps(config, indent=2, ensure_ascii=False))
" 2>&1)

if echo "$CONFIG_CHECK" | grep -q "keep_recent_days"; then
    echo -e "${GREEN}✅ 配置已載入${NC}"
    echo "$CONFIG_CHECK" | python3 -m json.tool 2>/dev/null || echo "$CONFIG_CHECK"
else
    echo -e "${RED}❌ 配置未載入！${NC}"
fi
echo ""

# ============================================================================
# 6. 檢查資料庫當前狀態
# ============================================================================
echo -e "${BLUE}💾 6. 檢查資料庫當前狀態${NC}"
echo "------------------------------------------------------------------------"

DB_STATUS=$(docker exec nt-django python manage.py shell -c "
from api.models import JenkinsServer, JenkinsJob, JenkinsBuild
from django.utils import timezone
from datetime import timedelta

servers = JenkinsServer.objects.filter(is_active=True).count()
jobs = JenkinsJob.objects.count()
builds = JenkinsBuild.objects.count()

# 最近 7 天的 Builds
seven_days_ago = timezone.now() - timedelta(days=7)
recent_builds = JenkinsBuild.objects.filter(last_sync_at__gte=seven_days_ago).count()

print(f'Jenkins Servers: {servers} 個（在線）')
print(f'總 Jobs: {jobs} 個')
print(f'總 Builds: {builds} 個')
print(f'最近 7 天同步的 Builds: {recent_builds} 個')
" 2>&1)

echo "$DB_STATUS"
echo ""

# ============================================================================
# 總結
# ============================================================================
echo "========================================================================"
echo -e "${GREEN}✅ Phase 2 監控檢查完成${NC}"
echo "========================================================================"
echo ""
echo "📌 下一步行動："
echo "   1. 明天（11-22）03:00 後執行此腳本，查看第一次驗證任務結果"
echo "   2. 週日（11-24）04:00 後執行此腳本，查看第一次清理任務結果"
echo "   3. 如發現異常，查看詳細日誌："
echo "      tail -f logs/django.log | grep 'validate_jenkins_data\\|cleanup-orphaned'"
echo ""
echo "💡 提示："
echo "   - 孤立 Jobs/Builds = 0：表示資料一致性良好"
echo "   - 受保護項目 > 0：表示保護機制正常運作"
echo "   - 執行時間 < 5 秒：表示性能良好"
echo ""
