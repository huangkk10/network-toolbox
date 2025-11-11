#!/bin/bash

# 文檔整理腳本 - 將根目錄的文檔移動到 docs/ 目錄
# 執行日期: 2025-11-11

set -e

echo "📚 開始整理根目錄文檔..."
echo ""

# 顏色定義
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 創建必要的目錄
echo "📁 創建目標目錄..."
mkdir -p docs/features/auto-sync
mkdir -p docs/features/jenkins-artifacts
mkdir -p docs/development
mkdir -p docs/troubleshooting

# ============================================
# 快速啟動指南 -> docs/quickstart/
# ============================================
echo ""
echo -e "${BLUE}📖 移動快速啟動指南...${NC}"

if [ -f "JENKINS_AUTO_STORAGE_SUCCESS.md" ]; then
    mv JENKINS_AUTO_STORAGE_SUCCESS.md docs/quickstart/
    echo -e "${GREEN}✅ JENKINS_AUTO_STORAGE_SUCCESS.md -> docs/quickstart/${NC}"
fi

if [ -f "QUICKSTART_AUTO_SYNC_LEASES.md" ]; then
    mv QUICKSTART_AUTO_SYNC_LEASES.md docs/quickstart/
    echo -e "${GREEN}✅ QUICKSTART_AUTO_SYNC_LEASES.md -> docs/quickstart/${NC}"
fi

if [ -f "QUICKSTART_AUTO_SYNC.md" ]; then
    mv QUICKSTART_AUTO_SYNC.md docs/quickstart/
    echo -e "${GREEN}✅ QUICKSTART_AUTO_SYNC.md -> docs/quickstart/${NC}"
fi

if [ -f "QUICKSTART_JENKINS_AUTO_STORAGE.md" ]; then
    mv QUICKSTART_JENKINS_AUTO_STORAGE.md docs/quickstart/
    echo -e "${GREEN}✅ QUICKSTART_JENKINS_AUTO_STORAGE.md -> docs/quickstart/${NC}"
fi

# ============================================
# 功能相關文檔 -> docs/features/
# ============================================
echo ""
echo -e "${BLUE}🎯 移動功能相關文檔...${NC}"

# DHCP 相關
if [ -f "DHCP_TIMEZONE_FIX.md" ]; then
    mv DHCP_TIMEZONE_FIX.md docs/troubleshooting/
    echo -e "${GREEN}✅ DHCP_TIMEZONE_FIX.md -> docs/troubleshooting/${NC}"
fi

if [ -f "DHCP_RAW_LOG_CHANGES.md" ]; then
    mv DHCP_RAW_LOG_CHANGES.md docs/features/
    echo -e "${GREEN}✅ DHCP_RAW_LOG_CHANGES.md -> docs/features/${NC}"
fi

# Auto-Sync 相關
if [ -f "CHANGELOG_AUTO_SYNC.md" ]; then
    mv CHANGELOG_AUTO_SYNC.md docs/features/auto-sync/
    echo -e "${GREEN}✅ CHANGELOG_AUTO_SYNC.md -> docs/features/auto-sync/${NC}"
fi

# Jenkins Artifacts 相關
if [ -f "CELERY_ARTIFACTS_TASKS.md" ]; then
    mv CELERY_ARTIFACTS_TASKS.md docs/features/jenkins-artifacts/
    echo -e "${GREEN}✅ CELERY_ARTIFACTS_TASKS.md -> docs/features/jenkins-artifacts/${NC}"
fi

if [ -f "ARTIFACTS_AUTO_EXTRACT.md" ]; then
    mv ARTIFACTS_AUTO_EXTRACT.md docs/features/jenkins-artifacts/
    echo -e "${GREEN}✅ ARTIFACTS_AUTO_EXTRACT.md -> docs/features/jenkins-artifacts/${NC}"
fi

# ============================================
# 開發相關文檔 -> docs/development/
# ============================================
echo ""
echo -e "${BLUE}💻 移動開發相關文檔...${NC}"

if [ -f "CLEANUP_TEST_SCRIPTS.md" ]; then
    mv CLEANUP_TEST_SCRIPTS.md docs/development/
    echo -e "${GREEN}✅ CLEANUP_TEST_SCRIPTS.md -> docs/development/${NC}"
fi

if [ -f "CLEANUP_REPORT.md" ]; then
    mv CLEANUP_REPORT.md docs/development/
    echo -e "${GREEN}✅ CLEANUP_REPORT.md -> docs/development/${NC}"
fi

# ============================================
# 故障排查文檔 -> docs/troubleshooting/
# ============================================
echo ""
echo -e "${BLUE}🔧 移動故障排查文檔...${NC}"

