# Jenkins Workspace 存儲功能 - 測試指南

## 📋 測試目標

驗證 Jenkins Build Workspace 可以成功存儲到 NAS (`/mnt/mdt/jenkins_test_storage`)

---

## 🎯 測試準備

### 1. 確認 NAS 掛載狀態

```bash
# 檢查 NAS 掛載
curl -s http://localhost/api/jenkins-builds/check_nas_status/ | python3 -m json.tool

# 預期輸出：
# {
#     "success": true,
#     "nas_check": {
#         "accessible": true,
#         "writable": true
#     },
#     ...
# }
```

✅ **狀態**：NAS 已成功掛載

### 2. 確認測試數據

**可用的 Jenkins Servers**：
- Server 1: `10.252.170.187` (http://10.252.170.187:8080/)
- Server 2: `Performance` (http://10.252.170.188:8080/)

**可用的 Test Builds**：
- Job: `PC51Q_seed` (Job ID: 25)
  - Build #6 ✅ SUCCESS
  - Build #5 ✅ SUCCESS
  - Build #4 ✅ SUCCESS

---

## 🧪 測試步驟

### 方法 1：通過前端 UI 測試（推薦）

#### 步驟 1：打開 RVT 分析頁面

1. 打開瀏覽器訪問：http://localhost/rvt-analytics

2. 切換到 **"Jenkins 詳細"** Tab

3. 選擇 Jenkins Server（例如：`Performance` 或 `10.252.170.187`）

#### 步驟 2：找到 Build 並展開

1. 在 Table 中找到 `PC51Q_seed` Job

2. 點擊展開圖標（▶️）展開 Builds

3. 應該看到多個 Builds：
   - Build #6 ✅ SUCCESS
   - Build #5 ✅ SUCCESS
   - Build #4 ✅ SUCCESS

#### 步驟 3：存儲 Workspace

1. 在 Build #6 的操作欄中，點擊 **"Workspace"** 按鈕（💾 圖標）

2. 確認對話框會顯示：
   ```
   確定要將以下 Build 的 Workspace 存儲到 NAS 嗎？
   
   Job: PC51Q_seed
   Build: #6
   
   存儲路徑：\\10.250.0.1\mdt\Team\PQ1-3\tool\jenkins_test_storage\
           {jenkins_ip}\{job_name}\{build_number}
   ```

3. 點擊 **"確定存儲"**

#### 步驟 4：等待存儲完成

- 應該看到 Loading 提示
- 成功後會顯示：
  ```
  ✅ Workspace 存儲成功！
  路徑: /mnt/mdt/jenkins_test_storage/10.252.170.188/PC51Q_seed/6/workspace
  大小: X.XX MB
  文件數: XX
  ```

#### 步驟 5：驗證存儲結果

**方式 A：通過容器檢查**
```bash
# 列出存儲的文件
docker exec nt-django ls -lah /mnt/mdt/jenkins_test_storage/

# 檢查特定 Build 的 Workspace
docker exec nt-django ls -lah /mnt/mdt/jenkins_test_storage/10.252.170.188/PC51Q_seed/6/
```

**方式 B：通過 NAS 網路共享（Windows）**
```
\\10.250.0.1\mdt\jenkins_test_storage\10.252.170.188\PC51Q_seed\6\
```

**方式 C：通過 NAS 網路共享（Linux/Mac）**
```bash
smb://10.250.0.1/mdt/jenkins_test_storage/10.252.170.188/PC51Q_seed/6/
```

---

### 方法 2：通過 API 直接測試

#### 步驟 1：獲取 Build ID

```bash
# 列出 Job 25 的 Builds
curl -s "http://localhost/api/jenkins-jobs/25/builds/" | python3 -m json.tool

# 記下 Build ID，例如：jenkins-25-6
```

#### 步驟 2：調用存儲 API

```bash
# 存儲 Build jenkins-25-6 的 Workspace
curl -X POST "http://localhost/api/jenkins-builds/jenkins-25-6/store_workspace/" \
  -H "Content-Type: application/json" \
  | python3 -m json.tool
```

**預期成功響應**：
```json
{
    "success": true,
    "message": "Workspace 存儲成功",
    "workspace_path": "/mnt/mdt/jenkins_test_storage/10.252.170.188/PC51Q_seed/6/workspace",
    "workspace_size": 12345678,
    "files_count": 25,
    "stored_at": "2025-11-05T10:30:00"
}
```

**預期錯誤響應（如果 Jenkins 不可訪問）**：
```json
{
    "success": false,
    "error": "下載失敗: Connection timeout"
}
```

#### 步驟 3：驗證存儲

```bash
# 檢查容器內文件
docker exec nt-django ls -lah /mnt/mdt/jenkins_test_storage/10.252.170.188/PC51Q_seed/6/

# 檢查文件樹結構
docker exec nt-django tree -L 3 /mnt/mdt/jenkins_test_storage/
```

---

## ✅ 成功標準

### 必須滿足的條件：

1. ✅ **API 返回成功**
   - `success: true`
   - 返回 `workspace_path`、`workspace_size`、`files_count`

2. ✅ **文件實際存在**
   ```bash
   docker exec nt-django ls /mnt/mdt/jenkins_test_storage/10.252.170.188/PC51Q_seed/6/workspace/
   # 應該列出 Workspace 文件
   ```

3. ✅ **數據庫更新**
   ```bash
   # 檢查 Build 記錄
   docker exec nt-django python manage.py shell -c "
   from api.models import JenkinsBuild
   build = JenkinsBuild.objects.get(id='jenkins-25-6')
   print(f'Stored: {build.is_workspace_stored}')
   print(f'Path: {build.workspace_path}')
   print(f'Size: {build.workspace_size}')
   "
   ```

4. ✅ **前端顯示更新**
   - 刷新頁面後，Build 應該顯示 "已存儲" 標籤（如果你已實現 Phase 8.2）

---

## ❌ 常見錯誤

### 錯誤 1：NAS 掛載失敗

**錯誤訊息**：
```json
{
    "success": false,
    "error": "基礎路徑不存在: /mnt/mdt/jenkins_test_storage"
}
```

**解決方式**：
```bash
# 重啟 Django 容器以重新掛載 NAS
docker compose restart django

# 檢查掛載狀態
docker logs nt-django --tail 20
```

### 錯誤 2：Jenkins 連接失敗

**錯誤訊息**：
```json
{
    "success": false,
    "error": "下載失敗: Connection refused"
}
```

**原因**：
- Jenkins Server 離線或不可訪問
- 網路連通性問題

**檢查方式**：
```bash
# 從容器內測試 Jenkins 連接
docker exec nt-django curl -I http://10.252.170.188:8080/job/PC51Q_seed/6/
```

### 錯誤 3：認證失敗

**錯誤訊息**：
```json
{
    "success": false,
    "error": "下載失敗: 401 Unauthorized"
}
```

**解決方式**：
- 檢查 Jenkins Server 的 `username` 和 `api_token` 是否正確
- 在 Django Admin 更新憑證

### 錯誤 4：權限錯誤

**錯誤訊息**：
```json
{
    "success": false,
    "error": "存儲失敗: Permission denied"
}
```

**解決方式**：
```bash
# 檢查目錄權限
docker exec nt-django ls -la /mnt/mdt/jenkins_test_storage/

# 修改權限（如果需要）
docker exec nt-django chmod -R 755 /mnt/mdt/jenkins_test_storage/
```

---

## 📊 測試後檢查清單

- [ ] API 返回成功狀態
- [ ] 文件存在於容器內 (`/mnt/mdt/jenkins_test_storage/...`)
- [ ] 文件存在於 NAS 共享路徑
- [ ] 數據庫記錄已更新（`is_workspace_stored = True`）
- [ ] 文件大小合理（大於 0）
- [ ] 文件數量合理（大於 0）
- [ ] 日誌沒有錯誤訊息

---

## 🎯 下一步

測試成功後，可以開始：

1. **Phase 8.2：顯示存儲狀態**
   - 在 Table 中添加 "Workspace" 欄位
   - 顯示已存儲/未存儲標籤
   - 顯示文件大小和存儲時間

2. **Phase 8.3：存儲空間統計**
   - 創建統計 API
   - 在概觀 Tab 添加統計卡片

3. **批量存儲功能**
   - 選擇多個 Builds
   - 批量執行存儲操作

---

**測試指南版本**：1.0  
**最後更新**：2025-11-05  
**文件位置**：`docs/features/jenkins-workspace-storage/TESTING_GUIDE.md`
