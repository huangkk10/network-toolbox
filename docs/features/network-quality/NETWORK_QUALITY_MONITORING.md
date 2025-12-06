# 網路連線品質監控功能規劃

> **文件狀態**：規劃中（尚未實施）  
> **創建日期**：2025-12-07  
> **作者**：Network Toolbox Team  
> **相關頁面**：DHCP Server 分析 > Switch 管理

---

## 📋 目錄

1. [功能概述](#功能概述)
2. [系統架構](#系統架構)
3. [資料模型](#資料模型)
4. [後端 API 設計](#後端-api-設計)
5. [前端 UI 設計](#前端-ui-設計)
6. [定時任務設計](#定時任務設計)
7. [數據收集與聚合策略](#數據收集與聚合策略)
8. [實施計畫](#實施計畫)
9. [檔案清單](#檔案清單)

---

## 🎯 功能概述

### 背景

根據截圖，現有 Switch 管理頁面已顯示：
- Switch 列表（名稱、Remote ID、MAC 地址、IP 地址、狀態、連接設備數等）
- 7 台 Switch，全部為「活躍」狀態

### 需求

在現有頁面基礎上，新增 **DHCP Server 到各台 Switch 的網路連線品質監控**功能：

1. **即時監控**：顯示 DHCP Server 到每台 Switch 的延遲、封包遺失率
2. **歷史趨勢**：透過曲線圖展示歷史網路品質數據
3. **時間範圍選擇**：支援 1 小時、6 小時、24 小時、7 天、30 天等時間範圍
4. **多 Switch 比較**：可同時選擇多台 Switch 進行品質比較

### 目標

- 快速發現網路異常
- 追蹤歷史品質趨勢
- 輔助網路問題排查

---

## 🏗️ 系統架構

```
┌─────────────────────────────────────────────────────────────────┐
│                        前端 (React + Ant Design)                 │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  │
│  │ 品質概覽卡片     │  │ 趨勢曲線圖      │  │ Switch 品質表格  │  │
│  │ (Statistic)     │  │ (recharts)      │  │ (Table)         │  │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                        後端 API (Django REST)                    │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ GET /api/dhcp-servers/{id}/network-quality/             │    │
│  │ GET /api/dhcp-servers/{id}/network-quality/history/     │    │
│  │ POST /api/dhcp-servers/{id}/network-quality/refresh/    │    │
│  └─────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                    網路品質服務 (NetworkQualityService)          │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  │
│  │ Ping 檢測       │  │ 數據聚合        │  │ 歷史查詢        │  │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                    定時任務 (Celery)                             │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ collect_network_quality_task (每 5 分鐘)                │    │
│  └─────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                    資料庫 (PostgreSQL)                           │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ NetworkQualityRecord (網路品質記錄表)                    │    │
│  └─────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🗂️ 資料模型

### NetworkQualityRecord 模型

```python
# backend/api/models.py

class NetworkQualityRecord(models.Model):
    """
    網路連線品質記錄
    
    記錄 DHCP Server 到 Switch 的網路品質指標
    """
    
    # 關聯
    dhcp_server = models.ForeignKey(
        'DHCPServer', 
        on_delete=models.CASCADE,
        related_name='network_quality_records',
        verbose_name='DHCP Server'
    )
    switch = models.ForeignKey(
        'Switch', 
        on_delete=models.CASCADE,
        related_name='network_quality_records',
        verbose_name='Switch'
    )
    
    # 品質指標
    latency_ms = models.FloatField(
        verbose_name='延遲 (ms)',
        help_text='Ping 往返時間'
    )
    latency_min_ms = models.FloatField(
        verbose_name='最小延遲 (ms)',
        null=True,
        blank=True
    )
    latency_max_ms = models.FloatField(
        verbose_name='最大延遲 (ms)',
        null=True,
        blank=True
    )
    packet_loss = models.FloatField(
        verbose_name='封包遺失率 (%)',
        help_text='0-100 的百分比值'
    )
    jitter_ms = models.FloatField(
        verbose_name='抖動 (ms)',
        null=True,
        blank=True,
        help_text='延遲變化程度'
    )
    
    # 連線狀態
    is_reachable = models.BooleanField(
        default=True,
        verbose_name='是否可達'
    )
    
    # Ping 詳細資訊
    packets_sent = models.IntegerField(
        default=5,
        verbose_name='發送封包數'
    )
    packets_received = models.IntegerField(
        default=5,
        verbose_name='接收封包數'
    )
    
    # 時間戳
    recorded_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        verbose_name='記錄時間'
    )
    
    class Meta:
        db_table = 'network_quality_record'
        verbose_name = '網路品質記錄'
        verbose_name_plural = '網路品質記錄'
        indexes = [
            models.Index(fields=['dhcp_server', 'switch', 'recorded_at']),
            models.Index(fields=['dhcp_server', 'recorded_at']),
            models.Index(fields=['switch', 'recorded_at']),
            models.Index(fields=['recorded_at']),
        ]
        ordering = ['-recorded_at']
    
    def __str__(self):
        return f"{self.dhcp_server.name} -> {self.switch.name}: {self.latency_ms}ms ({self.recorded_at})"
```

### 資料保留策略

| 數據類型 | 保留時間 | 說明 |
|---------|---------|------|
| 原始數據 | 7 天 | 每 5 分鐘一筆 |
| 小時聚合 | 30 天 | 每小時平均值 |
| 日聚合 | 365 天 | 每日平均值 |

---

## 🔌 後端 API 設計

### API 端點列表

| Method | Endpoint | 說明 |
|--------|----------|------|
| GET | `/api/dhcp-servers/{id}/network-quality/` | 獲取當前所有 Switch 的網路品質 |
| GET | `/api/dhcp-servers/{id}/network-quality/history/` | 獲取歷史數據（帶時間範圍參數） |
| POST | `/api/dhcp-servers/{id}/network-quality/refresh/` | 手動觸發品質檢測 |
| GET | `/api/dhcp-servers/{id}/network-quality/summary/` | 獲取品質統計摘要 |

### API 詳細設計

#### 1. 獲取當前網路品質

```
GET /api/dhcp-servers/{id}/network-quality/
```

**Response:**
```json
{
    "success": true,
    "data": {
        "dhcp_server": {
            "id": 9,
            "name": "10.250.10.1",
            "ip_address": "10.250.10.1"
        },
        "recorded_at": "2025-12-07T03:30:38Z",
        "summary": {
            "total_switches": 7,
            "reachable": 6,
            "unreachable": 1,
            "avg_latency_ms": 1.25,
            "avg_packet_loss": 0.5
        },
        "switches": [
            {
                "switch_id": 1,
                "switch_name": "VN32KYC41Z",
                "switch_ip": "10.250.16.13",
                "quality": {
                    "latency_ms": 0.85,
                    "latency_min_ms": 0.52,
                    "latency_max_ms": 1.23,
                    "packet_loss": 0,
                    "jitter_ms": 0.12,
                    "is_reachable": true,
                    "status": "excellent"
                },
                "recorded_at": "2025-12-07T03:30:38Z"
            },
            {
                "switch_id": 2,
                "switch_name": "VN4AKYC1W0",
                "switch_ip": "10.250.15.15",
                "quality": {
                    "latency_ms": 1.20,
                    "latency_min_ms": 0.89,
                    "latency_max_ms": 1.56,
                    "packet_loss": 0,
                    "jitter_ms": 0.18,
                    "is_reachable": true,
                    "status": "good"
                },
                "recorded_at": "2025-12-07T03:30:38Z"
            }
        ]
    }
}
```

#### 2. 獲取歷史數據

```
GET /api/dhcp-servers/{id}/network-quality/history/?time_range=24h&switch_ids=1,2,3
```

**Query Parameters:**

| 參數 | 類型 | 必填 | 說明 |
|-----|------|-----|------|
| `time_range` | string | 是 | 時間範圍：`1h`, `6h`, `24h`, `7d`, `30d` |
| `switch_ids` | string | 否 | Switch ID 列表，逗號分隔（不傳則返回全部） |
| `metric` | string | 否 | 指標類型：`latency`, `packet_loss`, `jitter`（預設 `latency`） |

**Response:**
```json
{
    "success": true,
    "data": {
        "time_range": "24h",
        "interval": "15min",
        "start_time": "2025-12-06T03:30:00Z",
        "end_time": "2025-12-07T03:30:00Z",
        "switches": [
            {
                "switch_id": 1,
                "switch_name": "VN32KYC41Z",
                "switch_ip": "10.250.16.13",
                "data_points": [
                    {
                        "timestamp": "2025-12-06T03:30:00Z",
                        "latency_ms": 0.82,
                        "packet_loss": 0,
                        "jitter_ms": 0.10,
                        "is_reachable": true
                    },
                    {
                        "timestamp": "2025-12-06T03:45:00Z",
                        "latency_ms": 0.91,
                        "packet_loss": 0,
                        "jitter_ms": 0.15,
                        "is_reachable": true
                    }
                ]
            }
        ],
        "statistics": {
            "avg_latency_ms": 0.88,
            "max_latency_ms": 2.35,
            "min_latency_ms": 0.45,
            "avg_packet_loss": 0.1,
            "uptime_percent": 99.8
        }
    }
}
```

#### 3. 手動刷新

```
POST /api/dhcp-servers/{id}/network-quality/refresh/
```

**Request Body (Optional):**
```json
{
    "switch_ids": [1, 2, 3]
}
```

**Response:**
```json
{
    "success": true,
    "message": "網路品質檢測已觸發",
    "task_id": "abc123-def456"
}
```

### ViewSet 實現

```python
# backend/api/views.py

class NetworkQualityViewSet(viewsets.ViewSet):
    """網路品質 API"""
    
    permission_classes = [AllowAny]  # 開發環境
    
    @action(detail=True, methods=['get'], url_path='network-quality')
    def current_quality(self, request, pk=None):
        """獲取當前網路品質"""
        pass
    
    @action(detail=True, methods=['get'], url_path='network-quality/history')
    def quality_history(self, request, pk=None):
        """獲取歷史網路品質"""
        pass
    
    @action(detail=True, methods=['post'], url_path='network-quality/refresh')
    def refresh_quality(self, request, pk=None):
        """手動觸發品質檢測"""
        pass
    
    @action(detail=True, methods=['get'], url_path='network-quality/summary')
    def quality_summary(self, request, pk=None):
        """獲取品質統計摘要"""
        pass
```

---

## 🖥️ 前端 UI 設計

### 頁面佈局

在現有 Switch 管理頁面新增「網路品質」Tab：

```
┌─────────────────────────────────────────────────────────────────────────┐
│  品 Switch 列表  │  Top Switch  │  📊 網路品質                          │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │  時間範圍:                                                          │ │
│  │  ○ 1小時  ○ 6小時  ● 24小時  ○ 7天  ○ 30天      [🔄 刷新] [⚙ 設定] │ │
│  └────────────────────────────────────────────────────────────────────┘ │
│                                                                          │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐    │
│  │ 📶 平均延遲  │ │ 📉 封包遺失  │ │ ✅ 連線正常  │ │ ❌ 連線異常  │    │
│  │              │ │              │ │              │ │              │    │
│  │   1.25 ms    │ │    0.5 %     │ │      6       │ │      1       │    │
│  │   ↓ 0.2ms    │ │   ↓ 0.1%    │ │              │ │              │    │
│  └──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘    │
│                                                                          │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │  📈 延遲趨勢圖                               Switch 選擇: [▼ 全部] │ │
│  │                                                                    │ │
│  │  3ms ┤                                                             │ │
│  │      │                    ╭─╮                                      │ │
│  │  2ms ┤        ╭──╮      ╭╯  ╰╮                                     │ │
│  │      │   ╭──╮╭╯  ╰╮  ╭─╯    ╰──╮                                  │ │
│  │  1ms ┤──╯  ╰╯    ╰──╯          ╰───────────────────────           │ │
│  │      │                                                             │ │
│  │  0ms ┼────────────────────────────────────────────────────────    │ │
│  │      00:00    06:00    12:00    18:00    24:00                     │ │
│  │                                                                    │ │
│  │  ─── VN32KYC41Z (10.250.16.13)                                    │ │
│  │  ─── VN4AKYC1W0 (10.250.15.15)                                    │ │
│  │  ─── VN31KYC2JG (10.250.14.12)                                    │ │
│  └────────────────────────────────────────────────────────────────────┘ │
│                                                                          │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │  Switch 網路品質詳情                                    🔍 搜尋    │ │
│  ├────────────┬────────────┬────────┬────────┬────────┬──────┬───────┤ │
│  │ Switch 名稱│ IP 地址    │ 延遲   │ 遺失率 │ 抖動   │ 狀態 │ 操作  │ │
│  ├────────────┼────────────┼────────┼────────┼────────┼──────┼───────┤ │
│  │ VN32KYC41Z │10.250.16.13│ 0.85ms │   0%   │ 0.12ms │ 🟢   │ 📊 📈 │ │
│  │ VN4AKYC1W0 │10.250.15.15│ 1.20ms │   0%   │ 0.18ms │ 🟢   │ 📊 📈 │ │
│  │ VN31KYC2JG │10.250.14.12│ 0.92ms │   0%   │ 0.15ms │ 🟢   │ 📊 📈 │ │
│  │ VN4BKYC0Q5 │10.250.11.63│ 15.3ms │   2%   │ 3.21ms │ 🟡   │ 📊 📈 │ │
│  │ Switch-XX  │10.250.10.30│  N/A   │  100%  │  N/A   │ 🔴   │ 📊 📈 │ │
│  └────────────┴────────────┴────────┴────────┴────────┴──────┴───────┘ │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### 品質狀態定義

| 狀態 | 圖示 | 延遲條件 | 封包遺失條件 | 顏色 |
|-----|------|---------|-------------|------|
| 優秀 (Excellent) | 🟢 | < 1ms | 0% | `#52c41a` |
| 良好 (Good) | 🟢 | < 5ms | < 1% | `#52c41a` |
| 一般 (Fair) | 🟡 | < 20ms | < 5% | `#faad14` |
| 較差 (Poor) | 🟠 | < 100ms | < 10% | `#fa8c16` |
| 離線 (Offline) | 🔴 | N/A | 100% | `#ff4d4f` |

### React 組件結構

```
frontend/src/
├── components/
│   └── NetworkQuality/
│       ├── index.js                    # 組件導出
│       ├── NetworkQualityTab.js        # 主 Tab 組件
│       ├── QualitySummaryCards.js      # 統計卡片
│       ├── QualityTrendChart.js        # 趨勢曲線圖
│       ├── QualityTable.js             # 品質詳情表格
│       ├── TimeRangeSelector.js        # 時間範圍選擇器
│       ├── SwitchSelector.js           # Switch 多選器
│       └── QualityStatusTag.js         # 品質狀態標籤
├── pages/
│   └── DHCPAnalytics/
│       └── SwitchManagement.js         # 修改：新增 Tab
└── services/
    └── networkQualityApi.js            # API 調用服務
```

### 主要組件代碼示例

#### TimeRangeSelector.js

```javascript
import React from 'react';
import { Radio, Space } from 'antd';

const TIME_RANGES = [
    { label: '1 小時', value: '1h' },
    { label: '6 小時', value: '6h' },
    { label: '24 小時', value: '24h' },
    { label: '7 天', value: '7d' },
    { label: '30 天', value: '30d' },
];

const TimeRangeSelector = ({ value, onChange }) => {
    return (
        <Space>
            <span>時間範圍：</span>
            <Radio.Group 
                value={value} 
                onChange={(e) => onChange(e.target.value)}
                optionType="button"
                buttonStyle="solid"
            >
                {TIME_RANGES.map(range => (
                    <Radio.Button key={range.value} value={range.value}>
                        {range.label}
                    </Radio.Button>
                ))}
            </Radio.Group>
        </Space>
    );
};

export default TimeRangeSelector;
```

#### QualityTrendChart.js

```javascript
import React from 'react';
import { Card, Select, Empty, Spin } from 'antd';
import {
    LineChart,
    Line,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    Legend,
    ResponsiveContainer
} from 'recharts';

// 為每個 Switch 生成不同顏色
const COLORS = [
    '#1890ff', '#52c41a', '#faad14', '#f5222d', 
    '#722ed1', '#13c2c2', '#eb2f96', '#fa8c16'
];

const QualityTrendChart = ({ 
    data, 
    switches, 
    selectedSwitchIds, 
    onSwitchChange,
    loading,
    metric = 'latency' 
}) => {
    const metricConfig = {
        latency: { label: '延遲 (ms)', key: 'latency_ms' },
        packet_loss: { label: '封包遺失率 (%)', key: 'packet_loss' },
        jitter: { label: '抖動 (ms)', key: 'jitter_ms' }
    };
    
    const config = metricConfig[metric];
    
    return (
        <Card 
            title="📈 延遲趨勢圖"
            extra={
                <Select
                    mode="multiple"
                    placeholder="選擇 Switch"
                    value={selectedSwitchIds}
                    onChange={onSwitchChange}
                    style={{ minWidth: 200 }}
                    maxTagCount={2}
                >
                    {switches.map(sw => (
                        <Select.Option key={sw.id} value={sw.id}>
                            {sw.name} ({sw.ip_address})
                        </Select.Option>
                    ))}
                </Select>
            }
        >
            <Spin spinning={loading}>
                {data && data.length > 0 ? (
                    <ResponsiveContainer width="100%" height={300}>
                        <LineChart data={data}>
                            <CartesianGrid strokeDasharray="3 3" />
                            <XAxis 
                                dataKey="timestamp" 
                                tickFormatter={(val) => new Date(val).toLocaleTimeString()}
                            />
                            <YAxis 
                                label={{ 
                                    value: config.label, 
                                    angle: -90, 
                                    position: 'insideLeft' 
                                }}
                            />
                            <Tooltip 
                                labelFormatter={(val) => new Date(val).toLocaleString()}
                            />
                            <Legend />
                            {selectedSwitchIds.map((switchId, index) => {
                                const sw = switches.find(s => s.id === switchId);
                                return (
                                    <Line
                                        key={switchId}
                                        type="monotone"
                                        dataKey={`switch_${switchId}_${config.key}`}
                                        name={sw ? `${sw.name}` : `Switch ${switchId}`}
                                        stroke={COLORS[index % COLORS.length]}
                                        dot={false}
                                        strokeWidth={2}
                                    />
                                );
                            })}
                        </LineChart>
                    </ResponsiveContainer>
                ) : (
                    <Empty description="暫無數據" />
                )}
            </Spin>
        </Card>
    );
};

export default QualityTrendChart;
```

#### QualityStatusTag.js

```javascript
import React from 'react';
import { Tag, Tooltip } from 'antd';

const getQualityStatus = (latency, packetLoss) => {
    if (packetLoss === 100 || latency === null) {
        return { status: 'offline', label: '離線', color: '#ff4d4f' };
    }
    if (latency < 1 && packetLoss === 0) {
        return { status: 'excellent', label: '優秀', color: '#52c41a' };
    }
    if (latency < 5 && packetLoss < 1) {
        return { status: 'good', label: '良好', color: '#52c41a' };
    }
    if (latency < 20 && packetLoss < 5) {
        return { status: 'fair', label: '一般', color: '#faad14' };
    }
    return { status: 'poor', label: '較差', color: '#fa8c16' };
};

const QualityStatusTag = ({ latency, packetLoss }) => {
    const { label, color } = getQualityStatus(latency, packetLoss);
    
    return (
        <Tooltip title={`延遲: ${latency ?? 'N/A'}ms, 遺失: ${packetLoss}%`}>
            <Tag color={color}>{label}</Tag>
        </Tooltip>
    );
};

export default QualityStatusTag;
```

---

## ⏰ 定時任務設計

### 保護機制

**遵循現有的系統保護機制**：所有定時任務在執行前會檢查 CPU 使用率，確保在 **80% 以下** 才執行，避免影響系統正常運作。

### CPU 檢查工具函數

```python
# backend/library/utils/system_check.py

import psutil
import logging

logger = logging.getLogger(__name__)

# CPU 使用率閾值
CPU_THRESHOLD = 80

def check_cpu_usage() -> tuple[bool, float]:
    """
    檢查 CPU 使用率是否在安全範圍內
    
    Returns:
        tuple[bool, float]: (是否可執行, 當前 CPU 使用率)
    """
    cpu_percent = psutil.cpu_percent(interval=1)
    can_execute = cpu_percent < CPU_THRESHOLD
    
    if not can_execute:
        logger.warning(f"CPU usage {cpu_percent}% >= {CPU_THRESHOLD}%, task will be skipped")
    
    return can_execute, cpu_percent


def check_system_resources() -> dict:
    """
    檢查系統資源狀態
    
    Returns:
        {
            'can_execute': bool,
            'cpu_percent': float,
            'memory_percent': float,
            'reason': str or None
        }
    """
    cpu_percent = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory()
    
    result = {
        'can_execute': True,
        'cpu_percent': cpu_percent,
        'memory_percent': memory.percent,
        'reason': None
    }
    
    if cpu_percent >= CPU_THRESHOLD:
        result['can_execute'] = False
        result['reason'] = f'CPU usage {cpu_percent}% >= {CPU_THRESHOLD}%'
    
    return result
```

### Celery Task（含 CPU 檢查）

```python
# backend/api/tasks.py

import logging
from celery import shared_task
from library.services.network_quality_service import NetworkQualityService
from library.utils.system_check import check_cpu_usage, check_system_resources

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def collect_network_quality_task(self, dhcp_server_id: int = None):
    """
    收集網路品質數據
    
    每 5 分鐘執行一次，檢測所有 DHCP Server 到其關聯 Switch 的網路品質
    
    保護機制：
    - CPU 使用率 >= 80% 時跳過執行
    - 失敗時最多重試 3 次，間隔 60 秒
    
    Args:
        dhcp_server_id: 指定 DHCP Server ID（不傳則檢測全部）
    """
    # ========== CPU 使用率檢查 ==========
    can_execute, cpu_percent = check_cpu_usage()
    if not can_execute:
        logger.warning(
            f"[collect_network_quality_task] Skipped due to high CPU usage: {cpu_percent}%"
        )
        return {
            'status': 'skipped',
            'reason': f'CPU usage {cpu_percent}% >= 80%',
            'cpu_percent': cpu_percent
        }
    # =====================================
    
    try:
        logger.info(f"[collect_network_quality_task] Starting (CPU: {cpu_percent}%)")
        
        service = NetworkQualityService()
        
        if dhcp_server_id:
            results = service.collect_server_quality(dhcp_server_id)
        else:
            results = service.collect_all_quality()
        
        logger.info(
            f"[collect_network_quality_task] Completed: {results.get('total_records', 0)} records"
        )
        
        return {
            'status': 'success',
            'cpu_percent': cpu_percent,
            **results
        }
        
    except Exception as e:
        logger.error(f"[collect_network_quality_task] Failed: {e}", exc_info=True)
        raise self.retry(exc=e, countdown=60)


@shared_task
def cleanup_old_quality_records_task():
    """
    清理舊的網路品質記錄
    
    每天凌晨執行，清理超過保留期限的數據
    
    保護機制：
    - CPU 使用率 >= 80% 時跳過執行
    """
    # ========== CPU 使用率檢查 ==========
    can_execute, cpu_percent = check_cpu_usage()
    if not can_execute:
        logger.warning(
            f"[cleanup_old_quality_records_task] Skipped due to high CPU usage: {cpu_percent}%"
        )
        return {
            'status': 'skipped',
            'reason': f'CPU usage {cpu_percent}% >= 80%',
            'cpu_percent': cpu_percent
        }
    # =====================================
    
    from api.models import NetworkQualityRecord
    from django.utils import timezone
    from datetime import timedelta
    
    logger.info(f"[cleanup_old_quality_records_task] Starting (CPU: {cpu_percent}%)")
    
    # 刪除 7 天前的原始數據
    cutoff = timezone.now() - timedelta(days=7)
    deleted, _ = NetworkQualityRecord.objects.filter(
        recorded_at__lt=cutoff
    ).delete()
    
    logger.info(f"[cleanup_old_quality_records_task] Cleaned up {deleted} old records")
    
    return {
        'status': 'success',
        'deleted': deleted,
        'cpu_percent': cpu_percent
    }
```

### 任務優先級配置

| 任務 | 優先級 | CPU 閾值 | 允許跳過 | 說明 |
|-----|--------|---------|---------|------|
| `collect_network_quality_task` | normal | 80% | ✅ | 每 5 分鐘收集，可跳過 |
| `cleanup_old_quality_records_task` | low | 80% | ✅ | 每日清理，可跳過 |

### Celery Beat 配置

```python
# backend/network_toolbox/celery.py

from celery.schedules import crontab

CELERY_BEAT_SCHEDULE = {
    # ... 現有任務 ...
    
    # 網路品質收集任務（每 5 分鐘，含 CPU 檢查）
    'collect-network-quality': {
        'task': 'api.tasks.collect_network_quality_task',
        'schedule': crontab(minute='*/5'),  # 每 5 分鐘
        'options': {
            'queue': 'network_quality',
            'expires': 240,  # 4 分鐘後過期，避免任務堆積
        }
    },
    
    # 舊數據清理任務（每天凌晨 3 點，含 CPU 檢查）
    'cleanup-old-quality-records': {
        'task': 'api.tasks.cleanup_old_quality_records_task',
        'schedule': crontab(hour=3, minute=0),  # 每天凌晨 3 點
        'options': {
            'queue': 'maintenance',
            'expires': 3600,  # 1 小時後過期
        }
    },
}
```

### 保護機制流程圖

```
┌─────────────────────────────────────────────────────────────┐
│                    Celery Beat 觸發任務                      │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    檢查 CPU 使用率                           │
│                    psutil.cpu_percent()                      │
└─────────────────────────────────────────────────────────────┘
                              │
                    ┌─────────┴─────────┐
                    │                   │
                    ▼                   ▼
         ┌──────────────────┐  ┌──────────────────┐
         │   CPU < 80%      │  │   CPU >= 80%     │
         │   ✅ 執行任務    │  │   ⏭️ 跳過任務    │
         └──────────────────┘  └──────────────────┘
                    │                   │
                    ▼                   ▼
         ┌──────────────────┐  ┌──────────────────┐
         │  收集網路品質    │  │  記錄 WARNING    │
         │  儲存到資料庫    │  │  返回 skipped    │
         └──────────────────┘  └──────────────────┘
                    │                   │
                    ▼                   ▼
         ┌──────────────────┐  ┌──────────────────┐
         │  返回 success    │  │  等待下次執行    │
         │  記錄 INFO 日誌  │  │  (5 分鐘後)      │
         └──────────────────┘  └──────────────────┘
```

### 日誌輸出範例

**正常執行：**
```
[INFO] [collect_network_quality_task] Starting (CPU: 45.2%)
[INFO] [collect_network_quality_task] Completed: 7 records
```

**CPU 過高跳過：**
```
[WARNING] CPU usage 85.3% >= 80%, task will be skipped
[WARNING] [collect_network_quality_task] Skipped due to high CPU usage: 85.3%
```

---

## 📊 數據收集與聚合策略

### 數據粒度

| 時間範圍 | 原始數據間隔 | 查詢時聚合粒度 | 數據點數量 |
|---------|-------------|---------------|-----------|
| 1 小時 | 5 分鐘 | 5 分鐘 | 12 |
| 6 小時 | 5 分鐘 | 5 分鐘 | 72 |
| 24 小時 | 5 分鐘 | 15 分鐘 | 96 |
| 7 天 | 5 分鐘 | 1 小時 | 168 |
| 30 天 | 5 分鐘 | 4 小時 | 180 |

### 聚合查詢 SQL

```python
# backend/library/services/network_quality_service.py

def get_aggregated_history(self, dhcp_server_id: int, switch_id: int, 
                           time_range: str) -> List[Dict]:
    """
    獲取聚合後的歷史數據
    """
    # 時間範圍配置
    RANGE_CONFIG = {
        '1h': {'hours': 1, 'interval': '5 minutes'},
        '6h': {'hours': 6, 'interval': '5 minutes'},
        '24h': {'hours': 24, 'interval': '15 minutes'},
        '7d': {'days': 7, 'interval': '1 hour'},
        '30d': {'days': 30, 'interval': '4 hours'},
    }
    
    config = RANGE_CONFIG.get(time_range, RANGE_CONFIG['24h'])
    
    # 使用 Django ORM 或原生 SQL 進行聚合查詢
    # ...
```

### Ping 檢測服務

```python
# backend/library/services/network_quality_service.py

import subprocess
import re
from typing import Dict, List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class NetworkQualityService:
    """網路品質檢測服務"""
    
    DEFAULT_PING_COUNT = 5
    DEFAULT_TIMEOUT = 2  # 秒
    
    def ping_host(self, ip: str, count: int = None) -> Dict:
        """
        執行 Ping 測試
        
        Args:
            ip: 目標 IP 地址
            count: Ping 次數
            
        Returns:
            {
                'is_reachable': bool,
                'latency_ms': float or None,
                'latency_min_ms': float or None,
                'latency_max_ms': float or None,
                'packet_loss': float,
                'jitter_ms': float or None,
                'packets_sent': int,
                'packets_received': int,
                'error': str or None
            }
        """
        count = count or self.DEFAULT_PING_COUNT
        
        try:
            # Linux ping 命令
            result = subprocess.run(
                ['ping', '-c', str(count), '-W', str(self.DEFAULT_TIMEOUT), ip],
                capture_output=True,
                text=True,
                timeout=count * self.DEFAULT_TIMEOUT + 5
            )
            
            return self._parse_ping_output(result.stdout, result.returncode, count)
            
        except subprocess.TimeoutExpired:
            logger.warning(f"Ping timeout for {ip}")
            return self._create_unreachable_result(count, "Timeout")
        except Exception as e:
            logger.error(f"Ping error for {ip}: {e}")
            return self._create_unreachable_result(count, str(e))
    
    def _parse_ping_output(self, output: str, return_code: int, 
                           packets_sent: int) -> Dict:
        """解析 Ping 輸出"""
        result = {
            'is_reachable': return_code == 0,
            'latency_ms': None,
            'latency_min_ms': None,
            'latency_max_ms': None,
            'packet_loss': 100.0,
            'jitter_ms': None,
            'packets_sent': packets_sent,
            'packets_received': 0,
            'error': None
        }
        
        # 解析封包統計
        # 格式: "5 packets transmitted, 5 received, 0% packet loss"
        packet_match = re.search(
            r'(\d+) packets transmitted, (\d+) received.*?(\d+(?:\.\d+)?)% packet loss',
            output
        )
        if packet_match:
            result['packets_sent'] = int(packet_match.group(1))
            result['packets_received'] = int(packet_match.group(2))
            result['packet_loss'] = float(packet_match.group(3))
        
        # 解析延遲統計
        # 格式: "rtt min/avg/max/mdev = 0.521/0.856/1.234/0.123 ms"
        rtt_match = re.search(
            r'rtt min/avg/max/mdev = ([\d.]+)/([\d.]+)/([\d.]+)/([\d.]+) ms',
            output
        )
        if rtt_match:
            result['latency_min_ms'] = float(rtt_match.group(1))
            result['latency_ms'] = float(rtt_match.group(2))  # 平均值
            result['latency_max_ms'] = float(rtt_match.group(3))
            result['jitter_ms'] = float(rtt_match.group(4))  # mdev 作為抖動
        
        return result
    
    def _create_unreachable_result(self, packets_sent: int, error: str) -> Dict:
        """創建不可達結果"""
        return {
            'is_reachable': False,
            'latency_ms': None,
            'latency_min_ms': None,
            'latency_max_ms': None,
            'packet_loss': 100.0,
            'jitter_ms': None,
            'packets_sent': packets_sent,
            'packets_received': 0,
            'error': error
        }
    
    def collect_server_quality(self, dhcp_server_id: int) -> Dict:
        """
        收集指定 DHCP Server 的所有 Switch 網路品質
        """
        from api.models import DHCPServer, Switch, NetworkQualityRecord
        
        server = DHCPServer.objects.get(id=dhcp_server_id)
        switches = Switch.objects.filter(server=server, status='active')
        
        results = []
        for switch in switches:
            quality = self.ping_host(switch.ip_address)
            
            # 儲存記錄
            record = NetworkQualityRecord.objects.create(
                dhcp_server=server,
                switch=switch,
                latency_ms=quality['latency_ms'] or 0,
                latency_min_ms=quality['latency_min_ms'],
                latency_max_ms=quality['latency_max_ms'],
                packet_loss=quality['packet_loss'],
                jitter_ms=quality['jitter_ms'],
                is_reachable=quality['is_reachable'],
                packets_sent=quality['packets_sent'],
                packets_received=quality['packets_received']
            )
            
            results.append({
                'switch_id': switch.id,
                'switch_name': switch.name,
                'quality': quality,
                'record_id': record.id
            })
        
        return {
            'dhcp_server_id': dhcp_server_id,
            'total': len(results),
            'results': results
        }
    
    def collect_all_quality(self) -> Dict:
        """收集所有 DHCP Server 的網路品質"""
        from api.models import DHCPServer
        
        servers = DHCPServer.objects.filter(status='online')
        all_results = []
        
        for server in servers:
            result = self.collect_server_quality(server.id)
            all_results.append(result)
        
        return {
            'total_servers': len(all_results),
            'total_records': sum(r['total'] for r in all_results),
            'results': all_results
        }
```

---

## 📅 實施計畫

### 階段一：後端基礎建設（2 天）

| 任務 | 說明 | 預估時間 |
|-----|------|---------|
| 資料模型 | 創建 `NetworkQualityRecord` 模型 | 0.25 天 |
| 資料庫遷移 | 執行 migration | 0.25 天 |
| 網路品質服務 | 實現 `NetworkQualityService` | 0.5 天 |
| API 端點 | 實現 ViewSet 和路由 | 0.5 天 |
| 定時任務 | 配置 Celery Task | 0.5 天 |

### 階段二：前端開發（2 天）

| 任務 | 說明 | 預估時間 |
|-----|------|---------|
| 組件結構 | 創建組件目錄和基礎文件 | 0.25 天 |
| 統計卡片 | 實現 `QualitySummaryCards` | 0.25 天 |
| 趨勢圖表 | 實現 `QualityTrendChart` | 0.5 天 |
| 品質表格 | 實現 `QualityTable` | 0.5 天 |
| Tab 整合 | 整合到 Switch 管理頁面 | 0.5 天 |

### 階段三：整合測試（1 天）

| 任務 | 說明 | 預估時間 |
|-----|------|---------|
| API 測試 | 測試所有 API 端點 | 0.25 天 |
| 前端測試 | 測試 UI 交互和圖表 | 0.25 天 |
| 整合測試 | 端對端測試 | 0.25 天 |
| 性能優化 | 優化查詢和圖表渲染 | 0.25 天 |

### 總計：5 天

---

## 📁 檔案清單

### 後端新增/修改檔案

```
backend/
├── api/
│   ├── models.py                           # 新增 NetworkQualityRecord
│   ├── serializers.py                      # 新增 NetworkQualitySerializer
│   ├── views.py                            # 新增 NetworkQualityViewSet
│   ├── urls.py                             # 新增路由
│   └── tasks.py                            # 新增定時任務
├── library/
│   └── services/
│       └── network_quality_service.py      # 新增網路品質服務
└── migrations/
    └── XXXX_add_network_quality_record.py  # 資料庫遷移
```

### 前端新增/修改檔案

```
frontend/src/
├── components/
│   └── NetworkQuality/
│       ├── index.js                        # 組件導出
│       ├── NetworkQualityTab.js            # 主 Tab 組件
│       ├── QualitySummaryCards.js          # 統計卡片
│       ├── QualityTrendChart.js            # 趨勢曲線圖
│       ├── QualityTable.js                 # 品質詳情表格
│       ├── TimeRangeSelector.js            # 時間範圍選擇器
│       ├── SwitchSelector.js               # Switch 多選器
│       └── QualityStatusTag.js             # 品質狀態標籤
├── pages/
│   └── DHCPAnalytics/
│       └── SwitchManagement.js             # 修改：新增 Tab
└── services/
    └── networkQualityApi.js                # API 調用服務
```

### 測試檔案

```
tests/
├── unit/
│   └── backend/
│       └── test_network_quality_service.py
└── integration/
    └── api/
        └── test_network_quality_api.py
```

---

## ✅ 驗收標準

### 功能驗收

- [ ] 可以查看所有 Switch 的當前網路品質
- [ ] 可以選擇不同時間範圍（1h, 6h, 24h, 7d, 30d）
- [ ] 趨勢圖可以正確顯示歷史數據
- [ ] 可以選擇多個 Switch 進行比較
- [ ] 手動刷新功能正常工作
- [ ] 品質狀態（優秀/良好/一般/較差/離線）正確顯示

### 性能驗收

- [ ] API 響應時間 < 2 秒
- [ ] 圖表渲染流暢（60fps）
- [ ] 數據聚合查詢效率

### 數據驗收

- [ ] 定時任務每 5 分鐘正確執行
- [ ] 數據自動清理正常工作
- [ ] 數據聚合結果準確

---

## 📝 備註

- 此文件為規劃文件，尚未實施
- Ping 檢測需要適當的系統權限
- 建議先在測試環境驗證後再部署到生產環境
- 根據 Switch 數量，可能需要調整任務並發度

---

**最後更新**：2025-12-07  
**版本**：v1.0（規劃版）
