# 測試案例配置獨立顯示規劃

## 📋 需求說明

在 **Ansible 配置查看器** 的 **HostConfigTab** 組件中，將 `testcase_set` 相關的配置**獨立成一個單獨的 Card Block**，而不是混在「其他配置」或「Ansible 變數」中。

### 當前狀況

目前在查看主機配置時，`testcase_set` 欄位混在其他配置項目中，沒有特別突出顯示。

### 目標效果

```
┌─────────────────────────────────────────┐
│  💻 基本資訊                            │
│  ├─ IP 地址：10.250.120.114             │
│  ├─ 設備號：PC-SSD-6151                 │
│  ├─ 樣品號：SSD-Y-15716                 │
│  └─ MAC 地址：90:E2:BA:ED:09:6C         │
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│  🧪 測試案例配置                 [新增]  │  ← 獨立 Block
│  ├─ 測試案例集：testcases_demo          │
│  ├─ 檔案數量：15 個                     │
│  └─ 總大小：128.5 KB                    │
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│  🔧 UART 連接資訊                       │
│  ├─ UART ID：KVM03                      │
│  └─ UART 主機：10.250.0.2               │
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│  📦 Ansible 變數                        │
│  ├─ 使用者：root                        │
│  ├─ 密碼：••••••                        │
│  └─ Shell 類型：sh                      │
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│  ⚙️  其他配置                           │
│  ├─ platform_install_vnc：False         │
│  └─ mailto：example@test.com            │
└─────────────────────────────────────────┘
```

---

## 🎯 規劃方案

### 方案 A：簡單顯示 testcase_set ✅ **推薦（第一階段）**

**顯示內容**：
- 測試案例集名稱（`testcase_set`）
- 簡單的說明文字

**優點**：
- ✅ 實現簡單快速
- ✅ 不需要額外的 API 調用
- ✅ 直接從現有配置中提取

**缺點**：
- ⚠️ 只顯示名稱，沒有額外資訊

---

### 方案 B：顯示測試案例詳細資訊（第二階段）

**顯示內容**：
- 測試案例集名稱
- 檔案數量
- 總大小
- 「查看檔案」按鈕（連結到檔案列表）

**優點**：
- ✅ 資訊更完整
- ✅ 提供檔案查看入口

**缺點**：
- ⚠️ 需要額外的 API 調用
- ⚠️ 實現較複雜

---

## 📦 方案 A 詳細設計（第一階段）

### 1. 修改 HostConfigTab 組件

**位置**：`frontend/src/components/AnsibleConfig/HostConfigTab.jsx`

#### 1.1 分類邏輯調整

在 `formatConfigForDisplay` 函數中，將 `testcase_set` 單獨分類：

```javascript
// 當前分類邏輯
const importantFields = {
    ansible_host: 'IP 地址',
    device_number: '設備號',
    sample_number: '樣品號',
    macaddress: 'MAC 地址',
    // UART 連接資訊
    uart_id: 'UART ID',
    uart_host: 'UART 主機',
    // Ansible 變數
    ansible_user: '使用者',
    ansible_password: '密碼',
    ansible_shell_type: 'Shell 類型',
    testcase_set: '測試案例集',  // ← 從這裡移除
    // ...
};
```

**修改為**：

```javascript
// 新增：測試案例相關欄位（獨立分類）
const testcaseFields = {
    testcase_set: '測試案例集',
};

// 基本資訊欄位
const basicInfoFields = {
    ansible_host: 'IP 地址',
    device_number: '設備號',
    sample_number: '樣品號',
    macaddress: 'MAC 地址',
};

// UART 連接資訊
const uartFields = {
    uart_id: 'UART ID',
    uart_host: 'UART 主機',
};

// Ansible 變數
const ansibleFields = {
    ansible_user: '使用者',
    ansible_password: '密碼',
    ansible_shell_type: 'Shell 類型',
};

// 其他配置（動態）
// 排除以上所有已定義的欄位
```

#### 1.2 配置項目分組函數

新增一個函數來分組配置項目：

