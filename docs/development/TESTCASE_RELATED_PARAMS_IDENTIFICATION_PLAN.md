# 測試案例相關參數辨識規劃

## 📋 需求說明

在 Ansible Inventory 配置查看器中，需要將 `testcase_set` 及其**相關參數**獨立顯示在一個 Card Block 中。

**核心問題**：如何辨識哪些參數是與測試案例相關的？

---

## 🔍 現況分析

### 1. Inventory 檔案結構範例

根據實際的 inventory 檔案分析，主機條目格式如下：

```ini
[PQ1_3]
Test-KVM01 ansible_host=10.250.71.22 device_number=PC-SSD-4632 sample_number=SM2703AB-02003 uart_id=KVM01 macaddress=CC:28:AA:86:C3:7F testcase_set=testcases_demo
```

### 2. 主機配置參數分類

目前已知的參數類型：

| 參數名稱              | 分類           | 說明                           |
| --------------------- | -------------- | ------------------------------ |
| `ansible_host`        | 基本資訊       | 主機 IP 地址                   |
| `device_number`       | 基本資訊       | 設備編號                       |
| `sample_number`       | 基本資訊       | 樣品編號                       |
| `macaddress`          | 基本資訊       | MAC 地址                       |
| `uart_id`             | UART 連接資訊  | UART 識別碼                    |
| `uart_host`           | UART 連接資訊  | UART 主機 IP                   |
| `ansible_user`        | Ansible 變數   | SSH 使用者                     |
| `ansible_password`    | Ansible 變數   | SSH 密碼                       |
| `ansible_shell_type`  | Ansible 變數   | Shell 類型                     |
| **`testcase_set`**    | **測試案例**   | **測試案例集名稱（核心參數）** |
| `testcase_*`          | **測試案例**   | **其他 testcase_ 開頭的參數**  |
| `test_*`              | **測試案例？** | **test_ 開頭的參數（待確認）** |

---

## 🎯 辨識方法設計

### 方案 A：命名規則辨識（前綴匹配） ✅ **推薦**

#### 核心邏輯

**凡是參數名稱符合以下規則之一，即視為測試案例相關參數**：

1. **完全匹配**：
   - `testcase_set` - 測試案例集名稱（核心參數）

2. **前綴匹配**：
   - `testcase_*` - 所有以 `testcase_` 開頭的參數
   - `test_case_*` - 支援底線分隔的命名方式
   - `test_*` - 所有以 `test_` 開頭的參數（**可選，需確認**）

#### 優點
- ✅ 實現簡單，基於命名慣例
- ✅ 自動適應新增的測試相關參數
- ✅ 不需要維護固定的參數清單
- ✅ 擴展性好

#### 缺點
- ⚠️ 依賴命名規範的一致性
- ⚠️ 可能誤判（如 `test_user` 可能不是測試案例參數）

---

### 方案 B：白名單辨識（固定列表）

#### 核心邏輯

**維護一個明確的測試案例參數白名單**：

```javascript
const testcaseFields = {
    testcase_set: '測試案例集',
    testcase_path: '測試案例路徑',
    testcase_version: '測試案例版本',
    testcase_branch: '測試案例分支',
    testcase_timeout: '測試超時時間',
    testcase_retry: '測試重試次數',
    testcase_parallel: '並行測試數量',
    // ... 其他明確的測試相關參數
};
```

#### 優點
- ✅ 精確控制，不會誤判
- ✅ 可為每個參數定義友善的中文標籤

#### 缺點
- ❌ 需要手動維護參數列表
- ❌ 新增參數時需要更新代碼
- ❌ 擴展性差

---

### 方案 C：混合方式（推薦 + 白名單） 🌟 **最佳方案**

#### 核心邏輯

**結合前綴匹配和白名單，兼顧靈活性和精確性**：

1. **核心參數（白名單，必須定義標籤）**：
   ```javascript
   const coreTestcaseFields = {
       testcase_set: '測試案例集',
       testcase_path: '測試案例路徑',
       testcase_version: '測試案例版本',
   };
   ```

2. **前綴匹配（自動識別）**：
   - 匹配 `testcase_*` 前綴的參數
   - 如果不在核心參數中，使用參數名本身作為標籤

3. **排除規則（黑名單，避免誤判）**：
   ```javascript
   const excludeTestFields = [
       'test_user',        // 測試使用者（屬於 Ansible 變數）
       'test_password',    // 測試密碼（屬於 Ansible 變數）
       'test_env',         // 測試環境（可能是其他配置）
   ];
   ```

