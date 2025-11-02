# Switch 管理功能使用指南

## 📡 功能概述

Network Toolbox 新增了基於 **DHCP Option 82** 的網路交換器管理功能，可以自動識別和管理網路拓撲中的 Switch 設備。

## 🎯 主要功能

### 1. 自動識別 Switch
- 從 DHCP Lease 記錄中提取 Option 82 資訊
- 自動建立 Switch 和端口清單
- 追蹤每個 Switch 的連接設備

### 2. Switch 統計資訊
- 總 Switch 數量
- 活躍/非活躍 Switch
- 連接設備總數
- 端口使用率

### 3. 設備拓撲視圖
- 按 Switch 分組顯示設備
- 按端口顯示連接的設備
- 即時更新連接狀態

## 📊 Web 介面使用

### 訪問 Switch 管理頁面

1. 登入 Network Toolbox
2. 進入 **DHCP Server 分析** 頁面
3. 點擊 **Switch 管理** Tab

### 功能說明

#### Switch 列表 Tab
- **顯示內容**：
  - Switch 名稱和 Remote ID
  - MAC 地址和 IP 地址
  - 狀態（活躍/非活躍/未知）
  - 連接設備數量
  - 活動端口數
  - 最後活動時間

- **操作按鈕**：
  - **同步 Switch**：從 DHCP Lease 記錄同步 Switch 資訊
  - **重新整理**：刷新列表
  - **查看**：查看 Switch 詳細資訊和連接設備

#### Top Switch Tab
- 顯示連接設備最多的前 10 個 Switch
- 適合快速定位網路熱點

#### Switch 詳情 Modal
點擊「查看」按鈕後，顯示：
- Switch 基本資訊
- 連接設備列表（按端口分組）
- 每個端口的設備 IP、MAC、主機名

## 🔧 API 使用

### 1. 獲取 Switch 列表

```bash
# 獲取所有 Switch
curl http://localhost/api/switches/

# 按 DHCP Server 過濾
curl http://localhost/api/switches/?server_id=1

# 按狀態過濾
curl http://localhost/api/switches/?status=active
```

**響應範例**：
```json
[
  {
    "id": 1,
    "name": "Core Switch 1",
    "remote_id": "00:1a:2b:3c:4d:5e",
    "mac_address": "00:1a:2b:3c:4d:5e",
    "ip_address": "10.0.0.1",
    "status": "active",
    "connected_devices": 45,
    "active_ports": 18,
    "total_ports": 24,
    "last_seen": "2025-11-02T10:30:00Z"
  }
]
```

### 2. 獲取 Switch 詳細資訊

```bash
curl http://localhost/api/switches/1/
```

### 3. 獲取 Switch 下的設備

```bash
# 獲取最近 24 小時的設備
curl http://localhost/api/switches/1/devices/

# 自訂時間範圍（最近 48 小時）
curl http://localhost/api/switches/1/devices/?hours=48
```

**響應範例**：
```json
{
  "switch_id": 1,
  "switch_name": "Core Switch 1",
  "remote_id": "00:1a:2b:3c:4d:5e",
  "total_devices": 45,
  "devices_by_port": {
    "gi0/0/1": [
      {
        "id": 101,
        "ip_address": "10.0.1.10",
        "mac_address": "aa:bb:cc:dd:ee:01",
        "hostname": "workstation-01",
        "lease_start": "2025-11-02T08:00:00Z",
        "lease_end": "2025-11-03T08:00:00Z",
        "server_name": "DHCP Server 1"
      }
    ],
    "gi0/0/2": [...]
  }
}
```

### 4. 獲取統計資訊

```bash
# 所有 Server 的統計
curl http://localhost/api/switches/statistics/

# 特定 Server 的統計
curl http://localhost/api/switches/statistics/?server_id=1
```