```javascript
/**
 * 將主機配置分組為不同的區塊
 * @param {object} config - 主機配置物件
 * @returns {object} 分組後的配置
 */
const categorizeConfig = (config) => {
    if (!config) return null;

    // 測試案例配置
    const testcaseConfig = {};
    Object.entries(testcaseFields).forEach(([key, label]) => {
        if (config[key] !== undefined) {
            testcaseConfig[key] = {
                label,
                value: config[key],
            };
        }
    });

    // 基本資訊
    const basicInfo = {};
    Object.entries(basicInfoFields).forEach(([key, label]) => {
        if (config[key] !== undefined) {
            basicInfo[key] = {
                label,
                value: config[key],
            };
        }
    });

    // UART 連接資訊
    const uartInfo = {};
    Object.entries(uartFields).forEach(([key, label]) => {
        if (config[key] !== undefined) {
            uartInfo[key] = {
                label,
                value: config[key],
            };
        }
    });

    // Ansible 變數
    const ansibleVars = {};
    Object.entries(ansibleFields).forEach(([key, label]) => {
        if (config[key] !== undefined) {
            ansibleVars[key] = {
                label,
                value: config[key],
            };
        }
    });

    // 其他配置（排除已分類的）
    const allDefinedKeys = [
        ...Object.keys(testcaseFields),
        ...Object.keys(basicInfoFields),
        ...Object.keys(uartFields),
        ...Object.keys(ansibleFields),
    ];

    const otherConfig = {};
    Object.entries(config).forEach(([key, value]) => {
        if (!allDefinedKeys.includes(key)) {
            otherConfig[key] = {
                label: key,
                value: value,
            };
        }
    });

    return {
        testcaseConfig,
        basicInfo,
        uartInfo,
        ansibleVars,
        otherConfig,
    };
};
```

#### 1.3 渲染測試案例 Card

在組件的 JSX 中，新增測試案例 Card：

```javascript
// 在 loadHostConfig 成功後
const loadHostConfig = async (hostname) => {
    // ... 現有邏輯
    
    const config = result.config;
    setHostConfig(config);
    
    // 分組配置
    const categorized = categorizeConfig(config);
    setCategorizedConfig(categorized);
};

// JSX 渲染
return (
    <div>
        {/* 主機選擇下拉框 */}
        <Select ...>...</Select>

        {loading && <Spin />}

        {!loading && hostConfig && (
            <Space direction="vertical" size="large" style={{ width: '100%' }}>
                
                {/* 基本資訊 */}
                {Object.keys(categorizedConfig.basicInfo).length > 0 && (
                    <Card 
                        title={
                            <Space>
                                <DesktopOutlined style={{ color: '#1890ff' }} />
                                <Text strong>基本資訊</Text>
                            </Space>
                        } 
                        size="small"
                    >
                        <Descriptions column={2} bordered size="small">
                            {Object.entries(categorizedConfig.basicInfo).map(([key, item]) => (
                                <Descriptions.Item key={key} label={item.label}>
                                    <Text copyable={item.value !== 'N/A'}>
                                        {item.value}
                                    </Text>
                                </Descriptions.Item>
                            ))}
                        </Descriptions>
                    </Card>
                )}

                {/* 🧪 測試案例配置（新增獨立 Block） */}
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
                            borderLeft: '3px solid #52c41a',  // 綠色左邊框突出顯示
                        }}
                    >
                        <Descriptions column={1} bordered size="small">
                            {Object.entries(categorizedConfig.testcaseConfig).map(([key, item]) => (
                                <Descriptions.Item 
                                    key={key} 
                                    label={
                                        <Space>
                                            <Text strong>{item.label}</Text>
                                        </Space>
                                    }
                                >
                                    <Space>
                                        <Tag color="green" icon={<ExperimentOutlined />}>
                                            {item.value}
                                        </Tag>
                                        <Text type="secondary" style={{ fontSize: 12 }}>
                                            測試案例集名稱
                                        </Text>
                                    </Space>
                                </Descriptions.Item>
                            ))}
                        </Descriptions>
                        
                        {/* 說明文字 */}
                        <Alert
                            message="測試案例說明"
                            description="此配置指定了該主機使用的測試案例集合。測試案例檔案位於 workspace 目錄下。"
                            type="info"
                            showIcon
                            style={{ marginTop: 12 }}
                        />
                    </Card>
                )}

                {/* UART 連接資訊 */}
                {Object.keys(categorizedConfig.uartInfo).length > 0 && (
                    <Card title="🔧 UART 連接資訊" size="small">
                        <Descriptions column={2} bordered size="small">
                            {Object.entries(categorizedConfig.uartInfo).map(([key, item]) => (
                                <Descriptions.Item key={key} label={item.label}>
                                    <Text copyable>{item.value}</Text>
                                </Descriptions.Item>
                            ))}
                        </Descriptions>
                    </Card>
                )}

                {/* Ansible 變數 */}
                {Object.keys(categorizedConfig.ansibleVars).length > 0 && (
                    <Card title="📦 Ansible 變數" size="small">
                        <Descriptions column={2} bordered size="small">
                            {Object.entries(categorizedConfig.ansibleVars).map(([key, item]) => (
                                <Descriptions.Item key={key} label={item.label}>
                                    <Text copyable>{item.value}</Text>
                                </Descriptions.Item>
                            ))}
                        </Descriptions>
                    </Card>
                )}

                {/* 其他配置 */}
                {Object.keys(categorizedConfig.otherConfig).length > 0 && (
                    <Card title="⚙️ 其他配置" size="small">
                        <Descriptions column={2} bordered size="small">
                            {Object.entries(categorizedConfig.otherConfig).map(([key, item]) => (
                                <Descriptions.Item key={key} label={item.label}>
                                    <Text copyable>{item.value}</Text>
                                </Descriptions.Item>
                            ))}
                        </Descriptions>
                    </Card>
                )}

                {/* 完整 JSON 配置 */}
                <Collapse>
                    <Panel header={<Space><CodeOutlined /><Text strong>完整配置 (JSON)</Text></Space>} key="json">
                        <Paragraph>
                            <pre style={{ 
                                background: '#f5f5f5', 
                                padding: '16px', 
                                borderRadius: '4px',
                                maxHeight: '400px',
                                overflow: 'auto',
                                fontSize: '12px',
                            }}>
                                {JSON.stringify(hostConfig, null, 2)}
                            </pre>
                        </Paragraph>
                    </Panel>
                </Collapse>
            </Space>
        )}
    </div>
);
```

