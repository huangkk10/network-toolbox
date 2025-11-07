# Jenkins 整合功能文檔

**專案名稱**: Network Toolbox - Jenkins 整合  
**更新時間**: 2025-11-06

---

## 📚 文檔索引

### 核心文檔

1. **[開發進度報告](PROGRESS_REPORT.md)** - Jenkins 整合的完整開發進度
2. **[Blue Ocean Pipeline Stage 追蹤](BLUE_OCEAN_PIPELINE_STAGES.md)** - Pipeline Stage 失敗追蹤功能
3. **[Web UI 失敗 Stage 顯示](FEATURE_COMPLETED_WEB_UI_STAGE.md)** - ✨ 在前端顯示失敗 Stage 名稱

### 功能概述

本目錄包含 Network Toolbox 專案中 Jenkins 整合相關的所有文檔：

- ✅ Jenkins Server 管理
- ✅ Jenkins Job 同步
- ✅ Jenkins Build 記錄
- ✅ **Pipeline Stage 追蹤**（Blue Ocean）
- ✅ **Web UI 失敗 Stage 顯示** ✨ NEW
- ✅ NAS 存儲整合
- ✅ Build Workspace 自動存儲
- ✅ 前端 UI 頁面（基礎功能已完成）

---

## 🎯 快速開始

### 1. Blue Ocean Pipeline Stage 追蹤

**使用場景**: 追蹤 Jenkins Pipeline 中哪個 Stage 失敗

**文檔**: [BLUE_OCEAN_PIPELINE_STAGES.md](BLUE_OCEAN_PIPELINE_STAGES.md)

**快速範例**:
```bash
# 同步 Build 的 Pipeline Stage 資訊
curl -X POST http://localhost/api/jenkins-builds/123/pipeline_stages/

# 獲取失敗的 Stage
curl http://localhost/api/jenkins-builds/123/pipeline_stages/
```

---

### 2. 開發進度查詢

**文檔**: [PROGRESS_REPORT.md](PROGRESS_REPORT.md)

查看目前 Jenkins 整合的開發進度、已完成的功能、以及待開發項目。

---

## 📊 功能狀態

| 功能 | 狀態 | 文檔 |
|------|------|------|
| Pipeline Stage 追蹤 | ✅ 完成 | [BLUE_OCEAN_PIPELINE_STAGES.md](BLUE_OCEAN_PIPELINE_STAGES.md) |
| Jenkins Server 管理 | ✅ 完成 | [PROGRESS_REPORT.md](PROGRESS_REPORT.md) |
| Jenkins Job 同步 | ✅ 完成 | [PROGRESS_REPORT.md](PROGRESS_REPORT.md) |
| Build 記錄管理 | ✅ 完成 | [PROGRESS_REPORT.md](PROGRESS_REPORT.md) |
| NAS 存儲服務 | ✅ 完成 | [PROGRESS_REPORT.md](PROGRESS_REPORT.md) |
| Workspace 自動存儲 | ✅ 完成 | [PROGRESS_REPORT.md](PROGRESS_REPORT.md) |
| REST API 端點 | 🚧 部分完成 | [PROGRESS_REPORT.md](PROGRESS_REPORT.md) |
| 前端 UI 頁面 | ⏳ 待開始 | - |

---

## 🔗 相關連結

- **專案主頁**: [Network Toolbox](../../../README.md)
- **API 文檔**: [/docs/api/](../../api/)
- **開發文檔**: [/docs/development/](../../development/)

---

**維護者**: Network Toolbox Team
