#!/bin/bash
# 日誌分析腳本 - Network Toolbox
# 用途：分析日誌檔案，統計錯誤、警告和訪問情況

set -e

LOGS_DIR="./logs"
REPORT_FILE="./logs/analysis_report_$(date +%Y%m%d_%H%M%S).txt"

echo "========================================"
echo "  Network Toolbox 日誌分析工具"
echo "  分析時間: $(date '+%Y-%m-%d %H:%M:%S')"
echo "========================================"
echo ""

# 檢查 logs 目錄
if [ ! -d "$LOGS_DIR" ]; then
    echo "❌ 錯誤：找不到 logs 目錄"
    exit 1
fi

# 開始生成報告
{
    echo "========================================"
    echo "  Network Toolbox 日誌分析報告"
    echo "  生成時間: $(date '+%Y-%m-%d %H:%M:%S')"
    echo "========================================"
    echo ""

    # 1. 日誌檔案概覽
    echo "📁 日誌檔案概覽"
    echo "----------------------------------------"
    if [ -n "$(ls -A $LOGS_DIR/*.log 2>/dev/null)" ]; then
        for file in $LOGS_DIR/*.log; do
            if [ -f "$file" ]; then
                size=$(du -h "$file" | cut -f1)
                lines=$(wc -l < "$file" 2>/dev/null || echo "0")
                echo "  ✅ $(basename "$file"): $size ($lines 行)"
            fi
        done
    else
        echo "  ⚠️  沒有找到日誌檔案"
    fi
    echo ""

    # 2. 日誌級別統計
    echo "📊 日誌級別統計 (django.log)"
    echo "----------------------------------------"
    if [ -f "$LOGS_DIR/django.log" ]; then
        info_count=$(grep -c "\[INFO\]" "$LOGS_DIR/django.log" 2>/dev/null || echo "0")
        warning_count=$(grep -c "\[WARNING\]" "$LOGS_DIR/django.log" 2>/dev/null || echo "0")
        error_count=$(grep -c "\[ERROR\]" "$LOGS_DIR/django.log" 2>/dev/null || echo "0")
        critical_count=$(grep -c "\[CRITICAL\]" "$LOGS_DIR/django.log" 2>/dev/null || echo "0")
        
        echo "  INFO:     $info_count 筆"
        echo "  WARNING:  $warning_count 筆"
        echo "  ERROR:    $error_count 筆"
        echo "  CRITICAL: $critical_count 筆"
    else
        echo "  ⚠️  django.log 不存在"
    fi
    echo ""

    # 3. 錯誤分析
    echo "🚨 錯誤和警告分析"
    echo "----------------------------------------"
    if [ -f "$LOGS_DIR/django.log" ]; then
        echo "  最近 10 筆錯誤："
        grep "\[ERROR\]\|\[CRITICAL\]" "$LOGS_DIR/django.log" 2>/dev/null | tail -10 | while read line; do
            echo "    - $line"
        done || echo "    ✅ 沒有錯誤記錄"
        
        echo ""
        echo "  最近 10 筆警告："
        grep "\[WARNING\]" "$LOGS_DIR/django.log" 2>/dev/null | tail -10 | while read line; do
            echo "    - $line"
        done || echo "    ✅ 沒有警告記錄"
    fi
    echo ""

    # 4. API 訪問統計
    echo "🌐 API 訪問統計 (api_access.log)"
    echo "----------------------------------------"
    if [ -f "$LOGS_DIR/api_access.log" ]; then
        total_requests=$(wc -l < "$LOGS_DIR/api_access.log" 2>/dev/null || echo "0")
        echo "  總請求數: $total_requests"
        
        if [ "$total_requests" -gt 0 ]; then
            echo ""
            echo "  最常訪問的端點 (Top 10)："
            grep -oP '(GET|POST|PUT|DELETE|PATCH) [^ ]+' "$LOGS_DIR/api_access.log" 2>/dev/null | \
                sort | uniq -c | sort -rn | head -10 | while read count endpoint; do
                echo "    $count 次 - $endpoint"
            done || echo "    ⚠️  無法解析訪問記錄"
        fi
    else
        echo "  ⚠️  api_access.log 不存在"
    fi
    echo ""

    # 5. DHCP 操作統計
    echo "🔌 DHCP 操作統計 (dhcp_operations.log)"
    echo "----------------------------------------"
    if [ -f "$LOGS_DIR/dhcp_operations.log" ]; then
        operations=$(wc -l < "$LOGS_DIR/dhcp_operations.log" 2>/dev/null || echo "0")
        echo "  DHCP 操作記錄: $operations 筆"
        
        if [ "$operations" -gt 0 ]; then
            echo ""
            echo "  最近 5 筆操作："
            tail -5 "$LOGS_DIR/dhcp_operations.log" | while read line; do
                echo "    - $line"
            done
        fi
    else
        echo "  ⚠️  dhcp_operations.log 不存在（可能尚未有 DHCP 操作）"
    fi
    echo ""

    # 6. 磁碟使用統計
    echo "💾 磁碟使用統計"
    echo "----------------------------------------"
    total_size=$(du -sh "$LOGS_DIR" 2>/dev/null | cut -f1 || echo "0")
    echo "  日誌總大小: $total_size"
    echo ""
    echo "  各檔案大小："
    du -h "$LOGS_DIR"/*.log 2>/dev/null | while read size file; do
        echo "    $(basename "$file"): $size"
    done || echo "    ⚠️  沒有日誌檔案"
    echo ""

    # 7. 時間範圍
    echo "⏰ 日誌時間範圍"
    echo "----------------------------------------"
    if [ -f "$LOGS_DIR/django.log" ] && [ -s "$LOGS_DIR/django.log" ]; then
        first_line=$(head -1 "$LOGS_DIR/django.log" 2>/dev/null | grep -oP '\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}' || echo "無法解析")
        last_line=$(tail -1 "$LOGS_DIR/django.log" 2>/dev/null | grep -oP '\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}' || echo "無法解析")
        echo "  最早記錄: $first_line"
        echo "  最新記錄: $last_line"
    else
        echo "  ⚠️  無法確定時間範圍"
    fi
    echo ""

    echo "========================================"
    echo "  報告生成完成"
    echo "========================================"

} | tee "$REPORT_FILE"

echo ""
echo "✅ 分析報告已保存至: $REPORT_FILE"
