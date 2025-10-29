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
const { TabPane } = Tabs;

const NASAnalyticsPage = () => {
    const [loading, setLoading] = useState(false);
    const [statistics, setStatistics] = useState(null);
    const [logs, setLogs] = useState([]);
    const [timeRange, setTimeRange] = useState(7); // 默認7天
    const [speedChartRange, setSpeedChartRange] = useState(7); // 傳輸速度圖表的時間範圍

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
            
            // 除錯：輸出速度趨勢數據
            console.log('速度趨勢數據:', statsResponse.data.speed_trends);
            console.log('速度趨勢數據數量:', statsResponse.data.speed_trends?.length || 0);

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

    // 根據選擇的時間範圍過濾傳輸速度數據
    const getFilteredSpeedData = () => {
        if (!statistics?.speed_trends || statistics.speed_trends.length === 0) {
            return [];
        }

        // 如果時間範圍等於或大於頁面全局設定，直接返回所有數據
        if (speedChartRange >= timeRange) {
            return statistics.speed_trends;
        }

        // 否則，只顯示最後 N 個數據點
        const now = new Date();
        const cutoffDate = new Date(now.getTime() - speedChartRange * 24 * 60 * 60 * 1000);
        
        // 嘗試解析時間字串（格式：MM-DD HH:MM 或 MM-DD HH:00）
        return statistics.speed_trends.filter(item => {
            try {
                const currentYear = now.getFullYear();
                // 將 "10-28 14:00" 轉換為完整日期
                const [datePart, timePart] = item.time.split(' ');
                const [month, day] = datePart.split('-');
                const [hour, minute] = timePart.split(':');
                
                const itemDate = new Date(currentYear, parseInt(month) - 1, parseInt(day), parseInt(hour), parseInt(minute) || 0);
                
                // 處理跨年的情況
                if (itemDate > now) {
                    itemDate.setFullYear(currentYear - 1);
                }
                
                return itemDate >= cutoffDate;
            } catch (error) {
                console.error('Error parsing date:', item.time, error);
                return true; // 如果解析失敗，保留該數據點
            }
        });
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
                {/* 連線統計（每日/每小時切換） */}
                <Col xs={24} lg={16}>
                    <Card title="連線統計">
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
                                            <Line type="monotone" dataKey="success" stroke="#52c41a" name="成功" strokeWidth={2} />
                                            <Line type="monotone" dataKey="failed" stroke="#ff4d4f" name="失敗" strokeWidth={2} />
                                            <Line type="monotone" dataKey="total" stroke="#2196f3" name="總計" strokeWidth={2} strokeDasharray="5 5" />
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

                {/* 成功率餅圖 */}
                <Col xs={24} lg={8}>
                    <Card title="連線狀態分佈" extra={<Text type="secondary">總計</Text>}>
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

                {/* 傳輸速度趨勢圖 */}
                <Col xs={24}>
                    <Card 
                        title="傳輸速度趨勢" 
                        extra={
                            <Space>
                                <Text type="secondary">上傳/下載速度（MB/s）</Text>
                                <Select 
                                    value={speedChartRange} 
                                    onChange={setSpeedChartRange} 
                                    style={{ width: 120 }}
                                    size="small"
                                >
                                    <Option value={1}>最近 1 天</Option>
                                    <Option value={3}>最近 3 天</Option>
                                    <Option value={7}>最近 1 週</Option>
                                    <Option value={14}>最近 2 週</Option>
                                </Select>
                            </Space>
                        }
                    >
                        {statistics?.speed_trends && statistics.speed_trends.length > 0 ? (
                            getFilteredSpeedData().length > 0 ? (
                                <ResponsiveContainer width="100%" height={350}>
                                    <LineChart data={getFilteredSpeedData()}>
                                        <CartesianGrid strokeDasharray="3 3" />
                                        <XAxis 
                                            dataKey="time" 
                                            angle={-45} 
                                            textAnchor="end" 
                                            height={80}
                                            style={{ fontSize: '12px' }}
                                        />
                                        <YAxis 
                                            label={{ value: '速度 (MB/s)', angle: -90, position: 'insideLeft' }}
                                            domain={[0, 'auto']}
                                        />
                                        <Tooltip 
                                            formatter={(value) => value ? `${value.toFixed(2)} MB/s` : 'N/A'}
                                            labelFormatter={(label) => `時間: ${label}`}
                                        />
                                        <Legend />
                                        <Line 
                                            type="monotone" 
                                            dataKey="upload_speed" 
                                            stroke="#1890ff" 
                                            strokeWidth={2.5}
                                            name="上傳速度" 
                                            dot={{ r: 3 }}
                                            activeDot={{ r: 5 }}
                                            connectNulls
                                        />
                                        <Line 
                                            type="monotone" 
                                            dataKey="download_speed" 
                                            stroke="#722ed1" 
                                            strokeWidth={2.5}
                                            name="下載速度" 
                                            dot={{ r: 3 }}
                                            activeDot={{ r: 5 }}
                                            connectNulls
                                        />
                                    </LineChart>
                                </ResponsiveContainer>
                            ) : (
                                <Empty 
                                    description={`選定時間範圍內暫無數據，請選擇較長的時間範圍或等待數據採集`}
                                    style={{ padding: '80px 0' }}
                                />
                            )
                        ) : (
                            <Empty 
                                description="暫無速度數據" 
                                style={{ padding: '80px 0' }}
                            />
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
