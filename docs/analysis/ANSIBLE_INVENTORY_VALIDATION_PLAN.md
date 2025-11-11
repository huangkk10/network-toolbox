# Ansible Inventory 配置檢查機制規劃

## 📋 配置文件分析

### 文件路徑
```
\\10.250.0.1\mdt\Team\PQ1-3\tool\jenkins_test_storage\10.252.170.171\Test-KVM01\148\artifacts\inventory\hosts
```

### 文件結構分析

#### 1. **Host Groups（主機群組）**
```ini
[IOL_Linux]
[PQ1_3]
[PQ1_3_K14]
[PQ1_3_K14_DEV]
[PQ1_3_K01]
[SPVT_BAT_2]
[PQ1_3_MANDi]
[uart]
[local]
```

#### 2. **Group Variables（群組變數）**
```ini
[IOL_Linux:vars]
[PQ1_3:vars]
[PQ1_3_K14:vars]
[PQ1_3_K14_DEV:vars]
[PQ1_3_K01:vars]
[SPVT_BAT_2:vars]
[PQ1_3_MANDi:vars]
[uart:vars]
[all:vars]
[compatibility_test:vars]
```

#### 3. **Group Hierarchy（群組層級）**
```ini
[compatibility_test:children]
PQ1_3
PQ1_3_K01
PQ1_3_K14
PQ1_3_MANDi
IOL_Linux
```

#### 4. **Host Entries（主機條目）**
典型格式：
```ini
Test-KVM01 ansible_host=10.250.71.22 device_number=PC-SSD-4632 sample_number=SM2703AB-02003 uart_id=KVM01 macaddress=CC:28:AA:86:C3:7F testcase_set=testcases_demo
```

---

## 🔍 發現的配置問題

### 1. **格式問題**
- ❌ 長行未換行（超過 120 字符）
- ❌ 註釋行混雜（`;` 開頭的註釋行）
- ❌ 重複的變數定義（如 `testcase_set` 在同一行出現兩次）
- ❌ 路徑格式不一致：
  - Windows 路徑：`\\10.250.0.1\mdt\...`
  - 轉義路徑：`\\\\\\\\10.250.0.1\\\\mdt\\\\...`

### 2. **潛在的邏輯問題**
- ⚠️ Host 重複定義（Test-KVM01 有多個註釋行）
- ⚠️ 變數覆蓋（群組變數 vs 主機變數）
- ⚠️ IP 地址衝突（同一 IP 被多個主機使用）
- ⚠️ 必填欄位缺失（某些 host 缺少 `ansible_host`）

### 3. **安全問題**
- 🔒 明文密碼（`ansible_password=1.a`）
- 🔒 NAS 憑證明文（`nas_password=p@ssw0rd`）

---

## 🎯 檢查機制方案

### 方案 A：使用 Ansible 內建工具檢查 ✅ **推薦**

#### 優點
- ✅ 官方工具，準確性高
- ✅ 可以驗證語法正確性
- ✅ 可以檢查變數解析
- ✅ 可以列出所有主機和變數

#### 工具列表

1. **ansible-inventory**
   ```bash
   # 檢查語法並輸出解析後的 inventory
   ansible-inventory -i hosts --list
   ansible-inventory -i hosts --graph
   
   # 檢查特定主機的變數
   ansible-inventory -i hosts --host Test-KVM01
   ```

2. **ansible-playbook --syntax-check**
   ```bash
   # 需要配合簡單的 playbook 檢查
   ansible-playbook -i hosts check_syntax.yml --syntax-check
   ```

3. **ansible-lint** (需要安裝)
   ```bash
   # 檢查最佳實踐
   ansible-lint hosts
   ```

#### 檢查流程
```
1. ansible-inventory --list
   ↓
2. 檢查是否有錯誤輸出
   ↓
3. 驗證主機數量、群組結構
   ↓
4. 檢查變數解析是否正確
```

---

### 方案 B：使用 Python + configparser 檢查

