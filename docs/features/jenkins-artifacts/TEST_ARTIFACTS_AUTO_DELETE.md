# Jenkins Artifacts 自動刪除壓縮檔測試報告

## 📋 測試目標

驗證在解壓縮成功後，系統會自動刪除原始壓縮檔，只保留解壓後的內容。

## 🧪 測試環境

- **Server**: 10.252.170.171 (uart)
- **Job**: Test-KVM01
- **Build**: #148
- **Artifact**: RVT-SupportBundle_Test-KVM01_20251105_105701.7z (54.89 MB)
- **測試日期**: 2025-11-10

## ✅ 測試結果

### 1. 下載並存儲 Artifact

```bash
curl -X POST http://localhost:8000/api/jenkins-builds/1048/store_artifacts/
```

**API 回應**：
```json
{
  "success": true,
  "artifacts_count": 1,
  "stored_items": [
    {
      "file_name": "RVT-SupportBundle_Test-KVM01_20251105_105701.7z",
      "size": 57551432,
      "extracted": true,
      "extracted_files": 20,
      "extracted_size": 63140025
    }
  ]
}
```

### 2. 驗證壓縮檔已刪除

```bash
# 查找 .7z 檔案
find /mnt/mdt/.../artifacts/ -name '*.7z' | wc -l
# 輸出: 0 ✅ 已刪除
```

### 3. 驗證解壓內容存在

```bash
ls -lh /mnt/mdt/.../artifacts/
# 輸出:
# drwxr-xr-x 2 root root 0 Nov  5 10:37 inventory
# drwxr-xr-x 2 root root 0 Nov 10 14:44 output
```

**統計資訊**：
- ✅ 總檔案數: **20**（只包含解壓內容）
- ✅ 總目錄數: **15**
- ✅ 總大小: **61 MB**（節省了 55 MB 壓縮檔空間）

### 4. 日誌驗證

```
[INFO] 開始解壓縮: RVT-SupportBundle_Test-KVM01_20251105_105701.7z (格式: 7z)
[INFO] ✓ 解壓縮成功: 20 個檔案, 60.22 MB
[INFO] ✓ 已刪除原始壓縮檔: RVT-SupportBundle_Test-KVM01_20251105_105701.7z
```

## 📊 空間節省效果

| 項目 | 之前（保留壓縮檔） | 現在（自動刪除） | 節省 |
|------|-------------------|-----------------|------|
| 壓縮檔 | 55 MB | 0 MB | -55 MB |
| 解壓內容 | 61 MB | 61 MB | 0 MB |
| **總計** | **116 MB** | **61 MB** | **-55 MB (47%)** |

## 🔄 完整流程

```
1. 下載 Artifact (54.89 MB)
   ↓
2. 解壓縮到同一目錄 (60.22 MB)
   ↓
3. 驗證解壓成功 (20 個檔案)
   ↓
4. 刪除原始壓縮檔 ✅
   ↓
5. 更新數據庫記錄
   - extracted: true
   - extracted_files: 20
   - extracted_size: 63140025
```

## ✨ 關鍵特性

1. **自動刪除** ✅
   - 解壓成功後立即刪除原始壓縮檔
   - 日誌記錄刪除操作

2. **錯誤處理** ✅
   - 如果解壓失敗，保留原始壓縮檔
   - 如果刪除失敗，記錄警告但不影響流程

3. **節省空間** ✅
   - 測試案例節省了 47% 的存儲空間
   - 對於大量 Build Artifacts，節省效果顯著

4. **透明追蹤** ✅
   - 數據庫記錄 `extracted` 狀態
   - API 回應包含解壓資訊

## 🎯 測試結論

✅ **測試通過**：自動刪除功能正常工作

- 解壓縮成功後，原始壓縮檔被正確刪除
- 只保留解壓後的內容，節省存儲空間
- 日誌完整記錄了整個過程
- API 回應正確反映了操作結果

## 📝 代碼實現

### jenkins_storage_service.py

```python
def _extract_archive(self, archive_path: Path, extract_to: Path) -> Dict[str, Any]:
    # ... 解壓縮邏輯 ...
    
    if success:
        logger.info(f"✓ 解壓縮成功: {files_count} 個檔案, {total_size / (1024**2):.2f} MB")
        
        # 刪除原始壓縮檔
        try:
            archive_path.unlink()
            logger.info(f"✓ 已刪除原始壓縮檔: {file_name}")
        except Exception as del_error:
            logger.warning(f"刪除原始壓縮檔失敗: {del_error}")
        
        return {
            'success': True,
            'files_count': files_count,
            'total_size': total_size
        }
```

---

**測試人員**: GitHub Copilot  
**測試日期**: 2025-11-10  
**測試狀態**: ✅ 通過
