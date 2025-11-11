# Shell 腳本清理評估報告

## 📅 評估日期
**2025-11-11**

---

## 📋 待評估的腳本

### 1. `cleanup_root_scripts.sh` ✅ **可以移動到 scripts/**

**用途**：
- 清理根目錄的重複和過時 Python 腳本
- 已執行完畢，功能已完成

**狀態**：
- ✅ 已執行完畢
- ✅ 已生成報告：`docs/development/ROOT_SCRIPTS_CLEANUP_REPORT.md`

**建議**：
- ⚠️ **移動到 `scripts/maintenance/`**
- 保留作為歷史記錄和未來參考
- 未來可能需要再次清理時使用

**執行命令**：
```bash
mv cleanup_root_scripts.sh scripts/maintenance/
```

---

### 2. `cleanup_test_scripts.sh` ✅ **可以移動到 scripts/**

**用途**：
- 測試腳本清理自動化腳本
- 刪除過時的測試腳本

**狀態**：
- ✅ 已執行完畢
- ✅ 相關報告：`docs/development/CLEANUP_TEST_SCRIPTS.md`

**建議**：
- ⚠️ **移動到 `scripts/maintenance/`**
- 保留作為歷史記錄

**執行命令**：
```bash
mv cleanup_test_scripts.sh scripts/maintenance/
```

---

### 3. `deploy_ansible_inventory.sh` ⚠️ **需要確認**

**用途**：
- Ansible Inventory 功能部署腳本

**狀態**：
- ❓ 需要確認是否還在使用

**建議**：
- 如果功能已穩定運行 → **移動到 `scripts/deployment/`**
- 如果還在開發測試 → **保留在根目錄**

**檢查方式**：
```bash
# 檢查是否有相關文檔
ls docs/features/ansible-inventory/
```

---

### 4. `fix_dhcp_timezone.sh` ✅ **可以移動到 scripts/**

**用途**：
- DHCP 日誌時區修復腳本
- 一次性修復腳本

**狀態**：
- ✅ 問題已修復
- ✅ 相關報告：`docs/troubleshooting/DHCP_TIMEZONE_FIX.md`

**建議**：
- ⚠️ **移動到 `scripts/maintenance/`**
- 保留以防未來需要再次修復

**執行命令**：
```bash
mv fix_dhcp_timezone.sh scripts/maintenance/
```

---

### 5. `organize_root_docs.sh` ✅ **可以移動到 scripts/**

**用途**：
- 將根目錄的文檔移動到 docs/ 目錄
- 已執行完畢

**狀態**：
- ✅ 已執行完畢
- ✅ 已生成報告：`docs/development/DOCS_ORGANIZATION_REPORT.md`

**建議**：
- ⚠️ **移動到 `scripts/maintenance/`**
- 保留作為文檔整理的參考範本

**執行命令**：
```bash
mv organize_root_docs.sh scripts/maintenance/
```

---

### 6. `reorganize_docs_phase2.sh` ✅ **可以移動到 scripts/**

**用途**：
- 文檔整理腳本 - 第二階段
- 已執行完畢

**狀態**：
- ✅ 已執行完畢
- ✅ 相關報告：`docs/development/DOCS_REORGANIZATION_REPORT_2025_11_11.md`

**建議**：
- ⚠️ **移動到 `scripts/maintenance/`**
- 與 `organize_root_docs.sh` 一起保存

**執行命令**：
```bash
mv reorganize_docs_phase2.sh scripts/maintenance/
```

---

### 7. `start_auto_sync_leases.sh` ⚠️ **保留或移動**

**用途**：
- DHCP 租約自動同步 - 啟動與測試腳本
- **仍在使用中**

**引用位置**：
- `docs/quickstart/AUTO_SYNC_DHCP_LEASES_QUICKSTART.md`
- `docs/features/AUTO_SYNC_DHCP_LEASES.md`

**建議**：
- 🔵 **選項 1：保留在根目錄**（推薦）
  - 因為快速指南中有引用
  - 用戶容易找到和執行
  
