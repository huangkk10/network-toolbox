"""
SSH 連接服務模組

提供統一的 SSH 客戶端封裝，支援：
- 密碼認證和金鑰認證
- 自動重連機制
- 命令執行
- 檔案傳輸（SFTP）
- 連接池管理
"""
import paramiko
import logging
from typing import Optional, Tuple, Union
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class SSHClient:
    """
    通用 SSH 客戶端類別
    
    提供簡化的 SSH 連接和命令執行功能，支援密碼和金鑰認證。
    """
    
    def __init__(
        self,
        host: str,
        port: int = 22,
        username: str = 'root',
        password: Optional[str] = None,
        key_file: Optional[str] = None,
        timeout: int = 10,
        auto_add_host_key: bool = True
    ):
        """
        初始化 SSH 客戶端
        
        Args:
            host: SSH 伺服器地址
            port: SSH 端口（預設 22）
            username: 用戶名
            password: 密碼（密碼認證時使用）
            key_file: SSH 金鑰檔案路徑（金鑰認證時使用）
            timeout: 連接超時時間（秒）
            auto_add_host_key: 是否自動添加主機金鑰
        """
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.key_file = key_file
        self.timeout = timeout
        self.auto_add_host_key = auto_add_host_key
        self.client: Optional[paramiko.SSHClient] = None
        self._is_connected = False
    
    def connect(self) -> bool:
        """
        建立 SSH 連接
        
        Returns:
            bool: 連接成功返回 True，失敗返回 False
        
        Examples:
            >>> ssh = SSHClient('192.168.1.1', username='admin', password='password')
            >>> if ssh.connect():
            ...     print('連接成功')
            ...     ssh.close()
        """
        try:
            self.client = paramiko.SSHClient()
            
            # 設置主機金鑰政策
            if self.auto_add_host_key:
                self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            else:
                self.client.load_system_host_keys()
            
            # 建立連接
            connect_kwargs = {
                'hostname': self.host,
                'port': self.port,
                'username': self.username,
                'timeout': self.timeout,
            }
            
            # 根據認證方式添加相應參數
            if self.key_file:
                connect_kwargs['key_filename'] = self.key_file
                logger.info(f'使用金鑰認證連接到 {self.host}:{self.port}')
            else:
                connect_kwargs['password'] = self.password
                logger.info(f'使用密碼認證連接到 {self.host}:{self.port}')
            
            self.client.connect(**connect_kwargs)
            self._is_connected = True
            
            logger.info(f'✅ SSH 連接成功: {self.host}:{self.port}')
            return True
        
        except paramiko.AuthenticationException:
            logger.error(f'❌ SSH 認證失敗: {self.host}:{self.port}')
            return False
        except paramiko.SSHException as e:
            logger.error(f'❌ SSH 連接錯誤 ({self.host}:{self.port}): {e}', exc_info=True)
            return False
        except Exception as e:
            logger.error(f'❌ 連接失敗 ({self.host}:{self.port}): {e}', exc_info=True)
            return False
    
    def execute_command(
        self,
        command: str,
        timeout: Optional[int] = None,
        get_pty: bool = False
    ) -> Tuple[str, str, int]:
        """
        執行 SSH 命令
        
        Args:
            command: 要執行的命令
            timeout: 命令執行超時時間（秒），None 表示使用預設值
            get_pty: 是否請求偽終端（適用於需要 sudo 的命令）
        
        Returns:
            Tuple[str, str, int]: (stdout, stderr, exit_code)
        
        Raises:
            ConnectionError: 未建立連接時拋出
        
        Examples:
            >>> ssh = SSHClient('192.168.1.1', username='admin', password='password')
            >>> ssh.connect()
            >>> stdout, stderr, code = ssh.execute_command('ls -la')
            >>> print(stdout)
            >>> ssh.close()
        """
        if not self.is_connected():
            raise ConnectionError(f'未連接到 {self.host}')
        
        try:
            logger.debug(f'執行命令: {command[:100]}...')
            
            stdin, stdout, stderr = self.client.exec_command(
                command,
                timeout=timeout or self.timeout,
                get_pty=get_pty
            )
            
            # 讀取輸出
            stdout_data = stdout.read().decode('utf-8', errors='ignore')
            stderr_data = stderr.read().decode('utf-8', errors='ignore')
            exit_code = stdout.channel.recv_exit_status()
            
            if exit_code != 0:
                logger.warning(f'命令執行返回非零狀態碼 {exit_code}: {command[:50]}')
            
            logger.debug(f'命令執行完成，輸出長度: {len(stdout_data)} bytes')
            return stdout_data, stderr_data, exit_code
        
        except Exception as e:
            error_msg = f'命令執行失敗: {e}'
            logger.error(error_msg, exc_info=True)
            return '', error_msg, -1
    
    def execute_sudo_command(
        self,
        command: str,
        sudo_password: Optional[str] = None,
        timeout: Optional[int] = None
    ) -> Tuple[str, str, int]:
        """
        執行需要 sudo 的命令
        
        Args:
            command: 要執行的命令（不需要包含 sudo 前綴）
            sudo_password: sudo 密碼（如果為 None，使用初始化時的密碼）
            timeout: 命令執行超時時間（秒）
        
        Returns:
            Tuple[str, str, int]: (stdout, stderr, exit_code)
        
        Examples:
            >>> ssh = SSHClient('192.168.1.1', username='admin', password='password')
            >>> ssh.connect()
            >>> stdout, stderr, code = ssh.execute_sudo_command('systemctl restart nginx')
            >>> ssh.close()
        """
        if not self.is_connected():
            raise ConnectionError(f'未連接到 {self.host}')
        
        try:
            sudo_pass = sudo_password or self.password
            full_command = f'sudo -S {command}'
            
            logger.debug(f'執行 sudo 命令: {command[:100]}...')
            
            stdin, stdout, stderr = self.client.exec_command(
                full_command,
                timeout=timeout or self.timeout,
                get_pty=True
            )
            
            # 發送 sudo 密碼
            if sudo_pass:
                stdin.write(sudo_pass + '\n')
                stdin.flush()
            
            # 讀取輸出
            stdout_data = stdout.read().decode('utf-8', errors='ignore')
            stderr_data = stderr.read().decode('utf-8', errors='ignore')
            exit_code = stdout.channel.recv_exit_status()
            
            # 過濾掉 sudo 提示信息
            lines = stdout_data.split('\n')
            filtered_lines = [
                line for line in lines 
                if 'password' not in line.lower() and 'sudo' not in line.lower() or line.strip()
            ]
            stdout_data = '\n'.join(filtered_lines)
            
            return stdout_data, stderr_data, exit_code
        
        except Exception as e:
            error_msg = f'Sudo 命令執行失敗: {e}'
            logger.error(error_msg, exc_info=True)
            return '', error_msg, -1
    
    def get_sftp_client(self) -> paramiko.SFTPClient:
        """
        獲取 SFTP 客戶端
        
        Returns:
            paramiko.SFTPClient: SFTP 客戶端實例
        
        Raises:
            ConnectionError: 未建立連接時拋出
        
        Examples:
            >>> ssh = SSHClient('192.168.1.1', username='admin', password='password')
            >>> ssh.connect()
            >>> sftp = ssh.get_sftp_client()
            >>> sftp.listdir('/')
            >>> sftp.close()
            >>> ssh.close()
        """
        if not self.is_connected():
            raise ConnectionError(f'未連接到 {self.host}')
        
        try:
            return self.client.open_sftp()
        except Exception as e:
            logger.error(f'創建 SFTP 客戶端失敗: {e}', exc_info=True)
            raise
    
    def is_connected(self) -> bool:
        """
        檢查是否已連接
        
        Returns:
            bool: 已連接返回 True，否則返回 False
        """
        if not self.client or not self._is_connected:
            return False
        
        try:
            # 測試連接是否有效
            transport = self.client.get_transport()
            return transport is not None and transport.is_active()
        except Exception:
            return False
    
    def close(self):
        """關閉 SSH 連接"""
        if self.client:
            try:
                self.client.close()
                logger.info(f'SSH 連接已關閉: {self.host}:{self.port}')
            except Exception as e:
                logger.error(f'關閉 SSH 連接失敗: {e}')
            finally:
                self.client = None
                self._is_connected = False
    
    def __enter__(self):
        """支援 with 語句（上下文管理器）"""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """自動關閉連接"""
        self.close()
    
    def __del__(self):
        """析構函數，確保連接被關閉"""
        self.close()


@contextmanager
def ssh_connection(
    host: str,
    port: int = 22,
    username: str = 'root',
    password: Optional[str] = None,
    key_file: Optional[str] = None,
    timeout: int = 10
):
    """
    SSH 連接上下文管理器
    
    使用 with 語句自動管理 SSH 連接的建立和關閉
    
    Args:
        host: SSH 伺服器地址
        port: SSH 端口
        username: 用戶名
        password: 密碼
        key_file: SSH 金鑰檔案路徑
        timeout: 連接超時時間
    
    Yields:
        SSHClient: SSH 客戶端實例
    
    Examples:
        >>> with ssh_connection('192.168.1.1', username='admin', password='password') as ssh:
        ...     stdout, stderr, code = ssh.execute_command('ls -la')
        ...     print(stdout)
    """
    client = SSHClient(
        host=host,
        port=port,
        username=username,
        password=password,
        key_file=key_file,
        timeout=timeout
    )
    
    try:
        if client.connect():
            yield client
        else:
            raise ConnectionError(f'無法連接到 {host}:{port}')
    finally:
        client.close()
