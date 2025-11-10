# Jenkins Builds 自動存儲 - 快速啟動指南

## 🚀 5 分鐘快速啟動

### 步驟 1：重啟服務（必須）

```bash
cd /home/owner/Codes/network-toolbox

# 重啟所有相關服務
docker compose restart django celery_worker celery_beat

# 等待服務啟動（約 30 秒）
sleep 30

# 確認服務運行中
docker compose ps | grep -E "django|celery"
```

**預期輸出**：
```
django          Up
celery_worker   Up
celery_beat     Up
```

---

### 步驟 2：執行測試驗證

```bash
# 執行完整測試腳本
./test_jenkins_auto_storage.sh
```

**測試項目**：
- ✅ 資料庫狀態檢查
- ✅ Celery 任務註冊
- ✅ 定時排程配置
- ✅ 存儲策略配置
- ✅ NAS 路徑檢查

---

### 步驟 3：監控第一次自動執行

**方式 A：訪問 Celery Flower**
```bash
# 在瀏覽器中打開
http://localhost:5555

# 查找任務：auto-store-jenkins-builds-every-30-minutes
# 等待下一個 30 分鐘（例如：14:00, 14:30, 15:00...）
```

**方式 B：查看日誌**
```bash
# 實時查看 Django 日誌
tail -f logs/django.log | grep -i "jenkins.*store"

# 查看 Celery Beat 日誌
docker compose logs -f celery_beat | grep -i jenkins
```

---

## 📊 快速使用示例

### 1. 手動觸發少量存儲（推薦新手）

```bash
# 演練模式：查看將要處理的 5 個 Builds
docker exec nt-django python manage.py store_jenkins_builds --limit 5 --dry-run

# 同步模式：直接存儲（實時查看進度）
docker exec nt-django python manage.py store_jenkins_builds --limit 5 --sync
```

**適用場景**：
- ✅ 第一次使用，想看看效果
- ✅ 測試功能是否正常
- ✅ NAS 速度較慢，想控制進度

---

### 2. 批量異步存儲（推薦生產環境）

```bash
# 異步模式：創建 20 個 Celery 任務
docker exec nt-django python manage.py store_jenkins_builds --limit 20

# 在 Celery Flower 中監控進度
# http://localhost:5555/tasks
```

**適用場景**：
- ✅ 生產環境使用
- ✅ 大量 Builds 需要存儲
- ✅ 不阻塞終端，後台執行

---

### 3. 只存儲失敗的 Builds

```bash
# 只存儲失敗的 Builds（用於快速問題診斷）
docker exec nt-django python manage.py store_jenkins_builds \
    --results FAILURE \
    --limit 10 \
    --sync
```

**適用場景**：
- ✅ 診斷構建失敗原因
- ✅ 保留失敗日誌
- ✅ 節省 NAS 空間

---

### 4. 存儲特定 Job 的 Builds

```bash
# 只存儲某個 Job 的 Builds
docker exec nt-django python manage.py store_jenkins_builds \
    --job-name "SAF3202_KVM03" \
    --sync
```

**適用場景**：
- ✅ 特定項目需要完整記錄
- ✅ 測試單個 Job 的存儲功能

---

## 🔧 常用操作

### 查看存儲統計

```bash
docker exec nt-django python manage.py shell << 'EOF'
from api.models import JenkinsBuild

total = JenkinsBuild.objects.count()
stored = JenkinsBuild.objects.filter(is_workspace_stored=True).count()
not_stored = JenkinsBuild.objects.filter(is_workspace_stored=False, is_building=False).count()

print(f"📊 Jenkins Builds 存儲統計")
print(f"  總數：{total}")
print(f"  ✅ 已存儲：{stored} ({stored/total*100:.1f}%)")
print(f"  ⏳ 待存儲：{not_stored}")
print(f"  🔨 正在構建：{total - stored - not_stored}")
EOF
```

### 查看 NAS 使用量

```bash
# 查看總使用量
docker exec nt-django du -sh /mnt/mdt/Team/PQ1-3/tool/jenkins_test_storage/

# 查看各伺服器使用量
docker exec nt-django du -sh /mnt/mdt/Team/PQ1-3/tool/jenkins_test_storage/*/

# 查看最大的 10 個 Job 資料夾
docker exec nt-django du -sh /mnt/mdt/Team/PQ1-3/tool/jenkins_test_storage/*/*/ | sort -h | tail -10
```

