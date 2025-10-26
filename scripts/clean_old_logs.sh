#!/bin/bash
# 日誌清理腳本 - Network Toolbox
# 用途：清理指定天數之前的舊日誌檔案

set -e

LOGS_DIR="./logs"
DEFAULT_DAYS=30

# 使用參數或預設值
DAYS=${1:-$DEFAULT_DAYS}

echo "========================================"
echo "  Network Toolbox 日誌清理工具"
echo "  清理時間: $(date '+%Y-%m-%d %H:%M:%S')"
echo "========================================"
echo ""

# 檢查 logs 目錄
if [ ! -d "$LOGS_DIR" ]; then
    echo "❌ 錯誤：找不到 logs 目錄"
    exit 1
fi

echo "🔍 搜尋 $DAYS 天前的日誌檔案..."
echo ""

# 查找並顯示將要刪除的檔案
OLD_FILES=$(find "$LOGS_DIR" -name "*.log.*" -mtime +$DAYS 2>/dev/null)

if [ -z "$OLD_FILES" ]; then
    echo "✅ 沒有找到 $DAYS 天前的舊日誌檔案"
    exit 0
fi

echo "📋 將要刪除的檔案："
echo "$OLD_FILES" | while read file; do
    size=$(du -h "$file" | cut -f1)
    mtime=$(stat -c %y "$file" | cut -d' ' -f1)
    echo "  - $(basename "$file") ($size, 修改時間: $mtime)"
done

echo ""
read -p "⚠️  確定要刪除這些檔案嗎? [y/N] " -n 1 -r
echo

if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo ""
    echo "🗑️  開始刪除..."
    
    deleted_count=0
    total_size=0
    
    echo "$OLD_FILES" | while read file; do
        size=$(du -k "$file" | cut -f1)
        if rm "$file" 2>/dev/null; then
            echo "  ✅ 已刪除: $(basename "$file")"
            deleted_count=$((deleted_count + 1))
            total_size=$((total_size + size))
        else
            echo "  ❌ 刪除失敗: $(basename "$file")"
        fi
    done
    
    echo ""
    echo "========================================"
    echo "  清理完成"
    echo "========================================"
    echo "  已刪除檔案數: $(echo "$OLD_FILES" | wc -l)"
    echo "  釋放空間: 約 $(du -sh "$LOGS_DIR" | cut -f1)"
else
    echo ""
    echo "❌ 取消清理操作"
fi
