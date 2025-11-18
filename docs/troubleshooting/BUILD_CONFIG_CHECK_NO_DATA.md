# Build 配置檢查無資料問題排查

## 🔴 問題現象

點擊「配置檢查」按鈕後，顯示：
- 無法載入配置
- 檢查項目無資料
- 錯誤訊息：「Failed to load build」或「No config data」

## ⚠️ SAF7522_K05 Build #16 案例分析

### 問題診斷結果

**Build #16 未被自動下載的原因：**

```
Build 資訊：
  - Build 時間：2025-11-02 18:26:48
  - Build 結果：SUCCESS
  - Is Building：False
  - Artifacts 已存儲：False

定時任務配置：
  - 任務名稱：auto-store-jenkins-artifacts-hourly
  - 執行頻率：每 30 分鐘一次
  - 時間範圍：最近 7 天（168 小時）
  - 最小年齡：至少 30 分鐘前完成
  - 任務狀態：已啟用 ✅
  - 最後執行：2025-11-17 20:30:00
  - 總執行次數：323 次

問題根因：
  ❌ Build 時間（2025-11-02）超出 7 天範圍
  
  定時任務時間範圍：
    2025-11-10 ~ 2025-11-17 (最近 7 天)
  
  Build #16 時間：
    2025-11-02 (16 天前) ← 超出範圍！
```

### 結論

**定時任務正常運作**，但 Build #16 因為**太舊**（超過 7 天）而未被自動下載。

定時任務的設計是為了：
- 🎯 **優先處理最近的 Builds**（最近 7 天）
- 💾 **節省存儲空間**（不無限制下載所有歷史 Builds）
- ⚡ **提升效率**（每次最多處理 50 個 Build）

## 🔍 問題診斷

### 檢查 Build 是否有 Artifacts

**原因**：配置檢查需要從 Ansible Inventory 讀取配置，而 Inventory 文件存儲在 artifacts 中。

**診斷步驟**：

1. 在 RVT 分析頁面查看 Build 記錄
2. 檢查該 Build 是否有「日誌」按鈕
3. 如果沒有「日誌」按鈕，表示 artifacts 尚未存儲

### 常見原因

| 原因 | 說明 | 影響 |
|-----|------|------|
| Artifacts 未存儲 | Build 完成後，artifacts 尚未同步到 NAS | 無法查看配置 |
| Inventory 文件缺失 | artifacts 中沒有 `inventory/hosts` 文件 | 無法讀取配置 |
| Build 未完成 | Build 正在執行中或被中斷 | artifacts 尚未生成 |
| Jenkins Job 配置問題 | Job 沒有啟用「Archive artifacts」 | 不會產生 artifacts |

## ✅ 解決方案

### 方案 1：等待 Artifacts 同步（推薦）

如果 Build 已完成但 artifacts 尚未同步：

1. **自動同步**（如果啟用了定時任務）
   - 系統會定期自動同步 artifacts
   - 等待下次同步週期（通常 5-30 分鐘）

2. **手動同步**
   ```bash
   # 在 Django 容器中執行
   docker exec nt-django python manage.py shell
   
   # 執行同步腳本
   from api.tasks import sync_jenkins_artifacts
   sync_jenkins_artifacts.delay()  # 使用 Celery
   # 或
   sync_jenkins_artifacts()  # 直接執行
   ```

3. **針對特定 Build 同步**
   - 在 Build 詳情頁面點擊「存儲工作空間」按鈕
   - 系統會自動同步該 Build 的 artifacts

### 方案 2：檢查 Jenkins Job 配置

確保 Jenkins Job 配置正確：

1. 登入 Jenkins
2. 進入 Job 配置頁面
3. 檢查「Post-build Actions」
4. 確認有「Archive the artifacts」選項
5. 設定要保存的文件模式：
   ```
   artifacts/**/*
   inventory/**/*
   ```

### 方案 3：使用資料庫配置（備用方案）

如果 Ansible Inventory 不可用，系統會嘗試使用資料庫中的配置：

1. 確認 Build 的 `parameters` 或 `ansible_config` 欄位有資料
2. 這些資料可能在 Build 創建時從 Jenkins API 獲取
3. 配置來源會顯示為「database」而非「ansible_inventory」

## 🛠️ 開發者診斷工具

### 1. 檢查 Build Artifacts 狀態

```bash
docker exec nt-django python manage.py shell << 'EOF'
from api.models import JenkinsBuild

# 查詢特定 Build
build_id = 16  # 替換為實際 Build ID
build = JenkinsBuild.objects.get(id=build_id)

print(f"Build #{build.build_number}")
print(f"Job: {build.job.name}")
print(f"Artifacts Stored: {build.artifacts_stored_at}")
print(f"Artifacts Path: {build.artifacts_path}")
print(f"Has Parameters: {bool(build.parameters)}")
print(f"Has Ansible Config: {bool(build.ansible_config)}")

# 檢查 artifacts 路徑
if build.artifacts_path:
    import os
    inventory_path = os.path.join(build.artifacts_path, 'inventory', 'hosts')
    print(f"\nInventory Path: {inventory_path}")
    print(f"Inventory Exists: {os.path.exists(inventory_path)}")
else:
    print("\n⚠️ No artifacts path")
EOF
```