**響應範例**：
```json
{
  "total_switches": 10,
  "active_switches": 8,
  "inactive_switches": 1,
  "unknown_switches": 1,
  "total_devices": 250,
  "total_ports": 240,
  "active_ports": 180,
  "switches_by_server": [
    {
      "dhcp_server__name": "DHCP Server 1",
      "dhcp_server__id": 1,
      "count": 6
    }
  ],
  "top_switches": [
    {
      "id": 1,
      "name": "Core Switch 1",
      "remote_id": "00:1a:2b:3c:4d:5e",
      "connected_devices": 45,
      "active_ports": 18,
      "status": "active"
    }
  ]
}
```

### 5. 同步 Switch 資訊

```bash
# 從所有 DHCP Lease 同步
curl -X POST http://localhost/api/switches/sync_from_leases/ \
  -H "Content-Type: application/json"

# 從特定 Server 同步最近 48 小時的記錄
curl -X POST http://localhost/api/switches/sync_from_leases/ \
  -H "Content-Type: application/json" \
  -d '{"server_id": 1, "hours": 48}'
```

**響應範例**：
```json
{
  "success": true,
  "message": "同步完成",
  "created": 3,
  "updated": 7,
  "total": 10
}
```

### 6. 更新 Switch 統計

```bash
# 更新單個 Switch 的統計資訊
curl -X POST http://localhost/api/switches/1/update_stats/
```

### 7. 獲取網路拓撲資訊

```bash
# 獲取拓撲資料（適用於 D3.js 等視覺化）
curl http://localhost/api/switches/topology/

# 特定 Server 的拓撲
curl http://localhost/api/switches/topology/?server_id=1
```

**響應範例**：
```json
{
  "nodes": [
    {
      "id": "server_1",
      "name": "DHCP Server 1",
      "type": "dhcp_server",
      "ip": "10.0.0.100",
      "status": "online"
    },
    {
      "id": "switch_1",
      "name": "Core Switch 1",
      "type": "switch",
      "remote_id": "00:1a:2b:3c:4d:5e",
      "status": "active",
      "connected_devices": 45,
      "active_ports": 18
    },
    {
      "id": "devices_1",
      "name": "45 台設備",
      "type": "device_group",
      "count": 45
    }
  ],
  "links": [
    {
      "source": "server_1",
      "target": "switch_1",
      "type": "dhcp_relay"
    },
    {
      "source": "switch_1",
      "target": "devices_1",
      "type": "connection",
      "count": 45
    }
  ]
}
```

## 🔍 DHCP Option 82 說明

### 什麼是 Option 82？

DHCP Option 82（Relay Agent Information）是網路設備在轉發 DHCP 請求時添加的資訊，包含：

- **Sub-option 1 (Circuit ID)**：通常是 Switch 的端口資訊
  - 範例：`gi0/0/1`, `GigabitEthernet0/0/1`, `port-24`
  
- **Sub-option 2 (Remote ID)**：通常是 Switch 的 MAC 地址或唯一識別碼
  - 範例：`00:1a:2b:3c:4d:5e`

### Option 82 格式支援

系統支援以下格式：

1. **已解析格式**：
   ```
   CircuitID=gi0/0/1,RemoteID=00:1a:2b:3c:4d:5e
   ```

2. **Hex 編碼格式**：
   ```
   0x01066769302f302f3102060019e88a4660
   ```

## 📈 資料庫模型

### NetworkSwitch（網路交換器）
- `remote_id`：唯一識別碼（來自 Option 82）
- `name`：Switch 名稱（可自訂）
- `mac_address`：Switch MAC 地址
- `ip_address`：Switch IP 地址
- `status`：狀態（active/inactive/unknown）
- `connected_devices`：連接設備數
- `active_ports`：活動端口數
- `total_ports`：總端口數

### SwitchPort（Switch 端口）
- `switch`：所屬 Switch
- `circuit_id`：端口識別碼（來自 Option 82）
- `port_number`：端口號
- `port_name`：端口名稱（可自訂）
- `status`：狀態（up/down/unknown）
- `connected_devices`：連接設備數

### DHCPLease（擴展）
新增欄位：
- `relay_agent_info`：完整的 Option 82 資訊
- `circuit_id`：Circuit ID（Switch 端口）
- `remote_id`：Remote ID（Switch 識別碼）

