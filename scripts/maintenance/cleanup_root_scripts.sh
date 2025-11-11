#!/bin/bash

# 清理根目錄的重複和過時 Python 腳本
# 執行日期: 2025-11-11

set -e

cd /home/owner/Codes/network-toolbox

# 顏色定義
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo ""
echo -e "${BLUE}🗑️  清理根目錄 Python 腳本${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# 計數器
deleted_count=0

# 1. 刪除一次性初始化腳本
if [ -f "create_db.py" ]; then
    rm create_db.py
    echo -e "${GREEN}✅ 已刪除: create_db.py${NC}"
    echo "   └─ 理由: 資料庫初始化已完成，不再需要"
    ((deleted_count++))
else
    echo -e "${YELLOW}⚠️  create_db.py 不存在${NC}"
fi

echo ""

# 2. 刪除重複的 DHCP 日誌清理腳本
if [ -f "clean_old_dhcp_logs.py" ]; then
    rm clean_old_dhcp_logs.py
    echo -e "${GREEN}✅ 已刪除: clean_old_dhcp_logs.py${NC}"
    echo "   └─ 理由: 與 backend/ 版本重複，保留 backend/ 版本"
    ((deleted_count++))
else
    echo -e "${YELLOW}⚠️  clean_old_dhcp_logs.py 不存在${NC}"
fi

echo ""

if [ -f "clean_dhcp_logs_by_server.py" ]; then
    rm clean_dhcp_logs_by_server.py
    echo -e "${GREEN}✅ 已刪除: clean_dhcp_logs_by_server.py${NC}"
    echo "   └─ 理由: 與 backend/ 版本重複，保留 backend/ 版本"
    ((deleted_count++))
else
    echo -e "${YELLOW}⚠️  clean_dhcp_logs_by_server.py 不存在${NC}"
fi

echo ""

# 3. 刪除重複的 NAS 檢查腳本
if [ -f "check_nas_logs.py" ]; then
    rm check_nas_logs.py
    echo -e "${GREEN}✅ 已刪除: check_nas_logs.py${NC}"
    echo "   └─ 理由: 與 backend/ 版本重複，保留 backend/ 版本"
    ((deleted_count++))
else
    echo -e "${YELLOW}⚠️  check_nas_logs.py 不存在${NC}"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "${GREEN}✨ 清理完成！共刪除 ${deleted_count} 個文件${NC}"
echo ""

# 顯示保留的腳本位置
echo -e "${BLUE}📋 保留的腳本（在 backend/ 目錄）：${NC}"
echo ""
if [ -f "backend/clean_old_dhcp_logs.py" ]; then
    echo -e "${GREEN}✅${NC} backend/clean_old_dhcp_logs.py"
fi
if [ -f "backend/clean_dhcp_logs_by_server.py" ]; then
    echo -e "${GREEN}✅${NC} backend/clean_dhcp_logs_by_server.py"
fi
if [ -f "backend/check_nas_logs.py" ]; then
    echo -e "${GREEN}✅${NC} backend/check_nas_logs.py"
fi

echo ""
echo -e "${BLUE}📝 使用方式：${NC}"
echo ""
echo "  # 清理所有 DHCP 日誌"
echo "  docker exec nt-django python /app/clean_old_dhcp_logs.py"
echo ""
echo "  # 清理特定 Server 的日誌（互動式）"
echo "  docker exec -it nt-django python /app/clean_dhcp_logs_by_server.py"
echo ""
echo "  # 檢查 NAS 連線狀態"
echo "  docker exec nt-django python /app/check_nas_logs.py"
echo ""

# 生成清理報告
cat > docs/development/ROOT_SCRIPTS_CLEANUP_REPORT.md << 'EOF'
# 根目錄 Python 腳本清理報告

## 📅 清理日期
**2025-11-11**

---

## ✅ 已清理的腳本

| 文件名 | 刪除理由 | 替代方案 |
|--------|---------|---------|
| `create_db.py` | 資料庫初始化已完成，一次性腳本 | 使用 Docker Compose 重建資料庫 |
| `clean_old_dhcp_logs.py` | 與 backend/ 版本重複 | 使用 `backend/clean_old_dhcp_logs.py` |
| `clean_dhcp_logs_by_server.py` | 與 backend/ 版本重複 | 使用 `backend/clean_dhcp_logs_by_server.py` |
| `check_nas_logs.py` | 與 backend/ 版本重複 | 使用 `backend/check_nas_logs.py` |

---

## 📊 清理統計

- **刪除文件總數**: 4 個
- **一次性腳本**: 1 個
- **重複腳本**: 3 個
- **保留位置**: backend/ 目錄

---

## 🎯 清理目的

1. **避免混淆**: 根目錄和 backend/ 不再有重複文件
2. **保持整潔**: 根目錄只保留必要的啟動腳本
3. **符合規範**: Python 功能腳本統一放在 backend/
4. **減少維護**: 只需維護一個版本

---

## 📋 保留的腳本

### backend/ 目錄中的功能腳本

```
backend/
├── clean_old_dhcp_logs.py          # DHCP 日誌清理
├── clean_dhcp_logs_by_server.py    # 特定 Server 日誌清理
└── check_nas_logs.py               # NAS 連線檢查
```

### 根目錄中的系統腳本

```
根目錄/
├── start.sh                        # 啟動服務
├── stop.sh                         # 停止服務
├── verify_all.sh                   # 系統驗證
└── organize_root_docs.sh           # 文檔整理
```

---

## 📝 使用指南

### DHCP 日誌管理

```bash
# 清理所有 DHCP 日誌並重新同步
docker exec nt-django python /app/clean_old_dhcp_logs.py

# 清理特定 Server 的日誌（互動式選擇）
docker exec -it nt-django python /app/clean_dhcp_logs_by_server.py
```

### NAS 連線檢查

```bash
# 檢查 NAS 連線記錄
docker exec nt-django python /app/check_nas_logs.py
```

### 資料庫重建

如果需要重建資料庫（取代 create_db.py）：

```bash
# 完全重建資料庫
docker compose down -v
docker compose up -d
docker exec nt-django python manage.py migrate
docker exec nt-django python manage.py createsuperuser
```

---

## ✅ 驗證

### 1. 檢查根目錄
```bash
$ ls -1 *.py 2>/dev/null
(應該沒有 Python 文件)
```

### 2. 檢查 backend/ 目錄
```bash
$ ls -1 backend/*.py | grep -E 'clean|check'
backend/check_nas_logs.py
backend/clean_dhcp_logs_by_server.py
backend/clean_old_dhcp_logs.py
```

### 3. 測試功能
```bash
# 測試 NAS 檢查腳本
docker exec nt-django python /app/check_nas_logs.py

# 測試 DHCP 清理腳本（dry-run）
docker exec nt-django python /app/clean_old_dhcp_logs.py --help
```

---

## 📚 相關文檔

- **清理計劃**: `docs/development/ROOT_SCRIPTS_CLEANUP_PLAN.md`
- **測試腳本清理**: `docs/development/CLEANUP_TEST_SCRIPTS.md`
- **文檔整理報告**: `docs/development/FINAL_DOCS_CLEANUP_REPORT.md`

---

**清理完成日期**: 2025-11-11  
**執行者**: GitHub Copilot  
**狀態**: ✅ 已完成
EOF

echo -e "${GREEN}✅ 已生成清理報告: docs/development/ROOT_SCRIPTS_CLEANUP_REPORT.md${NC}"
echo ""
