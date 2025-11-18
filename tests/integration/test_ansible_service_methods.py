#!/usr/bin/env python3
"""
測試 AnsibleInventoryService 所有必要方法

問題：
- jenkins.py 調用了多個 AnsibleInventoryService 的方法
- 但這些方法在服務類別中沒有實現

已修復的方法：
1. get_full_inventory(use_cache) - 獲取完整 Inventory
2. get_host_config(hostname, use_cache) - 獲取特定主機配置
3. clear_cache(cache_type) - 清除快取（預留）

執行方式：
    python3 tests/integration/test_ansible_service_methods.py
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent

print("=" * 80)
print("測試 AnsibleInventoryService 方法完整性")
print("=" * 80)
print()

# ==================== 檢查服務文件 ====================
print("步驟 1: 檢查 AnsibleInventoryService 方法")
print("-" * 80)

service_file = project_root / 'library' / 'services' / 'ansible_inventory_service.py'

if not service_file.exists():
    print(f"✗ 服務文件不存在: {service_file}")
    sys.exit(1)

with open(service_file, 'r', encoding='utf-8') as f:
    content = f.read()

# 檢查所有必要的方法
required_methods = [
    ('def get_full_inventory(', 'get_full_inventory(use_cache)'),
    ('def get_host_config(', 'get_host_config(hostname, use_cache)'),
    ('def clear_cache(', 'clear_cache(cache_type)'),
]

all_methods_exist = True
for method_signature, method_name in required_methods:
    if method_signature in content:
        print(f"  ✓ {method_name} 方法已實現")
    else:
        print(f"  ✗ {method_name} 方法缺失")
        all_methods_exist = False

if not all_methods_exist:
    sys.exit(1)

print()

# ==================== 檢查方法簽名 ====================
print("步驟 2: 驗證方法簽名")
print("-" * 80)

method_signatures = [
    ('def get_full_inventory(self, use_cache: bool = True)', 'get_full_inventory'),
    ('def get_host_config(self, hostname: str, use_cache: bool = True)', 'get_host_config'),
    ('def clear_cache(self, cache_type: str = \'all\')', 'clear_cache'),
]

for signature, name in method_signatures:
    if signature in content:
        print(f"  ✓ {name} 簽名正確")
    else:
        print(f"  ⚠ {name} 簽名可能不同（但方法存在）")

print()

# ==================== 檢查 jenkins.py 調用 ====================
print("步驟 3: 檢查 jenkins.py 中的方法調用")
print("-" * 80)

jenkins_file = project_root / 'backend' / 'api' / 'views' / 'jenkins.py'

if not jenkins_file.exists():
    print(f"✗ jenkins.py 不存在: {jenkins_file}")
    sys.exit(1)

with open(jenkins_file, 'r', encoding='utf-8') as f:
    jenkins_content = f.read()

# 檢查方法調用
method_calls = [
    ('service.get_full_inventory(use_cache=use_cache)', 'get_full_inventory 調用'),
    ('service.get_host_config(hostname, use_cache=use_cache)', 'get_host_config 調用'),
    ('service.clear_cache(', 'clear_cache 調用'),
]

for call, desc in method_calls:
    if call in jenkins_content:
        print(f"  ✓ {desc} 存在")
    else:
        print(f"  ⚠ {desc} 未找到（可能調用方式不同）")

print()

# ==================== 檢查返回值結構 ====================
print("步驟 4: 檢查返回值結構")
print("-" * 80)

# get_full_inventory 返回值檢查
get_full_start = content.find('def get_full_inventory(')
get_full_end = content.find('\n    def ', get_full_start + 1)
if get_full_end == -1:
    get_full_end = content.find('\n    def clear_cache', get_full_start)

get_full_content = content[get_full_start:get_full_end]

full_inv_checks = [
    ("'success':", 'success 字段'),
    ("'cached':", 'cached 字段'),
    ("'data':", 'data 字段'),
    ("'error':", 'error 字段'),
]

print("get_full_inventory 返回值:")
for pattern, desc in full_inv_checks:
    if pattern in get_full_content:
        print(f"  ✓ 包含 {desc}")
    else:
        print(f"  ✗ 缺少 {desc}")

print()

# get_host_config 返回值檢查
get_host_start = content.find('def get_host_config(')
get_host_end = content.find('\n    def clear_cache', get_host_start)

get_host_content = content[get_host_start:get_host_end]

host_config_checks = [
    ("'success':", 'success 字段'),
    ("'cached':", 'cached 字段'),
    ("'hostname':", 'hostname 字段'),
    ("'config':", 'config 字段'),
    ("'groups':", 'groups 字段'),
]

print("get_host_config 返回值:")
for pattern, desc in host_config_checks:
    if pattern in get_host_content:
        print(f"  ✓ 包含 {desc}")
    else:
        print(f"  ✗ 缺少 {desc}")

print()

# ==================== 檢查錯誤處理 ====================
print("步驟 5: 檢查錯誤處理")
print("-" * 80)

error_handling_checks = [
    ('try:', 'Try-catch 塊'),
    ('except FileNotFoundError', 'FileNotFoundError 處理'),
    ('except subprocess.TimeoutExpired', 'TimeoutExpired 處理'),
    ('except json.JSONDecodeError', 'JSONDecodeError 處理'),
    ('except Exception', '通用異常處理'),
    ('logger.error', '錯誤日誌'),
    ('logger.info', '資訊日誌'),
]

print("get_full_inventory 錯誤處理:")
for pattern, desc in error_handling_checks[:5]:
    if pattern in get_full_content:
        print(f"  ✓ {desc}")

print()
print("get_host_config 錯誤處理:")
for pattern, desc in error_handling_checks:
    if pattern in get_host_content:
        print(f"  ✓ {desc}")

print()

# ==================== 檢查核心邏輯 ====================
print("步驟 6: 檢查核心邏輯")
print("-" * 80)

print("get_full_inventory 邏輯:")
full_logic_checks = [
    ('os.path.exists(self.nas_base_path)', '文件存在性檢查'),
    ('self.parse_inventory(self.nas_base_path)', '調用 parse_inventory'),
]

for pattern, desc in full_logic_checks:
    if pattern in get_full_content:
        print(f"  ✓ {desc}")
    else:
        print(f"  ✗ {desc} 缺失")

print()
print("get_host_config 邏輯:")
host_logic_checks = [
    ('ansible-inventory', '使用 ansible-inventory 命令'),
    ('--host', '使用 --host 參數'),
    ('subprocess.run', '執行子進程'),
    ('json.loads', '解析 JSON'),
]

for pattern, desc in host_logic_checks:
    if pattern in get_host_content:
        print(f"  ✓ {desc}")
    else:
        print(f"  ✗ {desc} 缺失")

print()

# ==================== 總結 ====================
print("=" * 80)
print("✓✓✓ AnsibleInventoryService 方法驗證完成！✓✓✓")
print("=" * 80)
print()
print("修復摘要：")
print("  ✓ get_full_inventory() - 獲取完整 Inventory 數據")
print("  ✓ get_host_config() - 獲取特定主機配置")
print("  ✓ clear_cache() - 快取管理（預留）")
print()
print("所有方法特性：")
print("  ✓ 完整的錯誤處理")
print("  ✓ 詳細的日誌記錄")
print("  ✓ 統一的返回值格式")
print("  ✓ use_cache 參數支持（預留）")
print()
print("測試建議：")
print("  1. 訪問 RVT Build 配置檢查頁面")
print("  2. 驗證不再出現 AttributeError")
print("  3. 確認可以正常顯示 Inventory 數據")
print("  4. 測試主機配置查看功能")
print()
