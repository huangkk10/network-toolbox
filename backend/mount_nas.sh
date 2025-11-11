#!/bin/bash
# 容器內 NAS 掛載腳本
# 此腳本在 Django 容器啟動時執行

set -e

echo "========================================="
echo "容器內 NAS 掛載腳本"
echo "========================================="

# NAS 配置（從環境變數讀取，或使用默認值）
NAS_IP="${NAS_IP:-10.250.0.1}"
NAS_SHARE="${NAS_SHARE:-mdt}"
NAS_USER="${NAS_USER:-mdt}"
NAS_PASSWORD="${NAS_PASSWORD:-p@ssw0rd}"
MOUNT_POINT="${NAS_MOUNT_PATH:-/mnt/mdt}"

echo "NAS 配置："
echo "  IP: ${NAS_IP}"
echo "  共享: ${NAS_SHARE}"
echo "  用戶: ${NAS_USER}"
echo "  掛載點: ${MOUNT_POINT}"

# 檢查是否已掛載
if mount | grep -q "${MOUNT_POINT}"; then
    echo "✅ ${MOUNT_POINT} 已經掛載"
    mount | grep "${MOUNT_POINT}"
    exit 0
fi

# 創建掛載點
if [ ! -d "${MOUNT_POINT}" ]; then
    echo "📁 創建掛載點 ${MOUNT_POINT}..."
    mkdir -p "${MOUNT_POINT}"
fi

# 掛載 NAS
echo "🔗 掛載 NAS..."
mount -t cifs "//${NAS_IP}/${NAS_SHARE}" "${MOUNT_POINT}" \
    -o username="${NAS_USER}",password="${NAS_PASSWORD}",uid=0,gid=0,file_mode=0755,dir_mode=0755

# 檢查掛載結果
if mount | grep -q "${MOUNT_POINT}"; then
    echo "✅ NAS 掛載成功！"
    echo ""
    echo "掛載信息："
    mount | grep "${MOUNT_POINT}"
    echo ""
    echo "目錄內容（前 10 項）："
    ls -lah "${MOUNT_POINT}" 2>/dev/null | head -11 || echo "無法列出目錄內容"
    
    echo ""
    echo "✅ NAS 掛載完成！"
else
    echo "❌ NAS 掛載失敗！"
    exit 1
fi
