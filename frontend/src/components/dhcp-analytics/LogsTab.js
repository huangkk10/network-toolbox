import React, { useState, useEffect, useRef } from 'react';
import { Card, Select, Input, Switch, Button, Space, Tag, Empty, Spin, Radio, message } from 'antd';
import {
    DownloadOutlined,
    ReloadOutlined,
    ClearOutlined,
    SearchOutlined,
} from '@ant-design/icons';
import axios from 'axios';
import './LogsTab.css';

const { Option } = Select;

const LogsTab = ({ serverId }) => {
    const [logs, setLogs] = useState([]);
    const [loading, setLoading] = useState(false);
    const [logLevel, setLogLevel] = useState('ALL');
    const [keyword, setKeyword] = useState('');
    const [autoRefresh, setAutoRefresh] = useState(false);
    const [source, setSource] = useState('local');  // local 或 remote
    const [limit, setLimit] = useState(200);  // 默認顯示 200 條
    const logContainerRef = useRef(null);

    useEffect(() => {
        loadLogs();
    }, [serverId, logLevel, keyword, source, limit]);

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

            const response = await axios.get('/api/dhcp-analytics/logs/', { params });
            setLogs(response.data || []);

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

    const stats = getLogStats();

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

                    <Select
                        style={{ width: 120 }}
                        value={limit}
                        onChange={setLimit}
                        placeholder="顯示筆數"
                    >
                        <Option value={50}>50 筆</Option>
                        <Option value={100}>100 筆</Option>
                        <Option value={200}>200 筆</Option>
                        <Option value={500}>500 筆</Option>
                        <Option value={1000}>1000 筆</Option>
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
                <Space split="|" size="large">
                    <span>
                        <strong>顯示:</strong> {stats.total} 行 / 最多 {limit} 行
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
                            logs.map((log) => (
                                <div key={log.id} className={`log-line log-${log.level.toLowerCase()}`}>
                                    <span className="log-time">{log.timestamp}</span>
                                    {getLogLevelTag(log.level)}
                                    <span className="log-message">{log.message}</span>
                                </div>
                            ))
                        )}
                    </div>
                </Spin>
            </Card>
        </div>
    );
};

export default LogsTab;
