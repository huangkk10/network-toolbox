# Switch 自動識別機制 - 完整指南

## 📋 概述

本文檔說明 Network Toolbox 如何自動識別和管理網路交換器（Switch）設備，以及新增 DHCP Server 後的自動化流程。

## 🎯 問題背景

### 原始問題

當新增一個 DHCP Server 後，Switch 管理頁面可能沒有資料，原因如下：

1. **缺少 DHCP Option 82**：租約記錄沒有 `remote_id` 和 `circuit_id` 資訊
2. **未自動識別**：新 Server 的 Switch 設備尚未被識別和同步
3. **需手動觸發**：需要手動點擊「立即同步」按鈕

### 識別機制

系統透過兩種方式識別 Switch：

#### 方式 1：DHCP Option 82（推薦）

**Option 82 是什麼？**

DHCP Option 82（Relay Agent Information Option）是由 Switch 在 DHCP 請求中插入的資訊：

- **Remote ID**：識別 Switch 本身（MAC 地址或名稱）
- **Circuit ID**：識別連接的端口（例如：`Gi1/0/24`）

**優點**：
- ✅ 準確識別 Switch 和端口
- ✅ 可建立完整的網路拓撲
- ✅ 追蹤設備連接位置

**要求**：
- Switch 需支援並啟用 DHCP Snooping
- Switch 需啟用 Option 82 插入
- DHCP Server 需記錄 Option 82 資訊

#### 方式 2：廠商識別（自動備援）

**工作原理**：

系統根據 MAC 地址的 OUI（前 6 位）識別設備廠商，如果是 Switch 廠商則自動標記為 Switch。

**支援的 Switch 廠商**：
```python
SWITCH_VENDOR_KEYWORDS = [
    'cisco', 'juniper', 'arista', 'extreme', 'huawei', 'h3c',
    'hewlett packard', 'hpe', 'dell', 'brocade', 'netgear',
    'd-link', 'tp-link', 'ubiquiti', 'mikrotik', 'zyxel',
    'switch', 'switching', 'ruijie', 'planet', 'edimax',
]
```

**識別邏輯**：
```python
def is_switch_vendor(vendor):
    # 排除 PC 網卡廠商
    exclude_keywords = ['intel', 'realtek', 'broadcom', 'microsoft', 'apple']
    
    # 匹配 Switch 廠商關鍵字
    for keyword in SWITCH_VENDOR_KEYWORDS:
        if keyword in vendor.lower():
            return True
    return False
```

**優點**：
- ✅ 不需要 Option 82
- ✅ 自動識別常見 Switch 品牌
- ✅ 適用於簡單網路環境

**限制**：
- ❌ 無法識別端口資訊
- ❌ 可能誤判（如果 PC 使用 Switch 廠商的網卡）

---

## 🔄 自動化改善方案

### 1. 定時自動識別（已實現）

**Celery Beat 定時任務**：

```python
# backend/network_toolbox/celery.py
'auto-identify-switches-hourly': {
    'task': 'api.tasks.auto_identify_switches_task',
    'schedule': crontab(minute=0),  # 每小時整點執行
    'kwargs': {
        'server_id': None  # None 表示處理所有 Server
    },
}
```

**功能**：
- ⏰ **執行頻率**：每小時整點（00:00, 01:00, 02:00...）
- 🔍 **掃描範圍**：所有 DHCP Server
- 📊 **識別方式**：基於廠商關鍵字
- 📝 **自動更新**：創建新 Switch 或更新現有 Switch

**查看執行日誌**：
```bash
# 查看 Celery 日誌
docker compose logs celery -f | grep "Switch 自動識別"

# 或查看 Django 日誌
tail -f logs/django.log | grep "Switch"
```

### 2. 新增 Server 自動觸發（新增）

**Django Signal 處理器**：

當新增 DHCP Server 時，自動觸發 Switch 識別任務：

```python
# backend/api/signals.py
@receiver(post_save, sender=DHCPServer)
def dhcp_server_post_save(sender, instance, created, **kwargs):
    if created:
        # 延遲 60 秒後自動執行 Switch 識別
        auto_identify_switches_task.apply_async(
            kwargs={'server_id': instance.id},
            countdown=60,  # 等待租約同步完成
        )
```

**觸發時機**：
1. ✅ 新增 DHCP Server
2. ⏳ 延遲 60 秒後執行（等待租約同步）
3. 🔄 自動重試 2 次（失敗時）

