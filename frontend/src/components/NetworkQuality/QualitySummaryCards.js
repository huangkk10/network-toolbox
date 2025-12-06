/**
 * 品質統計卡片組件
 */

import React from 'react';
import { Row, Col, Card, Statistic, Tooltip } from 'antd';
import {
    WifiOutlined,
    CloseCircleOutlined,
    CheckCircleOutlined,
    FieldTimeOutlined,
} from '@ant-design/icons';

const QualitySummaryCards = ({ summary, loading }) => {
    if (!summary) {
        return null;
    }
    
    const {
        total_switches = 0,
        reachable = 0,
        unreachable = 0,
        avg_latency_ms = 0,
        avg_packet_loss = 0,
    } = summary;
    
    return (
        <Row gutter={[16, 16]} style={{ marginBottom: '24px' }}>
            <Col xs={12} sm={6}>
                <Card size="small">
                    <Statistic
                        title={
                            <Tooltip title="Ping 平均往返時間">
                                <span><WifiOutlined /> 平均延遲</span>
                            </Tooltip>
                        }
                        value={avg_latency_ms}
                        precision={2}
                        suffix="ms"
                        loading={loading}
                        valueStyle={{ 
                            color: avg_latency_ms < 5 ? '#52c41a' : 
                                   avg_latency_ms < 20 ? '#faad14' : '#ff4d4f' 
                        }}
                    />
                </Card>
            </Col>
            <Col xs={12} sm={6}>
                <Card size="small">
                    <Statistic
                        title={
                            <Tooltip title="封包遺失百分比">
                                <span><FieldTimeOutlined /> 封包遺失</span>
                            </Tooltip>
                        }
                        value={avg_packet_loss}
                        precision={1}
                        suffix="%"
                        loading={loading}
                        valueStyle={{ 
                            color: avg_packet_loss === 0 ? '#52c41a' : 
                                   avg_packet_loss < 5 ? '#faad14' : '#ff4d4f' 
                        }}
                    />
                </Card>
            </Col>
            <Col xs={12} sm={6}>
                <Card size="small">
                    <Statistic
                        title={
                            <Tooltip title="可正常連線的 Switch 數量">
                                <span><CheckCircleOutlined /> 連線正常</span>
                            </Tooltip>
                        }
                        value={reachable}
                        suffix={`/ ${total_switches}`}
                        loading={loading}
                        valueStyle={{ color: '#52c41a' }}
                    />
                </Card>
            </Col>
            <Col xs={12} sm={6}>
                <Card size="small">
                    <Statistic
                        title={
                            <Tooltip title="無法連線的 Switch 數量">
                                <span><CloseCircleOutlined /> 連線異常</span>
                            </Tooltip>
                        }
                        value={unreachable}
                        loading={loading}
                        valueStyle={{ color: unreachable > 0 ? '#ff4d4f' : '#52c41a' }}
                    />
                </Card>
            </Col>
        </Row>
    );
};

export default QualitySummaryCards;
