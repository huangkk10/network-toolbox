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
    Tabs,
} from 'antd';
import {
    CheckCircleOutlined,
    CloseCircleOutlined,
    GitlabOutlined,
    ThunderboltOutlined,
    ClockCircleOutlined,
    CloudOutlined,
    ApiOutlined,
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

const { Title, Text } = Typography;
const { Option } = Select;
const { TabPane } = Tabs;

const GitLabAnalyticsPage = () => {
    const [loading, setLoading] = useState(false);
    const [statistics, setStatistics] = useState(null);
    const [logs, setLogs] = useState([]);
    const [currentStatus, setCurrentStatus] = useState(null);
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
            const statsResponse = await axios.get(`/api/gitlab-connection/statistics/?days=${timeRange}`);
            setStatistics(statsResponse.data);

            // 獲取當前狀態
            const statusResponse = await axios.get('/api/gitlab-connection/current_status/');
            setCurrentStatus(statusResponse.data);

            // 獲取記錄列表
            const logsResponse = await axios.get(`/api/gitlab-connection/?days=${timeRange}`);
            setLogs(logsResponse.data);
        } catch (error) {
            console.error('Error fetching GitLab data:', error);
            message.error('載入 GitLab 數據失敗：' + error.message);
        } finally {
            setLoading(false);
        }
    };

    // 表格列定義
    const columns = [
        {
            title: '檢查時間',
            dataIndex: 'checked_at',
            key: 'checked_at',
            width: 180,
            render: (time) => new Date(time).toLocaleString('zh-TW'),
            sorter: (a, b) => new Date(a.checked_at) - new Date(b.checked_at),
        },
        {
            title: '狀態',
            dataIndex: 'status',
            key: 'status',
            width: 100,
            render: (status) => {
                const statusConfig = {
                    success: { icon: <CheckCircleOutlined />, color: 'success', text: '正常' },
                    failed: { icon: <CloseCircleOutlined />, color: 'error', text: '失敗' },
                    timeout: { icon: <ClockCircleOutlined />, color: 'warning', text: '超時' },
                };
                const config = statusConfig[status] || statusConfig.failed;
                return (
                    <Tag icon={config.icon} color={config.color}>
                        {config.text}
                    </Tag>
                );
            },
            filters: [
                { text: '正常', value: 'success' },
                { text: '失敗', value: 'failed' },
                { text: '超時', value: 'timeout' },
            ],
            onFilter: (value, record) => record.status === value,
        },
        {
            title: 'Ping 延遲',
            dataIndex: 'ping_latency',
            key: 'ping_latency',
            width: 120,
            render: (latency) => latency ? `${latency.toFixed(2)} ms` : 'N/A',
            sorter: (a, b) => (a.ping_latency || 999999) - (b.ping_latency || 999999),
        },
        {
            title: 'HTTP 響應',
            dataIndex: 'http_response_time',
            key: 'http_response_time',
            width: 120,
            render: (time) => time ? `${time.toFixed(3)} s` : 'N/A',
            sorter: (a, b) => (a.http_response_time || 999999) - (b.http_response_time || 999999),
        },
        {
            title: 'HTTP 狀態碼',
            dataIndex: 'http_status_code',
            key: 'http_status_code',
            width: 120,
            render: (code) => {
                if (!code) return 'N/A';
                const color = code < 300 ? 'success' : code < 400 ? 'processing' : code < 500 ? 'warning' : 'error';
                return <Tag color={color}>{code}</Tag>;
            },
        },
        {
            title: '封包遺失率',
            dataIndex: 'packet_loss',
            key: 'packet_loss',
            width: 120,
            render: (loss) => {
                const color = loss === 0 ? 'success' : loss < 10 ? 'warning' : 'error';
                return <Tag color={color}>{loss.toFixed(1)}%</Tag>;
            },
            sorter: (a, b) => (a.packet_loss || 0) - (b.packet_loss || 0),
        },
        {
            title: '可達性',
            dataIndex: 'is_reachable',
            key: 'is_reachable',
            width: 100,
            render: (reachable) => (
                <Tag color={reachable ? 'success' : 'error'}>
                    {reachable ? '可達' : '不可達'}
                </Tag>
            ),
        },
        {
            title: '錯誤訊息',
            dataIndex: 'error_message',
            key: 'error_message',
            ellipsis: true,
            render: (message) => message || '-',
        },
    ];

    // 狀態分佈餅圖數據
    const pieData = statistics ? [
        { name: '正常', value: statistics.successful_checks, color: '#52c41a' },
        { name: '失敗', value: statistics.failed_checks, color: '#ff4d4f' },
        { name: '超時', value: statistics.timeout_checks, color: '#faad14' },
    ].filter(item => item.value > 0) : [];

    if (loading && !statistics) {
        return (
            <div style={{ padding: '24px', display: 'flex', justifyContent: 'center', alignItems: 'center', height: '80vh' }}>
                <Spin size="large" tip="載入中..." />
            </div>
        );
    }

    return (
        <div style={{ padding: '24px', background: '#f5f5f5' }}>
            {/* 頁面標題 */}
            <div style={{ marginBottom: '24px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <Title level={2} style={{ margin: 0 }}>
                    <GitlabOutlined /> GitLab 連線品質分析
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

            {/* 當前狀態警示 */}
            {currentStatus && (
                <Alert
                    message="GitLab 伺服器當前狀態"
                    description={
                        <Space direction="vertical" style={{ width: '100%' }}>
                            <Row gutter={16}>
                                <Col span={12}>
                                    <Text strong>伺服器：</Text>
                                    <Text>{currentStatus.gitlab_name || 'GitLab Server'}</Text>
                                </Col>
                                <Col span={12}>
                                    <Text strong>URL：</Text>
                                    <Text copyable>{currentStatus.gitlab_url}</Text>
                                </Col>
                            </Row>
                            <Row gutter={16}>
                                <Col span={12}>
                                    <Text strong>狀態：</Text>
                                    <Tag
                                        color={currentStatus.status === 'success' ? 'success' : 'error'}
                                        icon={currentStatus.is_reachable ? <CheckCircleOutlined /> : <CloseCircleOutlined />}
                                    >
                                        {currentStatus.is_reachable ? '在線' : '離線'}
                                    </Tag>
                                </Col>
                                <Col span={12}>
                                    <Text strong>最後檢查：</Text>
                                    <Text>{currentStatus.minutes_since_check} 分鐘前</Text>
                                </Col>
                            </Row>
                            {currentStatus.ping_latency && (
                                <Row gutter={16}>
                                    <Col span={12}>
                                        <Text strong>Ping 延遲：</Text>
                                        <Text>{currentStatus.ping_latency.toFixed(2)} ms</Text>
                                    </Col>
                                    <Col span={12}>
                                        <Text strong>HTTP 響應：</Text>
                                        <Text>{currentStatus.http_response_time?.toFixed(3)} s</Text>
                                    </Col>
                                </Row>
                            )}
                            {currentStatus.error_message && (
                                <Text type="danger">錯誤：{currentStatus.error_message}</Text>
                            )}
                            <Text type="secondary">每 5 分鐘自動檢測一次連線品質</Text>
                        </Space>
                    }
                    type={currentStatus.is_reachable ? 'success' : 'error'}
                    showIcon
                    style={{ marginBottom: '24px' }}
                />
            )}

            {/* 統計卡片 */}
            <Row gutter={[16, 16]} style={{ marginBottom: '24px' }}>
                <Col xs={24} sm={12} md={6}>
                    <Card>
                        <Statistic
                            title="總檢查次數"
                            value={statistics?.total_checks || 0}
                            prefix={<ClockCircleOutlined />}
                            valueStyle={{ color: '#2196f3' }}
                        />
                    </Card>
                </Col>
                <Col xs={24} sm={12} md={6}>
                    <Card>
                        <Statistic
                            title="可用性"
                            value={statistics?.uptime_percentage || 0}
                            suffix="%"
                            prefix={<CheckCircleOutlined />}
                            valueStyle={{ color: '#52c41a' }}
                            precision={2}
                        />
                    </Card>
                </Col>
                <Col xs={24} sm={12} md={6}>
                    <Card>
                        <Statistic
                            title="平均 Ping 延遲"
                            value={statistics?.avg_ping_latency || 0}
                            suffix="ms"
                            prefix={<ApiOutlined />}
                            precision={2}
                            valueStyle={{ color: '#faad14' }}
                        />
                    </Card>
                </Col>
                <Col xs={24} sm={12} md={6}>
                    <Card>
                        <Statistic
                            title="平均 HTTP 響應"
                            value={statistics?.avg_http_response ? (statistics.avg_http_response * 1000).toFixed(0) : 0}
                            suffix="ms"
                            prefix={<ThunderboltOutlined />}
                            valueStyle={{ color: '#722ed1' }}
                        />
                    </Card>
                </Col>
            </Row>

            {/* 圖表 */}
            <Row gutter={[16, 16]} style={{ marginBottom: '24px' }}>
                {/* 連線統計（每日/每小時切換） */}
                <Col xs={24} lg={16}>
                    <Card title="連線品質統計">
                        <Tabs defaultActiveKey="daily">
                            <TabPane tab="每日趨勢" key="daily">
                                {statistics?.daily_trends && statistics.daily_trends.length > 0 ? (
                                    <ResponsiveContainer width="100%" height={350}>
                                        <LineChart data={statistics.daily_trends}>
                                            <CartesianGrid strokeDasharray="3 3" />
                                            <XAxis dataKey="date" />
                                            <YAxis yAxisId="left" />
                                            <YAxis yAxisId="right" orientation="right" />
                                            <Tooltip />
                                            <Legend />
                                            <Line
                                                yAxisId="left"
                                                type="monotone"
                                                dataKey="success_rate"
                                                stroke="#52c41a"
                                                name="成功率 (%)"
                                                strokeWidth={2}
                                            />
                                            <Line
                                                yAxisId="right"
                                                type="monotone"
                                                dataKey="avg_latency"
                                                stroke="#1890ff"
                                                name="平均延遲 (ms)"
                                                strokeWidth={2}
                                            />
                                        </LineChart>
                                    </ResponsiveContainer>
                                ) : (
                                    <Empty description="暫無每日數據" />
                                )}
                            </TabPane>
                            <TabPane tab="每小時趨勢" key="hourly">
                                {statistics?.hourly_trends && statistics.hourly_trends.length > 0 ? (
                                    <ResponsiveContainer width="100%" height={350}>
                                        <AreaChart data={statistics.hourly_trends}>
                                            <CartesianGrid strokeDasharray="3 3" />
                                            <XAxis
                                                dataKey="hour"
                                                angle={-45}
                                                textAnchor="end"
                                                height={80}
                                            />
                                            <YAxis />
                                            <Tooltip />
                                            <Legend />
                                            <Area
                                                type="monotone"
                                                dataKey="success_count"
                                                stackId="1"
                                                stroke="#52c41a"
                                                fill="#52c41a"
                                                name="成功"
                                            />
                                            <Area
                                                type="monotone"
                                                dataKey="total_checks"
                                                stroke="#2196f3"
                                                fill="none"
                                                name="總計"
                                                strokeDasharray="5 5"
                                            />
                                        </AreaChart>
                                    </ResponsiveContainer>
                                ) : (
                                    <Empty description="暫無每小時數據" />
                                )}
                            </TabPane>
                        </Tabs>
                    </Card>
                </Col>

                {/* 狀態分佈餅圖 */}
                <Col xs={24} lg={8}>
                    <Card title="連線狀態分佈">
                        {pieData.length > 0 ? (
                            <ResponsiveContainer width="100%" height={350}>
                                <PieChart>
                                    <Pie
                                        data={pieData}
                                        cx="50%"
                                        cy="50%"
                                        labelLine={false}
                                        label={({ name, percent }) => `${name}: ${(percent * 100).toFixed(1)}%`}
                                        outerRadius={100}
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

                {/* 網路延遲趨勢 */}
                <Col xs={24}>
                    <Card title="網路延遲趨勢" extra={<Text type="secondary">Ping 延遲 (ms)</Text>}>
                        {statistics?.daily_trends && statistics.daily_trends.length > 0 ? (
                            <ResponsiveContainer width="100%" height={300}>
                                <LineChart data={statistics.daily_trends}>
                                    <CartesianGrid strokeDasharray="3 3" />
                                    <XAxis dataKey="date" />
                                    <YAxis />
                                    <Tooltip />
                                    <Legend />
                                    <Line
                                        type="monotone"
                                        dataKey="avg_latency"
                                        stroke="#1890ff"
                                        strokeWidth={2.5}
                                        name="平均延遲"
                                        dot={{ r: 4 }}
                                        activeDot={{ r: 6 }}
                                    />
                                    <Line
                                        type="monotone"
                                        dataKey="avg_http_response"
                                        stroke="#722ed1"
                                        strokeWidth={2}
                                        name="HTTP 響應 (×100ms)"
                                        dot={{ r: 3 }}
                                        strokeDasharray="5 5"
                                    />
                                </LineChart>
                            </ResponsiveContainer>
                        ) : (
                            <Empty description="暫無延遲數據" />
                        )}
                    </Card>
                </Col>
            </Row>

            {/* 詳細記錄表格 */}
            <Card title="詳細檢查記錄" extra={<Text type="secondary">共 {logs.length} 筆</Text>}>
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
                    scroll={{ x: 1400 }}
                    size="middle"
                />
            </Card>
        </div>
    );
};

export default GitLabAnalyticsPage;
