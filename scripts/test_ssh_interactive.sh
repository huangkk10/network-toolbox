#!/bin/bash

# 進入 Django Shell 並執行測試
# 使用方式：./scripts/test_ssh_interactive.sh

cat << 'EOF' | docker exec -i nt-django python manage.py shell
from api.models import DHCPServer
from api.ssh_powershell_service import WindowsSSHPowerShellService

# 配置
DHCP_IP = '10.250.50.1'
SSH_USER = 'administrator'
SSH_PASSWORD = input(f"請輸入 {SSH_USER}@{DHCP_IP} 的密碼: ")

# 創建 Server
server, created = DHCPServer.objects.update_or_create(
    ip_address=DHCP_IP,
    defaults={
        'name': 'Windows DHCP Server',
        'status': 'online',
        'ssh_port': 22,
        'ssh_username': SSH_USER,
        'ssh_password': SSH_PASSWORD,
    }
)

print(f"\n{'=' * 60}")
print(f"Server: {server.name} (ID: {server.id})")
print(f"{'=' * 60}\n")

# 測試同步
print("[1/3] 連接 SSH...")
with WindowsSSHPowerShellService(server) as service:
    print("✓ SSH 連接成功\n")
    
    print("[2/3] 獲取 Scope...")
    scopes = service.get_dhcp_scopes()
    print(f"✓ 發現 {len(scopes)} 個 Scope\n")
    
    print("[3/3] 同步租約...")
    result = service.sync_leases_to_db()
    print(f"✓ 同步完成: {result}\n")

print(f"總租約: {server.total_leases}, 活躍: {server.active_leases}")
EOF
