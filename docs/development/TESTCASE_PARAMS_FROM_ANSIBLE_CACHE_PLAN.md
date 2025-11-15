# 從 Ansible Cache 提取測試案例相關參數規劃

## 📋 需求說明

在 Ansible Inventory 配置查看器中，需要識別並獨立顯示 **testcase_set 及其相關參數**。

**核心問題**：如何從 **Ansible Inventory Service 解析並快取的 JSON 資料**中，自動識別哪些參數是測試案例相關的？

---

## 🎯 核心概念

### 現有機制說明

**Ansible Inventory Service** 已經做了以下工作：

1. **執行 Ansible 命令**：
   ```bash
   ansible-inventory -i /path/to/hosts --host <hostname>
   ```

2. **解析 JSON 輸出**：
   ```json
   {
       "ansible_host": "10.250.71.22",
       "device_number": "PC-SSD-4632",
       "sample_number": "SM2703AB-02003",
       "testcase_set": "testcases_demo",
       "testcase_version": "v1.2.3",
       "testcase_timeout": "3600",
       "uart_id": "KVM01",
       "ansible_user": "root",
       ...
   }
   ```

3. **儲存到快取**：
   ```python
   # 快取位置：/tmp/ansible_cache_{job_id}/ansible_host_{hostname}.json
   self._save_to_cache('host_config', host_config, hostname)
   ```

4. **前端 API 返回**：
   ```javascript
   {
       "success": true,
       "cached": true,
       "hostname": "Test-KVM01",
       "config": {
           "ansible_host": "10.250.71.22",
           "testcase_set": "testcases_demo",
           ...
       }
   }
   ```

---

## 💡 解決方案

### 方案：從 config 物件中過濾參數 ✅ **推薦**

**核心思路**：
- ✅ **不需要解析 inventory 檔案**
- ✅ **直接使用 `get_host_config()` 返回的 `config` 物件**
- ✅ **在前端使用辨識函數過濾參數**

---

## 📦 實施設計

### 資料流程

```
用戶打開 Ansible 配置查看器
         ↓
前端調用：getHostConfig(jobId, hostname)
         ↓
API：GET /api/jenkins-jobs/{id}/ansible-inventory/hosts/{hostname}/
         ↓
後端：AnsibleInventoryService.get_host_config(hostname)
         ↓
返回 JSON：
{
    "success": true,
    "cached": true,  ← 可能從快取載入
    "hostname": "Test-KVM01",
    "config": {      ← 完整的主機配置（所有參數）
        "ansible_host": "10.250.71.22",
        "device_number": "PC-SSD-4632",
        "testcase_set": "testcases_demo",        ← 測試案例參數
        "testcase_version": "v1.2.3",            ← 測試案例參數
        "testcase_timeout": "3600",              ← 測試案例參數
        "testcase_custom_param": "value123",     ← 測試案例參數
        "uart_id": "KVM01",
        "ansible_user": "root",
        ...
    }
}
         ↓
前端處理：categorizeConfig(config)
         ↓
使用辨識函數過濾：
  - isTestcaseField(key) → 判斷是否為測試案例參數
  - getTestcaseFieldLabel(key) → 獲取顯示標籤
         ↓
分組顯示：
  - testcaseConfig: { testcase_set, testcase_version, ... }
  - basicInfo: { ansible_host, device_number, ... }
  - uartInfo: { uart_id, uart_host, ... }
  - ansibleVars: { ansible_user, ansible_password, ... }
  - otherConfig: { ... }
```

---

## 🔍 config 物件結構分析

### 實際的 config 物件範例

```json
{
    "ansible_host": "10.250.71.22",
    "device_number": "PC-SSD-4632",
    "sample_number": "SM2703AB-02003",
    "uart_id": "KVM01",
    "uart_host": "10.250.0.2",
    "macaddress": "CC:28:AA:86:C3:7F",
    "testcase_set": "testcases_demo",
    "ansible_user": "root",
    "ansible_password": "password123",
    "ansible_shell_type": "sh",
    "ansible_connection": "ssh",
    "ansible_port": 22
}
```

