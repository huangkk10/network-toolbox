import React from 'react';
import { Card, Typography } from 'antd';
import { SettingOutlined } from '@ant-design/icons';

const { Title, Paragraph } = Typography;

const SettingsPage = () => {
    return (
        <div style={{ padding: '24px' }}>
            <Card>
                <div style={{ textAlign: 'center', padding: '60px 20px' }}>
                    <SettingOutlined style={{ fontSize: '64px', color: '#2196f3', marginBottom: '24px' }} />
                    <Title level={3}>系統設定</Title>
                    <Paragraph type="secondary">
                        此頁面將提供系統的各項設定功能
                    </Paragraph>
                    <Paragraph type="secondary">
                        包含：告警閾值、同步間隔、通知設定等
                    </Paragraph>
                </div>
            </Card>
        </div>
    );
};

export default SettingsPage;
