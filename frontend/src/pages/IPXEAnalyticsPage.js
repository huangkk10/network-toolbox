import React, { useState, useEffect } from 'react';
import { Card, Tabs, Select, Button, Space, Typography, message, Breadcrumb } from 'antd';
import {
    BarChartOutlined,
    FileTextOutlined,
    LineChartOutlined,
    CloudServerOutlined,
    ReloadOutlined,
    GlobalOutlined,
    HomeOutlined,
} from '@ant-design/icons';
import axios from 'axios';
import { Link } from 'react-router-dom';

// Tab 組件
import OverviewTab from '../components/ipxe-analytics/OverviewTab';
import LogsTab from '../components/ipxe-analytics/LogsTab';
import StatisticsTab from '../components/ipxe-analytics/StatisticsTab';
import NetworkQualityTab from '../components/ipxe-analytics/NetworkQualityTab';

const { Title } = Typography;

const IPXEAnalyticsPage = () => {
    const [selectedServer, setSelectedServer] = useState('all');
    const [activeTab, setActiveTab] = useState('overview');
    const [loading, setLoading] = useState(false);
    const [servers, setServers] = useState([]);
    const [loadingServers, setLoadingServers] = useState(false);

    // 載入 IPXE Server 列表
    const fetchServers = async () => {
        setLoadingServers(true);
        try {
            const response = await axios.get('/api/ipxe-servers/');
            const data = response.data.results || response.data;
            setServers(Array.isArray(data) ? data : []);
        } catch (error) {
            console.error('Error fetching servers:', error);
            message.error('載入伺服器列表失敗：' + (error.response?.data?.message || error.message));
        } finally {
            setLoadingServers(false);
        }
    };

    useEffect(() => {
        fetchServers();
        
        // 設置自動刷新（每 10 分鐘）
        const intervalId = setInterval(() => {
            console.log('自動刷新 IPXE 資料...');
            fetchServers();
        }, 10 * 60 * 1000); // 10 分鐘

        return () => clearInterval(intervalId);
    }, []);

    const handleServerChange = (serverId) => {
        setSelectedServer(serverId);
        console.log('切換到 Server:', serverId);
    };

    const handleTabChange = (key) => {
        setActiveTab(key);
    };

    const handleRefresh = () => {
        setLoading(true);
        fetchServers();
        setTimeout(() => {
            setLoading(false);
            message.success('資料已更新');
        }, 1000);
    };

    // 生成 Server 選項
    const getServerOptions = () => {
        const options = [
            { value: 'all', label: '◈ 所有 Server（彙總）' }
        ];

        if (servers.length > 0) {
            const serverOptions = servers.map(server => {
                // 根據狀態設定圖示
                const statusIcon = {
                    'online': '🟢',
                    'offline': '🔴',
                    'syncing': '🔄',
                }[server.status] || '⚪';

                return {
                    value: server.id.toString(),
                    label: `${statusIcon} ${server.ip_address} (${server.name})`,
                };
            });

            options.push({
                label: '可用 Server',
                options: serverOptions,
            });
        }

        return options;
    };

    const tabItems = [
        {
            key: 'overview',
            label: <span><BarChartOutlined /> 概覽</span>,
            children: <OverviewTab serverId={selectedServer} />,
        },
        {
            key: 'logs',
            label: <span><FileTextOutlined /> 日誌查看</span>,
            children: <LogsTab serverId={selectedServer} />,
        },
        {
            key: 'statistics',
            label: <span><LineChartOutlined /> 統計分析</span>,
            children: <StatisticsTab serverId={selectedServer} />,
        },
        {
            key: 'network-quality',
            label: <span><GlobalOutlined /> 網路品質</span>,
            children: <NetworkQualityTab serverId={selectedServer} />,
        },
    ];

    // 獲取當前選擇的伺服器資訊
    const serverInfo = servers.find(s => s.id.toString() === selectedServer);
    const serverName = selectedServer === 'all' 
        ? '所有 Server（彙整）' 
        : serverInfo 
            ? `${serverInfo.name} (${serverInfo.ip_address})`
            : '載入中...';

    // Tab 對應的中文名稱
    const tabNameMap = {
        'overview': '概覽',
        'logs': '日誌查看',
        'statistics': '統計分析',
        'network-quality': '網路品質',
    };
    const tabName = tabNameMap[activeTab] || activeTab;

    // 渲染麵包屑導航
    const renderBreadcrumb = () => {
        return (
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
                <Breadcrumb>
                    <Breadcrumb.Item>
                        <Link to="/dashboard">
                            <HomeOutlined /> Home
                        </Link>
                    </Breadcrumb.Item>
                    <Breadcrumb.Item>
                        <Link to="/ipxe-analytics/overview">
                            <GlobalOutlined /> iPXE 分析
                        </Link>
                    </Breadcrumb.Item>
                    {selectedServer !== 'all' && serverInfo ? (
                        <Breadcrumb.Item>
                            <Link to={`/ipxe-analytics/server/${selectedServer}/overview`}>
                                {serverName}
                            </Link>
                        </Breadcrumb.Item>
                    ) : (
                        <Breadcrumb.Item>{serverName}</Breadcrumb.Item>
                    )}
                    <Breadcrumb.Item>{tabName}</Breadcrumb.Item>
                </Breadcrumb>
                
                <Space>
                    <Select
                        style={{ width: 280 }}
                        value={selectedServer}
                        onChange={handleServerChange}
                        placeholder="選擇 IPXE Server"
                        loading={loadingServers}
                        options={getServerOptions()}
                    />
                    <Button icon={<ReloadOutlined />} onClick={handleRefresh} loading={loading}>
                        重新整理
                    </Button>
                </Space>
            </div>
        );
    };

    return (
        <div style={{ padding: '24px', background: '#f5f5f5' }}>
            {/* 麵包屑導航與操作按鈕 */}
            {renderBreadcrumb()}
            
            <Card>
                <Tabs activeKey={activeTab} onChange={handleTabChange} items={tabItems} size="large" />
            </Card>
        </div>
    );
};

export default IPXEAnalyticsPage;
