import React, { useState, useEffect } from 'react';
import { Card, Table, Button, Modal, Form, Input, Select, message, Space, Tag, Popconfirm } from 'antd';
import { PlusOutlined, EditOutlined, DeleteOutlined, ReloadOutlined } from '@ant-design/icons';
import axios from 'axios';

const { TextArea } = Input;
const { Option } = Select;

const DHCPServerManagementPage = () => {
    const [servers, setServers] = useState([]);
    const [loading, setLoading] = useState(false);
    const [modalVisible, setModalVisible] = useState(false);
    const [editingServer, setEditingServer] = useState(null);
    const [form] = Form.useForm();

    // 載入 DHCP 伺服器列表
    const fetchServers = async () => {
        setLoading(true);
        try {
            const response = await axios.get('/api/dhcp-servers/');
            // 處理分頁格式：{count, next, previous, results}
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
                await axios.put(`/api/dhcp-servers/${editingServer.id}/`, values);
                message.success('更新成功！');
            } else {
                // 新增 DHCP Server
                const response = await axios.post('/api/dhcp-servers/', values);
                message.success('新增成功！');
                
                // 顯示自動同步結果
                if (response.data.auto_sync) {
                    const sync = response.data.auto_sync;
                    
                    // 顯示同步統計
                    if (sync.scopes && sync.scopes.success) {
                        const stats = sync.scopes.stats;
                        message.success(
                            `✓ 已同步 ${stats.found || 0} 個 Scope（新增 ${stats.created || 0}，更新 ${stats.updated || 0}）`, 
                            5
                        );
                    }
                    
                    if (sync.leases && sync.leases.success) {
                        const stats = sync.leases.stats;
                        message.success(
                            `✓ 已同步 ${stats.total || 0} 筆租約（新增 ${stats.created || 0}，更新 ${stats.updated || 0}）`, 
                            5
                        );
                    }
                    
                    if (sync.logs && sync.logs.success) {
                        const stats = sync.logs.stats;
                        message.success(
                            `✓ 已同步 ${stats.created || 0} 條日誌（跳過 ${stats.skipped || 0} 條重複）`, 
                            5
                        );
                    }
                    
                    // 如果有錯誤，顯示警告
                    if (sync.errors && sync.errors.length > 0) {
                        message.warning(
                            `部分數據同步失敗，但 Server 已創建成功。請檢查日誌或手動同步。`, 
                            8
                        );
                        console.warn('同步錯誤:', sync.errors);
                    }
                    
                    // 如果全部失敗，顯示提示
                    if (!sync.scopes.success && !sync.leases.success && !sync.logs.success) {
                        message.warning(
                            `Server 已創建，但自動同步失敗。請檢查 SSH 連線設定後手動同步。`, 
                            8
                        );
                    }
                }
            }
            setModalVisible(false);
            fetchServers();
        } catch (error) {
            console.error('Error saving server:', error);
            message.error('儲存失敗：' + (error.response?.data?.error || error.message));
        }
    };

    // 刪除
    const handleDelete = async (id) => {
        try {
            await axios.delete(`/api/dhcp-servers/${id}/`);
            message.success('刪除成功！');
            fetchServers();
        } catch (error) {
            console.error('Error deleting server:', error);
            message.error('刪除失敗：' + error.message);
        }
    };

    // 表格欄位定義
    const columns = [
        {
            title: 'ID',
            dataIndex: 'id',
            key: 'id',
            width: 80,
        },
        {
            title: '伺服器名稱',
            dataIndex: 'name',
            key: 'name',
        },
        {
            title: 'IP 位址',
            dataIndex: 'ip_address',
            key: 'ip_address',
        },
        {
            title: '狀態',
            dataIndex: 'status',
            key: 'status',
            render: (status) => {
                const colors = {
                    online: 'success',
                    offline: 'default',
                    warning: 'warning',
                };
                const labels = {
                    online: 'Online',
                    offline: 'Offline',
                    warning: 'Warning',
                };
                return <Tag color={colors[status]}>{labels[status]}</Tag>;
            },
        },
        {
            title: '池使用率',
            dataIndex: 'pool_usage',
            key: 'pool_usage',
            render: (usage) => `${usage.toFixed(1)}%`,
        },
        {
            title: '總租約數',
            dataIndex: 'total_leases',
            key: 'total_leases',
        },
        {
            title: '活動租約數',
            dataIndex: 'active_leases',
            key: 'active_leases',
        },
        {
            title: '操作',
            key: 'action',
            width: 150,
            render: (_, record) => (
                <Space>
                    <Button
                        type="link"
                        icon={<EditOutlined />}
                        onClick={() => handleEdit(record)}
                    >
                        編輯
                    </Button>
                    <Popconfirm
                        title="確定要刪除這個伺服器嗎？"
                        onConfirm={() => handleDelete(record.id)}
                        okText="確定"
                        cancelText="取消"
                    >
                        <Button type="link" danger icon={<DeleteOutlined />}>
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
                title="DHCP Server 管理"
                extra={
                    <Space>
                        <Button icon={<ReloadOutlined />} onClick={fetchServers}>
                            重新整理
                        </Button>
                        <Button type="primary" icon={<PlusOutlined />} onClick={handleAdd}>
                            新增 DHCP Server
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
                        showTotal: (total) => `共 ${total} 筆`,
                    }}
                />
            </Card>

            {/* 新增/編輯對話框 */}
            <Modal
                title={editingServer ? '編輯 DHCP Server' : '新增 DHCP Server'}
                open={modalVisible}
                onCancel={() => setModalVisible(false)}
                onOk={() => form.submit()}
                okText="儲存"
                cancelText="取消"
                width={600}
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
                        <Input placeholder="例如：主要 DHCP 伺服器" />
                    </Form.Item>

                    <Form.Item
                        label="IP 位址"
                        name="ip_address"
                        rules={[
                            { required: true, message: '請輸入 IP 位址' },
                            { pattern: /^(\d{1,3}\.){3}\d{1,3}$/, message: '請輸入有效的 IP 位址' },
                        ]}
                    >
                        <Input placeholder="例如：192.168.1.1" />
                    </Form.Item>

                    <Form.Item
                        label="狀態"
                        name="status"
                        initialValue="offline"
                    >
                        <Select>
                            <Option value="online">Online</Option>
                            <Option value="offline">Offline</Option>
                            <Option value="warning">Warning</Option>
                        </Select>
                    </Form.Item>

                    <Form.Item
                        label="描述"
                        name="description"
                    >
                        <TextArea rows={3} placeholder="伺服器的詳細說明..." />
                    </Form.Item>

                    {/* SSH 連線設定 */}
                    <h4 style={{ marginTop: '16px', marginBottom: '16px' }}>SSH 連線設定</h4>

                    <Form.Item
                        label="SSH 連接埠"
                        name="ssh_port"
                        initialValue={22}
                        rules={[{ required: true, message: '請輸入 SSH 連接埠' }]}
                    >
                        <Input type="number" placeholder="預設：22" />
                    </Form.Item>

                    <Form.Item
                        label="SSH 使用者名稱"
                        name="ssh_username"
                        initialValue="Administrator"
                        rules={[{ required: true, message: '請輸入 SSH 使用者名稱' }]}
                    >
                        <Input placeholder="Windows Server 通常使用 Administrator" />
                    </Form.Item>

                    <Form.Item
                        label="SSH 密碼"
                        name="ssh_password"
                        rules={[{ required: true, message: '請輸入 SSH 密碼' }]}
                    >
                        <Input.Password placeholder="SSH 登入密碼" />
                    </Form.Item>

                    <Form.Item
                        label="DHCP Leases 檔案路徑"
                        name="dhcp_leases_path"
                        initialValue="C:\\Windows\\System32\\dhcp\\dhcp.mdb"
                        tooltip="Windows DHCP Server 的租約資料庫路徑"
                    >
                        <Input placeholder="Windows: C:\Windows\System32\dhcp\dhcp.mdb" />
                    </Form.Item>

                    <Form.Item
                        label="DHCP Config 檔案路徑"
                        name="dhcp_config_path"
                        initialValue="C:\\Windows\\System32\\dhcp\\dhcpd.conf"
                        tooltip="DHCP 設定檔路徑（選填）"
                    >
                        <Input placeholder="Windows: C:\Windows\System32\dhcp\dhcpd.conf" />
                    </Form.Item>
                </Form>
            </Modal>
        </div>
    );
};

export default DHCPServerManagementPage;
