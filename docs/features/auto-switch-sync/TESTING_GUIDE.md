# 自動 Switch 同步測試指南

## 📋 測試目的

驗證新增 DHCP Server 後，系統能自動識別並同步 Switch 設備，無需手動操作。

## 🧪 測試環境

- **系統**：Network Toolbox
- **服務**：Django + Celery + PostgreSQL
- **測試對象**：DHCP Server Switch 自動識別機制

## 📝 測試前準備

### 1. 確認服務運行

```bash
# 檢查所有服務
docker compose ps

# 必須運行的服務：
# - nt-django (Django 後端)
# - nt-celery (Celery Worker)
# - nt-celery-beat (定時任務調度器)
# - nt-react (前端)
# - nt-nginx (反向代理)
```

### 2. 檢查 Celery 狀態

```bash
# 查看 Celery 日誌
docker compose logs celery --tail 50

# 應該看到類似輸出：
# [2025-11-07 07:00:00,000: INFO/MainProcess] Connected to redis://...
# [2025-11-07 07:00:00,000: INFO/MainProcess] celery@... ready.
```

### 3. 準備測試數據

```bash
# 檢查現有 DHCP Server 數量
docker exec nt-django python manage.py shell -c "
from api.models import DHCPServer
print(f'Current servers: {DHCPServer.objects.count()}')
"
```

## 🎯 測試案例

### 測試案例 1：新增 DHCP Server（自動同步）

#### 步驟 1：創建測試 Server

```bash
# 使用 Django Shell 創建測試 Server
docker exec nt-django python manage.py shell -c "
from api.models import DHCPServer

# 創建測試 Server（模擬前端操作）
server = DHCPServer.objects.create(
    name='TEST-AUTO-SYNC',
    ip_address='10.250.200.1',
    ssh_username='admin',
    ssh_password='test123',
    ssh_port=22,
    status='online',
    os_type='windows',
    dhcp_service_type='isc-dhcp'
)

print(f'✅ Created test server: {server.name} (ID: {server.id})')
"
```

#### 步驟 2：監控信號觸發

```bash
# 在另一個終端監控 Django 日誌
docker compose logs django -f | grep -E "\[Signal\]|Switch"

# 預期輸出（10 秒內）：
# [Signal] 偵測到新建 DHCP Server: TEST-AUTO-SYNC (10.250.200.1)
# [Signal] 排程 Scope 初始同步任務 - Server ID: X
# [Signal] 排程 Switch 自動識別任務 - Server ID: X
```

#### 步驟 3：監控 Celery 任務

```bash
# 監控 Celery 日誌
docker compose logs celery -f | grep -E "auto_identify_switches|TEST-AUTO-SYNC"

# 預期輸出（60 秒內）：
# [Celery] 開始 Switch 自動識別 - Server ID: X
# [Celery] 找到 X 個 Switch 設備
```

#### 步驟 4：驗證結果

```bash
# 等待 70 秒後檢查結果
sleep 70

# 檢查是否創建了 Switch
docker exec nt-django python manage.py shell -c "
from api.models import DHCPServer, NetworkSwitch

server = DHCPServer.objects.get(name='TEST-AUTO-SYNC')
switches = NetworkSwitch.objects.filter(dhcp_server=server)

print(f'Server: {server.name}')
print(f'Switches found: {switches.count()}')

for sw in switches:
    print(f'  - {sw.name} ({sw.ip_address})')
"
```

#### 預期結果

- ✅ 信號成功觸發
- ✅ Celery 任務成功執行
- ✅ Switch 被自動識別並創建
- ✅ 前端頁面可以看到 Switch（需重新整理）

---

### 測試案例 2：有 Switch 設備的真實 Server

#### 步驟 1：準備有 Switch 的 Server

```bash
# 假設你有一個真實的 DHCP Server，其中包含 Switch 設備
# 例如：10.250.120.1（已知有 4 個 Zyxel Switch）

# 先刪除現有的 Switch（模擬新 Server 情況）
docker exec nt-django python manage.py shell -c "
from api.models import DHCPServer, NetworkSwitch

server = DHCPServer.objects.get(ip_address='10.250.120.1')
NetworkSwitch.objects.filter(dhcp_server=server).delete()
print('Existing switches deleted')
"
```

#### 步驟 2：手動觸發識別

```bash
# 使用信號處理器的手動觸發函數
docker exec nt-django python manage.py shell -c "
from api.signals import trigger_switch_identification_for_server
from api.models import DHCPServer

server = DHCPServer.objects.get(ip_address='10.250.120.1')
task_id = trigger_switch_identification_for_server(
    server_id=server.id,
    delay_seconds=5
)

print(f'Task ID: {task_id}')
print('等待 5 秒後執行...')
"
```

#### 步驟 3：監控執行過程

```bash
# 監控 Celery 日誌
docker compose logs celery -f --tail 20

# 預期看到：
# [Celery] 開始 Switch 自動識別 - Server ID: 6
# [Celery] 找到 4 個 Switch 設備
# [Celery] 創建: 4, 更新: 0
```

#### 步驟 4：驗證結果

```bash
# 10 秒後檢查
sleep 10

docker exec nt-django python manage.py shell -c "
from api.models import NetworkSwitch, DHCPServer

server = DHCPServer.objects.get(ip_address='10.250.120.1')
switches = NetworkSwitch.objects.filter(dhcp_server=server)

print(f'✅ Switches created: {switches.count()}')
for sw in switches:
    print(f'  - {sw.name}: {sw.ip_address} (MAC: {sw.mac_address})')
"
```

#### 預期結果

- ✅ 找到 4 個 Zyxel Switch
- ✅ 所有 Switch 都被創建
- ✅ 統計資訊正確更新

---

