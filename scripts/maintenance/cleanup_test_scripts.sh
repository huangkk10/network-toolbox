#!/bin/bash
# ============================================
# 測試腳本清理自動化腳本
# ============================================

set -e  # 遇到錯誤立即退出

# 顏色定義
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo "================================================"
echo "測試腳本清理工具"
echo "================================================"
echo ""

# 顯示將要刪除的腳本
echo -e "${BLUE}將要刪除的臨時測試腳本：${NC}"
echo ""
SCRIPTS_TO_DELETE=(
    "test_dhcp_raw_log.sh"
    "test_stage2_quick.sh"
    "test_stage2_feasibility.sh"
    "test_server_dropdown_sorting.sh"
    "test_ipxe_improvements.sh"
    "test_ipxe_auto_sync.sh"
    "test_auto_sync.sh"
)

TOTAL_SIZE=0
for script in "${SCRIPTS_TO_DELETE[@]}"; do
    if [ -f "$script" ]; then
        SIZE=$(ls -lh "$script" | awk '{print $5}')
        echo -e "  ${RED}✗${NC} $script ($SIZE)"
        BYTES=$(stat -c%s "$script" 2>/dev/null || stat -f%z "$script" 2>/dev/null || echo 0)
        TOTAL_SIZE=$((TOTAL_SIZE + BYTES))
    else
        echo -e "  ${YELLOW}⚠${NC} $script (不存在)"
    fi
done

echo ""
echo -e "${BLUE}總大小：${NC} $(numfmt --to=iec $TOTAL_SIZE 2>/dev/null || echo "$TOTAL_SIZE bytes")"
echo ""

# 顯示將要遷移的腳本
echo -e "${BLUE}將要遷移的測試腳本：${NC}"
echo ""
echo -e "  ${GREEN}→${NC} test_auto_ipxe_sync.sh → tests/integration/ipxe/"
echo -e "  ${GREEN}→${NC} test_auto_switch_sync.sh → tests/integration/network/"
echo -e "  ${GREEN}→${NC} test_ipxe_ssh_verification.sh → tests/integration/ipxe/"
echo ""

# 確認操作
echo -e "${YELLOW}⚠️  警告：此操作將刪除以上測試腳本${NC}"
echo -e "${YELLOW}   (這些是臨時開發測試腳本，功能已實現並驗證完畢)${NC}"
echo ""
read -p "是否繼續？[y/N] " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}已取消操作${NC}"
    exit 0
fi

echo ""
echo "================================================"
echo "開始清理..."
echo "================================================"
echo ""

# 選項：是否創建備份
read -p "是否創建備份？[Y/n] " -n 1 -r
echo ""
CREATE_BACKUP=true
if [[ $REPLY =~ ^[Nn]$ ]]; then
    CREATE_BACKUP=false
fi

# 創建備份
if [ "$CREATE_BACKUP" = true ]; then
    echo -e "${BLUE}[1/4] 創建備份目錄...${NC}"
    BACKUP_DIR="archive/old_test_scripts_$(date +%Y%m%d_%H%M%S)"
    mkdir -p "$BACKUP_DIR"
    
    for script in "${SCRIPTS_TO_DELETE[@]}"; do
        if [ -f "$script" ]; then
            cp "$script" "$BACKUP_DIR/"
            echo -e "  ${GREEN}✓${NC} 已備份: $script"
        fi
    done
    echo ""
fi

# 遷移測試腳本
echo -e "${BLUE}[2/4] 遷移測試腳本...${NC}"

# 創建目標目錄
mkdir -p tests/integration/ipxe/
mkdir -p tests/integration/network/

# 遷移 iPXE 相關測試
if [ -f "test_auto_ipxe_sync.sh" ]; then
    mv test_auto_ipxe_sync.sh tests/integration/ipxe/test_auto_sync_integration.sh
    echo -e "  ${GREEN}✓${NC} test_auto_ipxe_sync.sh → tests/integration/ipxe/"
fi

if [ -f "test_ipxe_ssh_verification.sh" ]; then
    mv test_ipxe_ssh_verification.sh tests/integration/ipxe/test_ssh_verification.sh
    echo -e "  ${GREEN}✓${NC} test_ipxe_ssh_verification.sh → tests/integration/ipxe/"
fi

# 遷移 Switch 相關測試
if [ -f "test_auto_switch_sync.sh" ]; then
    mv test_auto_switch_sync.sh tests/integration/network/test_switch_sync_integration.sh
    echo -e "  ${GREEN}✓${NC} test_auto_switch_sync.sh → tests/integration/network/"
fi

echo ""

# 刪除臨時測試腳本
echo -e "${BLUE}[3/4] 刪除臨時測試腳本...${NC}"
DELETED_COUNT=0
for script in "${SCRIPTS_TO_DELETE[@]}"; do
    if [ -f "$script" ]; then
        rm -f "$script"
        echo -e "  ${RED}✗${NC} 已刪除: $script"
        DELETED_COUNT=$((DELETED_COUNT + 1))
    fi
done

if [ $DELETED_COUNT -eq 0 ]; then
    echo -e "  ${YELLOW}⚠${NC} 沒有找到需要刪除的腳本"
fi

echo ""

# 驗證清理結果
echo -e "${BLUE}[4/4] 驗證清理結果...${NC}"

# 檢查根目錄的測試腳本
REMAINING_TESTS=$(ls test_*.sh 2>/dev/null | wc -l)
echo -e "  剩餘測試腳本: ${REMAINING_TESTS} 個"

if [ -f "verify_all.sh" ]; then
    echo -e "  ${GREEN}✓${NC} verify_all.sh (保留)"
fi

# 檢查遷移的腳本
MIGRATED_COUNT=$(find tests/integration/ -name "*.sh" 2>/dev/null | wc -l)
echo -e "  已遷移測試: ${MIGRATED_COUNT} 個"

echo ""
echo "================================================"
echo -e "${GREEN}清理完成！${NC}"
echo "================================================"
echo ""

if [ "$CREATE_BACKUP" = true ]; then
    echo -e "📦 備份位置: ${BACKUP_DIR}"
    echo ""
fi

echo "📊 統計："
echo -e "  ${RED}✗${NC} 已刪除: ${DELETED_COUNT} 個腳本"
echo -e "  ${GREEN}→${NC} 已遷移: 3 個腳本"
echo -e "  ${BLUE}✓${NC} 保留: verify_all.sh"
echo ""

echo "🔍 建議的後續步驟："
echo "  1. 執行系統驗證："
echo "     ./verify_all.sh"
echo ""
echo "  2. 檢查 Docker 服務："
echo "     docker compose ps"
echo ""
echo "  3. 測試遷移的腳本："
echo "     ./tests/integration/ipxe/test_auto_sync_integration.sh"
echo ""
echo "  4. 更新相關文檔："
echo "     - README.md"
echo "     - tests/README.md"
echo ""

if [ "$CREATE_BACKUP" = true ]; then
    echo "💡 提示："
    echo "  如需恢復，請從備份目錄複製："
    echo "  cp $BACKUP_DIR/<script_name> ."
    echo ""
fi
