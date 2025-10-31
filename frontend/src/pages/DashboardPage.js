import React, { useState, useEffect } from 'react';
import { Card, Row, Col, Statistic, Button, Alert, Table, Tag, Space, Progress, message } from 'antd';
import {
    DatabaseOutlined,
    CheckCircleOutlined,
    WarningOutlined,
    ReloadOutlined,
    ArrowUpOutlined,
    ArrowDownOutlined,
    CloseCircleOutlined,
} from '@ant-design/icons';
import axios from 'axios';
import './DashboardPage.css';

const DashboardPage = () => {
    const [loading, setLoading] = useState(false);
    const [dashboardData, setDashboardData] = useState({
        totalServers: 0,
        onlineServers: 0,
        warningServers: 0,
        offlineServers: 0,
        totalLeases: 0,
        activeLeases: 0,
        avgPoolUsage: 0,
    });
    const [dhcpServers, setDhcpServers] = useState([]);
    const [recentAlerts, setRecentAlerts] = useState([]);

    // 獲取 Dashboard 統計數據
    const fetchDashboardStats = async () => {
        try {
            const response = await axios.get('/api/dashboard/stats/');
            setDashboardData({
                totalServers: response.data.total_servers,
                onlineServers: response.data.online_servers,
                warningServers: response.data.warning_servers,
                offlineServers: response.data.offline_servers,
                totalLeases: response.data.total_leases,
                activeLeases: response.data.active_leases,
                avgPoolUsage: response.data.avg_pool_usage,
            });
        } catch (error) {
            console.error('獲取 Dashboard 統計失敗:', error);
            message.error('載入統計數據失敗：' + (error.response?.data?.error || error.message));
        }
    };

    // 獲取 DHCP Server 列表
    const fetchDHCPServers = async () => {
        try {
            const response = await axios.get('/api/dhcp-servers/');
            // API 返回的是分頁格式，需要取 results
            const servers = response.data.results || response.data;
            setDhcpServers(servers);
            
            // 根據服務器狀態生成告警
            generateAlerts(servers);
        } catch (error) {
            console.error('獲取 DHCP Server 列表失敗:', error);
            message.error('載入服務器列表失敗：' + (error.response?.data?.error || error.message));
        }
    };

    // 生成系統告警
    const generateAlerts = (servers) => {
        const alerts = [];
        
        servers.forEach(server => {
            // 高使用率警告
            if (server.pool_usage > 80) {
                alerts.push({
                    id: `warning-${server.id}`,
                    type: 'warning',
                    message: `${server.name} IP 池使用率達到 ${server.pool_usage.toFixed(1)}%`,
                    time: '即時',
                });
            }
            
            // 離線警告
            if (server.status === 'offline') {
                alerts.push({
                    id: `offline-${server.id}`,
                    type: 'error',
                    message: `${server.name} 伺服器離線`,
                    time: '即時',
                });
            }
        });
        
        // 如果沒有告警，顯示成功訊息
        if (alerts.length === 0 && servers.length > 0) {
            alerts.push({
                id: 'success-1',
                type: 'success',
                message: `所有 ${servers.length} 台 DHCP 伺服器運行正常`,
                time: '即時',
            });
        }
        
        setRecentAlerts(alerts);
    };

    // 載入所有數據
    const loadAllData = async () => {
        setLoading(true);
        try {
            await Promise.all([
                fetchDashboardStats(),
                fetchDHCPServers(),
            ]);
        } finally {
            setLoading(false);
        }
    };

    // 重新整理數據
    const refreshData = () => {
        loadAllData();
    };

    // 初始載入
    useEffect(() => {
        loadAllData();
    }, []);

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
                    <span style={{ color: '#757575', fontSize: '12px' }}>
                        {record.hostname || record.ip_address}
                    </span>
                </div>
            ),
        },
        {
            title: 'IP 地址',
            dataIndex: 'ip_address',
            key: 'ip_address',
        },
        {
            title: '狀態',
            dataIndex: 'status',
            key: 'status',
            render: (status) => {
                const statusConfig = {
                    online: { color: 'success', text: '運行中', icon: <CheckCircleOutlined /> },
                    warning: { color: 'warning', text: '警告', icon: <WarningOutlined /> },
                    offline: { color: 'error', text: '離線', icon: <CloseCircleOutlined /> },
                };
                const config = statusConfig[status] || statusConfig.online;
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
                const poolUsage = record.pool_usage || 0;
                const progressStatus = poolUsage > 80 ? 'exception' : poolUsage > 60 ? 'normal' : 'success';
                
                return (
                    <div>
                        <Progress
                            percent={poolUsage}
                            size="small"
                            status={progressStatus}
                            format={(percent) => `${percent.toFixed(1)}%`}
                        />
                        <div style={{ fontSize: '12px', color: '#757575', marginTop: '4px' }}>
                            總租約: {record.total_leases || 0} 個
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
                    <Button type="link" size="small" href={`/dhcp-servers/${record.id}`}>
                        查看詳情
                    </Button>
                    <Button type="link" size="small" href={`/dhcp-analytics?server=${record.id}`}>
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
                            {dashboardData.onlineServers === dashboardData.totalServers ? (
                                <>
                                    <CheckCircleOutlined style={{ color: '#52c41a' }} /> 全部運行中
                                </>
                            ) : (
                                <>
                                    <WarningOutlined style={{ color: '#ff9800' }} /> {dashboardData.onlineServers} 台運行中
                                </>
                            )}
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
                            <CheckCircleOutlined style={{ color: '#52c41a' }} /> {dashboardData.activeLeases} 個活躍
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
                            {dashboardData.activeLeases > 0 ? (
                                <>
                                    <CheckCircleOutlined style={{ color: '#52c41a' }} /> 正常運作中
                                </>
                            ) : (
                                <>
                                    <WarningOutlined style={{ color: '#ff9800' }} /> 無活躍租約
                                </>
                            )}
                        </div>
                    </Card>
                </Col>
                <Col xs={24} sm={12} lg={6}>
                    <Card>
                        <Statistic
                            title="IP池使用率"
                            value={dashboardData.avgPoolUsage}
                            valueStyle={{ 
                                color: dashboardData.avgPoolUsage > 80 ? '#f44336' : 
                                       dashboardData.avgPoolUsage > 60 ? '#ff9800' : '#52c41a'
                            }}
                            suffix="%"
                        />
                        <div className="stat-footer">
                            {dashboardData.avgPoolUsage > 80 ? (
                                <>
                                    <WarningOutlined style={{ color: '#f44336' }} /> 使用率偏高
                                </>
                            ) : dashboardData.avgPoolUsage > 60 ? (
                                <>
                                    <WarningOutlined style={{ color: '#ff9800' }} /> 使用率中等
                                </>
                            ) : (
                                <>
                                    <CheckCircleOutlined style={{ color: '#52c41a' }} /> 使用率正常
                                </>
                            )}
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
