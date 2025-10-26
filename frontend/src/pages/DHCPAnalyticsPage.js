import React from 'react';
import { Card, Typography } from 'antd';
import { BarChartOutlined } from '@ant-design/icons';

const { Title, Paragraph } = Typography;

const DHCPAnalyticsPage = () => {
    return (
        <div style={{ padding: '24px' }}>
            <Card>
                <div style={{ textAlign: 'center', padding: '60px 20px' }}>
                    <BarChartOutlined style={{ fontSize: '64px', color: '#2196f3', marginBottom: '24px' }} />
                    <Title level={3}>DHCP Server 分析</Title>
                    <Paragraph type="secondary">
                        此頁面將顯示 DHCP Server 的詳細分析數據
                    </Paragraph>
                    <Paragraph type="secondary">
                        包含：租約趨勢圖、IP 分佈分析、Top 客戶端列表等
                    </Paragraph>
                </div>
            </Card>
        </div>
    );
};

export default DHCPAnalyticsPage;
