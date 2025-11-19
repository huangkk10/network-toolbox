/**
 * RVT 分析頁面
 * 
 * 功能：
 * - 顯示 RVT Server、Job、Build 的樹狀結構
 * - 統計卡片（伺服器總數、Jobs 總數、今日構建數、成功率）
 * - 篩選功能（伺服器、狀態、時間範圍、搜尋）
 * - Tree Table（兩層：Job → Build）
 * - Console Log Modal、Build 詳情 Drawer
 * 
 * 權限：所有登入使用者可訪問
 */

import React, { useState, useEffect } from 'react';
import {
    Layout,
    Card,
    Row,
    Col,
    Statistic,
    Table,
    Tag,
    Button,
    Space,
    Select,
    Input,
    DatePicker,
    Modal,
    Drawer,
    Descriptions,
    message,
    Spin,
    Tooltip,
} from 'antd';
import {
    CloudServerOutlined,
    FolderOutlined,
    RocketOutlined,
    CheckCircleOutlined,
    BarChartOutlined,
    FileTextOutlined,
    RightOutlined,
    DownOutlined,
    SaveOutlined,
    SettingOutlined,
} from '@ant-design/icons';
import axios from 'axios';
import { useAuth } from '../contexts/AuthContext';
import { useNavigate, useLocation } from 'react-router-dom';
import { AnsibleConfigDrawer } from '../components/AnsibleConfig';
import AnsibleInventoryManagerPage from './AnsibleInventoryManagerPage';
import JenkinsStatisticsCharts from '../components/jenkins/JenkinsStatisticsCharts';

const { Content } = Layout;
const { Option } = Select;
const { RangePicker } = DatePicker;

// 自訂表格表頭樣式（淺灰背景、黑色文字）
const tableHeaderStyles = `
    .ant-table-thead > tr > th {
        background-color: #d9d9d9 !important;
        color: #000000 !important;
        font-weight: 600 !important;
        border-bottom: 2px solid #bfbfbf !important;
    }
    .ant-table-thead > tr > th:hover {
        background-color: #e8e8e8 !important;
    }
`;

// 插入樣式到 head
if (typeof document !== 'undefined') {
    const styleId = 'rvt-table-header-styles';
    if (!document.getElementById(styleId)) {
        const styleElement = document.createElement('style');
        styleElement.id = styleId;
        styleElement.textContent = tableHeaderStyles;
        document.head.appendChild(styleElement);
    }
}

