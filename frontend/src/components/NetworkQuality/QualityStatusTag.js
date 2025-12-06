/**
 * 品質狀態標籤組件
 * 
 * 根據延遲和丟包率顯示網路品質狀態
 */

import React from 'react';
import { Tag, Tooltip } from 'antd';

/**
 * 根據延遲和丟包率計算品質狀態
 */
const getQualityStatus = (latency, packetLoss) => {
    if (packetLoss === 100 || latency === null || latency === undefined) {
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

/**
 * 品質狀態標籤
 */
const QualityStatusTag = ({ latency, packetLoss, showTooltip = true }) => {
    const { label, color } = getQualityStatus(latency, packetLoss);
    
    const tag = <Tag color={color}>{label}</Tag>;
    
    if (!showTooltip) {
        return tag;
    }
    
    const latencyText = latency !== null && latency !== undefined ? `${latency.toFixed(2)}ms` : 'N/A';
    const packetLossText = packetLoss !== null && packetLoss !== undefined ? `${packetLoss}%` : 'N/A';
    
    return (
        <Tooltip title={`延遲: ${latencyText}, 遺失: ${packetLossText}`}>
            {tag}
        </Tooltip>
    );
};

/**
 * 獲取品質狀態顏色
 */
export const getQualityColor = (status) => {
    const colorMap = {
        'excellent': '#52c41a',
        'good': '#52c41a',
        'fair': '#faad14',
        'poor': '#fa8c16',
        'offline': '#ff4d4f',
    };
    return colorMap[status] || '#d9d9d9';
};

export { getQualityStatus };
export default QualityStatusTag;
