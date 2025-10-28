#!/bin/bash
# IPXE 日誌自動化任務配置腳本

echo "========================================="
echo "  IPXE 日誌自動化 Cron 設置"
echo "========================================="
echo ""

# 定義 cron 任務
CRON_COLLECT="*/10 * * * * docker exec nt-django python manage.py collect_ipxe_logs --limit 1000 >> /var/log/ipxe_collect.log 2>&1"
CRON_CLEANUP="0 2 * * * docker exec nt-django python manage.py cleanup_ipxe_logs --days 7 >> /var/log/ipxe_cleanup.log 2>&1"

echo "將設置以下 Cron 任務："
echo ""
echo "1. 日誌收集（每 10 分鐘）:"
echo "   $CRON_COLLECT"
echo ""
echo "2. 日誌清理（每天凌晨 2 點）:"
echo "   $CRON_CLEANUP"
echo ""

# 檢查是否已存在
if crontab -l 2>/dev/null | grep -q "collect_ipxe_logs"; then
    echo "⚠️  警告：已存在 IPXE 日誌收集任務"
    echo ""
    read -p "是否要更新現有任務？ (y/N): " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "取消設置"
        exit 0
    fi
    
    # 移除舊任務
    crontab -l 2>/dev/null | grep -v "collect_ipxe_logs" | grep -v "cleanup_ipxe_logs" | crontab -
    echo "✓ 已移除舊任務"
fi

# 添加新任務
(crontab -l 2>/dev/null; echo ""; echo "# IPXE 日誌自動化"; echo "$CRON_COLLECT"; echo "$CRON_CLEANUP") | crontab -

echo ""
echo "✓ Cron 任務設置完成！"
echo ""
echo "當前 Cron 任務："
echo "-------------------"
crontab -l | grep -A 2 "IPXE"
echo ""

# 創建日誌目錄
sudo touch /var/log/ipxe_collect.log
sudo touch /var/log/ipxe_cleanup.log
sudo chmod 666 /var/log/ipxe_collect.log
sudo chmod 666 /var/log/ipxe_cleanup.log

echo "✓ 日誌檔案已創建："
echo "  - /var/log/ipxe_collect.log"
echo "  - /var/log/ipxe_cleanup.log"
echo ""
echo "========================================="
echo "  設置完成！"
echo "========================================="
echo ""
echo "查看日誌收集輸出："
echo "  tail -f /var/log/ipxe_collect.log"
echo ""
echo "查看日誌清理輸出："
echo "  tail -f /var/log/ipxe_cleanup.log"
echo ""
echo "移除 Cron 任務："
echo "  crontab -e"
echo "  （刪除包含 'collect_ipxe_logs' 和 'cleanup_ipxe_logs' 的行）"
echo ""
