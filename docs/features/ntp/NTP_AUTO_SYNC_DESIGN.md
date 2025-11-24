# NTP 自動時間校正系統設計方案

**規劃日期**：2025-11-23  
**狀態**：📋 設計階段（尚未執行）  
**優先級**：🔴 高（時間偏移已超過 5 秒）

---

## 🔍 問題分析

### 當前狀況

**檢測系統**：
- ✅ NTP 檢測任務：每 5 分鐘執行一次
- ✅ 資料記錄：完整的 NTPSyncLog 記錄
- ✅ 檢測功能：正常運作（已執行 3,445 次）

**時間偏移數據**（最近 24 小時）：
```
最早記錄（24 小時前）：-4,828.28 ms
最新記錄（現在）    ：-5,122.48 ms
總漂移量           ：-294.20 ms
漂移速率           ：-12.30 ms/hour
預估 1 天漂移      ：-295.22 ms
```

### 根本原因

**系統時鐘漂移（Clock Drift）**：
- 📉 **現象**：系統時間與 NTP 服務器的偏移持續增加
- 🔍 **原因**：
  1. **只檢測，不校正**：當前系統僅監控 NTP 偏移，未執行時間同步
  2. **硬體時鐘誤差**：系統 RTC（Real-Time Clock）存在固有誤差
  3. **溫度影響**：CPU 溫度變化影響晶振頻率
  4. **負載影響**：高負載時系統時鐘可能不準確

**時間偏移的影響**：
- ⚠️ **日誌時間戳不準確**：影響日誌分析和故障排查
- ⚠️ **Celery 任務調度誤差**：定時任務可能延遲或提前執行
- ⚠️ **SSL 憑證驗證問題**：時間偏差過大可能導致 HTTPS 請求失敗
- ⚠️ **數據庫事務時間錯誤**：影響數據完整性和一致性

---

## 🎯 設計目標

### 主要目標

1. **自動時間校正**：當偏移超過閾值時自動同步系統時間
2. **智能同步策略**：避免頻繁調整，確保系統穩定
3. **安全保護機制**：防止時間突變導致的系統問題
4. **完整日誌記錄**：記錄所有同步操作和結果

### 性能指標

| 指標 | 目標值 | 說明 |
|------|--------|------|
| **時間偏移** | <50ms | 正常運行範圍 |
| **警告閾值** | 100ms | 觸發警告日誌 |
| **同步閾值** | 200ms | 觸發自動校正 |
| **最大偏移** | 1000ms | 強制立即同步 |
| **同步間隔** | ≥30分鐘 | 防止頻繁調整 |

---

## 🏗️ 架構設計

### 系統架構圖

```
┌─────────────────────────────────────────────────────────────┐
│  檢測層（Detection Layer）- 每 5 分鐘                         │
│  ┌──────────────────────────────────────────────┐           │
│  │  check_ntp_sync_task()                       │           │
│  │  - 查詢 NTP Server (10.10.10.51)            │           │
│  │  - 記錄時間偏移到 NTPSyncLog                 │           │
│  │  - 返回偏移量、Stratum、Jitter               │           │
│  └──────────────────────────────────────────────┘           │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  決策層（Decision Layer）- 新增                              │
│  ┌──────────────────────────────────────────────┐           │
│  │  auto_sync_ntp_time_task()  【新任務】       │           │
│  │  - 讀取最近 3 次檢測結果                      │           │
│  │  - 計算平均偏移量                            │           │
│  │  - 判斷是否需要同步                          │           │
│  │  - 檢查上次同步時間（防止頻繁）               │           │
│  └──────────────────────────────────────────────┘           │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  執行層（Execution Layer）- 新增                             │
│  ┌──────────────────────────────────────────────┐           │
│  │  NTPSyncService.sync_system_time()           │           │
│  │  - 調用系統命令 (ntpdate 或 chrony)          │           │
│  │  - 記錄同步前後的時間差                      │           │
│  │  - 更新 NTPSyncOperation 記錄                │           │
│  └──────────────────────────────────────────────┘           │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  監控層（Monitoring Layer）                                  │
│  ┌──────────────────────────────────────────────┐           │
│  │  - Dashboard 顯示同步歷史                     │           │
│  │  - Alert 發送（時間偏移過大時）               │           │
│  │  - 日誌分析和趨勢預測                        │           │
│  └──────────────────────────────────────────────┘           │
└─────────────────────────────────────────────────────────────┘
```

