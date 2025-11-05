# Jenkins/RVT 真實伺服器連接指南

## 📋 概述

當前 RVT 分析頁面顯示的是**假的測試數據**（由 `create_jenkins_test_data.py` 生成）。本指南說明如何連接真實的 Jenkins/RVT 伺服器。

---

## 🎯 連接真實伺服器的方法

### 方法 1：使用管理腳本（推薦）

```bash
# 進入 Django 容器
docker exec -it nt-django bash

# 執行管理腳本
python setup_real_jenkins_server.py
```

**操作流程：**
1. 選擇選項 2（清除測試數據並添加真實伺服器）
2. 輸入 Jenkins 伺服器資訊：
   - 伺服器名稱：例如 `RVT Production`
   - URL：例如 `http://10.252.170.188:8080`
   - 用戶名：您的 Jenkins 用戶名
   - API Token：從 Jenkins 獲取的 API Token
3. 訪問 http://localhost/rvt-analytics
4. 點擊「同步所有伺服器」按鈕

---

### 方法 2：通過 Django Admin 手動添加

1. **訪問 Django Admin**：
   ```
   http://localhost/admin/api/jenkinsserver/
   ```

2. **登入**（使用您的 Admin 帳號）

3. **點擊「Add Jenkins Server」**

4. **填寫伺服器資訊**：
   - **Name**: 伺服器名稱（例如：RVT Production）
   - **URL**: Jenkins 完整 URL（例如：http://10.252.170.188:8080）
   - **Username**: Jenkins 用戶名（用於 API 認證）
   - **API Token**: Jenkins API Token（在 Jenkins 用戶設置中生成）
   - **Description**: 伺服器描述（可選）
   - **Status**: 選擇 `online`
   - **Is Active**: 勾選

5. **保存後**，到 RVT 分析頁面點擊「同步所有伺服器」

---

### 方法 3：通過 API 添加

```bash
# 添加真實伺服器
curl -X POST http://localhost/api/jenkins-servers/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "name": "RVT Production",
    "url": "http://10.252.170.188:8080",
    "username": "your_jenkins_username",
    "api_token": "your_jenkins_api_token",
    "description": "生產環境 RVT 伺服器",
    "status": "online",
    "is_active": true
  }'
```

---

## 🔑 獲取 Jenkins API Token

1. **登入 Jenkins**：
   ```
   http://your-jenkins-server:8080
   ```

2. **進入用戶設置**：
   - 點擊右上角用戶名
   - 選擇「Configure」或「設定」

3. **生成 API Token**：
   - 找到「API Token」區塊
   - 點擊「Add new Token」
   - 輸入 Token 名稱（例如：Network Toolbox）
   - 點擊「Generate」
   - **複製並保存 Token**（只會顯示一次）

---

## 📊 同步 Jobs 和 Builds

### 自動同步（推薦）

1. 訪問 RVT 分析頁面：http://localhost/rvt-analytics
2. 點擊右上角「同步所有伺服器」按鈕
3. 系統會自動：
   - 測試連接
   - 獲取所有 Jobs
   - 獲取每個 Job 的最近 Builds

### 手動同步（通過 API）

```bash
# 測試連接
curl -X POST http://localhost/api/jenkins-servers/{SERVER_ID}/test_connection/

# 同步 Jobs
curl -X POST http://localhost/api/jenkins-servers/{SERVER_ID}/sync_jobs/

# 同步所有伺服器
curl -X POST http://localhost/api/jenkins-servers/sync_all/
```

---

## 🗑️ 清除測試數據

### 方法 1：使用管理腳本

```bash
docker exec -it nt-django python setup_real_jenkins_server.py
# 選擇選項 1
```

### 方法 2：使用 Django Shell

```bash
docker exec -it nt-django python manage.py shell
```

```python
from api.models import JenkinsServer, JenkinsJob, JenkinsBuild

# 查看當前數據
print(f"Servers: {JenkinsServer.objects.count()}")
print(f"Jobs: {JenkinsJob.objects.count()}")
print(f"Builds: {JenkinsBuild.objects.count()}")

# 清除所有數據
JenkinsBuild.objects.all().delete()
JenkinsJob.objects.all().delete()
JenkinsServer.objects.all().delete()

print("✅ 已清除所有數據")
```

### 方法 3：使用 SQL

```bash
docker exec -it nt-django python manage.py dbshell
```

