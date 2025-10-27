import React, { useState, useEffect } from 'react';
import { Card, Tabs, Select, Button, Space, Typography, message } from 'antd';
import {
    BarChartOutlined,
    UnorderedListOutlined,
    FileTextOutlined,
    LineChartOutlined,
    SettingOutlined,
    GlobalOutlined,
    ReloadOutlined,
} from '@ant-design/icons';
import axios from 'axios';

// Tab 組件
import OverviewTab from '../components/dhcp-analytics/OverviewTab';
import LeasesTab from '../components/dhcp-analytics/LeasesTab';
import LogsTab from '../components/dhcp-analytics/LogsTab';
import StatisticsTab from '../components/dhcp-analytics/StatisticsTab';
import ConfigTab from '../components/dhcp-analytics/ConfigTab';

const { Title } = Typography;

const DHCPAnalyticsPage = () => {
    const [selectedServer, setSelectedServer] = useState('all');
    const [activeTab, setActiveTab] = useState('overview');
    const [loading, setLoading] = useState(false);
    const [servers, setServers] = useState([]);
    const [loadingServers, setLoadingServers] = useState(false);

    // 載入 DHCP Server 列表
    const fetchServers = async () => {
        setLoadingServers(true);
        try {
            const response = await axios.get('/api/dhcp-servers/');
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
                    'warning': '🟡',
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
            key: 'leases',
            label: <span><UnorderedListOutlined /> 租約管理</span>,
            children: <LeasesTab serverId={selectedServer} />,
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
            key: 'config',
            label: <span><SettingOutlined /> Server 設定</span>,
            children: <ConfigTab serverId={selectedServer} />,
        },
    ];

    return (
        <div style={{ padding: '24px', background: '#f5f5f5' }}>
            <div style={{ marginBottom: '24px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <Title level={3} style={{ margin: 0 }}>
                    <GlobalOutlined /> DHCP Server 分析
                </Title>
                <Space>
                    <Select
                        style={{ width: 250 }}
                        value={selectedServer}
                        onChange={handleServerChange}
                        placeholder="選擇 DHCP Server"
                        loading={loadingServers}
                        options={getServerOptions()}
                    />
                    <Button icon={<ReloadOutlined />} onClick={handleRefresh} loading={loading}>
                        重新整理
                    </Button>
                </Space>
            </div>
            <Card>
                <Tabs activeKey={activeTab} onChange={handleTabChange} items={tabItems} size="large" />
            </Card>
        </div>
    );
};

export default DHCPAnalyticsPage;
