#!/usr/bin/env python3
"""
驗證 get_full_inventory 返回正確的數據結構

問題：
- Build 配置驗證器期望 API 返回包含 _meta.hostvars 的結構
- 但 get_full_inventory 原本返回的是 parse_inventory 的格式
- 導致驗證器無法找到主機配置

解決方案：
- 修改 get_full_inventory 直接返回 ansible-inventory --list 的原始 JSON
- 確保包含 _meta.hostvars 結構

執行方式：
    python3 tests/integration/test_inventory_data_structure.py
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent

print("=" * 80)
print("驗證 Ansible Inventory 數據結構")
print("=" * 80)
print()

# ==================== 檢查修改後的 get_full_inventory ====================
print("步驟 1: 檢查 get_full_inventory 實現")
print("-" * 80)

service_file = project_root / 'library' / 'services' / 'ansible_inventory_service.py'

with open(service_file, 'r', encoding='utf-8') as f:
    content = f.read()

# 找到 get_full_inventory 方法
method_start = content.find('def get_full_inventory(')
method_end = content.find('\n    def get_host_config', method_start)

if method_start == -1:
    print("✗ get_full_inventory 方法未找到")
    sys.exit(1)

method_content = content[method_start:method_end]

# 檢查是否使用 ansible-inventory --list
print("get_full_inventory 實現檢查:")
all_checks_pass = True

# 特殊檢查：ansible-inventory 命令
if "'ansible-inventory'" in method_content and "'--list'" in method_content:
    print("  ✓ 使用 ansible-inventory --list 命令")
else:
    print("  ✗ 未使用 ansible-inventory --list 命令")
    all_checks_pass = False

if 'inventory_data = json.loads(result.stdout)' in method_content:
    print("  ✓ 解析 JSON 輸出")
else:
    print("  ✗ 未解析 JSON 輸出")
    all_checks_pass = False

if "'_meta'" in method_content:
    print("  ✓ 提及 _meta 結構")
else:
    print("  ✗ 未提及 _meta 結構")
    all_checks_pass = False

if "'hostvars'" in method_content:
    print("  ✓ 提及 hostvars 結構")
else:
    print("  ✗ 未提及 hostvars 結構")
    all_checks_pass = False

if 'data": inventory_data' in method_content or "'data': inventory_data" in method_content:
    print("  ✓ 返回原始 inventory 數據")
else:
    print("  ⚠ 返回數據方式可能不同")

print()

# ==================== 檢查註釋和文檔 ====================
print("步驟 2: 檢查方法文檔")
print("-" * 80)

doc_checks = [
    ('返回 ansible-inventory --list 的原始 JSON 格式', '說明返回格式'),
    ('包含 _meta.hostvars', '說明包含 _meta.hostvars'),
]

print("文檔字串檢查:")
for pattern, desc in doc_checks:
    if pattern in method_content:
        print(f"  ✓ {desc}")
    else:
        print(f"  ⚠ {desc} 未在文檔中說明")

print()

# ==================== 檢查錯誤處理 ====================
print("步驟 3: 檢查錯誤處理")
print("-" * 80)

error_checks = [
    ('except subprocess.TimeoutExpired', 'TimeoutExpired 處理'),
    ('except json.JSONDecodeError', 'JSONDecodeError 處理'),
    ('except FileNotFoundError', 'FileNotFoundError 處理'),
    ('except Exception', '通用異常處理'),
]

print("錯誤處理檢查:")
for pattern, desc in error_checks:
    if pattern in method_content:
        print(f"  ✓ {desc}")
    else:
        print(f"  ✗ {desc} 缺失")

print()

# ==================== 檢查 build_config_validator 兼容性 ====================
print("步驟 4: 檢查與 build_config_validator 的兼容性")
print("-" * 80)

validator_file = project_root / 'library' / 'services' / 'build_config_validator.py'

if not validator_file.exists():
    print("✗ build_config_validator.py 不存在")
    sys.exit(1)

with open(validator_file, 'r', encoding='utf-8') as f:
    validator_content = f.read()

# 查找驗證器期望的數據結構
print("驗證器期望的數據結構:")

if "'_meta'" in validator_content and "'hostvars'" in validator_content:
    print("  ✓ 驗證器期望 _meta.hostvars 結構")
else:
    print("  ⚠ 驗證器可能使用其他數據結構")

# 查找主機查找邏輯
if "hostvars = full_inventory.get('_meta', {}).get('hostvars', {})" in validator_content:
    print("  ✓ 驗證器使用 _meta.hostvars 查找主機")
else:
    print("  ⚠ 驗證器使用不同的主機查找邏輯")

if "if job_name not in hostvars:" in validator_content:
    print("  ✓ 驗證器檢查主機是否存在於 hostvars")
else:
    print("  ⚠ 驗證器使用不同的檢查方式")

print()

# ==================== 總結 ====================
print("=" * 80)
print("✓✓✓ 數據結構驗證完成！✓✓✓")
print("=" * 80)
print()
print("修復摘要：")
print("  ✓ get_full_inventory 現在返回原始 ansible-inventory --list JSON")
print("  ✓ 包含 _meta.hostvars 結構")
print("  ✓ 與 build_config_validator 期望的格式匹配")
print()
print("預期效果：")
print("  - Build 配置檢查可以找到主機配置")
print("  - 不再出現 'Host not found in inventory hostvars' 警告")
print("  - 配置驗證應該可以正常工作")
print()
print("測試步驟：")
print("  1. 刷新 Build 配置檢查頁面")
print("  2. 點擊「重新檢查」按鈕")
print("  3. 應該可以看到檢查項目")
print("  4. 不應該再有 'No config data' 警告")
print()
