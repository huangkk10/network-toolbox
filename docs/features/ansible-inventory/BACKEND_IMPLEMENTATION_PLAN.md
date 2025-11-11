# Ansible Inventory 后端功能实现规划

## 📋 需求确认

### 核心功能
通过 **Job Name** 获取该 Job 最新 Build 的 Ansible Inventory 配置信息

### 使用方案
**方案 A**: 使用 Ansible 官方工具 (`ansible-inventory`)

### 输入输出
```
输入: Job Name (例如: "Test-KVM01")
输出: Ansible Inventory 配置信息 (JSON)
```

---

## 🎯 功能设计

### 1. API Endpoint 设计

```
GET /api/jenkins-jobs/<job_id>/ansible_inventory/
GET /api/jenkins-jobs/<job_id>/ansible_inventory/hosts/
GET /api/jenkins-jobs/<job_id>/ansible_inventory/hosts/<hostname>/
```

#### Endpoint 1: 获取完整 Inventory
```http
GET /api/jenkins-jobs/269/ansible_inventory/

Response:
{
    "success": true,
    "job_id": 269,
    "job_name": "Test-KVM01",
    "build_number": 148,
    "inventory_path": "/mnt/mdt/.../inventory/hosts",
    "inventory_exists": true,
    "total_hosts": 15,
    "total_groups": 12,
    "data": {
        "_meta": {
            "hostvars": {
                "Test-KVM01": {...},
                "Test-KVM03": {...},
                ...
            }
        },
        "all": {
            "children": ["ungrouped", "PQ1_3", ...]
        },
        "PQ1_3": {
            "hosts": ["Test-KVM03", "Test-KVM04", ...],
            "vars": {...}
        },
        ...
    }
}
```

#### Endpoint 2: 获取所有主机列表
```http
GET /api/jenkins-jobs/269/ansible_inventory/hosts/

Response:
{
    "success": true,
    "job_id": 269,
    "job_name": "Test-KVM01",
    "build_number": 148,
    "total_hosts": 15,
    "hosts": [
        {
            "hostname": "Test-KVM01",
            "ansible_host": "10.250.71.22",
            "device_number": "PC-SSD-4632",
            "groups": ["PQ1_3_K01", "compatibility_test", "all"]
        },
        {
            "hostname": "Test-KVM03",
            "ansible_host": "10.250.71.17",
            "device_number": "PC-SSD-4634",
            "groups": ["PQ1_3", "compatibility_test", "all"]
        },
        ...
    ]
}
```

#### Endpoint 3: 获取特定主机配置
```http
GET /api/jenkins-jobs/269/ansible_inventory/hosts/Test-KVM01/

Response:
{
    "success": true,
    "job_id": 269,
    "job_name": "Test-KVM01",
    "build_number": 148,
    "hostname": "Test-KVM01",
    "groups": ["PQ1_3_K01", "compatibility_test", "all"],
    "variables": {
        "ansible_host": "10.250.71.22",
        "device_number": "PC-SSD-4632",
        "sample_number": "SM2703AB-02003",
        "uart_id": "KVM01",
        "macaddress": "CC:28:AA:86:C3:7F",
        "testcase_set": "testcases_demo",
        "uart_host": "UART-HUB00",
        "ansible_user": "administrator",
        "ansible_password": "1.a",
        "firmware_sku_keyword": "STD_Pyrite",
        ...
    },
    "variable_sources": {
        "ansible_host": "host",
        "device_number": "host",
        "uart_host": "group:PQ1_3_K01",
        "firmware_sku_keyword": "group:compatibility_test",
        "saf_enabled": "group:all"
    }
}
```

---

## 🏗️ 架构设计

### 1. 文件结构

```
backend/
├── library/
│   └── services/
│       ├── ansible_inventory_service.py  # 新增：Ansible Inventory 服务
│       └── jenkins_client.py             # 现有
├── api/
│   ├── models.py                         # 现有（无需修改）
│   ├── serializers.py                    # 可能需要新增序列化器
│   └── views/
│       └── jenkins.py                    # 扩展 JenkinsJobViewSet
└── requirements.txt                       # 新增 ansible 依赖
```

### 2. 核心服务类设计

