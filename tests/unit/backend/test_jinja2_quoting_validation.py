"""
測試 Jinja2 變數引號檢查功能

測試場景：
1. :vars 區塊中 Jinja2 變數未加引號（應該報錯）
2. :vars 區塊中 Jinja2 變數有加引號（應該通過）
3. 主機行中 Jinja2 變數未加引號（應該報錯）
4. 主機行中 Jinja2 變數有加引號（應該通過）
"""
import sys
import os

# 添加專案根目錄到 Python 路徑
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'backend'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from library.utils.enhanced_ini_validator import validate_ini_with_line_numbers


def test_case(name: str, content: str, expected_valid: bool) -> bool:
    """
    執行測試案例
    
    Args:
        name: 測試名稱
        content: 測試內容
        expected_valid: 預期是否有效
        
    Returns:
        測試是否通過
    """
    print(f"\n{'='*60}")
    print(f"測試: {name}")
    print(f"{'='*60}")
    
    result = validate_ini_with_line_numbers(content)
    
    actual_valid = result['is_valid']
    
    if actual_valid == expected_valid:
        status = "✅ 通過"
    else:
        status = "❌ 失敗"
    
    print(f"預期結果: {'有效' if expected_valid else '無效'}")
    print(f"實際結果: {'有效' if actual_valid else '無效'}")
    print(f"測試狀態: {status}")
    
    if not actual_valid:
        print(f"錯誤訊息: {result.get('error_message')}")
        if result.get('error_line'):
            print(f"錯誤行號: {result.get('error_line')}")
    
    return actual_valid == expected_valid


def main():
    """執行所有測試"""
    print("\n" + "="*60)
    print("Jinja2 變數引號檢查功能測試")
    print("="*60)
    
    all_passed = True
    
    # 測試 1: :vars 區塊中 Jinja2 變數未加引號（應該報錯）
    content_1 = """[UART]
UART-SAF3201-a ansible_host=10.250.131.56

[all:vars]
firmware_project=pvf01
saf_comment_full={{ firmware_sku_keyword }} - {{ sample_size }} - {{ saf_comment }}
ansible_user=administrator
"""
    all_passed &= test_case(
        "1. :vars 區塊中 Jinja2 變數未加引號",
        content_1,
        expected_valid=False
    )
    
    # 測試 2: :vars 區塊中 Jinja2 變數有加雙引號（應該通過）
    content_2 = """[UART]
UART-SAF3201-a ansible_host=10.250.131.56

[all:vars]
firmware_project=pvf01
saf_comment_full="{{ firmware_sku_keyword }} - {{ sample_size }} - {{ saf_comment }}"
ansible_user=administrator
"""
    all_passed &= test_case(
        "2. :vars 區塊中 Jinja2 變數有加雙引號",
        content_2,
        expected_valid=True
    )
    
    # 測試 3: :vars 區塊中 Jinja2 變數有加單引號（應該通過）
    content_3 = """[UART]
UART-SAF3201-a ansible_host=10.250.131.56

[all:vars]
firmware_project=pvf01
saf_comment_full='{{ firmware_sku_keyword }} - {{ sample_size }} - {{ saf_comment }}'
ansible_user=administrator
"""
    all_passed &= test_case(
        "3. :vars 區塊中 Jinja2 變數有加單引號",
        content_3,
        expected_valid=True
    )
    
    # 測試 4: 簡單的 Jinja2 變數未加引號（應該報錯）
    content_4 = """[webservers]
server1 ansible_host=192.168.1.1

[webservers:vars]
app_name={{ project_name }}
"""
    all_passed &= test_case(
        "4. 簡單 Jinja2 變數未加引號",
        content_4,
        expected_valid=False
    )
    
    # 測試 5: 沒有 Jinja2 變數的正常 inventory（應該通過）
    content_5 = """[webservers]
server1 ansible_host=192.168.1.1

[webservers:vars]
app_name=myapp
port=8080
"""
    all_passed &= test_case(
        "5. 沒有 Jinja2 變數的正常 inventory",
        content_5,
        expected_valid=True
    )
    
    # 測試 6: 多個 Jinja2 變數，部分加引號部分未加（應該報錯）
    content_6 = """[servers]
server1 ansible_host=192.168.1.1

[servers:vars]
var1="{{ good_var }}"
var2={{ bad_var }}
var3="static_value"
"""
    all_passed &= test_case(
        "6. 部分 Jinja2 變數未加引號",
        content_6,
        expected_valid=False
    )
    
    # 測試 7: 用戶提供的實際 inventory 格式（問題場景）
    content_7 = """[UART]
UART-SAF3201-a ansible_host=10.250.131.56
UART-SAF3201-b ansible_host=10.250.131.57

[SAF3201:children]
SAF3201_P
SAF3201_S

[SAF3201_P]

[SAF3201_S]
SAF3201_KVM01 ansible_host=10.250.131.13 device_number=PC-SSD-6631 uart_host=UART-SAF3201-a

[SAF3201:vars]

[all:vars]
firmware_project=pvf01
saf_comment_full={{ firmware_sku_keyword }} - {{ sample_size }} - {{ saf_comment }}
ansible_user=administrator
ansible_password=1.a
"""
    all_passed &= test_case(
        "7. 用戶實際 inventory（問題場景）",
        content_7,
        expected_valid=False
    )
    
    # 測試 8: 修正後的用戶 inventory（應該通過）
    content_8 = """[UART]
UART-SAF3201-a ansible_host=10.250.131.56
UART-SAF3201-b ansible_host=10.250.131.57

[SAF3201:children]
SAF3201_P
SAF3201_S

[SAF3201_P]

[SAF3201_S]
SAF3201_KVM01 ansible_host=10.250.131.13 device_number=PC-SSD-6631 uart_host=UART-SAF3201-a

[SAF3201:vars]

[all:vars]
firmware_project=pvf01
saf_comment_full="{{ firmware_sku_keyword }} - {{ sample_size }} - {{ saf_comment }}"
ansible_user=administrator
ansible_password=1.a
"""
    all_passed &= test_case(
        "8. 修正後的用戶 inventory",
        content_8,
        expected_valid=True
    )
    
    # 測試 9: 主機行中的 Jinja2 變數（較少見但應該檢查）
    content_9 = """[servers]
server1 ansible_host=192.168.1.1 custom_var={{ some_var }}

[servers:vars]
some_var=value
"""
    all_passed &= test_case(
        "9. 主機行中 Jinja2 變數未加引號",
        content_9,
        expected_valid=False
    )
    
    # 總結
    print("\n" + "="*60)
    print("測試總結")
    print("="*60)
    
    if all_passed:
        print("✅ 所有測試通過！")
        return 0
    else:
        print("❌ 有測試失敗！")
        return 1


if __name__ == '__main__':
    sys.exit(main())
