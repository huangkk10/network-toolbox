# Ansible Inventory 快取機制規劃

## 📋 需求確認

### 使用者需求
- ✅ **同意安裝 Ansible**：使用方案 A（Ansible 官方工具）
- ✅ **測試數據**：使用 Test-KVM01 Build #148 真實數據
- ❓ **快取策略**：將解析結果存到 NAS，避免重複解析

---

## 🎯 快取策略分析

### 為什麼需要快取？

#### 當前問題
```
每次 API 請求 → ansible-inventory 解析 → 耗時 1-3 秒
├─ 讀取 inventory/hosts 文件
├─ 解析 INI 格式
├─ 計算變量繼承
└─ 生成 JSON 輸出
```

#### 快取優勢
```
首次請求 → 解析 → 存快取 (3 秒)
後續請求 → 讀快取 → 返回 (0.1 秒)
效能提升：30x
```

---

## 📦 快取架構設計

### 方案評估

#### 方案 A：存入資料庫（不推薦）
```python
# PostgreSQL JSONB 欄位
class AnsibleInventoryCache(models.Model):
    job_id = models.ForeignKey(JenkinsJob)
    build_number = models.IntegerField()
    inventory_data = models.JSONField()  # 大 JSON 對象
    created_at = models.DateTimeField(auto_now_add=True)
```

❌ **缺點**：
- Inventory JSON 可能很大（幾百 KB）
- 增加資料庫負擔
- 查詢速度不如文件系統
- 難以手動檢查和調試

---

#### 方案 B：存入 Redis（部分推薦）
```python
import redis
cache = redis.Redis()

# 存入
cache.setex(
    f'ansible_inventory:{job_id}:{build_number}',
    3600,  # 1 小時過期
    json.dumps(inventory_data)
)

# 讀取
data = cache.get(f'ansible_inventory:{job_id}:{build_number}')
```

✅ **優點**：
- 快速（內存存取）
- 自動過期（TTL）
- 支持分佈式

⚠️ **缺點**：
- 需要額外的 Redis 服務（當前專案未使用）
- 重啟後數據丟失
- 無法持久化到 NAS

---

#### 方案 C：存入 NAS 文件系統（✅ 推薦）
```bash
# NAS 存儲結構
/mnt/mdt/Team/PQ1-3/tool/jenkins_test_storage/
├── 10.252.170.171/
│   └── Test-KVM01/
│       └── 148/
│           ├── artifacts/
│           │   ├── inventory/
│           │   │   └── hosts                    # 原始文件
│           │   └── ...
│           └── cache/                           # 🆕 快取目錄
│               ├── ansible_inventory.json       # 完整 inventory
│               ├── ansible_hosts_list.json      # 主機列表
│               ├── ansible_host_Test-KVM01.json # 單主機配置
│               └── cache_metadata.json          # 快取元數據
```

✅ **優點**：
- **持久化存儲**：不會因重啟丟失
- **與 artifacts 一起管理**：同一位置，便於備份
- **手動可檢查**：可直接查看 JSON 文件
- **無需額外服務**：使用現有 NAS
- **支持部分快取**：可以只快取常用查詢（如 hosts list）
- **自動清理**：artifacts 自動刪除時，快取也一併刪除

⚠️ **注意事項**：
- 需要處理文件讀寫競爭
- NAS I/O 速度比 Redis 慢（但比重新解析快很多）

---

## 🏗️ 快取實施方案（方案 C）

### 1. 快取目錄結構

```bash
{server_ip}/{job_name}/{build_number}/cache/
├── ansible_inventory.json       # 完整 inventory（來自 --list）
├── ansible_hosts_list.json      # 主機列表摘要（自訂格式）
├── ansible_host_{hostname}.json # 各主機的完整配置（來自 --host）
└── cache_metadata.json          # 快取元數據
```

### 2. 快取元數據格式

```json
{
    "job_id": 269,
    "job_name": "Test-KVM01",
    "build_number": 148,
    "inventory_path": "/mnt/mdt/.../inventory/hosts",
    "inventory_file_mtime": "2025-11-09T15:30:00+08:00",
    "cache_created_at": "2025-11-10T10:00:00+08:00",
    "cache_expires_at": "2025-11-17T10:00:00+08:00",
    "cache_version": "1.0",
    "cached_items": {
        "full_inventory": true,
        "hosts_list": true,
        "individual_hosts": ["Test-KVM01", "Test-KVM03", ...]
    }
}
```

### 3. 快取有效性判斷

