import React, { useState } from 'react';
import './App.css';
import { BrowserRouter as Router, Routes, Route, Navigate, useLocation, useNavigate } from 'react-router-dom';
import { Layout, Tabs } from 'antd';
import { BarChartOutlined, FolderOutlined, FileTextOutlined } from '@ant-design/icons';
import Sidebar from './components/Sidebar';
import TopHeader from './components/TopHeader';
import { AuthProvider, useAuth } from './contexts/AuthContext';

// Pages
import LoginPage from './pages/LoginPage';
import RegisterPage from './pages/RegisterPage';
import DashboardPage from './pages/DashboardPage';
import DHCPAnalyticsPage from './pages/DHCPAnalyticsPage';
import NASAnalyticsPage from './pages/NASAnalyticsPage';
import NTPAnalyticsPage from './pages/NTPAnalyticsPage';
import GitLabAnalyticsPage from './pages/GitLabAnalyticsPage';
import IPXEAnalyticsPage from './pages/IPXEAnalyticsPage';
import DHCPServerManagementPage from './pages/DHCPServerManagementPage';
import IPXEManagementPage from './pages/IPXEManagementPage';
import UserManagementPage from './pages/UserManagementPage';
import SettingsPage from './pages/SettingsPage';
import SystemMonitorPage from './pages/SystemMonitorPage';
import RVTAnalysisPage from './pages/RVTAnalysisPage';
import RVTManagementPage from './pages/RVTManagementPage';
import BuildConfigValidatorPage from './pages/BuildConfigValidatorPage';
import AnsibleInventoryManagerPage from './pages/AnsibleInventoryManagerPage';

const { Content } = Layout;

function App() {
    return (
        <AuthProvider>
            <Router future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
                <AppLayout />
            </Router>
        </AuthProvider>
    );
}

