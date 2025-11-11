"""
Ansible Inventory 解析服務

提供 Ansible Inventory 文件的解析功能，支持快取機制以提升性能。
"""

import os
import json
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
import subprocess

logger = logging.getLogger(__name__)


class AnsibleInventoryService:
    """
    Ansible Inventory 解析服務（帶快取支持）
    
    功能：
    1. 解析 Ansible Inventory 文件（使用 ansible-inventory 命令）
    2. 快取解析結果到 NAS 文件系統
    3. 智能快取有效性檢查（版本、過期時間、文件修改時間）
    4. 快取管理（清除、統計）
    
    快取策略：
    - 保留時間：7 天
    - 存儲位置：{build_dir}/cache/
    - 有效性判斷：版本 + 過期時間 + inventory 文件 mtime
    """
    
    CACHE_EXPIRY_DAYS = 7  # 快取保留 7 天
    CACHE_VERSION = "1.0"
    
    def __init__(self, inventory_path: str):
        """
        初始化服務
        
        Args:
            inventory_path: inventory/hosts 文件的絕對路徑
                           例如: /mnt/mdt/.../10.252.170.171/Test-KVM01/148/artifacts/inventory/hosts
        
        Raises:
            FileNotFoundError: 如果 inventory 文件不存在
        """
        self.inventory_path = Path(inventory_path)
        
        if not self.inventory_path.exists():
            raise FileNotFoundError(f"Inventory 文件不存在: {inventory_path}")
        
        # 計算快取目錄路徑
        # 從 /path/to/148/artifacts/inventory/hosts → /path/to/148/cache/
        self.build_dir = self.inventory_path.parent.parent.parent  # 回到 148/ 目錄
        self.cache_dir = self.build_dir / 'cache'
        
        logger.info(f"初始化 AnsibleInventoryService")
        logger.info(f"  Inventory: {self.inventory_path}")
        logger.info(f"  Cache Dir: {self.cache_dir}")
    
    # ==================== 快取管理 ====================
    
    def _ensure_cache_dir(self):
        """確保快取目錄存在"""
        try:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logger.error(f"創建快取目錄失敗: {e}", exc_info=True)
    
    def _get_cache_metadata_path(self) -> Path:
        """獲取快取元數據文件路徑"""
        return self.cache_dir / 'cache_metadata.json'
    
    def _get_cache_file_path(self, cache_type: str, hostname: str = None) -> Path:
        """
        獲取快取文件路徑
        
        Args:
            cache_type: 'full_inventory' | 'hosts_list' | 'host_config'
            hostname: 當 cache_type='host_config' 時指定主機名
        
        Returns:
            Path: 快取文件路徑
        """
        if cache_type == 'full_inventory':
            return self.cache_dir / 'ansible_inventory.json'
        elif cache_type == 'hosts_list':
            return self.cache_dir / 'ansible_hosts_list.json'
        elif cache_type == 'host_config':
            if not hostname:
                raise ValueError("hostname is required for host_config cache")
            return self.cache_dir / f'ansible_host_{hostname}.json'
        else:
            raise ValueError(f"Unknown cache_type: {cache_type}")
    
    def _load_cache_metadata(self) -> Optional[Dict[str, Any]]:
        """
        載入快取元數據
        
        Returns:
            dict: 元數據內容，如果不存在或載入失敗返回 None
        """
        metadata_path = self._get_cache_metadata_path()
        
        if not metadata_path.exists():
            return None
        
        try:
            with open(metadata_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"載入快取元數據失敗: {e}")
            return None
    
    def _save_cache_metadata(self, metadata: Dict[str, Any]):
        """
        保存快取元數據
        
        Args:
            metadata: 元數據內容
        """
        self._ensure_cache_dir()
        metadata_path = self._get_cache_metadata_path()
        
        try:
            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)
            logger.info(f"快取元數據已保存: {metadata_path}")
        except Exception as e:
            logger.error(f"保存快取元數據失敗: {e}", exc_info=True)
    
    def _is_cache_valid(self, metadata: Dict[str, Any]) -> bool:
        """
        判斷快取是否有效
        
        有效條件：
        1. 快取版本匹配
        2. 快取未過期
        3. inventory 文件未被修改
        
        Args:
            metadata: 快取元數據
        
        Returns:
            bool: 快取是否有效
        """
        # 1. 檢查版本
        if metadata.get('cache_version') != self.CACHE_VERSION:
            logger.info("快取版本不匹配，快取失效")
            return False
        
        # 2. 檢查是否過期
        try:
            expires_at = datetime.fromisoformat(metadata['cache_expires_at'])
            if datetime.now() > expires_at:
                logger.info("快取已過期")
                return False
        except (KeyError, ValueError) as e:
            logger.warning(f"解析過期時間失敗: {e}")
            return False
        
        # 3. 檢查原始文件是否被修改
        try:
            current_mtime = self.inventory_path.stat().st_mtime
            cached_mtime_str = metadata.get('inventory_file_mtime')
            
            if not cached_mtime_str:
                return False
            
            cached_mtime = datetime.fromisoformat(cached_mtime_str).timestamp()
            
            if current_mtime > cached_mtime:
                logger.info("Inventory 文件已被修改，快取失效")
                return False
        except Exception as e:
            logger.warning(f"檢查文件修改時間失敗: {e}")
            return False
        
        return True
    
    def _load_from_cache(self, cache_type: str, hostname: str = None) -> Optional[Dict[str, Any]]:
        """
        從快取載入數據
        
        Args:
            cache_type: 快取類型
            hostname: 主機名（可選）
        
        Returns:
            dict: 快取數據，如果快取無效返回 None
        """
        # 1. 載入元數據
        metadata = self._load_cache_metadata()
        if not metadata:
            logger.debug("快取元數據不存在")
            return None
        
        # 2. 檢查快取是否有效
        if not self._is_cache_valid(metadata):
            logger.debug("快取已失效")
            return None
        
        # 3. 檢查該類型的快取是否存在
        cache_file = self._get_cache_file_path(cache_type, hostname)
        if not cache_file.exists():
            logger.debug(f"快取文件不存在: {cache_file}")
            return None
        
        # 4. 載入快取數據
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            logger.info(f"✅ 從快取載入: {cache_file.name}")
            return data
        except Exception as e:
            logger.warning(f"載入快取文件失敗: {e}")
            return None
    
    def _save_to_cache(self, cache_type: str, data: Dict[str, Any], hostname: str = None):
        """
        保存數據到快取
        
        Args:
            cache_type: 快取類型
            data: 要保存的數據
            hostname: 主機名（可選）
        """
        self._ensure_cache_dir()
        
        # 1. 保存數據文件
        cache_file = self._get_cache_file_path(cache_type, hostname)
        try:
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            logger.info(f"✅ 快取已保存: {cache_file.name}")
        except Exception as e:
            logger.error(f"保存快取文件失敗: {e}", exc_info=True)
            return
        
        # 2. 更新元數據
        metadata = self._load_cache_metadata() or self._create_initial_metadata()
        
        # 更新快取項目記錄
        if cache_type == 'full_inventory':
            metadata['cached_items']['full_inventory'] = True
        elif cache_type == 'hosts_list':
            metadata['cached_items']['hosts_list'] = True
        elif cache_type == 'host_config':
            if 'individual_hosts' not in metadata['cached_items']:
                metadata['cached_items']['individual_hosts'] = []
            if hostname not in metadata['cached_items']['individual_hosts']:
                metadata['cached_items']['individual_hosts'].append(hostname)
        
        self._save_cache_metadata(metadata)
    
    def _create_initial_metadata(self) -> Dict[str, Any]:
        """
        創建初始快取元數據
        
        Returns:
            dict: 初始元數據
        """
        now = datetime.now()
        expires_at = now + timedelta(days=self.CACHE_EXPIRY_DAYS)
        
        return {
            'inventory_path': str(self.inventory_path),
            'inventory_file_mtime': datetime.fromtimestamp(
                self.inventory_path.stat().st_mtime
            ).isoformat(),
            'cache_created_at': now.isoformat(),
            'cache_expires_at': expires_at.isoformat(),
            'cache_version': self.CACHE_VERSION,
            'cached_items': {
                'full_inventory': False,
                'hosts_list': False,
                'individual_hosts': []
            }
        }
    
    # ==================== 主要功能（帶快取） ====================
    
    def get_full_inventory(self, use_cache: bool = True) -> Dict[str, Any]:
        """
        獲取完整的 Inventory 數據（支持快取）
        
        執行 ansible-inventory --list 命令獲取完整的 inventory 信息。
        
        Args:
            use_cache: 是否使用快取（默認 True）
        
        Returns:
            dict: {
                "success": bool,
                "cached": bool,  # 是否來自快取
                "data": {...},   # ansible-inventory --list 的輸出
                "message": str
            }
        """
        # 1. 嘗試從快取載入
        if use_cache:
            cached_data = self._load_from_cache('full_inventory')
            if cached_data:
                return {
                    'success': True,
                    'cached': True,
                    'data': cached_data,
                    'message': '從快取載入'
                }
        
        # 2. 執行 ansible-inventory 命令
        logger.info("執行 ansible-inventory --list")
        cmd = [
            'ansible-inventory',
            '-i', str(self.inventory_path),
            '--list'
        ]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                return {
                    'success': False,
                    'cached': False,
                    'error': result.stderr,
                    'message': 'ansible-inventory 執行失敗'
                }
            
            # 3. 解析 JSON 輸出
            inventory_data = json.loads(result.stdout)
            
            # 4. 保存到快取
            self._save_to_cache('full_inventory', inventory_data)
            
            return {
                'success': True,
                'cached': False,
                'data': inventory_data,
                'message': '從 Ansible 解析'
            }
            
        except subprocess.TimeoutExpired:
            return {
                'success': False,
                'cached': False,
                'error': '命令執行超時',
                'message': 'ansible-inventory 執行超時'
            }
        except json.JSONDecodeError as e:
            return {
                'success': False,
                'cached': False,
                'error': f'JSON 解析失敗: {str(e)}',
                'message': 'Ansible 輸出格式錯誤'
            }
        except Exception as e:
            logger.error(f"執行 ansible-inventory 失敗: {e}", exc_info=True)
            return {
                'success': False,
                'cached': False,
                'error': str(e),
                'message': '未知錯誤'
            }
    
    def get_host_config(self, hostname: str, use_cache: bool = True) -> Dict[str, Any]:
        """
        獲取特定主機的完整配置（支持快取）
        
        執行 ansible-inventory --host <hostname> 命令獲取主機的所有變量
        （包括從群組繼承的變量）。
        
        Args:
            hostname: 主機名
            use_cache: 是否使用快取
        
        Returns:
            dict: {
                "success": bool,
                "cached": bool,
                "hostname": str,
                "config": {...},  # 主機的所有變量
                "message": str
            }
        """
        # 1. 嘗試從快取載入
        if use_cache:
            cached_data = self._load_from_cache('host_config', hostname)
            if cached_data:
                return {
                    'success': True,
                    'cached': True,
                    'hostname': hostname,
                    'config': cached_data,
                    'message': '從快取載入'
                }
        
        # 2. 執行 ansible-inventory --host 命令
        logger.info(f"執行 ansible-inventory --host {hostname}")
        cmd = [
            'ansible-inventory',
            '-i', str(self.inventory_path),
            '--host', hostname
        ]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                return {
                    'success': False,
                    'cached': False,
                    'hostname': hostname,
                    'error': result.stderr,
                    'message': f'找不到主機: {hostname}'
                }
            
            # 3. 解析 JSON 輸出
            host_config = json.loads(result.stdout)
            
            # 4. 保存到快取
            self._save_to_cache('host_config', host_config, hostname)
            
            return {
                'success': True,
                'cached': False,
                'hostname': hostname,
                'config': host_config,
                'message': '從 Ansible 解析'
            }
            
        except subprocess.TimeoutExpired:
            return {
                'success': False,
                'cached': False,
                'hostname': hostname,
                'error': '命令執行超時',
                'message': 'ansible-inventory 執行超時'
            }
        except json.JSONDecodeError as e:
            return {
                'success': False,
                'cached': False,
                'hostname': hostname,
                'error': f'JSON 解析失敗: {str(e)}',
                'message': 'Ansible 輸出格式錯誤'
            }
        except Exception as e:
            logger.error(f"執行 ansible-inventory 失敗: {e}", exc_info=True)
            return {
                'success': False,
                'cached': False,
                'hostname': hostname,
                'error': str(e),
                'message': '未知錯誤'
            }
    
    def list_all_hosts(self, use_cache: bool = True) -> Dict[str, Any]:
        """
        獲取所有主機列表（支持快取，自訂格式）
        
        提取主機摘要信息，包括主機名、IP、設備號、所屬群組等。
        
        Args:
            use_cache: 是否使用快取
        
        Returns:
            dict: {
                "success": bool,
                "cached": bool,
                "total_hosts": int,
                "hosts": [
                    {
                        "hostname": str,
                        "ansible_host": str,
                        "device_number": str,
                        "groups": [str, ...]
                    },
                    ...
                ]
            }
        """
        # 1. 嘗試從快取載入
        if use_cache:
            cached_data = self._load_from_cache('hosts_list')
            if cached_data:
                return {
                    'success': True,
                    'cached': True,
                    **cached_data
                }
        
        # 2. 獲取完整 inventory（會使用快取）
        full_result = self.get_full_inventory(use_cache=use_cache)
        if not full_result['success']:
            return {
                'success': False,
                'cached': False,
                'error': full_result.get('error', 'Unknown error'),
                'message': '無法獲取 inventory'
            }
        
        inventory_data = full_result['data']
        
        # 3. 提取主機列表
        hosts_list = []
        hostvars = inventory_data.get('_meta', {}).get('hostvars', {})
        
        for hostname, vars_dict in hostvars.items():
            # 獲取主機所屬的群組
            groups = []
            for group_name, group_data in inventory_data.items():
                if group_name == '_meta':
                    continue
                if 'hosts' in group_data and hostname in group_data['hosts']:
                    groups.append(group_name)
            
            hosts_list.append({
                'hostname': hostname,
                'ansible_host': vars_dict.get('ansible_host', 'N/A'),
                'device_number': vars_dict.get('device_number', 'N/A'),
                'groups': groups
            })
        
        # 4. 構建結果
        result_data = {
            'total_hosts': len(hosts_list),
            'hosts': hosts_list
        }
        
        # 5. 保存到快取
        self._save_to_cache('hosts_list', result_data)
        
        return {
            'success': True,
            'cached': False,
            **result_data
        }
    
    # ==================== 快取管理功能 ====================
    
    def clear_cache(self, cache_type: str = 'all', hostname: str = None) -> Dict[str, Any]:
        """
        清除快取
        
        Args:
            cache_type: 'all' | 'full_inventory' | 'hosts_list' | 'host_config'
            hostname: 當 cache_type='host_config' 時指定主機名
        
        Returns:
            dict: {"success": bool, "message": str, "cleared": [str, ...]}
        """
        cleared_files = []
        
        try:
            if cache_type == 'all':
                # 刪除整個快取目錄
                if self.cache_dir.exists():
                    import shutil
                    shutil.rmtree(self.cache_dir)
                    cleared_files.append('all cache files')
                    logger.info(f"✅ 已清除所有快取: {self.cache_dir}")
            else:
                # 刪除特定快取文件
                cache_file = self._get_cache_file_path(cache_type, hostname)
                if cache_file.exists():
                    cache_file.unlink()
                    cleared_files.append(cache_file.name)
                    logger.info(f"✅ 已清除快取: {cache_file.name}")
                
                # 更新元數據
                metadata = self._load_cache_metadata()
                if metadata:
                    if cache_type == 'full_inventory':
                        metadata['cached_items']['full_inventory'] = False
                    elif cache_type == 'hosts_list':
                        metadata['cached_items']['hosts_list'] = False
                    elif cache_type == 'host_config' and hostname:
                        if hostname in metadata['cached_items'].get('individual_hosts', []):
                            metadata['cached_items']['individual_hosts'].remove(hostname)
                    
                    self._save_cache_metadata(metadata)
            
            return {
                'success': True,
                'message': '快取已清除',
                'cleared': cleared_files
            }
            
        except Exception as e:
            logger.error(f"清除快取失敗: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
                'message': '清除快取失敗'
            }
    
    def get_cache_statistics(self) -> Dict[str, Any]:
        """
        獲取快取統計信息
        
        Returns:
            dict: {
                "cache_exists": bool,
                "cache_valid": bool,
                "cache_size_mb": float,
                "cache_created_at": str,
                "cache_expires_at": str,
                "cached_items": {...}
            }
        """
        metadata = self._load_cache_metadata()
        
        if not metadata:
            return {
                'cache_exists': False,
                'cache_valid': False,
                'cache_size_mb': 0,
                'message': '快取不存在'
            }
        
        # 計算快取大小
        cache_size = 0
        if self.cache_dir.exists():
            for file in self.cache_dir.iterdir():
                if file.is_file():
                    cache_size += file.stat().st_size
        
        return {
            'cache_exists': True,
            'cache_valid': self._is_cache_valid(metadata),
            'cache_size_mb': round(cache_size / 1024 / 1024, 2),
            'cache_created_at': metadata.get('cache_created_at'),
            'cache_expires_at': metadata.get('cache_expires_at'),
            'cached_items': metadata.get('cached_items', {})
        }
