import React, { useState, useEffect } from 'react';
import { Table, Tag, Space, Input, Select, DatePicker, Button, message, Modal, Typography } from 'antd';
import { SearchOutlined, ReloadOutlined, EyeOutlined } from '@ant-design/icons';
import axios from 'axios';
import dayjs from 'dayjs';

const { Paragraph } = Typography;
const { RangePicker } = DatePicker;

const LogsTab = ({ serverId }) => {
    const [logs, setLogs] = useState([]);
    const [loading, setLoading] = useState(false);
    const [modalVisible, setModalVisible] = useState(false);
    const [selectedLog, setSelectedLog] = useState(null);
    const [pagination, setPagination] = useState({
        current: 1,
        pageSize: 50,
        total: 0,
    });
    const [filters, setFilters] = useState({
        log_type: '',
        action: '',
        search: '',
        date_range: null,
    });

    const fetchLogs = async (page = 1, pageSize = 50) => {
        setLoading(true);
        try {
            const params = {
                limit: 100,  // 限制返回數量
            };

            // 加入 server_id 篩選
            if (serverId && serverId !== 'all') {
                params.server_id = serverId;
            }

            // 加入其他篩選條件
            if (filters.log_type) params.log_type = filters.log_type;
            if (filters.search) params.search = filters.search;
            
            // 時間範圍篩選（使用 days 參數）
            if (filters.date_range && filters.date_range.length === 2) {
                const days = dayjs().diff(filters.date_range[0], 'day');
                params.days = Math.max(1, days);
            } else {
                params.days = 7;  // 預設 7 天
            }

            console.log('Fetching logs with params:', params);
            const response = await axios.get('/api/ipxe-logs/', { params });
            const data = Array.isArray(response.data) ? response.data : [];

            console.log('Fetched logs:', data.length);
            setLogs(data);
            setPagination({
                current: page,
                pageSize: pageSize,
                total: data.length,
            });
        } catch (error) {
            console.error('Error fetching logs:', error);
            message.error('載入日誌失敗：' + (error.response?.data?.message || error.message));
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchLogs(1, pagination.pageSize);
        
        // 自動刷新（每 10 分鐘）
        const intervalId = setInterval(() => {
            fetchLogs(pagination.current, pagination.pageSize);
        }, 10 * 60 * 1000);

        return () => clearInterval(intervalId);
    }, [serverId, filters]);

    const handleTableChange = (newPagination, filters, sorter) => {
        setPagination(newPagination);
    };

    const handleFilterChange = (key, value) => {
        setFilters(prev => ({ ...prev, [key]: value }));
    };

    const handleReset = () => {
        setFilters({
            log_type: '',
            action: '',
            search: '',
            date_range: null,
        });
    };

    const showLogModal = (record) => {
        setSelectedLog(record);
        setModalVisible(true);
    };

    const handleModalClose = () => {
        setModalVisible(false);
        setSelectedLog(null);
    };

    const columns = [
        {
            title: '時間',
            dataIndex: 'timestamp',
            key: 'timestamp',
            width: 180,
            render: (text) => dayjs(text).format('YYYY-MM-DD HH:mm:ss'),
            sorter: (a, b) => dayjs(a.timestamp).unix() - dayjs(b.timestamp).unix(),
        },
        {
            title: '類型',
            dataIndex: 'log_type',
            key: 'log_type',
            width: 100,
            render: (type) => {
                const colors = {
                    'MAC': 'blue',
                    'BOOT': 'green',
                };
                return <Tag color={colors[type] || 'default'}>{type}</Tag>;
            },
            filters: [
                { text: 'MAC 管理', value: 'MAC' },
                { text: 'BOOT 請求', value: 'BOOT' },
            ],
        },
        {
            title: '動作',
            dataIndex: 'action',
            key: 'action',
            width: 120,
            render: (action) => {
                const colors = {
                    'set_mac': 'cyan',
                    'get_mac': 'geekblue',
                    'boot_request': 'green',
                };
                return <Tag color={colors[action] || 'default'}>{action}</Tag>;
            },
        },
        {
            title: 'Client IP',
            dataIndex: 'client_ip',
            key: 'client_ip',
            width: 140,
        },
        {
            title: 'MAC 地址',
            dataIndex: 'mac_address',
            key: 'mac_address',
            width: 160,
            render: (text) => text || '-',
        },
        {
            title: '狀態碼',
            dataIndex: 'status_code',
            key: 'status_code',
            width: 100,
            render: (code) => {
                const color = code >= 200 && code < 300 ? 'success' : code >= 400 ? 'error' : 'warning';
                return <Tag color={color}>{code}</Tag>;
            },
        },
        {
            title: '原始 Log',
            dataIndex: 'raw',
            key: 'raw',
            width: 150,
            align: 'center',
            render: (text, record) => (
                <Button
                    type="link"
                    icon={<EyeOutlined />}
                    onClick={() => showLogModal(record)}
                    size="small"
                >
                    查看詳情
                </Button>
            ),
        },
    ];

    return (
        <div>
            {/* 篩選區域 */}
            <div style={{ marginBottom: '16px', background: '#fafafa', padding: '16px', borderRadius: '4px' }}>
                <Space wrap>
                    <Input
                        placeholder="搜尋 IP / MAC"
                        prefix={<SearchOutlined />}
                        style={{ width: 250 }}
                        value={filters.search}
                        onChange={(e) => handleFilterChange('search', e.target.value)}
                        allowClear
                    />
                    <Select
                        placeholder="日誌類型"
                        style={{ width: 150 }}
                        value={filters.log_type}
                        onChange={(value) => handleFilterChange('log_type', value)}
                        allowClear
                    >
                        <Select.Option value="MAC">MAC 管理</Select.Option>
                        <Select.Option value="BOOT">BOOT 請求</Select.Option>
                    </Select>
                    <Select
                        placeholder="動作類型"
                        style={{ width: 150 }}
                        value={filters.action}
                        onChange={(value) => handleFilterChange('action', value)}
                        allowClear
                    >
                        <Select.Option value="set_mac">set_mac</Select.Option>
                        <Select.Option value="get_mac">get_mac</Select.Option>
                        <Select.Option value="boot_request">boot_request</Select.Option>
                    </Select>
                    <RangePicker
                        value={filters.date_range}
                        onChange={(dates) => handleFilterChange('date_range', dates)}
                        format="YYYY-MM-DD"
                        placeholder={['開始日期', '結束日期']}
                    />
                    <Button icon={<ReloadOutlined />} onClick={handleReset}>
                        重置
                    </Button>
                </Space>
            </div>

            {/* 日誌表格 */}
            <Table
                columns={columns}
                dataSource={logs}
                loading={loading}
                pagination={{
                    ...pagination,
                    showSizeChanger: true,
                    showTotal: (total) => `共 ${total} 筆日誌`,
                    pageSizeOptions: ['20', '50', '100', '200'],
                }}
                onChange={handleTableChange}
                rowKey="id"
                size="middle"
                scroll={{ x: 1200 }}
            />

            {/* 原始 Log 詳情 Modal */}
            <Modal
                title="原始日誌詳情"
                open={modalVisible}
                onCancel={handleModalClose}
                footer={[
                    <Button key="close" onClick={handleModalClose}>
                        關閉
                    </Button>,
                ]}
                width={800}
            >
                {selectedLog && (
                    <div>
                        <div style={{ marginBottom: '16px' }}>
                            <strong>時間：</strong>{dayjs(selectedLog.timestamp).format('YYYY-MM-DD HH:mm:ss')}
                        </div>
                        <div style={{ marginBottom: '16px' }}>
                            <strong>Server：</strong>{selectedLog.server_ip}
                        </div>
                        <div style={{ marginBottom: '16px' }}>
                            <strong>類型：</strong>
                            <Tag color={selectedLog.log_type === 'MAC' ? 'blue' : 'green'} style={{ marginLeft: '8px' }}>
                                {selectedLog.log_type}
                            </Tag>
                        </div>
                        <div style={{ marginBottom: '16px' }}>
                            <strong>動作：</strong>
                            <Tag style={{ marginLeft: '8px' }}>{selectedLog.action}</Tag>
                        </div>
                        <div style={{ marginBottom: '16px' }}>
                            <strong>Client IP：</strong>{selectedLog.client_ip}
                        </div>
                        {selectedLog.mac_address && (
                            <div style={{ marginBottom: '16px' }}>
                                <strong>MAC 地址：</strong>{selectedLog.mac_address}
                            </div>
                        )}
                        <div style={{ marginBottom: '16px' }}>
                            <strong>狀態碼：</strong>
                            <Tag 
                                color={selectedLog.status_code >= 200 && selectedLog.status_code < 300 ? 'success' : 'error'}
                                style={{ marginLeft: '8px' }}
                            >
                                {selectedLog.status_code}
                            </Tag>
                        </div>
                        <div style={{ marginBottom: '8px' }}>
                            <strong>原始 Log：</strong>
                        </div>
                        <Paragraph
                            copyable
                            code
                            style={{
                                background: '#f5f5f5',
                                padding: '12px',
                                borderRadius: '4px',
                                whiteSpace: 'pre-wrap',
                                wordBreak: 'break-all',
                            }}
                        >
                            {selectedLog.raw || '無原始日誌'}
                        </Paragraph>
                    </div>
                )}
            </Modal>
        </div>
    );
};

export default LogsTab;