function AppLayout() {
    const [collapsed, setCollapsed] = useState(false);
    const location = useLocation();
    const navigate = useNavigate();
    const { isAuthenticated, loading } = useAuth();

    const toggleSidebar = () => {
        setCollapsed(!collapsed);
    };
    
    // 從 URL 獲取當前 Tab（用於 RVT Analytics）
    const getRVTActiveTab = () => {
        const params = new URLSearchParams(location.search);
        const tab = params.get('tab');
        // 如果沒有 tab 參數（概觀頁面），返回 null，不選中任何 Tab
        // 如果有 tab 參數，返回對應的值
        return tab || null;
    };
    
    // 處理 RVT Tab 切換
    const handleRVTTabChange = (tab) => {
        navigate(`/rvt-analytics?tab=${tab}`);
    };

    // 處理 RVT 頁面標題點擊（導航到概觀）
    const handleRVTTitleClick = () => {
        if (location.pathname.startsWith('/rvt-analytics')) {
            navigate('/rvt-analytics'); // 移除所有 query parameters，回到概觀
        }
    };

    // 未登入且不在登入或註冊頁面，重定向到登入頁
    if (!loading && !isAuthenticated && location.pathname !== '/login' && location.pathname !== '/register') {
        return <Navigate to="/login" replace />;
    }

    const getPageTitle = (pathname) => {
        // 處理 DHCP Analytics 子路由
        if (pathname.startsWith('/dhcp-analytics')) {
            return 'DHCP Server 分析';
        }
        
        // 處理 iPXE Analytics 子路由
        if (pathname.startsWith('/ipxe-analytics')) {
            return 'iPXE 分析';
        }
        
        // 處理 RVT Analytics 子路由
        if (pathname.startsWith('/rvt-analytics')) {
            return 'RVT 分析';
        }
        
        switch (pathname) {
            case '/login':
                return '登入';
            case '/register':
                return '註冊';
            case '/dashboard':
                return 'Dashboard';
            case '/nas-analytics':
                return 'NAS 分析';
            case '/ntp-analytics':
                return 'NTP 分析';
            case '/gitlab-analytics':
                return 'GitLab 分析';
            case '/system-monitor':
                return '系統監控';
            case '/admin/dhcp-server-management':
                return 'DHCP Server 管理';
            case '/admin/ipxe-server-management':
                return 'IPXE Server 管理';
            case '/admin/rvt-management':
                return 'RVT 管理';
            case '/admin/user-management':
                return '用戶管理';
            case '/settings':
                return '系統設定';
            default:
                return 'NT Network Toolbox';
        }
    };

    const currentPageTitle = getPageTitle(location.pathname);
    
    // 為 RVT Analytics 頁面準備 Tab（始終顯示 Jenkins 詳細 Tab）
    const rvtAnalyticsTabs = location.pathname.startsWith('/rvt-analytics') ? (
        <div style={{ 
            display: 'flex', 
            alignItems: 'center', 
            justifyContent: 'center',
            height: '64px',
            position: 'absolute',
            left: '50%',
            transform: 'translateX(-50%)',
            top: 0
        }}>
            <Tabs 
                activeKey={getRVTActiveTab()}
                onChange={handleRVTTabChange}
                size="large"
                style={{ 
                    marginBottom: 0,
                }}
                className="rvt-header-tabs"
            >
                <Tabs.TabPane 
                    tab={
                        <span style={{ 
                            padding: '10px 24px',
                            display: 'inline-block',
                            fontWeight: 500,
                            fontSize: '15px'
                        }}>
                            <FolderOutlined style={{ marginRight: 8, fontSize: '16px' }} />
                            Jenkins 詳細
                        </span>
                    } 
                    key="details"
                />
                <Tabs.TabPane 
                    tab={
                        <span style={{ 
                            padding: '10px 24px',
                            display: 'inline-block',
                            fontWeight: 500,
                            fontSize: '15px'
                        }}>
                            <FileTextOutlined style={{ marginRight: 8, fontSize: '16px' }} />
                            Ansible Inventory
                        </span>
                    } 
                    key="inventory"
                />
            </Tabs>
            <style>{`
                .rvt-header-tabs .ant-tabs-nav {
                    margin: 0 !important;
                }
                .rvt-header-tabs .ant-tabs-tab {
                    background: transparent;
                    border: none;
                    margin: 0 8px;
                    padding: 6px 0;
                    color: #666;
                    transition: all 0.3s ease;
                }
                .rvt-header-tabs .ant-tabs-tab:hover {
                    color: #1890ff;
                    background: rgba(24, 144, 255, 0.08);
                    border-radius: 6px;
                }
                .rvt-header-tabs .ant-tabs-tab-active {
                    background: linear-gradient(135deg, #1890ff 0%, #096dd9 100%) !important;
                    border-radius: 6px !important;
                    box-shadow: 0 2px 8px rgba(24, 144, 255, 0.3);
                }
                .rvt-header-tabs .ant-tabs-tab-active .ant-tabs-tab-btn {
                    color: #ffffff !important;
                }
                .rvt-header-tabs .ant-tabs-ink-bar {
                    display: none;
                }
            `}</style>
        </div>
    ) : null;

    // 載入中
    if (loading) {
        return <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh' }}>載入中...</div>;
    }

    // 登入/註冊頁面（獨立布局）
    if (location.pathname === '/login' || location.pathname === '/register') {
        return (
            <Routes>
                <Route path="/login" element={<LoginPage />} />
                <Route path="/register" element={<RegisterPage />} />
            </Routes>
        );
    }

    // 主要介面（需要登入）
    return (
        <Layout style={{ minHeight: '100vh' }}>
            <Sidebar
                collapsed={collapsed}
                onCollapse={toggleSidebar}
            />

            <Layout style={{ marginLeft: collapsed ? 80 : 300, transition: 'margin-left 0.2s' }}>
                <TopHeader
                    collapsed={collapsed}
                    onToggleSidebar={toggleSidebar}
                    pageTitle={currentPageTitle}
                    extraActions={rvtAnalyticsTabs}
                    onTitleClick={location.pathname.startsWith('/rvt-analytics') ? handleRVTTitleClick : null}
                />

                <Content style={{
                    marginTop: 64,
                    background: '#f5f5f5',
                    minHeight: 'calc(100vh - 64px)',
                    overflow: 'auto'
                }}>
                    <Routes>
                        <Route path="/" element={<Navigate to="/dhcp-analytics" replace />} />
                        <Route path="/dashboard" element={<DashboardPage />} />
                        
                        {/* DHCP Analytics 路由 - 支援子路由 */}
                        <Route path="/dhcp-analytics" element={<DHCPAnalyticsPage />} />
                        <Route path="/dhcp-analytics/:tab" element={<DHCPAnalyticsPage />} />
                        <Route path="/dhcp-analytics/server/:serverId/:tab" element={<DHCPAnalyticsPage />} />
                        
                        <Route path="/nas-analytics" element={<NASAnalyticsPage />} />
                        <Route path="/ntp-analytics" element={<NTPAnalyticsPage />} />
                        <Route path="/gitlab-analytics" element={<GitLabAnalyticsPage />} />
                        
                        {/* iPXE Analytics 路由 - 支援子路由 */}
                        <Route path="/ipxe-analytics" element={<IPXEAnalyticsPage />} />
                        <Route path="/ipxe-analytics/:tab" element={<IPXEAnalyticsPage />} />
                        <Route path="/ipxe-analytics/server/:serverId/:tab" element={<IPXEAnalyticsPage />} />
                        
                        {/* RVT Analytics 路由 - 僅 Admin 可訪問 */}
                        <Route path="/rvt-analytics" element={<RVTAnalysisPage />} />
                        <Route path="/rvt-analytics/build-config-validator/:buildId" element={<BuildConfigValidatorPage />} />
                        
                        {/* Ansible Inventory Manager 路由 */}
                        <Route path="/ansible-inventory-manager" element={<AnsibleInventoryManagerPage />} />
                        
                        <Route path="/system-monitor" element={<SystemMonitorPage />} />
                        <Route path="/admin/dhcp-server-management" element={<DHCPServerManagementPage />} />
                        <Route path="/admin/ipxe-server-management" element={<IPXEManagementPage />} />
                        <Route path="/admin/rvt-management" element={<RVTManagementPage />} />
                        <Route path="/admin/user-management" element={<UserManagementPage />} />
                        <Route path="/settings" element={<SettingsPage />} />
                    </Routes>
                </Content>
            </Layout>
        </Layout>
    );
}

export default App;
