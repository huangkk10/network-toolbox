# SSH 服務使用指南

## 概述

`library/services/ssh_service.py` 提供了統一的 SSH 客戶端封裝，用於替代重複的 SSH 連接代碼。

## 功能特點

- ✅ 支援密碼認證和金鑰認證
- ✅ 自動重連機制
- ✅ 統一的命令執行接口
- ✅ Sudo 命令支援
- ✅ SFTP 文件傳輸
- ✅ 上下文管理器（with 語句）
- ✅ 完整的錯誤處理和日誌記錄

## 基本用法

### 1. 使用密碼認證

```python
from library.services import SSHClient

# 創建客戶端
ssh = SSHClient(
    host='192.168.1.1',
    port=22,
    username='admin',
    password='password'
)

# 連接
if ssh.connect():
    # 執行命令
    stdout, stderr, exit_code = ssh.execute_command('ls -la')
    print(stdout)
    
    # 關閉連接
    ssh.close()
```

### 2. 使用金鑰認證

```python
from library.services import SSHClient

ssh = SSHClient(
    host='192.168.1.1',
    username='admin',
    key_file='/path/to/private_key'
)

if ssh.connect():
    stdout, stderr, code = ssh.execute_command('uptime')
    ssh.close()
```

### 3. 使用上下文管理器（推薦）

```python
from library.services import SSHClient

with SSHClient(host='192.168.1.1', username='admin', password='password') as ssh:
    stdout, stderr, code = ssh.execute_command('df -h')
    print(stdout)
# 自動關閉連接
```

### 4. 使用便捷函數

```python
from library.services import ssh_connection

with ssh_connection(host='192.168.1.1', username='admin', password='password') as ssh:
    stdout, stderr, code = ssh.execute_command('hostname')
    print(f'主機名: {stdout.strip()}')
```

### 5. 執行 Sudo 命令

```python
from library.services import SSHClient

with SSHClient(host='192.168.1.1', username='admin', password='password') as ssh:
    # 執行需要 sudo 的命令
    stdout, stderr, code = ssh.execute_sudo_command('systemctl restart nginx')
    
    if code == 0:
        print('服務重啟成功')
    else:
        print(f'失敗: {stderr}')
```

### 6. SFTP 文件傳輸

```python
from library.services import SSHClient

with SSHClient(host='192.168.1.1', username='admin', password='password') as ssh:
    # 獲取 SFTP 客戶端
    sftp = ssh.get_sftp_client()
    
    # 列出目錄
    files = sftp.listdir('/var/log')
    
    # 下載文件
    sftp.get('/remote/file.txt', '/local/file.txt')
    
    # 上傳文件
    sftp.put('/local/file.txt', '/remote/file.txt')
    
    sftp.close()
```

## 遷移指南：現有服務重構

### ssh_powershell_service.py 遷移範例

**Before（現有代碼）：**
```python
class WindowsSSHPowerShellService:
    def __init__(self, dhcp_server):
        self.dhcp_server = dhcp_server
        self.host = dhcp_server.ip_address
        self.port = dhcp_server.ssh_port
        self.username = dhcp_server.ssh_username
        self.password = dhcp_server.ssh_password
        self.key_file = dhcp_server.ssh_key_file
        self.client = None
    
    def connect(self):
        try:
            self.client = paramiko.SSHClient()
            self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            if self.key_file:
                self.client.connect(
                    self.host,
                    port=self.port,
                    username=self.username,
                    key_filename=self.key_file,
                    timeout=10
                )
            else:
                self.client.connect(
                    self.host,
                    port=self.port,
                    username=self.username,
                    password=self.password,
                    timeout=10
                )
            
            logger.info(f'成功連接到 Windows DHCP Server: {self.host}')
            return True
        
        except Exception as e:
            logger.error(f'SSH 連接失敗 ({self.host}): {str(e)}', exc_info=True)
            return False
```

**After（使用新的 SSH 服務）：**
```python
from library.services import SSHClient

class WindowsSSHPowerShellService:
    def __init__(self, dhcp_server):
        self.dhcp_server = dhcp_server
        # 使用統一的 SSH 客戶端
        self.ssh_client = SSHClient(
            host=dhcp_server.ip_address,
            port=dhcp_server.ssh_port,
            username=dhcp_server.ssh_username,
            password=dhcp_server.ssh_password,
            key_file=dhcp_server.ssh_key_file
        )
    
    def connect(self):
        """建立 SSH 連接"""
        return self.ssh_client.connect()
    
    def execute_powershell(self, command):
        """執行 PowerShell 命令"""
        full_command = f'powershell.exe -Command "{command}"'
        stdout, stderr, exit_code = self.ssh_client.execute_command(
            full_command,
            timeout=60
        )
        
        if exit_code == 0:
            return stdout, stderr
        else:
            return None, stderr
```

### ipxe_service.py 遷移範例

**Before：**
```python
def connect_ssh(self):
    try:
        self.ssh_client = paramiko.SSHClient()
        self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        self.ssh_client.connect(
            hostname=self.server.ip_address,
            port=self.server.ssh_port,
            username=self.server.ssh_username,
            password=self.server.ssh_password,
            timeout=10
        )
        
        logger.info(f'成功連接到 IPXE Server: {self.server.ip_address}')
        return True
        
    except Exception as e:
        logger.error(f'SSH 連接失敗 ({self.server.ip_address}): {e}', exc_info=True)
        return False
```

**After：**
```python
from library.services import SSHClient

def __init__(self, server: IPXEServer):
    self.server = server
    self.ssh_client = SSHClient(
        host=server.ip_address,
        port=server.ssh_port,
        username=server.ssh_username,
        password=server.ssh_password
    )

def connect_ssh(self):
    """建立 SSH 連接"""
    return self.ssh_client.connect()

def execute_docker_command(self, container_name: str, command: str = "logs --tail 1000") -> str:
    """執行 Docker 命令"""
    full_command = f"sudo -S docker {command} {container_name}"
    stdout, stderr, exit_code = self.ssh_client.execute_sudo_command(
        f"docker {command} {container_name}",
        sudo_password=self.server.ssh_password
    )
    return stdout
```

## 優點

### 1. 代碼重用
- 消除重複的 SSH 連接代碼
- 統一的錯誤處理和日誌記錄
- 減少維護成本

### 2. 功能增強
- 自動重連機制
- 更好的錯誤處理
- 支援 SFTP 文件傳輸
- 統一的 sudo 命令執行

### 3. 可測試性
- 更容易進行單元測試
- 可以模擬 SSH 連接
- 獨立的測試覆蓋率

### 4. 可擴展性
- 易於添加新功能（如連接池、重試機制）
- 統一的接口便於未來優化

## 測試

```python
# 在 Django shell 中測試
from library.services import SSHClient

# 測試連接
ssh = SSHClient(host='10.250.50.1', username='Administrator', password='your_password')
if ssh.connect():
    print('✅ 連接成功')
    
    # 測試命令執行
    stdout, stderr, code = ssh.execute_command('hostname')
    print(f'主機名: {stdout.strip()}')
    
    ssh.close()
else:
    print('❌ 連接失敗')
```

## 注意事項

1. **向後兼容**：現有代碼可以繼續使用，不需要立即遷移
2. **逐步遷移**：建議在新功能中優先使用新的 SSH 服務
3. **測試充分**：遷移現有代碼前請充分測試
4. **文檔更新**：遷移後記得更新相關文檔

## 下一步

- [ ] 創建連接池管理器
- [ ] 添加自動重連機制
- [ ] 實現 SSH 跳板機支援
- [ ] 添加命令執行結果緩存
