import React, { useState } from 'react';
import { Modal, Form, Input, message, Progress } from 'antd';
import { LockOutlined } from '@ant-design/icons';
import axios from 'axios';

/**
 * 修改密碼 Modal 組件
 * 功能：
 * - 驗證舊密碼
 * - 輸入新密碼（帶強度檢查）
 * - 確認新密碼
 * - 成功後建議重新登入
 */
const ChangePasswordModal = ({ open, onCancel, onSuccess }) => {
    const [form] = Form.useForm();
    const [loading, setLoading] = useState(false);
    const [passwordStrength, setPasswordStrength] = useState({
        score: 0,
        text: '',
        percent: 0,
        status: 'exception'
    });

    /**
     * 計算密碼強度
     * @param {string} password - 密碼
     * @returns {object} 強度信息 { score, text, percent, status }
     */
    const calculatePasswordStrength = (password) => {
        if (!password) {
            return { score: 0, text: '', percent: 0, status: 'exception' };
        }

        let score = 0;
        const checks = {
            length: password.length >= 8,           // 長度至少 8 位
            lowercase: /[a-z]/.test(password),      // 包含小寫字母
            uppercase: /[A-Z]/.test(password),      // 包含大寫字母
            number: /[0-9]/.test(password),         // 包含數字
            special: /[^A-Za-z0-9]/.test(password)  // 包含特殊字符
        };

        // 計算滿足的條件數
        score = Object.values(checks).filter(Boolean).length;

        // 根據分數判斷強度
        let text, percent, status;
        if (score <= 2) {
            text = '弱';
            percent = 33;
            status = 'exception';
        } else if (score <= 3) {
            text = '中';
            percent = 66;
            status = 'normal';
        } else {
            text = '強';
            percent = 100;
            status = 'success';
        }

        return { score, text, percent, status };
    };

    /**
     * 處理新密碼輸入變化
     */
    const handleNewPasswordChange = (e) => {
        const password = e.target.value;
        const strength = calculatePasswordStrength(password);
        setPasswordStrength(strength);
    };

    /**
     * 處理表單提交
     */
    const handleSubmit = async (values) => {
        setLoading(true);
        try {
            const response = await axios.post('/api/user-profile/change-password/', {
                old_password: values.old_password,
                new_password: values.new_password,
                confirm_password: values.confirm_password
            });

            message.success(response.data.message || '密碼修改成功！建議重新登入以確保安全。');
            
            // 清空表單
            form.resetFields();
            setPasswordStrength({ score: 0, text: '', percent: 0, status: 'exception' });
            
            // 調用成功回調
            if (onSuccess) {
                onSuccess();
            }

            // 關閉 Modal
            onCancel();

        } catch (error) {
            console.error('修改密碼失敗:', error);
            
            // 顯示後端返回的錯誤訊息
            if (error.response?.data?.error) {
                message.error(error.response.data.error);
            } else if (error.response?.data) {
                // 處理 Django 驗證錯誤（可能是字段錯誤）
                const errors = error.response.data;
                const errorMessages = Object.values(errors).flat();
                message.error(errorMessages.join(', '));
            } else {
                message.error('修改密碼失敗：' + error.message);
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
        setPasswordStrength({ score: 0, text: '', percent: 0, status: 'exception' });
        onCancel();
    };

    return (
        <Modal
            title={
                <span>
                    <LockOutlined style={{ marginRight: 8 }} />
                    修改密碼
                </span>
            }
            open={open}
            onOk={() => form.submit()}
            onCancel={handleCancel}
            confirmLoading={loading}
            okText="確定"
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
                    label="舊密碼"
                    name="old_password"
                    rules={[
                        { required: true, message: '請輸入舊密碼' }
                    ]}
                >
                    <Input.Password
                        prefix={<LockOutlined />}
                        placeholder="請輸入舊密碼"
                        autoComplete="off"
                    />
                </Form.Item>

                <Form.Item
                    label="新密碼"
                    name="new_password"
                    rules={[
                        { required: true, message: '請輸入新密碼' },
                        { min: 8, message: '密碼長度至少 8 位' },
                        {
                            validator: (_, value) => {
                                if (!value) return Promise.resolve();
                                const oldPassword = form.getFieldValue('old_password');
                                if (oldPassword && value === oldPassword) {
                                    return Promise.reject('新密碼不能與舊密碼相同');
                                }
                                return Promise.resolve();
                            }
                        }
                    ]}
                >
                    <Input.Password
                        prefix={<LockOutlined />}
                        placeholder="請輸入新密碼（至少 8 位）"
                        onChange={handleNewPasswordChange}
                        autoComplete="new-password"
                    />
                </Form.Item>

                {/* 密碼強度指示器 */}
                {passwordStrength.percent > 0 && (
                    <Form.Item>
                        <div style={{ marginTop: -16, marginBottom: 8 }}>
                            <Progress
                                percent={passwordStrength.percent}
                                status={passwordStrength.status}
                                format={() => `密碼強度：${passwordStrength.text}`}
                                strokeWidth={8}
                            />
                        </div>
                        <div style={{ fontSize: 12, color: '#8c8c8c' }}>
                            建議：至少 8 位，包含大小寫字母、數字和特殊字符
                        </div>
                    </Form.Item>
                )}

                <Form.Item
                    label="確認新密碼"
                    name="confirm_password"
                    dependencies={['new_password']}
                    rules={[
                        { required: true, message: '請確認新密碼' },
                        {
                            validator: (_, value) => {
                                if (!value || form.getFieldValue('new_password') === value) {
                                    return Promise.resolve();
                                }
                                return Promise.reject('兩次輸入的密碼不一致');
                            }
                        }
                    ]}
                >
                    <Input.Password
                        prefix={<LockOutlined />}
                        placeholder="請再次輸入新密碼"
                        autoComplete="new-password"
                    />
                </Form.Item>

                <div style={{ 
                    padding: '12px', 
                    backgroundColor: '#f0f5ff', 
                    borderRadius: 4,
                    fontSize: 12,
                    color: '#595959'
                }}>
                    <strong>安全提示：</strong>
                    <ul style={{ margin: '4px 0 0 16px', paddingLeft: 0 }}>
                        <li>密碼修改後，建議重新登入以確保安全</li>
                        <li>請勿使用與其他網站相同的密碼</li>
                        <li>定期更換密碼以保護您的帳戶</li>
                    </ul>
                </div>
            </Form>
        </Modal>
    );
};

export default ChangePasswordModal;
