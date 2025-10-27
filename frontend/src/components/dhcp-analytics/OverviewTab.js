import React, { useState, useEffect } from 'react';
import { Card, Row, Col, Statistic, Table, Tag, Progress, message } from 'antd';
import {
    CheckCircleOutlined,
    ClockCircleOutlined,
    GlobalOutlined,
    ArrowUpOutlined,
    ArrowDownOutlined,
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
import axios from 'axios';

const OverviewTab = ({ serverId }) => {
    const [loading, setLoading] = useState(false);
    const [stats, setStats] = useState({
        totalLeases: 0,
        activeLeases: 0,
        expiredLeases: 0,
        ipUtilization: 0,
        trend: 0,
    });
    const [trendData, setTrendData] = useState([]);
    const [statusDistribution, setStatusDistribution] = useState([]);
    const [recentLeases, setRecentLeases] = useState([]);

    // 載入總覽統計
    const fetchOverviewStats = async () => {
        try {
            const response = await axios.get('/api/dhcp-analytics/overview/', {
                params: { server: serverId }
            });
            setStats({
                totalLeases: response.data.total_leases || 0,
                activeLeases: response.data.active_leases || 0,
                expiredLeases: response.data.expired_leases || 0,
                ipUtilization: response.data.ip_utilization || 0,
                trend: response.data.trend || 0,
            });
        } catch (error) {
            console.error('載入統計資料失敗:', error);
            message.error('載入統計資料失敗：' + (error.response?.data?.error || error.message));
        }
    };

    // 載入趨勢資料
    const fetchTrendData = async () => {
        try {
            const response = await axios.get('/api/dhcp-analytics/trend/', {
                params: { server: serverId, days: 7 }
            });
            setTrendData(response.data || []);
        } catch (error) {
            console.error('載入趨勢資料失敗:', error);
            message.error('載入趨勢資料失敗：' + (error.response?.data?.error || error.message));
        }
    };

    // 載入狀態分佈
    const fetchStatusDistribution = async () => {
        try {
            const response = await axios.get('/api/dhcp-analytics/status-distribution/', {
                params: { server: serverId }
            });
            setStatusDistribution(response.data || []);
        } catch (error) {
            console.error('載入狀態分佈失敗:', error);
            message.error('載入狀態分佈失敗：' + (error.response?.data?.error || error.message));
        }
    };

    // 載入最近租約
    const fetchRecentLeases = async () => {
        try {
            const response = await axios.get('/api/dhcp-analytics/recent-leases/', {
                params: { server: serverId, limit: 10 }
            });
            setRecentLeases(response.data || []);
        } catch (error) {
            console.error('載入最近租約失敗:', error);
            message.error('載入最近租約失敗：' + (error.response?.data?.error || error.message));
        }
    };

    // 載入所有資料
    const fetchAllData = async () => {
        setLoading(true);
        try {
            await Promise.all([
                fetchOverviewStats(),
                fetchTrendData(),
                fetchStatusDistribution(),
                fetchRecentLeases(),
            ]);
        } finally {
            setLoading(false);
        }
    };

    // 當 serverId 改變時重新載入資料
    useEffect(() => {
        fetchAllData();
    }, [serverId]);

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
                    <Card loading={loading}>
                        <Statistic
                            title="總租約數"
                            value={stats.totalLeases}
                            prefix={<GlobalOutlined />}
                            valueStyle={{ color: '#2196f3' }}
                        />
                    </Card>
                </Col>
                <Col xs={24} sm={12} lg={6}>
                    <Card loading={loading}>
                        <Statistic
                            title="活躍租約"
                            value={stats.activeLeases}
                            prefix={<CheckCircleOutlined />}
                            suffix={
                                stats.trend !== 0 && (
                                    <span style={{ fontSize: '14px', color: stats.trend > 0 ? '#52c41a' : '#ff4d4f' }}>
                                        {stats.trend > 0 ? <ArrowUpOutlined /> : <ArrowDownOutlined />} {Math.abs(stats.trend).toFixed(1)}%
                                    </span>
                                )
                            }
                            valueStyle={{ color: '#52c41a' }}
                        />
                    </Card>
                </Col>
                <Col xs={24} sm={12} lg={6}>
                    <Card loading={loading}>
                        <Statistic
                            title="已過期租約"
                            value={stats.expiredLeases}
                            prefix={<ClockCircleOutlined />}
                            valueStyle={{ color: '#faad14' }}
                        />
                    </Card>
                </Col>
                <Col xs={24} sm={12} lg={6}>
                    <Card loading={loading}>
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
                    <Card title="租約趨勢（最近 7 天）" bordered={false} loading={loading}>
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
                    <Card title="租約狀態分佈" bordered={false} loading={loading}>
                        <ResponsiveContainer width="100%" height={300}>
                            <PieChart>
                                <Pie
                                    data={statusDistribution}
                                    cx="50%"
                                    cy="50%"
                                    labelLine={false}
                                    label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                                    outerRadius={80}
                                    fill="#8884d8"
                                    dataKey="value"
                                >
                                    {statusDistribution.map((entry, index) => (
                                        <Cell key={`cell-${index}`} fill={entry.color} />
                                    ))}
                                </Pie>
                                <Tooltip />
                            </PieChart>
                        </ResponsiveContainer>
                    </Card>
                </Col>
            </Row>

            {/* 最近租約 */}
            <Card title="最近租約" bordered={false}>
                <Table
                    columns={leaseColumns}
                    dataSource={recentLeases}
                    pagination={{ pageSize: 10 }}
                    size="middle"
                    loading={loading}
                />
            </Card>
        </div>
    );
};

export default OverviewTab;
