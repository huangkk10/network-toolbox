/**
 * Ansible Inventory API 服務
 * 
 * 提供 Ansible Inventory 相關的所有 API 請求方法
 */

import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || '/api';

/**
 * 獲取 Job 的完整 Ansible Inventory
 * @param {number} jobId - Jenkins Job ID
 * @param {boolean} useCache - 是否使用快取（預設 true）
 * @returns {Promise} API 響應
 */
export const getAnsibleInventory = async (jobId, useCache = true) => {
    try {
        const response = await axios.get(
            `${API_BASE_URL}/jenkins-jobs/${jobId}/ansible-inventory/`,
            {
                params: { use_cache: useCache }
            }
        );
        return response.data;
    } catch (error) {
        console.error('Failed to fetch Ansible inventory:', error);
        throw error;
    }
};

/**
 * 獲取主機列表
 * @param {number} jobId - Jenkins Job ID
 * @param {boolean} useCache - 是否使用快取（預設 true）
 * @returns {Promise} API 響應
 */
export const getAnsibleHosts = async (jobId, useCache = true) => {
    try {
        const response = await axios.get(
            `${API_BASE_URL}/jenkins-jobs/${jobId}/ansible-inventory/hosts/`,
            {
                params: { use_cache: useCache }
            }
        );
        return response.data;
    } catch (error) {
        console.error('Failed to fetch Ansible hosts:', error);
        throw error;
    }
};

/**
 * 獲取特定主機的配置
 * @param {number} jobId - Jenkins Job ID
 * @param {string} hostname - 主機名稱
 * @param {boolean} useCache - 是否使用快取（預設 true）
 * @returns {Promise} API 響應
 */
export const getHostConfig = async (jobId, hostname, useCache = true) => {
    try {
        const response = await axios.get(
            `${API_BASE_URL}/jenkins-jobs/${jobId}/ansible-inventory/hosts/${hostname}/`,
            {
                params: { use_cache: useCache }
            }
        );
        return response.data;
    } catch (error) {
        console.error(`Failed to fetch config for host ${hostname}:`, error);
        throw error;
    }
};

/**
 * 獲取快取統計資訊
 * @param {number} jobId - Jenkins Job ID
 * @returns {Promise} API 響應
 */
export const getCacheStatistics = async (jobId) => {
    try {
        const response = await axios.get(
            `${API_BASE_URL}/jenkins-jobs/${jobId}/ansible-inventory/cache/statistics/`
        );
        return response.data;
    } catch (error) {
        console.error('Failed to fetch cache statistics:', error);
        throw error;
    }
};

/**
 * 清除快取
 * @param {number} jobId - Jenkins Job ID
 * @param {string} cacheType - 快取類型 ('all', 'inventory', 'hosts', 'host')
 * @param {string} hostname - 主機名稱（cacheType='host' 時必填）
 * @returns {Promise} API 響應
 */
export const clearCache = async (jobId, cacheType = 'all', hostname = null) => {
    try {
        const params = { cache_type: cacheType };
        if (hostname) {
            params.hostname = hostname;
        }
        
        const response = await axios.delete(
            `${API_BASE_URL}/jenkins-jobs/${jobId}/ansible-inventory/cache/`,
            { params }
        );
        return response.data;
    } catch (error) {
        console.error('Failed to clear cache:', error);
        throw error;
    }
};

/**
 * 解析 Inventory 資料為主機列表
 * @param {object} inventoryData - Inventory API 響應資料
 * @returns {Array} 主機列表
 */
export const parseInventoryToHostList = (inventoryData) => {
    if (!inventoryData || !inventoryData.data || !inventoryData.data._meta) {
        return [];
    }

    const hostvars = inventoryData.data._meta.hostvars;
    const hosts = [];

    // 提取每個主機的基本資訊
    Object.entries(hostvars).forEach(([hostname, vars]) => {
        hosts.push({
            key: hostname,
            hostname: hostname,
            ansible_host: vars.ansible_host || 'N/A',
            device_number: vars.device_number || 'N/A',
            macaddress: vars.macaddress || 'N/A',
            ansible_user: vars.ansible_user || 'N/A',
            // 找出該主機所屬的群組
            groups: findHostGroups(hostname, inventoryData.data),
        });
    });

    return hosts;
};

/**
 * 找出主機所屬的所有群組
 * @param {string} hostname - 主機名稱
 * @param {object} inventoryData - Inventory 資料
 * @returns {Array} 群組名稱陣列
 */
