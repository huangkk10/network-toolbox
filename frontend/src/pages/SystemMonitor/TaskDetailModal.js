import React from 'react';
import { Modal, Descriptions, Tag, Alert } from 'antd';
import moment from 'moment';

const TaskDetailModal = ({ task, visible, onClose }) => {
  if (!task) return null;

  // 狀態標籤映射
  const getStatusTag = (status) => {
    const statusMap = {
      'SUCCESS': { color: 'success', text: '成功' },
      'FAILURE': { color: 'error', text: '失敗' },
      'RUNNING': { color: 'processing', text: '執行中' },
      'PENDING': { color: 'default', text: '等待中' }
    };
    
    const config = statusMap[status] || statusMap['PENDING'];
    
    return <Tag color={config.color}>{config.text}</Tag>;
  };

  return (
    <Modal
      title={`任務詳情 - ${task.display_name}`}
      open={visible}
      onCancel={onClose}
      footer={null}
      width={800}
    >
      <Descriptions bordered column={2} size="small">
        <Descriptions.Item label="任務 ID" span={2}>
          <code style={{ fontSize: 12 }}>{task.task_id}</code>
        </Descriptions.Item>
        <Descriptions.Item label="任務名稱" span={2}>
          <code style={{ fontSize: 12 }}>{task.task_name}</code>
        </Descriptions.Item>
        <Descriptions.Item label="狀態">
          {getStatusTag(task.status)}
        </Descriptions.Item>
        <Descriptions.Item label="執行時間">
          {task.duration ? `${task.duration}s` : '-'}
        </Descriptions.Item>
        <Descriptions.Item label="開始時間" span={2}>
          {task.started_at ? moment(task.started_at).format('YYYY-MM-DD HH:mm:ss') : '-'}
        </Descriptions.Item>
        <Descriptions.Item label="結束時間" span={2}>
          {task.finished_at ? moment(task.finished_at).format('YYYY-MM-DD HH:mm:ss') : '-'}
        </Descriptions.Item>
        <Descriptions.Item label="參數" span={2}>
          <pre style={{ 
            marginBottom: 0, 
            backgroundColor: '#f5f5f5', 
            padding: 8, 
            borderRadius: 4,
            fontSize: 12,
            maxHeight: 100,
            overflow: 'auto'
          }}>
            {task.args}
          </pre>
        </Descriptions.Item>
        <Descriptions.Item label="結果" span={2}>
          <pre style={{ 
            marginBottom: 0, 
            backgroundColor: '#f5f5f5', 
            padding: 8, 
            borderRadius: 4,
            fontSize: 12,
            maxHeight: 150,
            overflow: 'auto'
          }}>
            {task.result || '-'}
          </pre>
        </Descriptions.Item>
      </Descriptions>

      {task.status === 'FAILURE' && task.error && (
        <Alert
          message="錯誤訊息"
          description={
            <pre style={{ 
              maxHeight: 200, 
              overflow: 'auto',
              fontSize: 12,
              marginBottom: 0
            }}>
              {task.error}
            </pre>
          }
          type="error"
          style={{ marginTop: 16 }}
        />
      )}
    </Modal>
  );
};

export default TaskDetailModal;
