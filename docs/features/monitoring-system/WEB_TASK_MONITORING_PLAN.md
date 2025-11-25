# Web 系統監控整合背景任務監控功能規劃

**創建日期**：2025-11-25  
**目的**：在現有 Web 系統監控頁面中整合 Celery 背景任務監控功能  
**狀態**：規劃階段（未執行）  
**預計時間**：3-4 小時

---

## 📊 需求分析

### 現況評估

**現有系統監控頁面包含**：
- ✅ 磁碟空間使用率（38.1%）
- ✅ CPU 使用率（0.4%）
- ✅ 記憶體使用率（30.1%）
- ✅ 資源使用趨勢圖（過去 1 天）

**缺少的監控項目**：
- ❌ 背景任務執行狀態
- ❌ 任務成功/失敗統計
- ❌ Worker 狀態監控
- ❌ 任務執行時間統計

### 目標與價值

**為什麼要在 Web 中整合任務監控？**

1. **統一監控入口**：
   - ✅ 不需要額外訪問 Flower（http://localhost:5555）
   - ✅ 與系統資源監控整合在同一頁面
   - ✅ 更符合用戶使用習慣

2. **即時問題發現**：
   - ✅ 任務失敗時立即看到紅色警告
   - ✅ Worker 離線時顯示異常狀態
   - ✅ 任務積壓時提示需要處理

3. **數據關聯分析**：
   - ✅ CPU 飆升 + 任務執行中 → 確認是任務導致
   - ✅ 記憶體不足 + 大量任務失敗 → 資源問題
   - ✅ 磁碟滿載 + 存儲任務失敗 → NAS 問題

4. **操作便利性**：
   - ✅ 快速重試失敗任務
   - ✅ 手動觸發緊急任務
   - ✅ 查看任務執行歷史

---

## 🎨 UI/UX 設計方案

### 方案 A：下方擴展區域（推薦）

**佈局結構**：
```
┌─────────────────────────────────────────────────────────┐
│  系統監控                     [自動刷新] [暫停] [手動刷新]  │
│  即時查看監控資料和資源使用狀況                               │
├─────────────────────────────────────────────────────────┤
│  ┌──────────┐  ┌──────────┐  ┌──────────┐              │
│  │ 磁碟 38.1%│  │ CPU 0.4% │  │ 記憶體   │              │
│  │          │  │          │  │  30.1%   │              │
│  └──────────┘  └──────────┘  └──────────┘              │
├─────────────────────────────────────────────────────────┤
│  資源使用趨勢 [近 3 星 | 近 1 日]                          │
│  [折線圖顯示 CPU、記憶體、磁碟趨勢]                          │
├─────────────────────────────────────────────────────────┤
│  背景任務監控                                             │  ← 🆕 新增區塊
├─────────────────────────────────────────────────────────┤
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐│
│  │ 執行中   │  │ 成功率   │  │ Worker   │  │ 失敗任務  ││
│  │ 2 個任務 │  │ 98.5%    │  │ 8/8 在線 │  │ 3 個      ││
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘│
├─────────────────────────────────────────────────────────┤
│  最近任務執行記錄                      [查看全部 →]         │
│  ┌─────────────────────────────────────────────────────┐│
│  │ 任務名稱           狀態    執行時間   耗時    操作      ││
│  │ DHCP 日誌同步      成功    2 分鐘前   1.2s   [詳情]   ││
│  │ Jenkins Builds同步 執行中  剛剛       45s    [取消]   ││
│  │ NAS 連線檢測       失敗    5 分鐘前   0.3s   [重試]   ││
│  └─────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────┘
```

**優點**：
- ✅ 與現有監控頁面整合，統一入口
- ✅ 保持現有佈局不變，新增區域自然延伸
- ✅ 用戶可以一次看到所有監控數據

**缺點**：
- ⚠️ 頁面會變長，需要捲動查看
- ⚠️ 行動裝置上可能需要優化排版

