# NTP 自動同步 Sudo 權限配置指南

## 📋 問題說明

Django 容器內執行 `ntpdate` 命令需要 `sudo` 權限，但 Docker 容器預設沒有 sudo 權限。

## 🎯 解決方案

有兩種方式配置權限：

### 方案 A：在主機層級執行（推薦）✅

**優勢**：
- 不需要給容器 sudo 權限（安全）
- 主機同步後，所有容器自動繼承
- 配置簡單，維護容易

**實施方式**：使用主機的 `systemd-timesyncd` 服務（已在主文檔說明）

### 方案 B：給 Django 容器配置 Sudo 權限

**適用場景**：需要從 Django 應用內直接執行同步

**安全考量**：⚠️ 需要謹慎配置，避免安全風險

---

## 🛠️ 方案 B 實施步驟（可選）

如果您選擇讓 Django 容器可以執行時間同步，按以下步驟操作：

### 步驟 1：修改 Dockerfile

編輯 `backend/Dockerfile`，安裝 sudo 和 ntpdate：

```dockerfile
# 安裝必要工具
RUN apt-get update && apt-get install -y \
    sudo \
    ntpdate \
    && rm -rf /var/lib/apt/lists/*

# 創建 sudoers 規則（只允許執行 ntpdate）
RUN echo "app ALL=(ALL) NOPASSWD: /usr/sbin/ntpdate" >> /etc/sudoers.d/app-ntpdate && \
    chmod 0440 /etc/sudoers.d/app-ntpdate
```

### 步驟 2：修改 docker-compose.yml

給 Django 容器添加必要的 capabilities：

```yaml
services:
  django:
    # ... 其他配置 ...
    cap_add:
      - SYS_TIME  # 允許修改系統時間
    # ... 其他配置 ...
```

### 步驟 3：重建容器

```bash
# 進入專案目錄
cd /home/owner/Codes/network-toolbox

# 重建 Django 容器
docker compose build django

# 重新啟動服務
docker compose up -d django
```

### 步驟 4：驗證權限

```bash
# 進入容器測試
docker exec -it nt-django bash

# 測試 sudo ntpdate（應該不需要密碼）
sudo ntpdate -q 10.10.10.51

# 退出容器
exit
```

---

## ⚠️ 安全注意事項

### 最小權限原則

**方案 B 的 sudoers 配置**只允許執行特定命令：

```bash
# ✅ 允許（無需密碼）
sudo ntpdate -u 10.10.10.51

# ❌ 不允許
sudo apt-get install ...
sudo rm -rf / ...
sudo systemctl ...
```

### CAP_SYS_TIME 說明

`SYS_TIME` capability 允許容器：
- ✅ 修改系統時間
- ❌ **不會**影響主機時間（容器內的時間調整）
- ⚠️ 如果容器與主機共享時間命名空間，可能影響主機

### 建議配置

```yaml
# 推薦配置：限制 capability
cap_add:
  - SYS_TIME
cap_drop:
  - ALL  # 移除所有其他 capabilities

# 如果需要更嚴格的隔離
security_opt:
  - no-new-privileges:true
```

---

## 🔍 驗證與測試

### 測試 1：檢查 sudo 權限

```bash
docker exec nt-django sudo -l

# 預期輸出：
# User app may run the following commands on ...:
#     (ALL) NOPASSWD: /usr/sbin/ntpdate
```

### 測試 2：手動執行同步

```bash
docker exec nt-django python manage.py shell -c "
from api.ntp_service import NTPSyncService

sync_service = NTPSyncService('10.10.10.51')
result = sync_service.sync_system_time(method='ntpdate', triggered_by='manual')
print(result)
"
```

### 測試 3：執行 Celery 任務

```bash
docker exec nt-django python -c "
from api.tasks import sync_ntp_time_task
result = sync_ntp_time_task()
print(result)
"
```

---

## 🔄 方案比較

| 項目 | 方案 A（主機層級） | 方案 B（容器權限） |
|------|-------------------|-------------------|
| 安全性 | ✅ 高 | ⚠️ 中（需謹慎配置） |
| 配置複雜度 | ✅ 簡單 | ⚠️ 中等 |
| 對容器影響 | ✅ 無（自動繼承） | ⚠️ 需重建容器 |
| 同步範圍 | ✅ 主機 + 所有容器 | ❌ 僅容器內 |
| 推薦使用 | ✅ 生產環境 | ⚠️ 開發/測試環境 |

---

## 💡 推薦策略

### 生產環境（推薦）

使用**方案 A（主機層級同步）**：

1. ✅ 在主機配置 `systemd-timesyncd`
2. ✅ 容器自動繼承主機時間
3. ✅ Django 應用的定時任務**僅用於監控**（check_ntp_sync_task）
4. ❌ 不使用 `sync_ntp_time_task`（或設為停用）

### 開發/測試環境（可選）

使用**方案 B（容器權限）**進行測試：

1. ⚠️ 配置 Dockerfile 和 docker-compose.yml
2. ⚠️ 啟用 `sync_ntp_time_task` 定時任務
3. ⚠️ 定期檢查安全配置

---

## 📚 相關文檔

- [主機 NTP 同步指南](./HOST_NTP_SETUP_GUIDE.md) - 方案 A 詳細步驟
- [Docker Security](https://docs.docker.com/engine/security/) - Docker 安全最佳實踐
- [Linux Capabilities](https://man7.org/linux/man-pages/man7/capabilities.7.html) - CAP_SYS_TIME 說明

---

**最後更新**：2025-11-25  
**維護者**：Network Toolbox Team