### 假設包含更多測試案例參數

```json
{
    "ansible_host": "10.250.71.22",
    "device_number": "PC-SSD-4632",
    
    // 測試案例相關參數（需要識別）
    "testcase_set": "testcases_demo",
    "testcase_version": "v1.2.3",
    "testcase_branch": "main",
    "testcase_timeout": "3600",
    "testcase_retry": "3",
    "testcase_parallel": "4",
    "testcase_config_file": "pytest.ini",
    "testcase_custom_setting": "value123",
    
    // 其他參數
    "uart_id": "KVM01",
    "ansible_user": "root"
}
```

---

## 📦 前端實現（完整版）

### 1. 辨識函數定義

**位置**：`frontend/src/services/ansibleService.js`

```javascript
/**
 * ===== 測試案例參數辨識規則 =====
 */

// 核心測試案例參數（有預定義的友善標籤）
const coreTestcaseFields = {
    testcase_set: '測試案例集',
    testcase_version: '測試案例版本',
    testcase_branch: '測試案例分支',
    testcase_path: '測試案例路徑',
    testcase_timeout: '測試超時時間',
    testcase_retry: '測試重試次數',
    testcase_parallel: '並行測試數量',
    testcase_config_file: '測試配置檔案',
    testcase_env: '測試環境變數',
    testcase_tags: '測試標籤',
    testcase_exclude: '排除測試',
};

// 測試案例參數前綴（自動匹配）
const testcasePrefixes = [
    'testcase_',     // testcase_xxx
    'test_case_',    // test_case_xxx（支援底線分隔）
];

// 排除規則（避免誤判為測試案例參數）
const excludeTestcaseFields = [
    'test_user',       // 測試使用者（屬於 Ansible 變數）
    'test_password',   // 測試密碼（屬於 Ansible 變數）
    'test_env',        // 測試環境（可能是其他配置）
    'test_mode',       // 測試模式（可能是其他配置）
    'test_server',     // 測試伺服器（可能是其他配置）
];

/**
 * 判斷參數是否為測試案例相關參數
 * 
 * @param {string} key - 參數名稱
 * @returns {boolean} 是否為測試案例參數
 * 
 * @example
 * isTestcaseField('testcase_set')           // true
 * isTestcaseField('testcase_version')       // true
 * isTestcaseField('testcase_custom_param')  // true（前綴匹配）
 * isTestcaseField('test_user')              // false（排除規則）
 * isTestcaseField('ansible_host')           // false
 */
export const isTestcaseField = (key) => {
    // 1. 檢查是否在排除列表中
    if (excludeTestcaseFields.includes(key)) {
        return false;
    }
    
    // 2. 檢查是否為核心測試案例參數
    if (key in coreTestcaseFields) {
        return true;
    }
    
    // 3. 檢查是否匹配測試案例前綴
    return testcasePrefixes.some(prefix => key.startsWith(prefix));
};

/**
 * 獲取測試案例參數的顯示標籤
 * 
 * @param {string} key - 參數名稱
 * @returns {string} 顯示標籤
 * 
 * @example
 * getTestcaseFieldLabel('testcase_set')           // '測試案例集'
 * getTestcaseFieldLabel('testcase_version')       // '測試案例版本'
 * getTestcaseFieldLabel('testcase_custom_param')  // '測試案例 Custom Param'
 */
export const getTestcaseFieldLabel = (key) => {
    // 1. 如果是核心參數，返回預定義標籤
    if (key in coreTestcaseFields) {
        return coreTestcaseFields[key];
    }
    
    // 2. 自動生成標籤：將參數名轉換為易讀格式
    // 例如：testcase_custom_param → Custom Param
    let label = key;
    
    // 移除前綴
    if (label.startsWith('testcase_')) {
        label = label.substring('testcase_'.length);
    } else if (label.startsWith('test_case_')) {
        label = label.substring('test_case_'.length);
    }
    
    // 底線轉空格，首字母大寫
    label = label
        .split('_')
        .map(word => word.charAt(0).toUpperCase() + word.slice(1))
        .join(' ');
    
    return `測試案例 ${label}`;
};

/**
 * 從 config 物件中提取測試案例相關參數
 * 
 * @param {object} config - 主機配置物件（從 API 獲取）
 * @returns {object} 測試案例參數物件
 * 
 * @example
 * const config = {
 *     ansible_host: '10.250.71.22',
 *     testcase_set: 'testcases_demo',
 *     testcase_version: 'v1.2.3',
 *     testcase_custom: 'value',
 *     uart_id: 'KVM01'
 * };
 * 
 * extractTestcaseFields(config)
 * // 返回：
 * // {
 * //     testcase_set: { label: '測試案例集', value: 'testcases_demo' },
 * //     testcase_version: { label: '測試案例版本', value: 'v1.2.3' },
 * //     testcase_custom: { label: '測試案例 Custom', value: 'value' }
 * // }
 */
export const extractTestcaseFields = (config) => {
    const testcaseFields = {};
    
    if (!config) return testcaseFields;
    
    Object.entries(config).forEach(([key, value]) => {
        if (isTestcaseField(key)) {
            testcaseFields[key] = {
                label: getTestcaseFieldLabel(key),
                value: value
            };
        }
    });
    
    return testcaseFields;
};
```