---

### 方案 B：Tab 分頁設計

**佈局結構**：
```
┌─────────────────────────────────────────────────────────┐
│  系統監控                                                 │
│  [系統資源] [背景任務] [網路監控] [日誌分析]   ← 🆕 Tab 切換 │
├─────────────────────────────────────────────────────────┤
│  背景任務監控 頁籤內容                                     │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐│
│  │ 今日成功 │  │ 今日失敗 │  │ 執行中   │  │ Worker   ││
│  │ 1,245 個 │  │ 18 個    │  │ 3 個     │  │ 8/8 在線 ││
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘│
├─────────────────────────────────────────────────────────┤
│  任務執行趨勢（過去 24 小時）                               │
│  [折線圖：成功/失敗數量]                                   │
├─────────────────────────────────────────────────────────┤
│  定時任務列表（共 17 個）              [篩選: 全部 ▼]       │
│  ┌─────────────────────────────────────────────────────┐│
│  │ 任務名稱               頻率      下次執行   狀態  操作  ││
│  │ DHCP 日誌同步          每10分鐘  5分鐘後   啟用  [⋯]  ││
│  │ Jenkins Builds 同步    每10分鐘  8分鐘後   啟用  [⋯]  ││
│  │ Jenkins 資料驗證       每日02:00 明天02:00 啟用  [⋯]  ││
│  └─────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────┘
```

**優點**：
- ✅ 頁面內容分離，不會太擁擠
- ✅ 任務監控可以有更多展示空間
- ✅ 可以添加更多監控類別（網路、日誌等）

**缺點**：
- ⚠️ 需要切換 Tab 查看，不如方案 A 直觀
- ⚠️ 無法同時看到系統資源和任務狀態

---

### 方案 C：折疊卡片設計（混合方案）

**佈局結構**：
```
┌─────────────────────────────────────────────────────────┐
│  系統監控                                                 │
├─────────────────────────────────────────────────────────┤
│  [系統資源區域 - 始終可見]                                 │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐              │
│  │ 磁碟 38.1%│  │ CPU 0.4% │  │ 記憶體   │              │
│  └──────────┘  └──────────┘  └──────────┘              │
├─────────────────────────────────────────────────────────┤
│  背景任務監控 ▼ [展開/收起]        [查看詳細 →]            │  ← 🆕 可折疊
│  ┌──────────┐  ┌──────────┐  ┌──────────┐              │
│  │ 執行中 2 │  │ 成功率   │  │ Worker   │              │
│  │          │  │ 98.5%    │  │ 8/8 在線 │              │
│  └──────────┘  └──────────┘  └──────────┘              │
│                                                          │
│  [展開後顯示詳細任務列表]                                  │
└─────────────────────────────────────────────────────────┘
```

**優點**：
- ✅ 折疊狀態：簡潔，只顯示關鍵指標
- ✅ 展開狀態：完整信息，詳細列表
- ✅ 靈活性高，用戶可自由控制

**缺點**：
- ⚠️ 需要額外交互（點擊展開/收起）
- ⚠️ 折疊邏輯需要前端狀態管理

---

## 🎯 推薦方案：方案 A（下方擴展區域）

**選擇理由**：

1. **實施最簡單**：直接在現有頁面下方新增組件
2. **用戶體驗最佳**：所有監控數據在同一頁面，無需切換
3. **與現有風格一致**：使用相同的卡片佈局和顏色方案
4. **易於維護**：邏輯清晰，不需要複雜的狀態管理

---

## 🔧 技術實施方案

### 階段 1：後端 API 設計（1 小時）

#### 1.1 任務統計 API

**端點**：`GET /api/system/task-stats/`

