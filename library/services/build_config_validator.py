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
                }
            },
            'summary': {
                'total_checks': 4,
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
