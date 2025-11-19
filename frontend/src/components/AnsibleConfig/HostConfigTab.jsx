/**
 * 主機配置詳情標籤組件
 * 
 * 顯示選定主機的完整配置資訊
 */

import React, { useState, useEffect } from 'react';
import { 
    Select, 
    Card, 
    Descriptions, 
    Spin, 
    Alert, 
    Collapse, 
    Typography,
    Space,
    Tag,
    Button,
    Empty,
    message,
} from 'antd';
import { 
    DesktopOutlined, 
    CodeOutlined,
    CopyOutlined,
    CheckCircleOutlined,
    CloseCircleOutlined,
    ExperimentOutlined,
} from '@ant-design/icons';
import { 
    getHostConfig,
    formatConfigForDisplay,
    extractTestcaseFields,
} from '../../services/ansibleService';

const { Panel } = Collapse;
const { Paragraph, Text } = Typography;
const { Option } = Select;

const HostConfigTab = ({ jobId, hosts, initialHostname = null }) => {
    const [selectedHost, setSelectedHost] = useState(initialHostname);
    const [hostConfig, setHostConfig] = useState(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const [cached, setCached] = useState(false);

    // 當 initialHostname 改變時自動載入
    useEffect(() => {
        if (initialHostname) {
            setSelectedHost(initialHostname);
            fetchHostConfig(initialHostname);
        }
    }, [initialHostname]);

    // 獲取主機配置
    const fetchHostConfig = async (hostname) => {
        if (!hostname) return;

        setLoading(true);
        setError(null);

        try {
            const response = await getHostConfig(jobId, hostname);
            
            if (response.success) {
                setHostConfig(response.config);
                setCached(response.cached);
            } else {
                throw new Error(response.message || '獲取配置失敗');
            }
        } catch (err) {
            console.error('Failed to fetch host config:', err);
            setError(err.message || '獲取配置失敗');
            message.error('獲取配置失敗：' + err.message);
        } finally {
            setLoading(false);
        }
    };

    // 處理主機選擇
    const handleSelectHost = (hostname) => {
        setSelectedHost(hostname);
        fetchHostConfig(hostname);
    };

    // 複製 JSON 到剪貼簿
    const handleCopyJSON = () => {
        const json = JSON.stringify(hostConfig, null, 2);
        if (navigator.clipboard && navigator.clipboard.writeText) {
            navigator.clipboard.writeText(json)
                .then(() => {
                    message.success('已複製 JSON 配置');
                })
                .catch(() => {
                    message.error('複製失敗');
                });
        } else {
            try {
                const textArea = document.createElement('textarea');
                textArea.value = json;
                textArea.style.position = 'fixed';
                textArea.style.opacity = '0';
                document.body.appendChild(textArea);
                textArea.select();
                document.execCommand('copy');
                document.body.removeChild(textArea);
                message.success('已複製 JSON 配置');
            } catch (err) {
                console.error('複製失敗:', err);
                message.error('複製失敗');
            }
        }
    };

    // 格式化配置項目（已自動排除測試案例參數）
    const configItems = hostConfig ? formatConfigForDisplay(hostConfig) : [];

    // 提取測試案例參數（獨立分類）
    const testcaseFields = hostConfig ? extractTestcaseFields(hostConfig) : {};
    const testcaseKeys = Object.keys(testcaseFields);

    // 分類配置項目（configItems 已經不包含測試案例參數）
    const basicItems = configItems.filter(item => 
        ['ansible_host', 'device_number', 'sample_number', 'macaddress'].includes(item.key)
    );
    
    // UART 相關配置（根據 key 或 label 識別）
    const uartItems = configItems.filter(item => {
        // 根據 key 識別
        const uartKeys = [
            'uart_id', 
            'uart_host', 
            'UART_IP', 
            'ansible_user', 
            'ansible_password',
            'uart_logger_lowpower_enabled',
            'uart_logger_parser_hp_enabled',
            'uart_logger_upload_dir'
            // UART_HOSTNAME 已移除（與 uart_host 重複）
        ];
        if (uartKeys.includes(item.key)) return true;
        
        // 根據 label 識別（英文）
        const uartLabels = [
            'UART ID', 
            'UART Host', 
            'UART IP', 
            'UART Logger Low Power',
            'UART Logger Parser HP',
            'UART Logger Upload Dir',
            'User', 
            'Password'
        ];
        if (uartLabels.includes(item.label)) return true;
        
        return false;
    });
    
    // JTAG 相關配置（根據 key 識別）
    const jtagItems = configItems.filter(item => {
        const jtagKeys = [
            'enable_jtag_dump', 
            'jtag_serial', 
            'firmware_sku_keyword',
            'jtag_dump_upload_dir',
            'firmware_polling_dir'
        ];
        return jtagKeys.includes(item.key);
    });
    
    const ansibleItems = configItems.filter(item => {
        // 排除已在 UART 區塊顯示的欄位
        const excludeKeys = [
            'ansible_host', 
            'ansible_user', 
            'ansible_password', 
            'uart_id', 
            'uart_host', 
            'UART_IP',
            'uart_logger_lowpower_enabled',
            'uart_logger_parser_hp_enabled',
            'uart_logger_upload_dir'
            // UART_HOSTNAME 已移除（與 uart_host 重複）
        ];
        if (excludeKeys.includes(item.key)) return false;
        
        // 排除已在 JTAG 區塊顯示的欄位
        const jtagKeys = ['enable_jtag_dump', 'jtag_serial', 'firmware_sku_keyword', 'jtag_dump_upload_dir', 'firmware_polling_dir'];
        if (jtagKeys.includes(item.key)) return false;
        
        // 只保留 ansible_ 開頭的欄位
        return item.key.startsWith('ansible_');
    });
    
    const otherItems = configItems.filter(item => {
        // 排除基本資訊
        const basicKeys = ['ansible_host', 'device_number', 'sample_number', 'macaddress'];
        if (basicKeys.includes(item.key)) return false;
        
        // 排除 UART 資訊
        const uartKeys = [
            'uart_id', 
            'uart_host', 
            'UART_IP', 
            'ansible_user', 
            'ansible_password',
            'uart_logger_lowpower_enabled',
            'uart_logger_parser_hp_enabled',
            'uart_logger_upload_dir'
            // UART_HOSTNAME 已移除（與 uart_host 重複）
        ];
        if (uartKeys.includes(item.key)) return false;
        
        // 排除 JTAG 資訊
        const jtagKeys = ['enable_jtag_dump', 'jtag_serial', 'firmware_sku_keyword', 'jtag_dump_upload_dir', 'firmware_polling_dir'];
        if (jtagKeys.includes(item.key)) return false;
        
        // 排除 Ansible 變數
        if (item.key.startsWith('ansible_')) return false;
        
        return true;
    });

    return (
        <div>
            {/* 主機選擇器 */}
            <div style={{ marginBottom: 24 }}>
                <Space direction="vertical" style={{ width: '100%' }}>
                    <Text strong>選擇主機：</Text>
                    <Select
                        showSearch
                        style={{ width: '100%', maxWidth: 400 }}
                        placeholder="請選擇要查看配置的主機"
                        value={selectedHost}
                        onChange={handleSelectHost}
                        optionFilterProp="children"
                        filterOption={(input, option) =>
                            option.children.toLowerCase().includes(input.toLowerCase())
                        }
                    >
                        {hosts.map(host => (
                            <Option key={host.hostname} value={host.hostname}>
                                <Space>
                                    <DesktopOutlined />
                                    {host.hostname}
                                    <Text type="secondary" style={{ fontSize: '12px' }}>
                                        ({host.ansible_host})
                                    </Text>
                                </Space>
                            </Option>
                        ))}
                    </Select>
                    
                    {cached && (
                        <Tag icon={<CheckCircleOutlined />} color="success">
                            使用快取資料
                        </Tag>
                    )}
                </Space>
            </div>

            {/* 載入中 */}
            {loading && (
                <div style={{ textAlign: 'center', padding: '40px' }}>
                    <Spin size="large" tip="正在載入主機配置..." />
                </div>
            )}

            {/* 錯誤訊息 */}
            {error && !loading && (
                <Alert
                    message="載入失敗"
                    description={error}
                    type="error"
                    showIcon
                    closable
                />
            )}

            {/* 配置內容 */}
            {!loading && !error && selectedHost && hostConfig && (
                <Space direction="vertical" size="large" style={{ width: '100%' }}>
                    {/* 基本資訊卡片 */}
                    <Card 
                        title={
                            <Space>
                                <DesktopOutlined />
                                {selectedHost}
                            </Space>
                        }
                        extra={
                            <Button 
                                icon={<CopyOutlined />}
                                onClick={handleCopyJSON}
                            >
                                複製 JSON
                            </Button>
                        }
                    >
                        <Descriptions 
                            column={2} 
                            bordered
                            size="small"
                        >
                            {basicItems.map(item => (
                                <Descriptions.Item 
                                    key={item.key} 
                                    label={item.label}
                                >
                                    <Text copyable={item.value !== 'N/A'}>
                                        {item.value}
                                    </Text>
                                </Descriptions.Item>
                            ))}
                        </Descriptions>
                    </Card>

                    {/* UART 資訊卡片 */}
                    {uartItems.length > 0 && (
                        <Card 
                            title={
                                <Space>
                                    <DesktopOutlined />
                                    UART 連接資訊
                                </Space>
                            }
                            size="small"
                            style={{ 
                                borderColor: '#1890ff',
                                boxShadow: '0 2px 8px rgba(24, 144, 255, 0.1)'
                            }}
                        >
                            <Descriptions 
                                column={2} 
                                bordered
                                size="small"
                            >
                                {uartItems.map(item => (
                                    <Descriptions.Item 
                                        key={item.key} 
                                        label={<Text strong>{item.label}</Text>}
                                    >
                                        <Text 
                                            copyable={item.value !== 'N/A'}
                                            style={{ 
                                                color: item.label === 'Password' ? '#ff4d4f' : undefined,
                                                fontFamily: item.label === 'Password' ? 'monospace' : undefined
                                            }}
                                        >
                                            {item.value}
                                        </Text>
                                    </Descriptions.Item>
                                ))}
                            </Descriptions>
                        </Card>
                    )}

                    {/* JTAG 配置卡片 */}
                    {jtagItems.length > 0 && (
                        <Card 
                            title={
                                <Space>
                                    <CodeOutlined />
                                    JTAG 配置
                                </Space>
                            }
                            size="small"
                            style={{ 
                                borderColor: '#722ed1',
                                boxShadow: '0 2px 8px rgba(114, 46, 209, 0.1)'
                            }}
                        >
                            <Descriptions 
                                column={2} 
                                bordered
                                size="small"
                            >
                                {jtagItems.map(item => (
                                    <Descriptions.Item 
                                        key={item.key} 
                                        label={<Text strong>{item.label}</Text>}
                                    >
                                        <Text copyable={item.value !== 'N/A'}>
                                            {item.value}
                                        </Text>
                                    </Descriptions.Item>
                                ))}
                            </Descriptions>
                        </Card>
                    )}

                    {/* 測試案例配置卡片 */}
                    {testcaseKeys.length > 0 && (
                        <Card 
                            title={
                                <Space>
                                    <ExperimentOutlined />
                                    測試案例配置
                                </Space>
                            }
                            size="small"
                            style={{ 
                                borderColor: '#52c41a',
                                boxShadow: '0 2px 8px rgba(82, 196, 26, 0.1)'
                            }}
                        >
                            <Space direction="vertical" style={{ width: '100%' }} size="middle">
                                {testcaseKeys.map(key => {
                                    const field = testcaseFields[key];
                                    
                                    // 如果是測試配置的 array of objects，展開顯示詳細欄位
                                    if (Array.isArray(field.value) && 
                                        field.value.length > 0 && 
                                        typeof field.value[0] === 'object') {
                                        
                                        const testcaseFields_detail = ['id', 'enabled', 'script_exec', 'log_path', 'timeout', 'archive_patterns'];
                                        const hasTestcaseFields = testcaseFields_detail.some(f => f in field.value[0]);
                                        
                                        if (hasTestcaseFields) {
                                            // 這是測試配置，展開顯示每個測試項目
                                            return (
                                                <div key={key}>
                                                    <Text strong style={{ color: '#52c41a', fontSize: '16px' }}>
                                                        {field.label}
                                                    </Text>
                                                    {field.value.map((testItem, index) => (
                                                        <Card 
                                                            key={index}
                                                            size="small"
                                                            style={{ marginTop: 8, backgroundColor: testItem.enabled ? '#f6ffed' : '#fff1f0' }}
                                                            title={
                                                                <Space>
                                                                    {testItem.enabled ? (
                                                                        <CheckCircleOutlined style={{ color: '#52c41a' }} />
                                                                    ) : (
                                                                        <CloseCircleOutlined style={{ color: '#ff4d4f' }} />
                                                                    )}
                                                                    <Text strong>
                                                                        測試項目 #{index + 1}
                                                                        {testItem.id && `: ${testItem.id}`}
                                                                    </Text>
                                                                </Space>
                                                            }
                                                        >
                                                            <Descriptions 
                                                                column={1} 
                                                                bordered
                                                                size="small"
                                                            >
                                                                {Object.entries(testItem).map(([itemKey, itemValue]) => (
                                                                    <Descriptions.Item 
                                                                        key={itemKey}
                                                                        label={<Text strong>{itemKey}</Text>}
                                                                    >
                                                                        <Text copyable>
                                                                            {typeof itemValue === 'boolean' 
                                                                                ? (itemValue ? '✓ 是' : '✗ 否')
                                                                                : (typeof itemValue === 'object' 
                                                                                    ? JSON.stringify(itemValue, null, 2) 
                                                                                    : String(itemValue))
                                                                            }
                                                                        </Text>
                                                                    </Descriptions.Item>
                                                                ))}
                                                            </Descriptions>
                                                        </Card>
                                                    ))}
                                                </div>
                                            );
                                        }
                                    }
                                    
                                    // 其他類型的測試案例參數（如 testcase_set, testcase_version 等）
                                    let displayValue = field.value;
                                    if (Array.isArray(field.value)) {
                                        displayValue = field.value.join(', ');
                                    } else if (typeof field.value === 'object' && field.value !== null) {
                                        displayValue = JSON.stringify(field.value, null, 2);
                                    } else {
                                        displayValue = String(field.value);
                                    }
                                    
                                    return (
                                        <Descriptions 
                                            key={key}
                                            column={2} 
                                            bordered
                                            size="small"
                                        >
                                            <Descriptions.Item 
                                                label={<Text strong style={{ color: '#52c41a' }}>{field.label}</Text>}
                                                span={2}
                                            >
                                                <Text 
                                                    copyable={displayValue !== 'N/A'}
                                                    style={{ color: '#389e0d' }}
                                                >
                                                    {displayValue}
                                                </Text>
                                            </Descriptions.Item>
                                        </Descriptions>
                                    );
                                })}
                            </Space>
                        </Card>
                    )}

                    {/* Ansible 變數 */}
                    {ansibleItems.length > 0 && (
                        <Card title="Ansible 變數" size="small">
                            <Descriptions 
                                column={2} 
                                bordered
                                size="small"
                            >
                                {ansibleItems.map(item => (
                                    <Descriptions.Item 
                                        key={item.key} 
                                        label={item.label}
                                    >
                                        <Text copyable={item.value !== 'N/A'}>
                                            {item.value}
                                        </Text>
                                    </Descriptions.Item>
                                ))}
                            </Descriptions>
                        </Card>
                    )}

                    {/* 其他配置 */}
                    {otherItems.length > 0 && (
                        <Card title="其他配置" size="small">
                            <Descriptions 
                                column={2} 
                                bordered
                                size="small"
                            >
                                {otherItems.map(item => (
                                    <Descriptions.Item 
                                        key={item.key} 
                                        label={item.label}
                                    >
                                        <Text copyable={item.value !== 'N/A'}>
                                            {item.value}
                                        </Text>
                                    </Descriptions.Item>
                                ))}
                            </Descriptions>
                        </Card>
                    )}

                    {/* 完整 JSON 配置 */}
                    <Collapse>
                        <Panel 
                            header={
                                <Space>
                                    <CodeOutlined />
                                    <Text strong>完整配置 (JSON)</Text>
                                </Space>
                            } 
                            key="json"
                        >
                            <Paragraph>
                                <pre style={{ 
                                    background: '#f5f5f5', 
                                    padding: '16px', 
                                    borderRadius: '4px',
                                    maxHeight: '400px',
                                    overflow: 'auto',
                                    fontSize: '12px',
                                }}>
                                    {JSON.stringify(hostConfig, null, 2)}
                                </pre>
                            </Paragraph>
                        </Panel>
                    </Collapse>
                </Space>
            )}

            {/* 未選擇主機 */}
            {!loading && !selectedHost && (
                <Empty 
                    description="請選擇要查看配置的主機"
                    image={Empty.PRESENTED_IMAGE_SIMPLE}
                />
            )}
        </div>
    );
};

export default HostConfigTab;
