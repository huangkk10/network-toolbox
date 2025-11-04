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
 * 權限：僅 Admin 可訪問
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
    PlayCircleOutlined,
    FileTextOutlined,
    RightOutlined,
    DownOutlined,
    ReloadOutlined,
    SyncOutlined,
} from '@ant-design/icons';
import axios from 'axios';
import { useAuth } from '../contexts/AuthContext';
import { useNavigate } from 'react-router-dom';

const { Content } = Layout;
const { Option } = Select;
const { RangePicker } = DatePicker;

const RVTAnalysisPage = () => {
    const { user } = useAuth();
    const navigate = useNavigate();
    
    // 權限檢查：非 Admin 跳轉
    useEffect(() => {
        if (user && !user.is_staff) {
            message.error('您沒有權限訪問此頁面');
            navigate('/dashboard');
        }
    }, [user, navigate]);

    // ========== State 管理 ==========
    const [loading, setLoading] = useState(false);
    const [statistics, setStatistics] = useState({
        total_servers: 0,
        total_jobs: 0,
        today_builds: 0,
        success_rate: 0,
    });
    
    const [servers, setServers] = useState([]);
    const [treeData, setTreeData] = useState([]);
    const [expandedRowKeys, setExpandedRowKeys] = useState([]);
    
    // 篩選條件
    const [filters, setFilters] = useState({
        server_id: null,
        status: null,
        date_range: null,
        search: '',
    });
    
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

    // ========== API 調用 ==========
    
    // 載入統計資料
    const fetchStatistics = async () => {
        try {
            // 獲取伺服器列表
            const serversRes = await axios.get('/api/jenkins-servers/');
            const serversData = serversRes.data;
            
            setServers(serversData);
            
            // 計算統計
            const totalServers = serversData.length;
            let totalJobs = 0;
            let todayBuilds = 0;
            let totalBuilds = 0;
            let successBuilds = 0;
            
            // 獲取所有 Jobs
            const jobsRes = await axios.get('/api/jenkins-jobs/');
            totalJobs = jobsRes.data.length;
            
            // 獲取今日 Builds（簡化版，實際應該用日期過濾）
            const buildsRes = await axios.get('/api/jenkins-builds/');
            const today = new Date().toISOString().split('T')[0];
            
            buildsRes.data.forEach(build => {
                const buildDate = build.build_timestamp.split(' ')[0];
                if (buildDate === today) {
                    todayBuilds++;
                }
                if (build.status === 'SUCCESS') {
                    successBuilds++;
                }
                totalBuilds++;
            });
            
            const successRate = totalBuilds > 0 
                ? ((successBuilds / totalBuilds) * 100).toFixed(1)
                : 0;
            
            setStatistics({
                total_servers: totalServers,
                total_jobs: totalJobs,
                today_builds: todayBuilds,
                success_rate: parseFloat(successRate),
            });
        } catch (error) {
            console.error('載入統計資料失敗:', error);
            message.error('載入統計資料失敗');
        }
    };
    
    // 載入 Jobs 列表
    const fetchJobs = async () => {
        setLoading(true);
        try {
            let url = '/api/jenkins-jobs/';
            const params = [];
            
            if (filters.server_id) {
                params.push(`server_id=${filters.server_id}`);
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
    
    // 觸發構建（Placeholder）
    const handleTriggerBuild = (record) => {
        Modal.confirm({
            title: '觸發構建',
            content: `確定要觸發 ${record.name} 的新構建嗎？`,
            onOk: () => {
                message.info('此功能尚未實現');
            },
        });
    };
    
    // 同步所有伺服器
    const handleSyncAll = async () => {
        if (servers.length === 0) {
            message.warning('沒有可同步的伺服器');
            return;
        }
        
        setLoading(true);
        try {
            const promises = servers.map(server => 
                axios.post(`/api/jenkins-servers/${server.id}/sync_jobs/`)
            );
            
            await Promise.all(promises);
            message.success('同步完成');
            fetchJobs();  // 重新載入 Jobs
        } catch (error) {
            console.error('同步失敗:', error);
            message.error('同步失敗');
        } finally {
            setLoading(false);
        }
    };

    // ========== Table Columns ==========
    const columns = [
        {
            title: 'Job / Build',
            dataIndex: 'name',
            key: 'name',
            width: 250,
            render: (text, record) => {
                if (record.type === 'job') {
                    return (
                        <Space>
                            <FolderOutlined style={{ color: '#1890ff' }} />
                            <span style={{ fontWeight: 500 }}>{text}</span>
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
            width: 150,
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
                    return <Tag color={config.color}>{config.text}</Tag>;
                }
            },
        },
        {
            title: '開始時間',
            dataIndex: 'last_build_time',
            key: 'time',
            width: 180,
            render: (text, record) => {
                if (record.type === 'job') {
                    return <span>{text}</span>;
                } else {
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
            width: 200,
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
                            <Tooltip title="觸發構建">
                                <Button 
                                    size="small" 
                                    type="primary"
                                    icon={<PlayCircleOutlined />}
                                    onClick={() => handleTriggerBuild(record)}
                                >
                                    構建
                                </Button>
                            </Tooltip>
                        </Space>
                    );
                } else {
                    return (
                        <Space size="small">
                            <Tooltip title="查看控制台日誌">
                                <Button 
                                    size="small"
                                    icon={<FileTextOutlined />}
                                    onClick={() => handleViewLog(record)}
                                >
                                    日誌
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
        fetchStatistics();
        fetchJobs();
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);
    
    useEffect(() => {
        fetchJobs();
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [filters]);

    // ========== 渲染 ==========
    return (
        <Content style={{ padding: '24px' }}>
            {/* 頁面標題 */}
            <div style={{ marginBottom: 24, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <h1 style={{ margin: 0, fontSize: 24, fontWeight: 600 }}>RVT 分析</h1>
                <Space>
                    <Button 
                        icon={<ReloadOutlined />}
                        onClick={() => { fetchStatistics(); fetchJobs(); }}
                    >
                        刷新
                    </Button>
                    <Button 
                        type="primary"
                        icon={<SyncOutlined />}
                        onClick={handleSyncAll}
                        loading={loading}
                    >
                        同步所有伺服器
                    </Button>
                </Space>
            </div>

            {/* 統計卡片 */}
            <Row gutter={16} style={{ marginBottom: 24 }}>
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
                            title="今日構建數"
                            value={statistics.today_builds}
                            prefix={<RocketOutlined />}
                            valueStyle={{ color: '#faad14' }}
                        />
                    </Card>
                </Col>
                <Col span={6}>
                    <Card>
                        <Statistic
                            title="成功率（總體）"
                            value={statistics.success_rate}
                            suffix="%"
                            prefix={<CheckCircleOutlined />}
                            valueStyle={{ color: '#52c41a' }}
                        />
                    </Card>
                </Col>
            </Row>

            {/* 篩選區域 */}
            <Card style={{ marginBottom: 16 }}>
                <Row gutter={16}>
                    <Col span={6}>
                        <Select
                            placeholder="選擇 Jenkins"
                            style={{ width: '100%' }}
                            allowClear
                            onChange={(value) => setFilters({ ...filters, server_id: value })}
                        >
                            {servers.map(server => (
                                <Option key={server.id} value={server.id}>
                                    {server.name}
                                </Option>
                            ))}
                        </Select>
                    </Col>
                    
                    <Col span={6}>
                        <Select
                            placeholder="篩選狀態"
                            style={{ width: '100%' }}
                            allowClear
                            onChange={(value) => setFilters({ ...filters, status: value })}
                        >
                            <Option value="SUCCESS">✅ Success</Option>
                            <Option value="FAILURE">❌ Failure</Option>
                            <Option value="RUNNING">🔄 Running</Option>
                            <Option value="UNSTABLE">⚠️ Unstable</Option>
                        </Select>
                    </Col>
                    
                    <Col span={6}>
                        <RangePicker
                            style={{ width: '100%' }}
                            onChange={(dates) => setFilters({ ...filters, date_range: dates })}
                            placeholder={['開始日期', '結束日期']}
                        />
                    </Col>
                    
                    <Col span={6}>
                        <Input.Search
                            placeholder="搜尋 Job 名稱..."
                            allowClear
                            onSearch={(value) => setFilters({ ...filters, search: value })}
                            enterButton
                        />
                    </Col>
                </Row>
            </Card>

            {/* Tree Table */}
            <Card>
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
                        pageSize: 10,
                        pageSizeOptions: ['10', '20', '50', '100'],
                        showSizeChanger: true,
                        showQuickJumper: true,
                        showTotal: (total, range) => `${range[0]}-${range[1]} of ${total}`,
                    }}
                    scroll={{ x: 1200 }}
                    size="middle"
                />
            </Card>

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
        </Content>
    );
};

export default RVTAnalysisPage;