#### 優點
- ✅ 核心參數有友善標籤
- ✅ 自動適應新參數
- ✅ 可排除誤判
- ✅ 平衡靈活性和精確性

#### 缺點
- ⚠️ 實現稍複雜
- ⚠️ 需要定期檢查排除規則

---

## 📦 方案 C 詳細設計（推薦實施）

### 1. 定義辨識規則

**位置**：`frontend/src/services/ansibleService.js`

```javascript
/**
 * 測試案例相關參數辨識規則
 */

// 核心測試案例參數（明確定義標籤）
const coreTestcaseFields = {
    testcase_set: '測試案例集',
    testcase_path: '測試案例路徑',
    testcase_version: '測試案例版本',
    testcase_branch: '測試案例分支',
    testcase_timeout: '測試超時時間',
    testcase_retry: '測試重試次數',
    testcase_parallel: '並行測試數量',
    testcase_config: '測試配置文件',
    testcase_env: '測試環境變數',
};

// 測試案例參數前綴（自動匹配）
const testcasePrefixes = [
    'testcase_',     // testcase_xxx
    'test_case_',    // test_case_xxx（支援底線分隔）
];

// 排除規則（避免誤判）
const excludeTestcaseFields = [
    'test_user',      // 測試使用者（Ansible 變數）
    'test_password',  // 測試密碼（Ansible 變數）
    'test_env',       // 測試環境（其他配置）
    'test_mode',      // 測試模式（其他配置）
];

/**
 * 判斷參數是否為測試案例相關參數
 * @param {string} key - 參數名稱
 * @returns {boolean} 是否為測試案例參數
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
 * @param {string} key - 參數名稱
 * @returns {string} 顯示標籤
 */
export const getTestcaseFieldLabel = (key) => {
    // 1. 如果是核心參數，返回預定義標籤
    if (key in coreTestcaseFields) {
        return coreTestcaseFields[key];
    }
    
    // 2. 自動生成標籤：將參數名轉換為易讀格式
    // 例如：testcase_custom_param → 測試案例自訂參數
    const label = key
        .replace(/^testcase_/, '')       // 移除 testcase_ 前綴
        .replace(/^test_case_/, '')      // 移除 test_case_ 前綴
        .replace(/_/g, ' ')              // 底線轉空格
        .split(' ')
        .map(word => word.charAt(0).toUpperCase() + word.slice(1))  // 首字母大寫
        .join(' ');
    
    return `測試案例 ${label}`;
};
```

---

### 2. 修改配置分類函數

**位置**：`frontend/src/components/AnsibleConfig/HostConfigTab.jsx`

```javascript
import { isTestcaseField, getTestcaseFieldLabel } from '../../services/ansibleService';

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

    // 遍歷所有配置項目
    Object.entries(config).forEach(([key, value]) => {
        // 1. 測試案例相關參數（使用辨識函數）
        if (isTestcaseField(key)) {
            testcaseConfig[key] = {
                label: getTestcaseFieldLabel(key),
                value: value
            };
            return;
        }

        // 2. 基本資訊
        if (['ansible_host', 'device_number', 'sample_number', 'macaddress'].includes(key)) {
            basicInfo[key] = {
                label: basicInfoFieldLabels[key],
                value: value
            };
            return;
        }

        // 3. UART 連接資訊
        if (['uart_id', 'uart_host'].includes(key)) {
            uartInfo[key] = {
                label: uartFieldLabels[key],
                value: value
            };
            return;
        }

        // 4. Ansible 變數（ansible_ 開頭）
        if (key.startsWith('ansible_')) {
            ansibleVars[key] = {
                label: ansibleFieldLabels[key] || key,
                value: value
            };
            return;
        }

        // 5. 其他配置
        otherConfig[key] = {
            label: key,
            value: value
        };
    });

    return {
        testcaseConfig,
        basicInfo,
        uartInfo,
        ansibleVars,
        otherConfig,
    };
};

// 基本資訊標籤
const basicInfoFieldLabels = {
    ansible_host: 'IP 地址',
    device_number: '設備號',
    sample_number: '樣品號',
    macaddress: 'MAC 地址',
};

// UART 連接標籤
const uartFieldLabels = {
    uart_id: 'UART ID',
    uart_host: 'UART 主機',
};

// Ansible 變數標籤
const ansibleFieldLabels = {
    ansible_user: '使用者',
    ansible_password: '密碼',
    ansible_shell_type: 'Shell 類型',
    ansible_port: 'SSH 端口',
    ansible_connection: '連接類型',
};
```

