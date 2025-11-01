import React from 'react';
import { Card, Tag, Space, Typography, Tooltip } from 'antd';
import {
    LineChart,
    Line,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip as RechartsTooltip,
    Legend,
    ResponsiveContainer,
    ReferenceArea,
} from 'recharts';
import {
    CheckCircleOutlined,
    WarningOutlined,
    CloseCircleOutlined,
    QuestionCircleOutlined,
} from '@ant-design/icons';

const { Text, Title } = Typography;

/**
 * 網路品質圖表組件 - 使用背景顏色區域顯示品質等級
 * 
 * @param {Object} props
 * @param {Array} props.data - 圖表數據 [{timestamp, value, ...}]
 * @param {string} props.metricType - 指標類型: 'ping', 'http', 'ssh'
 * @param {string} props.title - 圖表標題
 * @param {string} props.unit - 單位 (ms, s, etc.)
 */
const NetworkQualityChart = ({ data, metricType = 'ping', title, unit = 'ms' }) => {
    // 根據不同的指標類型定義品質範圍
    const qualityRanges = {
        ping: {
            excellent: { max: 1, color: '#52c41a', label: '優秀' },
            good: { min: 1, max: 5, color: '#73d13d', label: '良好' },
            acceptable: { min: 5, max: 20, color: '#faad14', label: '尚可' },
            warning: { min: 20, max: 50, color: '#ff7a45', label: '警告' },
            poor: { min: 50, color: '#ff4d4f', label: '不良' },
        },
        http: {
            excellent: { max: 20, color: '#52c41a', label: '優秀' },
            good: { min: 20, max: 50, color: '#73d13d', label: '良好' },
            acceptable: { min: 50, max: 100, color: '#faad14', label: '尚可' },
            warning: { min: 100, max: 200, color: '#ff7a45', label: '警告' },
            poor: { min: 200, color: '#ff4d4f', label: '不良' },
        },
        ssh: {
            excellent: { max: 50, color: '#52c41a', label: '優秀' },
            good: { min: 50, max: 100, color: '#73d13d', label: '良好' },
            acceptable: { min: 100, max: 200, color: '#faad14', label: '尚可' },
            warning: { min: 200, max: 500, color: '#ff7a45', label: '警告' },
            poor: { min: 500, color: '#ff4d4f', label: '不良' },
        },
        packet_loss: {
            excellent: { max: 0.5, color: '#52c41a', label: '優秀' },
            good: { min: 0.5, max: 2, color: '#73d13d', label: '良好' },
            acceptable: { min: 2, max: 5, color: '#faad14', label: '尚可' },
            warning: { min: 5, max: 10, color: '#ff7a45', label: '警告' },
            poor: { min: 10, color: '#ff4d4f', label: '不良' },
        },
        download_speed: {
            excellent: { min: 50, color: '#52c41a', label: '優秀' },
            good: { min: 20, max: 50, color: '#73d13d', label: '良好' },
            acceptable: { min: 10, max: 20, color: '#faad14', label: '尚可' },
            warning: { min: 5, max: 10, color: '#ff7a45', label: '警告' },
            poor: { max: 5, color: '#ff4d4f', label: '不良' },
        },
    };

    const ranges = qualityRanges[metricType] || qualityRanges.ping;

    // 計算圖表的 Y 軸最大值（用於設定背景區域）
    const getYAxisMax = () => {
        if (!data || data.length === 0) return 100;
        const maxValue = Math.max(...data.map(d => d.value));
        
        // 特殊處理：丟包率圖表
        if (metricType === 'packet_loss') {
            // 如果最大值很小（接近0），使用固定範圍以便觀察
            if (maxValue <= 1) {
                return 5;  // 固定顯示 0-5% 範圍
            } else if (maxValue <= 5) {
                return 10;  // 顯示 0-10% 範圍
            } else {
                return Math.ceil(maxValue * 1.2);
            }
        }
        
        // 根據最大值智能設定 Y 軸上限
        if (maxValue <= ranges.excellent.max * 2) {
            return ranges.acceptable.max || ranges.good.max || 50;
        } else if (maxValue <= ranges.good.max * 2) {
            return ranges.warning.max || ranges.acceptable.max || 100;
        } else {
            return Math.ceil(maxValue * 1.2); // 最大值的 1.2 倍
        }
    };

    const yAxisMax = getYAxisMax();
    
    // 調試信息
    if (metricType === 'packet_loss' && data && data.length > 0) {
        console.log('丟包率圖表配置:', {
            metricType,
            dataLength: data.length,
            maxValue: Math.max(...data.map(d => d.value)),
            yAxisMax,
            ranges: ranges
        });
    }

    // 根據當前值獲取品質等級
    const getQualityLevel = (value) => {
        if (value === null || value === undefined) return null;
        
        // 優秀（最小區間）
        if (ranges.excellent.max !== undefined && value <= ranges.excellent.max) return 'excellent';
        
        // 良好
        if (ranges.good.min !== undefined && ranges.good.max !== undefined) {
            if (value > ranges.good.min && value <= ranges.good.max) return 'good';
        }
        
        // 尚可
        if (ranges.acceptable.min !== undefined && ranges.acceptable.max !== undefined) {
            if (value > ranges.acceptable.min && value <= ranges.acceptable.max) return 'acceptable';
        }
        
        // 警告
        if (ranges.warning.min !== undefined && ranges.warning.max !== undefined) {
            if (value > ranges.warning.min && value <= ranges.warning.max) return 'warning';
        }
        
        // 不良（超過所有範圍）
        return 'poor';
    };

    // 獲取當前整體品質狀態
    const getCurrentStatus = () => {
        if (!data || data.length === 0) {
            return { level: null, icon: <QuestionCircleOutlined />, text: '無資料', color: '#d9d9d9' };
        }

        const latestValue = data[data.length - 1]?.value;
        const level = getQualityLevel(latestValue);

        const statusMap = {
            excellent: { icon: <CheckCircleOutlined />, text: '優秀', color: '#52c41a' },
            good: { icon: <CheckCircleOutlined />, text: '良好', color: '#73d13d' },
            acceptable: { icon: <WarningOutlined />, text: '尚可', color: '#faad14' },
            warning: { icon: <WarningOutlined />, text: '警告', color: '#ff7a45' },
            poor: { icon: <CloseCircleOutlined />, text: '不良', color: '#ff4d4f' },
        };

        return { level, ...statusMap[level] };
    };

    const currentStatus = getCurrentStatus();

    // 格式化時間戳
    const formatTimestamp = (timestamp) => {
        const date = new Date(timestamp);
        return `${date.getMonth() + 1}/${date.getDate()} ${date.getHours()}:${String(date.getMinutes()).padStart(2, '0')}`;
    };

    // 自訂 Tooltip
    const CustomTooltip = ({ active, payload }) => {
        if (active && payload && payload.length) {
            const value = payload[0].value;
            const level = getQualityLevel(value);
            const levelInfo = ranges[level];

            return (
                <Card size="small" style={{ border: `2px solid ${levelInfo?.color}` }}>
                    <Space direction="vertical" size="small">
                        <Text strong>{payload[0].payload.timestamp}</Text>
                        <Text>
                            {title}: <Text strong>{value} {unit}</Text>
                        </Text>
                        <Tag color={levelInfo?.color}>{levelInfo?.label}</Tag>
                    </Space>
                </Card>
            );
        }
        return null;
    };

    return (
        <Card
            title={
                <Space>
                    <span>{title}</span>
                    <Tooltip title={`當前狀態：${currentStatus.text}`}>
                        <Tag icon={currentStatus.icon} color={currentStatus.color}>
                            {currentStatus.text}
                        </Tag>
                    </Tooltip>
                </Space>
            }
            extra={
                <Space size="small">
                    {Object.entries(ranges).map(([key, range]) => (
                        <Tag key={key} color={range.color} style={{ fontSize: '11px' }}>
                            {range.label}
                        </Tag>
                    ))}
                </Space>
            }
        >
            <ResponsiveContainer width="100%" height={300}>
                <LineChart data={data} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis
                        dataKey="timestamp"
                        tickFormatter={formatTimestamp}
                        angle={-45}
                        textAnchor="end"
                        height={80}
                    />
                    <YAxis 
                        label={{ value: `${title} (${unit})`, angle: -90, position: 'insideLeft' }} 
                        domain={[0, yAxisMax]} 
                        allowDataOverflow={false}
                        type="number"
                    />
                    <RechartsTooltip content={<CustomTooltip />} />
                    <Legend />

                    {/* 背景顏色區域 - 優秀 */}
                    {ranges.excellent.max && (
                        <ReferenceArea
                            y1={0}
                            y2={ranges.excellent.max}
                            fill={ranges.excellent.color}
                            fillOpacity={0.1}
                            label={{ value: ranges.excellent.label, position: 'insideTopRight', fill: ranges.excellent.color, fontSize: 12 }}
                        />
                    )}

                    {/* 背景顏色區域 - 良好 */}
                    {ranges.good.min && ranges.good.max && (
                        <ReferenceArea
                            y1={ranges.good.min}
                            y2={ranges.good.max}
                            fill={ranges.good.color}
                            fillOpacity={0.1}
                            label={{ value: ranges.good.label, position: 'insideTopRight', fill: ranges.good.color, fontSize: 12 }}
                        />
                    )}

                    {/* 背景顏色區域 - 尚可 */}
                    {ranges.acceptable.min && ranges.acceptable.max && (
                        <ReferenceArea
                            y1={ranges.acceptable.min}
                            y2={ranges.acceptable.max}
                            fill={ranges.acceptable.color}
                            fillOpacity={0.15}
                            label={{ value: ranges.acceptable.label, position: 'insideTopRight', fill: ranges.acceptable.color, fontSize: 12 }}
                        />
                    )}

                    {/* 背景顏色區域 - 警告 */}
                    {ranges.warning.min && ranges.warning.max && (
                        <ReferenceArea
                            y1={ranges.warning.min}
                            y2={ranges.warning.max}
                            fill={ranges.warning.color}
                            fillOpacity={0.15}
                            label={{ value: ranges.warning.label, position: 'insideTopRight', fill: ranges.warning.color, fontSize: 12 }}
                        />
                    )}

                    {/* 背景顏色區域 - 不良 */}
                    {ranges.poor.min && (
                        <ReferenceArea
                            y1={ranges.poor.min}
                            y2={yAxisMax}
                            fill={ranges.poor.color}
                            fillOpacity={0.2}
                            label={{ value: ranges.poor.label, position: 'insideTopRight', fill: ranges.poor.color, fontSize: 12 }}
                        />
                    )}

                    {/* 主要折線 */}
                    <Line
                        type="monotone"
                        dataKey="value"
                        stroke="#1890ff"
                        strokeWidth={2}
                        dot={{ r: 4, fill: '#1890ff' }}
                        activeDot={{ r: 6 }}
                        name={title}
                        connectNulls={true}
                    />
                </LineChart>
            </ResponsiveContainer>
        </Card>
    );
};

export default NetworkQualityChart;
