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
 * @param {object} config - 主機配置物件
 * @returns {Array} 格式化後的配置項目
 */
export const formatConfigForDisplay = (config) => {
    if (!config) return [];

    // 定義重要欄位的顯示順序和中文名稱
    const importantFields = {
        ansible_host: 'IP 地址',
        device_number: '設備號',
        sample_number: '樣品號',
        macaddress: 'MAC 地址',
        // UART 連接資訊（獨立區塊）
        uart_id: 'UART ID',
        uart_host: 'UART 主機',
        ansible_user: '使用者',
        ansible_password: '密碼',
        // 其他 Ansible 變數
        ansible_shell_type: 'Shell 類型',
        testcase_set: '測試案例集',
        platform_install_vnc: 'VNC 安裝',
        mailto: '郵件通知',
    };

    const items = [];

    // 先添加重要欄位
    Object.entries(importantFields).forEach(([key, label]) => {
        if (config[key] !== undefined) {
            items.push({
                key: key,
                label: label,
                value: formatValue(config[key]),
            });
        }
    });

    // 再添加其他欄位（排除已顯示的）
    Object.entries(config).forEach(([key, value]) => {
        if (!importantFields[key]) {
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
 * @returns {string} 格式化後的字串
 */
const formatValue = (value) => {
    if (value === null || value === undefined) {
        return 'N/A';
    }
    if (typeof value === 'boolean') {
        return value ? '是' : '否';
    }
    if (Array.isArray(value)) {
        return value.join(', ');
    }
    if (typeof value === 'object') {
        return JSON.stringify(value, null, 2);
    }
    return String(value);
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
};
