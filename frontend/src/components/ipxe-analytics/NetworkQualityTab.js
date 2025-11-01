import React, { useState, useEffect } from 'react';
import axios from 'axios';
import {
    Card,
    Row,
    Col,
    Statistic,
    Table,
    Tag,
    Spin,
    message,
    Select,
    Space,
    Typography,
    Alert,
    Empty,
} from 'antd';
import {
    CheckCircleOutlined,
    CloseCircleOutlined,
    ThunderboltOutlined,
    CloudServerOutlined,
    ApiOutlined,
    LockOutlined,
    DownloadOutlined,
    WarningOutlined,
} from '@ant-design/icons';
import NetworkQualityChart from '../NetworkQualityChart';

const { Text } = Typography;
const { Option } = Select;

const NetworkQualityTab = ({ serverId }) => {
    const [loading, setLoading] = useState(false);
    const [statistics, setStatistics] = useState(null);
    const [logs, setLogs] = useState([]);
    const [timeRange, setTimeRange] = useState(7); // 默認7天
    const [ipxeServer, setIpxeServer] = useState(null);

    useEffect(() => {
        fetchIPXEServer();
    }, [serverId]);

    useEffect(() => {
        if (ipxeServer) {
            fetchData();
            // 設置自動刷新（每30秒）
            const interval = setInterval(fetchData, 30000);
            return () => clearInterval(interval);
        }
    }, [timeRange, ipxeServer]);

    const fetchIPXEServer = async () => {
        try {
            if (serverId === 'all') {
                // 如果是 "all"，獲取第一個伺服器
                const response = await axios.get('/api/ipxe-servers/');
                const servers = response.data.results || response.data;
                if (servers && servers.length > 0) {
                    setIpxeServer(servers[0]);
                }
            } else {
                // 獲取特定伺服器
                const response = await axios.get(`/api/ipxe-servers/${serverId}/`);
                setIpxeServer(response.data);
            }
        } catch (error) {
            console.error('Error fetching IPXE server:', error);
            message.error('載入 IPXE 伺服器資訊失敗：' + error.message);
        }
    };

    const fetchData = async () => {
        if (!ipxeServer) return;
        
        setLoading(true);
        try {
            // 獲取統計資料
            const statsResponse = await axios.get(`/api/ipxe-network-quality/statistics/?days=${timeRange}&server_id=${ipxeServer.id}`);
            setStatistics(statsResponse.data);

            // 獲取記錄列表（處理分頁格式）
            const logsResponse = await axios.get(`/api/ipxe-network-quality/?days=${timeRange}&server_id=${ipxeServer.id}`);
            const logsData = logsResponse.data.results || logsResponse.data;
            setLogs(Array.isArray(logsData) ? logsData : []);
        } catch (error) {
            console.error('Error fetching IPXE network quality data:', error);
            message.error('載入 IPXE 網路品質數據失敗：' + error.message);
        } finally {
            setLoading(false);
        }
    };

    // 狀態標籤渲染
    const renderStatusTag = (status) => {
        const statusConfig = {
            success: { color: 'success', icon: <CheckCircleOutlined />, text: '正常' },
            partial: { color: 'warning', icon: <WarningOutlined />, text: '部分失敗' },
            failed: { color: 'error', icon: <CloseCircleOutlined />, text: '失敗' },
        };
        const config = statusConfig[status] || statusConfig.failed;
        return <Tag icon={config.icon} color={config.color}>{config.text}</Tag>;
    };

    // 表格列定義
    const columns = [
        {
            title: '時間',
            dataIndex: 'timestamp',
            key: 'timestamp',
            width: 180,
            render: (timestamp) => new Date(timestamp).toLocaleString('zh-TW'),
            sorter: (a, b) => new Date(a.timestamp) - new Date(b.timestamp),
        },
        {
            title: '狀態',
            dataIndex: 'status',
            key: 'status',
            width: 100,
            render: renderStatusTag,
            filters: [
                { text: '正常', value: 'success' },
                { text: '部分失敗', value: 'partial' },
                { text: '失敗', value: 'failed' },
            ],
            onFilter: (value, record) => record.status === value,
        },
        {
            title: 'Ping 延遲',
            dataIndex: 'ping_latency',
            key: 'ping_latency',
            width: 120,
            render: (latency) => latency ? `${latency.toFixed(2)} ms` : 'N/A',
            sorter: (a, b) => (a.ping_latency || 0) - (b.ping_latency || 0),
        },
        {
            title: '丟包率',
            dataIndex: 'ping_packet_loss',
            key: 'ping_packet_loss',
            width: 100,
            render: (loss) => {
                if (loss === null || loss === undefined) return 'N/A';
                const color = loss === 0 ? 'success' : loss < 5 ? 'warning' : 'error';
                return <Tag color={color}>{loss.toFixed(1)}%</Tag>;
            },
        },
        {
            title: 'HTTP 響應',
            dataIndex: 'http_response_time',
            key: 'http_response_time',
            width: 120,
            render: (time) => time ? `${time.toFixed(2)} ms` : 'N/A',
        },
        {
            title: 'HTTP 狀態',
            dataIndex: 'http_status_code',
            key: 'http_status_code',
            width: 100,
            render: (code) => {
                if (!code) return 'N/A';
                const color = code === 200 ? 'success' : 'error';
                return <Tag color={color}>{code}</Tag>;
            },
        },
        {
            title: 'SSH 響應',
            dataIndex: 'ssh_response_time',
            key: 'ssh_response_time',
            width: 120,
            render: (time) => time ? `${time.toFixed(2)} ms` : 'N/A',
        },
        {
            title: 'SSH 連接',
            dataIndex: 'ssh_connected',
            key: 'ssh_connected',
            width: 100,
            render: (connected) => {
                if (connected === null || connected === undefined) return 'N/A';
                return connected ? 
                    <Tag icon={<CheckCircleOutlined />} color="success">已連接</Tag> : 
                    <Tag icon={<CloseCircleOutlined />} color="error">斷開</Tag>;
            },
        },
        {
            title: '下載速度',
            dataIndex: 'download_speed',
            key: 'download_speed',
            width: 120,
            render: (speed) => speed ? `${speed.toFixed(2)} MB/s` : 'N/A',
        },
        {
            title: '錯誤訊息',
            dataIndex: 'error_message',
            key: 'error_message',
            ellipsis: true,
            render: (message) => message || '-',
        },
    ];

    if (loading && !statistics) {
        return (
            <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '400px' }}>
                <Spin size="large" tip="載入中..." />
            </div>
        );
    }

    if (!ipxeServer) {
        return (
            <Alert
                message="未找到 IPXE 伺服器"
                description="請先在 IPXE 管理頁面添加 IPXE 伺服器"
                type="warning"
                showIcon
                style={{ margin: '24px 0' }}
            />
        );
    }

    return (
        <div>
            {/* 時間範圍選擇器 */}
            <div style={{ marginBottom: '16px', display: 'flex', justifyContent: 'flex-end' }}>
                <Space>
                    <Text>時間範圍：</Text>
                    <Select value={timeRange} onChange={setTimeRange} style={{ width: 120 }}>
                        <Option value={1}>最近 1 天</Option>
                        <Option value={3}>最近 3 天</Option>
                        <Option value={7}>最近 7 天</Option>
                        <Option value={14}>最近 14 天</Option>
                    </Select>
                </Space>
            </div>

            {/* IPXE 伺服器資訊 */}
            <Alert
                message="網路品質監控資訊"
                description={
                    <Space direction="vertical">
                        <Text><strong>監控伺服器:</strong> {ipxeServer.name} ({ipxeServer.ip_address})</Text>
                        <Text type="secondary">每 5 分鐘自動檢測一次網路品質（Ping、HTTP、SSH、下載速度）</Text>
                    </Space>
                }
                type="info"
                showIcon
                style={{ marginBottom: '16px' }}
            />

            {/* 統計卡片 */}
            {statistics && (
                <>
                    <Row gutter={[16, 16]} style={{ marginBottom: '16px' }}>
                        <Col xs={24} sm={12} md={8} lg={6}>
                            <Card>
                                <Statistic
                                    title="總檢測次數"
                                    value={statistics.summary.total_records}
                                    prefix={<CloudServerOutlined />}
                                />
                            </Card>
                        </Col>
                        <Col xs={24} sm={12} md={8} lg={6}>
                            <Card>
                                <Statistic
                                    title="成功率"
                                    value={statistics.summary.success_rate}
                                    suffix="%"
                                    prefix={<CheckCircleOutlined />}
                                    valueStyle={{ color: statistics.summary.success_rate > 95 ? '#52c41a' : '#faad14' }}
                                />
                            </Card>
                        </Col>
                        <Col xs={24} sm={12} md={8} lg={6}>
                            <Card>
                                <Statistic
                                    title="平均 Ping 延遲"
                                    value={statistics.summary.avg_ping_latency}
                                    suffix="ms"
                                    prefix={<ThunderboltOutlined />}
                                    precision={2}
                                    valueStyle={{ color: statistics.summary.avg_ping_latency < 50 ? '#52c41a' : '#faad14' }}
                                />
                            </Card>
                        </Col>
                        <Col xs={24} sm={12} md={8} lg={6}>
                            <Card>
                                <Statistic
                                    title="平均丟包率"
                                    value={statistics.summary.avg_packet_loss}
                                    suffix="%"
                                    prefix={<WarningOutlined />}
                                    precision={2}
                                    valueStyle={{ color: statistics.summary.avg_packet_loss === 0 ? '#52c41a' : '#ff4d4f' }}
                                />
                            </Card>
                        </Col>
                    </Row>

                    <Row gutter={[16, 16]} style={{ marginBottom: '16px' }}>
                        <Col xs={24} sm={12} md={8}>
                            <Card>
                                <Statistic
                                    title="平均 HTTP 響應時間"
                                    value={statistics.summary.avg_http_response_time}
                                    suffix="ms"
                                    prefix={<ApiOutlined />}
                                    precision={2}
                                />
                            </Card>
                        </Col>
                        <Col xs={24} sm={12} md={8}>
                            <Card>
                                <Statistic
                                    title="平均 SSH 響應時間"
                                    value={statistics.summary.avg_ssh_response_time}
                                    suffix="ms"
                                    prefix={<LockOutlined />}
                                    precision={2}
                                />
                            </Card>
                        </Col>
                        <Col xs={24} sm={12} md={8}>
                            <Card>
                                <Statistic
                                    title="平均下載速度"
                                    value={statistics.summary.avg_download_speed}
                                    suffix="MB/s"
                                    prefix={<DownloadOutlined />}
                                    precision={2}
                                />
                            </Card>
                        </Col>
                    </Row>

                    {/* Ping 延遲趨勢圖 - 使用新的品質分級圖表 */}
                    {statistics.quality_trends && statistics.quality_trends.length > 0 ? (
                        <NetworkQualityChart
                            data={statistics.quality_trends
                                .filter(item => item.avg_ping_latency !== null && item.avg_ping_latency !== undefined)
                                .map(item => ({
                                    timestamp: item.timestamp,
                                    value: item.avg_ping_latency,
                                }))}
                            metricType="ping"
                            title="Ping 延遲"
                            unit="ms"
                        />
                    ) : (
                        <Card title="Ping 延遲趨勢" style={{ marginBottom: '16px' }}>
                            <Empty description="無數據" />
                        </Card>
                    )}

                    {/* HTTP 響應時間趨勢圖 - 使用新的品質分級圖表 */}
                    {statistics.quality_trends && statistics.quality_trends.length > 0 ? (
                        <NetworkQualityChart
                            data={statistics.quality_trends
                                .filter(item => item.avg_http_response_time !== null && item.avg_http_response_time !== undefined)
                                .map(item => ({
                                    timestamp: item.timestamp,
                                    value: item.avg_http_response_time,
                                }))}
                            metricType="http"
                            title="HTTP 響應時間"
                            unit="ms"
                        />
                    ) : (
                        <Card title="HTTP 響應時間" style={{ marginBottom: '16px' }}>
                            <Empty description="無數據" />
                        </Card>
                    )}

                    {/* SSH 響應時間趨勢圖 - 使用新的品質分級圖表 */}
                    {statistics.quality_trends && statistics.quality_trends.length > 0 ? (
                        <NetworkQualityChart
                            data={statistics.quality_trends
                                .filter(item => item.avg_ssh_response_time !== null && item.avg_ssh_response_time !== undefined)
                                .map(item => ({
                                    timestamp: item.timestamp,
                                    value: item.avg_ssh_response_time,
                                }))}
                            metricType="ssh"
                            title="SSH 響應時間"
                            unit="ms"
                        />
                    ) : (
                        <Card title="SSH 響應時間" style={{ marginBottom: '16px' }}>
                            <Empty description="無數據" />
                        </Card>
                    )}

                    {/* 丟包率趨勢圖 - 使用新的品質分級圖表 */}
                    {statistics.quality_trends && statistics.quality_trends.length > 0 ? (
                        <NetworkQualityChart
                            data={statistics.quality_trends
                                .filter(item => item.avg_packet_loss !== null && item.avg_packet_loss !== undefined)
                                .map(item => ({
                                    timestamp: item.timestamp,
                                    value: item.avg_packet_loss,
                                }))}
                            metricType="packet_loss"
                            title="丟包率"
                            unit="%"
                        />
                    ) : (
                        <Card title="丟包率趨勢" style={{ marginBottom: '16px' }}>
                            <Empty description="無數據" />
                        </Card>
                    )}

                    {/* 下載速度趨勢圖 - 使用新的品質分級圖表 */}
                    {statistics.quality_trends && statistics.quality_trends.length > 0 ? (
                        <NetworkQualityChart
                            data={statistics.quality_trends
                                .filter(item => item.avg_download_speed !== null && item.avg_download_speed !== undefined)
                                .map(item => ({
                                    timestamp: item.timestamp,
                                    value: item.avg_download_speed,
                                }))}
                            metricType="download_speed"
                            title="下載速度"
                            unit="MB/s"
                        />
                    ) : (
                        <Card title="下載速度趨勢" style={{ marginBottom: '16px' }}>
                            <Empty description="無數據" />
                        </Card>
                    )}
                </>
            )}

            {/* 檢測記錄表格 */}
            <Card 
                title="檢測記錄" 
                extra={
                    <Space>
                        <Text type="secondary">
                            共 {logs.length} 條記錄
                        </Text>
                    </Space>
                }
            >
                <Table
                    columns={columns}
                    dataSource={logs}
                    rowKey="id"
                    loading={loading}
                    pagination={{
                        pageSize: 10,
                        showSizeChanger: true,
                        showTotal: (total) => `共 ${total} 筆`,
                    }}
                    scroll={{ x: 1200 }}
                    size="small"
                />
            </Card>
        </div>
    );
};

export default NetworkQualityTab;
