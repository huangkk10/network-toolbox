import React, { useState, useEffect } from 'react';
import {
    Card,
    Form,
    Input,
    Button,
    message,
    Statistic,
    Row,
    Col,
    Divider,
    Descriptions,
    Tag,
    Spin,
    Space
} from 'antd';
import {
    UploadOutlined,
    UserOutlined,
    TeamOutlined,
    HistoryOutlined,
    ReloadOutlined,
    CheckCircleOutlined
} from '@ant-design/icons';
import axios from 'axios';
import InventoryFileEditor from '../components/InventoryFileEditor';
import InventoryValidationDrawer from '../components/InventoryValidationDrawer';

const AnsibleInventoryManagerPage = () => {
    // 狀態管理
    const [loading, setLoading] = useState(false);
    const [importing, setImporting] = useState(false);
    const [currentInventory, setCurrentInventory] = useState(null);
    const [validationDrawerVisible, setValidationDrawerVisible] = useState(false);
    const [form] = Form.useForm();

    // 初始載入
    useEffect(() => {
        loadCurrentInventory();
    }, []);

    // 載入當前 Inventory
    const loadCurrentInventory = async () => {
        try {
            setLoading(true);
            const response = await axios.get('/api/ansible-inventory/');
            if (response.data.results && response.data.results.length > 0) {
                // 載入最新的 Inventory
                const latest = response.data.results[0];
                setCurrentInventory(latest);
            }
        } catch (error) {
            console.error('載入 Inventory 失敗:', error);
        } finally {
            setLoading(false);
        }
    };

    // 導入 Inventory
    const handleImport = async (values) => {
        try {
            setImporting(true);
            const response = await axios.post('/api/ansible-inventory/import/', {
                nas_path: values.nas_path,
                file_name: values.file_name || 'hosts'
            });
            
            message.success(`成功導入 ${response.data.total_hosts} 台 Host！`);
            setCurrentInventory(response.data);
            form.resetFields();
        } catch (error) {
            console.error('導入失敗:', error);
            message.error('導入失敗：' + (error.response?.data?.error || error.message));
        } finally {
            setImporting(false);
        }
    };

    // 編輯器儲存後的回調
    const handleEditorSaved = () => {
        // 重新載入 Inventory 資訊以更新統計數據
        loadCurrentInventory();
    };

    // 打開驗證抽屜
    const handleOpenValidationDrawer = () => {
        setValidationDrawerVisible(true);
    };

    // 關閉驗證抽屜
    const handleCloseValidationDrawer = () => {
        setValidationDrawerVisible(false);
    };

    return (
        <div style={{ padding: '24px' }}>
            <h1>Ansible Inventory Manager</h1>
            
            {/* 導入表單 */}
            <Card title="導入 Ansible Inventory" style={{ marginBottom: 24 }}>
                <Form
                    form={form}
                    layout="vertical"
                    onFinish={handleImport}
                >
                    <Row gutter={16}>
                        <Col xs={24} md={12}>
                            <Form.Item
                                label="NAS 路徑"
                                name="nas_path"
                                rules={[{ required: true, message: '請輸入 NAS 路徑' }]}
                            >
                                <Input
                                    placeholder="\\10.250.0.1\mdt\Script\chunwei_test\26_7F_new\inventory"
                                    disabled={importing}
                                />
                            </Form.Item>
                        </Col>
                        <Col xs={24} md={8}>
                            <Form.Item
                                label="檔案名稱"
                                name="file_name"
                                initialValue="hosts"
                            >
                                <Input placeholder="hosts" disabled={importing} />
                            </Form.Item>
                        </Col>
                        <Col xs={24} md={4}>
                            <Form.Item label=" ">
                                <Button
                                    type="primary"
                                    htmlType="submit"
                                    icon={<UploadOutlined />}
                                    loading={importing}
                                    block
                                >
                                    導入
                                </Button>
                            </Form.Item>
                        </Col>
                    </Row>
                </Form>
            </Card>

            {/* 當前 Inventory 資訊 */}
            {currentInventory && (
                <>
                    <Card
                        title={`當前 Inventory: ${currentInventory.nas_path}/${currentInventory.file_name}`}
                        style={{ marginBottom: 24 }}
                        extra={
                            <Space>
                                <Button
                                    type="primary"
                                    icon={<CheckCircleOutlined />}
                                    onClick={handleOpenValidationDrawer}
                                >
                                    檢查配置
                                </Button>
                                <Button
                                    icon={<ReloadOutlined />}
                                    onClick={loadCurrentInventory}
                                    loading={loading}
                                >
                                    重新載入
                                </Button>
                            </Space>
                        }
                    >
                        <Row gutter={16}>
                            <Col xs={12} sm={6}>
                                <Statistic
                                    title="總 Hosts"
                                    value={currentInventory.total_hosts}
                                    prefix={<UserOutlined />}
                                />
                            </Col>
                            <Col xs={12} sm={6}>
                                <Statistic
                                    title="總 Groups"
                                    value={currentInventory.total_groups}
                                    prefix={<TeamOutlined />}
                                />
                            </Col>
                            <Col xs={12} sm={6}>
                                <Statistic
                                    title="當前版本"
                                    value={`v${currentInventory.current_version}`}
                                    prefix={<HistoryOutlined />}
                                />
                            </Col>
                            <Col xs={12} sm={6}>
                                <div style={{ marginTop: 8 }}>
                                    <Tag 
                                        color={currentInventory.syntax_valid ? 'success' : 'error'}
                                        style={{ fontSize: '14px', padding: '4px 12px' }}
                                    >
                                        {currentInventory.syntax_valid ? '✅ 語法正確' : '❌ 語法錯誤'}
                                    </Tag>
                                </div>
                            </Col>
                        </Row>

                        <Divider />

                        <Descriptions size="small" column={1}>
                            <Descriptions.Item label="NAS 路徑">
                                {currentInventory.nas_path}/{currentInventory.file_name}
                            </Descriptions.Item>
                            <Descriptions.Item label="最後更新">
                                {new Date(currentInventory.updated_at).toLocaleString('zh-TW')}
                            </Descriptions.Item>
                            <Descriptions.Item label="導入時間">
                                {new Date(currentInventory.imported_at).toLocaleString('zh-TW')}
                            </Descriptions.Item>
                        </Descriptions>
                    </Card>

                    {/* 文本編輯器 */}
                    <InventoryFileEditor 
                        inventoryId={currentInventory.id}
                        onSaved={handleEditorSaved}
                    />
                </>
            )}

            {/* 無 Inventory 提示 */}
            {!currentInventory && !loading && (
                <Card>
                    <div style={{ textAlign: 'center', padding: '48px 0' }}>
                        <p style={{ fontSize: '16px', color: '#8c8c8c' }}>
                            請先導入 Ansible Inventory 文件
                        </p>
                    </div>
                </Card>
            )}

            {/* 載入中 */}
            {loading && !currentInventory && (
                <Card>
                    <div style={{ textAlign: 'center', padding: '48px 0' }}>
                        <Spin size="large" />
                        <p style={{ marginTop: 16, color: '#8c8c8c' }}>載入中...</p>
                    </div>
                </Card>
            )}

            {/* 配置驗證抽屜 */}
            {currentInventory && (
                <InventoryValidationDrawer
                    visible={validationDrawerVisible}
                    onClose={handleCloseValidationDrawer}
                    inventoryId={currentInventory.id}
                    inventoryName={`${currentInventory.nas_path}/${currentInventory.file_name}`}
                />
            )}
        </div>
    );
};

export default AnsibleInventoryManagerPage;
