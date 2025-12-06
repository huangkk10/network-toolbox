/**
 * 網路品質監控主 Tab 組件
 * 
 * 整合所有網路品質相關組件
 */

import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { Card, Button, Space, message, Alert, Tooltip } from 'antd';
import { ReloadOutlined } from '@ant-design/icons';
import axios from 'axios';

import TimeRangeSelector from './TimeRangeSelector';
import QualitySummaryCards from './QualitySummaryCards';
import QualityTrendChart from './QualityTrendChart';
import QualityTable from './QualityTable';

const NetworkQualityTab = ({ serverId }) => {
    // 狀態
    const [loading, setLoading] = useState(false);
    const [refreshing, setRefreshing] = useState(false);
    const [currentQuality, setCurrentQuality] = useState(null);
    const [historyData, setHistoryData] = useState(null);
    const [historyLoading, setHistoryLoading] = useState(false);
    const [timeRange, setTimeRange] = useState('24h');
    const [selectedSwitchIds, setSelectedSwitchIds] = useState([]);
    const [error, setError] = useState(null);
    
    /**
     * 從當前品質數據計算摘要統計
     */
    const summary = useMemo(() => {
        if (!currentQuality?.switches) return null;
        
        const switches = currentQuality.switches;
        const total_switches = switches.length;
        const reachable = switches.filter(sw => sw.is_reachable === true).length;
        const unreachable = switches.filter(sw => sw.is_reachable === false).length;
        const noData = switches.filter(sw => sw.status === 'no_data').length;
        
        // 計算平均延遲（只計算有數據的）
        const withLatency = switches.filter(sw => sw.latency !== null);
        const avg_latency_ms = withLatency.length > 0
            ? withLatency.reduce((sum, sw) => sum + sw.latency, 0) / withLatency.length
            : 0;
        
        // 計算平均封包遺失
        const withPacketLoss = switches.filter(sw => sw.packet_loss !== null);
        const avg_packet_loss = withPacketLoss.length > 0
            ? withPacketLoss.reduce((sum, sw) => sum + sw.packet_loss, 0) / withPacketLoss.length
            : 0;
        
        return {
            total_switches,
            reachable,
            unreachable,
            no_data: noData,
            avg_latency_ms,
            avg_packet_loss
        };
    }, [currentQuality]);
    
    /**
     * 載入當前網路品質
     */
    const fetchCurrentQuality = useCallback(async () => {
        if (!serverId || serverId === 'all') {
            setError('請選擇特定的 DHCP Server 以查看網路品質');
            return;
        }
        
        setLoading(true);
        setError(null);
        
        try {
            const response = await axios.get(`/api/dhcp-servers/${serverId}/network-quality/`);
            
            if (response.data.success) {
                setCurrentQuality(response.data.data);
                
                // 自動選擇前 3 個有數據的 Switch 用於圖表顯示
                const switchesWithData = response.data.data.switches?.filter(
                    sw => sw.status !== 'no_data'
                ) || [];
                if (selectedSwitchIds.length === 0 && switchesWithData.length > 0) {
                    setSelectedSwitchIds(
                        switchesWithData.slice(0, 3).map(sw => sw.switch_id)
                    );
                }
            } else {
                setError(response.data.error || '載入失敗');
            }
        } catch (err) {
            console.error('Error fetching current quality:', err);
            setError(err.response?.data?.error || err.message);
        } finally {
            setLoading(false);
        }
    }, [serverId, selectedSwitchIds.length]);
    
    /**
     * 載入歷史數據
     */
    const fetchHistory = useCallback(async () => {
        if (!serverId || serverId === 'all') return;
        
        setHistoryLoading(true);
        
        try {
            const params = {
                time_range: timeRange,
            };
            
            if (selectedSwitchIds.length > 0) {
                params.switch_ids = selectedSwitchIds.join(',');
            }
            
            const response = await axios.get(
                `/api/dhcp-servers/${serverId}/network-quality/history/`,
                { params }
            );
            
            if (response.data.success) {
                setHistoryData(response.data.data);
            }
        } catch (err) {
            console.error('Error fetching history:', err);
            message.error('載入歷史數據失敗');
        } finally {
            setHistoryLoading(false);
        }
    }, [serverId, timeRange, selectedSwitchIds]);
    
    /**
     * 手動刷新品質數據
     */
    const handleRefresh = async () => {
        if (!serverId || serverId === 'all') return;
        
        setRefreshing(true);
        
        try {
            const response = await axios.post(`/api/dhcp-servers/${serverId}/network-quality/refresh/`);
            
            if (response.data.success) {
                message.success(response.data.message || '刷新成功');
                // 重新載入數據
                fetchCurrentQuality();
                fetchHistory();
            } else {
                message.error(response.data.error || '刷新失敗');
            }
        } catch (err) {
            console.error('Error refreshing quality:', err);
            message.error(err.response?.data?.error || '刷新失敗');
        } finally {
            setRefreshing(false);
        }
    };
    
    /**
     * 時間範圍變更
     */
    const handleTimeRangeChange = (newRange) => {
        setTimeRange(newRange);
    };
    
    /**
     * Switch 選擇變更
     */
    const handleSwitchChange = (newSelectedIds) => {
        setSelectedSwitchIds(newSelectedIds);
    };
    
    /**
     * 查看特定 Switch 的歷史
     */
    const handleViewHistory = (record) => {
        // 選中該 Switch 並滾動到圖表
        setSelectedSwitchIds([record.switch_id]);
    };
    
    // 初始載入
    useEffect(() => {
        console.log('[NetworkQualityTab] Initial load, serverId:', serverId);
        fetchCurrentQuality();
    }, [fetchCurrentQuality]);
    
    // 時間範圍或選中的 Switch 變更時重新載入歷史數據
    useEffect(() => {
        console.log('[NetworkQualityTab] History effect triggered');
        console.log('  - currentQuality:', !!currentQuality);
        console.log('  - selectedSwitchIds:', selectedSwitchIds);
        console.log('  - timeRange:', timeRange);
        if (currentQuality) {
            fetchHistory();
        }
    }, [timeRange, selectedSwitchIds, fetchHistory, currentQuality]);
    
    // 如果未選擇特定 Server
    if (!serverId || serverId === 'all') {
        return (
            <Alert
                type="info"
                showIcon
                message="請選擇特定的 DHCP Server"
                description="網路品質監控需要選擇特定的 DHCP Server 才能查看其到各 Switch 的連線品質。"
                style={{ marginTop: '20px' }}
            />
        );
    }
    
    // 錯誤狀態
    if (error && !currentQuality) {
        return (
            <Alert
                type="error"
                showIcon
                message="載入失敗"
                description={error}
                action={
                    <Button size="small" onClick={fetchCurrentQuality}>
                        重試
                    </Button>
                }
                style={{ marginTop: '20px' }}
            />
        );
    }
    
    return (
        <div>
            {/* 工具列 */}
            <Card size="small" style={{ marginBottom: '16px' }}>
                <Space style={{ display: 'flex', justifyContent: 'space-between', width: '100%' }}>
                    <TimeRangeSelector 
                        value={timeRange} 
                        onChange={handleTimeRangeChange}
                        disabled={loading}
                    />
                    <Space>
                        <Tooltip title="手動執行 Ping 測試並更新數據">
                            <Button
                                icon={<ReloadOutlined spin={refreshing} />}
                                onClick={handleRefresh}
                                loading={refreshing}
                            >
                                刷新
                            </Button>
                        </Tooltip>
                    </Space>
                </Space>
            </Card>
            
            {/* 統計卡片 */}
            <QualitySummaryCards 
                summary={summary} 
                loading={loading} 
            />
            
            {/* 趨勢圖表 */}
            <QualityTrendChart
                historyData={historyData}
                switches={currentQuality?.switches || []}
                selectedSwitchIds={selectedSwitchIds}
                onSwitchChange={handleSwitchChange}
                loading={historyLoading}
            />
            
            {/* 詳情表格 */}
            <QualityTable
                switches={currentQuality?.switches || []}
                loading={loading}
                onViewHistory={handleViewHistory}
            />
        </div>
    );
};

export default NetworkQualityTab;
