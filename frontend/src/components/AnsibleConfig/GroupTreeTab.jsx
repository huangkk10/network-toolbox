/**
 * 群組樹狀圖標籤組件
 * 
 * 顯示群組階層結構，可展開查看每個群組的主機
 */

import React, { useState } from 'react';
import { Tree, Input, Space, Card, Empty, Tag } from 'antd';
import { 
    SearchOutlined, 
    FolderOutlined, 
    FolderOpenOutlined,
    DesktopOutlined 
} from '@ant-design/icons';

const GroupTreeTab = ({ treeData, onSelectHost, loading }) => {
    const [searchValue, setSearchValue] = useState('');
    const [expandedKeys, setExpandedKeys] = useState([]);
    const [autoExpandParent, setAutoExpandParent] = useState(true);

    // 生成所有可展開的 key
    const getAllKeys = (data) => {
        const keys = [];
        const traverse = (nodes) => {
            nodes.forEach(node => {
                if (!node.isLeaf) {
                    keys.push(node.key);
                }
                if (node.children) {
                    traverse(node.children);
                }
            });
        };
        traverse(data);
        return keys;
    };

    // 搜尋過濾
    const getFilteredData = (data, searchValue) => {
        if (!searchValue) return data;

        const filterTree = (nodes) => {
            return nodes.reduce((acc, node) => {
                // 檢查節點標題是否匹配
                const titleMatch = node.title.toLowerCase().includes(searchValue.toLowerCase());
                
                // 檢查子節點
                const filteredChildren = node.children ? filterTree(node.children) : [];
                
                // 如果當前節點或子節點匹配，則保留
                if (titleMatch || filteredChildren.length > 0) {
                    acc.push({
                        ...node,
                        children: filteredChildren.length > 0 ? filteredChildren : node.children,
                    });
                }
                
                return acc;
            }, []);
        };

        return filterTree(data);
    };

    // 處理搜尋
    const handleSearch = (e) => {
        const value = e.target.value;
        setSearchValue(value);

        if (value) {
            // 展開所有包含搜尋結果的節點
            const keys = getAllKeys(treeData);
            setExpandedKeys(keys);
            setAutoExpandParent(true);
        } else {
            setExpandedKeys([]);
            setAutoExpandParent(false);
        }
    };

    // 處理節點展開/收起
    const handleExpand = (expandedKeys) => {
        setExpandedKeys(expandedKeys);
        setAutoExpandParent(false);
    };

    // 處理節點選擇
    const handleSelect = (selectedKeys, info) => {
        if (info.node.isLeaf && info.node.hostname) {
            onSelectHost(info.node.hostname);
        }
    };

    // 自訂樹節點圖標
    const renderTreeIcon = ({ expanded, isLeaf }) => {
        if (isLeaf) {
            return <DesktopOutlined style={{ color: '#2196f3' }} />;
        }
        return expanded ? (
            <FolderOpenOutlined style={{ color: '#faad14' }} />
        ) : (
            <FolderOutlined style={{ color: '#faad14' }} />
        );
    };

    // 過濾後的資料
    const filteredData = getFilteredData(treeData, searchValue);

    // 統計資訊
    const totalGroups = treeData.length;
    const totalHosts = treeData.reduce((sum, group) => {
        return sum + (group.children ? group.children.length : 0);
    }, 0);

    return (
        <div>
            {/* 搜尋欄和統計 */}
            <Space direction="vertical" style={{ width: '100%', marginBottom: 16 }}>
                <Input
                    placeholder="搜尋群組或主機名稱..."
                    prefix={<SearchOutlined />}
                    value={searchValue}
                    onChange={handleSearch}
                    allowClear
                />
                
                <Space>
                    <Tag color="blue">
                        {totalGroups} 個群組
                    </Tag>
                    <Tag color="green">
                        {totalHosts} 個主機
                    </Tag>
                    {searchValue && (
                        <Tag color="orange">
                            搜尋結果：{filteredData.length} 個群組
                        </Tag>
                    )}
                </Space>
            </Space>

            {/* 樹狀圖 */}
            {filteredData.length > 0 ? (
                <Card bordered={false} style={{ background: '#fafafa' }}>
                    <Tree
                        showIcon
                        icon={renderTreeIcon}
                        treeData={filteredData}
                        expandedKeys={expandedKeys}
                        autoExpandParent={autoExpandParent}
                        onExpand={handleExpand}
                        onSelect={handleSelect}
                        style={{ 
                            background: '#fff', 
                            padding: '16px',
                            borderRadius: '4px',
                        }}
                    />
                </Card>
            ) : (
                <Empty 
                    description="沒有符合搜尋條件的群組或主機"
                    image={Empty.PRESENTED_IMAGE_SIMPLE}
                />
            )}

            {/* 提示文字 */}
            <div style={{ 
                marginTop: 16, 
                padding: '12px', 
                background: '#e6f7ff', 
                border: '1px solid #91d5ff',
                borderRadius: '4px',
                fontSize: '13px',
            }}>
                💡 <strong>提示：</strong>點擊主機名稱（藍色電腦圖標）可查看該主機的詳細配置
            </div>
        </div>
    );
};

export default GroupTreeTab;
