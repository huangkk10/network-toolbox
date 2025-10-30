#!/bin/bash

# DHCP Analytics URL 導航功能測試腳本
# 日期: 2025-10-30

echo "=========================================="
echo "DHCP Analytics URL 導航功能測試"
echo "=========================================="
echo ""

BASE_URL="http://localhost"

echo "📋 測試清單："
echo ""

echo "✅ 測試 1: 彙總視圖 URL"
echo "   訪問: ${BASE_URL}/dhcp-analytics"
echo "   訪問: ${BASE_URL}/dhcp-analytics/overview"
echo "   訪問: ${BASE_URL}/dhcp-analytics/logs"
echo "   訪問: ${BASE_URL}/dhcp-analytics/leases"
echo "   訪問: ${BASE_URL}/dhcp-analytics/statistics"
echo "   訪問: ${BASE_URL}/dhcp-analytics/config"
echo ""

echo "✅ 測試 2: 單一 Server URL"
echo "   訪問: ${BASE_URL}/dhcp-analytics/server/1/overview"
echo "   訪問: ${BASE_URL}/dhcp-analytics/server/1/logs"
echo "   訪問: ${BASE_URL}/dhcp-analytics/server/1/leases"
echo "   訪問: ${BASE_URL}/dhcp-analytics/server/1/statistics"
echo "   訪問: ${BASE_URL}/dhcp-analytics/server/1/config"
echo ""

echo "✅ 測試 3: 刷新頁面測試"
echo "   1. 導航到 ${BASE_URL}/dhcp-analytics/server/1/logs"
echo "   2. 按 F5 刷新頁面"
echo "   3. 確認頁面保持在 Server 1 的日誌查看 Tab"
echo ""

echo "✅ 測試 4: 瀏覽器導航測試"
echo "   1. 從 overview 依序導航到多個頁面"
echo "   2. 使用瀏覽器「後退」按鈕"
echo "   3. 使用瀏覽器「前進」按鈕"
echo "   4. 確認導航歷史正常運作"
echo ""

echo "✅ 測試 5: 直接訪問 URL"
echo "   1. 在瀏覽器位址列輸入完整 URL"
echo "   2. 按 Enter"
echo "   3. 確認直接導向正確頁面"
echo ""

echo "✅ 測試 6: 麵包屑導航測試"
echo "   1. 導航到 ${BASE_URL}/dhcp-analytics/server/1/logs"
echo "   2. 檢查麵包屑顯示："
echo "      Home > DHCP Server 分析 > [Server IP] > 日誌查看"
echo "   3. 點擊「DHCP Server 分析」"
echo "   4. 確認導向 ${BASE_URL}/dhcp-analytics/overview"
echo "   5. 點擊「Home」"
echo "   6. 確認導向 ${BASE_URL}/dashboard"
echo ""

echo "✅ 測試 7: Tab 切換（保持 Server）"
echo "   1. 當前: ${BASE_URL}/dhcp-analytics/server/1/logs"
echo "   2. 點擊「租約管理」Tab"
echo "   3. 確認 URL 變為: ${BASE_URL}/dhcp-analytics/server/1/leases"
echo "   4. 確認 Server 下拉選單仍顯示 Server 1"
echo ""

echo "✅ 測試 8: Server 切換（保持 Tab）"
echo "   1. 當前: ${BASE_URL}/dhcp-analytics/server/1/logs"
echo "   2. 從下拉選單選擇 Server 2"
echo "   3. 確認 URL 變為: ${BASE_URL}/dhcp-analytics/server/2/logs"
echo "   4. 確認仍在「日誌查看」Tab"
echo ""

echo "✅ 測試 9: 切換到所有 Server（彙總）"
echo "   1. 當前: ${BASE_URL}/dhcp-analytics/server/1/logs"
echo "   2. 從下拉選單選擇「所有 Server」"
echo "   3. 確認 URL 變為: ${BASE_URL}/dhcp-analytics/logs"
echo "   4. 確認仍在「日誌查看」Tab"
echo ""

echo "✅ 測試 10: 動態頁面標題"
echo "   1. 導航到不同頁面"
echo "   2. 檢查瀏覽器分頁標題是否正確更新"
echo "   預期格式: [Tab名稱] - [Server名稱] | DHCP Server 分析"
echo ""

echo "=========================================="
echo "測試完成後，請確認以上所有功能正常運作"
echo "=========================================="
echo ""

# 提供快速測試的 curl 命令（檢查路由是否存在）
echo "🔧 快速檢查路由（curl 測試）："
echo ""

ROUTES=(
    "/dhcp-analytics"
    "/dhcp-analytics/overview"
    "/dhcp-analytics/logs"
    "/dhcp-analytics/server/1/overview"
    "/dhcp-analytics/server/1/logs"
)

for route in "${ROUTES[@]}"; do
    echo "正在檢查: ${BASE_URL}${route}"
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "${BASE_URL}${route}")
    if [ "$HTTP_CODE" -eq 200 ]; then
        echo "  ✅ 成功 (HTTP $HTTP_CODE)"
    else
        echo "  ❌ 失敗 (HTTP $HTTP_CODE)"
    fi
done

echo ""
echo "=========================================="
echo "提示："
echo "- 請使用瀏覽器手動測試所有功能"
echo "- 測試時請開啟瀏覽器開發者工具（F12）"
echo "- 觀察 Console 和 Network 面板"
echo "=========================================="
