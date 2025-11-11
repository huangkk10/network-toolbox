# Jenkins Artifacts 自動解壓縮功能

## 📋 功能概述

當從 Jenkins 下載 Build Artifacts 並存儲到 NAS 時，系統會**自動檢測並解壓縮**壓縮檔案，解壓縮成功後會**自動刪除原始壓縮檔**，只保留解壓後的內容。

## 🎯 支持的壓縮格式

| 格式 | 副檔名 | 解壓工具 | 狀態 |
|------|--------|----------|------|
| 7-Zip | `.7z` | `7z` (p7zip-full) | ✅ 支持 |
| ZIP | `.zip` | Python `zipfile` | ✅ 支持 |
| TAR | `.tar` | Python `tarfile` | ✅ 支持 |
| TAR.GZ | `.tar.gz`, `.tgz` | Python `tarfile` | ✅ 支持 |
| TAR.BZ2 | `.tar.bz2`, `.tbz2` | Python `tarfile` | ✅ 支持 |
| TAR.XZ | `.tar.xz` | Python `tarfile` | ✅ 支持 |

## 📂 存儲結構

```
/mnt/mdt/Team/PQ1-3/tool/jenkins_test_storage/
└── {jenkins_ip}/
    └── {job_name}/
        └── {build_number}/
            ├── workspace/                    # Workspace 檔案
            └── artifacts/                    # Artifacts 檔案
                ├── folder1/                  # ✅ 解壓縮內容
                │   ├── file1.txt
                │   └── file2.log
                └── folder2/                  # ✅ 解壓縮內容
                    └── data.bin
```

**特點**：
- ✅ 原始壓縮檔**自動刪除**（節省空間）
- ✅ 只保留解壓縮後的內容
- ✅ 保持原始目錄結構

## 🧪 測試案例：Test-KVM01 Build #148

### 測試對象
- **Server**: 10.252.170.171 (uart)
- **Job**: Test-KVM01
- **Build**: #148
- **Artifact**: `RVT-SupportBundle_Test-KVM01_20251105_105701.7z`
- **原始大小**: 54.89 MB (57,551,432 bytes)

### 測試結果

```bash
# 1. 下載並存儲 Artifact
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
      "extracted": true,           // ✅ 已解壓縮
      "extracted_files": 20,       // ✅ 解壓出 20 個檔案
      "extracted_size": 63140025   // ✅ 解壓後總大小 60.2 MB
    }
  ]
}
```

### 目錄結構

```
148/artifacts/
├── inventory/                                        (解壓縮內容)
│   ├── group_vars/
│   │   ├── IOL_Linux/
│   │   ├── PQ1_3_K01/
│   │   ├── PQ1_3_K07/
│   │   ├── PQ1_3_K13/
│   │   ├── PQ1_3_K14/
│   │   └── PQ1_3_MANDi/
│   └── hosts
└── output/                                           (解壓縮內容)
    ├── automp/
    │   ├── InitialCard_DynamicLogging_*.log
    │   └── InitialCard_Test-KVM01.log
    └── firmware/
        ├── STD_Pyrite/
        ├── firmware_file_name.txt
        └── fw_package.ini

統計：
- 總檔案數: 20（原始壓縮檔已刪除）
- 總目錄數: 15
- 總大小: 61 MB（只包含解壓內容）
```

## 🔧 實現細節

### 1. 自動檢測

系統會根據副檔名自動判斷是否為壓縮檔：

```python
supported_formats = {
    '.7z': '7z',
    '.zip': 'zip',
    '.tar': 'tar',
    '.gz': 'tar.gz',
    '.tgz': 'tar.gz',
    '.bz2': 'tar.bz2',
    '.tbz2': 'tar.bz2',
    '.xz': 'tar.xz',
}
```

### 2. 解壓流程

```
下載 Artifact
    ↓
檢查副檔名
    ↓
是壓縮檔？
    ├─ 是 → 自動解壓縮
    │       ├─ 7z  → 使用 7z 命令
    │       ├─ zip → 使用 zipfile 模塊
    │       └─ tar.* → 使用 tarfile 模塊
    │       ↓
    │   解壓成功？
    │       ├─ 是 → 刪除原始壓縮檔 ✅
    │       └─ 否 → 保留原始壓縮檔（記錄錯誤）
    └─ 否 → 保留原始檔案
```

### 3. 錯誤處理

- ✅ 壓縮檔損壞：記錄錯誤但保留原始檔案
- ✅ 解壓超時：300 秒超時保護
- ✅ 磁碟空間不足：提前檢查並報錯
- ✅ 權限問題：記錄錯誤訊息

## 📊 API 使用

### 獲取 Artifacts 資訊（含解壓狀態）

```bash
GET /api/jenkins-builds/{build_id}/artifacts/
```