**流程圖**：
```
新增 DHCP Server
    ↓
觸發 post_save 信號
    ↓
排程 Scope 同步任務 (10 秒後)
    ↓
排程 Switch 識別任務 (60 秒後)
    ↓
執行任務
    ↓
更新 Switch 列表
```

### 3. 租約更新自動觸發（新增）

**租約變化時自動更新 Switch 統計**：

```python
# backend/api/signals.py
@receiver(post_save, sender=DHCPLease)
def dhcp_lease_post_save(sender, instance, created, **kwargs):
    if instance.remote_id:
        # 找到對應的 Switch，更新統計資訊
        switch = NetworkSwitch.objects.filter(remote_id=instance.remote_id).first()
        if switch:
            update_switch_statistics_task.apply_async(
                kwargs={'switch_id': switch.id},
                countdown=30,
            )
```

**功能**：
- 📊 自動更新 Switch 連接設備數量
- 🔌 更新活動端口統計
- ⏱️ 批次更新（30 秒內同一 Switch 只更新一次）

---

## 🚀 使用指南

### 情境 1：新增 DHCP Server

**步驟**：

1. **新增 Server**（前端操作）
   ```
   DHCP Server 管理 → 新增 Server
   填寫：名稱、IP、SSH 憑證等
   點擊「保存」
   ```

2. **自動流程**（無需手動操作）
   ```
   ✅ 系統自動觸發：
   - 10 秒後：Scope 同步
   - 60 秒後：Switch 識別
   ```

3. **查看結果**（1-2 分鐘後）
   ```
   DHCP Server 分析 → Switch 管理
   選擇新 Server → 查看 Switch 列表
   ```

**預期結果**：
- ✅ 如果有 Switch 設備（Zyxel、Cisco 等），會自動顯示
- ✅ 統計資訊自動更新
- ✅ 無需手動同步

### 情境 2：手動立即同步

**適用情況**：
- 🔸 剛新增 Server，不想等待 60 秒
- 🔸 懷疑 Switch 資料不完整
- 🔸 測試或故障排查

**操作方式**：

```
DHCP Server 分析 → Switch 管理
選擇 Server → 點擊「立即同步」按鈕
```

**或使用 API**：
```bash
curl -X POST http://localhost/api/switches/sync_from_leases/ \
  -H "Content-Type: application/json" \
  -d '{"server_id": 6, "hours": 24}'
```

**或使用 Django Shell**：
```python
from api.signals import trigger_switch_identification_for_server

# 觸發特定 Server 的識別（延遲 5 秒）
task_id = trigger_switch_identification_for_server(server_id=6, delay_seconds=5)
print(f"Task ID: {task_id}")
```

### 情境 3：啟用 Option 82（推薦）

**Windows DHCP Server 配置**：

1. **啟用 Relay Agent 記錄**
   ```powershell
   # 在 Windows DHCP Server 上執行
   Set-DhcpServerv4OptionValue -OptionId 82 -Value "Enabled"
   ```

2. **DHCP Server 管理控制台**
   ```
   伺服器屬性 → 進階
   ✅ 勾選「記錄 DHCP Relay Agent 資訊」
   ```

**Switch 配置（Cisco 範例）**：

```cisco
# 全域啟用 DHCP Snooping
ip dhcp snooping
ip dhcp snooping vlan 1-100

# 啟用 Option 82 插入
ip dhcp snooping information option

# 信任上行端口（連接 DHCP Server）
interface GigabitEthernet0/1
  ip dhcp snooping trust
```

**Zyxel Switch 配置**：

```
# 啟用 DHCP Snooping
switch(config)# ip dhcp snooping
switch(config)# ip dhcp snooping vlan 1-100

# 啟用 Option 82
switch(config)# ip dhcp snooping information option

# 設定上行端口
switch(config)# interface eth1
switch(config-if)# ip dhcp snooping trust
```

---

## 🔧 故障排查

### 問題 1：新增 Server 後沒有 Switch 資料

**診斷步驟**：

1. **檢查是否有租約**
   ```bash
   docker exec nt-django python manage.py shell -c "
   from api.models import DHCPServer, DHCPLease
   server = DHCPServer.objects.get(id=YOUR_SERVER_ID)
   print(f'Total leases: {DHCPLease.objects.filter(server=server).count()}')
   "
   ```

