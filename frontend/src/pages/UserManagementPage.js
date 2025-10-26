import React from 'react';
import { Card, Typography } from 'antd';
import { UserOutlined } from '@ant-design/icons';

const { Title, Paragraph } = Typography;

const UserManagementPage = () => {
    return (
        <div style={{ padding: '24px' }}>
            <Card>
                <div style={{ textAlign: 'center', padding: '60px 20px' }}>
                    <UserOutlined style={{ fontSize: '64px', color: '#2196f3', marginBottom: '24px' }} />
                    <Title level={3}>用戶管理</Title>
                    <Paragraph type="secondary">
                        此頁面將提供系統用戶的管理功能
                    </Paragraph>
                    <Paragraph type="secondary">
                        包含：用戶列表、權限設定、角色管理等
                    </Paragraph>
                </div>
            </Card>
        </div>
    );
};

export default UserManagementPage;
