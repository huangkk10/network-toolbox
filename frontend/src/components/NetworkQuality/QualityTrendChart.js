/**
 * 品質趨勢圖表組件
 * 
 * 包含品質等級背景色分層顯示
 */

import React, { useMemo } from 'react';
import { Card, Select, Empty, Spin, Tag, Space } from 'antd';
import {
    LineChart,
    Line,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    Legend,
    ResponsiveContainer,
    ReferenceArea,
} from 'recharts';

// 為每個 Switch 生成不同顏色
const COLORS = [
    '#1890ff', '#52c41a', '#faad14', '#f5222d', 
    '#722ed1', '#13c2c2', '#eb2f96', '#fa8c16',
    '#2f54eb', '#a0d911', '#fadb14', '#ff7a45',
];

/**
 * 品質等級定義（延遲 ms）
 * 與附件1的顏色分層對應
 */
const QUALITY_LEVELS = {
    latency: [
        { min: 0, max: 1, label: '優秀', color: '#52c41a', bgColor: 'rgba(82, 196, 26, 0.15)' },
        { min: 1, max: 5, label: '良好', color: '#73d13d', bgColor: 'rgba(115, 209, 61, 0.15)' },
        { min: 5, max: 10, label: '尚可', color: '#fadb14', bgColor: 'rgba(250, 219, 20, 0.15)' },
        { min: 10, max: 20, label: '警告', color: '#faad14', bgColor: 'rgba(250, 173, 20, 0.15)' },
        { min: 20, max: 100, label: '不良', color: '#ff4d4f', bgColor: 'rgba(255, 77, 79, 0.15)' },
    ],
    packet_loss: [
        { min: 0, max: 1, label: '優秀', color: '#52c41a', bgColor: 'rgba(82, 196, 26, 0.15)' },
        { min: 1, max: 3, label: '良好', color: '#73d13d', bgColor: 'rgba(115, 209, 61, 0.15)' },
        { min: 3, max: 5, label: '尚可', color: '#fadb14', bgColor: 'rgba(250, 219, 20, 0.15)' },
        { min: 5, max: 10, label: '警告', color: '#faad14', bgColor: 'rgba(250, 173, 20, 0.15)' },
        { min: 10, max: 100, label: '不良', color: '#ff4d4f', bgColor: 'rgba(255, 77, 79, 0.15)' },
    ],
    jitter: [
        { min: 0, max: 1, label: '優秀', color: '#52c41a', bgColor: 'rgba(82, 196, 26, 0.15)' },
        { min: 1, max: 5, label: '良好', color: '#73d13d', bgColor: 'rgba(115, 209, 61, 0.15)' },
        { min: 5, max: 10, label: '尚可', color: '#fadb14', bgColor: 'rgba(250, 219, 20, 0.15)' },
        { min: 10, max: 20, label: '警告', color: '#faad14', bgColor: 'rgba(250, 173, 20, 0.15)' },
        { min: 20, max: 100, label: '不良', color: '#ff4d4f', bgColor: 'rgba(255, 77, 79, 0.15)' },
    ],
};

/**
 * 將歷史數據轉換為圖表可用的格式
 * API 返回的 history 是一個包含所有 Switch 數據的平坦陣列
 */
const transformChartData = (historyData, selectedSwitchIds) => {
    if (!historyData || !historyData.history || historyData.history.length === 0) {
        return [];
    }
    
    // 收集所有時間點
    const timeMap = new Map();
    
    historyData.history.forEach(point => {
        if (!selectedSwitchIds.includes(point.switch_id)) return;
        
        const timestamp = point.timestamp;
        if (!timeMap.has(timestamp)) {
            timeMap.set(timestamp, { timestamp });
        }
        const dataPoint = timeMap.get(timestamp);
        dataPoint[`switch_${point.switch_id}_latency`] = point.latency;
        dataPoint[`switch_${point.switch_id}_packet_loss`] = point.packet_loss;
        dataPoint[`switch_${point.switch_id}_jitter`] = point.jitter;
    });
    
    // 轉換為數組並排序
    return Array.from(timeMap.values()).sort((a, b) => 
        new Date(a.timestamp) - new Date(b.timestamp)
    );
};

/**
 * 品質等級圖例組件
 */
const QualityLegend = ({ levels }) => (
    <Space size="small" style={{ marginLeft: 16 }}>
        {levels.map((level, index) => (
            <Tag 
                key={index} 
                color={level.color}
                style={{ margin: 0 }}
            >
                {level.label}
            </Tag>
        ))}
    </Space>
);

