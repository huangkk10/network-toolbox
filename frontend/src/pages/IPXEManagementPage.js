import React, { useState, useEffect } from 'react';
import { Card, Table, Button, Modal, Form, Input, Select, message, Space, Tag, Popconfirm, Statistic, Row, Col } from 'antd';
import { PlusOutlined, EditOutlined, DeleteOutlined, ReloadOutlined, SyncOutlined, CloudServerOutlined } from '@ant-design/icons';
import axios from 'axios';

const { TextArea } = Input;
const { Option } = Select;

const IPXEManagementPage = () => {
    const [servers, setServers] = useState([]);
    const [loading, setLoading] = useState(false);
    const [syncing, setSyncing] = useState({});
    const [modalVisible, setModalVisible] = useState(false);
    const [editingServer, setEditingServer] = useState(null);
    const [form] = Form.useForm();

    // 載入 IPXE 伺服器列表
    const fetchServers = async () => {
        setLoading(true);
        try {
            const response = await axios.get('/api/ipxe-servers/');
            const data = response.data.results || response.data;
            setServers(Array.isArray(data) ? data : []);
        } catch (error) {
            console.error('Error fetching servers:', error);
            message.error('載入伺服器列表失敗：' + (error.response?.data?.message || error.message));
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchServers();
    }, []);

    // 開啟新增/編輯對話框
    const handleAdd = () => {
        setEditingServer(null);
        form.resetFields();
        setModalVisible(true);
    };

    const handleEdit = (record) => {
        setEditingServer(record);
        form.setFieldsValue(record);
        setModalVisible(true);
    };

    // 儲存（新增或更新）
    const handleSubmit = async (values) => {
        try {
            if (editingServer) {
                // 更新
                await axios.patch(`/api/ipxe-servers/${editingServer.id}/`, values);
                message.success('更新成功！');
            } else {
                // 新增
                await axios.post('/api/ipxe-servers/', values);
                message.success('新增成功！');
            }
            setModalVisible(false);
            fetchServers();
        } catch (error) {
            console.error('Error saving server:', error);
            message.error('儲存失敗：' + (error.response?.data?.message || error.message));
        }
    };

    // 刪除
    const handleDelete = async (id) => {
        try {
            await axios.delete(`/api/ipxe-servers/${id}/`);
            message.success('刪除成功！');
            fetchServers();
        } catch (error) {
            console.error('Error deleting server:', error);
            message.error('刪除失敗：' + (error.response?.data?.message || error.message));
        }
    };

    // 手動同步日誌
    const handleSync = async (serverId) => {
        setSyncing(prev => ({ ...prev, [serverId]: true }));
        try {
            const response = await axios.post(`/api/ipxe-servers/${serverId}/sync-logs/`, {
                limit: 1000
            });
            message.success(
                `同步成功！MAC 日誌: ${response.data.mac_logs_collected} 條，` +
                `BOOT 日誌: ${response.data.boot_logs_collected} 條`
            );
            fetchServers();
        } catch (error) {
            console.error('Error syncing logs:', error);
            message.error('同步失敗：' + (error.response?.data?.error || error.message));
        } finally {
            setSyncing(prev => ({ ...prev, [serverId]: false }));
        }
    };

    // 表格欄位定義
    const columns = [
        {
            title: 'ID',
            dataIndex: 'id',
            key: 'id',
            width: 60,
        },
        {
            title: '伺服器名稱',
            dataIndex: 'name',
            key: 'name',
            width: 150,
        },
        {
            title: 'IP 位址',
            dataIndex: 'ip_address',
            key: 'ip_address',
            width: 140,
        },
        {
            title: '狀態',
            dataIndex: 'status',
            key: 'status',
            width: 90,
            render: (status) => {
                const colors = {
                    online: 'success',
                    offline: 'default',
                    syncing: 'processing',
                };
                const labels = {
                    online: '在線',
                    offline: '離線',
                    syncing: '同步中',
                };
                return <Tag color={colors[status]}>{labels[status] || status}</Tag>;
            },
        },
        {
            title: 'MAC 容器',
            dataIndex: 'docker_container_mac',
            key: 'docker_container_mac',
            width: 140,
            render: (name) => <Tag color="blue">{name}</Tag>,
        },
        {
            title: 'BOOT 容器',
            dataIndex: 'docker_container_ipxe',
            key: 'docker_container_ipxe',
            width: 120,
            render: (name) => <Tag color="cyan">{name}</Tag>,
        },
        {
            title: '最後同步',
            dataIndex: 'last_sync_at',
            key: 'last_sync_at',
            width: 160,
            render: (time) => {
                if (!time) return <span style={{ color: '#999' }}>從未同步</span>;
                const date = new Date(time);
                return date.toLocaleString('zh-TW', {
                    year: 'numeric',
                    month: '2-digit',
                    day: '2-digit',
                    hour: '2-digit',
                    minute: '2-digit',
                });
            },
        },
        {
            title: '操作',
            key: 'action',
            width: 200,
            fixed: 'right',
            render: (_, record) => (
                <Space>
                    <Button
                        type="link"
                        size="small"
                        icon={<SyncOutlined spin={syncing[record.id]} />}
                        onClick={() => handleSync(record.id)}
                        loading={syncing[record.id]}
                    >
                        同步
                    </Button>
                    <Button
                        type="link"
                        size="small"
                        icon={<EditOutlined />}
                        onClick={() => handleEdit(record)}
                    >
                        編輯
                    </Button>
                    <Popconfirm
                        title="確定要刪除這個伺服器嗎？"
                        description="刪除後相關日誌也會一併刪除"
                        onConfirm={() => handleDelete(record.id)}
                        okText="確定"
                        cancelText="取消"
                    >
                        <Button type="link" size="small" danger icon={<DeleteOutlined />}>
                            刪除
                        </Button>
                    </Popconfirm>
                </Space>
            ),
        },
    ];

    // 計算統計資料
    const totalServers = servers.length;
    const onlineServers = servers.filter(s => s.status === 'online').length;
    const totalRequests = servers.reduce((sum, s) => sum + (s.total_requests_today || 0), 0);
    const totalMacRegs = servers.reduce((sum, s) => sum + (s.mac_registrations || 0), 0);

    return (
        <div style={{ padding: '24px' }}>
            {/* 統計卡片 */}
            <Row gutter={[16, 16]} style={{ marginBottom: '24px' }}>
                <Col xs={24} sm={12} md={6}>
                    <Card>
                        <Statistic
                            title="總伺服器數"
                            value={totalServers}
                            prefix={<CloudServerOutlined />}
                            valueStyle={{ color: '#1890ff' }}
                        />
                    </Card>
                </Col>
                <Col xs={24} sm={12} md={6}>
                    <Card>
                        <Statistic
                            title="在線伺服器"
                            value={onlineServers}
                            suffix={`/ ${totalServers}`}
                            valueStyle={{ color: '#52c41a' }}
                        />
                    </Card>
                </Col>
                <Col xs={24} sm={12} md={6}>
                    <Card>
                        <Statistic
                            title="今日總請求"
                            value={totalRequests}
                            valueStyle={{ color: '#faad14' }}
                        />
                    </Card>
                </Col>
                <Col xs={24} sm={12} md={6}>
                    <Card>
                        <Statistic
                            title="MAC 註冊數"
                            value={totalMacRegs}
                            valueStyle={{ color: '#722ed1' }}
                        />
                    </Card>
                </Col>
            </Row>

            {/* 伺服器列表 */}
            <Card
                title="IPXE 伺服器管理"
                extra={
                    <Space>
                        <Button icon={<ReloadOutlined />} onClick={fetchServers}>
                            重新整理
                        </Button>
                        <Button type="primary" icon={<PlusOutlined />} onClick={handleAdd}>
                            新增 IPXE Server
                        </Button>
                    </Space>
                }
            >
                <Table
                    columns={columns}
                    dataSource={servers}
                    rowKey="id"
                    loading={loading}
                    scroll={{ x: 1200 }}
                    pagination={{
                        pageSize: 10,
                        showSizeChanger: true,
                        showTotal: (total) => `共 ${total} 筆`,
                    }}
                />
            </Card>

            {/* 新增/編輯對話框 */}
            <Modal
                title={editingServer ? '編輯 IPXE Server' : '新增 IPXE Server'}
                open={modalVisible}
                onCancel={() => setModalVisible(false)}
                onOk={() => form.submit()}
                okText="儲存"
                cancelText="取消"
                width={700}
            >
                <Form
                    form={form}
                    layout="vertical"
                    onFinish={handleSubmit}
                >
                    <Form.Item
                        label="伺服器名稱"
                        name="name"
                        rules={[{ required: true, message: '請輸入伺服器名稱' }]}
                    >
                        <Input placeholder="例如：IPXE Server 50" />
                    </Form.Item>

                    <Form.Item
                        label="IP 位址"
                        name="ip_address"
                        rules={[
                            { required: true, message: '請輸入 IP 位址' },
                            { pattern: /^(\d{1,3}\.){3}\d{1,3}$/, message: '請輸入有效的 IP 位址' },
                        ]}
                    >
                        <Input placeholder="例如：10.250.50.2" />
                    </Form.Item>

                    <Form.Item
                        label="狀態"
                        name="status"
                        initialValue="offline"
                    >
                        <Select>
                            <Option value="online">在線</Option>
                            <Option value="offline">離線</Option>
                        </Select>
                    </Form.Item>

                    <Form.Item
                        label="描述"
                        name="description"
                    >
                        <TextArea rows={3} placeholder="伺服器的詳細說明..." />
                    </Form.Item>

                    {/* SSH 連線設定 */}
                    <h4 style={{ marginTop: '16px', marginBottom: '16px', borderBottom: '1px solid #f0f0f0', paddingBottom: '8px' }}>
                        SSH 連線設定
                    </h4>

                    <Row gutter={16}>
                        <Col span={12}>
                            <Form.Item
                                label="SSH 使用者名稱"
                                name="ssh_username"
                                initialValue="rvt"
                                rules={[{ required: true, message: '請輸入 SSH 使用者名稱' }]}
                            >
                                <Input placeholder="預設：rvt" />
                            </Form.Item>
                        </Col>
                        <Col span={12}>
                            <Form.Item
                                label="SSH 連接埠"
                                name="ssh_port"
                                initialValue={22}
                                rules={[{ required: true, message: '請輸入 SSH 連接埠' }]}
                            >
                                <Input type="number" placeholder="預設：22" />
                            </Form.Item>
                        </Col>
                    </Row>

                    <Form.Item
                        label="SSH 密碼"
                        name="ssh_password"
                        rules={[{ required: true, message: '請輸入 SSH 密碼' }]}
                    >
                        <Input.Password placeholder="SSH 登入密碼" />
                    </Form.Item>

                    {/* Docker 容器設定 */}
                    <h4 style={{ marginTop: '16px', marginBottom: '16px', borderBottom: '1px solid #f0f0f0', paddingBottom: '8px' }}>
                        Docker 容器設定
                    </h4>

                    <Form.Item
                        label="MAC 管理容器名稱"
                        name="docker_container_mac"
                        initialValue="ipxe_mac-flask"
                        rules={[{ required: true, message: '請輸入 MAC 容器名稱' }]}
                        tooltip="管理 MAC 地址 BOOT 旗標的容器"
                    >
                        <Input placeholder="預設：ipxe_mac-flask" />
                    </Form.Item>

                    <Form.Item
                        label="IPXE 開機容器名稱"
                        name="docker_container_ipxe"
                        initialValue="ipxe"
                        rules={[{ required: true, message: '請輸入 IPXE 容器名稱' }]}
                        tooltip="提供 IPXE 開機檔案的 HTTP 服務容器"
                    >
                        <Input placeholder="預設：ipxe" />
                    </Form.Item>
                </Form>
            </Modal>
        </div>
    );
};

export default IPXEManagementPage;
