#!/bin/bash

###############################################################################
# NTP 自動同步功能快速設置腳本
# 
# 功能：
# 1. 設置主機層級的 NTP 同步（systemd-timesyncd）
# 2. 設置應用層級的定時任務（每天凌晨 3 點）
# 3. 驗證配置
#
# 使用方法：
#   sudo ./scripts/setup_ntp_auto_sync.sh
#
# 作者：Network Toolbox Team
# 日期：2025-11-25
###############################################################################

set -e

# 顏色定義
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

print_header() {
    echo ""
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

# 檢查 root 權限
if [[ $EUID -ne 0 ]]; then
    echo "❌ 此腳本需要 root 權限執行"
    echo "請使用: sudo $0"
    exit 1
fi

clear

print_header "Network Toolbox - NTP 自動同步設置"

echo ""
echo "此腳本將設置兩層的 NTP 時間同步："
echo ""
echo "  1️⃣  主機層級："
echo "     - 配置 systemd-timesyncd"
echo "     - 執行首次強制同步"
echo "     - Docker 容器自動繼承主機時間"
echo ""
echo "  2️⃣  應用層級："
echo "     - 設置每天凌晨 3 點的自動同步任務"
echo "     - 智能決策（只有偏移 > 200ms 才同步）"
echo "     - 記錄同步操作到資料庫"
echo ""
echo "⚠️  注意：應用層級同步需要額外配置 sudo 權限"
echo "   如果不需要，可以只設置主機層級同步"
echo ""

read -p "是否繼續？(y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "已取消"
    exit 0
fi

# ============================================================================
# 步驟 1: 主機層級 NTP 同步設置
# ============================================================================

print_header "步驟 1: 主機層級 NTP 同步設置"

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

if [ -f "$SCRIPT_DIR/setup_ntp_sync.sh" ]; then
    print_info "執行主機 NTP 同步設置腳本..."
    bash "$SCRIPT_DIR/setup_ntp_sync.sh"
else
    print_info "找不到 setup_ntp_sync.sh，跳過主機層級設置"
fi

# ============================================================================
# 步驟 2: 應用層級定時任務設置
# ============================================================================

print_header "步驟 2: 應用層級定時任務設置"

echo ""
read -p "是否設置應用層級的每日自動同步任務？(y/N) " -n 1 -r
echo

if [[ $REPLY =~ ^[Yy]$ ]]; then
    print_info "設置 Django Celery 定時任務..."
    
    if docker ps --format '{{.Names}}' | grep -q "nt-django"; then
        docker exec nt-django python backend/setup_ntp_sync_task.py
        print_success "定時任務設置完成"
        
        echo ""
        print_info "⚠️  重要提醒："
        echo "   應用層級同步需要配置 Django 容器的 sudo 權限"
        echo "   詳細步驟請參考："
        echo "   docs/features/ntp-sync/SUDO_PERMISSION_SETUP.md"
        echo ""
        echo "   或者，您可以選擇只使用主機層級同步（已完成）"
        echo "   並將此定時任務設為停用（僅用於監控）"
    else
        print_info "⚠️  Django 容器未運行，無法設置定時任務"
        echo "   請稍後手動執行："
        echo "   docker exec nt-django python backend/setup_ntp_sync_task.py"
    fi
else
    print_info "跳過應用層級定時任務設置"
fi

# ============================================================================
# 總結
# ============================================================================

print_header "設置完成總結"

echo ""
echo "✅ 主機層級 NTP 同步："
timedatectl status | grep -E "synchronized|NTP service" || true

echo ""
echo "📊 NTP 同步狀態："
timedatectl timesync-status 2>/dev/null || timedatectl show-timesync --all | grep -E "Server|Packet" || true

echo ""
echo "📌 後續步驟："
echo ""
echo "1️⃣  驗證主機同步（5-10 分鐘後）："
echo "   timedatectl timesync-status"
echo ""
echo "2️⃣  查看 Django NTP 檢測記錄："
echo "   docker exec nt-django python manage.py shell -c \\"
echo "   \"from api.models import NTPSyncLog; \\"
echo "   print(NTPSyncLog.objects.order_by('-timestamp').first())\""
echo ""
echo "3️⃣  （可選）配置應用層級 sudo 權限："
echo "   參考文檔：docs/features/ntp-sync/SUDO_PERMISSION_SETUP.md"
echo ""
echo "4️⃣  在前端查看："
echo "   訪問「系統監控」頁面 → 查看 NTP 相關任務"
echo ""

print_success "全部完成！"
