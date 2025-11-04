import React, { useState, useEffect } from 'react';
import { Card, Table, Button, Modal, Form, Input, Select, message, Space, Tag, Popconfirm, Tooltip } from 'antd';
import { PlusOutlined, EditOutlined, DeleteOutlined, ReloadOutlined, SyncOutlined, ApiOutlined } from '@ant-design/icons';
import axios from 'axios';

const { TextArea } = Input;
const { Option } = Select;

const RVTManagementPage = () => {
    const [servers, setServers] = useState([]);
    const [loading, setLoading] = useState(false);
    const [modalVisible, setModalVisible] = useState(false);
    const [editingServer, setEditingServer] = useState(null);
    const [syncing, setSyncing] = useState({});
    const [testing, setTesting] = useState({});
    const [form] = Form.useForm();

    // 載入 Jenkins 伺服器列表
    const fetchServers = async () => {
        setLoading(true);
        try {
            const response = await axios.get('/api/jenkins-servers/');
            const data = response.data.results || response.data;
            setServers(Array.isArray(data) ? data : []);
            message.success('載入成功');
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

    // 測試連接
    const handleTestConnection = async (record) => {
        setTesting({ ...testing, [record.id]: true });
        try {
            const response = await axios.post(`/api/jenkins-servers/${record.id}/test_connection/`);
            if (response.data.success) {
                message.success(`連接成功！Jobs: ${response.data.server_info?.jobs_count || 0}`);
                fetchServers(); // 刷新列表以更新狀態
            } else {
                message.error('連接失敗：' + response.data.message);
            }
        } catch (error) {
            console.error('Error testing connection:', error);
            message.error('測試連接失敗：' + (error.response?.data?.message || error.message));
        } finally {
            setTesting({ ...testing, [record.id]: false });
        }
    };

    // 同步 Jobs
    const handleSyncJobs = async (record) => {
        setSyncing({ ...syncing, [record.id]: true });
        try {
            const response = await axios.post(`/api/jenkins-servers/${record.id}/sync_jobs/`);
            if (response.data.success) {
                message.success(
                    `同步完成！新增 ${response.data.created}，更新 ${response.data.updated}，共 ${response.data.total} 個 Jobs`,
                    5
                );
                fetchServers(); // 刷新列表
            } else {
                message.error('同步失敗：' + response.data.message);
            }
        } catch (error) {
            console.error('Error syncing jobs:', error);
            message.error('同步失敗：' + (error.response?.data?.message || error.message));
        } finally {
            setSyncing({ ...syncing, [record.id]: false });
        }
    };

    // 儲存（新增或更新）
    const handleSubmit = async (values) => {
        try {
            if (editingServer) {
                // 更新
                await axios.put(`/api/jenkins-servers/${editingServer.id}/`, values);
                message.success('更新成功！');
            } else {
                // 新增 Jenkins Server
                const response = await axios.post('/api/jenkins-servers/', values);
                message.success('新增成功！');
                
                // 提示用戶可以進行初始同步
                const serverId = response.data.id;
                Modal.confirm({
                    title: '是否立即同步 Jobs？',
                    content: '新增的 Jenkins 伺服器需要同步 Jobs 才能查看數據。',
                    okText: '立即同步',
                    cancelText: '稍後手動同步',
                    onOk: async () => {
                        await handleSyncJobs({ id: serverId });
                    }
                });
            }
            
            setModalVisible(false);
            form.resetFields();
            fetchServers();
        } catch (error) {
            console.error('Error saving server:', error);
            message.error('儲存失敗：' + (error.response?.data?.message || error.message));
        }
    };

    // 刪除伺服器
    const handleDelete = async (id) => {
        try {
            await axios.delete(`/api/jenkins-servers/${id}/`);
            message.success('刪除成功！');
            fetchServers();
        } catch (error) {
            console.error('Error deleting server:', error);
            message.error('刪除失敗：' + (error.response?.data?.message || error.message));
        }
    };

    // 狀態標籤
    const renderStatusTag = (status) => {
        const statusMap = {
            online: { color: 'success', text: 'Online' },
            offline: { color: 'error', text: 'Offline' },
            unreachable: { color: 'default', text: 'Unreachable' },
        };
        const config = statusMap[status] || { color: 'default', text: status };
        return <Tag color={config.color}>{config.text}</Tag>;
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
            title: '名稱',
            dataIndex: 'name',
            key: 'name',
            width: 200,
        },
        {
            title: 'URL',
            dataIndex: 'url',
            key: 'url',
            render: (text) => (
                <a href={text} target="_blank" rel="noopener noreferrer">
                    {text}
                </a>
            ),
        },
        {
            title: '狀態',
            dataIndex: 'status',
            key: 'status',
            width: 100,
            render: renderStatusTag,
        },
        {
            title: 'Jobs 數量',
            dataIndex: 'jobs_count',
            key: 'jobs_count',
            width: 100,
            render: (count) => count || 0,
        },
        {
            title: '最後同步',
            dataIndex: 'last_sync_at',
            key: 'last_sync_at',
            width: 180,
            render: (text) => text ? new Date(text).toLocaleString('zh-TW') : '-',
        },
        {
            title: '操作',
            key: 'action',
            width: 280,
            render: (_, record) => (
                <Space size="small">
                    <Tooltip title="測試連接">
                        <Button
                            type="link"
                            size="small"
                            icon={<ApiOutlined />}
                            loading={testing[record.id]}
                            onClick={() => handleTestConnection(record)}
                        >
                            測試
                        </Button>
                    </Tooltip>
                    <Tooltip title="同步 Jobs">
                        <Button
                            type="link"
                            size="small"
                            icon={<SyncOutlined />}
                            loading={syncing[record.id]}
                            onClick={() => handleSyncJobs(record)}
                        >
                            同步
                        </Button>
                    </Tooltip>
                    <Button
                        type="link"
                        size="small"
                        icon={<EditOutlined />}
                        onClick={() => handleEdit(record)}
                    >
                        編輯
                    </Button>
                    <Popconfirm
                        title="確定要刪除此伺服器嗎？"
                        description="此操作將同時刪除所有相關的 Jobs 和 Builds 數據！"
                        onConfirm={() => handleDelete(record.id)}
                        okText="確定"
                        cancelText="取消"
                    >
                        <Button
                            type="link"
                            size="small"
                            danger
                            icon={<DeleteOutlined />}
                        >
                            刪除
                        </Button>
                    </Popconfirm>
                </Space>
            ),
        },
    ];

    return (
        <div style={{ padding: '24px' }}>
            <Card
                title="RVT 管理（Jenkins Server）"
                extra={
                    <Space>
                        <Button
                            icon={<ReloadOutlined />}
                            onClick={fetchServers}
                            loading={loading}
                        >
                            刷新
                        </Button>
                        <Button
                            type="primary"
                            icon={<PlusOutlined />}
                            onClick={handleAdd}
                        >
                            新增 Jenkins 伺服器
                        </Button>
                    </Space>
                }
            >
                <Table
                    columns={columns}
                    dataSource={servers}
                    rowKey="id"
                    loading={loading}
                    pagination={{
                        pageSize: 10,
                        showSizeChanger: true,
                        showTotal: (total) => `共 ${total} 個伺服器`,
                    }}
                    size="middle"
                />
            </Card>

            {/* 新增/編輯對話框 */}
            <Modal
                title={editingServer ? '編輯 Jenkins 伺服器' : '新增 Jenkins 伺服器'}
                open={modalVisible}
                onOk={() => form.submit()}
                onCancel={() => {
                    setModalVisible(false);
                    form.resetFields();
                }}
                width={600}
                okText="儲存"
                cancelText="取消"
            >
                <Form
                    form={form}
                    layout="vertical"
                    onFinish={handleSubmit}
                >
                    <Form.Item
                        label="伺服器名稱"
                        name="name"
                        rules={[
                            { required: true, message: '請輸入伺服器名稱' }
                        ]}
                    >
                        <Input placeholder="例如：RVT Production Server" />
                    </Form.Item>

                    <Form.Item
                        label="Jenkins URL"
                        name="url"
                        rules={[
                            { required: true, message: '請輸入 Jenkins URL' },
                            { type: 'url', message: '請輸入有效的 URL' }
                        ]}
                        extra="例如：http://10.252.170.188:8080"
                    >
                        <Input placeholder="http://10.252.170.188:8080" />
                    </Form.Item>

                    <Form.Item
                        label="使用者名稱"
                        name="username"
                        extra="如果 Jenkins 需要認證，請提供使用者名稱"
                    >
                        <Input placeholder="admin（選填）" />
                    </Form.Item>

                    <Form.Item
                        label="API Token"
                        name="api_token"
                        extra="如果 Jenkins 需要認證，請提供 API Token（在 Jenkins 使用者設定中生成）"
                    >
                        <Input.Password placeholder="API Token（選填）" />
                    </Form.Item>

                    <Form.Item
                        label="描述"
                        name="description"
                    >
                        <TextArea
                            rows={3}
                            placeholder="此 Jenkins 伺服器的說明（選填）"
                        />
                    </Form.Item>

                    <Form.Item
                        label="狀態"
                        name="status"
                        initialValue="offline"
                    >
                        <Select>
                            <Option value="online">Online</Option>
                            <Option value="offline">Offline</Option>
                            <Option value="unreachable">Unreachable</Option>
                        </Select>
                    </Form.Item>

                    <Form.Item
                        label="是否啟用"
                        name="is_active"
                        valuePropName="checked"
                        initialValue={true}
                    >
                        <Select>
                            <Option value={true}>啟用</Option>
                            <Option value={false}>停用</Option>
                        </Select>
                    </Form.Item>
                </Form>
            </Modal>
        </div>
    );
};

export default RVTManagementPage;
