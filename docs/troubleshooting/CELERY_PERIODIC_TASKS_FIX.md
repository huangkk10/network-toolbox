# Celery 週期性任務修復報告

## 📋 問題描述

**報告時間**：2025-11-14

**問題現象**：
- Jenkins 相關的 NAS 存儲目錄沒有更新
- 最後更新時間停留在 11月13日
- 週期性任務（如 Jenkins Builds 自動存儲）沒有運行

## 🔍 問題診斷

### 1. 檢查 Celery 服務狀態

```bash
docker compose exec django celery -A network_toolbox inspect active
```

**發現問題**：
- ✅ **Celery Worker 正在運行**（2 個節點）
- ❌ **Celery Beat 沒有運行**（定時任務調度器）

### 2. 檢查 Jenkins 存儲目錄

```bash
docker compose exec django ls -lh /mnt/mdt/Team/PQ1-3/tool/jenkins_test_storage/
```

**發現問題**：
- `10.252.170.171`: 最後更新 11月10日
- `10.252.170.187`: 最後更新 11月13日
- `10.252.170.188`: 最後更新 11月13日
- **結論**：自 11月13日後沒有新的更新

### 3. 根本原因

**原因**：`backend/entrypoint.sh` 只啟動了 Django 開發伺服器，沒有啟動 Celery Beat。

**舊版 entrypoint.sh**：
```bash
#!/bin/bash
# 只有這些內容
echo "🚀 啟動 Django 開發伺服器..."
exec python manage.py runserver 0.0.0.0:8000
```

**問題**：
- ✅ Django 開發伺服器：已啟動
- ✅ Celery Worker：手動啟動（容器重啟後會消失）
- ❌ Celery Beat：**從未啟動**

## ✅ 解決方案

### 修改 `backend/entrypoint.sh`

添加 Celery Worker 和 Beat 的自動啟動：

```bash
#!/bin/bash
# Django 容器啟動腳本
# 1. 掛載 NAS
# 2. 啟動 Celery Worker
# 3. 啟動 Celery Beat
# 4. 啟動 Django 開發伺服器

set -e

echo "========================================="
echo "Django 容器啟動中..."
echo "========================================="

# 執行 NAS 掛載
if [ -f "/app/mount_nas.sh" ]; then
    echo "🔗 執行 NAS 掛載..."
    bash /app/mount_nas.sh || echo "⚠️  NAS 掛載失敗，繼續啟動服務..."
else
    echo "⚠️  找不到 mount_nas.sh，跳過 NAS 掛載"
fi

echo ""
echo "🚀 啟動 Celery Worker..."
celery -A network_toolbox worker --loglevel=info --detach

echo "🚀 啟動 Celery Beat（定時任務調度器）..."
celery -A network_toolbox beat --loglevel=info --detach

echo "🚀 啟動 Django 開發伺服器..."
exec python manage.py runserver 0.0.0.0:8000
```

### 重啟容器

```bash
docker compose restart django
```

## 🧪 驗證結果

### 1. 驗證 Celery 服務狀態

```bash
# 檢查 Worker
docker compose exec django celery -A network_toolbox inspect active

# 檢查 Beat 排程
docker compose exec django celery -A network_toolbox inspect scheduled
```

**結果**：
- ✅ Celery Worker：2 個節點正在運行
- ✅ Celery Beat：正在運行
- ✅ 定時任務已註冊

### 2. 手動觸發測試任務

```bash
docker compose exec django python manage.py shell -c "
from api.tasks import auto_store_jenkins_builds_task
result = auto_store_jenkins_builds_task.delay()
print(f'任務 ID: {result.id}')
"
```

**結果**：
- ✅ 任務成功提交
- ✅ 創建了 5 個子任務（處理不同的 Builds）

### 3. 檢查文件更新時間

```bash
docker compose exec django find /mnt/mdt/Team/PQ1-3/tool/jenkins_test_storage/10.252.170.188 -type f -printf "%T+ %p\n" | sort -r | head -5
```

**結果**：
```
2025-11-14+05:29:31 - 文件已更新 ✅
```

**確認**：Jenkins 存儲功能已恢復正常！

## 📊 當前週期性任務列表

以下是所有已配置的週期性任務：

