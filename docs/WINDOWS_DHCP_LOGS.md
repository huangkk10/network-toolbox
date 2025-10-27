# Windows DHCP Server 日誌整合

## 📋 概述

本文檔說明如何從 Windows DHCP Server 讀取真實的 DHCP 日誌。

## 🔧 技術架構

### 日誌來源
- **Windows DHCP Server 日誌位置**：`C:\Windows\System32\dhcp\DhcpSrvLog-*.log`
- **日誌格式**：CSV 格式，每週一個檔案（Mon, Tue, Wed, Thu, Fri, Sat, Sun）

### 讀取方式
- **傳輸協議**：SSH (OpenSSH for Windows)
- **執行命令**：PowerShell `Get-Content`
- **解析器**：`WindowsDHCPLogParser`

## 📊 Windows DHCP 日誌格式

### 日誌欄位結構

```
EventID,Date,Time,Description,IPAddress,HostName,MACAddress,...
```

### 事件代碼對應表

| 代碼 | 事件類型 | 說明 | 日誌等級 |
|------|---------|------|---------|
| 00 | Start | 日誌服務啟動 | INFO |
| 01 | Stop | 日誌服務停止 | INFO |
| 10 | Assign | 新租約分配 | INFO |
| 11 | Renew | 租約更新 | INFO |
| 12 | Release | 租約釋放 | INFO |
| 13 | Deny | 拒絕請求 | WARN |
| 14 | Conflict | IP 衝突 | ERROR |
| 20 | DNS | DNS 記錄更新 | DEBUG |
| 30 | NAP | DNS 更新請求 | DEBUG |
| 31 | DNS Fail | DNS 更新失敗 | WARN |

### 日誌範例

```csv
11,10/27/25,17:03:37,Renew,10.250.52.18,PC-SSD-5824,A0AD9F02A039,,3281646423,0
31,10/27/25,17:03:37,DNS Update Failed,10.250.52.18,WIN-0RB6C3OL9HL,,,0,6,,,,,,,,,10054
10,10/27/25,17:04:20,Assign,10.250.50.40,DESKTOP-OHVNO4B,D85ED385CC10,,0,0
```

## 🚀 使用方法

### 1. 透過 Python API

```python
from api.models import DHCPServer
from api.services import DHCPLogService

# 取得 DHCP Server
server = DHCPServer.objects.get(ip_address='10.250.50.1')

# 創建日誌服務
log_service = DHCPLogService(server)

# 讀取遠端日誌
logs = log_service.get_remote_logs(
    limit=100,           # 最多返回 100 筆
    level='WARN',        # 篩選警告等級
    keyword='DNS',       # 關鍵字篩選
)

# 處理日誌
for log in logs:
    print(f"[{log['level']}] {log['timestamp']} - {log['message']}")
```

### 2. 透過 REST API

```bash
# 讀取遠端 Windows DHCP 日誌
curl "http://localhost/api/dhcp-analytics/logs/?server=1&source=remote&limit=50"

# 篩選特定等級
curl "http://localhost/api/dhcp-analytics/logs/?server=1&source=remote&level=WARN"

# 關鍵字搜尋
curl "http://localhost/api/dhcp-analytics/logs/?server=1&source=remote&keyword=DNS"

# 時間範圍篩選
curl "http://localhost/api/dhcp-analytics/logs/?server=1&source=remote&start_time=2025-10-27 16:00:00&end_time=2025-10-27 18:00:00"
```

### 3. 透過前端 UI

1. 進入 **DHCP Server 分析** 頁面
2. 選擇 **日誌查看** 分頁
3. 點擊 **遠端 SSH** 按鈕
4. 選擇要查看的 Server
5. 設定篩選條件（等級、關鍵字、時間範圍）
6. 點擊 **重新載入** 按鈕

## 🔍 日誌解析示例

### 原始日誌
```
11,10/27/25,17:03:37,Renew,10.250.52.18,PC-SSD-5824,A0AD9F02A039,,3281646423,0
```

### 解析後的 JSON
```json
{
    "timestamp": "2025-10-27 17:03:37",
    "level": "INFO",
    "event": "Renew",
    "message": "DHCPREQUEST for 10.250.52.18 from a0:ad:9f:02:a0:39 via eth0",
    "raw": "11,10/27/25,17:03:37,Renew,10.250.52.18,PC-SSD-5824,A0AD9F02A039,,3281646423,0"
}
```

## 🛠️ 實作細節

### WindowsSSHPowerShellService 新增方法

