import React from 'react';
import { Card, Table, Tag, Space, Divider, Button, message } from 'antd';
import { WarningOutlined, ClockCircleOutlined, CopyOutlined } from '@ant-design/icons';
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
    // 複製 Task 內容到剪貼簿（支援 HTTP 環境）
    const handleCopyTaskContent = (content) => {
        // 優先使用 Clipboard API（需要 HTTPS）
        if (navigator.clipboard && window.isSecureContext) {
            navigator.clipboard.writeText(content)
                .then(() => {
                    message.success('已複製 Task 內容到剪貼簿');
                })
                .catch(() => {
                    fallbackCopy(content);
                });
        } else {
            // Fallback: 使用傳統方式（支援 HTTP）
            fallbackCopy(content);
        }
    };

    // Fallback 複製方法
    const fallbackCopy = (content) => {
        const textArea = document.createElement('textarea');
        textArea.value = content;
        textArea.style.position = 'fixed';
        textArea.style.left = '-9999px';
        textArea.style.top = '-9999px';
        document.body.appendChild(textArea);
        textArea.focus();
        textArea.select();
        
        try {
            const successful = document.execCommand('copy');
            if (successful) {
                message.success('已複製 Task 內容到剪貼簿');
            } else {
                message.error('複製失敗，請手動選取複製');
            }
        } catch (err) {
            message.error('複製失敗，請手動選取複製');
        }
        
        document.body.removeChild(textArea);
    };

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
                        <Button
                            type="text"
                            icon={<CopyOutlined />}
                            size="small"
                            style={{ marginLeft: '12px' }}
                            onClick={() => handleCopyTaskContent(record.task_content)}
                        >
                            複製
                        </Button>
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