---

## 🎨 UI 設計細節

### 測試案例 Card 樣式

```javascript
<Card 
    title={
        <Space>
            <ExperimentOutlined style={{ color: '#52c41a' }} />
            <Text strong>測試案例配置</Text>
        </Space>
    } 
    size="small"
    style={{
        borderLeft: '3px solid #52c41a',  // 綠色左邊框
        backgroundColor: '#f6ffed',       // 淺綠色背景（可選）
    }}
>
    <Descriptions column={1} bordered size="small">
        <Descriptions.Item label={<Text strong>測試案例集</Text>}>
            <Space>
                <Tag color="green" icon={<ExperimentOutlined />}>
                    testcases_demo
                </Tag>
                <Text type="secondary" style={{ fontSize: 12 }}>
                    測試案例集名稱
                </Text>
            </Space>
        </Descriptions.Item>
    </Descriptions>
    
    {/* 說明文字 */}
    <Alert
        message="測試案例說明"
        description="此配置指定了該主機使用的測試案例集合。測試案例檔案位於 workspace 目錄下。"
        type="info"
        showIcon
        style={{ marginTop: 12 }}
    />
</Card>
```

### 顏色方案

- **圖標顏色**：`#52c41a`（綠色） - 代表測試
- **標籤顏色**：`green` - 與測試相關
- **邊框**：左側 3px 綠色邊框，突出顯示
- **背景**：`#f6ffed`（淺綠色，可選）

---

## 📦 完整程式碼範例

### HostConfigTab.jsx 修改

