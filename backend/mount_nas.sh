#!/bin/bash
# 容器內 NAS 掛載腳本
# 此腳本在 Django 容器啟動時執行

set -e

echo "========================================="
echo "容器內 NAS 掛載腳本"
echo "========================================="

# 掛載單個 NAS 的函數
mount_nas() {
    local NAS_IP="$1"
    local NAS_SHARE="$2"
    local NAS_USER="$3"
    local NAS_PASSWORD="$4"
    local MOUNT_POINT="$5"
    local SMB_VERSION="${6:-2.0}"
    
    echo ""
    echo "----------------------------------------"
    echo "掛載 NAS: ${NAS_IP}/${NAS_SHARE}"
    echo "  用戶: ${NAS_USER}"
    echo "  掛載點: ${MOUNT_POINT}"
    echo "----------------------------------------"
    
    # 檢查是否已掛載
    if mount | grep -q "${MOUNT_POINT}"; then
        echo "✅ ${MOUNT_POINT} 已經掛載"
        return 0
    fi
    
    # 創建掛載點
    if [ ! -d "${MOUNT_POINT}" ]; then
        echo "📁 創建掛載點 ${MOUNT_POINT}..."
        mkdir -p "${MOUNT_POINT}"
    fi
    
    # 掛載 NAS
    echo "🔗 掛載中..."
    if mount -t cifs "//${NAS_IP}/${NAS_SHARE}" "${MOUNT_POINT}" \
        -o username="${NAS_USER}",password="${NAS_PASSWORD}",vers="${SMB_VERSION}",uid=1000,gid=1000,file_mode=0755,dir_mode=0755 2>&1; then
        echo "✅ ${NAS_IP} 掛載成功！"
        return 0
    else
        echo "⚠️  ${NAS_IP} 掛載失敗"
        return 1
    fi
}

# ========================================
# NAS 掛載列表
# ========================================

# NAS 1: 10.250.0.1 (主要 NAS)
mount_nas "10.250.0.1" "mdt" "${NAS_USER:-mdt}" "${NAS_PASSWORD:-p@ssw0rd}" "/mnt/mdt" "2.0" || true

# NAS 2: 10.8.246.11 (次要 NAS)
mount_nas "10.8.246.11" "mdt" "administrator" "1.a" "/mnt/nas_10.8.246.11" "2.0" || true

# ========================================
# 顯示掛載結果
# ========================================
echo ""
echo "========================================="
echo "NAS 掛載結果："
echo "========================================="
mount | grep cifs || echo "沒有 CIFS 掛載"
echo ""
echo "✅ NAS 掛載腳本執行完成！"
