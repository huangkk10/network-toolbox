import React, { useState, useEffect } from 'react';
import { Card, List, Tag, Spin } from 'antd';
import { ThunderboltOutlined, ClockCircleOutlined } from '@ant-design/icons';
import axios from 'axios';

const TaskFrequencyStats = () => {
    const [frequencyData, setFrequencyData] = useState({});
    const [loading, setLoading] = useState(false);

    const fetchFrequencyData = async () => {
        setLoading(true);
        try {
            const response = await axios.get('/api/system/task-trend/', {
                params: { time_range: '1hour' }
            });
            
            if (response.data.success) {
                setFrequencyData(response.data.data.frequency_summary);
            }
        } catch (error) {
            console.error('獲取任務頻率失敗:', error);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchFrequencyData();
        
        // 每 30 秒自動刷新
        const interval = setInterval(fetchFrequencyData, 30000);
        return () => clearInterval(interval);
    }, []);

    // 排序並取前5個
    const sortedTasks = Object.entries(frequencyData)
        .sort((a, b) => b[1].total - a[1].total)
        .slice(0, 5);

    // 判斷任務是否為高頻
    const isHighFrequency = (perMinute) => perMinute >= 1;

    return (
        <Card 
            title="高頻任務 TOP 5" 
            size="small"
            style={{ height: '100%' }}
        >
            <Spin spinning={loading}>
                <List
                    dataSource={sortedTasks}
                    locale={{ emptyText: '暫無數據' }}
                    renderItem={([taskName, stats], index) => (
                        <List.Item style={{ padding: '8px 0' }}>
                            <div style={{ width: '100%' }}>
                                <div style={{ 
                                    display: 'flex', 
                                    justifyContent: 'space-between', 
                                    alignItems: 'center' 
                                }}>
                                    <span style={{ fontSize: 13 }}>
                                        {index + 1}. {taskName}
                                    </span>
                                    <Tag 
                                        icon={isHighFrequency(stats.per_minute) ? 
                                            <ThunderboltOutlined /> : 
                                            <ClockCircleOutlined />
                                        }
                                        color={isHighFrequency(stats.per_minute) ? 'red' : 'blue'}
                                    >
                                        {stats.frequency_text}
                                    </Tag>
                                </div>
                                <div style={{ 
                                    fontSize: 11, 
                                    color: '#999', 
                                    marginTop: 4 
                                }}>
                                    過去 1 小時：{stats.total} 次
                                </div>
                            </div>
                        </List.Item>
                    )}
                />
            </Spin>
        </Card>
    );
};

export default TaskFrequencyStats;
