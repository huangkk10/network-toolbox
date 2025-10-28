import React, { useState, useEffect } from 'react';
import axios from 'axios';
import {
    Card,
    Row,
    Col,
    Statistic,
    Table,
    Tag,
    Spin,
    message,
    Select,
    Space,
    Typography,
    Alert,
    Empty,
} from 'antd';
import {
    CheckCircleOutlined,
    CloseCircleOutlined,
    CloudServerOutlined,
    ThunderboltOutlined,
    UploadOutlined,
    DownloadOutlined,
    ClockCircleOutlined,
} from '@ant-design/icons';
import {
    LineChart,
    Line,
    AreaChart,
    Area,
    BarChart,
    Bar,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    Legend,
    ResponsiveContainer,
    PieChart,
    Pie,
    Cell,
} from 'recharts';
import './NASAnalyticsPage.css';

const { Title, Text } = Typography;
const { Option } = Select;

const NASAnalyticsPage = () => {
    const [loading, setLoading] = useState(false);
    const [statistics, setStatistics] = useState(null);
    const [logs, setLogs] = useState([]);
    const [timeRange, setTimeRange] = useState(7); // 默認7天

    useEffect(() => {
        fetchData();
        // 設置自動刷新（每30秒）
        const interval = setInterval(fetchData, 30000);
        return () => clearInterval(interval);
    }, [timeRange]);

    const fetchData = async () => {
        setLoading(true);
        try {
            // 獲取統計資料
            const statsResponse = await axios.get(`/api/nas-logs/statistics/?days=${timeRange}`);
            setStatistics(statsResponse.data);

            // 獲取記錄列表
            const logsResponse = await axios.get(`/api/nas-logs/?days=${timeRange}`);
            setLogs(logsResponse.data);
        } catch (error) {
            console.error('Error fetching NAS data:', error);
            message.error('載入 NAS 數據失敗：' + error.message);
        } finally {
            setLoading(false);
        }
    };

    // 表格列定義
    const columns = [
        {
            title: '時間',
            dataIndex: 'timestamp',
            key: 'timestamp',
            width: 180,
            render: (timestamp) => new Date(timestamp).toLocaleString('zh-TW'),
            sorter: (a, b) => new Date(a.timestamp) - new Date(b.timestamp),
        },
        {
            title: '狀態',
            dataIndex: 'status',
            key: 'status',
            width: 100,
            render: (status) => (
                <Tag
                    icon={status === 'success' ? <CheckCircleOutlined /> : <CloseCircleOutlined />}
                    color={status === 'success' ? 'success' : 'error'}
                >
                    {status === 'success' ? '成功' : '失敗'}
                </Tag>
            ),
            filters: [
                { text: '成功', value: 'success' },
                { text: '失敗', value: 'failed' },
            ],
            onFilter: (value, record) => record.status === value,
        },
        {
            title: 'NAS IP',
            dataIndex: 'nas_ip',
            key: 'nas_ip',
            width: 140,
        },
        {
            title: '共享名稱',
            dataIndex: 'nas_share',
            key: 'nas_share',
            width: 120,
        },
        {
            title: '響應時間',
            dataIndex: 'response_time',
            key: 'response_time',
            width: 120,
            render: (time) => time ? `${time.toFixed(2)} ms` : 'N/A',
            sorter: (a, b) => (a.response_time || 0) - (b.response_time || 0),
        },
        {
            title: '上傳速度',
            dataIndex: 'upload_speed',
            key: 'upload_speed',
            width: 120,
            render: (speed) => speed ? `${speed.toFixed(2)} MB/s` : 'N/A',
        },
        {
            title: '下載速度',
            dataIndex: 'download_speed',
            key: 'download_speed',
            width: 120,
            render: (speed) => speed ? `${speed.toFixed(2)} MB/s` : 'N/A',
        },
        {
            title: '錯誤訊息',
            dataIndex: 'error_message',
            key: 'error_message',
            ellipsis: true,
            render: (message) => message || '-',
        },
    ];

    // 成功率餅圖數據
    const pieData = statistics ? [
        { name: '成功', value: statistics.success_count, color: '#52c41a' },
        { name: '失敗', value: statistics.failed_count, color: '#ff4d4f' },
    ] : [];

    if (loading && !statistics) {
        return (
            <div style={{ padding: '24px', display: 'flex', justifyContent: 'center', alignItems: 'center', height: '80vh' }}>
                <Spin size="large" tip="載入中..." />
            </div>
        );
    }

    return (
        <div className="nas-analytics-page" style={{ padding: '24px', background: '#f5f5f5' }}>
            {/* 頁面標題 */}
            <div style={{ marginBottom: '24px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <Title level={2} style={{ margin: 0 }}>
                    <CloudServerOutlined /> NAS 連線分析
                </Title>
                <Space>
                    <Text>時間範圍：</Text>
                    <Select value={timeRange} onChange={setTimeRange} style={{ width: 120 }}>
                        <Option value={1}>最近 1 天</Option>
                        <Option value={3}>最近 3 天</Option>
                        <Option value={7}>最近 7 天</Option>
                        <Option value={14}>最近 14 天</Option>
                    </Select>
                </Space>
            </div>

            {/* NAS 配置資訊 */}
            <Alert
                message="NAS 配置資訊"
                description={
                    <Space direction="vertical">
                        <Text>IP: 10.250.0.1</Text>
                        <Text>共享: mdt</Text>
                        <Text>測試路徑: \\10.250.0.1\mdt\Script\chunwei_tset\nas_test</Text>
                        <Text type="secondary">每 5 分鐘自動檢測一次連線狀況</Text>
                    </Space>
                }
                type="info"
                showIcon
                style={{ marginBottom: '24px' }}
            />

            {/* 統計卡片 */}
            <Row gutter={[16, 16]} style={{ marginBottom: '24px' }}>
                <Col xs={24} sm={12} md={6}>
                    <Card>
                        <Statistic
                            title="總記錄數"
                            value={statistics?.total_records || 0}
                            prefix={<ClockCircleOutlined />}
                            valueStyle={{ color: '#2196f3' }}
                        />
                    </Card>
                </Col>
                <Col xs={24} sm={12} md={6}>
                    <Card>
                        <Statistic
                            title="成功率"
                            value={statistics?.success_rate || 0}
                            suffix="%"
                            prefix={<CheckCircleOutlined />}
                            valueStyle={{ color: '#52c41a' }}
                        />
                    </Card>
                </Col>
                <Col xs={24} sm={12} md={6}>
                    <Card>
                        <Statistic
                            title="平均響應時間"
                            value={statistics?.avg_response_time || 0}
                            suffix="ms"
                            prefix={<ThunderboltOutlined />}
                            precision={2}
                            valueStyle={{ color: '#faad14' }}
                        />
                    </Card>
                </Col>
                <Col xs={24} sm={12} md={6}>
                    <Card>
                        <Statistic
                            title="平均下載速度"
                            value={statistics?.avg_download_speed || 0}
                            suffix="MB/s"
                            prefix={<DownloadOutlined />}
                            precision={2}
                            valueStyle={{ color: '#722ed1' }}
                        />
                    </Card>
                </Col>
            </Row>

            {/* 圖表 */}
            <Row gutter={[16, 16]} style={{ marginBottom: '24px' }}>
                {/* 每日統計趨勢 */}
                <Col xs={24} lg={16}>
                    <Card title="每日連線統計" extra={<Text type="secondary">最近 7 天</Text>}>
                        {statistics?.daily_stats && statistics.daily_stats.length > 0 ? (
                            <ResponsiveContainer width="100%" height={300}>
                                <LineChart data={statistics.daily_stats}>
                                    <CartesianGrid strokeDasharray="3 3" />
                                    <XAxis dataKey="date" />
                                    <YAxis />
                                    <Tooltip />
                                    <Legend />
                                    <Line type="monotone" dataKey="success" stroke="#52c41a" name="成功" strokeWidth={2} />
                                    <Line type="monotone" dataKey="failed" stroke="#ff4d4f" name="失敗" strokeWidth={2} />
                                    <Line type="monotone" dataKey="total" stroke="#2196f3" name="總計" strokeWidth={2} strokeDasharray="5 5" />
                                </LineChart>
                            </ResponsiveContainer>
                        ) : (
                            <Empty description="暫無數據" />
                        )}
                    </Card>
                </Col>

                {/* 成功率餅圖 */}
                <Col xs={24} lg={8}>
                    <Card title="連線狀態分佈" extra={<Text type="secondary">總計</Text>}>
                        {pieData.length > 0 && pieData.some(d => d.value > 0) ? (
                            <ResponsiveContainer width="100%" height={300}>
                                <PieChart>
                                    <Pie
                                        data={pieData}
                                        cx="50%"
                                        cy="50%"
                                        labelLine={false}
                                        label={({ name, percent }) => `${name}: ${(percent * 100).toFixed(1)}%`}
                                        outerRadius={80}
                                        fill="#8884d8"
                                        dataKey="value"
                                    >
                                        {pieData.map((entry, index) => (
                                            <Cell key={`cell-${index}`} fill={entry.color} />
                                        ))}
                                    </Pie>
                                    <Tooltip />
                                </PieChart>
                            </ResponsiveContainer>
                        ) : (
                            <Empty description="暫無數據" />
                        )}
                    </Card>
                </Col>

                {/* 每小時統計 */}
                <Col xs={24}>
                    <Card title="每小時連線統計" extra={<Text type="secondary">最近 24 小時</Text>}>
                        {statistics?.hourly_stats && statistics.hourly_stats.length > 0 ? (
                            <ResponsiveContainer width="100%" height={300}>
                                <AreaChart data={statistics.hourly_stats}>
                                    <CartesianGrid strokeDasharray="3 3" />
                                    <XAxis dataKey="hour" angle={-45} textAnchor="end" height={80} />
                                    <YAxis />
                                    <Tooltip />
                                    <Legend />
                                    <Area type="monotone" dataKey="success" stackId="1" stroke="#52c41a" fill="#52c41a" name="成功" />
                                    <Area type="monotone" dataKey="failed" stackId="1" stroke="#ff4d4f" fill="#ff4d4f" name="失敗" />
                                </AreaChart>
                            </ResponsiveContainer>
                        ) : (
                            <Empty description="暫無數據" />
                        )}
                    </Card>
                </Col>
            </Row>

            {/* 詳細記錄表格 */}
            <Card title="詳細連線記錄" extra={<Text type="secondary">共 {logs.length} 筆</Text>}>
                <Table
                    columns={columns}
                    dataSource={logs}
                    rowKey="id"
                    loading={loading}
                    pagination={{
                        pageSize: 20,
                        showSizeChanger: true,
                        showTotal: (total) => `共 ${total} 筆記錄`,
                    }}
                    scroll={{ x: 1200 }}
                    size="middle"
                />
            </Card>
        </div>
    );
};

export default NASAnalyticsPage;