**返回數據結構**：
```json
{
  "success": true,
  "data": {
    "current_tasks": {
      "running": 2,           // 當前執行中的任務數量
      "pending": 5,           // 隊列中等待的任務數量
      "scheduled": 17         // 定時任務總數
    },
    "today_stats": {
      "success": 1245,        // 今日成功任務數
      "failure": 18,          // 今日失敗任務數
      "total": 1263,          // 今日總任務數
      "success_rate": 98.58   // 成功率（%）
    },
    "workers": {
      "total": 8,             // Worker 總數（並發數）
      "active": 8,            // 活躍 Worker 數
      "offline": 0            // 離線 Worker 數
    },
    "avg_execution_time": {
      "all_tasks": 2.5,       // 所有任務平均執行時間（秒）
      "last_hour": 1.8        // 最近 1 小時平均執行時間
    }
  }
}
```

**實現邏輯**：
```python
# backend/api/views.py

from rest_framework.decorators import api_view
from rest_framework.response import Response
from celery import current_app
from django.utils import timezone
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)

@api_view(['GET'])
def get_task_stats(request):
    """
    獲取任務統計數據
    
    返回：
    - 當前執行中的任務數量
    - 今日任務成功/失敗統計
    - Worker 狀態
    - 平均執行時間
    """
    try:
        # 獲取 Celery Inspector
        inspector = current_app.control.inspect()
        
        # 1. 當前執行中的任務
        active_tasks = inspector.active()
        running_count = sum(len(tasks) for tasks in (active_tasks or {}).values())
        
        # 2. 定時任務數量
        scheduled_count = len(current_app.conf.beat_schedule)
        
        # 3. Worker 狀態
        stats = inspector.stats()
        worker_count = len(stats) if stats else 0
        
        # 4. 今日任務統計（從 Celery Result Backend 或數據庫查詢）
        # 注意：需要啟用 task_track_started 和 result backend
        today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
        
        # 如果使用 Django Celery Results（推薦）
        try:
            from django_celery_results.models import TaskResult
            
            today_tasks = TaskResult.objects.filter(
                date_created__gte=today_start
            )
            
            success_count = today_tasks.filter(status='SUCCESS').count()
            failure_count = today_tasks.filter(status='FAILURE').count()
            total_count = today_tasks.count()
            
            success_rate = (success_count / total_count * 100) if total_count > 0 else 0
            
        except ImportError:
            # 如果沒有安裝 django-celery-results，返回模擬數據
            logger.warning('django-celery-results 未安裝，返回模擬數據')
            success_count = 0
            failure_count = 0
            total_count = 0
            success_rate = 0
        
        # 返回統計數據
        return Response({
            'success': True,
            'data': {
                'current_tasks': {
                    'running': running_count,
                    'pending': 0,  # 需要查詢 Redis 隊列長度
                    'scheduled': scheduled_count
                },
                'today_stats': {
                    'success': success_count,
                    'failure': failure_count,
                    'total': total_count,
                    'success_rate': round(success_rate, 2)
                },
                'workers': {
                    'total': worker_count,
                    'active': worker_count,  # 簡化：假設所有 Worker 都活躍
                    'offline': 0
                },
                'avg_execution_time': {
                    'all_tasks': 0,  # 需要從結果中計算
                    'last_hour': 0
                }
            }
        })
        
    except Exception as e:
        logger.error(f'獲取任務統計失敗: {e}', exc_info=True)
        return Response({
            'success': False,
            'error': str(e)
        }, status=500)
```

#### 1.2 最近任務列表 API

**端點**：`GET /api/system/recent-tasks/`

**查詢參數**：
- `limit`: 返回數量（預設 10）
- `status`: 過濾狀態（all/success/failure/running）

**返回數據結構**：
```json
{
  "success": true,
  "data": {
    "tasks": [
      {
        "task_id": "abc123-def456-ghi789",
        "task_name": "api.tasks.sync_all_dhcp_logs_task",
        "display_name": "DHCP 日誌同步",
        "status": "SUCCESS",           // SUCCESS/FAILURE/RUNNING/PENDING
        "started_at": "2025-11-25T10:30:00Z",
        "finished_at": "2025-11-25T10:30:01.2Z",
        "duration": 1.2,               // 執行時間（秒）
        "args": "[server_id=1]",       // 任務參數
        "result": "同步成功：500 筆",   // 任務結果
        "error": null                  // 錯誤訊息（如果失敗）
      },
      // ... 更多任務
    ],
    "total": 50
  }
}
```