const QualityTrendChart = ({ 
    historyData, 
    switches = [], 
    selectedSwitchIds = [], 
    onSwitchChange,
    loading = false,
    metric = 'latency'
}) => {
    // 轉換數據
    const chartData = useMemo(() => {
        return transformChartData(historyData, selectedSwitchIds);
    }, [historyData, selectedSwitchIds]);
    
    // 計算 Y 軸最大值（用於品質區域）
    const yAxisMax = useMemo(() => {
        if (!chartData || chartData.length === 0) return 20;
        
        let maxValue = 0;
        chartData.forEach(point => {
            selectedSwitchIds.forEach(switchId => {
                const key = `switch_${switchId}_${metric}`;
                if (point[key] && point[key] > maxValue) {
                    maxValue = point[key];
                }
            });
        });
        
        // 確保至少顯示到 20ms，讓品質區域可見
        return Math.max(Math.ceil(maxValue * 1.2), 20);
    }, [chartData, selectedSwitchIds, metric]);
    
    const metricConfig = {
        latency: { 
            label: '延遲 (ms)', 
            suffix: '_latency',
            yAxisLabel: '延遲 (ms)'
        },
        packet_loss: { 
            label: '封包遺失率 (%)', 
            suffix: '_packet_loss',
            yAxisLabel: '遺失率 (%)'
        },
        jitter: {
            label: '抖動 (ms)',
            suffix: '_jitter',
            yAxisLabel: '抖動 (ms)'
        }
    };
    
    const config = metricConfig[metric] || metricConfig.latency;
    const qualityLevels = QUALITY_LEVELS[metric] || QUALITY_LEVELS.latency;
    
    // 格式化時間戳
    const formatTime = (timestamp) => {
        const date = new Date(timestamp);
        return date.toLocaleTimeString('zh-TW', { 
            hour: '2-digit', 
            minute: '2-digit' 
        });
    };
    
    // 格式化日期時間（用於 Tooltip）
    const formatDateTime = (timestamp) => {
        const date = new Date(timestamp);
        return date.toLocaleString('zh-TW', {
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit',
        });
    };
    
    return (
        <Card 
            title={
                <Space>
                    <span>📈 延遲趨勢圖</span>
                    <QualityLegend levels={qualityLevels} />
                </Space>
            }
            extra={
                <Select
                    mode="multiple"
                    placeholder="選擇 Switch"
                    value={selectedSwitchIds}
                    onChange={onSwitchChange}
                    style={{ minWidth: 250 }}
                    maxTagCount={2}
                    allowClear
                >
                    {switches.map(sw => (
                        <Select.Option key={sw.switch_id} value={sw.switch_id}>
                            {sw.switch_name} ({sw.ip_address || 'N/A'})
                        </Select.Option>
                    ))}
                </Select>
            }
            style={{ marginBottom: '24px' }}
        >
            <Spin spinning={loading}>
                {chartData && chartData.length > 0 ? (
                    <ResponsiveContainer width="100%" height={350}>
                        <LineChart 
                            data={chartData}
                            margin={{ top: 10, right: 30, left: 20, bottom: 5 }}
                        >
                            {/* 品質等級背景區域 - 從下到上繪製 */}
                            {qualityLevels.map((level, index) => (
                                <ReferenceArea
                                    key={index}
                                    y1={level.min}
                                    y2={Math.min(level.max, yAxisMax)}
                                    fill={level.bgColor}
                                    fillOpacity={1}
                                    ifOverflow="hidden"
                                />
                            ))}
                            
                            <CartesianGrid strokeDasharray="3 3" stroke="#e0e0e0" />
                            <XAxis 
                                dataKey="timestamp" 
                                tickFormatter={formatTime}
                                tick={{ fontSize: 11 }}
                                axisLine={{ stroke: '#d9d9d9' }}
                            />
                            <YAxis 
                                domain={[0, yAxisMax]}
                                label={{ 
                                    value: config.yAxisLabel, 
                                    angle: -90, 
                                    position: 'insideLeft',
                                    style: { textAnchor: 'middle', fontSize: 12 }
                                }}
                                tick={{ fontSize: 11 }}
                                axisLine={{ stroke: '#d9d9d9' }}
                            />
                            <Tooltip 
                                labelFormatter={formatDateTime}
                                contentStyle={{
                                    backgroundColor: 'rgba(255, 255, 255, 0.95)',
                                    border: '1px solid #d9d9d9',
                                    borderRadius: '4px',
                                }}
                                formatter={(value, name) => {
                                    // 從 name 中提取 switch_id
                                    const match = name.match(/switch_(\d+)/);
                                    if (match) {
                                        const switchId = parseInt(match[1]);
                                        const sw = switches.find(s => s.switch_id === switchId);
                                        const displayName = sw ? sw.switch_name : `Switch ${switchId}`;
                                        const unit = metric === 'packet_loss' ? '%' : 'ms';
                                        return [
                                            value !== null ? `${value.toFixed(2)} ${unit}` : 'N/A',
                                            displayName
                                        ];
                                    }
                                    return [value, name];
                                }}
                            />
                            <Legend 
                                formatter={(value) => {
                                    const match = value.match(/switch_(\d+)/);
                                    if (match) {
                                        const switchId = parseInt(match[1]);
                                        const sw = switches.find(s => s.switch_id === switchId);
                                        return sw ? sw.switch_name : `Switch ${switchId}`;
                                    }
                                    return value;
                                }}
                            />
                            {selectedSwitchIds.map((switchId, index) => (
                                <Line
                                    key={switchId}
                                    type="monotone"
                                    dataKey={`switch_${switchId}${config.suffix}`}
                                    name={`switch_${switchId}${config.suffix}`}
                                    stroke={COLORS[index % COLORS.length]}
                                    dot={{ r: 3, fill: COLORS[index % COLORS.length] }}
                                    strokeWidth={2}
                                    connectNulls
                                    activeDot={{ r: 5, strokeWidth: 2 }}
                                />
                            ))}
                        </LineChart>
                    </ResponsiveContainer>
                ) : (
                    <Empty 
                        description={
                            selectedSwitchIds.length === 0 
                                ? "請選擇要查看的 Switch" 
                                : "暫無數據"
                        } 
                    />
                )}
            </Spin>
        </Card>
    );
};

export default QualityTrendChart;
