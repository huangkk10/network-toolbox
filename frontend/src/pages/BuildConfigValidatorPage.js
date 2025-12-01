/**
 * Build 配置檢查頁面 - Check List 版本
 * 
 * 功能：
 * 1. 顯示 Build 基本資訊和檢查總覽
 * 2. 使用 Check List 風格展示檢查項目
 * 3. 支持展開/折疊詳細信息
 * 4. 提供重新檢查、導出報告等功能
 * 5. 智能展開（錯誤項目自動展開）
 */

import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
    Card,
    Checkbox,
    Collapse,
    Progress,
    Button,
    Descriptions,
    Tag,
    Spin,
    Space,
    Divider,
    message,
    Select,
    Statistic,
    Row,
    Col,
    Typography,
} from 'antd';
import {
    CheckCircleOutlined,
    CloseCircleOutlined,
    WarningOutlined,
    SyncOutlined,
    LeftOutlined,
    InfoCircleOutlined,
    DownloadOutlined,
    ClockCircleOutlined,
    FileTextOutlined,
} from '@ant-design/icons';
import axios from 'axios';
import { AnsibleConfigDrawer } from '../components/AnsibleConfig';

const { Panel } = Collapse;
const { Option } = Select;
const { Title, Text } = Typography;

const BuildConfigValidatorPage = () => {
    const { buildId } = useParams();
    const navigate = useNavigate();

    // 狀態管理
    const [loading, setLoading] = useState(false);
    const [initialLoading, setInitialLoading] = useState(true);  // 新增：初始載入狀態
    const [buildInfo, setBuildInfo] = useState(null);
    const [validationResult, setValidationResult] = useState(null);
    const [dhcpServers, setDhcpServers] = useState([]);
    const [selectedDhcpServer, setSelectedDhcpServer] = useState(null);
    const [expandedPanels, setExpandedPanels] = useState([]);
    const [validationTime, setValidationTime] = useState(null);
    const [isAutoTriggered, setIsAutoTriggered] = useState(false);  // 新增：是否為自動檢查
    const [ansibleConfigDrawer, setAnsibleConfigDrawer] = useState({
        visible: false,
        jobId: null,
        jobName: null,
        buildNumber: null,
        hostname: null,
    });

    // 獲取 Build 基本資訊和已有的檢查結果
    useEffect(() => {
        if (buildId) {
            fetchBuildInfo();
            fetchExistingValidation();  // 新增：優先獲取已有結果
            fetchDhcpServers();
        } else {
            message.error('無效的 Build ID');
            setInitialLoading(false);
        }
    // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [buildId]);

    // 智能展開：錯誤項目自動展開
    useEffect(() => {
        if (validationResult && validationResult.checks) {
            const errorKeys = Object.keys(validationResult.checks).filter(
                key => validationResult.checks[key].status === 'error' || 
                       validationResult.checks[key].status === 'warning'
            );
            setExpandedPanels(errorKeys);
        }
    }, [validationResult]);

    // 新增：獲取已有的檢查結果
    const fetchExistingValidation = async () => {
        try {
            // 先檢查是否有結果
            const checkResponse = await axios.get(`/api/jenkins-builds/${buildId}/has_config_validation/`);
            
            if (checkResponse.data.has_validation) {
                // 有結果，獲取完整內容
                const resultResponse = await axios.get(`/api/jenkins-builds/${buildId}/config_validation/`);
                setValidationResult(resultResponse.data);
                
                // 設置檢查時間
                if (resultResponse.data.build_info?.validated_at) {
                    setValidationTime(new Date(resultResponse.data.build_info.validated_at));
                }
                
                // 檢查是否為自動觸發
                if (resultResponse.data.build_info?.auto_triggered) {
                    setIsAutoTriggered(true);
                    message.info('此檢查結果由系統自動生成');
                }
            }
        } catch (error) {
            // 沒有結果，顯示手動檢查按鈕
            console.log('No existing validation result, manual check required');
        } finally {
            setInitialLoading(false);
        }
    };

    const fetchBuildInfo = async () => {
        setLoading(true);
        try {
            const response = await axios.get(`/api/jenkins-builds/${buildId}/`);
            setBuildInfo(response.data);
        } catch (error) {
            console.error('獲取 Build 資訊失敗:', error);
            message.error('獲取 Build 資訊失敗');
        } finally {
            setLoading(false);
        }
    };

    const fetchDhcpServers = async () => {
        try {
            const response = await axios.get('/api/dhcp-servers/');
            if (Array.isArray(response.data)) {
                setDhcpServers(response.data);
            } else {
                setDhcpServers([]);
            }
        } catch (error) {
            console.error('獲取 DHCP Server 列表失敗:', error);
            setDhcpServers([]);
        }
    };

    // 執行配置檢查
    const handleValidate = async () => {
        setLoading(true);
        try {
            const payload = selectedDhcpServer ? { dhcp_server_id: selectedDhcpServer } : {};
            
            const response = await axios.post(`/api/jenkins-builds/${buildId}/validate_config/`, payload);
            
            setValidationResult(response.data);
            setValidationTime(new Date());
            setIsAutoTriggered(false);  // 手動檢查
            message.success('配置檢查完成');
        } catch (error) {
            console.error('配置檢查失敗:', error);
            message.error('配置檢查失敗：' + (error.response?.data?.message || error.message));
        } finally {
            setLoading(false);
        }
    };

    // 返回上一頁
    const handleBack = () => {
        navigate(-1);
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
        link.download = `build_${buildId}_validation_report.json`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(url);
        
        message.success('報告已下載');
    };

    // 查看 Ansible 配置
    const handleViewAnsibleConfig = () => {
        if (!buildInfo || !buildInfo.job || !buildInfo.job_name) {
            message.warning('Build 資訊不完整，無法查看配置');
            return;
        }
        
        setAnsibleConfigDrawer({
            visible: true,
            jobId: buildInfo.job,  // API 返回的是 job (ID)
            jobName: buildInfo.job_name,
            buildNumber: buildInfo.build_number,
            hostname: buildInfo.job_name,
        });
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
                return <CheckCircleOutlined style={{ color: '#52c41a', fontSize: '20px' }} />;
            case 'warning':
                return <WarningOutlined style={{ color: '#faad14', fontSize: '20px' }} />;
            case 'error':
                return <CloseCircleOutlined style={{ color: '#ff4d4f', fontSize: '20px' }} />;
            default:
                return <InfoCircleOutlined style={{ color: '#d9d9d9', fontSize: '20px' }} />;
        }
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

    // 獲取狀態標籤
    const getStatusTag = (status) => {
        const config = {
            success: { color: 'success', text: '成功' },
            warning: { color: 'warning', text: '警告' },
            error: { color: 'error', text: '錯誤' },
            unknown: { color: 'default', text: '未檢查' },
        };
        const { color, text } = config[status] || config.unknown;
        return <Tag color={color}>{text}</Tag>;
    };

    // 檢查項目顯示名稱
    const getItemDisplayName = (item) => {
        const names = {
            host_ip: 'HOST_IP 檢查',
            host_mac: 'HOST_MAC 檢查',
            uart_ip: 'UART_IP 檢查',
            uart_ssh: 'UART SSH 連線檢查',
            nas_connection: 'NAS 連線檢查',
            mdt_web: 'MDT Web 檢查',
        };
        return names[item] || item;
    };

    // 計算進度百分比
    const calculateProgress = () => {
        if (!validationResult || !validationResult.summary) return 0;
        
        const { total_checks, passed } = validationResult.summary;
        if (total_checks === 0) return 0;
        
        return Math.round((passed / total_checks) * 100);
    };

    // 渲染檢查總覽
    const renderOverviewCard = () => {
        if (!validationResult) return null;

        const { overall_status, config_source, summary, build_info } = validationResult;
        const progress = calculateProgress();

        return (
            <Card 
                title={
                    <Space>
                        <span>📋 檢查總覽</span>
                        {(isAutoTriggered || build_info?.auto_triggered) && (
                            <Tag color="blue">自動檢查</Tag>
                        )}
                    </Space>
                }
                style={{ marginBottom: '24px' }}
            >
                <Row gutter={[16, 16]}>
                    <Col xs={24} sm={12} md={8}>
                        <Descriptions column={1} size="small">
                            <Descriptions.Item label="Build ID">
                                #{buildId}
                            </Descriptions.Item>
                            <Descriptions.Item label="Job 名稱">
                                {buildInfo?.job_name || 'N/A'}
                            </Descriptions.Item>
                            <Descriptions.Item label="配置來源">
                                <Tag color="blue">
                                    {config_source === 'ansible_inventory' ? 'Ansible Inventory' : '資料庫'}
                                </Tag>
                            </Descriptions.Item>
                        </Descriptions>
                    </Col>
                    
                    <Col xs={24} sm={12} md={8}>
                        <div style={{ textAlign: 'center' }}>
                            <Text strong style={{ fontSize: '16px' }}>整體狀態</Text>
                            <div style={{ marginTop: '8px' }}>
                                {renderStatusIcon(overall_status)}
                                <div style={{ marginTop: '4px' }}>
                                    {getStatusTag(overall_status)}
                                </div>
                            </div>
                            <Progress 
                                percent={progress} 
                                status={overall_status === 'success' ? 'success' : 'active'}
                                strokeColor={getStatusColor(overall_status)}
                                style={{ marginTop: '8px' }}
                            />
                            <Text type="secondary" style={{ fontSize: '12px' }}>
                                {summary.passed}/{summary.total_checks} 通過
                            </Text>
                        </div>
                    </Col>
                    
                    <Col xs={24} sm={24} md={8}>
                        <Space direction="vertical" style={{ width: '100%' }}>
                            <Button 
                                type="primary" 
                                icon={<SyncOutlined />} 
                                onClick={handleValidate}
                                loading={loading}
                                block
                            >
                                重新檢查
                            </Button>
                            <Button 
                                icon={<DownloadOutlined />} 
                                onClick={handleExportReport}
                                block
                            >
                                導出報告
                            </Button>
                        </Space>
                    </Col>
                </Row>
            </Card>
        );
    };

    // 渲染檢查項目
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
                style={{ marginBottom: '24px' }}
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
                                                style={{ 
                                                    pointerEvents: 'none',
                                                }}
                                            />
                                            <Text strong style={{ fontSize: '16px' }}>
                                                {getItemDisplayName(key)}
                                            </Text>
                                        </Space>
                                        <Space>
                                            {getStatusTag(checkData.status)}
                                            {renderStatusIcon(checkData.status)}
                                        </Space>
                                    </div>
                                }
                                style={{
                                    marginBottom: '16px',
                                    backgroundColor: hasError ? '#fff1f0' : hasWarning ? '#fffbe6' : '#f6ffed',
                                    border: `1px solid ${hasError ? '#ffccc7' : hasWarning ? '#ffe58f' : '#b7eb8f'}`,
                                    borderRadius: '4px',
                                }}
                            >
                                <div style={{ paddingLeft: '32px' }}>
                                    <Descriptions column={1} size="small" bordered>
                                        <Descriptions.Item label="檢查值">
                                            <code style={{ 
                                                backgroundColor: '#f5f5f5', 
                                                padding: '2px 6px',
                                                borderRadius: '3px'
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
                                            <Divider orientation="left" style={{ fontSize: '14px' }}>
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
                                            <Divider orientation="left" style={{ fontSize: '14px' }}>
                                                建議
                                            </Divider>
                                            <ul style={{ marginLeft: '20px' }}>
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

    // 渲染統計卡片
    const renderStatisticsCard = () => {
        if (!validationResult || !validationResult.summary) return null;

        const { summary } = validationResult;

        return (
            <Card title="📊 檢查統計" style={{ marginBottom: '24px' }}>
                <Row gutter={[16, 16]}>
                    <Col xs={24} sm={8}>
                        <Statistic
                            title="成功"
                            value={summary.passed}
                            prefix={<CheckCircleOutlined style={{ color: '#52c41a' }} />}
                            suffix={`/ ${summary.total_checks} 項`}
                            valueStyle={{ color: '#52c41a' }}
                        />
                    </Col>
                    <Col xs={24} sm={8}>
                        <Statistic
                            title="警告"
                            value={summary.warnings}
                            prefix={<WarningOutlined style={{ color: '#faad14' }} />}
                            suffix="項"
                            valueStyle={{ color: '#faad14' }}
                        />
                    </Col>
                    <Col xs={24} sm={8}>
                        <Statistic
                            title="錯誤"
                            value={summary.errors}
                            prefix={<CloseCircleOutlined style={{ color: '#ff4d4f' }} />}
                            suffix="項"
                            valueStyle={{ color: '#ff4d4f' }}
                        />
                    </Col>
                </Row>
                
                {validationTime && (
                    <div style={{ marginTop: '16px', textAlign: 'center' }}>
                        <Text type="secondary">
                            <ClockCircleOutlined /> 最後檢查時間: {validationTime.toLocaleString('zh-TW')}
                        </Text>
                    </div>
                )}
            </Card>
        );
    };

    // 格式化詳細信息標籤
    const formatDetailLabel = (key) => {
        const labels = {
            ip_address: 'IP 地址',
            mac_address: 'MAC 地址',
            hostname: '主機名稱',
            dhcp_server: 'DHCP Server',
            dhcp_hostname: 'DHCP 主機名稱',
            lease_start: '租約開始',
            lease_end: '租約到期',
            is_active: '租約狀態',
            type: '類型',
            normalized: '標準化格式',
            dhcp_mac: 'DHCP 租約 MAC',
            match: 'MAC 匹配',
            config_mac: '配置 MAC',
            ip: 'IP 地址',
            user: '用戶名稱',
            port: 'SSH 端口',
            password_set: '密碼已設置',
            connected: '連線狀態',
            connection_time: '連線時間',
            error: '錯誤信息',
            // NAS 連線檢查相關
            log_file_path: '日誌檔案路徑',
            storage_dir: '儲存目錄',
            dir_exists: '目錄存在',
            file_exists: '檔案存在',
            dir_readable: '目錄可讀',
            dir_writable: '目錄可寫',
            connection_status: '連線狀態',
            response_time_ms: '響應時間 (ms)',
            upload_speed_mbps: '上傳速度 (MB/s)',
            download_speed_mbps: '下載速度 (MB/s)',
            error_message: '錯誤訊息',
            connection_test: '連線測試',
            test_error: '測試錯誤',
            // MDT Web 檢查相關
            device_number: '設備編號',
            dhcp_server_ip: 'DHCP Server IP',
            mdt_web_ip: 'MDT Web IP',
            mdt_web_accessible: 'MDT Web 可訪問',
            device_found: '設備已找到',
            config_matches: '配置一致',
            differences: '配置差異',
            is_unknown_network: '未知網段',
            connection_error: '連線錯誤',
        };
        return labels[key] || key;
    };

    // 格式化詳細信息值
    const formatDetailValue = (key, value) => {
        if (value === true) return <Tag color="success">是</Tag>;
        if (value === false) return <Tag color="default">否</Tag>;
        if (key === 'lease_start' || key === 'lease_end') {
            return value ? new Date(value).toLocaleString('zh-TW') : 'N/A';
        }
        if (key === 'is_active') {
            return value ? <Tag color="success">活躍</Tag> : <Tag color="default">非活躍</Tag>;
        }
        if (key === 'connected') {
            return value ? <Tag color="success">已連接</Tag> : <Tag color="error">未連接</Tag>;
        }
        if (key === 'password_set') {
            return value ? <Tag color="success">已設置</Tag> : <Tag color="warning">未設置</Tag>;
        }
        if (key === 'type') {
            if (value === 'ip') return <Tag color="blue">IP 地址</Tag>;
            if (value === 'hostname') return <Tag color="purple">主機名稱</Tag>;
            if (value === 'resolved_from_hostname') return <Tag color="cyan">從主機名稱解析</Tag>;
            return <Tag>{value}</Tag>;
        }
        // NAS 連線檢查相關
        if (key === 'dir_exists' || key === 'file_exists' || key === 'dir_readable' || key === 'dir_writable') {
            return value ? <Tag color="success">是</Tag> : <Tag color="error">否</Tag>;
        }
        if (key === 'connection_status') {
            if (value === 'success') return <Tag color="success">成功</Tag>;
            if (value === 'error' || value === 'failed') return <Tag color="error">失敗</Tag>;
            return <Tag color="default">{value || 'N/A'}</Tag>;
        }
        if (key === 'response_time_ms') {
            return value ? `${value.toFixed(1)} ms` : 'N/A';
        }
        if (key === 'upload_speed_mbps' || key === 'download_speed_mbps') {
            return value ? `${value.toFixed(2)} MB/s` : 'N/A';
        }
        // MDT Web 檢查相關
        if (key === 'mdt_web_accessible' || key === 'device_found' || key === 'config_matches') {
            return value ? <Tag color="success">是</Tag> : <Tag color="error">否</Tag>;
        }
        if (key === 'is_unknown_network') {
            return value ? <Tag color="warning">是</Tag> : <Tag color="default">否</Tag>;
        }
        if (key === 'differences' && Array.isArray(value)) {
            if (value.length === 0) return <Tag color="success">無差異</Tag>;
            return (
                <ul style={{ margin: 0, paddingLeft: '20px' }}>
                    {value.map((diff, idx) => (
                        <li key={idx}>
                            <strong>{diff.field}</strong>: 
                            Inventory: <code>{diff.inventory_value || 'N/A'}</code>, 
                            MDT: <code>{diff.mdt_web_value || 'N/A'}</code>
                        </li>
                    ))}
                </ul>
            );
        }
        return String(value || 'N/A');
    };

    // 初始載入中
    if (initialLoading) {
        return (
            <div style={{ padding: '24px', textAlign: 'center' }}>
                <Spin size="large" tip="載入檢查結果中..." />
            </div>
        );
    }

    if (loading && !buildInfo) {
        return (
            <div style={{ padding: '24px', textAlign: 'center' }}>
                <Spin size="large" tip="載入中..." />
            </div>
        );
    };

    return (
        <div style={{ padding: '24px', background: '#f0f2f5', minHeight: '100vh' }}>
            {/* 頁面標題 */}
            <Card style={{ marginBottom: '24px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <Space>
                        <Button icon={<LeftOutlined />} onClick={handleBack}>
                            返回
                        </Button>
                        <Divider type="vertical" />
                        <Title level={2} style={{ margin: 0 }}>
                            Build 配置檢查 #{buildId}
                        </Title>
                    </Space>
                    
                    {/* 查看配置按鈕 */}
                    <Button 
                        icon={<FileTextOutlined />} 
                        onClick={handleViewAnsibleConfig}
                        disabled={!buildInfo || !buildInfo.job}
                    >
                        查看配置
                    </Button>
                </div>
            </Card>

            {/* 執行檢查區域 */}
            {!validationResult && (
                <Card title="執行檢查" style={{ marginBottom: '24px' }}>
                    <Space direction="vertical" style={{ width: '100%' }}>
                        {buildInfo && (
                            <Descriptions column={2} size="small">
                                <Descriptions.Item label="Job 名稱">
                                    {buildInfo.job_name}
                                </Descriptions.Item>
                                <Descriptions.Item label="Build 編號">
                                    #{buildInfo.build_number}
                                </Descriptions.Item>
                            </Descriptions>
                        )}
                        <Divider />
                        <div>
                            <Text strong>指定 DHCP Server（可選）：</Text>
                            <Select
                                placeholder="選擇 DHCP Server（留空則自動選擇）"
                                allowClear
                                style={{ width: '100%', marginTop: '8px' }}
                                value={selectedDhcpServer}
                                onChange={setSelectedDhcpServer}
                            >
                                {dhcpServers.map((server) => (
                                    <Option key={server.id} value={server.id}>
                                        {server.name} ({server.ip_address})
                                    </Option>
                                ))}
                            </Select>
                        </div>
                        <Button
                            type="primary"
                            icon={<SyncOutlined />}
                            onClick={handleValidate}
                            loading={loading}
                            size="large"
                            block
                        >
                            開始檢查
                        </Button>
                    </Space>
                </Card>
            )}

            {/* 檢查結果 */}
            {validationResult && (
                <>
                    {renderOverviewCard()}
                    {renderCheckItems()}
                    {renderStatisticsCard()}
                </>
            )}
            
            {/* Ansible 配置 Drawer */}
            <AnsibleConfigDrawer
                visible={ansibleConfigDrawer.visible}
                onClose={() => setAnsibleConfigDrawer({ ...ansibleConfigDrawer, visible: false })}
                jobId={ansibleConfigDrawer.jobId}
                jobName={ansibleConfigDrawer.jobName}
                buildNumber={ansibleConfigDrawer.buildNumber}
                hostname={ansibleConfigDrawer.hostname}
            />
        </div>
    );
};

export default BuildConfigValidatorPage;