---

## 📋 實施計劃

### Phase 1: 資料模型擴展（1 天）

**1.1 新增 NTPSyncOperation 模型**

```python
# backend/api/models.py

class NTPSyncOperation(models.Model):
    """NTP 時間同步操作記錄"""
    
    SYNC_METHOD_CHOICES = [
        ('ntpdate', 'ntpdate'),
        ('chrony', 'chronyd'),
        ('manual', 'Manual'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('success', 'Success'),
        ('failed', 'Failed'),
    ]
    
    # 基本資訊
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name='操作時間')
    ntp_server = models.CharField(max_length=100, verbose_name='NTP 服務器')
    sync_method = models.CharField(
        max_length=20, 
        choices=SYNC_METHOD_CHOICES,
        default='ntpdate',
        verbose_name='同步方法'
    )
    
    # 同步前後狀態
    offset_before = models.FloatField(verbose_name='同步前偏移 (ms)')
    offset_after = models.FloatField(null=True, blank=True, verbose_name='同步後偏移 (ms)')
    
    # 執行結果
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name='狀態'
    )
    duration = models.FloatField(null=True, blank=True, verbose_name='執行時間 (秒)')
    
    # 詳細資訊
    command_output = models.TextField(blank=True, verbose_name='命令輸出')
    error_message = models.TextField(blank=True, verbose_name='錯誤訊息')
    
    # 決策資訊
    triggered_by = models.CharField(max_length=50, verbose_name='觸發原因')  # 'auto', 'manual', 'alert'
    sync_decision_reason = models.TextField(blank=True, verbose_name='同步決策原因')
    
    class Meta:
        verbose_name = 'NTP 同步操作'
        verbose_name_plural = 'NTP 同步操作'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['-timestamp']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        return f"NTP Sync - {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')} ({self.status})"
```

**1.2 創建資料庫遷移**

```bash
python manage.py makemigrations
python manage.py migrate
```

---

### Phase 2: NTP 同步服務（1-2 天）

**2.1 擴展 NTPService 類**

