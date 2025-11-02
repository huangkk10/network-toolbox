import React, { useState, useEffect } from 'react';
import { 
    Card, Table, Tabs, Row, Col, Statistic, Tag, Button, Space, 
    message, Spin, Empty, Modal, Descriptions, Badge 
} from 'antd';
import {
    ApartmentOutlined,
    ApiOutlined,
    ReloadOutlined,
    EyeOutlined,
    SyncOutlined,
    NodeIndexOutlined,
} from '@ant-design/icons';
import axios from 'axios';

const SwitchTab = ({ serverId }) => {
    const [loading, setLoading] = useState(false);
    const [switches, setSwitches] = useState([]);
    const [statistics, setStatistics] = useState(null);
    const [activeTab, setActiveTab] = useState('list');
    const [selectedSwitch, setSelectedSwitch] = useState(null);
    const [modalVisible, setModalVisible] = useState(false);
    const [switchDevices, setSwitchDevices] = useState(null);
    const [loadingDevices, setLoadingDevices] = useState(false);

    // 載入 Switch 列表
    const fetchSwitches = async () => {
        setLoading(true);
        try {
            const params = serverId !== 'all' ? { server_id: serverId } : {};
            const response = await axios.get('/api/switches/', { params });
            setSwitches(response.data);
        } catch (error) {
            console.error('Error fetching switches:', error);
            message.error('載入 Switch 列表失敗：' + (error.response?.data?.message || error.message));
        } finally {
            setLoading(false);
        }
    };

    // 載入統計資訊
    const fetchStatistics = async () => {
        try {
            const params = serverId !== 'all' ? { server_id: serverId } : {};
            const response = await axios.get('/api/switches/statistics/', { params });
            setStatistics(response.data);
        } catch (error) {
            console.error('Error fetching statistics:', error);
        }
    };

    // 同步 Switch 資訊
    const handleSync = async () => {
        setLoading(true);
        try {
            const data = serverId !== 'all' ? { server_id: serverId } : {};
            const response = await axios.post('/api/switches/sync_from_leases/', data);
            
            message.success(
                `同步完成！創建 ${response.data.created} 個，更新 ${response.data.updated} 個 Switch`
            );
            
            // 重新載入數據
            fetchSwitches();
            fetchStatistics();
        } catch (error) {
            console.error('Error syncing switches:', error);
            message.error('同步失敗：' + (error.response?.data?.error || error.message));
        } finally {
            setLoading(false);
        }
    };

    // 查看 Switch 詳情
    const handleViewDetails = async (switchRecord) => {
        setSelectedSwitch(switchRecord);
        setModalVisible(true);
        setLoadingDevices(true);
        
        try {
            const response = await axios.get(`/api/switches/${switchRecord.id}/devices/`);
            setSwitchDevices(response.data);
        } catch (error) {
            console.error('Error fetching switch devices:', error);
            message.error('載入設備列表失敗');
        } finally {
            setLoadingDevices(false);
        }
    };

    useEffect(() => {
        fetchSwitches();
        fetchStatistics();
    }, [serverId]);

    // Switch 狀態標籤
    const renderStatusTag = (status) => {
        const statusConfig = {
            'active': { color: 'success', text: '活躍' },
            'inactive': { color: 'default', text: '非活躍' },
            'unknown': { color: 'warning', text: '未知' },
        };
        const config = statusConfig[status] || { color: 'default', text: status };
        return <Tag color={config.color}>{config.text}</Tag>;
    };

    // Switch 列表欄位定義
    const columns = [
        {
            title: 'Switch 名稱',
            dataIndex: 'name',
            key: 'name',
            render: (text, record) => text || <span style={{ color: '#999' }}>{record.remote_id}</span>,
        },
        {
            title: 'Remote ID',
            dataIndex: 'remote_id',
            key: 'remote_id',
            ellipsis: true,
        },
        {
            title: 'MAC 地址',
            dataIndex: 'mac_address',
            key: 'mac_address',
            render: (text) => text || '-',
        },
        {
            title: 'IP 地址',
            dataIndex: 'ip_address',
            key: 'ip_address',
            render: (text) => text || '-',
        },
        {
            title: '狀態',
            dataIndex: 'status',
            key: 'status',
            render: renderStatusTag,
        },
        {
            title: '連接設備',
            dataIndex: 'connected_devices',
            key: 'connected_devices',
            sorter: (a, b) => a.connected_devices - b.connected_devices,
            render: (count) => <Badge count={count} showZero color="#2196f3" />,
        },
        {
            title: '活動端口',
            dataIndex: 'active_ports',
            key: 'active_ports',
            render: (active, record) => `${active} / ${record.total_ports || '?'}`,
        },
        {
            title: '最後活動',
            dataIndex: 'last_seen',
            key: 'last_seen',
            render: (text) => new Date(text).toLocaleString('zh-TW'),
        },
        {
            title: '操作',
            key: 'action',
            render: (_, record) => (
                <Space>
                    <Button 
                        type="link" 
                        icon={<EyeOutlined />}
                        onClick={() => handleViewDetails(record)}
                    >
                        查看
                    </Button>
                </Space>
            ),
        },
    ];

    // 統計卡片
    const renderStatistics = () => {
        if (!statistics) return null;

        return (
            <Row gutter={[16, 16]} style={{ marginBottom: '24px' }}>
                <Col xs={24} sm={12} md={6}>
                    <Card>
                        <Statistic
                            title="總 Switch 數"
                            value={statistics.total_switches}
                            prefix={<ApartmentOutlined />}
                            valueStyle={{ color: '#2196f3' }}
                        />
                    </Card>
                </Col>
                <Col xs={24} sm={12} md={6}>
                    <Card>
                        <Statistic
                            title="活躍 Switch"
                            value={statistics.active_switches}
                            prefix={<ApiOutlined />}
                            valueStyle={{ color: '#52c41a' }}
                        />
                    </Card>
                </Col>
                <Col xs={24} sm={12} md={6}>
                    <Card>
                        <Statistic
                            title="連接設備總數"
                            value={statistics.total_devices}
                            prefix={<NodeIndexOutlined />}
                            valueStyle={{ color: '#1890ff' }}
                        />
                    </Card>
                </Col>
                <Col xs={24} sm={12} md={6}>
                    <Card>
                        <Statistic
                            title="活動端口"
                            value={statistics.active_ports}
                            suffix={`/ ${statistics.total_ports}`}
                            valueStyle={{ color: '#faad14' }}
                        />
                    </Card>
                </Col>
            </Row>
        );
    };

    // Switch 列表 Tab
    const renderListTab = () => (
        <div>
            {renderStatistics()}
            <Card
                title={
                    <Space>
                        <ApartmentOutlined />
                        <span>Switch 列表</span>
                    </Space>
                }
                extra={
                    <Space>
                        <Button 
                            icon={<SyncOutlined />} 
                            onClick={handleSync}
                            loading={loading}
                        >
                            同步 Switch
                        </Button>
                        <Button 
                            icon={<ReloadOutlined />} 
                            onClick={() => {
                                fetchSwitches();
                                fetchStatistics();
                            }}
                            loading={loading}
                        >
                            重新整理
                        </Button>
                    </Space>
                }
            >
                <Table
                    columns={columns}
                    dataSource={switches}
                    rowKey="id"
                    loading={loading}
                    pagination={{
                        pageSize: 10,
                        showSizeChanger: true,
                        showTotal: (total) => `共 ${total} 個 Switch`,
                    }}
                    locale={{
                        emptyText: (
                            <Empty
                                description="暫無 Switch 資料"
                                image={Empty.PRESENTED_IMAGE_SIMPLE}
                            >
                                <Button type="primary" icon={<SyncOutlined />} onClick={handleSync}>
                                    立即同步
                                </Button>
                            </Empty>
                        ),
                    }}
                />
            </Card>
        </div>
    );

    // Top Switch Tab
    const renderTopSwitchesTab = () => {
        if (!statistics || !statistics.top_switches) return <Empty />;

        const topColumns = [
            {
                title: '排名',
                key: 'rank',
                render: (_, __, index) => index + 1,
                width: 60,
            },
            {
                title: 'Switch 名稱',
                dataIndex: 'name',
                key: 'name',
            },
            {
                title: '狀態',
                dataIndex: 'status',
                key: 'status',
                render: renderStatusTag,
            },
            {
                title: '連接設備',
                dataIndex: 'connected_devices',
                key: 'connected_devices',
                sorter: (a, b) => a.connected_devices - b.connected_devices,
                defaultSortOrder: 'descend',
                render: (count) => <Badge count={count} showZero color="#2196f3" />,
            },
            {
                title: '活動端口',
                dataIndex: 'active_ports',
                key: 'active_ports',
            },
        ];

        return (
            <Card title="Top 10 連接設備最多的 Switch">
                <Table
                    columns={topColumns}
                    dataSource={statistics.top_switches}
                    rowKey="id"
                    pagination={false}
                />
            </Card>
        );
    };

    // Switch 詳情 Modal
    const renderDetailsModal = () => {
        if (!selectedSwitch) return null;

        return (
            <Modal
                title={
                    <Space>
                        <ApartmentOutlined />
                        <span>{selectedSwitch.name || selectedSwitch.remote_id}</span>
                    </Space>
                }
                open={modalVisible}
                onCancel={() => {
                    setModalVisible(false);
                    setSelectedSwitch(null);
                    setSwitchDevices(null);
                }}
                width={900}
                footer={[
                    <Button key="close" onClick={() => setModalVisible(false)}>
                        關閉
                    </Button>,
                ]}
            >
                <Descriptions bordered column={2} size="small" style={{ marginBottom: '24px' }}>
                    <Descriptions.Item label="Remote ID">
                        {selectedSwitch.remote_id}
                    </Descriptions.Item>
                    <Descriptions.Item label="狀態">
                        {renderStatusTag(selectedSwitch.status)}
                    </Descriptions.Item>
                    <Descriptions.Item label="MAC 地址">
                        {selectedSwitch.mac_address || '-'}
                    </Descriptions.Item>
                    <Descriptions.Item label="IP 地址">
                        {selectedSwitch.ip_address || '-'}
                    </Descriptions.Item>
                    <Descriptions.Item label="連接設備">
                        {selectedSwitch.connected_devices} 台
                    </Descriptions.Item>
                    <Descriptions.Item label="活動端口">
                        {selectedSwitch.active_ports} / {selectedSwitch.total_ports || '?'}
                    </Descriptions.Item>
                    <Descriptions.Item label="位置">
                        {selectedSwitch.location || '-'}
                    </Descriptions.Item>
                    <Descriptions.Item label="最後活動">
                        {new Date(selectedSwitch.last_seen).toLocaleString('zh-TW')}
                    </Descriptions.Item>
                </Descriptions>

                {loadingDevices ? (
                    <div style={{ textAlign: 'center', padding: '40px' }}>
                        <Spin tip="載入設備列表..." />
                    </div>
                ) : switchDevices ? (
                    <div>
                        <h4>連接設備列表（按端口分組）</h4>
                        {Object.keys(switchDevices.devices_by_port).length === 0 ? (
                            <Empty description="暫無設備" />
                        ) : (
                            Object.entries(switchDevices.devices_by_port).map(([port, devices]) => (
                                <Card 
                                    key={port} 
                                    size="small" 
                                    title={`端口: ${port}`}
                                    style={{ marginBottom: '16px' }}
                                >
                                    {devices.map((device, index) => (
                                        <div key={index} style={{ marginBottom: '8px' }}>
                                            <Tag color="blue">{device.ip_address}</Tag>
                                            <Tag>{device.mac_address}</Tag>
                                            {device.hostname && <Tag color="green">{device.hostname}</Tag>}
                                            <span style={{ color: '#999', fontSize: '12px' }}>
                                                {' '}({device.server_name})
                                            </span>
                                        </div>
                                    ))}
                                </Card>
                            ))
                        )}
                    </div>
                ) : null}
            </Modal>
        );
    };

    const tabItems = [
        {
            key: 'list',
            label: <span><ApartmentOutlined /> Switch 列表</span>,
            children: renderListTab(),
        },
        {
            key: 'top',
            label: <span><NodeIndexOutlined /> Top Switch</span>,
            children: renderTopSwitchesTab(),
        },
    ];

    return (
        <div>
            <Tabs 
                activeKey={activeTab} 
                onChange={setActiveTab}
                items={tabItems}
            />
            {renderDetailsModal()}
        </div>
    );
};

export default SwitchTab;
