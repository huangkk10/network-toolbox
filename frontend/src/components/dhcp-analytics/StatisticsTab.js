import React, { useState } from 'react';
import { Card, Row, Col, Select, Space, Table, Statistic } from 'antd';
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

const StatisticsTab = ({ serverId }) => {
    const [timeRange, setTimeRange] = useState('7d');

    // 租約增長趨勢數據
    const growthData = [
        { date: '10/20', count: 1000 },
        { date: '10/21', count: 1040 },
        { date: '10/22', count: 1080 },
        { date: '10/23', count: 1140 },
        { date: '10/24', count: 1180 },
        { date: '10/25', count: 1210 },
        { date: '10/26', count: 1245 },
    ];

    // 每日活躍租約數
    const dailyActiveData = [
        { day: '週一', count: 720 },
        { day: '週二', count: 750 },
        { day: '週三', count: 780 },
        { day: '週四', count: 820 },
        { day: '週五', count: 850 },
        { day: '週六', count: 670 },
        { day: '週日', count: 650 },
    ];

    // Top 10 活躍客戶端
    const topClientsData = [
        { hostname: 'desktop-001', count: 156 },
        { hostname: 'laptop-005', count: 142 },
        { hostname: 'server-web-01', count: 98 },
        { hostname: 'printer-002', count: 87 },
        { hostname: 'mobile-device-123', count: 76 },
        { hostname: 'iot-sensor-01', count: 65 },
        { hostname: 'tablet-10', count: 54 },
        { hostname: 'camera-entrance', count: 48 },
        { hostname: 'switch-floor2', count: 42 },
        { hostname: 'ap-office-3', count: 38 },
    ];

    // MAC Vendor 分佈
    const vendorData = [
        { name: 'Dell Inc.', value: 320, color: '#2196f3' },
        { name: 'Apple, Inc.', value: 280, color: '#52c41a' },
        { name: 'Samsung Electronics', value: 210, color: '#faad14' },
        { name: 'HP Inc.', value: 180, color: '#ff4d4f' },
        { name: '其他', value: 255, color: '#d9d9d9' },
    ];

    // 每日統計摘要
    const dailySummary = [
        {
            key: '1',
            date: '2025-10-26',
            total: 1245,
            active: 892,
            expired: 253,
            released: 100,
            utilization: '71.6%',
        },
        {
            key: '2',
            date: '2025-10-25',
            total: 1210,
            active: 870,
            expired: 240,
            released: 100,
            utilization: '69.8%',
        },
        {
            key: '3',
            date: '2025-10-24',
            total: 1180,
            active: 850,
            expired: 230,
            released: 100,
            utilization: '68.2%',
        },
        {
            key: '4',
            date: '2025-10-23',
            total: 1140,
            active: 820,
            expired: 220,
            released: 100,
            utilization: '66.5%',
        },
        {
            key: '5',
            date: '2025-10-22',
            total: 1080,
            active: 780,
            expired: 200,
            released: 100,
            utilization: '64.1%',
        },
    ];

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
                            <LineChart data={growthData}>
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
                                />
                            </LineChart>
                        </ResponsiveContainer>
                    </Card>
                </Col>

                {/* 每日活躍租約數 */}
                <Col xs={24} lg={12}>
                    <Card title="每日活躍租約數" bordered={false}>
                        <ResponsiveContainer width="100%" height={250}>
                            <BarChart data={dailyActiveData}>
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
                        <ResponsiveContainer width="100%" height={300}>
                            <BarChart data={topClientsData} layout="vertical">
                                <CartesianGrid strokeDasharray="3 3" />
                                <XAxis type="number" />
                                <YAxis dataKey="hostname" type="category" width={120} />
                                <Tooltip />
                                <Legend />
                                <Bar dataKey="count" fill="#2196f3" name="租約次數" />
                            </BarChart>
                        </ResponsiveContainer>
                    </Card>
                </Col>

                {/* MAC Vendor 分佈 */}
                <Col xs={24} lg={12}>
                    <Card title="設備製造商分佈" bordered={false}>
                        <ResponsiveContainer width="100%" height={300}>
                            <PieChart>
                                <Pie
                                    data={vendorData}
                                    cx="50%"
                                    cy="50%"
                                    labelLine={false}
                                    label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                                    outerRadius={100}
                                    fill="#8884d8"
                                    dataKey="value"
                                >
                                    {vendorData.map((entry, index) => (
                                        <Cell key={`cell-${index}`} fill={entry.color} />
                                    ))}
                                </Pie>
                                <Tooltip />
                            </PieChart>
                        </ResponsiveContainer>
                    </Card>
                </Col>
            </Row>

            {/* 每日統計摘要表 */}
            <Card title="每日統計摘要" bordered={false}>
                <Table
                    columns={summaryColumns}
                    dataSource={dailySummary}
                    pagination={false}
                    size="middle"
                />
            </Card>
        </div>
    );
};

export default StatisticsTab;
