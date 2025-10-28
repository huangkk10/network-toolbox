import React, { useState, useEffect } from 'react';
import { Row, Col, Card, Statistic, Table, message, Spin } from 'antd';
import {
    CloudServerOutlined,
    FileTextOutlined,
    ApiOutlined,
    DatabaseOutlined,
    RiseOutlined,
    FallOutlined,
} from '@ant-design/icons';
import axios from 'axios';
import { LineChart, Line, BarChart, Bar, PieChart, Pie, Cell, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';

const OverviewTab = ({ serverId }) => {
    const [overview, setOverview] = useState(null);
    const [loading, setLoading] = useState(false);

    const fetchOverview = async () => {
        setLoading(true);
        try {
            const params = serverId !== 'all' ? { server_id: serverId } : {};
            const response = await axios.get('/api/ipxe-analytics/overview/', { params });
            setOverview(response.data);
        } catch (error) {
            console.error('Error fetching overview:', error);
            message.error('載入概覽資料失敗：' + (error.response?.data?.message || error.message));
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchOverview();
        
        // 自動刷新（每 10 分鐘）
        const intervalId = setInterval(() => {
            fetchOverview();
        }, 10 * 60 * 1000);

        return () => clearInterval(intervalId);
    }, [serverId]);

    if (loading && !overview) {
        return (
            <div style={{ textAlign: 'center', padding: '50px' }}>
                <Spin size="large" tip="載入資料中..." />
            </div>
        );
    }

    if (!overview) {
        return <div style={{ textAlign: 'center', padding: '50px', color: '#999' }}>暫無資料</div>;
    }

    const { summary, daily_trends, log_type_distribution, top_mac_addresses, recent_boot_files } = overview;

    // 日誌類型分佈餅圖資料
    const pieData = [
        { name: 'MAC 管理', value: log_type_distribution?.MAC || 0, color: '#2196f3' },
        { name: 'BOOT 請求', value: log_type_distribution?.BOOT || 0, color: '#52c41a' },
    ];

    return (
        <div>
            {/* 統計卡片 */}
            <Row gutter={[16, 16]} style={{ marginBottom: '24px' }}>
                <Col xs={24} sm={12} md={6}>
                    <Card>
                        <Statistic
                            title="總伺服器數"
                            value={summary?.total_servers || 0}
                            prefix={<CloudServerOutlined />}
                            valueStyle={{ color: '#2196f3' }}
                        />
                    </Card>
                </Col>
                <Col xs={24} sm={12} md={6}>
                    <Card>
                        <Statistic
                            title="總日誌筆數"
                            value={summary?.total_logs || 0}
                            prefix={<FileTextOutlined />}
                            valueStyle={{ color: '#52c41a' }}
                        />
                    </Card>
                </Col>
                <Col xs={24} sm={12} md={6}>
                    <Card>
                        <Statistic
                            title="MAC 管理請求"
                            value={summary?.mac_logs || 0}
                            prefix={<ApiOutlined />}
                            valueStyle={{ color: '#faad14' }}
                        />
                    </Card>
                </Col>
                <Col xs={24} sm={12} md={6}>
                    <Card>
                        <Statistic
                            title="BOOT 請求"
                            value={summary?.boot_logs || 0}
                            prefix={<DatabaseOutlined />}
                            valueStyle={{ color: '#f5222d' }}
                        />
                    </Card>
                </Col>
            </Row>

            <Row gutter={[16, 16]}>
                {/* 每日趨勢圖 */}
                <Col xs={24} lg={16}>
                    <Card title="過去 7 天日誌趨勢">
                        <ResponsiveContainer width="100%" height={300}>
                            <LineChart data={daily_trends || []}>
                                <CartesianGrid strokeDasharray="3 3" />
                                <XAxis dataKey="date" />
                                <YAxis />
                                <Tooltip />
                                <Legend />
                                <Line type="monotone" dataKey="mac_count" stroke="#2196f3" name="MAC 管理" strokeWidth={2} />
                                <Line type="monotone" dataKey="boot_count" stroke="#52c41a" name="BOOT 請求" strokeWidth={2} />
                            </LineChart>
                        </ResponsiveContainer>
                    </Card>
                </Col>

                {/* 日誌類型分佈 */}
                <Col xs={24} lg={8}>
                    <Card title="日誌類型分佈">
                        <ResponsiveContainer width="100%" height={300}>
                            <PieChart>
                                <Pie
                                    data={pieData}
                                    cx="50%"
                                    cy="50%"
                                    labelLine={false}
                                    label={({ name, percent }) => `${name}: ${(percent * 100).toFixed(0)}%`}
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
                    </Card>
                </Col>

                {/* Top MAC 地址 */}
                <Col xs={24} lg={12}>
                    <Card title="Top 10 活躍 MAC 地址">
                        <Table
                            dataSource={top_mac_addresses || []}
                            columns={[
                                { title: 'MAC 地址', dataIndex: 'mac_address', key: 'mac_address' },
                                { title: '請求次數', dataIndex: 'count', key: 'count', sorter: (a, b) => b.count - a.count },
                            ]}
                            pagination={false}
                            size="small"
                            rowKey="mac_address"
                        />
                    </Card>
                </Col>

                {/* 最近請求的 BOOT 文件 */}
                <Col xs={24} lg={12}>
                    <Card title="最近請求的 BOOT 文件">
                        <Table
                            dataSource={recent_boot_files || []}
                            columns={[
                                { title: '文件路徑', dataIndex: 'file_path', key: 'file_path', ellipsis: true },
                                { title: '請求次數', dataIndex: 'count', key: 'count', sorter: (a, b) => b.count - a.count },
                            ]}
                            pagination={false}
                            size="small"
                            rowKey="file_path"
                        />
                    </Card>
                </Col>
            </Row>
        </div>
    );
};

export default OverviewTab;