```python
# backend/api/ntp_service.py

class NTPSyncService(NTPService):
    """NTP 時間同步服務（擴展版）"""
    
    def __init__(self, ntp_server: str = '10.10.10.51', timeout: int = 5):
        super().__init__(ntp_server, timeout)
        self.sync_history = []
    
    def can_sync_now(self) -> tuple[bool, str]:
        """
        檢查是否可以執行同步
        
        Returns:
            (bool, str): (是否可以同步, 原因說明)
        """
        from .models import NTPSyncOperation
        from django.utils import timezone
        from datetime import timedelta
        
        # 1. 檢查上次同步時間（至少間隔 30 分鐘）
        last_sync = NTPSyncOperation.objects.filter(
            status='success'
        ).order_by('-timestamp').first()
        
        if last_sync:
            time_since_last = timezone.now() - last_sync.timestamp
            min_interval = timedelta(minutes=30)
            
            if time_since_last < min_interval:
                remaining = (min_interval - time_since_last).total_seconds() / 60
                return False, f"距離上次同步未滿 30 分鐘（還需 {remaining:.1f} 分鐘）"
        
        # 2. 檢查是否有進行中的同步操作
        pending_sync = NTPSyncOperation.objects.filter(
            status='pending'
        ).exists()
        
        if pending_sync:
            return False, "有同步操作正在進行中"
        
        return True, "可以執行同步"
    
    def should_sync(self, threshold_ms: float = 200.0) -> tuple[bool, str, float]:
        """
        判斷是否需要同步
        
        Args:
            threshold_ms: 同步閾值（毫秒）
        
        Returns:
            (bool, str, float): (是否需要同步, 原因, 當前偏移量)
        """
        from .models import NTPSyncLog
        from django.utils import timezone
        from datetime import timedelta
        
        # 獲取最近 3 次檢測結果（最近 15 分鐘內）
        recent_time = timezone.now() - timedelta(minutes=15)
        recent_logs = NTPSyncLog.objects.filter(
            timestamp__gte=recent_time,
            status='success'
        ).order_by('-timestamp')[:3]
        
        if recent_logs.count() < 2:
            return False, "檢測數據不足", 0.0
        
        # 計算平均偏移量
        avg_offset = sum(log.offset for log in recent_logs) / recent_logs.count()
        abs_offset = abs(avg_offset)
        
        # 決策邏輯
        if abs_offset >= 1000:
            return True, f"時間偏移嚴重（{abs_offset:.1f}ms），需立即同步", avg_offset
        
        if abs_offset >= threshold_ms:
            return True, f"時間偏移超過閾值（{abs_offset:.1f}ms > {threshold_ms}ms）", avg_offset
        
        return False, f"時間偏移在可接受範圍內（{abs_offset:.1f}ms）", avg_offset
    
    def sync_system_time(self, method: str = 'ntpdate') -> Dict:
        """
        同步系統時間
        
        Args:
            method: 同步方法 ('ntpdate' 或 'chrony')
        
        Returns:
            Dict: 同步結果
            {
                'success': bool,
                'offset_before': float,
                'offset_after': float,
                'duration': float,
                'output': str,
                'error': str
            }
        """
        import subprocess
        import time
        
        result = {
            'success': False,
            'offset_before': None,
            'offset_after': None,
            'duration': 0.0,
            'output': '',
            'error': ''
        }
        
        try:
            # 1. 記錄同步前的偏移量
            pre_check = self.check_sync()
            if pre_check['status'] != 'success':
                result['error'] = '無法獲取同步前的偏移量'
                return result
            
            result['offset_before'] = pre_check['offset']
            
            # 2. 執行時間同步
            start_time = time.time()
            
            if method == 'ntpdate':
                # 使用 ntpdate 命令
                cmd = ['ntpdate', '-u', self.ntp_server]
                logger.info(f"執行命令: {' '.join(cmd)}")
                
                process = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                
                result['output'] = process.stdout
                
                if process.returncode != 0:
                    result['error'] = process.stderr
                    logger.error(f"ntpdate 執行失敗: {process.stderr}")
                    return result
            
            elif method == 'chrony':
                # 使用 chronyc 命令
                cmd = ['chronyc', 'makestep']
                logger.info(f"執行命令: {' '.join(cmd)}")
                
                process = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                
                result['output'] = process.stdout
                
                if process.returncode != 0:
                    result['error'] = process.stderr
                    logger.error(f"chronyc 執行失敗: {process.stderr}")
                    return result
            
            else:
                result['error'] = f"不支援的同步方法: {method}"
                return result
            
            result['duration'] = time.time() - start_time
            
            # 3. 等待 2 秒讓系統時間穩定
            time.sleep(2)
            
            # 4. 記錄同步後的偏移量
            post_check = self.check_sync()
            if post_check['status'] == 'success':
                result['offset_after'] = post_check['offset']
            
            result['success'] = True
            logger.info(
                f"時間同步成功 - "
                f"Before: {result['offset_before']:.2f}ms, "
                f"After: {result['offset_after']:.2f}ms, "
                f"Duration: {result['duration']:.2f}s"
            )
            
        except subprocess.TimeoutExpired:
            result['error'] = "命令執行超時"
            logger.error(f"時間同步超時: {method}")
        
        except Exception as e:
            result['error'] = str(e)
            logger.error(f"時間同步異常: {e}", exc_info=True)
        
        return result
```

---

### Phase 3: Celery 自動同步任務（1 天）

**3.1 創建自動同步任務**

