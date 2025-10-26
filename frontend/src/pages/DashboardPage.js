import React, { useState, useEffect } from 'react';
import { Card, Row, Col, Statistic, Button, Alert, Table, Tag, Space, Progress } from 'antd';
import {
    DatabaseOutlined,
    CheckCircleOutlined,
    WarningOutlined,
    ReloadOutlined,
    ArrowUpOutlined,
    ArrowDownOutlined,
} from '@ant-design/icons';
import './DashboardPage.css';

const DashboardPage = () => {
    const [loading, setLoading] = useState(false);
    const [dashboardData, setDashboardData] = useState({
        totalServers: 3,
        totalLeases: 456,
        activeLeases: 398,
        expiredLeases: 58,
        avgPoolUsage: 72,
    });

    // 模擬 DHCP Server 數據
    const dhcpServers = [
        {
            id: 1,
            name: 'Server-1',
            ip: '10.0.1.1',
            hostname: 'dhcp-server-01.local',
            status: 'running',
            leases: 150,
            maxLeases: 200,
            activeLeases: 142,
        },
        {
            id: 2,
            name: 'Server-2',
            ip: '10.0.2.1',
            hostname: 'dhcp-server-02.local',
            status: 'running',
            leases: 180,
            maxLeases: 250,
            activeLeases: 165,
        },
        {
            id: 3,
            name: 'Server-3',
            ip: '192.168.1.1',
            hostname: 'dhcp-server-03.local',
            status: 'warning',
            leases: 126,
            maxLeases: 150,
            activeLeases: 91,
        },
    ];

    // 最近告警
    const recentAlerts = [
        {
            id: 1,
            type: 'warning',
            message: 'Server-3 IP 池使用率達到 84%',
            time: '2分鐘前',
        },
        {
            id: 2,
            type: 'info',
            message: 'Server-1 新增 12 個租約',
            time: '10分鐘前',
        },
        {
            id: 3,
            type: 'success',
            message: '定時同步完成：3 台服務器',
            time: '30分鐘前',
        },
    ];

    const refreshData = () => {
        setLoading(true);
        setTimeout(() => {
            setLoading(false);
        }, 1000);
    };

    // DHCP Server 表格列定義
    const columns = [
        {
            title: '服務器名稱',
            dataIndex: 'name',
            key: 'name',
            render: (text, record) => (
                <div>
                    <strong>{text}</strong>
                    <br />
                    <span style={{ color: '#757575', fontSize: '12px' }}>{record.hostname}</span>
                </div>
            ),
        },
        {
            title: 'IP 地址',
            dataIndex: 'ip',
            key: 'ip',
        },
        {
            title: '狀態',
            dataIndex: 'status',
            key: 'status',
            render: (status) => {
                const statusConfig = {
                    running: { color: 'success', text: '運行中', icon: <CheckCircleOutlined /> },
                    warning: { color: 'warning', text: '警告', icon: <WarningOutlined /> },
                    error: { color: 'error', text: '錯誤', icon: <WarningOutlined /> },
                };
                const config = statusConfig[status] || statusConfig.running;
                return (
                    <Tag color={config.color} icon={config.icon}>
                        {config.text}
                    </Tag>
                );
            },
        },
        {
            title: '租約使用情況',
            key: 'usage',
            render: (_, record) => {
                const percentage = Math.round((record.leases / record.maxLeases) * 100);
                const status = percentage > 80 ? 'exception' : percentage > 60 ? 'normal' : 'success';
                return (
                    <div>
                        <Progress
                            percent={percentage}
                            size="small"
                            status={status}
                            format={() => `${record.leases}/${record.maxLeases}`}
                        />
                        <div style={{ fontSize: '12px', color: '#757575', marginTop: '4px' }}>
                            活躍: {record.activeLeases} 個
                        </div>
                    </div>
                );
            },
        },
        {
            title: '操作',
            key: 'actions',
            render: (_, record) => (
                <Space size="small">
                    <Button type="link" size="small">
                        查看詳情
                    </Button>
                    <Button type="link" size="small">
                        管理租約
                    </Button>
                </Space>
            ),
        },
    ];

    return (
        <div className="dashboard-page">
            {/* 頁面標題和操作 */}
            <div className="page-header">
                <h2>系統概覽</h2>
                <Button
                    icon={<ReloadOutlined />}
                    onClick={refreshData}
                    loading={loading}
                >
                    重新載入
                </Button>
            </div>

            {/* 統計卡片 */}
            <Row gutter={[16, 16]}>
                <Col xs={24} sm={12} lg={6}>
                    <Card>
                        <Statistic
                            title="DHCP 服務器"
                            value={dashboardData.totalServers}
                            prefix={<DatabaseOutlined />}
                            valueStyle={{ color: '#2196f3' }}
                            suffix="台"
                        />
                        <div className="stat-footer">
                            <CheckCircleOutlined style={{ color: '#52c41a' }} /> 全部運行中
                        </div>
                    </Card>
                </Col>
                <Col xs={24} sm={12} lg={6}>
                    <Card>
                        <Statistic
                            title="總租約數"
                            value={dashboardData.totalLeases}
                            valueStyle={{ color: '#37474f' }}
                        />
                        <div className="stat-footer">
                            <ArrowUpOutlined style={{ color: '#52c41a' }} /> +12 今日
                        </div>
                    </Card>
                </Col>
                <Col xs={24} sm={12} lg={6}>
                    <Card>
                        <Statistic
                            title="活躍租約"
                            value={dashboardData.activeLeases}
                            valueStyle={{ color: '#52c41a' }}
                        />
                        <div className="stat-footer">
                            <CheckCircleOutlined style={{ color: '#52c41a' }} /> 正常
                        </div>
                    </Card>
                </Col>
                <Col xs={24} sm={12} lg={6}>
                    <Card>
                        <Statistic
                            title="IP池使用率"
                            value={dashboardData.avgPoolUsage}
                            valueStyle={{ color: '#ff9800' }}
                            suffix="%"
                        />
                        <div className="stat-footer">
                            <WarningOutlined style={{ color: '#ff9800' }} /> 中等
                        </div>
                    </Card>
                </Col>
            </Row>

            {/* DHCP Server 狀態一覽 */}
            <Card
                title="DHCP Server 狀態一覽"
                extra={<Button type="link">查看詳細分析 →</Button>}
                style={{ marginTop: 16 }}
            >
                <Table
                    columns={columns}
                    dataSource={dhcpServers}
                    rowKey="id"
                    pagination={false}
                    loading={loading}
                />
            </Card>

            {/* 系統通知與告警 */}
            <Card title="系統通知與告警" extra={<Button type="link">查看全部 →</Button>} style={{ marginTop: 16 }}>
                <Space direction="vertical" style={{ width: '100%' }} size="middle">
                    {recentAlerts.map((alert) => (
                        <Alert
                            key={alert.id}
                            message={alert.message}
                            description={alert.time}
                            type={alert.type}
                            showIcon
                            closable
                        />
                    ))}
                </Space>
            </Card>
        </div>
    );
};

export default DashboardPage;