**實現邏輯**：
```python
@api_view(['GET'])
def get_recent_tasks(request):
    """
    獲取最近任務列表
    """
    try:
        limit = int(request.GET.get('limit', 10))
        status_filter = request.GET.get('status', 'all')
        
        from django_celery_results.models import TaskResult
        
        # 查詢最近任務
        query = TaskResult.objects.all()
        
        if status_filter != 'all':
            query = query.filter(status=status_filter.upper())
        
        tasks = query.order_by('-date_created')[:limit]
        
        # 任務名稱映射（中文顯示）
        task_name_map = {
            'api.tasks.sync_all_dhcp_logs_task': 'DHCP 日誌同步',
            'api.tasks.sync_jenkins_builds': 'Jenkins Builds 同步',
            'api.tasks.check_nas_connection_task': 'NAS 連線檢測',
            # ... 其他任務映射
        }
        
        result = []
        for task in tasks:
            # 計算執行時間
            duration = None
            if task.date_done and task.date_created:
                duration = (task.date_done - task.date_created).total_seconds()
            
            result.append({
                'task_id': task.task_id,
                'task_name': task.task_name,
                'display_name': task_name_map.get(task.task_name, task.task_name),
                'status': task.status,
                'started_at': task.date_created.isoformat() if task.date_created else None,
                'finished_at': task.date_done.isoformat() if task.date_done else None,
                'duration': round(duration, 2) if duration else None,
                'args': task.task_args or '[]',
                'result': str(task.result) if task.result else None,
                'error': task.traceback if task.status == 'FAILURE' else None
            })
        
        return Response({
            'success': True,
            'data': {
                'tasks': result,
                'total': TaskResult.objects.count()
            }
        })
        
    except Exception as e:
        logger.error(f'獲取任務列表失敗: {e}', exc_info=True)
        return Response({
            'success': False,
            'error': str(e)
        }, status=500)
```

#### 1.3 註冊路由

**文件**：`backend/api/urls.py`

```python
from django.urls import path
from . import views

urlpatterns = [
    # ... 現有路由 ...
    
    # 🆕 系統監控 - 任務統計
    path('system/task-stats/', views.get_task_stats, name='task_stats'),
    path('system/recent-tasks/', views.get_recent_tasks, name='recent_tasks'),
]
```

---

### 階段 2：前端組件開發（2 小時）

#### 2.1 創建任務監控組件

**文件結構**：
```
frontend/src/pages/SystemMonitor/
├── index.js                    # 主頁面（現有）
├── TaskMonitoring.js           # 🆕 任務監控組件
├── TaskStatsCards.js           # 🆕 任務統計卡片
├── RecentTasksTable.js         # 🆕 最近任務表格
└── styles.css                  # 樣式（可選）
```

#### 2.2 任務統計卡片組件

**文件**：`frontend/src/pages/SystemMonitor/TaskStatsCards.js`

```jsx
import React from 'react';
import { Card, Row, Col, Statistic, Badge, Progress } from 'antd';
import {
  PlayCircleOutlined,
  CheckCircleOutlined,
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
```

#### 2.3 最近任務表格組件

**文件**：`frontend/src/pages/SystemMonitor/RecentTasksTable.js`

```jsx
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
```

#### 2.4 主任務監控組件

**文件**：`frontend/src/pages/SystemMonitor/TaskMonitoring.js`

