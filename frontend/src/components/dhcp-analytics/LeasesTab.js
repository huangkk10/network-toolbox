import React, { useState, useEffect } from 'react';
import { Card, Table, Input, Select, Button, Space, Tag, DatePicker, Modal, Descriptions } from 'antd';
import {
    SearchOutlined,
    ReloadOutlined,
    DownloadOutlined,
    CheckCircleOutlined,
    ClockCircleOutlined,
    InfoCircleOutlined,
} from '@ant-design/icons';
import dayjs from 'dayjs';

const { RangePicker } = DatePicker;

const LeasesTab = ({ serverId }) => {
    const [loading, setLoading] = useState(false);
    const [data, setData] = useState([]);
    const [searchText, setSearchText] = useState('');
    const [statusFilter, setStatusFilter] = useState('all');
    const [detailModalVisible, setDetailModalVisible] = useState(false);
    const [selectedLease, setSelectedLease] = useState(null);

    // 模擬租約數據
    const mockLeases = [
        {
            key: '1',
            ip: '192.168.1.100',
            mac: '00:1A:2B:3C:4D:5E',
            hostname: 'desktop-001',
            status: 'active',
            startTime: '2025-10-26 14:30:22',
            endTime: '2025-10-27 14:30:22',
            server: '192.168.1.1',
            vendor: 'Dell Inc.',
        },
        {
            key: '2',
            ip: '192.168.1.101',
            mac: '00:1A:2B:3C:4D:5F',
            hostname: 'laptop-005',
            status: 'active',
            startTime: '2025-10-26 13:15:10',
            endTime: '2025-10-27 13:15:10',
            server: '192.168.1.1',
            vendor: 'Apple, Inc.',
        },
        {
            key: '3',
            ip: '192.168.2.50',
            mac: '00:1A:2B:3C:4D:60',
            hostname: 'server-db-01',
            status: 'expired',
            startTime: '2025-10-25 10:00:00',
            endTime: '2025-10-26 10:00:00',
            server: '192.168.2.1',
            vendor: 'HP Inc.',
        },
        {
            key: '4',
            ip: '10.0.1.200',
            mac: '00:1A:2B:3C:4D:61',
            hostname: 'printer-002',
            status: 'active',
            startTime: '2025-10-26 09:45:33',
            endTime: '2025-10-27 09:45:33',
            server: '10.0.1.1',
            vendor: 'Canon Inc.',
        },
        {
            key: '5',
            ip: '192.168.1.150',
            mac: '00:1A:2B:3C:4D:62',
            hostname: 'mobile-device-123',
            status: 'active',
            startTime: '2025-10-26 16:20:45',
            endTime: '2025-10-27 16:20:45',
            server: '192.168.1.1',
            vendor: 'Samsung Electronics',
        },
        {
            key: '6',
            ip: '192.168.3.88',
            mac: '00:1A:2B:3C:4D:63',
            hostname: 'iot-sensor-01',
            status: 'released',
            startTime: '2025-10-24 08:00:00',
            endTime: '2025-10-25 08:00:00',
            server: '192.168.3.1',
            vendor: 'Raspberry Pi Foundation',
        },
    ];

    useEffect(() => {
        // 模擬載入數據
        setData(mockLeases);
    }, [serverId]);

    const columns = [
        {
            title: 'IP 位址',
            dataIndex: 'ip',
            key: 'ip',
            sorter: (a, b) => a.ip.localeCompare(b.ip),
            filterDropdown: ({ setSelectedKeys, selectedKeys, confirm, clearFilters }) => (
                <div style={{ padding: 8 }}>
                    <Input
                        placeholder="搜尋 IP"
                        value={selectedKeys[0]}
                        onChange={(e) => setSelectedKeys(e.target.value ? [e.target.value] : [])}
                        onPressEnter={() => confirm()}
                        style={{ width: 188, marginBottom: 8, display: 'block' }}
                    />
                    <Space>
                        <Button
                            type="primary"
                            onClick={() => confirm()}
                            icon={<SearchOutlined />}
                            size="small"
                            style={{ width: 90 }}
                        >
                            搜尋
                        </Button>
                        <Button onClick={() => clearFilters()} size="small" style={{ width: 90 }}>
                            重置
                        </Button>
                    </Space>
                </div>
            ),
            filterIcon: (filtered) => <SearchOutlined style={{ color: filtered ? '#2196f3' : undefined }} />,
            onFilter: (value, record) => record.ip.toLowerCase().includes(value.toLowerCase()),
        },
        {
            title: 'MAC 位址',
            dataIndex: 'mac',
            key: 'mac',
            render: (mac) => <code>{mac}</code>,
        },
        {
            title: '主機名稱',
            dataIndex: 'hostname',
            key: 'hostname',
            sorter: (a, b) => a.hostname.localeCompare(b.hostname),
        },
        {
            title: '狀態',
            dataIndex: 'status',
            key: 'status',
            filters: [
                { text: '活躍中', value: 'active' },
                { text: '已過期', value: 'expired' },
                { text: '已釋放', value: 'released' },
            ],
            onFilter: (value, record) => record.status === value,
            render: (status) => {
                const statusConfig = {
                    active: { color: 'success', icon: <CheckCircleOutlined />, text: '活躍中' },
                    expired: { color: 'warning', icon: <ClockCircleOutlined />, text: '已過期' },
                    released: { color: 'default', icon: <InfoCircleOutlined />, text: '已釋放' },
                };
                const config = statusConfig[status];
                return (
                    <Tag color={config.color} icon={config.icon}>
                        {config.text}
                    </Tag>
                );
            },
        },
        {
            title: '開始時間',
            dataIndex: 'startTime',
            key: 'startTime',
            sorter: (a, b) => new Date(a.startTime) - new Date(b.startTime),
        },
        {
            title: '到期時間',
            dataIndex: 'endTime',
            key: 'endTime',
            sorter: (a, b) => new Date(a.endTime) - new Date(b.endTime),
        },
        {
            title: 'DHCP Server',
            dataIndex: 'server',
            key: 'server',
        },
        {
            title: '操作',
            key: 'action',
            render: (_, record) => (
                <Button
                    type="link"
                    size="small"
                    onClick={() => {
                        setSelectedLease(record);
                        setDetailModalVisible(true);
                    }}
                >
                    詳細
                </Button>
            ),
        },
    ];

    const handleRefresh = () => {
        setLoading(true);
        setTimeout(() => {
            setData(mockLeases);
            setLoading(false);
        }, 500);
    };

    const handleExport = () => {
        // TODO: 實作匯出 CSV 功能
        console.log('Export to CSV');
    };

    return (
        <div>
            {/* 操作工具列 */}
            <Card style={{ marginBottom: '16px' }}>
                <Space wrap>
                    <Input.Search
                        placeholder="搜尋 IP、MAC 或主機名稱..."
                        allowClear
                        style={{ width: 300 }}
                        onSearch={(value) => setSearchText(value)}
                    />
                    <Select
                        style={{ width: 120 }}
                        value={statusFilter}
                        onChange={setStatusFilter}
                        options={[
                            { value: 'all', label: '所有狀態' },
                            { value: 'active', label: '活躍中' },
                            { value: 'expired', label: '已過期' },
                            { value: 'released', label: '已釋放' },
                        ]}
                    />
                    <RangePicker />
                    <Button icon={<DownloadOutlined />} onClick={handleExport}>
                        匯出 CSV
                    </Button>
                    <Button icon={<ReloadOutlined />} onClick={handleRefresh}>
                        重新整理
                    </Button>
                </Space>
            </Card>

            {/* 租約列表 */}
            <Card>
                <Table
                    columns={columns}
                    dataSource={data}
                    loading={loading}
                    pagination={{
                        pageSize: 20,
                        showSizeChanger: true,
                        showTotal: (total) => `共 ${total} 筆`,
                    }}
                    size="middle"
                />
            </Card>

            {/* 詳細資訊 Modal */}
            <Modal
                title="租約詳細資訊"
                open={detailModalVisible}
                onCancel={() => setDetailModalVisible(false)}
                footer={[
                    <Button key="close" onClick={() => setDetailModalVisible(false)}>
                        關閉
                    </Button>,
                ]}
                width={700}
            >
                {selectedLease && (
                    <Descriptions bordered column={2}>
                        <Descriptions.Item label="IP 位址" span={2}>
                            <strong>{selectedLease.ip}</strong>
                        </Descriptions.Item>
                        <Descriptions.Item label="MAC 位址" span={2}>
                            <code>{selectedLease.mac}</code>
                        </Descriptions.Item>
                        <Descriptions.Item label="主機名稱" span={2}>
                            {selectedLease.hostname}
                        </Descriptions.Item>
                        <Descriptions.Item label="狀態">
                            <Tag
                                color={
                                    selectedLease.status === 'active'
                                        ? 'success'
                                        : selectedLease.status === 'expired'
                                            ? 'warning'
                                            : 'default'
                                }
                            >
                                {selectedLease.status === 'active'
                                    ? '活躍中'
                                    : selectedLease.status === 'expired'
                                        ? '已過期'
                                        : '已釋放'}
                            </Tag>
                        </Descriptions.Item>
                        <Descriptions.Item label="製造商">{selectedLease.vendor}</Descriptions.Item>
                        <Descriptions.Item label="開始時間">{selectedLease.startTime}</Descriptions.Item>
                        <Descriptions.Item label="到期時間">{selectedLease.endTime}</Descriptions.Item>
                        <Descriptions.Item label="DHCP Server" span={2}>
                            {selectedLease.server}
                        </Descriptions.Item>
                    </Descriptions>
                )}
            </Modal>
        </div>
    );
};

export default LeasesTab;
