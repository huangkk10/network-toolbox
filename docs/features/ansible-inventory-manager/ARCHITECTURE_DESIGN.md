# Ansible Inventory Manager - 架構設計文檔

## 📋 功能概述

**目標**：提供一個網頁介面，讓使用者可以從 NAS 導入、檢查、編輯、並儲存 Ansible Inventory 配置文件。

**核心功能**：
1. 從 NAS 路徑導入 `inventory/hosts` 文件
2. 使用 `ansible-inventory` 命令驗證語法
3. 讀取並顯示所有 Host 配置（統計資訊）
4. **使用文本編輯器直接編輯整份 hosts 文件**
5. 語法驗證和實時錯誤提示
6. 對每台 Host 進行配置檢查（類似 Build 配置檢查）
7. 版本備份和回滾機制
8. 操作日誌記錄

---

## 🏗️ 系統架構

### 整體架構圖

```
┌─────────────────────────────────────────────────────────────┐
│                        Frontend (React)                      │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Ansible Inventory Manager Page                      │  │
│  │  ├── Import Form (NAS Path Input)                    │  │
│  │  ├── Inventory Info Card (統計資訊)                 │  │
│  │  ├── Monaco Text Editor (hosts 文件編輯器)          │  │
│  │  │   ├── 語法高亮                                    │  │
│  │  │   ├── 行號顯示                                    │  │
│  │  │   ├── 錯誤標記                                    │  │
│  │  │   └── 自動儲存草稿                                │  │
│  │  ├── Validation Results Display                      │  │
│  │  └── Version History Viewer                          │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                            ↕ REST API
┌─────────────────────────────────────────────────────────────┐
│                     Backend (Django)                         │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  API Endpoints (api/views/ansible_inventory.py)      │  │
│  │  ├── POST   /api/ansible-inventory/import/           │  │
│  │  ├── GET    /api/ansible-inventory/<id>/content/     │  │
│  │  ├── POST   /api/ansible-inventory/<id>/update-content/│ │
│  │  ├── POST   /api/ansible-inventory/validate-content/ │  │
│  │  ├── POST   /api/ansible-inventory/<id>/save/        │  │
│  │  ├── GET    /api/ansible-inventory/<id>/versions/    │  │
│  │  └── POST   /api/ansible-inventory/<id>/rollback/    │  │
│  └──────────────────────────────────────────────────────┘  │
│                            ↕                                 │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Business Logic (library/services/)                  │  │
│  │  ├── AnsibleInventoryService                         │  │
│  │  │   ├── import_from_nas()                           │  │
│  │  │   ├── validate_syntax()                           │  │
│  │  │   ├── parse_inventory()                           │  │
│  │  │   ├── get_file_content()         (新增)           │  │
│  │  │   ├── update_file_content()      (新增)           │  │
│  │  │   ├── validate_content_syntax()  (新增)           │  │
│  │  │   ├── save_to_nas()                               │  │
│  │  │   └── create_backup()                             │  │
│  │  │                                                    │  │
│  │  └── InventoryConfigValidator                        │  │
│  │      ├── validate_host_config()                      │  │
│  │      ├── check_ip_address()                          │  │
│  │      ├── check_mac_address()                         │  │
│  │      └── check_uart_ssh()                            │  │
│  └──────────────────────────────────────────────────────┘  │
│                            ↕                                 │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Database Models (api/models.py)                     │  │
│  │  ├── AnsibleInventoryImport                          │  │
│  │  ├── AnsibleHostConfig                               │  │
│  │  ├── InventoryVersion                                │  │
│  │  └── InventoryEditLog                                │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                            ↕
┌─────────────────────────────────────────────────────────────┐
│                       NAS Storage                            │
│  /mnt/mdt/Script/chunwei_test/26_7F_new/inventory/          │
│  ├── hosts                          (原始檔案)              │
│  ├── hosts.backup.2025-11-18_14-30  (自動備份)              │
│  └── hosts.backup.2025-11-18_15-00  (自動備份)              │
└─────────────────────────────────────────────────────────────┘

---

## 📊 資料庫設計

### 1. AnsibleInventoryImport（導入記錄）

```python
class AnsibleInventoryImport(models.Model):
    """Ansible Inventory 導入記錄"""
    
    # 基本資訊
    nas_path = models.CharField(max_length=500, verbose_name='NAS 路徑')
    # 範例: \\10.250.0.1\mdt\Script\chunwei_test\26_7F_new\inventory
    
    file_name = models.CharField(max_length=255, default='hosts', verbose_name='檔案名稱')
    
    # 導入狀態
    STATUS_CHOICES = [
        ('pending', '等待導入'),
        ('importing', '導入中'),
        ('success', '導入成功'),
        ('failed', '導入失敗'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # 語法驗證結果
    syntax_valid = models.BooleanField(default=False, verbose_name='語法有效')
    syntax_error = models.TextField(blank=True, null=True, verbose_name='語法錯誤訊息')
    
    # 統計資訊
    total_hosts = models.IntegerField(default=0, verbose_name='總 Host 數量')
    total_groups = models.IntegerField(default=0, verbose_name='總 Group 數量')
    
    # 編輯鎖定（防止多人同時編輯）
    is_locked = models.BooleanField(default=False, verbose_name='編輯鎖定')
    locked_by = models.ForeignKey(
        'auth.User', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='locked_inventories',
        verbose_name='鎖定者'
    )
    locked_at = models.DateTimeField(null=True, blank=True, verbose_name='鎖定時間')
    
    # 當前版本
    current_version = models.IntegerField(default=1, verbose_name='當前版本號')
    
    # 時間戳記
    imported_at = models.DateTimeField(auto_now_add=True, verbose_name='導入時間')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新時間')
    imported_by = models.ForeignKey(
        'auth.User',
        on_delete=models.SET_NULL,
        null=True,
        related_name='imported_inventories',
        verbose_name='導入者'
    )
    
    class Meta:
        db_table = 'ansible_inventory_import'
        verbose_name = 'Ansible Inventory 導入'
        verbose_name_plural = 'Ansible Inventory 導入記錄'
        ordering = ['-imported_at']
    
    def __str__(self):
        return f"{self.nas_path}/{self.file_name} - {self.status}"
```

### 2. AnsibleHostConfig（Host 配置）

```python
class AnsibleHostConfig(models.Model):
    """Ansible Host 配置"""
    
    # 關聯到導入記錄
    inventory = models.ForeignKey(
        AnsibleInventoryImport,
        on_delete=models.CASCADE,
        related_name='hosts',
        verbose_name='所屬 Inventory'
    )
    
    # Host 基本資訊
    hostname = models.CharField(max_length=255, verbose_name='主機名稱')
    # 範例: PQ1_3_K14_01
    
    groups = models.JSONField(default=list, verbose_name='所屬 Groups')
    # 範例: ["IOL_Linux", "PQ1_3", "PQ1_3_K14"]
    
    # Ansible 變數（從 inventory 解析）
    ansible_host = models.CharField(max_length=255, blank=True, null=True, verbose_name='IP 地址')
    ansible_user = models.CharField(max_length=100, blank=True, null=True, verbose_name='SSH 使用者')
    ansible_password = models.CharField(max_length=255, blank=True, null=True, verbose_name='SSH 密碼')
    ansible_port = models.IntegerField(default=22, verbose_name='SSH 端口')
    
    # 自訂變數
    mac_address = models.CharField(max_length=17, blank=True, null=True, verbose_name='MAC 地址')
    uart_host = models.CharField(max_length=255, blank=True, null=True, verbose_name='UART 主機')
    
    # 其他所有變數存為 JSON
    other_vars = models.JSONField(default=dict, verbose_name='其他變數')
    
    # 配置驗證結果
    validation_status = models.CharField(
        max_length=20,
        choices=[
            ('not_checked', '未檢查'),
            ('passed', '通過'),
            ('failed', '失敗'),
            ('warning', '警告'),
        ],
        default='not_checked',
        verbose_name='驗證狀態'
    )
    validation_results = models.JSONField(default=dict, verbose_name='驗證結果')
    # 格式: {
    #     'ip_check': {'status': 'passed', 'message': '...'},
    #     'mac_check': {'status': 'failed', 'message': '...'},
    #     'uart_ssh': {'status': 'passed', 'details': {...}}
    # }
    
    # 最後驗證時間
    last_validated_at = models.DateTimeField(null=True, blank=True, verbose_name='最後驗證時間')
    
    # 時間戳記
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='創建時間')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新時間')
    
    class Meta:
        db_table = 'ansible_host_config'
        verbose_name = 'Ansible Host 配置'
        verbose_name_plural = 'Ansible Host 配置'
        ordering = ['hostname']
        unique_together = [['inventory', 'hostname']]
    
    def __str__(self):
        return f"{self.hostname} ({self.ansible_host})"
```

### 3. InventoryVersion（版本記錄）

```python
class InventoryVersion(models.Model):
    """Inventory 文件版本記錄"""
    
    # 關聯到導入記錄
    inventory = models.ForeignKey(
        AnsibleInventoryImport,
        on_delete=models.CASCADE,
        related_name='versions',
        verbose_name='所屬 Inventory'
    )
    
    # 版本資訊
    version_number = models.IntegerField(verbose_name='版本號')
    
    # 備份文件路徑
    backup_file_path = models.CharField(max_length=500, verbose_name='備份檔案路徑')
    # 範例: /mnt/mdt/.../inventory/hosts.backup.2025-11-18_14-30-00
    
    # 文件內容快照（可選，用於快速預覽）
    content_snapshot = models.TextField(blank=True, null=True, verbose_name='內容快照')
    
    # 變更摘要
    change_summary = models.TextField(blank=True, null=True, verbose_name='變更摘要')
    # 範例: "修改了 3 台 Host 的 IP 地址"
    
    # 時間和操作者
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='創建時間')
    created_by = models.ForeignKey(
        'auth.User',
        on_delete=models.SET_NULL,
        null=True,
        verbose_name='創建者'
    )
    
    class Meta:
        db_table = 'inventory_version'
        verbose_name = 'Inventory 版本'
        verbose_name_plural = 'Inventory 版本記錄'
        ordering = ['-version_number']
        unique_together = [['inventory', 'version_number']]
    
    def __str__(self):
        return f"{self.inventory.file_name} v{self.version_number}"