```python
# backend/api/tasks.py

@shared_task(
    bind=True,
    name='api.tasks.auto_sync_ntp_time_task',
    max_retries=2,
    time_limit=120,  # 2 分鐘超時
    soft_time_limit=90
)
def auto_sync_ntp_time_task(self, force: bool = False, threshold_ms: float = 200.0):
    """
    NTP 自動時間校正任務（每 15 分鐘檢查一次）
    
    Args:
        force: 強制同步（忽略間隔限制）
        threshold_ms: 同步閾值（毫秒）
    
    Returns:
        dict: {
            'checked': bool,
            'synced': bool,
            'offset_before': float,
            'offset_after': float,
            'reason': str
        }
    """
    try:
        logger.info('[Celery] 開始執行 NTP 自動時間校正檢查')
        
        from .ntp_service import NTPSyncService
        from .models import NTPSyncOperation
        
        service = NTPSyncService()
        
        # 1. 判斷是否需要同步
        should_sync, reason, current_offset = service.should_sync(threshold_ms)
        
        result = {
            'checked': True,
            'synced': False,
            'offset_before': current_offset,
            'offset_after': None,
            'reason': reason,
            'decision': 'skip'
        }
        
        if not should_sync and not force:
            logger.info(f'[Celery] 不需要同步 - {reason}')
            return result
        
        # 2. 檢查是否可以同步（防止頻繁同步）
        if not force:
            can_sync, sync_reason = service.can_sync_now()
            if not can_sync:
                logger.warning(f'[Celery] 無法同步 - {sync_reason}')
                result['reason'] = sync_reason
                result['decision'] = 'blocked'
                return result
        
        # 3. 創建同步操作記錄
        sync_op = NTPSyncOperation.objects.create(
            ntp_server=service.ntp_server,
            sync_method='ntpdate',
            offset_before=current_offset,
            status='pending',
            triggered_by='auto' if not force else 'manual',
            sync_decision_reason=reason
        )
        
        logger.info(f'[Celery] 開始執行時間同步 - Offset: {current_offset:.2f}ms')
        
        # 4. 執行時間同步
        sync_result = service.sync_system_time(method='ntpdate')
        
        # 5. 更新同步操作記錄
        sync_op.status = 'success' if sync_result['success'] else 'failed'
        sync_op.offset_after = sync_result.get('offset_after')
        sync_op.duration = sync_result.get('duration', 0)
        sync_op.command_output = sync_result.get('output', '')
        sync_op.error_message = sync_result.get('error', '')
        sync_op.save()
        
        # 6. 返回結果
        result.update({
            'synced': sync_result['success'],
            'offset_after': sync_result.get('offset_after'),
            'decision': 'synced' if sync_result['success'] else 'failed'
        })
        
        if sync_result['success']:
            improvement = abs(current_offset) - abs(sync_result.get('offset_after', 0))
            logger.info(
                f'[Celery] 時間同步完成 - '
                f'Before: {current_offset:.2f}ms, '
                f'After: {sync_result.get("offset_after"):.2f}ms, '
                f'改善: {improvement:.2f}ms'
            )
        else:
            logger.error(f'[Celery] 時間同步失敗 - {sync_result.get("error")}')
        
        return result
        
    except Exception as exc:
        logger.error('[Celery] NTP 自動同步異常', exc_info=True)
        
        # 自動重試
        try:
            raise self.retry(exc=exc, countdown=300)  # 5 分鐘後重試
        except self.MaxRetriesExceededError:
            logger.error('[Celery] NTP 自動同步重試次數已達上限')
            return {
                'checked': True,
                'synced': False,
                'reason': str(exc),
                'decision': 'error'
            }
```

**3.2 註冊到 Celery Beat**

```python
# backend/network_toolbox/celery.py

# 在資料庫中註冊（使用 DatabaseScheduler）
from django_celery_beat.models import PeriodicTask, IntervalSchedule

# 創建 15 分鐘間隔
interval, _ = IntervalSchedule.objects.get_or_create(
    every=15,
    period='minutes'
)

# 創建定時任務
PeriodicTask.objects.update_or_create(
    name='auto-sync-ntp-time-every-15-minutes',
    defaults={
        'task': 'api.tasks.auto_sync_ntp_time_task',
        'interval': interval,
        'enabled': True,
        'description': 'NTP 自動時間校正（每 15 分鐘檢查，偏移 >200ms 時同步）',
    }
)
```

---

### Phase 4: 手動同步 API（1 天）

**4.1 創建 ViewSet**