- 🔵 **選項 2：移動到 `scripts/`** 並更新文檔
  - 移動到 `scripts/auto-sync/`
  - 更新所有文檔中的路徑引用

**如果移動**：
```bash
mkdir -p scripts/auto-sync
mv start_auto_sync_leases.sh scripts/auto-sync/
# 然後更新文檔中的引用
```

---

### 8. `start_auto_sync.sh` ⚠️ **保留或移動**

**用途**：
- 啟動並測試 DHCP 日誌自動同步功能
- **仍在使用中**

**引用位置**：
- `docs/quickstart/AUTO_SYNC_DHCP_LOGS_QUICKSTART.md`

**建議**：
- 🔵 **選項 1：保留在根目錄**（推薦）
  - 因為快速指南中有引用
  - 用戶容易找到和執行
  
- 🔵 **選項 2：移動到 `scripts/`** 並更新文檔
  - 移動到 `scripts/auto-sync/`
  - 更新所有文檔中的路徑引用

**如果移動**：
```bash
mkdir -p scripts/auto-sync
mv start_auto_sync.sh scripts/auto-sync/
# 然後更新文檔中的引用
```

---

## 📊 清理建議總結

| 腳本名稱 | 當前狀態 | 建議操作 | 目標位置 |
|---------|---------|---------|---------|
| `cleanup_root_scripts.sh` | 已完成 | ✅ 移動 | `scripts/maintenance/` |
| `cleanup_test_scripts.sh` | 已完成 | ✅ 移動 | `scripts/maintenance/` |
| `deploy_ansible_inventory.sh` | 需確認 | ⚠️ 待定 | `scripts/deployment/` 或保留 |
| `fix_dhcp_timezone.sh` | 已完成 | ✅ 移動 | `scripts/maintenance/` |
| `organize_root_docs.sh` | 已完成 | ✅ 移動 | `scripts/maintenance/` |
| `reorganize_docs_phase2.sh` | 已完成 | ✅ 移動 | `scripts/maintenance/` |
| `start_auto_sync_leases.sh` | 使用中 | 🔵 保留或移動 | 根目錄 或 `scripts/auto-sync/` |
| `start_auto_sync.sh` | 使用中 | 🔵 保留或移動 | 根目錄 或 `scripts/auto-sync/` |

---

## 🎯 推薦方案

### 方案一：最小改動（推薦）

**移動已完成的維護腳本，保留功能性腳本在根目錄**

```bash
# 1. 創建目錄
mkdir -p scripts/maintenance
mkdir -p scripts/deployment

# 2. 移動已完成的維護腳本
mv cleanup_root_scripts.sh scripts/maintenance/
mv cleanup_test_scripts.sh scripts/maintenance/
mv fix_dhcp_timezone.sh scripts/maintenance/
mv organize_root_docs.sh scripts/maintenance/
mv reorganize_docs_phase2.sh scripts/maintenance/

# 3. 檢查 deploy_ansible_inventory.sh 狀態後決定
# 如果功能已穩定：
mv deploy_ansible_inventory.sh scripts/deployment/

# 4. 保留在根目錄（仍在使用）
# - start_auto_sync_leases.sh
# - start_auto_sync.sh
```

**優點**：
- ✅ 根目錄更整潔
- ✅ 不需要更新文檔
- ✅ 用戶體驗不受影響

**結果**：
```
根目錄/
├── start.sh                    # 系統啟動
├── stop.sh                     # 系統停止
├── verify_all.sh               # 系統驗證
├── start_auto_sync.sh          # DHCP 日誌自動同步（使用中）
├── start_auto_sync_leases.sh   # DHCP 租約自動同步（使用中）
└── ...
```

---

### 方案二：完全整理

**將所有腳本移動到 scripts/ 目錄**

