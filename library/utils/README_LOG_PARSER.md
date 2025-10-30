# Log 解析器使用指南

統一的日誌解析模組，支援 DHCP、Windows DHCP、iPXE 等多種格式。

---

## 📦 安裝與導入

```python
# 導入解析器類別
from library.utils import (
    DHCPLogParser,
    WindowsDHCPLogParser,
    IPXELogParser,
    LogLevel,
)

# 或使用便捷函數
from library.utils import (
    parse_dhcp_log,
    parse_windows_dhcp_log,
    parse_ipxe_log,
)
```

---

## 🔧 使用方式

### 1. DHCP 日誌解析（Linux/Unix）

#### 方式 A：使用便捷函數（推薦）

```python
from library.utils import parse_dhcp_log

# 讀取日誌檔案
with open('/var/log/dhcpd.log', 'r') as f:
    content = f.read()

# 解析日誌（返回最後 1000 行）
logs = parse_dhcp_log(content, limit=1000)

for log in logs:
    print(f"[{log['level']}] {log['timestamp']}: {log['message']}")
```

#### 方式 B：使用類別方法

```python
from library.utils import DHCPLogParser

# 解析單行
line = "[INFO] 2025-10-27 14:30:22 | DHCPDISCOVER from 00:11:22:33:44:55 via eth0"
entry = DHCPLogParser.parse_line(line)

print(f"時間: {entry['timestamp']}")
print(f"等級: {entry['level']}")
print(f"訊息: {entry['message']}")

# 解析整個檔案
with open('/var/log/dhcpd.log', 'r') as f:
    content = f.read()

entries = DHCPLogParser.parse_file(content, limit=1000)
```

#### 支援的格式

```python
# 格式 1: [LEVEL] timestamp | message
"[INFO] 2025-10-27 14:30:22 | DHCPDISCOVER from 00:11:22:33:44:55"

# 格式 2: timestamp LEVEL message
"2025-10-27 14:30:23 INFO DHCPOFFER of 192.168.1.100"

# 格式 3: syslog - Month Day Time hostname service: message
"Oct 27 14:30:24 server dhcpd[1234]: DHCPREQUEST from 00:11:22:33:44:55"

# 格式 4: timestamp message
"2025-10-27 14:30:25 DHCP lease expired"
```

---

### 2. Windows DHCP 日誌解析

#### 方式 A：使用便捷函數（推薦）

```python
from library.utils import parse_windows_dhcp_log

# 讀取 Windows DHCP 日誌（CSV 格式）
with open('DhcpSrvLog-Mon.log', 'r', encoding='utf-8') as f:
    content = f.read()

# 解析日誌
logs = parse_windows_dhcp_log(content, limit=1000)

for log in logs:
    if 'ip_address' in log:
        print(f"{log['event_type']}: {log['ip_address']} - {log.get('mac_address', 'N/A')}")
        if 'client_type' in log:
            print(f"  客戶端類型: {log['client_type']}")
```

#### 方式 B：使用類別方法

```python
from library.utils import WindowsDHCPLogParser

# 解析單行
line = "11,10/18/25,15:32:59,Renew,10.250.132.27,,BCFCE73A61C9,,727830406,0,,,,0x505845436C69656E74,PXEClient,0x69505845,iPXE"
entry = WindowsDHCPLogParser.parse_line(line)

if entry:
    print(f"事件: {entry['event_type']}")
    print(f"IP: {entry['ip_address']}")
    print(f"MAC: {entry['mac_address']}")
    print(f"客戶端類型: {entry['client_type']}")  # 輸出: iPXE
    print(f"Boot 階段: {entry['boot_stage']}")   # 輸出: iPXE Loading
```

#### 客戶端類型識別

模組自動識別客戶端類型：

```python
entry = WindowsDHCPLogParser.parse_line(log_line)

# 可能的客戶端類型：
# - 'iPXE' - iPXE（User Class 包含 "iPXE"）
# - 'PXE' - BIOS PXE（Vendor Class 包含 "PXEClient"）
# - 'WinPE' - Windows PE（Vendor Class 包含 "MSFT" 或主機名以 "minint-" 開頭）
# - 'OS' - 正常作業系統（有主機名但無 DHCP Options）
# - 'Unknown' - 無法識別

if entry['client_type'] == 'iPXE':
    print(f"偵測到 iPXE 客戶端: {entry['mac_address']}")
```

#### 排序日誌