#### 優點
- ✅ 可以自定義檢查規則
- ✅ 可以集成到現有系統
- ✅ 可以生成詳細報告
- ✅ 不需要 Ansible 環境

#### Python 庫選擇
```python
# 選項 1: configparser (標準庫)
import configparser

# 選項 2: ansible.parsing (Ansible SDK)
from ansible.parsing.dataloader import DataLoader
from ansible.inventory.manager import InventoryManager

# 選項 3: 正則表達式 + 自定義解析
import re
```

#### 檢查項目
```python
checks = {
    "syntax": [
        "check_section_format",      # [group_name] 格式
        "check_host_format",          # hostname key=value 格式
        "check_variables_format",     # key=value 格式
    ],
    "logic": [
        "check_duplicate_hosts",      # 重複主機名
        "check_ip_conflicts",         # IP 衝突
        "check_required_fields",      # 必填欄位
        "check_variable_override",    # 變數覆蓋
    ],
    "best_practice": [
        "check_line_length",          # 行長度
        "check_password_plain_text",  # 明文密碼
        "check_path_format",          # 路徑格式一致性
    ]
}
```

---

### 方案 C：混合方案（最佳） ⭐

結合 Ansible 工具 + Python 自定義檢查

```
Step 1: Ansible 語法檢查
  └─> ansible-inventory --list (JSON 輸出)
       ↓
Step 2: Python 解析 JSON
  └─> 提取主機、群組、變數
       ↓
Step 3: 自定義規則檢查
  ├─> IP 衝突檢查
  ├─> 必填欄位檢查
  ├─> 路徑格式檢查
  └─> 安全性檢查
       ↓
Step 4: 生成檢查報告
  └─> 儲存到資料庫 / 文件
```

---

## 📊 詳細檢查規則設計

### 1. 語法檢查（Syntax Check）

```yaml
syntax_rules:
  - name: "Section Format"
    pattern: '^\[[\w_]+(:vars|:children)?\]$'
    error: "Invalid section name format"
    
  - name: "Host Entry Format"
    pattern: '^[\w\-_]+ ([\w_]+=[\S]+\s*)+$'
    error: "Invalid host entry format"
    
  - name: "Comment Format"
    pattern: '^;.*$'
    warning: "Use # for comments instead of ;"
```

### 2. 邏輯檢查（Logic Check）

```python
logic_checks = {
    "duplicate_hosts": {
        "description": "檢查重複的主機名",
        "severity": "ERROR",
        "action": lambda hosts: len(hosts) != len(set(hosts))
    },
    
    "ip_conflicts": {
        "description": "檢查 IP 衝突（同一 IP 被多個主機使用）",
        "severity": "ERROR",
        "action": check_ip_conflicts
    },
    
    "required_fields": {
        "description": "檢查必填欄位",
        "required": ["ansible_host", "device_number", "sample_number"],
        "severity": "WARNING"
    },
    
    "variable_override": {
        "description": "檢查變數覆蓋（主機變數覆蓋群組變數）",
        "severity": "INFO"
    }
}
```

### 3. 最佳實踐檢查（Best Practice Check）

```python
best_practice_checks = {
    "line_length": {
        "max_length": 120,
        "severity": "WARNING"
    },
    
    "password_security": {
        "patterns": [r'password=\S+', r'nas_password=\S+'],
        "severity": "CRITICAL",
        "message": "明文密碼不安全，建議使用 Ansible Vault"
    },
    
    "path_format": {
        "description": "路徑格式應一致使用 \\\\ 或 /",
        "severity": "WARNING"
    },
    
    "comment_style": {
        "preferred": "#",
        "deprecated": ";",
        "severity": "INFO"
    }
}
```

---

## 🛠️ 實現架構

### 選項 1: 命令行工具

