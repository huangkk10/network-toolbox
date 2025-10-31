"""
SSH 服務整合測試

測試 library.services.SSHClient 的功能
"""
import os
import sys

# 添加專案根目錄到 Python 路徑
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# 設置 Django 環境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'network_toolbox.settings')
import django
django.setup()

from library.services import SSHClient, ssh_connection


def test_ssh_client_basic():
    """測試 SSH 客戶端基本功能"""
    print('\n' + '='*70)
    print('測試 1: SSH 客戶端基本功能')
    print('='*70)
    
    # 使用現有的 DHCP Server 配置
    from api.models import DHCPServer
    server = DHCPServer.objects.first()
    
    if not server:
        print('❌ 未找到 DHCP Server，跳過測試')
        return False
    
    print(f'測試伺服器: {server.ip_address}')
    
    ssh = SSHClient(
        host=server.ip_address,
        port=server.ssh_port,
        username=server.ssh_username,
        password=server.ssh_password
    )
    
    try:
        # 測試連接
        if not ssh.connect():
            print('❌ SSH 連接失敗')
            return False
        
        print('✅ SSH 連接成功')
        
        # 測試命令執行
        stdout, stderr, exit_code = ssh.execute_command('hostname')
        print(f'✅ 執行命令成功')
        print(f'   主機名: {stdout.strip()}')
        print(f'   Exit Code: {exit_code}')
        
        # 測試連接狀態檢查
        if ssh.is_connected():
            print('✅ 連接狀態檢查正常')
        
        return True
    
    except Exception as e:
        print(f'❌ 測試失敗: {e}')
        return False
    
    finally:
        ssh.close()
        print('✅ 連接已關閉')


def test_context_manager():
    """測試上下文管理器"""
    print('\n' + '='*70)
    print('測試 2: 上下文管理器（with 語句）')
    print('='*70)
    
    from api.models import DHCPServer
    server = DHCPServer.objects.first()
    
    if not server:
        print('❌ 未找到 DHCP Server，跳過測試')
        return False
    
    try:
        with SSHClient(
            host=server.ip_address,
            port=server.ssh_port,
            username=server.ssh_username,
            password=server.ssh_password
        ) as ssh:
            stdout, stderr, exit_code = ssh.execute_command('echo "Hello from SSH"')
            print(f'✅ 上下文管理器正常工作')
            print(f'   輸出: {stdout.strip()}')
        
        print('✅ 連接自動關閉')
        return True
    
    except Exception as e:
        print(f'❌ 測試失敗: {e}')
        return False


def test_powershell_command():
    """測試 PowerShell 命令執行（Windows DHCP Server）"""
    print('\n' + '='*70)
    print('測試 3: PowerShell 命令執行')
    print('='*70)
    
    from api.models import DHCPServer
    server = DHCPServer.objects.first()
    
    if not server:
        print('❌ 未找到 DHCP Server，跳過測試')
        return False
    
    try:
        with SSHClient(
            host=server.ip_address,
            port=server.ssh_port,
            username=server.ssh_username,
            password=server.ssh_password
        ) as ssh:
            # 執行簡單的 PowerShell 命令
            command = 'Get-Date -Format "yyyy-MM-dd HH:mm:ss"'
            full_command = f'powershell.exe -Command "{command}"'
            
            stdout, stderr, exit_code = ssh.execute_command(full_command, timeout=30)
            
            if exit_code == 0:
                print(f'✅ PowerShell 命令執行成功')
                print(f'   伺服器時間: {stdout.strip()}')
                return True
            else:
                print(f'❌ PowerShell 命令執行失敗')
                print(f'   Error: {stderr}')
                return False
    
    except Exception as e:
        print(f'❌ 測試失敗: {e}')
        return False


def test_convenience_function():
    """測試便捷函數 ssh_connection"""
    print('\n' + '='*70)
    print('測試 4: 便捷函數 ssh_connection')
    print('='*70)
    
    from api.models import DHCPServer
    server = DHCPServer.objects.first()
    
    if not server:
        print('❌ 未找到 DHCP Server，跳過測試')
        return False
    
    try:
        with ssh_connection(
            host=server.ip_address,
            port=server.ssh_port,
            username=server.ssh_username,
            password=server.ssh_password
        ) as ssh:
            stdout, stderr, exit_code = ssh.execute_command('echo "便捷函數測試"')
            print(f'✅ 便捷函數正常工作')
            print(f'   輸出: {stdout.strip()}')
        
        return True
    
    except Exception as e:
        print(f'❌ 測試失敗: {e}')
        return False


def run_all_tests():
    """執行所有測試"""
    print('\n' + '#'*70)
    print('#' + ' '*20 + 'SSH 服務整合測試' + ' '*20 + '#')
    print('#'*70)
    
    results = []
    
    results.append(('基本功能', test_ssh_client_basic()))
    results.append(('上下文管理器', test_context_manager()))
    results.append(('PowerShell 命令', test_powershell_command()))
    results.append(('便捷函數', test_convenience_function()))
    
    # 顯示總結
    print('\n' + '='*70)
    print('測試總結')
    print('='*70)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = '✅ 通過' if result else '❌ 失敗'
        print(f'{status} - {name}')
    
    print(f'\n總計: {passed}/{total} 個測試通過')
    
    if passed == total:
        print('\n🎉 所有測試通過！')
        return True
    else:
        print(f'\n⚠️  有 {total - passed} 個測試失敗')
        return False


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
