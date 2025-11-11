# 測試腳本清理計劃

## 📋 評估日期：2025-11-10

## ✅ 保留的腳本

### 1. `verify_all.sh`
- **狀態**: 保留
- **用途**: 系統整體健康檢查
- **說明**: 用於快速診斷系統狀態，建議持續維護

---

## 🔄 需要遷移的腳本

以下腳本應該遷移到正式的 `tests/` 目錄結構中：

### 1. `test_auto_ipxe_sync.sh` → `tests/integration/ipxe/`
- **內容**: iPXE 日誌自動同步功能測試
- **遷移後名稱**: `test_auto_sync_integration.sh`
- **原因**: 這是整合測試，應該納入正式測試框架

### 2. `test_auto_switch_sync.sh` → `tests/integration/network/`
- **內容**: Switch 自動同步功能測試
- **遷移後名稱**: `test_switch_sync_integration.sh`
- **原因**: 網路設備整合測試

### 3. `test_ipxe_ssh_verification.sh` → `tests/integration/ipxe/`
- **內容**: iPXE SSH 連接驗證測試
- **遷移後名稱**: `test_ssh_verification.sh`
- **原因**: SSH 連接整合測試

---

## ❌ 可以刪除的腳本

以下是**臨時性開發測試腳本**，功能已實現並驗證完畢，可以安全刪除：

### 1. `test_dhcp_raw_log.sh` (3.1K)
- **狀態**: ✅ 可刪除
- **原因**: DHCP Raw Log 顯示功能已實現，時區問題已修復
- **相關文檔**: `DHCP_RAW_LOG_CHANGES.md`, `DHCP_TIMEZONE_FIX.md`
- **驗證**: 功能正常運作中

### 2. `test_stage2_quick.sh` (4.5K)
- **狀態**: ✅ 可刪除
- **原因**: 階段二可行性測試，開發階段已完成
- **功能**: DHCP Options 檢查
- **驗證**: 功能已實現並穩定

### 3. `test_stage2_feasibility.sh` (8.8K)
- **狀態**: ✅ 可刪除
- **原因**: DHCP Options 可行性測試，功能已驗證
- **功能**: PXE Options 檢查
- **驗證**: 功能已整合到主系統

### 4. `test_server_dropdown_sorting.sh` (2.7K)
- **狀態**: ✅ 可刪除
- **原因**: Server 下拉選單排序功能已實現
- **功能**: 前端 UI 排序測試
- **驗證**: 功能正常運作

### 5. `test_ipxe_improvements.sh` (9.4K)
- **狀態**: ✅ 可刪除
- **原因**: iPXE Server 改進功能測試，開發完成
- **功能**: SSH 驗證、錯誤處理、健康檢查
- **驗證**: 所有改進已整合並穩定

### 6. `test_ipxe_auto_sync.sh` (9.3K)
- **狀態**: ✅ 可刪除
- **原因**: 與 `test_auto_ipxe_sync.sh` 重複
- **功能**: iPXE 自動同步驗證
- **驗證**: 功能已整合到新版測試腳本

### 7. `test_auto_sync.sh` (4.4K)
- **狀態**: ✅ 可刪除
- **原因**: DHCP Server 自動同步功能已穩定
- **功能**: DHCP 自動同步測試
- **驗證**: 功能正常運作，定期任務已配置

---

## 🚀 執行計劃

### 階段一：備份（可選）
```bash
# 創建備份目錄
mkdir -p archive/old_test_scripts/

# 備份所有待刪除的腳本
mv test_dhcp_raw_log.sh archive/old_test_scripts/
mv test_stage2_quick.sh archive/old_test_scripts/
mv test_stage2_feasibility.sh archive/old_test_scripts/
mv test_server_dropdown_sorting.sh archive/old_test_scripts/
mv test_ipxe_improvements.sh archive/old_test_scripts/
mv test_ipxe_auto_sync.sh archive/old_test_scripts/
mv test_auto_sync.sh archive/old_test_scripts/
```

### 階段二：遷移需要保留的測試
```bash
# 創建目標目錄
mkdir -p tests/integration/ipxe/
mkdir -p tests/integration/network/

# 遷移 iPXE 相關測試
mv test_auto_ipxe_sync.sh tests/integration/ipxe/test_auto_sync_integration.sh
mv test_ipxe_ssh_verification.sh tests/integration/ipxe/test_ssh_verification.sh

# 遷移 Switch 相關測試
mv test_auto_switch_sync.sh tests/integration/network/test_switch_sync_integration.sh
```

### 階段三：直接刪除（推薦）
```bash
# 直接刪除臨時測試腳本
rm -f test_dhcp_raw_log.sh
rm -f test_stage2_quick.sh
rm -f test_stage2_feasibility.sh
rm -f test_server_dropdown_sorting.sh
rm -f test_ipxe_improvements.sh
rm -f test_ipxe_auto_sync.sh
rm -f test_auto_sync.sh

echo "✅ 臨時測試腳本已清理完成"
```

---

## 📊 清理統計

### 刪除前
- 測試腳本總數：10 個
- 總大小：~62.2 KB

### 刪除後
- 保留腳本：1 個 (`verify_all.sh`)
- 遷移腳本：3 個
- 刪除腳本：7 個
- 節省空間：~41.3 KB

---

## ✅ 驗證步驟

清理完成後，請執行以下驗證：

1. **檢查系統功能**：
   ```bash
   ./verify_all.sh
   ```

2. **檢查 Docker 服務**：
   ```bash
   docker compose ps
   ```

3. **檢查定期任務**：
   ```bash
   docker exec nt-django python manage.py shell -c "
   from django_celery_beat.models import PeriodicTask
   for task in PeriodicTask.objects.filter(enabled=True):
       print(f'{task.name}: {task.task}')
   "
   ```

4. **測試自動同步**：
   - DHCP 日誌同步正常運作
   - iPXE 日誌自動同步正常
   - Switch 設備自動發現正常

---

## 📝 相關文檔

清理完成後，請更新以下文檔：
- ✅ `README.md` - 移除已刪除腳本的引用
- ✅ `QUICKSTART_AUTO_SYNC.md` - 更新測試說明
- ✅ `tests/README.md` - 添加新遷移的測試腳本說明

---

## 🔍 回滾計劃

如果發現需要恢復某個腳本：

```bash
# 從 Git 歷史恢復
git checkout HEAD~1 -- test_<腳本名稱>.sh

# 或從備份恢復（如果執行了階段一）
cp archive/old_test_scripts/test_<腳本名稱>.sh .
```

---

**建立日期**: 2025-11-10  
**評估者**: GitHub Copilot  
**狀態**: 待執行