```javascript
import React, { useState, useEffect } from 'react';
import { 
    Select, 
    Card, 
    Descriptions, 
    Spin, 
    Alert, 
    Collapse, 
    Typography,
    Space,
    Tag,
    Empty,
} from 'antd';
import { 
    DesktopOutlined, 
    CodeOutlined,
    ExperimentOutlined,  // 新增
} from '@ant-design/icons';
import { getHostConfig } from '../../services/ansibleService';

const { Panel } = Collapse;
const { Paragraph, Text } = Typography;
const { Option } = Select;

// 欄位分類定義
const testcaseFields = {
    testcase_set: '測試案例集',
};

const basicInfoFields = {
    ansible_host: 'IP 地址',
    device_number: '設備號',
    sample_number: '樣品號',
    macaddress: 'MAC 地址',
};

const uartFields = {
    uart_id: 'UART ID',
    uart_host: 'UART 主機',
};

const ansibleFields = {
    ansible_user: '使用者',
    ansible_password: '密碼',
    ansible_shell_type: 'Shell 類型',
};

/**
 * 將主機配置分組為不同的區塊
 */
const categorizeConfig = (config) => {
    if (!config) return null;

    const testcaseConfig = {};
    const basicInfo = {};
    const uartInfo = {};
    const ansibleVars = {};
    const otherConfig = {};

    // 提取測試案例配置
    Object.entries(testcaseFields).forEach(([key, label]) => {
        if (config[key] !== undefined) {
            testcaseConfig[key] = { label, value: config[key] };
        }
    });

    // 提取基本資訊
    Object.entries(basicInfoFields).forEach(([key, label]) => {
        if (config[key] !== undefined) {
            basicInfo[key] = { label, value: config[key] };
        }
    });

    // 提取 UART 資訊
    Object.entries(uartFields).forEach(([key, label]) => {
        if (config[key] !== undefined) {
            uartInfo[key] = { label, value: config[key] };
        }
    });

    // 提取 Ansible 變數
    Object.entries(ansibleFields).forEach(([key, label]) => {
        if (config[key] !== undefined) {
            ansibleVars[key] = { label, value: config[key] };
        }
    });

    // 提取其他配置
    const allDefinedKeys = [
        ...Object.keys(testcaseFields),
        ...Object.keys(basicInfoFields),
        ...Object.keys(uartFields),
        ...Object.keys(ansibleFields),
    ];

    Object.entries(config).forEach(([key, value]) => {
        if (!allDefinedKeys.includes(key)) {
            otherConfig[key] = { label: key, value };
        }
    });

    return {
        testcaseConfig,
        basicInfo,
        uartInfo,
        ansibleVars,
        otherConfig,
    };
};

const HostConfigTab = ({ jobId, hosts, initialHostname = null }) => {
    const [selectedHost, setSelectedHost] = useState(initialHostname);
    const [hostConfig, setHostConfig] = useState(null);
    const [categorizedConfig, setCategorizedConfig] = useState(null);
    const [loading, setLoading] = useState(false);

    // 載入主機配置
    const loadHostConfig = async (hostname) => {
        if (!hostname) return;

        setLoading(true);
        try {
            const result = await getHostConfig(jobId, hostname);
            
            if (result.success) {
                const config = result.config;
                setHostConfig(config);
                setCategorizedConfig(categorizeConfig(config));
            }
        } catch (error) {
            console.error('載入主機配置失敗:', error);
        } finally {
            setLoading(false);
        }
    };

    // 初始載入
    useEffect(() => {
        if (initialHostname) {
            setSelectedHost(initialHostname);
            loadHostConfig(initialHostname);
        }
    }, [initialHostname]);

    // 主機切換
    const handleHostChange = (hostname) => {
        setSelectedHost(hostname);
        loadHostConfig(hostname);
    };

    return (
        <div>
            {/* 主機選擇 */}
            <Select
                value={selectedHost}
                onChange={handleHostChange}
                style={{ width: '100%', marginBottom: 16 }}
                placeholder="請選擇主機"
            >
                {hosts.map(host => (
                    <Option key={host.hostname} value={host.hostname}>
                        {host.hostname} ({host.ansible_host})
                    </Option>
                ))}
            </Select>

            {/* 載入中 */}
            {loading && (
                <div style={{ textAlign: 'center', padding: '50px' }}>
                    <Spin size="large" />
                </div>
            )}

            {/* 配置顯示 */}
            {!loading && categorizedConfig && (
                <Space direction="vertical" size="large" style={{ width: '100%' }}>
                    
                    {/* 基本資訊 */}
                    {Object.keys(categorizedConfig.basicInfo).length > 0 && (
                        <Card 
                            title={
                                <Space>
                                    <DesktopOutlined style={{ color: '#1890ff' }} />
                                    <Text strong>基本資訊</Text>
                                </Space>
                            } 
                            size="small"
                        >
                            <Descriptions column={2} bordered size="small">
                                {Object.entries(categorizedConfig.basicInfo).map(([key, item]) => (
                                    <Descriptions.Item key={key} label={item.label}>
                                        <Text copyable={item.value !== 'N/A'}>
                                            {item.value}
                                        </Text>
                                    </Descriptions.Item>
                                ))}
                            </Descriptions>
                        </Card>
                    )}

                    {/* 🧪 測試案例配置（新增獨立 Block） */}
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
                            <Descriptions column={1} bordered size="small">
                                {Object.entries(categorizedConfig.testcaseConfig).map(([key, item]) => (
                                    <Descriptions.Item 
                                        key={key} 
                                        label={<Text strong>{item.label}</Text>}
                                    >
                                        <Space>
                                            <Tag color="green" icon={<ExperimentOutlined />}>
                                                {item.value}
                                            </Tag>
                                            <Text type="secondary" style={{ fontSize: 12 }}>
                                                測試案例集名稱
                                            </Text>
                                        </Space>
                                    </Descriptions.Item>
                                ))}
                            </Descriptions>
                            
                            {/* 說明文字 */}
                            <Alert
                                message="測試案例說明"
                                description="此配置指定了該主機使用的測試案例集合。測試案例檔案位於 workspace 目錄下。"
                                type="info"
                                showIcon
                                style={{ marginTop: 12 }}
                            />
                        </Card>
                    )}

                    {/* UART 連接資訊 */}
                    {Object.keys(categorizedConfig.uartInfo).length > 0 && (
                        <Card title="🔧 UART 連接資訊" size="small">
                            <Descriptions column={2} bordered size="small">
                                {Object.entries(categorizedConfig.uartInfo).map(([key, item]) => (
                                    <Descriptions.Item key={key} label={item.label}>
                                        <Text copyable>{item.value}</Text>
                                    </Descriptions.Item>
                                ))}
                            </Descriptions>
                        </Card>
                    )}

                    {/* Ansible 變數 */}
                    {Object.keys(categorizedConfig.ansibleVars).length > 0 && (
                        <Card title="📦 Ansible 變數" size="small">
                            <Descriptions column={2} bordered size="small">
                                {Object.entries(categorizedConfig.ansibleVars).map(([key, item]) => (
                                    <Descriptions.Item key={key} label={item.label}>
                                        <Text copyable>{item.value}</Text>
                                    </Descriptions.Item>
                                ))}
                            </Descriptions>
                        </Card>
                    )}

                    {/* 其他配置 */}
                    {Object.keys(categorizedConfig.otherConfig).length > 0 && (
                        <Card title="⚙️ 其他配置" size="small">
                            <Descriptions column={2} bordered size="small">
                                {Object.entries(categorizedConfig.otherConfig).map(([key, item]) => (
                                    <Descriptions.Item key={key} label={item.label}>
                                        <Text copyable>{item.value}</Text>
                                    </Descriptions.Item>
                                ))}
                            </Descriptions>
                        </Card>
                    )}

                    {/* 完整 JSON 配置 */}
                    <Collapse>
                        <Panel 
                            header={
                                <Space>
                                    <CodeOutlined />
                                    <Text strong>完整配置 (JSON)</Text>
                                </Space>
                            } 
                            key="json"
                        >
                            <Paragraph>
                                <pre style={{ 
                                    background: '#f5f5f5', 
                                    padding: '16px', 
                                    borderRadius: '4px',
                                    maxHeight: '400px',
                                    overflow: 'auto',
                                    fontSize: '12px',
                                }}>
                                    {JSON.stringify(hostConfig, null, 2)}
                                </pre>
                            </Paragraph>
                        </Panel>
                    </Collapse>
                </Space>
            )}

            {/* 未選擇主機 */}
            {!loading && !selectedHost && (
                <Empty 
                    description="請選擇要查看配置的主機"
                    image={Empty.PRESENTED_IMAGE_SIMPLE}
                />
            )}
        </div>
    );
};

export default HostConfigTab;
```

