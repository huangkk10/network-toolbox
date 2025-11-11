# Jenkins Artifacts 功能文檔

本目錄包含 Jenkins Build Artifacts 自動存儲和處理相關的功能文檔。

## 📚 文檔列表

- [CELERY_ARTIFACTS_TASKS.md](CELERY_ARTIFACTS_TASKS.md) - Celery 自動化任務說明
- [ARTIFACTS_AUTO_EXTRACT.md](ARTIFACTS_AUTO_EXTRACT.md) - 自動解壓縮功能說明

## 🎯 功能概述

### Celery 自動化任務
- 自動掃描新的 Jenkins Builds
- 下載並存儲 Artifacts 到 NAS
- 支持定時任務和手動觸發

### 自動解壓縮
- 支持多種壓縮格式（7z, zip, tar.* 等）
- 解壓成功後自動刪除原始壓縮檔
- 保持目錄結構完整

## 🔗 相關文檔

- **快速啟動**：`docs/quickstart/QUICKSTART_JENKINS_AUTO_STORAGE.md`
- **實施報告**：`docs/features/jenkins-auto-storage/IMPLEMENTATION_REPORT.md`
