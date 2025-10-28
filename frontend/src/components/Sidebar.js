import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Layout, Menu, Avatar, Typography } from 'antd';
import {
    HomeOutlined,
    BarChartOutlined,
    DatabaseOutlined,
    UserOutlined,
    SettingOutlined,
    MenuFoldOutlined,
    MenuUnfoldOutlined,
    ExperimentOutlined,
    CloudServerOutlined,
} from '@ant-design/icons';
import { useAuth } from '../contexts/AuthContext';
import './Sidebar.css';

const { Sider } = Layout;
const { Text } = Typography;

const Sidebar = ({ collapsed, onCollapse }) => {
    const { user, isAuthenticated } = useAuth();
    const navigate = useNavigate();

    // 處理選單點擊
    const handleMenuClick = ({ key }) => {
        console.log('Menu clicked:', key);
        switch (key) {
            case 'dashboard':
                navigate('/dashboard');
                break;
            case 'dhcp-analytics':
                navigate('/dhcp-analytics');
                break;
            case 'nas-analytics':
                navigate('/nas-analytics');
                break;
            case 'dhcp-server-management':
                navigate('/admin/dhcp-server-management');
                break;
            case 'user-management':
                navigate('/admin/user-management');
                break;
            case 'settings':
                navigate('/settings');
                break;
            default:
                console.log('Unknown menu key:', key);
                break;
        }
    };

    // 主選單項目
    const mainMenuItems = [
        {
            key: 'dhcp-analytics',
            icon: <BarChartOutlined />,
            label: 'DHCP Server 分析',
        },
        {
            key: 'nas-analytics',
            icon: <CloudServerOutlined />,
            label: 'NAS 分析',
        },
    ];

    // 管理功能選單
    const adminMenuItems = [
        {
            key: 'admin-group',
            type: 'group',
            label: '管理功能',
            children: [
                {
                    key: 'dhcp-server-management',
                    icon: <DatabaseOutlined />,
                    label: 'DHCP Server 管理',
                },
                {
                    key: 'user-management',
                    icon: <UserOutlined />,
                    label: '用戶管理',
                },
            ],
        },
    ];

    // 系統選單
    const systemMenuItems = [
        {
            key: 'settings',
            icon: <SettingOutlined />,
            label: '系統設定',
        },
    ];

    // 根據用戶權限組合選單項目
    const allMenuItems = [
        ...mainMenuItems,
        // 只有已登入且是 admin 的用戶才能看到管理功能和系統設定
        ...(isAuthenticated && user?.is_staff ? adminMenuItems : []),
        ...(isAuthenticated && user?.is_staff ? systemMenuItems : []),
    ];

    return (
        <Sider
            trigger={null}
            collapsible
            collapsed={collapsed}
            width={300}
            collapsedWidth={80}
            className="nt-sidebar"
            style={{
                overflow: 'auto',
                height: '100vh',
                position: 'fixed',
                left: 0,
                top: 0,
                bottom: 0,
                zIndex: 1000,
            }}
        >
            {/* Logo 區域 */}
            <div className="sidebar-logo" onClick={() => navigate('/dashboard')}>
                {!collapsed ? (
                    <div className="logo-expanded">
                        <Avatar
                            size={48}
                            icon={<HomeOutlined />}
                            className="logo-icon"
                        />
                        <div className="logo-text">
                            <Text className="logo-title">NT</Text>
                            <Text className="logo-subtitle">Network Toolbox</Text>
                            <Text className="logo-description">DHCP Management</Text>
                        </div>
                    </div>
                ) : (
                    <div className="logo-collapsed">
                        <Avatar
                            size={40}
                            icon={<HomeOutlined />}
                            className="logo-icon"
                        />
                        <Text className="logo-title-small">NT</Text>
                    </div>
                )}
            </div>

            {/* 菜單 */}
            <Menu
                theme="light"
                mode="inline"
                defaultSelectedKeys={['dashboard']}
                items={allMenuItems}
                onClick={handleMenuClick}
                className="sidebar-menu"
            />

            {/* 收縮按鈕 */}
            <div className="collapse-button-container" onClick={onCollapse}>
                <div className="collapse-button">
                    {collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
                </div>
            </div>
        </Sider>
    );
};

export default Sidebar;