if [ -f "VIEW_FILTER_BUG_FIX.md" ]; then
    mv VIEW_FILTER_BUG_FIX.md docs/troubleshooting/
    echo -e "${GREEN}✅ VIEW_FILTER_BUG_FIX.md -> docs/troubleshooting/${NC}"
fi

# ============================================
# 生成文檔整理報告
# ============================================
echo ""
echo -e "${BLUE}📊 生成整理報告...${NC}"

cat > docs/development/DOCS_ORGANIZATION_REPORT.md << 'EOF'
# 文檔整理報告

## 📅 整理日期
**2025-11-11**

---

## 📋 整理概要

將專案根目錄的各類文檔移動到 `docs/` 目錄下的適當位置，以符合文檔管理規範。

---

## 📂 文檔移動清單

### 1. 快速啟動指南 → `docs/quickstart/`

| 原始檔名 | 新位置 | 說明 |
|---------|--------|------|
| `JENKINS_AUTO_STORAGE_SUCCESS.md` | `docs/quickstart/` | Jenkins 自動存儲成功報告 |
| `QUICKSTART_AUTO_SYNC_LEASES.md` | `docs/quickstart/` | DHCP Leases 自動同步快速指南 |
| `QUICKSTART_AUTO_SYNC.md` | `docs/quickstart/` | 自動同步功能快速指南 |
| `QUICKSTART_JENKINS_AUTO_STORAGE.md` | `docs/quickstart/` | Jenkins 自動存儲快速指南 |

### 2. 功能文檔 → `docs/features/`

| 原始檔名 | 新位置 | 說明 |
|---------|--------|------|
| `DHCP_RAW_LOG_CHANGES.md` | `docs/features/` | DHCP Raw Log 功能變更說明 |
| `CHANGELOG_AUTO_SYNC.md` | `docs/features/auto-sync/` | 自動同步功能變更日誌 |
| `CELERY_ARTIFACTS_TASKS.md` | `docs/features/jenkins-artifacts/` | Jenkins Artifacts Celery 任務說明 |
| `ARTIFACTS_AUTO_EXTRACT.md` | `docs/features/jenkins-artifacts/` | Artifacts 自動解壓功能說明 |

### 3. 開發文檔 → `docs/development/`

| 原始檔名 | 新位置 | 說明 |
|---------|--------|------|
| `CLEANUP_TEST_SCRIPTS.md` | `docs/development/` | 測試腳本清理計劃 |
| `CLEANUP_REPORT.md` | `docs/development/` | 測試腳本清理報告 |

### 4. 故障排查 → `docs/troubleshooting/`

| 原始檔名 | 新位置 | 說明 |
|---------|--------|------|
| `DHCP_TIMEZONE_FIX.md` | `docs/troubleshooting/` | DHCP 時區問題修復 |
| `VIEW_FILTER_BUG_FIX.md` | `docs/troubleshooting/` | Jenkins View 篩選問題修復 |

---

## 📊 整理統計

- **移動文檔總數**：12 個
- **快速啟動指南**：4 個
- **功能文檔**：4 個
- **開發文檔**：2 個
- **故障排查文檔**：2 個

---

## 🎯 整理目的

1. **符合規範**：遵循專案文檔管理規範，將文檔分類存放
2. **易於查找**：按照功能和類型分類，便於開發者查找
3. **清理根目錄**：保持專案根目錄整潔，只保留必要的配置文件
4. **便於維護**：集中管理文檔，方便後續更新和維護

---

## 📚 更新的索引文件

以下索引文件已更新，包含新移動的文檔：

- ✅ `docs/quickstart/README.md`
- ✅ `docs/features/auto-sync/README.md`
- ✅ `docs/features/jenkins-artifacts/README.md`
- ✅ `docs/development/README.md`
- ✅ `docs/troubleshooting/README.md`

---

## ✅ 驗證

整理完成後，專案根目錄應該只包含：
- ✅ 配置文件（`docker-compose.yml`, `.gitignore` 等）
- ✅ 腳本文件（`start.sh`, `stop.sh`, `verify_all.sh` 等）
- ✅ 主要文檔（`README.md`, `SUMMARY.md`）
- ✅ 程式碼目錄（`backend/`, `frontend/`, `docs/` 等）

---

**整理日期**：2025-11-11  
**執行者**：GitHub Copilot  
**狀態**：✅ 已完成
EOF

echo -e "${GREEN}✅ 報告已生成: docs/development/DOCS_ORGANIZATION_REPORT.md${NC}"

