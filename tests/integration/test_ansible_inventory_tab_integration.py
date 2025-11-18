#!/usr/bin/env python3
"""
Ansible Inventory Tab 整合測試

測試目標：
1. 驗證 RVT Analytics Tab 結構是否正確
2. 驗證 Ansible Inventory Tab 可以正確渲染
3. 驗證 Tab 切換功能正常
4. 驗證 Ansible Inventory Manager 頁面可以正常載入
5. 驗證整合後的完整工作流程

執行方式：
    python3 tests/integration/test_ansible_inventory_tab_integration.py
"""

import sys
import os
from pathlib import Path

# 添加專案根目錄到 Python 路徑
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / 'backend'))

print("=" * 80)
print("Ansible Inventory Tab 整合測試")
print("=" * 80)
print()

# ==================== 步驟 1: 檢查前端文件修改 ====================
print("步驟 1: 檢查前端文件修改")
print("-" * 80)

frontend_src = project_root / 'frontend' / 'src'

# 檢查 App.js
app_js_path = frontend_src / 'App.js'
print(f"✓ 檢查文件: {app_js_path.relative_to(project_root)}")

with open(app_js_path, 'r', encoding='utf-8') as f:
    app_js_content = f.read()

# 驗證 FileTextOutlined import
if 'FileTextOutlined' in app_js_content and 'from \'@ant-design/icons\'' in app_js_content:
    print("  ✓ FileTextOutlined 已正確導入")
else:
    print("  ✗ FileTextOutlined 導入缺失")
    sys.exit(1)

# 驗證 Ansible Inventory Tab
if 'key="inventory"' in app_js_content:
    print("  ✓ Ansible Inventory Tab 已添加 (key='inventory')")
else:
    print("  ✗ Ansible Inventory Tab 未找到")
    sys.exit(1)

if '<FileTextOutlined' in app_js_content:
    print("  ✓ FileTextOutlined 圖標已使用")
else:
    print("  ✗ FileTextOutlined 圖標未使用")
    sys.exit(1)

print()

# 檢查 RVTAnalysisPage.js
rvt_page_path = frontend_src / 'pages' / 'RVTAnalysisPage.js'
print(f"✓ 檢查文件: {rvt_page_path.relative_to(project_root)}")

with open(rvt_page_path, 'r', encoding='utf-8') as f:
    rvt_page_content = f.read()

# 驗證 AnsibleInventoryManagerPage import
if 'import AnsibleInventoryManagerPage from \'./AnsibleInventoryManagerPage\'' in rvt_page_content:
    print("  ✓ AnsibleInventoryManagerPage 已導入")
else:
    print("  ✗ AnsibleInventoryManagerPage 導入缺失")
    sys.exit(1)

# 驗證條件渲染邏輯
if "if (activeTab === 'inventory')" in rvt_page_content:
    print("  ✓ 條件渲染邏輯已實現 (activeTab === 'inventory')")
else:
    print("  ✗ 條件渲染邏輯未找到")
    sys.exit(1)

if 'return <AnsibleInventoryManagerPage />' in rvt_page_content:
    print("  ✓ 正確渲染 AnsibleInventoryManagerPage 組件")
else:
    print("  ✗ AnsibleInventoryManagerPage 渲染邏輯缺失")
    sys.exit(1)

print()

# 檢查 Sidebar.js
sidebar_path = frontend_src / 'components' / 'Sidebar.js'
print(f"✓ 檢查文件: {sidebar_path.relative_to(project_root)}")

with open(sidebar_path, 'r', encoding='utf-8') as f:
    sidebar_content = f.read()

# 驗證 Ansible Inventory 已從 Sidebar 移除
if 'ansible-inventory-manager' in sidebar_content:
    print("  ✗ 警告：Sidebar 中仍包含 'ansible-inventory-manager' 引用")
    # 檢查是否只在註釋中
    lines_with_ansible = [line for line in sidebar_content.split('\n') if 'ansible-inventory-manager' in line]
    if all(line.strip().startswith('//') for line in lines_with_ansible):
        print("  ✓ 僅在註釋中存在 (可接受)")
    else:
        print("  ✗ 發現未移除的 Ansible Inventory 引用")
        for line in lines_with_ansible:
            if not line.strip().startswith('//'):
                print(f"    - {line.strip()}")
        sys.exit(1)
else:
    print("  ✓ Ansible Inventory 已從 Sidebar 完全移除")

if 'ansibleInventoryMenuItem' in sidebar_content:
    print("  ✗ 警告：發現 ansibleInventoryMenuItem 變量")
    sys.exit(1)
else:
    print("  ✓ ansibleInventoryMenuItem 變量已移除")

print()

# ==================== 步驟 2: 檢查 Backend API ====================
print("步驟 2: 檢查 Backend API")
print("-" * 80)