```

### 4. InventoryEditLog（操作日誌）

```python
class InventoryEditLog(models.Model):
    """Inventory 編輯操作日誌"""
    
    # 關聯
    inventory = models.ForeignKey(
        AnsibleInventoryImport,
        on_delete=models.CASCADE,
        related_name='edit_logs',
        verbose_name='所屬 Inventory'
    )
    
    host_config = models.ForeignKey(
        AnsibleHostConfig,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='edit_logs',
        verbose_name='相關 Host'
    )
    
    # 操作類型
    ACTION_CHOICES = [
        ('import', '導入'),
        ('edit', '編輯'),
        ('save', '儲存'),
        ('rollback', '回滾'),
        ('validate', '驗證'),
    ]
    action = models.CharField(max_length=20, choices=ACTION_CHOICES, verbose_name='操作類型')
    
    # 變更詳情
    changes = models.JSONField(default=dict, verbose_name='變更內容')
    # 格式: {
    #     'field': 'ansible_host',
    #     'old_value': '192.168.1.100',
    #     'new_value': '192.168.1.101'
    # }
    
    # 操作結果
    success = models.BooleanField(default=True, verbose_name='操作成功')
    error_message = models.TextField(blank=True, null=True, verbose_name='錯誤訊息')
    
    # 時間和操作者
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='操作時間')
    created_by = models.ForeignKey(
        'auth.User',
        on_delete=models.SET_NULL,
        null=True,
        verbose_name='操作者'
    )
    
    # IP 地址（追蹤來源）
    ip_address = models.GenericIPAddressField(blank=True, null=True, verbose_name='來源 IP')
    
    class Meta:
        db_table = 'inventory_edit_log'
        verbose_name = 'Inventory 編輯日誌'
        verbose_name_plural = 'Inventory 編輯日誌'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.action} by {self.created_by} at {self.created_at}"
