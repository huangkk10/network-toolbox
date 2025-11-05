#!/bin/bash
# 掛載 NAS 到 /mnt/mdt 腳本
# NAS IP: 10.250.0.1
# User: mdt
# Password: p@ssw0rd

set -e

echo "========================================="
echo "掛載 NAS 到 /mnt/mdt"
echo "========================================="

# 檢查是否已掛載
if mount | grep -q "/mnt/mdt"; then
    echo "⚠️  /mnt/mdt 已經掛載，先卸載..."
    sudo umount /mnt/mdt
fi

# 創建掛載點
if [ ! -d "/mnt/mdt" ]; then
    echo "📁 創建掛載點 /mnt/mdt..."
    sudo mkdir -p /mnt/mdt
fi

# 設置權限
sudo chown $USER:$USER /mnt/mdt

# NAS 配置
NAS_IP="10.250.0.1"
NAS_SHARE="mdt"  # 共享資料夾名稱
NAS_USER="mdt"
NAS_PASSWORD="p@ssw0rd"

echo "🔗 掛載 NAS..."
echo "   NAS IP: ${NAS_IP}"
echo "   共享: //${NAS_IP}/${NAS_SHARE}"
echo "   掛載點: /mnt/mdt"

# 掛載 NAS（使用 CIFS/SMB）
sudo mount -t cifs //${NAS_IP}/${NAS_SHARE} /mnt/mdt \
    -o username=${NAS_USER},password=${NAS_PASSWORD},uid=$(id -u),gid=$(id -g),file_mode=0755,dir_mode=0755

# 檢查掛載結果
if mount | grep -q "/mnt/mdt"; then
    echo "✅ NAS 掛載成功！"
    echo ""
    echo "掛載信息："
    mount | grep /mnt/mdt
    echo ""
    echo "目錄內容："
    ls -lah /mnt/mdt | head -20
    echo ""
    echo "磁碟空間："
    df -h /mnt/mdt
else
    echo "❌ NAS 掛載失敗！"
    exit 1
fi

echo ""
echo "========================================="
echo "✅ 掛載完成！"
echo "========================================="
echo ""
echo "下一步："
echo "1. 創建 Jenkins 存儲目錄：sudo mkdir -p /mnt/mdt/jenkins_test_storage"
echo "2. 修改 docker-compose.yml 啟用 NAS 掛載"
echo "3. 重啟 Django 容器：docker compose restart django"
