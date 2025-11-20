"""
Ansible Inventory Configuration Validator

Validates Ansible Inventory files for:
- Syntax correctness (INI format, Jinja2 templates)
- Structure integrity (groups, hierarchy, circular dependencies)
- Host configuration completeness (required variables)
- IP/MAC address validation
- Network connectivity (optional)
- DHCP record matching (optional)

Author: Network Toolbox Team
Created: 2025-11-18
"""

import logging
import re
import os
import socket
import ipaddress
from typing import Dict, List, Optional, Tuple
from configparser import ConfigParser
from collections import defaultdict

# Django imports
from api.models import AnsibleInventoryImport

logger = logging.getLogger(__name__)


class InventoryConfigValidator:
    """
    Ansible Inventory Configuration Validator
    
    Performs comprehensive validation of Ansible Inventory files,
    similar to Jenkins Build configuration checker.
    """
    
    def __init__(self, inventory_id: int, check_connectivity: bool = False, check_dhcp: bool = False):
        """
        初始化驗證器
        
        Args:
            inventory_id: Inventory 記錄 ID
            check_connectivity: 是否執行網路連線測試（耗時）
            check_dhcp: 是否檢查 DHCP 記錄
        """
        self.inventory_id = inventory_id
        self.check_connectivity = check_connectivity
        self.check_dhcp = check_dhcp
        
        # 資料
        self.inventory = None
        self.content = ""
        self.parsed_data = {}
        
        # 驗證結果
        self.validation_results = {
            'overall_status': 'unknown',
            'inventory_id': inventory_id,
            'checks': {},
            'summary': {
                'total_checks': 0,
                'passed': 0,
                'warnings': 0,
                'errors': 0
            }
        }
    
    def validate(self) -> Dict:
        """
        執行完整驗證流程
        
        Returns:
            驗證結果字典
        """
        try:
            logger.info(f"🔍 Starting validation for Inventory ID: {self.inventory_id}")
            
            # 1. 載入 Inventory
            if not self._load_inventory():
                return self._create_error_result("Failed to load inventory")
            
            # 2. 語法驗證
            self._check_syntax()
            
            # 3. 結構完整性檢查
            self._check_structure()
            
            # 4. 主機配置檢查
            self._check_host_config()
            
            # 5. IP 地址驗證（包含 DHCP 租約比對）
            self._check_ip_addresses()
            
            # 6. MAC 地址驗證（包含 DHCP 租約比對）
            self._check_mac_addresses()
            
            # 7. UART SSH 連接檢查
            self._check_uart_ssh_connections()
            
            # 8. NAS 連線檢查（新增）
            self._check_nas_connection()
            
            # 9. 網路連線測試（可選）
            if self.check_connectivity:
                self._check_network_connectivity()
            
            # 10. 計算總體狀態
            self._calculate_overall_status()
            
            logger.info(f"✅ Validation complete. Status: {self.validation_results['overall_status']}")
            
            return self.validation_results
            
        except Exception as e:
            logger.error(f"❌ Validation error: {e}", exc_info=True)
            return self._create_error_result(f"Validation exception: {str(e)}")
    
    def _load_inventory(self) -> bool:
        """載入 Inventory 記錄"""
        try:
            self.inventory = AnsibleInventoryImport.objects.filter(id=self.inventory_id).first()
            
            if not self.inventory:
                logger.error(f"Inventory not found: {self.inventory_id}")
                return False
            
            # 從 NAS 路徑讀取內容
            from library.services.ansible_inventory_service import AnsibleInventoryService
            
            service = AnsibleInventoryService()
            linux_path = service.convert_windows_path_to_linux(self.inventory.nas_path)
            full_path = os.path.join(linux_path, self.inventory.file_name)
            
            # 檢查文件是否存在
            if not os.path.exists(full_path):
                logger.error(f"Inventory file not found: {full_path}")
                return False
            
            # 讀取文件內容
            with open(full_path, 'r', encoding='utf-8') as f:
                self.content = f.read()
            
            if not self.content:
                logger.warning(f"Inventory {self.inventory_id} has no content")
                return False
            
            logger.info(f"✓ Loaded Inventory: {self.inventory.id} from {full_path} ({len(self.content)} chars)")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load inventory: {e}", exc_info=True)
            return False
    
    def _check_syntax(self):
        """語法驗證"""
        try:
            logger.info("Checking syntax...")
            
            from library.utils.enhanced_ini_validator import EnhancedINIValidator
            
            result = EnhancedINIValidator.validate(self.content)
            
            if result.get('is_valid', False):
                # 語法有效
                self.validation_results['checks']['syntax'] = {
                    'status': 'success',
                    'message': '語法檢查通過，無錯誤',
                    'value': f"{len(self.content.splitlines())} 行",
                    'details': {
                        'line_count': len(self.content.splitlines())
                    },
                    'suggestions': []
                }
                logger.info(f"✓ Syntax check passed")
            else:
                # 語法無效
                error_msg = result.get('error_message', '未知錯誤')
                error_line = result.get('error_line', 'N/A')
                
                self.validation_results['checks']['syntax'] = {
                    'status': 'error',
                    'message': f"發現語法錯誤",
                    'value': f"第 {error_line} 行" if error_line != 'N/A' else "未知位置",
                    'details': {
                        'error_message': error_msg,
                        'error_line': error_line,
                        'error_line_content': result.get('error_line_content', '')
                    },
                    'suggestions': [
                        '修正語法錯誤後重新檢查',
                        '確認 INI 格式正確（[section] 和 key=value）',
                        '檢查 Jinja2 模板語法（{{ variable }}）',
                        '參考 Ansible Inventory 文檔'
                    ]
                }
                logger.warning(f"⚠ Syntax check failed: {error_msg}")
                
        except Exception as e:
            logger.error(f"Syntax check exception: {e}", exc_info=True)
            self.validation_results['checks']['syntax'] = self._create_error_check('syntax', str(e))
    
    def _check_structure(self):
        """結構完整性檢查"""
        try:
            logger.info("Checking structure integrity...")
            
            # 解析 INI 結構（使用 RawConfigParser 並保持原始大小寫）
            from configparser import RawConfigParser
            
            config = RawConfigParser(allow_no_value=True, strict=False)
            # 重要：保持 key 的原始大小寫
            config.optionxform = str
            config.read_string(self.content)
            
            sections = config.sections()
            issues = []
            warnings = []
            
            # 檢查 1: 必要的 Section
            has_hosts = any(not s.endswith(':children') and not s.endswith(':vars') for s in sections)
            if not has_hosts:
                issues.append("缺少主機定義 Section")
            
            # 檢查 2: Group 結構
            groups = {}
            group_children = {}
            
            for section in sections:
                if section.endswith(':children'):
                    group_name = section.replace(':children', '')
                    children = [item[0] for item in config.items(section)]
                    group_children[group_name] = children
                    groups[group_name] = 'parent'
                elif section.endswith(':vars'):
                    continue  # 變數 Section，跳過
                else:
                    groups[section] = 'leaf'
            
            # 檢查 3: 循環依賴
            circular_deps = self._detect_circular_dependencies(group_children)
            if circular_deps:
                issues.append(f"發現循環依賴: {' → '.join(circular_deps)}")
            
            # 檢查 4: 孤立的 children 引用
            for parent, children in group_children.items():
                for child in children:
                    if child not in groups:
                        warnings.append(f"Group '{parent}' 引用不存在的子 Group '{child}'")
            
            # 判斷狀態
            if issues:
                status = 'error'
                message = f"結構檢查失敗：{len(issues)} 個錯誤"
            elif warnings:
                status = 'warning'
                message = f"結構檢查通過，但有 {len(warnings)} 個警告"
            else:
                status = 'success'
                message = "結構檢查通過，無問題"
            
            self.validation_results['checks']['structure'] = {
                'status': status,
                'message': message,
                'value': f"{len(groups)} 個 Group",
                'details': {
                    'total_groups': len(groups),
                    'parent_groups': sum(1 for v in groups.values() if v == 'parent'),
                    'leaf_groups': sum(1 for v in groups.values() if v == 'leaf'),
                    'issues': issues,
                    'warnings': warnings
                },
                'suggestions': self._generate_structure_suggestions(issues, warnings)
            }
            
            logger.info(f"✓ Structure check: {status} - {len(groups)} groups")
            
        except Exception as e:
            logger.error(f"Structure check exception: {e}", exc_info=True)
            self.validation_results['checks']['structure'] = self._create_error_check('structure', str(e))
    
    def _detect_circular_dependencies(self, group_children: Dict[str, List[str]]) -> List[str]:
        """檢測循環依賴"""
        def dfs(node: str, path: List[str], visited: set) -> List[str]:
            if node in path:
                # 找到循環
                cycle_start = path.index(node)
                return path[cycle_start:] + [node]
            
            if node not in group_children:
                return []
            
            path.append(node)
            
            for child in group_children[node]:
                cycle = dfs(child, path.copy(), visited)
                if cycle:
                    return cycle
            
            return []
        
        for group in group_children:
            cycle = dfs(group, [], set())
            if cycle:
                return cycle
        
        return []
    
    def _generate_structure_suggestions(self, issues: List[str], warnings: List[str]) -> List[str]:
        """生成結構建議"""
        suggestions = []
        
        if "缺少主機定義" in ' '.join(issues):
            suggestions.append("至少定義一個主機 Section（如 [webservers]）")
        
        if "循環依賴" in ' '.join(issues):
            suggestions.append("移除 Group 之間的循環引用")
            suggestions.append("重新設計 Group 層級結構")
        
        if warnings:
            suggestions.append("檢查 [group:children] 引用的 Group 是否存在")
        
        if not suggestions:
            suggestions.append("結構符合 Ansible 最佳實踐")
        
        return suggestions
    
    def _check_host_config(self):
        """主機配置檢查（使用 Ansible 原生 API）"""
        try:
            logger.info("Checking host configurations using Ansible native API...")
            
            # 使用 Ansible 原生 API 解析 Inventory
            from ansible.inventory.manager import InventoryManager
            from ansible.parsing.dataloader import DataLoader
            from ansible.vars.manager import VariableManager
            import tempfile
            
            # 創建臨時文件（Ansible API 需要文件路徑）
            with tempfile.NamedTemporaryFile(mode='w', suffix='.ini', delete=False, encoding='utf-8') as tmp_file:
                tmp_file.write(self.content)
                tmp_file_path = tmp_file.name
            
            try:
                # 初始化 Ansible DataLoader 和 InventoryManager
                loader = DataLoader()
                inventory = InventoryManager(loader=loader, sources=[tmp_file_path])
                variable_manager = VariableManager(loader=loader, inventory=inventory)
                
                # 收集所有主機及其變數（Ansible 已自動處理繼承）
                host_configs = {}
                all_hosts = inventory.get_hosts()
                
                logger.info(f"Found {len(all_hosts)} hosts via Ansible API")
                
                for host in all_hosts:
                    # 過濾掉假主機（主機名不應包含 '=' 字符）
                    if '=' in host.name:
                        logger.debug(f"Skipping invalid host name: {host.name}")
                        continue
                    
                    # 獲取主機的所有變數（包含繼承的 group vars）
                    host_vars = variable_manager.get_vars(host=host)
                    
                    # 只提取 ansible_* 相關變數
                    ansible_vars = {k: v for k, v in host_vars.items() if k.startswith('ansible_')}
                    host_configs[host.name] = ansible_vars
                
                logger.info(f"Valid hosts after filtering: {len(host_configs)}")
                
                # 檢查必要變數
                required_vars = ['ansible_host']  # 最基本的必要變數
                recommended_vars = ['ansible_user']  # 建議的變數
                
                incomplete_hosts = []
                missing_recommended = []
                
                for hostname, vars in host_configs.items():
                    # 特殊處理 localhost（使用 ansible_connection=local 時不需要 ansible_host）
                    if hostname == 'localhost' and vars.get('ansible_connection') == 'local':
                        continue
                    
                    missing = [v for v in required_vars if v not in vars]
                    if missing:
                        incomplete_hosts.append({'host': hostname, 'missing': missing})
                    
                    missing_rec = [v for v in recommended_vars if v not in vars]
                    if missing_rec:
                        missing_recommended.append({'host': hostname, 'missing': missing_rec})
                
                # 判斷狀態
                if incomplete_hosts:
                    status = 'error'
                    message = f"{len(incomplete_hosts)} 個主機缺少必要變數"
                elif missing_recommended:
                    status = 'warning'
                    message = f"{len(missing_recommended)} 個主機缺少建議變數"
                else:
                    status = 'success'
                    message = f"所有 {len(host_configs)} 個主機配置完整"
                
                self.validation_results['checks']['host_config'] = {
                    'status': status,
                    'message': message,
                    'value': f"{len(host_configs)} 個主機",
                    'details': {
                        'total_hosts': len(host_configs),
                        'complete_hosts': len(host_configs) - len(incomplete_hosts),
                        'incomplete_hosts': incomplete_hosts[:10],  # 最多顯示 10 個
                        'missing_recommended': missing_recommended[:10]
                    },
                    'suggestions': self._generate_host_config_suggestions(incomplete_hosts, missing_recommended)
                }
                
                logger.info(f"✓ Host config check: {status} - {len(host_configs)} hosts")
                
            finally:
                # 清理臨時文件
                import os
                if os.path.exists(tmp_file_path):
                    os.unlink(tmp_file_path)
            
        except Exception as e:
            logger.error(f"Host config check exception: {e}", exc_info=True)
            self.validation_results['checks']['host_config'] = self._create_error_check('host_config', str(e))
    
    def _parse_host_vars(self, vars_str: str) -> Dict:
        """解析主機變數字串"""
        vars_dict = {}
        if not vars_str:
            return vars_dict
        
        # 簡單的 key=value 解析
        parts = vars_str.split()
        for part in parts:
            if '=' in part:
                key, value = part.split('=', 1)
                vars_dict[key] = value
        
        return vars_dict
    
    def _generate_host_config_suggestions(self, incomplete: List[Dict], missing_rec: List[Dict]) -> List[str]:
        """生成主機配置建議"""
        suggestions = []
        
        if incomplete:
            suggestions.append("為缺少 ansible_host 的主機添加 IP 地址")
            suggestions.append("範例：server1 ansible_host=192.168.1.100")
        
        if missing_rec:
            suggestions.append("建議為主機添加 ansible_user（SSH 用戶名）")
            suggestions.append("建議添加認證方式（ansible_password 或 ansible_ssh_private_key_file）")
        
        if not suggestions:
            suggestions.append("主機配置符合最佳實踐")
        
        return suggestions
    
    def _check_ip_addresses(self):
        """IP 地址驗證（包含 DHCP 租約比對）"""
        try:
            logger.info("Checking IP addresses...")
            
            # 收集所有 IP 地址及其對應的主機名（排除註釋行）
            ips_found = []
            ip_to_host = {}
            
            for line in self.content.split('\n'):
                stripped = line.strip()
                # 跳過註釋行
                if stripped.startswith('#') or stripped.startswith(';'):
                    continue
                
                # 提取主機名
                parts = stripped.split()
                hostname = None
                if parts and not stripped.startswith('[') and '=' not in parts[0]:
                    hostname = parts[0]
                
                # 查找 ansible_host=IP
                match = re.search(r'ansible_host\s*=\s*([0-9]+\.[0-9]+\.[0-9]+\.[0-9]+)', line)
                if match:
                    ip = match.group(1)
                    ips_found.append(ip)
                    if hostname:
                        ip_to_host[ip] = hostname
            
            if not ips_found:
                self.validation_results['checks']['ip_addresses'] = {
                    'status': 'warning',
                    'message': '未找到任何 ansible_host IP 地址',
                    'value': '0 個 IP',
                    'details': {},
                    'suggestions': ['為主機添加 ansible_host=<IP> 配置']
                }
                return
            
            # 驗證 IP 格式和檢查衝突
            ip_map = defaultdict(list)  # {ip: [occurrences]}
            invalid_ips = []
            
            for ip in ips_found:
                try:
                    ipaddress.ip_address(ip)
                    ip_map[ip].append(ip)
                except ValueError:
                    invalid_ips.append(ip)
            
            # 檢查衝突
            conflicts = {ip: len(hosts) for ip, hosts in ip_map.items() if len(hosts) > 1}
            
            # DHCP 租約比對（如果啟用）
            dhcp_match_rate = 0
            dhcp_matched = 0
            dhcp_unmatched = []
            dhcp_total_leases = 0
            
            if self.check_dhcp:
                try:
                    from api.models import DHCPLease
                    
                    # 查詢 DHCP 租約
                    dhcp_leases = DHCPLease.objects.filter(is_active=True)
                    dhcp_ips = set(lease.ip_address for lease in dhcp_leases)
                    dhcp_total_leases = len(dhcp_leases)
                    
                    # 比對
                    inventory_ips = set(ip_map.keys())
                    matched_ips = inventory_ips & dhcp_ips
                    unmatched_ips = inventory_ips - dhcp_ips
                    
                    dhcp_matched = len(matched_ips)
                    dhcp_match_rate = (dhcp_matched / len(inventory_ips) * 100) if inventory_ips else 0
                    dhcp_unmatched = [
                        {'host': ip_to_host.get(ip, 'unknown'), 'ip': ip} 
                        for ip in list(unmatched_ips)[:10]
                    ]
                    
                    logger.info(f"DHCP IP match: {dhcp_matched}/{len(inventory_ips)} ({dhcp_match_rate:.1f}%)")
                    
                except Exception as e:
                    logger.error(f"DHCP IP check failed: {e}", exc_info=True)
            
            # 判斷狀態（按優先級）
            if invalid_ips:
                status = 'error'
                message = f"發現 {len(invalid_ips)} 個無效 IP"
            elif self.check_dhcp and dhcp_match_rate < 80:
                status = 'error'
                message = f"多數 IP 不在 DHCP 租約中（匹配率: {dhcp_match_rate:.0f}%）"
            elif conflicts:
                status = 'warning'
                message = f"發現 {len(conflicts)} 個 IP 重複定義（可能是測試配置）"
            elif self.check_dhcp and dhcp_match_rate < 95:
                status = 'warning'
                message = f"部分 IP 不在 DHCP 租約中（匹配率: {dhcp_match_rate:.0f}%）"
            else:
                status = 'success'
                if self.check_dhcp:
                    message = f"所有 {len(ip_map)} 個 IP 有效、無衝突且在 DHCP 租約中"
                else:
                    message = f"所有 {len(ip_map)} 個 IP 地址有效且無衝突"
            
            # 構建詳細資訊
            details = {
                'total_ips': len(ips_found),
                'unique_ips': len(ip_map),
                'invalid_ips': invalid_ips,
                'conflicts': [{'ip': ip, 'count': len(hosts)} for ip, hosts in ip_map.items() if len(hosts) > 1]
            }
            
            # 添加 DHCP 資訊（如果啟用）
            if self.check_dhcp:
                details.update({
                    'dhcp_enabled': True,
                    'dhcp_total_leases': dhcp_total_leases,
                    'dhcp_matched': dhcp_matched,
                    'dhcp_match_rate': round(dhcp_match_rate, 1),
                    'dhcp_unmatched_count': len(inventory_ips) - dhcp_matched if self.check_dhcp else 0,
                    'dhcp_unmatched_hosts': dhcp_unmatched
                })
            
            self.validation_results['checks']['ip_addresses'] = {
                'status': status,
                'message': message,
                'value': f"{len(ip_map)} 個唯一 IP",
                'details': details,
                'suggestions': self._generate_ip_suggestions(invalid_ips, conflicts, dhcp_match_rate if self.check_dhcp else 100, dhcp_unmatched if self.check_dhcp else [])
            }
            
            logger.info(f"✓ IP check: {status} - {len(ip_map)} unique IPs")
            
        except Exception as e:
            logger.error(f"IP check exception: {e}", exc_info=True)
            self.validation_results['checks']['ip_addresses'] = self._create_error_check('ip_addresses', str(e))
    
    def _generate_ip_suggestions(self, invalid_ips: List[str], conflicts: Dict, dhcp_match_rate: float = 100, dhcp_unmatched: List = None) -> List[str]:
        """生成 IP 建議（包含 DHCP）"""
        suggestions = []
        
        if invalid_ips:
            suggestions.append(f"修正無效的 IP 地址：{', '.join(invalid_ips[:3])}")
            suggestions.append("確保 IP 格式為 XXX.XXX.XXX.XXX")
        
        if conflicts:
            suggestions.append("解決 IP 衝突：每個主機應使用唯一的 IP 地址")
            suggestions.append("檢查是否有重複定義的主機")
        
        # DHCP 建議
        if dhcp_match_rate < 95 and dhcp_unmatched:
            suggestions.append(f"⚠️ DHCP 比對：有 {len(dhcp_unmatched)} 個 IP 不在租約中")
            suggestions.append("請確認這些設備是否已獲取 DHCP 租約或更新租約")
            if dhcp_match_rate < 80:
                suggestions.append("⚠️ 匹配率過低，建議檢查設備在線狀態")
        
        if not suggestions:
            suggestions.append("IP 地址配置正確" + ("且所有設備都在 DHCP 租約中" if dhcp_match_rate >= 95 else ""))
        
        return suggestions
    
    def _check_mac_addresses(self):
        """MAC 地址驗證（包含 DHCP 租約比對）"""
        try:
            logger.info("Checking MAC addresses...")
            
            # 收集所有 MAC 地址及其對應的主機名（支持多種格式，排除註釋行）
            macs_found = []
            mac_to_host = {}
            
            for line in self.content.split('\n'):
                stripped = line.strip()
                # 跳過註釋行
                if stripped.startswith('#') or stripped.startswith(';'):
                    continue
                
                # 提取主機名
                parts = stripped.split()
                hostname = None
                if parts and not stripped.startswith('[') and '=' not in parts[0]:
                    hostname = parts[0]
                
                # 查找 macaddress=XX:XX:XX:XX:XX:XX 或 XX-XX-XX-XX-XX-XX
                match = re.search(r'macaddress\s*=\s*([0-9A-Fa-f:]{17}|[0-9A-Fa-f-]{17})', line)
                if match:
                    mac = match.group(1)
                    macs_found.append(mac)
                    if hostname:
                        mac_to_host[mac.lower().replace('-', ':')] = hostname
            
            if not macs_found:
                self.validation_results['checks']['mac_addresses'] = {
                    'status': 'warning',
                    'message': '未找到任何 MAC 地址',
                    'value': '0 個 MAC',
                    'details': {},
                    'suggestions': ['如果需要 DHCP 管理，建議添加 macaddress 變數']
                }
                logger.info("⚠ No MAC addresses found")
                return
            
            # 驗證 MAC 格式
            mac_map = defaultdict(list)
            invalid_macs = []
            
            for mac in macs_found:
                # 標準化 MAC（統一為小寫冒號格式）
                normalized = mac.lower().replace('-', ':')
                
                if self._is_valid_mac(normalized):
                    mac_map[normalized].append(mac)
                else:
                    invalid_macs.append(mac)
            
            # 檢查重複
            duplicates = {mac: len(occurrences) for mac, occurrences in mac_map.items() if len(occurrences) > 1}
            
            # DHCP 租約比對（如果啟用）
            dhcp_match_rate = 0
            dhcp_matched = 0
            dhcp_unmatched = []
            dhcp_total_leases = 0
            
            if self.check_dhcp:
                try:
                    from api.models import DHCPLease
                    
                    # 查詢 DHCP 租約
                    dhcp_leases = DHCPLease.objects.filter(is_active=True)
                    dhcp_macs = set(lease.mac_address.lower() for lease in dhcp_leases if lease.mac_address)
                    dhcp_total_leases = len(dhcp_leases)
                    
                    # 比對
                    inventory_macs = set(mac_map.keys())
                    matched_macs = inventory_macs & dhcp_macs
                    unmatched_macs = inventory_macs - dhcp_macs
                    
                    dhcp_matched = len(matched_macs)
                    dhcp_match_rate = (dhcp_matched / len(inventory_macs) * 100) if inventory_macs else 0
                    dhcp_unmatched = [
                        {'host': mac_to_host.get(mac, 'unknown'), 'mac': mac} 
                        for mac in list(unmatched_macs)[:10]
                    ]
                    
                    logger.info(f"DHCP MAC match: {dhcp_matched}/{len(inventory_macs)} ({dhcp_match_rate:.1f}%)")
                    
                except Exception as e:
                    logger.error(f"DHCP MAC check failed: {e}", exc_info=True)
            
            # 判斷狀態（按優先級）
            if invalid_macs:
                status = 'error'
                message = f"發現 {len(invalid_macs)} 個無效 MAC"
            elif self.check_dhcp and dhcp_match_rate < 80:
                status = 'error'
                message = f"多數 MAC 不在 DHCP 租約中（匹配率: {dhcp_match_rate:.0f}%）"
            elif duplicates:
                status = 'warning'
                message = f"發現 {len(duplicates)} 個 MAC 重複定義（可能是測試配置）"
            elif self.check_dhcp and dhcp_match_rate < 95:
                status = 'warning'
                message = f"部分 MAC 不在 DHCP 租約中（匹配率: {dhcp_match_rate:.0f}%）"
            else:
                status = 'success'
                if self.check_dhcp:
                    message = f"所有 {len(mac_map)} 個 MAC 有效、無重複且在 DHCP 租約中"
                else:
                    message = f"所有 {len(mac_map)} 個 MAC 地址有效且無重複"
            
            # 構建詳細資訊
            details = {
                'total_macs': len(macs_found),
                'unique_macs': len(mac_map),
                'invalid_macs': invalid_macs,
                'duplicates': [{'mac': mac, 'count': len(occurrences)} for mac, occurrences in mac_map.items() if len(occurrences) > 1]
            }
            
            # 添加 DHCP 資訊（如果啟用）
            if self.check_dhcp:
                details.update({
                    'dhcp_enabled': True,
                    'dhcp_total_leases': dhcp_total_leases,
                    'dhcp_matched': dhcp_matched,
                    'dhcp_match_rate': round(dhcp_match_rate, 1),
                    'dhcp_unmatched_count': len(mac_map) - dhcp_matched if self.check_dhcp else 0,
                    'dhcp_unmatched_hosts': dhcp_unmatched
                })
            
            self.validation_results['checks']['mac_addresses'] = {
                'status': status,
                'message': message,
                'value': f"{len(mac_map)} 個唯一 MAC",
                'details': details,
                'suggestions': self._generate_mac_suggestions(invalid_macs, duplicates, dhcp_match_rate if self.check_dhcp else 100, dhcp_unmatched if self.check_dhcp else [])
            }
            
            logger.info(f"✓ MAC check: {status} - {len(mac_map)} unique MACs")
            
        except Exception as e:
            logger.error(f"MAC check exception: {e}", exc_info=True)
            self.validation_results['checks']['mac_addresses'] = self._create_error_check('mac_addresses', str(e))
    
    def _is_valid_mac(self, mac: str) -> bool:
        """驗證 MAC 地址格式"""
        pattern = r'^([0-9a-f]{2}:){5}[0-9a-f]{2}$'
        return bool(re.match(pattern, mac))
    
    def _generate_mac_suggestions(self, invalid_macs: List[str], duplicates: Dict, dhcp_match_rate: float = 100, dhcp_unmatched: List = None) -> List[str]:
        """生成 MAC 建議（包含 DHCP）"""
        suggestions = []
        
        if invalid_macs:
            suggestions.append("修正無效的 MAC 地址格式")
            suggestions.append("MAC 格式應為 XX:XX:XX:XX:XX:XX 或 XX-XX-XX-XX-XX-XX")
        
        if duplicates:
            suggestions.append("解決 MAC 重複：每個主機應使用唯一的 MAC 地址")
            suggestions.append("檢查是否有重複定義或複製貼上錯誤")
        
        # DHCP 建議
        if dhcp_match_rate < 95 and dhcp_unmatched:
            suggestions.append(f"⚠️ DHCP 比對：有 {len(dhcp_unmatched)} 個 MAC 不在租約中")
            suggestions.append("請確認這些設備是否在線上並已獲取 DHCP 租約")
            if dhcp_match_rate < 80:
                suggestions.append("⚠️ 匹配率過低，建議檢查設備連接狀態")
        
        if not suggestions:
            suggestions.append("MAC 地址配置正確" + ("且所有設備都在 DHCP 租約中" if dhcp_match_rate >= 95 else ""))
        
        return suggestions
    
    def _check_uart_ssh_connections(self):
        """檢查所有 UART 主機的 SSH 連接"""
        try:
            logger.info("Checking UART SSH connections...")
            
            from api.models import AnsibleHostConfig
            
            # 獲取所有有 uart_host 配置的 Host
            hosts_with_uart = AnsibleHostConfig.objects.filter(
                inventory_id=self.inventory_id
            ).exclude(uart_host__isnull=True).exclude(uart_host='')
            
            if not hosts_with_uart.exists():
                self.validation_results['checks']['uart_ssh'] = {
                    'status': 'warning',
                    'message': '沒有配置 UART 的主機，跳過 SSH 檢查',
                    'value': '0 個 UART 主機',
                    'details': {},
                    'suggestions': ['如需使用 UART 功能，請在 Inventory 中配置 uart_host']
                }
                return
            
            # 統計數據
            total_uart_hosts = hosts_with_uart.count()
            successful_connections = 0
            failed_connections = 0
            skipped_connections = 0
            connection_details = []
            
            logger.info(f"Found {total_uart_hosts} hosts with UART configuration")
            
            # 逐個檢查 UART SSH 連接
            for host in hosts_with_uart:
                result = self._check_single_uart_ssh(host)
                connection_details.append(result)
                
                if result['status'] == 'success':
                    successful_connections += 1
                elif result['status'] == 'warning':
                    skipped_connections += 1
                else:
                    failed_connections += 1
            
            # 判斷整體狀態
            if failed_connections > 0:
                status = 'error'
                message = f'UART SSH 檢查：{failed_connections}/{total_uart_hosts} 連接失敗'
            elif skipped_connections == total_uart_hosts:
                status = 'warning'
                message = f'所有 UART SSH 檢查被跳過（缺少認證信息）'
            elif successful_connections == total_uart_hosts:
                status = 'success'
                message = f'所有 UART SSH 連接成功（{total_uart_hosts}/{total_uart_hosts}）'
            else:
                status = 'warning'
                message = f'UART SSH 檢查：{successful_connections} 成功，{skipped_connections} 跳過，{failed_connections} 失敗'
            
            # 生成建議
            suggestions = []
            if failed_connections > 0:
                suggestions.append(f'⚠️ 有 {failed_connections} 個 UART 主機連接失敗')
                suggestions.append('檢查 UART 主機是否在線上且 SSH 服務正常')
                suggestions.append('驗證 ansible_user 和 ansible_password 是否正確')
            if skipped_connections > 0:
                suggestions.append(f'⚠️ 有 {skipped_connections} 個 UART 主機缺少認證信息')
                suggestions.append('在 UART 主機配置中添加 ansible_user 和 ansible_password')
            if successful_connections == total_uart_hosts:
                suggestions.append('✅ 所有 UART SSH 連接正常')
            
            self.validation_results['checks']['uart_ssh'] = {
                'status': status,
                'message': message,
                'value': f'{successful_connections}/{total_uart_hosts} 成功',
                'details': {
                    'total': total_uart_hosts,
                    'successful': successful_connections,
                    'failed': failed_connections,
                    'skipped': skipped_connections,
                    'connections': connection_details
                },
                'suggestions': suggestions
            }
            
            logger.info(f"UART SSH check complete: {successful_connections} success, {failed_connections} failed, {skipped_connections} skipped")
            
        except Exception as e:
            logger.error(f"UART SSH check exception: {e}", exc_info=True)
            self.validation_results['checks']['uart_ssh'] = self._create_error_check('uart_ssh', str(e))
    
    def _check_single_uart_ssh(self, host) -> Dict:
        """檢查單個主機的 UART SSH 連接"""
        result = {
            'hostname': host.hostname,
            'uart_host': host.uart_host,
            'status': 'unknown',
            'message': '',
            'details': {}
        }
        
        try:
            # 獲取 UART 主機的配置
            uart_ip = None
            uart_user = host.ansible_user
            uart_password = host.ansible_password
            uart_port = host.ansible_port or 22
            
            # 解析 uart_host（可能是 IP 或 hostname）
            if self._is_valid_ip(host.uart_host):
                # uart_host 已經是 IP
                uart_ip = host.uart_host
            else:
                # uart_host 是 hostname，需要解析
                from api.models import AnsibleHostConfig
                uart_config = AnsibleHostConfig.objects.filter(
                    inventory_id=self.inventory_id,
                    hostname=host.uart_host
                ).first()
                
                if uart_config and uart_config.ansible_host:
                    uart_ip = uart_config.ansible_host
                    # 從 UART 主機配置獲取認證信息
                    if uart_config.ansible_user:
                        uart_user = uart_config.ansible_user
                    if uart_config.ansible_password:
                        uart_password = uart_config.ansible_password
                    if uart_config.ansible_port:
                        uart_port = uart_config.ansible_port
                else:
                    result['status'] = 'warning'
                    result['message'] = f'無法解析 UART hostname: {host.uart_host}'
                    result['details'] = {
                        'uart_hostname': host.uart_host,
                        'reason': 'UART 主機在 Inventory 中找不到'
                    }
                    return result
            
            # 檢查必要信息
            if not uart_ip:
                result['status'] = 'warning'
                result['message'] = 'UART IP 未設置'
                return result
            
            if not uart_user:
                result['status'] = 'warning'
                result['message'] = f'UART 主機 {uart_ip} 未設置 ansible_user'
                result['details'] = {'uart_ip': uart_ip}
                return result
            
            if not uart_password:
                result['status'] = 'warning'
                result['message'] = f'UART 主機 {uart_ip} 未設置 ansible_password'
                result['details'] = {'uart_ip': uart_ip, 'uart_user': uart_user}
                return result
            
            # 嘗試 SSH 連接
            logger.info(f"Testing SSH to UART: {uart_user}@{uart_ip}:{uart_port} for host {host.hostname}")
            
            import paramiko
            import socket
            
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            try:
                ssh.connect(
                    hostname=uart_ip,
                    port=uart_port,
                    username=uart_user,
                    password=uart_password,
                    timeout=10,
                    banner_timeout=10,
                    auth_timeout=10
                )
                
                result['status'] = 'success'
                result['message'] = f'SSH 連接成功: {uart_user}@{uart_ip}'
                result['details'] = {
                    'uart_ip': uart_ip,
                    'uart_user': uart_user,
                    'uart_port': uart_port,
                    'connected': True
                }
                
                logger.info(f"✅ SSH connection successful to {uart_ip} for host {host.hostname}")
                ssh.close()
                
            except paramiko.AuthenticationException:
                result['status'] = 'error'
                result['message'] = f'SSH 認證失敗: {uart_user}@{uart_ip}'
                result['details'] = {
                    'uart_ip': uart_ip,
                    'uart_user': uart_user,
                    'uart_port': uart_port,
                    'error': 'Authentication failed'
                }
                logger.error(f"❌ SSH auth failed for {uart_ip}")
                
            except socket.timeout:
                result['status'] = 'error'
                result['message'] = f'SSH 連接超時: {uart_ip}:{uart_port}'
                result['details'] = {
                    'uart_ip': uart_ip,
                    'uart_user': uart_user,
                    'uart_port': uart_port,
                    'error': 'Connection timeout'
                }
                logger.error(f"❌ SSH timeout for {uart_ip}")
                
            except socket.error as e:
                result['status'] = 'error'
                result['message'] = f'SSH 連接錯誤: {str(e)}'
                result['details'] = {
                    'uart_ip': uart_ip,
                    'uart_user': uart_user,
                    'uart_port': uart_port,
                    'error': str(e)
                }
                logger.error(f"❌ SSH error for {uart_ip}: {e}")
                
            except Exception as e:
                result['status'] = 'error'
                result['message'] = f'SSH 連接失敗: {str(e)}'
                result['details'] = {
                    'uart_ip': uart_ip,
                    'error': str(e)
                }
                logger.error(f"❌ SSH failed for {uart_ip}: {e}")
                
        except Exception as e:
            result['status'] = 'error'
            result['message'] = f'檢查 UART SSH 時發生錯誤: {str(e)}'
            result['details'] = {'error': str(e)}
            logger.error(f"Exception checking UART SSH for {host.hostname}: {e}", exc_info=True)
        
        return result
    
    def _check_nas_connection(self):
        """
        NAS 連線檢查
        驗證 NAS 路徑是否可訪問，並測試連線狀態
        """
        try:
            logger.info("🔍 Checking NAS connection...")
            
            result = {
                'status': 'unknown',
                'message': '',
                'value': 'N/A',
                'details': {},
                'suggestions': []
            }
            
            # 檢查 Inventory 是否有 NAS 路徑
            if not self.inventory or not self.inventory.nas_path:
                result['status'] = 'warning'
                result['message'] = '未設定 NAS 路徑'
                result['details'] = {'error': 'No NAS path configured'}
                result['suggestions'] = ['請設定 NAS 路徑以啟用 NAS 連線檢查']
                self.validation_results['checks']['nas_connection'] = result
                logger.warning("⚠️ No NAS path configured")
                return
            
            # 獲取 NAS 資訊
            from library.services.ansible_inventory_service import AnsibleInventoryService
            service = AnsibleInventoryService()
            linux_path = service.convert_windows_path_to_linux(self.inventory.nas_path)
            full_path = os.path.join(linux_path, self.inventory.file_name)
            
            # 檢查文件是否存在（基本檢查）
            file_exists = os.path.exists(full_path)
            file_readable = os.access(full_path, os.R_OK) if file_exists else False
            
            result['details'] = {
                'nas_path': self.inventory.nas_path,
                'linux_path': linux_path,
                'full_path': full_path,
                'file_exists': file_exists,
                'file_readable': file_readable
            }
            
            # 執行 NAS 連線測試（使用現有的 nas_service）
            try:
                from api.nas_service import check_nas_connection
                
                logger.info(f"Testing NAS connection to {full_path}...")
                status, response_time, upload_speed, download_speed, error_message = check_nas_connection()
                
                result['details'].update({
                    'connection_status': status,
                    'response_time_ms': response_time,
                    'upload_speed_mbps': upload_speed,
                    'download_speed_mbps': download_speed,
                    'error_message': error_message
                })
                
                # 根據連線結果設定狀態
                if status == 'success':
                    if file_exists and file_readable:
                        result['status'] = 'success'
                        result['message'] = f'NAS 連線正常，文件可訪問 ({response_time:.1f}ms)' if response_time else 'NAS 連線正常，文件可訪問'
                        result['value'] = '✓ 可用'
                        logger.info(f"✓ NAS connection successful, file accessible")
                    else:
                        result['status'] = 'warning'
                        result['message'] = 'NAS 連線正常，但文件不存在或不可讀'
                        result['value'] = '⚠ 文件問題'
                        result['suggestions'] = [
                            f'文件路徑: {full_path}',
                            '請檢查文件是否存在' if not file_exists else '請檢查文件讀取權限'
                        ]
                        logger.warning(f"⚠️ NAS connected but file issue: exists={file_exists}, readable={file_readable}")
                else:
                    result['status'] = 'error'
                    result['message'] = f'NAS 連線失敗: {error_message}'
                    result['value'] = '✗ 無法連線'
                    result['suggestions'] = [
                        '檢查 NAS 伺服器是否運行',
                        '檢查網路連線',
                        '檢查 SMB 共享權限',
                        f'錯誤: {error_message}'
                    ]
                    logger.error(f"✗ NAS connection failed: {error_message}")
                
            except ImportError:
                result['status'] = 'warning'
                result['message'] = 'NAS 連線測試模組未安裝'
                result['value'] = 'N/A'
                result['suggestions'] = ['請安裝 pysmb 套件: pip install pysmb']
                logger.warning("⚠️ NAS service module not available")
            
            except Exception as nas_error:
                result['status'] = 'error'
                result['message'] = f'NAS 連線測試失敗: {str(nas_error)}'
                result['value'] = '✗ 測試失敗'
                result['details']['test_error'] = str(nas_error)
                result['suggestions'] = [f'測試過程發生錯誤: {str(nas_error)}']
                logger.error(f"✗ NAS connection test failed: {nas_error}", exc_info=True)
            
            self.validation_results['checks']['nas_connection'] = result
            
        except Exception as e:
            logger.error(f"❌ NAS connection check exception: {e}", exc_info=True)
            self.validation_results['checks']['nas_connection'] = {
                'status': 'error',
                'message': f'NAS 檢查時發生錯誤: {str(e)}',
                'value': '✗ 錯誤',
                'details': {'exception': str(e)},
                'suggestions': [f'檢查發生異常: {str(e)}']
            }
    
    def _is_valid_ip(self, ip_string: str) -> bool:
        """驗證 IPv4 地址格式"""
        try:
            ipaddress.IPv4Address(ip_string)
            return True
        except (ValueError, ipaddress.AddressValueError):
            return False
    
    def _check_network_connectivity(self):
        """網路連線測試（可選，耗時）"""
        try:
            logger.info("Checking network connectivity...")
            
            # TODO: 實現網路連線測試
            # 使用多線程並行測試
            
            self.validation_results['checks']['network_connectivity'] = {
                'status': 'warning',
                'message': '網路連線測試功能開發中',
                'value': 'N/A',
                'details': {},
                'suggestions': ['此功能將在後續版本實現']
            }
            
        except Exception as e:
            logger.error(f"Network connectivity check exception: {e}", exc_info=True)
            self.validation_results['checks']['network_connectivity'] = self._create_error_check('network_connectivity', str(e))
    
    def _calculate_overall_status(self):
        """計算總體狀態"""
        checks = self.validation_results['checks']
        
        if not checks:
            self.validation_results['overall_status'] = 'unknown'
            return
        
        total = len(checks)
        passed = sum(1 for c in checks.values() if c['status'] == 'success')
        warnings = sum(1 for c in checks.values() if c['status'] == 'warning')
        errors = sum(1 for c in checks.values() if c['status'] == 'error')
        
        self.validation_results['summary'] = {
            'total_checks': total,
            'passed': passed,
            'warnings': warnings,
            'errors': errors
        }
        
        if errors > 0:
            self.validation_results['overall_status'] = 'error'
        elif warnings > 0:
            self.validation_results['overall_status'] = 'warning'
        elif passed == total:
            self.validation_results['overall_status'] = 'success'
        else:
            self.validation_results['overall_status'] = 'unknown'
        
        logger.info(f"Summary: {passed}/{total} passed, {warnings} warnings, {errors} errors")
    
    def _create_error_result(self, message: str) -> Dict:
        """創建錯誤結果"""
        return {
            'overall_status': 'error',
            'inventory_id': self.inventory_id,
            'error': message,
            'checks': {},
            'summary': {
                'total_checks': 0,
                'passed': 0,
                'warnings': 0,
                'errors': 1
            }
        }
    
    def _create_error_check(self, check_name: str, error: str) -> Dict:
        """創建錯誤檢查項目"""
        return {
            'status': 'error',
            'message': f'檢查失敗: {error}',
            'value': 'N/A',
            'details': {'error': error},
            'suggestions': ['檢查系統日誌以獲取更多信息', '聯繫管理員']
        }