```jsx
import React, { useState, useEffect } from 'react';
import { Card, Button, Space, message } from 'antd';
import { ReloadOutlined } from '@ant-design/icons';
import axios from 'axios';
import TaskStatsCards from './TaskStatsCards';
import RecentTasksTable from './RecentTasksTable';

const TaskMonitoring = () => {
  const [stats, setStats] = useState(null);
  const [tasks, setTasks] = useState([]);
  const [loading, setLoading] = useState(false);

  // 獲取任務統計
  const fetchTaskStats = async () => {
    try {
      const response = await axios.get('/api/system/task-stats/');
      if (response.data.success) {
        setStats(response.data.data);
      }
    } catch (error) {
      console.error('獲取任務統計失敗:', error);
      message.error('獲取任務統計失敗');
    }
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
    // TODO: 實現重試邏輯
  };

  // 查看任務詳情
  const handleViewDetail = (task) => {
    // TODO: 實現詳情 Modal
    console.log('查看任務詳情:', task);
  };

  // 組件掛載時獲取數據
  useEffect(() => {
    fetchTaskStats();
    fetchRecentTasks();

    // 每 10 秒自動刷新
    const interval = setInterval(() => {
      fetchTaskStats();
      fetchRecentTasks();
    }, 10000);

    return () => clearInterval(interval);
  }, []);

  return (
    <div style={{ marginTop: 24 }}>
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
          <Button type="link" onClick={() => window.open('/admin', '_blank')}>
            查看全部 →
          </Button>
        }
      >
        <RecentTasksTable
          tasks={tasks}
          loading={loading}
          onRetry={handleRetry}
          onViewDetail={handleViewDetail}
        />
      </Card>
    </div>
  );
};

export default TaskMonitoring;
```

#### 2.5 整合到系統監控頁面

**文件**：`frontend/src/pages/SystemMonitor/index.js`

```jsx
import React, { useState, useEffect } from 'react';
import { Card, Row, Col, Statistic, Button, Space } from 'antd';
import {
  DatabaseOutlined,
  ThunderboltOutlined,
  DesktopOutlined,
  ReloadOutlined
} from '@ant-design/icons';
import TaskMonitoring from './TaskMonitoring';  // 🆕 導入任務監控組件
import axios from 'axios';

const SystemMonitor = () => {
  // ... 現有的狀態和邏輯 ...

  return (
    <div style={{ padding: '24px' }}>
      {/* 頁面標題 */}
      <Card
        title="系統監控"
        extra={/* ... 現有的按鈕 ... */}
        style={{ marginBottom: 16 }}
      >
        即時查看監控資料和資源使用狀況
      </Card>

      {/* 系統資源監控（現有） */}
      <Row gutter={[16, 16]}>
        <Col xs={24} sm={12} md={8}>
          {/* 磁碟使用率卡片 */}
        </Col>
        <Col xs={24} sm={12} md={8}>
          {/* CPU 使用率卡片 */}
        </Col>
        <Col xs={24} sm={12} md={8}>
          {/* 記憶體使用率卡片 */}
        </Col>
      </Row>

      {/* 資源使用趨勢圖（現有） */}
      <Card title="資源使用趨勢" style={{ marginTop: 16 }}>
        {/* ... 現有的圖表 ... */}
      </Card>

      {/* 🆕 背景任務監控 */}
      <TaskMonitoring />
    </div>
  );
};

export default SystemMonitor;
```

---

### 階段 3：優化與進階功能（1 小時）

#### 3.1 安裝 django-celery-results（推薦）

**為什麼需要？**
- Celery 預設不持久化任務結果
- django-celery-results 將結果存儲到 Django 資料庫
- 可以查詢歷史任務記錄

**安裝步驟**：
```bash
# 1. 安裝依賴
docker exec nt-django pip install django-celery-results

# 2. 添加到 requirements.txt
echo "django-celery-results==2.5.1" >> backend/requirements.txt
```

**配置**：

**文件**：`backend/network_toolbox/settings.py`

