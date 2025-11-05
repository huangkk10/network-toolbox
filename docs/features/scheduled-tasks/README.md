# 📅 定時任務功能文檔

本目錄包含 Network Toolbox 的定時任務（Scheduled Tasks）相關文檔。

## 📚 文檔列表

### 核心指南

#### 1. [CRON_VS_CELERY_COMPARISON.md](./CRON_VS_CELERY_COMPARISON.md)
**定時任務方案比較：主機 Cron vs 容器 Celery Beat**

- 📊 兩種方案的詳細對比
- 🎯 專案需求分析
- 💡 建議選擇與理由
- 📝 適用場景說明

**適合閱讀對象**：決策者、架構師、初次部署者

---

#### 2. [CRON_SETUP_GUIDE.md](./CRON_SETUP_GUIDE.md)
**方案 A：Cron 定時任務設置指南**

- ⚙️ Cron 設置步驟（5 分鐘完成）
- ✅ 驗證與測試方法
- 🔧 調整與優化技巧
- 🛠️ 故障排查指南

**適合閱讀對象**：選擇 Cron 方案的使用者

---

#### 3. [CELERY_IMPLEMENTATION_GUIDE.md](./CELERY_IMPLEMENTATION_GUIDE.md)
**方案 B：Celery 實施指南**

- 🎯 已完成的配置清單
- 🚀 部署步驟（含遷移）
- 📊 Flower 監控功能說明
- 🛠️ 常用管理命令
- 🔍 故障排查
- 📈 監控與維護

**適合閱讀對象**：選擇 Celery 方案的使用者

---

#### 4. [LOGS_SYNC_GUIDE.md](./LOGS_SYNC_GUIDE.md)
**DHCP 日誌同步完整指南**

- 🔄 Windows DHCP Server 日誌機制解析
- 📊 7 天滾動視窗實現原理
- ⏰ 定時同步配置建議
- 📈 資料累積時間線
- 🛠️ 故障排查與維護

**適合閱讀對象**：所有使用日誌同步功能的使用者

---

#### 5. [ADDING_NEW_CELERY_TASK_GUIDE.md](./ADDING_NEW_CELERY_TASK_GUIDE.md)
**如何在 iPXE 功能中加入新的 Celery 定期任務（詳細指南）**

- 📝 完整的步驟指南（5 個步驟）
- 💼 實際範例（從 API 抓取資料、解析日誌檔案）
- 🧪 測試與驗證方法
- ❓ 常見問題解答
- 🎯 最佳實踐

**適合閱讀對象**：開發者、需要新增定期任務的使用者

---

#### 6. [QUICK_REFERENCE.md](./QUICK_REFERENCE.md)
**新增 Celery 任務快速參考（5 分鐘速成）**

- ⚡ 5 分鐘快速新增任務流程
- 📋 實用的代碼模板
- 🎯 關鍵要點（DO & DON'T）
- 🔍 快速故障排查

**適合閱讀對象**：有經驗的開發者、需要快速參考的使用者

---

#### 7. [CHECKLIST.md](./CHECKLIST.md)
**新增任務檢查清單（確保萬無一失）**

- ✅ 逐步檢查清單（所有必要步驟）
- 🔍 驗證步驟（6 種檢查方法）
- ❌ 常見問題排查
- 📊 完成度驗證

**適合閱讀對象**：所有使用者，特別是初次新增任務的使用者

---

## 🎯 快速導航

### 我該選擇哪種方案？

```
簡單需求（個人/小團隊）
├─ 只需要基本的定時同步
├─ 不需要 Web 監控界面
└─ 資源受限（記憶體 < 2GB）
    → 選擇 Cron（方案 A）
    → 閱讀：CRON_SETUP_GUIDE.md

企業級需求
├─ 需要 Web 監控與任務追蹤
├─ 需要動態調整排程
├─ 需要任務失敗自動重試
└─ 未來可能有複雜的定時任務
    → 選擇 Celery（方案 B）
    → 閱讀：CELERY_IMPLEMENTATION_GUIDE.md
```

### 我已經選好方案了，怎麼開始？

**方案 A（Cron）使用者**：
1. 閱讀 `CRON_SETUP_GUIDE.md`
2. 執行 5 分鐘設置步驟
3. 閱讀 `LOGS_SYNC_GUIDE.md` 了解日誌機制
4. 開始使用！

**方案 B（Celery）使用者**：
1. 閱讀 `CELERY_IMPLEMENTATION_GUIDE.md`
2. 按照指南執行部署步驟（已完成大部分配置）
3. 訪問 Flower 監控界面（http://localhost:5555）
4. 閱讀 `LOGS_SYNC_GUIDE.md` 了解日誌機制
5. 開始使用！

---

## 📊 功能對比表

| 功能 | Cron 方案 | Celery 方案 |
|------|-----------|-------------|
| **Web 監控** | ❌ | ✅ Flower |
| **任務歷史** | ❌ 日誌文件 | ✅ 資料庫 |
| **動態調整** | ❌ 編輯 crontab | ✅ Web 管理 |
| **失敗重試** | ❌ 手動 | ✅ 自動（3次） |
| **資源消耗** | 0 MB | +250 MB |
| **容器數量** | 4 個 | 7 個 |
| **設置時間** | 5 分鐘 | 已完成 |
| **維護成本** | 極低 | 中等 |

---

## 🔗 相關文檔

- **API 文檔**：`docs/api/`
- **部署文檔**：`docs/deployment/DEPLOYMENT.md`
- **開發文檔**：`docs/development/DEVELOPMENT.md`
- **日誌功能**：`docs/features/LOGS_*.md`

---

## 💡 常見問題

### Q1：我可以從 Cron 切換到 Celery 嗎？
**A**：可以！兩種方案可以共存或遷移。如果需要切換：
1. 停用 Cron 任務（`crontab -e` 註解掉）
2. 按照 `CELERY_IMPLEMENTATION_GUIDE.md` 部署 Celery
3. 驗證 Celery 正常運行後，移除 Cron 配置

### Q2：定時任務多久執行一次？
**A**：預設配置：
- **同步任務**：每 5 分鐘執行一次
- **清理任務**：每天凌晨 3 點執行一次

可以根據實際需求調整頻率。

### Q3：為什麼只有 1 天的日誌數據？
**A**：這是正常現象！請閱讀 `LOGS_SYNC_GUIDE.md` 了解：
- Windows DHCP Server 使用**週循環**（7 個檔案）
- 只有當前週的日誌存在於 Windows Server
- 需要**連續同步 7 天**才能累積完整的 7 天資料庫記錄

### Q4：定時任務失敗了怎麼辦？
**A**：
- **Cron 方案**：查看 `logs/cron_sync.log` 日誌檔案
- **Celery 方案**：訪問 Flower (http://localhost:5555) 查看失敗任務詳情

兩種方案的故障排查步驟都在各自的指南中有詳細說明。

---

## 🚀 下一步

1. **選擇方案**：閱讀 `CRON_VS_CELERY_COMPARISON.md`
2. **部署實施**：按照對應的指南操作
3. **理解機制**：閱讀 `LOGS_SYNC_GUIDE.md`
4. **監控維護**：定期檢查任務執行狀態

---

**最後更新**：2025-10-28  
**維護者**：Network Toolbox Team
