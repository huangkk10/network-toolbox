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
import { useParams, useNavigate, useSearchParams, Link } from 'react-router-dom';
import axios from 'axios';

// Tab 組件
import OverviewTab from '../components/ipxe-analytics/OverviewTab';
import LogsTab from '../components/ipxe-analytics/LogsTab';
import StatisticsTab from '../components/ipxe-analytics/StatisticsTab';
import NetworkQualityTab from '../components/ipxe-analytics/NetworkQualityTab';

const { Title } = Typography;

const IPXEAnalyticsPage = () => {
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
    
    // 動態設定頁面標題
    useEffect(() => {
        const serverInfo = servers.find(s => s.id.toString() === selectedServer);
        const serverName = serverInfo ? 
            `${serverInfo.ip_address} (${serverInfo.name})` : 
            selectedServer === 'all' ? '所有 Server' : 'Server';
        
        const tabName = {
            'overview': '概覽',
            'logs': '日誌查看',
            'statistics': '統計分析',
            'network-quality': '網路品質',
        }[activeTab] || '概覽';
        
        document.title = `${tabName} - ${serverName} | iPXE 分析`;
    }, [activeTab, selectedServer, servers]);

    // Server 切換處理（保持當前 Tab）
    const handleServerChange = (serverId) => {
        console.log('切換到 Server:', serverId);
        
        if (serverId === 'all') {
            // 切換到彙總視圖
            navigate(`/ipxe-analytics/${activeTab}`);
        } else {
            // 切換到特定 Server
            navigate(`/ipxe-analytics/server/${serverId}/${activeTab}`);
        }
    };

    // Tab 切換處理（保持當前 Server）
    const handleTabChange = (key) => {
        if (selectedServer === 'all') {
            // 彙總視圖
            navigate(`/ipxe-analytics/${key}`);
        } else {
            // 特定 Server
            navigate(`/ipxe-analytics/server/${selectedServer}/${key}`);
        }
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
            // 排序 Server：按 IP 地址排序
            const sortedServers = [...servers].sort((a, b) => {
                // 將 IP 地址轉換為數字陣列進行比較
                const ipA = a.ip_address.split('.').map(Number);
                const ipB = b.ip_address.split('.').map(Number);
                
                for (let i = 0; i < 4; i++) {
                    if (ipA[i] !== ipB[i]) {
                        return ipA[i] - ipB[i];
                    }
                }
                return 0;
            });

            const serverOptions = sortedServers.map(server => {
                // 根據狀態設定圖示
                const statusIcon = {
                    'online': '🟢',
                    'offline': '🔴',
                    'syncing': '🔄',
                }[server.status] || '⚪';

                return {
                    value: server.id.toString(),
                    label: `${statusIcon} ${server.ip_address} (${server.name})`,
                    server: server, // 保留原始資料供搜尋使用
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
                        showSearch
                        style={{ width: 300 }}
                        value={selectedServer}
                        onChange={handleServerChange}
                        placeholder="選擇 IPXE Server"
                        loading={loadingServers}
                        options={getServerOptions()}
                        filterOption={(input, option) => {
                            // 支援搜尋 IP 和名稱
                            if (!option || !option.label) return false;
                            const searchText = input.toLowerCase();
                            const labelText = option.label.toLowerCase();
                            return labelText.includes(searchText);
                        }}
                        optionFilterProp="label"
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
