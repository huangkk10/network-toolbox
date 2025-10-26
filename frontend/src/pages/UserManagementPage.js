import React, { useState, useEffect } from 'react';
import { Card, Table, Button, Modal, Form, Input, Switch, message, Space, Tag, Popconfirm } from 'antd';
import { UserOutlined, PlusOutlined, EditOutlined, DeleteOutlined, KeyOutlined } from '@ant-design/icons';
import axios from 'axios';

const UserManagementPage = () => {
    const [users, setUsers] = useState([]);
    const [loading, setLoading] = useState(false);
    const [modalVisible, setModalVisible] = useState(false);
    const [passwordModalVisible, setPasswordModalVisible] = useState(false);
    const [editingUser, setEditingUser] = useState(null);
    const [form] = Form.useForm();
    const [passwordForm] = Form.useForm();

    useEffect(() => {
        fetchUsers();
    }, []);

    const fetchUsers = async () => {
        setLoading(true);
        try {
            const response = await axios.get('/api/users/');
            // DRF 分頁格式：{count, next, previous, results}
            const userData = response.data.results || response.data;
            setUsers(Array.isArray(userData) ? userData : [userData]);
        } catch (error) {
            message.error('獲取用戶列表失敗');
            console.error('Error fetching users:', error);
        } finally {
            setLoading(false);
        }
    };

    const handleAdd = () => {
        setEditingUser(null);
        form.resetFields();
        setModalVisible(true);
    };

    const handleEdit = (record) => {
        setEditingUser(record);
        form.setFieldsValue({
            username: record.username,
            email: record.email,
            first_name: record.first_name,
            last_name: record.last_name,
            is_active: record.is_active,
            is_staff: record.is_staff,
            is_superuser: record.is_superuser,
        });
        setModalVisible(true);
    };

    const handleDelete = async (id) => {
        try {
            await axios.delete(`/api/users/${id}/`);
            message.success('用戶刪除成功');
            fetchUsers();
        } catch (error) {
            message.error('刪除用戶失敗');
            console.error('Error deleting user:', error);
        }
    };

    const handleResetPassword = (record) => {
        setEditingUser(record);
        passwordForm.resetFields();
        setPasswordModalVisible(true);
    };

    const handleSubmit = async (values) => {
        try {
            if (editingUser) {
                await axios.put(`/api/users/${editingUser.id}/`, values);
                message.success('用戶更新成功');
            } else {
                await axios.post('/api/users/', values);
                message.success('用戶創建成功');
            }
            setModalVisible(false);
            form.resetFields();
            fetchUsers();
        } catch (error) {
            message.error(editingUser ? '更新用戶失敗' : '創建用戶失敗');
            console.error('Error saving user:', error);
        }
    };

    const handlePasswordSubmit = async (values) => {
        try {
            await axios.post(`/api/users/${editingUser.id}/reset_password/`, {
                password: values.password
            });
            message.success('密碼重設成功');
            setPasswordModalVisible(false);
            passwordForm.resetFields();
        } catch (error) {
            message.error('密碼重設失敗');
            console.error('Error resetting password:', error);
        }
    };

    const columns = [
        {
            title: 'ID',
            dataIndex: 'id',
            key: 'id',
            width: 80,
        },
        {
            title: '用戶名',
            dataIndex: 'username',
            key: 'username',
        },
        {
            title: 'Email',
            dataIndex: 'email',
            key: 'email',
        },
        {
            title: '姓名',
            key: 'name',
            render: (_, record) => `${record.first_name || ''} ${record.last_name || ''}`.trim() || '-',
        },
        {
            title: '狀態',
            key: 'status',
            render: (_, record) => (
                <Space>
                    {record.is_active && <Tag color="green">啟用</Tag>}
                    {!record.is_active && <Tag color="red">停用</Tag>}
                    {record.is_superuser && <Tag color="purple">超級管理員</Tag>}
                    {record.is_staff && !record.is_superuser && <Tag color="blue">管理員</Tag>}
                </Space>
            ),
        },
        {
            title: '加入時間',
            dataIndex: 'date_joined',
            key: 'date_joined',
            render: (text) => new Date(text).toLocaleString('zh-TW'),
        },
        {
            title: '操作',
            key: 'action',
            render: (_, record) => (
                <Space>
                    <Button
                        type="link"
                        icon={<EditOutlined />}
                        onClick={() => handleEdit(record)}
                    >
                        編輯
                    </Button>
                    <Button
                        type="link"
                        icon={<KeyOutlined />}
                        onClick={() => handleResetPassword(record)}
                    >
                        重設密碼
                    </Button>
                    <Popconfirm
                        title="確定要刪除此用戶嗎？"
                        onConfirm={() => handleDelete(record.id)}
                        okText="確定"
                        cancelText="取消"
                    >
                        <Button
                            type="link"
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
                title={
                    <span>
                        <UserOutlined style={{ marginRight: '8px' }} />
                        用戶管理
                    </span>
                }
                extra={
                    <Button
                        type="primary"
                        icon={<PlusOutlined />}
                        onClick={handleAdd}
                    >
                        新增用戶
                    </Button>
                }
            >
                <Table
                    columns={columns}
                    dataSource={users}
                    rowKey="id"
                    loading={loading}
                    pagination={{
                        pageSize: 10,
                        showSizeChanger: true,
                        showTotal: (total) => `共 ${total} 個用戶`,
                    }}
                />
            </Card>

            {/* 新增/編輯用戶 Modal */}
            <Modal
                title={editingUser ? '編輯用戶' : '新增用戶'}
                open={modalVisible}
                onCancel={() => {
                    setModalVisible(false);
                    form.resetFields();
                }}
                onOk={() => form.submit()}
                width={600}
            >
                <Form
                    form={form}
                    layout="vertical"
                    onFinish={handleSubmit}
                >
                    <Form.Item
                        name="username"
                        label="用戶名"
                        rules={[{ required: true, message: '請輸入用戶名' }]}
                    >
                        <Input placeholder="請輸入用戶名" disabled={editingUser !== null} />
                    </Form.Item>

                    {!editingUser && (
                        <Form.Item
                            name="password"
                            label="密碼"
                            rules={[{ required: true, message: '請輸入密碼' }]}
                        >
                            <Input.Password placeholder="請輸入密碼" />
                        </Form.Item>
                    )}

                    <Form.Item
                        name="email"
                        label="Email"
                        rules={[
                            { type: 'email', message: '請輸入有效的 Email' },
                        ]}
                    >
                        <Input placeholder="請輸入 Email" />
                    </Form.Item>

                    <Form.Item
                        name="first_name"
                        label="名字"
                    >
                        <Input placeholder="請輸入名字" />
                    </Form.Item>

                    <Form.Item
                        name="last_name"
                        label="姓氏"
                    >
                        <Input placeholder="請輸入姓氏" />
                    </Form.Item>

                    <Form.Item
                        name="is_active"
                        label="啟用狀態"
                        valuePropName="checked"
                        initialValue={true}
                    >
                        <Switch checkedChildren="啟用" unCheckedChildren="停用" />
                    </Form.Item>

                    <Form.Item
                        name="is_staff"
                        label="管理員權限"
                        valuePropName="checked"
                        initialValue={false}
                    >
                        <Switch checkedChildren="是" unCheckedChildren="否" />
                    </Form.Item>

                    <Form.Item
                        name="is_superuser"
                        label="超級管理員"
                        valuePropName="checked"
                        initialValue={false}
                    >
                        <Switch checkedChildren="是" unCheckedChildren="否" />
                    </Form.Item>
                </Form>
            </Modal>

            {/* 重設密碼 Modal */}
            <Modal
                title="重設密碼"
                open={passwordModalVisible}
                onCancel={() => {
                    setPasswordModalVisible(false);
                    passwordForm.resetFields();
                }}
                onOk={() => passwordForm.submit()}
            >
                <Form
                    form={passwordForm}
                    layout="vertical"
                    onFinish={handlePasswordSubmit}
                >
                    <Form.Item
                        name="password"
                        label="新密碼"
                        rules={[{ required: true, message: '請輸入新密碼' }]}
                    >
                        <Input.Password placeholder="請輸入新密碼" />
                    </Form.Item>

                    <Form.Item
                        name="confirm_password"
                        label="確認密碼"
                        dependencies={['password']}
                        rules={[
                            { required: true, message: '請確認密碼' },
                            ({ getFieldValue }) => ({
                                validator(_, value) {
                                    if (!value || getFieldValue('password') === value) {
                                        return Promise.resolve();
                                    }
                                    return Promise.reject(new Error('兩次輸入的密碼不一致'));
                                },
                            }),
                        ]}
                    >
                        <Input.Password placeholder="請再次輸入密碼" />
                    </Form.Item>
                </Form>
            </Modal>
        </div>
    );
};

export default UserManagementPage;
