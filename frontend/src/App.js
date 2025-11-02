import React, { useState } from 'react';
import './App.css';
import { BrowserRouter as Router, Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { Layout } from 'antd';
import Sidebar from './components/Sidebar';
import TopHeader from './components/TopHeader';
import { AuthProvider, useAuth } from './contexts/AuthContext';

// Pages
import LoginPage from './pages/LoginPage';
import RegisterPage from './pages/RegisterPage';
import DashboardPage from './pages/DashboardPage';
import DHCPAnalyticsPage from './pages/DHCPAnalyticsPage';
import NASAnalyticsPage from './pages/NASAnalyticsPage';
import GitLabAnalyticsPage from './pages/GitLabAnalyticsPage';
import IPXEAnalyticsPage from './pages/IPXEAnalyticsPage';
import DHCPServerManagementPage from './pages/DHCPServerManagementPage';
import IPXEManagementPage from './pages/IPXEManagementPage';
import UserManagementPage from './pages/UserManagementPage';
import SettingsPage from './pages/SettingsPage';
import SystemMonitorPage from './pages/SystemMonitorPage';

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
    const { isAuthenticated, loading } = useAuth();

    const toggleSidebar = () => {
        setCollapsed(!collapsed);
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
        
        switch (pathname) {
            case '/login':
                return '登入';
            case '/register':
                return '註冊';
            case '/dashboard':
                return 'Dashboard';
            case '/nas-analytics':
                return 'NAS 分析';
            case '/gitlab-analytics':
                return 'GitLab 分析';
            case '/system-monitor':
                return '系統監控';
            case '/admin/dhcp-server-management':
                return 'DHCP Server 管理';
            case '/admin/ipxe-server-management':
                return 'IPXE Server 管理';
            case '/admin/user-management':
                return '用戶管理';
            case '/settings':
                return '系統設定';
            default:
                return 'NT Network Toolbox';
        }
    };

    const currentPageTitle = getPageTitle(location.pathname);

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
                        <Route path="/gitlab-analytics" element={<GitLabAnalyticsPage />} />
                        
                        {/* iPXE Analytics 路由 - 支援子路由 */}
                        <Route path="/ipxe-analytics" element={<IPXEAnalyticsPage />} />
                        <Route path="/ipxe-analytics/:tab" element={<IPXEAnalyticsPage />} />
                        <Route path="/ipxe-analytics/server/:serverId/:tab" element={<IPXEAnalyticsPage />} />
                        <Route path="/system-monitor" element={<SystemMonitorPage />} />
                        <Route path="/admin/dhcp-server-management" element={<DHCPServerManagementPage />} />
                        <Route path="/admin/ipxe-server-management" element={<IPXEManagementPage />} />
                        <Route path="/admin/user-management" element={<UserManagementPage />} />
                        <Route path="/settings" element={<SettingsPage />} />
                    </Routes>
                </Content>
            </Layout>
        </Layout>
    );
}

export default App;
