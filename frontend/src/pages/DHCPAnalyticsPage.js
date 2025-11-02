import React, { useState, useEffect } from 'react';
import { Card, Tabs, Select, Button, Space, Typography, message, Breadcrumb } from 'antd';
import {
    BarChartOutlined,
    UnorderedListOutlined,
    FileTextOutlined,
    LineChartOutlined,
    SettingOutlined,
    GlobalOutlined,
    ReloadOutlined,
    HomeOutlined,
    ApartmentOutlined,
} from '@ant-design/icons';
import { useParams, useNavigate, useSearchParams, Link } from 'react-router-dom';
import axios from 'axios';

// Tab 組件
import OverviewTab from '../components/dhcp-analytics/OverviewTab';
import LeasesTab from '../components/dhcp-analytics/LeasesTab';
import LogsTab from '../components/dhcp-analytics/LogsTab';
import StatisticsTab from '../components/dhcp-analytics/StatisticsTab';
import ConfigTab from '../components/dhcp-analytics/ConfigTab';
import SwitchTab from '../components/dhcp-analytics/SwitchTab';

const { Title } = Typography;

const DHCPAnalyticsPage = () => {
    // 從 URL 獲取參數
    const { serverId: urlServerId, tab: urlTab } = useParams();
    const [searchParams] = useSearchParams();
    const navigate = useNavigate();
    
    // 從 URL 決定當前狀態（URL 為唯一真實來源）
    const activeTab = urlTab || 'overview';
    const selectedServer = urlServerId || searchParams.get('server') || 'all';
    
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
    
    // 動態設定頁面標題
    useEffect(() => {
        const serverInfo = servers.find(s => s.id.toString() === selectedServer);
        const serverName = serverInfo ? 
            `${serverInfo.ip_address} (${serverInfo.name})` : 
            selectedServer === 'all' ? '所有 Server' : 'Server';
        
        const tabName = {
            'overview': '概覽',
            'logs': '日誌查看',
            'leases': '租約管理',
            'statistics': '統計分析',
            'switches': 'Switch 管理',
            'config': 'Server 設定',
        }[activeTab] || '概覽';
        
        document.title = `${tabName} - ${serverName} | DHCP Server 分析`;
    }, [activeTab, selectedServer, servers]);

    // Server 切換處理（保持當前 Tab）
    const handleServerChange = (serverId) => {
        console.log('切換到 Server:', serverId);
        
        if (serverId === 'all') {
            // 切換到彙總視圖
            navigate(`/dhcp-analytics/${activeTab}`);
        } else {
            // 切換到特定 Server
            navigate(`/dhcp-analytics/server/${serverId}/${activeTab}`);
        }
    };

    // Tab 切換處理（保持當前 Server）
    const handleTabChange = (key) => {
        if (selectedServer === 'all') {
            // 彙總視圖
            navigate(`/dhcp-analytics/${key}`);
        } else {
            // 特定 Server
            navigate(`/dhcp-analytics/server/${selectedServer}/${key}`);
        }
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
            key: 'switches',
            label: <span><ApartmentOutlined /> Switch 管理</span>,
            children: <SwitchTab serverId={selectedServer} />,
        },
        {
            key: 'config',
            label: <span><SettingOutlined /> Server 設定</span>,
            children: <ConfigTab serverId={selectedServer} />,
        },
    ];
    
    // 生成麵包屑
    const renderBreadcrumb = () => {
        const serverInfo = servers.find(s => s.id.toString() === selectedServer);
        const serverName = serverInfo ? 
            `${serverInfo.ip_address} (${serverInfo.name})` : 
            '所有 Server';
        
        const tabName = {
            'overview': '概覽',
            'logs': '日誌查看',
            'leases': '租約管理',
            'statistics': '統計分析',
            'switches': 'Switch 管理',
            'config': 'Server 設定',
        }[activeTab] || '概覽';
        
        return (
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
                <Breadcrumb>
                    <Breadcrumb.Item>
                        <Link to="/dashboard">
                            <HomeOutlined /> Home
                        </Link>
                    </Breadcrumb.Item>
                    <Breadcrumb.Item>
                        <Link to="/dhcp-analytics/overview">
                            <GlobalOutlined /> DHCP Server 分析
                        </Link>
                    </Breadcrumb.Item>
                    {selectedServer !== 'all' && serverInfo ? (
                        <Breadcrumb.Item>
                            <Link to={`/dhcp-analytics/server/${selectedServer}/overview`}>
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

export default DHCPAnalyticsPage;
