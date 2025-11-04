# Switch 管理功能 - 快速開始

## 🚀 5 分鐘快速上手

### 步驟 1：確認環境

確保您的 Network Toolbox 已經正常運行：

```bash
# 檢查服務狀態
docker compose ps

# 確認所有容器都在運行
# nt-nginx    - 前端服務
# nt-react    - React 開發服務器
# nt-django   - Django 後端
# nt-adminer  - 資料庫管理
```

### 步驟 2：同步 Switch 資訊

有兩種方式同步 Switch 資訊：

#### 方式 1：透過 Web 介面（推薦）

1. 開啟瀏覽器訪問 `http://localhost`
2. 進入 **DHCP Server 分析** 頁面
3. 點擊 **Switch 管理** Tab
4. 點擊 **同步 Switch** 按鈕

#### 方式 2：透過 API

```bash
# 同步所有 DHCP Lease 的 Switch 資訊
curl -X POST http://localhost/api/switches/sync_from_leases/ \
  -H "Content-Type: application/json"

# 或指定特定 Server 和時間範圍
curl -X POST http://localhost/api/switches/sync_from_leases/ \
  -H "Content-Type: application/json" \
  -d '{
    "server_id": 1,
    "hours": 48
  }'
```

### 步驟 3：查看 Switch 列表

#### Web 介面

在 **Switch 管理** Tab 中，您會看到：
- 📊 統計卡片（總 Switch 數、活躍 Switch、連接設備數）
- 📋 Switch 列表（名稱、Remote ID、MAC、IP、狀態、設備數）
- 👁️ 查看按鈕（點擊可查看詳細資訊）

#### API 查詢

```bash
# 獲取 Switch 列表
curl http://localhost/api/switches/ | python3 -m json.tool

# 獲取統計資訊
curl http://localhost/api/switches/statistics/ | python3 -m json.tool
```

### 步驟 4：查看設備分佈

點擊任一 Switch 的「查看」按鈕，會顯示：
- Switch 基本資訊
- 連接設備列表（按端口分組）
- 每個設備的 IP、MAC、主機名

### 步驟 5：自訂 Switch 資訊（選用）

您可以透過 Django Admin 或 API 更新 Switch 資訊：

```bash
# 透過 API 更新 Switch 名稱和位置
curl -X PATCH http://localhost/api/switches/1/ \
  -H "Content-Type: application/json" \
  -d '{
    "name": "1樓核心交換器",
    "location": "機房A",
    "building": "總部大樓",
    "floor": "1F"
  }'
```

## 📊 常用命令速查

### 查詢操作

```bash
# 獲取所有 Switch
curl http://localhost/api/switches/

# 獲取特定 Switch 的設備列表
curl http://localhost/api/switches/1/devices/

# 獲取 Switch 端口資訊
curl http://localhost/api/switches/1/ports/

# 獲取統計資訊
curl http://localhost/api/switches/statistics/

# 獲取網路拓撲
curl http://localhost/api/switches/topology/
```

### 同步和更新操作

```bash
# 同步 Switch 資訊
curl -X POST http://localhost/api/switches/sync_from_leases/ \
  -H "Content-Type: application/json"

# 更新單個 Switch 的統計
curl -X POST http://localhost/api/switches/1/update_stats/
```

### 過濾查詢

```bash
# 按 DHCP Server 過濾
curl "http://localhost/api/switches/?server_id=1"

# 按狀態過濾
curl "http://localhost/api/switches/?status=active"

# 獲取最近 48 小時的設備
curl "http://localhost/api/switches/1/devices/?hours=48"
```

## 🎯 實用腳本

### 自動同步腳本

創建 `sync_switches.sh`：

```bash
#!/bin/bash
# 自動同步 Switch 資訊

echo "正在同步 Switch 資訊..."

response=$(curl -s -X POST http://localhost/api/switches/sync_from_leases/ \
  -H "Content-Type: application/json")

echo "$response" | python3 -m json.tool

# 檢查結果
if echo "$response" | grep -q '"success": true'; then
    echo "✅ 同步成功！"
else
    echo "❌ 同步失敗！"
    exit 1
fi
```

### 統計報表腳本

創建 `switch_report.sh`：

```bash
#!/bin/bash
# 生成 Switch 統計報表

echo "=== Switch 統計報表 ==="
echo "生成時間: $(date '+%Y-%m-%d %H:%M:%S')"
echo ""

stats=$(curl -s http://localhost/api/switches/statistics/)

echo "📊 總覽："
echo "$stats" | python3 -c "
import sys, json
data = json.load(sys.stdin)
print(f\"  總 Switch 數: {data['total_switches']}\")
print(f\"  活躍 Switch: {data['active_switches']}\")
print(f\"  連接設備總數: {data['total_devices']}\")
print(f\"  活動端口: {data['active_ports']}/{data['total_ports']}\")
"

echo ""
echo "🏆 Top 5 Switch (按設備數排序)："
echo "$stats" | python3 -c "
import sys, json
data = json.load(sys.stdin)
for i, sw in enumerate(data['top_switches'][:5], 1):
    print(f\"  {i}. {sw['name']} - {sw['connected_devices']} 台設備\")
"
```

