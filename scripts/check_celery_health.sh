#!/bin/bash
################################################################################
# Celery Health Check Script
# 用途：監控 Celery Worker 的 Task 註冊狀態，自動修復註冊失敗問題
# 執行頻率：建議每 5 分鐘一次（透過 cron）
# 作者：Network Toolbox Team
# 更新日期：2025-11-06
################################################################################

# 顏色定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 配置
PROJECT_DIR="/home/owner/Codes/network-toolbox"
MIN_EXPECTED_TASKS=15  # 最少應該有 15 個 api.tasks
LOG_FILE="${PROJECT_DIR}/logs/celery_health.log"

# 記錄時間戳
echo "========================================" | tee -a "$LOG_FILE"
echo "[$(date '+%Y-%m-%d %H:%M:%S')] 開始檢查 Celery 健康狀態" | tee -a "$LOG_FILE"

# 切換到專案目錄
cd "$PROJECT_DIR" || exit 1

# 檢查容器是否運行
echo "檢查容器狀態..." | tee -a "$LOG_FILE"
if ! docker ps | grep -q "nt-celery-worker"; then
    echo -e "${RED}❌ Celery Worker 容器未運行！${NC}" | tee -a "$LOG_FILE"
    echo "嘗試啟動容器..." | tee -a "$LOG_FILE"
    docker compose up -d celery_worker celery_beat | tee -a "$LOG_FILE"
    sleep 5
    exit 1
fi

if ! docker ps | grep -q "nt-celery-beat"; then
    echo -e "${RED}❌ Celery Beat 容器未運行！${NC}" | tee -a "$LOG_FILE"
    echo "嘗試啟動容器..." | tee -a "$LOG_FILE"
    docker compose up -d celery_beat | tee -a "$LOG_FILE"
    sleep 5
    exit 1
fi

echo -e "${GREEN}✅ 容器運行中${NC}" | tee -a "$LOG_FILE"

# 檢查 Task 註冊數量（使用 celery inspect 命令）
echo "檢查 Task 註冊狀態..." | tee -a "$LOG_FILE"
TASK_COUNT=$(docker exec nt-celery-worker celery -A network_toolbox inspect registered 2>/dev/null | grep "api.tasks" | wc -l)

# 檢查結果
if [ -z "$TASK_COUNT" ]; then
    echo -e "${RED}❌ 無法獲取 Task 數量（Django 連接失敗）${NC}" | tee -a "$LOG_FILE"
    exit 1
fi

echo "當前註冊的 api.tasks 數量：$TASK_COUNT" | tee -a "$LOG_FILE"

if [ "$TASK_COUNT" -lt "$MIN_EXPECTED_TASKS" ]; then
    echo -e "${RED}❌ Celery Tasks 註冊異常！${NC}" | tee -a "$LOG_FILE"
    echo "   預期：至少 $MIN_EXPECTED_TASKS 個 tasks" | tee -a "$LOG_FILE"
    echo "   實際：只有 $TASK_COUNT 個 tasks" | tee -a "$LOG_FILE"
    echo "" | tee -a "$LOG_FILE"
    echo "🔧 正在重啟 Celery 服務..." | tee -a "$LOG_FILE"
    
    # 重啟服務
    docker compose restart celery_worker celery_beat 2>&1 | tee -a "$LOG_FILE"
    
    # 等待服務啟動
    echo "等待服務啟動（10 秒）..." | tee -a "$LOG_FILE"
    sleep 10
    
    # 再次檢查（使用 celery inspect 命令）
    NEW_TASK_COUNT=$(docker exec nt-celery-worker celery -A network_toolbox inspect registered 2>/dev/null | grep "api.tasks" | wc -l)
    
    if [ "$NEW_TASK_COUNT" -ge "$MIN_EXPECTED_TASKS" ]; then
        echo -e "${GREEN}✅ 重啟成功！Tasks 已恢復：$NEW_TASK_COUNT 個${NC}" | tee -a "$LOG_FILE"
    else
        echo -e "${RED}❌ 重啟失敗！Tasks 仍然異常：$NEW_TASK_COUNT 個${NC}" | tee -a "$LOG_FILE"
        echo "請手動檢查容器日誌：docker compose logs celery_worker" | tee -a "$LOG_FILE"
    fi
    
    exit 1
else
    echo -e "${GREEN}✅ Celery Tasks 狀態正常（$TASK_COUNT 個已註冊）${NC}" | tee -a "$LOG_FILE"
fi

# 檢查最近的 Task 執行記錄（可選）
echo "" | tee -a "$LOG_FILE"
echo "檢查最近 2 小時的 Task 執行記錄..." | tee -a "$LOG_FILE"
LAST_AUTO_STORE=$(docker compose logs celery_worker --since 2h 2>/dev/null | grep "auto_store_workspaces.*SUCCESS" | tail -1)

if [ -z "$LAST_AUTO_STORE" ]; then
    echo -e "${YELLOW}⚠️  警告：最近 2 小時內未發現 auto_store_workspaces 執行記錄${NC}" | tee -a "$LOG_FILE"
    echo "   這可能是正常的（如果系統剛啟動）或表示 Beat 調度問題" | tee -a "$LOG_FILE"
else
    echo -e "${GREEN}✅ 最近的 auto_store_workspaces 執行：${NC}" | tee -a "$LOG_FILE"
    echo "   $LAST_AUTO_STORE" | tee -a "$LOG_FILE"
fi

echo "" | tee -a "$LOG_FILE"
echo "[$(date '+%Y-%m-%d %H:%M:%S')] 健康檢查完成" | tee -a "$LOG_FILE"
echo "========================================" | tee -a "$LOG_FILE"
echo "" >> "$LOG_FILE"