```python
# backend/api/views.py

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import NTPSyncOperation
from .serializers import NTPSyncOperationSerializer

class NTPSyncViewSet(viewsets.ReadOnlyModelViewSet):
    """NTP 同步操作 ViewSet"""
    
    queryset = NTPSyncOperation.objects.all()
    serializer_class = NTPSyncOperationSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    @action(detail=False, methods=['post'])
    def sync_now(self, request):
        """
        手動觸發 NTP 時間同步
        
        POST /api/ntp-sync/sync_now/
        Body: {
            "force": true,  // 可選，強制同步
            "threshold_ms": 100  // 可選，自訂閾值
        }
        """
        from .tasks import auto_sync_ntp_time_task
        
        force = request.data.get('force', False)
        threshold_ms = request.data.get('threshold_ms', 200.0)
        
        # 異步執行同步任務
        task = auto_sync_ntp_time_task.delay(force=force, threshold_ms=threshold_ms)
        
        return Response({
            'message': '時間同步任務已提交',
            'task_id': task.id,
            'force': force,
            'threshold_ms': threshold_ms
        }, status=status.HTTP_202_ACCEPTED)
    
    @action(detail=False, methods=['get'])
    def status(self, request):
        """
        獲取 NTP 同步狀態
        
        GET /api/ntp-sync/status/
        """
        from .models import NTPSyncLog
        from django.utils import timezone
        from datetime import timedelta
        
        # 最新檢測記錄
        latest_log = NTPSyncLog.objects.order_by('-timestamp').first()
        
        # 最後一次成功同步
        latest_sync = NTPSyncOperation.objects.filter(
            status='success'
        ).order_by('-timestamp').first()
        
        # 最近 1 小時的漂移率
        one_hour_ago = timezone.now() - timedelta(hours=1)
        recent_logs = NTPSyncLog.objects.filter(
            timestamp__gte=one_hour_ago,
            status='success'
        ).order_by('timestamp')
        
        drift_rate = None
        if recent_logs.count() >= 2:
            first = recent_logs.first()
            last = recent_logs.last()
            time_diff = (last.timestamp - first.timestamp).total_seconds() / 3600
            offset_diff = last.offset - first.offset
            drift_rate = offset_diff / time_diff if time_diff > 0 else None
        
        return Response({
            'current_offset': latest_log.offset if latest_log else None,
            'current_status': 'healthy' if (latest_log and abs(latest_log.offset) < 100) else 'warning',
            'last_check': latest_log.timestamp if latest_log else None,
            'last_sync': latest_sync.timestamp if latest_sync else None,
            'drift_rate': drift_rate,
            'needs_sync': latest_log and abs(latest_log.offset) > 200,
        })
```

---

### Phase 5: 前端 UI（1-2 天）

**5.1 NTP 狀態卡片組件**

```javascript
// frontend/src/components/NTPStatusCard.js

import React, { useState, useEffect } from 'react';
import { Card, Statistic, Button, Badge, Space, message } from 'antd';
import { ClockCircleOutlined, SyncOutlined } from '@ant-design/icons';
import axios from 'axios';

const NTPStatusCard = () => {
    const [status, setStatus] = useState(null);
    const [loading, setLoading] = useState(false);
    const [syncing, setSyncing] = useState(false);

    const fetchStatus = async () => {
        setLoading(true);
        try {
            const response = await axios.get('/api/ntp-sync/status/');
            setStatus(response.data);
        } catch (error) {
            message.error('獲取 NTP 狀態失敗');
        } finally {
            setLoading(false);
        }
    };

    const handleSyncNow = async () => {
        setSyncing(true);
        try {
            await axios.post('/api/ntp-sync/sync_now/', { force: true });
            message.success('時間同步任務已提交，請稍候...');
            
            // 5 秒後刷新狀態
            setTimeout(fetchStatus, 5000);
        } catch (error) {
            message.error('提交同步任務失敗');
        } finally {
            setSyncing(false);
        }
    };

    useEffect(() => {
        fetchStatus();
        const interval = setInterval(fetchStatus, 30000); // 每 30 秒刷新
        return () => clearInterval(interval);
    }, []);

    const getStatusBadge = () => {
        if (!status) return <Badge status="default" text="未知" />;
        
        const absOffset = Math.abs(status.current_offset);
        if (absOffset < 50) return <Badge status="success" text="正常" />;
        if (absOffset < 100) return <Badge status="processing" text="良好" />;
        if (absOffset < 200) return <Badge status="warning" text="警告" />;
        return <Badge status="error" text="需同步" />;
    };

    return (
        <Card
            title={
                <Space>
                    <ClockCircleOutlined />
                    <span>NTP 時間同步狀態</span>
                </Space>
            }
            loading={loading}
            extra={
                <Button
                    type="primary"
                    icon={<SyncOutlined spin={syncing} />}
                    onClick={handleSyncNow}
                    loading={syncing}
                    disabled={!status || !status.needs_sync}
                >
                    立即同步
                </Button>
            }
        >
            <Space direction="vertical" style={{ width: '100%' }}>
                <Statistic
                    title="當前時間偏移"
                    value={status?.current_offset?.toFixed(2) || 0}
                    suffix="ms"
                    prefix={getStatusBadge()}
                />
                
                {status?.drift_rate && (
                    <Statistic
                        title="漂移速率"
                        value={status.drift_rate.toFixed(2)}
                        suffix="ms/hour"
                    />
                )}
                
                <div>
                    <small>最後檢查：{status?.last_check ? new Date(status.last_check).toLocaleString() : '-'}</small>
                    <br />
                    <small>最後同步：{status?.last_sync ? new Date(status.last_sync).toLocaleString() : '從未同步'}</small>
                </div>
            </Space>
        </Card>
    );
};

export default NTPStatusCard;
```

