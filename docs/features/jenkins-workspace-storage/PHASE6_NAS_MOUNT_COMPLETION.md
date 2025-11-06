# Phase 6: NAS 掛載配置 - 完成報告

## 📋 任務概述

**目標**：配置 Docker 容器內 NAS 掛載（方案 B：容器內直接掛載）

**完成日期**：2025-11-05

**NAS 配置**：
- IP: `10.250.0.1`
- 共享: `mdt`
- 用戶: `mdt`
- 密碼: `p@ssw0rd`
- 掛載點: `/mnt/mdt`
- Jenkins 存儲路徑: `/mnt/mdt/jenkins_test_storage`

---

## ✅ 已完成的任務

### 1. 修改 Dockerfile

**文件**: `backend/Dockerfile`

```dockerfile
# 安裝 cifs-utils（CIFS/SMB 掛載工具）
RUN apt-get update && apt-get install -y \
    postgresql-client \
    iputils-ping \
    cifs-utils \
    && rm -rf /var/lib/apt/lists/*

# 設置啟動腳本權限
RUN chmod +x /app/entrypoint.sh /app/mount_nas.sh
```

### 2. 創建 NAS 掛載腳本

**文件**: `backend/mount_nas.sh`

功能：
- ✅ 從環境變數讀取 NAS 配置
- ✅ 檢查是否已掛載（避免重複掛載）
- ✅ 使用 `mount -t cifs` 掛載 SMB/CIFS 共享
- ✅ 自動創建 Jenkins 存儲目錄
- ✅ 驗證掛載成功並列出目錄內容

關鍵命令：
```bash
mount -t cifs "//${NAS_IP}/${NAS_SHARE}" "${MOUNT_POINT}" \
    -o username="${NAS_USER}",password="${NAS_PASSWORD}",uid=0,gid=0,file_mode=0755,dir_mode=0755
```

### 3. 創建容器啟動腳本

**文件**: `backend/entrypoint.sh`

功能：
- ✅ 啟動時自動執行 NAS 掛載腳本
- ✅ 掛載失敗不中斷服務啟動（容錯處理）
- ✅ 啟動 Django 開發伺服器

### 4. 修改 docker-compose.yml

**修改的服務**: `django`, `celery_worker`, `celery_beat`

新增配置：
```yaml
privileged: true  # 允許容器內執行 mount 命令
cap_add:
  - SYS_ADMIN  # 需要系統管理員能力
devices:
  - /dev/fuse  # FUSE 設備（可選）

environment:
  - NAS_MOUNT_PATH=/mnt/mdt
  - NAS_IP=10.250.0.1
  - NAS_SHARE=mdt
  - NAS_USER=mdt
  - NAS_PASSWORD=p@ssw0rd
```

**Celery 服務啟動命令**：
```yaml
command: bash -c "bash /app/mount_nas.sh || true && celery -A network_toolbox worker ..."
```

### 5. 重建並啟動容器

**執行的命令**：
```bash
# 添加腳本執行權限
chmod +x backend/entrypoint.sh backend/mount_nas.sh

# 重建並啟動 Django 容器
docker compose up -d --build --force-recreate django

# 重建並啟動 Celery 容器
docker compose up -d --build --force-recreate celery_worker celery_beat
```

### 6. 驗證 NAS 掛載

**驗證結果**：

**容器日誌**：
```
✅ NAS 掛載成功！

掛載信息：
//10.250.0.1/mdt on /mnt/mdt type cifs (rw,relatime,vers=3.1.1,...)

目錄內容（前 10 項）：
drwxr-xr-x AutoMP/
drwxr-xr-x DS/
drwxr-xr-x Driver/
drwxr-xr-x Log/
...

📁 創建 Jenkins 存儲目錄: /mnt/mdt/jenkins_test_storage
✅ NAS 掛載完成！
```

**API 測試**：
```bash
curl http://localhost/api/jenkins-builds/check_nas_status/
```

返回：
```json
{
    "success": true,
    "nas_check": {
        "accessible": true,
        "writable": true
    },
    "mount_status": {
        "mount_point": "/mnt/mdt/jenkins_test_storage",
        "exists": true,
        "is_dir": true,
        "writable": true,
        "contents": []
    }
}
```

---

## 🔧 技術細節

### 方案 B：容器內直接掛載

**優點**：
- ✅ 不依賴主機配置
- ✅ 容器完全自包含
- ✅ 易於遷移和部署

**缺點**：
- ⚠️ 需要特權模式（`privileged: true`）
- ⚠️ 安全性較低（容器有更多權限）
- ⚠️ 容器重啟時需要重新掛載

