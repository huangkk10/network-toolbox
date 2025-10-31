import React, { useState, useEffect } from 'react';
import { Card, Row, Col, Select, Space, Table, Statistic, Spin, message } from 'antd';
import {
    LineChart,
    Line,
    BarChart,
    Bar,
    PieChart,
    Pie,
    Cell,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    Legend,
    ResponsiveContainer,
} from 'recharts';
import axios from 'axios';

const StatisticsTab = ({ serverId }) => {
    const [timeRange, setTimeRange] = useState('7d');
    const [loading, setLoading] = useState(false);
    const [statisticsData, setStatisticsData] = useState(null);

    // 獲取統計數據
    const fetchStatistics = async () => {
        setLoading(true);
        try {
            const days = timeRange === '7d' ? 7 : timeRange === '30d' ? 30 : timeRange === '90d' ? 90 : 7;
            const response = await axios.get('/api/dhcp-analytics/statistics/', {
                params: {
                    server: serverId,
                    days: days,
                },
            });
            setStatisticsData(response.data);
        } catch (error) {
            console.error('獲取統計數據失敗:', error);
            message.error('載入統計數據失敗：' + (error.response?.data?.error || error.message));
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        if (serverId) {
            fetchStatistics();
        }
    }, [serverId, timeRange]);

    // 如果還在載入或沒有數據
    if (loading || !statisticsData) {
        return (
            <div style={{ textAlign: 'center', padding: '50px' }}>
                <Spin size="large" />
                <div style={{ marginTop: '16px' }}>載入統計數據中...</div>
            </div>
        );
    }

    const { growth_data, daily_active_data, top_clients_data, vendor_data, daily_summary } = statisticsData;

    const summaryColumns = [
        {
            title: '日期',
            dataIndex: 'date',
            key: 'date',
        },
        {
            title: '總租約數',
            dataIndex: 'total',
            key: 'total',
        },
        {
            title: '活躍',
            dataIndex: 'active',
            key: 'active',
        },
        {
            title: '過期',
            dataIndex: 'expired',
            key: 'expired',
        },
        {
            title: '已釋放',
            dataIndex: 'released',
            key: 'released',
        },
        {
            title: 'IP 使用率',
            dataIndex: 'utilization',
            key: 'utilization',
        },
    ];

    return (
        <div>
            {/* 時間範圍選擇 */}
            <Card size="small" style={{ marginBottom: '16px' }}>
                <Space>
                    <span>時間範圍:</span>
                    <Select
                        style={{ width: 150 }}
                        value={timeRange}
                        onChange={setTimeRange}
                        options={[
                            { value: '7d', label: '最近 7 天' },
                            { value: '30d', label: '最近 30 天' },
                            { value: '90d', label: '最近 90 天' },
                            { value: 'custom', label: '自訂範圍' },
                        ]}
                    />
                </Space>
            </Card>

            {/* 圖表區域 */}
            <Row gutter={[16, 16]} style={{ marginBottom: '24px' }}>
                {/* 租約增長趨勢 */}
                <Col xs={24} lg={12}>
                    <Card title="租約增長趨勢" bordered={false}>
                        <ResponsiveContainer width="100%" height={250}>
                            <LineChart data={growth_data}>
                                <CartesianGrid strokeDasharray="3 3" />
                                <XAxis dataKey="date" />
                                <YAxis />
                                <Tooltip />
                                <Legend />
                                <Line
                                    type="monotone"
                                    dataKey="count"
                                    stroke="#2196f3"
                                    strokeWidth={2}
                                    name="租約總數"
                                    connectNulls={true}
                                />
                            </LineChart>
                        </ResponsiveContainer>
                    </Card>
                </Col>

                {/* 每日活躍租約數 */}
                <Col xs={24} lg={12}>
                    <Card title="每日活躍租約數" bordered={false}>
                        <ResponsiveContainer width="100%" height={250}>
                            <BarChart data={daily_active_data}>
                                <CartesianGrid strokeDasharray="3 3" />
                                <XAxis dataKey="day" />
                                <YAxis />
                                <Tooltip />
                                <Legend />
                                <Bar dataKey="count" fill="#52c41a" name="活躍租約" />
                            </BarChart>
                        </ResponsiveContainer>
                    </Card>
                </Col>

                {/* Top 10 活躍客戶端 */}
                <Col xs={24} lg={12}>
                    <Card title="Top 10 活躍客戶端" bordered={false}>
                        {top_clients_data && top_clients_data.length > 0 ? (
                            <ResponsiveContainer width="100%" height={300}>
                                <BarChart data={top_clients_data} layout="vertical">
                                    <CartesianGrid strokeDasharray="3 3" />
                                    <XAxis type="number" />
                                    <YAxis dataKey="hostname" type="category" width={120} />
                                    <Tooltip />
                                    <Legend />
                                    <Bar dataKey="count" fill="#2196f3" name="租約次數" />
                                </BarChart>
                            </ResponsiveContainer>
                        ) : (
                            <div style={{ textAlign: 'center', padding: '50px', color: '#999' }}>
                                暫無客戶端數據
                            </div>
                        )}
                    </Card>
                </Col>

                {/* MAC Vendor 分佈 */}
                <Col xs={24} lg={12}>
                    <Card title="設備製造商分佈" bordered={false}>
                        {vendor_data && vendor_data.length > 0 ? (
                            <ResponsiveContainer width="100%" height={300}>
                                <PieChart>
                                    <Pie
                                        data={vendor_data}
                                        cx="50%"
                                        cy="50%"
                                        labelLine={false}
                                        label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                                        outerRadius={100}
                                        fill="#8884d8"
                                        dataKey="value"
                                    >
                                        {vendor_data.map((entry, index) => (
                                            <Cell key={`cell-${index}`} fill={entry.color} />
                                        ))}
                                    </Pie>
                                    <Tooltip />
                                </PieChart>
                            </ResponsiveContainer>
                        ) : (
                            <div style={{ textAlign: 'center', padding: '50px', color: '#999' }}>
                                暫無製造商數據
                            </div>
                        )}
                    </Card>
                </Col>
            </Row>

            {/* 每日統計摘要表 */}
            <Card title="每日統計摘要" bordered={false}>
                <Table
                    columns={summaryColumns}
                    dataSource={daily_summary}
                    pagination={false}
                    size="middle"
                />
            </Card>
        </div>
    );
};

export default StatisticsTab;