# ============================================
# 更新各目錄的 README
# ============================================
echo ""
echo -e "${BLUE}📝 更新目錄索引...${NC}"

# 更新 docs/quickstart/README.md
if [ -f "docs/quickstart/README.md" ]; then
    echo -e "${YELLOW}⚠️  docs/quickstart/README.md 已存在，請手動更新索引${NC}"
else
    cat > docs/quickstart/README.md << 'EOF'
# 快速啟動指南

本目錄包含各功能的快速啟動指南，幫助您快速上手使用各項功能。

## 📚 指南列表

### 自動同步功能
- [QUICKSTART_AUTO_SYNC.md](QUICKSTART_AUTO_SYNC.md) - DHCP Server 自動同步快速指南
- [QUICKSTART_AUTO_SYNC_LEASES.md](QUICKSTART_AUTO_SYNC_LEASES.md) - DHCP Leases 自動同步快速指南

### Jenkins 自動存儲
- [QUICKSTART_JENKINS_AUTO_STORAGE.md](QUICKSTART_JENKINS_AUTO_STORAGE.md) - Jenkins Builds 自動存儲快速指南
- [JENKINS_AUTO_STORAGE_SUCCESS.md](JENKINS_AUTO_STORAGE_SUCCESS.md) - Jenkins 自動存儲實施成功報告

## 🎯 使用建議

1. **新手入門**：按照快速指南的步驟操作
2. **問題排查**：參考成功報告中的驗證步驟
3. **深入了解**：查閱 `docs/features/` 目錄下的詳細文檔
EOF
    echo -e "${GREEN}✅ 已創建: docs/quickstart/README.md${NC}"
fi

# 更新 docs/features/jenkins-artifacts/README.md
mkdir -p docs/features/jenkins-artifacts
cat > docs/features/jenkins-artifacts/README.md << 'EOF'
# Jenkins Artifacts 功能文檔

本目錄包含 Jenkins Build Artifacts 自動存儲和處理相關的功能文檔。

## 📚 文檔列表

- [CELERY_ARTIFACTS_TASKS.md](CELERY_ARTIFACTS_TASKS.md) - Celery 自動化任務說明
- [ARTIFACTS_AUTO_EXTRACT.md](ARTIFACTS_AUTO_EXTRACT.md) - 自動解壓縮功能說明

## 🎯 功能概述

### Celery 自動化任務
- 自動掃描新的 Jenkins Builds
- 下載並存儲 Artifacts 到 NAS
- 支持定時任務和手動觸發

### 自動解壓縮
- 支持多種壓縮格式（7z, zip, tar.* 等）
- 解壓成功後自動刪除原始壓縮檔
- 保持目錄結構完整

## 🔗 相關文檔

- **快速啟動**：`docs/quickstart/QUICKSTART_JENKINS_AUTO_STORAGE.md`
- **實施報告**：`docs/features/jenkins-auto-storage/IMPLEMENTATION_REPORT.md`
EOF

echo -e "${GREEN}✅ 已創建: docs/features/jenkins-artifacts/README.md${NC}"

# 更新 docs/features/auto-sync/README.md
mkdir -p docs/features/auto-sync
cat > docs/features/auto-sync/README.md << 'EOF'
# DHCP 自動同步功能文檔

本目錄包含 DHCP Server 自動同步功能的相關文檔。

## 📚 文檔列表

- [CHANGELOG_AUTO_SYNC.md](CHANGELOG_AUTO_SYNC.md) - 自動同步功能變更日誌

## 🎯 功能概述

DHCP Server 創建後會自動執行以下同步操作：
- ✅ 自動同步 Scopes
- ✅ 自動同步 Leases
- ✅ 自動同步 Logs（最近 1000 條）
- ✅ 自動計算統計數據

## 🔗 相關文檔

- **快速啟動**：`docs/quickstart/QUICKSTART_AUTO_SYNC.md`
- **Leases 同步**：`docs/quickstart/QUICKSTART_AUTO_SYNC_LEASES.md`
EOF

echo -e "${GREEN}✅ 已創建: docs/features/auto-sync/README.md${NC}"

echo ""
echo -e "${GREEN}✨ 文檔整理完成！${NC}"
echo ""
echo "📂 整理結果："
echo "   - docs/quickstart/        : 4 個快速啟動指南"
echo "   - docs/features/          : 4 個功能文檔"
echo "   - docs/development/       : 3 個開發文檔（含報告）"
echo "   - docs/troubleshooting/   : 2 個故障排查文檔"
echo ""
echo "📋 詳細報告："
echo "   docs/development/DOCS_ORGANIZATION_REPORT.md"
echo ""
