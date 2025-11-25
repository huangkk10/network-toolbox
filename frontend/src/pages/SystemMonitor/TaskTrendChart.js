import React, { useState, useEffect } from 'react';
import { Card, Select, Spin, Empty } from 'antd';
import { 
    LineChart, 
    Line, 
    XAxis, 
    YAxis, 
    CartesianGrid, 
    Tooltip, 
    Legend, 
    ResponsiveContainer 
} from 'recharts';
import axios from 'axios';

const { Option } = Select;

const TaskTrendChart = () => {
    const [data, setData] = useState([]);
    const [topTasks, setTopTasks] = useState([]);
    const [timeRange, setTimeRange] = useState('1hour');
    const [loading, setLoading] = useState(false);

    // 為不同任務分配顏色
    const colors = [
        '#2196f3',  // 藍色
        '#52c41a',  // 綠色
        '#faad14',  // 橙色
        '#f5222d',  // 紅色
        '#722ed1',  // 紫色
    ];

    const fetchTrendData = async () => {
        setLoading(true);
        try {
            const response = await axios.get('/api/system/task-trend/', {
                params: { 
                    time_range: timeRange,
                    interval: timeRange === '1hour' ? 5 : timeRange === '6hours' ? 30 : 60
                }
            });
            
            if (response.data.success) {
                setData(response.data.data.data_points);
                setTopTasks(response.data.data.top_tasks);
            }
        } catch (error) {
            console.error('獲取任務趨勢失敗:', error);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchTrendData();
        
        // 每 30 秒自動刷新
        const interval = setInterval(fetchTrendData, 30000);
        return () => clearInterval(interval);
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [timeRange]);

    const handleTimeRangeChange = (value) => {
        setTimeRange(value);
    };

    return (
        <Card
            title="任務執行趨勢"
            extra={
                <Select 
                    value={timeRange} 
                    onChange={handleTimeRangeChange}
                    style={{ width: 120 }}
                >
                    <Option value="1hour">過去 1 小時</Option>
                    <Option value="6hours">過去 6 小時</Option>
                    <Option value="24hours">過去 24 小時</Option>
                </Select>
            }
        >
            <Spin spinning={loading}>
                {data.length > 0 ? (
                    <ResponsiveContainer width="100%" height={300}>
                        <LineChart
                            data={data}
                            margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
                        >
                            <CartesianGrid strokeDasharray="3 3" />
                            <XAxis 
                                dataKey="time" 
                                style={{ fontSize: 12 }}
                            />
                            <YAxis 
                                label={{ 
                                    value: '執行次數', 
                                    angle: -90, 
                                    position: 'insideLeft',
                                    style: { fontSize: 12 }
                                }}
                                style={{ fontSize: 12 }}
                            />
                            <Tooltip />
                            <Legend 
                                wrapperStyle={{ fontSize: 12 }}
                                iconType="line"
                            />
                            {topTasks.map((task, index) => (
                                <Line
                                    key={task.task_name}
                                    type="monotone"
                                    dataKey={task.name}
                                    stroke={colors[index % colors.length]}
                                    strokeWidth={2}
                                    dot={{ r: 3 }}
                                    activeDot={{ r: 5 }}
                                    name={task.name}
                                />
                            ))}
                        </LineChart>
                    </ResponsiveContainer>
                ) : (
                    <Empty 
                        description="暫無趨勢數據" 
                        style={{ padding: '60px 0' }}
                    />
                )}
            </Spin>
        </Card>
    );
};

export default TaskTrendChart;
