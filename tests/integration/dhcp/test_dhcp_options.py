#!/usr/bin/env python3
"""
測試從 Windows DHCP Server 取得 DHCP Options (Option 60, 66, 67)
用於驗證階段二實作的可行性
"""
import os
import sys
import django

# 設定 Django 環境
sys.path.insert(0, '/home/owner/Codes/network-toolbox/backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'network_toolbox.settings')
django.setup()

from api.models import DHCPServer
from api.ssh_powershell_service import WindowsSSHPowerShellService
import json

def test_get_dhcp_options():
    """測試取得 DHCP Options"""
    
    print("=" * 70)
    print("📡 測試 Windows DHCP Server - DHCP Options 取得功能")
    print("=" * 70)
    print()
    
    try:
        # 取得 DHCP Server
        server = DHCPServer.objects.get(ip_address='10.250.50.1')
        print(f"✅ 找到 DHCP Server: {server.name} ({server.ip_address})")
        print()
        
        # 建立 SSH 連線
        service = WindowsSSHPowerShellService(server)
        print("🔌 正在連線到 Windows DHCP Server...")
        
        if not service.connect():
            print("❌ SSH 連線失敗！")
            return False
        
        print("✅ SSH 連線成功！")
        print()
        
        # 測試 1: 取得 Server 級別的所有 DHCP Options
        print("-" * 70)
        print("測試 1: 取得 Server 級別的所有 DHCP Options")
        print("-" * 70)
        
        command1 = """
        Get-DhcpServerv4OptionValue -ComputerName localhost |
        Select-Object OptionId, Name, Type, Value |
        ConvertTo-Json -Depth 3
        """
        
        result1 = service.execute_command(command1)
        
        if result1:
            print("✅ 成功取得 Server 級別 Options:")
            try:
                options = json.loads(result1)
                if isinstance(options, list):
                    for opt in options:
                        print(f"  - Option {opt['OptionId']}: {opt['Name']} = {opt['Value']}")
                else:
                    print(f"  - Option {options['OptionId']}: {options['Name']} = {options['Value']}")
            except json.JSONDecodeError:
                print(f"  原始輸出:\n{result1}")
        else:
            print("⚠️  Server 級別沒有設定 Options")
        
        print()
        
        # 測試 2: 取得特定 Scope 的 DHCP Options
        print("-" * 70)
        print("測試 2: 取得 Scope 10.250.50.0 的 DHCP Options")
        print("-" * 70)
        
        command2 = """
        Get-DhcpServerv4OptionValue -ComputerName localhost -ScopeId 10.250.50.0 |
        Select-Object OptionId, Name, Type, Value |
        ConvertTo-Json -Depth 3
        """
        
        result2 = service.execute_command(command2)
        
        if result2:
            print("✅ 成功取得 Scope 級別 Options:")
            try:
                options = json.loads(result2)
                if isinstance(options, list):
                    for opt in options:
                        print(f"  - Option {opt['OptionId']}: {opt['Name']} = {opt['Value']}")
                else:
                    print(f"  - Option {options['OptionId']}: {options['Name']} = {options['Value']}")
            except json.JSONDecodeError:
                print(f"  原始輸出:\n{result2}")
        else:
            print("⚠️  Scope 沒有設定 Options")
        
        print()
        
        # 測試 3: 專門取得 PXE/iPXE 相關的 Options (60, 66, 67)
        print("-" * 70)
        print("測試 3: 取得 PXE/iPXE 相關 Options (60, 66, 67)")
        print("-" * 70)
        
        command3 = """
        $pxeOptions = Get-DhcpServerv4OptionValue -ComputerName localhost -ScopeId 10.250.50.0 -ErrorAction SilentlyContinue |
        Where-Object { $_.OptionId -in @(60,66,67) }
        
        if ($pxeOptions) {
            $pxeOptions | Select-Object OptionId, Name, Type, Value | ConvertTo-Json -Depth 3
        } else {
            Write-Output "NO_PXE_OPTIONS"
        }
        """
        
        result3 = service.execute_command(command3)
        
        if result3 and result3.strip() != "NO_PXE_OPTIONS":
            print("🚀 找到 PXE/iPXE Options:")
            try:
                options = json.loads(result3)
                if isinstance(options, list):
                    for opt in options:
                        icon = "🚀" if opt['OptionId'] == 60 else "🌐" if opt['OptionId'] == 66 else "📁"
                        print(f"  {icon} Option {opt['OptionId']}: {opt['Name']} = {opt['Value']}")
                else:
                    icon = "🚀" if options['OptionId'] == 60 else "🌐" if options['OptionId'] == 66 else "📁"
                    print(f"  {icon} Option {options['OptionId']}: {options['Name']} = {options['Value']}")
            except json.JSONDecodeError:
                print(f"  原始輸出:\n{result3}")
        else:
            print("❌ 沒有找到 PXE/iPXE Options (60, 66, 67)")
            print("   這表示 DHCP Server 沒有設定 PXE Boot 功能")
        
        print()
        
        # 測試 4: 列出所有 Scopes
        print("-" * 70)
        print("測試 4: 列出所有 Scopes（測試每個 Scope 的 Options）")
        print("-" * 70)
        
        command4 = """
        Get-DhcpServerv4Scope -ComputerName localhost |
        Select-Object ScopeId, Name, State |
        ConvertTo-Json -Depth 3
        """
        
        result4 = service.execute_command(command4)
        
        if result4:
            print("✅ 找到以下 Scopes:")
            try:
                scopes = json.loads(result4)
                if not isinstance(scopes, list):
                    scopes = [scopes]
                
                for scope in scopes:
                    print(f"\n  📊 Scope: {scope['ScopeId']} - {scope['Name']} ({scope['State']})")
                    
                    # 檢查每個 Scope 的 PXE Options
                    cmd_scope_options = f"""
                    $opts = Get-DhcpServerv4OptionValue -ComputerName localhost -ScopeId {scope['ScopeId']} -ErrorAction SilentlyContinue |
                    Where-Object {{ $_.OptionId -in @(60,66,67) }}
                    
                    if ($opts) {{
                        $opts | Select-Object OptionId, Name, Value | ConvertTo-Json -Depth 3
                    }} else {{
                        Write-Output "NONE"
                    }}
                    """
                    
                    scope_opt_result = service.execute_command(cmd_scope_options)
                    
                    if scope_opt_result and scope_opt_result.strip() != "NONE":
                        try:
                            opts = json.loads(scope_opt_result)
                            if not isinstance(opts, list):
                                opts = [opts]
                            print("      🚀 PXE Options:")
                            for opt in opts:
                                print(f"         - Option {opt['OptionId']}: {opt['Value']}")
                        except:
                            print("      ⚠️  無法解析 Options")
                    else:
                        print("      - 沒有 PXE Options")
                        
            except json.JSONDecodeError:
                print(f"  原始輸出:\n{result4}")
        
        print()
        
        # 關閉連線
        service.disconnect()
        print("=" * 70)
        print("🎉 測試完成！")
        print("=" * 70)
        print()
        
        return True
        
    except DHCPServer.DoesNotExist:
        print("❌ 找不到 IP 為 10.250.50.1 的 DHCP Server")
        print("   請先執行 create_test_data.py 建立測試資料")
        return False
        
    except Exception as e:
        print(f"❌ 發生錯誤: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    print()
    success = test_get_dhcp_options()
    print()
    
    if success:
        print("📋 結論:")
        print("   ✅ 如果上方顯示了 PXE Options → 階段二可行！")
        print("   ❌ 如果沒有 PXE Options → 階段二無效，建議只做階段一")
        print()
        print("📝 下一步:")
        print("   1. 如果有 Options → 實作 get_dhcp_options() 功能")
        print("   2. 修改 DHCPScope 模型新增 Options 欄位")
        print("   3. 在前端 ConfigTab 顯示 PXE 設定")
    else:
        print("❌ 測試失敗，請檢查:")
        print("   1. DHCP Server 是否存在於資料庫")
        print("   2. SSH 連線是否正常")
        print("   3. PowerShell 權限是否足夠")
    
    print()
