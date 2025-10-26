import React, { useState, useEffect, useRef } from 'react';
import { Card, Select, Input, Switch, Button, Space, Tag, Empty, Spin } from 'antd';
import {
    DownloadOutlined,
    ReloadOutlined,
    ClearOutlined,
    SearchOutlined,
} from '@ant-design/icons';
import './LogsTab.css';

const { Option } = Select;

const LogsTab = ({ serverId }) => {
    const [logs, setLogs] = useState([]);
    const [loading, setLoading] = useState(false);
    const [logLevel, setLogLevel] = useState('ALL');
    const [keyword, setKeyword] = useState('');
    const [autoRefresh, setAutoRefresh] = useState(false);
    const logContainerRef = useRef(null);

    // 模擬日誌數據
    const mockLogs = [
        {
            id: 1,
            timestamp: '2025-10-27 14:30:22',
            level: 'INFO',
            message: 'DHCP DISCOVER from 00:1A:2B:3C:4D:5E via eth0',
        },
        {
            id: 2,
            timestamp: '2025-10-27 14:30:23',
            level: 'INFO',
            message: 'DHCP OFFER on 192.168.1.100 to 00:1A:2B:3C:4D:5E via eth0',
        },
        {
            id: 3,
            timestamp: '2025-10-27 14:30:24',
            level: 'WARN',
            message: 'IP pool 192.168.1.0/24 usage at 85%, threshold warning',
        },
        {
            id: 4,
            timestamp: '2025-10-27 14:30:25',
            level: 'INFO',
            message: 'DHCP REQUEST for 192.168.1.100 from 00:1A:2B:3C:4D:5E via eth0',
        },
        {
            id: 5,
            timestamp: '2025-10-27 14:30:26',
            level: 'INFO',
            message: 'DHCP ACK on 192.168.1.100 to 00:1A:2B:3C:4D:5E via eth0',
        },
        {
            id: 6,
            timestamp: '2025-10-27 14:30:27',
            level: 'ERROR',
            message: 'Lease conflict detected: 192.168.1.105 already in use',
        },
        {
            id: 7,
            timestamp: '2025-10-27 14:30:28',
            level: 'INFO',
            message: 'DHCP RELEASE from 00:1A:2B:3C:4D:60 (192.168.2.50)',
        },
        {
            id: 8,
            timestamp: '2025-10-27 14:30:29',
            level: 'INFO',
            message: 'Lease expired: 192.168.1.88 (00:1A:2B:3C:4D:AA)',
        },
        {
            id: 9,
            timestamp: '2025-10-27 14:30:30',
            level: 'WARN',
            message: 'Failed to ping 192.168.1.120 before offering lease',
        },
        {
            id: 10,
            timestamp: '2025-10-27 14:30:31',
            level: 'INFO',
            message: 'DHCP DISCOVER from 00:1A:2B:3C:4D:70 via eth1',
        },
        {
            id: 11,
            timestamp: '2025-10-27 14:30:32',
            level: 'DEBUG',
            message: 'Checking available IP addresses in pool 10.0.1.0/24',
        },
        {
            id: 12,
            timestamp: '2025-10-27 14:30:33',
            level: 'INFO',
            message: 'DHCP OFFER on 10.0.1.200 to 00:1A:2B:3C:4D:70 via eth1',
        },
    ];

    useEffect(() => {
        loadLogs();
    }, [serverId, logLevel, keyword]);

    useEffect(() => {
        if (autoRefresh) {
            const interval = setInterval(() => {
                loadLogs(true);
            }, 3000);
            return () => clearInterval(interval);
        }
    }, [autoRefresh, logLevel, keyword]);

    const loadLogs = (isAutoRefresh = false) => {
        if (!isAutoRefresh) {
            setLoading(true);
        }

        setTimeout(() => {
            let filteredLogs = [...mockLogs];

            // 按日誌等級篩選
            if (logLevel !== 'ALL') {
                filteredLogs = filteredLogs.filter((log) => log.level === logLevel);
            }

            // 按關鍵字篩選
            if (keyword) {
                filteredLogs = filteredLogs.filter((log) =>
                    log.message.toLowerCase().includes(keyword.toLowerCase())
                );
            }

            setLogs(filteredLogs);
            setLoading(false);

            // 自動滾動到底部
            if (logContainerRef.current) {
                logContainerRef.current.scrollTop = logContainerRef.current.scrollHeight;
            }
        }, 500);
    };

    const handleClear = () => {
        setLogs([]);
    };

    const handleDownload = () => {
        // TODO: 實作下載日誌功能
        const logText = logs.map((log) => `[${log.timestamp}] ${log.level}: ${log.message}`).join('\n');
        const blob = new Blob([logText], { type: 'text/plain' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `dhcp-server-${serverId}-logs-${new Date().getTime()}.log`;
        a.click();
        URL.revokeObjectURL(url);
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

                    <Space>
                        <span style={{ color: '#666' }}>自動更新:</span>
                        <Switch checked={autoRefresh} onChange={setAutoRefresh} />
                    </Space>

                    <Button icon={<ReloadOutlined />} onClick={() => loadLogs()}>
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
                        <strong>總計:</strong> {stats.total} 行
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