---

### 3. UI 顯示範例

#### 當主機只有 `testcase_set`

```
┌─────────────────────────────────────────┐
│  🧪 測試案例配置                        │
│  ├─ 測試案例集：testcases_demo          │
└─────────────────────────────────────────┘
```

#### 當主機有多個測試相關參數

```
┌─────────────────────────────────────────┐
│  🧪 測試案例配置                        │
│  ├─ 測試案例集：testcases_demo          │
│  ├─ 測試案例路徑：/path/to/tests        │
│  ├─ 測試案例版本：v1.2.3                │
│  ├─ 測試超時時間：3600                  │
│  ├─ 測試重試次數：3                     │
│  └─ 測試案例 Custom Param：value123    │ ← 自動辨識的參數
└─────────────────────────────────────────┘
```

---

## 🧪 測試場景

### 場景 1：只有 testcase_set

**Input**：
```json
{
    "ansible_host": "10.250.71.22",
    "device_number": "PC-SSD-4632",
    "testcase_set": "testcases_demo"
}
```

**預期分類**：
- 測試案例配置：`testcase_set`
- 基本資訊：`ansible_host`, `device_number`

---

### 場景 2：多個 testcase_ 參數

**Input**：
```json
{
    "ansible_host": "10.250.71.22",
    "testcase_set": "testcases_demo",
    "testcase_version": "v1.2.3",
    "testcase_timeout": "3600",
    "testcase_custom_field": "custom_value"
}
```

**預期分類**：
- 測試案例配置：
  - `testcase_set` → "測試案例集"
  - `testcase_version` → "測試案例版本"
  - `testcase_timeout` → "測試超時時間"
  - `testcase_custom_field` → "測試案例 Custom Field"（自動生成）

---

### 場景 3：排除誤判（test_user）

**Input**：
```json
{
    "ansible_host": "10.250.71.22",
    "testcase_set": "testcases_demo",
    "test_user": "testuser",
    "test_password": "testpass"
}
```

**預期分類**：
- 測試案例配置：`testcase_set`
- Ansible 變數：`test_user`, `test_password`（不被誤判為測試案例參數）

---

### 場景 4：沒有測試案例參數

**Input**：
```json
{
    "ansible_host": "10.250.71.22",
    "device_number": "PC-SSD-4632",
    "uart_id": "KVM01"
}
```

**預期分類**：
- **測試案例配置 Card 不顯示**
- 基本資訊：`ansible_host`, `device_number`
- UART 連接資訊：`uart_id`

---

## 📊 參數命名慣例建議

### 推薦的測試案例參數命名

為了確保參數能被正確辨識，建議使用以下命名規範：

| 參數類型         | 命名格式              | 範例                          |
| ---------------- | --------------------- | ----------------------------- |
| 測試案例集       | `testcase_set`        | `testcases_demo`              |
| 測試案例路徑     | `testcase_path`       | `/workspace/tests`            |
| 測試案例版本     | `testcase_version`    | `v1.2.3`                      |
| 測試案例分支     | `testcase_branch`     | `main`                        |
| 測試超時時間     | `testcase_timeout`    | `3600`                        |
| 測試重試次數     | `testcase_retry`      | `3`                           |
| 測試並行數量     | `testcase_parallel`   | `4`                           |
| 測試配置文件     | `testcase_config`     | `pytest.ini`                  |
| 測試環境變數     | `testcase_env`        | `PYTEST_ENV=staging`          |
| 自訂測試參數     | `testcase_<name>`     | `testcase_custom_setting`     |

### 避免使用的命名（容易誤判）

| 避免使用           | 原因                           | 建議替代                    |
| ------------------ | ------------------------------ | --------------------------- |
| `test_user`        | 可能被視為測試使用者帳號       | `ansible_user` 或 `testcase_runner` |
| `test_password`    | 可能被視為測試密碼             | `ansible_password`          |
| `test_env`         | 與測試案例無直接關聯           | `testcase_env` 或 `environment` |
| `test_mode`        | 模糊不清                       | `testcase_execution_mode`   |

---

## 🔄 擴展性考量

### 如何新增測試案例參數

#### 方法 1：使用 testcase_ 前綴（推薦）

