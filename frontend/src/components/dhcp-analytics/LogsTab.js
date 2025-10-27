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
    const [macToHostnameCache, setMacToHostnameCache] = useState({});  // MAC → Hostname 快取
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
            const logData = response.data || [];
            setLogs(logData);
            setCurrentPage(1);  // 重置到第一頁

            // 批量查詢 hostname（性能優化）
            if (logData.length > 0) {
                enrichLogsWithHostnames(logData);
            }

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

    // 從日誌訊息中提取 MAC 地址
    const extractMacFromMessage = (message) => {
        if (!message) return null;
        // 匹配格式: xx:xx:xx:xx:xx:xx 或 xx-xx-xx-xx-xx-xx
        const macRegex = /([0-9a-f]{2}[:-][0-9a-f]{2}[:-][0-9a-f]{2}[:-][0-9a-f]{2}[:-][0-9a-f]{2}[:-][0-9a-f]{2})/i;
        const match = message.match(macRegex);
        return match ? match[1].toLowerCase().replace(/-/g, ':') : null;
    };

    // 根據 MAC 地址查詢 hostname
    const fetchHostnameByMac = async (mac) => {
        if (!mac) return null;
        
        // 檢查快取
        if (macToHostnameCache[mac]) {
            return macToHostnameCache[mac];
        }
        
        try {
            const response = await axios.get('/api/dhcp-leases/lookup/', {
                params: { mac }
            });
            
            const hostname = response.data.hostname || null;
            
            // 更新快取
            setMacToHostnameCache(prev => ({
                ...prev,
                [mac]: hostname
            }));
            
            return hostname;
        } catch (error) {
            console.error(`查詢 MAC ${mac} 失敗:`, error);
            return null;
        }
    };

    // 批量查詢並豐富日誌資料（性能優化）
    const enrichLogsWithHostnames = async (logList) => {
        // 提取所有唯一的 MAC 地址
        const macs = new Set();
        logList.forEach(log => {
            const mac = extractMacFromMessage(log.message);
            if (mac && !macToHostnameCache[mac]) {
                macs.add(mac);
            }
        });
        
        // 批量查詢所有未快取的 MAC
        const macArray = Array.from(macs);
        if (macArray.length > 0) {
            const promises = macArray.map(mac => fetchHostnameByMac(mac));
            await Promise.all(promises);
        }
    };

    // 客戶端類型檢測函數（優先使用 hostname）
    const detectClientType = (message) => {
        if (!message) return null;  // 返回 null 表示不顯示
        
        const msgLower = message.toLowerCase();
        
        // 優先級 1: 從快取中查找 hostname
        const mac = extractMacFromMessage(message);
        if (mac && macToHostnameCache[mac]) {
            const hostname = macToHostnameCache[mac];
            if (hostname) {
                return detectClientTypeFromHostname(hostname);
            }
        }
        
        // 優先級 2: 檢查訊息關鍵字（iPXE/PXE/WinPE/UEFI）
        if (msgLower.includes('ipxe')) return 'iPXE';
        if (msgLower.includes('pxeboot') || 
            msgLower.includes('pxe boot') ||
            msgLower.includes('pxeclient')) return 'PXE';
        if (msgLower.includes('winpe') || 
            msgLower.includes('minint-')) return 'WinPE';
        if (msgLower.includes('uefi')) return 'UEFI';
        
        // 優先級 3: 檢查 MAC 地址特徵（虛擬機）
        const vmMacPatterns = [
            /00:0c:29/i,  // VMware
            /00:50:56/i,  // VMware ESXi
            /08:00:27/i,  // VirtualBox
            /52:54:00/i,  // QEMU/KVM
            /00:15:5d/i,  // Hyper-V
        ];
        if (vmMacPatterns.some(pattern => pattern.test(message))) {
            return 'VM';
        }
        
        // 優先級 4: 檢查 IoT 設備 MAC（Raspberry Pi）
        const iotMacPatterns = [
            /b8:27:eb/i,  // Raspberry Pi
            /dc:a6:32/i,  // Raspberry Pi
            /e4:5f:01/i,  // Raspberry Pi
        ];
        if (iotMacPatterns.some(pattern => pattern.test(message))) {
            return 'IoT';
        }
        
        // 優先級 5: 訊息中的 hostname 模式（不太可靠）
        if (/desktop-[a-z0-9]+/i.test(message)) return 'Windows';
        if (/win-[a-z0-9]+/i.test(message)) return 'Windows';
        if (/laptop-[a-z0-9]+/i.test(message)) return 'Windows';
        if (/ubuntu|debian|centos|fedora/i.test(message)) return 'Linux';
        if (/server-/i.test(message)) return 'Server';
        if (/printer-/i.test(message)) return 'Printer';
        
        // 無法識別：返回 null（不顯示標籤）
        return null;
    };

    // 根據 hostname 判斷客戶端類型
    const detectClientTypeFromHostname = (hostname) => {
        if (!hostname) return null;
        
        const hostLower = hostname.toLowerCase();
        
        // Windows 主機名模式
        if (/^(desktop|win|laptop|pc)-/i.test(hostname)) return 'Windows';
        if (hostLower.includes('windows')) return 'Windows';
        if (hostLower.includes('win10') || hostLower.includes('win11')) return 'Windows';
        
        // Linux 主機名模式
        if (/ubuntu|debian|centos|fedora|redhat|rhel|mint|arch/i.test(hostname)) return 'Linux';
        if (/^linux-/i.test(hostname)) return 'Linux';
        
        // 伺服器
        if (/^(server|srv|host)-/i.test(hostname)) return 'Server';
        if (hostLower.includes('server')) return 'Server';
        
        // 印表機
        if (/^(printer|print|hp|canon|epson)-/i.test(hostname)) return 'Printer';
        
        // IoT 設備
        if (/^(iot|sensor|camera|raspberry|rpi)-/i.test(hostname)) return 'IoT';
        
        // 行動裝置
        if (/^(mobile|phone|iphone|android)-/i.test(hostname)) return 'Mobile';
        if (/iphone|ipad|android/i.test(hostname)) return 'Mobile';
        
        // Apple 設備
        if (/^(mac|macbook|imac)-/i.test(hostname)) return 'Apple';
        if (hostLower.includes('macos')) return 'Apple';
        
        return null;  // 無法從 hostname 判斷
    };

    // 客戶端類型標籤生成函數
    const getClientTypeTag = (message) => {
        const clientType = detectClientType(message);
        
        // 如果無法識別，不顯示標籤
        if (!clientType) return null;
        
        const typeConfig = {
            'Windows': { color: 'blue', icon: '🪟', text: 'Windows' },
            'Linux': { color: 'green', icon: '🐧', text: 'Linux' },
            'iPXE': { color: 'purple', icon: '🚀', text: 'iPXE' },
            'PXE': { color: 'cyan', icon: '⚙️', text: 'PXE' },
            'WinPE': { color: 'geekblue', icon: '🔧', text: 'WinPE' },
            'UEFI': { color: 'magenta', icon: '⚡', text: 'UEFI' },
            'VM': { color: 'orange', icon: '📦', text: 'VM' },
            'Apple': { color: 'default', icon: '🍎', text: 'Apple' },
            'IoT': { color: 'lime', icon: '📡', text: 'IoT' },
            'Server': { color: 'gold', icon: '🖥️', text: 'Server' },
            'Printer': { color: 'volcano', icon: '🖨️', text: 'Printer' },
            'Mobile': { color: 'pink', icon: '📱', text: 'Mobile' },
        };
        
        const config = typeConfig[clientType];
        if (!config) return null;
        
        return <Tag color={config.color} style={{ minWidth: '90px', textAlign: 'center' }}>{config.icon} {config.text}</Tag>;
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

    // 客戶端類型統計（過濾掉 null）
    const getClientTypeStats = () => {
        const typeStats = {};
        logs.forEach(log => {
            const type = detectClientType(log.message);
            if (type) {  // 只統計可識別的類型
                typeStats[type] = (typeStats[type] || 0) + 1;
            }
        });
        return typeStats;
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
    const clientTypeStats = getClientTypeStats();
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
                <div style={{ marginBottom: '12px', fontSize: '13px' }}>
                    <Space split="|" wrap>
                        <span>總計: <strong>{stats.total}</strong> 行</span>
                        <span>當前頁: <strong>{currentPageLogs.length}</strong> 行</span>
                        <span>
                            <Tag color="blue">INFO: {stats.info}</Tag>
                            <Tag color="orange">WARN: {stats.warn}</Tag>
                            <Tag color="red">ERROR: {stats.error}</Tag>
                            <Tag color="default">DEBUG: {stats.debug}</Tag>
                        </span>
                    </Space>
                    {Object.keys(clientTypeStats).length > 0 && (
                        <div style={{ marginTop: '8px' }}>
                            <Space wrap>
                                <span style={{ color: '#858585' }}>客戶端類型:</span>
                                {Object.entries(clientTypeStats)
                                    .sort((a, b) => b[1] - a[1])  // 按數量排序
                                    .slice(0, 6)  // 只顯示前6個
                                    .map(([type, count]) => {
                                        const typeConfig = {
                                            'Windows': { color: 'blue', icon: '🪟' },
                                            'Linux': { color: 'green', icon: '🐧' },
                                            'iPXE': { color: 'purple', icon: '🚀' },
                                            'PXE': { color: 'cyan', icon: '⚙️' },
                                            'WinPE': { color: 'geekblue', icon: '🔧' },
                                            'UEFI': { color: 'magenta', icon: '⚡' },
                                            'VM': { color: 'orange', icon: '📦' },
                                            'Apple': { color: 'default', icon: '🍎' },
                                            'IoT': { color: 'lime', icon: '📡' },
                                            'Server': { color: 'gold', icon: '🖥️' },
                                            'Printer': { color: 'volcano', icon: '🖨️' },
                                            'Mobile': { color: 'pink', icon: '📱' },
                                        };
                                        const config = typeConfig[type];
                                        if (!config) return null;
                                        return (
                                            <Tag key={type} color={config.color}>
                                                {config.icon} {type}: {count}
                                            </Tag>
                                        );
                                    })
                                }
                            </Space>
                        </div>
                    )}
                </div>            {/* 日誌內容區 */}
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
                                    {getClientTypeTag(log.message)}
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