```python
def is_cache_valid(cache_metadata: dict, inventory_path: Path) -> bool:
    """
    判斷快取是否有效
    
    有效條件：
    1. cache_metadata.json 存在
    2. 快取未過期（7 天）
    3. inventory/hosts 文件未被修改
    """
    # 1. 檢查是否過期
    expires_at = datetime.fromisoformat(cache_metadata['cache_expires_at'])
    if datetime.now() > expires_at:
        return False
    
    # 2. 檢查原始文件是否被修改
    current_mtime = inventory_path.stat().st_mtime
    cached_mtime = datetime.fromisoformat(
        cache_metadata['inventory_file_mtime']
    ).timestamp()
    
    if current_mtime > cached_mtime:
        # 文件被修改，快取失效
        return False
    
    return True
```

---

## 🔧 服務類別修改

### 修改 AnsibleInventoryService

```python
# library/services/ansible_inventory_service.py

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
    """
    
    CACHE_EXPIRY_DAYS = 7  # 快取保留 7 天
    CACHE_VERSION = "1.0"
    
    def __init__(self, inventory_path: str):
        """
        初始化服務
        
        Args:
            inventory_path: inventory/hosts 文件的絕對路徑
                           例如: /mnt/mdt/.../10.252.170.171/Test-KVM01/148/artifacts/inventory/hosts
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
        self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_cache_metadata_path(self) -> Path:
        """獲取快取元數據文件路徑"""
        return self.cache_dir / 'cache_metadata.json'
    
    def _get_cache_file_path(self, cache_type: str, hostname: str = None) -> Path:
        """
        獲取快取文件路徑
        
        Args:
            cache_type: 'full_inventory' | 'hosts_list' | 'host_config'
            hostname: 當 cache_type='host_config' 時指定主機名
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
        """載入快取元數據"""
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
        """保存快取元數據"""
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
        """創建初始快取元數據"""
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
```

---

## 🔌 API 端點修改

### 擴展 JenkinsJobViewSet

