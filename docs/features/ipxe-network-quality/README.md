# IPXE 網路品質監控

## 📖 功能簡介

IPXE 網路品質監控功能提供對 IPXE 伺服器的全方位網路性能監控，包括：

- **🌐 Ping 測試**：網路延遲和丟包率
- **🔌 HTTP 測試**：Web 服務可用性和響應時間
- **🔐 SSH 測試**：SSH 服務連接性和響應時間
- **📥 下載速度**：實際檔案傳輸速度

## 🚀 快速開始

### 1. 訪問監控頁面

在側邊欄點擊「**IPXE 網路品質**」或直接訪問：
```
http://localhost/ipxe-network-quality
```

### 2. 查看監控數據

頁面自動顯示：
- **統計卡片**：成功率、平均延遲、丟包率等關鍵指標
- **趨勢圖表**：Ping 延遲、響應時間、丟包率、下載速度
- **詳細記錄**：每次檢測的完整數據

### 3. 調整時間範圍

頁面右上角可選擇：
- 最近 1 天
- 最近 3 天
- 最近 7 天（預設）
- 最近 14 天

## 📊 監控指標說明

### Ping 測試
- **延遲 (Latency)**：網路往返時間，越低越好（正常 < 50ms）
- **丟包率 (Packet Loss)**：封包遺失百分比，應為 0%

### HTTP 測試
- **響應時間**：Web 服務響應速度（正常 < 100ms）
- **HTTP 狀態碼**：200 表示正常，其他值表示異常

### SSH 測試
- **響應時間**：SSH 連接建立時間（正常 < 200ms）
- **連接狀態**：顯示是否成功連接

### 下載速度
- **速度值**：實際檔案下載速度（MB/s）
- 受網路頻寬和檔案大小影響

## 🎨 狀態標籤

- 🟢 **正常 (success)**：所有測試通過
- 🟡 **部分失敗 (partial)**：部分測試失敗（如 Ping 失敗但 HTTP 正常）
- 🔴 **失敗 (failed)**：所有測試失敗或重要測試失敗

## 🔄 自動監控

系統每 **5 分鐘** 自動執行一次網路品質檢測：

```bash
# Cron 任務
*/5 * * * * /home/owner/Codes/network-toolbox/scripts/check_ipxe_network.sh
```

檢測結果自動保存到資料庫，頁面每 **30 秒** 自動刷新數據。

## 🛠️ 進階操作

### 手動觸發檢測

如需立即執行一次檢測：

```bash
docker exec nt-django python manage.py shell -c "
from api.ipxe_network_service import record_ipxe_network_quality
record_ipxe_network_quality()
"
```

### 查看檢測日誌

```bash
tail -f logs/ipxe_network_cron.log
```

### API 訪問

**獲取統計資料**：
```bash
curl http://localhost/api/ipxe-network-quality/statistics/?days=7
```

**獲取原始記錄**：
```bash
curl http://localhost/api/ipxe-network-quality/?days=7&server_id=1
```

## 📈 圖表說明

### 1. Ping 延遲趨勢
- 顯示隨時間變化的網路延遲
- 用於識別網路抖動或高延遲時段

### 2. 響應時間對比
- 同時顯示 HTTP 和 SSH 響應時間
- 可對比不同服務的性能差異

### 3. 丟包率趨勢
- 顯示網路封包遺失情況
- 面積圖清楚展示丟包嚴重程度

### 4. 下載速度趨勢
- 顯示實際檔案傳輸速度變化
- 用於監控頻寬使用狀況

## ⚠️ 常見問題

### Q1: 為什麼 Ping 測試一直失敗？

**原因**：Docker 容器中未安裝 `ping` 工具。

**解決方案**：
```bash
# 方案 1：在容器中安裝
docker exec -u root nt-django apt-get update
docker exec -u root nt-django apt-get install -y iputils-ping

# 方案 2：重建容器（在 Dockerfile 中添加）
# 編輯 backend/Dockerfile，添加：
# RUN apt-get update && apt-get install -y iputils-ping && rm -rf /var/lib/apt/lists/*
docker compose up -d --build django
```

**影響**：即使 Ping 失敗，HTTP/SSH/下載測試仍正常工作。

### Q2: 為什麼下載速度顯示很慢？

**可能原因**：
- 測試檔案較小，受協議開銷影響
- 網路環境限制
- SSH/SFTP 協議本身的效能特性

**正常範圍**：
- 內網環境：通常 0.1 - 10 MB/s
- 跨網環境：視實際頻寬而定

### Q3: 如何設定告警？

目前版本尚未實現自動告警功能。

**建議**：
- 定期查看監控頁面
- 關注成功率和丟包率指標
- 查看錯誤訊息欄位了解失敗原因

## 📚 相關文檔

- [完整實施報告](./IMPLEMENTATION_REPORT.md)
- [IPXE 分析與實現](../IPXE_ANALYSIS_AND_IMPLEMENTATION.md)
- [系統部署文檔](../../deployment/DEPLOYMENT.md)

---

**版本**：1.0.0  
**更新日期**：2025-10-29