const findHostGroups = (hostname, inventoryData) => {
    const groups = [];
    
    Object.entries(inventoryData).forEach(([groupName, groupData]) => {
        if (groupName === '_meta') return;
        
        if (groupData.hosts && groupData.hosts.includes(hostname)) {
            groups.push(groupName);
        }
    });
    
    return groups;
};

/**
 * 解析 Inventory 資料為群組樹狀結構
 * @param {object} inventoryData - Inventory API 響應資料
 * @returns {Array} 樹狀資料
 */
export const parseInventoryToGroupTree = (inventoryData) => {
    if (!inventoryData || !inventoryData.data) {
        return [];
    }

    const treeData = [];

    Object.entries(inventoryData.data).forEach(([groupName, groupData]) => {
        if (groupName === '_meta') return;

        const hosts = groupData.hosts || [];
        
        treeData.push({
            title: `${groupName} (${hosts.length} 個主機)`,
            key: groupName,
            icon: '📁',
            children: hosts.map(hostname => ({
                title: hostname,
                key: `${groupName}-${hostname}`,
                icon: '💻',
                isLeaf: true,
                hostname: hostname, // 保存主機名稱供後續使用
            })),
        });
    });

    return treeData;
};

/**
 * 格式化配置資料為 Descriptions 所需格式
 * 注意：此函數會自動排除測試案例參數（testcase_*），這些參數應使用 extractTestcaseFields() 獲取
 * 
 * @param {object} config - 主機配置物件
 * @returns {Array} 格式化後的配置項目（不包含測試案例參數）
 */
export const formatConfigForDisplay = (config) => {
    if (!config) return [];

    // 定義重要欄位的顯示順序和中文名稱
    const importantFields = {
        // 主機基本資訊（顯示在主機資訊區塊）
        ansible_host: 'IP 地址',
        device_number: '設備號',
        sample_number: '樣品號',
        macaddress: 'MAC 地址',
        ansible_user: '使用者',
        ansible_password: '密碼',
        ansible_port: 'SSH 端口',
        // UART 連接資訊（獨立區塊）- 使用英文標籤
        uart_id: 'UART ID',
        uart_host: 'UART Host',
        UART_IP: 'UART IP',
        // UART_HOSTNAME 已移除（與 uart_host 重複，顯示相同內容）
        uart_logger_lowpower_enabled: 'UART Logger Low Power',
        uart_logger_parser_hp_enabled: 'UART Logger Parser HP',
        uart_logger_upload_dir: 'UART Logger Upload Dir',
        uart_self_test_enabled: 'UART Self Test Enabled',
        // JTAG 配置（獨立區塊）
        enable_jtag_dump: '啟用 JTAG Dump',
        jtag_serial: 'JTAG 序列號',
        jtag_dump_upload_dir: 'JTAG Dump 上傳目錄',
        // MDT 配置（獨立區塊）
        mdt_driver_root: 'MDT Driver Root',
        mdt_post_install_timeout_min: 'MDT Post Install Timeout (min)',
        mdt_winpe_install_timeout_min: 'MDT WinPE Install Timeout (min)',
        mdt_os_build: 'MDT OS Build',
        mdt_web: 'MDT Web',
        // NAS 配置（獨立區塊）
        nas_user: 'NAS User',
        nas_password: 'NAS Password',
        // SAF 配置（獨立區塊）
        saf_comment: 'SAF Comment',
        saf_comment_full: 'SAF Comment Full',
        saf_enabled: 'SAF Enabled',
        saf_mode: 'SAF Mode',
        // Firmware 相關配置（顯示在其他 Ansible 配置區塊）
        firmware_sku_keyword: 'Firmware SKU 關鍵字',
        firmware_polling_dir: 'Firmware 輪詢目錄',
        // 其他 Ansible 變數
        ansible_shell_type: 'Shell 類型',
        // testcase_set 已移至測試案例配置區塊，不再顯示在這裡
        // testcase_set: '測試案例集',
        platform_install_vnc: 'VNC 安裝',
        mailto: '郵件通知',
    };

    const items = [];
    
    /**
     * 判斷是否為測試案例配置欄位
     * 測試案例配置的特徵：
     * 1. key 為 'testcase_set'（指定當前使用的測試案例）
     * 2. value 為 array of objects，且包含測試案例配置的典型欄位（id, enabled, script_exec 等）
     * 3. key 以 testcase_ 開頭
     */
    const isTestcaseConfigField = (key, value) => {
        // 1. testcase_set 本身
        if (key === 'testcase_set') {
            return true;
        }
        
        // 2. 值為 array 且包含測試案例配置
        if (Array.isArray(value) && value.length > 0) {
            const firstItem = value[0];
            if (typeof firstItem === 'object' && firstItem !== null) {
                // 檢查是否有測試案例配置的典型欄位
                const testcaseFields = ['id', 'enabled', 'script_exec', 'log_path', 'timeout', 'archive_patterns'];
                const hasTestcaseFields = testcaseFields.some(field => field in firstItem);
                if (hasTestcaseFields) {
                    return true;
                }
            }
        }
        
        // 3. 以 testcase_ 開頭的欄位
        return isTestcaseField(key);
    };

    // 先添加重要欄位（排除測試案例配置）
    Object.entries(importantFields).forEach(([key, label]) => {
        if (config[key] !== undefined && !isTestcaseConfigField(key, config[key])) {
            items.push({
                key: key,
                label: label,
                value: formatValue(config[key]),
            });
        }
    });

    // 再添加其他欄位（排除已顯示的 & 排除測試案例配置）
    Object.entries(config).forEach(([key, value]) => {
        if (!importantFields[key] && !isTestcaseConfigField(key, value)) {
            items.push({
                key: key,
                label: key,
                value: formatValue(value),
            });
        }
    });

    return items;
};