```python
INSTALLED_APPS = [
    # ... 現有 apps ...
    'django_celery_results',  # 🆕 添加
]

# Celery 配置
CELERY_RESULT_BACKEND = 'django-db'  # 🆕 使用 Django 資料庫存儲結果
CELERY_CACHE_BACKEND = 'django-cache'  # 🆕 使用 Django 快取
```

**執行遷移**：
```bash
docker exec nt-django python manage.py migrate django_celery_results
```

#### 3.2 任務詳情 Modal

**創建組件**：`frontend/src/pages/SystemMonitor/TaskDetailModal.js`

```jsx
import React from 'react';
import { Modal, Descriptions, Tag, Alert } from 'antd';
import moment from 'moment';

const TaskDetailModal = ({ task, visible, onClose }) => {
  if (!task) return null;

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
          {task.task_id}
        </Descriptions.Item>
        <Descriptions.Item label="任務名稱" span={2}>
          {task.task_name}
        </Descriptions.Item>
        <Descriptions.Item label="狀態">
          <Tag color={task.status === 'SUCCESS' ? 'success' : 'error'}>
            {task.status}
          </Tag>
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
          <pre style={{ marginBottom: 0 }}>{task.args}</pre>
        </Descriptions.Item>
        <Descriptions.Item label="結果" span={2}>
          {task.result || '-'}
        </Descriptions.Item>
      </Descriptions>

      {task.status === 'FAILURE' && task.error && (
        <Alert
          message="錯誤訊息"
          description={
            <pre style={{ maxHeight: 200, overflow: 'auto' }}>
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
```

#### 3.3 告警提示機制

**在任務統計卡片中添加警告**：

```jsx
const TaskStatsCards = ({ stats }) => {
  // 檢查是否需要顯示警告
  const showWarning = () => {
    const warnings = [];
    
    // 成功率過低
    if (stats?.today_stats?.success_rate < 90) {
      warnings.push('今日任務成功率低於 90%');
    }
    
    // Worker 離線
    if (stats?.workers?.offline > 0) {
      warnings.push(`${stats.workers.offline} 個 Worker 離線`);
    }
    
    // 失敗任務過多
    if (stats?.today_stats?.failure > 20) {
      warnings.push('今日失敗任務數量異常');
    }
    
    return warnings;
  };

  const warnings = showWarning();

  return (
    <div>
      {warnings.length > 0 && (
        <Alert
          message="任務監控警告"
          description={
            <ul style={{ marginBottom: 0 }}>
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
      
      {/* ... 原有的統計卡片 ... */}
    </div>
  );
};
```

---

## 📋 實施檢查清單

### 階段 1：後端開發

- [ ] **安裝 django-celery-results**
  - [ ] `pip install django-celery-results`
  - [ ] 添加到 `INSTALLED_APPS`
  - [ ] 配置 `CELERY_RESULT_BACKEND`
  - [ ] 執行 `python manage.py migrate`

- [ ] **創建任務統計 API**
  - [ ] 在 `api/views.py` 創建 `get_task_stats` 視圖
  - [ ] 實現 Celery Inspector 查詢邏輯
  - [ ] 實現今日任務統計查詢
  - [ ] 測試 API 返回數據格式

- [ ] **創建最近任務 API**
  - [ ] 在 `api/views.py` 創建 `get_recent_tasks` 視圖
  - [ ] 實現任務列表查詢和過濾
  - [ ] 添加任務名稱中文映射
  - [ ] 測試 API 返回數據

- [ ] **註冊路由**
  - [ ] 在 `api/urls.py` 添加路由
  - [ ] 測試端點可訪問性

### 階段 2：前端開發

- [ ] **創建任務統計卡片組件**
  - [ ] 創建 `TaskStatsCards.js`
  - [ ] 使用 Ant Design Card 和 Statistic
  - [ ] 實現響應式佈局
  - [ ] 添加圖標和顏色

