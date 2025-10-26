import React from 'react';
import { Card, Typography, Button } from 'antd';
import { DatabaseOutlined, PlusOutlined } from '@ant-design/icons';

const { Title, Paragraph } = Typography;

const DHCPServerManagementPage = () => {
    return (
        <div style={{ padding: '24px' }}>
            <Card>
                <div style={{ textAlign: 'center', padding: '60px 20px' }}>
                    <DatabaseOutlined style={{ fontSize: '64px', color: '#2196f3', marginBottom: '24px' }} />
                    <Title level={3}>DHCP Server 管理</Title>
                    <Paragraph type="secondary">
                        此頁面將提供 DHCP Server 的管理功能
                    </Paragraph>
                    <Paragraph type="secondary">
                        包含：新增/編輯/刪除服務器、連接測試、同步設定等
                    </Paragraph>
                    <Button type="primary" icon={<PlusOutlined />} size="large" style={{ marginTop: '24px' }}>
                        新增 DHCP Server
                    </Button>
                </div>
            </Card>
        </div>
    );
};

export default DHCPServerManagementPage;