---

### 2. 配置分類函數（修改版）

**位置**：`frontend/src/components/AnsibleConfig/HostConfigTab.jsx`

```javascript
import { 
    isTestcaseField, 
    getTestcaseFieldLabel,
    extractTestcaseFields 
} from '../../services/ansibleService';

/**
 * 將主機配置分組為不同的區塊
 * 
 * @param {object} config - 從 API 獲取的主機配置（已由 Ansible 解析）
 * @returns {object} 分組後的配置
 */
const categorizeConfig = (config) => {
    if (!config) return null;

    // 1. 提取測試案例參數（使用辨識函數）
    const testcaseConfig = extractTestcaseFields(config);

    // 2. 提取基本資訊
    const basicInfoKeys = ['ansible_host', 'device_number', 'sample_number', 'macaddress'];
    const basicInfo = {};
    basicInfoKeys.forEach(key => {
        if (config[key] !== undefined) {
            basicInfo[key] = {
                label: basicInfoFieldLabels[key],
                value: config[key]
            };
        }
    });

    // 3. 提取 UART 連接資訊
    const uartKeys = ['uart_id', 'uart_host'];
    const uartInfo = {};
    uartKeys.forEach(key => {
        if (config[key] !== undefined) {
            uartInfo[key] = {
                label: uartFieldLabels[key],
                value: config[key]
            };
        }
    });

    // 4. 提取 Ansible 變數（ansible_ 開頭）
    const ansibleVars = {};
    Object.entries(config).forEach(([key, value]) => {
        if (key.startsWith('ansible_') && !basicInfoKeys.includes(key)) {
            ansibleVars[key] = {
                label: ansibleFieldLabels[key] || key,
                value: value
            };
        }
    });

    // 5. 其他配置（排除已分類的）
    const allDefinedKeys = [
        ...Object.keys(testcaseConfig),  // ← 測試案例參數
        ...basicInfoKeys,
        ...uartKeys,
        ...Object.keys(ansibleVars)
    ];

    const otherConfig = {};
    Object.entries(config).forEach(([key, value]) => {
        if (!allDefinedKeys.includes(key)) {
            otherConfig[key] = {
                label: key,
                value: value
            };
        }
    });

    return {
        testcaseConfig,  // ← 測試案例配置（自動識別）
        basicInfo,
        uartInfo,
        ansibleVars,
        otherConfig,
    };
};

// 欄位標籤定義
const basicInfoFieldLabels = {
    ansible_host: 'IP 地址',
    device_number: '設備號',
    sample_number: '樣品號',
    macaddress: 'MAC 地址',
};

const uartFieldLabels = {
    uart_id: 'UART ID',
    uart_host: 'UART 主機',
};

const ansibleFieldLabels = {
    ansible_user: '使用者',
    ansible_password: '密碼',
    ansible_shell_type: 'Shell 類型',
    ansible_port: 'SSH 端口',
    ansible_connection: '連接類型',
};
```

