#!/bin/bash
# 驗證 Jenkins Jobs 自動同步修復是否成功

HOUR=$(date +%H)
NEXT_HOUR=$((HOUR + 1))

echo "=========================================="
echo "Jenkins Jobs 自動同步修復驗證"
echo "=========================================="
echo "當前時間：$(date '+%Y-%m-%d %H:%M:%S')"
echo "下一個整點：${NEXT_HOUR}:00"
echo ""

# 等待到下一個整點
echo "⏰ 等待到 ${NEXT_HOUR}:00..."
while true; do
    CURRENT_HOUR=$(date +%H)
    CURRENT_MIN=$(date +%M)
    CURRENT_SEC=$(date +%S)
    
    if [ "$CURRENT_HOUR" = "$NEXT_HOUR" ] && [ "$CURRENT_MIN" = "00" ]; then
        echo "✅ ${NEXT_HOUR}:00 到了！"
        break
    fi
    
    # 顯示倒計時
    REMAINING_MIN=$((59 - 10#$CURRENT_MIN))
    REMAINING_SEC=$((60 - 10#$CURRENT_SEC))
    printf "\r剩餘時間：%02d:%02d" $REMAINING_MIN $REMAINING_SEC
    sleep 1
done

echo ""
echo ""
echo "⏱️  等待 10 秒讓任務執行..."
sleep 10

echo ""
echo "【1】檢查 Beat 是否發送任務"
echo "-----------------------------------------------------------"
docker logs nt-celery-beat --since "$(date '+%Y-%m-%d')T${NEXT_HOUR}:00:00" --until "$(date '+%Y-%m-%d')T${NEXT_HOUR}:00:10" 2>&1 | grep "sync-jenkins-jobs-hourly"
BEAT_RESULT=$?

echo ""
echo "【2】檢查 Worker 是否收到任務"
echo "-----------------------------------------------------------"
docker logs nt-celery-worker --since "$(date '+%Y-%m-%d')T${NEXT_HOUR}:00:00" --until "$(date '+%Y-%m-%d')T${NEXT_HOUR}:01:00" 2>&1 | grep "sync_all_jenkins_jobs_task.*received"
WORKER_RESULT=$?

echo ""
echo "【3】檢查應用程式日誌"
echo "-----------------------------------------------------------"
docker exec nt-django grep "${NEXT_HOUR}:00:" /app/logs/django.log 2>/dev/null | grep "Jenkins Jobs" | tail -5
APP_RESULT=$?

echo ""
echo "=========================================="
echo "驗證結果"
echo "=========================================="

if [ $BEAT_RESULT -eq 0 ]; then
    echo "✅ Beat 已發送任務"
else
    echo "❌ Beat 未發送任務"
fi

if [ $WORKER_RESULT -eq 0 ]; then
    echo "✅ Worker 已收到任務 🎉"
    echo ""
    echo "🎊 修復成功！Jenkins Jobs 自動同步已恢復正常！"
else
    echo "❌ Worker 未收到任務"
    echo ""
    echo "⚠️  修復失敗，需要進一步調查"
fi

if [ $APP_RESULT -eq 0 ]; then
    echo "✅ 應用程式有執行記錄"
else
    echo "⚠️  應用程式日誌中無記錄（可能任務尚未執行完成）"
fi

echo ""
echo "=========================================="
echo "驗證完成：$(date '+%Y-%m-%d %H:%M:%S')"
echo "=========================================="