```bash
# 使用方式
python check_ansible_inventory.py \
    --inventory /path/to/hosts \
    --output report.json \
    --verbose

# 輸出
✓ Syntax Check: PASSED
✗ Logic Check: FAILED (2 errors)
  - Duplicate host: Test-KVM01
  - IP conflict: 10.250.71.22 used by 2 hosts
⚠ Best Practice: WARNING (3 warnings)
  - Line too long: line 45 (156 chars)
  - Plain text password found: line 23
  - Inconsistent path format: line 67
```

### 選項 2: Django API 集成

```python
# API Endpoint
POST /api/jenkins-builds/{build_id}/validate_inventory/

# Request
{
    "inventory_path": "artifacts/inventory/hosts",
    "check_types": ["syntax", "logic", "best_practice"],
    "severity_threshold": "WARNING"
}

# Response
{
    "success": true,
    "build_id": 1048,
    "inventory_path": "...",
    "validation_result": {
        "overall_status": "WARNING",
        "checks_passed": 15,
        "checks_failed": 2,
        "checks_warning": 3,
        "errors": [...],
        "warnings": [...],
        "info": [...]
    },
    "timestamp": "2025-11-10T15:30:00Z"
}
```

### 選項 3: Celery 定期檢查

```python
@shared_task
def validate_jenkins_build_inventory(build_id):
    """
    自動檢查 Jenkins Build 的 Ansible Inventory
    
    觸發時機：
    1. Build Artifacts 存儲完成後
    2. 定期掃描（每天一次）
    """
    build = JenkinsBuild.objects.get(id=build_id)
    inventory_path = os.path.join(
        build.artifacts_path,
        'inventory/hosts'
    )
    
    if not os.path.exists(inventory_path):
        return {"status": "skipped", "reason": "No inventory file"}
    
    # 執行檢查
    validator = AnsibleInventoryValidator(inventory_path)
    result = validator.validate_all()
    
    # 儲存結果到資料庫
    InventoryValidation.objects.create(
        build=build,
        validation_result=result,
        status=result['overall_status']
    )
    
    return result
```

---

## 📦 檢查工具實現細節

### 1. 使用 Ansible 原生檢查

```python
import subprocess
import json

class AnsibleInventoryChecker:
    def __init__(self, inventory_path):
        self.inventory_path = inventory_path
    
    def check_syntax(self):
        """使用 ansible-inventory 檢查語法"""
        cmd = [
            'ansible-inventory',
            '-i', self.inventory_path,
            '--list',
            '--export'
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
                    "status": "FAILED",
                    "error": result.stderr
                }
            
            # 解析 JSON 輸出
            inventory_data = json.loads(result.stdout)
            
            return {
                "status": "PASSED",
                "data": inventory_data,
                "hosts_count": len(inventory_data.get('_meta', {}).get('hostvars', {})),
                "groups_count": len([k for k in inventory_data.keys() if k != '_meta'])
            }
            
        except subprocess.TimeoutExpired:
            return {"status": "FAILED", "error": "Command timeout"}
        except json.JSONDecodeError as e:
            return {"status": "FAILED", "error": f"Invalid JSON output: {e}"}
        except Exception as e:
            return {"status": "FAILED", "error": str(e)}
    
    def get_host_vars(self, hostname):
        """獲取特定主機的所有變數"""
        cmd = [
            'ansible-inventory',
            '-i', self.inventory_path,
            '--host', hostname
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            return json.loads(result.stdout)
        return None
    
    def list_all_hosts(self):
        """列出所有主機"""
        cmd = [
            'ansible-inventory',
            '-i', self.inventory_path,
            '--list',
            '--export'
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            data = json.loads(result.stdout)
            return list(data.get('_meta', {}).get('hostvars', {}).keys())
        return []
```

### 2. 自定義 Python 檢查器