### 設備定位腳本

創建 `find_device.sh`：

```bash
#!/bin/bash
# 尋找設備連接的 Switch 和端口

if [ -z "$1" ]; then
    echo "使用方法: $0 <MAC地址或IP地址>"
    exit 1
fi

search_term="$1"

echo "正在搜尋設備: $search_term"
echo ""

# 搜尋所有 Switch
switches=$(curl -s http://localhost/api/switches/)

echo "$switches" | python3 -c "
import sys, json, requests

search = '$search_term'
switches = json.load(sys.stdin)

found = False
for sw in switches:
    # 獲取 Switch 的設備列表
    devices = requests.get(f\"http://localhost/api/switches/{sw['id']}/devices/\").json()
    
    for port, port_devices in devices['devices_by_port'].items():
        for device in port_devices:
            if search in device['ip_address'] or search in device['mac_address']:
                print(f\"✅ 找到設備！\")
                print(f\"  Switch: {sw['name']} ({sw['remote_id']})\")
                print(f\"  端口: {port}\")
                print(f\"  IP: {device['ip_address']}\")
                print(f\"  MAC: {device['mac_address']}\")
                print(f\"  主機名: {device['hostname']}\")
                found = True
                break
        if found:
            break
    if found:
        break

if not found:
    print('❌ 未找到設備')
"
```

## 🔧 設定定時同步

### 使用 Cron（推薦）

編輯 crontab：

```bash
crontab -e
```

添加以下行（每小時同步一次）：

```cron
0 * * * * /path/to/sync_switches.sh >> /var/log/switch_sync.log 2>&1
```

### 使用 Celery Beat（Docker 環境）

在 `backend/api/tasks.py` 中添加：

```python
from celery import shared_task
import requests

@shared_task
def sync_switches():
    """定時同步 Switch 資訊"""
    try:
        response = requests.post(
            'http://localhost:8000/api/switches/sync_from_leases/',
            json={}
        )
        return response.json()
    except Exception as e:
        return {'success': False, 'error': str(e)}
```

在 Celery Beat 配置中添加：

```python
CELERY_BEAT_SCHEDULE = {
    'sync-switches-hourly': {
        'task': 'api.tasks.sync_switches',
        'schedule': crontab(minute=0),  # 每小時整點執行
    },
}
```

## ❓ 常見問題

### Q1: 為什麼 Switch 列表是空的？

**A:** 這表示您的 DHCP Lease 記錄中沒有 Option 82 資訊。請檢查：
1. Switch 是否啟用了 DHCP Relay
2. Switch 是否配置了 Option 82
3. DHCP Server 日誌是否包含完整的 Option 資訊

### Q2: 如何知道 Switch 是否有 Option 82？

**A:** 檢查 DHCP Lease 記錄：

```bash
# 查看 Lease 記錄中的 Option 82 欄位
curl http://localhost/api/dhcp-leases/ | python3 -c "
import sys, json
leases = json.load(sys.stdin)
for lease in leases:
    if lease.get('remote_id'):
        print(f\"✅ {lease['ip_address']} - Remote ID: {lease['remote_id']}\")
" | head -5
```

### Q3: 設備數量為 0 但我知道有設備連接

**A:** 執行統計更新：

```bash
curl -X POST http://localhost/api/switches/1/update_stats/
```

### Q4: 如何批量更新所有 Switch 的統計？

**A:** 創建腳本：

```bash
#!/bin/bash
switches=$(curl -s http://localhost/api/switches/ | python3 -c "import sys, json; print(' '.join(str(s['id']) for s in json.load(sys.stdin)))")

for id in $switches; do
    echo "更新 Switch $id..."
    curl -s -X POST http://localhost/api/switches/$id/update_stats/
done

echo "✅ 所有 Switch 統計已更新"
```

## 🎓 進階使用

查看完整文檔：
- [Switch 管理功能完整指南](./SWITCH_MANAGEMENT_GUIDE.md)
- [DHCP Option 82 技術說明](../deployment/DHCP_OPTION_82.md)
- [API 參考文檔](../api/SWITCH_API.md)

## 📞 需要幫助？

- 📧 Email: support@network-toolbox.com
- 📖 文檔: https://docs.network-toolbox.com
- 🐛 問題回報: https://github.com/network-toolbox/issues

---

**快速開始版本**：v1.0.0  
**最後更新**：2025-11-02
