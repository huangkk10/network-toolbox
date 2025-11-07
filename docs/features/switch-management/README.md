# Switch 管理功能文檔

網路交換器（Switch）管理功能的完整文檔。

## 📚 文檔列表

### 主要功能

1. **[Switch 自動識別機制](./AUTO_SWITCH_IDENTIFICATION.md)** ⭐ 推薦閱讀
   - Switch 識別原理（Option 82 / 廠商識別）
   - 新增 DHCP Server 後的自動化流程
   - 定時任務和信號處理器配置
   - 故障排查和最佳實踐

### 快速連結

- **自動識別**：[AUTO_SWITCH_IDENTIFICATION.md](./AUTO_SWITCH_IDENTIFICATION.md)
- **手動管理**：前端頁面 → DHCP Server 分析 → Switch 管理

## 🎯 快速開始

### 新增 DHCP Server 後查看 Switch

1. **自動方式**（推薦）
   ```
   新增 Server → 等待 1-2 分鐘 → 自動顯示 Switch
   ```

2. **手動方式**
   ```
   Switch 管理頁面 → 點擊「立即同步」按鈕
   ```

### 啟用完整功能（推薦）

1. **啟用 DHCP Option 82**
   - Windows DHCP Server：記錄 Relay Agent 資訊
   - Switch 配置：啟用 DHCP Snooping 和 Option 82

2. **確認 Celery 運行**
   ```bash
   docker compose ps | grep celery
   ```

## 📊 功能特性

| 功能 | 支援方式 | 說明 |
|------|---------|------|
| **Switch 識別** | Option 82 / 廠商識別 | 自動識別網路交換器 |
| **端口管理** | Option 82 | 追蹤設備連接端口 |
| **統計資訊** | 自動更新 | 連接設備數、活動端口數 |
| **網路拓撲** | API | 視覺化網路結構 |
| **定時同步** | Celery | 每小時自動更新 |
| **即時更新** | Signal | 租約變化時自動更新 |

## 🔧 技術架構

```
前端 (React + Ant Design)
    ↓
API (Django REST Framework)
    ↓
後端服務
    ├── Models: NetworkSwitch, SwitchPort
    ├── Tasks: auto_identify_switches_task
    ├── Signals: 自動觸發機制
    └── Celery Beat: 定時任務
```

## 📝 相關文檔

- [DHCP Server 管理](../../dhcp-server/README.md)
- [定時任務配置](../../deployment/CELERY_SETUP.md)
- [API 文檔](../../api/SWITCHES_API.md)

---

**最後更新**：2025-11-07
