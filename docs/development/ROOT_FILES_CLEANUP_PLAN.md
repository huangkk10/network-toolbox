# 根目錄文件清理評估報告

## 📅 評估日期
**2025-11-11**

---

## 📋 待評估的文件

### 1. `deploy_ansible_inventory.sh` ⚠️ **建議移動**

**類型**：Shell 腳本（13 KB）

**用途**：
- Ansible Inventory 功能部署腳本
- 用於一次性部署和驗證 Ansible 功能

**內容分析**：
- 重建 Django 容器（安裝 Ansible）
- 驗證 Ansible 安裝
- 測試 API 端點
- 驗證快取機制
- 測試 Celery 清理任務

**最後修改**：2025-11-11 07:55

**建議**：
- ⚠️ **移動到 `scripts/deployment/`**
- 這是部署腳本，不是日常使用的腳本
- 功能應該已經部署完成

**執行命令**：
```bash
mv deploy_ansible_inventory.sh scripts/deployment/
```

---

### 2. `deploy_log.txt` ❌ **可以刪除**

**類型**：日誌文件（11 KB）

**用途**：
- `deploy_ansible_inventory.sh` 執行時的輸出日誌
- 記錄 2025-11-11 07:52 的部署過程

**內容分析**：
- Docker 容器重建日誌
- Ansible 安裝驗證輸出
- API 測試結果
- 帶有 ANSI 顏色代碼

**建議**：
- ❌ **可以刪除**
- 這是臨時的部署日誌
- 功能已部署完成，日誌可以清理
- 如果需要保留歷史記錄 → 移動到 `logs/deployment/` 或 `docs/deployment/`

**刪除命令**：
```bash
rm deploy_log.txt
```

**或保留命令**：
```bash
mkdir -p logs/deployment
mv deploy_log.txt logs/deployment/ansible_inventory_deploy_2025-11-11.log
```

---

### 3. `verify_all.sh` ✅ **保留在根目錄**

**類型**：Shell 腳本（6.0 KB）

**用途**：
- 系統驗證腳本
- 驗證所有 API 端點和功能是否正常運作
- **經常使用的診斷工具**

**內容分析**：
- 測試多個 API 端點
- 檢查系統健康狀態
- 提供友好的測試結果輸出
- 使用顏色高亮顯示結果

**最後修改**：2025-10-27 11:35

**建議**：
- ✅ **保留在根目錄**
- 這是日常使用的系統驗證腳本
- 方便用戶快速檢查系統狀態
- 已在文檔中提及（如 CLEANUP_REPORT.md）

**保留理由**：
1. 經常使用
2. 系統級別的診斷工具
3. 用戶需要快速訪問
4. 文檔中有引用

---

### 4. `test_jenkins_auto_storage.sh` ⚠️ **建議移動**

**類型**：Shell 腳本（9.9 KB）

**用途**：
- Jenkins Builds 自動存儲功能測試腳本
- 測試 Celery 定時任務和手動存儲功能

**內容分析**：
- 檢查資料庫中的 Jenkins Builds 狀態
- 測試 Celery 定時任務
- 測試手動存儲 API
- 驗證自動存儲功能

**最後修改**：2025-11-10 10:31

**建議**：
- ⚠️ **移動到 `tests/integration/` 或 `scripts/testing/`**
- 這是測試腳本，不是日常使用的工具
- 功能應該已經驗證完成

**執行命令**：
```bash
# 選項 1：移動到測試目錄
mkdir -p tests/integration/jenkins
mv test_jenkins_auto_storage.sh tests/integration/jenkins/

# 選項 2：移動到腳本測試目錄
mkdir -p scripts/testing
mv test_jenkins_auto_storage.sh scripts/testing/
```

---

## 📊 清理建議總結

| 文件 | 類型 | 大小 | 建議操作 | 目標位置 |
|------|------|------|----------|----------|
| `deploy_ansible_inventory.sh` | 腳本 | 13 KB | ⚠️ 移動 | `scripts/deployment/` |
| `deploy_log.txt` | 日誌 | 11 KB | ❌ 刪除 | 可選：`logs/deployment/` |
| `verify_all.sh` | 腳本 | 6.0 KB | ✅ 保留 | 根目錄 |
| `test_jenkins_auto_storage.sh` | 腳本 | 9.9 KB | ⚠️ 移動 | `tests/integration/` 或 `scripts/testing/` |

---

## 🎯 推薦執行方案

### 方案一：完整清理（推薦）

```bash
#!/bin/bash
cd /home/owner/Codes/network-toolbox

# 1. 創建目標目錄
mkdir -p scripts/deployment
mkdir -p scripts/testing

# 2. 移動部署腳本
mv deploy_ansible_inventory.sh scripts/deployment/
echo "✅ 已移動: deploy_ansible_inventory.sh → scripts/deployment/"

# 3. 刪除臨時日誌
rm deploy_log.txt
echo "✅ 已刪除: deploy_log.txt"

# 4. 移動測試腳本
mv test_jenkins_auto_storage.sh scripts/testing/
echo "✅ 已移動: test_jenkins_auto_storage.sh → scripts/testing/"

# 5. 保留驗證腳本
echo "✅ 保留: verify_all.sh（根目錄）"

echo ""
echo "🎉 清理完成！"
```