```python
import re
from typing import List, Dict, Any

class CustomInventoryValidator:
    def __init__(self, inventory_path):
        self.inventory_path = inventory_path
        self.errors = []
        self.warnings = []
        self.info = []
    
    def validate(self):
        """執行所有檢查"""
        with open(self.inventory_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        self.check_line_length(lines)
        self.check_ip_conflicts(lines)
        self.check_plain_text_passwords(lines)
        self.check_path_format(lines)
        self.check_duplicate_hosts(lines)
        
        return {
            "errors": self.errors,
            "warnings": self.warnings,
            "info": self.info,
            "overall_status": self._get_overall_status()
        }
    
    def check_line_length(self, lines, max_length=120):
        """檢查行長度"""
        for i, line in enumerate(lines, 1):
            if len(line.strip()) > max_length:
                self.warnings.append({
                    "type": "line_length",
                    "line": i,
                    "length": len(line.strip()),
                    "max_length": max_length,
                    "message": f"Line {i} is too long ({len(line.strip())} > {max_length})"
                })
    
    def check_ip_conflicts(self, lines):
        """檢查 IP 衝突"""
        ip_pattern = r'ansible_host=([\d.]+)'
        ip_hosts = {}
        
        for i, line in enumerate(lines, 1):
            match = re.search(ip_pattern, line)
            if match:
                ip = match.group(1)
                hostname = line.split()[0] if line.strip() and not line.strip().startswith('[') else None
                
                if hostname:
                    if ip in ip_hosts:
                        self.errors.append({
                            "type": "ip_conflict",
                            "line": i,
                            "ip": ip,
                            "hosts": [ip_hosts[ip], hostname],
                            "message": f"IP {ip} is used by multiple hosts: {ip_hosts[ip]}, {hostname}"
                        })
                    else:
                        ip_hosts[ip] = hostname
    
    def check_plain_text_passwords(self, lines):
        """檢查明文密碼"""
        password_patterns = [
            r'ansible_password=\S+',
            r'nas_password=\S+',
            r'password=\S+'
        ]
        
        for i, line in enumerate(lines, 1):
            for pattern in password_patterns:
                if re.search(pattern, line):
                    self.errors.append({
                        "type": "security",
                        "severity": "CRITICAL",
                        "line": i,
                        "message": f"Plain text password found on line {i}. Use Ansible Vault instead."
                    })
    
    def check_path_format(self, lines):
        """檢查路徑格式一致性"""
        windows_path_pattern = r'\\\\[\d.]+\\[\w\\]+'
        escaped_path_pattern = r'\\\\\\\\[\d.]+\\\\[\w\\]+'
        
        for i, line in enumerate(lines, 1):
            if re.search(windows_path_pattern, line) and re.search(escaped_path_pattern, line):
                self.warnings.append({
                    "type": "path_format",
                    "line": i,
                    "message": f"Inconsistent path format on line {i}"
                })
    
    def check_duplicate_hosts(self, lines):
        """檢查重複的主機定義"""
        hosts = []
        for i, line in enumerate(lines, 1):
            line = line.strip()
            if line and not line.startswith('[') and not line.startswith(';') and not line.startswith('#'):
                hostname = line.split()[0]
                if hostname in hosts:
                    self.errors.append({
                        "type": "duplicate_host",
                        "line": i,
                        "hostname": hostname,
                        "message": f"Duplicate host definition: {hostname}"
                    })
                hosts.append(hostname)
    
    def _get_overall_status(self):
        """計算整體狀態"""
        if self.errors:
            return "FAILED"
        elif self.warnings:
            return "WARNING"
        else:
            return "PASSED"
```

---

## 🗄️ 資料庫設計

### 新增 Model: InventoryValidation

```python
class InventoryValidation(models.Model):
    """Ansible Inventory 驗證結果"""
    
    build = models.ForeignKey(
        'JenkinsBuild',
        on_delete=models.CASCADE,
        related_name='inventory_validations'
    )
    
    inventory_path = models.CharField(
        max_length=1000,
        help_text='Inventory 文件路徑'
    )
    
    status = models.CharField(
        max_length=20,
        choices=[
            ('PASSED', '通過'),
            ('WARNING', '警告'),
            ('FAILED', '失敗'),
            ('SKIPPED', '跳過'),
        ],
        default='PASSED'
    )
    
    validation_result = models.JSONField(
        default=dict,
        help_text='驗證結果 JSON'
    )
    
    # 統計資訊
    checks_total = models.IntegerField(default=0)
    checks_passed = models.IntegerField(default=0)
    checks_failed = models.IntegerField(default=0)
    checks_warning = models.IntegerField(default=0)
    
    # 錯誤和警告
    errors = models.JSONField(default=list)
    warnings = models.JSONField(default=list)
    info = models.JSONField(default=list)
    
    # 時間戳
    validated_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'inventory_validation'
        ordering = ['-validated_at']
        indexes = [
            models.Index(fields=['build', 'status']),
            models.Index(fields=['validated_at']),
        ]
```