```python
# backend/api/views/jenkins.py

from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from library.services.ansible_inventory_service import AnsibleInventoryService

class JenkinsJobViewSet(viewsets.ModelViewSet):
    # ... 現有代碼 ...
    
    @action(detail=True, methods=['get'], url_path='ansible-inventory')
    def ansible_inventory(self, request, pk=None):
        """
        獲取完整 Inventory
        
        Query Parameters:
            - use_cache: 是否使用快取（默認 true）
            - force_refresh: 強制刷新（清除快取後重新解析）
        """
        job = self.get_object()
        use_cache = request.query_params.get('use_cache', 'true').lower() == 'true'
        force_refresh = request.query_params.get('force_refresh', 'false').lower() == 'true'
        
        # 獲取 inventory 文件路徑
        inventory_path = self._get_latest_build_inventory_path(job)
        if not inventory_path:
            return Response({
                'success': False,
                'error': '找不到 inventory 文件'
            }, status=status.HTTP_404_NOT_FOUND)
        
        try:
            service = AnsibleInventoryService(inventory_path)
            
            # 強制刷新：先清除快取
            if force_refresh:
                service.clear_cache('all')
                use_cache = False
            
            # 獲取數據
            result = service.get_full_inventory(use_cache=use_cache)
            
            if result['success']:
                return Response({
                    'success': True,
                    'job_id': job.id,
                    'job_name': job.name,
                    'cached': result['cached'],
                    'data': result['data']
                })
            else:
                return Response(result, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                
        except Exception as e:
            logger.error(f"獲取 Ansible Inventory 失敗: {e}", exc_info=True)
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['get'], url_path='ansible-inventory/hosts')
    def ansible_inventory_hosts(self, request, pk=None):
        """
        獲取主機列表
        
        Query Parameters:
            - use_cache: 是否使用快取（默認 true）
        """
        job = self.get_object()
        use_cache = request.query_params.get('use_cache', 'true').lower() == 'true'
        
        inventory_path = self._get_latest_build_inventory_path(job)
        if not inventory_path:
            return Response({
                'success': False,
                'error': '找不到 inventory 文件'
            }, status=status.HTTP_404_NOT_FOUND)
        
        try:
            service = AnsibleInventoryService(inventory_path)
            result = service.list_all_hosts(use_cache=use_cache)
            
            if result['success']:
                return Response({
                    'success': True,
                    'job_id': job.id,
                    'job_name': job.name,
                    'cached': result['cached'],
                    'total_hosts': result['total_hosts'],
                    'hosts': result['hosts']
                })
            else:
                return Response(result, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                
        except Exception as e:
            logger.error(f"獲取主機列表失敗: {e}", exc_info=True)
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['get'], url_path='ansible-inventory/hosts/(?P<hostname>[^/.]+)')
    def ansible_inventory_host_config(self, request, pk=None, hostname=None):
        """
        獲取特定主機配置
        
        Query Parameters:
            - use_cache: 是否使用快取（默認 true）
        """
        job = self.get_object()
        use_cache = request.query_params.get('use_cache', 'true').lower() == 'true'
        
        inventory_path = self._get_latest_build_inventory_path(job)
        if not inventory_path:
            return Response({
                'success': False,
                'error': '找不到 inventory 文件'
            }, status=status.HTTP_404_NOT_FOUND)
        
        try:
            service = AnsibleInventoryService(inventory_path)
            result = service.get_host_config(hostname, use_cache=use_cache)
            
            if result['success']:
                return Response({
                    'success': True,
                    'job_id': job.id,
                    'job_name': job.name,
                    'cached': result['cached'],
                    'hostname': hostname,
                    'config': result['config']
                })
            else:
                return Response(result, status=status.HTTP_404_NOT_FOUND)
                
        except Exception as e:
            logger.error(f"獲取主機配置失敗: {e}", exc_info=True)
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['delete'], url_path='ansible-inventory/cache')
    def clear_ansible_cache(self, request, pk=None):
        """
        清除快取
        
        Query Parameters:
            - cache_type: 'all' | 'full_inventory' | 'hosts_list' | 'host_config'
            - hostname: 當 cache_type='host_config' 時指定主機名
        """
        job = self.get_object()
        cache_type = request.query_params.get('cache_type', 'all')
        hostname = request.query_params.get('hostname')
        
        inventory_path = self._get_latest_build_inventory_path(job)
        if not inventory_path:
            return Response({
                'success': False,
                'error': '找不到 inventory 文件'
            }, status=status.HTTP_404_NOT_FOUND)
        
        try:
            service = AnsibleInventoryService(inventory_path)
            result = service.clear_cache(cache_type, hostname)
            return Response(result)
            
        except Exception as e:
            logger.error(f"清除快取失敗: {e}", exc_info=True)
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['get'], url_path='ansible-inventory/cache/statistics')
    def ansible_cache_statistics(self, request, pk=None):
        """
        獲取快取統計信息
        """
        job = self.get_object()
        
        inventory_path = self._get_latest_build_inventory_path(job)
        if not inventory_path:
            return Response({
                'success': False,
                'error': '找不到 inventory 文件'
            }, status=status.HTTP_404_NOT_FOUND)
        
        try:
            service = AnsibleInventoryService(inventory_path)
            stats = service.get_cache_statistics()
            
            return Response({
                'success': True,
                'job_id': job.id,
                'job_name': job.name,
                **stats
            })
            
        except Exception as e:
            logger.error(f"獲取快取統計失敗: {e}", exc_info=True)
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
```

---

## 🔄 Celery 自動清理任務

### 定期清理過期快取

```python
# backend/api/tasks.py

from celery import shared_task
from pathlib import Path
from datetime import datetime, timedelta
import logging
import json
import shutil

logger = logging.getLogger(__name__)


@shared_task(name='清理過期的 Ansible Inventory 快取')
def clean_expired_ansible_caches():
    """
    清理過期的 Ansible Inventory 快取
    
    每天執行一次，清理 7 天前的快取
    """
    from django.conf import settings
    
    base_path = Path(settings.JENKINS_STORAGE_BASE_PATH)
    now = datetime.now()
    cleaned_count = 0
    total_size_mb = 0
    
    logger.info("開始清理過期的 Ansible Inventory 快取")
    
    try:
        # 遍歷所有 cache 目錄
        for cache_dir in base_path.rglob('cache'):
            if not cache_dir.is_dir():
                continue
            
            # 讀取快取元數據
            metadata_file = cache_dir / 'cache_metadata.json'
            if not metadata_file.exists():
                continue
            
            try:
                with open(metadata_file, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
                
                # 檢查是否過期
                expires_at = datetime.fromisoformat(metadata.get('cache_expires_at', ''))
                
                if now > expires_at:
                    # 計算快取大小
                    cache_size = sum(
                        f.stat().st_size for f in cache_dir.iterdir() if f.is_file()
                    )
                    cache_size_mb = cache_size / 1024 / 1024
                    
                    # 刪除快取目錄
                    shutil.rmtree(cache_dir)
                    cleaned_count += 1
                    total_size_mb += cache_size_mb
                    
                    logger.info(f"✅ 已清理過期快取: {cache_dir} ({cache_size_mb:.2f} MB)")
                    
            except Exception as e:
                logger.warning(f"處理快取目錄失敗 {cache_dir}: {e}")
                continue
        
        logger.info(f"✅ 快取清理完成：清理 {cleaned_count} 個目錄，釋放 {total_size_mb:.2f} MB")
        
        return {
            'success': True,
            'cleaned_count': cleaned_count,
            'total_size_mb': round(total_size_mb, 2)
        }
        
    except Exception as e:
        logger.error(f"清理快取失敗: {e}", exc_info=True)
        return {
            'success': False,
            'error': str(e)
        }
```

