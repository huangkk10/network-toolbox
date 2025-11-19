#!/bin/bash
#
# NTP 時間同步修復腳本
# 用途：配置系統使用內部 NTP 伺服器並強制同步時間
#

set -e

# 顏色定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# NTP 伺服器配置
NTP_SERVER="10.10.10.51"
FALLBACK_NTP="time.google.com time.cloudflare.com"
TIMESYNCD_CONF="/etc/systemd/timesyncd.conf"
TIMESYNCD_CONF_BACKUP="/etc/systemd/timesyncd.conf.backup-$(date +%Y%m%d-%H%M%S)"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}NTP 時間同步修復工具${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# 檢查是否為 root 用戶
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}錯誤：此腳本需要 root 權限執行${NC}"
    echo "請使用: sudo $0"
    exit 1
fi

# 1. 顯示當前時間狀態
echo -e "${YELLOW}[1/5] 檢查當前時間狀態...${NC}"
echo "-----------------------------------"
timedatectl status
echo ""

# 2. 備份原始配置
echo -e "${YELLOW}[2/5] 備份原始配置...${NC}"
if [ -f "$TIMESYNCD_CONF" ]; then
    cp "$TIMESYNCD_CONF" "$TIMESYNCD_CONF_BACKUP"
    echo -e "${GREEN}✓ 配置已備份至: $TIMESYNCD_CONF_BACKUP${NC}"
else
    echo -e "${YELLOW}⚠ 配置檔案不存在，將創建新檔案${NC}"
fi
echo ""

# 3. 配置 NTP 伺服器
echo -e "${YELLOW}[3/5] 配置 NTP 伺服器...${NC}"
cat > "$TIMESYNCD_CONF" << EOF
#  This file is part of systemd.
#
#  systemd is free software; you can redistribute it and/or modify it under the
#  terms of the GNU Lesser General Public License as published by the Free
#  Software Foundation; either version 2.1 of the License, or (at your option)
#  any later version.
#
# Entries in this file show the compile time defaults. Local configuration
# should be created by either modifying this file, or by creating "drop-ins" in
# the timesyncd.conf.d/ subdirectory. The latter is generally recommended.
# Defaults can be restored by simply deleting this file and all drop-ins.
#
# See timesyncd.conf(5) for details.

[Time]
# 主要 NTP 伺服器（內部）
NTP=$NTP_SERVER

# 備用 NTP 伺服器（公開）
FallbackNTP=$FALLBACK_NTP

# 最大根距離（秒）
#RootDistanceMaxSec=5

# 輪詢間隔（秒）
#PollIntervalMinSec=32
#PollIntervalMaxSec=2048
EOF

echo -e "${GREEN}✓ NTP 伺服器已配置為: $NTP_SERVER${NC}"
echo -e "${GREEN}✓ 備用 NTP 伺服器: $FALLBACK_NTP${NC}"
echo ""

# 4. 重啟 systemd-timesyncd 服務
echo -e "${YELLOW}[4/5] 重啟 systemd-timesyncd 服務...${NC}"
systemctl restart systemd-timesyncd
systemctl enable systemd-timesyncd
echo -e "${GREEN}✓ systemd-timesyncd 服務已重啟並啟用${NC}"
echo ""

# 等待服務啟動
sleep 2

# 5. 驗證時間同步
echo -e "${YELLOW}[5/5] 驗證時間同步狀態...${NC}"
echo "-----------------------------------"

# 等待最多 30 秒讓時間同步完成
MAX_WAIT=30
WAITED=0
SYNC_SUCCESS=false

while [ $WAITED -lt $MAX_WAIT ]; do
    SYNC_STATUS=$(timedatectl status | grep "System clock synchronized" | awk '{print $4}')
    
    if [ "$SYNC_STATUS" = "yes" ]; then
        SYNC_SUCCESS=true
        break
    fi
    
    echo -e "${BLUE}等待時間同步... ($WAITED/$MAX_WAIT 秒)${NC}"
    sleep 5
    WAITED=$((WAITED + 5))
done

echo ""
timedatectl status
echo ""

if [ "$SYNC_SUCCESS" = true ]; then
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}✓ 時間同步成功！${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo ""
    
    # 顯示 NTP 同步詳情
    echo -e "${BLUE}查詢 NTP 伺服器狀態...${NC}"
    systemctl status systemd-timesyncd --no-pager | grep -A 5 "Status:"
    echo ""
    
    # 測試與 NTP 伺服器的連接
    echo -e "${BLUE}測試與 NTP 伺服器的時間偏移...${NC}"
    docker exec nt-django python -c "
import ntplib
import time
try:
    c = ntplib.NTPClient()
    response = c.request('$NTP_SERVER', version=4, timeout=5)
    offset_ms = response.offset * 1000
    print(f'NTP 伺服器: $NTP_SERVER')
    print(f'時間偏移: {offset_ms:.2f} ms')
    print(f'Stratum: {response.stratum}')
    
    if abs(offset_ms) < 50:
        print('狀態: ✓ 優秀（< 50 ms）')
    elif abs(offset_ms) < 200:
        print('狀態: ✓ 良好（< 200 ms）')
    elif abs(offset_ms) < 1000:
        print('狀態: ⚠ 警告（< 1000 ms）')
    else:
        print('狀態: ✗ 錯誤（> 1000 ms）')
except Exception as e:
    print(f'測試失敗: {e}')
" 2>/dev/null || echo -e "${YELLOW}⚠ 無法測試 NTP 偏移（Django 容器可能未運行）${NC}"
    
    echo ""
    echo -e "${GREEN}後續步驟：${NC}"
    echo "1. 訪問 Web 介面查看 NTP 分析頁面"
    echo "2. 確認時間偏移已降低到正常範圍（< 200 ms）"
    echo "3. 如果問題持續，請查看文檔："
    echo "   docs/troubleshooting/NTP_OFFSET_ANALYSIS.md"
    
else
    echo -e "${RED}========================================${NC}"
    echo -e "${RED}✗ 時間同步失敗或超時${NC}"
    echo -e "${RED}========================================${NC}"
    echo ""
    echo -e "${YELLOW}可能的原因：${NC}"
    echo "1. 無法連接到 NTP 伺服器 $NTP_SERVER"
    echo "2. 網路連接問題"
    echo "3. NTP 服務未正確啟動"
    echo ""
    echo -e "${YELLOW}建議的排查步驟：${NC}"
    echo "1. 測試 NTP 伺服器連接："
    echo "   ping $NTP_SERVER"
    echo ""
    echo "2. 檢查服務日誌："
    echo "   journalctl -u systemd-timesyncd -n 50"
    echo ""
    echo "3. 手動測試 NTP 連接："
    echo "   sudo systemctl stop systemd-timesyncd"
    echo "   sudo ntpdate $NTP_SERVER"
    echo "   sudo systemctl start systemd-timesyncd"
    echo ""
    echo "4. 查看完整文檔："
    echo "   docs/troubleshooting/NTP_OFFSET_ANALYSIS.md"
fi

echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}腳本執行完成${NC}"
echo -e "${BLUE}========================================${NC}"
