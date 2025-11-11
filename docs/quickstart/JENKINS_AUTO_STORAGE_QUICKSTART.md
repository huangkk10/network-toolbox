# Jenkins Builds 自動存儲 - 快速啟動指南

## 🚀 快速開始（3 步驟）

### 步驟 1：重啟服務

```bash
# 重啟所有相關服務
docker compose restart django celery_worker celery_beat
```

### 步驟 2：執行測試

```bash
# 執行測試腳本驗證功能
./test_jenkins_auto_storage.sh
```

### 步驟 3：監控運行

```bash
# 訪問 Celery Flower 監控界面
open http://localhost:5555
```

---

## 📖 詳細說明

### 自動存儲機制

**執行頻率**：每 30 分鐘自動執行一次

**執行邏輯**：
1. 掃描資料庫中未存儲的 Jenkins Builds
2. 過濾條件：SUCCESS、FAILURE、UNSTABLE 結果
3. 每次最多處理 20 個 Builds
4. 異步存儲到 NAS

**首次執行時間**：服務重啟後的整點或半點
- 例如：11:00, 11:30, 12:00, 12:30...

---

## 🔧 手動操作

### 查看未存儲的 Builds

```bash
docker exec nt-django python manage.py shell -c "
from api.models import JenkinsBuild
count = JenkinsBuild.objects.filter(is_workspace_stored=False, is_building=False).count()
print(f'未存儲的 Builds：{count} 個')
"
```

### 手動批量存儲（演練模式）

```bash
# 查看將要處理的前 10 個 Builds
docker exec nt-django python manage.py store_jenkins_builds --limit 10 --dry-run
```

### 手動批量存儲（實際執行）

```bash
# 異步模式（推薦，使用 Celery）
docker exec nt-django python manage.py store_jenkins_builds --limit 20

# 同步模式（直接執行，適合測試）
docker exec nt-django python manage.py store_jenkins_builds --limit 5 --sync
```

### 手動觸發一次自動掃描

```bash
docker exec nt-django python manage.py shell -c "
from api.tasks import auto_store_jenkins_builds_task
task = auto_store_jenkins_builds_task.delay(limit=10)
print(f'任務已創建：{task.id}')
print(f'查看狀態：http://localhost:5555/task/{task.id}')
"
```

---

## 📊 監控和查詢

### 查看存儲統計

```bash
docker exec nt-django python manage.py shell -c "
from api.models import JenkinsBuild

total = JenkinsBuild.objects.count()
stored = JenkinsBuild.objects.filter(is_workspace_stored=True).count()
not_stored = JenkinsBuild.objects.filter(is_workspace_stored=False, is_building=False).count()

print(f'總 Builds：{total}')
print(f'已存儲：{stored} ({stored/total*100:.1f}%)')
print(f'未存儲：{not_stored}')
"
```

### 查看最近存儲的 Builds

```bash
docker exec nt-django python manage.py shell -c "
from api.models import JenkinsBuild

builds = JenkinsBuild.objects.filter(
    is_workspace_stored=True
).select_related('job', 'job__server').order_by('-workspace_stored_at')[:5]

print('最近存儲的 5 個 Builds：')
for b in builds:
    size_mb = b.workspace_size / 1024 / 1024 if b.workspace_size else 0
    print(f'  {b.job.name} #{b.build_number} - {size_mb:.2f} MB')
"
```

### 查看 NAS 存儲使用情況

```bash
# 查看總存儲大小
docker exec nt-django du -sh /mnt/mdt/Team/PQ1-3/tool/jenkins_test_storage/

# 查看各伺服器存儲大小
docker exec nt-django du -sh /mnt/mdt/Team/PQ1-3/tool/jenkins_test_storage/*/
```

---

## ⚙️ 配置調整

### 修改存儲策略

編輯文件：`backend/network_toolbox/settings.py`

```python
JENKINS_STORAGE_POLICY = {
    'auto_store': True,  # 改為 False 可停用自動存儲
    'store_results': ['SUCCESS', 'FAILURE', 'UNSTABLE'],  # 只存儲這些結果
    'batch_size': 20,  # 每次處理的 Builds 數量
}
```

**修改後需要重啟**：
```bash
docker compose restart django celery_worker celery_beat
```

### 修改掃描頻率

編輯文件：`backend/network_toolbox/celery.py`

```python
'auto-store-jenkins-builds-every-30-minutes': {
    'schedule': crontab(minute='*/15'),  # 改為每 15 分鐘
```

**修改後需要重啟**：
```bash
docker compose restart celery_beat
```

---

## 🔍 故障排查

### 問題：定時任務沒有執行

**檢查 Celery Beat 狀態**：
```bash
docker compose ps celery_beat
docker compose logs celery_beat --tail 50
```

**解決方法**：
```bash
docker compose restart celery_beat
```

### 問題：任務執行失敗

**查看任務詳情**：
- 訪問 http://localhost:5555/tasks
- 查看失敗的任務詳情

**常見原因**：
- NAS 未掛載或無權限
- Jenkins API Token 過期
- Workspace 不存在

**查看 Worker 日誌**：
```bash
docker compose logs celery_worker --tail 100
```

### 問題：存儲速度慢

**原因**：
- NAS 網路速度慢
- Workspace 文件太大
- 同時處理太多任務

**解決方法**：
1. 減少 batch_size（改為 10）
2. 延長掃描間隔（改為 60 分鐘）
3. 添加 Workspace 大小限制

---

## 📚 更多文檔

- **完整實施報告**：`docs/features/jenkins-auto-storage/IMPLEMENTATION_REPORT.md`
- **NAS 存儲分析**：`docs/analysis/NAS_JENKINS_STORAGE_ANALYSIS.md`
- **測試腳本**：`test_jenkins_auto_storage.sh`

---

## 💡 提示

1. **首次使用建議**：
   - 先執行演練模式了解情況
   - 從小批量開始（--limit 10）
   - 監控 NAS 空間使用

2. **長期運行建議**：
   - 定期檢查存儲統計
   - 監控 Celery 任務狀態
   - 關注 NAS 磁碟空間

3. **性能優化**：
   - 根據實際情況調整 batch_size
   - 只存儲重要的 Builds（如失敗的）
   - 實施保留期限清理策略

---

**最後更新**：2025-11-10
