/**
 * Jenkins 統計圖表組件
 * 
 * 功能：
 * - 顯示 Jenkins Build 趨勢圖表
 * - 支援時間範圍切換（今日、7天、14天、30天、全部）
 * - 三種圖表：Build 趨勢線圖、成功率面積圖、Build 數量長條圖
 * 
 * Props:
 * - timeRange: 'today' | 'week' | '2weeks' | 'month' | 'all'
 * - serverId: number | 'all' (預設: 'all')
 */

import React, { useState, useEffect } from 'react';
import { Row, Col, Card, Spin, message, Empty } from 'antd';
import {
    LineChart,
    Line,
    AreaChart,
    Area,
    BarChart,
    Bar,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    Legend,
    ResponsiveContainer,
} from 'recharts';
import axios from 'axios';

const JenkinsStatisticsCharts = ({ timeRange = 'today', serverId = 'all' }) => {
    const [loading, setLoading] = useState(false);
    const [trendData, setTrendData] = useState([]);

    // 載入趨勢數據
    const fetchTrendData = async () => {
        setLoading(true);
        try {
            const params = {
                time_range: timeRange,
                server_id: serverId,
            };

            const response = await axios.get('/api/jenkins-analytics/build-trend/', { params });
            setTrendData(response.data || []);
        } catch (error) {
            console.error('載入 Jenkins 趨勢資料失敗:', error);
            message.error('載入趨勢資料失敗：' + (error.response?.data?.message || error.message));
        } finally {
            setLoading(false);
        }
    };

    // 當 timeRange 或 serverId 改變時重新載入
    useEffect(() => {
        fetchTrendData();
    }, [timeRange, serverId]);

    // 自訂 Tooltip 樣式
    const CustomTooltip = ({ active, payload, label }) => {
        if (active && payload && payload.length) {
            return (
                <div style={{
                    backgroundColor: 'rgba(255, 255, 255, 0.95)',
                    padding: '12px',
                    border: '1px solid #d9d9d9',
                    borderRadius: '4px',
                    boxShadow: '0 2px 8px rgba(0,0,0,0.15)',
                }}>
                    <p style={{ margin: 0, fontWeight: 600, marginBottom: 8 }}>{label}</p>
                    {payload.map((entry, index) => (
                        <p key={index} style={{ margin: 0, color: entry.color, fontSize: 13 }}>
                            {entry.name}: <span style={{ fontWeight: 600 }}>{entry.value}</span>
                            {entry.dataKey === 'success_rate' && '%'}
                        </p>
                    ))}
                </div>
            );
        }
        return null;
    };

    // 如果沒有數據
    if (!loading && trendData.length === 0) {
        return (
            <Card>
                <Empty description="目前時間範圍內沒有構建數據" />
            </Card>
        );
    }

    return (
        <Spin spinning={loading}>
            <Row gutter={[16, 16]}>
                {/* Build 趨勢線圖（成功 vs 失敗） */}
                <Col xs={24} lg={12}>
                    <Card 
                        title="Build 趨勢" 
                        style={{ height: '100%' }}
                        bodyStyle={{ padding: '16px' }}
                    >
                        <ResponsiveContainer width="100%" height={300}>
                            <LineChart data={trendData}>
                                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                                <XAxis 
                                    dataKey="time" 
                                    tick={{ fontSize: 12 }}
                                    angle={-45}
                                    textAnchor="end"
                                    height={60}
                                />
                                <YAxis tick={{ fontSize: 12 }} />
                                <Tooltip content={<CustomTooltip />} />
                                <Legend 
                                    wrapperStyle={{ fontSize: 12 }}
                                    iconType="line"
                                />
                                <Line
                                    type="monotone"
                                    dataKey="success_count"
                                    stroke="#52c41a"
                                    name="成功"
                                    strokeWidth={2}
                                    dot={{ r: 3 }}
                                    activeDot={{ r: 5 }}
                                    connectNulls={true}
                                />
                                <Line
                                    type="monotone"
                                    dataKey="failure_count"
                                    stroke="#ff4d4f"
                                    name="失敗"
                                    strokeWidth={2}
                                    dot={{ r: 3 }}
                                    activeDot={{ r: 5 }}
                                    connectNulls={true}
                                />
                                <Line
                                    type="monotone"
                                    dataKey="total_builds"
                                    stroke="#1890ff"
                                    name="總計"
                                    strokeWidth={2}
                                    strokeDasharray="5 5"
                                    dot={{ r: 2 }}
                                    activeDot={{ r: 4 }}
                                    connectNulls={true}
                                />
                            </LineChart>
                        </ResponsiveContainer>
                    </Card>
                </Col>

                {/* 成功率面積圖 */}
                <Col xs={24} lg={12}>
                    <Card 
                        title="成功率趨勢" 
                        style={{ height: '100%' }}
                        bodyStyle={{ padding: '16px' }}
                    >
                        <ResponsiveContainer width="100%" height={300}>
                            <AreaChart data={trendData}>
                                <defs>
                                    <linearGradient id="colorSuccessRate" x1="0" y1="0" x2="0" y2="1">
                                        <stop offset="5%" stopColor="#52c41a" stopOpacity={0.8}/>
                                        <stop offset="95%" stopColor="#52c41a" stopOpacity={0.1}/>
                                    </linearGradient>
                                </defs>
                                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                                <XAxis 
                                    dataKey="time" 
                                    tick={{ fontSize: 12 }}
                                    angle={-45}
                                    textAnchor="end"
                                    height={60}
                                />
                                <YAxis 
                                    tick={{ fontSize: 12 }}
                                    domain={[0, 100]}
                                    label={{ value: '%', position: 'insideLeft', style: { fontSize: 12 } }}
                                />
                                <Tooltip content={<CustomTooltip />} />
                                <Legend 
                                    wrapperStyle={{ fontSize: 12 }}
                                    iconType="rect"
                                />
                                <Area
                                    type="monotone"
                                    dataKey="success_rate"
                                    stroke="#52c41a"
                                    fillOpacity={1}
                                    fill="url(#colorSuccessRate)"
                                    name="成功率"
                                    strokeWidth={2}
                                    connectNulls={true}
                                />
                            </AreaChart>
                        </ResponsiveContainer>
                    </Card>
                </Col>

                {/* Build 數量長條圖 */}
                <Col xs={24}>
                    <Card 
                        title="Build 數量分佈" 
                        bodyStyle={{ padding: '16px' }}
                    >
                        <ResponsiveContainer width="100%" height={300}>
                            <BarChart data={trendData}>
                                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                                <XAxis 
                                    dataKey="time" 
                                    tick={{ fontSize: 12 }}
                                    angle={-45}
                                    textAnchor="end"
                                    height={60}
                                />
                                <YAxis tick={{ fontSize: 12 }} />
                                <Tooltip content={<CustomTooltip />} />
                                <Legend 
                                    wrapperStyle={{ fontSize: 12 }}
                                    iconType="rect"
                                />
                                <Bar 
                                    dataKey="success_count" 
                                    stackId="builds"
                                    fill="#52c41a" 
                                    name="成功"
                                    radius={[0, 0, 4, 4]}
                                />
                                <Bar 
                                    dataKey="failure_count" 
                                    stackId="builds"
                                    fill="#ff4d4f" 
                                    name="失敗"
                                    radius={[4, 4, 0, 0]}
                                />
                            </BarChart>
                        </ResponsiveContainer>
                    </Card>
                </Col>
            </Row>
        </Spin>
    );
};

export default JenkinsStatisticsCharts;