---

### 3. UI 渲染（測試案例 Card）

```javascript
{/* 🧪 測試案例配置（自動識別） */}
{Object.keys(categorizedConfig.testcaseConfig).length > 0 && (
    <Card 
        title={
            <Space>
                <ExperimentOutlined style={{ color: '#52c41a' }} />
                <Text strong>測試案例配置</Text>
            </Space>
        } 
        size="small"
        style={{
            borderLeft: '3px solid #52c41a',
        }}
    >
        <Descriptions column={2} bordered size="small">
            {Object.entries(categorizedConfig.testcaseConfig).map(([key, item]) => (
                <Descriptions.Item 
                    key={key} 
                    label={
                        <Space>
                            <Text strong>{item.label}</Text>
                        </Space>
                    }
                >
                    {/* 根據參數類型顯示不同樣式 */}
                    {key === 'testcase_set' ? (
                        <Space>
                            <Tag color="green" icon={<ExperimentOutlined />}>
                                {item.value}
                            </Tag>
                            <Text type="secondary" style={{ fontSize: 12 }}>
                                測試案例集名稱
                            </Text>
                        </Space>
                    ) : (
                        <Text copyable={item.value !== 'N/A'}>
                            {item.value}
                        </Text>
                    )}
                </Descriptions.Item>
            ))}
        </Descriptions>
        
        {/* 說明文字 */}
        <Alert
            message="測試案例說明"
            description="此配置指定了該主機使用的測試案例相關設定。所有 testcase_ 開頭的參數會自動顯示在此區塊。"
            type="info"
            showIcon
            style={{ marginTop: 12 }}
        />
    </Card>
)}
```

---

## 🔍 參數識別範例

### 範例 1：只有 testcase_set

**API 返回的 config**：
```json
{
    "ansible_host": "10.250.71.22",
    "device_number": "PC-SSD-4632",
    "testcase_set": "testcases_demo",
    "uart_id": "KVM01"
}
```

**識別結果**：
```javascript
testcaseConfig = {
    testcase_set: {
        label: '測試案例集',
        value: 'testcases_demo'
    }
}
```

**UI 顯示**：
```
🧪 測試案例配置
├─ 測試案例集：testcases_demo
```

---

### 範例 2：多個測試案例參數

**API 返回的 config**：
```json
{
    "ansible_host": "10.250.71.22",
    "device_number": "PC-SSD-4632",
    "testcase_set": "testcases_demo",
    "testcase_version": "v1.2.3",
    "testcase_timeout": "3600",
    "testcase_retry": "3",
    "testcase_custom_setting": "value123",
    "uart_id": "KVM01",
    "ansible_user": "root"
}
```

**識別結果**：
```javascript
testcaseConfig = {
    testcase_set: {
        label: '測試案例集',
        value: 'testcases_demo'
    },
    testcase_version: {
        label: '測試案例版本',
        value: 'v1.2.3'
    },
    testcase_timeout: {
        label: '測試超時時間',
        value: '3600'
    },
    testcase_retry: {
        label: '測試重試次數',
        value: '3'
    },
    testcase_custom_setting: {
        label: '測試案例 Custom Setting',  // ← 自動生成
        value: 'value123'
    }
}
```

**UI 顯示**：
```
🧪 測試案例配置
├─ 測試案例集：testcases_demo
├─ 測試案例版本：v1.2.3
├─ 測試超時時間：3600
├─ 測試重試次數：3
└─ 測試案例 Custom Setting：value123
```

---

### 範例 3：排除誤判（test_user）

**API 返回的 config**：
```json
{
    "ansible_host": "10.250.71.22",
    "testcase_set": "testcases_demo",
    "test_user": "testuser",
    "test_password": "testpass",
    "ansible_user": "root"
}
```

