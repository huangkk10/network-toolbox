# Jenkins Console Log Fatal Error 分析功能

> **狀態**: Phase 1 已完成 ✅  
> **版本**: 1.0  
> **創建日期**: 2025-11-27  
> **最後更新**: 2025-11-27

---

## 📚 文檔導航

### 核心文檔

- **[實作計畫](./IMPLEMENTATION_PLAN.md)** ⭐  
  完整的功能規劃、技術設計和實施步驟

- **[Phase 1 完成報告](./PHASE1_COMPLETION_REPORT.md)** 🎉  
  核心分析模組開發完成並通過驗證

- **[Fatal Block 提取分析](./FATAL_BLOCK_EXTRACTION_ANALYSIS.md)**  
  詳細的演算法設計和邊界處理說明

### 功能概述

此功能從已存儲的 Jenkins Console Log 中自動提取包含 "fatal" 關鍵字的 Ansible Task 範圍，並將結果保存為 JSON 文件到 NAS。

### 核心特性

✅ **智能觸發**：僅在 Jenkins Build 狀態為 `FAILURE` 時執行分析  
✅ **無縫整合**：與現有 Console Log 下載流程整合  
✅ **精準定位**：自動識別 fatal 錯誤所屬的完整 Ansible Task 範圍  
✅ **結構化存儲**：分析結果以 JSON 格式存儲到 NAS  

### 整合位置

- **Task**: `store_jenkins_build_task`（`backend/api/tasks.py`）
- **觸發條件**: `build.result == 'FAILURE'` 且 Console Log 下載成功
- **分析器**: `ConsoleLogAnalyzer`（`backend/library/utils/console_log_analyzer.py`）

### 輸出範例

**JSON 文件路徑**：
```
\\10.250.0.1\mdt\Team\PQ1-3\tool\jenkins_test_storage\
  └── {server_ip}/
      └── {job_name}/
          └── {build_number}/
              ├── console.log
              ├── console_log_analysis.json  ← 分析結果
              └── workspace/
```

**JSON 結構**：
```json
{
  "build_info": {
    "jenkins_server": "10.252.170.171",
    "job_name": "Test-KVM01",
    "build_number": 166
  },
  "summary": {
    "total_fatal_tasks": 2,
    "fatal_keywords_found": 5
  },
  "fatal_tasks": [
    {
      "task_name": "test : Validate test case STC-551",
      "task_start_time": "13:20:22",
      "task_start_line": 1234,
      "task_end_line": 1256,
      "fatal_count": 2,
      "task_content": "..."
    }
  ]
}
```

---

## 🚀 快速開始

### 查看計畫

請參閱 **[實作計畫](./IMPLEMENTATION_PLAN.md)** 了解：
- 現有機制分析
- 整合方案設計
- 技術實現細節
- 完整實施步驟

---

## 📝 狀態追蹤

### Phase 1: 核心分析模組開發 ✅
- [x] 創建 `ConsoleLogAnalyzer` 類
- [x] 實現核心分析方法（6 個核心方法 + 輔助方法）
- [x] 編寫單元測試（27 個測試用例，100% 通過）
- [x] 創建測試數據（5 個測試場景）
- [x] 驗證功能（所有測試通過）
- [x] 完成報告（[查看報告](./PHASE1_COMPLETION_REPORT.md)）

### Phase 2: 整合到 Celery Task ⏸️
- [ ] 擴展數據庫模型（可選）
- [ ] 修改 `store_jenkins_build_task`
- [ ] 整合測試

### Phase 3: API 和前端（可選） ⏸️
- [ ] 創建 API 端點
- [ ] 前端組件開發
- [ ] UI/UX 測試

### Phase 4: 批量處理（可選） ⏸️
- [ ] 創建 Management Command
- [ ] 批量處理測試

---

**文檔維護者**：Network Toolbox Team  
**最後更新**：2025-11-27