```

---

## 🔌 API 端點設計

### 1. 導入 Inventory

**端點**：`POST /api/ansible-inventory/import/`

**請求**：
```json
{
    "nas_path": "\\\\10.250.0.1\\mdt\\Script\\chunwei_test\\26_7F_new\\inventory",
    "file_name": "hosts"
}
```

**處理流程**：
1. 驗證 NAS 路徑格式
2. 將 Windows 路徑轉換為 Linux 掛載路徑（`/mnt/mdt/...`）
3. 檢查文件是否存在
4. 使用 `ansible-inventory` 驗證語法
5. 解析 Inventory，提取統計資訊（總 Host 數、總 Group 數）
6. 創建 `AnsibleInventoryImport` 記錄
7. 批次創建 `AnsibleHostConfig` 記錄（用於後續配置檢查）
8. 返回導入結果

**響應**：
```json
{
    "id": 1,
    "nas_path": "\\\\10.250.0.1\\mdt\\Script\\chunwei_test\\26_7F_new\\inventory",
    "status": "success",
    "syntax_valid": true,
    "total_hosts": 15,
    "total_groups": 6,
    "imported_at": "2025-11-18T14:30:00Z"
}
```

---

### 2. 獲取文件內容（新增）

**端點**：`GET /api/ansible-inventory/<id>/content/`

**處理流程**：
1. 從資料庫獲取 NAS 路徑
2. 讀取 hosts 文件內容
3. 返回原始文本

**響應**：
```json
{
    "content": "[IOL_Linux]\nPQ1_3_K14_01 ansible_host=10.250.53.83 ...\n",
    "file_path": "/mnt/mdt/.../inventory/hosts",
    "last_modified": "2025-11-18T14:30:00Z"
}
```

---

### 3. 更新文件內容（新增）

**端點**：`POST /api/ansible-inventory/<id>/update-content/`

**請求**：
```json
{
    "content": "[IOL_Linux]\nPQ1_3_K14_01 ansible_host=10.250.53.84 ...\n",
    "validate_only": false,
    "change_summary": "修改了 PQ1_3_K14_01 的 IP 地址"
}
```

**處理流程**：
1. 檢查 Inventory 是否被鎖定
2. 如果未鎖定，自動鎖定給當前使用者
3. 驗證內容語法（寫入臨時文件測試）
4. 如果 `validate_only=true`，只返回驗證結果
5. 如果 `validate_only=false`：
   - 創建備份
   - 寫入 NAS
   - 重新解析並更新資料庫
   - 創建版本記錄
   - 記錄操作日誌
   - 解除鎖定

**響應**：
```json
{
    "success": true,
    "syntax_valid": true,
    "version": 2,
    "backup_file": "/mnt/mdt/.../hosts.backup.2025-11-18_14-45-00",
    "saved_at": "2025-11-18T14:45:00Z"
}
```

---

### 4. 驗證內容語法（新增）

**端點**：`POST /api/ansible-inventory/validate-content/`

**請求**：
```json
{
    "content": "[IOL_Linux]\nPQ1_3_K14_01 ansible_host=10.250.53.84 ...\n"
}
```

**處理流程**：
1. 將內容寫入臨時文件
2. 使用 `ansible-inventory --list` 驗證
3. 返回驗證結果
4. 刪除臨時文件

**響應**：
```json
{
    "syntax_valid": true,
    "error_message": null,
    "parsed_hosts": 15,
    "parsed_groups": 6
}
```

或錯誤情況：
```json
{
    "syntax_valid": false,
    "error_message": "ERROR! Syntax Error at line 10: ...",
    "error_line": 10
}
```

---

### 5. 驗證配置

**端點**：`POST /api/ansible-inventory/<id>/validate/`

**請求**：
```json
{
    "validate_type": "config"  // 對所有 Host 進行配置檢查
}
```

**處理流程**：
1. 對每台 Host 進行配置檢查（IP、MAC、UART SSH）
2. 更新 `AnsibleHostConfig` 的驗證結果
3. 返回檢查統計

**響應**：
```json
{
    "validation_results": {
        "hosts_checked": 15,
        "hosts_passed": 12,
        "hosts_failed": 3,
        "details": [
            {
                "hostname": "PQ1_3_K14_01",
                "status": "passed",
                "checks": {
                    "ip_check": {"status": "passed"},
                    "mac_check": {"status": "passed"},
                    "uart_ssh": {"status": "passed"}
                }
            },
            ...
        ]
    }
}
```

---

### 6. 獲取 Host 列表（保留用於配置檢查結果顯示）

**端點**：`GET /api/ansible-inventory/<id>/hosts/`

**查詢參數**：
- `validation_status`: 過濾驗證狀態（passed/failed/warning）

**響應**：
```json
{
    "total": 15,
    "hosts": [
        {
            "id": 1,
            "hostname": "PQ1_3_K14_01",
            "ansible_host": "10.250.53.83",
            "validation_status": "passed",
            "validation_results": {...},
            "last_validated_at": "2025-11-18T14:35:00Z"
        },
        ...
    ]
}
```

---

### 7. 獲取版本歷史

**端點**：`GET /api/ansible-inventory/<id>/versions/`

**響應**：
```json
{
    "current_version": 3,
    "versions": [
        {
            "version_number": 3,
            "backup_file_path": "/mnt/mdt/.../hosts.backup.2025-11-18_15-00-00",
            "change_summary": "修改了 UART 配置",
            "created_at": "2025-11-18T15:00:00Z",
            "created_by": "admin"
        },
        {
            "version_number": 2,
            "backup_file_path": "/mnt/mdt/.../hosts.backup.2025-11-18_14-45-00",
            "change_summary": "修改了 IP 地址",
            "created_at": "2025-11-18T14:45:00Z",
            "created_by": "admin"
        },
        ...
    ]
}
```

---

### 7. 回滾到特定版本

**端點**：`POST /api/ansible-inventory/<id>/rollback/`

**請求**：
```json
{
    "version_number": 2
}
```

**處理流程**：
1. 檢查目標版本是否存在
2. 讀取備份檔案內容
3. **創建當前版本的備份**（以防回滾錯誤）
4. 將備份內容寫回 NAS
5. 重新導入並解析 Inventory
6. 更新所有 Host 配置
7. 創建新版本記錄
8. 記錄回滾操作日誌

**響應**：
```json
{
    "success": true,
    "rolled_back_to": 2,
    "new_version": 4,
    "message": "成功回滾到版本 2"
}
```

---

## 🔧 後端服務設計

### AnsibleInventoryService

```python
# library/services/ansible_inventory_service.py

import os
import re
import subprocess
import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