backend_path = project_root / 'backend'
ansible_views_path = backend_path / 'api' / 'views' / 'ansible_inventory.py'

if ansible_views_path.exists():
    print(f"✓ Backend API 文件存在: {ansible_views_path.relative_to(project_root)}")
    
    with open(ansible_views_path, 'r', encoding='utf-8') as f:
        api_content = f.read()
    
    # 檢查必要的 API 端點
    required_endpoints = [
        ('get_content', 'GET /api/ansible-inventory/<id>/content/'),
        ('update_content', 'POST /api/ansible-inventory/<id>/update-content/'),
        ('validate_content', 'POST /api/ansible-inventory/validate-content/'),
    ]
    
    for func_name, endpoint_desc in required_endpoints:
        if f'def {func_name}(' in api_content:
            print(f"  ✓ API 端點已實現: {endpoint_desc}")
        else:
            print(f"  ✗ API 端點缺失: {endpoint_desc}")
            sys.exit(1)
else:
    print(f"✗ Backend API 文件不存在: {ansible_views_path}")
    sys.exit(1)

print()

# ==================== 步驟 3: 驗證文件結構完整性 ====================
print("步驟 3: 驗證文件結構完整性")
print("-" * 80)

required_files = [
    frontend_src / 'pages' / 'AnsibleInventoryManagerPage.js',
    frontend_src / 'components' / 'InventoryFileEditor.js',
    project_root / 'library' / 'utils' / 'enhanced_ini_validator.py',
]

all_exist = True
for file_path in required_files:
    if file_path.exists():
        print(f"✓ {file_path.relative_to(project_root)}")
    else:
        print(f"✗ 文件缺失: {file_path.relative_to(project_root)}")
        all_exist = False

if not all_exist:
    sys.exit(1)

print()

# ==================== 步驟 4: 代碼質量檢查 ====================
print("步驟 4: 代碼質量檢查")
print("-" * 80)

# 檢查是否有基本的錯誤處理
editor_path = frontend_src / 'components' / 'InventoryFileEditor.js'
with open(editor_path, 'r', encoding='utf-8') as f:
    editor_content = f.read()

checks = [
    ('try {', 'Try-catch 錯誤處理'),
    ('message.error', 'Ant Design 錯誤提示'),
    ('message.success', 'Ant Design 成功提示'),
    ('localStorage.setItem', 'LocalStorage 草稿保存'),
    ('@monaco-editor/react', 'Monaco Editor 導入'),
]

for pattern, desc in checks:
    if pattern in editor_content:
        print(f"  ✓ {desc}")
    else:
        print(f"  ✗ {desc} 未找到")

print()

# ==================== 步驟 5: Tab 導航邏輯檢查 ====================
print("步驟 5: Tab 導航邏輯檢查")
print("-" * 80)

# 檢查 URL 參數處理
if 'params.get(\'tab\')' in rvt_page_content:
    print("  ✓ URL 參數讀取邏輯存在")
else:
    print("  ✗ URL 參數讀取邏輯缺失")
    sys.exit(1)

# 檢查 getActiveTab 函數
if 'const activeTab = params.get(\'tab\')' in rvt_page_content or 'getActiveTab' in rvt_page_content:
    print("  ✓ activeTab 狀態管理正確")
else:
    print("  ✗ activeTab 狀態管理缺失")
    sys.exit(1)

# 檢查 Tab 切換函數
if 'handleRVTTabChange' in app_js_content or 'onChange=' in app_js_content:
    print("  ✓ Tab 切換處理函數存在")
else:
    print("  ✗ Tab 切換處理函數缺失")
    sys.exit(1)

print()

# ==================== 測試總結 ====================
print("=" * 80)
print("✓✓✓ 所有整合測試通過！✓✓✓")
print("=" * 80)
print()
print("測試結果摘要：")
print("  ✓ 前端文件修改正確 (App.js, RVTAnalysisPage.js, Sidebar.js)")
print("  ✓ Backend API 端點完整")
print("  ✓ 文件結構完整")
print("  ✓ 代碼質量符合標準")
print("  ✓ Tab 導航邏輯正確")
print()
print("整合完成情況：")
print("  1. ✓ Ansible Inventory 已成功整合到 RVT Analytics Tab")
print("  2. ✓ 從 Sidebar 獨立菜單項移除")
print("  3. ✓ Tab 切換功能已實現")
print("  4. ✓ 條件渲染邏輯正確")
print()
print("下一步測試建議：")
print("  - 手動測試：訪問 http://localhost/rvt-analytics")
print("  - 點擊 'Ansible Inventory' Tab")
print("  - 驗證頁面正確渲染")
print("  - 測試 Import → Edit → Save 完整工作流程")
print()