```python
def get_dhcp_logs(self, limit=100, log_date=None):
    """
    從 Windows DHCP Server 讀取日誌檔案
    
    Args:
        limit: 返回的日誌行數限制
        log_date: 指定日期 ('Mon', 'Tue', etc.)，預設為今天
    
    Returns:
        list: 日誌內容列表
    """
    # 自動判斷今天的日誌檔案
    days_of_week = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
    today = datetime.now().weekday()
    log_date = days_of_week[today]
    
    log_file = f'DhcpSrvLog-{log_date}.log'
    log_path = f'C:\\Windows\\System32\\dhcp\\{log_file}'
    
    # 使用 PowerShell 讀取日誌
    ps_command = f'Get-Content -Path "{log_path}" -Tail {limit}'
    output, error = self.execute_powershell(ps_command)
    
    return output.strip().split('\n')
```

### WindowsDHCPLogParser

```python
class WindowsDHCPLogParser:
    """Windows DHCP Server 日誌解析器"""
    
    EVENT_TYPES = {
        '10': 'Assign',
        '11': 'Renew',
        '12': 'Release',
        '13': 'Deny',
        '14': 'Conflict',
        # ... 更多事件類型
    }
    
    @staticmethod
    def parse_log_lines(lines, limit=100):
        """解析日誌行並轉換為標準格式"""
        logs = []
        
        for line in lines:
            fields = line.split(',')
            event_id = fields[0].strip()
            
            # 根據事件類型解析不同欄位
            if event_id in ['10', '11', '12', '13']:
                ip_address = fields[4].strip()
                hostname = fields[5].strip()
                mac_address = fields[6].strip().replace('-', ':').lower()
                
                # 格式化訊息
                message = f'DHCPREQUEST for {ip_address} from {mac_address} via eth0'
                level = 'WARN' if event_id == '13' else 'INFO'
            
            logs.append({
                'timestamp': timestamp,
                'level': level,
                'event': event_type,
                'message': message,
                'raw': line,
            })
        
        return logs
```

## 📈 效能考量

### 讀取效能
- **SSH 連接**：~1 秒
- **讀取 100 行日誌**：~0.3 秒
- **解析 100 筆記錄**：~0.1 秒
- **總計**：約 1.5 秒

### 快取建議
- 前端可以快取最近的日誌（5 分鐘）
- 減少頻繁的 SSH 連接
- 使用自動重新載入（可選）

## 🔧 故障排查

### 1. 無法讀取日誌

**問題**：API 返回空陣列

**檢查**：
```bash
# 確認 SSH 連接
docker exec nt-django python manage.py shell << 'EOF'
from api.models import DHCPServer
from api.ssh_powershell_service import WindowsSSHPowerShellService

server = DHCPServer.objects.get(ip_address='10.250.50.1')
with WindowsSSHPowerShellService(server) as service:
    files = service.list_available_log_files()
    print(files)
EOF
```

**解決**：
- 確認 Windows DHCP Server 的 OpenSSH Service 正在運行
- 確認日誌目錄權限：`C:\Windows\System32\dhcp\`
- 確認 DHCP Server 服務正在運行

### 2. 日誌格式錯誤

**問題**：解析失敗或顯示異常

**檢查**：
```python
# 查看原始日誌內容
logs = service.get_dhcp_logs(limit=5)
for line in logs:
    print(repr(line))
```

**解決**：
- Windows DHCP 日誌格式可能因版本而異
- 檢查 `WindowsDHCPLogParser` 的欄位對應
- 更新事件代碼對應表

### 3. 權限問題

**錯誤訊息**：`Access is denied`

**解決**：
- 確認 SSH 使用者有讀取 `C:\Windows\System32\dhcp\` 的權限
- 建議使用 Administrator 帳號
- 或調整 DHCP 日誌目錄的 ACL 權限

## 🎯 最佳實踐

1. **定期同步**：建議每 5-10 分鐘自動重新載入日誌
2. **篩選優先**：使用等級篩選減少傳輸資料量
3. **分析模式**：
   - 即時監控：查看最近 50 筆
   - 問題排查：使用時間範圍 + 關鍵字
   - 統計分析：匯出更多資料進行離線分析

## 📚 相關文件

- [SSH_WINDOWS_DHCP_SYNC.md](./SSH_WINDOWS_DHCP_SYNC.md) - SSH 同步設定
- [API 文件](../backend/api/README.md) - API 使用說明
- [前端整合](../frontend/README.md) - 前端顯示實作

---

**最後更新**：2025-10-27  
**版本**：1.0.0  
**維護者**：Network Toolbox Team
