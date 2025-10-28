import React, { useState, useEffect } from 'react';
import { Row, Col, Card, Statistic, Select, DatePicker, Space, Button, message, Spin } from 'antd';
import { LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { ReloadOutlined, RiseOutlined, FallOutlined } from '@ant-design/icons';
import axios from 'axios';
import dayjs from 'dayjs';

const { RangePicker } = DatePicker;

const StatisticsTab = ({ serverId }) => {
    const [statistics, setStatistics] = useState(null);
    const [loading, setLoading] = useState(false);
    const [dateRange, setDateRange] = useState([dayjs().subtract(7, 'day'), dayjs()]);
    const [granularity, setGranularity] = useState('hourly');

    const fetchStatistics = async () => {
        setLoading(true);
        try {
            const params = {
                start_date: dateRange[0].format('YYYY-MM-DD'),
                end_date: dateRange[1].format('YYYY-MM-DD'),
                granularity,
            };

            if (serverId !== 'all') {
                params.server_id = serverId;
            }

            const response = await axios.get('/api/ipxe-analytics/statistics/', { params });
            setStatistics(response.data);
        } catch (error) {
            console.error('Error fetching statistics:', error);
            message.error('載入統計資料失敗：' + (error.response?.data?.message || error.message));
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchStatistics();
        
        // 自動刷新（每 10 分鐘）
        const intervalId = setInterval(() => {
            fetchStatistics();
        }, 10 * 60 * 1000);

        return () => clearInterval(intervalId);
    }, [serverId, dateRange, granularity]);

    const handleRefresh = () => {
        fetchStatistics();
    };

    if (loading && !statistics) {
        return (
            <div style={{ textAlign: 'center', padding: '50px' }}>
                <Spin size="large" tip="載入統計資料中..." />
            </div>
        );
    }

    if (!statistics) {
        return <div style={{ textAlign: 'center', padding: '50px', color: '#999' }}>暫無統計資料</div>;
    }

    const { summary, time_series, top_clients, top_files } = statistics;

    // 計算增長率
    const calculateGrowth = (current, previous) => {
        if (!previous || previous === 0) return 0;
        return (((current - previous) / previous) * 100).toFixed(1);
    };

    return (
        <div>
            {/* 篩選區域 */}
            <div style={{ marginBottom: '24px', background: '#fafafa', padding: '16px', borderRadius: '4px' }}>
                <Space wrap>
                    <RangePicker
                        value={dateRange}
                        onChange={setDateRange}
                        format="YYYY-MM-DD"
                        presets={[
                            { label: '最近 24 小時', value: [dayjs().subtract(1, 'day'), dayjs()] },
                            { label: '最近 3 天', value: [dayjs().subtract(3, 'day'), dayjs()] },
                            { label: '最近 7 天', value: [dayjs().subtract(7, 'day'), dayjs()] },
                            { label: '最近 30 天', value: [dayjs().subtract(30, 'day'), dayjs()] },
                        ]}
                    />
                    <Select
                        value={granularity}
                        onChange={setGranularity}
                        style={{ width: 150 }}
                    >
                        <Select.Option value="hourly">每小時</Select.Option>
                        <Select.Option value="daily">每日</Select.Option>
                    </Select>
                    <Button icon={<ReloadOutlined />} onClick={handleRefresh} loading={loading}>
                        重新整理
                    </Button>
                </Space>
            </div>

            {/* 總計統計卡片 */}
            <Row gutter={[16, 16]} style={{ marginBottom: '24px' }}>
                <Col xs={24} sm={12} md={6}>
                    <Card>
                        <Statistic
                            title="總請求數"
                            value={summary?.total_requests || 0}
                            valueStyle={{ color: '#2196f3' }}
                            prefix={summary?.growth_rate > 0 ? <RiseOutlined /> : <FallOutlined />}
                            suffix={summary?.growth_rate ? `${summary.growth_rate}%` : ''}
                        />
                    </Card>
                </Col>
                <Col xs={24} sm={12} md={6}>
                    <Card>
                        <Statistic
                            title="MAC 管理"
                            value={summary?.mac_requests || 0}
                            valueStyle={{ color: '#52c41a' }}
                        />
                    </Card>
                </Col>
                <Col xs={24} sm={12} md={6}>
                    <Card>
                        <Statistic
                            title="BOOT 請求"
                            value={summary?.boot_requests || 0}
                            valueStyle={{ color: '#faad14' }}
                        />
                    </Card>
                </Col>
                <Col xs={24} sm={12} md={6}>
                    <Card>
                        <Statistic
                            title="唯一 Client"
                            value={summary?.unique_clients || 0}
                            valueStyle={{ color: '#f5222d' }}
                        />
                    </Card>
                </Col>
            </Row>

            <Row gutter={[16, 16]}>
                {/* 時間序列圖 */}
                <Col xs={24}>
                    <Card title={`請求趨勢（${granularity === 'hourly' ? '每小時' : '每日'}）`}>
                        <ResponsiveContainer width="100%" height={350}>
                            <LineChart data={time_series || []}>
                                <CartesianGrid strokeDasharray="3 3" />
                                <XAxis dataKey="time" />
                                <YAxis />
                                <Tooltip />
                                <Legend />
                                <Line type="monotone" dataKey="mac_count" stroke="#2196f3" name="MAC 管理" strokeWidth={2} />
                                <Line type="monotone" dataKey="boot_count" stroke="#52c41a" name="BOOT 請求" strokeWidth={2} />
                                <Line type="monotone" dataKey="total_count" stroke="#faad14" name="總計" strokeWidth={2} strokeDasharray="5 5" />
                            </LineChart>
                        </ResponsiveContainer>
                    </Card>
                </Col>

                {/* Top Clients */}
                <Col xs={24} lg={12}>
                    <Card title="Top 10 活躍 Client">
                        <ResponsiveContainer width="100%" height={300}>
                            <BarChart data={top_clients || []}>
                                <CartesianGrid strokeDasharray="3 3" />
                                <XAxis dataKey="client_ip" angle={-45} textAnchor="end" height={100} />
                                <YAxis />
                                <Tooltip />
                                <Legend />
                                <Bar dataKey="count" fill="#2196f3" name="請求次數" />
                            </BarChart>
                        </ResponsiveContainer>
                    </Card>
                </Col>

                {/* Top Files */}
                <Col xs={24} lg={12}>
                    <Card title="Top 10 請求文件">
                        <ResponsiveContainer width="100%" height={300}>
                            <BarChart data={top_files || []} layout="vertical">
                                <CartesianGrid strokeDasharray="3 3" />
                                <XAxis type="number" />
                                <YAxis type="category" dataKey="file_path" width={150} />
                                <Tooltip />
                                <Legend />
                                <Bar dataKey="count" fill="#52c41a" name="請求次數" />
                            </BarChart>
                        </ResponsiveContainer>
                    </Card>
                </Col>
            </Row>
        </div>
    );
};

export default StatisticsTab;
