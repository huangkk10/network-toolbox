import React, { useState, useEffect } from 'react';
import { Card, Row, Col, Statistic, Progress, message, Spin } from 'antd';
import {
    HddOutlined,
    DatabaseOutlined,
    ThunderboltOutlined,
    ReloadOutlined,
} from '@ant-design/icons';
import axios from 'axios';
import {
    AreaChart,
    Area,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    ResponsiveContainer,
    Legend,
} from 'recharts';

const SystemMonitorPage = () => {
    const [systemData, setSystemData] = useState(null);
    const [loading, setLoading] = useState(false);
    const [historyData, setHistoryData] = useState([]);
    const [autoRefresh, setAutoRefresh] = useState(true);

    // 獲取系統狀態
    const fetchSystemStatus = async () => {
        setLoading(true);
        try {
            const response = await axios.get('/api/system/status/');
            setSystemData(response.data);

            // 更新歷史數據（保留最近 20 筆）
            const now = new Date();
            const timeStr = `${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}:${now.getSeconds().toString().padStart(2, '0')}`;
            
            setHistoryData(prev => {
                const newData = [
                    ...prev,
                    {
                        time: timeStr,
                        cpu: response.data.cpu.percent,
                        ram: response.data.ram.percent,
                        disk: response.data.disk.percent,
                    }
                ];
                // 只保留最近 20 筆數據
                return newData.slice(-20);
            });
        } catch (error) {
            console.error('Error fetching system status:', error);
            message.error('獲取系統狀態失敗：' + error.message);
        } finally {
            setLoading(false);
        }
    };

    // 初始載入
    useEffect(() => {
        fetchSystemStatus();
    }, []);

    // 自動刷新（每 5 秒）
    useEffect(() => {
        if (autoRefresh) {
            const interval = setInterval(() => {
                fetchSystemStatus();
            }, 5000);
            return () => clearInterval(interval);
        }
    }, [autoRefresh]);

    // 根據使用率返回顏色
    const getStatusColor = (percent) => {
        if (percent < 60) return '#52c41a';  // 綠色（正常）
        if (percent < 80) return '#faad14';  // 黃色（警告）
        return '#ff4d4f';  // 紅色（危險）
    };

    if (!systemData) {
        return (
            <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '80vh' }}>
                <Spin size="large" tip="載入系統狀態..." />
            </div>
        );
    }

    return (
        <div style={{ padding: '24px', background: '#f5f5f5' }}>
            {/* 頁面標題 */}
            <Row gutter={[16, 16]} style={{ marginBottom: '24px' }}>
                <Col span={24}>
                    <Card>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                            <div>
                                <h2 style={{ margin: 0 }}>系統監控</h2>
                                <p style={{ margin: 0, color: '#666' }}>即時監控伺服器系統資源使用狀況</p>
                            </div>
                            <div style={{ display: 'flex', gap: '8px' }}>
                                <span style={{ color: autoRefresh ? '#52c41a' : '#666' }}>
                                    ● {autoRefresh ? '自動刷新中' : '已暫停'}
                                </span>
                                <a onClick={() => setAutoRefresh(!autoRefresh)}>
                                    {autoRefresh ? '暫停' : '繼續'}
                                </a>
                                <a onClick={fetchSystemStatus} style={{ marginLeft: '8px' }}>
                                    <ReloadOutlined spin={loading} /> 手動刷新
                                </a>
                            </div>
                        </div>
                    </Card>
                </Col>
            </Row>

            {/* 統計卡片 */}
            <Row gutter={[16, 16]} style={{ marginBottom: '24px' }}>
                {/* 磁碟空間 */}
                <Col xs={24} sm={12} lg={8}>
                    <Card>
                        <Statistic
                            title="磁碟空間使用率"
                            value={systemData.disk.percent}
                            precision={1}
                            suffix="%"
                            prefix={<HddOutlined />}
                            valueStyle={{ color: getStatusColor(systemData.disk.percent) }}
                        />
                        <Progress
                            percent={systemData.disk.percent}
                            strokeColor={getStatusColor(systemData.disk.percent)}
                            showInfo={false}
                            style={{ marginTop: '16px' }}
                        />
                        <div style={{ marginTop: '16px', fontSize: '14px', color: '#666' }}>
                            <div>總容量：{systemData.disk.total} GB</div>
                            <div>已使用：{systemData.disk.used} GB</div>
                            <div>可用空間：{systemData.disk.free} GB</div>
                        </div>
                    </Card>
                </Col>

                {/* CPU 使用率 */}
                <Col xs={24} sm={12} lg={8}>
                    <Card>
                        <Statistic
                            title="CPU 使用率"
                            value={systemData.cpu.percent}
                            precision={1}
                            suffix="%"
                            prefix={<ThunderboltOutlined />}
                            valueStyle={{ color: getStatusColor(systemData.cpu.percent) }}
                        />
                        <Progress
                            percent={systemData.cpu.percent}
                            strokeColor={getStatusColor(systemData.cpu.percent)}
                            showInfo={false}
                            style={{ marginTop: '16px' }}
                        />
                        <div style={{ marginTop: '16px', fontSize: '14px', color: '#666' }}>
                            <div>CPU 核心數：{systemData.cpu.count}</div>
                        </div>
                    </Card>
                </Col>

                {/* RAM 使用率 */}
                <Col xs={24} sm={12} lg={8}>
                    <Card>
                        <Statistic
                            title="記憶體使用率"
                            value={systemData.ram.percent}
                            precision={1}
                            suffix="%"
                            prefix={<DatabaseOutlined />}
                            valueStyle={{ color: getStatusColor(systemData.ram.percent) }}
                        />
                        <Progress
                            percent={systemData.ram.percent}
                            strokeColor={getStatusColor(systemData.ram.percent)}
                            showInfo={false}
                            style={{ marginTop: '16px' }}
                        />
                        <div style={{ marginTop: '16px', fontSize: '14px', color: '#666' }}>
                            <div>總記憶體：{systemData.ram.total} GB</div>
                            <div>已使用：{systemData.ram.used} GB</div>
                            <div>可用：{systemData.ram.available} GB</div>
                        </div>
                    </Card>
                </Col>
            </Row>

            {/* 歷史趨勢圖 */}
            {historyData.length > 0 && (
                <Row gutter={[16, 16]}>
                    <Col span={24}>
                        <Card title="資源使用趨勢" extra={<span style={{ fontSize: '12px', color: '#666' }}>最近 {historyData.length} 筆數據</span>}>
                            <ResponsiveContainer width="100%" height={400}>
                                <AreaChart
                                    data={historyData}
                                    margin={{ top: 10, right: 30, left: 0, bottom: 0 }}
                                >
                                    <defs>
                                        <linearGradient id="colorCpu" x1="0" y1="0" x2="0" y2="1">
                                            <stop offset="5%" stopColor="#2196f3" stopOpacity={0.8} />
                                            <stop offset="95%" stopColor="#2196f3" stopOpacity={0} />
                                        </linearGradient>
                                        <linearGradient id="colorRam" x1="0" y1="0" x2="0" y2="1">
                                            <stop offset="5%" stopColor="#52c41a" stopOpacity={0.8} />
                                            <stop offset="95%" stopColor="#52c41a" stopOpacity={0} />
                                        </linearGradient>
                                        <linearGradient id="colorDisk" x1="0" y1="0" x2="0" y2="1">
                                            <stop offset="5%" stopColor="#faad14" stopOpacity={0.8} />
                                            <stop offset="95%" stopColor="#faad14" stopOpacity={0} />
                                        </linearGradient>
                                    </defs>
                                    <CartesianGrid strokeDasharray="3 3" />
                                    <XAxis dataKey="time" />
                                    <YAxis domain={[0, 100]} />
                                    <Tooltip />
                                    <Legend />
                                    <Area
                                        type="monotone"
                                        dataKey="cpu"
                                        stroke="#2196f3"
                                        fillOpacity={1}
                                        fill="url(#colorCpu)"
                                        name="CPU (%)"
                                    />
                                    <Area
                                        type="monotone"
                                        dataKey="ram"
                                        stroke="#52c41a"
                                        fillOpacity={1}
                                        fill="url(#colorRam)"
                                        name="RAM (%)"
                                    />
                                    <Area
                                        type="monotone"
                                        dataKey="disk"
                                        stroke="#faad14"
                                        fillOpacity={1}
                                        fill="url(#colorDisk)"
                                        name="磁碟 (%)"
                                    />
                                </AreaChart>
                            </ResponsiveContainer>
                        </Card>
                    </Col>
                </Row>
            )}
        </div>
    );
};

export default SystemMonitorPage;
