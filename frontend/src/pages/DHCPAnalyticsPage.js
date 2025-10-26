import React, { useState } from 'react';
import { Card, Tabs, Select, Button, Space, Typography } from 'antd';
import {
    BarChartOutlined,
    UnorderedListOutlined,
    FileTextOutlined,
    LineChartOutlined,
    SettingOutlined,
    GlobalOutlined,
    ReloadOutlined,
} from '@ant-design/icons';

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

    const handleServerChange = (serverId) => {
        setSelectedServer(serverId);
        console.log('切換到 Server:', serverId);
    };

    const handleTabChange = (key) => {
        setActiveTab(key);
    };

    const handleRefresh = () => {
        setLoading(true);
        setTimeout(() => {
            setLoading(false);
        }, 1000);
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
                        options={[
                            { value: 'all', label: '�� 所有 Server（彙總）' },
                            {
                                label: '可用 Server',
                                options: [
                                    { value: '1', label: '🟢 192.168.1.1 (Main)' },
                                    { value: '2', label: '🟢 192.168.2.1 (Branch 1)' },
                                    { value: '3', label: '🟡 10.0.1.1 (Branch 2)' },
                                    { value: '4', label: '🔴 172.16.0.1 (Backup - 離線)' },
                                ],
                            },
                        ]}
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