---

## ⚙️ 配置參數

### 建議配置

```python
# backend/network_toolbox/settings.py

# NTP 自動同步配置
NTP_AUTO_SYNC_CONFIG = {
    # 同步閾值（毫秒）
    'sync_threshold_ms': 200,      # 超過此值觸發同步
    'warning_threshold_ms': 100,   # 超過此值發出警告
    'critical_threshold_ms': 1000, # 超過此值立即同步
    
    # 同步間隔限制
    'min_sync_interval_minutes': 30,  # 最短同步間隔（防止頻繁）
    
    # 檢查頻率
    'check_interval_minutes': 15,  # 每 15 分鐘檢查一次
    
    # NTP 服務器
    'ntp_server': '10.10.10.51',
    
    # 同步方法
    'sync_method': 'ntpdate',  # 'ntpdate' 或 'chrony'
    
    # 決策參數
    'avg_sample_count': 3,  # 計算平均偏移的樣本數
    'avg_sample_window_minutes': 15,  # 樣本時間窗口
}
```

---

## 🔒 安全考量

### 權限要求

**系統權限**：
- `ntpdate` 命令需要 **root 權限**
- Docker 容器需要 `--privileged` 或 `CAP_SYS_TIME` 能力

**解決方案選項**：

**選項 A：使用 sudo（推薦）**
```bash
# 在 Django 容器中配置 sudo 無密碼執行 ntpdate
# /etc/sudoers.d/ntpdate
django ALL=(ALL) NOPASSWD: /usr/sbin/ntpdate

# 修改代碼使用 sudo
cmd = ['sudo', 'ntpdate', '-u', self.ntp_server]
```

**選項 B：Docker Privileged 模式**
```yaml
# docker-compose.yml
services:
  django:
    privileged: true
```

**選項 C：添加 CAP_SYS_TIME 能力（最安全）**
```yaml
# docker-compose.yml
services:
  django:
    cap_add:
      - SYS_TIME
```

### 風險評估

| 風險 | 影響 | 緩解措施 |
|------|------|---------|
| **時間突變** | 數據庫事務錯誤 | 限制單次調整量（<1秒） |
| **頻繁同步** | 系統不穩定 | 最短間隔 30 分鐘 |
| **同步失敗** | 時間持續漂移 | 自動重試 + 告警 |
| **權限不足** | 同步無法執行 | sudo 配置 + 測試 |

---

## 📈 監控與告警

### Dashboard 指標

1. **當前時間偏移**（實時）
2. **漂移速率**（ms/hour）
3. **最後同步時間**
4. **同步成功率**（最近 7 天）
5. **偏移趨勢圖**（24 小時/7 天/30 天）

### 告警規則

| 級別 | 條件 | 動作 |
|------|------|------|
| **Info** | 偏移 > 100ms | 記錄日誌 |
| **Warning** | 偏移 > 200ms | 發送通知 + 自動同步 |
| **Critical** | 偏移 > 1000ms | 立即同步 + 郵件告警 |
| **Error** | 同步失敗 3 次 | 郵件告警 + 人工介入 |

---

## ✅ 測試計劃

### 單元測試

