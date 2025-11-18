#!/usr/bin/env python
"""
測試 UART SSH 連線檢查功能

使用方式：
python test_uart_ssh_check.py <build_id>
"""

import sys
import os
import django

# Setup Django
sys.path.insert(0, '/home/owner/Codes/network-toolbox/backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'network_toolbox.settings')
django.setup()

from library.services.build_config_validator import BuildConfigValidator
import json

def test_uart_ssh_check(build_id):
    """測試 UART SSH 檢查功能"""
    print(f"🔍 測試 Build ID: {build_id} 的配置檢查...")
    print("=" * 80)
    
    validator = BuildConfigValidator(build_id)
    result = validator.validate()
    
    print(f"\n📊 檢查結果：")
    print(f"   整體狀態: {result['overall_status']}")
    print(f"   配置來源: {result['config_source']}")
    print(f"   總檢查項: {result['summary']['total_checks']}")
    print(f"   通過: {result['summary']['passed']}")
    print(f"   警告: {result['summary']['warnings']}")
    print(f"   錯誤: {result['summary']['errors']}")
    
    print(f"\n🔌 UART SSH 連線檢查結果：")
    print("=" * 80)
    
    uart_ssh = result['checks'].get('uart_ssh', {})
    
    print(f"   狀態: {uart_ssh.get('status', 'unknown')}")
    print(f"   訊息: {uart_ssh.get('message', 'N/A')}")
    print(f"   值: {uart_ssh.get('value', 'N/A')}")
    
    if uart_ssh.get('details'):
        print(f"\n   詳細資訊:")
        for key, value in uart_ssh['details'].items():
            print(f"     - {key}: {value}")
    
    if uart_ssh.get('suggestions'):
        print(f"\n   建議:")
        for suggestion in uart_ssh['suggestions']:
            print(f"     - {suggestion}")
    
    print("\n" + "=" * 80)
    print("✅ 測試完成！")
    
    # 輸出完整 JSON（方便調試）
    print(f"\n📄 完整 JSON 結果（僅 UART SSH 部分）:")
    print(json.dumps(uart_ssh, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("❌ 請提供 Build ID")
        print(f"使用方式: python {sys.argv[0]} <build_id>")
        sys.exit(1)
    
    try:
        build_id = int(sys.argv[1])
        test_uart_ssh_check(build_id)
    except ValueError:
        print(f"❌ 無效的 Build ID: {sys.argv[1]}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ 測試失敗: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
