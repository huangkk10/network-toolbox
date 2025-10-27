import React, { useState, useEffect, useRef } from 'react';
import { Card, Select, Input, Switch, Button, Space, Tag, Empty, Spin, Radio, message, Pagination, DatePicker } from 'antd';
import {
    DownloadOutlined,
    ReloadOutlined,
    ClearOutlined,
    SearchOutlined,
} from '@ant-design/icons';
import axios from 'axios';
import dayjs from 'dayjs';
import './LogsTab.css';

const { Option } = Select;
const { RangePicker } = DatePicker;

const LogsTab = ({ serverId }) => {
    const [logs, setLogs] = useState([]);
    const [loading, setLoading] = useState(false);
    const [logLevel, setLogLevel] = useState('ALL');
    const [keyword, setKeyword] = useState('');
    const [autoRefresh, setAutoRefresh] = useState(false);
    const [source, setSource] = useState('local');  // local 或 remote
    const [limit, setLimit] = useState(500);  // 默認顯示 500 條
    const [currentPage, setCurrentPage] = useState(1);  // 當前頁碼
    const [pageSize, setPageSize] = useState(20);  // 每頁顯示數量
    const [dateRange, setDateRange] = useState(null);  // 時間範圍 [startDate, endDate]
    const logContainerRef = useRef(null);

    useEffect(() => {
        loadLogs();
        setCurrentPage(1);  // 重置到第一頁
    }, [serverId, logLevel, keyword, source, limit, dateRange]);

    useEffect(() => {
        if (autoRefresh) {
            const interval = setInterval(() => {
                loadLogs(true);
            }, 3000);
            return () => clearInterval(interval);
        }
    }, [autoRefresh, serverId, logLevel, keyword, source, limit]);

    const loadLogs = async (isAutoRefresh = false) => {
        if (!isAutoRefresh) {
            setLoading(true);
        }

        try {
            const params = {
                server: serverId,
                source: source,
                limit: limit,
            };

            if (logLevel && logLevel !== 'ALL') {
                params.level = logLevel;
            }

            if (keyword) {
                params.keyword = keyword;
            }

            // 時間範圍過濾
            if (dateRange && dateRange[0] && dateRange[1]) {
                params.start_time = dateRange[0].format('YYYY-MM-DD HH:mm:ss');
                params.end_time = dateRange[1].format('YYYY-MM-DD HH:mm:ss');
            }

            const response = await axios.get('/api/dhcp-analytics/logs/', { params });
            setLogs(response.data || []);
            setCurrentPage(1);  // 重置到第一頁

            // 自動滾動到底部
            setTimeout(() => {
                if (logContainerRef.current) {
                    logContainerRef.current.scrollTop = logContainerRef.current.scrollHeight;
                }
            }, 100);
        } catch (error) {
            console.error('載入日誌失敗:', error);
            if (!isAutoRefresh) {
                message.error('載入日誌失敗：' + (error.response?.data?.error || error.message));
            }
        } finally {
            setLoading(false);
        }
    };

    const handleClear = () => {
        setLogs([]);
        message.success('日誌已清除');
    };

    const handleDownload = () => {
        if (logs.length === 0) {
            message.warning('沒有日誌可下載');
            return;
        }

        const content = logs
            .map(log => `[${log.level}] ${log.timestamp} | ${log.message}`)
            .join('\n');

        const blob = new Blob([content], { type: 'text/plain;charset=utf-8' });
        const url = window.URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = `dhcp_logs_${serverId}_${new Date().toISOString().slice(0, 10)}.txt`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        window.URL.revokeObjectURL(url);

        message.success('日誌已下載');
    };

    const getLogLevelTag = (level) => {
        const levelConfig = {
            INFO: { color: 'blue', text: 'INFO' },
            WARN: { color: 'orange', text: 'WARN' },
            ERROR: { color: 'red', text: 'ERROR' },
            DEBUG: { color: 'default', text: 'DEBUG' },
        };
        const config = levelConfig[level] || { color: 'default', text: level };
        return <Tag color={config.color}>{config.text}</Tag>;
    };

    const getLogStats = () => {
        const stats = {
            total: logs.length,
            info: logs.filter((log) => log.level === 'INFO').length,
            warn: logs.filter((log) => log.level === 'WARN').length,
            error: logs.filter((log) => log.level === 'ERROR').length,
            debug: logs.filter((log) => log.level === 'DEBUG').length,
        };
        return stats;
    };

    // 分頁處理
    const handlePageChange = (page, newPageSize) => {
        setCurrentPage(page);
        if (newPageSize !== pageSize) {
            setPageSize(newPageSize);
            setCurrentPage(1);  // 改變每頁數量時重置到第一頁
        }
    };

    // 獲取當前頁的日誌
    const getCurrentPageLogs = () => {
        const startIndex = (currentPage - 1) * pageSize;
        const endIndex = startIndex + pageSize;
        return logs.slice(startIndex, endIndex);
    };

    const stats = getLogStats();
    const currentPageLogs = getCurrentPageLogs();

    return (
        <div>
            {/* 控制列 */}
            <Card style={{ marginBottom: '16px' }}>
                <Space wrap>
                    <Radio.Group value={source} onChange={(e) => setSource(e.target.value)}>
                        <Radio.Button value="local">本地日誌</Radio.Button>
                        <Radio.Button value="remote" disabled={serverId === 'all'}>
                            遠端 SSH
                        </Radio.Button>
                    </Radio.Group>

                    <Select
                        style={{ width: 120 }}
                        value={logLevel}
                        onChange={setLogLevel}
                        placeholder="日誌等級"
                    >
                        <Option value="ALL">所有等級</Option>
                        <Option value="INFO">INFO</Option>
                        <Option value="WARN">WARN</Option>
                        <Option value="ERROR">ERROR</Option>
                        <Option value="DEBUG">DEBUG</Option>
                    </Select>

                    <Input.Search
                        placeholder="搜尋關鍵字..."
                        allowClear
                        style={{ width: 250 }}
                        onSearch={setKeyword}
                        prefix={<SearchOutlined />}
                    />

                    <RangePicker
                        showTime
                        format="YYYY-MM-DD HH:mm:ss"
                        placeholder={['開始時間', '結束時間']}
                        value={dateRange}
                        onChange={setDateRange}
                        style={{ width: 380 }}
                    />

                    <Select
                        style={{ width: 120 }}
                        value={limit}
                        onChange={setLimit}
                        placeholder="顯示筆數"
                    >
                        <Option value={100}>100 筆</Option>
                        <Option value={200}>200 筆</Option>
                        <Option value={300}>300 筆</Option>
                        <Option value={500}>500 筆</Option>
                    </Select>

                    <Space>
                        <span style={{ color: '#666' }}>自動更新:</span>
                        <Switch checked={autoRefresh} onChange={setAutoRefresh} />
                    </Space>

                    <Button icon={<ReloadOutlined />} onClick={() => loadLogs()} loading={loading}>
                        重新載入
                    </Button>

                    <Button icon={<ClearOutlined />} onClick={handleClear}>
                        清除螢幕
                    </Button>

                    <Button icon={<DownloadOutlined />} onClick={handleDownload}>
                        下載日誌
                    </Button>
                </Space>
            </Card>

            {/* 日誌統計 */}
            <Card size="small" style={{ marginBottom: '16px' }}>
                <Space split="|" size="large" style={{ flexWrap: 'wrap' }}>
                    <span>
                        <strong>總計:</strong> {stats.total} 行
                    </span>
                    <span>
                        <strong>當前頁:</strong> {currentPageLogs.length} 行
                    </span>
                    <span>
                        <Tag color="blue">INFO: {stats.info}</Tag>
                    </span>
                    <span>
                        <Tag color="orange">WARN: {stats.warn}</Tag>
                    </span>
                    <span>
                        <Tag color="red">ERROR: {stats.error}</Tag>
                    </span>
                    <span>
                        <Tag color="default">DEBUG: {stats.debug}</Tag>
                    </span>
                </Space>
            </Card>

            {/* 日誌內容區 */}
            <Card
                title={
                    <Space>
                        <span>日誌內容</span>
                        {autoRefresh && <Tag color="success">自動更新中...</Tag>}
                    </Space>
                }
            >
                <Spin spinning={loading}>
                    <div className="log-container" ref={logContainerRef}>
                        {logs.length === 0 ? (
                            <Empty description="無日誌記錄" />
                        ) : (
                            currentPageLogs.map((log, index) => (
                                <div key={log.id || index} className={`log-line log-${log.level.toLowerCase()}`}>
                                    <span className="log-time">{log.timestamp}</span>
                                    {getLogLevelTag(log.level)}
                                    <span className="log-message">{log.message}</span>
                                </div>
                            ))
                        )}
                    </div>

                    {/* 分頁器 */}
                    {logs.length > 0 && (
                        <div style={{ marginTop: '16px', textAlign: 'center' }}>
                            <Pagination
                                current={currentPage}
                                pageSize={pageSize}
                                total={logs.length}
                                onChange={handlePageChange}
                                onShowSizeChange={handlePageChange}
                                showSizeChanger
                                showQuickJumper
                                showTotal={(total) => `共 ${total} 條日誌`}
                                pageSizeOptions={['10', '20', '50', '100']}
                            />
                        </div>
                    )}
                </Spin>
            </Card>
        </div>
    );
};

export default LogsTab;