### 臨時停用自動存儲

```python
# 編輯 backend/network_toolbox/settings.py
JENKINS_STORAGE_POLICY = {
    'auto_store': False,  # 改為 False
    # ... 其他配置保持不變
}
```

```bash
# 重啟服務
docker compose restart django celery_worker celery_beat
```

### 調整掃描頻率

```python
# 編輯 backend/network_toolbox/celery.py
'auto-store-jenkins-builds-every-30-minutes': {
    'schedule': crontab(minute='*/15'),  # 從 30 改為 15 分鐘
```

```bash
# 重啟 Celery Beat
docker compose restart celery_beat
```

---

## 📈 預期結果時間線

### 啟動後 30 分鐘
- ✅ 第一次自動掃描執行
- ✅ 創建最多 20 個存儲任務
- 📊 查看 Celery Flower 確認任務執行

### 啟動後 1 小時
- ✅ 第二次掃描執行
- ✅ 約 40 個 Builds 開始存儲或已完成
- 📊 存儲比例開始提升

### 啟動後 1 天
- ✅ 48 次掃描（每 30 分鐘一次）
- ✅ 最多處理 960 個 Builds（理論值）
- 📊 大部分待存儲的 Builds 已處理

### 穩定運行後
- ✅ 新 Builds 在 30 分鐘內自動存儲
- ✅ 存儲比例保持 90%+
- 📊 無需人工干預

---

## ⚠️ 注意事項

### 1. NAS 空間監控

```bash
# 每天檢查一次 NAS 使用量
docker exec nt-django df -h /mnt/mdt | grep mdt
```

**建議**：
- 當使用率超過 80% 時，考慮清理舊資料
- 或調整存儲策略（只存儲失敗的 Builds）

### 2. 網路連接問題

如果看到大量任務失敗：
- 檢查 Jenkins 伺服器是否在線
- 檢查 API Token 是否過期
- 檢查 NAS 是否正常掛載

### 3. 大量歷史 Builds

如果有大量歷史 Builds 需要回填：
```bash
# 謹慎使用 --backfill 參數
docker exec nt-django python manage.py store_jenkins_builds \
    --backfill \
    --days 7 \
    --limit 100 \
    --dry-run  # 先演練
```

⚠️ **警告**：回填會重新處理所有 Builds，可能佔用大量空間和時間！

---

## 🐛 快速故障排查

### 問題：定時任務沒有執行

```bash
# 1. 檢查 Celery Beat 是否運行
docker compose ps celery_beat

# 2. 查看 Celery Beat 日誌
docker compose logs celery_beat | tail -50

# 3. 重啟 Celery Beat
docker compose restart celery_beat
```

### 問題：任務一直在等待

```bash
# 1. 檢查 Celery Worker 是否運行
docker compose ps celery_worker

# 2. 查看 Worker 日誌
docker compose logs celery_worker | tail -100

# 3. 重啟 Worker
docker compose restart celery_worker
```

### 問題：存儲失敗

```bash
# 1. 查看詳細錯誤
tail -f logs/django_error.log | grep -i jenkins

# 2. 檢查 NAS 掛載
docker exec nt-django mount | grep /mnt/mdt

# 3. 測試 NAS 寫入權限
docker exec nt-django touch /mnt/mdt/Team/PQ1-3/tool/jenkins_test_storage/.test && \
docker exec nt-django rm /mnt/mdt/Team/PQ1-3/tool/jenkins_test_storage/.test && \
echo "✅ NAS 可寫入"
```

---

## 📚 更多資訊

- **完整文檔**：`docs/features/jenkins-auto-storage/IMPLEMENTATION_REPORT.md`
- **測試腳本**：`test_jenkins_auto_storage.sh`
- **Celery Flower**：http://localhost:5555
- **分析報告**：`docs/analysis/NAS_JENKINS_STORAGE_ANALYSIS.md`

---

## ✅ 檢查清單

在正式使用前，請確認：

- [ ] 已重啟 Django、Celery Worker、Celery Beat
- [ ] 測試腳本執行成功
- [ ] Celery Flower 可以訪問
- [ ] NAS 掛載正常且可寫入
- [ ] 至少等待 30 分鐘觀察第一次自動掃描
- [ ] 嘗試手動存儲幾個 Builds 測試功能

---

**最後更新**：2025-11-10  
**文檔版本**：v1.0  
**適用環境**：Docker Compose 部署
