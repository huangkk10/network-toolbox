# Network Toolbox 文檔目│   ├── auto-switch-sync/               # 自動 Switch 同步功能
│   │   ├── README.md                   # 完整技術說明
│   │   ├── QUICKSTART.md               # 快速開始指南
│   │   ├── TESTING_GUIDE.md            # 測試指南
│   │   └── SOLUTION_SUMMARY.md         # 問題解決總結
│   └── server-dropdown-sorting/        # Server 下拉選單排序
│       └── README.md                   # 功能說明
└── api/                                # API 文檔
    └── API_TEST_REPORT.md              # API 測試報告 文檔結構

```
docs/
├── README.md                           # 本文件 - 文檔導覽
├── quickstart/                         # 快速開始指南
│   ├── QUICKSTART.md                   # 總體快速開始
│   └── LOGS_QUICKSTART.md              # 日誌功能快速開始
├── development/                        # 開發相關文檔
│   ├── DEVELOPMENT.md                  # 開發指南
│   └── REAL_DATA_CONVERSION_REPORT.md  # 真實數據轉換報告
├── deployment/                         # 部署相關文檔
│   └── DEPLOYMENT.md                   # 部署指南
├── features/                           # 功能實作文檔
│   ├── LOGS_API_IMPLEMENTATION.md      # 日誌 API 實作報告
│   ├── LOGS_IMPLEMENTATION_COMPLETE.md # 日誌功能完成報告
│   ├── DHCP_SSH_INTEGRATION.md         # DHCP SSH 集成文檔
│   ├── LOGS_TAB_USAGE.md               # LogsTab 使用指南
│   ├── LOG_FILES_EXPLAINED.md          # 日誌文件說明
│   └── auto-switch-sync/               # 自動 Switch 同步功能
│       ├── README.md                   # 完整技術說明
│       ├── QUICKSTART.md               # 快速開始指南
│       ├── TESTING_GUIDE.md            # 測試指南
│       └── SOLUTION_SUMMARY.md         # 問題解決總結
└── api/                                # API 文檔
    └── API_TEST_REPORT.md              # API 測試報告
```

## 🚀 快速導覽

### 新手入門
1. **[快速開始](quickstart/QUICKSTART.md)** - 5 分鐘快速部署和使用
2. **[日誌功能快速開始](quickstart/LOGS_QUICKSTART.md)** - 日誌查看功能快速上手

### 開發人員
1. **[開發指南](development/DEVELOPMENT.md)** - 完整的開發環境設置和規範
2. **[真實數據轉換報告](development/REAL_DATA_CONVERSION_REPORT.md)** - 從假數據到真實 API 的轉換過程

### 運維人員
1. **[部署指南](deployment/DEPLOYMENT.md)** - 生產環境部署步驟

### 功能文檔
1. **[日誌 API 實作](features/LOGS_API_IMPLEMENTATION.md)** - 日誌 API 技術細節
2. **[日誌功能完成報告](features/LOGS_IMPLEMENTATION_COMPLETE.md)** - 日誌功能完整實作總結
3. **[LogsTab 使用指南](features/LOGS_TAB_USAGE.md)** - LogsTab 頁面使用說明
4. **[日誌文件說明](features/LOG_FILES_EXPLAINED.md)** - 各日誌文件的用途和配置
5. **[DHCP SSH 集成](features/DHCP_SSH_INTEGRATION.md)** - DHCP 伺服器 SSH 連接實作
6. **[自動 Switch 同步](features/auto-switch-sync/QUICKSTART.md)** - 🆕 新增 DHCP Server 後自動識別 Switch
7. **[Server 下拉選單排序](features/server-dropdown-sorting/README.md)** - 🆕 Server 列表 IP 排序與搜尋

### API 文檔
1. **[API 測試報告](api/API_TEST_REPORT.md)** - 所有 API 端點的測試結果

## 📖 按主題查找

### Docker 相關
- [部署指南 - Docker Compose 設定](deployment/DEPLOYMENT.md#docker-compose-配置)
- [開發指南 - Docker 開發環境](development/DEVELOPMENT.md#docker-開發工作流程)

### 日誌功能
- [日誌 API 實作報告](features/LOGS_API_IMPLEMENTATION.md) - 技術實作細節
- [LogsTab 使用指南](features/LOGS_TAB_USAGE.md) - 用戶使用說明
- [日誌文件說明](features/LOG_FILES_EXPLAINED.md) - 日誌配置和維護
- [日誌功能快速開始](quickstart/LOGS_QUICKSTART.md) - 快速上手

### DHCP 功能
- [DHCP SSH 集成](features/DHCP_SSH_INTEGRATION.md) - SSH 連接和租約同步
- [API 測試報告](api/API_TEST_REPORT.md) - DHCP API 測試結果

### 數據轉換
- [真實數據轉換報告](development/REAL_DATA_CONVERSION_REPORT.md) - OverviewTab 和 LogsTab 轉換過程

## 🔍 常見問題快速索引

| 問題 | 查看文檔 |
|------|---------|
| 如何快速啟動專案？ | [快速開始](quickstart/QUICKSTART.md) |
| 如何查看 DHCP 日誌？ | [LogsTab 使用指南](features/LOGS_TAB_USAGE.md) |
| 日誌顯示 Django 內部訊息？ | [日誌文件說明 - Django 日誌混入](features/LOG_FILES_EXPLAINED.md#問題-django-日誌混入) |
| 如何設置開發環境？ | [開發指南](development/DEVELOPMENT.md) |
| 如何部署到生產環境？ | [部署指南](deployment/DEPLOYMENT.md) |
| API 端點有哪些？ | [API 測試報告](api/API_TEST_REPORT.md) |
| 如何配置 SSH 連接？ | [DHCP SSH 集成](features/DHCP_SSH_INTEGRATION.md) |
| 新增 DHCP Server 後 Switch 沒有自動出現？ | [自動 Switch 同步](features/auto-switch-sync/QUICKSTART.md) |
| Server 下拉選單順序混亂？ | [Server 下拉選單排序](features/server-dropdown-sorting/README.md) |

## 📝 文檔更新記錄

| 日期 | 文檔 | 變更 |
|------|------|------|
| 2025-11-07 | server-dropdown-sorting/ | 🆕 新增 Server 下拉選單排序功能 |
| 2025-11-07 | auto-switch-sync/ | 🆕 新增自動 Switch 同步功能文檔 |
| 2025-10-27 | 所有文檔 | 重新組織文檔結構，移至 docs/ 目錄 |
| 2025-10-27 | LOG_FILES_EXPLAINED.md | 新增，說明日誌文件和 Django 日誌混入問題 |
| 2025-10-27 | LOGS_IMPLEMENTATION_COMPLETE.md | 新增，日誌功能完成總結 |
| 2025-10-27 | LOGS_API_IMPLEMENTATION.md | 日誌 API 實作完成 |
| 2025-10-27 | REAL_DATA_CONVERSION_REPORT.md | OverviewTab 和 LogsTab 轉換完成 |

---

**維護者**: Network Toolbox Team  
**最後更新**: 2025-11-07