/**
 * 格式化值的顯示
 * @param {*} value - 值
 * @returns {string|React.Element} 格式化後的字串或 React 元素
 */
const formatValue = (value) => {
    if (value === null || value === undefined) {
        return 'N/A';
    }
    if (typeof value === 'boolean') {
        return value ? '是' : '否';
    }
    if (Array.isArray(value)) {
        // 檢查是否為測試案例配置（array of objects）
        if (value.length > 0 && typeof value[0] === 'object' && value[0] !== null) {
            // 檢查是否有測試案例配置的典型欄位
            const testcaseFields = ['id', 'enabled', 'script_exec', 'log_path', 'timeout'];
            const hasTestcaseFields = testcaseFields.some(field => field in value[0]);
            
            if (hasTestcaseFields) {
                // 測試案例配置：顯示摘要資訊
                const items = value.map(item => {
                    const id = item.id || 'N/A';
                    const enabled = item.enabled ? '✓' : '✗';
                    return `[${enabled}] ${id}`;
                }).join(', ');
                return `${value.length} 個測試項目: ${items}`;
            }
        }
        
        // 一般 array：嘗試 join
        try {
            return value.map(v => {
                if (typeof v === 'object') {
                    return JSON.stringify(v);
                }
                return String(v);
            }).join(', ');
        } catch (e) {
            return JSON.stringify(value);
        }
    }
    if (typeof value === 'object') {
        return JSON.stringify(value, null, 2);
    }
    return String(value);
};

// ========================================
// 測試案例參數辨識函數
// ========================================

/**
 * 核心測試案例參數（有預定義的友善標籤）
 */
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

/**
 * 測試案例參數前綴（自動匹配）
 */
const testcasePrefixes = [
    'testcase_',     // testcase_xxx
    'test_case_',    // test_case_xxx（支援底線分隔）
];

/**
 * 排除規則（避免誤判為測試案例參數）
 */
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
    
    // 2. 特殊處理：測試案例配置通常是測試項目名稱（如 S3_BIT, SST_Lv1）
    // 直接使用原始名稱，添加 "測試項目" 前綴
    // 不要移除前綴，保持原始名稱
    
    // 3. 自動生成標籤：底線轉空格，首字母大寫
    let label = key
        .split('_')
        .map(word => word.charAt(0).toUpperCase() + word.slice(1))
        .join(' ');
    
    return label;
};

/**
 * 從測試案例集名稱中提取可能的前綴
 * 
 * @param {string} testcaseSet - 測試案例集名稱（例如：'S3_BIT', 'SST_Lv1'）
 * @returns {Array} 前綴陣列
 * 
 * @example
 * extractTestcasePrefixes('S3_BIT')
 * // 返回：['S3_', 'BIT_', 'S3_BIT_']
 * 
 * extractTestcasePrefixes('SST_Performance_Lv1')
 * // 返回：['SST_', 'Performance_', 'Lv1_', 'SST_Performance_', 'Performance_Lv1_', 'SST_Performance_Lv1_']
 */