```python
from library.utils import WindowsDHCPLogParser

# 讀取多個日誌檔案的內容
all_lines = []
for log_file in ['DhcpSrvLog-Mon.log', 'DhcpSrvLog-Tue.log']:
    with open(log_file, 'r', encoding='utf-8') as f:
        all_lines.extend(f.readlines())

# 按時間戳排序
sorted_lines = WindowsDHCPLogParser.sort_by_timestamp(all_lines)

# 解析排序後的日誌
logs = [WindowsDHCPLogParser.parse_line(line) for line in sorted_lines]
logs = [log for log in logs if log]  # 過濾 None
```

---

### 3. iPXE 日誌解析

#### 方式 A：使用便捷函數（推薦）

```python
from library.utils import parse_ipxe_log

# 解析 iPXE Boot 日誌
with open('/var/log/ipxe_boot.log', 'r') as f:
    content = f.read()

boot_logs = parse_ipxe_log(content, log_type='BOOT', limit=1000)

for log in boot_logs:
    print(f"{log['client_ip']}: {log['action']} - {log['file_requested']}")

# 解析 MAC Flask 日誌
with open('/var/log/ipxe_mac.log', 'r') as f:
    content = f.read()

mac_logs = parse_ipxe_log(content, log_type='MAC', limit=1000)

for log in mac_logs:
    if log['mac_address']:
        print(f"MAC 操作: {log['action']} - {log['mac_address']}")
```

#### 方式 B：使用類別方法

```python
from library.utils import IPXELogParser

# 解析 MAC Flask 日誌
mac_line = '10.252.170.188 - - [28/Oct/2025:10:18:24 +0000] "GET /iPxeMac/Set?MAC=10:FF:E0:E2:91:56&BOOT=1 HTTP/1.1" 200 7 "-" "ansible-httpget"'
entry = IPXELogParser.parse_line(mac_line, log_type='MAC')

print(f"動作: {entry['action']}")  # 輸出: set_mac
print(f"MAC: {entry['mac_address']}")  # 輸出: 10:ff:e0:e2:91:56
print(f"Boot Flag: {entry['boot_flag']}")  # 輸出: 1

# 解析 Boot 日誌
boot_line = '10.250.53.25 - - [28/Oct/2025:10:18:57 +0000] "GET /boot.ipxe HTTP/1.1" 200 116 "-" "iPXE/1.21.1+"'
entry = IPXELogParser.parse_line(boot_line, log_type='BOOT')

print(f"檔案: {entry['file_requested']}")  # 輸出: boot.ipxe
print(f"動作: {entry['action']}")  # 輸出: boot.ipxe
```

#### 支援的檔案類型

```python
# 自動識別 action：
# - 'boot.ipxe' - iPXE 啟動腳本
# - 'wimboot' - WIM 啟動載入器
# - 'BCD' - Windows Boot Configuration Data
# - 'boot.sdi' - Windows PE SDI 檔案
# - 'wim_file' - WIM 映像檔（.wim）
# - 'other' - 其他檔案
```

---

## 🎯 進階用法

### 1. 日誌等級過濾

```python
from library.utils import parse_dhcp_log, LogLevel

logs = parse_dhcp_log(content)

# 只顯示錯誤和警告
errors = [log for log in logs if log['level'] in [LogLevel.ERROR, LogLevel.WARN]]

for log in errors:
    print(f"[{log['level']}] {log['message']}")
```

### 2. 自訂解析邏輯

```python
from library.utils import DHCPLogParser

class CustomDHCPParser(DHCPLogParser):
    """自訂 DHCP 解析器"""
    
    @classmethod
    def _infer_log_level(cls, message):
        """自訂等級推斷"""
        # 添加自訂關鍵字
        if 'critical' in message.lower():
            return 'CRITICAL'
        return super()._infer_log_level(message)

# 使用自訂解析器
entry = CustomDHCPParser.parse_line(log_line)
```

### 3. 批量處理多個檔案

```python
from library.utils import parse_windows_dhcp_log
import glob

all_logs = []

# 處理所有 Windows DHCP 日誌檔案
for log_file in glob.glob('C:\\Windows\\System32\\dhcp\\DhcpSrvLog-*.log'):
    with open(log_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    logs = parse_windows_dhcp_log(content, limit=10000)
    all_logs.extend(logs)

print(f"總共處理 {len(all_logs)} 條日誌")
```

### 4. 與 Django 模型整合

