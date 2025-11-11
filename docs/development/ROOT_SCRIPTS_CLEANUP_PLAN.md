# 根目錄 Python 腳本清理計劃

## 📅 評估日期
**2025-11-11**

---

## 📋 待清理的腳本

### 1. `create_db.py` ✅ **可以刪除**

**文件位置**：
- 根目錄：`/home/owner/Codes/network-toolbox/create_db.py`

**用途**：
- 創建 PostgreSQL 資料庫 `network_toolbox`
- 一次性初始化腳本

**刪除理由**：
- ✅ 資料庫已創建完成
- ✅ 後續使用 Docker 和 Django migrations 管理資料庫
- ✅ 不需要重複執行
- ✅ 功能已完成，無後續使用需求

**替代方案**：
- 如需重建資料庫，使用 Docker Compose：
  ```bash
  docker compose down -v  # 刪除資料庫
  docker compose up -d    # 重新創建
  docker exec nt-django python manage.py migrate
  ```

---

### 2. `clean_old_dhcp_logs.py` ⚠️ **移動到 backend/ 即可**

**文件位置**：
- 根目錄：`/home/owner/Codes/network-toolbox/clean_old_dhcp_logs.py`
- backend：`/home/owner/Codes/network-toolbox/backend/clean_old_dhcp_logs.py`
- **狀態**：兩個文件完全相同

**用途**：
- 清理所有 DHCP 日誌
- 觸發重新同步

**建議**：
- ✅ **刪除根目錄版本**
- ✅ **保留 backend/ 版本**
- 根目錄的版本是重複的，backend/ 中的版本更合適

**執行方式**（使用 backend/ 版本）：
```bash
docker exec nt-django python /app/clean_old_dhcp_logs.py
```

---

### 3. `clean_dhcp_logs_by_server.py` ⚠️ **移動到 backend/ 即可**

**文件位置**：
- 根目錄：`/home/owner/Codes/network-toolbox/clean_dhcp_logs_by_server.py`
- backend：`/home/owner/Codes/network-toolbox/backend/clean_dhcp_logs_by_server.py`
- **狀態**：兩個文件完全相同

**用途**：
- 清理特定 DHCP Server 的日誌
- 互動式選擇 Server

**建議**：
- ✅ **刪除根目錄版本**
- ✅ **保留 backend/ 版本**
- 功能性腳本應該放在 backend/ 目錄

**執行方式**（使用 backend/ 版本）：
```bash
docker exec -it nt-django python /app/clean_dhcp_logs_by_server.py
```

---

### 4. `check_nas_logs.py` ⚠️ **移動到 backend/ 即可**

**文件位置**：
- 根目錄：`/home/owner/Codes/network-toolbox/check_nas_logs.py`
- backend：`/home/owner/Codes/network-toolbox/backend/check_nas_logs.py`
- **狀態**：兩個文件完全相同

**用途**：
- 檢查 NAS 連線記錄
- 顯示最近的連線狀態

**建議**：
- ✅ **刪除根目錄版本**
- ✅ **保留 backend/ 版本**
- 診斷性腳本應該放在 backend/ 目錄

**執行方式**（使用 backend/ 版本）：
```bash
docker exec nt-django python /app/check_nas_logs.py
```

---

## 🎯 清理建議總結

| 文件 | 根目錄 | backend/ | 建議 |
|------|--------|----------|------|
| `create_db.py` | ✅ 存在 | ❌ 不存在 | 🗑️ **直接刪除**（功能已完成） |
| `clean_old_dhcp_logs.py` | ✅ 存在 | ✅ 存在（相同）| 🗑️ **刪除根目錄版本** |
| `clean_dhcp_logs_by_server.py` | ✅ 存在 | ✅ 存在（相同）| 🗑️ **刪除根目錄版本** |
| `check_nas_logs.py` | ✅ 存在 | ✅ 存在（相同）| 🗑️ **刪除根目錄版本** |

---

## 🚀 執行清理

### 一鍵清理腳本

