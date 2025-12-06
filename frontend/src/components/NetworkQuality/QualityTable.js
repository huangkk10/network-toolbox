/**
 * 品質詳情表格組件
 */

import React from 'react';
import { Table, Card, Input, Space, Tooltip, Badge } from 'antd';
import { SearchOutlined, LineChartOutlined } from '@ant-design/icons';
import QualityStatusTag from './QualityStatusTag';

const QualityTable = ({ 
    switches = [], 
    loading = false,
    onViewHistory,
}) => {
    const [searchText, setSearchText] = React.useState('');
    
    // 過濾數據
    const filteredData = switches.filter(sw => {
        if (!searchText) return true;
        const search = searchText.toLowerCase();
        return (
            sw.switch_name?.toLowerCase().includes(search) ||
            sw.ip_address?.toLowerCase().includes(search)
        );
    });
    
    const columns = [
        {
            title: 'Switch 名稱',
            dataIndex: 'switch_name',
            key: 'switch_name',
            sorter: (a, b) => (a.switch_name || '').localeCompare(b.switch_name || ''),
            render: (text, record) => (
                <Space>
                    <span>{text || record.switch_id}</span>
                    {record.status === 'no_data' && (
                        <Badge status="default" text="無數據" />
                    )}
                </Space>
            ),
        },
        {
            title: 'IP 地址',
            dataIndex: 'ip_address',
            key: 'ip_address',
            render: (text) => text || '-',
        },
        {
            title: '延遲',
            key: 'latency',
            sorter: (a, b) => (a.latency || 999) - (b.latency || 999),
            render: (_, record) => {
                if (record.status === 'no_data' || !record.is_reachable) return '-';
                
                const latency = record.latency;
                const min = record.latency_min;
                const max = record.latency_max;
                
                return (
                    <Tooltip title={min && max ? `最小: ${min?.toFixed(2)}ms / 最大: ${max?.toFixed(2)}ms` : ''}>
                        <span style={{ 
                            color: latency < 5 ? '#52c41a' : latency < 20 ? '#faad14' : '#ff4d4f' 
                        }}>
                            {latency?.toFixed(2)} ms
                        </span>
                    </Tooltip>
                );
            },
        },
        {
            title: '遺失率',
            key: 'packet_loss',
            sorter: (a, b) => (a.packet_loss ?? 100) - (b.packet_loss ?? 100),
            render: (_, record) => {
                if (record.status === 'no_data') return '-';
                
                const loss = record.packet_loss;
                return (
                    <span style={{ 
                        color: loss === 0 ? '#52c41a' : loss < 5 ? '#faad14' : '#ff4d4f' 
                    }}>
                        {loss}%
                    </span>
                );
            },
        },
        {
            title: '抖動',
            key: 'jitter',
            render: (_, record) => {
                if (record.status === 'no_data' || !record.is_reachable || record.jitter === null) return '-';
                return `${record.jitter?.toFixed(2)} ms`;
            },
        },
        {
            title: '狀態',
            key: 'status',
            filters: [
                { text: '優秀', value: 'excellent' },
                { text: '良好', value: 'good' },
                { text: '一般', value: 'fair' },
                { text: '較差', value: 'poor' },
                { text: '離線', value: 'offline' },
                { text: '無數據', value: 'no_data' },
            ],
            onFilter: (value, record) => record.status === value,
            render: (_, record) => {
                if (record.status === 'no_data') {
                    return <Badge status="default" text="無數據" />;
                }
                return (
                    <QualityStatusTag 
                        latency={record.latency} 
                        packetLoss={record.packet_loss} 
                    />
                );
            },
        },
        {
            title: '更新時間',
            key: 'timestamp',
            render: (_, record) => {
                if (!record.timestamp) return '-';
                return new Date(record.timestamp).toLocaleString('zh-TW');
            },
        },
        {
            title: '操作',
            key: 'action',
            width: 80,
            render: (_, record) => (
                <Tooltip title="查看歷史趨勢">
                    <LineChartOutlined 
                        style={{ cursor: 'pointer', color: '#1890ff', fontSize: '16px' }}
                        onClick={() => onViewHistory && onViewHistory(record)}
                    />
                </Tooltip>
            ),
        },
    ];
    
    return (
        <Card 
            title="Switch 網路品質詳情"
            extra={
                <Input
                    placeholder="搜尋 Switch"
                    prefix={<SearchOutlined />}
                    value={searchText}
                    onChange={(e) => setSearchText(e.target.value)}
                    style={{ width: 200 }}
                    allowClear
                />
            }
        >
            <Table
                columns={columns}
                dataSource={filteredData}
                rowKey="switch_id"
                loading={loading}
                size="middle"
                pagination={{
                    pageSize: 10,
                    showSizeChanger: true,
                    showTotal: (total) => `共 ${total} 台 Switch`,
                }}
            />
        </Card>
    );
};

export default QualityTable;
