import React from 'react';
import { Layout, Button, Dropdown, Avatar, Typography, Space } from 'antd';
import {
    MenuOutlined,
    UserOutlined,
    SettingOutlined,
    LogoutOutlined,
    BellOutlined,
    ReloadOutlined,
} from '@ant-design/icons';
import { useAuth } from '../contexts/AuthContext';
import './TopHeader.css';

const { Header } = Layout;
const { Text } = Typography;

const TopHeader = ({ collapsed, onToggleSidebar, pageTitle, extraActions }) => {
    const { user, isAuthenticated, logout } = useAuth();

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
            onClick: logout,
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
                    <div className="page-title-container">
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

                    {/* 通知按鈕 */}
                    <Button
                        type="text"
                        icon={<BellOutlined />}
                        className="icon-button"
                    />

                    {/* 重新載入按鈕 */}
                    <Button
                        type="text"
                        icon={<ReloadOutlined />}
                        className="icon-button"
                    />

                    {/* 用戶下拉選單 */}
                    {isAuthenticated && user ? (
                        <Dropdown
                            menu={{ items: userMenuItems }}
                            placement="bottomRight"
                            trigger={['click']}
                        >
                            <div className="user-info">
                                <Avatar
                                    size={36}
                                    icon={<UserOutlined />}
                                    className="user-avatar"
                                />
                                <div className="user-details">
                                    <Text className="user-name">{user.username || 'Admin'}</Text>
                                    <Text className="user-role">{user.is_staff ? '管理員' : '用戶'}</Text>
                                </div>
                            </div>
                        </Dropdown>
                    ) : (
                        <Avatar
                            size={36}
                            icon={<UserOutlined />}
                            className="user-avatar"
                        />
                    )}
                </Space>
            </div>
        </Header>
    );
};

export default TopHeader;
