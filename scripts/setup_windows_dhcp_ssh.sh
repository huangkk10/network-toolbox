#!/bin/bash

# Windows DHCP Server SSH 同步快速設定腳本
# 適用於已安裝 OpenSSH Server 的 Windows Server

set -e

echo "============================================"
echo "  Windows DHCP Server SSH 同步設定助手"
echo "============================================"
echo ""

# 顏色定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 檢查 Docker 是否運行
echo -e "${BLUE}[1/6] 檢查 Docker 環境...${NC}"
if ! docker compose ps | grep -q nt-django; then
    echo -e "${RED}✗ Django 容器未運行，請先啟動：docker compose up -d${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Docker 容器運行中${NC}"
echo ""

# 收集資訊
echo -e "${BLUE}[2/6] 收集 Windows DHCP Server 資訊${NC}"
read -p "Windows DHCP Server IP 位址 (例如: 10.250.50.1): " DHCP_IP
read -p "Windows DHCP Server 名稱 (例如: Windows DHCP Server): " DHCP_NAME
read -p "SSH 連接埠 (預設 22): " SSH_PORT
SSH_PORT=${SSH_PORT:-22}
read -p "SSH 使用者名稱 (例如: Administrator): " SSH_USER

echo ""
echo "選擇認證方式："
echo "  1) 使用密碼認證（快速）"
echo "  2) 使用 SSH 金鑰認證（推薦，更安全）"
read -p "請選擇 (1 或 2): " AUTH_METHOD

if [ "$AUTH_METHOD" == "1" ]; then
    read -sp "SSH 密碼: " SSH_PASS
    echo ""
    SSH_KEY=""
else
    echo ""
    echo -e "${BLUE}[3/6] 生成 SSH 金鑰對...${NC}"
    
    # 在容器中生成 SSH 金鑰
    docker exec -it nt-django bash -c "mkdir -p /app/.ssh && ssh-keygen -t rsa -b 4096 -f /app/.ssh/id_rsa -N '' -q"
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ SSH 金鑰生成成功${NC}"
        
        # 顯示公鑰
        echo ""
        echo -e "${YELLOW}請將以下公鑰添加到 Windows Server：${NC}"
        echo -e "${YELLOW}位置：C:\\Users\\${SSH_USER}\\.ssh\\authorized_keys${NC}"
        echo ""
        echo "----------------------------------------"
        docker exec nt-django cat /app/.ssh/id_rsa.pub
        echo "----------------------------------------"
        echo ""
        
        echo "在 Windows Server 上執行以下 PowerShell 命令："
        echo ""
        echo "# 創建 .ssh 目錄"
        echo "New-Item -ItemType Directory -Path \"\$env:USERPROFILE\\.ssh\" -Force"
        echo ""
        echo "# 複製上面的公鑰內容到 authorized_keys"
        echo "notepad \"\$env:USERPROFILE\\.ssh\\authorized_keys\""
        echo ""
        echo "# 設定權限"
        echo "icacls \"\$env:USERPROFILE\\.ssh\\authorized_keys\" /inheritance:r"
        echo "icacls \"\$env:USERPROFILE\\.ssh\\authorized_keys\" /grant:r \"\$env:USERNAME:F\""
        echo ""
        
        read -p "完成後按 Enter 繼續..."
        
        SSH_KEY="/app/.ssh/id_rsa"
        SSH_PASS=""
    else
        echo -e "${RED}✗ SSH 金鑰生成失敗${NC}"
        exit 1
    fi
fi

echo ""
echo -e "${BLUE}[4/6] 測試 SSH 連接...${NC}"

# 測試 SSH 連接
if [ -n "$SSH_KEY" ]; then
    # 使用金鑰
    TEST_CMD="docker exec -it nt-django ssh -o StrictHostKeyChecking=no -i $SSH_KEY ${SSH_USER}@${DHCP_IP} 'powershell.exe -Command Get-Date'"
else
    # 使用密碼（需要 sshpass）
    if ! command -v sshpass &> /dev/null; then
        echo -e "${YELLOW}⚠ 請手動測試 SSH 連接${NC}"
    else
        TEST_CMD="sshpass -p '$SSH_PASS' ssh -o StrictHostKeyChecking=no ${SSH_USER}@${DHCP_IP} 'powershell.exe -Command Get-Date'"
    fi
fi

echo "執行測試命令..."
if eval $TEST_CMD > /dev/null 2>&1; then
    echo -e "${GREEN}✓ SSH 連接成功${NC}"
else
    echo -e "${YELLOW}⚠ SSH 連接測試失敗，但繼續設定（可能是正常的）${NC}"
fi

echo ""
echo -e "${BLUE}[5/6] 在資料庫中創建 DHCP Server...${NC}"

# 創建 Python 腳本
cat > /tmp/create_dhcp_server.py << EOF
from api.models import DHCPServer

# 檢查是否已存在
existing = DHCPServer.objects.filter(ip_address='$DHCP_IP').first()

