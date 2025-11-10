# 🗂️ DHCP 日誌保留策略 - 快速參考

## ⏰ 核心資訊

| 項目 | 設定值 |
|-----|-------|
| 📅 **保留天數** | **15 天** |
| 🕐 **清理時間** | 每天凌晨 **3:00 AM** (Taipei) |
| 📊 **當前日誌數** | ~20,000 筆 |
| 🔄 **清理頻率** | 每日自動執行 |
| ✅ **任務狀態** | 已啟用並正常運作 |

---

## 🔍 快速檢查命令

### 查看保留策略
```bash
docker exec nt-django python manage.py shell -c "
from api.models import DHCPLog
from django.utils import timezone
from datetime import timedelta

cutoff = timezone.now() - timedelta(days=15)
total = DHCPLog.objects.count()
old = DHCPLog.objects.filter(timestamp__lt=cutoff).count()

print(f'📊 總日誌: {total:,}')
print(f'🗑️  待清理: {old:,}')
print(f'✅ 保留: {total - old:,}')
"
```

### 手動觸發清理
```bash
docker exec nt-django python manage.py shell -c "
from api.tasks import cleanup_old_logs_task
result = cleanup_old_logs_task.delay(days=15)
print(f'✅ 任務已提交: {result.id}')
"
```

### 查看清理日誌
```bash
grep "清理 DHCP 舊日誌" logs/django.log | tail -5
```

---

## ⚙️ 修改保留天數

### 改為 30 天（不需重啟）
```bash
docker exec nt-django python manage.py shell -c "
from django_celery_beat.models import PeriodicTask
import json

task = PeriodicTask.objects.get(name='cleanup-old-dhcp-logs-daily')
task.kwargs = json.dumps({'days': 30})
task.save()

print('✅ 已更新為 30 天')
"
```

---

## 📚 詳細文檔

請參閱: [`docs/features/dhcp/LOG_RETENTION_POLICY.md`](./LOG_RETENTION_POLICY.md)

---

**最後更新**: 2025-11-10
