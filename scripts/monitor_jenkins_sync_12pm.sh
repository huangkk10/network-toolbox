#!/bin/bash
# 監控 12:00 時的 Jenkins Jobs 同步任務

echo "==================== Jenkins Jobs 同步任務監控 ===================="
echo "當前時間：$(date)"
echo "等待 12:00..."
echo ""

# 等待到 12:00
while true; do
    CURRENT_MINUTE=$(date +%M)
    CURRENT_SECOND=$(date +%S)
    
    if [ "$CURRENT_MINUTE" = "00" ] && [ "$CURRENT_SECOND" -lt "30" ]; then
        echo "✅ 12:00 到了！開始檢查..."
        break
    fi
    
    sleep 1
done

# 等待 5 秒讓任務發送完成
sleep 5

echo ""
echo "【1】檢查 Beat 是否發送了任務："
echo "-----------------------------------------------------------"
docker logs nt-celery-beat --since '2025-11-19T12:00:00' --until '2025-11-19T12:00:10' 2>&1 | grep -i "sync-jenkins-jobs"

echo ""
echo "【2】檢查 Worker 是否收到了任務："
echo "-----------------------------------------------------------"
docker logs nt-celery-worker --since '2025-11-19T12:00:00' --until '2025-11-19T12:00:30' 2>&1 | grep -i "sync_all_jenkins_jobs_task" || echo "❌ Worker 未收到任務"

echo ""
echo "【3】檢查應用程式日誌："
echo "-----------------------------------------------------------"
docker exec nt-django tail -50 /app/logs/django.log | grep -A 10 "12:00:" | grep -i "jenkins" || echo "❌ 應用程式日誌中無 Jenkins sync 記錄"

echo ""
echo "==================== 監控完成 ===================="
