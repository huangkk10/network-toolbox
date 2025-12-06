/**
 * 時間範圍選擇器組件
 */

import React from 'react';
import { Radio, Space } from 'antd';

const TIME_RANGES = [
    { label: '1 小時', value: '1h' },
    { label: '6 小時', value: '6h' },
    { label: '24 小時', value: '24h' },
    { label: '7 天', value: '7d' },
    { label: '30 天', value: '30d' },
];

const TimeRangeSelector = ({ value, onChange, disabled = false }) => {
    return (
        <Space>
            <span>時間範圍：</span>
            <Radio.Group 
                value={value} 
                onChange={(e) => onChange(e.target.value)}
                optionType="button"
                buttonStyle="solid"
                disabled={disabled}
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