const RVTAnalysisPage = () => {
    const { user } = useAuth();
    const navigate = useNavigate();
    const location = useLocation();
    
    // ✅ 權限檢查已移除：所有登入使用者都可以訪問此頁面
    // 如果未登入，由 PrivateRoute 處理跳轉

    // ========== State 管理 ==========
    // 從 URL 參數讀取當前 Tab
    const getActiveTab = () => {
        const params = new URLSearchParams(location.search);
        return params.get('tab') || 'overview';
    };
    const activeTab = getActiveTab();
    
    // 從 URL 參數讀取時間範圍
    const getTimeRangeFromURL = () => {
        const params = new URLSearchParams(location.search);
        return params.get('time_range') || 'today';
    };
    const [timeRange, setTimeRange] = useState(getTimeRangeFromURL());
    
    // 從 URL 參數讀取篩選條件
    const getFiltersFromURL = () => {
        const params = new URLSearchParams(location.search);
        return {
            server_id: params.get('server_id') ? parseInt(params.get('server_id')) : null,
            view_name: params.get('view_name') || null,
            status: params.get('status') || null,
            date_range: null,
            search: params.get('search') || '',
        };
    };
    
    const [loading, setLoading] = useState(false);
    const [statisticsLoading, setStatisticsLoading] = useState(false);
    const [statistics, setStatistics] = useState({
        total_servers: 0,
        total_jobs: 0,
        period_builds: 0,
        period_success: 0,
        period_failure: 0,
        success_rate: 0,
        period_label: '今日',
        period_start: null,
        period_end: null,
    });
    
    const [servers, setServers] = useState([]);
    const [treeData, setTreeData] = useState([]);
    const [expandedRowKeys, setExpandedRowKeys] = useState([]);
    
    // 篩選條件（從 URL 初始化）
    const [filters, setFilters] = useState(getFiltersFromURL());
    
    // 分頁設置
    const [pagination, setPagination] = useState({
        current: 1,
        pageSize: 10,
    });
    
    // View 列表（從 Jobs 中提取唯一的 view_name）
    const [availableViews, setAvailableViews] = useState([]);
    
    // 更新 URL 參數（保持篩選條件持久化）
    const updateURLParams = (newFilters) => {
        const params = new URLSearchParams(location.search);
        
        // 更新篩選參數
        if (newFilters.server_id) {
            params.set('server_id', newFilters.server_id);
        } else {
            params.delete('server_id');
        }
        
        if (newFilters.view_name) {
            params.set('view_name', newFilters.view_name);
        } else {
            params.delete('view_name');
        }
        
        if (newFilters.status) {
            params.set('status', newFilters.status);
        } else {
            params.delete('status');
        }
        
        if (newFilters.search) {
            params.set('search', newFilters.search);
        } else {
            params.delete('search');
        }
        
        // 導航到新的 URL（不會重新載入頁面）
        navigate(`${location.pathname}?${params.toString()}`, { replace: true });
    };
    
    // Modal & Drawer
    const [consoleLogModal, setConsoleLogModal] = useState({
        visible: false,
        loading: false,
        content: '',
        buildInfo: null,
    });
    
    const [buildDetailDrawer, setBuildDetailDrawer] = useState({
        visible: false,
        loading: false,
        data: null,
    });
    
    const [jobStatsDrawer, setJobStatsDrawer] = useState({
        visible: false,
        loading: false,
        data: null,
    });
    
    // Ansible Config Drawer
    const [ansibleConfigDrawer, setAnsibleConfigDrawer] = useState({
        visible: false,
        jobId: null,
        jobName: null,
        buildNumber: null,
        hostname: null, // 添加 hostname 參數，用於過濾主機
    });

    // ========== API 調用 ==========
    
    // 載入統計資料
    const fetchStatistics = async (range = timeRange) => {
        setStatisticsLoading(true);
        try {
            // 獲取伺服器列表
            const serversRes = await axios.get('/api/jenkins-servers/');
            const serversData = serversRes.data;
            setServers(serversData);
            
            // 調用新的 global-statistics API
            const statsRes = await axios.get(`/api/jenkins-servers/global-statistics/?time_range=${range}`);
            setStatistics(statsRes.data);
        } catch (error) {
            console.error('載入統計資料失敗:', error);
            message.error('載入統計資料失敗');
        } finally {
            setStatisticsLoading(false);
        }
    };
    
    // 處理時間範圍變更
    const handleTimeRangeChange = (value) => {
        setTimeRange(value);
        updateTimeRangeURL(value);
        fetchStatistics(value);
    };
    
    // 更新 URL 參數
    const updateTimeRangeURL = (range) => {
        const params = new URLSearchParams(location.search);
        params.set('time_range', range);
        navigate(`${location.pathname}?${params.toString()}`, { replace: true });
    };
    
    // 獲取時間範圍顯示文字
    const getTimeRangeDisplay = () => {
        switch (timeRange) {
            case 'today': return '今日';
            case 'week': return '最近 7 天';
            case '2weeks': return '最近 14 天';
            case 'month': return '最近 30 天';
            case 'all': return '全部時間';
            default: return '今日';
        }
    };
    
    // 載入可用的 View 列表（根據當前選擇的伺服器）
    const fetchAvailableViews = async (serverId = null) => {
        try {
            // 根據 serverId 過濾 Jobs
            let url = '/api/jenkins-jobs/';
            if (serverId) {
                url += `?server_id=${serverId}`;
            }
            
            const response = await axios.get(url);
            
            // 提取唯一的 View 名稱列表
            const uniqueViews = [...new Set(
                response.data
                    .map(job => job.view_name)
                    .filter(view => view && view !== '')
            )].sort();
            
            setAvailableViews(uniqueViews);
        } catch (error) {
            console.error('載入 View 列表失敗:', error);
            // 不顯示錯誤訊息，因為這不是關鍵功能
        }
    };
    
    // 載入 Jobs 列表
    const fetchJobs = async () => {
        setLoading(true);
        setExpandedRowKeys([]);  // ← 清空展開狀態，避免顯示孤立的 Build 記錄
        try {
            let url = '/api/jenkins-jobs/';
            const params = [];
            
            if (filters.server_id) {
                params.push(`server_id=${filters.server_id}`);
            }
            if (filters.view_name) {
                params.push(`view_name=${encodeURIComponent(filters.view_name)}`);
            }
            if (filters.status) {
                params.push(`status=${filters.status}`);
            }
            if (filters.search) {
                params.push(`search=${filters.search}`);
            }
            
            if (params.length > 0) {
                url += '?' + params.join('&');
            }
            
            const response = await axios.get(url);
            
            // 轉換為 Tree Table 資料格式
            const jobs = response.data.map(job => ({
                key: `job-${job.id}`,
                type: 'job',
                job_id: job.id,
                server_id: job.server,
                server_name: job.server_name || `Server ${job.server}`,
                name: job.name,
                view_name: job.view_name || '',  // ← 添加 view_name 字段
                status: job.status,
                last_build_time: job.last_build_time || 'N/A',
                last_build_status: job.last_build_status || null,  // ← 添加 last_build_status
                avg_duration: '計算中...',  // 後續可以從統計 API 獲取
                builds_count: job.builds_count || 0,
                url: job.url,
                children: [],  // 初始為空，展開時才載入
            }));
            
            setTreeData(jobs);
        } catch (error) {
            console.error('載入 Jobs 失敗:', error);
            message.error('載入 Jobs 失敗');
        } finally {
            setLoading(false);
        }
    };
    
    // 展開 Job 時載入 Builds
    const handleExpand = async (expanded, record) => {
        if (expanded && record.type === 'job' && record.children.length === 0) {
            setLoading(true);
            try {
                const response = await axios.get(
                    `/api/jenkins-jobs/${record.job_id}/builds/?limit=10`
                );
                
                const builds = response.data.builds.map(build => ({
                    key: `build-${build.build_number}`,
                    type: 'build',
                    build_id: build.id,
                    build_number: build.build_number,
                    result: build.result || build.status,  // 兼容兩種命名
                    failed_stage: build.failed_stage || null,  // ← 新增：失敗的 Stage
                    build_timestamp: build.build_timestamp,
                    duration: build.duration_formatted || `${build.duration}s`,
                    url: build.url,  // Jenkins Build URL
                    job_id: record.job_id,
                    job_name: record.name,
                }));
                
                // 更新該 Job 的 children
                setTreeData(prevData => {
                    return prevData.map(item => {
                        if (item.key === record.key) {
                            return { ...item, children: builds };
                        }
                        return item;
                    });
                });
                
                message.success(`載入了 ${builds.length} 個 Builds`);
            } catch (error) {
                console.error('載入 Builds 失敗:', error);
                message.error('載入 Builds 失敗');
            } finally {
                setLoading(false);
            }
        }
    };
    
    // 查看 Console Log（直接打開 Jenkins 頁面）
    const handleViewLog = (record) => {
        if (record.url) {
            // 打開 Jenkins Build Console 頁面
            window.open(`${record.url}console`, '_blank');
            message.success('已在新視窗中打開 Console Log');
        } else {
            message.error('Build URL 不可用');
        }
    };
    
    // 查看 Build 詳情（直接打開 Jenkins 頁面）
    const handleViewDetail = (record) => {
        if (record.url) {
            // 打開 Jenkins Build 詳情頁面
            window.open(record.url, '_blank');
            message.success('已在新視窗中打開 Build 詳情');
        } else {
            message.error('Build URL 不可用');
        }
    };
    
    // 查看 Job 統計
    const handleViewStats = async (record) => {
        setJobStatsDrawer({
            visible: true,
            loading: true,
            data: null,
        });
        
        try {
            const response = await axios.get(`/api/jenkins-jobs/${record.job_id}/statistics/`);
            
            setJobStatsDrawer({
                visible: true,
                loading: false,
                data: response.data,
            });
        } catch (error) {
            console.error('獲取 Job 統計失敗:', error);
            message.error('獲取 Job 統計失敗');
            setJobStatsDrawer({
                visible: false,
                loading: false,
                data: null,
            });
        }
    };
    
    // 查看 Ansible 配置（從 Build 行調用）
    const handleViewAnsibleConfig = (record) => {
        // record 是 Build 行，包含 job_id, job_name, build_number
        setAnsibleConfigDrawer({
            visible: true,
            jobId: record.job_id,
            jobName: record.job_name,
            buildNumber: record.build_number,
            hostname: record.job_name, // 只顯示與 job_name 相同的主機
        });
    };
    
    // 存儲 Workspace 到 NAS
    const handleStoreWorkspace = async (record) => {
        Modal.confirm({
            title: '存儲 Workspace 到 NAS',
            content: (
                <div>
                    <p>確定要將以下 Build 的 Workspace 存儲到 NAS 嗎？</p>
                    <p><strong>Job:</strong> {record.job_name}</p>
                    <p><strong>Build:</strong> #{record.build_number}</p>
                    <p style={{ marginTop: 10, color: '#999', fontSize: 12 }}>
                        存儲路徑：\\10.250.0.1\mdt\Team\PQ1-3\tool\jenkins_test_storage\{'{jenkins_ip}'}\{'{job_name}'}\{'{build_number}'}
                    </p>
                </div>
            ),
            okText: '確定存儲',
            cancelText: '取消',
            onOk: async () => {
                try {
                    message.loading({ content: '正在存儲 Workspace...', key: 'storeWorkspace', duration: 0 });
                    
                    const response = await axios.post(
                        `/api/jenkins-builds/${record.build_id}/store_workspace/`
                    );
                    
                    message.success({
                        content: (
                            <div>
                                <div>Workspace 存儲成功！</div>
                                <div style={{ fontSize: 12, color: '#666', marginTop: 4 }}>
                                    路徑：{response.data.workspace_path}
                                </div>
                                <div style={{ fontSize: 12, color: '#666' }}>
                                    大小：{(response.data.workspace_size / (1024 * 1024)).toFixed(2)} MB
                                </div>
                                <div style={{ fontSize: 12, color: '#666' }}>
                                    檔案數量：{response.data.files_count}
                                </div>
                            </div>
                        ),
                        key: 'storeWorkspace',
                        duration: 5,
                    });
                    
                    // 重新載入數據
                    fetchJobs();
                } catch (error) {
                    console.error('存儲 Workspace 失敗:', error);
                    message.error({
                        content: '存儲 Workspace 失敗：' + (error.response?.data?.error || error.message),
                        key: 'storeWorkspace',
                        duration: 5,
                    });
                }
            },
        });
    };
    
    // ========== 顏色映射函數 ==========
    /**
     * 根據 Build 狀態返回對應的樣式配置
     * @param {string} status - Build 狀態 (SUCCESS, FAILURE, UNSTABLE, ABORTED, BUILDING, UNKNOWN)
     * @returns {object} 樣式配置 { bg, border, color }
     */
    const getJobStatusStyle = (status) => {
        const styleMap = {
            'SUCCESS': { 
                bg: '#f6ffed',      // 淺綠色背景
                border: '#b7eb8f',  // 綠色邊框
                color: '#52c41a',   // 深綠色文字
                icon: '✅'
            },
            'FAILURE': { 
                bg: '#fff2f0',      // 淺紅色背景
                border: '#ffccc7',  // 紅色邊框
                color: '#ff4d4f',   // 深紅色文字
                icon: '❌'
            },
            'UNSTABLE': { 
                bg: '#fffbe6',      // 淺黃色背景
                border: '#ffe58f',  // 黃色邊框
                color: '#faad14',   // 深黃色文字
                icon: '⚠️'
            },
            'ABORTED': { 
                bg: '#fafafa',      // 淺灰色背景
                border: '#d9d9d9',  // 灰色邊框
                color: '#8c8c8c',   // 深灰色文字
                icon: '🚫'
            },
            'BUILDING': { 
                bg: '#e6f7ff',      // 淺藍色背景
                border: '#91d5ff',  // 藍色邊框
                color: '#1890ff',   // 深藍色文字
                icon: '🔄'
            },
            'UNKNOWN': { 
                bg: '#f5f5f5',      // 淺灰色背景
                border: '#d9d9d9',  // 灰色邊框
                color: '#595959',   // 深灰色文字
                icon: '❓'
            },
        };
        
        // 返回對應狀態的樣式，如果沒有匹配則返回默認樣式（無 Build）
        return styleMap[status] || { 
            bg: '#ffffff',          // 白色背景
            border: '#e8e8e8',      // 淺灰邊框
            color: '#000000',       // 黑色文字
            icon: ''
        };
    };
    
    // ========== Table Columns ==========
    const columns = [
        {
            title: 'Job / Build',
            dataIndex: 'name',
            key: 'name',
            width: 250,
            sorter: (a, b) => {
                // 只對 Job 行進行排序，Build 行跟隨 Job
                if (a.type === 'job' && b.type === 'job') {
                    return a.name.localeCompare(b.name, 'zh-TW');
                }
                return 0;
            },
            render: (text, record) => {
                if (record.type === 'job') {
                    // 獲取 Job 狀態對應的樣式
                    const statusStyle = getJobStatusStyle(record.last_build_status);
                    
                    return (
                        <Space>
                            <FolderOutlined style={{ color: statusStyle.color }} />
                            <span 
                                style={{ 
                                    fontWeight: 500,
                                    padding: '4px 8px',
                                    borderRadius: '4px',
                                    backgroundColor: statusStyle.bg,
                                    border: `1px solid ${statusStyle.border}`,
                                    color: statusStyle.color,
                                    display: 'inline-block'
                                }}
                            >
                                {text}
                            </span>
                            <Tag color="blue" style={{ fontSize: 11 }}>
                                {record.builds_count} Builds
                            </Tag>
                        </Space>
                    );
                } else {
                    return (
                        <div style={{ paddingLeft: 32 }}>
                            <Space>
                                <span style={{ color: '#666' }}>#{record.build_number}</span>
                            </Space>
                        </div>
                    );
                }
            },
        },
        {
            title: 'View',
            dataIndex: 'view_name',
            key: 'view_name',
            width: 150,
            render: (text, record) => {
                if (record.type === 'job') {
                    if (text) {
                        return <Tag color="geekblue">{text}</Tag>;
                    } else {
                        return <Tag color="default">未分類</Tag>;
                    }
                } else {
                    return <span style={{ color: '#ccc' }}>-</span>;
                }
            },
        },
        {
            title: '狀態',
            dataIndex: 'status',
            key: 'status',
            width: 250,
            render: (text, record) => {
                if (record.type === 'job') {
                    return text === 'active' 
                        ? <Tag color="success">🟢 Active</Tag>
                        : <Tag color="default">⚪ Inactive</Tag>;
                } else {
                    const statusMap = {
                        'SUCCESS': { color: 'success', text: '✅ Success' },
                        'FAILURE': { color: 'error', text: '❌ Failure' },
                        'UNSTABLE': { color: 'warning', text: '⚠️ Unstable' },
                        'ABORTED': { color: 'default', text: '🚫 Aborted' },
                        'RUNNING': { color: 'processing', text: '🔄 Running' },
                    };
                    const config = statusMap[record.result] || statusMap['SUCCESS'];
                    
                    // 如果是失敗且有 failed_stage，顯示在旁邊
                    return (
                        <Space>
                            <Tag color={config.color}>{config.text}</Tag>
                            {record.result === 'FAILURE' && record.failed_stage && (
                                <Tooltip title="失敗的 Stage">
                                    <Tag color="red" style={{ fontSize: 11 }}>
                                        📍 {record.failed_stage}
                                    </Tag>
                                </Tooltip>
                            )}
                        </Space>
                    );
                }
            },
        },
        {
            title: '最新 Build 時間',
            dataIndex: 'last_build_time',
            key: 'time',
            width: 200,
            sorter: (a, b) => {
                // 只對 Job 行進行排序，Build 行跟隨 Job
                if (a.type === 'job' && b.type === 'job') {
                    // 處理無 Build 記錄的情況（排到最後）
                    if (!a.last_build_time || a.last_build_time === 'N/A') return 1;
                    if (!b.last_build_time || b.last_build_time === 'N/A') return -1;
                    
                    // 比較時間（新的排前面）
                    const timeA = new Date(a.last_build_time).getTime();
                    const timeB = new Date(b.last_build_time).getTime();
                    return timeB - timeA;
                }
                return 0;
            },
            render: (text, record) => {
                if (record.type === 'job') {
                    // Job 行：顯示最新 Build 時間
                    if (!text || text === 'N/A') {
                        return <span style={{ color: '#999' }}>無 Build 記錄</span>;
                    }
                    
                    // 格式化時間顯示
                    try {
                        const buildTime = new Date(text);
                        const now = new Date();
                        const diffMs = now - buildTime;
                        const diffMins = Math.floor(diffMs / 60000);
                        const diffHours = Math.floor(diffMs / 3600000);
                        const diffDays = Math.floor(diffMs / 86400000);
                        
                        let relativeTime = '';
                        if (diffMins < 1) {
                            relativeTime = '剛剛';
                        } else if (diffMins < 60) {
                            relativeTime = `${diffMins} 分鐘前`;
                        } else if (diffHours < 24) {
                            relativeTime = `${diffHours} 小時前`;
                        } else if (diffDays < 7) {
                            relativeTime = `${diffDays} 天前`;
                        } else {
                            relativeTime = buildTime.toLocaleDateString('zh-TW', {
                                year: 'numeric',
                                month: '2-digit',
                                day: '2-digit'
                            });
                        }
                        
                        return (
                            <Tooltip title={buildTime.toLocaleString('zh-TW')}>
                                <span style={{ color: diffDays > 7 ? '#ff4d4f' : '#666' }}>
                                    {relativeTime}
                                </span>
                            </Tooltip>
                        );
                    } catch (e) {
                        return <span>{text}</span>;
                    }
                } else {
                    // Build 行：顯示構建開始時間
                    return <span>{record.build_timestamp}</span>;
                }
            },
        },
        {
            title: '執行時間',
            dataIndex: 'avg_duration',
            key: 'duration',
            width: 120,
            render: (text, record) => {
                if (record.type === 'job') {
                    return <span style={{ color: '#999' }}>平均 {text}</span>;
                } else {
                    return <span>{record.duration}</span>;
                }
            },
        },
        {
            title: '操作',
            key: 'action',
            width: 250,
            fixed: 'right',
            render: (_, record) => {
                if (record.type === 'job') {
                    return (
                        <Space size="small">
                            <Tooltip title="查看統計">
                                <Button 
                                    size="small" 
                                    icon={<BarChartOutlined />}
                                    onClick={() => handleViewStats(record)}
                                >
                                    統計
                                </Button>
                            </Tooltip>
                        </Space>
                    );
                } else {
                    return (
                        <Space size="small">
                            <Tooltip title="檢查 Build 配置">
                                <Button 
                                    size="small"
                                    icon={<CheckCircleOutlined />}
                                    onClick={() => {
                                        console.log('🔍 檢查配置按鈕 - record:', record);
                                        console.log('🔍 record.id:', record.id);
                                        console.log('🔍 record.build_id:', record.build_id);
                                        console.log('🔍 record.build_number:', record.build_number);
                                        // 使用 build_id（後端 API 的主鍵）
                                        const buildId = record.build_id || record.id;
                                        console.log('🔍 最終使用的 buildId:', buildId);
                                        navigate(`/rvt-analytics/build-config-validator/${buildId}`);
                                    }}
                                >
                                    檢查配置
                                </Button>
                            </Tooltip>
                            <Tooltip title="查看控制台日誌">
                                <Button 
                                    size="small"
                                    icon={<FileTextOutlined />}
                                    onClick={() => handleViewLog(record)}
                                >
                                    日誌
                                </Button>
                            </Tooltip>
                            <Tooltip title="查看 Ansible 配置">
                                <Button 
                                    size="small" 
                                    icon={<SettingOutlined />}
                                    onClick={() => handleViewAnsibleConfig(record)}
                                >
                                    配置
                                </Button>
                            </Tooltip>
                            <Tooltip title="查看構建詳情">
                                <Button 
                                    size="small"
                                    onClick={() => handleViewDetail(record)}
                                >
                                    詳情
                                </Button>
                            </Tooltip>
                        </Space>
                    );
                }
            },
        },
    ];

    // ========== 初始化 ==========
    useEffect(() => {
        const range = getTimeRangeFromURL();
        setTimeRange(range);
        fetchStatistics(range);  // 使用 URL 中的時間範圍
        fetchAvailableViews(filters.server_id);
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);
    
    // 當 URL 參數變化時，更新 filters 並重新載入數據
    useEffect(() => {
        const urlFilters = getFiltersFromURL();
        setFilters(urlFilters);
        fetchJobs();
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [location.search]);

    // ========== 渲染 ==========
    
    // 如果 activeTab 是 'inventory'，則渲染 Ansible Inventory Manager
    if (activeTab === 'inventory') {
        return <AnsibleInventoryManagerPage />;
    }
    
    return (
        <Content style={{ 
            padding: 0,
            height: 'calc(100vh - 64px)',
            overflow: 'hidden',
            display: 'flex',
            flexDirection: 'column',
            backgroundColor: '#f5f5f5',
        }}>
            {/* Tab 內容區域（Tab 本身已移到 TopHeader） */}
            {activeTab === 'overview' && (
                <div style={{ 
                    flex: '1 1 auto',
                    overflow: 'auto',
                    padding: '16px',
                }}>
                    {/* 時間範圍選擇器 */}
                    <Card style={{ marginBottom: 12 }}>
                        <Space size="middle" align="center" style={{ width: '100%' }}>
                            <span style={{ fontWeight: 500, fontSize: 14 }}>統計時間範圍：</span>
                            <Select
                                value={timeRange}
                                onChange={handleTimeRangeChange}
                                size="middle"
                                style={{ width: '300px' }}
                            >
                                <Option value="today">今日</Option>
                                <Option value="week">最近 7 天</Option>
                                <Option value="2weeks">最近 14 天</Option>
                                <Option value="month">最近 30 天</Option>
                                <Option value="all">全部時間</Option>
                            </Select>
                            {statistics.period_start && statistics.period_end && (
                                <span style={{ color: '#999', fontSize: 14 }}>
                                    統計區間：{new Date(statistics.period_start).toLocaleString('zh-TW')} ~ {new Date(statistics.period_end).toLocaleString('zh-TW')}
                                    <span style={{ marginLeft: 16, color: '#666' }}>
                                        （成功：<span style={{ color: '#52c41a', fontWeight: 500 }}>{statistics.period_success}</span> | 
                                        失敗：<span style={{ color: '#ff4d4f', fontWeight: 500 }}>{statistics.period_failure}</span>）
                                    </span>
                                </span>
                            )}
                        </Space>
                    </Card>

                    {/* 統計卡片 */}
                    <Spin spinning={statisticsLoading}>
                        <Row gutter={12} style={{ marginBottom: 16 }}>
                            <Col span={6}>
                                <Card>
                                    <Statistic
                                        title="伺服器總數"
                                        value={statistics.total_servers}
                                        prefix={<CloudServerOutlined />}
                                        valueStyle={{ color: '#1890ff' }}
                                    />
                                </Card>
                            </Col>
                            <Col span={6}>
                                <Card>
                                    <Statistic
                                        title="Jobs 總數"
                                        value={statistics.total_jobs}
                                        prefix={<FolderOutlined />}
                                        valueStyle={{ color: '#52c41a' }}
                                    />
                                </Card>
                            </Col>
                            <Col span={6}>
                                <Card>
                                    <Statistic
                                        title={`${statistics.period_label}構建數`}
                                        value={statistics.period_builds}
                                        prefix={<RocketOutlined />}
                                        valueStyle={{ color: '#faad14' }}
                                    />
                                </Card>
                            </Col>
                            <Col span={6}>
                                <Card>
                                    <Statistic
                                        title={`${statistics.period_label}成功率`}
                                        value={statistics.success_rate}
                                        suffix="%"
                                        prefix={<CheckCircleOutlined />}
                                        valueStyle={{ color: '#52c41a' }}
                                    />
                                </Card>
                            </Col>
                        </Row>
                    </Spin>

                    {/* Jenkins 趨勢圖表 */}
                    <JenkinsStatisticsCharts 
                        timeRange={timeRange} 
                        serverId="all" 
                    />
                </div>
            )}

            {activeTab === 'details' && (
                <>
                    {/* 固定篩選區域 - 緊湊單行佈局 */}
                    <div style={{ 
                        flex: '0 0 auto',
                        padding: '12px 16px',
                        backgroundColor: '#f5f5f5',
                    }}>
                        <Card 
                            size="small"
                            bodyStyle={{ padding: '10px 16px' }}
                            style={{ 
                                marginBottom: 0,
                                boxShadow: '0 1px 4px rgba(0,0,0,0.08)',
                            }}
                        >
                            <Row gutter={12} align="middle">
                                {/* Jenkins Server */}
                                <Col flex="auto" style={{ maxWidth: 400 }}>
                                    <Space size={4} style={{ width: '100%', flexWrap: 'nowrap' }}>
                                        <span style={{ fontSize: 13, color: '#666', whiteSpace: 'nowrap' }}>Server:</span>
                                        <Select
                                            placeholder="選擇 Server"
                                            style={{ flex: 1, minWidth: 0 }}
                                            dropdownStyle={{ minWidth: 350 }}
                                            allowClear
                                            value={filters.server_id}
                                            onChange={(value) => {
                                                const newFilters = { ...filters, server_id: value, view_name: null };
                                                setFilters(newFilters);
                                                updateURLParams(newFilters);
                                                fetchAvailableViews(value);
                                            }}
                                            size="small"
                                            getPopupContainer={() => document.body}
                                        >
                                            {servers.map(server => (
                                                <Option key={server.id} value={server.id}>
                                                    <CloudServerOutlined style={{ marginRight: 6, fontSize: 12 }} />
                                                    {server.name}
                                                </Option>
                                            ))}
                                        </Select>
                                    </Space>
                                </Col>
                                
                                {/* View */}
                                <Col flex="auto" style={{ maxWidth: 320 }}>
                                    <Space size={4} style={{ width: '100%', flexWrap: 'nowrap' }}>
                                        <span style={{ fontSize: 13, color: '#666', whiteSpace: 'nowrap' }}>View:</span>
                                        <Select
                                            placeholder="選擇 View"
                                            style={{ flex: 1, minWidth: 0 }}
                                            dropdownStyle={{ minWidth: 400 }}
                                            allowClear
                                            value={filters.view_name}
                                            onChange={(value) => {
                                                const newFilters = { ...filters, view_name: value };
                                                setFilters(newFilters);
                                                updateURLParams(newFilters);
                                            }}
                                            size="small"
                                            showSearch
                                            filterOption={(input, option) =>
                                                option.children.toLowerCase().indexOf(input.toLowerCase()) >= 0
                                            }
                                            getPopupContainer={() => document.body}
                                        >
                                            {availableViews.map(view => (
                                                <Option key={view} value={view}>
                                                    <FolderOutlined style={{ marginRight: 6, fontSize: 12 }} />
                                                    {view}
                                                </Option>
                                            ))}
                                        </Select>
                                    </Space>
                                </Col>
                                
                                {/* 狀態 */}
                                <Col flex="auto" style={{ maxWidth: 140 }}>
                                    <Select
                                        placeholder="狀態"
                                        style={{ width: '100%' }}
                                        allowClear
                                        value={filters.status}
                                        onChange={(value) => {
                                            const newFilters = { ...filters, status: value };
                                            setFilters(newFilters);
                                            updateURLParams(newFilters);
                                        }}
                                        size="small"
                                        getPopupContainer={() => document.body}
                                    >
                                        <Option value="SUCCESS">Success</Option>
                                        <Option value="FAILURE">Failure</Option>
                                        <Option value="UNSTABLE">Unstable</Option>
                                        <Option value="ABORTED">Aborted</Option>
                                    </Select>
                                </Col>
                                
                                {/* 日期範圍 */}
                                <Col flex="auto" style={{ maxWidth: 260 }}>
                                    <RangePicker
                                        style={{ width: '100%' }}
                                        onChange={(dates) => {
                                            const newFilters = { ...filters, date_range: dates };
                                            setFilters(newFilters);
                                        }}
                                        placeholder={['開始日期', '結束日期']}
                                        size="small"
                                        getPopupContainer={() => document.body}
                                    />
                                </Col>
                                
                                {/* 搜尋 */}
                                <Col flex="1 1 auto" style={{ minWidth: 180 }}>
                                    <Input.Search
                                        placeholder="搜尋 Job 名稱..."
                                        allowClear
                                        value={filters.search}
                                        onSearch={(value) => {
                                            const newFilters = { ...filters, search: value };
                                            setFilters(newFilters);
                                            updateURLParams(newFilters);
                                        }}
                                        onChange={(e) => {
                                            setFilters({ ...filters, search: e.target.value });
                                        }}
                                        size="small"
                                        enterButton
                                    />
                                </Col>
                            </Row>
                        </Card>
                    </div>

                    {/* Table 區域 - 自適應高度並內部滾動 */}
                    <div style={{ 
                        flex: '1 1 auto',
                        overflow: 'hidden',
                        padding: '0 16px 16px',
                    }}>
                        <Card 
                            style={{ height: '100%' }}
                            bodyStyle={{ padding: 12, height: '100%', display: 'flex', flexDirection: 'column' }}
                        >
                            <Table
                                dataSource={treeData}
                                columns={columns}
                                rowKey="key"
                                loading={loading}
                                expandable={{
                                    expandedRowKeys,
                                    onExpandedRowsChange: setExpandedRowKeys,
                                    onExpand: handleExpand,
                                    indentSize: 0,
                                    expandIcon: ({ expanded, onExpand, record }) => {
                                        if (record.type === 'job') {
                                            return (
                                                <Button
                                                    type="text"
                                                    size="small"
                                                    icon={expanded ? <DownOutlined /> : <RightOutlined />}
                                                    onClick={e => onExpand(record, e)}
                                                />
                                            );
                                        }
                                        return <span style={{ width: 24, display: 'inline-block' }} />;
                                    },
                                }}
                                pagination={{
                                    current: pagination.current,
                                    pageSize: pagination.pageSize,
                                    pageSizeOptions: ['10', '20', '50', '100'],
                                    showSizeChanger: true,
                                    showQuickJumper: true,
                                    showTotal: (total, range) => `${range[0]}-${range[1]} of ${total}`,
                                    onChange: (page, pageSize) => {
                                        setPagination({ current: page, pageSize });
                                    },
                                    onShowSizeChange: (current, size) => {
                                        setPagination({ current: 1, pageSize: size });
                                    },
                                }}
                                scroll={{ 
                                    x: 1200,
                                    y: 'calc(100vh - 240px)',  // 自適應高度
                                }}
                                size="small"
                            />
                        </Card>
                    </div>
                </>
            )}

            {/* Console Log Modal */}
            <Modal
                title={`Build #${consoleLogModal.buildInfo?.build_number} - Console Log`}
                open={consoleLogModal.visible}
                onCancel={() => setConsoleLogModal({ ...consoleLogModal, visible: false })}
                width={1000}
                footer={null}
            >
                {consoleLogModal.loading ? (
                    <div style={{ textAlign: 'center', padding: '40px' }}>
                        <Spin size="large" />
                    </div>
                ) : (
                    <pre style={{ 
                        maxHeight: '600px', 
                        overflow: 'auto',
                        backgroundColor: '#1e1e1e',
                        color: '#d4d4d4',
                        padding: '16px',
                        borderRadius: '4px',
                    }}>
                        {consoleLogModal.content}
                    </pre>
                )}
            </Modal>

            {/* Build Detail Drawer */}
            <Drawer
                title="Build 詳情"
                width={720}
                open={buildDetailDrawer.visible}
                onClose={() => setBuildDetailDrawer({ ...buildDetailDrawer, visible: false })}
            >
                {buildDetailDrawer.loading ? (
                    <div style={{ textAlign: 'center', padding: '40px' }}>
                        <Spin size="large" />
                    </div>
                ) : buildDetailDrawer.data ? (
                    <Descriptions column={2} bordered>
                        <Descriptions.Item label="Build Number">
                            #{buildDetailDrawer.data.build_number}
                        </Descriptions.Item>
                        <Descriptions.Item label="Status">
                            <Tag color={buildDetailDrawer.data.status === 'SUCCESS' ? 'success' : 'error'}>
                                {buildDetailDrawer.data.status}
                            </Tag>
                        </Descriptions.Item>
                        <Descriptions.Item label="開始時間" span={2}>
                            {buildDetailDrawer.data.build_timestamp}
                        </Descriptions.Item>
                        <Descriptions.Item label="執行時間" span={2}>
                            {buildDetailDrawer.data.duration_formatted || `${buildDetailDrawer.data.duration}s`}
                        </Descriptions.Item>
                        <Descriptions.Item label="Job 名稱" span={2}>
                            {buildDetailDrawer.data.job_name || 'N/A'}
                        </Descriptions.Item>
                    </Descriptions>
                ) : null}
            </Drawer>

            {/* Job Statistics Drawer */}
            <Drawer
                title="Job 統計"
                width={720}
                open={jobStatsDrawer.visible}
                onClose={() => setJobStatsDrawer({ ...jobStatsDrawer, visible: false })}
            >
                {jobStatsDrawer.loading ? (
                    <div style={{ textAlign: 'center', padding: '40px' }}>
                        <Spin size="large" />
                    </div>
                ) : jobStatsDrawer.data ? (
                    <>
                        <Descriptions column={2} bordered>
                            <Descriptions.Item label="Job 名稱" span={2}>
                                {jobStatsDrawer.data.job_name}
                            </Descriptions.Item>
                            <Descriptions.Item label="總 Builds">
                                {jobStatsDrawer.data.total_builds}
                            </Descriptions.Item>
                            <Descriptions.Item label="成功率">
                                {jobStatsDrawer.data.success_rate}%
                            </Descriptions.Item>
                            <Descriptions.Item label="平均執行時間" span={2}>
                                {jobStatsDrawer.data.average_duration ? 
                                    `${jobStatsDrawer.data.average_duration.toFixed(0)}s` : 'N/A'}
                            </Descriptions.Item>
                            <Descriptions.Item label="最近 7 天 Builds" span={2}>
                                {jobStatsDrawer.data.recent_builds_7d}
                            </Descriptions.Item>
                        </Descriptions>
                        
                        {/* Build 狀態分佈 */}
                        {jobStatsDrawer.data.build_status_distribution && (
                            <div style={{ marginTop: 24 }}>
                                <h3>Build 狀態分佈</h3>
                                <Space direction="vertical" style={{ width: '100%' }}>
                                    {jobStatsDrawer.data.build_status_distribution.map(item => (
                                        <div key={item.result} style={{ display: 'flex', justifyContent: 'space-between' }}>
                                            <span>{item.result}:</span>
                                            <Tag>{item.count}</Tag>
                                        </div>
                                    ))}
                                </Space>
                            </div>
                        )}
                    </>
                ) : null}
            </Drawer>

            {/* Ansible Config Drawer */}
            <AnsibleConfigDrawer
                visible={ansibleConfigDrawer.visible}
                onClose={() => setAnsibleConfigDrawer({ ...ansibleConfigDrawer, visible: false })}
                jobId={ansibleConfigDrawer.jobId}
                jobName={ansibleConfigDrawer.jobName}
                buildNumber={ansibleConfigDrawer.buildNumber}
                hostname={ansibleConfigDrawer.hostname}
            />
        </Content>
    );
};

export default RVTAnalysisPage;
