import React, { useState, useEffect } from 'react';
import { 
    Card, Select, Input, Button, Space, Tag, Empty, Spin, 
    Radio, message, Pagination, DatePicker, Row, Col, Statistic 
} from 'antd';
import {
    DownloadOutlined,
    ReloadOutlined,
    InfoCircleOutlined,
    WarningOutlined,
    CloseCircleOutlined,
    ClearOutlined,
} from '@ant-design/icons';
import axios from 'axios';
import dayjs from 'dayjs';
import './LogsTab.css';

const { Option } = Select;
const { RangePicker } = DatePicker;

const LogsTab = ({ serverId }) => {
    const [logs, setLogs] = useState([]);
    const [loading, setLoading] = useState(false);
    const [syncing, setSyncing] = useState(false);
    const [logLevel, setLogLevel] = useState('ALL');
    const [keyword, setKeyword] = useState('');
    const [source, setSource] = useState('database');
    const [timeRange, setTimeRange] = useState('today');
    const [customDateRange, setCustomDateRange] = useState(null);
    
    const [currentPage, setCurrentPage] = useState(1);
    const [pageSize, setPageSize] = useState(20);
    const [total, setTotal] = useState(0);
    const [totalPages, setTotalPages] = useState(0);
    
    const [statistics, setStatistics] = useState({
        total: 0,
        info: 0,
        warn: 0,
        error: 0,
        debug: 0,
    });

    useEffect(() => {
        if (serverId && serverId !== 'all') {
            loadLogs();
            setCurrentPage(1);
        }
    }, [serverId, logLevel, keyword, source, timeRange, customDateRange]);

    useEffect(() => {
        if (serverId && serverId !== 'all' && currentPage > 0) {
            loadLogs();
        }
    }, [currentPage, pageSize]);

    const loadLogs = async () => {
        if (!serverId || serverId === 'all') {
            message.warning('請先選擇 DHCP Server');
            return;
        }

        setLoading(true);

        try {
            const params = {
                server: serverId,
                source: source,
                page: currentPage,
                page_size: pageSize,
            };

            if (logLevel && logLevel !== 'ALL') {
                params.level = logLevel;
            }

            if (keyword) {
                params.keyword = keyword;
            }

            if (customDateRange && customDateRange[0] && customDateRange[1]) {
                params.start_time = customDateRange[0].format('YYYY-MM-DD HH:mm:ss');
                params.end_time = customDateRange[1].format('YYYY-MM-DD HH:mm:ss');
            } else if (timeRange) {
                params.time_range = timeRange;
            }

            const response = await axios.get('/api/dhcp-analytics/logs/', { params });
            
            if (response.data) {
                setLogs(response.data.logs || []);
                setTotal(response.data.total || 0);
                setTotalPages(response.data.total_pages || 0);
                setStatistics(response.data.statistics || {
                    total: 0,
                    info: 0,
                    warn: 0,
                    error: 0,
                    debug: 0,
                });
            }
        } catch (error) {
            console.error('載入日誌失敗:', error);
            message.error('載入日誌失敗：' + (error.response?.data?.error || error.message));
        } finally {
            setLoading(false);
        }
    };

    const handleSyncLogs = async () => {
        if (!serverId || serverId === 'all') {
            message.warning('請先選擇 DHCP Server');
            return;
        }

        setSyncing(true);
        try {
            const response = await axios.post('/api/dhcp-servers/' + serverId + '/sync-logs/');
            message.success('日誌同步成功！新增 ' + response.data.stats.created + ' 筆');
            
            loadLogs();
        } catch (error) {
            console.error('同步日誌失敗:', error);
            message.error('同步日誌失敗：' + (error.response?.data?.error || error.message));
        } finally {
            setSyncing(false);
        }
    };

    const handleExport = () => {
        if (logs.length === 0) {
            message.warning('沒有日誌可以匯出');
            return;
        }

        const csvHeader = 'Timestamp,Level,Event,Message\n';
        const csvRows = logs.map(log => {
            const timestamp = log.timestamp || '-';
            const level = log.level || '-';
            const event = log.event || '-';
            const msg = (log.message || '').replace(/,/g, ';').replace(/"/g, '""');
            return '"' + timestamp + '","' + level + '","' + event + '","' + msg + '"';
        }).join('\n');

        const csvContent = csvHeader + csvRows;
        const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
        const link = document.createElement('a');
        link.href = URL.createObjectURL(blob);
        link.download = 'dhcp_logs_' + dayjs().format('YYYYMMDDHHmmss') + '.csv';
        link.click();

        message.success('日誌已匯出');
    };

    const handleClear = () => {
        setLogLevel('ALL');
        setKeyword('');
        setTimeRange('today');
        setCustomDateRange(null);
        setCurrentPage(1);
    };

    const getLevelTag = (level) => {
        const levelConfig = {
            'INFO': { color: 'blue', icon: <InfoCircleOutlined /> },
            'WARN': { color: 'orange', icon: <WarningOutlined /> },
            'ERROR': { color: 'red', icon: <CloseCircleOutlined /> },
            'DEBUG': { color: 'default', icon: <InfoCircleOutlined /> },
        };

        const config = levelConfig[level] || levelConfig['INFO'];
        return (
            <Tag color={config.color} icon={config.icon}>
                {level}
            </Tag>
        );
    };

    const formatTimestamp = (timestamp) => {
        if (!timestamp) return '-';
        return dayjs(timestamp).format('YYYY-MM-DD HH:mm:ss');
    };

    return (
        <div>
            <Row gutter={16} style={{ marginBottom: '16px' }}>
                <Col xs={24} sm={12} md={6}>
                    <Card bordered={false}>
                        <Statistic
                            title="總日誌數"
                            value={statistics.total}
                            valueStyle={{ color: '#1890ff' }}
                        />
                    </Card>
                </Col>
                <Col xs={24} sm={12} md={6}>
                    <Card bordered={false}>
                        <Statistic
                            title="錯誤 (ERROR)"
                            value={statistics.error}
                            valueStyle={{ color: '#ff4d4f' }}
                            prefix={<CloseCircleOutlined />}
                        />
                    </Card>
                </Col>
                <Col xs={24} sm={12} md={6}>
                    <Card bordered={false}>
                        <Statistic
                            title="警告 (WARN)"
                            value={statistics.warn}
                            valueStyle={{ color: '#faad14' }}
                            prefix={<WarningOutlined />}
                        />
                    </Card>
                </Col>
                <Col xs={24} sm={12} md={6}>
                    <Card bordered={false}>
                        <Statistic
                            title="資訊 (INFO)"
                            value={statistics.info}
                            valueStyle={{ color: '#52c41a' }}
                            prefix={<InfoCircleOutlined />}
                        />
                    </Card>
                </Col>
            </Row>

            <Card
                title="DHCP Server 日誌"
                extra={
                    <Space>
                        <Button
                            type="primary"
                            icon={<ReloadOutlined />}
                            onClick={handleSyncLogs}
                            loading={syncing}
                        >
                            同步日誌
                        </Button>
                        <Button
                            icon={<ReloadOutlined />}
                            onClick={loadLogs}
                            loading={loading}
                        >
                            重新載入
                        </Button>
                        <Button
                            icon={<DownloadOutlined />}
                            onClick={handleExport}
                            disabled={logs.length === 0}
                        >
                            匯出 CSV
                        </Button>
                    </Space>
                }
            >
                <Space direction="vertical" style={{ width: '100%', marginBottom: '16px' }}>
                    <Row gutter={[16, 16]}>
                        <Col xs={24} sm={12} md={6}>
                            <div style={{ marginBottom: '8px' }}>資料來源：</div>
                            <Select
                                style={{ width: '100%' }}
                                value={source}
                                onChange={(value) => {
                                    setSource(value);
                                    setCurrentPage(1);
                                }}
                            >
                                <Option value="database">資料庫（快速）</Option>
                                <Option value="remote">SSH 即時查詢</Option>
                            </Select>
                        </Col>

                        <Col xs={24} sm={12} md={6}>
                            <div style={{ marginBottom: '8px' }}>時間範圍：</div>
                            <Radio.Group
                                value={timeRange}
                                onChange={(e) => {
                                    setTimeRange(e.target.value);
                                    setCustomDateRange(null);
                                    setCurrentPage(1);
                                }}
                                buttonStyle="solid"
                                style={{ width: '100%' }}
                            >
                                <Radio.Button value="today" style={{ width: '25%', textAlign: 'center' }}>今天</Radio.Button>
                                <Radio.Button value="1d" style={{ width: '25%', textAlign: 'center' }}>1天</Radio.Button>
                                <Radio.Button value="3d" style={{ width: '25%', textAlign: 'center' }}>3天</Radio.Button>
                                <Radio.Button value="7d" style={{ width: '25%', textAlign: 'center' }}>7天</Radio.Button>
                            </Radio.Group>
                        </Col>

                        <Col xs={24} sm={12} md={6}>
                            <div style={{ marginBottom: '8px' }}>自訂時間範圍：</div>
                            <RangePicker
                                style={{ width: '100%' }}
                                showTime
                                format="YYYY-MM-DD HH:mm"
                                value={customDateRange}
                                onChange={(dates) => {
                                    setCustomDateRange(dates);
                                    if (dates) {
                                        setTimeRange(null);
                                    }
                                    setCurrentPage(1);
                                }}
                                placeholder={['開始時間', '結束時間']}
                            />
                        </Col>

                        <Col xs={24} sm={12} md={6}>
                            <div style={{ marginBottom: '8px' }}>日誌等級：</div>
                            <Select
                                style={{ width: '100%' }}
                                value={logLevel}
                                onChange={(value) => {
                                    setLogLevel(value);
                                    setCurrentPage(1);
                                }}
                            >
                                <Option value="ALL">全部</Option>
                                <Option value="INFO">INFO</Option>
                                <Option value="WARN">WARN</Option>
                                <Option value="ERROR">ERROR</Option>
                                <Option value="DEBUG">DEBUG</Option>
                            </Select>
                        </Col>
                    </Row>

                    <Row gutter={[16, 16]}>
                        <Col xs={24} sm={18}>
                            <Input
                                placeholder="搜尋關鍵字（訊息、事件）..."
                                value={keyword}
                                onChange={(e) => setKeyword(e.target.value)}
                                onPressEnter={() => {
                                    setCurrentPage(1);
                                    loadLogs();
                                }}
                                allowClear
                            />
                        </Col>
                        <Col xs={24} sm={6}>
                            <Button
                                icon={<ClearOutlined />}
                                onClick={handleClear}
                                block
                            >
                                清除篩選
                            </Button>
                        </Col>
                    </Row>
                </Space>

                <Spin spinning={loading}>
                    {logs.length === 0 ? (
                        <Empty description="沒有日誌資料" />
                    ) : (
                        <div>
                            <div className="log-container" style={{ 
                                maxHeight: '800px', 
                                overflow: 'auto',
                                background: '#fafafa',
                                padding: '16px',
                                borderRadius: '4px',
                                fontFamily: 'monospace',
                                fontSize: '13px',
                            }}>
                                {logs.map((log, index) => (
                                    <div
                                        key={index}
                                        style={{
                                            marginBottom: '6px',
                                            padding: '6px 10px',
                                            background: '#fff',
                                            borderRadius: '4px',
                                            borderLeft: '4px solid ' + (
                                                log.level === 'ERROR' ? '#ff4d4f' :
                                                log.level === 'WARN' ? '#faad14' :
                                                log.level === 'DEBUG' ? '#d9d9d9' :
                                                '#52c41a'
                                            ),
                                            display: 'flex',
                                            alignItems: 'center',
                                            gap: '12px',
                                        }}
                                    >
                                        <span style={{ color: '#595959', fontWeight: '500', whiteSpace: 'nowrap' }}>
                                            {formatTimestamp(log.timestamp)}
                                        </span>
                                        {getLevelTag(log.level)}
                                        {log.event && (
                                            <Tag color="purple">{log.event}</Tag>
                                        )}
                                        <span style={{ color: '#262626', fontWeight: '500', flex: 1, wordBreak: 'break-all' }}>
                                            {log.message}
                                        </span>
                                    </div>
                                ))}
                            </div>

                            <div style={{ marginTop: '16px', textAlign: 'right' }}>
                                <Pagination
                                    current={currentPage}
                                    pageSize={pageSize}
                                    total={total}
                                    onChange={(page, size) => {
                                        setCurrentPage(page);
                                        setPageSize(size);
                                    }}
                                    showSizeChanger
                                    showQuickJumper
                                    showTotal={(total) => '共 ' + total + ' 筆日誌'}
                                    pageSizeOptions={[10, 20, 50, 100]}
                                />
                            </div>
                        </div>
                    )}
                </Spin>
            </Card>
        </div>
    );
};

export default LogsTab;