---

## 🎨 前端展示

### Dashboard 展示

```
╭─────────────────────────────────────────────────────────╮
│  Build #148 - Inventory Validation                     │
├─────────────────────────────────────────────────────────┤
│  Status: ⚠️ WARNING                                     │
│  Validated: 2025-11-10 15:30:00                         │
│                                                         │
│  Summary:                                               │
│    ✅ Checks Passed: 15                                 │
│    ❌ Checks Failed: 2                                  │
│    ⚠️  Warnings: 3                                      │
│                                                         │
│  Errors:                                                │
│    🔴 [Line 23] IP conflict: 10.250.71.22              │
│    🔴 [Line 45] Plain text password found              │
│                                                         │
│  Warnings:                                              │
│    🟡 [Line 67] Line too long (156 chars)              │
│    🟡 [Line 89] Inconsistent path format               │
│    🟡 [Line 123] Use # for comments instead of ;       │
╰─────────────────────────────────────────────────────────╯
```

---

## 📝 建議實施步驟

### Phase 1: 基礎檢查（1-2 天）
1. ✅ 實現 `ansible-inventory` 語法檢查
2. ✅ 建立基本的 Python 檢查器
3. ✅ 建立命令行工具測試

### Phase 2: API 集成（2-3 天）
1. ✅ 建立 Django Model (`InventoryValidation`)
2. ✅ 建立 API Endpoint
3. ✅ 與 Artifacts 存儲流程集成

### Phase 3: 自動化（1-2 天）
1. ✅ 建立 Celery Task
2. ✅ 在 Artifacts 存儲後自動觸發
3. ✅ 建立定期掃描任務

### Phase 4: 前端展示（2-3 天）
1. ✅ 在 Build 詳情頁面顯示驗證結果
2. ✅ 建立驗證報告頁面
3. ✅ 建立統計圖表

---

## ❓ 需要確認的問題

### 1. 檢查方式選擇
- ✅ **方案 A**: 純 Ansible 工具（簡單、快速）
- ⭐ **方案 C**: Ansible + Python（推薦、靈活）
- ❓ 您偏好哪種方案？

### 2. 觸發時機
- ⬜ Artifacts 存儲完成後自動檢查
- ⬜ 手動觸發檢查
- ⬜ 定期掃描（每天一次）
- ❓ 您希望何時觸發檢查？

### 3. 檢查嚴格程度
- ⬜ 寬鬆模式（只報告錯誤）
- ⬜ 標準模式（報告錯誤 + 警告）
- ⬜ 嚴格模式（報告錯誤 + 警告 + 建議）
- ❓ 您需要多嚴格的檢查？

### 4. 報告格式
- ⬜ JSON 文件
- ⬜ HTML 報告
- ⬜ 儲存到資料庫
- ⬜ Email 通知
- ❓ 您需要什麼格式的報告？

### 5. 是否需要 Ansible 環境
- ❓ 系統中是否已安裝 Ansible？
- ❓ 是否可以在 Docker 容器中安裝 Ansible？
- ❓ 或者只使用 Python 自定義檢查器？

---

## 🎯 下一步

請確認：
1. ✅ 選擇檢查方案（A / C）
2. ✅ 確認觸發時機
3. ✅ 確認檢查嚴格程度
4. ✅ 確認是否安裝 Ansible

確認後，我會開始實現檢查機制！🚀