**只需在 inventory 中新增參數，無需修改代碼**：

```ini
Test-KVM01 testcase_set=testcases_demo testcase_new_param=value123
```

系統會自動辨識 `testcase_new_param`，並顯示為「測試案例 New Param」。

#### 方法 2：添加到核心參數（需要友善標籤）

**修改 `ansibleService.js`**：

```javascript
const coreTestcaseFields = {
    testcase_set: '測試案例集',
    testcase_new_param: '新測試參數',  // 新增
};
```

---

## 🎯 實施優先級

### Phase 1：基本實現（方案 A - 前綴匹配）

**時間**：1 小時

**範圍**：
- 實現 `isTestcaseField()` 函數（簡單前綴匹配）
- 修改 `categorizeConfig()` 函數
- 測試基本功能

**適用場景**：
- 只有 `testcase_set` 的情況
- 測試參數命名規範良好

---

### Phase 2：完整實現（方案 C - 混合方式）

**時間**：2-3 小時

**範圍**：
- 實現核心參數白名單
- 實現排除規則
- 自動生成標籤邏輯
- 完整測試

**適用場景**：
- 有多個測試相關參數
- 需要避免誤判
- 需要友善的中文標籤

---

### Phase 3：優化（可選）

**時間**：1-2 小時

**範圍**：
- UI 優化（圖標、顏色、佈局）
- 添加說明文字和提示
- 參數值的特殊處理（如檔案路徑可複製）

---

## ✅ 驗收標準

### 功能測試

- [ ] `testcase_set` 正確顯示在測試案例 Card
- [ ] 所有 `testcase_*` 前綴參數自動辨識
- [ ] 核心參數顯示友善的中文標籤
- [ ] 自訂參數自動生成標籤
- [ ] 排除規則正確執行（`test_user` 不被誤判）
- [ ] 沒有測試參數時，測試案例 Card 不顯示

### 擴展性測試

- [ ] 新增 `testcase_new_param` 參數後，自動辨識
- [ ] 修改核心參數白名單後，標籤正確更新
- [ ] 修改排除規則後，正確過濾

### UI 測試

- [ ] 測試案例 Card 獨立顯示
- [ ] 參數標籤易讀
- [ ] 參數值可複製
- [ ] 多個參數顯示整齊

---

## 📝 決策記錄

### 為何選擇方案 C（混合方式）？

1. **靈活性**：透過前綴匹配，自動適應新參數
2. **精確性**：透過核心參數白名單，提供友善標籤
3. **安全性**：透過排除規則，避免誤判
4. **可維護性**：規則集中管理，易於調整

### 為何不選擇方案 B（純白名單）？

- ❌ 每次新增測試參數都需要修改代碼
- ❌ 擴展性差，不靈活
- ❌ 維護成本高

### 為何不選擇方案 A（純前綴匹配）？

- ⚠️ 容易誤判（如 `test_user`）
- ⚠️ 參數標籤不友善（如 `testcase_set` → 直接顯示 key）

---

## 📚 相關文件

- [測試案例配置獨立顯示規劃](./TESTCASE_BLOCK_SEPARATION_PLAN.md)
- [Ansible Inventory 配置查看器 - 功能文檔](../features/ansible-inventory/README.md)
- [Jenkins Build 測試案例檔案顯示規劃](./JENKINS_BUILD_TESTCASE_FILES_DISPLAY_PLAN.md)

---

**規劃日期**：2025-11-15  
**規劃者**：GitHub Copilot  
**版本**：v1.0.0  
**狀態**：✅ 規劃完成，待確認執行

---

## 🎯 總結

### 推薦方案

**方案 C：混合方式（前綴匹配 + 白名單 + 排除規則）**

### 核心邏輯

1. **前綴匹配**：自動辨識 `testcase_*` 開頭的參數
2. **核心白名單**：為常用參數定義友善標籤
3. **排除規則**：避免誤判特定參數

### 實施步驟

1. ✅ 定義 `isTestcaseField()` 和 `getTestcaseFieldLabel()` 函數
2. ✅ 修改 `categorizeConfig()` 函數使用新邏輯
3. ✅ 測試各種場景
4. ✅ 優化 UI 顯示

### 預期效果

- ✅ **自動化**：新參數無需修改代碼，自動辨識
- ✅ **友善**：常用參數有清楚的中文標籤
- ✅ **精確**：避免誤判，分類清晰
- ✅ **擴展**：易於新增、調整規則
