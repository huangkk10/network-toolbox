import React from 'react';
import { Card, Row, Col, Statistic, Badge, Progress } from 'antd';
import {
  PlayCircleOutlined,
  CloseCircleOutlined,
  TeamOutlined
} from '@ant-design/icons';

const TaskStatsCards = ({ stats }) => {
  // 計算成功率顏色
  const getSuccessRateColor = (rate) => {
    if (rate >= 95) return '#52c41a';  // 綠色
    if (rate >= 80) return '#faad14';  // 橙色
    return '#ff4d4f';                   // 紅色
  };

  return (
    <Row gutter={[16, 16]}>
      {/* 執行中任務 */}
      <Col xs={24} sm={12} md={6}>
        <Card>
          <Statistic
            title="執行中任務"
            value={stats?.current_tasks?.running || 0}
            prefix={<PlayCircleOutlined style={{ color: '#2196f3' }} />}
            suffix="個"
          />
          <div style={{ marginTop: 8, fontSize: 12, color: '#999' }}>
            定時任務：{stats?.current_tasks?.scheduled || 0} 個
          </div>
        </Card>
      </Col>

      {/* 今日成功率 */}
      <Col xs={24} sm={12} md={6}>
        <Card>
          <Statistic
            title="今日成功率"
            value={stats?.today_stats?.success_rate || 0}
            precision={2}
            suffix="%"
            valueStyle={{ 
              color: getSuccessRateColor(stats?.today_stats?.success_rate || 0) 
            }}
          />
          <Progress
            percent={stats?.today_stats?.success_rate || 0}
            strokeColor={getSuccessRateColor(stats?.today_stats?.success_rate || 0)}
            showInfo={false}
            style={{ marginTop: 8 }}
          />
        </Card>
      </Col>

      {/* Worker 狀態 */}
      <Col xs={24} sm={12} md={6}>
        <Card>
          <Statistic
            title="Worker 狀態"
            value={stats?.workers?.active || 0}
            suffix={`/ ${stats?.workers?.total || 0}`}
            prefix={<TeamOutlined style={{ color: '#52c41a' }} />}
          />
          <div style={{ marginTop: 8 }}>
            <Badge status="success" text="在線" />
            {stats?.workers?.offline > 0 && (
              <Badge 
                status="error" 
                text={`離線 ${stats.workers.offline}`} 
                style={{ marginLeft: 16 }}
              />
            )}
          </div>
        </Card>
      </Col>

      {/* 失敗任務 */}
      <Col xs={24} sm={12} md={6}>
        <Card>
          <Statistic
            title="今日失敗任務"
            value={stats?.today_stats?.failure || 0}
            prefix={<CloseCircleOutlined style={{ color: '#ff4d4f' }} />}
            suffix="個"
            valueStyle={{ 
              color: (stats?.today_stats?.failure || 0) > 0 ? '#ff4d4f' : '#999' 
            }}
          />
          <div style={{ marginTop: 8, fontSize: 12, color: '#999' }}>
            總任務：{stats?.today_stats?.total || 0} 個
          </div>
        </Card>
      </Col>
    </Row>
  );
};

export default TaskStatsCards;
