# Ansible Inventory 配置檢查功能 - 規劃文檔

> **狀態**: 📋 規劃階段（尚未實施）  
> **創建日期**: 2025-11-18  
> **仿效對象**: Jenkins Build 配置檢查功能  
> **目標**: 在 Ansible Inventory 頁面的右側邊欄提供配置驗證功能

---

## 📑 目錄

- [功能概述](#功能概述)
- [參考實現分析](#參考實現分析)
- [驗證項目設計](#驗證項目設計)
- [UI/UX 設計](#uiux-設計)
- [後端架構設計](#後端架構設計)
- [前端架構設計](#前端架構設計)
- [API 設計](#api-設計)
- [實施階段規劃](#實施階段規劃)
- [技術考量](#技術考量)

---

## 功能概述

### 目標

為 Ansible Inventory Manager 添加配置檢查功能，類似於 Jenkins Build 的「檢查配置」功能，提供逐項驗證和結果展示。

### 使用場景

1. **配置完整性檢查**: 導入或編輯 Inventory 後，驗證配置是否完整
2. **語法驗證**: 檢查 INI 格式、變數語法、Jinja2 模板
3. **網路連線測試**: 驗證主機 IP 可達性、SSH 連線
4. **資料一致性**: 檢查 IP 衝突、重複 MAC 地址、變數遺漏
5. **自動修正建議**: 提供錯誤修復建議

### 核心特性

- ✅ **逐項檢查**: 一個個顯示檢查進度（類似 Jenkins Build）
- ✅ **右側抽屜**: 點擊按鈕從右側彈出檢查面板
- ✅ **實時反饋**: 每個檢查項目顯示 ✓/⚠/✗ 狀態
- ✅ **詳細信息**: 展開查看錯誤詳情和建議
- ✅ **智能展開**: 錯誤/警告項目自動展開
- ✅ **報告導出**: 支援匯出 JSON/PDF 檢查報告

---

## 參考實現分析

### Jenkins Build 配置檢查功能

#### 現有實現路徑

**前端組件**:
- `frontend/src/pages/BuildConfigValidatorPage.js` (650 行)
- 從 RVT Analytics Build 列表點擊「檢查配置」按鈕進入

**後端服務**:
- `library/services/build_config_validator.py` (766 行)
- 驗證 HOST_IP, HOST_MAC, UART_IP, UART_SSH

**API 端點**:
- `POST /api/jenkins-builds/{buildId}/validate_config/`

#### UI 特性分析

```javascript
// 1. 檢查總覽卡片
<Card title="📋 檢查總覽">
    <Row gutter={[16, 16]}>
        <Col>Build ID, Job 名稱, 配置來源</Col>
        <Col>整體狀態, 進度條, 通過率</Col>
        <Col>重新檢查, 導出報告按鈕</Col>
    </Row>
</Card>

// 2. 檢查項目列表（使用 Collapse）
<Collapse activeKey={expandedPanels}>
    {Object.entries(checks).map(([key, checkData]) => (
        <Panel
            header={
                <Space>
                    <Checkbox checked={isSuccess} disabled />
                    <Text>檢查項目名稱</Text>
                    <Tag>狀態標籤</Tag>
                    <Icon>狀態圖標</Icon>
                </Space>
            }
            style={{
                backgroundColor: hasError ? '#fff1f0' : '#f6ffed',
                border: hasError ? '1px solid #ffccc7' : '1px solid #b7eb8f'
            }}
        >
            <Descriptions>檢查值, 狀態訊息</Descriptions>
            <Divider>詳細資訊</Divider>
            <Descriptions>詳細數據</Descriptions>
            <Divider>建議</Divider>
            <ul>建議列表</ul>
        </Panel>
    ))}
</Collapse>
```

#### 檢查邏輯流程

```python
class BuildConfigValidator:
    def validate(self) -> Dict:
        """執行完整驗證流程"""
        # 1. 載入 Build 資料
        self._load_build()
        
        # 2. 解析配置（從 Ansible Inventory API）
        self._parse_config()
        
        # 3. 確定 DHCP Server
        self._determine_dhcp_servers()
        
        # 4. 逐項檢查（4 個檢查項目）
        self._check_host_ip()
        self._check_host_mac()
        self._check_uart_ip()
        self._check_uart_ssh_connection()
        
        # 5. 計算總體狀態
        self._calculate_overall_status()
        
        return self.validation_results
```

#### 返回資料結構

```json
{
    "overall_status": "success|warning|error",
    "config_source": "ansible_inventory|database",
    "build_result": "SUCCESS|FAILURE",
    "auto_triggered": false,
    "checks": {
        "host_ip": {
            "status": "success|warning|error|unknown",
            "message": "檢查結果描述",
            "value": "192.168.1.100",
            "details": {
                "dhcp_record_ip": "192.168.1.100",
                "matches": true,
                "dhcp_server": "Server 1"
            },
            "suggestions": [
                "建議 1",
                "建議 2"
            ]
        }
    },
    "summary": {
        "total_checks": 4,
        "passed": 3,
        "warnings": 1,
        "errors": 0
    }
}
```

---

## 驗證項目設計

### 階段 1: 基礎驗證（必須）

#### 1. 語法驗證 (Syntax Validation)

**檢查內容**:
- ✅ INI 格式正確性
- ✅ Section 語法（`[group_name]`）
- ✅ 變數賦值語法（`key=value`）
- ✅ Jinja2 模板語法（`{{ variable }}`）
- ✅ 特殊字元轉義

**狀態判定**:
- ✅ **成功**: 無語法錯誤
- ⚠ **警告**: 有潛在問題（如註釋格式不規範）
- ✗ **錯誤**: 無法解析的語法錯誤

**實現**:
```python
def _check_syntax(self):
    """檢查 INI 語法"""
    try:
        from library.utils.enhanced_ini_validator import validate_ini_content
        
        result = validate_ini_content(self.inventory_content)
        
        if result['valid']:
            return {
                'status': 'success',
                'message': '語法檢查通過',
                'value': f"{result['line_count']} 行",
                'details': {
                    'sections': len(result['sections']),
                    'variables': len(result['variables']),
                    'hosts': len(result['hosts'])
                },
                'suggestions': []
            }
        else:
            return {
                'status': 'error',
                'message': '發現語法錯誤',
                'value': f"{len(result['errors'])} 個錯誤",
                'details': {'errors': result['errors']},
                'suggestions': [
                    '修正語法錯誤後重新檢查',
                    '參考 Ansible Inventory 語法文檔'
                ]
            }
    except Exception as e:
        return self._create_error_check('syntax', str(e))
```

#### 2. 結構完整性 (Structure Integrity)

**檢查內容**:
- ✅ 必要的 Section 存在（`[all]`, `[ungrouped]` 等）
- ✅ Group 層級關係正確（`[group:children]`）
- ✅ Host 定義完整（至少包含 `ansible_host`）
- ✅ 變數定義區域正確（`[group:vars]`）
- ✅ 循環依賴檢測（Group A → B → A）

**狀態判定**:
- ✅ **成功**: 結構完整且符合最佳實踐
- ⚠ **警告**: 缺少建議的 Section 或變數
- ✗ **錯誤**: 結構錯誤或循環依賴

#### 3. 主機配置檢查 (Host Configuration)

**檢查內容**:
- ✅ 每個 Host 必須有 `ansible_host`
- ✅ 認證信息完整（`ansible_user`, `ansible_password` 或 `ansible_ssh_key`）
- ✅ 連接參數合理（`ansible_port`, `ansible_connection`）
- ✅ 必要變數存在（根據項目需求）

**範例檢查**:
```python
def _check_host_config(self, hostname, host_vars):
    """檢查單個主機配置"""
    required_vars = ['ansible_host', 'ansible_user']
    missing_vars = [v for v in required_vars if v not in host_vars]
    
    if missing_vars:
        return {
            'status': 'error',
            'message': f'主機 {hostname} 缺少必要變數',
            'value': hostname,
            'details': {'missing': missing_vars},
            'suggestions': [
                f'添加缺少的變數: {", ".join(missing_vars)}'
            ]
        }
    return {'status': 'success', ...}
```

#### 4. IP 地址驗證 (IP Address Validation)

**檢查內容**:
- ✅ IP 格式正確（IPv4/IPv6）
- ✅ IP 地址在允許的子網範圍內
- ✅ 無 IP 衝突（不同主機相同 IP）
- ✅ 特殊 IP 處理（0.0.0.0, 127.0.0.1, 255.255.255.255）

**實現**:
```python
def _check_ip_addresses(self):
    """檢查 IP 地址"""
    from library.utils.network import validate_ip, check_ip_conflict
    
    ip_map = {}  # {ip: [hostnames]}
    invalid_ips = []
    
    for host, vars in self.hosts.items():
        ip = vars.get('ansible_host')
        if not ip:
            continue
        
        # 驗證格式
        if not validate_ip(ip):
            invalid_ips.append((host, ip))
            continue
        
        # 檢查衝突
        if ip not in ip_map:
            ip_map[ip] = []
        ip_map[ip].append(host)
    
    conflicts = {ip: hosts for ip, hosts in ip_map.items() if len(hosts) > 1}
    
    if invalid_ips or conflicts:
        return {
            'status': 'error',
            'message': f'發現 {len(invalid_ips)} 個無效 IP, {len(conflicts)} 個衝突',
            'details': {
                'invalid': invalid_ips,
                'conflicts': conflicts
            },
            'suggestions': ['修正無效 IP', '解決 IP 衝突']
        }
    
    return {
        'status': 'success',
        'message': f'所有 {len(ip_map)} 個 IP 地址有效',
        'value': f'{len(ip_map)} 個唯一 IP'
    }
```

#### 5. MAC 地址驗證 (MAC Address Validation)

**檢查內容**:
- ✅ MAC 格式正確（`XX:XX:XX:XX:XX:XX` 或 `XX-XX-XX-XX-XX-XX`）
- ✅ 無重複 MAC 地址
- ✅ MAC 地址屬於有效廠商（OUI 檢查）

### 階段 2: 進階驗證（推薦）

#### 6. 網路連線測試 (Network Connectivity)

**檢查內容**:
- ✅ Ping 測試（ICMP）
- ✅ SSH 端口可達性（Telnet/Socket 測試）
- ✅ DNS 解析（如果使用 hostname）

**實現考量**:
- ⚠️ 可能耗時較長（需要逐一測試）
- 🔄 使用異步或多線程加速
- ⏱️ 設置合理的超時時間（3-5 秒）

```python
import socket
import concurrent.futures

def _check_network_connectivity(self):
    """並行測試網路連線"""
    results = {}
    
    def test_host(hostname, ip, port=22):
        """測試單個主機"""
        try:
            with socket.create_connection((ip, port), timeout=3):
                return {'status': 'success', 'reachable': True}
        except Exception as e:
            return {'status': 'warning', 'reachable': False, 'error': str(e)}
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = {
            executor.submit(test_host, host, vars.get('ansible_host')): host
            for host, vars in self.hosts.items()
            if vars.get('ansible_host')
        }
        
        for future in concurrent.futures.as_completed(futures):
            hostname = futures[future]
            results[hostname] = future.result()
    
    unreachable = [h for h, r in results.items() if not r['reachable']]
    
    return {
        'status': 'warning' if unreachable else 'success',
        'message': f'{len(results) - len(unreachable)}/{len(results)} 主機可達',
        'details': {'unreachable': unreachable},
        'suggestions': ['檢查網路連線', '確認防火牆設置'] if unreachable else []
    }
```

#### 7. SSH 認證測試 (SSH Authentication)

**檢查內容**:
- ✅ SSH 連線成功
- ✅ 認證方式正確（密碼/密鑰）
- ✅ 權限足夠（sudo 檢查）

**安全考量**:
- 🔒 不在檢查結果中顯示密碼
- ⚠️ 可選功能（用戶確認後執行）
- 📝 記錄失敗原因但不記錄敏感信息

#### 8. DHCP 記錄比對 (DHCP Record Matching)

**檢查內容**:
- ✅ Inventory 中的 IP 是否在 DHCP Server 中有記錄
- ✅ MAC 地址是否匹配
- ✅ 租約狀態（是否過期）

**實現**:
```python
def _check_dhcp_records(self):
    """比對 DHCP 記錄"""
    from api.models import DHCPLease
    
    matches = 0
    mismatches = []
    
    for host, vars in self.hosts.items():
        ip = vars.get('ansible_host')
        mac = vars.get('macaddress')
        
        if not ip or not mac:
            continue
        
        # 查詢 DHCP 記錄
        lease = DHCPLease.objects.filter(ip_address=ip).first()
        
        if lease:
            if lease.mac_address.lower() == mac.lower():
                matches += 1
            else:
                mismatches.append({
                    'host': host,
                    'inventory_mac': mac,
                    'dhcp_mac': lease.mac_address
                })
        else:
            mismatches.append({
                'host': host,
                'reason': 'No DHCP record found'
            })
    
    return {
        'status': 'warning' if mismatches else 'success',
        'message': f'{matches} 個主機匹配 DHCP 記錄',
        'details': {'mismatches': mismatches},
        'suggestions': ['同步 DHCP 記錄', '更新 Inventory MAC 地址']
    }
```

### 階段 3: 智能建議（可選）

#### 9. 最佳實踐檢查 (Best Practices)

**檢查內容**:
- ✅ Group 命名規範（小寫、底線分隔）
- ✅ 變數命名規範（避免保留字）
- ✅ 文檔註釋完整性
- ✅ 敏感信息處理（使用 Ansible Vault）

#### 10. 性能優化建議 (Performance Tips)

**檢查內容**:
- ✅ Group 結構過於扁平或過於複雜
- ✅ 過多的 `ansible_connection=local`
- ✅ 未使用變數繼承（重複定義）

---

## UI/UX 設計

### 觸發入口

**位置**: Ansible Inventory Manager 頁面

```javascript
// frontend/src/pages/AnsibleInventoryManagerPage.js
<Card
    title="Ansible Inventory Manager"
    extra={
        <Space>
            <Button 
                type="primary" 
                icon={<CheckCircleOutlined />}
                onClick={handleOpenValidationDrawer}
            >
                檢查配置
            </Button>
            <Button icon={<DownloadOutlined />}>導出</Button>
        </Space>
    }
>
    {/* Inventory 內容 */}
</Card>
```

### 右側抽屜設計

**組件**: `InventoryValidationDrawer.js`

```javascript
import React, { useState, useEffect } from 'react';
import { Drawer, Button, Space, Progress, Card, Collapse, Checkbox, Tag, Descriptions } from 'antd';
import { CheckCircleOutlined, CloseCircleOutlined, WarningOutlined, SyncOutlined } from '@ant-design/icons';

const InventoryValidationDrawer = ({ visible, onClose, inventoryId }) => {
    const [loading, setLoading] = useState(false);
    const [validationResult, setValidationResult] = useState(null);
    const [expandedPanels, setExpandedPanels] = useState([]);

    // 執行檢查
    const handleValidate = async () => {
        setLoading(true);
        try {
            const response = await axios.post(
                `/api/ansible-inventory/${inventoryId}/validate-config/`
            );
            setValidationResult(response.data);
            
            // 自動展開錯誤和警告項目
            const errorKeys = Object.keys(response.data.checks).filter(
                key => ['error', 'warning'].includes(response.data.checks[key].status)
            );
            setExpandedPanels(errorKeys);
            
            message.success('檢查完成');
        } catch (error) {
            message.error('檢查失敗：' + error.message);
        } finally {
            setLoading(false);
        }
    };

    return (
        <Drawer
            title="Ansible Inventory 配置檢查"
            placement="right"
            width={720}
            onClose={onClose}
            visible={visible}
            extra={
                <Space>
                    <Button 
                        type="primary" 
                        icon={<SyncOutlined />}
                        onClick={handleValidate}
                        loading={loading}
                    >
                        {validationResult ? '重新檢查' : '開始檢查'}
                    </Button>
                </Space>
            }
        >
            {!validationResult ? (
                <Card>
                    <p>點擊「開始檢查」按鈕執行配置驗證</p>
                    <p>檢查項目包括：</p>
                    <ul>
                        <li>✓ 語法驗證</li>
                        <li>✓ 結構完整性</li>
                        <li>✓ 主機配置檢查</li>
                        <li>✓ IP 地址驗證</li>
                        <li>✓ MAC 地址驗證</li>
                        <li>✓ 網路連線測試（可選）</li>
                        <li>✓ DHCP 記錄比對（可選）</li>
                    </ul>
                </Card>
            ) : (
                <>
                    {/* 檢查總覽 */}
                    <Card title="📋 檢查總覽" style={{ marginBottom: 16 }}>
                        <Space direction="vertical" style={{ width: '100%' }}>
                            <div>
                                狀態: {renderStatusTag(validationResult.overall_status)}
                            </div>
                            <Progress 
                                percent={calculateProgress(validationResult.summary)}
                                status={validationResult.overall_status === 'success' ? 'success' : 'active'}
                            />
                            <div>
                                {validationResult.summary.passed}/{validationResult.summary.total_checks} 通過
                            </div>
                        </Space>
                    </Card>

                    {/* 檢查項目列表 */}
                    <Card title="✓ 檢查項目">
                        <Collapse 
                            activeKey={expandedPanels}
                            onChange={setExpandedPanels}
                            ghost
                        >
                            {Object.entries(validationResult.checks).map(([key, checkData]) => (
                                <Panel
                                    key={key}
                                    header={
                                        <Space>
                                            <Checkbox 
                                                checked={checkData.status === 'success'}
                                                disabled
                                            />
                                            <span>{getCheckDisplayName(key)}</span>
                                            {renderStatusIcon(checkData.status)}
                                        </Space>
                                    }
                                    style={{
                                        backgroundColor: 
                                            checkData.status === 'error' ? '#fff1f0' :
                                            checkData.status === 'warning' ? '#fffbe6' : '#f6ffed',
                                        border: `1px solid ${
                                            checkData.status === 'error' ? '#ffccc7' :
                                            checkData.status === 'warning' ? '#ffe58f' : '#b7eb8f'
                                        }`,
                                        marginBottom: 16,
                                        borderRadius: 4
                                    }}
                                >
                                    <Descriptions column={1} size="small" bordered>
                                        <Descriptions.Item label="檢查值">
                                            {checkData.value || 'N/A'}
                                        </Descriptions.Item>
                                        <Descriptions.Item label="狀態">
                                            {checkData.message}
                                        </Descriptions.Item>
                                    </Descriptions>

                                    {/* 詳細信息 */}
                                    {checkData.details && (
                                        <>
                                            <Divider>詳細資訊</Divider>
                                            <Descriptions column={1} size="small" bordered>
                                                {Object.entries(checkData.details).map(([k, v]) => (
                                                    <Descriptions.Item key={k} label={k}>
                                                        {JSON.stringify(v)}
                                                    </Descriptions.Item>
                                                ))}
                                            </Descriptions>
                                        </>
                                    )}

                                    {/* 建議 */}
                                    {checkData.suggestions?.length > 0 && (
                                        <>
                                            <Divider>建議</Divider>
                                            <ul>
                                                {checkData.suggestions.map((s, i) => (
                                                    <li key={i}>{s}</li>
                                                ))}
                                            </ul>
                                        </>
                                    )}
                                </Panel>
                            ))}
                        </Collapse>
                    </Card>
                </>
            )}
        </Drawer>
    );
};

export default InventoryValidationDrawer;
```

### 檢查項目名稱映射

```javascript
const getCheckDisplayName = (key) => {
    const names = {
        syntax: '語法驗證',
        structure: '結構完整性',
        host_config: '主機配置檢查',
        ip_addresses: 'IP 地址驗證',
        mac_addresses: 'MAC 地址驗證',
        network_connectivity: '網路連線測試',
        ssh_authentication: 'SSH 認證測試',
        dhcp_records: 'DHCP 記錄比對',
        best_practices: '最佳實踐檢查',
        performance: '性能優化建議'
    };
    return names[key] || key;
};
```

### 狀態圖標渲染

```javascript
const renderStatusIcon = (status) => {
    switch (status) {
        case 'success':
            return <CheckCircleOutlined style={{ color: '#52c41a', fontSize: 20 }} />;
        case 'warning':
            return <WarningOutlined style={{ color: '#faad14', fontSize: 20 }} />;
        case 'error':
            return <CloseCircleOutlined style={{ color: '#ff4d4f', fontSize: 20 }} />;
        default:
            return <InfoCircleOutlined style={{ color: '#d9d9d9', fontSize: 20 }} />;
    }
};

const renderStatusTag = (status) => {
    const config = {
        success: { color: 'success', text: '通過' },
        warning: { color: 'warning', text: '警告' },
        error: { color: 'error', text: '失敗' },
        unknown: { color: 'default', text: '未檢查' }
    };
    const { color, text } = config[status] || config.unknown;
    return <Tag color={color}>{text}</Tag>;
};
```

---

## 後端架構設計

### 服務類別: `InventoryConfigValidator`

**位置**: `library/services/inventory_config_validator.py`

```python
"""
Ansible Inventory Configuration Validator

Validates Ansible Inventory files for:
- Syntax correctness
- Structure integrity
- Host configuration completeness
- IP/MAC address validation
- Network connectivity (optional)
- DHCP record matching (optional)

Author: Network Toolbox Team
Created: 2025-11-18 (Planned)
"""

import logging
import re
from typing import Dict, List, Optional
from configparser import ConfigParser

logger = logging.getLogger(__name__)


class InventoryConfigValidator:
    """
    Ansible Inventory Configuration Validator
    """
    
    def __init__(self, inventory_id: int, check_connectivity: bool = False):
        """
        初始化驗證器
        
        Args:
            inventory_id: Inventory 記錄 ID
            check_connectivity: 是否執行網路連線測試（耗時）
        """
        self.inventory_id = inventory_id
        self.check_connectivity = check_connectivity
        self.inventory = None
        self.content = ""
        self.parsed_inventory = {}
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
            logger.info(f"Starting validation for Inventory ID: {self.inventory_id}")
            
            # 1. 載入 Inventory
            if not self._load_inventory():
                return self._create_error_result("Failed to load inventory")
            
            # 2. 語法驗證
            self._check_syntax()
            
            # 3. 結構完整性檢查
            self._check_structure()
            
            # 4. 主機配置檢查
            self._check_host_config()
            
            # 5. IP 地址驗證
            self._check_ip_addresses()
            
            # 6. MAC 地址驗證
            self._check_mac_addresses()
            
            # 7. 網路連線測試（可選）
            if self.check_connectivity:
                self._check_network_connectivity()
            
            # 8. DHCP 記錄比對（可選）
            self._check_dhcp_records()
            
            # 9. 計算總體狀態
            self._calculate_overall_status()
            
            logger.info(f"Validation complete. Status: {self.validation_results['overall_status']}")
            
            return self.validation_results
            
        except Exception as e:
            logger.error(f"Validation error: {e}", exc_info=True)
            return self._create_error_result(f"Validation exception: {str(e)}")
    
    def _load_inventory(self) -> bool:
        """載入 Inventory 記錄"""
        try:
            from api.models import AnsibleInventory
            
            self.inventory = AnsibleInventory.objects.filter(id=self.inventory_id).first()
            
            if not self.inventory:
                logger.error(f"Inventory not found: {self.inventory_id}")
                return False
            
            self.content = self.inventory.content or ""
            
            if not self.content:
                logger.warning(f"Inventory {self.inventory_id} has no content")
                return False
            
            logger.info(f"Loaded Inventory: {self.inventory.id} ({len(self.content)} chars)")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load inventory: {e}", exc_info=True)
            return False
    
    def _check_syntax(self):
        """語法驗證"""
        try:
            from library.utils.enhanced_ini_validator import validate_ini_content
            
            result = validate_ini_content(self.content)
            
            if result['valid']:
                self.validation_results['checks']['syntax'] = {
                    'status': 'success',
                    'message': '語法檢查通過',
                    'value': f"{result['line_count']} 行",
                    'details': {
                        'sections': len(result.get('sections', [])),
                        'variables': len(result.get('variables', [])),
                        'hosts': len(result.get('hosts', []))
                    },
                    'suggestions': []
                }
            else:
                self.validation_results['checks']['syntax'] = {
                    'status': 'error',
                    'message': f"發現 {len(result['errors'])} 個語法錯誤",
                    'value': f"{len(result['errors'])} 錯誤",
                    'details': {'errors': result['errors'][:10]},  # 最多顯示 10 個
                    'suggestions': [
                        '修正語法錯誤後重新檢查',
                        '參考 Ansible Inventory 文檔'
                    ]
                }
        except Exception as e:
            logger.error(f"Syntax check failed: {e}", exc_info=True)
            self.validation_results['checks']['syntax'] = self._create_error_check('syntax', str(e))
    
    def _check_structure(self):
        """結構完整性檢查"""
        # TODO: 實現
        pass
    
    def _check_host_config(self):
        """主機配置檢查"""
        # TODO: 實現
        pass
    
    def _check_ip_addresses(self):
        """IP 地址驗證"""
        # TODO: 實現
        pass
    
    def _check_mac_addresses(self):
        """MAC 地址驗證"""
        # TODO: 實現
        pass
    
    def _check_network_connectivity(self):
        """網路連線測試"""
        # TODO: 實現
        pass
    
    def _check_dhcp_records(self):
        """DHCP 記錄比對"""
        # TODO: 實現
        pass
    
    def _calculate_overall_status(self):
        """計算總體狀態"""
        checks = self.validation_results['checks']
        
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
    
    def _create_error_result(self, message: str) -> Dict:
        """創建錯誤結果"""
        return {
            'overall_status': 'error',
            'error': message,
            'checks': {},
            'summary': {'total_checks': 0, 'passed': 0, 'warnings': 0, 'errors': 1}
        }
    
    def _create_error_check(self, check_name: str, error: str) -> Dict:
        """創建錯誤檢查項目"""
        return {
            'status': 'error',
            'message': f'檢查失敗: {error}',
            'value': 'N/A',
            'details': {},
            'suggestions': ['請聯繫管理員']
        }
```

---

## API 設計

### 端點: 驗證 Inventory 配置

**URL**: `POST /api/ansible-inventory/{id}/validate-config/`

**請求參數**:
```json
{
    "check_connectivity": false,  // 是否執行網路連線測試（可選，默認 false）
    "check_dhcp": false,          // 是否檢查 DHCP 記錄（可選，默認 false）
    "dhcp_server_ids": [1, 2]     // 指定 DHCP Server（可選）
}
```

**響應格式**:
```json
{
    "success": true,
    "data": {
        "overall_status": "warning",
        "inventory_id": 123,
        "checks": {
            "syntax": {
                "status": "success",
                "message": "語法檢查通過",
                "value": "150 行",
                "details": {
                    "sections": 5,
                    "variables": 20,
                    "hosts": 10
                },
                "suggestions": []
            },
            "structure": {
                "status": "success",
                "message": "結構完整",
                "value": "5 個 Group",
                "details": {},
                "suggestions": []
            },
            "host_config": {
                "status": "warning",
                "message": "2 個主機缺少必要變數",
                "value": "8/10 完整",
                "details": {
                    "incomplete_hosts": [
                        {"host": "server1", "missing": ["ansible_user"]},
                        {"host": "server2", "missing": ["ansible_password"]}
                    ]
                },
                "suggestions": [
                    "為 server1 添加 ansible_user",
                    "為 server2 添加 ansible_password"
                ]
            }
        },
        "summary": {
            "total_checks": 5,
            "passed": 3,
            "warnings": 2,
            "errors": 0
        }
    }
}
```

### ViewSet 實現

**位置**: `backend/api/views/ansible_inventory.py`

```python
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from library.services.inventory_config_validator import InventoryConfigValidator

class AnsibleInventoryViewSet(viewsets.ModelViewSet):
    # ... 現有代碼 ...
    
    @action(detail=True, methods=['post'], url_path='validate-config')
    def validate_config(self, request, pk=None):
        """
        驗證 Ansible Inventory 配置
        
        POST /api/ansible-inventory/{id}/validate-config/
        
        Body:
            check_connectivity (bool): 是否執行網路連線測試
            check_dhcp (bool): 是否檢查 DHCP 記錄
            dhcp_server_ids (list): 指定 DHCP Server IDs
        
        Returns:
            驗證結果
        """
        try:
            inventory = self.get_object()
            
            check_connectivity = request.data.get('check_connectivity', False)
            check_dhcp = request.data.get('check_dhcp', False)
            dhcp_server_ids = request.data.get('dhcp_server_ids', [])
            
            logger.info(f"Validating Inventory {inventory.id}, connectivity={check_connectivity}, dhcp={check_dhcp}")
            
            validator = InventoryConfigValidator(
                inventory_id=inventory.id,
                check_connectivity=check_connectivity
            )
            
            result = validator.validate()
            
            return Response({
                'success': True,
                'data': result
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Validation failed: {e}", exc_info=True)
            return Response({
                'success': False,
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
```

---

## 實施階段規劃

### 階段 1: MVP 實現（1-2 週）

**目標**: 基礎驗證功能可用

**任務清單**:
1. ✅ 創建後端服務 `InventoryConfigValidator`
2. ✅ 實現語法驗證（使用現有 `enhanced_ini_validator`）
3. ✅ 實現結構完整性檢查
4. ✅ 實現主機配置檢查
5. ✅ 實現 API 端點 `validate-config`
6. ✅ 創建前端組件 `InventoryValidationDrawer`
7. ✅ 整合到 `AnsibleInventoryManagerPage`
8. ✅ 單元測試（後端）
9. ✅ 整合測試（前後端）
10. ✅ 文檔更新

**驗收標準**:
- [ ] 可以打開右側抽屜
- [ ] 可以執行語法、結構、主機配置檢查
- [ ] 檢查結果正確顯示（成功/警告/錯誤）
- [ ] 錯誤項目自動展開
- [ ] 可以重新檢查
- [ ] 基本的錯誤處理

### 階段 2: 進階功能（1 週）

**目標**: 添加 IP/MAC 驗證和網路測試

**任務清單**:
1. ✅ 實現 IP 地址驗證
2. ✅ 實現 MAC 地址驗證
3. ✅ 實現網路連線測試（使用多線程）
4. ✅ 添加超時和錯誤處理
5. ✅ 更新前端 UI（顯示進度）
6. ✅ 性能優化
7. ✅ 測試

**驗收標準**:
- [ ] IP/MAC 格式驗證正確
- [ ] 衝突檢測準確
- [ ] 網路測試不阻塞 UI
- [ ] 超時設置合理（3-5 秒）
- [ ] 進度反饋清晰

### 階段 3: DHCP 整合（3-5 天）

**目標**: 比對 DHCP 記錄

**任務清單**:
1. ✅ 實現 DHCP 記錄查詢
2. ✅ 實現 IP/MAC 比對邏輯
3. ✅ 添加不匹配建議
4. ✅ 測試

**驗收標準**:
- [ ] 可以正確查詢 DHCP 記錄
- [ ] 比對邏輯準確
- [ ] 建議實用

### 階段 4: 報告導出和優化（3-5 天）

**目標**: 報告導出、性能優化

**任務清單**:
1. ✅ 實現 JSON 報告導出
2. ✅ 實現 PDF 報告導出（可選）
3. ✅ 添加快取機制（避免重複檢查）
4. ✅ 性能分析和優化
5. ✅ 用戶文檔

**驗收標準**:
- [ ] 可以導出完整報告
- [ ] 檢查速度合理（< 10 秒）
- [ ] 文檔清晰完整

---

## 技術考量

### 性能優化

1. **並行檢查**:
   - 使用 `concurrent.futures` 並行測試網路連線
   - 獨立的檢查項目可以並行執行

2. **快取機制**:
   - 短期快取檢查結果（5-10 分鐘）
   - 使用 Redis 或 Django Cache

3. **超時設置**:
   - 網路測試: 3 秒
   - SSH 測試: 5 秒
   - 總體檢查: 30 秒

### 安全考量

1. **敏感信息保護**:
   - 不在檢查結果中顯示密碼
   - SSH 測試需要用戶確認

2. **權限控制**:
   - 只有 Inventory 擁有者可以執行檢查
   - API 端點需要認證

### 錯誤處理

1. **網路錯誤**:
   - 超時 → 標記為警告，不是錯誤
   - 連線拒絕 → 檢查端口和防火牆

2. **資料錯誤**:
   - 格式錯誤 → 提供修正建議
   - 缺失數據 → 標記為警告

### 測試策略

1. **單元測試**:
   - 每個檢查方法單獨測試
   - Mock 外部依賴（DHCP, SSH）

2. **整合測試**:
   - 完整驗證流程測試
   - 前後端整合測試

3. **性能測試**:
   - 大型 Inventory 測試（100+ hosts）
   - 網路測試並發性能

---

## 附錄

### 相關文件

- `library/services/build_config_validator.py` - 參考實現
- `library/utils/enhanced_ini_validator.py` - 語法驗證器
- `frontend/src/pages/BuildConfigValidatorPage.js` - 參考 UI
- `frontend/src/components/AnsibleConfig.js` - Ansible 配置組件

### 參考資源

- Ansible Inventory 文檔: https://docs.ansible.com/ansible/latest/user_guide/intro_inventory.html
- Ant Design Drawer: https://ant.design/components/drawer/
- Ant Design Collapse: https://ant.design/components/collapse/

---

**文檔版本**: v1.0  
**最後更新**: 2025-11-18  
**狀態**: 📋 規劃階段 - 待審核和實施
