import React from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
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
    DashboardOutlined,
    GitlabOutlined,
    RocketOutlined,
} from '@ant-design/icons';
import { useAuth } from '../contexts/AuthContext';
import './Sidebar.css';

const { Sider } = Layout;
const { Text } = Typography;

const Sidebar = ({ collapsed, onCollapse }) => {
    const { user, isAuthenticated } = useAuth();
    const navigate = useNavigate();
    const location = useLocation();
    
    // 根據當前路徑決定選中的菜單項
    const getSelectedKey = () => {
        const pathname = location.pathname;
        
        // 處理 DHCP Analytics 子路由
        if (pathname.startsWith('/dhcp-analytics')) {
            return 'dhcp-analytics';
        }
        
        // 處理 iPXE Analytics 子路由
        if (pathname.startsWith('/ipxe-analytics')) {
            return 'ipxe-analytics';
        }
        
        // 處理 RVT Analytics 子路由
        if (pathname.startsWith('/rvt-analytics')) {
            return 'rvt-analytics';
        }
        
        // 處理其他路由
        if (pathname.startsWith('/admin/dhcp-server-management')) {
            return 'dhcp-server-management';
        }
        if (pathname.startsWith('/admin/ipxe-server-management')) {
            return 'ipxe-server-management';
        }
        if (pathname.startsWith('/admin/rvt-management')) {
            return 'rvt-management';
        }
        if (pathname.startsWith('/admin/user-management')) {
            return 'user-management';
        }
        if (pathname.startsWith('/nas-analytics')) {
            return 'nas-analytics';
        }
        if (pathname.startsWith('/gitlab-analytics')) {
            return 'gitlab-analytics';
        }
        if (pathname.startsWith('/system-monitor')) {
            return 'system-monitor';
        }
        if (pathname.startsWith('/settings')) {
            return 'settings';
        }
        if (pathname.startsWith('/dashboard') || pathname === '/') {
            return 'dashboard';
        }
        
        return 'dashboard';
    };

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
            case 'gitlab-analytics':
                navigate('/gitlab-analytics');
                break;
            case 'ipxe-analytics':
                navigate('/ipxe-analytics');
                break;
            case 'rvt-analytics':
                navigate('/rvt-analytics');
                break;
            case 'system-monitor':
                navigate('/system-monitor');
                break;
            case 'dhcp-server-management':
                navigate('/admin/dhcp-server-management');
                break;
            case 'ipxe-server-management':
                navigate('/admin/ipxe-server-management');
                break;
            case 'rvt-management':
                navigate('/admin/rvt-management');
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
        {
            key: 'gitlab-analytics',
            icon: <GitlabOutlined />,
            label: 'GitLab 分析',
        },
        {
            key: 'ipxe-analytics',
            icon: <ExperimentOutlined />,
            label: 'IPXE 分析',
        },
    ];
    
    // RVT 分析菜單項（僅 Admin 可見）
    const rvtMenuItem = {
        key: 'rvt-analytics',
        icon: <RocketOutlined />,
        label: 'RVT 分析',
    };

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
                    key: 'ipxe-server-management',
                    icon: <ExperimentOutlined />,
                    label: 'IPXE Server 管理',
                },
                {
                    key: 'rvt-management',
                    icon: <RocketOutlined />,
                    label: 'RVT 管理',
                },
                {
                    key: 'user-management',
                    icon: <UserOutlined />,
                    label: '用戶管理',
                },
                {
                    key: 'system-monitor',
                    icon: <DashboardOutlined />,
                    label: '系統監控',
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
        // RVT 分析（僅 Admin 可見）
        ...(isAuthenticated && user?.is_staff ? [rvtMenuItem] : []),
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
                            src="/management.png"
                            icon={<HomeOutlined />}
                            className="logo-icon"
                            style={{ backgroundColor: 'transparent' }}
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
                            src="/management.png"
                            icon={<HomeOutlined />}
                            className="logo-icon"
                            style={{ backgroundColor: 'transparent' }}
                        />
                        <Text className="logo-title-small">NT</Text>
                    </div>
                )}
            </div>

            {/* 菜單 */}
            <Menu
                theme="light"
                mode="inline"
                selectedKeys={[getSelectedKey()]}
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