```bash
#!/bin/bash
# 清理根目錄的重複和過時腳本

cd /home/owner/Codes/network-toolbox

echo "🗑️  清理根目錄 Python 腳本..."
echo ""

# 1. 刪除一次性初始化腳本
if [ -f "create_db.py" ]; then
    rm create_db.py
    echo "✅ 已刪除: create_db.py (資料庫初始化已完成)"
fi

# 2. 刪除重複的 DHCP 日誌清理腳本
if [ -f "clean_old_dhcp_logs.py" ]; then
    rm clean_old_dhcp_logs.py
    echo "✅ 已刪除: clean_old_dhcp_logs.py (保留 backend/ 版本)"
fi

if [ -f "clean_dhcp_logs_by_server.py" ]; then
    rm clean_dhcp_logs_by_server.py
    echo "✅ 已刪除: clean_dhcp_logs_by_server.py (保留 backend/ 版本)"
fi

# 3. 刪除重複的 NAS 檢查腳本
if [ -f "check_nas_logs.py" ]; then
    rm check_nas_logs.py
    echo "✅ 已刪除: check_nas_logs.py (保留 backend/ 版本)"
fi

echo ""
echo "✨ 清理完成！"
echo ""
echo "📋 保留的腳本（在 backend/ 目錄）："
echo "   - backend/clean_old_dhcp_logs.py"
echo "   - backend/clean_dhcp_logs_by_server.py"
echo "   - backend/check_nas_logs.py"
echo ""
echo "📝 使用方式："
echo "   docker exec nt-django python /app/clean_old_dhcp_logs.py"
echo "   docker exec -it nt-django python /app/clean_dhcp_logs_by_server.py"
echo "   docker exec nt-django python /app/check_nas_logs.py"
echo ""
```

### 手動執行

```bash
cd /home/owner/Codes/network-toolbox

# 刪除根目錄的腳本
rm -f create_db.py
rm -f clean_old_dhcp_logs.py
rm -f clean_dhcp_logs_by_server.py
rm -f check_nas_logs.py

echo "✅ 清理完成"
```

---

## ✅ 驗證

清理後，根目錄應該只包含：

### 保留的腳本（根目錄）
- ✅ `start.sh` - 啟動服務
- ✅ `stop.sh` - 停止服務
- ✅ `verify_all.sh` - 系統驗證
- ✅ `organize_root_docs.sh` - 文檔整理
- ✅ 其他功能性 shell 腳本

### 移除的腳本（根目錄）
- ❌ `create_db.py` - 已刪除
- ❌ `clean_old_dhcp_logs.py` - 已刪除（保留 backend/ 版本）
- ❌ `clean_dhcp_logs_by_server.py` - 已刪除（保留 backend/ 版本）
- ❌ `check_nas_logs.py` - 已刪除（保留 backend/ 版本）

### backend/ 目錄保留的腳本
- ✅ `backend/clean_old_dhcp_logs.py`
- ✅ `backend/clean_dhcp_logs_by_server.py`
- ✅ `backend/check_nas_logs.py`
- ✅ 其他功能性 Python 腳本

---

## 📚 相關文檔

- **測試腳本清理**：`docs/development/CLEANUP_TEST_SCRIPTS.md`
- **文檔整理報告**：`docs/development/FINAL_DOCS_CLEANUP_REPORT.md`

---

## 🔍 為什麼要清理？

### 1. **避免混淆**
- 根目錄和 backend/ 有相同的腳本，不知道該執行哪個

### 2. **保持根目錄整潔**
- 根目錄應該只放啟動腳本和配置文件
- Python 功能腳本應該放在 backend/ 目錄

### 3. **符合專案結構規範**
- Django 相關的腳本屬於 backend/
- 根目錄只保留 Docker 和系統級別的腳本

### 4. **減少維護成本**
- 只需要維護一個版本
- 避免兩邊修改不同步的問題

---

## 📝 清理後的使用方式

### DHCP 日誌清理
```bash
# 清理所有日誌並重新同步
docker exec nt-django python /app/clean_old_dhcp_logs.py

# 清理特定 Server 的日誌
docker exec -it nt-django python /app/clean_dhcp_logs_by_server.py
```

### NAS 連線檢查
```bash
# 檢查 NAS 連線記錄
docker exec nt-django python /app/check_nas_logs.py
```

### 資料庫重建（如需要）
```bash
# 完全重建資料庫
docker compose down -v
docker compose up -d
docker exec nt-django python manage.py migrate
docker exec nt-django python manage.py createsuperuser
```

---

**評估日期**：2025-11-11  
**評估者**：GitHub Copilot  
**狀態**：建議執行清理
