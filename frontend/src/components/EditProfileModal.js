import React, { useState, useEffect } from 'react';
import { Modal, Form, Input, message } from 'antd';
import { UserOutlined, MailOutlined } from '@ant-design/icons';
import axios from 'axios';

/**
 * 編輯個人資料 Modal 組件
 * 功能：
 * - 編輯郵件地址
 * - 編輯姓名
 * - 更新個人資料
 */
const EditProfileModal = ({ open, onCancel, onSuccess, initialValues }) => {
    const [form] = Form.useForm();
    const [loading, setLoading] = useState(false);

    /**
     * 當 Modal 打開或 initialValues 變化時，更新表單值
     */
    useEffect(() => {
        if (open && initialValues) {
            form.setFieldsValue({
                email: initialValues.email || '',
                first_name: initialValues.first_name || '',
                last_name: initialValues.last_name || ''
            });
        }
    }, [open, initialValues, form]);

    /**
     * 處理表單提交
     */
    const handleSubmit = async (values) => {
        setLoading(true);
        try {
            const response = await axios.put('/api/user-profile/update-profile/', {
                email: values.email || '',
                first_name: values.first_name || '',
                last_name: values.last_name || ''
            });

            message.success(response.data.message || '個人資料更新成功！');
            
            // 調用成功回調
            if (onSuccess) {
                onSuccess();
            }

            // 關閉 Modal
            onCancel();

        } catch (error) {
            console.error('更新個人資料失敗:', error);
            
            // 顯示後端返回的錯誤訊息
            if (error.response?.data?.error) {
                message.error(error.response.data.error);
            } else if (error.response?.data) {
                // 處理 Django 驗證錯誤（可能是字段錯誤）
                const errors = error.response.data;
                const errorMessages = Object.values(errors).flat();
                message.error(errorMessages.join(', '));
            } else {
                message.error('更新個人資料失敗：' + error.message);
            }
        } finally {
            setLoading(false);
        }
    };

    /**
     * 處理 Modal 關閉
     */
    const handleCancel = () => {
        form.resetFields();
        onCancel();
    };

    return (
        <Modal
            title={
                <span>
                    <UserOutlined style={{ marginRight: 8 }} />
                    編輯個人資料
                </span>
            }
            open={open}
            onOk={() => form.submit()}
            onCancel={handleCancel}
            confirmLoading={loading}
            okText="儲存"
            cancelText="取消"
            width={500}
        >
            <Form
                form={form}
                layout="vertical"
                onFinish={handleSubmit}
                autoComplete="off"
            >
                <Form.Item
                    label="用戶名稱"
                    name="username"
                    tooltip="用戶名稱無法修改"
                >
                    <Input
                        prefix={<UserOutlined />}
                        value={initialValues?.username}
                        disabled
                        placeholder={initialValues?.username || '載入中...'}
                    />
                </Form.Item>

                <Form.Item
                    label="電子郵件"
                    name="email"
                    rules={[
                        { 
                            type: 'email', 
                            message: '請輸入有效的電子郵件地址' 
                        }
                    ]}
                >
                    <Input
                        prefix={<MailOutlined />}
                        placeholder="請輸入電子郵件"
                        autoComplete="email"
                    />
                </Form.Item>

                <Form.Item
                    label="名字"
                    name="first_name"
                >
                    <Input
                        prefix={<UserOutlined />}
                        placeholder="請輸入名字"
                        autoComplete="given-name"
                    />
                </Form.Item>

                <Form.Item
                    label="姓氏"
                    name="last_name"
                >
                    <Input
                        prefix={<UserOutlined />}
                        placeholder="請輸入姓氏"
                        autoComplete="family-name"
                    />
                </Form.Item>

                <div style={{ 
                    padding: '12px', 
                    backgroundColor: '#f6ffed', 
                    borderRadius: 4,
                    fontSize: 12,
                    color: '#595959',
                    border: '1px solid #b7eb8f'
                }}>
                    <strong>提示：</strong> 更新電子郵件或姓名後，系統會立即保存您的變更。
                </div>
            </Form>
        </Modal>
    );
};

export default EditProfileModal;