**識別結果**：
```javascript
testcaseConfig = {
    testcase_set: {
        label: '測試案例集',
        value: 'testcases_demo'
    }
    // test_user 和 test_password 被排除，不出現在這裡
}

ansibleVars = {
    ansible_user: {
        label: '使用者',
        value: 'root'
    }
}

otherConfig = {
    test_user: {
        label: 'test_user',
        value: 'testuser'
    },
    test_password: {
        label: 'test_password',
        value: 'testpass'
    }
}
```

**UI 顯示**：
```
🧪 測試案例配置
└─ 測試案例集：testcases_demo

📦 Ansible 變數
└─ 使用者：root

⚙️ 其他配置
├─ test_user：testuser
└─ test_password：testpass
```

---

### 範例 4：沒有測試案例參數

**API 返回的 config**：
```json
{
    "ansible_host": "10.250.71.22",
    "device_number": "PC-SSD-4632",
    "uart_id": "KVM01",
    "ansible_user": "root"
}
```

**識別結果**：
```javascript
testcaseConfig = {}  // ← 空物件
```

**UI 顯示**：
```
測試案例配置 Card 不顯示（因為 Object.keys(testcaseConfig).length === 0）
```

---

## 🎯 核心優勢

### 1. 不需要解析 inventory 檔案 ✅

```python
# ❌ 舊方式：硬解析 inventory 檔案
with open(inventory_path, 'r') as f:
    content = f.read()
    # 複雜的正則表達式解析...

# ✅ 新方式：直接使用 Ansible 解析結果
service = AnsibleInventoryService(inventory_path)
result = service.get_host_config(hostname, use_cache=True)
config = result['config']  # ← 已經是 Python dict/JSON
```

### 2. 使用快取機制 ✅

```python
# Ansible Inventory Service 自動處理快取
# - 第一次：執行 ansible-inventory 命令
# - 後續：從快取載入（7 天有效）
result = service.get_host_config(hostname, use_cache=True)
if result['cached']:
    print("從快取載入，速度快！")
```

### 3. 前端只需要過濾邏輯 ✅

```javascript
// 前端只需要簡單的過濾邏輯
const testcaseConfig = extractTestcaseFields(config);

// 不需要：
// - 解析 ini 檔案格式
// - 處理群組繼承
// - 合併變數
// - ... (這些都由 Ansible 處理了)
```

### 4. 自動適應新參數 ✅

```javascript
// inventory 新增任何 testcase_xxx 參數：
// testcase_new_feature = "enabled"

// 前端自動識別並顯示：
// 測試案例 New Feature: enabled

// 完全不需要修改代碼！
```

---

## 📊 資料流程圖（完整版）

