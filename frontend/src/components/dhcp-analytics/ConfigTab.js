import React from 'react';
import { Card, Descriptions, Table, Tag, Button, Space } from 'antd';
import {
    CheckCircleOutlined,
    SyncOutlined,
    StopOutlined,
    EditOutlined,
    FileTextOutlined,
} from '@ant-design/icons';

const ConfigTab = ({ serverId }) => {
    // 模擬 Server 基本資訊
    const serverInfo = {
        ip: serverId === 'all' ? 'N/A' : '192.168.1.1',
        name: serverId === 'all' ? '所有 Server' : 'Main DHCP Server',
        status: 'running',
        uptime: '15 天 8 小時 32 分鐘',
        version: 'ISC DHCP 4.4.1',
        configFile: '/etc/dhcp/dhcpd.conf',
        leaseFile: '/var/lib/dhcp/dhcpd.leases',
    };

    // IP 池配置
    const ipPools = [
        {
            key: '1',
            subnet: '192.168.1.0/24',
            startIp: '192.168.1.10',
            endIp: '192.168.1.254',
            total: 245,
            used: 180,
            available: 65,
            utilization: '73.5%',
        },
        {
            key: '2',
            subnet: '192.168.2.0/24',
            startIp: '192.168.2.10',
            endIp: '192.168.2.254',
            total: 245,
            used: 220,
            available: 25,
            utilization: '89.8%',
        },
        {
            key: '3',
            subnet: '192.168.3.0/24',
            startIp: '192.168.3.10',
            endIp: '192.168.3.254',
            total: 245,
            used: 150,
            available: 95,
            utilization: '61.2%',
        },
        {
            key: '4',
            subnet: '10.0.1.0/24',
            startIp: '10.0.1.10',
            endIp: '10.0.1.254',
            total: 245,
            used: 200,
            available: 45,
            utilization: '81.6%',
        },
    ];

    const poolColumns = [
        {
            title: '網段',
            dataIndex: 'subnet',
            key: 'subnet',
        },
        {
            title: '起始 IP',
            dataIndex: 'startIp',
            key: 'startIp',
        },
        {
            title: '結束 IP',
            dataIndex: 'endIp',
            key: 'endIp',
        },
        {
            title: '總數',
            dataIndex: 'total',
            key: 'total',
        },
        {
            title: '已使用',
            dataIndex: 'used',
            key: 'used',
            render: (used, record) => (
                <span style={{ color: record.utilization > '80%' ? '#ff4d4f' : '#2196f3' }}>
                    <strong>{used}</strong>
                </span>
            ),
        },
        {
            title: '可用',
            dataIndex: 'available',
            key: 'available',
            render: (available, record) => (
                <span style={{ color: record.utilization > '80%' ? '#ff4d4f' : '#52c41a' }}>
                    <strong>{available}</strong>
                </span>
            ),
        },
        {
            title: '使用率',
            dataIndex: 'utilization',
            key: 'utilization',
            render: (utilization) => {
                const value = parseFloat(utilization);
                let color = '#2196f3';
                if (value > 90) color = '#ff4d4f';
                else if (value > 80) color = '#faad14';
                return <Tag color={color}>{utilization}</Tag>;
            },
        },
    ];

    // DHCP 參數
    const dhcpParams = {
        defaultLeaseTime: '86400 秒 (24 小時)',
        maxLeaseTime: '604800 秒 (7 天)',
        dnsServers: '8.8.8.8, 8.8.4.4',
        gateway: '192.168.1.1',
        domainName: 'network-toolbox.local',
        ntpServer: 'time.google.com',
    };

    return (
        <div>
            {/* Server 基本資訊 */}
            <Card title="Server 基本資訊" style={{ marginBottom: '16px' }}>
                <Descriptions bordered column={2}>
                    <Descriptions.Item label="Server IP" span={2}>
                        <strong>{serverInfo.ip}</strong>
                    </Descriptions.Item>
                    <Descriptions.Item label="Server 名稱" span={2}>
                        {serverInfo.name}
                    </Descriptions.Item>
                    <Descriptions.Item label="狀態">
                        <Tag icon={<CheckCircleOutlined />} color="success">
                            運行中
                        </Tag>
                    </Descriptions.Item>
                    <Descriptions.Item label="運行時間">{serverInfo.uptime}</Descriptions.Item>
                    <Descriptions.Item label="版本" span={2}>
                        {serverInfo.version}
                    </Descriptions.Item>
                    <Descriptions.Item label="配置檔案">{serverInfo.configFile}</Descriptions.Item>
                    <Descriptions.Item label="租約檔案">{serverInfo.leaseFile}</Descriptions.Item>
                </Descriptions>

                <div style={{ marginTop: '16px' }}>
                    <Space>
                        <Button icon={<EditOutlined />}>編輯配置</Button>
                        <Button icon={<SyncOutlined />}>重啟服務</Button>
                        <Button icon={<StopOutlined />} danger>
                            停止服務
                        </Button>
                        <Button icon={<FileTextOutlined />}>查看完整配置檔</Button>
                    </Space>
                </div>
            </Card>

            {/* IP 池配置 */}
            <Card title="IP 池配置" style={{ marginBottom: '16px' }}>
                <Table columns={poolColumns} dataSource={ipPools} pagination={false} size="middle" />
            </Card>

            {/* DHCP 參數 */}
            <Card title="DHCP 參數">
                <Descriptions bordered column={2}>
                    <Descriptions.Item label="預設租期">{dhcpParams.defaultLeaseTime}</Descriptions.Item>
                    <Descriptions.Item label="最大租期">{dhcpParams.maxLeaseTime}</Descriptions.Item>
                    <Descriptions.Item label="DNS Server" span={2}>
                        {dhcpParams.dnsServers}
                    </Descriptions.Item>
                    <Descriptions.Item label="Gateway">{dhcpParams.gateway}</Descriptions.Item>
                    <Descriptions.Item label="Domain Name">{dhcpParams.domainName}</Descriptions.Item>
                    <Descriptions.Item label="NTP Server" span={2}>
                        {dhcpParams.ntpServer}
                    </Descriptions.Item>
                </Descriptions>
            </Card>
        </div>
    );
};

export default ConfigTab;
