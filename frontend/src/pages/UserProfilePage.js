import React, { useState, useEffect } from 'react';
import { Card, Descriptions, Button, Space, message, Spin, Tag } from 'antd';
import { UserOutlined, LockOutlined, EditOutlined, SafetyOutlined } from '@ant-design/icons';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';
import ChangePasswordModal from '../components/ChangePasswordModal';
import EditProfileModal from '../components/EditProfileModal';

/**
 * 用戶個人資料頁面
 * 功能：
 * - 顯示用戶基本資料
 * - 修改密碼
 * - 編輯個人資料
 */
const UserProfilePage = () => {
    const navigate = useNavigate();
    const [userProfile, setUserProfile] = useState(null);
    const [loading, setLoading] = useState(true);
    const [changePasswordModalVisible, setChangePasswordModalVisible] = useState(false);
    const [editProfileModalVisible, setEditProfileModalVisible] = useState(false);

    /**
     * 載入用戶資料
     */
    const fetchUserProfile = async () => {
        setLoading(true);
        try {
            const response = await axios.get('/api/user-profile/me/');
            setUserProfile(response.data);
        } catch (error) {
            console.error('獲取用戶資料失敗:', error);
            if (error.response?.status === 401) {
                message.error('請先登入');
                navigate('/login');
            } else {
                message.error('獲取用戶資料失敗：' + error.message);
            }
        } finally {
            setLoading(false);
        }
    };

    /**
     * 組件載入時獲取用戶資料
     */
    useEffect(() => {
        fetchUserProfile();
    }, []);

    /**
     * 處理修改密碼成功
     */
    const handlePasswordChangeSuccess = () => {
        message.info('密碼已修改，建議重新登入以確保安全。');
        // 可選：3 秒後自動導向登入頁面
        // setTimeout(() => {
        //     navigate('/login');
        // }, 3000);
    };

    /**
     * 處理編輯資料成功
     */
    const handleEditProfileSuccess = () => {
        // 重新載入用戶資料
        fetchUserProfile();
    };

    /**
     * 格式化日期時間
     */
    const formatDateTime = (dateString) => {
        if (!dateString) return '無';
        const date = new Date(dateString);
        return date.toLocaleString('zh-TW', {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit'
        });
    };

    if (loading) {
        return (
            <div style={{ 
                display: 'flex', 
                justifyContent: 'center', 
                alignItems: 'center', 
                height: '100vh' 
            }}>
                <Spin size="large" tip="載入中..." />
            </div>
        );
    }

    return (
        <div style={{ padding: '24px', maxWidth: 1200, margin: '0 auto' }}>
            <h1 style={{ fontSize: 24, marginBottom: 24 }}>
                <UserOutlined style={{ marginRight: 8 }} />
                個人資料
            </h1>

            {/* 基本資料卡片 */}
            <Card
                title={
                    <span>
                        <UserOutlined style={{ marginRight: 8 }} />
                        基本資料
                    </span>
                }
                extra={
                    <Button
                        type="primary"
                        icon={<EditOutlined />}
                        onClick={() => setEditProfileModalVisible(true)}
                    >
                        編輯資料
                    </Button>
                }
                style={{ marginBottom: 24 }}
            >
                <Descriptions bordered column={2}>
                    <Descriptions.Item label="用戶名稱" span={2}>
                        <strong>{userProfile?.username}</strong>
                        <Tag color="blue" style={{ marginLeft: 8 }}>當前用戶</Tag>
                    </Descriptions.Item>
                    
                    <Descriptions.Item label="電子郵件">
                        {userProfile?.email || '未設定'}
                    </Descriptions.Item>
                    
                    <Descriptions.Item label="用戶 ID">
                        {userProfile?.id}
                    </Descriptions.Item>
                    
                    <Descriptions.Item label="名字">
                        {userProfile?.first_name || '未設定'}
                    </Descriptions.Item>
                    
                    <Descriptions.Item label="姓氏">
                        {userProfile?.last_name || '未設定'}
                    </Descriptions.Item>
                    
                    <Descriptions.Item label="註冊時間" span={2}>
                        {formatDateTime(userProfile?.date_joined)}
                    </Descriptions.Item>
                    
                    <Descriptions.Item label="最後登入時間" span={2}>
                        {formatDateTime(userProfile?.last_login)}
                    </Descriptions.Item>
                </Descriptions>
            </Card>

            {/* 安全設定卡片 */}
            <Card
                title={
                    <span>
                        <SafetyOutlined style={{ marginRight: 8 }} />
                        安全設定
                    </span>
                }
            >
                <Space direction="vertical" size="middle" style={{ width: '100%' }}>
                    <div style={{ 
                        display: 'flex', 
                        justifyContent: 'space-between', 
                        alignItems: 'center',
                        padding: '12px',
                        backgroundColor: '#fafafa',
                        borderRadius: 4
                    }}>
                        <div>
                            <div style={{ fontWeight: 500, marginBottom: 4 }}>
                                <LockOutlined style={{ marginRight: 8 }} />
                                登入密碼
                            </div>
                            <div style={{ fontSize: 12, color: '#8c8c8c' }}>
                                定期更換密碼可以提高帳戶安全性
                            </div>
                        </div>
                        <Button
                            type="primary"
                            icon={<LockOutlined />}
                            onClick={() => setChangePasswordModalVisible(true)}
                        >
                            修改密碼
                        </Button>
                    </div>

                    <div style={{ 
                        padding: '12px', 
                        backgroundColor: '#fffbe6', 
                        borderRadius: 4,
                        fontSize: 12,
                        color: '#595959',
                        border: '1px solid #ffe58f'
                    }}>
                        <strong>安全建議：</strong>
                        <ul style={{ margin: '4px 0 0 16px', paddingLeft: 0 }}>
                            <li>使用強密碼：至少 8 位，包含大小寫字母、數字和特殊字符</li>
                            <li>定期更換密碼：建議每 3-6 個月更換一次</li>
                            <li>不要在多個網站使用相同的密碼</li>
                            <li>不要與他人分享您的密碼</li>
                        </ul>
                    </div>
                </Space>
            </Card>

            {/* 修改密碼 Modal */}
            <ChangePasswordModal
                open={changePasswordModalVisible}
                onCancel={() => setChangePasswordModalVisible(false)}
                onSuccess={handlePasswordChangeSuccess}
            />

            {/* 編輯資料 Modal */}
            <EditProfileModal
                open={editProfileModalVisible}
                onCancel={() => setEditProfileModalVisible(false)}
                onSuccess={handleEditProfileSuccess}
                initialValues={userProfile}
            />
        </div>
    );
};

export default UserProfilePage;
