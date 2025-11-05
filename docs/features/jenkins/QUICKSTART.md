# Jenkins 整合功能 - 快速開始指南

**狀態**: Phase 1-4 已完成，可以進行基本測試 ✅

---

## 📦 已完成的功能

### 1. Jenkins REST API 客戶端（JenkinsClient）

**使用範例**：

```python
from library.services.jenkins_client import JenkinsClient

# 初始化客戶端
client = JenkinsClient(
    base_url='http://192.168.1.100:8080',
    username='admin',
    api_token='your_api_token'
)

# 測試連接
if client.test_connection():
    print("✅ Jenkins 連接成功")

# 獲取伺服器資訊
server_info = client.get_server_info()
print(f"Jenkins 版本: {server_info.get('version', 'N/A')}")

# 列出所有 Job
jobs = client.list_jobs()
for job in jobs:
    print(f"Job: {job['name']}, URL: {job['url']}")

# 獲取 Build 資訊
build_info = client.get_build_info('MyJob', 123)
print(f"Build #123 結果: {build_info['result']}")

# 獲取控制台日誌
console_log = client.get_console_log('MyJob', 123)
print(f"日誌長度: {len(console_log)} 字符")

# 提取 Ansible 配置
ansible_config = client.extract_ansible_config(console_log)
print(f"Ansible 配置: {ansible_config}")

# 關閉連接
client.close()
```

---

### 2. NAS 存儲服務（JenkinsStorageService）

**使用範例**：

```python
from library.services.jenkins_storage_service import JenkinsStorageService

# 初始化服務
storage = JenkinsStorageService()

# 讀取配置文件
config = storage.read_config_file(
    jenkins_ip='192.168.1.100',
    job_name='MyJob',
    build_number=123
)
print(f"配置內容: {config}")

# 讀取日誌文件（最後 100 行）
log = storage.read_log_file(
    jenkins_ip='192.168.1.100',
    job_name='MyJob',
    build_number=123,
    log_type='console',
    max_lines=100
)
print(f"日誌內容（最後 100 行）: {log}")

# 列出所有 Build
builds = storage.list_builds(
    jenkins_ip='192.168.1.100',
    job_name='MyJob'
)
print(f"Build 列表: {builds}")

# 檢查文件是否存在
file_status = storage.check_build_files_exist(
    jenkins_ip='192.168.1.100',
    job_name='MyJob',
    build_number=123
)
print(f"文件存在狀態: {file_status}")
```

---

### 3. 數據聚合（資料庫 + 文件系統）

**使用範例**：

```python
from api.models import JenkinsBuild
from library.services.jenkins_storage_service import JenkinsStorageService

# 獲取 Build 對象
build = JenkinsBuild.objects.get(
    job__name='MyJob',
    build_number=123
)

# 聚合完整數據
storage = JenkinsStorageService()
full_data = storage.aggregate_build_data(
    build_obj=build,
    include_config=True,      # 包含配置文件
    include_log=True,         # 包含日誌
    log_max_lines=200         # 最多 200 行日誌
)

print(f"Build 編號: {full_data['build_number']}")
print(f"結果: {full_data['result']}")
print(f"持續時間: {full_data['duration']} 秒")
print(f"參數: {full_data['parameters']}")
print(f"Ansible 配置（資料庫）: {full_data['ansible_config_db']}")
print(f"Ansible 配置（文件）: {full_data['ansible_config_file']}")
print(f"控制台日誌: {full_data['console_log'][:500]}...")  # 前 500 字符
```

---

## 🗄️ Django 模型使用

### 創建 Jenkins 伺服器

```python
from api.models import JenkinsServer

server = JenkinsServer.objects.create(
    name='Production Jenkins',
    url='http://192.168.1.100:8080',
    ip_address='192.168.1.100',
    username='admin',
    api_token='your_api_token',
    status='online',
    is_active=True
)
print(f"✅ 伺服器創建成功: {server.name}")
```

### 創建 Jenkins Job

```python
from api.models import JenkinsJob

job = JenkinsJob.objects.create(
    server=server,
    name='MyJob',
    full_name='MyJob',
    url='http://192.168.1.100:8080/job/MyJob/',
    is_buildable=True,
    is_disabled=False
)
print(f"✅ Job 創建成功: {job.name}")
```

### 創建 Jenkins Build

```python
from api.models import JenkinsBuild
from datetime import datetime

build = JenkinsBuild.objects.create(
    job=job,
    build_number=123,
    display_name='#123',
    url='http://192.168.1.100:8080/job/MyJob/123/',
    result='SUCCESS',
    duration=120000,  # ms
    parameters={'branch': 'main', 'env': 'prod'},
    ansible_config={'hosts': ['server1', 'server2']},
    build_timestamp=datetime.now()
)
print(f"✅ Build 創建成功: {build.display_name}")
```

