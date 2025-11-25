#!/bin/bash

###############################################################################
# 主機 NTP 時間同步設置腳本
# 
# 功能：
# 1. 檢查當前時間同步狀態
# 2. 備份現有配置
# 3. 配置 systemd-timesyncd
# 4. 執行首次強制同步
# 5. 驗證同步結果
#
# 使用方法：
#   sudo ./scripts/setup_ntp_sync.sh
#
# 作者：Network Toolbox Team
# 日期：2025-11-25
###############################################################################

set -e  # 遇到錯誤立即停止

# 顏色定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# NTP 伺服器配置
NTP_SERVER="10.10.10.51"
FALLBACK_NTP="time.google.com time.cloudflare.com"

# 配置文件路徑
TIMESYNCD_CONF="/etc/systemd/timesyncd.conf"
BACKUP_CONF="${TIMESYNCD_CONF}.backup.$(date +%Y%m%d_%H%M%S)"

###############################################################################
# 輔助函數
###############################################################################

print_header() {
    echo ""
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

check_root() {
    if [[ $EUID -ne 0 ]]; then
        print_error "此腳本需要 root 權限執行"
        echo "請使用: sudo $0"
        exit 1
    fi
}

###############################################################################
# 步驟 1: 檢查當前狀態
###############################################################################

check_current_status() {
    print_header "步驟 1: 檢查當前時間同步狀態"
    
    echo ""
    echo "🕐 當前系統時間："
    date
    
    echo ""
    echo "📊 時間同步狀態："
    timedatectl status | grep -E "synchronized|NTP service"
    
    echo ""
    echo "🌐 NTP 伺服器狀態："
    if command -v timedatectl &> /dev/null; then
        timedatectl timesync-status 2>/dev/null || timedatectl show-timesync --all | grep -E "Server|Packet"
    fi
    
    echo ""
    echo "📡 測試 NTP 伺服器連線："
    if ping -c 3 -W 2 "$NTP_SERVER" > /dev/null 2>&1; then
        print_success "可以 ping 通 $NTP_SERVER"
        ping -c 3 "$NTP_SERVER" | tail -2
    else
        print_error "無法 ping 通 $NTP_SERVER"
        exit 1
    fi
    
    echo ""
    read -p "按 Enter 繼續..."
}

###############################################################################
# 步驟 2: 備份現有配置
###############################################################################

backup_config() {
    print_header "步驟 2: 備份現有配置"
    
    if [[ -f "$TIMESYNCD_CONF" ]]; then
        cp "$TIMESYNCD_CONF" "$BACKUP_CONF"
        print_success "配置已備份到: $BACKUP_CONF"
    else
        print_warning "配置文件不存在，將創建新文件"
    fi
}

###############################################################################
# 步驟 3: 配置 systemd-timesyncd
###############################################################################

configure_timesyncd() {
    print_header "步驟 3: 配置 systemd-timesyncd"
    
    cat > "$TIMESYNCD_CONF" << EOF
#  systemd-timesyncd 配置文件
#  由 Network Toolbox 自動生成
#  生成時間: $(date)

[Time]
# 主要 NTP 伺服器（內部）
NTP=$NTP_SERVER

# 備用 NTP 伺服器（公開）
FallbackNTP=$FALLBACK_NTP

# 最大根距離（秒）- 放寬限制以允許較大的時間偏移
RootDistanceMaxSec=10

# 輪詢間隔（秒）- 縮短間隔加快同步速度
PollIntervalMinSec=32
PollIntervalMaxSec=1024
EOF
    
    print_success "配置文件已更新"
    echo ""
    echo "📄 新配置內容："
    cat "$TIMESYNCD_CONF" | grep -v "^#" | grep -v "^$"
    
    echo ""
    read -p "按 Enter 繼續..."
}

###############################################################################
# 步驟 4: 執行首次強制同步
###############################################################################

force_sync() {
    print_header "步驟 4: 執行首次強制同步"
    
    # 檢查是否安裝 ntpdate
    if ! command -v ntpdate &> /dev/null; then
        print_warning "未安裝 ntpdate，正在安裝..."
        apt-get update -qq
        apt-get install -y ntpdate
    fi
    
    echo ""
    print_info "停止 systemd-timesyncd 服務..."
    systemctl stop systemd-timesyncd
    
    echo ""
    print_info "使用 ntpdate 強制同步時間（可能需要幾秒鐘）..."
    
    # 顯示同步前的時間
    echo ""
    echo "⏰ 同步前時間: $(date)"
    
    # 執行同步
    if ntpdate -u "$NTP_SERVER"; then
        print_success "時間同步成功！"
    else
        print_error "ntpdate 同步失敗，嘗試使用備用方案..."
        
        # 嘗試公開 NTP
        if ntpdate -u time.google.com; then
            print_success "使用公開 NTP (time.google.com) 同步成功"
        else
            print_error "時間同步失敗"
            exit 1
        fi
    fi
    
    # 顯示同步後的時間
    echo ""
    echo "⏰ 同步後時間: $(date)"
    
    echo ""
    print_info "重新啟動 systemd-timesyncd 服務..."
    systemctl restart systemd-timesyncd
    
    echo ""
    print_info "啟用開機自動啟動..."
    systemctl enable systemd-timesyncd
    
    echo ""
    print_success "服務已重新啟動"
    
    echo ""
    print_info "等待 5 秒讓服務穩定..."
    sleep 5
}

###############################################################################
# 步驟 5: 驗證同步結果
###############################################################################

verify_sync() {
    print_header "步驟 5: 驗證同步結果"
    
    echo ""
    echo "📊 時間同步狀態："
    timedatectl status
    
    echo ""
    echo "🌐 NTP 同步詳情："
    timedatectl timesync-status 2>/dev/null || timedatectl show-timesync --all
    
    echo ""
    echo "📝 服務狀態（最近 10 行日誌）："
    systemctl status systemd-timesyncd --no-pager -n 10
    
    echo ""
    echo "🔍 檢查是否同步成功..."
    
    # 檢查同步狀態
    if timedatectl status | grep -q "System clock synchronized: yes"; then
        print_success "系統時鐘已同步 ✅"
    else
        print_warning "系統時鐘尚未同步，請稍後檢查"
    fi
    
    # 檢查 Packet count
    PACKET_COUNT=$(timedatectl timesync-status 2>/dev/null | grep "Packet count" | awk '{print $3}' || echo "0")
    if [[ "$PACKET_COUNT" -gt 0 ]]; then
        print_success "已成功與 NTP 伺服器通訊 (Packet count: $PACKET_COUNT) ✅"
    else
        print_warning "尚未成功與 NTP 伺服器通訊，請稍後檢查"
    fi
}

###############################################################################
# 步驟 6: 驗證 Docker 容器時間
###############################################################################

verify_docker_time() {
    print_header "步驟 6: 驗證 Docker 容器時間"
    
    # 檢查 Docker 是否運行
    if ! command -v docker &> /dev/null; then
        print_warning "Docker 未安裝，跳過容器時間檢查"
        return
    fi
    
    # 檢查 nt-django 容器是否運行
    if ! docker ps --format '{{.Names}}' | grep -q "nt-django"; then
        print_warning "nt-django 容器未運行，跳過容器時間檢查"
        return
    fi
    
    echo ""
    echo "🐳 Docker 容器時間："
    CONTAINER_TIME=$(docker exec nt-django date '+%Y-%m-%d %H:%M:%S %Z')
    echo "   容器時間: $CONTAINER_TIME"
    
    echo ""
    HOST_TIME=$(date '+%Y-%m-%d %H:%M:%S %Z')
    echo "🖥️  主機時間："
    echo "   主機時間: $HOST_TIME"
    
    echo ""
    if [[ "${CONTAINER_TIME%% *}" == "${HOST_TIME%% *}" ]]; then
        print_success "容器時間與主機時間一致 ✅"
    else
        print_warning "容器時間與主機時間可能有差異，請檢查"
    fi
}

###############################################################################
# 步驟 7: 後續檢查建議
###############################################################################

show_recommendations() {
    print_header "步驟 7: 後續檢查建議"
    
    echo ""
    echo "✅ NTP 時間同步已設置完成！"
    echo ""
    echo "📌 建議後續操作："
    echo ""
    echo "1️⃣  監控同步狀態（5-10 分鐘後）："
    echo "   timedatectl timesync-status"
    echo ""
    echo "2️⃣  查看服務日誌："
    echo "   journalctl -u systemd-timesyncd -n 50"
    echo ""
    echo "3️⃣  查看 Django 應用的 NTP 檢測記錄："
    echo "   docker exec nt-django python manage.py shell -c \\"
    echo "   \"from api.models import NTPSyncLog; \\"
    echo "   print(NTPSyncLog.objects.order_by('-timestamp').first())\""
    echo ""
    echo "4️⃣  在 Network Toolbox 前端查看："
    echo "   訪問「系統監控」頁面 → 查看「NTP 時間同步檢測」任務"
    echo ""
    echo "⚠️  注意事項："
    echo "   - 首次同步後，時間偏移應該 < 100 ms"
    echo "   - 如果仍有問題，請查看配置文檔："
    echo "     docs/features/ntp-sync/HOST_NTP_SETUP_GUIDE.md"
    echo ""
    echo "📄 配置備份位置: $BACKUP_CONF"
    echo ""
}

###############################################################################
# 主程序
###############################################################################

main() {
    clear
    
    print_header "Network Toolbox - NTP 時間同步設置"
    
    echo ""
    echo "此腳本將："
    echo "  1. 檢查當前時間同步狀態"
    echo "  2. 備份現有配置"
    echo "  3. 配置 systemd-timesyncd (NTP: $NTP_SERVER)"
    echo "  4. 執行首次強制同步"
    echo "  5. 驗證同步結果"
    echo "  6. 驗證 Docker 容器時間"
    echo ""
    
    read -p "是否繼續？(y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "已取消"
        exit 0
    fi
    
    # 檢查 root 權限
    check_root
    
    # 執行各步驟
    check_current_status
    backup_config
    configure_timesyncd
    force_sync
    verify_sync
    verify_docker_time
    show_recommendations
    
    print_success "完成！"
}

# 執行主程序
main
