import React, { useState, useEffect } from 'react';
import { Card, Row, Col, Statistic, Table, Tag, Progress } from 'antd';
import {
    CheckCircleOutlined,
    ClockCircleOutlined,
    GlobalOutlined,
    ArrowUpOutlined,
} from '@ant-design/icons';
import {
    AreaChart,
    Area,
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

const OverviewTab = ({ serverId }) => {
    const [loading, setLoading] = useState(false);

    // 模擬統計數據
    const stats = {
        totalLeases: serverId === 'all' ? 1245 : 450,
        activeLeases: serverId === 'all' ? 892 : 320,
        expiredLeases: serverId === 'all' ? 353 : 130,
        ipUtilization: serverId === 'all' ? 71.6 : 68.2,
        trend: 12.5,
    };

    // 租約趨勢數據（最近 7 天）
    const trendData = [
        { date: '10/20', active: 720, expired: 280, total: 1000 },
        { date: '10/21', active: 750, expired: 290, total: 1040 },
        { date: '10/22', active: 780, expired: 300, total: 1080 },
        { date: '10/23', active: 820, expired: 320, total: 1140 },
        { date: '10/24', active: 850, expired: 330, total: 1180 },
        { date: '10/25', active: 870, expired: 340, total: 1210 },
        { date: '10/26', active: 892, expired: 353, total: 1245 },
    ];

    // IP 池使用分佈
    const ipPoolData = [
        { name: '192.168.1.0/24', used: 180, available: 74 },
        { name: '192.168.2.0/24', used: 220, available: 34 },
        { name: '192.168.3.0/24', used: 150, available: 104 },
        { name: '10.0.1.0/24', used: 200, available: 54 },
    ];

    // 租約狀態分佈
    const leaseStatusData = [
        { name: '活躍中', value: stats.activeLeases, color: '#52c41a' },
        { name: '已過期', value: 253, color: '#faad14' },
        { name: '已釋放', value: 100, color: '#d9d9d9' },
    ];

    // 最近租約列表
    const recentLeases = [
        {
            key: '1',
            ip: '192.168.1.100',
            mac: '00:1A:2B:3C:4D:5E',
            hostname: 'desktop-001',
            status: 'active',
            endTime: '2025-10-27 14:30:22',
        },
        {
            key: '2',
            ip: '192.168.1.101',
            mac: '00:1A:2B:3C:4D:5F',
            hostname: 'laptop-005',
            status: 'active',
            endTime: '2025-10-27 13:15:10',
        },
        {
            key: '3',
            ip: '192.168.2.50',
            mac: '00:1A:2B:3C:4D:60',
            hostname: 'server-db-01',
            status: 'expired',
            endTime: '2025-10-26 10:00:00',
        },
        {
            key: '4',
            ip: '10.0.1.200',
            mac: '00:1A:2B:3C:4D:61',
            hostname: 'printer-002',
            status: 'active',
            endTime: '2025-10-27 09:45:33',
        },
        {
            key: '5',
            ip: '192.168.1.150',
            mac: '00:1A:2B:3C:4D:62',
            hostname: 'mobile-device-123',
            status: 'active',
            endTime: '2025-10-27 16:20:45',
        },
    ];

    const leaseColumns = [
        {
            title: 'IP 位址',
            dataIndex: 'ip',
            key: 'ip',
        },
        {
            title: 'MAC 位址',
            dataIndex: 'mac',
            key: 'mac',
            render: (mac) => <code>{mac}</code>,
        },
        {
            title: '主機名稱',
            dataIndex: 'hostname',
            key: 'hostname',
        },
        {
            title: '狀態',
            dataIndex: 'status',
            key: 'status',
            render: (status) => (
                <Tag
                    color={status === 'active' ? 'success' : 'warning'}
                    icon={status === 'active' ? <CheckCircleOutlined /> : <ClockCircleOutlined />}
                >
                    {status === 'active' ? '活躍中' : '已過期'}
                </Tag>
            ),
        },
        {
            title: '到期時間',
            dataIndex: 'endTime',
            key: 'endTime',
        },
    ];

    return (
        <div>
            {/* 統計卡片 */}
            <Row gutter={[16, 16]} style={{ marginBottom: '24px' }}>
                <Col xs={24} sm={12} lg={6}>
                    <Card>
                        <Statistic
                            title="總租約數"
                            value={stats.totalLeases}
                            prefix={<GlobalOutlined />}
                            valueStyle={{ color: '#2196f3' }}
                        />
                    </Card>
                </Col>
                <Col xs={24} sm={12} lg={6}>
                    <Card>
                        <Statistic
                            title="活躍租約"
                            value={stats.activeLeases}
                            prefix={<CheckCircleOutlined />}
                            suffix={
                                <span style={{ fontSize: '14px', color: '#52c41a' }}>
                                    <ArrowUpOutlined /> {stats.trend}%
                                </span>
                            }
                            valueStyle={{ color: '#52c41a' }}
                        />
                    </Card>
                </Col>
                <Col xs={24} sm={12} lg={6}>
                    <Card>
                        <Statistic
                            title="已過期租約"
                            value={stats.expiredLeases}
                            prefix={<ClockCircleOutlined />}
                            valueStyle={{ color: '#faad14' }}
                        />
                    </Card>
                </Col>
                <Col xs={24} sm={12} lg={6}>
                    <Card>
                        <Statistic
                            title="IP 使用率"
                            value={stats.ipUtilization}
                            suffix="%"
                            valueStyle={{ color: stats.ipUtilization > 80 ? '#ff4d4f' : '#2196f3' }}
                        />
                        <Progress
                            percent={stats.ipUtilization}
                            strokeColor={stats.ipUtilization > 80 ? '#ff4d4f' : '#2196f3'}
                            showInfo={false}
                            style={{ marginTop: '8px' }}
                        />
                    </Card>
                </Col>
            </Row>

            {/* 圖表區域 */}
            <Row gutter={[16, 16]} style={{ marginBottom: '24px' }}>
                {/* 租約趨勢圖 */}
                <Col xs={24} lg={16}>
                    <Card title="租約趨勢（最近 7 天）" bordered={false}>
                        <ResponsiveContainer width="100%" height={300}>
                            <AreaChart data={trendData}>
                                <CartesianGrid strokeDasharray="3 3" />
                                <XAxis dataKey="date" />
                                <YAxis />
                                <Tooltip />
                                <Legend />
                                <Area
                                    type="monotone"
                                    dataKey="active"
                                    stackId="1"
                                    stroke="#52c41a"
                                    fill="#52c41a"
                                    name="活躍租約"
                                />
                                <Area
                                    type="monotone"
                                    dataKey="expired"
                                    stackId="1"
                                    stroke="#faad14"
                                    fill="#faad14"
                                    name="過期租約"
                                />
                            </AreaChart>
                        </ResponsiveContainer>
                    </Card>
                </Col>

                {/* 租約狀態分佈 */}
                <Col xs={24} lg={8}>
                    <Card title="租約狀態分佈" bordered={false}>
                        <ResponsiveContainer width="100%" height={300}>
                            <PieChart>
                                <Pie
                                    data={leaseStatusData}
                                    cx="50%"
                                    cy="50%"
                                    labelLine={false}
                                    label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                                    outerRadius={80}
                                    fill="#8884d8"
                                    dataKey="value"
                                >
                                    {leaseStatusData.map((entry, index) => (
                                        <Cell key={`cell-${index}`} fill={entry.color} />
                                    ))}
                                </Pie>
                                <Tooltip />
                            </PieChart>
                        </ResponsiveContainer>
                    </Card>
                </Col>
            </Row>

            {/* IP 池使用情況 */}
            <Row gutter={[16, 16]} style={{ marginBottom: '24px' }}>
                <Col xs={24}>
                    <Card title="IP 池使用情況" bordered={false}>
                        <ResponsiveContainer width="100%" height={250}>
                            <BarChart data={ipPoolData}>
                                <CartesianGrid strokeDasharray="3 3" />
                                <XAxis dataKey="name" />
                                <YAxis />
                                <Tooltip />
                                <Legend />
                                <Bar dataKey="used" fill="#2196f3" name="已使用" />
                                <Bar dataKey="available" fill="#52c41a" name="可用" />
                            </BarChart>
                        </ResponsiveContainer>
                    </Card>
                </Col>
            </Row>

            {/* 最近租約 */}
            <Card title="最近租約" bordered={false}>
                <Table
                    columns={leaseColumns}
                    dataSource={recentLeases}
                    pagination={{ pageSize: 5 }}
                    size="middle"
                    loading={loading}
                />
            </Card>
        </div>
    );
};

export default OverviewTab;
