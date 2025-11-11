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
    ClockCircleOutlined,
    ThunderboltOutlined,
    SyncOutlined,
    FieldTimeOutlined,
} from '@ant-design/icons';
import {
    LineChart,
    Line,
    AreaChart,
    Area,
    PieChart,
    Pie,
    Cell,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    Legend,
    ResponsiveContainer,
    ReferenceArea,
    ReferenceDot,
} from 'recharts';

const { Title, Text } = Typography;
const { Option } = Select;
const { TabPane } = Tabs;

const NTPAnalyticsPage = () => {
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
            const statsResponse = await axios.get(`/api/ntp-logs/statistics/?days=${timeRange}`);
            setStatistics(statsResponse.data);

            // 獲取記錄列表
            const logsResponse = await axios.get(`/api/ntp-logs/?days=${timeRange}`);
            setLogs(logsResponse.data);
        } catch (error) {
            console.error('Error fetching NTP data:', error);
            message.error('載入 NTP 數據失敗：' + error.message);
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
            title: 'NTP Server',
            dataIndex: 'ntp_server',
            key: 'ntp_server',
            width: 140,
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
            title: '時間偏移',
            dataIndex: 'offset',
            key: 'offset',
            width: 120,
            render: (offset) => {
                if (offset === null || offset === undefined) return 'N/A';
                const color = Math.abs(offset) > 100 ? 'error' : Math.abs(offset) > 50 ? 'warning' : 'success';
                return <Tag color={color}>{offset.toFixed(3)} ms</Tag>;
            },
            sorter: (a, b) => Math.abs(a.offset || 0) - Math.abs(b.offset || 0),
        },
        {
            title: 'Stratum',
            dataIndex: 'stratum',
            key: 'stratum',
            width: 100,
            render: (stratum) => {
                if (!stratum) return 'N/A';
                const color = stratum <= 2 ? 'success' : stratum <= 4 ? 'processing' : 'warning';
                return <Tag color={color}>{stratum}</Tag>;
            },
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
        <div style={{ padding: '24px', background: '#f5f5f5' }}>
            {/* 頁面標題 */}
            <div style={{ marginBottom: '24px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <Title level={2} style={{ margin: 0 }}>
                    <FieldTimeOutlined /> NTP 時間同步分析
                </Title>
                <Space>
                    <Text>時間範圍：</Text>
                    <Select value={timeRange} onChange={setTimeRange} style={{ width: 120 }}>
                        <Option value={1}>最近 1 天</Option>
                        <Option value={3}>最近 3 天</Option>
                        <Option value={7}>最近 7 天</Option>
                        <Option value={14}>最近 14 天</Option>
                        <Option value={30}>最近 30 天</Option>
                    </Select>
                </Space>
            </div>

            {/* NTP 配置資訊 */}
            <Alert
                message="NTP 配置資訊"
                description={
                    <Space direction="vertical">
                        <Text>NTP Server: 10.10.10.51</Text>
                        <Text>協議: NTP v4 (UDP Port 123)</Text>
                        <Text type="secondary">每 5 分鐘自動檢測一次時間同步狀況</Text>
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
                            title="同步成功率"
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
                            title="平均時間偏移"
                            value={statistics?.avg_offset ? Math.abs(statistics.avg_offset) : 0}
                            suffix="ms"
                            prefix={<SyncOutlined />}
                            precision={3}
                            valueStyle={{ color: '#722ed1' }}
                        />
                    </Card>
                </Col>
            </Row>

            {/* 圖表 */}
            <Row gutter={[16, 16]} style={{ marginBottom: '24px' }}>
                {/* 同步統計（每日/每小時切換） */}
                <Col xs={24} lg={16}>
                    <Card title="同步統計">
                        <Tabs defaultActiveKey="daily">
                            <TabPane tab="每日統計" key="daily">
                                {statistics?.daily_stats && statistics.daily_stats.length > 0 ? (
                                    <ResponsiveContainer width="100%" height={350}>
                                        <LineChart data={statistics.daily_stats}>
                                            <CartesianGrid strokeDasharray="3 3" />
                                            <XAxis dataKey="date" />
                                            <YAxis />
                                            <Tooltip />
                                            <Legend />
                                            <Line type="monotone" dataKey="success" stroke="#52c41a" name="成功" strokeWidth={2} connectNulls={true} />
                                            <Line type="monotone" dataKey="failed" stroke="#ff4d4f" name="失敗" strokeWidth={2} connectNulls={true} />
                                            <Line type="monotone" dataKey="total" stroke="#2196f3" name="總計" strokeWidth={2} strokeDasharray="5 5" connectNulls={true} />
                                        </LineChart>
                                    </ResponsiveContainer>
                                ) : (
                                    <Empty description="暫無每日數據" />
                                )}
                            </TabPane>
                            <TabPane tab="每小時統計" key="hourly">
                                {statistics?.hourly_stats && statistics.hourly_stats.length > 0 ? (
                                    <ResponsiveContainer width="100%" height={350}>
                                        <AreaChart data={statistics.hourly_stats}>
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
                                            <Area type="monotone" dataKey="success" stackId="1" stroke="#52c41a" fill="#52c41a" name="成功" />
                                            <Area type="monotone" dataKey="failed" stackId="1" stroke="#ff4d4f" fill="#ff4d4f" name="失敗" />
                                        </AreaChart>
                                    </ResponsiveContainer>
                                ) : (
                                    <Empty description="暫無每小時數據" />
                                )}
                            </TabPane>
                        </Tabs>
                    </Card>
                </Col>

                {/* 同步狀態餅圖 */}
                <Col xs={24} lg={8}>
                    <Card title="同步狀態分佈" extra={<Text type="secondary">總計</Text>}>
                        {pieData.length > 0 && pieData.some(d => d.value > 0) ? (
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

                {/* 時間偏移趨勢圖 */}
                <Col xs={24}>
                    <Card 
                        title={
                            <Space>
                                <span>時間偏移趨勢</span>
                                <Select 
                                    value={timeRange} 
                                    onChange={setTimeRange} 
                                    style={{ width: 120 }}
                                    size="small"
                                >
                                    <Option value={1}>最近 1 天</Option>
                                    <Option value={3}>最近 3 天</Option>
                                    <Option value={7}>最近 7 天</Option>
                                    <Option value={14}>最近 14 天</Option>
                                    <Option value={30}>最近 30 天</Option>
                                </Select>
                            </Space>
                        }
                        extra={
                            <Space>
                                <Tag color="#52c41a">優秀 (≤50ms)</Tag>
                                <Tag color="#faad14">良好 (50-100ms)</Tag>
                                <Tag color="#ff4d4f">警告 (&gt;100ms)</Tag>
                                <Tag icon={<CloseCircleOutlined />} color="error">同步失敗</Tag>
                            </Space>
                        }
                    >
                        {statistics?.offset_trends && statistics.offset_trends.length > 0 ? (
                            <ResponsiveContainer width="100%" height={350}>
                                <LineChart data={statistics.offset_trends} margin={{ top: 5, right: 30, left: 20, bottom: 50 }}>
                                    <CartesianGrid strokeDasharray="3 3" />
                                    {/* 品質區域：優秀（綠色） -50 到 50 */}
                                    <ReferenceArea y1={-50} y2={50} fill="#52c41a" fillOpacity={0.2} />
                                    {/* 品質區域：良好（黃色） 50 到 100 和 -100 到 -50 */}
                                    <ReferenceArea y1={50} y2={100} fill="#faad14" fillOpacity={0.2} />
                                    <ReferenceArea y1={-100} y2={-50} fill="#faad14" fillOpacity={0.2} />
                                    {/* 品質區域：警告（紅色） >100 和 <-100 */}
                                    <ReferenceArea y1={100} y2={200} fill="#ff4d4f" fillOpacity={0.2} />
                                    <ReferenceArea y1={-200} y2={-100} fill="#ff4d4f" fillOpacity={0.2} />
                                    <XAxis 
                                        dataKey="time" 
                                        angle={-45} 
                                        textAnchor="end" 
                                        height={80}
                                        tick={{ fontSize: 11 }}
                                    />
                                    <YAxis 
                                        label={{ value: '偏移量 (ms)', angle: -90, position: 'insideLeft' }}
                                        domain={[-200, 200]}
                                    />
                                    <Tooltip 
                                        content={({ active, payload }) => {
                                            if (active && payload && payload.length) {
                                                const data = payload[0].payload;
                                                return (
                                                    <div style={{ 
                                                        backgroundColor: 'white', 
                                                        padding: '10px', 
                                                        border: '1px solid #ccc',
                                                        borderRadius: '4px',
                                                        boxShadow: '0 2px 8px rgba(0,0,0,0.15)'
                                                    }}>
                                                        <p style={{ margin: '0 0 5px 0', fontWeight: 'bold' }}>{data.time}</p>
                                                        {data.status === 'failed' ? (
                                                            <p style={{ margin: 0, color: '#ff4d4f' }}>
                                                                ✕ 同步失敗
                                                            </p>
                                                        ) : (
                                                            <p style={{ margin: 0, color: '#722ed1' }}>
                                                                時間偏移: {data.offset ? data.offset.toFixed(3) + ' ms' : 'N/A'}
                                                            </p>
                                                        )}
                                                    </div>
                                                );
                                            }
                                            return null;
                                        }}
                                    />
                                    <Legend />
                                    <Line 
                                        type="monotone" 
                                        dataKey="offset" 
                                        stroke="#722ed1" 
                                        strokeWidth={3}
                                        name="時間偏移" 
                                        dot={({ cx, cy, payload }) => {
                                            // 只繪製成功的點
                                            if (payload && payload.status === 'success' && payload.offset !== null) {
                                                return <circle cx={cx} cy={cy} r={4} fill="#722ed1" stroke="#fff" strokeWidth={1} />;
                                            }
                                            // 失敗點不在這裡繪製
                                            return null;
                                        }}
                                        activeDot={{ r: 7 }}
                                        connectNulls={false}
                                        isAnimationActive={false}
                                    />
                                    {/* 使用 ReferenceDot 繪製失敗標記，確保在最上層 */}
                                    {statistics.offset_trends.map((item, index) => {
                                        if (item.status === 'failed') {
                                            return (
                                                <ReferenceDot
                                                    key={`failed-${index}`}
                                                    x={item.time}
                                                    y={0}  // 失敗時沒有 offset 值，顯示在 0 位置
                                                    r={10}
                                                    fill="#ff4d4f"
                                                    stroke="#fff"
                                                    strokeWidth={3}
                                                    shape={(props) => {
                                                        const { cx, cy } = props;
                                                        return (
                                                            <g>
                                                                {/* 紅色圓圈 */}
                                                                <circle 
                                                                    cx={cx} 
                                                                    cy={cy} 
                                                                    r={10} 
                                                                    fill="#ff4d4f" 
                                                                    stroke="#fff" 
                                                                    strokeWidth={3}
                                                                />
                                                                {/* 白色 X 符號 */}
                                                                <line 
                                                                    x1={cx - 5} 
                                                                    y1={cy - 5} 
                                                                    x2={cx + 5} 
                                                                    y2={cy + 5} 
                                                                    stroke="#fff" 
                                                                    strokeWidth={3} 
                                                                    strokeLinecap="round"
                                                                />
                                                                <line 
                                                                    x1={cx + 5} 
                                                                    y1={cy - 5} 
                                                                    x2={cx - 5} 
                                                                    y2={cy + 5} 
                                                                    stroke="#fff" 
                                                                    strokeWidth={3} 
                                                                    strokeLinecap="round"
                                                                />
                                                            </g>
                                                        );
                                                    }}
                                                />
                                            );
                                        }
                                        return null;
                                    })}
                                </LineChart>
                            </ResponsiveContainer>
                        ) : (
                            <Empty description="暫無偏移數據" />
                        )}
                    </Card>
                </Col>

                {/* 響應時間趨勢圖 */}
                <Col xs={24}>
                    <Card 
                        title={
                            <Space>
                                <span>響應時間趨勢</span>
                                <Select 
                                    value={timeRange} 
                                    onChange={setTimeRange} 
                                    style={{ width: 120 }}
                                    size="small"
                                >
                                    <Option value={1}>最近 1 天</Option>
                                    <Option value={3}>最近 3 天</Option>
                                    <Option value={7}>最近 7 天</Option>
                                    <Option value={14}>最近 14 天</Option>
                                    <Option value={30}>最近 30 天</Option>
                                </Select>
                            </Space>
                        }
                        extra={
                            <Space>
                                <Tag color="#52c41a">優秀 (≤20ms)</Tag>
                                <Tag color="#faad14">良好 (20-50ms)</Tag>
                                <Tag color="#ff4d4f">較慢 (&gt;50ms)</Tag>
                                <Tag icon={<CloseCircleOutlined />} color="error">同步失敗</Tag>
                            </Space>
                        }
                    >
                        {statistics?.response_trends && statistics.response_trends.length > 0 ? (
                            <ResponsiveContainer width="100%" height={350}>
                                <LineChart data={statistics.response_trends} margin={{ top: 5, right: 30, left: 20, bottom: 50 }}>
                                    <CartesianGrid strokeDasharray="3 3" />
                                    {/* 品質區域：優秀（綠色）0-20ms */}
                                    <ReferenceArea y1={0} y2={20} fill="#52c41a" fillOpacity={0.2} />
                                    {/* 品質區域：良好（黃色）20-50ms */}
                                    <ReferenceArea y1={20} y2={50} fill="#faad14" fillOpacity={0.2} />
                                    {/* 品質區域：較慢（紅色）>50ms */}
                                    <ReferenceArea y1={50} y2={1000} fill="#ff4d4f" fillOpacity={0.2} />
                                    <XAxis 
                                        dataKey="time" 
                                        angle={-45} 
                                        textAnchor="end" 
                                        height={80}
                                        tick={{ fontSize: 11 }}
                                    />
                                    <YAxis 
                                        label={{ value: '響應時間 (ms)', angle: -90, position: 'insideLeft' }}
                                        domain={[0, 'auto']}
                                    />
                                    <Tooltip 
                                        content={({ active, payload }) => {
                                            if (active && payload && payload.length) {
                                                const data = payload[0].payload;
                                                return (
                                                    <div style={{ 
                                                        backgroundColor: 'white', 
                                                        padding: '10px', 
                                                        border: '1px solid #ccc',
                                                        borderRadius: '4px',
                                                        boxShadow: '0 2px 8px rgba(0,0,0,0.15)'
                                                    }}>
                                                        <p style={{ margin: '0 0 5px 0', fontWeight: 'bold' }}>{data.time}</p>
                                                        {data.status === 'failed' ? (
                                                            <p style={{ margin: 0, color: '#ff4d4f' }}>
                                                                ✕ 同步失敗
                                                            </p>
                                                        ) : (
                                                            <p style={{ margin: 0, color: '#1890ff' }}>
                                                                響應時間: {data.response_time ? data.response_time.toFixed(2) + ' ms' : 'N/A'}
                                                            </p>
                                                        )}
                                                    </div>
                                                );
                                            }
                                            return null;
                                        }}
                                    />
                                    <Legend />
                                    <Line 
                                        type="monotone" 
                                        dataKey="response_time" 
                                        stroke="#1890ff" 
                                        strokeWidth={3}
                                        name="響應時間" 
                                        dot={({ cx, cy, payload }) => {
                                            // 只繪製成功的點
                                            if (payload && payload.status === 'success' && payload.response_time !== null) {
                                                return <circle cx={cx} cy={cy} r={4} fill="#1890ff" stroke="#fff" strokeWidth={1} />;
                                            }
                                            // 失敗點不在這裡繪製
                                            return null;
                                        }}
                                        activeDot={{ r: 7 }}
                                        connectNulls={false}
                                        isAnimationActive={false}
                                    />
                                    {/* 使用 ReferenceDot 繪製失敗標記，確保在最上層 */}
                                    {statistics.response_trends.map((item, index) => {
                                        if (item.status === 'failed') {
                                            return (
                                                <ReferenceDot
                                                    key={`failed-${index}`}
                                                    x={item.time}
                                                    y={50}  // 在響應時間圖中，失敗標記顯示在 50ms 位置（圖表中間）
                                                    r={10}
                                                    fill="#ff4d4f"
                                                    stroke="#fff"
                                                    strokeWidth={3}
                                                    shape={(props) => {
                                                        const { cx, cy } = props;
                                                        return (
                                                            <g>
                                                                {/* 紅色圓圈 */}
                                                                <circle 
                                                                    cx={cx} 
                                                                    cy={cy} 
                                                                    r={10} 
                                                                    fill="#ff4d4f" 
                                                                    stroke="#fff" 
                                                                    strokeWidth={3}
                                                                />
                                                                {/* 白色 X 符號 */}
                                                                <line 
                                                                    x1={cx - 5} 
                                                                    y1={cy - 5} 
                                                                    x2={cx + 5} 
                                                                    y2={cy + 5} 
                                                                    stroke="#fff" 
                                                                    strokeWidth={3} 
                                                                    strokeLinecap="round"
                                                                />
                                                                <line 
                                                                    x1={cx + 5} 
                                                                    y1={cy - 5} 
                                                                    x2={cx - 5} 
                                                                    y2={cy + 5} 
                                                                    stroke="#fff" 
                                                                    strokeWidth={3} 
                                                                    strokeLinecap="round"
                                                                />
                                                            </g>
                                                        );
                                                    }}
                                                />
                                            );
                                        }
                                        return null;
                                    })}
                                </LineChart>
                            </ResponsiveContainer>
                        ) : (
                            <Empty description="暫無響應數據" />
                        )}
                    </Card>
                </Col>
            </Row>

            {/* 詳細記錄表格 */}
            <Card title="詳細同步記錄" extra={<Text type="secondary">共 {logs.length} 筆</Text>}>
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
                    scroll={{ x: 1000 }}
                    size="middle"
                />
            </Card>
        </div>
    );
};

export default NTPAnalyticsPage;