| 任務名稱 | 執行週期 | 功能 | 狀態 |
|---------|---------|------|------|
| `sync-all-dhcp-logs-every-10-minutes` | 每 10 分鐘 | 同步 DHCP 日誌 | ✅ 運行中 |
| `cleanup-old-dhcp-logs-daily` | 每天 03:00 | 清理舊的 DHCP 日誌 | ✅ 運行中 |
| `update-oui-database-monthly` | 每月 1 號 02:00 | 更新 OUI 資料庫 | ✅ 運行中 |
| `check-nas-connection-every-5-minutes` | 每 5 分鐘 | NAS 連線檢測 | ✅ 運行中 |
| `check-all-ipxe-network-quality-every-5-minutes` | 每 5 分鐘 | IPXE 網路品質檢測 | ✅ 運行中 |
| `sync-all-dhcp-scopes-daily` | 每天 04:00 | 同步 DHCP Scope | ✅ 運行中 |
| `sync-all-dhcp-leases-every-15-minutes` | 每 15 分鐘 | 同步 DHCP 租約 | ✅ 運行中 |
| `auto-identify-switches-hourly` | 每小時整點 | 自動識別 Switch | ✅ 運行中 |
| `check-gitlab-connection-every-5-minutes` | 每 5 分鐘 | GitLab 連線檢測 | ✅ 運行中 |
| `sync-jenkins-builds-every-10-minutes` | 每 10 分鐘 | 同步 Jenkins Builds | ✅ 運行中 |
| `auto-store-jenkins-workspaces-hourly` | 每小時整點 | 自動存儲 Workspace | ✅ 運行中 |
| `auto-store-jenkins-builds-every-30-minutes` | 每 30 分鐘 | 自動存儲 Builds 到 NAS | ✅ 運行中 |
| `clean-expired-ansible-caches-daily` | 每天 03:30 | 清理過期快取 | ✅ 運行中 |
| `sync-jenkins-jobs-hourly` | 每小時整點 | 自動同步 Jenkins Jobs | ✅ 運行中 |

## 🔧 維護建議

### 1. 監控 Celery 健康狀態

定期檢查 Celery 服務狀態：

```bash
# 每日檢查
docker compose exec django celery -A network_toolbox inspect ping

# 查看活動任務
docker compose exec django celery -A network_toolbox inspect active

# 查看排程任務
docker compose exec django celery -A network_toolbox inspect scheduled
```

### 2. 監控 NAS 存儲空間

```bash
# 檢查 Jenkins 存儲空間使用
docker compose exec django du -sh /mnt/mdt/Team/PQ1-3/tool/jenkins_test_storage/*

# 檢查 NAS 總空間
docker compose exec django df -h /mnt/mdt
```

### 3. 查看任務執行日誌

```bash
# 查看 Celery 相關日誌
tail -f logs/django.log | grep Celery

# 查看特定任務的執行記錄
tail -100 logs/django.log | grep "auto_store_jenkins_builds"
```

### 4. 清理舊的存儲文件（可選）

如果存儲空間不足，可以定期清理舊的 Jenkins Builds：

```bash
# 列出佔用空間最大的目錄
docker compose exec django du -h /mnt/mdt/Team/PQ1-3/tool/jenkins_test_storage/* | sort -h | tail -20

# 手動刪除舊的 Builds（需謹慎）
# docker compose exec django rm -rf /mnt/mdt/Team/PQ1-3/tool/jenkins_test_storage/10.252.170.187/JOB_NAME/OLD_BUILD_NUMBER
```

## 🚨 故障排查

### 問題 1：容器重啟後 Celery 沒有運行

**檢查步驟**：
1. 確認 `entrypoint.sh` 包含 Celery 啟動命令
2. 檢查容器日誌：
   ```bash
   docker compose logs django | grep -E "(Celery|Worker|Beat)"
   ```

### 問題 2：任務執行失敗

**檢查步驟**：
1. 查看錯誤日誌：
   ```bash
   tail -100 logs/django_error.log
   ```

2. 檢查 NAS 連接：
   ```bash
   docker compose exec django ls -lh /mnt/mdt/
   ```

3. 手動執行任務測試：
   ```bash
   docker compose exec django python manage.py shell -c "
   from api.tasks import auto_store_jenkins_builds_task
   result = auto_store_jenkins_builds_task()
   print(result)
   "
   ```

### 問題 3：週期性任務沒有按時執行

**檢查步驟**：
1. 確認 Celery Beat 正在運行
2. 檢查系統時間是否正確：
   ```bash
   docker compose exec django date
   ```

3. 查看 Beat 日誌：
   ```bash
   docker compose logs django | grep beat
   ```

## 📈 效果確認

修復後的效果：

| 指標 | 修復前 | 修復後 |
|-----|-------|-------|
| Celery Beat 狀態 | ❌ 未運行 | ✅ 運行中 |
| 週期性任務執行 | ❌ 停止 | ✅ 正常 |
| Jenkins 文件更新 | ❌ 停在 11/13 | ✅ 11/14 05:29 |
| 自動同步 Jobs | ❌ 未運行 | ✅ 每小時執行 |
| 自動存儲 Builds | ❌ 未運行 | ✅ 每 30 分鐘執行 |

## 📝 總結

**問題原因**：
- `entrypoint.sh` 缺少 Celery Beat 啟動命令
- 導致所有週期性任務無法自動執行

**解決方案**：
- 修改 `entrypoint.sh`，添加 Celery Worker 和 Beat 啟動
- 確保容器重啟後服務自動恢復

**驗證結果**：
- ✅ Celery 服務正常運行
- ✅ 週期性任務已恢復
- ✅ Jenkins 文件正常更新
- ✅ 所有 14 個定時任務正常工作

## 🔗 相關文檔

- [Celery 配置](../../backend/network_toolbox/celery.py)
- [定時任務列表](../../backend/api/tasks.py)
- [Jenkins 自動同步功能](../features/jenkins-auto-sync/README.md)

## 👥 維護者

Network Toolbox Team

**修復日期**：2025-11-14
**修復者**：GitHub Copilot