```python
# library/services/ansible_inventory_service.py

import subprocess
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)


class AnsibleInventoryService:
    """
    Ansible Inventory 服务
    
    使用 ansible-inventory 命令解析和查询 Ansible inventory 配置文件
    """
    
    def __init__(self, inventory_path: str):
        """
        初始化服务
        
        Args:
            inventory_path: inventory 文件的完整路径
        """
        self.inventory_path = Path(inventory_path)
        self._validate_inventory()
    
    def _validate_inventory(self):
        """验证 inventory 文件是否存在"""
        if not self.inventory_path.exists():
            raise FileNotFoundError(f"Inventory file not found: {self.inventory_path}")
    
    def _run_ansible_inventory(self, args: List[str], timeout: int = 30) -> Dict:
        """
        执行 ansible-inventory 命令
        
        Args:
            args: 命令参数列表
            timeout: 超时时间（秒）
        
        Returns:
            dict: 命令输出的 JSON 数据
        
        Raises:
            RuntimeError: 命令执行失败
        """
        cmd = ['ansible-inventory', '-i', str(self.inventory_path)] + args
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=self.inventory_path.parent  # 在 inventory 文件所在目录执行
            )
            
            if result.returncode != 0:
                logger.error(f"ansible-inventory failed: {result.stderr}")
                raise RuntimeError(f"ansible-inventory command failed: {result.stderr}")
            
            return json.loads(result.stdout)
            
        except subprocess.TimeoutExpired:
            logger.error(f"ansible-inventory timeout after {timeout}s")
            raise RuntimeError(f"Command timeout after {timeout}s")
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse ansible-inventory output: {e}")
            raise RuntimeError(f"Invalid JSON output: {e}")
        except FileNotFoundError:
            logger.error("ansible-inventory command not found")
            raise RuntimeError(
                "ansible-inventory command not found. "
                "Please install ansible: pip install ansible"
            )
    
    def get_full_inventory(self) -> Dict[str, Any]:
        """
        获取完整的 inventory 数据
        
        Returns:
            dict: 完整的 inventory 结构
            {
                '_meta': {'hostvars': {...}},
                'all': {...},
                'group1': {...},
                ...
            }
        """
        logger.info(f"Getting full inventory from {self.inventory_path}")
        return self._run_ansible_inventory(['--list'])
    
    def get_host_config(self, hostname: str) -> Dict[str, Any]:
        """
        获取特定主机的配置（包括所有继承的变量）
        
        Args:
            hostname: 主机名
        
        Returns:
            dict: 主机的所有变量
        """
        logger.info(f"Getting config for host: {hostname}")
        return self._run_ansible_inventory(['--host', hostname])
    
    def list_all_hosts(self) -> List[str]:
        """
        列出所有主机名
        
        Returns:
            list: 主机名列表
        """
        inventory = self.get_full_inventory()
        hostvars = inventory.get('_meta', {}).get('hostvars', {})
        return list(hostvars.keys())
    
    def list_all_groups(self) -> List[str]:
        """
        列出所有群组名
        
        Returns:
            list: 群组名列表（排除 _meta）
        """
        inventory = self.get_full_inventory()
        return [key for key in inventory.keys() if key != '_meta']
    
    def get_group_hosts(self, group_name: str) -> List[str]:
        """
        获取特定群组的主机列表
        
        Args:
            group_name: 群组名
        
        Returns:
            list: 主机名列表
        """
        inventory = self.get_full_inventory()
        group_data = inventory.get(group_name, {})
        return group_data.get('hosts', [])
    
    def get_host_groups(self, hostname: str) -> List[str]:
        """
        获取主机所属的所有群组
        
        Args:
            hostname: 主机名
        
        Returns:
            list: 群组名列表
        """
        inventory = self.get_full_inventory()
        groups = []
        
        for group_name, group_data in inventory.items():
            if group_name == '_meta':
                continue
            hosts = group_data.get('hosts', [])
            if hostname in hosts:
                groups.append(group_name)
        
        return groups
    
    def get_hosts_summary(self) -> List[Dict[str, Any]]:
        """
        获取所有主机的摘要信息
        
        Returns:
            list: 主机摘要列表
            [
                {
                    'hostname': 'Test-KVM01',
                    'ansible_host': '10.250.71.22',
                    'device_number': 'PC-SSD-4632',
                    'groups': ['PQ1_3_K01', 'all']
                },
                ...
            ]
        """
        inventory = self.get_full_inventory()
        hostvars = inventory.get('_meta', {}).get('hostvars', {})
        
        hosts_summary = []
        for hostname, variables in hostvars.items():
            groups = self.get_host_groups(hostname)
            
            summary = {
                'hostname': hostname,
                'ansible_host': variables.get('ansible_host', 'N/A'),
                'device_number': variables.get('device_number', 'N/A'),
                'sample_number': variables.get('sample_number', 'N/A'),
                'uart_id': variables.get('uart_id', 'N/A'),
                'groups': groups
            }
            hosts_summary.append(summary)
        
        return hosts_summary
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        获取 inventory 统计信息
        
        Returns:
            dict: 统计信息
        """
        inventory = self.get_full_inventory()
        hostvars = inventory.get('_meta', {}).get('hostvars', {})
        
        total_hosts = len(hostvars)
        total_groups = len([k for k in inventory.keys() if k != '_meta'])
        
        # 统计各群组的主机数量
        group_stats = {}
        for group_name, group_data in inventory.items():
            if group_name == '_meta':
                continue
            hosts = group_data.get('hosts', [])
            group_stats[group_name] = len(hosts)
        
        return {
            'total_hosts': total_hosts,
            'total_groups': total_groups,
            'group_stats': group_stats,
            'inventory_path': str(self.inventory_path)
        }


# ================ 使用示例 ================

if __name__ == '__main__':
    # 示例：解析 inventory 文件
    inventory_path = '/mnt/mdt/Team/PQ1-3/tool/jenkins_test_storage/10.252.170.171/Test-KVM01/148/artifacts/inventory/hosts'
    
    service = AnsibleInventoryService(inventory_path)
    
    # 获取统计信息
    stats = service.get_statistics()
    print(f"Total hosts: {stats['total_hosts']}")
    print(f"Total groups: {stats['total_groups']}")
    
    # 获取所有主机
    hosts = service.list_all_hosts()
    print(f"\nHosts: {hosts}")
    
    # 获取特定主机配置
    config = service.get_host_config('Test-KVM01')
    print(f"\nTest-KVM01 config:")
    print(f"  IP: {config.get('ansible_host')}")
    print(f"  Device: {config.get('device_number')}")
```

