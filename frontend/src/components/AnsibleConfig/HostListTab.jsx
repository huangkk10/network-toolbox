/**
 * 主機列表標籤組件
 * 
 * 顯示所有主機的表格，支援排序、搜尋、分頁
 */

import React, { useState, useMemo } from 'react';
import { Table, Input, Space, Tag, Button, Tooltip } from 'antd';
import { 
    SearchOutlined, 
    DesktopOutlined, 
    EyeOutlined,
    CopyOutlined 
} from '@ant-design/icons';
import { message } from 'antd';

const HostListTab = ({ hosts, onViewConfig, loading }) => {
    const [searchText, setSearchText] = useState('');
    const [filteredHosts, setFilteredHosts] = useState(hosts);

    // 處理搜尋
    const handleSearch = (value) => {
        setSearchText(value);
        
        if (!value) {
            setFilteredHosts(hosts);
            return;
        }

        const filtered = hosts.filter(host => 
            host.hostname.toLowerCase().includes(value.toLowerCase()) ||
            host.ansible_host.toLowerCase().includes(value.toLowerCase()) ||
            host.device_number.toLowerCase().includes(value.toLowerCase()) ||
            host.groups.some(g => g.toLowerCase().includes(value.toLowerCase()))
        );
        
        setFilteredHosts(filtered);
    };

    // 複製到剪貼簿
    const handleCopy = (text, label) => {
        navigator.clipboard.writeText(text).then(() => {
            message.success(`已複製 ${label}`);
        }).catch(() => {
            message.error('複製失敗');
        });
    };

    // 表格欄位定義
    const columns = [
        {
            title: '主機名稱',
            dataIndex: 'hostname',
            key: 'hostname',
            width: 200,
            fixed: 'left',
            sorter: (a, b) => a.hostname.localeCompare(b.hostname),
            render: (text) => (
                <Space>
                    <DesktopOutlined style={{ color: '#2196f3' }} />
                    <span style={{ fontWeight: 500 }}>{text}</span>
                    <Tooltip title="複製主機名稱">
                        <Button
                            type="text"
                            size="small"
                            icon={<CopyOutlined />}
                            onClick={() => handleCopy(text, '主機名稱')}
                        />
                    </Tooltip>
                </Space>
            ),
        },
        {
            title: 'IP 地址',
            dataIndex: 'ansible_host',
            key: 'ansible_host',
            width: 150,
            sorter: (a, b) => {
                // IP 排序
                const aNum = a.ansible_host.split('.').map(Number);
                const bNum = b.ansible_host.split('.').map(Number);
                for (let i = 0; i < 4; i++) {
                    if (aNum[i] !== bNum[i]) return aNum[i] - bNum[i];
                }
                return 0;
            },
            render: (text) => (
                <Space>
                    <span style={{ fontFamily: 'monospace' }}>{text}</span>
                    {text !== 'N/A' && (
                        <Tooltip title="複製 IP">
                            <Button
                                type="text"
                                size="small"
                                icon={<CopyOutlined />}
                                onClick={() => handleCopy(text, 'IP 地址')}
                            />
                        </Tooltip>
                    )}
                </Space>
            ),
        },
        {
            title: '設備號',
            dataIndex: 'device_number',
            key: 'device_number',
            width: 150,
            sorter: (a, b) => a.device_number.localeCompare(b.device_number),
            render: (text) => (
                <Space>
                    <span style={{ fontFamily: 'monospace' }}>{text}</span>
                    {text !== 'N/A' && (
                        <Tooltip title="複製設備號">
                            <Button
                                type="text"
                                size="small"
                                icon={<CopyOutlined />}
                                onClick={() => handleCopy(text, '設備號')}
                            />
                        </Tooltip>
                    )}
                </Space>
            ),
        },
        {
            title: 'MAC 地址',
            dataIndex: 'macaddress',
            key: 'macaddress',
            width: 180,
            render: (text) => (
                <span style={{ fontFamily: 'monospace', fontSize: '12px' }}>
                    {text}
                </span>
            ),
        },
        {
            title: '使用者',
            dataIndex: 'ansible_user',
            key: 'ansible_user',
            width: 120,
        },
        {
            title: '群組',
            dataIndex: 'groups',
            key: 'groups',
            width: 250,
            render: (groups) => (
                <Space size={[0, 4]} wrap>
                    {groups.map(group => (
                        <Tag key={group} color="blue">
                            {group}
                        </Tag>
                    ))}
                </Space>
            ),
        },
        {
            title: '操作',
            key: 'action',
            width: 100,
            fixed: 'right',
            render: (_, record) => (
                <Button
                    type="primary"
                    size="small"
                    icon={<EyeOutlined />}
                    onClick={() => onViewConfig(record.hostname)}
                >
                    查看配置
                </Button>
            ),
        },
    ];

    // 更新 filteredHosts 當 hosts 改變時
    useMemo(() => {
        if (searchText) {
            handleSearch(searchText);
        } else {
            setFilteredHosts(hosts);
        }
    }, [hosts]);

    return (
        <div>
            {/* 搜尋欄 */}
            <div style={{ marginBottom: 16 }}>
                <Input
                    placeholder="搜尋主機名稱、IP、設備號或群組..."
                    prefix={<SearchOutlined />}
                    value={searchText}
                    onChange={(e) => handleSearch(e.target.value)}
                    allowClear
                    style={{ width: 400 }}
                />
                <span style={{ marginLeft: 16, color: '#666' }}>
                    顯示 {filteredHosts.length} / {hosts.length} 個主機
                </span>
            </div>

            {/* 主機列表表格 */}
            <Table
                columns={columns}
                dataSource={filteredHosts}
                loading={loading}
                rowKey="hostname"
                size="middle"
                scroll={{ x: 1200 }}
                pagination={{
                    pageSize: 10,
                    showSizeChanger: true,
                    showQuickJumper: true,
                    showTotal: (total) => `共 ${total} 個主機`,
                    pageSizeOptions: ['10', '20', '50'],
                }}
                bordered
            />
        </div>
    );
};

export default HostListTab;
