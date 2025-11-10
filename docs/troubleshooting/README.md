# 故障排查文檔

本目錄包含 Network Toolbox 專案的常見問題和解決方案。

---

## 📚 文檔列表

### 已解決的問題

1. **[DHCP 日誌時區修復](./DHCP_TIMEZONE_FIX.md)** ✅
   - **問題**：Web 顯示的 DHCP 日誌時間與 Raw Log 相差 8 小時
   - **狀態**：已修復（2025-11-10）
   - **影響**：DHCP Server 分析 → 日誌查看
   - **根本原因**：Windows DHCP 日誌時間未正確處理時區
   - **解決方案**：使用 pytz 正確處理時區轉換

---

## 🔍 問題分類

### 時區相關
- [DHCP 日誌時區修復](./DHCP_TIMEZONE_FIX.md)

### 資料庫相關
- （待補充）

### Docker 相關
- （待補充）

### 前端相關
- （待補充）

---

## 📝 報告新問題

如果您遇到新的問題，請按照以下格式記錄：

### 問題描述模板

```markdown
# [問題標題]

**發現日期**：YYYY-MM-DD  
**狀態**：🔴 未解決 / 🟡 調查中 / 🟢 已解決  
**優先級**：高 / 中 / 低  
**影響範圍**：[說明影響的功能]

## 症狀

[詳細描述問題的表現]

## 重現步驟

1. 步驟 1
2. 步驟 2
3. 步驟 3

## 預期行為

[描述預期的正確行為]

## 實際行為

[描述實際發生的錯誤行為]

## 環境資訊

- OS: [例如 Ubuntu 22.04]
- Docker 版本: [例如 24.0.5]
- Python 版本: [例如 3.11]
- Django 版本: [例如 4.2.25]

## 錯誤日誌

```
[貼上相關的錯誤日誌]
```

## 臨時解決方案

[如果有臨時的 workaround，在此說明]

## 相關資源

- 相關 Issue: #XXX
- 相關 PR: #XXX
- 相關文檔: [連結]
```

---

## 🛠️ 常用除錯工具

### 1. 檢查 Docker 容器狀態
```bash
docker compose ps
docker compose logs django --tail 50
docker compose logs -f
```

### 2. 進入 Django Shell
```bash
docker exec -it nt-django python manage.py shell
```

### 3. 檢查資料庫
```bash
docker exec -it nt-django python manage.py dbshell
```

### 4. 查看日誌
```bash
tail -f logs/django.log
tail -f logs/django_error.log
```

### 5. 測試 API
```bash
curl -s "http://localhost/api/endpoint/" | python3 -m json.tool
```

---

## 📖 相關文檔

- [開發指南](../development/DEVELOPMENT.md)
- [時區處理最佳實踐](../development/TIMEZONE_BEST_PRACTICES.md)
- [部署文檔](../deployment/DEPLOYMENT.md)

---

**最後更新**：2025-11-10  
**維護者**：Network Toolbox Team