- [ ] **創建最近任務表格組件**
  - [ ] 創建 `RecentTasksTable.js`
  - [ ] 定義表格列
  - [ ] 實現狀態標籤渲染
  - [ ] 添加操作按鈕

- [ ] **創建主任務監控組件**
  - [ ] 創建 `TaskMonitoring.js`
  - [ ] 實現數據獲取邏輯
  - [ ] 添加自動刷新機制
  - [ ] 整合統計卡片和任務表格

- [ ] **整合到系統監控頁面**
  - [ ] 在 `SystemMonitor/index.js` 導入組件
  - [ ] 添加到頁面下方
  - [ ] 測試佈局和樣式

### 階段 3：測試與優化

- [ ] **功能測試**
  - [ ] 測試任務統計數據顯示
  - [ ] 測試最近任務列表
  - [ ] 測試自動刷新功能
  - [ ] 測試響應式佈局

- [ ] **進階功能**
  - [ ] 實現任務詳情 Modal
  - [ ] 添加告警提示機制
  - [ ] 實現重試失敗任務功能

- [ ] **性能優化**
  - [ ] 優化 API 查詢性能
  - [ ] 添加數據快取
  - [ ] 優化前端渲染

---

## 🎯 預期效果

### 功能效果

1. **統一監控入口**：
   - ✅ 系統資源 + 任務狀態在同一頁面
   - ✅ 無需切換到 Flower 查看任務

2. **即時問題發現**：
   - ✅ 任務失敗立即顯示紅色警告
   - ✅ Worker 離線顯示異常狀態
   - ✅ 成功率過低自動提示

3. **數據關聯分析**：
   - ✅ CPU 飆升時可看到正在執行的任務
   - ✅ 任務失敗時可查看詳細錯誤
   - ✅ 長期趨勢分析

### UI 效果預覽

```
系統監控頁面
├── [現有] 磁碟/CPU/記憶體卡片
├── [現有] 資源使用趨勢圖
└── [新增] 背景任務監控
    ├── 任務統計卡片（4個）
    │   ├── 執行中任務：2 個
    │   ├── 今日成功率：98.5%
    │   ├── Worker 狀態：8/8 在線
    │   └── 今日失敗任務：3 個
    └── 最近任務執行記錄
        └── 表格（10 筆最新任務）
```

---

## 🔧 故障排查

### 問題 1：API 返回數據為空

**診斷**：
```bash
# 檢查 Celery Inspector 是否可用
docker exec nt-django python manage.py shell -c "
from celery import current_app
inspector = current_app.control.inspect()
print(inspector.stats())
"
```

**解決**：
- 確保 Celery Worker 正在運行
- 確保 Redis 連接正常
- 檢查 Celery 配置

### 問題 2：任務歷史記錄為空

**診斷**：
```bash
# 檢查 django-celery-results 是否正確安裝
docker exec nt-django python manage.py shell -c "
from django_celery_results.models import TaskResult
print(TaskResult.objects.count())
"
```

**解決**：
- 確保已執行遷移
- 確保 `CELERY_RESULT_BACKEND = 'django-db'`
- 手動執行一個測試任務驗證

### 問題 3：前端無法獲取數據

**診斷**：
```bash
# 測試 API 端點
curl http://localhost/api/system/task-stats/
```

**解決**：
- 檢查路由是否正確註冊
- 檢查 CORS 設定（如果前端跨域）
- 查看瀏覽器 Console 錯誤訊息

---

## 📚 參考資源

- **Celery Monitoring**: https://docs.celeryq.dev/en/stable/userguide/monitoring.html
- **django-celery-results**: https://github.com/celery/django-celery-results
- **Ant Design Statistic**: https://ant.design/components/statistic/
- **Ant Design Table**: https://ant.design/components/table/

---

**最後更新**：2025-11-25  
**狀態**：規劃完成，待實施  
**預計時間**：3-4 小時  
**推薦方案**：方案 A（下方擴展區域）  
**優先級**：🔥🔥 中高（提升運維效率）
