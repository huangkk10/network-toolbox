import React, { useState, useEffect } from 'react';
import { Card, Row, Col, Statistic, Button, Alert, Table, Tag, Space, Progress, message, List, Avatar } from 'antd';
import {
    DatabaseOutlined,
    CheckCircleOutlined,
    WarningOutlined,
    ReloadOutlined,
    CloseCircleOutlined,
    CloudUploadOutlined,
    CloudDownloadOutlined,
    UserOutlined,
    ApiOutlined,
    TeamOutlined,
    GlobalOutlined,
} from '@ant-design/icons';
import axios from 'axios';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, BarChart, Bar } from 'recharts';
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
    const [nasSpeedTrend, setNasSpeedTrend] = useState([]);
    const [nasStats, setNasStats] = useState({
        avgUploadSpeed: 0,
        avgDownloadSpeed: 0,
        successRate: 0,
    });
    // ✨ 網站使用統計狀態
    const [websiteUsage, setWebsiteUsage] = useState({
        today: {
            total_page_views: 0,
            unique_visitors: 0,
            total_api_requests: 0,
            error_count: 0,
        },
        trend: [],
        page_distribution: {},
        feature_usage: {},
        top_pages: {},
        top_api_endpoints: {},
    });

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
            
            // ✨ 設置網站使用統計數據
            if (response.data.website_usage) {
                setWebsiteUsage(response.data.website_usage);
            }
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

    // 獲取 NAS 速度趨勢數據
    const fetchNASSpeedTrend = async () => {
        try {
            const response = await axios.get('/api/nas-logs/statistics/?days=1');
            
            // 過濾掉 null 值的數據點
            const validTrends = response.data.speed_trends.filter(
                item => item.upload_speed !== null && item.download_speed !== null
            );
            
            setNasSpeedTrend(validTrends);
            setNasStats({
                avgUploadSpeed: response.data.avg_upload_speed,
                avgDownloadSpeed: response.data.avg_download_speed,
                successRate: response.data.success_rate,
            });
        } catch (error) {
            console.error('獲取 NAS 速度趨勢失敗:', error);
            // 不顯示錯誤訊息，避免干擾用戶
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
                fetchNASSpeedTrend(),
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
        // eslint-disable-next-line react-hooks/exhaustive-deps
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

            {/* ✨ 網站使用統計 */}
            <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
                {/* 今日頁面瀏覽 */}
                <Col xs={24} sm={8} md={6}>
                    <Card>
                        <Statistic
                            title="今日頁面瀏覽"
                            value={websiteUsage.today.total_page_views}
                            prefix={<GlobalOutlined />}
                            valueStyle={{ color: '#2196f3' }}
                            suffix="次"
                        />
                        <div className="stat-footer">
                            <UserOutlined style={{ color: '#2196f3' }} /> {websiteUsage.today.unique_visitors} 位訪客
                        </div>
                    </Card>
                </Col>

                {/* 今日API請求 */}
                <Col xs={24} sm={8} md={6}>
                    <Card>
                        <Statistic
                            title="今日 API 請求"
                            value={websiteUsage.today.total_api_requests}
                            prefix={<ApiOutlined />}
                            valueStyle={{ color: '#673ab7' }}
                            suffix="次"
                        />
                        <div className="stat-footer">
                            <CheckCircleOutlined style={{ color: '#52c41a' }} /> 服務正常
                        </div>
                    </Card>
                </Col>

                {/* 唯一訪客數 */}
                <Col xs={24} sm={8} md={6}>
                    <Card>
                        <Statistic
                            title="唯一訪客數"
                            value={websiteUsage.today.unique_visitors}
                            prefix={<TeamOutlined />}
                            valueStyle={{ color: '#ff9800' }}
                            suffix="人"
                        />
                        <div className="stat-footer">
                            <TeamOutlined style={{ color: '#ff9800' }} /> 今日訪客
                        </div>
                    </Card>
                </Col>

                {/* 錯誤次數 */}
                <Col xs={24} sm={8} md={6}>
                    <Card>
                        <Statistic
                            title="今日錯誤"
                            value={websiteUsage.today.error_count}
                            prefix={<WarningOutlined />}
                            valueStyle={{ 
                                color: websiteUsage.today.error_count > 50 ? '#f44336' : 
                                       websiteUsage.today.error_count > 20 ? '#ff9800' : '#52c41a'
                            }}
                            suffix="次"
                        />
                        <div className="stat-footer">
                            {websiteUsage.today.error_count > 50 ? (
                                <WarningOutlined style={{ color: '#f44336' }} />
                            ) : (
                                <CheckCircleOutlined style={{ color: '#52c41a' }} />
                            )} 系統狀態
                        </div>
                    </Card>
                </Col>
            </Row>

            {/* 過去7天使用人數趨勢 */}
            {websiteUsage.trend && websiteUsage.trend.length > 0 && (
                <Card
                    title="📈 過去 7 天使用人數趨勢"
                    style={{ marginTop: 16 }}
                >
                    <ResponsiveContainer width="100%" height={300}>
                        <LineChart data={websiteUsage.trend}>
                            <CartesianGrid strokeDasharray="3 3" />
                            <XAxis
                                dataKey="date"
                                tick={{ fontSize: 12 }}
                            />
                            <YAxis
                                tick={{ fontSize: 12 }}
                                label={{ value: '使用人數', angle: -90, position: 'insideLeft' }}
                            />
                            <Tooltip
                                contentStyle={{ backgroundColor: '#fff', border: '1px solid #ccc' }}
                                formatter={(value) => [`${value} 人`, '唯一訪客']}
                            />
                            <Legend />
                            <Line
                                type="monotone"
                                dataKey="unique_visitors"
                                stroke="#2196f3"
                                strokeWidth={3}
                                dot={{ fill: '#2196f3', r: 5 }}
                                activeDot={{ r: 7 }}
                                name="每日使用人數"
                            />
                        </LineChart>
                    </ResponsiveContainer>
                </Card>
            )}

            {/* 功能使用統計 */}
            {websiteUsage.feature_usage && Object.keys(websiteUsage.feature_usage).length > 0 && (
                <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
                    <Col xs={24} sm={12} md={6}>
                        <Card>
                            <Statistic
                                title="DHCP 同步"
                                value={websiteUsage.feature_usage.dhcp_sync || 0}
                                prefix={<DatabaseOutlined />}
                                valueStyle={{ color: '#2196f3' }}
                                suffix="次"
                            />
                        </Card>
                    </Col>
                    <Col xs={24} sm={12} md={6}>
                        <Card>
                            <Statistic
                                title="iPXE 操作"
                                value={websiteUsage.feature_usage.ipxe_operations || 0}
                                prefix={<CloudUploadOutlined />}
                                valueStyle={{ color: '#673ab7' }}
                                suffix="次"
                            />
                        </Card>
                    </Col>
                    <Col xs={24} sm={12} md={6}>
                        <Card>
                            <Statistic
                                title="Jenkins Build"
                                value={websiteUsage.feature_usage.jenkins_builds || 0}
                                prefix={<CheckCircleOutlined />}
                                valueStyle={{ color: '#ff9800' }}
                                suffix="次"
                            />
                        </Card>
                    </Col>
                    <Col xs={24} sm={12} md={6}>
                        <Card>
                            <Statistic
                                title="Ansible 執行"
                                value={websiteUsage.feature_usage.ansible_executions || 0}
                                prefix={<ApiOutlined />}
                                valueStyle={{ color: '#52c41a' }}
                                suffix="次"
                            />
                        </Card>
                    </Col>
                </Row>
            )}

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

            {/* NAS 傳輸速度趨勢 */}
            <Card 
                title="NAS 傳輸速度趨勢（最近 24 小時）" 
                extra={
                    <Space>
                        <Statistic
                            title="平均上傳"
                            value={nasStats.avgUploadSpeed}
                            suffix="MB/s"
                            valueStyle={{ fontSize: '14px', color: '#2196f3' }}
                            prefix={<CloudUploadOutlined />}
                        />
                        <Statistic
                            title="平均下載"
                            value={nasStats.avgDownloadSpeed}
                            suffix="MB/s"
                            valueStyle={{ fontSize: '14px', color: '#52c41a' }}
                            prefix={<CloudDownloadOutlined />}
                        />
                    </Space>
                }
                style={{ marginTop: 16 }}
            >
                {nasSpeedTrend.length > 0 ? (
                    <ResponsiveContainer width="100%" height={300}>
                        <LineChart data={nasSpeedTrend} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
                            <CartesianGrid strokeDasharray="3 3" />
                            <XAxis 
                                dataKey="time" 
                                tick={{ fontSize: 12 }}
                                angle={-45}
                                textAnchor="end"
                                height={80}
                            />
                            <YAxis 
                                label={{ value: '速度 (MB/s)', angle: -90, position: 'insideLeft' }}
                                tick={{ fontSize: 12 }}
                            />
                            <Tooltip 
                                formatter={(value) => `${value} MB/s`}
                                labelStyle={{ color: '#000' }}
                            />
                            <Legend />
                            <Line 
                                type="monotone" 
                                dataKey="upload_speed" 
                                stroke="#2196f3" 
                                name="上傳速度"
                                strokeWidth={2}
                                dot={{ r: 2 }}
                                activeDot={{ r: 5 }}
                            />
                            <Line 
                                type="monotone" 
                                dataKey="download_speed" 
                                stroke="#52c41a" 
                                name="下載速度"
                                strokeWidth={2}
                                dot={{ r: 2 }}
                                activeDot={{ r: 5 }}
                            />
                        </LineChart>
                    </ResponsiveContainer>
                ) : (
                    <div style={{ textAlign: 'center', padding: '40px', color: '#757575' }}>
                        <CloudDownloadOutlined style={{ fontSize: '48px', marginBottom: '16px' }} />
                        <p>暫無 NAS 速度數據</p>
                    </div>
                )}
            </Card>

            {/* 系統通知與警告 */}
            <Card title="系統通知與警告" extra={<Button type="link">查看全部 →</Button>} style={{ marginTop: 16 }}>
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