### CIFS/SMB 掛載參數說明

| 參數 | 值 | 說明 |
|------|-----|------|
| `-t cifs` | - | 使用 CIFS（SMB）文件系統類型 |
| `username` | `mdt` | NAS 登錄用戶名 |
| `password` | `p@ssw0rd` | NAS 登錄密碼 |
| `uid=0` | root | 文件所有者 UID |
| `gid=0` | root | 文件所有者 GID |
| `file_mode=0755` | rwxr-xr-x | 文件權限 |
| `dir_mode=0755` | rwxr-xr-x | 目錄權限 |

### 容器權限配置

**privileged模式**：
```yaml
privileged: true
```
- 給予容器幾乎所有主機能力
- 等同於以 root 身份運行（在容器內）

**SYS_ADMIN 能力**：
```yaml
cap_add:
  - SYS_ADMIN
```
- 允許執行 `mount`、`umount` 等系統管理命令
- 更細粒度的權限控制（比 `privileged` 更安全）

---

## 📊 新增的 API 端點

### 檢查 NAS 狀態

**端點**: `GET /api/jenkins-builds/check_nas_status/`

**功能**：
- 檢查 NAS 路徑是否可訪問
- 檢查是否有寫入權限
- 列出目錄內容（前 10 項）

**響應示例**：
```json
{
    "success": true,
    "nas_check": {
        "accessible": true,
        "writable": true
    },
    "mount_status": {
        "mount_point": "/mnt/mdt/jenkins_test_storage",
        "exists": true,
        "is_dir": true,
        "writable": true,
        "contents": []
    }
}
```

---

## 🔍 故障排查

### 問題 1：權限錯誤（Permission denied）

**現象**：
```
exec: "/app/entrypoint.sh": permission denied
```

**解決方式**：
```bash
chmod +x backend/entrypoint.sh backend/mount_nas.sh
docker compose up -d --build django
```

### 問題 2：掛載失敗

**檢查步驟**：
```bash
# 1. 查看容器日誌
docker logs nt-django

# 2. 進入容器手動測試
docker exec -it nt-django bash
mount -t cifs //10.250.0.1/mdt /mnt/mdt -o username=mdt,password=p@ssw0rd

# 3. 檢查網路連通性
docker exec nt-django ping -c 3 10.250.0.1
```

### 問題 3：容器無法訪問 NAS

**可能原因**：
- 網路問題（容器無法訪問 NAS IP）
- 認證失敗（用戶名或密碼錯誤）
- NAS 共享未啟用（SMB/CIFS 服務未開啟）

**解決方式**：
```bash
# 檢查容器網路
docker network inspect nt_network

# 測試 NAS 連接
docker exec nt-django ping 10.250.0.1
docker exec nt-django mount | grep mdt
```

---

## 🎯 下一步

**Phase 6 已完成！** 可以開始 **測試基本存儲功能**

### 測試步驟：

1. **前往 RVT 分析頁面**
   - URL: http://localhost/rvt-analytics?tab=details

2. **選擇一個 Build**
   - 展開 Job，找到一個 Build

3. **點擊 "Workspace" 按鈕**
   - 確認存儲對話框顯示正確路徑
   - 點擊 "確定存儲"

4. **驗證存儲結果**
   ```bash
   # 檢查容器內文件
   docker exec nt-django ls -la /mnt/mdt/jenkins_test_storage/
   
   # 檢查 NAS 實際路徑（如果有訪問權限）
   # \\10.250.0.1\mdt\jenkins_test_storage\
   ```

---

## 📝 文件變更總結

### 修改的文件
1. `backend/Dockerfile` - 安裝 `cifs-utils`，設置腳本權限
2. `docker-compose.yml` - 添加特權模式、NAS 環境變數
3. `backend/api/views/jenkins.py` - 添加 `check_nas_status` API 端點

### 新增的文件
1. `backend/mount_nas.sh` - NAS 掛載腳本
2. `backend/entrypoint.sh` - 容器啟動腳本
3. `docs/features/jenkins-workspace-storage/PHASE6_NAS_MOUNT_COMPLETION.md` - 本文件

---

## ✨ 成功標準

- ✅ Django 容器啟動時自動掛載 NAS
- ✅ Celery Worker 和 Beat 容器也可訪問 NAS
- ✅ `/mnt/mdt/jenkins_test_storage` 目錄可讀寫
- ✅ API 端點 `check_nas_status` 返回成功狀態
- ✅ 容器重啟後 NAS 自動重新掛載

---

**完成者**：GitHub Copilot  
**審查者**：待審查  
**狀態**：✅ 完成，可以開始測試 Workspace 存儲功能