---

## 🔧 Django Views 扩展

### 扩展 JenkinsJobViewSet

```python
# backend/api/views/jenkins.py

from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from pathlib import Path
import logging

from library.services.ansible_inventory_service import AnsibleInventoryService

logger = logging.getLogger(__name__)


class JenkinsJobViewSet(viewsets.ModelViewSet):
    # ... 现有代码 ...
    
    def _get_latest_build_inventory_path(self, job):
        """
        获取 Job 最新 Build 的 inventory 文件路径
        
        Args:
            job: JenkinsJob 实例
        
        Returns:
            Path or None: inventory 文件路径，如果不存在返回 None
        """
        # 获取最新的 Build（有 artifacts 的）
        latest_build = job.builds.filter(
            is_artifacts_stored=True
        ).order_by('-build_number').first()
        
        if not latest_build:
            return None
        
        # 构建 inventory 文件路径
        inventory_path = Path(latest_build.artifacts_path) / 'inventory' / 'hosts'
        
        if inventory_path.exists():
            return inventory_path
        
        return None
    
    @action(detail=True, methods=['get'])
    def ansible_inventory(self, request, pk=None):
        """
        获取完整的 Ansible Inventory 数据
        
        GET /api/jenkins-jobs/{id}/ansible_inventory/
        
        Returns:
            完整的 inventory 结构（JSON）
        """
        job = self.get_object()
        
        try:
            inventory_path = self._get_latest_build_inventory_path(job)
            
            if not inventory_path:
                return Response({
                    'success': False,
                    'message': 'No inventory file found for this job'
                }, status=status.HTTP_404_NOT_FOUND)
            
            # 使用 AnsibleInventoryService 解析
            service = AnsibleInventoryService(str(inventory_path))
            
            # 获取完整数据
            inventory_data = service.get_full_inventory()
            stats = service.get_statistics()
            
            return Response({
                'success': True,
                'job_id': job.id,
                'job_name': job.name,
                'build_number': job.builds.filter(
                    is_artifacts_stored=True
                ).order_by('-build_number').first().build_number,
                'inventory_path': str(inventory_path),
                'inventory_exists': True,
                'total_hosts': stats['total_hosts'],
                'total_groups': stats['total_groups'],
                'data': inventory_data
            })
            
        except FileNotFoundError as e:
            logger.error(f"Inventory file not found: {e}")
            return Response({
                'success': False,
                'message': str(e)
            }, status=status.HTTP_404_NOT_FOUND)
        except RuntimeError as e:
            logger.error(f"Failed to parse inventory: {e}")
            return Response({
                'success': False,
                'message': f'Failed to parse inventory: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as e:
            logger.error(f"Unexpected error: {e}", exc_info=True)
            return Response({
                'success': False,
                'message': f'Unexpected error: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['get'], url_path='ansible_inventory/hosts')
    def ansible_inventory_hosts(self, request, pk=None):
        """
        获取所有主机列表
        
        GET /api/jenkins-jobs/{id}/ansible_inventory/hosts/
        
        Returns:
            主机列表（包含基本信息）
        """
        job = self.get_object()
        
        try:
            inventory_path = self._get_latest_build_inventory_path(job)
            
            if not inventory_path:
                return Response({
                    'success': False,
                    'message': 'No inventory file found for this job'
                }, status=status.HTTP_404_NOT_FOUND)
            
            service = AnsibleInventoryService(str(inventory_path))
            
            # 获取主机摘要
            hosts_summary = service.get_hosts_summary()
            
            latest_build = job.builds.filter(
                is_artifacts_stored=True
            ).order_by('-build_number').first()
            
            return Response({
                'success': True,
                'job_id': job.id,
                'job_name': job.name,
                'build_number': latest_build.build_number,
                'total_hosts': len(hosts_summary),
                'hosts': hosts_summary
            })
            
        except Exception as e:
            logger.error(f"Failed to get hosts: {e}", exc_info=True)
            return Response({
                'success': False,
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['get'], url_path='ansible_inventory/hosts/(?P<hostname>[^/.]+)')
    def ansible_inventory_host_config(self, request, pk=None, hostname=None):
        """
        获取特定主机的配置
        
        GET /api/jenkins-jobs/{id}/ansible_inventory/hosts/{hostname}/
        
        Args:
            hostname: 主机名（URL 参数）
        
        Returns:
            主机的完整配置（包括所有继承的变量）
        """
        job = self.get_object()
        
        try:
            inventory_path = self._get_latest_build_inventory_path(job)
            
            if not inventory_path:
                return Response({
                    'success': False,
                    'message': 'No inventory file found for this job'
                }, status=status.HTTP_404_NOT_FOUND)
            
            service = AnsibleInventoryService(str(inventory_path))
            
            # 获取主机配置
            host_config = service.get_host_config(hostname)
            groups = service.get_host_groups(hostname)
            
            latest_build = job.builds.filter(
                is_artifacts_stored=True
            ).order_by('-build_number').first()
            
            return Response({
                'success': True,
                'job_id': job.id,
                'job_name': job.name,
                'build_number': latest_build.build_number,
                'hostname': hostname,
                'groups': groups,
                'variables': host_config
            })
            
        except RuntimeError as e:
            # ansible-inventory --host 失败（主机不存在）
            logger.warning(f"Host not found: {hostname}")
            return Response({
                'success': False,
                'message': f'Host not found: {hostname}'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Failed to get host config: {e}", exc_info=True)
            return Response({
                'success': False,
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
```