if existing:
    print(f'更新現有 Server: {existing.name} (ID: {existing.id})')
    server = existing
    server.name = '$DHCP_NAME'
    server.ssh_port = $SSH_PORT
    server.ssh_username = '$SSH_USER'
    server.ssh_password = '$SSH_PASS'
    server.ssh_key_file = '$SSH_KEY'
    server.status = 'online'
    server.save()
else:
    print('創建新 DHCP Server')
    server = DHCPServer.objects.create(
        name='$DHCP_NAME',
        ip_address='$DHCP_IP',
        description='透過 SSH + PowerShell 自動同步的 Windows DHCP Server',
        status='online',
        ssh_port=$SSH_PORT,
        ssh_username='$SSH_USER',
        ssh_password='$SSH_PASS',
        ssh_key_file='$SSH_KEY',
    )

print(f'Server ID: {server.id}')
print(f'名稱: {server.name}')
print(f'IP: {server.ip_address}')
print(f'SSH Port: {server.ssh_port}')
print(f'SSH User: {server.ssh_username}')
print(f'認證方式: {"金鑰" if server.ssh_key_file else "密碼"}')
EOF

# 執行 Python 腳本
docker exec -i nt-django python manage.py shell < /tmp/create_dhcp_server.py

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ DHCP Server 設定成功${NC}"
else
    echo -e "${RED}✗ DHCP Server 設定失敗${NC}"
    exit 1
fi

# 清理臨時檔案
rm /tmp/create_dhcp_server.py

echo ""
echo -e "${BLUE}[6/6] 測試同步功能...${NC}"

# 獲取 Server ID
SERVER_ID=$(docker exec nt-django python manage.py shell -c "from api.models import DHCPServer; s=DHCPServer.objects.filter(ip_address='$DHCP_IP').first(); print(s.id if s else '')")

if [ -n "$SERVER_ID" ]; then
    echo "Server ID: $SERVER_ID"
    echo ""
    read -p "是否立即測試同步？(y/n): " TEST_SYNC
    
    if [ "$TEST_SYNC" == "y" ] || [ "$TEST_SYNC" == "Y" ]; then
        echo ""
        echo "執行同步測試..."
        
        # 創建測試腳本
        cat > /tmp/test_sync.py << EOF
from api.models import DHCPServer
from api.ssh_powershell_service import WindowsSSHPowerShellService

server = DHCPServer.objects.get(id=$SERVER_ID)

print(f'測試連接到: {server.name} ({server.ip_address})')
print('')

try:
    with WindowsSSHPowerShellService(server) as service:
        # 測試獲取 Scope
        print('[1/3] 獲取 DHCP Scope...')
        scopes = service.get_dhcp_scopes()
        print(f'✓ 發現 {len(scopes)} 個 Scope')
        for scope in scopes[:5]:  # 只顯示前 5 個
            print(f'  - {scope["ScopeId"]} ({scope["Name"]})')
        
        print('')
        print('[2/3] 獲取租約資料...')
        leases = service.get_dhcp_leases()
        print(f'✓ 獲取 {len(leases)} 筆租約')
        
        # 顯示前 3 筆樣本
        for i, lease in enumerate(leases[:3]):
            print(f'  {i+1}. IP: {lease["IPAddress"]}, Hostname: {lease.get("HostName", "(無)")}')
        
        print('')
        print('[3/3] 同步到資料庫...')
        result = service.sync_leases_to_db()
        print(f'✓ 同步完成')
        print(f'  - 總數: {result["total"]}')
        print(f'  - 新增: {result["created"]}')
        print(f'  - 更新: {result["updated"]}')
        print(f'  - 跳過: {result["skipped"]}')
        print(f'  - 錯誤: {result["errors"]}')
        
    print('')
    print('✓ 測試成功！')

except Exception as e:
    print(f'✗ 測試失敗: {str(e)}')
    import traceback
    traceback.print_exc()
EOF
        
        docker exec -i nt-django python manage.py shell < /tmp/test_sync.py
        
        if [ $? -eq 0 ]; then
            echo ""
            echo -e "${GREEN}✓ 同步測試成功！${NC}"
        else
            echo ""
            echo -e "${YELLOW}⚠ 同步測試失敗，請檢查日誌${NC}"
        fi
        
        rm /tmp/test_sync.py
    fi
fi

echo ""
echo "============================================"
echo -e "${GREEN}  設定完成！${NC}"
echo "============================================"
echo ""
echo "您現在可以："
echo "  1. 訪問前端：http://localhost"
echo "  2. 進入「DHCP 分析」頁面"
echo "  3. 選擇 '$DHCP_NAME'"
echo "  4. 點擊「同步租約」按鈕"
echo ""
echo "或透過 API 手動同步："
echo "  curl -X POST http://localhost/api/dhcp-servers/${SERVER_ID}/sync-leases/"
echo ""
echo "查看詳細文檔："
echo "  docs/SSH_WINDOWS_DHCP_SYNC.md"
echo ""
echo -e "${BLUE}提示：可設定定時任務實現自動同步（參考文檔）${NC}"
echo ""