```sql
-- 查看數據
SELECT COUNT(*) FROM api_jenkinsserver;
SELECT COUNT(*) FROM api_jenkinsjob;
SELECT COUNT(*) FROM api_jenkinsbuild;

-- 清除數據（注意：會級聯刪除）
DELETE FROM api_jenkinsbuild;
DELETE FROM api_jenkinsjob;
DELETE FROM api_jenkinsserver;
```

---

## ⚙️ Jenkins API 配置要求

### 必要設置

1. **Jenkins 版本**：2.x 以上
2. **API 認證**：啟用 API Token 認證
3. **CORS**：如需從瀏覽器直接訪問，需配置 CORS
4. **網路連通性**：確保 Django 容器可以訪問 Jenkins URL

### Jenkins 插件需求（可選）

- **Ansible Plugin**：如果使用 Ansible 自動化
- **Blue Ocean**：更好的 Pipeline 視覺化
- **REST API Plugin**：增強的 API 支持

---

## 🔍 故障排查

### 連接失敗

**症狀**：點擊「同步所有伺服器」後顯示連接失敗

**檢查步驟**：

1. **測試網路連通性**：
   ```bash
   docker exec nt-django curl -I http://10.252.170.188:8080
   ```

2. **檢查認證**：
   ```bash
   docker exec nt-django curl -u username:api_token http://10.252.170.188:8080/api/json
   ```

3. **查看 Django 日誌**：
   ```bash
   docker compose logs django | tail -50
   ```

4. **檢查防火牆**：確保 Jenkins 端口（通常 8080）開放

### 認證失敗

**症狀**：返回 401 或 403 錯誤

**解決方案**：
- 確認 API Token 正確（重新生成並測試）
- 確認用戶名正確
- 檢查 Jenkins 用戶權限（需要讀取權限）

### 數據未同步

**症狀**：同步後頁面仍然沒有數據

**檢查步驟**：

1. **查看數據庫**：
   ```bash
   docker exec nt-django python manage.py shell -c "
   from api.models import JenkinsJob, JenkinsBuild
   print(f'Jobs: {JenkinsJob.objects.count()}')
   print(f'Builds: {JenkinsBuild.objects.count()}')
   "
   ```

2. **查看 API 響應**：
   ```bash
   curl http://localhost/api/jenkins-jobs/
   ```

3. **檢查同步日誌**：
   ```bash
   tail -f logs/django.log | grep -i jenkins
   ```

---

## 📝 範例：完整設置流程

```bash
# 1. 清除測試數據
docker exec -it nt-django python setup_real_jenkins_server.py
# 選擇選項 1

# 2. 添加真實伺服器（通過 Django Admin）
# 訪問 http://localhost/admin/api/jenkinsserver/
# 填寫：
#   - Name: RVT Production
#   - URL: http://10.252.170.188:8080
#   - Username: admin
#   - API Token: 11e234567890abcdef1234567890abcd
#   - Status: online

# 3. 測試連接
curl -X POST http://localhost/api/jenkins-servers/1/test_connection/

# 4. 同步 Jobs
curl -X POST http://localhost/api/jenkins-servers/1/sync_jobs/

# 5. 驗證數據
docker exec nt-django python manage.py shell -c "
from api.models import JenkinsJob, JenkinsBuild
print(f'✅ Jobs: {JenkinsJob.objects.count()}')
print(f'✅ Builds: {JenkinsBuild.objects.count()}')
"

# 6. 訪問頁面
# http://localhost/rvt-analytics
```

---

## 🔄 定期同步

### 手動同步
- 點擊頁面上的「同步所有伺服器」按鈕
- 或使用 API 端點定期調用

### 自動同步（計劃任務）
可以使用 Celery 或 Cron 設置定期同步：

```python
# backend/api/tasks.py
from celery import shared_task
from .models import JenkinsServer

@shared_task
def sync_all_jenkins_servers():
    """定期同步所有 Jenkins 伺服器"""
    for server in JenkinsServer.objects.filter(is_active=True):
        server.sync_jobs()  # 需要實現此方法
```

---

## 📚 相關文檔

- **Jenkins REST API**: https://www.jenkins.io/doc/book/using/remote-access-api/
- **Python Jenkins Library**: https://python-jenkins.readthedocs.io/
- **Django Models**: `/backend/api/models.py`
- **API Views**: `/backend/api/views.py`
- **Frontend Page**: `/frontend/src/pages/RVTAnalysisPage.js`

---

## 🆘 需要幫助？

如果遇到問題，請查看：
1. Django 日誌：`tail -f logs/django.log`
2. Django 錯誤日誌：`tail -f logs/django_error.log`
3. API 訪問日誌：`tail -f logs/api_access.log`

或聯繫系統管理員。