---

## 📦 依赖安装

### requirements.txt

```txt
# 现有依赖
Django==4.2.25
djangorestframework==3.14.0
...

# 新增：Ansible
ansible>=8.0.0  # 或 ansible-core>=2.15.0（更轻量）
```

### Dockerfile 修改

```dockerfile
# backend/Dockerfile

FROM python:3.11-slim

# ... 现有内容 ...

# 安装系统依赖（Ansible 可能需要）
RUN apt-get update && apt-get install -y \
    gcc \
    python3-dev \
    libffi-dev \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# 安装 Python 依赖
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# ... 其余内容 ...
```

---

## 🧪 测试用例设计

### 单元测试

```python
# backend/api/tests/test_ansible_inventory_service.py

import unittest
from pathlib import Path
from library.services.ansible_inventory_service import AnsibleInventoryService


class TestAnsibleInventoryService(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        """设置测试环境"""
        cls.inventory_path = Path('/mnt/mdt/Team/PQ1-3/tool/jenkins_test_storage/10.252.170.171/Test-KVM01/148/artifacts/inventory/hosts')
        cls.service = AnsibleInventoryService(str(cls.inventory_path))
    
    def test_get_full_inventory(self):
        """测试获取完整 inventory"""
        inventory = self.service.get_full_inventory()
        
        self.assertIn('_meta', inventory)
        self.assertIn('hostvars', inventory['_meta'])
        self.assertIsInstance(inventory['_meta']['hostvars'], dict)
    
    def test_list_all_hosts(self):
        """测试列出所有主机"""
        hosts = self.service.list_all_hosts()
        
        self.assertIsInstance(hosts, list)
        self.assertGreater(len(hosts), 0)
        self.assertIn('Test-KVM01', hosts)
    
    def test_get_host_config(self):
        """测试获取主机配置"""
        config = self.service.get_host_config('Test-KVM01')
        
        self.assertIsInstance(config, dict)
        self.assertIn('ansible_host', config)
        self.assertEqual(config['ansible_host'], '10.250.71.22')
    
    def test_get_host_groups(self):
        """测试获取主机群组"""
        groups = self.service.get_host_groups('Test-KVM01')
        
        self.assertIsInstance(groups, list)
        self.assertIn('PQ1_3_K01', groups)
    
    def test_get_statistics(self):
        """测试获取统计信息"""
        stats = self.service.get_statistics()
        
        self.assertIn('total_hosts', stats)
        self.assertIn('total_groups', stats)
        self.assertGreater(stats['total_hosts'], 0)
```

