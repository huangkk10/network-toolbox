import React, { useState } from 'react';
import './App.css';
import { BrowserRouter as Router, Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { Layout } from 'antd';
import Sidebar from './components/Sidebar';
import TopHeader from './components/TopHeader';
import { AuthProvider } from './contexts/AuthContext';

// Pages
import DashboardPage from './pages/DashboardPage';
import DHCPAnalyticsPage from './pages/DHCPAnalyticsPage';
import DHCPServerManagementPage from './pages/DHCPServerManagementPage';
import UserManagementPage from './pages/UserManagementPage';
import SettingsPage from './pages/SettingsPage';

const { Content } = Layout;

function App() {
    return (
        <AuthProvider>
            <Router>
                <AppLayout />
            </Router>
        </AuthProvider>
    );
}

function AppLayout() {
    const [collapsed, setCollapsed] = useState(false);
    const location = useLocation();

    const toggleSidebar = () => {
        setCollapsed(!collapsed);
    };

    const getPageTitle = (pathname) => {
        switch (pathname) {
            case '/dashboard':
                return 'Dashboard';
            case '/dhcp-analytics':
                return 'DHCP Server 分析';
            case '/admin/dhcp-server-management':
                return 'DHCP Server 管理';
            case '/admin/user-management':
                return '用戶管理';
            case '/settings':
                return '系統設定';
            default:
                return 'NT Network Toolbox';
        }
    };

    const currentPageTitle = getPageTitle(location.pathname);

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
                        <Route path="/" element={<Navigate to="/dashboard" replace />} />
                        <Route path="/dashboard" element={<DashboardPage />} />
                        <Route path="/dhcp-analytics" element={<DHCPAnalyticsPage />} />
                        <Route path="/admin/dhcp-server-management" element={<DHCPServerManagementPage />} />
                        <Route path="/admin/user-management" element={<UserManagementPage />} />
                        <Route path="/settings" element={<SettingsPage />} />
                    </Routes>
                </Content>
            </Layout>
        </Layout>
    );
}

export default App;