---

## 🧪 測試腳本

創建 `backend/test_jenkins_integration.py` 測試文件：

```python
#!/usr/bin/env python
"""
Jenkins 整合功能測試腳本
"""

import os
import django

# Django 設置
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'network_toolbox.settings')
django.setup()

from library.services.jenkins_client import JenkinsClient
from library.services.jenkins_storage_service import JenkinsStorageService
from api.models import JenkinsServer, JenkinsJob, JenkinsBuild

def test_jenkins_client():
    """測試 Jenkins 客戶端"""
    print("\n=== 測試 Jenkins 客戶端 ===")
    
    client = JenkinsClient(
        base_url='http://192.168.1.100:8080',
        username='admin',
        api_token='your_token'
    )
    
    # 測試連接
    if client.test_connection():
        print("✅ 連接成功")
    else:
        print("❌ 連接失敗")
        return
    
    # 列出 Job
    jobs = client.list_jobs()
    print(f"✅ 獲取到 {len(jobs)} 個 Job")
    
    client.close()

def test_storage_service():
    """測試存儲服務"""
    print("\n=== 測試存儲服務 ===")
    
    storage = JenkinsStorageService()
    
    # 列出 Job
    jobs = storage.list_jobs('192.168.1.100')
    print(f"✅ NAS 上有 {len(jobs)} 個 Job")
    
    if jobs:
        # 列出第一個 Job 的 Build
        builds = storage.list_builds('192.168.1.100', jobs[0])
        print(f"✅ Job '{jobs[0]}' 有 {len(builds)} 個 Build")

def test_data_aggregation():
    """測試數據聚合"""
    print("\n=== 測試數據聚合 ===")
    
    # 查詢最新的 Build
    build = JenkinsBuild.objects.first()
    
    if not build:
        print("❌ 資料庫中沒有 Build 記錄")
        return
    
    storage = JenkinsStorageService()
    full_data = storage.aggregate_build_data(
        build_obj=build,
        include_config=True,
        include_log=False  # 不包含日誌（避免太大）
    )
    
    print(f"✅ 聚合數據成功:")
    print(f"  - Build 編號: {full_data['build_number']}")
    print(f"  - 結果: {full_data['result']}")
    print(f"  - 參數數量: {len(full_data['parameters'])}")
    print(f"  - 配置文件: {'存在' if full_data['ansible_config_file'] else '不存在'}")

if __name__ == '__main__':
    print("🚀 開始測試 Jenkins 整合功能...")
    
    test_jenkins_client()
    test_storage_service()
    test_data_aggregation()
    
    print("\n✅ 測試完成！")
```

**執行測試**：

```bash
docker exec nt-django python backend/test_jenkins_integration.py
```

---

## 🔧 配置檢查

### 1. 檢查 PostgreSQL 連接

```bash
docker exec nt-django python manage.py dbshell
```

### 2. 檢查 Redis 連接

```bash
docker exec nt-django python -c "from django.core.cache import cache; print('Redis PING:', cache.get('test') or 'Connected')"
```

### 3. 檢查 NAS 掛載

```bash
# 如果 NAS 已掛載，取消 docker-compose.yml 中的註釋
docker exec nt-django ls -la /mnt/mdt/
```

### 4. 檢查資料庫表

```bash
docker exec nt-django python manage.py shell -c "from api.models import JenkinsServer; print(JenkinsServer.objects.count())"
```

---

## 📌 下一步

Phase 5-6 完成後，您將可以：

1. **通過 REST API 管理 Jenkins 資料**：
   - `GET /api/jenkins-servers/` - 列出所有伺服器
   - `GET /api/jenkins-jobs/` - 列出所有 Job
   - `GET /api/jenkins-builds/` - 列出所有 Build
   - `GET /api/jenkins-builds/{id}/logs/` - 獲取日誌
   - `GET /api/jenkins-builds/{id}/config/` - 獲取配置

2. **使用前端界面**：
   - 伺服器管理頁面
   - Job 列表頁面
   - Build 詳情頁面
   - 日誌查看器

---

## 💡 提示

- **NAS 掛載**：確保 `/mnt/mdt` 已掛載，並取消 docker-compose.yml 中的註釋
- **API Token**：從 Jenkins 獲取（User → Configure → API Token）
- **權限**：確保 Jenkins 用戶有足夠的權限訪問 API

---

**有問題？** 查看日誌：
```bash
docker compose logs django -f
```
