"""
Ansible Inventory 管理服務

提供 Ansible Inventory 文件的導入、解析、驗證、生成和儲存功能。
"""

import os
import re
import subprocess
import json
import shutil
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class AnsibleInventoryService:
    """Ansible Inventory 管理服務"""
    
    # NAS IP 到掛載點的映射表
    NAS_MOUNT_MAP = {
        '10.250.0.1': '/mnt/mdt',
        '10.8.246.11': '/mnt/nas_10.8.246.11',
    }
    
    def __init__(self, nas_base_path: str = '/mnt/mdt'):
        """
        初始化服務
        
        Args:
            nas_base_path: NAS 掛載的基礎路徑（預設 /mnt/mdt，作為未知 NAS 的後備）
        """
        self.nas_base_path = nas_base_path
        logger.info(f"AnsibleInventoryService initialized with nas_base_path: {nas_base_path}")
    
    def convert_windows_path_to_linux(self, windows_path: str) -> str:
        """
        將 Windows 網路路徑轉換為 Linux 掛載路徑
        
        範例:
            \\\\10.250.0.1\\mdt\\Script\\test -> /mnt/mdt/Script/test
            \\10.8.246.11\mdt\Script\test -> /mnt/nas_10.8.246.11/Script/test
        
        Args:
            windows_path: Windows 格式的路徑
            
        Returns:
            Linux 格式的路徑
        """
        logger.debug(f"Converting Windows path: {windows_path}")
        
        # 統一使用正斜線
        path = windows_path.replace('\\', '/')
        logger.debug(f"After replacing backslashes: {path}")
        
        # 提取 NAS IP 地址
        ip_match = re.match(r'^//([\d\.]+)/', path)
        nas_ip = ip_match.group(1) if ip_match else None
        logger.debug(f"Extracted NAS IP: {nas_ip}")
        
        # 根據 NAS IP 選擇掛載點
        if nas_ip and nas_ip in self.NAS_MOUNT_MAP:
            mount_point = self.NAS_MOUNT_MAP[nas_ip]
            logger.debug(f"Using mount point for {nas_ip}: {mount_point}")
        else:
            mount_point = self.nas_base_path
            logger.debug(f"Using default mount point: {mount_point}")
        
        # 移除開頭的網路路徑格式
        # 範例: //10.250.0.1/mdt/Script/test -> Script/test
        # 支援格式: //IP/mdt/... 或 //IP/share/mdt/...
        path = re.sub(r'^//[\d\.]+/[^/]+/', '', path)
        logger.debug(f"After removing network prefix: {path}")
        
        # 如果路徑開頭還是 '/'，移除它
        if path.startswith('/'):
            path = path.lstrip('/')
        
        # 組合完整路徑
        linux_path = os.path.join(mount_point, path)
        
        logger.info(f"Converted Windows path '{windows_path}' to Linux path '{linux_path}'")
        return linux_path
    
    def import_from_nas(
        self, 
        nas_path: str, 
        file_name: str = 'hosts'
    ) -> Tuple[bool, str, Dict]:
        """
        從 NAS 導入 Inventory 文件
        
        Args:
            nas_path: NAS 路徑（Windows 格式）
            file_name: 檔案名稱（預設 'hosts'）
        
        Returns:
            Tuple[success, error_message, parsed_data]
            - success: 是否成功
            - error_message: 錯誤訊息（成功時為空字串）
            - parsed_data: 解析後的數據（包含 hosts, groups, total_hosts, total_groups）
        """
        try:
            # 轉換路徑
            linux_path = self.convert_windows_path_to_linux(nas_path)
            
            # 智能處理路徑：如果 nas_path 已經包含檔案名稱，就不再拼接
            if linux_path.endswith(f'/{file_name}') or linux_path.endswith(f'\\{file_name}'):
                full_path = linux_path
                logger.info(f"nas_path already contains file_name, using: {full_path}")
            else:
                full_path = os.path.join(linux_path, file_name)
                logger.info(f"Joining nas_path and file_name: {full_path}")
            
            logger.info(f"Attempting to import inventory from: {full_path}")
            
            # 檢查文件是否存在
            if not os.path.exists(full_path):
                error_msg = f"文件不存在: {full_path}"
                logger.error(error_msg)
                return False, error_msg, {}
            
            # 基本檔案檢查（不進行嚴格的語法驗證）
            try:
                with open(full_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                # 簡單檢查：確保文件不是空的
                if not content.strip():
                    error_msg = "文件內容為空"
                    logger.error(error_msg)
                    return False, error_msg, {}
                
                logger.info(f"File loaded successfully: {len(content)} characters")
                
            except Exception as e:
                error_msg = f"無法讀取文件: {str(e)}"
                logger.error(error_msg, exc_info=True)
                return False, error_msg, {}
            
            # 嘗試解析 Inventory（使用寬鬆模式）
            # 注意：即使有語法錯誤，也嘗試導入，讓驗證階段來處理
            try:
                parsed_data = self.parse_inventory(full_path)
            except Exception as e:
                logger.warning(f"Parse inventory with errors: {e}")
                # 即使解析失敗，也回傳部分數據，允許導入
                parsed_data = {
                    'hosts': [],
                    'groups': {},
                    'total_hosts': 0,
                    'total_groups': 0,
                    'parse_error': str(e)
                }
            
            logger.info(f"Successfully imported inventory: {parsed_data.get('total_hosts', 0)} hosts, {parsed_data.get('total_groups', 0)} groups")
            return True, "", parsed_data
            
        except Exception as e:
            error_msg = f"導入失敗: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return False, error_msg, {}
    
    def validate_syntax(self, inventory_path: str) -> Tuple[bool, Optional[str]]:
        """
        使用 ansible-inventory 驗證語法
        
        注意：ansible-inventory 在遇到語法錯誤時：
        - exit code 仍然是 0（不會報錯退出）
        - 但會在 stderr 輸出 WARNING 或錯誤訊息
        - 因此需要檢查 stderr 內容來判斷是否有錯誤
        
        Args:
            inventory_path: Inventory 文件的完整路徑
        
        Returns:
            Tuple[is_valid, error_message]
            - is_valid: 語法是否有效
            - error_message: 錯誤訊息（有效時為 None）
        """
        try:
            logger.debug(f"Validating syntax for: {inventory_path}")
            
            # 使用環境變數強制 Ansible 使用 INI 插件，避免將文件當作腳本執行
            env = os.environ.copy()
            env['ANSIBLE_INVENTORY_ENABLED'] = 'ini,yaml'  # 只啟用 ini 和 yaml 插件
            
            result = subprocess.run(
                ['ansible-inventory', '-i', inventory_path, '--list'],
                capture_output=True,
                text=True,
                timeout=30,
                env=env  # 使用修改後的環境變數
            )
            
            # 檢查 returncode（雖然通常是 0）
            if result.returncode != 0:
                logger.warning(f"ansible-inventory command failed with return code {result.returncode}")
                return False, result.stderr
            
            # **重點：檢查 stderr 是否包含錯誤訊息**
            # Ansible 會在 stderr 輸出 WARNING 或錯誤
            stderr_lower = result.stderr.lower()
            error_indicators = [
                'failed to parse',
                'invalid section',
                'expected key=value',
                'not enough values to unpack',
                'unable to parse',
                'yaml parsing failed',           # Jinja2 變數未加引號會觸發此錯誤
                'mapping values are not allowed', # Jinja2 變數未加引號的典型錯誤
                'could not match',
                'syntax error',
                'error parsing',
                '[error]',
            ]
            
            has_error = any(indicator in stderr_lower for indicator in error_indicators)
            
            if has_error:
                # 清理錯誤訊息，移除顏色代碼和多餘的換行
                error_msg = result.stderr.strip()
                # 移除 ANSI 顏色代碼
                import re
                error_msg = re.sub(r'\x1b\[[0-9;]*m', '', error_msg)
                
                # 提取有意義的錯誤行
                error_lines = []
                for line in error_msg.split('\n'):
                    line_lower = line.lower()
                    if any(keyword in line_lower for keyword in [
                        'warning', 'error', 'failed', 'caused by', 
                        'yaml parsing', 'mapping values'
                    ]):
                        error_lines.append(line.strip())
                
                if error_lines:
                    error_msg = '\n'.join(error_lines[:5])  # 最多顯示前 5 行
                
                # 如果是 Jinja2 相關的 YAML 解析錯誤，提供更友好的提示
                if 'yaml parsing' in error_msg.lower() or 'mapping values' in error_msg.lower():
                    error_msg += "\n\n💡 提示: 這個錯誤通常是因為 Jinja2 變數 {{ ... }} 沒有用引號包起來。\n" \
                                 "例如: saf_comment_full={{ var }} 應該改為 saf_comment_full=\"{{ var }}\""
                
                logger.warning(f"Ansible inventory syntax error detected: {error_msg}")
                return False, error_msg
            
            # 嘗試解析 JSON 輸出
            try:
                json.loads(result.stdout)
                logger.debug("Syntax validation passed")
                return True, None
            except json.JSONDecodeError as e:
                error_msg = f"JSON 解析錯誤: {str(e)}"
                logger.error(error_msg)
                return False, error_msg
            
        except subprocess.TimeoutExpired:
            error_msg = "語法驗證超時（30秒）"
            logger.error(error_msg)
            return False, error_msg
        except FileNotFoundError:
            error_msg = "找不到 ansible-inventory 命令，請確認 Ansible 已安裝"
            logger.error(error_msg)
            return False, error_msg
        except Exception as e:
            error_msg = f"驗證失敗: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return False, error_msg
    
    def parse_inventory(self, inventory_path: str) -> Dict:
        """
        解析 Inventory 文件，提取所有 Host 和變數
        
        Args:
            inventory_path: Inventory 文件的完整路徑
        
        Returns:
            Dict 包含:
            {
                'hosts': List[Dict],  # Host 配置列表
                'groups': Dict,       # Group 名稱 -> Host 列表的映射
                'total_hosts': int,   # 總 Host 數量
                'total_groups': int   # 總 Group 數量
            }
        """
        try:
            logger.info(f"Parsing inventory file: {inventory_path}")
            
            # 使用環境變數強制 Ansible 使用 INI 插件
            env = os.environ.copy()
            env['ANSIBLE_INVENTORY_ENABLED'] = 'ini,yaml'
            
            result = subprocess.run(
                ['ansible-inventory', '-i', inventory_path, '--list'],
                capture_output=True,
                text=True,
                timeout=30,
                env=env
            )
            
            # 檢查命令執行狀態
            if result.returncode != 0:
                error_msg = result.stderr if result.stderr else "未知錯誤"
                logger.warning(f"ansible-inventory 命令失敗: {error_msg}")
                return {
                    'hosts': [],
                    'groups': {},
                    'total_hosts': 0,
                    'total_groups': 0,
                    'parse_error': error_msg
                }
            
            # 嘗試解析 JSON 輸出
            try:
                inventory_data = json.loads(result.stdout)
            except json.JSONDecodeError as e:
                logger.warning(f"JSON parsing failed: {e}")
                return {
                    'hosts': [],
                    'groups': {},
                    'total_hosts': 0,
                    'total_groups': 0,
                    'parse_error': f"JSON 解析錯誤: {str(e)}"
                }
            
            # 提取 Host 資訊
            hosts = []
            groups = {}
            
            # 解析 _meta.hostvars
            hostvars = inventory_data.get('_meta', {}).get('hostvars', {})
            
            for hostname, vars_dict in hostvars.items():
                # 提取標準 Ansible 變數
                host_info = {
                    'hostname': hostname,
                    'ansible_host': vars_dict.get('ansible_host'),
                    'ansible_user': vars_dict.get('ansible_user'),
                    'ansible_password': vars_dict.get('ansible_password'),
                    'ansible_port': vars_dict.get('ansible_port', 22),
                    'mac_address': vars_dict.get('mac_address'),
                    'uart_host': vars_dict.get('uart_host'),
                    'groups': []
                }
                
                # 提取其他自訂變數
                excluded_keys = [
                    'ansible_host', 'ansible_user', 'ansible_password',
                    'ansible_port', 'mac_address', 'uart_host'
                ]
                host_info['other_vars'] = {
                    k: v for k, v in vars_dict.items()
                    if k not in excluded_keys
                }
                
                hosts.append(host_info)
            
            # 解析 Groups
            for group_name, group_data in inventory_data.items():
                if group_name in ['_meta', 'all']:
                    continue
                
                group_hosts = group_data.get('hosts', [])
                groups[group_name] = group_hosts
                
                # 為每個 Host 添加所屬 Groups
                for host_name in group_hosts:
                    for host in hosts:
                        if host['hostname'] == host_name:
                            host['groups'].append(group_name)
                            break
            
            result_data = {
                'hosts': hosts,
                'groups': groups,
                'total_hosts': len(hosts),
                'total_groups': len(groups)
            }
            
            logger.info(f"Parsed {result_data['total_hosts']} hosts in {result_data['total_groups']} groups")
            return result_data
            
        except subprocess.TimeoutExpired:
            logger.warning("Parsing timeout (30s)")
            return {
                'hosts': [],
                'groups': {},
                'total_hosts': 0,
                'total_groups': 0,
                'parse_error': '解析 Inventory 超時（30秒）'
            }
        except Exception as e:
            logger.warning(f"Parsing failed with exception: {e}", exc_info=True)
            return {
                'hosts': [],
                'groups': {},
                'total_hosts': 0,
                'total_groups': 0,
                'parse_error': f'解析 Inventory 失敗: {str(e)}'
            }
    
    def create_backup(self, original_file_path: str) -> str:
        """
        創建備份檔案
        
        Args:
            original_file_path: 原始文件路徑
        
        Returns:
            備份文件路徑
        """
        timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        
        # 備份檔名格式: .backup.hosts.2025-12-02_05-08-18
        # 以點開頭，Ansible 會忽略這些檔案，不會誤認為 inventory
        directory = os.path.dirname(original_file_path)
        filename = os.path.basename(original_file_path)
        backup_filename = f".backup.{filename}.{timestamp}"
        backup_path = os.path.join(directory, backup_filename)
        
        try:
            shutil.copy2(original_file_path, backup_path)
            logger.info(f"Created backup: {backup_path}")
            return backup_path
        except Exception as e:
            logger.error(f"Failed to create backup: {e}", exc_info=True)
            raise Exception(f"創建備份失敗: {str(e)}")
    
    def generate_inventory_content(self, hosts_config: List[Dict]) -> str:
        """
        從 Host 配置生成 Ansible Inventory 格式內容
        
        Args:
            hosts_config: Host 配置字典列表
        
        Returns:
            Ansible Inventory 格式的字串
        """
        try:
            logger.debug(f"Generating inventory content for {len(hosts_config)} hosts")
            
            # 組織 Groups
            groups_dict = {}
            for host in hosts_config:
                for group in host.get('groups', []):
                    if group not in groups_dict:
                        groups_dict[group] = []
                    groups_dict[group].append(host)
            
            # 生成內容
            lines = []
            
            for group_name, group_hosts in sorted(groups_dict.items()):
                lines.append(f"[{group_name}]")
                
                for host in sorted(group_hosts, key=lambda h: h['hostname']):
                    # 基本 Host 行
                    host_line = host['hostname']
                    
                    # 添加變數
                    if host.get('ansible_host'):
                        host_line += f" ansible_host={host['ansible_host']}"
                    if host.get('ansible_user'):
                        host_line += f" ansible_user={host['ansible_user']}"
                    if host.get('ansible_password'):
                        host_line += f" ansible_password={host['ansible_password']}"
                    if host.get('ansible_port') and host['ansible_port'] != 22:
                        host_line += f" ansible_port={host['ansible_port']}"
                    if host.get('mac_address'):
                        host_line += f" mac_address={host['mac_address']}"
                    if host.get('uart_host'):
                        host_line += f" uart_host={host['uart_host']}"
                    
                    # 添加其他變數
                    for key, value in host.get('other_vars', {}).items():
                        if isinstance(value, str):
                            host_line += f" {key}={value}"
                        else:
                            host_line += f" {key}={json.dumps(value)}"
                    
                    lines.append(host_line)
                
                lines.append("")  # 空行分隔 Groups
            
            content = "\n".join(lines)
            logger.debug(f"Generated inventory content: {len(content)} characters")
            return content
            
        except Exception as e:
            logger.error(f"Failed to generate inventory content: {e}", exc_info=True)
            raise Exception(f"生成 Inventory 內容失敗: {str(e)}")
    
    def save_to_nas(
        self,
        inventory_path: str,
        content: str,
        create_backup: bool = True
    ) -> Tuple[bool, str, Optional[str]]:
        """
        儲存 Inventory 到 NAS
        
        Args:
            inventory_path: Inventory 文件路徑
            content: 要儲存的內容
            create_backup: 是否創建備份（預設 True）
        
        Returns:
            Tuple[success, error_message, backup_file_path]
            - success: 是否成功
            - error_message: 錯誤訊息（成功時為空字串）
            - backup_file_path: 備份文件路徑（如果創建了備份）
        """
        backup_path = None
        temp_path = None
        
        try:
            logger.info(f"Saving inventory to: {inventory_path}")
            
            # 創建備份
            if create_backup and os.path.exists(inventory_path):
                backup_path = self.create_backup(inventory_path)
            
            # 驗證生成的內容語法（寫入臨時文件測試）
            temp_path = f"{inventory_path}.tmp"
            with open(temp_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            logger.debug("Validating generated content syntax")
            syntax_valid, syntax_error = self.validate_syntax(temp_path)
            if not syntax_valid:
                os.remove(temp_path)
                error_msg = f"生成的內容語法錯誤: {syntax_error}"
                logger.error(error_msg)
                return False, error_msg, backup_path
            
            # 寫入正式文件
            shutil.move(temp_path, inventory_path)
            logger.info(f"Successfully saved inventory to NAS")
            
            return True, "", backup_path
            
        except Exception as e:
            # 清理臨時文件
            if temp_path and os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except:
                    pass
            
            error_msg = f"儲存失敗: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return False, error_msg, backup_path
    
    def rollback_to_backup(
        self,
        inventory_path: str,
        backup_path: str
    ) -> Tuple[bool, str]:
        """
        從備份回滾
        
        Args:
            inventory_path: Inventory 文件路徑
            backup_path: 備份文件路徑
        
        Returns:
            Tuple[success, error_message]
            - success: 是否成功
            - error_message: 錯誤訊息（成功時為空字串）
        """
        current_backup = None
        
        try:
            logger.info(f"Rolling back from backup: {backup_path}")
            
            if not os.path.exists(backup_path):
                error_msg = f"備份檔案不存在: {backup_path}"
                logger.error(error_msg)
                return False, error_msg
            
            # 先創建當前版本的備份（防止回滾錯誤）
            if os.path.exists(inventory_path):
                current_backup = self.create_backup(inventory_path)
            
            # 複製備份檔案覆蓋當前檔案
            shutil.copy2(backup_path, inventory_path)
            
            # 驗證語法
            syntax_valid, syntax_error = self.validate_syntax(inventory_path)
            if not syntax_valid:
                # 回滾失敗，恢復當前版本
                if current_backup:
                    shutil.copy2(current_backup, inventory_path)
                error_msg = f"回滾後語法錯誤: {syntax_error}"
                logger.error(error_msg)
                return False, error_msg
            
            logger.info("Successfully rolled back to backup")
            return True, ""
            
        except Exception as e:
            # 嘗試恢復當前版本
            if current_backup:
                try:
                    shutil.copy2(current_backup, inventory_path)
                except:
                    pass
            
            error_msg = f"回滾失敗: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return False, error_msg
    
    def cleanup_old_backups(
        self,
        inventory_path: str,
        keep_count: int = 30
    ) -> int:
        """
        清理舊備份文件
        
        Args:
            inventory_path: Inventory 文件路徑
            keep_count: 保留的備份數量（預設 30）
        
        Returns:
            刪除的備份數量
        """
        try:
            directory = os.path.dirname(inventory_path)
            filename = os.path.basename(inventory_path)
            
            # 找出所有備份檔案
            # 新格式: .backup.hosts.2025-12-02_05-08-18 (以點開頭)
            # 舊格式: hosts.backup.2025-12-02_05-08-18 (相容舊備份)
            backups = []
            
            for file in os.listdir(directory):
                # 匹配新格式 (.backup.hosts.xxx) 或舊格式 (hosts.backup.xxx)
                if file.startswith(f".backup.{filename}.") or file.startswith(f"{filename}.backup."):
                    full_path = os.path.join(directory, file)
                    backups.append((full_path, os.path.getmtime(full_path)))
            
            # 按時間排序（最新的在前）
            backups.sort(key=lambda x: x[1], reverse=True)
            
            # 刪除超過保留數量的備份
            deleted_count = 0
            for backup_path, _ in backups[keep_count:]:
                try:
                    os.remove(backup_path)
                    deleted_count += 1
                    logger.debug(f"Deleted old backup: {backup_path}")
                except Exception as e:
                    logger.warning(f"Failed to delete backup {backup_path}: {e}")
            
            if deleted_count > 0:
                logger.info(f"Cleaned up {deleted_count} old backup(s), kept {keep_count} most recent")
            
            return deleted_count
            
        except Exception as e:
            logger.error(f"Failed to cleanup old backups: {e}", exc_info=True)
            return 0
    
    def get_file_content(self, inventory_path: str) -> Tuple[bool, str, Optional[str]]:
        """
        讀取 Inventory 文件內容（新增）
        
        Args:
            inventory_path: Inventory 文件的完整路徑
        
        Returns:
            Tuple[success, content, error_message]
            - success: 是否成功
            - content: 文件內容（失敗時為空字串）
            - error_message: 錯誤訊息（成功時為 None）
        """
        try:
            logger.info(f"Reading file content from: {inventory_path}")
            
            if not os.path.exists(inventory_path):
                error_msg = f"文件不存在: {inventory_path}"
                logger.error(error_msg)
                return False, "", error_msg
            
            with open(inventory_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            logger.info(f"Successfully read {len(content)} characters from {inventory_path}")
            return True, content, None
            
        except Exception as e:
            error_msg = f"讀取文件失敗: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return False, "", error_msg
    
    def update_file_content(
        self, 
        inventory_path: str, 
        content: str,
        create_backup: bool = True
    ) -> Tuple[bool, str, Optional[str]]:
        """
        更新 Inventory 文件內容（新增）
        
        Args:
            inventory_path: Inventory 文件的完整路徑
            content: 新的文件內容
            create_backup: 是否創建備份（預設 True）
        
        Returns:
            Tuple[success, error_message, backup_file_path]
            - success: 是否成功
            - error_message: 錯誤訊息（成功時為空字串）
            - backup_file_path: 備份文件路徑（如果創建了備份）
        """
        import tempfile
        
        try:
            logger.info(f"Updating file content: {inventory_path}")
            
            # 創建備份
            backup_path = None
            if create_backup and os.path.exists(inventory_path):
                backup_path = self.create_backup(inventory_path)
                logger.info(f"Created backup: {backup_path}")
            
            # 驗證內容語法（寫入臨時文件測試）
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.ini', encoding='utf-8') as f:
                f.write(content)
                temp_path = f.name
            
            try:
                syntax_valid, syntax_error = self.validate_syntax(temp_path)
                
                if not syntax_valid:
                    os.remove(temp_path)
                    error_msg = f"語法錯誤: {syntax_error}"
                    logger.error(error_msg)
                    return False, error_msg, backup_path
                
                # 寫入正式文件
                shutil.move(temp_path, inventory_path)
                logger.info(f"Successfully updated file: {inventory_path}")
                
                # 清理舊備份（保留最近 30 個）
                self.cleanup_old_backups(inventory_path, keep_count=30)
                
                return True, "", backup_path
                
            finally:
                # 確保臨時文件被刪除
                if os.path.exists(temp_path):
                    os.remove(temp_path)
            
        except Exception as e:
            error_msg = f"更新文件失敗: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return False, error_msg, None
    
    def validate_content_syntax(self, content: str) -> Tuple[bool, Optional[str], Optional[Dict]]:
        """
        驗證文本內容的語法（使用增強版驗證器 + Ansible 雙重驗證）
        
        策略：
        1. 先用增強版驗證器預檢查（可獲得精確行號）
        2. 如果通過，再用 Ansible 最終驗證
        3. 返回行號資訊（如果有錯誤）
        
        Args:
            content: 要驗證的文本內容
        
        Returns:
            Tuple[is_valid, error_message, parsed_stats]
            - is_valid: 語法是否有效
            - error_message: 錯誤訊息（語法正確時為 None）
            - parsed_stats: 解析統計資訊（包含 total_hosts, total_groups, error_line）
        """
        import tempfile
        from library.utils.enhanced_ini_validator import validate_ini_with_line_numbers
        
        try:
            logger.info("Validating content syntax with enhanced validator")
            
            # 第一步：使用增強版驗證器預檢查（可獲得行號）
            validation_result = validate_ini_with_line_numbers(content)
            
            if not validation_result['is_valid']:
                # 驗證失敗，返回詳細的錯誤資訊（包含行號）
                error_stats = {
                    'error_line': validation_result.get('error_line'),
                    'error_line_content': validation_result.get('error_line_content'),
                    'validation_method': validation_result.get('validation_method')
                }
                logger.warning(f"Enhanced validation failed at line {validation_result.get('error_line')}: {validation_result['error_message']}")
                return False, validation_result['error_message'], error_stats
            
            logger.info("Enhanced validation passed, proceeding to Ansible validation")
            
            # 第二步：創建臨時文件進行 Ansible 最終驗證
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.ini', encoding='utf-8') as f:
                f.write(content)
                temp_path = f.name
            
            try:
                # 使用 Ansible 驗證（確保 Ansible 也能解析）
                syntax_valid, syntax_error = self.validate_syntax(temp_path)
                
                # 如果語法正確，解析統計資訊
                parsed_stats = None
                if syntax_valid:
                    try:
                        parsed_data = self.parse_inventory(temp_path)
                        parsed_stats = {
                            'total_hosts': parsed_data['total_hosts'],
                            'total_groups': parsed_data['total_groups']
                        }
                        logger.info(f"Content validation passed: {parsed_stats['total_hosts']} hosts, {parsed_stats['total_groups']} groups")
                    except Exception as parse_error:
                        logger.warning(f"Syntax valid but failed to parse inventory: {parse_error}")
                else:
                    logger.warning(f"Ansible validation failed: {syntax_error}")
                
                return syntax_valid, syntax_error, parsed_stats
                
            finally:
                # 刪除臨時文件
                if os.path.exists(temp_path):
                    os.remove(temp_path)
            
        except Exception as e:
            error_msg = f"驗證失敗: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return False, error_msg, None
    
    def get_full_inventory(self, use_cache: bool = True) -> Dict:
        """
        獲取完整的 Inventory 數據（用於 Jenkins API）
        
        返回 ansible-inventory --list 的原始 JSON 格式，包含 _meta.hostvars
        
        Args:
            use_cache: 是否使用快取（目前未實現快取，參數保留用於未來擴展）
        
        Returns:
            Dict 包含:
            {
                'success': bool,
                'cached': bool,  # 目前固定為 False（未實現快取）
                'data': {
                    '_meta': {
                        'hostvars': {
                            'hostname': {...}  # 主機變數
                        }
                    },
                    'group_name': {
                        'hosts': [...]  # 群組中的主機列表
                    }
                },
                'error': str (optional)
            }
        """
        try:
            logger.info(f"Getting full inventory from: {self.nas_base_path}")
            
            # 檢查文件是否存在
            if not os.path.exists(self.nas_base_path):
                error_msg = f"Inventory 文件不存在: {self.nas_base_path}"
                logger.error(error_msg)
                return {
                    'success': False,
                    'cached': False,
                    'error': error_msg
                }
            
            # 執行 ansible-inventory --list 獲取原始 JSON 格式
            result = subprocess.run(
                ['ansible-inventory', '-i', self.nas_base_path, '--list'],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                error_msg = f"ansible-inventory 命令失敗: {result.stderr}"
                logger.error(error_msg)
                return {
                    'success': False,
                    'cached': False,
                    'error': error_msg
                }
            
            # 解析 JSON 輸出
            inventory_data = json.loads(result.stdout)
            
            # 統計資訊（用於日誌）
            hostvars = inventory_data.get('_meta', {}).get('hostvars', {})
            total_hosts = len(hostvars)
            total_groups = len([k for k in inventory_data.keys() if k not in ['_meta', 'all']])
            
            logger.info(f"Successfully retrieved inventory: {total_hosts} hosts, {total_groups} groups")
            
            return {
                'success': True,
                'cached': False,  # 未實現快取機制
                'data': inventory_data  # 返回原始的 ansible-inventory JSON 格式
            }
            
        except subprocess.TimeoutExpired:
            error_msg = f"獲取 Inventory 超時（30秒）"
            logger.error(error_msg)
            return {
                'success': False,
                'cached': False,
                'error': error_msg
            }
        except json.JSONDecodeError as e:
            error_msg = f"解析 Inventory JSON 失敗: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'cached': False,
                'error': error_msg
            }
        except FileNotFoundError as e:
            error_msg = f"找不到 Inventory 文件: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'cached': False,
                'error': error_msg
            }
        except Exception as e:
            error_msg = f"獲取 Inventory 失敗: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {
                'success': False,
                'cached': False,
                'error': error_msg
            }
    
    def get_host_config(self, hostname: str, use_cache: bool = True) -> Dict:
        """
        獲取特定主機的完整配置
        
        Args:
            hostname: 主機名稱
            use_cache: 是否使用快取（目前未實現，參數保留）
        
        Returns:
            Dict 包含:
            {
                'success': bool,
                'cached': bool,
                'hostname': str,
                'config': Dict,  # 主機的所有變數
                'groups': List[str],  # 主機所屬的群組
                'error': str (optional)
            }
        """
        try:
            logger.info(f"Getting config for host: {hostname}")
            
            # 檢查文件是否存在
            if not os.path.exists(self.nas_base_path):
                error_msg = f"Inventory 文件不存在: {self.nas_base_path}"
                logger.error(error_msg)
                return {
                    'success': False,
                    'cached': False,
                    'error': error_msg
                }
            
            # 執行 ansible-inventory 獲取主機配置
            result = subprocess.run(
                ['ansible-inventory', '-i', self.nas_base_path, '--host', hostname],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                error_msg = f"無法獲取主機配置: {result.stderr}"
                logger.error(error_msg)
                return {
                    'success': False,
                    'cached': False,
                    'error': error_msg
                }
            
            # 解析 JSON 輸出
            host_config = json.loads(result.stdout)
            
            # 獲取主機所屬的群組
            # 需要再次獲取完整 inventory 來查找群組資訊
            full_result = self.parse_inventory(self.nas_base_path)
            host_groups = []
            
            for host in full_result.get('hosts', []):
                if host['hostname'] == hostname:
                    host_groups = host.get('groups', [])
                    break
            
            logger.info(f"Successfully retrieved config for host: {hostname}, groups: {host_groups}")
            
            return {
                'success': True,
                'cached': False,
                'hostname': hostname,
                'config': host_config,
                'groups': host_groups
            }
            
        except subprocess.TimeoutExpired:
            error_msg = f"獲取主機配置超時（30秒）: {hostname}"
            logger.error(error_msg)
            return {
                'success': False,
                'cached': False,
                'error': error_msg
            }
        except json.JSONDecodeError as e:
            error_msg = f"解析主機配置失敗: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'cached': False,
                'error': error_msg
            }
        except Exception as e:
            error_msg = f"獲取主機配置失敗: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {
                'success': False,
                'cached': False,
                'error': error_msg
            }
    
    def clear_cache(self, cache_type: str = 'all'):
        """
        清除快取（預留方法，目前未實現快取機制）
        
        Args:
            cache_type: 快取類型（'all', 'inventory', 'validation' 等）
        """
        logger.info(f"clear_cache called with type: {cache_type} (cache not implemented yet)")
        pass