```python
# tests/unit/backend/test_ntp_service.py

def test_ntp_sync_service_should_sync():
    """測試同步決策邏輯"""
    service = NTPSyncService()
    
    # 模擬偏移量 250ms
    should_sync, reason, offset = service.should_sync(threshold_ms=200)
    assert should_sync == True
    assert "超過閾值" in reason

def test_ntp_sync_service_can_sync_now():
    """測試同步間隔限制"""
    service = NTPSyncService()
    
    # 創建最近的同步記錄（5 分鐘前）
    NTPSyncOperation.objects.create(
        timestamp=timezone.now() - timedelta(minutes=5),
        status='success'
    )
    
    can_sync, reason = service.can_sync_now()
    assert can_sync == False
    assert "未滿 30 分鐘" in reason
```

### 整合測試

```python
# tests/integration/test_ntp_auto_sync.py

def test_auto_sync_workflow():
    """測試完整自動同步流程"""
    
    # 1. 創建模擬的高偏移量記錄
    for i in range(3):
        NTPSyncLog.objects.create(
            offset=-250.0,  # 超過閾值
            status='success'
        )
    
    # 2. 執行自動同步任務
    result = auto_sync_ntp_time_task(force=True)
    
    # 3. 驗證結果
    assert result['checked'] == True
    assert result['synced'] == True
    
    # 4. 驗證數據庫記錄
    sync_op = NTPSyncOperation.objects.latest('timestamp')
    assert sync_op.status == 'success'
    assert abs(sync_op.offset_after) < abs(sync_op.offset_before)
```

---

## 📝 實施檢查清單

### 準備階段
- [ ] 確認 NTP 服務器可訪問（10.10.10.51）
- [ ] 檢查 Docker 容器權限配置
- [ ] 安裝 ntpdate 工具（或 chrony）
- [ ] 配置 sudo 權限（如需要）

### 開發階段
- [ ] 創建 NTPSyncOperation 模型
- [ ] 執行資料庫遷移
- [ ] 擴展 NTPSyncService 類
- [ ] 創建 auto_sync_ntp_time_task 任務
- [ ] 註冊 Celery Beat 排程
- [ ] 創建 API ViewSet
- [ ] 開發前端 UI 組件

### 測試階段
- [ ] 單元測試（同步決策邏輯）
- [ ] 整合測試（完整同步流程）
- [ ] 手動測試（強制同步）
- [ ] 壓力測試（頻繁同步）
- [ ] 權限測試（sudo 執行）

### 部署階段
- [ ] 更新配置文件
- [ ] 重啟 Django 容器
- [ ] 驗證 Celery 任務註冊
- [ ] 監控首次自動同步
- [ ] 建立 Dashboard 監控

### 驗收標準
- [ ] 時間偏移 < 50ms（正常運行）
- [ ] 自動同步正常觸發（偏移 > 200ms）
- [ ] 同步成功率 > 95%
- [ ] 同步間隔限制有效（≥30 分鐘）
- [ ] 日誌記錄完整
- [ ] Dashboard 顯示正確

---

## 🚀 部署時間表

| 階段 | 預估時間 | 關鍵里程碑 |
|------|---------|----------|
| **Phase 1** | 1 天 | 資料模型完成 |
| **Phase 2** | 1-2 天 | NTP 同步服務完成 |
| **Phase 3** | 1 天 | Celery 任務完成 |
| **Phase 4** | 1 天 | API 完成 |
| **Phase 5** | 1-2 天 | 前端 UI 完成 |
| **測試** | 1 天 | 全面測試完成 |
| **部署** | 0.5 天 | 生產環境部署 |
| **總計** | **6-8 天** | 完整系統上線 |

---

## 📞 後續行動

### 立即行動（緊急）
1. **確認是否批准此方案**
2. **選擇權限解決方案**（sudo / privileged / cap_add）
3. **確認實施時間表**

### 短期行動（1 週內）
1. **Phase 1-3 開發**（核心功能）
2. **基本測試**
3. **試運行部署**

### 中期行動（2-4 週）
1. **Phase 4-5 開發**（UI + 完善）
2. **全面測試**
3. **正式部署**
4. **監控優化**

---

## 📚 參考資料

- **ntpdate 文檔**：https://linux.die.net/man/8/ntpdate
- **chrony 文檔**：https://chrony.tuxfamily.org/
- **NTP 協議**：RFC 5905
- **Docker CAP_SYS_TIME**：https://docs.docker.com/engine/reference/run/#runtime-privilege-and-linux-capabilities

---

**最後更新**：2025-11-23 13:45  
**狀態**：📋 設計完成，待審核批准  
**下一步**：等待用戶確認後開始實施