---

### 方案二：保守清理

只刪除日誌文件，保留其他腳本：

```bash
#!/bin/bash
cd /home/owner/Codes/network-toolbox

# 只刪除臨時日誌
rm deploy_log.txt
echo "✅ 已刪除: deploy_log.txt"

# 其他腳本暫時保留在根目錄
echo "✅ 其他腳本保留在根目錄"
```

---

### 方案三：保留日誌的完整清理

保留日誌作為歷史記錄：

```bash
#!/bin/bash
cd /home/owner/Codes/network-toolbox

# 1. 創建目標目錄
mkdir -p scripts/deployment
mkdir -p scripts/testing
mkdir -p logs/deployment

# 2. 移動部署腳本和日誌
mv deploy_ansible_inventory.sh scripts/deployment/
mv deploy_log.txt logs/deployment/ansible_inventory_deploy_2025-11-11.log
echo "✅ 部署腳本和日誌已移動"

# 3. 移動測試腳本
mv test_jenkins_auto_storage.sh scripts/testing/
echo "✅ 測試腳本已移動"

# 4. 保留驗證腳本
echo "✅ verify_all.sh 保留在根目錄"
```

---

## 📂 清理後的目錄結構

### 根目錄（方案一執行後）

```
根目錄/
├── start.sh                    # 系統啟動
├── stop.sh                     # 系統停止
├── verify_all.sh               # ✅ 系統驗證（保留）
├── start_auto_sync.sh          # DHCP 日誌自動同步
├── start_auto_sync_leases.sh   # DHCP 租約自動同步
└── organize_shell_scripts.sh   # 本次整理腳本
```

### scripts/ 目錄

```
scripts/
├── maintenance/                # 維護腳本
│   ├── cleanup_root_scripts.sh
│   ├── cleanup_test_scripts.sh
│   ├── fix_dhcp_timezone.sh
│   ├── organize_root_docs.sh
│   └── reorganize_docs_phase2.sh
├── deployment/                 # 部署腳本
│   └── deploy_ansible_inventory.sh  ✅ 新移動
└── testing/                    # 測試腳本
    └── test_jenkins_auto_storage.sh  ✅ 新移動
```

### logs/ 目錄（如果選擇方案三）

```
logs/
├── deployment/                 # 部署日誌
│   └── ansible_inventory_deploy_2025-11-11.log
└── ... (其他日誌)
```

---

## ✅ 驗證步驟

清理後執行驗證：

```bash
# 1. 檢查根目錄
ls -1 *.sh 2>/dev/null
# 應該看到 verify_all.sh 保留

# 2. 檢查 scripts/ 目錄
tree scripts/ -L 2

# 3. 測試驗證腳本
./verify_all.sh

# 4. 測試移動後的腳本（如需要）
./scripts/deployment/deploy_ansible_inventory.sh
./scripts/testing/test_jenkins_auto_storage.sh
```

---

## 📝 為什麼這樣分類？

### 保留在根目錄
- ✅ **verify_all.sh** - 經常使用的診斷工具
- ✅ **start.sh, stop.sh** - 系統啟動/停止
- ✅ **start_auto_sync*.sh** - 功能啟動腳本（文檔有引用）

### 移動到 scripts/deployment/
- ⚠️ **deploy_ansible_inventory.sh** - 一次性部署腳本
- 已完成部署，不需要頻繁使用

### 移動到 scripts/testing/
- ⚠️ **test_jenkins_auto_storage.sh** - 功能測試腳本
- 功能已驗證完成，不需要頻繁使用

### 刪除
- ❌ **deploy_log.txt** - 臨時部署日誌
- 功能已部署，日誌無保留價值
- 如需歷史記錄，可移到 logs/deployment/

---

## 🔄 維護建議

### 1. 日誌文件管理
- ❌ 不要將臨時日誌放在根目錄
- ✅ 使用 `logs/` 目錄存放日誌
- ✅ 定期清理過期日誌（超過 30 天）

### 2. 部署腳本管理
- ❌ 部署完成後不要留在根目錄
- ✅ 移動到 `scripts/deployment/`
- ✅ 保留以供未來重新部署使用

### 3. 測試腳本管理
- ❌ 測試完成後不要留在根目錄
- ✅ 移動到 `tests/` 或 `scripts/testing/`
- ✅ 保留以供回歸測試使用

---

## 📚 相關文檔

- **Shell 腳本清理**: `docs/development/SHELL_SCRIPTS_CLEANUP_REPORT.md`
- **Python 腳本清理**: `docs/development/ROOT_SCRIPTS_CLEANUP_REPORT.md`
- **文檔整理**: `docs/development/FINAL_DOCS_CLEANUP_REPORT.md`

---

**評估日期**: 2025-11-11  
**評估者**: GitHub Copilot  
**建議**: 執行方案一（完整清理）