---

## 🧪 測試計劃

### 手動測試步驟

1. **訪問 RVT 分析頁面**
   - URL: `http://localhost/rvt-analytics?tab=details`

2. **展開一個 Job**
   - 選擇 `SAF3101_KVM03` 或任何有 testcase_set 的 Job

3. **點擊「配置」按鈕**
   - 打開 Ansible 配置查看器

4. **檢查配置顯示**
   - ✅ **測試案例配置** Card 是否獨立顯示
   - ✅ 是否有綠色左邊框
   - ✅ testcase_set 是否以 Tag 形式顯示
   - ✅ 是否有說明文字
   - ✅ 測試案例配置在「基本資訊」和「UART 連接資訊」之間

5. **檢查其他配置**
   - ✅ 基本資訊 Card 正常
   - ✅ UART 連接資訊 Card 正常
   - ✅ Ansible 變數 Card 正常
   - ✅ 其他配置 Card 正常（testcase_set 不在其中）

6. **檢查沒有 testcase_set 的主機**
   - ✅ 測試案例 Card 不顯示
   - ✅ 其他配置正常顯示

---

## 📊 修改影響範圍

### 影響的檔案

| 檔案 | 修改內容 | 影響範圍 |
|------|---------|---------|
| `frontend/src/components/AnsibleConfig/HostConfigTab.jsx` | 新增測試案例 Card、修改分類邏輯 | 中等 |

