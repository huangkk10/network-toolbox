# 🚀 DHCP 日誌功能快速啟動指南

## ✅ 功能已完成

LogsTab 已經從假的 mockLogs 轉換為使用真實 API！

## 📺 如何查看

### 1. 確保服務運行

```bash
# 檢查所有容器狀態
docker compose ps

# 應該看到以下服務都在運行：
# ✅ nt-nginx      (Port 80)
# ✅ nt-django     (Port 8000)
# ✅ nt-react      (Port 3000)
# ✅ nt-postgres   (Port 5432)
# ✅ nt-adminer    (Port 9090)
```

### 2. 訪問前端

打開瀏覽器訪問：**http://localhost**

### 3. 導航到日誌頁面

```
首頁 → 側邊欄「DHCP 分析」→ 選擇「日誌」標籤
```

## 🎮 功能操作

### 日誌來源選擇

- **本地日誌**: 讀取主機的 `logs/dhcp_operations.log`
- **遠端 SSH**: 透過 SSH 讀取 DHCP 伺服器的日誌（需要先配置伺服器）

### 過濾功能

1. **級別過濾**
   - 點擊下拉選單選擇：ALL / INFO / WARN / ERROR / DEBUG
   - 只顯示符合級別的日誌

2. **關鍵字搜尋**
   - 在搜尋框輸入關鍵字（例如：pool, DHCP, failed）
   - 按 Enter 或點擊搜尋圖標
   - 只顯示包含該關鍵字的日誌

### 自動更新

- 打開「自動更新」開關
- 每 3 秒自動刷新日誌
- 適合監控即時日誌

### 操作按鈕

- **🔄 重新載入**: 手動刷新日誌
- **🧹 清除螢幕**: 清空當前顯示
- **💾 下載日誌**: 下載為 txt 檔案

## 🧪 測試 API

### 使用 cURL 測試

```bash
# 1. 獲取所有日誌
curl "http://localhost/api/dhcp-analytics/logs/?source=local&server=all"

# 2. 只看 ERROR 日誌
curl "http://localhost/api/dhcp-analytics/logs/?source=local&server=all&level=ERROR"

# 3. 搜尋關鍵字 "pool"
curl "http://localhost/api/dhcp-analytics/logs/?source=local&server=all&keyword=pool"

# 4. 組合過濾: WARN + pool
curl "http://localhost/api/dhcp-analytics/logs/?source=local&server=all&level=WARN&keyword=pool"
```

### 使用測試腳本

```bash
cd /home/owner/Codes/network-toolbox/backend
python3 test_logs_api.py
```

## 📊 當前測試數據

測試日誌檔案位於：`logs/dhcp_operations.log`

**統計**:
- 總計：20 條日誌
- INFO：13 條
- WARN：3 條
- ERROR：3 條
- DEBUG：1 條

**內容範例**:
```
[INFO] 2025-01-26 10:15:23 | DHCP server started successfully
[WARN] 2025-01-26 10:25:30 | Address pool is 80% full
[ERROR] 2025-01-26 10:35:22 | Failed to assign address: pool exhausted
```

## 🔧 常見問題

### Q1: 看不到日誌？

**檢查步驟**:
```bash
# 1. 確認日誌檔案存在
ls -la logs/dhcp_operations.log

# 2. 查看日誌內容
cat logs/dhcp_operations.log

# 3. 測試 API
curl "http://localhost/api/dhcp-analytics/logs/?source=local&server=all"

# 4. 查看 Django 日誌
docker compose logs django --tail 50
```

### Q2: API 返回錯誤？

**檢查 Django 容器**:
```bash
# 查看錯誤日誌
docker compose logs django | grep ERROR

# 查看檔案
tail -f logs/django_error.log
```

### Q3: 前端無法載入？

**檢查瀏覽器控制台**:
1. 按 F12 打開開發者工具
2. 切換到 Console 標籤
3. 查看是否有錯誤訊息
4. 切換到 Network 標籤
5. 查看 `/api/dhcp-analytics/logs/` 請求狀態

## 📚 完整文檔

詳細的實作說明請參考：
- **實作報告**: `LOGS_API_IMPLEMENTATION.md`
- **API 測試**: `backend/test_logs_api.py`
- **開發文檔**: `DEVELOPMENT.md`

## 🎯 下一步

日誌功能已完成！現在可以：

1. ✅ **查看真實日誌**: 在前端 LogsTab 查看本地日誌
2. ✅ **過濾和搜尋**: 使用級別和關鍵字過濾
3. ✅ **自動更新**: 啟用即時監控
4. ✅ **匯出日誌**: 下載為文字檔案

---

**完成時間**: 2025-01-27  
**狀態**: ✅ 生產就緒
