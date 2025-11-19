/**
 * Inventory Validation Drawer Component
 * 
 * Ansible Inventory 配置檢查抽屜組件
 * 仿效 Jenkins Build 配置檢查風格
 * 
 * 功能：
 * 1. 右側抽屜展示
 * 2. 逐項檢查並顯示結果（類似 BuildConfigValidatorPage）
 * 3. 自動展開錯誤和警告項目
 * 4. 提供重新檢查、導出報告等功能
 */

import React, { useState, useEffect } from 'react';
import {
    Drawer,
    Button,
    Space,
    Card,
    Progress,
    Collapse,
    Checkbox,
    Tag,
    Descriptions,
    Divider,
    message,
    Spin,
    Typography,
    Statistic,
    Row,
    Col,
} from 'antd';
import {
    CheckCircleOutlined,
    CloseCircleOutlined,
    WarningOutlined,
    SyncOutlined,
    DownloadOutlined,
    InfoCircleOutlined,
} from '@ant-design/icons';
import axios from 'axios';

const { Panel } = Collapse;
const { Text, Title } = Typography;

const InventoryValidationDrawer = ({ visible, onClose, inventoryId, inventoryName }) => {
    // 狀態管理
    const [loading, setLoading] = useState(false);
    const [validationResult, setValidationResult] = useState(null);
    const [expandedPanels, setExpandedPanels] = useState([]);
    const [validationTime, setValidationTime] = useState(null);

    // 執行檢查
    const handleValidate = async () => {
        setLoading(true);
        try {
            const response = await axios.post(
                `/api/ansible-inventory/${inventoryId}/validate-config/`,
                {
                    check_connectivity: false,  // 暫時不執行網路測試
                    check_dhcp: true            // ✅ 執行 DHCP 租約比對
                }
            );

            if (response.data.success) {
                setValidationResult(response.data.data);
                setValidationTime(new Date());

                // 自動展開錯誤和警告項目
                const errorKeys = Object.keys(response.data.data.checks).filter(
                    key => ['error', 'warning'].includes(response.data.data.checks[key].status)
                );
                setExpandedPanels(errorKeys);

                message.success('配置檢查完成');
            } else {
                message.error('檢查失敗：' + response.data.message);
            }
        } catch (error) {
            console.error('❌ Validation error:', error);
            message.error('檢查失敗：' + (error.response?.data?.message || error.message));
        } finally {
            setLoading(false);
        }
    };

    // 導出報告
    const handleExportReport = () => {
        if (!validationResult) {
            message.warning('請先執行檢查');
            return;
        }

        const reportContent = JSON.stringify(validationResult, null, 2);
        const blob = new Blob([reportContent], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = `inventory_${inventoryId}_validation_report.json`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(url);

        message.success('報告已下載');
    };

    // 全部展開/折疊
    const handleToggleAll = () => {
        if (!validationResult || !validationResult.checks) return;

        const allKeys = Object.keys(validationResult.checks);
        if (expandedPanels.length === allKeys.length) {
            setExpandedPanels([]);
        } else {
            setExpandedPanels(allKeys);
        }
    };

    // 渲染狀態圖標
    const renderStatusIcon = (status) => {
        switch (status) {
            case 'success':
                return <CheckCircleOutlined style={{ color: '#52c41a', fontSize: 20 }} />;
            case 'warning':
                return <WarningOutlined style={{ color: '#faad14', fontSize: 20 }} />;
            case 'error':
                return <CloseCircleOutlined style={{ color: '#ff4d4f', fontSize: 20 }} />;
            default:
                return <InfoCircleOutlined style={{ color: '#d9d9d9', fontSize: 20 }} />;
        }
    };

    // 獲取狀態標籤
    const getStatusTag = (status) => {
        const config = {
            success: { color: 'success', text: '通過' },
            warning: { color: 'warning', text: '警告' },
            error: { color: 'error', text: '失敗' },
            unknown: { color: 'default', text: '未檢查' }
        };
        const { color, text } = config[status] || config.unknown;
        return <Tag color={color}>{text}</Tag>;
    };

    // 檢查項目顯示名稱
    const getCheckDisplayName = (key) => {
        const names = {
            syntax: '語法驗證',
            structure: '結構完整性',
            host_config: '主機配置檢查',
            ip_addresses: 'IP 地址驗證',
            mac_addresses: 'MAC 地址驗證',
            uart_ssh: 'UART SSH 連線檢查',
            network_connectivity: '網路連線測試',
            ssh_authentication: 'SSH 認證測試',
            dhcp_records: 'DHCP 記錄比對',
            best_practices: '最佳實踐檢查',
            performance: '性能優化建議'
        };
        return names[key] || key;
    };

    // 計算進度百分比
    const calculateProgress = () => {
        if (!validationResult || !validationResult.summary) return 0;

        const { total_checks, passed } = validationResult.summary;
        if (total_checks === 0) return 0;

        return Math.round((passed / total_checks) * 100);
    };

    // 獲取狀態顏色
    const getStatusColor = (status) => {
        switch (status) {
            case 'success':
                return '#52c41a';
            case 'warning':
                return '#faad14';
            case 'error':
                return '#ff4d4f';
            default:
                return '#d9d9d9';
        }
    };

    // 格式化詳細信息標籤
    const formatDetailLabel = (key) => {
        const labels = {
            sections: 'Sections 數量',
            hosts: 'Hosts 數量',
            line_count: '總行數',
            total_groups: 'Groups 總數',
            parent_groups: '父 Groups',
            leaf_groups: '葉 Groups',
            issues: '問題列表',
            warnings: '警告列表',
            total_hosts: '主機總數',
            complete_hosts: '完整配置主機',
            incomplete_hosts: '不完整主機',
            missing_recommended: '缺少建議變數',
            total_ips: 'IP 總數',
            unique_ips: '唯一 IP',
            invalid_ips: '無效 IP',
            conflicts: 'IP 衝突',
            total_macs: 'MAC 總數',
            unique_macs: '唯一 MAC',
            invalid_macs: '無效 MAC',
            duplicates: 'MAC 重複',
            // UART SSH 檢查相關
            total: 'UART 主機總數',
            successful: '成功連接',
            failed: '失敗連接',
            skipped: '跳過檢查',
            connections: '連接詳情',
        };
        return labels[key] || key;
    };

    // 格式化詳細信息值
    const formatDetailValue = (key, value) => {
        // UART SSH 連接詳情的特殊處理
        if (key === 'connections' && Array.isArray(value)) {
            return (
                <div style={{ marginTop: 8 }}>
                    {value.map((conn, index) => (
                        <Card
                            key={index}
                            size="small"
                            style={{
                                marginBottom: 8,
                                backgroundColor: conn.status === 'success' ? '#f6ffed' : 
                                               conn.status === 'error' ? '#fff1f0' : '#fffbe6',
                                border: `1px solid ${conn.status === 'success' ? '#b7eb8f' : 
                                                     conn.status === 'error' ? '#ffccc7' : '#ffe58f'}`
                            }}
                        >
                            <Space direction="vertical" style={{ width: '100%' }}>
                                <div>
                                    <Text strong>{conn.hostname}</Text>
                                    {conn.status === 'success' && <CheckCircleOutlined style={{ color: '#52c41a', marginLeft: 8 }} />}
                                    {conn.status === 'error' && <CloseCircleOutlined style={{ color: '#ff4d4f', marginLeft: 8 }} />}
                                    {conn.status === 'warning' && <WarningOutlined style={{ color: '#faad14', marginLeft: 8 }} />}
                                </div>
                                <div>
                                    <Text type="secondary">UART 主機: </Text>
                                    <code style={{ backgroundColor: '#f5f5f5', padding: '2px 6px', borderRadius: 3 }}>
                                        {conn.uart_host}
                                    </code>
                                </div>
                                <div>
                                    <Text type="secondary">訊息: </Text>
                                    <span>{conn.message}</span>
                                </div>
                                {conn.details && Object.keys(conn.details).length > 0 && (
                                    <div style={{ fontSize: 12, color: '#8c8c8c' }}>
                                        {conn.details.uart_ip && <div>IP: {conn.details.uart_ip}</div>}
                                        {conn.details.uart_user && <div>User: {conn.details.uart_user}</div>}
                                        {conn.details.uart_port && <div>Port: {conn.details.uart_port}</div>}
                                        {conn.details.error && <div style={{ color: '#ff4d4f' }}>Error: {conn.details.error}</div>}
                                    </div>
                                )}
                            </Space>
                        </Card>
                    ))}
                </div>
            );
        }
        
        if (Array.isArray(value)) {
            if (value.length === 0) return '無';
            if (value.length > 5) {
                return (
                    <div>
                        <div>{value.slice(0, 5).map(v => <div key={JSON.stringify(v)}>{JSON.stringify(v)}</div>)}</div>
                        <Text type="secondary">...還有 {value.length - 5} 個</Text>
                    </div>
                );
            }
            return value.map(v => <div key={JSON.stringify(v)}>{JSON.stringify(v)}</div>);
        }
        if (typeof value === 'object') {
            return <pre style={{ fontSize: '12px' }}>{JSON.stringify(value, null, 2)}</pre>;
        }
        return String(value);
    };

    // 渲染未檢查狀態
    const renderEmptyState = () => (
        <Card>
            <div style={{ textAlign: 'center', padding: '40px 20px' }}>
                <InfoCircleOutlined style={{ fontSize: 48, color: '#1890ff', marginBottom: 16 }} />
                <Title level={4}>點擊「開始檢查」執行配置驗證</Title>
                <p style={{ color: '#8c8c8c', marginBottom: 24 }}>
                    檢查將包括：語法驗證、結構完整性、主機配置、IP/MAC 地址驗證、UART SSH 連線等
                </p>
                <ul style={{ textAlign: 'left', display: 'inline-block', color: '#595959' }}>
                    <li>✓ 語法驗證（INI 格式、Jinja2 模板）</li>
                    <li>✓ 結構完整性（Group 層級、循環依賴）</li>
                    <li>✓ 主機配置檢查（必要變數）</li>
                    <li>✓ IP 地址驗證（格式、衝突、DHCP 租約）</li>
                    <li>✓ MAC 地址驗證（格式、重複、DHCP 租約）</li>
                    <li>✓ UART SSH 連線檢查（認證、連接狀態）</li>
                </ul>
            </div>
        </Card>
    );

    // 渲染檢查總覽
    const renderOverviewCard = () => {
        if (!validationResult) return null;

        const { overall_status, summary } = validationResult;
        const progress = calculateProgress();

        return (
            <Card
                title={
                    <Space>
                        <span>📋 檢查總覽</span>
                    </Space>
                }
                style={{ marginBottom: 16 }}
            >
                <Row gutter={[16, 16]}>
                    <Col span={12}>
                        <Descriptions column={1} size="small">
                            <Descriptions.Item label="Inventory ID">
                                #{inventoryId}
                            </Descriptions.Item>
                            <Descriptions.Item label="檔案名稱">
                                {inventoryName || 'N/A'}
                            </Descriptions.Item>
                            {validationTime && (
                                <Descriptions.Item label="檢查時間">
                                    {validationTime.toLocaleString('zh-TW')}
                                </Descriptions.Item>
                            )}
                        </Descriptions>
                    </Col>

                    <Col span={12}>
                        <div style={{ textAlign: 'center' }}>
                            <Text strong style={{ fontSize: 16 }}>整體狀態</Text>
                            <div style={{ marginTop: 8 }}>
                                {renderStatusIcon(overall_status)}
                                <div style={{ marginTop: 4 }}>
                                    {getStatusTag(overall_status)}
                                </div>
                            </div>
                            <Progress
                                percent={progress}
                                status={overall_status === 'success' ? 'success' : 'active'}
                                strokeColor={getStatusColor(overall_status)}
                                style={{ marginTop: 8 }}
                            />
                            <Text type="secondary" style={{ fontSize: 12 }}>
                                {summary.passed}/{summary.total_checks} 通過
                            </Text>
                        </div>
                    </Col>
                </Row>

                <Divider style={{ margin: '16px 0' }} />

                <Row gutter={[16, 16]}>
                    <Col span={8}>
                        <Statistic
                            title="總檢查項"
                            value={summary.total_checks}
                            prefix={<InfoCircleOutlined />}
                        />
                    </Col>
                    <Col span={8}>
                        <Statistic
                            title="警告"
                            value={summary.warnings}
                            valueStyle={{ color: '#faad14' }}
                            prefix={<WarningOutlined />}
                        />
                    </Col>
                    <Col span={8}>
                        <Statistic
                            title="錯誤"
                            value={summary.errors}
                            valueStyle={{ color: '#ff4d4f' }}
                            prefix={<CloseCircleOutlined />}
                        />
                    </Col>
                </Row>
            </Card>
        );
    };

    // 渲染檢查項目列表
    const renderCheckItems = () => {
        if (!validationResult || !validationResult.checks) return null;

        const { checks } = validationResult;

        return (
            <Card
                title="✓ 檢查項目"
                extra={
                    <Button size="small" onClick={handleToggleAll}>
                        {expandedPanels.length === Object.keys(checks).length ? '全部折疊' : '全部展開'}
                    </Button>
                }
            >
                <Collapse
                    activeKey={expandedPanels}
                    onChange={setExpandedPanels}
                    ghost
                >
                    {Object.entries(checks).map(([key, checkData]) => {
                        const isChecked = checkData.status === 'success';
                        const hasError = checkData.status === 'error';
                        const hasWarning = checkData.status === 'warning';

                        return (
                            <Panel
                                key={key}
                                header={
                                    <div style={{
                                        display: 'flex',
                                        justifyContent: 'space-between',
                                        alignItems: 'center',
                                        padding: '8px 0'
                                    }}>
                                        <Space size="large">
                                            <Checkbox
                                                checked={isChecked}
                                                disabled
                                                style={{ pointerEvents: 'none' }}
                                            />
                                            <Text strong style={{ fontSize: 16 }}>
                                                {getCheckDisplayName(key)}
                                            </Text>
                                        </Space>
                                        <Space>
                                            {getStatusTag(checkData.status)}
                                            {renderStatusIcon(checkData.status)}
                                        </Space>
                                    </div>
                                }
                                style={{
                                    marginBottom: 16,
                                    backgroundColor: hasError ? '#fff1f0' : hasWarning ? '#fffbe6' : '#f6ffed',
                                    border: `1px solid ${hasError ? '#ffccc7' : hasWarning ? '#ffe58f' : '#b7eb8f'}`,
                                    borderRadius: 4,
                                }}
                            >
                                <div style={{ paddingLeft: 32 }}>
                                    <Descriptions column={1} size="small" bordered>
                                        <Descriptions.Item label="檢查值">
                                            <code style={{
                                                backgroundColor: '#f5f5f5',
                                                padding: '2px 6px',
                                                borderRadius: 3
                                            }}>
                                                {checkData.value || 'N/A'}
                                            </code>
                                        </Descriptions.Item>
                                        <Descriptions.Item label="狀態">
                                            {checkData.message}
                                        </Descriptions.Item>
                                    </Descriptions>

                                    {/* 詳細信息 */}
                                    {checkData.details && Object.keys(checkData.details).length > 0 && (
                                        <>
                                            <Divider orientation="left" style={{ fontSize: 14 }}>
                                                詳細資訊
                                            </Divider>
                                            <Descriptions column={1} size="small" bordered>
                                                {Object.entries(checkData.details).map(([detailKey, detailValue]) => (
                                                    <Descriptions.Item key={detailKey} label={formatDetailLabel(detailKey)}>
                                                        {formatDetailValue(detailKey, detailValue)}
                                                    </Descriptions.Item>
                                                ))}
                                            </Descriptions>
                                        </>
                                    )}

                                    {/* 建議 */}
                                    {checkData.suggestions && checkData.suggestions.length > 0 && (
                                        <>
                                            <Divider orientation="left" style={{ fontSize: 14 }}>
                                                建議
                                            </Divider>
                                            <ul style={{ marginLeft: 20 }}>
                                                {checkData.suggestions.map((suggestion, index) => (
                                                    <li key={index}>{suggestion}</li>
                                                ))}
                                            </ul>
                                        </>
                                    )}
                                </div>
                            </Panel>
                        );
                    })}
                </Collapse>
            </Card>
        );
    };

    return (
        <Drawer
            title={
                <Space>
                    <CheckCircleOutlined />
                    <span>Ansible Inventory 配置檢查</span>
                </Space>
            }
            placement="right"
            width={720}
            onClose={onClose}
            open={visible}
            extra={
                <Space>
                    <Button
                        icon={<DownloadOutlined />}
                        onClick={handleExportReport}
                        disabled={!validationResult}
                    >
                        導出報告
                    </Button>
                    <Button
                        type="primary"
                        icon={<SyncOutlined />}
                        onClick={handleValidate}
                        loading={loading}
                    >
                        {validationResult ? '重新檢查' : '開始檢查'}
                    </Button>
                </Space>
            }
        >
            <Spin spinning={loading} tip="正在執行檢查...">
                {!validationResult ? renderEmptyState() : (
                    <div>
                        {renderOverviewCard()}
                        {renderCheckItems()}
                    </div>
                )}
            </Spin>
        </Drawer>
    );
};

export default InventoryValidationDrawer;
