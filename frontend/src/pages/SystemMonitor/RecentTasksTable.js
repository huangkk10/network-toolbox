import React from 'react';
import { Table, Tag, Button, Tooltip } from 'antd';
import {
  CheckCircleOutlined,
  CloseCircleOutlined,
  SyncOutlined,
  ClockCircleOutlined,
  ReloadOutlined,
  InfoCircleOutlined
} from '@ant-design/icons';
import moment from 'moment';

const RecentTasksTable = ({ tasks, loading, onRetry, onViewDetail }) => {
  // 狀態標籤映射
  const getStatusTag = (status) => {
    const statusMap = {
      'SUCCESS': { color: 'success', icon: <CheckCircleOutlined />, text: '成功' },
      'FAILURE': { color: 'error', icon: <CloseCircleOutlined />, text: '失敗' },
      'RUNNING': { color: 'processing', icon: <SyncOutlined spin />, text: '執行中' },
      'PENDING': { color: 'default', icon: <ClockCircleOutlined />, text: '等待中' }
    };
    
    const config = statusMap[status] || statusMap['PENDING'];
    
    return (
      <Tag icon={config.icon} color={config.color}>
        {config.text}
      </Tag>
    );
  };

  // 表格列定義
  const columns = [
    {
      title: '任務名稱',
      dataIndex: 'display_name',
      key: 'display_name',
      width: 200,
      ellipsis: true,
      render: (text) => (
        <Tooltip title={text}>
          <span>{text}</span>
        </Tooltip>
      )
    },
    {
      title: '狀態',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      align: 'center',
      render: (status) => getStatusTag(status)
    },
    {
      title: '執行時間',
      dataIndex: 'started_at',
      key: 'started_at',
      width: 120,
      render: (time) => time ? moment(time).fromNow() : '-'
    },
    {
      title: '耗時',
      dataIndex: 'duration',
      key: 'duration',
      width: 80,
      align: 'right',
      render: (duration) => {
        if (!duration) return '-';
        if (duration < 1) return `${(duration * 1000).toFixed(0)}ms`;
        return `${duration.toFixed(1)}s`;
      }
    },
    {
      title: '結果',
      dataIndex: 'result',
      key: 'result',
      ellipsis: true,
      render: (result, record) => {
        if (record.status === 'FAILURE' && record.error) {
          return (
            <Tooltip title={record.error}>
              <span style={{ color: '#ff4d4f' }}>執行失敗</span>
            </Tooltip>
          );
        }
        return result || '-';
      }
    },
    {
      title: '操作',
      key: 'action',
      width: 120,
      align: 'center',
      render: (_, record) => (
        <div>
          <Tooltip title="查看詳情">
            <Button
              type="link"
              size="small"
              icon={<InfoCircleOutlined />}
              onClick={() => onViewDetail && onViewDetail(record)}
            />
          </Tooltip>
          {record.status === 'FAILURE' && (
            <Tooltip title="重試任務">
              <Button
                type="link"
                size="small"
                icon={<ReloadOutlined />}
                onClick={() => onRetry && onRetry(record)}
              />
            </Tooltip>
          )}
        </div>
      )
    }
  ];

  return (
    <Table
      columns={columns}
      dataSource={tasks}
      loading={loading}
      rowKey="task_id"
      pagination={false}
      size="small"
      locale={{
        emptyText: '暫無任務記錄'
      }}
    />
  );
};

export default RecentTasksTable;
