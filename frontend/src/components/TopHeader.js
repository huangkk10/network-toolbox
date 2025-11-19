import React from 'react';
import { Layout, Button, Dropdown, Avatar, Typography, Space } from 'antd';
import {
    MenuOutlined,
    UserOutlined,
    SettingOutlined,
    LogoutOutlined,
} from '@ant-design/icons';
import { useAuth } from '../contexts/AuthContext';
import { useNavigate } from 'react-router-dom';
import './TopHeader.css';

const { Header } = Layout;
const { Text } = Typography;

const TopHeader = ({ collapsed, onToggleSidebar, pageTitle, extraActions, onTitleClick }) => {
    const { user, isAuthenticated, logout } = useAuth();
    const navigate = useNavigate();

    // 處理用戶選單點擊
    const handleMenuClick = ({ key }) => {
        console.log('User menu clicked:', key);
        switch (key) {
            case 'profile':
                console.log('Navigate to profile');
                navigate('/profile');
                break;
            case 'settings':
                console.log('Navigate to settings');
                navigate('/settings');
                break;
            case 'logout':
                console.log('Logging out...');
                logout();
                // 登出後導向登入頁面
                navigate('/login');
                break;
            default:
                break;
        }
    };

    // 用戶下拉選單
    const userMenuItems = [
        {
            key: 'profile',
            icon: <UserOutlined />,
            label: '個人資料',
        },
        {
            key: 'settings',
            icon: <SettingOutlined />,
            label: '帳戶設定',
        },
        {
            type: 'divider',
        },
        {
            key: 'logout',
            icon: <LogoutOutlined />,
            label: '登出',
            danger: true,
        },
    ];

    return (
        <Header className="nt-topheader">
            <div className="topheader-left">
                <Button
                    type="text"
                    icon={<MenuOutlined />}
                    onClick={onToggleSidebar}
                    className="toggle-button"
                />
                {pageTitle && (
                    <div 
                        className="page-title-container"
                        onClick={onTitleClick}
                        style={{ cursor: onTitleClick ? 'pointer' : 'default' }}
                    >
                        <Text className="page-title">
                            {typeof pageTitle === 'object' ? pageTitle.text : pageTitle}
                        </Text>
                        {typeof pageTitle === 'object' && pageTitle.id && (
                            <Text className="page-subtitle">ID: {pageTitle.id}</Text>
                        )}
                    </div>
                )}
            </div>

            <div className="topheader-right">
                <Space size="middle">
                    {/* 額外操作按鈕 */}
                    {extraActions && <div className="extra-actions">{extraActions}</div>}

                    {/* 用戶選單或登入按鈕 */}
                    {isAuthenticated && user ? (
                        // 已登入：顯示用戶下拉選單
                        <Dropdown
                            menu={{
                                items: userMenuItems,
                                onClick: handleMenuClick
                            }}
                            placement="bottomRight"
                            trigger={['click']}
                            arrow
                        >
                            <div
                                className="user-info"
                                style={{ cursor: 'pointer' }}
                                onClick={(e) => {
                                    console.log('User info clicked', e);
                                    e.stopPropagation();
                                }}
                            >
                                <Avatar
                                    size={36}
                                    icon={<UserOutlined />}
                                    className="user-avatar"
                                    style={{ cursor: 'pointer' }}
                                />
                                <div className="user-details">
                                    <Text className="user-name">{user.username || 'Admin'}</Text>
                                    <Text className="user-role">{user.is_staff ? '管理員' : '用戶'}</Text>
                                </div>
                            </div>
                        </Dropdown>
                    ) : (
                        // 訪客模式：顯示登入按鈕
                        <Button
                            type="primary"
                            icon={<UserOutlined />}
                            onClick={() => navigate('/login')}
                        >
                            登入
                        </Button>
                    )}
                </Space>
            </div>
        </Header>
    );
};

export default TopHeader;