### DHCPLog（擴展）
新增欄位：
- `relay_agent_info`：完整的 Option 82 資訊
- `circuit_id`：Circuit ID（Switch 端口）
- `remote_id`：Remote ID（Switch 識別碼）

## 🚀 使用場景

### 1. 網路設備盤點
- 自動發現網路中的所有 Switch
- 追蹤 Switch 的活動狀態
- 統計每個 Switch 的連接設備數量

### 2. 故障排查
- 快速定位設備連接到哪個 Switch 和端口
- 識別異常流量的來源 Switch
- 追蹤設備移動歷史

### 3. 容量規劃
- 分析 Switch 端口使用率
- 識別需要擴充的 Switch
- 優化設備分佈

### 4. 安全審計
- 追蹤未授權設備的接入位置
- 監控特定端口的活動
- 建立設備位置基準線

## 🛠️ 配置需求

### DHCP Server 端

確保 DHCP Server 記錄包含 Option 82 資訊：

**Windows DHCP Server**：
1. 啟用稽核日誌
2. 確保日誌包含完整的 DHCP Options
3. 日誌格式應包含 `RelayAgentInfo` 欄位

**Linux DHCP Server (isc-dhcp-server)**：
```conf
# /etc/dhcp/dhcpd.conf
log-facility local7;
```

### Switch 端

確保 Switch 啟用 DHCP Relay 並添加 Option 82：

**Cisco IOS**：
```
interface GigabitEthernet0/0/1
  ip dhcp snooping information option
```

**HP/Aruba**：
```
dhcp-relay option-82
```

## 📝 最佳實踐

1. **定期同步**：
   - 建議每小時執行一次 `sync_from_leases`
   - 可以使用 Celery 定時任務自動化

2. **自訂 Switch 名稱**：
   - 為 Switch 設定有意義的名稱（如「1樓核心交換器」）
   - 設定實體位置資訊

3. **監控統計**：
   - 定期檢查 Switch 統計資訊
   - 設定告警閾值（如端口使用率 > 80%）

4. **資料清理**：
   - 定期清理非活躍的 Switch 記錄
   - 保留歷史資料用於審計

## 🐛 故障排查

### 問題：Switch 列表為空

**原因**：
- DHCP Lease 記錄中沒有 Option 82 資訊
- Switch 未啟用 DHCP Relay Option 82

**解決方法**：
1. 檢查 DHCP 日誌是否包含 `RelayAgentInfo`
2. 確認 Switch 配置
3. 執行同步操作

### 問題：設備數量不準確

**原因**：
- 統計時間範圍設定不當
- 需要更新統計資訊

**解決方法**：
1. 調整查詢的時間範圍（預設 24 小時）
2. 執行 `update_stats` API 更新統計

### 問題：Option 82 解析失敗

**原因**：
- Option 82 格式不標準
- Hex 編碼問題

**解決方法**：
1. 檢查日誌中的錯誤訊息
2. 查看原始的 `relay_agent_info` 欄位
3. 可能需要擴展解析器以支援特定格式

## 📚 相關文檔

- [DHCP Option 82 RFC 3046](https://www.rfc-editor.org/rfc/rfc3046)
- [Cisco DHCP Snooping Configuration Guide](https://www.cisco.com/c/en/us/td/docs/switches/lan/catalyst9300/software/release/16-12/configuration_guide/sec/b_1612_sec_9300_cg/b_1612_sec_9300_cg_chapter_01001.html)
- [Windows DHCP Server Logging](https://docs.microsoft.com/en-us/windows-server/networking/technologies/dhcp/dhcp-logging)

## 🆕 版本歷史

### v1.0.0 (2025-11-02)
- ✨ 初始版本發布
- 🎯 支援自動識別 Switch
- 📊 Switch 統計和拓撲視圖
- 🔍 設備位置追蹤
- 🌐 完整的 REST API

---

**最後更新**：2025-11-02  
**維護者**：Network Toolbox Team