**回應**：
```json
{
  "success": true,
  "build_id": 1048,
  "artifacts_count": 1,
  "artifacts": [
    {
      "file_name": "RVT-SupportBundle_*.7z",
      "size": 57551432,
      "extracted": true,
      "extracted_files": 20,
      "extracted_size": 63140025
    }
  ]
}
```

### 存儲並自動解壓

```bash
POST /api/jenkins-builds/{build_id}/store_artifacts/
```

系統會自動：
1. 下載 Artifact
2. 檢測壓縮格式
3. 解壓縮到同一目錄
4. 更新數據庫記錄
5. 返回詳細結果

## 🎛️ 配置選項

### 數據庫欄位

```python
class JenkinsBuild(models.Model):
    # Artifacts 存儲
    artifacts_path = models.CharField(...)       # 存儲路徑
    artifacts_size = models.BigIntegerField(...)  # 總大小
    artifacts_count = models.IntegerField(...)    # 檔案數量
    artifacts_list = models.JSONField(...)        # 詳細清單（含解壓資訊）
    is_artifacts_stored = models.BooleanField(...) # 是否已存儲
    artifacts_stored_at = models.DateTimeField(...) # 存儲時間
```

### artifacts_list 格式

```json
[
  {
    "file_name": "file.7z",
    "relative_path": "file.7z",
    "size": 57551432,
    "local_path": "/mnt/mdt/.../artifacts/file.7z",
    "extracted": true,           // ✅ 是否已解壓
    "extracted_files": 20,       // 解壓出的檔案數
    "extracted_size": 63140025   // 解壓後總大小
  }
]
```

## 💡 使用案例

### 案例 1：測試報告壓縮包

```
test-results.zip  (5 MB)
    ├── junit/
    │   └── TEST-*.xml
    ├── coverage/
    │   └── index.html
    └── screenshots/
        └── *.png
```

**好處**：可以直接訪問解壓後的 HTML 報告，無需手動下載解壓

### 案例 2：固件包

```
firmware-bundle.7z  (200 MB)
    ├── bin/
    │   └── firmware.bin
    ├── configs/
    │   └── settings.json
    └── docs/
        └── release-notes.txt
```

**好處**：測試人員可以直接從 NAS 訪問固件和配置文件

### 案例 3：日誌壓縮包

```
logs.tar.gz  (50 MB)
    ├── application.log
    ├── error.log
    └── debug/
        └── trace.log
```

**好處**：可以快速查看日誌內容，無需下載整個壓縮包

## 🔍 日誌示例

```
[INFO] 開始存儲 Artifacts 到: /mnt/mdt/.../artifacts
[INFO] 下載 Artifact: RVT-SupportBundle_*.7z
[INFO] 開始解壓縮: RVT-SupportBundle_*.7z (格式: 7z)
[INFO] ✓ 解壓縮成功: 20 個檔案, 60.21 MB
[INFO] ✓ 已刪除原始壓縮檔: RVT-SupportBundle_*.7z
[INFO]   ✓ RVT-SupportBundle_*.7z (54.89 MB) - 已解壓縮 20 個檔案
[INFO] Artifacts 存儲完成: 1/1 個檔案
```

## ⚠️ 注意事項

1. **磁碟空間**
   - 解壓縮過程中會暫時消耗雙倍空間（壓縮檔 + 解壓內容）
   - 解壓成功後自動刪除壓縮檔，只保留解壓內容
   - 相比保留壓縮檔，節省約 50% 的存儲空間

2. **解壓時間**
   - 大型壓縮檔（> 500 MB）可能需要較長時間
   - 設有 300 秒超時保護

3. **權限要求**
   - 需要 NAS 目錄的寫入權限
   - Docker 容器需要安裝 `p7zip-full`

4. **失敗處理**
   - 如果解壓失敗，原始壓縮檔**會保留**
   - 可以從數據庫的 `extracted` 欄位判斷是否解壓成功

## 🚀 部署需求

### Docker 容器

在 `Dockerfile` 中添加：

```dockerfile
RUN apt-get update && apt-get install -y \
    p7zip-full \
    && rm -rf /var/lib/apt/lists/*
```

### 驗證安裝

```bash
docker exec nt-django which 7z
# 輸出: /usr/bin/7z
```

## 📚 相關文檔

- [Jenkins Artifacts 功能實現完成總結](./README.md)
- [QUICKSTART_JENKINS_AUTO_STORAGE.md](./QUICKSTART_JENKINS_AUTO_STORAGE.md)
- [API 文檔](./docs/api/)

## 🎉 總結

- ✅ **自動化**：下載即解壓，無需手動操作
- ✅ **透明化**：API 回應包含解壓資訊
- ✅ **節省空間**：解壓成功後自動刪除壓縮檔
- ✅ **高效率**：支持多種壓縮格式
- ✅ **可靠性**：完善的錯誤處理，失敗時保留原始檔案

---

**最後更新**: 2025-11-10  
**測試環境**: Docker + Django 4.2 + Python 3.11  
**測試狀態**: ✅ 通過（含自動刪除功能）