2. **檢查是否有 Switch 廠商的設備**
   ```bash
   docker exec nt-django python manage.py shell -c "
   from api.models import DHCPLease, DHCPServer
   from api.serializers import DHCPLeaseSerializer
   
   server = DHCPServer.objects.get(id=YOUR_SERVER_ID)
   switch_vendors = ['Cisco', 'Zyxel', 'HP', 'Dell']
   
   for lease in DHCPLease.objects.filter(server=server)[:50]:
       serializer = DHCPLeaseSerializer(lease)
       vendor = serializer.data.get('vendor', '')
       if any(sv in vendor for sv in switch_vendors):
           print(f'{lease.ip_address}: {vendor}')
   "
   ```

3. **手動觸發識別**
   ```python
   from api.signals import trigger_switch_identification_for_server
   trigger_switch_identification_for_server(server_id=YOUR_SERVER_ID)
   ```

4. **檢查 Celery 是否運行**
   ```bash
   docker compose ps | grep celery
   docker compose logs celery --tail 50
   ```

### 問題 2：Celery 定時任務沒有執行

**檢查 Celery Beat**：

```bash
# 查看 Celery Beat 狀態
docker compose logs celery-beat --tail 50

# 查看定時任務配置
docker exec nt-django python manage.py shell -c "
from django_celery_beat.models import PeriodicTask
tasks = PeriodicTask.objects.filter(enabled=True)
for task in tasks:
    print(f'{task.name}: {task.enabled}')
"
```

**重啟 Celery 服務**：

```bash
docker compose restart celery celery-beat
```

### 問題 3：Switch 識別錯誤

**可能原因**：

1. **廠商關鍵字不匹配**
   - 解決：更新 `SWITCH_VENDOR_KEYWORDS` 列表

2. **PC 被誤判為 Switch**
   - 解決：更新 `exclude_keywords` 列表

3. **缺少 Option 82**
   - 解決：啟用 Option 82（參考上方配置）

---

## 📊 監控和維護

### 查看 Switch 識別任務執行歷史

```bash
# 查看最近的 Celery 任務執行記錄
docker exec nt-django python manage.py shell -c "
from django_celery_results.models import TaskResult
results = TaskResult.objects.filter(
    task_name='api.tasks.auto_identify_switches_task'
).order_by('-date_done')[:10]

for result in results:
    print(f'{result.date_done}: {result.status} - {result.result}')
"
```

### 查看 Switch 統計

```bash
# 查看所有 Switch 統計
curl http://localhost/api/switches/statistics/ | python3 -m json.tool

# 查看特定 Server 的 Switch
curl "http://localhost/api/switches/statistics/?server_id=6" | python3 -m json.tool
```

### 日誌監控

```bash
# 即時監控 Switch 相關日誌
docker compose logs -f django | grep "Switch"

# 查看 Celery 任務日誌
docker compose logs -f celery | grep "auto_identify_switches"
```

---

## 🎯 最佳實踐

### 1. 新網路環境部署

**建議順序**：

1. ✅ 先配置 DHCP Server（啟用 Option 82 記錄）
2. ✅ 配置 Switch（啟用 DHCP Snooping 和 Option 82）
3. ✅ 新增 DHCP Server 到系統
4. ✅ 等待 1-2 分鐘讓自動識別完成
5. ✅ 驗證 Switch 列表和統計資訊

### 2. 定期維護

**每週檢查**：
- 📊 Switch 統計是否正常更新
- 🔍 是否有未識別的 Switch 設備
- 📝 Celery 任務執行是否正常

**每月維護**：
- 🔄 更新 OUI 資料庫（自動）
- 🧹 清理舊的任務結果
- 📈 檢視 Switch 拓撲變化趨勢

### 3. 性能優化

**針對大型網路**：

- 調整 Celery Worker 數量
- 增加記憶體配額
- 調整定時任務頻率

```yaml
# docker-compose.yml
celery:
  deploy:
    resources:
      limits:
        memory: 2G
      reservations:
        memory: 1G
  command: celery -A network_toolbox worker -l info --concurrency=4
```

---

## 📚 相關文檔

- [DHCP Server 管理指南](../dhcp-server/README.md)
- [Option 82 配置詳解](../dhcp-server/OPTION82_GUIDE.md)
- [Celery 定時任務配置](../../deployment/CELERY_SETUP.md)
- [網路拓撲視覺化](../network-topology/README.md)

---

## 📝 更新日誌

- **2025-11-07**：新增自動識別機制和信號處理器
- **2025-10-27**：初始版本，手動同步功能

---

**維護者**：Network Toolbox Team  
**最後更新**：2025-11-07