### API 测试

```python
# backend/api/tests/test_ansible_inventory_api.py

from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from api.models import JenkinsJob, JenkinsBuild


class TestAnsibleInventoryAPI(TestCase):
    
    def setUp(self):
        """设置测试数据"""
        self.client = APIClient()
        
        # 创建测试 Job
        self.job = JenkinsJob.objects.create(
            name='Test-KVM01',
            server_id=12
        )
        
        # 创建测试 Build（假设已存储 artifacts）
        self.build = JenkinsBuild.objects.create(
            job=self.job,
            build_number=148,
            is_artifacts_stored=True,
            artifacts_path='/mnt/mdt/Team/PQ1-3/tool/jenkins_test_storage/10.252.170.171/Test-KVM01/148/artifacts'
        )
    
    def test_get_ansible_inventory(self):
        """测试获取完整 inventory"""
        url = reverse('jenkinsjob-ansible-inventory', kwargs={'pk': self.job.id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['success'])
        self.assertIn('data', response.data)
    
    def test_get_ansible_inventory_hosts(self):
        """测试获取主机列表"""
        url = reverse('jenkinsjob-ansible-inventory-hosts', kwargs={'pk': self.job.id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['success'])
        self.assertIn('hosts', response.data)
    
    def test_get_host_config(self):
        """测试获取特定主机配置"""
        url = reverse('jenkinsjob-ansible-inventory-host-config', 
                     kwargs={'pk': self.job.id, 'hostname': 'Test-KVM01'})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['success'])
        self.assertIn('variables', response.data)
```

---

## 📊 使用流程

### 1. 通过 Job Name 查询 Job ID

```bash
# 查询 Job
GET /api/jenkins-jobs/?search=Test-KVM01

Response:
[
    {
        "id": 269,
        "name": "Test-KVM01",
        ...
    }
]
```

### 2. 获取 Ansible Inventory

```bash
# 方式 1: 获取完整 inventory
GET /api/jenkins-jobs/269/ansible_inventory/

# 方式 2: 获取主机列表
GET /api/jenkins-jobs/269/ansible_inventory/hosts/

# 方式 3: 获取特定主机配置
GET /api/jenkins-jobs/269/ansible_inventory/hosts/Test-KVM01/
```

---

## 🔒 错误处理

### 错误场景

1. **Inventory 文件不存在**
   ```json
   {
       "success": false,
       "message": "No inventory file found for this job"
   }
   ```

2. **Ansible 未安装**
   ```json
   {
       "success": false,
       "message": "ansible-inventory command not found. Please install ansible: pip install ansible"
   }
   ```

3. **主机不存在**
   ```json
   {
       "success": false,
       "message": "Host not found: Invalid-Host"
   }
   ```

4. **Inventory 格式错误**
   ```json
   {
       "success": false,
       "message": "Failed to parse inventory: Invalid JSON output"
   }
   ```

---

## 📝 实施步骤

### Phase 1: 基础服务实现（1 天）
- [x] 规划完成
- [ ] 创建 `AnsibleInventoryService` 类
- [ ] 实现核心方法（get_full_inventory, get_host_config, list_all_hosts）
- [ ] 单元测试

### Phase 2: Django Views 集成（1 天）
- [ ] 扩展 `JenkinsJobViewSet`
- [ ] 实现 3 个 API endpoint
- [ ] 错误处理和日志记录
- [ ] API 测试

### Phase 3: 部署和测试（0.5 天）
- [ ] 更新 requirements.txt
- [ ] 修改 Dockerfile
- [ ] 重建容器并部署
- [ ] 端到端测试

### Phase 4: 文档和优化（0.5 天）
- [ ] API 文档
- [ ] 使用示例
- [ ] 性能优化（缓存）

**总计**: 约 3 天

---

## 🎯 下一步

确认以下问题后即可开始实施：

1. ✅ **方案确认**: 使用方案 A（Ansible 工具）
2. ✅ **查询方式**: 通过 Job Name → Job ID → Inventory
3. ✅ **API 设计**: 3 个 endpoint（完整 / 主机列表 / 特定主机）
4. ❓ **安装 Ansible**: 是否同意在 Django 容器中安装 ansible？
5. ❓ **测试数据**: 是否使用 Test-KVM01 Build #148 作为测试数据？

确认后立即开始实施！🚀