const extractTestcasePrefixes = (testcaseSet) => {
    if (!testcaseSet || typeof testcaseSet !== 'string') {
        return [];
    }
    
    const prefixes = new Set();
    
    // 1. 使用完整名稱作為前綴（例如：'S3_BIT_'）
    prefixes.add(testcaseSet + '_');
    
    // 2. 分割測試集名稱，提取各部分作為前綴
    // 例如：'S3_BIT' → ['S3', 'BIT']
    const parts = testcaseSet.split('_').filter(part => part.length > 0);
    
    // 3. 每個部分都作為前綴
    parts.forEach(part => {
        prefixes.add(part + '_');
    });
    
    // 4. 組合相鄰的部分（例如：'S3_BIT' → 'S3_BIT_'）
    if (parts.length > 1) {
        for (let i = 0; i < parts.length - 1; i++) {
            const combined = parts.slice(i, i + 2).join('_');
            prefixes.add(combined + '_');
        }
    }
    
    return Array.from(prefixes);
};

/**
 * 從 config 物件中提取測試案例相關參數
 * 
 * **動態識別規則**：
 * 1. 先找出 testcase_set 的值（例如：'S3_BIT'）
 * 2. 從 testcase_set 中提取前綴（例如：['S3_', 'BIT_', 'S3_BIT_']）
 * 3. 使用這些動態前綴來匹配其他參數
 * 4. 加上核心 testcase_ 前綴的參數
 * 
 * @param {object} config - 主機配置物件（從 API 獲取）
 * @returns {object} 測試案例參數物件
 * 
 * @example
 * const config = {
 *     ansible_host: '10.250.71.22',
 *     testcase_set: 'S3_BIT',
 *     testcase_version: 'v1.2.3',
 *     S3_Lv1: 'value1',
 *     BIT_timeout: '3600',
 *     S3_BIT_parallel: '4',
 *     uart_id: 'KVM01'
 * };
 * 
 * extractTestcaseFields(config)
 * // 返回：
 * // {
 * //     testcase_set: { label: '測試案例集', value: 'S3_BIT' },
 * //     testcase_version: { label: '測試案例版本', value: 'v1.2.3' },
 * //     S3_Lv1: { label: 'S3 Lv1', value: 'value1' },
 * //     BIT_timeout: { label: 'BIT Timeout', value: '3600' },
 * //     S3_BIT_parallel: { label: 'S3 BIT Parallel', value: '4' }
 * // }
 */
export const extractTestcaseFields = (config) => {
    const testcaseFields = {};
    
    if (!config) return testcaseFields;
    
    // 1. 首先提取 testcase_set 本身（如果存在）
    if (config.testcase_set) {
        testcaseFields['testcase_set'] = {
            label: '測試案例集',
            value: config.testcase_set
        };
        
        // 2. 然後只提取 testcase_set 指定的測試項目配置
        // 例如：如果 testcase_set = 'S3_BIT'，只提取 config['S3_BIT'] 的配置
        const testcaseSetValue = config.testcase_set;
        
        if (config[testcaseSetValue]) {
            testcaseFields[testcaseSetValue] = {
                label: getTestcaseFieldLabel(testcaseSetValue),
                value: config[testcaseSetValue]
            };
        }
    }
    
    // 3. 提取其他 testcase_ 開頭的參數（如 testcase_version, testcase_timeout 等）
    Object.entries(config).forEach(([key, value]) => {
        // 跳過已處理的 testcase_set 和其對應的測試項目
        if (key === 'testcase_set' || key === config.testcase_set) {
            return;
        }
        
        // 檢查是否在排除列表中
        if (excludeTestcaseFields.includes(key)) {
            return;
        }
        
        // 只提取以 testcase_ 或 test_case_ 開頭的參數
        if (testcasePrefixes.some(prefix => key.startsWith(prefix))) {
            testcaseFields[key] = {
                label: getTestcaseFieldLabel(key),
                value: value
            };
        }
    });
    
    return testcaseFields;
};

export default {
    getAnsibleInventory,
    getAnsibleHosts,
    getHostConfig,
    getCacheStatistics,
    clearCache,
    parseInventoryToHostList,
    parseInventoryToGroupTree,
    formatConfigForDisplay,
    isTestcaseField,
    getTestcaseFieldLabel,
    extractTestcaseFields,
};
