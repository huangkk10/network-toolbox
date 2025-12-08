"""
Jenkins Build Configuration Validator

Validates Jenkins build configurations by checking HOST_IP, HOST_MAC, and UART_IP
against DHCP records. Fetches actual config from Ansible Inventory API.

Author: Network Toolbox Team
Created: 2025-11-14
Updated: 2025-11-16 - Added Ansible Inventory API integration
"""

import logging
import re
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class BuildConfigValidator:
    """
    Validates Jenkins Build configurations.
    
    Config sources (priority order):
    1. Ansible Inventory API (actual build config from Jenkins)
    2. Database JenkinsBuild.parameters field (fallback)
    """
    
    def __init__(self, build_id: int, dhcp_server_ids: Optional[List[int]] = None, auto_check_on_failure: bool = True):
        self.build_id = build_id
        self.dhcp_server_ids = dhcp_server_ids or []
        self.auto_check_on_failure = auto_check_on_failure
        self.build = None
        self.config = {}
        self.config_source = 'unknown'
        self.validation_results = {
            'overall_status': 'unknown',
            'config_source': 'unknown',
            'build_result': None,  # 新增：記錄 Build 的結果狀態
            'auto_triggered': False,  # 新增：是否為自動觸發的檢查
            'checks': {
                'host_ip': {
                    'status': 'unknown',
                    'message': '',
                    'value': None,
                    'details': {},
                    'suggestions': []
                },
                'host_mac': {
                    'status': 'unknown',
                    'message': '',
                    'value': None,
                    'details': {},
                    'suggestions': []
                },
                'uart_ip': {
                    'status': 'unknown',
                    'message': '',
                    'value': None,
                    'details': {},
                    'suggestions': []
                },
                'uart_ssh': {
                    'status': 'unknown',
                    'message': '',
                    'value': None,
                    'details': {},
                    'suggestions': []
                },
                'nas_connection': {
                    'status': 'unknown',
                    'message': '',
                    'value': None,
                    'details': {},
                    'suggestions': []
                },
                'mdt_web': {
                    'status': 'unknown',
                    'message': '',
                    'value': None,
                    'details': {},
                    'suggestions': []
                },
                'fatal_errors': {
                    'status': 'unknown',
                    'message': '',
                    'value': None,
                    'details': {},
                    'suggestions': []
                }
            },
            'summary': {
                'total_checks': 7,
                'passed': 0,
                'warnings': 0,
                'errors': 0
            }
        }
    
    def validate(self) -> Dict:
        """Execute full validation"""
        try:
            logger.info(f"Starting validation for Build ID: {self.build_id}")
            
            if not self._load_build():
                return self._create_error_result("Failed to load build")
            
            # 檢查 Build 狀態，如果不是 SUCCESS 則標記為自動觸發
            if self.auto_check_on_failure and self.build.result != 'SUCCESS':
                self.validation_results['auto_triggered'] = True
                logger.warning(f"⚠️ Build {self.build_id} has {self.build.result} status (not SUCCESS), automatically triggering config validation")
            
            # 記錄 Build 結果
            self.validation_results['build_result'] = self.build.result
            
            if not self._parse_config():
                return self._create_error_result("Failed to parse config")
            
            self.validation_results['config_source'] = self.config_source
            
            self._determine_dhcp_servers()
            self._check_host_ip()
            self._check_host_mac()
            self._check_uart_ip()
            self._check_uart_ssh_connection()
            self._check_nas_connection()
            self._check_mdt_web()
            self._check_fatal_errors()
            self._calculate_overall_status()
            
            logger.info(f"Validation complete. Status: {self.validation_results['overall_status']}, Source: {self.config_source}")
            
            return self.validation_results
            
        except Exception as e:
            logger.error(f"Validation error: {e}", exc_info=True)
            return self._create_error_result(f"Validation exception: {str(e)}")
    
    def _load_build(self) -> bool:
        """Load build data"""
        try:
            from api.models import JenkinsBuild
            
            self.build = JenkinsBuild.objects.filter(id=self.build_id).first()
            
            if not self.build:
                logger.error(f"Build not found: {self.build_id}")
                return False
            
            logger.info(f"Loaded Build: {self.build.id}, Job: {self.build.job.name if self.build.job else 'Unknown'}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load build: {e}", exc_info=True)
            return False
    
    def _parse_config(self) -> bool:
        """
        Parse build config from Ansible Inventory API (preferred) or database (fallback)
        """
        try:
            # Method 1: Fetch from Ansible Inventory API
            config_from_api = self._fetch_config_from_ansible_api()
            
            if config_from_api:
                self.config = config_from_api
                self.config_source = 'ansible_inventory'
                logger.info(f"✅ Got config from Ansible Inventory ({len(self.config)} params)")
                logger.debug(f"Config keys: {list(self.config.keys())[:20]}")
                return True
            
            # Method 2: Use database parameters (fallback)
            logger.warning("Failed to fetch from Ansible API, using database parameters")
            
            self.config = {}
            
            if self.build.parameters:
                if isinstance(self.build.parameters, dict):
                    self.config.update(self.build.parameters)
                    logger.info(f"Loaded parameters: {list(self.build.parameters.keys())}")
            
            if self.build.ansible_config:
                if isinstance(self.build.ansible_config, dict):
                    self.config.update(self.build.ansible_config)
                    logger.info(f"Loaded ansible_config: {list(self.build.ansible_config.keys())}")
            
            if not self.config:
                logger.warning(f"No config data for Build {self.build_id}")
                return False
            
            self.config_source = 'database'
            logger.info(f"Loaded config from database ({len(self.config)} params)")
            return True
            
        except Exception as e:
            logger.error(f"Failed to parse config: {e}", exc_info=True)
            return False
    
    def _fetch_config_from_ansible_api(self) -> Optional[Dict]:
        """
        Fetch actual config from Ansible Inventory API
        
        Optimized Strategy:
        1. Get full inventory once (uses cache: ansible_inventory.json)
        2. Extract host config from _meta.hostvars[hostname]
        3. If uart_host is hostname, extract its ansible_host from full inventory
        
        Returns:
            Config dict or None if failed
        """
        try:
            if not self.build.job or not self.build.job.id:
                logger.warning("Build has no associated job, cannot fetch Ansible Inventory")
                return None
            
            job_name = self.build.job.name
            if not job_name:
                logger.warning("Job has no name, cannot fetch host config")
                return None
            
            import requests
            
            job_id = self.build.job.id
            
            # Optimized: Use full inventory API (single cache file: ansible_inventory.json)
            api_url = f"http://localhost:8000/api/jenkins-jobs/{job_id}/ansible-inventory/"
            
            logger.info(f"Calling Ansible Inventory API (--list): GET {api_url}?use_cache=true")
            
            response = requests.get(api_url, params={'use_cache': True}, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get('success') and data.get('data'):
                    full_inventory = data['data']
                    
                    # Extract host config from _meta.hostvars
                    hostvars = full_inventory.get('_meta', {}).get('hostvars', {})
                    
                    if job_name not in hostvars:
                        logger.warning(f"Host '{job_name}' not found in inventory hostvars")
                        return None
                    
                    host_config = hostvars[job_name]
                    
                    logger.info(f"✅ Got Ansible config for host: {job_name} ({len(host_config)} params)")
                    
                    # Map Ansible Inventory fields to validator fields
                    mapped_config = {}
                    mapped_config.update(host_config)
                    
                    if 'ansible_host' in host_config:
                        mapped_config['HOST_IP'] = host_config['ansible_host']
                        logger.debug(f"Mapped ansible_host -> HOST_IP: {host_config['ansible_host']}")
                    
                    if 'macaddress' in host_config:
                        mapped_config['HOST_MAC'] = host_config['macaddress']
                        logger.debug(f"Mapped macaddress -> HOST_MAC: {host_config['macaddress']}")
                    
                    # Map uart_host to UART_IP (optimized: resolve from full inventory)
                    if 'uart_host' in host_config:
                        uart_host = host_config['uart_host']
                        
                        # Check if uart_host is an IP or hostname
                        if self._is_valid_ip(uart_host):
                            # It's already an IP, use it directly
                            mapped_config['UART_IP'] = uart_host
                            logger.debug(f"Mapped uart_host -> UART_IP: {uart_host} (IP format)")
                        else:
                            # It's a hostname, resolve from full inventory (no additional API call!)
                            logger.debug(f"uart_host is hostname: {uart_host}, resolving from inventory...")
                            
                            if uart_host in hostvars:
                                uart_config = hostvars[uart_host]
                                
                                if 'ansible_host' in uart_config:
                                    resolved_ip = uart_config['ansible_host']
                                    mapped_config['UART_IP'] = resolved_ip
                                    mapped_config['UART_HOSTNAME'] = uart_host
                                    logger.info(f"✅ Resolved UART hostname '{uart_host}' -> IP: {resolved_ip} (from inventory cache)")
                                    
                                    # 同時獲取 UART 主機的認證信息
                                    if 'ansible_user' in uart_config:
                                        mapped_config['uart_user'] = uart_config['ansible_user']
                                        logger.debug(f"  Got UART ansible_user: {uart_config['ansible_user']}")
                                    
                                    if 'ansible_password' in uart_config:
                                        mapped_config['uart_password'] = uart_config['ansible_password']
                                        logger.debug(f"  Got UART ansible_password: ***")
                                    
                                    if 'ansible_port' in uart_config:
                                        mapped_config['uart_port'] = uart_config['ansible_port']
                                        logger.debug(f"  Got UART ansible_port: {uart_config['ansible_port']}")
                                else:
                                    logger.warning(f"UART hostname '{uart_host}' found but has no ansible_host")
                                    mapped_config['UART_IP'] = uart_host
                            else:
                                logger.warning(f"UART hostname '{uart_host}' not found in inventory")
                                mapped_config['UART_IP'] = uart_host
                    
                    return mapped_config
                else:
                    logger.warning(f"Ansible Inventory API format error: success={data.get('success')}, has_data={bool(data.get('data'))}")
                    return None
            elif response.status_code == 404:
                logger.warning(f"Inventory not found (404) for Job ID {job_id}")
                return None
            else:
                logger.warning(f"Ansible Inventory API error: HTTP {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Failed to call Ansible Inventory API: {e}", exc_info=True)
            return None
    
    def _determine_dhcp_servers(self):
        """Determine DHCP servers to query"""
        try:
            from api.models import DHCPServer
            
            if self.dhcp_server_ids:
                logger.info(f"Using API-specified DHCP servers: {self.dhcp_server_ids}")
                return
            
            dhcp_server_name = self.config.get('DHCP_SERVER')
            if dhcp_server_name:
                server = DHCPServer.objects.filter(name=dhcp_server_name).first()
                if server:
                    self.dhcp_server_ids = [server.id]
                    logger.info(f"Found DHCP server from config: {dhcp_server_name} (ID: {server.id})")
                    return
            
            online_servers = DHCPServer.objects.filter(status='online')
            self.dhcp_server_ids = list(online_servers.values_list('id', flat=True))
            logger.info(f"Using all online DHCP servers: {self.dhcp_server_ids}")
            
        except Exception as e:
            logger.error(f"Failed to determine DHCP servers: {e}", exc_info=True)
            self.dhcp_server_ids = []
    
    def _check_host_ip(self):
        """Check HOST_IP config"""
        check_result = self.validation_results['checks']['host_ip']
        
        try:
            host_ip = self.config.get('HOST_IP', '').strip()
            check_result['value'] = host_ip
            
            if not host_ip:
                check_result['status'] = 'error'
                check_result['message'] = 'HOST_IP not set'
                check_result['suggestions'].append('Please set HOST_IP parameter in build config')
                return
            
            if not self._is_valid_ip(host_ip):
                check_result['status'] = 'error'
                check_result['message'] = f'HOST_IP format invalid: {host_ip}'
                check_result['suggestions'].append('Check IP address format (e.g., 192.168.1.100)')
                return
            
            lease_info = self._query_dhcp_lease(host_ip)
            
            if lease_info:
                check_result['status'] = 'success'
                check_result['message'] = f'HOST_IP found in DHCP lease: {host_ip}'
                check_result['details'] = {
                    'ip_address': host_ip,
                    'mac_address': lease_info.get('mac_address'),
                    'hostname': lease_info.get('hostname'),
                    'dhcp_server': lease_info.get('dhcp_server'),
                    'lease_start': lease_info.get('lease_start'),
                    'lease_end': lease_info.get('lease_end'),
                    'lease_state': lease_info.get('lease_state')
                }
            else:
                check_result['status'] = 'warning'
                check_result['message'] = f'HOST_IP not found in DHCP lease: {host_ip}'
                check_result['details'] = {'ip_address': host_ip}
                check_result['suggestions'].extend([
                    'IP may not have DHCP lease yet',
                    'Check if device is powered on and connected',
                    f'Queried DHCP servers: {self.dhcp_server_ids}'
                ])
            
        except Exception as e:
            logger.error(f"Failed to check HOST_IP: {e}", exc_info=True)
            check_result['status'] = 'error'
            check_result['message'] = f'Error checking HOST_IP: {str(e)}'
    
    def _check_host_mac(self):
        """Check HOST_MAC config"""
        check_result = self.validation_results['checks']['host_mac']
        
        try:
            host_mac = self.config.get('HOST_MAC', '').strip()
            host_ip = self.config.get('HOST_IP', '').strip()
            check_result['value'] = host_mac
            
            if not host_mac:
                check_result['status'] = 'warning'
                check_result['message'] = 'HOST_MAC not set'
                check_result['suggestions'].append('Recommend setting HOST_MAC for device identification')
                return
            
            normalized_mac = self._normalize_mac(host_mac)
            if not normalized_mac:
                check_result['status'] = 'error'
                check_result['message'] = f'HOST_MAC format invalid: {host_mac}'
                check_result['suggestions'].extend([
                    'Valid formats: 00:11:22:33:44:55',
                    'Or: 00-11-22-33-44-55',
                    'Or: 001122334455'
                ])
                return
            
            if host_ip and self._is_valid_ip(host_ip):
                lease_info = self._query_dhcp_lease(host_ip)
                
                if lease_info:
                    dhcp_mac = self._normalize_mac(lease_info.get('mac_address', ''))
                    
                    if dhcp_mac == normalized_mac:
                        check_result['status'] = 'success'
                        check_result['message'] = f'HOST_MAC matches DHCP lease: {host_mac}'
                        check_result['details'] = {
                            'mac_address': host_mac,
                            'normalized': normalized_mac,
                            'dhcp_mac': lease_info.get('mac_address'),
                            'ip_address': host_ip,
                            'match': True
                        }
                    else:
                        check_result['status'] = 'error'
                        check_result['message'] = f'HOST_MAC mismatch with DHCP lease'
                        check_result['details'] = {
                            'config_mac': host_mac,
                            'dhcp_mac': lease_info.get('mac_address'),
                            'ip_address': host_ip,
                            'match': False
                        }
                        check_result['suggestions'].extend([
                            f'Config MAC: {host_mac}',
                            f'DHCP lease MAC: {lease_info.get("mac_address")}',
                            'Check if correct MAC address is used'
                        ])
                else:
                    check_result['status'] = 'success'
                    check_result['message'] = f'HOST_MAC format valid: {host_mac}'
                    check_result['details'] = {
                        'mac_address': host_mac,
                        'normalized': normalized_mac
                    }
            else:
                check_result['status'] = 'success'
                check_result['message'] = f'HOST_MAC format valid: {host_mac}'
                check_result['details'] = {
                    'mac_address': host_mac,
                    'normalized': normalized_mac
                }
            
        except Exception as e:
            logger.error(f"Failed to check HOST_MAC: {e}", exc_info=True)
            check_result['status'] = 'error'
            check_result['message'] = f'Error checking HOST_MAC: {str(e)}'
    
    def _check_uart_ip(self):
        """Check UART_IP config (accepts both IP and hostname)"""
        check_result = self.validation_results['checks']['uart_ip']
        
        try:
            uart_ip = self.config.get('UART_IP', '').strip()
            uart_hostname = self.config.get('UART_HOSTNAME', '')
            check_result['value'] = uart_ip
            
            if not uart_ip:
                check_result['status'] = 'warning'
                check_result['message'] = 'UART_IP not set'
                check_result['suggestions'].append('If UART connection needed, set UART_IP parameter')
                return
            
            # Check if it's an IP address or hostname
            is_ip_format = self._is_valid_ip(uart_ip)
            
            if is_ip_format:
                # It's an IP address, check DHCP lease
                lease_info = self._query_dhcp_lease(uart_ip)
                
                if lease_info:
                    check_result['status'] = 'success'
                    
                    # If this IP was resolved from a hostname, mention it
                    if uart_hostname:
                        check_result['message'] = f'UART_IP resolved from hostname {uart_hostname} and found in DHCP lease: {uart_ip}'
                        check_result['details'] = {
                            'hostname': uart_hostname,
                            'ip_address': uart_ip,
                            'type': 'resolved_from_hostname',
                            'mac_address': lease_info.get('mac_address'),
                            'dhcp_hostname': lease_info.get('hostname'),
                            'dhcp_server': lease_info.get('dhcp_server'),
                            'lease_start': lease_info.get('lease_start'),
                            'lease_end': lease_info.get('lease_end'),
                            'lease_state': lease_info.get('lease_state')
                        }
                    else:
                        check_result['message'] = f'UART_IP found in DHCP lease: {uart_ip}'
                        check_result['details'] = {
                            'ip_address': uart_ip,
                            'type': 'ip',
                            'mac_address': lease_info.get('mac_address'),
                            'hostname': lease_info.get('hostname'),
                            'dhcp_server': lease_info.get('dhcp_server'),
                            'lease_start': lease_info.get('lease_start'),
                            'lease_end': lease_info.get('lease_end'),
                            'lease_state': lease_info.get('lease_state')
                        }
                else:
                    check_result['status'] = 'warning'
                    
                    if uart_hostname:
                        check_result['message'] = f'UART_IP resolved from hostname {uart_hostname} but not found in DHCP lease: {uart_ip}'
                        check_result['details'] = {
                            'hostname': uart_hostname,
                            'ip_address': uart_ip,
                            'type': 'resolved_from_hostname'
                        }
                    else:
                        check_result['message'] = f'UART_IP not found in DHCP lease: {uart_ip}'
                        check_result['details'] = {
                            'ip_address': uart_ip,
                            'type': 'ip'
                        }
                    
                    check_result['suggestions'].extend([
                        'IP may not have DHCP lease yet',
                        'Check if UART device is connected to network',
                        f'Queried DHCP servers: {self.dhcp_server_ids}'
                    ])
            else:
                # It's a hostname (couldn't be resolved to IP)
                check_result['status'] = 'success'
                check_result['message'] = f'UART_IP configured as hostname: {uart_ip}'
                check_result['details'] = {
                    'hostname': uart_ip,
                    'type': 'hostname'
                }
                check_result['suggestions'].append(
                    f'Using UART hostname: {uart_ip} (DHCP validation skipped for hostnames)'
                )
            
        except Exception as e:
            logger.error(f"Failed to check UART_IP: {e}", exc_info=True)
            check_result['status'] = 'error'
            check_result['message'] = f'Error checking UART_IP: {str(e)}'
    
    def _check_uart_ssh_connection(self):
        """Check SSH connection to UART PC"""
        check_result = self.validation_results['checks']['uart_ssh']
        
        try:
            # Get UART connection info from config
            # Note: Values from Ansible Inventory may be non-string types (e.g., int password)
            uart_ip_raw = self.config.get('UART_IP', '')
            uart_ip = str(uart_ip_raw).strip() if uart_ip_raw else ''
            
            uart_user_raw = self.config.get('uart_user', '')
            uart_user = str(uart_user_raw).strip() if uart_user_raw else ''
            
            uart_password_raw = self.config.get('uart_password', '')
            uart_password = str(uart_password_raw) if uart_password_raw else ''  # Don't strip password
            
            uart_port_raw = self.config.get('uart_port', 22)
            uart_port = int(uart_port_raw) if uart_port_raw else 22  # Ensure int type
            
            # Store connection info in check result
            check_result['value'] = uart_ip
            check_result['details'] = {
                'ip': uart_ip,
                'user': uart_user,
                'port': uart_port,
                'password_set': bool(uart_password)
            }
            
            # Check if UART_IP is set
            if not uart_ip:
                check_result['status'] = 'warning'
                check_result['message'] = 'UART_IP not set, SSH check skipped'
                check_result['suggestions'].append('Set UART_IP if SSH connection to UART PC is needed')
                return
            
            # Check if user is set
            if not uart_user:
                check_result['status'] = 'warning'
                check_result['message'] = 'UART user not set, SSH check skipped'
                check_result['suggestions'].append('Set uart_user in config for SSH authentication')
                return
            
            # Check if password is set
            if not uart_password:
                check_result['status'] = 'warning'
                check_result['message'] = 'UART password not set, SSH check skipped'
                check_result['suggestions'].append('Set uart_password in config for SSH authentication')
                return
            
            # Check if UART_IP is valid (skip if it's a hostname)
            is_ip_format = self._is_valid_ip(uart_ip)
            if not is_ip_format:
                # It's a hostname, try to resolve it
                uart_hostname = self.config.get('UART_HOSTNAME', uart_ip)
                check_result['status'] = 'warning'
                check_result['message'] = f'UART is configured as hostname: {uart_hostname}, SSH check requires IP address'
                check_result['details']['hostname'] = uart_hostname
                check_result['suggestions'].append('Configure UART_IP as IP address for SSH connection test')
                return
            
            # Attempt SSH connection
            logger.info(f"Testing SSH connection to UART PC: {uart_user}@{uart_ip}:{uart_port}")
            
            import paramiko
            import socket
            
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            try:
                # Try to connect with timeout
                ssh.connect(
                    hostname=uart_ip,
                    port=uart_port,
                    username=uart_user,
                    password=uart_password,
                    timeout=10,
                    banner_timeout=10,
                    auth_timeout=10
                )
                
                # Connection successful
                check_result['status'] = 'success'
                check_result['message'] = f'SSH connection to UART PC successful: {uart_user}@{uart_ip}'
                check_result['details'].update({
                    'connected': True,
                    'connection_time': 'Success'
                })
                
                logger.info(f"✅ SSH connection to UART PC successful: {uart_user}@{uart_ip}")
                
                # Close connection
                ssh.close()
                
            except paramiko.AuthenticationException:
                check_result['status'] = 'error'
                check_result['message'] = f'SSH authentication failed: Invalid username or password'
                check_result['details']['connected'] = False
                check_result['details']['error'] = 'Authentication failed'
                check_result['suggestions'].extend([
                    'Check if uart_user is correct',
                    'Check if uart_password is correct',
                    'Verify credentials on UART PC'
                ])
                logger.error(f"❌ SSH authentication failed for {uart_user}@{uart_ip}")
                
            except socket.timeout:
                check_result['status'] = 'error'
                check_result['message'] = f'SSH connection timeout to {uart_ip}:{uart_port}'
                check_result['details']['connected'] = False
                check_result['details']['error'] = 'Connection timeout'
                check_result['suggestions'].extend([
                    'Check if UART PC is powered on',
                    'Check network connectivity to UART PC',
                    f'Verify SSH service is running on port {uart_port}'
                ])
                logger.error(f"❌ SSH connection timeout to {uart_ip}:{uart_port}")
                
            except socket.error as e:
                check_result['status'] = 'error'
                check_result['message'] = f'SSH connection error: {str(e)}'
                check_result['details']['connected'] = False
                check_result['details']['error'] = str(e)
                check_result['suggestions'].extend([
                    'Check if UART PC is reachable on the network',
                    'Verify firewall settings allow SSH connections',
                    f'Check if SSH is listening on port {uart_port}'
                ])
                logger.error(f"❌ SSH connection error to {uart_ip}: {e}")
                
            except Exception as e:
                check_result['status'] = 'error'
                check_result['message'] = f'SSH connection failed: {str(e)}'
                check_result['details']['connected'] = False
                check_result['details']['error'] = str(e)
                check_result['suggestions'].append('Check SSH connection settings and UART PC status')
                logger.error(f"❌ SSH connection failed to {uart_ip}: {e}")
            
        except Exception as e:
            logger.error(f"Failed to check UART SSH connection: {e}", exc_info=True)
            check_result['status'] = 'error'
            check_result['message'] = f'Error checking UART SSH: {str(e)}'
    
    def _query_dhcp_lease(self, ip_address: str) -> Optional[Dict]:
        """Query DHCP lease for IP"""
        try:
            from api.models import DHCPLease
            
            query = DHCPLease.objects.filter(ip_address=ip_address)
            
            if self.dhcp_server_ids:
                query = query.filter(server_id__in=self.dhcp_server_ids)
            
            lease = query.first()
            
            if lease:
                return {
                    'ip_address': lease.ip_address,
                    'mac_address': lease.mac_address,
                    'hostname': lease.hostname,
                    'dhcp_server': lease.server.name if lease.server else None,
                    'lease_start': lease.lease_start.isoformat() if lease.lease_start else None,
                    'lease_end': lease.lease_end.isoformat() if lease.lease_end else None,
                    'is_active': lease.is_active
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to query DHCP lease (IP: {ip_address}): {e}", exc_info=True)
            return None
    
    def _calculate_overall_status(self):
        """Calculate overall validation status"""
        checks = self.validation_results['checks']
        summary = self.validation_results['summary']
        
        summary['passed'] = sum(1 for c in checks.values() if c['status'] == 'success')
        summary['warnings'] = sum(1 for c in checks.values() if c['status'] == 'warning')
        summary['errors'] = sum(1 for c in checks.values() if c['status'] == 'error')
        
        if summary['errors'] > 0:
            self.validation_results['overall_status'] = 'error'
        elif summary['warnings'] > 0:
            self.validation_results['overall_status'] = 'warning'
        elif summary['passed'] == summary['total_checks']:
            self.validation_results['overall_status'] = 'success'
        else:
            self.validation_results['overall_status'] = 'unknown'
    
    def _create_error_result(self, error_message: str) -> Dict:
        """Create error result"""
        return {
            'overall_status': 'error',
            'config_source': self.config_source,
            'error': error_message,
            'checks': {},
            'summary': {
                'total_checks': 0,
                'passed': 0,
                'warnings': 0,
                'errors': 1
            }
        }
    
    @staticmethod
    def _is_valid_ip(ip_string: str) -> bool:
        """Validate IPv4 address format"""
        pattern = r'^((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$'
        return bool(re.match(pattern, ip_string))
    
    @staticmethod
    def _normalize_mac(mac_string: str) -> Optional[str]:
        """
        Normalize MAC address to XX:XX:XX:XX:XX:XX format
        
        Supported inputs: 00:11:22:33:44:55, 00-11-22-33-44-55, 001122334455, 0011.2233.4455
        """
        if not mac_string:
            return None
        
        mac_clean = re.sub(r'[:\-\.]', '', mac_string.upper())
        
        if len(mac_clean) != 12 or not re.match(r'^[0-9A-F]{12}$', mac_clean):
            return None
        
        return ':'.join(mac_clean[i:i+2] for i in range(0, 12, 2))
    
    def _check_nas_connection(self):
        """
        NAS 連線檢查
        驗證 Build 對應的 NAS 儲存路徑是否可訪問
        """
        check_result = self.validation_results['checks']['nas_connection']
        
        try:
            import os
            
            # 獲取 Build 的 log_file_path（儲存路徑）
            if not self.build or not self.build.log_file_path:
                check_result['status'] = 'warning'
                check_result['message'] = '未設定日誌檔案路徑，跳過 NAS 檢查'
                check_result['value'] = 'N/A'
                check_result['suggestions'] = ['Build 尚未有 console log 路徑']
                return
            
            log_path = self.build.log_file_path
            storage_dir = os.path.dirname(log_path)
            
            check_result['value'] = storage_dir
            check_result['details'] = {
                'log_file_path': log_path,
                'storage_dir': storage_dir
            }
            
            # 檢查目錄是否存在
            dir_exists = os.path.exists(storage_dir)
            file_exists = os.path.exists(log_path)
            
            check_result['details']['dir_exists'] = dir_exists
            check_result['details']['file_exists'] = file_exists
            
            if not dir_exists:
                check_result['status'] = 'error'
                check_result['message'] = f'NAS 儲存目錄不存在: {storage_dir}'
                check_result['suggestions'] = [
                    '檢查 NAS 是否已掛載',
                    '確認網路連線正常',
                    '檢查目錄權限'
                ]
                logger.error(f"❌ NAS storage directory not found: {storage_dir}")
                return
            
            # 檢查目錄可讀性
            dir_readable = os.access(storage_dir, os.R_OK)
            dir_writable = os.access(storage_dir, os.W_OK)
            
            check_result['details']['dir_readable'] = dir_readable
            check_result['details']['dir_writable'] = dir_writable
            
            if not dir_readable:
                check_result['status'] = 'error'
                check_result['message'] = f'NAS 儲存目錄無讀取權限'
                check_result['suggestions'] = ['檢查目錄權限設定', '確認 NAS 掛載正確']
                logger.error(f"❌ NAS storage directory not readable: {storage_dir}")
                return
            
            # 執行 NAS 連線測試（如果有服務可用）
            try:
                from api.nas_service import check_nas_connection
                
                status, response_time, upload_speed, download_speed, error_message = check_nas_connection()
                
                check_result['details']['connection_status'] = status
                check_result['details']['response_time_ms'] = response_time
                check_result['details']['upload_speed_mbps'] = upload_speed
                check_result['details']['download_speed_mbps'] = download_speed
                
                if status == 'success':
                    check_result['status'] = 'success'
                    if response_time:
                        check_result['message'] = f'NAS 連線正常 ({response_time:.1f}ms)'
                    else:
                        check_result['message'] = 'NAS 連線正常'
                    logger.info(f"✅ NAS connection successful")
                else:
                    check_result['status'] = 'warning'
                    check_result['message'] = f'NAS 連線測試失敗: {error_message}'
                    check_result['details']['error_message'] = error_message
                    check_result['suggestions'] = ['NAS 可能暫時不可用', '稍後重試']
                    logger.warning(f"⚠️ NAS connection test failed: {error_message}")
                    
            except ImportError:
                # NAS service 不可用，但目錄存在且可讀，視為成功
                check_result['status'] = 'success'
                check_result['message'] = f'NAS 儲存目錄可訪問'
                check_result['details']['connection_test'] = 'skipped (service unavailable)'
                logger.info(f"✓ NAS directory accessible (connection test skipped)")
                
            except Exception as nas_error:
                # NAS 測試失敗，但目錄存在，給予警告
                check_result['status'] = 'warning'
                check_result['message'] = f'NAS 儲存目錄可訪問，但連線測試失敗'
                check_result['details']['test_error'] = str(nas_error)
                logger.warning(f"⚠️ NAS connection test error: {nas_error}")
                
        except Exception as e:
            logger.error(f"Failed to check NAS connection: {e}", exc_info=True)
            check_result['status'] = 'error'
            check_result['message'] = f'NAS 檢查時發生錯誤: {str(e)}'
            check_result['suggestions'] = ['檢查系統日誌']
    
    def _check_mdt_web(self):
        """
        MDT Web 檢查
        驗證 Build 對應的設備在 MDT Web 中的配置是否一致
        僅當 Build 配置中有 device_number 時才執行
        """
        check_result = self.validation_results['checks']['mdt_web']
        
        try:
            # 檢查是否有 device_number
            device_number = self.config.get('device_number', '').strip()
            
            if not device_number:
                check_result['status'] = 'warning'
                check_result['message'] = '未設定 device_number，跳過 MDT Web 檢查'
                check_result['value'] = 'N/A'
                check_result['suggestions'] = ['如需 MDT Web 檢查，請在配置中添加 device_number']
                logger.info("⚠️ No device_number in config, skipping MDT Web check")
                return
            
            check_result['value'] = device_number
            check_result['details']['device_number'] = device_number
            
            # 優先從 HOST_IP 計算 MDT Web IP（最可靠的方式）
            mdt_web_ip = self._get_mdt_web_ip_from_host()
            
            # 備用：如果無法從 HOST_IP 計算，嘗試從 DHCP Server 推斷
            if not mdt_web_ip:
                dhcp_server_ip = self._get_dhcp_server_ip_for_mdt()
                if dhcp_server_ip:
                    check_result['details']['dhcp_server_ip'] = dhcp_server_ip
                    mdt_web_ip = self._calculate_mdt_web_ip(dhcp_server_ip)
            
            if not mdt_web_ip:
                check_result['status'] = 'warning'
                check_result['message'] = '無法確定 MDT Web IP，跳過檢查'
                check_result['suggestions'] = ['請確認 HOST_IP 設定正確']
                logger.warning("⚠️ Cannot determine MDT Web IP for MDT Web check")
                return
            
            check_result['details']['mdt_web_ip'] = mdt_web_ip
            
            # 連接 MDT Web 服務
            from library.services.mdt_web_service import MDTWebService
            
            mdt_service = MDTWebService(mdt_web_ip)
            is_accessible, connection_error = mdt_service.check_connection()
            
            check_result['details']['mdt_web_accessible'] = is_accessible
            
            if not is_accessible:
                # 檢查是否為未知網段
                network_prefix = '.'.join(mdt_web_ip.split('.')[:3])
                known_networks = ['10.250.10', '10.250.50', '10.250.71', 
                                  '10.250.120', '10.250.130', '10.250.140']
                is_unknown_network = network_prefix not in known_networks
                
                if is_unknown_network:
                    check_result['status'] = 'warning'
                    check_result['message'] = f'此網段可能沒有 MDT Web 伺服器 ({mdt_web_ip})'
                    check_result['suggestions'] = [
                        f'網段 {network_prefix} 不在已知 MDT Web 列表中',
                        '如確實有 MDT Web，請聯繫管理員更新配置'
                    ]
                else:
                    check_result['status'] = 'error'
                    check_result['message'] = f'MDT Web 無法訪問 ({mdt_web_ip})'
                    check_result['suggestions'] = [
                        f'檢查 MDT Web 伺服器 {mdt_web_ip} 是否運行',
                        '確認網路連線正常'
                    ]
                
                check_result['details']['connection_error'] = connection_error
                check_result['details']['is_unknown_network'] = is_unknown_network
                logger.warning(f"⚠️ MDT Web not accessible: {mdt_web_ip}")
                return
            
            # 驗證設備配置
            host_ip = self.config.get('HOST_IP', '').strip()
            host_mac = self.config.get('HOST_MAC', '').strip()
            job_name = self.build.job.name if self.build and self.build.job else ''
            
            validation_result = mdt_service.validate_device_config(device_number, {
                'hostname': job_name,
                'ansible_host': host_ip,
                'mac_address': host_mac
            })
            
            check_result['details']['device_found'] = validation_result.get('device_found', False)
            
            if not validation_result.get('device_found', False):
                check_result['status'] = 'error'
                check_result['message'] = f'設備 {device_number} 在 MDT Web 中找不到'
                check_result['suggestions'] = [
                    '確認 device_number 是否正確',
                    f'檢查 MDT Web ({mdt_web_ip}) 是否已同步設備資訊'
                ]
                logger.error(f"❌ Device {device_number} not found in MDT Web")
                return
            
            # 檢查配置一致性
            config_matches = validation_result.get('config_matches', False)
            differences = validation_result.get('differences', [])
            
            check_result['details']['config_matches'] = config_matches
            check_result['details']['differences'] = differences
            
            if not config_matches and differences:
                check_result['status'] = 'warning'
                check_result['message'] = f'設備 {device_number} 配置不一致'
                check_result['suggestions'] = [
                    '請更新 Inventory 配置或同步 MDT Web 資料'
                ]
                for diff in differences:
                    check_result['suggestions'].append(
                        f"  • {diff['field']}: Inventory={diff.get('inventory_value')}, MDT={diff.get('mdt_web_value')}"
                    )
                logger.warning(f"⚠️ Device {device_number} config mismatch: {differences}")
            else:
                check_result['status'] = 'success'
                check_result['message'] = f'設備 {device_number} 配置與 MDT Web 一致'
                logger.info(f"✅ Device {device_number} config matches MDT Web")
                
        except ImportError as e:
            check_result['status'] = 'warning'
            check_result['message'] = 'MDT Web 服務模組不可用'
            check_result['suggestions'] = ['MDT Web 檢查功能需要 mdt_web_service 模組']
            logger.warning(f"⚠️ MDT Web service not available: {e}")
            
        except Exception as e:
            logger.error(f"Failed to check MDT Web: {e}", exc_info=True)
            check_result['status'] = 'error'
            check_result['message'] = f'MDT Web 檢查時發生錯誤: {str(e)}'
            check_result['suggestions'] = ['檢查系統日誌']
    
    def _get_mdt_web_ip_from_host(self) -> Optional[str]:
        """
        根據 HOST_IP 計算 MDT Web IP
        
        MDT Web IP 規則：與設備 IP 同網段，最後一段為 .2
        例如：
        - HOST_IP: 10.250.10.100 → MDT Web: 10.250.10.2
        - HOST_IP: 10.250.50.55 → MDT Web: 10.250.50.2
        
        這是最可靠的方式，因為 MDT Web 與設備在同一個網段
        """
        try:
            host_ip = self.config.get('HOST_IP', '').strip()
            
            if not host_ip or not self._is_valid_ip(host_ip):
                logger.warning(f"MDT Web: Invalid or missing HOST_IP: {host_ip}")
                return None
            
            # 計算 MDT Web IP（前三段相同，最後一段為 .2）
            octets = host_ip.split('.')
            mdt_web_ip = f"{octets[0]}.{octets[1]}.{octets[2]}.2"
            
            logger.info(f"MDT Web: Calculated from HOST_IP {host_ip} → {mdt_web_ip}")
            return mdt_web_ip
            
        except Exception as e:
            logger.error(f"Failed to calculate MDT Web IP from HOST_IP: {e}", exc_info=True)
            return None
    
    def _get_dhcp_server_ip_for_mdt(self) -> Optional[str]:
        """
        獲取用於 MDT Web 檢查的 DHCP Server IP（備用方法）
        
        注意：此方法已不作為主要方式使用
        MDT Web IP 現在優先從 HOST_IP 計算（見 _get_mdt_web_ip_from_host）
        
        優先順序：
        1. 從 config 中的 DHCP_SERVER 名稱查詢
        2. 從已指定的 DHCP Server IDs 獲取（如果網段匹配 HOST_IP）
        """
        try:
            from api.models import DHCPServer
            
            host_ip = self.config.get('HOST_IP', '').strip()
            host_network_prefix = '.'.join(host_ip.split('.')[:3]) if host_ip and self._is_valid_ip(host_ip) else None
            
            # 方法 1: 從 config 中的 DHCP_SERVER 名稱查詢
            dhcp_server_name = self.config.get('DHCP_SERVER', '').strip()
            if dhcp_server_name:
                server = DHCPServer.objects.filter(name=dhcp_server_name).first()
                if server and server.ip_address:
                    logger.info(f"MDT Web: Got DHCP Server IP from config DHCP_SERVER: {server.ip_address}")
                    return server.ip_address
            
            # 方法 2: 從已指定的 DHCP Server IDs 獲取（但要驗證網段匹配）
            if self.dhcp_server_ids and host_network_prefix:
                for server_id in self.dhcp_server_ids:
                    server = DHCPServer.objects.filter(id=server_id).first()
                    if server and server.ip_address:
                        server_network_prefix = '.'.join(server.ip_address.split('.')[:3])
                        if server_network_prefix == host_network_prefix:
                            logger.info(f"MDT Web: Got matching DHCP Server IP: {server.ip_address} (matches HOST_IP network)")
                            return server.ip_address
                
                # 沒有匹配的，記錄警告
                logger.warning(f"MDT Web: No DHCP Server matches HOST_IP network {host_network_prefix}")
            
            logger.warning("MDT Web: Cannot determine DHCP Server IP from traditional methods")
            return None
            
        except Exception as e:
            logger.error(f"Failed to get DHCP server IP for MDT: {e}", exc_info=True)
            return None
    
    def _calculate_mdt_web_ip(self, dhcp_server_ip: str) -> Optional[str]:
        """計算 MDT Web IP（前三段相同，最後一段為 .2）"""
        try:
            if not dhcp_server_ip or not self._is_valid_ip(dhcp_server_ip):
                return None
            
            octets = dhcp_server_ip.split('.')
            return f"{octets[0]}.{octets[1]}.{octets[2]}.2"
            
        except Exception as e:
            logger.error(f"Failed to calculate MDT Web IP: {e}", exc_info=True)
            return None
    
    def _check_fatal_errors(self):
        """
        Fatal Errors 分析檢查
        
        分析 Build 的 Console Log 中是否包含 Sample Disk 相關的錯誤
        （如 NVMe Device Cannot be Found 等）
        """
        check_result = self.validation_results['checks']['fatal_errors']
        
        try:
            # 1. 檢查 Build 狀態
            if self.build.result == 'SUCCESS':
                check_result['status'] = 'success'
                check_result['message'] = 'Build 成功，無需檢查 Fatal Errors'
                check_result['value'] = 'N/A'
                logger.info("✓ Build SUCCESS, skipping Fatal Errors check")
                return
            
            # 2. 檢查 Console Log 是否存在
            if not self.build.log_file_path:
                check_result['status'] = 'warning'
                check_result['message'] = '尚無 Console Log，無法分析 Fatal Errors'
                check_result['value'] = 'N/A'
                check_result['suggestions'] = ['等待 Build 完成並下載 Console Log']
                logger.warning("⚠️ No console log path, cannot check Fatal Errors")
                return
            
            from pathlib import Path
            import json
            
            log_path = Path(self.build.log_file_path)
            analysis_path = log_path.parent / 'fatal_analysis.json'
            
            # 3. 檢查 Fatal Analysis 是否存在
            if not analysis_path.exists():
                check_result['status'] = 'warning'
                check_result['message'] = 'Fatal Analysis 尚未執行'
                check_result['value'] = 'N/A'
                check_result['details']['analysis_path'] = str(analysis_path)
                check_result['suggestions'] = ['等待系統自動分析或手動觸發分析']
                logger.warning(f"⚠️ Fatal analysis file not found: {analysis_path}")
                return
            
            # 4. 讀取 Fatal Analysis
            with open(analysis_path, 'r', encoding='utf-8') as f:
                analysis_data = json.load(f)
            
            fatal_count = analysis_data.get('summary', {}).get('total_fatal_count', 0)
            fatal_tasks = analysis_data.get('fatal_tasks', [])
            
            check_result['details']['fatal_count'] = fatal_count
            check_result['details']['fatal_tasks_count'] = len(fatal_tasks)
            check_result['details']['analyzed_at'] = analysis_data.get('build_info', {}).get('analyzed_at')
            
            if fatal_count == 0:
                check_result['status'] = 'success'
                check_result['message'] = 'Build 失敗但無 Fatal Errors 記錄'
                check_result['value'] = '0 個 Fatal'
                logger.info("✓ No Fatal Errors found in analysis")
                return
            
            # 5. 分析 Fatal 內容，識別 Sample Disk 問題
            sample_disk_issues = self._analyze_sample_disk_issues(fatal_tasks)
            
            check_result['value'] = f'{fatal_count} 個 Fatal'
            check_result['details']['sample_disk_issues'] = sample_disk_issues
            
            if sample_disk_issues:
                check_result['status'] = 'error'
                check_result['message'] = f'檢測到 Sample Disk 問題：{len(sample_disk_issues)} 個'
                check_result['suggestions'] = [
                    '檢查 NVMe 設備是否正確連接',
                    '確認 Sample Disk 已正確安裝',
                    '檢查設備電源和連接線',
                    '嘗試重新插拔 NVMe 設備',
                ]
                
                # 記錄具體問題（最多顯示 3 個）
                for issue in sample_disk_issues[:3]:
                    check_result['suggestions'].append(
                        f"  • {issue['pattern']}: Task [{issue['task_name']}]"
                    )
                
                logger.error(f"❌ Sample Disk issues detected: {len(sample_disk_issues)}")
            else:
                check_result['status'] = 'warning'
                check_result['message'] = f'有 {fatal_count} 個 Fatal Errors，但非 Sample Disk 問題'
                check_result['suggestions'] = [
                    '請查看 Fatal Errors 詳情頁面了解具體錯誤',
                    '點擊「查看 Fatal Errors」按鈕查看完整分析'
                ]
                logger.warning(f"⚠️ {fatal_count} Fatal Errors found, but no Sample Disk issues")
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Fatal Analysis JSON: {e}", exc_info=True)
            check_result['status'] = 'error'
            check_result['message'] = 'Fatal Analysis 檔案格式錯誤'
            check_result['suggestions'] = ['請重新執行 Fatal Error 分析']
            
        except Exception as e:
            logger.error(f"Failed to check Fatal Errors: {e}", exc_info=True)
            check_result['status'] = 'error'
            check_result['message'] = f'分析 Fatal Errors 時發生錯誤: {str(e)}'
            check_result['suggestions'] = ['檢查系統日誌']
    
    def _analyze_sample_disk_issues(self, fatal_tasks: List[Dict]) -> List[Dict]:
        """
        分析 Fatal Tasks 中是否包含 Sample Disk 相關問題
        
        Args:
            fatal_tasks: Fatal Tasks 列表
        
        Returns:
            List of detected issues: [{'pattern': str, 'task_name': str, 'matched_text': str}]
        """
        # Sample Disk 問題關鍵詞模式（模式, 描述）
        SAMPLE_DISK_PATTERNS = [
            # NVMe 相關
            (r'NVMe\s+Device\s+Cannot\s+be\s+Found', 'NVMe 設備未找到'),
            (r'The\s+NVMe\s+Device\s+Cannot\s+be\s+Found', 'NVMe 設備未找到'),
            (r'NVMe.*not\s+found', 'NVMe 未找到'),
            (r'NVMe.*missing', 'NVMe 缺失'),
            (r'No\s+NVMe\s+device', '無 NVMe 設備'),
            
            # 磁碟/儲存相關
            (r'sample.*disk.*not\s+found', 'Sample Disk 未找到'),
            (r'disk.*cannot.*found', '磁碟無法找到'),
            (r'InitializeDefaultDrives.*failed', '初始化預設磁碟機失敗'),
            (r'FileSystem.*provider\s+failed', '檔案系統提供者失敗'),
            (r'storage.*device.*not.*detected', '儲存設備未檢測到'),
            (r'drive.*not.*available', '磁碟機不可用'),
            
            # 測試樣品相關
            (r'sample.*not.*detected', '測試樣品未檢測到'),
            (r'DUT.*not.*found', 'DUT 未找到'),
            (r'target.*device.*missing', '目標設備缺失'),
        ]
        
        detected_issues = []
        
        for task in fatal_tasks:
            # 收集所有可能包含錯誤信息的內容
            content_parts = []
            
            # 檢查 task_content / content
            task_content = task.get('content', '') or task.get('task_content', '')
            if task_content:
                content_parts.append(task_content)
            
            # 檢查 fatal_occurrences 中的 line_content
            occurrences = task.get('fatal_occurrences', [])
            for occ in occurrences:
                line_content = occ.get('line_content', '')
                if line_content:
                    content_parts.append(line_content)
                
                # 也檢查 context_lines
                context_lines = occ.get('context_lines', [])
                for ctx_line in context_lines:
                    if ctx_line:
                        content_parts.append(ctx_line)
            
            # 檢查 fatal_snippets
            snippets = task.get('fatal_snippets', [])
            for snippet in snippets:
                if isinstance(snippet, str) and snippet:
                    content_parts.append(snippet)
            
            # 合併所有內容
            full_content = '\n'.join(content_parts)
            
            # 匹配關鍵詞
            for pattern, description in SAMPLE_DISK_PATTERNS:
                matches = list(re.finditer(pattern, full_content, re.IGNORECASE))
                for match in matches:
                    detected_issues.append({
                        'pattern': description,
                        'matched_text': match.group(),
                        'task_name': task.get('task_name', 'Unknown Task'),
                        'line_number': task.get('start_line', 0) or task.get('task_start_line', 0),
                    })
        
        # 去重（基於 pattern + task_name）
        seen = set()
        unique_issues = []
        for issue in detected_issues:
            key = (issue['pattern'], issue['task_name'])
            if key not in seen:
                seen.add(key)
                unique_issues.append(issue)
        
        logger.info(f"Sample Disk issue analysis: {len(unique_issues)} unique issues found")
        return unique_issues


def validate_build_config(build_id: int, dhcp_server_ids: Optional[List[int]] = None) -> Dict:
    """
    Convenience function to validate build config
    
    Args:
        build_id: Jenkins Build ID
        dhcp_server_ids: DHCP server IDs list (optional)
        
    Returns:
        Validation result dict
    """
    validator = BuildConfigValidator(build_id, dhcp_server_ids)
    return validator.validate()