```
┌─────────────────────────────────────────────────────────────┐
│  Ansible Inventory 檔案（原始）                              │
│  /mnt/.../artifacts/inventory/hosts                         │
│                                                             │
│  [PQ1_3]                                                    │
│  Test-KVM01 ansible_host=10.250.71.22 \                    │
│              device_number=PC-SSD-4632 \                    │
│              testcase_set=testcases_demo \                  │
│              testcase_version=v1.2.3                        │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│  Ansible Inventory Service 執行命令                          │
│  ansible-inventory -i hosts --host Test-KVM01               │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│  Ansible 解析結果（JSON）                                    │
│  {                                                          │
│    "ansible_host": "10.250.71.22",                         │
│    "device_number": "PC-SSD-4632",                         │
│    "testcase_set": "testcases_demo",                       │
│    "testcase_version": "v1.2.3",                           │
│    ...                                                      │
│  }                                                          │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│  快取存儲（可選，7天有效）                                   │
│  /tmp/ansible_cache_{job_id}/ansible_host_Test-KVM01.json  │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│  API 返回給前端                                              │
│  GET /api/jenkins-jobs/269/ansible-inventory/hosts/Test-KVM01/│
│                                                             │
│  Response:                                                  │
│  {                                                          │
│    "success": true,                                         │
│    "cached": true,                                          │
│    "hostname": "Test-KVM01",                                │
│    "config": {         ← 這就是我們要處理的物件！           │
│      "ansible_host": "10.250.71.22",                       │
│      "device_number": "PC-SSD-4632",                       │
│      "testcase_set": "testcases_demo",                     │
│      "testcase_version": "v1.2.3",                         │
│      ...                                                    │
│    }                                                        │
│  }                                                          │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│  前端處理（HostConfigTab.jsx）                               │
│  const categorized = categorizeConfig(config);              │
│                                                             │
│  使用辨識函數：                                              │
│  - isTestcaseField('testcase_set') → true                  │
│  - isTestcaseField('testcase_version') → true             │
│  - isTestcaseField('ansible_host') → false                │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│  分組結果                                                    │
│  {                                                          │
│    testcaseConfig: {                                        │
│      testcase_set: { label: '測試案例集', value: '...' },   │
│      testcase_version: { label: '測試案例版本', value: '...' }│
│    },                                                       │
│    basicInfo: { ... },                                      │
│    uartInfo: { ... },                                       │
│    ansibleVars: { ... },                                    │
│    otherConfig: { ... }                                     │
│  }                                                          │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│  UI 渲染                                                     │
│  ┌─ 🧪 測試案例配置 ─────────────────────┐                  │
│  │  測試案例集：testcases_demo            │                  │
│  │  測試案例版本：v1.2.3                  │                  │
│  └────────────────────────────────────────┘                  │
│  ┌─ 💻 基本資訊 ──────────────────────────┐                  │
│  │  IP 地址：10.250.71.22                 │                  │
│  │  設備號：PC-SSD-4632                   │                  │
│  └────────────────────────────────────────┘                  │
└─────────────────────────────────────────────────────────────┘
```

---

## 🧪 測試場景

### 測試 1：基本功能測試

**步驟**：
1. 打開 Ansible 配置查看器
2. 選擇主機 `Test-KVM01`
3. 查看配置顯示

**預期結果**：
- ✅ 測試案例配置 Card 顯示
- ✅ `testcase_set` 顯示為 "測試案例集"
- ✅ 其他 `testcase_*` 參數自動識別並顯示

---

### 測試 2：快取機制測試

**步驟**：
1. 第一次打開配置查看器（冷啟動）
2. 觀察載入時間和快取狀態
3. 關閉並重新打開（熱啟動）
4. 再次觀察載入時間

**預期結果**：
- ✅ 第一次：`cached: false`，可能較慢
- ✅ 第二次：`cached: true`，速度快
- ✅ 快取標籤顯示正確

---

### 測試 3：自訂參數測試

**步驟**：
1. 在 inventory 中新增自訂測試參數：
   ```ini
   Test-KVM01 testcase_set=testcases_demo testcase_new_feature=enabled
   ```
2. 清除快取
3. 重新載入配置查看器

**預期結果**：
- ✅ `testcase_new_feature` 自動顯示
- ✅ 標籤為 "測試案例 New Feature"
- ✅ 不需要修改前端代碼

---

### 測試 4：排除規則測試

**步驟**：
1. 在 inventory 中新增：
   ```ini
   Test-KVM01 testcase_set=testcases_demo test_user=testuser
   ```
2. 重新載入配置查看器

**預期結果**：
- ✅ `testcase_set` 在測試案例 Card
- ✅ `test_user` 在其他配置 Card（不在測試案例 Card）

---

## 📁 檔案結構

```
frontend/
├── src/
│   ├── services/
│   │   └── ansibleService.js              # 修改：新增辨識函數
│   └── components/
│       └── AnsibleConfig/
│           └── HostConfigTab.jsx           # 修改：使用辨識函數分類

backend/
└── library/
    └── services/
        └── ansible_inventory_service.py    # 無需修改（已有完整功能）

docs/
└── development/
    ├── TESTCASE_PARAMS_FROM_ANSIBLE_CACHE_PLAN.md  # 本文件
    ├── TESTCASE_RELATED_PARAMS_IDENTIFICATION_PLAN.md
    └── TESTCASE_BLOCK_SEPARATION_PLAN.md
```