### 測試案例 3：租約更新觸發統計

#### 步驟 1：更新一個租約

```bash
docker exec nt-django python manage.py shell -c "
from api.models import DHCPLease, NetworkSwitch

# 找一個有 remote_id 的租約
lease = DHCPLease.objects.exclude(remote_id='').first()

if lease:
    print(f'Updating lease: {lease.ip_address}')
    print(f'Remote ID: {lease.remote_id}')
    
    # 更新租約（觸發信號）
    lease.hostname = 'TEST-DEVICE-UPDATED'
    lease.save()
    
    print('✅ Lease updated, signal should trigger in 30 seconds')
else:
    print('❌ No lease with remote_id found')
"
```

#### 步驟 2：監控信號

```bash
# 監控 Django 日誌
docker compose logs django -f | grep -E "\[Signal\].*Switch"

# 預期輸出：
# [Signal] 已排程 Switch 統計更新: GS1900 (remote_id: f4:4d:5c:9a:b0:19)
```

#### 步驟 3：等待統計更新

```bash
# 30 秒後檢查
sleep 35

docker compose logs celery | grep "update_switch_statistics"
```

---

## 🐛 故障排查測試

### 測試案例 4：Celery 服務停止

#### 模擬故障

```bash
# 停止 Celery 服務
docker compose stop celery
```

#### 創建 Server

```bash
docker exec nt-django python manage.py shell -c "
from api.models import DHCPServer

server = DHCPServer.objects.create(
    name='TEST-CELERY-DOWN',
    ip_address='10.250.201.1',
    status='online'
)
print(f'Created: {server.name}')
"
```

#### 驗證行為

```bash
# 信號應該觸發，但任務會進入 Redis 隊列等待
docker compose logs django | grep "\[Signal\]"

# 應該看到信號觸發的日誌
```

#### 恢復服務

```bash
# 啟動 Celery
docker compose start celery

# 等待 10 秒，檢查任務是否執行
sleep 10
docker compose logs celery --tail 50
```

#### 預期結果

- ✅ 信號正常觸發
- ✅ 任務排隊等待
- ✅ Celery 啟動後自動執行

---

### 測試案例 5：沒有 Switch 設備的 Server

#### 創建無 Switch 的 Server

```bash
docker exec nt-django python manage.py shell -c "
from api.models import DHCPServer

# 創建一個沒有 Switch 的測試 Server
server = DHCPServer.objects.create(
    name='TEST-NO-SWITCH',
    ip_address='10.250.202.1',
    status='online'
)
print(f'Created: {server.name}')
"
```

#### 等待自動識別

```bash
# 等待 70 秒
sleep 70

# 檢查結果
docker exec nt-django python manage.py shell -c "
from api.models import DHCPServer, NetworkSwitch

server = DHCPServer.objects.get(name='TEST-NO-SWITCH')
switches = NetworkSwitch.objects.filter(dhcp_server=server)

print(f'Switches found: {switches.count()}')  # 應該是 0
"
```

#### 檢查日誌

```bash
docker compose logs celery | grep "TEST-NO-SWITCH"

# 應該看到類似：
# [Celery] 找到 0 個 Switch 設備
# [Celery] 創建: 0, 更新: 0
```

#### 預期結果

- ✅ 任務正常執行
- ✅ 沒有找到 Switch（正常）
- ✅ 沒有錯誤發生

---

## 📊 測試檢查清單

### 自動化功能檢查

- [ ] 新增 Server 時信號觸發
- [ ] Scope 同步任務排程（10 秒延遲）
- [ ] Switch 識別任務排程（60 秒延遲）
- [ ] 任務成功執行
- [ ] Switch 記錄創建
- [ ] 統計資訊更新
- [ ] 前端頁面顯示

### 錯誤處理檢查

- [ ] Celery 服務停止時任務排隊
- [ ] Celery 恢復後任務執行
- [ ] 沒有租約時不報錯
- [ ] 沒有 Switch 時不報錯
- [ ] 任務失敗時自動重試

### 性能檢查

- [ ] 租約更新不阻塞（延遲 30 秒）
- [ ] 批次更新避免重複
- [ ] 大量租約時不超時

---

## 🧹 測試清理

### 刪除測試數據

```bash
# 刪除所有測試 Server
docker exec nt-django python manage.py shell -c "
from api.models import DHCPServer

# 刪除測試 Server（會級聯刪除相關 Switch、Lease 等）
DHCPServer.objects.filter(name__startswith='TEST-').delete()
print('✅ Test servers deleted')
"
```

### 重置 Celery 隊列（可選）

```bash
# 清空 Celery 任務隊列
docker exec nt-celery celery -A network_toolbox purge -f
```

---

## 📈 測試報告範本

### 測試執行記錄

| 測試案例 | 狀態 | 執行時間 | 備註 |
|---------|------|---------|------|
| 案例 1：新增 Server 自動同步 | ✅ PASS | 2025-11-07 | 成功創建 4 個 Switch |
| 案例 2：手動觸發識別 | ✅ PASS | 2025-11-07 | 識別正確 |
| 案例 3：租約更新統計 | ✅ PASS | 2025-11-07 | 30 秒後更新 |
| 案例 4：Celery 停止 | ✅ PASS | 2025-11-07 | 恢復後執行 |
| 案例 5：無 Switch Server | ✅ PASS | 2025-11-07 | 正常處理 |

### 發現的問題

- 無

### 改進建議

- 考慮縮短 Switch 識別延遲時間（從 60 秒改為 30 秒）
- 增加前端實時通知功能

---

## 🔗 相關文檔

- [自動 Switch 同步機制說明](./README.md)
- [故障排查指南](../../troubleshooting/SWITCH_SYNC_ISSUES.md)