class AnsibleInventoryService:
    """Ansible Inventory 管理服務"""
    
    def __init__(self, nas_base_path: str = '/mnt/mdt'):
        self.nas_base_path = nas_base_path
    
    def convert_windows_path_to_linux(self, windows_path: str) -> str:
        """
        將 Windows 網路路徑轉換為 Linux 掛載路徑
        
        範例:
            \\10.250.0.1\mdt\Script\test
            -> /mnt/mdt/Script/test
        """
        # 移除開頭的 \\server\share\
        path = windows_path.replace('\\', '/')
        path = re.sub(r'^//[\d\.]+/mdt/', '', path)
        
        return os.path.join(self.nas_base_path, path)
    
    def import_from_nas(
        self, 
        nas_path: str, 
        file_name: str = 'hosts'
    ) -> Tuple[bool, str, Dict]:
        """
        從 NAS 導入 Inventory 文件
        
        Returns:
            (success, error_message, parsed_data)
        """
        # 轉換路徑
        linux_path = self.convert_windows_path_to_linux(nas_path)
        full_path = os.path.join(linux_path, file_name)
        
        # 檢查文件是否存在
        if not os.path.exists(full_path):
            return False, f"文件不存在: {full_path}", {}
        
        # 驗證語法
        syntax_valid, syntax_error = self.validate_syntax(full_path)
        if not syntax_valid:
            return False, syntax_error, {}
        
        # 解析 Inventory
        parsed_data = self.parse_inventory(full_path)
        
        return True, "", parsed_data
    
    def validate_syntax(self, inventory_path: str) -> Tuple[bool, Optional[str]]:
        """
        使用 ansible-inventory 驗證語法
        
        Returns:
            (is_valid, error_message)
        """
        try:
            result = subprocess.run(
                ['ansible-inventory', '-i', inventory_path, '--list'],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                return False, result.stderr
            
            # 嘗試解析 JSON 輸出
            json.loads(result.stdout)
            return True, None
            
        except subprocess.TimeoutExpired:
            return False, "語法驗證超時"
        except json.JSONDecodeError as e:
            return False, f"JSON 解析錯誤: {str(e)}"
        except Exception as e:
            return False, f"驗證失敗: {str(e)}"
    
    def parse_inventory(self, inventory_path: str) -> Dict:
        """
        解析 Inventory 文件，提取所有 Host 和變數
        
        Returns:
            {
                'hosts': [...],
                'groups': {...},
                'total_hosts': int,
                'total_groups': int
            }
        """
        try:
            result = subprocess.run(
                ['ansible-inventory', '-i', inventory_path, '--list'],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            inventory_data = json.loads(result.stdout)
            
            # 提取 Host 資訊
            hosts = []
            groups = {}
            
            # 解析 _meta.hostvars
            hostvars = inventory_data.get('_meta', {}).get('hostvars', {})
            
            for hostname, vars_dict in hostvars.items():
                host_info = {
                    'hostname': hostname,
                    'ansible_host': vars_dict.get('ansible_host'),
                    'ansible_user': vars_dict.get('ansible_user'),
                    'ansible_password': vars_dict.get('ansible_password'),
                    'ansible_port': vars_dict.get('ansible_port', 22),
                    'mac_address': vars_dict.get('mac_address'),
                    'uart_host': vars_dict.get('uart_host'),
                    'other_vars': {
                        k: v for k, v in vars_dict.items()
                        if k not in ['ansible_host', 'ansible_user', 'ansible_password', 
                                     'ansible_port', 'mac_address', 'uart_host']
                    },
                    'groups': []
                }
                hosts.append(host_info)
            
            # 解析 Groups
            for group_name, group_data in inventory_data.items():
                if group_name in ['_meta', 'all']:
                    continue
                
                groups[group_name] = group_data.get('hosts', [])
                
                # 為每個 Host 添加所屬 Groups
                for host_name in group_data.get('hosts', []):
                    for host in hosts:
                        if host['hostname'] == host_name:
                            host['groups'].append(group_name)
            
            return {
                'hosts': hosts,
                'groups': groups,
                'total_hosts': len(hosts),
                'total_groups': len(groups)
            }
            
        except Exception as e:
            raise Exception(f"解析 Inventory 失敗: {str(e)}")
    
    def create_backup(self, original_file_path: str) -> str:
        """
        創建備份檔案
        
        Returns:
            backup_file_path
        """
        timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        backup_path = f"{original_file_path}.backup.{timestamp}"
        
        shutil.copy2(original_file_path, backup_path)
        
        return backup_path
    
    def get_file_content(self, inventory_path: str) -> Tuple[bool, str, Optional[str]]:
        """
        讀取 Inventory 文件內容（新增）
        
        Returns:
            (success, content, error_message)
        """
        try:
            with open(inventory_path, 'r', encoding='utf-8') as f:
                content = f.read()
            return True, content, None
        except Exception as e:
            return False, "", str(e)
    
    def update_file_content(
        self, 
        inventory_path: str, 
        content: str,
        create_backup: bool = True
    ) -> Tuple[bool, str, Optional[str]]:
        """
        更新 Inventory 文件內容（新增）
        
        Returns:
            (success, error_message, backup_file_path)
        """
        try:
            # 創建備份
            backup_path = None
            if create_backup and os.path.exists(inventory_path):
                backup_path = self.create_backup(inventory_path)
            
            # 驗證內容語法（寫入臨時文件測試）
            temp_path = f"{inventory_path}.tmp"
            with open(temp_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            syntax_valid, syntax_error = self.validate_syntax(temp_path)
            if not syntax_valid:
                os.remove(temp_path)
                return False, f"語法錯誤: {syntax_error}", backup_path
            
            # 寫入正式文件
            shutil.move(temp_path, inventory_path)
            
            return True, "", backup_path
            
        except Exception as e:
            return False, str(e), None
    
    def validate_content_syntax(self, content: str) -> Tuple[bool, Optional[str], Optional[Dict]]:
        """
        驗證文本內容的語法（新增）
        
        Returns:
            (is_valid, error_message, parsed_stats)
        """
        import tempfile
        
        try:
            # 創建臨時文件
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.ini') as f:
                f.write(content)
                temp_path = f.name
            
            # 驗證語法
            syntax_valid, syntax_error = self.validate_syntax(temp_path)
            
            # 如果語法正確，解析統計資訊
            parsed_stats = None
            if syntax_valid:
                parsed_data = self.parse_inventory(temp_path)
                parsed_stats = {
                    'total_hosts': parsed_data['total_hosts'],
                    'total_groups': parsed_data['total_groups']
                }
            
            # 刪除臨時文件
            os.remove(temp_path)
            
            return syntax_valid, syntax_error, parsed_stats
            
        except Exception as e:
            return False, str(e), None
    
    def generate_inventory_content(self, hosts_config: List[Dict]) -> str:
        """
        從 Host 配置生成 Ansible Inventory 格式內容
        
        Args:
            hosts_config: List of AnsibleHostConfig records
        
        Returns:
            Ansible Inventory 格式的字串
        """
        # 組織 Groups
        groups_dict = {}
        for host in hosts_config:
            for group in host.get('groups', []):
                if group not in groups_dict:
                    groups_dict[group] = []
                groups_dict[group].append(host)
        
        # 生成內容
        lines = []
        
        for group_name, group_hosts in groups_dict.items():
            lines.append(f"[{group_name}]")
            
            for host in group_hosts:
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
            
            lines.append("")  # 空行分隔
        
        return "\n".join(lines)
    
    def save_to_nas(
        self, 
        inventory_path: str, 
        content: str,
        create_backup: bool = True
    ) -> Tuple[bool, str, Optional[str]]:
        """
        儲存 Inventory 到 NAS
        
        Returns:
            (success, error_message, backup_file_path)
        """
        try:
            # 創建備份
            backup_path = None
            if create_backup and os.path.exists(inventory_path):
                backup_path = self.create_backup(inventory_path)
            
            # 驗證生成的內容語法（寫入臨時文件測試）
            temp_path = f"{inventory_path}.tmp"
            with open(temp_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            syntax_valid, syntax_error = self.validate_syntax(temp_path)
            if not syntax_valid:
                os.remove(temp_path)
                return False, f"生成的內容語法錯誤: {syntax_error}", backup_path
            
            # 寫入正式文件
            shutil.move(temp_path, inventory_path)
            
            return True, "", backup_path
            
        except Exception as e:
            return False, str(e), None
    
    def rollback_to_backup(
        self, 
        inventory_path: str, 
        backup_path: str
    ) -> Tuple[bool, str]:
        """
        從備份回滾
        
        Returns:
            (success, error_message)
        """
        try:
            if not os.path.exists(backup_path):
                return False, f"備份檔案不存在: {backup_path}"
            
            # 先創建當前版本的備份（防止回滾錯誤）
            current_backup = self.create_backup(inventory_path)
            
            # 複製備份檔案覆蓋當前檔案
            shutil.copy2(backup_path, inventory_path)
            
            # 驗證語法
            syntax_valid, syntax_error = self.validate_syntax(inventory_path)
            if not syntax_valid:
                # 回滾失敗，恢復當前版本
                shutil.copy2(current_backup, inventory_path)
                return False, f"回滾後語法錯誤: {syntax_error}"
            
            return True, ""
            
        except Exception as e:
            return False, str(e)
```

---

## 🛡️ 安全保護措施

### 1. 編輯鎖定機制

**目的**：防止多人同時編輯同一個 Inventory

**實現**：
```python
def acquire_lock(inventory_id: int, user) -> bool:
    """獲取編輯鎖"""
    inventory = AnsibleInventoryImport.objects.get(id=inventory_id)
    
    # 檢查是否已被鎖定
    if inventory.is_locked:
        # 檢查鎖定時間是否超過 30 分鐘（自動解鎖）
        if inventory.locked_at:
            time_diff = timezone.now() - inventory.locked_at
            if time_diff.total_seconds() > 1800:  # 30 分鐘
                # 自動解鎖
                inventory.is_locked = False
                inventory.locked_by = None
                inventory.locked_at = None
            else:
                # 仍在鎖定中
                if inventory.locked_by != user:
                    return False
    
    # 鎖定
    inventory.is_locked = True
    inventory.locked_by = user
    inventory.locked_at = timezone.now()
    inventory.save()
    
    return True

def release_lock(inventory_id: int):
    """釋放編輯鎖"""
    inventory = AnsibleInventoryImport.objects.get(id=inventory_id)
    inventory.is_locked = False
    inventory.locked_by = None
    inventory.locked_at = None
    inventory.save()
```

**前端提示**：
- 如果 Inventory 被鎖定，顯示：「該配置正在被 {user} 編輯中，請稍後再試」
- 自動每 5 分鐘檢查鎖定狀態
- 提供「強制解鎖」按鈕（僅管理員）

---

### 2. 自動版本備份

**觸發時機**：每次儲存到 NAS 前

**備份命名**：`hosts.backup.YYYY-MM-DD_HH-MM-SS`

**保留策略**：
- 保留最近 30 個版本
- 超過 30 個自動刪除最舊的

```python
def cleanup_old_backups(inventory_path: str, keep_count: int = 30):
    """清理舊備份"""
    directory = os.path.dirname(inventory_path)
    filename = os.path.basename(inventory_path)
    
    # 找出所有備份檔案
    backup_pattern = f"{filename}.backup.*"
    backups = []
    
    for file in os.listdir(directory):
        if file.startswith(f"{filename}.backup."):
            full_path = os.path.join(directory, file)
            backups.append((full_path, os.path.getmtime(full_path)))
    
    # 按時間排序
    backups.sort(key=lambda x: x[1], reverse=True)
    
    # 刪除超過保留數量的備份
    for backup_path, _ in backups[keep_count:]:
        os.remove(backup_path)
```

---

### 3. 語法強制驗證

**儲存前驗證**：
- 生成內容後先寫入臨時檔案
- 使用 `ansible-inventory --list` 驗證語法
- 語法正確才寫入正式檔案

**回滾後驗證**：
- 回滾後驗證語法
- 如果語法錯誤，自動回滾到回滾前的狀態

---

### 4. 操作日誌記錄

**記錄內容**：
- 誰（User）
- 何時（Timestamp）
- 做了什麼（Action）
- 修改了什麼（Changes）
- 結果（Success/Fail）
- 來源 IP

**日誌用途**：
- 審計追蹤
- 問題排查
- 責任追究

---

### 5. 權限控制（未來擴展）

**權限級別**：
- **檢視者**：只能查看配置，不能編輯
- **編輯者**：可以編輯並儲存
- **管理員**：可以強制解鎖、刪除版本、回滾

**實現**：使用 Django Permissions 或 Django Guardian

---

## 🎨 前端 UI 設計

### 頁面結構（修訂版：文本編輯器模式）

```
┌─────────────────────────────────────────────────────────┐
│  Ansible Inventory Manager                              │
├─────────────────────────────────────────────────────────┤
│  [導入新 Inventory]                                      │
│                                                          │
│  ┌────────────────────────────────────────────────────┐ │
│  │  NAS Path: \\10.250.0.1\mdt\Script\...     [導入]  │ │
│  └────────────────────────────────────────────────────┘ │
├─────────────────────────────────────────────────────────┤
│  當前 Inventory: 26_7F_new/inventory/hosts              │
│  狀態: ✅ 語法正確  |  Hosts: 15  |  Groups: 6  |  v3   │
│  [儲存] [驗證語法] [驗證配置] [版本歷史]                │
├─────────────────────────────────────────────────────────┤
│  ┌──────────────────────────────────────────────────┐  │
│  │  Monaco Editor (文本編輯器)                      │  │
│  │  ┌────────────────────────────────────────────┐  │  │
│  │  │ 1  [IOL_Linux]                             │  │  │
│  │  │ 2  PQ1_3_K14_01 ansible_host=10.250.53.83  │  │  │
│  │  │ 3                  ansible_user=root        │  │  │
│  │  │ 4                  mac_address=E8:...      │  │  │
│  │  │ 5                  uart_host=PC-SSD-6305   │  │  │
│  │  │ 6                                           │  │  │
│  │  │ 7  PQ1_3_K14_02 ansible_host=10.250.53.84  │  │  │
│  │  │ 8                  ...                     │  │  │
│  │  │ 9                                           │  │  │
│  │  │10  [SPVT_BAT_2]                            │  │  │
│  │  │...                                          │  │  │
│  │  └────────────────────────────────────────────┘  │  │
│  │  * 自動儲存草稿到 LocalStorage                   │  │
│  │  * 語法高亮顯示                                  │  │
│  │  * 行號顯示                                      │  │
│  │  * 錯誤標記（紅色波浪線）                        │  │
│  └──────────────────────────────────────────────────┘  │
├─────────────────────────────────────────────────────────┤
│  配置檢查結果（可選展開）                                │
│  ├─ ✅ PQ1_3_K14_01: 所有檢查通過                       │
│  ├─ ⚠️ PQ1_3_K14_02: UART SSH 無法連接                 │
│  └─ ❌ PQ1_3_K01_01: IP 地址無法 ping                  │
└─────────────────────────────────────────────────────────┘
```

### 組件設計（修訂版）

#### 1. ImportForm（導入表單）- 保持不變

```javascript
const ImportForm = () => {
    const [nasPath, setNasPath] = useState('');
    const [fileName, setFileName] = useState('hosts');
    const [loading, setLoading] = useState(false);
    
    const handleImport = async () => {
        setLoading(true);
        try {
            const response = await axios.post('/api/ansible-inventory/import/', {
                nas_path: nasPath,
                file_name: fileName
            });
            message.success(`成功導入 ${response.data.total_hosts} 台 Host`);
            // 跳轉到編輯頁面
        } catch (error) {
            message.error('導入失敗：' + error.response?.data?.error);
        } finally {
            setLoading(false);
        }
    };
    
    return (
        <Card title="導入 Ansible Inventory">
            <Form layout="vertical">
                <Form.Item label="NAS 路徑">
                    <Input
                        placeholder="\\10.250.0.1\mdt\Script\chunwei_test\26_7F_new\inventory"
                        value={nasPath}
                        onChange={(e) => setNasPath(e.target.value)}
                    />
                </Form.Item>
                <Form.Item label="檔案名稱">
                    <Input
                        value={fileName}
                        onChange={(e) => setFileName(e.target.value)}
                    />
                </Form.Item>
                <Form.Item>
                    <Button
                        type="primary"
                        onClick={handleImport}
                        loading={loading}
                        icon={<UploadOutlined />}
                    >
                        導入
                    </Button>
                </Form.Item>
            </Form>
        </Card>
    );
};
```

#### 2. InventoryFileEditor（文件編輯器）- **核心新組件**

```javascript
import Editor from '@monaco-editor/react';

const InventoryFileEditor = ({ inventoryId }) => {
    const [content, setContent] = useState('');
    const [originalContent, setOriginalContent] = useState('');
    const [loading, setLoading] = useState(false);
    const [saving, setSaving] = useState(false);
    const [syntaxValid, setSyntaxValid] = useState(true);
    const [syntaxError, setSyntaxError] = useState(null);
    const [hasChanges, setHasChanges] = useState(false);
    
    // 載入文件內容
    useEffect(() => {
        loadContent();
    }, [inventoryId]);
    
    const loadContent = async () => {
        setLoading(true);
        try {
            const response = await axios.get(
                `/api/ansible-inventory/${inventoryId}/content/`
            );
            setContent(response.data.content);
            setOriginalContent(response.data.content);
        } catch (error) {
            message.error('載入失敗：' + error.message);
        } finally {
            setLoading(false);
        }
    };
    
    // 內容變更處理
    const handleEditorChange = (value) => {
        setContent(value);
        setHasChanges(value !== originalContent);
        
        // 自動儲存草稿到 LocalStorage
        localStorage.setItem(`inventory_draft_${inventoryId}`, value);
        
        // 防抖驗證（1 秒後自動驗證）
        if (validateTimeoutRef.current) {
            clearTimeout(validateTimeoutRef.current);
        }
        validateTimeoutRef.current = setTimeout(() => {
            validateSyntax(value);
        }, 1000);
    };
    
    // 驗證語法
    const validateSyntax = async (contentToValidate = content) => {
        try {
            const response = await axios.post(
                '/api/ansible-inventory/validate-content/',
                { content: contentToValidate }
            );
            setSyntaxValid(response.data.syntax_valid);
            setSyntaxError(response.data.error_message);
        } catch (error) {
            setSyntaxValid(false);
            setSyntaxError('驗證失敗');
        }
    };
    
    // 儲存到 NAS
    const handleSave = async () => {
        // 先驗證語法
        await validateSyntax();
        
        if (!syntaxValid) {
            Modal.confirm({
                title: '語法錯誤',
                content: '目前內容存在語法錯誤，是否仍要儲存？',
                onOk: () => saveToNAS()
            });
            return;
        }
        
        saveToNAS();
    };
    
    const saveToNAS = async () => {
        setSaving(true);
        try {
            const response = await axios.post(
                `/api/ansible-inventory/${inventoryId}/update-content/`,
                {
                    content: content,
                    change_summary: `更新 Inventory 配置`
                }
            );
            
            message.success(`已儲存到 NAS (版本 ${response.data.version})`);
            setOriginalContent(content);
            setHasChanges(false);
            
            // 清除草稿
            localStorage.removeItem(`inventory_draft_${inventoryId}`);
            
        } catch (error) {
            message.error('儲存失敗：' + error.response?.data?.error);
        } finally {
            setSaving(false);
        }
    };
    
    // 復原草稿
    useEffect(() => {
        const draft = localStorage.getItem(`inventory_draft_${inventoryId}`);
        if (draft && draft !== originalContent) {
            Modal.confirm({
                title: '發現未儲存的草稿',
                content: '是否要恢復之前未儲存的編輯內容？',
                onOk: () => setContent(draft),
                onCancel: () => localStorage.removeItem(`inventory_draft_${inventoryId}`)
            });
        }
    }, [inventoryId]);
    
    return (
        <Card
            title="Inventory 文件編輯"
            extra={
                <Space>
                    {hasChanges && (
                        <Tag color="orange">未儲存</Tag>
                    )}
                    {syntaxValid ? (
                        <Tag color="success">語法正確</Tag>
                    ) : (
                        <Tag color="error">語法錯誤</Tag>
                    )}
                    <Button
                        onClick={() => validateSyntax()}
                        icon={<CheckCircleOutlined />}
                    >
                        驗證語法
                    </Button>
                    <Button
                        type="primary"
                        onClick={handleSave}
                        loading={saving}
                        disabled={!hasChanges}
                        icon={<SaveOutlined />}
                    >
                        儲存到 NAS
                    </Button>
                </Space>
            }
        >
            {syntaxError && (
                <Alert
                    message="語法錯誤"
                    description={syntaxError}
                    type="error"
                    closable
                    style={{ marginBottom: 16 }}
                />
            )}
            
            <Spin spinning={loading}>
                <Editor
                    height="600px"
                    defaultLanguage="ini"
                    value={content}
                    onChange={handleEditorChange}
                    theme="vs-light"
                    options={{
                        minimap: { enabled: true },
                        lineNumbers: 'on',
                        scrollBeyondLastLine: false,
                        fontSize: 14,
                        wordWrap: 'on',
                        automaticLayout: true
                    }}
                />
            </Spin>
        </Card>
    );
};
```

#### 3. InventoryInfoCard（統計資訊卡片）

```javascript
const InventoryInfoCard = ({ inventory }) => {
    return (
        <Card>
            <Row gutter={16}>
                <Col span={6}>
                    <Statistic
                        title="總 Hosts"
                        value={inventory.total_hosts}
                        prefix={<UserOutlined />}
                    />
                </Col>
                <Col span={6}>
                    <Statistic
                        title="總 Groups"
                        value={inventory.total_groups}
                        prefix={<TeamOutlined />}
                    />
                </Col>
                <Col span={6}>
                    <Statistic
                        title="當前版本"
                        value={`v${inventory.current_version}`}
                        prefix={<HistoryOutlined />}
                    />
                </Col>
                <Col span={6}>
                    {inventory.syntax_valid ? (
                        <Tag color="success" style={{ fontSize: 16, padding: '8px 16px' }}>
                            ✅ 語法正確
                        </Tag>
                    ) : (
                        <Tag color="error" style={{ fontSize: 16, padding: '8px 16px' }}>
                            ❌ 語法錯誤
                        </Tag>
                    )}
                </Col>
            </Row>
            
            <Divider />
            
            <Descriptions size="small" column={1}>
                <Descriptions.Item label="NAS 路徑">
                    {inventory.nas_path}/{inventory.file_name}
                </Descriptions.Item>
                <Descriptions.Item label="最後更新">
                    {new Date(inventory.updated_at).toLocaleString()}
                </Descriptions.Item>
            </Descriptions>
        </Card>
    );
};
```

#### 4. ValidationResultsPanel（配置檢查結果）

```javascript
const ValidationResultsPanel = ({ inventoryId }) => {
    const [validationResults, setValidationResults] = useState(null);
    const [loading, setLoading] = useState(false);
    
    const runValidation = async () => {
        setLoading(true);
        try {
            const response = await axios.post(
                `/api/ansible-inventory/${inventoryId}/validate/`,
                { validate_type: 'config' }
            );
            setValidationResults(response.data.validation_results);
            message.success('配置檢查完成');
        } catch (error) {
            message.error('檢查失敗：' + error.message);
        } finally {
            setLoading(false);
        }
    };
    
    return (
        <Card
            title="配置檢查結果"
            extra={
                <Button
                    onClick={runValidation}
                    loading={loading}
                    icon={<CheckCircleOutlined />}
                >
                    執行配置檢查
                </Button>
            }
        >
            {validationResults && (
                <>
                    <Row gutter={16} style={{ marginBottom: 16 }}>
                        <Col span={8}>
                            <Statistic
                                title="已檢查"
                                value={validationResults.hosts_checked}
                                suffix="台"
                            />
                        </Col>
                        <Col span={8}>
                            <Statistic
                                title="通過"
                                value={validationResults.hosts_passed}
                                valueStyle={{ color: '#3f8600' }}
                            />
                        </Col>
                        <Col span={8}>
                            <Statistic
                                title="失敗"
                                value={validationResults.hosts_failed}
                                valueStyle={{ color: '#cf1322' }}
                            />
                        </Col>
                    </Row>
                    
                    <List
                        dataSource={validationResults.details}
                        renderItem={item => (
                            <List.Item>
                                <List.Item.Meta
                                    avatar={
                                        item.status === 'passed' ? (
                                            <CheckCircleOutlined style={{ color: '#52c41a', fontSize: 24 }} />
                                        ) : (
                                            <CloseCircleOutlined style={{ color: '#ff4d4f', fontSize: 24 }} />
                                        )
                                    }
                                    title={item.hostname}
                                    description={
                                        <Space>
                                            {Object.entries(item.checks).map(([key, value]) => (
                                                <Tag
                                                    key={key}
                                                    color={value.status === 'passed' ? 'success' : 'error'}
                                                >
                                                    {key}: {value.status}
                                                </Tag>
                                            ))}
                                        </Space>
                                    }
                                />
                            </List.Item>
                        )}
                    />
                </>
            )}
        </Card>
    );
};
```

---

## 📝 使用流程（修訂版：文本編輯模式）

### 完整操作流程

```
1. 使用者導入 Inventory
   ├─ 輸入 NAS 路徑
   ├─ 點擊「導入」
   └─ 系統驗證語法並解析統計資訊

2. 查看 Inventory 資訊
   ├─ 顯示統計資訊（總 Hosts、總 Groups、版本號）
   ├─ 顯示語法驗證狀態
   └─ 準備進入編輯模式

3. 使用文本編輯器編輯 hosts 文件
   ├─ Monaco Editor 載入文件內容
   ├─ 語法高亮顯示（INI 格式）
   ├─ 直接編輯整份文件內容
   │   ├─ 修改 Host 配置
   │   ├─ 添加/刪除 Hosts
   │   ├─ 調整 Groups
   │   └─ 修改變數
   ├─ 自動儲存草稿到 LocalStorage
   ├─ 實時語法驗證（1 秒防抖）
   └─ 顯示語法錯誤標記

4. 驗證編輯內容
   ├─ 自動驗證：編輯後 1 秒自動觸發
   ├─ 手動驗證：點擊「驗證語法」按鈕
   ├─ 顯示驗證結果（語法正確/錯誤）
   └─ 如有錯誤，顯示錯誤訊息和行號

5. 儲存到 NAS
   ├─ 點擊「儲存到 NAS」按鈕
   ├─ 系統最終驗證語法
   ├─ 如語法錯誤，提示確認是否仍要儲存
   ├─ 系統自動創建備份
   ├─ 寫入 NAS 覆蓋原始檔案
   ├─ 重新解析並更新資料庫
   ├─ 創建版本記錄
   └─ 清除 LocalStorage 草稿

6. 配置檢查（可選）
   ├─ 點擊「驗證配置」按鈕
   ├─ 系統對每台 Host 進行檢查
   │   ├─ IP 地址 ping 測試
   │   ├─ MAC 地址格式驗證
   │   └─ UART SSH 連接測試
   ├─ 顯示檢查結果列表
   └─ 標記通過/失敗/警告狀態

7. 版本管理
   ├─ 查看版本歷史
   ├─ 選擇特定版本回滾
   ├─ 系統自動備份當前版本
   ├─ 從備份文件恢復內容
   └─ 重新載入文本編輯器

8. 草稿恢復
   ├─ 重新開啟頁面時檢查 LocalStorage
   ├─ 如發現未儲存的草稿
   ├─ 提示使用者是否恢復
   └─ 恢復或丟棄草稿
```

### 主要差異對比

#### ❌ 舊設計（表單模式）
- 逐台 Host 編輯（使用 Drawer/Modal 表單）
- 先儲存到資料庫，最後一次性寫入 NAS
- 需要多次點擊「編輯」按鈕
- 編輯鎖定機制

#### ✅ 新設計（文本編輯模式）
- 直接編輯整份 hosts 文件（使用 Monaco Editor）
- 編輯完成後直接寫入 NAS
- 一次性完成所有修改
- 自動草稿儲存，防止意外丟失
- 實時語法驗證，即時錯誤提示
- 更接近傳統文本編輯器體驗

---

## 🚀 開發階段規劃（修訂版）

### 階段 1：基礎導入和顯示（✅ 已完成）

**目標**：實現從 NAS 導入並顯示統計資訊

- [x] 創建資料庫 Models
- [x] 實現 `AnsibleInventoryService` 基礎方法
  - [x] `convert_windows_path_to_linux()`
  - [x] `validate_syntax()`
  - [x] `parse_inventory()`
- [x] 實現導入 API
- [x] 前端導入表單
- [x] 前端統計資訊顯示

**交付物**：
- ✅ 可以導入 Inventory 並在網頁上查看統計資訊
- ✅ 成功測試：21 台 Host，10 個 Groups

---

### 階段 2：文本編輯器實現（⏳ 進行中）

**目標**：實現文本編輯器和內容管理

**後端開發**：
- [ ] 實現新 API 端點
  - [ ] `GET /api/ansible-inventory/<id>/content/` - 獲取文件內容
  - [ ] `POST /api/ansible-inventory/<id>/update-content/` - 更新文件內容
  - [ ] `POST /api/ansible-inventory/validate-content/` - 驗證內容語法
- [ ] 擴展 `AnsibleInventoryService`
  - [ ] `get_file_content()` - 讀取文件
  - [ ] `update_file_content()` - 更新文件
  - [ ] `validate_content_syntax()` - 驗證語法

**前端開發**：
- [ ] 安裝 `@monaco-editor/react`
- [ ] 實現 `InventoryFileEditor` 組件
  - [ ] Monaco Editor 整合
  - [ ] 語法高亮（INI 格式）
  - [ ] 行號顯示
  - [ ] 實時語法驗證（1 秒防抖）
  - [ ] 錯誤標記顯示
- [ ] 實現草稿儲存機制
  - [ ] 自動儲存到 LocalStorage
  - [ ] 頁面重載時恢復草稿
  - [ ] 儲存成功後清除草稿
- [ ] 實現儲存功能
  - [ ] 儲存前語法驗證
  - [ ] 錯誤確認對話框
  - [ ] 儲存進度提示
- [ ] 更新主頁面佈局
  - [ ] 移除 Host 列表 Table
  - [ ] 添加文本編輯器區域
  - [ ] 統計資訊卡片優化

**交付物**：
- 可以使用文本編輯器直接編輯 hosts 文件
- 實時語法驗證和錯誤提示
- 自動草稿儲存，防止意外丟失
- 儲存到 NAS 並自動備份

**預計時間**：2-3 天

---

### 階段 3：配置驗證（2-3 天）

**目標**：實現配置檢查功能

- [ ] 保留現有配置檢查功能
- [ ] 實現 `InventoryConfigValidator` 服務
- [ ] 實現 IP/MAC/UART SSH 檢查
- [ ] 實現驗證 API
- [ ] 前端 `ValidationResultsPanel` 組件
  - [ ] 顯示檢查統計
  - [ ] 顯示每台 Host 的檢查結果
  - [ ] 失敗項目詳細訊息
- [ ] 前端批次驗證功能

**交付物**：
- 可以對 Host 配置進行完整檢查
- 顯示檢查結果和錯誤訊息
- 區分 IP、MAC、UART 各項檢查狀態

---

### 階段 4：版本管理優化（1-2 天）

**目標**：完善版本控制和回滾功能

- [x] 實現自動備份機制（已有基礎實現）
- [x] 實現版本記錄（已有 Model）
- [ ] 實現版本歷史 API
- [ ] 實現回滾功能 API
- [ ] 前端版本歷史頁面
  - [ ] 版本列表顯示
  - [ ] 版本差異對比
  - [ ] 回滾確認對話框
- [ ] 實現備份清理機制

**交付物**：
- 可以查看版本歷史
- 可以對比版本差異
- 可以回滾到特定版本
- 自動清理過期備份

---

### 階段 5：優化和測試（1-2 天）

**目標**：優化性能和用戶體驗

- [ ] 編輯器性能優化
  - [ ] 大文件載入優化
  - [ ] 語法驗證防抖優化
- [ ] 錯誤處理完善
  - [ ] 網路錯誤處理
  - [ ] 檔案權限錯誤處理
  - [ ] 並發編輯衝突處理
- [ ] 使用者體驗優化
  - [ ] 快捷鍵支援（Ctrl+S 儲存）
  - [ ] 搜尋/替換功能
  - [ ] Undo/Redo 支援
  - [ ] 暗色主題選項
- [ ] 編寫測試用例
  - [ ] 後端 API 測試
  - [ ] 前端組件測試
  - [ ] 整合測試
- [ ] 編寫使用文檔

**交付物**：
- 完整的功能和文檔
- 穩定可用的系統
- 良好的使用者體驗

---

## 📖 相關文檔

### 待創建的文檔

- `API_REFERENCE.md` - API 詳細說明
- `USER_GUIDE.md` - 使用者操作手冊
- `DEVELOPER_GUIDE.md` - 開發者文檔
- `TROUBLESHOOTING.md` - 故障排查指南

---

## ❓ 待確認問題（更新版）

1. **編輯器功能**：
   - ✅ 使用 Monaco Editor 進行文本編輯（已確認）
   - 是否需要支援 Vim/Emacs 快捷鍵模式？
   - 是否需要代碼折疊功能？

2. **語法驗證**：
   - ✅ 實時驗證（1 秒防抖）（已確認）
   - 語法錯誤時是否允許強制儲存？（建議：提示確認但允許）

3. **草稿儲存**：
   - ✅ 自動儲存到 LocalStorage（已確認）
   - 草稿保留時間：建議 7 天，是否合適？
   - 是否需要雲端草稿同步（多裝置）？

4. **版本管理**：
   - ✅ 保留 30 個版本（已確認）
   - 是否需要版本差異對比視圖（類似 Git diff）？
   - 是否需要版本標籤/註釋功能？

5. **配置檢查**：
   - 除了 IP、MAC、UART SSH，還需要檢查其他項目嗎？
   - 檢查失敗時是否需要阻止儲存？

6. **權限控制**：
   - 是否需要實現不同角色的權限控制？
   - 編輯衝突處理：如何處理多人同時編輯？

7. **批次操作**：
   - 是否需要批次修改功能（例如：批次替換 IP 段）？
   - 是否需要匯出/匯入功能（Excel、CSV）？

8. **進階功能**（未來擴展）：
   - 是否需要整合 Ansible 執行功能（直接在網頁執行 Playbook）？
   - 是否需要變數庫管理（集中管理常用變數）？

---

## 📋 設計變更記錄

### 2025-11-18（第二版）
- **重大變更**：從表單模式改為文本編輯器模式
- **原因**：使用者需求為編輯整份 hosts 文件，而非逐台 Host 編輯
- **變更內容**：
  1. 前端 UI 從 Table + Drawer 改為 Monaco Editor
  2. API 端點調整：
     - 新增 `GET /content/` 獲取文件內容
     - 新增 `POST /update-content/` 更新文件內容
     - 新增 `POST /validate-content/` 驗證內容語法
     - 保留 `GET /hosts/` 用於配置檢查結果顯示
     - 移除 `PATCH /hosts/<hostname>/` 單個 Host 編輯
  3. Service 方法調整：
     - 新增 `get_file_content()`
     - 新增 `update_file_content()`
     - 新增 `validate_content_syntax()`
  4. 工作流程簡化：導入 → 編輯文本 → 驗證 → 儲存
  5. 新增草稿儲存機制（LocalStorage）

### 2025-11-18（第一版）
- 初始設計：表單模式
- 設計思路：類似 Build 配置檢查的逐台編輯模式
- **問題**：不符合使用者實際需求

---

**文檔創建日期**：2025-11-18  
**最後更新**：2025-11-18  
**設計者**：GitHub Copilot  
**狀態**：階段 1 已完成，階段 2 規劃中，等待實現確認