### 不影響的功能

- ✅ Ansible Inventory API（後端不變）
- ✅ 主機列表顯示
- ✅ 群組樹顯示
- ✅ 快取機制
- ✅ 其他頁面功能

---

## 🚀 實施步驟

### Phase 1：基本實現（1-2 小時）

1. ✅ 修改 `HostConfigTab.jsx`
2. ✅ 定義欄位分類
3. ✅ 實現 `categorizeConfig` 函數
4. ✅ 新增測試案例 Card
5. ✅ 調整 UI 樣式

### Phase 2：測試驗證（30 分鐘）

1. ✅ 手動測試各種情境
2. ✅ 檢查 UI 顯示
3. ✅ 驗證分類邏輯

### Phase 3：優化調整（30 分鐘）

1. ✅ 調整顏色和樣式
2. ✅ 優化說明文字
3. ✅ 確認沒有 Bug

**總計**：2-3 小時

---

## 📝 後續優化（方案 B - 可選）

### 顯示測試案例詳細資訊

在測試案例 Card 中新增：

```javascript
{/* 測試案例配置 - 增強版 */}
<Card 
    title={
        <Space>
            <ExperimentOutlined style={{ color: '#52c41a' }} />
            <Text strong>測試案例配置</Text>
        </Space>
    } 
    size="small"
    style={{ borderLeft: '3px solid #52c41a' }}
    extra={
        <Button 
            size="small" 
            type="link"
            icon={<FolderOpenOutlined />}
            onClick={() => handleViewTestCaseFiles(buildId)}
        >
            查看檔案
        </Button>
    }
>
    <Descriptions column={2} bordered size="small">
        <Descriptions.Item label="測試案例集">
            <Tag color="green" icon={<ExperimentOutlined />}>
                {testcase_set}
            </Tag>
        </Descriptions.Item>
        <Descriptions.Item label="檔案數量">
            <Text>{fileCount} 個</Text>
        </Descriptions.Item>
        <Descriptions.Item label="總大小" span={2}>
            <Text>{totalSize}</Text>
        </Descriptions.Item>
    </Descriptions>
    
    <Alert
        message="測試案例說明"
        description="此配置指定了該主機使用的測試案例集合。點擊「查看檔案」可查看詳細的測試檔案列表。"
        type="info"
        showIcon
        style={{ marginTop: 12 }}
    />
</Card>
```

**需要**：
- 新增 API 調用獲取檔案資訊
- 實現「查看檔案」功能
- 連結到檔案列表頁面

---

## ✅ 驗收標準

### 功能

- [ ] 測試案例配置獨立顯示為一個 Card
- [ ] Card 有綠色左邊框
- [ ] testcase_set 以 Tag 形式顯示
- [ ] 有說明文字
- [ ] 沒有 testcase_set 時不顯示該 Card
- [ ] testcase_set 不出現在其他配置中

### UI/UX

- [ ] Card 標題清晰（圖標 + 文字）
- [ ] 顏色方案統一（綠色主題）
- [ ] 與其他 Card 風格一致
- [ ] 說明文字友善易懂

### 測試

- [ ] 有 testcase_set 的主機正常顯示
- [ ] 沒有 testcase_set 的主機不顯示該 Card
- [ ] 切換不同主機正常
- [ ] 完整 JSON 中仍包含 testcase_set

---

## 📚 相關文件

- [Ansible Inventory 配置查看器 - 功能文檔](../features/ansible-inventory/README.md)
- [Ansible Inventory 測試指南](../features/ansible-inventory/TESTING_GUIDE.md)
- [Hostname 過濾功能更新](../features/ansible-inventory/HOSTNAME_FILTER_UPDATE.md)

---

**規劃日期**：2025-11-15  
**規劃者**：GitHub Copilot  
**版本**：v1.0.0  
**狀態**：✅ 規劃完成，待確認執行

---

## 🎯 總結

### 核心變更

1. **新增欄位分類**：將 `testcase_set` 從其他配置中分離
2. **新增 `categorizeConfig` 函數**：自動分組配置項目
3. **新增測試案例 Card**：獨立顯示區塊，綠色主題
4. **調整渲染邏輯**：按分類渲染不同的 Card

### 預期效果

- ✅ 測試案例配置更加突出
- ✅ UI 更清晰、更有條理
- ✅ 使用者能快速找到測試案例資訊
- ✅ 為後續功能擴展（查看檔案）打下基礎