### Celery Beat 配置

```python
# backend/network_toolbox/celery.py

app.conf.beat_schedule = {
    # ... 現有任務 ...
    
    'clean-expired-ansible-caches': {
        'task': '清理過期的 Ansible Inventory 快取',
        'schedule': crontab(hour=3, minute=0),  # 每天凌晨 3 點執行
        'options': {
            'expires': 3600,
        }
    },
}
```

---

## 📊 快取效能分析

### 預期效能提升

```
┌──────────────────────┬──────────────┬──────────────┬───────────┐
│ 操作                 │ 無快取       │ 有快取       │ 提升      │
├──────────────────────┼──────────────┼──────────────┼───────────┤
│ 獲取完整 Inventory   │ 2-3 秒       │ 0.1-0.2 秒   │ 15x       │
│ 獲取主機列表         │ 2-3 秒       │ 0.05-0.1 秒  │ 30x       │
│ 獲取單個主機配置     │ 1-2 秒       │ 0.05 秒      │ 20x       │
└──────────────────────┴──────────────┴──────────────┴───────────┘

快取命中率（預估）：
- 初次請求：0%（需要解析）
- 重複請求：95%（命中快取）
- 平均響應時間：從 2 秒降到 0.2 秒
```

### 快取大小預估

```
Test-KVM01 Build #148 範例：
├─ ansible_inventory.json       ～ 50 KB   （完整 inventory）
├─ ansible_hosts_list.json      ～ 5 KB    （主機列表）
├─ ansible_host_Test-KVM01.json ～ 2 KB    （單主機）
├─ ansible_host_Test-KVM03.json ～ 2 KB
├─ ... (15 個主機)              ～ 30 KB
└─ cache_metadata.json          ～ 1 KB
─────────────────────────────────────────
總計：約 86 KB

假設 100 個 Build，每個有快取：
100 x 86 KB = 8.6 MB（非常小）
```

---

## ✅ 實施階段

### Phase 1：核心快取功能（2 天）
- [x] 規劃快取架構
- [ ] 實施 AnsibleInventoryService 快取邏輯
- [ ] 添加快取有效性檢查
- [ ] 單元測試

### Phase 2：API 整合（1 天）
- [ ] 擴展 JenkinsJobViewSet
- [ ] 添加 use_cache 參數支持
- [ ] 添加快取管理端點
- [ ] API 測試

### Phase 3：自動清理（0.5 天）
- [ ] 實施 Celery 清理任務
- [ ] 配置 Celery Beat
- [ ] 測試自動清理

### Phase 4：部署和驗證（0.5 天）
- [ ] 安裝 Ansible
- [ ] 部署更新
- [ ] 使用 Test-KVM01 #148 測試
- [ ] 效能驗證

---

## 🎯 結論

### 快取方案評估結果

**✅ 推薦使用方案 C（NAS 文件系統快取）**

**原因**：
1. ✅ **持久化存儲**：與 artifacts 一起管理，不會因重啟丟失
2. ✅ **無需額外服務**：使用現有 NAS，無需部署 Redis
3. ✅ **便於調試**：可直接查看 JSON 文件
4. ✅ **自動清理**：與 artifacts 同步刪除
5. ✅ **效能顯著提升**：響應時間從 2 秒降到 0.2 秒（10x）
6. ✅ **空間占用小**：每個 Build 快取約 86 KB

**實施優先級**：
- 🔴 **HIGH**: AnsibleInventoryService 核心快取功能
- 🔴 **HIGH**: API 端點整合（支持 use_cache 參數）
- 🟡 **MEDIUM**: 快取管理端點（清除、統計）
- 🟢 **LOW**: Celery 自動清理（可後續添加）

**預期效果**：
- API 響應速度提升 **10-30 倍**
- 減少 Ansible 命令執行次數 **95%**
- NAS 存儲增加 < 10 MB（100 個 Build）

---

**最後更新**：2025-11-11  
**規劃者**：GitHub Copilot  
**版本**：v1.0.0  
**狀態**：✅ 規劃完成，待確認執行
