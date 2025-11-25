import React, { useState, useEffect } from 'react';
import { Card, Button, message, Alert } from 'antd';
import { ReloadOutlined } from '@ant-design/icons';
import axios from 'axios';
import TaskStatsCards from './TaskStatsCards';
import RecentTasksTable from './RecentTasksTable';
import TaskDetailModal from './TaskDetailModal';  // 🆕 導入 Modal

const TaskMonitoring = () => {
  const [stats, setStats] = useState(null);
  const [tasks, setTasks] = useState([]);
  const [loading, setLoading] = useState(false);
  const [warnings, setWarnings] = useState([]);
  const [selectedTask, setSelectedTask] = useState(null);  // 🆕 選中的任務
  const [modalVisible, setModalVisible] = useState(false);  // 🆕 Modal 可見性

  // 獲取任務統計
  const fetchTaskStats = async () => {
    try {
      const response = await axios.get('/api/system/task-stats/');
      if (response.data.success) {
        setStats(response.data.data);
        checkWarnings(response.data.data);
      }
    } catch (error) {
      console.error('獲取任務統計失敗:', error);
      message.error('獲取任務統計失敗');
    }
  };

  // 檢查是否需要顯示警告
  const checkWarnings = (statsData) => {
    const newWarnings = [];
    
    // 成功率過低
    if (statsData?.today_stats?.success_rate < 90) {
      newWarnings.push(`今日任務成功率低於 90%（當前 ${statsData.today_stats.success_rate.toFixed(1)}%）`);
    }
    
    // Worker 離線
    if (statsData?.workers?.offline > 0) {
      newWarnings.push(`${statsData.workers.offline} 個 Worker 離線`);
    }
    
    // 失敗任務過多
    if (statsData?.today_stats?.failure > 20) {
      newWarnings.push(`今日失敗任務數量異常（${statsData.today_stats.failure} 個）`);
    }
    
    setWarnings(newWarnings);
  };

  // 獲取最近任務
  const fetchRecentTasks = async () => {
    setLoading(true);
    try {
      const response = await axios.get('/api/system/recent-tasks/', {
        params: { limit: 10 }
      });
      if (response.data.success) {
        setTasks(response.data.data.tasks);
      }
    } catch (error) {
      console.error('獲取任務列表失敗:', error);
      message.error('獲取任務列表失敗');
    } finally {
      setLoading(false);
    }
  };

  // 刷新所有數據
  const handleRefresh = () => {
    fetchTaskStats();
    fetchRecentTasks();
  };

  // 重試失敗任務
  const handleRetry = (task) => {
    message.info(`重試任務：${task.display_name}`);
    // TODO: 實現重試邏輯（需要後端 API 支持）
  };

  // 查看任務詳情
  const handleViewDetail = (task) => {
    setSelectedTask(task);
    setModalVisible(true);
  };

  // 關閉 Modal
  const handleCloseModal = () => {
    setModalVisible(false);
    setSelectedTask(null);
  };

  // 組件掛載時獲取數據
  useEffect(() => {
    const fetchData = () => {
      fetchTaskStats();
      fetchRecentTasks();
    };
    
    fetchData();

    // 每 10 秒自動刷新
    const interval = setInterval(fetchData, 10000);

    return () => clearInterval(interval);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div style={{ marginTop: 24 }}>
      {/* 警告提示 */}
      {warnings.length > 0 && (
        <Alert
          message="任務監控警告"
          description={
            <ul style={{ marginBottom: 0, paddingLeft: 20 }}>
              {warnings.map((warning, index) => (
                <li key={index}>{warning}</li>
              ))}
            </ul>
          }
          type="warning"
          showIcon
          closable
          style={{ marginBottom: 16 }}
        />
      )}

      {/* 區塊標題 */}
      <Card
        title="背景任務監控"
        extra={
          <Button
            icon={<ReloadOutlined />}
            onClick={handleRefresh}
            loading={loading}
          >
            刷新
          </Button>
        }
        style={{ marginBottom: 16 }}
      >
        {/* 任務統計卡片 */}
        <TaskStatsCards stats={stats} />
      </Card>

      {/* 最近任務列表 */}
      <Card
        title="最近任務執行記錄"
        extra={
          <span style={{ fontSize: 12, color: '#999' }}>
            每 10 秒自動刷新
          </span>
        }
      >
        <RecentTasksTable
          tasks={tasks}
          loading={loading}
          onRetry={handleRetry}
          onViewDetail={handleViewDetail}
        />
      </Card>

      {/* 🆕 任務詳情 Modal */}
      <TaskDetailModal
        task={selectedTask}
        visible={modalVisible}
        onClose={handleCloseModal}
      />
    </div>
  );
};

export default TaskMonitoring;
