import React, { useState } from 'react';
import { Form, Input, Button, Card, message } from 'antd';
import { UserOutlined, MailOutlined, LockOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import './LoginPage.css';

const RegisterPage = () => {
    const navigate = useNavigate();
    const { register } = useAuth();
    const [loading, setLoading] = useState(false);
    const [form] = Form.useForm();

    const handleRegister = async (values) => {
        setLoading(true);
        try {
            const result = await register({
                username: values.username,
                email: values.email,
                password: values.password,
            });

            if (result.success) {
                message.success(result.message || '註冊成功！即將跳轉到登入頁面...');
                setTimeout(() => {
                    navigate('/login');
                }, 1500);
            } else {
                message.error(result.message || '註冊失敗');
            }
        } catch (error) {
            console.error('Register error:', error);
            message.error('註冊過程中發生錯誤');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="login-container">
            <Card className="login-card" bordered={false}>
                <div className="login-header">
                    <h1 className="brand-name">NT</h1>
                    <h2>Network Toolbox</h2>
                    <p className="login-subtitle">註冊新帳號</p>
                </div>
                <Form
                    form={form}
                    name="register"
                    onFinish={handleRegister}
                    autoComplete="off"
                    layout="vertical"
                >
                    <Form.Item
                        name="username"
                        rules={[
                            { required: true, message: '請輸入用戶名稱' },
                            { min: 3, message: '用戶名稱至少需要 3 個字符' },
                            { max: 30, message: '用戶名稱不能超過 30 個字符' },
                            { 
                                pattern: /^[a-zA-Z0-9_-]+$/, 
                                message: '用戶名稱只能包含字母、數字、底線和連字符' 
                            }
                        ]}
                    >
                        <Input
                            prefix={<UserOutlined />}
                            placeholder="用戶名稱"
                            size="large"
                        />
                    </Form.Item>

                    <Form.Item
                        name="email"
                        rules={[
                            { required: true, message: '請輸入電子郵件' },
                            { type: 'email', message: '請輸入有效的電子郵件地址' }
                        ]}
                    >
                        <Input
                            prefix={<MailOutlined />}
                            placeholder="電子郵件"
                            size="large"
                        />
                    </Form.Item>

                    <Form.Item
                        name="password"
                        rules={[
                            { required: true, message: '請輸入密碼' },
                            { min: 6, message: '密碼至少需要 6 個字符' }
                        ]}
                    >
                        <Input.Password
                            prefix={<LockOutlined />}
                            placeholder="密碼"
                            size="large"
                        />
                    </Form.Item>

                    <Form.Item
                        name="confirmPassword"
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
                        <Input.Password
                            prefix={<LockOutlined />}
                            placeholder="確認密碼"
                            size="large"
                        />
                    </Form.Item>

                    <Form.Item>
                        <Button
                            type="primary"
                            htmlType="submit"
                            loading={loading}
                            size="large"
                            block
                        >
                            註冊
                        </Button>
                    </Form.Item>

                    <div style={{ textAlign: 'center' }}>
                        <Button
                            type="link"
                            onClick={() => navigate('/login')}
                        >
                            已有帳號？立即登入
                        </Button>
                    </div>
                </Form>
            </Card>
        </div>
    );
};

export default RegisterPage;