### 2. 手動測試配置讀取

```bash
docker exec nt-django python manage.py shell << 'EOF'
from library.services.build_config_validator import BuildConfigValidator

build_id = 16  # 替換為實際 Build ID

validator = BuildConfigValidator(build_id)
validator._load_build()

print(f"\n=== Build Info ===")
print(f"Build ID: {validator.build.id}")
print(f"Job: {validator.build.job.name if validator.build.job else 'N/A'}")

# 嘗試從 Ansible API 獲取配置
print(f"\n=== Trying Ansible API ===")
config = validator._fetch_config_from_ansible_api()
if config:
    print(f"✅ Got config from Ansible API: {len(config)} keys")
else:
    print(f"❌ Failed to get config from Ansible API")

# 嘗試從資料庫獲取配置
print(f"\n=== Database Config ===")
if validator.build.parameters:
    print(f"Parameters: {len(validator.build.parameters)} keys")
else:
    print(f"No parameters in database")

if validator.build.ansible_config:
    print(f"Ansible Config: {len(validator.build.ansible_config)} keys")
else:
    print(f"No ansible_config in database")
EOF
```

### 3. 查看 Job 的 Artifacts 狀態

```bash
docker exec nt-django python manage.py shell << 'EOF'
from api.models import JenkinsJob, JenkinsBuild

job_name = 'SAF7522_K05'  # 替換為實際 Job 名稱
job = JenkinsJob.objects.get(name=job_name)

print(f"Job: {job.name}")
print(f"Total Builds: {job.builds.count()}")

# 統計 artifacts 狀態
builds_with_artifacts = job.builds.filter(artifacts_stored_at__isnull=False).count()
builds_without_artifacts = job.builds.filter(artifacts_stored_at__isnull=True).count()

print(f"\n=== Artifacts Status ===")
print(f"✅ With Artifacts: {builds_with_artifacts}")
print(f"❌ Without Artifacts: {builds_without_artifacts}")

# 列出最近的 Builds
print(f"\n=== Recent Builds ===")
for build in job.builds.order_by('-build_number')[:5]:
    status = "✅" if build.artifacts_stored_at else "❌"
    print(f"{status} Build #{build.build_number}: {build.result} - {build.artifacts_stored_at}")
EOF
```

## 📊 監控和預防

### 自動檢測缺失 Artifacts

在系統中添加監控腳本，定期檢查：

```python
# scripts/check_missing_artifacts.py
from api.models import JenkinsBuild
from datetime import datetime, timedelta

# 查找最近 7 天內完成但沒有 artifacts 的 Builds
recent_date = datetime.now() - timedelta(days=7)
builds_missing_artifacts = JenkinsBuild.objects.filter(
    timestamp__gte=recent_date,
    result__in=['SUCCESS', 'FAILURE', 'UNSTABLE'],
    artifacts_stored_at__isnull=True
)

print(f"Found {builds_missing_artifacts.count()} builds without artifacts")
for build in builds_missing_artifacts[:10]:
    print(f"  - {build.job.name} #{build.build_number}: {build.result}")
```

### 自動觸發 Artifacts 同步

在 Celery 定時任務中添加：

```python
@periodic_task(run_every=crontab(minute='*/30'))  # 每 30 分鐘執行一次
def auto_sync_missing_artifacts():
    """自動同步缺失的 artifacts"""
    from api.models import JenkinsBuild
    from datetime import datetime, timedelta
    
    # 查找最近完成但沒有 artifacts 的 Builds
    recent_date = datetime.now() - timedelta(hours=24)
    builds = JenkinsBuild.objects.filter(
        timestamp__gte=recent_date,
        result__in=['SUCCESS', 'FAILURE'],
        artifacts_stored_at__isnull=True
    )[:10]  # 限制每次處理 10 個
    
    for build in builds:
        try:
            # 調用同步 API
            sync_build_artifacts(build.id)
            logger.info(f"Synced artifacts for Build {build.id}")
        except Exception as e:
            logger.error(f"Failed to sync Build {build.id}: {e}")
```

## 🎯 最佳實踐

1. **Jenkins 配置**
   - 確保所有 Job 都啟用「Archive artifacts」
   - 設定合理的 artifacts 保留策略

2. **自動同步**
   - 啟用 Celery 定時任務自動同步 artifacts
   - 設定適當的同步頻率（建議 15-30 分鐘）

3. **手動同步**
   - 對於重要的 Builds，完成後立即手動同步
   - 使用「存儲工作空間」按鈕

4. **監控**
   - 定期檢查缺失 artifacts 的 Builds
   - 設定告警通知

## 🔗 相關文檔

- [Artifacts 同步機制](../features/jenkins-artifacts/SYNC_MECHANISM.md)
- [配置檢查功能](../features/build-config-validation/README.md)
- [Ansible Inventory 集成](../features/ansible-inventory/README.md)

---

**更新日期**：2025-11-18  
**維護者**：Network Toolbox Team
