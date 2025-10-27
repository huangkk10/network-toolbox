import React, { useState, useEffect } from 'react';
import { Card, Table, Input, Select, Button, Space, Tag, DatePicker, Modal, Descriptions, message } from 'antd';
import {
    SearchOutlined,
    ReloadOutlined,
    DownloadOutlined,
    CheckCircleOutlined,
    ClockCircleOutlined,
    InfoCircleOutlined,
    SyncOutlined,
} from '@ant-design/icons';
import axios from 'axios';
import dayjs from 'dayjs';

const { RangePicker } = DatePicker;

const LeasesTab = ({ serverId }) => {
    const [loading, setLoading] = useState(false);
    const [syncing, setSyncing] = useState(false);
    const [data, setData] = useState([]);
    const [totalCount, setTotalCount] = useState(0);
    const [currentPage, setCurrentPage] = useState(1);
    const [pageSize, setPageSize] = useState(20);
    const [searchText, setSearchText] = useState('');
    const [statusFilter, setStatusFilter] = useState('all');
    const [detailModalVisible, setDetailModalVisible] = useState(false);
    const [selectedLease, setSelectedLease] = useState(null);

    // 獲取租約數據
    const fetchLeases = async (page = 1, size = 20) => {
        setLoading(true);
        try {
            const params = {
                page: page,
                page_size: size,
            };
            
            // 如果選擇了特定 Server
            if (serverId && serverId !== 'all') {
                params.server = serverId;
            }
            
            const response = await axios.get('/api/dhcp-leases/', { params });
            
            // 轉換 API 數據格式為前端格式
            const formattedData = response.data.results.map(lease => ({
                key: lease.id,
                id: lease.id,
                ip: lease.ip_address,
                mac: lease.mac_address,
                hostname: lease.hostname,
                status: lease.is_active ? 'active' : 'expired',
                startTime: dayjs(lease.lease_start).format('YYYY-MM-DD HH:mm:ss'),
                endTime: dayjs(lease.lease_end).format('YYYY-MM-DD HH:mm:ss'),
                server: lease.server_name || `Server ${lease.server}`,
                leaseStart: lease.lease_start,
                leaseEnd: lease.lease_end,
                isActive: lease.is_active,
            }));
            
            setData(formattedData);
            setTotalCount(response.data.count);
            setCurrentPage(page);
            setPageSize(size);
            
        } catch (error) {
            console.error('獲取租約數據失敗:', error);
            message.error('載入租約數據失敗：' + (error.response?.data?.error || error.message));
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchLeases(1, pageSize);
    }, [serverId]);

    // 自動刷新功能：每 5 分鐘重新載入一次資料
    useEffect(() => {
        if (!serverId || serverId === 'all') return;

        const interval = setInterval(() => {
            console.log('[自動刷新] 重新載入租約資料...');
            fetchLeases(currentPage, pageSize);
        }, 5 * 60 * 1000); // 5 分鐘 = 300,000 毫秒

        // 清除定時器
        return () => clearInterval(interval);
    }, [serverId, currentPage, pageSize]);

    // 應用前端過濾
    const getFilteredData = () => {
        let filteredData = [...data];
        
        // 狀態過濾
        if (statusFilter !== 'all') {
            filteredData = filteredData.filter(item => item.status === statusFilter);
        }
        
        // 搜尋過濾（IP、MAC、主機名稱）
        if (searchText) {
            const searchLower = searchText.toLowerCase();
            filteredData = filteredData.filter(item => 
                item.ip.toLowerCase().includes(searchLower) ||
                item.mac.toLowerCase().includes(searchLower) ||
                item.hostname.toLowerCase().includes(searchLower)
            );
        }
        
        return filteredData;
    };

    const columns = [
        {
            title: 'IP 位址',
            dataIndex: 'ip',
            key: 'ip',
            sorter: (a, b) => a.ip.localeCompare(b.ip),
            filterDropdown: ({ setSelectedKeys, selectedKeys, confirm, clearFilters }) => (
                <div style={{ padding: 8 }}>
                    <Input
                        placeholder="搜尋 IP"
                        value={selectedKeys[0]}
                        onChange={(e) => setSelectedKeys(e.target.value ? [e.target.value] : [])}
                        onPressEnter={() => confirm()}
                        style={{ width: 188, marginBottom: 8, display: 'block' }}
                    />
                    <Space>
                        <Button
                            type="primary"
                            onClick={() => confirm()}
                            icon={<SearchOutlined />}
                            size="small"
                            style={{ width: 90 }}
                        >
                            搜尋
                        </Button>
                        <Button onClick={() => clearFilters()} size="small" style={{ width: 90 }}>
                            重置
                        </Button>
                    </Space>
                </div>
            ),
            filterIcon: (filtered) => <SearchOutlined style={{ color: filtered ? '#2196f3' : undefined }} />,
            onFilter: (value, record) => record.ip.toLowerCase().includes(value.toLowerCase()),
        },
        {
            title: 'MAC 位址',
            dataIndex: 'mac',
            key: 'mac',
            render: (mac) => <code>{mac}</code>,
        },
        {
            title: '主機名稱',
            dataIndex: 'hostname',
            key: 'hostname',
            sorter: (a, b) => a.hostname.localeCompare(b.hostname),
        },
        {
            title: '狀態',
            dataIndex: 'status',
            key: 'status',
            filters: [
                { text: '活躍中', value: 'active' },
                { text: '已過期', value: 'expired' },
                { text: '已釋放', value: 'released' },
            ],
            onFilter: (value, record) => record.status === value,
            render: (status) => {
                const statusConfig = {
                    active: { color: 'success', icon: <CheckCircleOutlined />, text: '活躍中' },
                    expired: { color: 'warning', icon: <ClockCircleOutlined />, text: '已過期' },
                    released: { color: 'default', icon: <InfoCircleOutlined />, text: '已釋放' },
                };
                const config = statusConfig[status];
                return (
                    <Tag color={config.color} icon={config.icon}>
                        {config.text}
                    </Tag>
                );
            },
        },
        {
            title: '開始時間',
            dataIndex: 'startTime',
            key: 'startTime',
            sorter: (a, b) => new Date(a.startTime) - new Date(b.startTime),
        },
        {
            title: '到期時間',
            dataIndex: 'endTime',
            key: 'endTime',
            sorter: (a, b) => new Date(a.endTime) - new Date(b.endTime),
        },
        {
            title: 'DHCP Server',
            dataIndex: 'server',
            key: 'server',
        },
        {
            title: '操作',
            key: 'action',
            render: (_, record) => (
                <Button
                    type="link"
                    size="small"
                    onClick={() => {
                        setSelectedLease(record);
                        setDetailModalVisible(true);
                    }}
                >
                    詳細
                </Button>
            ),
        },
    ];

    const handleRefresh = () => {
        fetchLeases(currentPage, pageSize);
    };

    const handleSyncLeases = async () => {
        if (!serverId || serverId === 'all') {
            message.warning('請先選擇 DHCP Server');
            return;
        }

        setSyncing(true);
        try {
            const response = await axios.post(`/api/dhcp-servers/${serverId}/sync-leases/`);
            message.success(`租約同步成功！新增 ${response.data.stats.created} 筆，更新 ${response.data.stats.updated} 筆`);
            
            // 同步完成後重新載入資料
            fetchLeases(1, pageSize);
        } catch (error) {
            console.error('同步租約失敗:', error);
            message.error('同步租約失敗：' + (error.response?.data?.error || error.message));
        } finally {
            setSyncing(false);
        }
    };

    const handleExport = () => {
        try {
            // 準備 CSV 數據
            const csvHeaders = ['IP位址', 'MAC位址', '主機名稱', '狀態', '開始時間', '到期時間', 'DHCP Server'];
            const csvRows = getFilteredData().map(lease => [
                lease.ip,
                lease.mac,
                lease.hostname,
                lease.status === 'active' ? '活躍中' : lease.status === 'expired' ? '已過期' : '已釋放',
                lease.startTime,
                lease.endTime,
                lease.server,
            ]);
            
            // 組合 CSV 內容
            const csvContent = [
                csvHeaders.join(','),
                ...csvRows.map(row => row.map(cell => `"${cell}"`).join(','))
            ].join('\n');
            
            // 添加 BOM 以支持中文
            const blob = new Blob(['\ufeff' + csvContent], { type: 'text/csv;charset=utf-8;' });
            const url = URL.createObjectURL(blob);
            const link = document.createElement('a');
            link.href = url;
            link.download = `dhcp_leases_${dayjs().format('YYYY-MM-DD_HHmmss')}.csv`;
            link.click();
            URL.revokeObjectURL(url);
            
            message.success(`成功匯出 ${csvRows.length} 筆租約數據`);
        } catch (error) {
            console.error('匯出 CSV 失敗:', error);
            message.error('匯出失敗：' + error.message);
        }
    };

    const handleTableChange = (pagination) => {
        fetchLeases(pagination.current, pagination.pageSize);
    };

    return (
        <div>
            {/* 操作工具列 */}
            <Card style={{ marginBottom: '16px' }}>
                <Space wrap>
                    <Input.Search
                        placeholder="搜尋 IP、MAC 或主機名稱..."
                        allowClear
                        style={{ width: 300 }}
                        onSearch={(value) => setSearchText(value)}
                    />
                    <Select
                        style={{ width: 120 }}
                        value={statusFilter}
                        onChange={setStatusFilter}
                        options={[
                            { value: 'all', label: '所有狀態' },
                            { value: 'active', label: '活躍中' },
                            { value: 'expired', label: '已過期' },
                            { value: 'released', label: '已釋放' },
                        ]}
                    />
                    <RangePicker />
                    <Button 
                        type="primary"
                        icon={<SyncOutlined />} 
                        onClick={handleSyncLeases}
                        loading={syncing}
                        disabled={!serverId || serverId === 'all'}
                    >
                        同步租約
                    </Button>
                    <Button icon={<DownloadOutlined />} onClick={handleExport}>
                        匯出 CSV
                    </Button>
                    <Button icon={<ReloadOutlined />} onClick={handleRefresh}>
                        重新整理
                    </Button>
                </Space>
            </Card>

            {/* 租約列表 */}
            <Card 
                title={
                    <Space>
                        <span>租約列表</span>
                        <Tag color="blue">總計: {totalCount} 筆</Tag>
                        {statusFilter !== 'all' && (
                            <Tag color="green">已過濾: {getFilteredData().length} 筆</Tag>
                        )}
                    </Space>
                }
            >
                <Table
                    columns={columns}
                    dataSource={getFilteredData()}
                    loading={loading}
                    pagination={{
                        current: currentPage,
                        pageSize: pageSize,
                        total: totalCount,
                        showSizeChanger: true,
                        showQuickJumper: true,
                        showTotal: (total) => `共 ${total} 筆`,
                        pageSizeOptions: ['10', '20', '50', '100'],
                    }}
                    onChange={handleTableChange}
                    size="middle"
                />
            </Card>

            {/* 詳細資訊 Modal */}
            <Modal
                title="租約詳細資訊"
                open={detailModalVisible}
                onCancel={() => setDetailModalVisible(false)}
                footer={[
                    <Button key="close" onClick={() => setDetailModalVisible(false)}>
                        關閉
                    </Button>,
                ]}
                width={700}
            >
                {selectedLease && (
                    <Descriptions bordered column={2}>
                        <Descriptions.Item label="IP 位址" span={2}>
                            <strong>{selectedLease.ip}</strong>
                        </Descriptions.Item>
                        <Descriptions.Item label="MAC 位址" span={2}>
                            <code>{selectedLease.mac}</code>
                        </Descriptions.Item>
                        <Descriptions.Item label="主機名稱" span={2}>
                            {selectedLease.hostname}
                        </Descriptions.Item>
                        <Descriptions.Item label="狀態">
                            <Tag
                                color={
                                    selectedLease.status === 'active'
                                        ? 'success'
                                        : selectedLease.status === 'expired'
                                            ? 'warning'
                                            : 'default'
                                }
                            >
                                {selectedLease.status === 'active'
                                    ? '活躍中'
                                    : selectedLease.status === 'expired'
                                        ? '已過期'
                                        : '已釋放'}
                            </Tag>
                        </Descriptions.Item>
                        <Descriptions.Item label="製造商">{selectedLease.vendor}</Descriptions.Item>
                        <Descriptions.Item label="開始時間">{selectedLease.startTime}</Descriptions.Item>
                        <Descriptions.Item label="到期時間">{selectedLease.endTime}</Descriptions.Item>
                        <Descriptions.Item label="DHCP Server" span={2}>
                            {selectedLease.server}
                        </Descriptions.Item>
                    </Descriptions>
                )}
            </Modal>
        </div>
    );
};

export default LeasesTab;