```bash
# 1. 創建目錄結構
mkdir -p scripts/maintenance
mkdir -p scripts/deployment
mkdir -p scripts/auto-sync

# 2. 移動所有腳本
mv cleanup_root_scripts.sh scripts/maintenance/
mv cleanup_test_scripts.sh scripts/maintenance/
mv fix_dhcp_timezone.sh scripts/maintenance/
mv organize_root_docs.sh scripts/maintenance/
mv reorganize_docs_phase2.sh scripts/maintenance/
mv deploy_ansible_inventory.sh scripts/deployment/
mv start_auto_sync.sh scripts/auto-sync/
mv start_auto_sync_leases.sh scripts/auto-sync/

# 3. 更新文檔引用
# 需要更新以下文件：
# - docs/quickstart/AUTO_SYNC_DHCP_LOGS_QUICKSTART.md
# - docs/quickstart/AUTO_SYNC_DHCP_LEASES_QUICKSTART.md
# - docs/features/AUTO_SYNC_DHCP_LEASES.md
```

**優點**：
- ✅ 根目錄最整潔
- ✅ 腳本分類清楚

**缺點**：
- ❌ 需要更新多個文檔
- ❌ 用戶需要記住新路徑

---

## 🚀 執行清理（方案一）

### 自動執行腳本

```bash
#!/bin/bash
# Shell 腳本整理 - 移動已完成的維護腳本

cd /home/owner/Codes/network-toolbox

echo "🗂️  整理 Shell 腳本..."
echo ""

# 創建目錄
mkdir -p scripts/maintenance
mkdir -p scripts/deployment

# 移動已完成的維護腳本
echo "📦 移動維護腳本..."
mv cleanup_root_scripts.sh scripts/maintenance/ 2>/dev/null && echo "✅ cleanup_root_scripts.sh"
mv cleanup_test_scripts.sh scripts/maintenance/ 2>/dev/null && echo "✅ cleanup_test_scripts.sh"
mv fix_dhcp_timezone.sh scripts/maintenance/ 2>/dev/null && echo "✅ fix_dhcp_timezone.sh"
mv organize_root_docs.sh scripts/maintenance/ 2>/dev/null && echo "✅ organize_root_docs.sh"
mv reorganize_docs_phase2.sh scripts/maintenance/ 2>/dev/null && echo "✅ reorganize_docs_phase2.sh"

echo ""
echo "📋 根目錄保留的腳本："
ls -1 *.sh 2>/dev/null | head -10

echo ""
echo "✅ 整理完成！"
```

---

## ✅ 驗證

### 檢查根目錄

```bash
$ ls -1 *.sh | head -10
start.sh
stop.sh
verify_all.sh
start_auto_sync.sh
start_auto_sync_leases.sh
...
```

### 檢查 scripts/ 目錄

```bash
$ tree scripts/ -L 2
scripts/
├── maintenance/
│   ├── cleanup_root_scripts.sh
│   ├── cleanup_test_scripts.sh
│   ├── fix_dhcp_timezone.sh
│   ├── organize_root_docs.sh
│   └── reorganize_docs_phase2.sh
├── deployment/
│   └── deploy_ansible_inventory.sh (可選)
└── auto-sync/ (如果選擇方案二)
    ├── start_auto_sync.sh
    └── start_auto_sync_leases.sh
```

---

## 📚 相關文檔

- **Python 腳本清理**: `docs/development/ROOT_SCRIPTS_CLEANUP_REPORT.md`
- **測試腳本清理**: `docs/development/CLEANUP_TEST_SCRIPTS.md`
- **文檔整理報告**: `docs/development/FINAL_DOCS_CLEANUP_REPORT.md`

---

## 📝 注意事項

1. **deploy_ansible_inventory.sh**
   - 需要先確認功能狀態
   - 如果仍在開發，建議保留在根目錄

2. **start_auto_sync*.sh**
   - 這些是功能性腳本，仍在使用
   - 建議保留在根目錄方便用戶使用
   - 或移動後更新所有文檔引用

3. **保留歷史**
   - 所有移動的腳本都保存在 `scripts/` 目錄
   - 未來需要時可以參考或重新執行

---

**評估日期**: 2025-11-11  
**評估者**: GitHub Copilot  
**建議**: 執行方案一（最小改動）