```python
from library.utils import parse_ipxe_log
from api.models import IPXELog

# 讀取並解析日誌
with open(log_file, 'r') as f:
    content = f.read()

logs = parse_ipxe_log(content, log_type='BOOT')

# 存入資料庫
for log_data in logs:
    IPXELog.objects.get_or_create(
        client_ip=log_data['client_ip'],
        timestamp=log_data['timestamp'],
        defaults={
            'action': log_data['action'],
            'file_requested': log_data['file_requested'],
            'status_code': log_data['status_code'],
            'raw': log_data['raw'],
        }
    )
```

---

## 🔍 錯誤處理

所有解析器都會優雅處理錯誤：

```python
from library.utils import WindowsDHCPLogParser
import logging

logger = logging.getLogger(__name__)

# 解析可能失敗的日誌
lines = ['valid,log,line', 'invalid line', 'another,valid,line']

parsed_logs = []
for line in lines:
    entry = WindowsDHCPLogParser.parse_line(line)
    if entry:
        parsed_logs.append(entry)
    else:
        logger.warning(f'無法解析日誌: {line}')

print(f'成功解析 {len(parsed_logs)} 條日誌')
```

---

## 📊 性能優化

### 1. 限制返回數量

```python
# 只處理最後 1000 行（減少記憶體使用）
logs = parse_dhcp_log(large_content, limit=1000)
```

### 2. 逐行處理大檔案

```python
from library.utils import DHCPLogParser

with open('huge_log_file.log', 'r') as f:
    for line in f:
        entry = DHCPLogParser.parse_line(line)
        if entry:
            # 立即處理，不累積在記憶體中
            process_entry(entry)
```

---

## 🧪 測試

```bash
# 執行測試
docker exec nt-django python /app/test_log_parser.py

# 或在 Django shell 中測試
docker exec -it nt-django python manage.py shell

>>> from library.utils import parse_dhcp_log
>>> logs = parse_dhcp_log("[INFO] 2025-10-27 14:30:22 | Test message")
>>> print(logs[0])
```

---

## 📚 API 參考

### DHCPLogParser

```python
DHCPLogParser.parse_line(line: str) -> Dict[str, Any]
    解析單行 DHCP 日誌
    
    Returns:
        {
            'timestamp': str,
            'level': str,  # INFO, WARN, ERROR, DEBUG
            'message': str,
            'raw': str
        }

DHCPLogParser.parse_file(content: str, limit: int = 1000) -> List[Dict]
    解析整個日誌檔案
```

### WindowsDHCPLogParser

```python
WindowsDHCPLogParser.parse_line(line: str) -> Optional[Dict[str, Any]]
    解析單行 Windows DHCP 日誌
    
    Returns:
        {
            'event_id': str,
            'event_type': str,
            'timestamp': str,
            'ip_address': str,
            'mac_address': str,
            'hostname': str,
            'client_type': str,  # iPXE, PXE, WinPE, OS, Unknown
            'boot_stage': str,
            'vendor_class': str,
            'user_class': str,
            'message': str,
            'level': str,
            'raw': str
        }

WindowsDHCPLogParser.parse_file(content: str, limit: int = 1000) -> List[Dict]
    解析整個 Windows DHCP 日誌檔案

WindowsDHCPLogParser.sort_by_timestamp(lines: List[str]) -> List[str]
    按時間戳排序日誌行
```

### IPXELogParser

```python
IPXELogParser.parse_line(line: str, log_type: str = 'BOOT') -> Optional[Dict[str, Any]]
    解析單行 iPXE 日誌
    
    Args:
        line: 日誌行
        log_type: 'MAC' 或 'BOOT'
    
    Returns:
        {
            'log_type': str,
            'timestamp': datetime,
            'client_ip': str,
            'method': str,
            'url': str,
            'action': str,
            'status_code': int,
            'bytes_sent': int,
            'user_agent': str,
            'mac_address': str,  # 僅 MAC 類型
            'boot_flag': int,     # 僅 MAC 類型
            'file_requested': str,  # 僅 BOOT 類型
            'raw': str
        }

IPXELogParser.parse_file(content: str, log_type: str = 'BOOT', limit: int = 1000) -> List[Dict]
    解析整個 iPXE 日誌檔案
```

---

## 🔗 相關資源

- **完整報告**：`docs/development/LOG_PARSER_MODULE_REPORT.md`
- **測試代碼**：`backend/test_log_parser.py`
- **原始碼**：`library/utils/log_parser.py`

---

**最後更新**：2025-10-30  
**維護者**：Network Toolbox Team

