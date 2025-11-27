import React from 'react';
import { Card, Table, Tag, Space, Divider } from 'antd';
import { WarningOutlined, ClockCircleOutlined } from '@ant-design/icons';
import CodeBlockWithHighlight from './CodeBlockWithHighlight';
import FatalSnippet from './FatalSnippet';

/**
 * Fatal Tasks 列表組件
 * 
 * 顯示所有包含 Fatal Errors 的 Ansible Tasks
 * - 可展開查看 Task 完整內容
 * - 高亮顯示 Fatal 行
 * - 顯示 Fatal 詳細上下文
 */
const FatalTaskTable = ({ fatalTasks }) => {
    const columns = [
        {
            title: '#',
            dataIndex: 'task_index',
            width: 60,
            align: 'center',
        },
        {
            title: 'Task 名稱',
            dataIndex: 'task_name',
            ellipsis: true,
            render: (text) => <strong>{text}</strong>
        },
        {
            title: '時間',
            dataIndex: 'task_start_time',
            width: 100,
            render: (time) => (
                <Space>
                    <ClockCircleOutlined />
                    {time}
                </Space>
            )
        },
        {
            title: 'Fatal 數量',
            dataIndex: 'fatal_count',
            width: 100,
            align: 'center',
            render: (count) => (
                <Tag 
                    color="red" 
                    icon={<WarningOutlined />}
                >
                    {count} 個
                </Tag>
            )
        },
        {
            title: '行範圍',
            key: 'line_range',
            width: 120,
            align: 'center',
            render: (_, record) => (
                <Tag color="blue">
                    L{record.task_start_line}-{record.task_end_line}
                </Tag>
            )
        },
        {
            title: '總行數',
            dataIndex: 'task_total_lines',
            width: 80,
            align: 'center',
        },
    ];
    
    // 展開行渲染
    const expandedRowRender = (record) => {
        return (
            <div style={{ padding: '20px', backgroundColor: '#fafafa' }}>
                {/* Task 完整內容 */}
                <div style={{ marginBottom: '24px' }}>
                    <h4 style={{ marginBottom: '12px' }}>
                        📄 Task 完整內容
                        <Tag color="blue" style={{ marginLeft: '12px' }}>
                            L{record.task_start_line}-{record.task_end_line}
                        </Tag>
                        <Tag color="red">
                            {record.fatal_count} 個 Fatal
                        </Tag>
                    </h4>
                    
                    {/* Code Block with Highlight */}
                    <CodeBlockWithHighlight
                        content={record.task_content}
                        highlightLines={record.fatal_line_numbers}
                        startLine={record.task_start_line}
                    />
                </div>
                
                {/* Fatal Snippets (使用新組件) */}
                {record.fatal_snippets && record.fatal_snippets.length > 0 && (
                    <div>
                        <Divider orientation="left">
                            🔍 Fatal 詳細上下文 ({record.fatal_snippets.length} 個)
                        </Divider>
                        
                        {record.fatal_snippets.map((snippet, idx) => (
                            <FatalSnippet 
                                key={idx} 
                                snippet={snippet}
                            />
                        ))}
                    </div>
                )}
            </div>
        );
    };
    
    return (
        <Card title={`Fatal Tasks 列表 (${fatalTasks?.length || 0} 個)`}>
            <Table
                columns={columns}
                dataSource={fatalTasks}
                rowKey="task_index"
                pagination={{
                    pageSize: 10,
                    showSizeChanger: true,
                    showTotal: (total) => `共 ${total} 個 Fatal Tasks`
                }}
                expandable={{
                    expandedRowRender,
                    expandRowByClick: false,
                }}
                size="middle"
            />
        </Card>
    );
};

export default FatalTaskTable;