---

## 🚀 實施步驟

### Phase 1：前端辨識函數（1-2 小時）

1. ✅ 在 `ansibleService.js` 中新增辨識函數：
   - `isTestcaseField(key)`
   - `getTestcaseFieldLabel(key)`
   - `extractTestcaseFields(config)`

2. ✅ 編寫單元測試（可選）

3. ✅ 測試辨識邏輯

---

### Phase 2：修改配置分類函數（1 小時）

1. ✅ 修改 `HostConfigTab.jsx` 中的 `categorizeConfig()` 函數
2. ✅ 使用 `extractTestcaseFields()` 提取測試案例參數
3. ✅ 確保其他分類不受影響

---

### Phase 3：UI 調整（1 小時）

1. ✅ 測試案例 Card 渲染
2. ✅ 參數顯示優化
3. ✅ 說明文字更新

---

### Phase 4：測試驗證（1 小時）

1. ✅ 功能測試
2. ✅ 快取測試
3. ✅ 自訂參數測試
4. ✅ 排除規則測試

**總計**：4-5 小時

---

## ✅ 驗收標準

### 功能驗收

- [ ] `testcase_set` 正確顯示在測試案例 Card
- [ ] 所有 `testcase_*` 參數自動識別
- [ ] 核心參數顯示友善標籤
- [ ] 自訂參數自動生成標籤
- [ ] 排除規則正確執行
- [ ] 沒有測試參數時 Card 不顯示

### 效能驗收

- [ ] 快取機制正常工作
- [ ] 第二次載入速度明顯提升
- [ ] 不影響其他配置顯示速度

### 擴展性驗收

- [ ] 新增 `testcase_*` 參數無需修改代碼
- [ ] 修改核心參數白名單後標籤正確
- [ ] 修改排除規則後過濾正確

---

## 🎯 核心優勢總結

### 為何這個方案更好？

1. **不硬解析 inventory 檔案** ✅
   - 讓 Ansible 做解析（專業的事交給專業的工具）
   - 避免維護複雜的 parser 邏輯

2. **利用現有的快取機制** ✅
   - 7 天有效期
   - 自動清理過期快取
   - 速度快

3. **前端只做過濾邏輯** ✅
   - 簡單的 JavaScript 邏輯
   - 易於維護
   - 易於擴展

4. **完全自動化** ✅
   - 新增參數自動識別
   - 無需修改代碼
   - 標籤自動生成

---

## 📚 相關文件

- [測試案例配置獨立顯示規劃](./TESTCASE_BLOCK_SEPARATION_PLAN.md)
- [測試案例相關參數辨識規劃](./TESTCASE_RELATED_PARAMS_IDENTIFICATION_PLAN.md)
- [Ansible Inventory Service 實現](../../library/services/ansible_inventory_service.py)
- [Ansible Inventory 後端實現規劃](../features/ansible-inventory/BACKEND_IMPLEMENTATION_PLAN.md)

---

**規劃日期**：2025-11-15  
**規劃者**：GitHub Copilot  
**版本**：v1.0.0  
**狀態**：✅ 規劃完成，待確認執行

---

## 🎯 總結

### 核心概念

**不要硬解析 inventory 檔案！** 

**Ansible Inventory Service 已經幫我們做好了：**
- ✅ 執行 `ansible-inventory --host <hostname>` 命令
- ✅ 解析 JSON 輸出
- ✅ 處理群組繼承和變數合併
- ✅ 快取結果（7 天）

### 我們只需要做

**在前端使用簡單的過濾邏輯：**
```javascript
// 從 API 獲取的 config 物件中過濾
const testcaseConfig = extractTestcaseFields(config);

// config 是已經由 Ansible 解析好的 JSON
// 我們只需要找出哪些 key 是 testcase_ 開頭的
```

### 優勢

- ✅ **簡單**：不需要複雜的 parser
- ✅ **快速**：使用快取機制
- ✅ **可靠**：依賴 Ansible 官方工具
- ✅ **擴展**：新參數自動識別
