import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { 
    Card, 
    Spin, 
    Alert, 
    Button, 
    Descriptions, 
    Statistic, 
    Row, 
    Col,
    Space,
    Tag
} from 'antd';
import { 
    ArrowLeftOutlined, 
    WarningOutlined,
    FileTextOutlined,
    ClockCircleOutlined
} from '@ant-design/icons';
import axios from 'axios';
import FatalTaskTable from '../components/jenkins/FatalTaskTable';

/**
 * Fatal Errors 詳情頁面
 * 
 * 顯示 Jenkins Build 的 Fatal Error 分析結果：
 * - Build 基本資訊
 * - Fatal 統計資料
 * - 所有 Fatal Tasks 列表
 */
const FatalErrorsDetail = () => {
    const { buildId } = useParams();
    const navigate = useNavigate();
    
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [buildInfo, setBuildInfo] = useState(null);
    const [analysisData, setAnalysisData] = useState(null);
    
    // 載入數據
    useEffect(() => {
        const fetchData = async () => {
            setLoading(true);
            setError(null);
            
            try {
                // 1. 獲取 Build 基本資訊
                const buildResponse = await axios.get(`/api/jenkins-builds/${buildId}/`);
                setBuildInfo(buildResponse.data);
                
                // 2. 獲取 Fatal Analysis 資料
                const analysisResponse = await axios.get(
                    `/api/jenkins-builds/${buildId}/fatal_analysis/`
                );
                setAnalysisData(analysisResponse.data);
                
            } catch (err) {
                console.error('Error fetching fatal errors:', err);
                
                if (err.response?.status === 404) {
                    setError('找不到 Fatal Error 分析結果，可能此 Build 尚未分析。');
                } else if (err.response?.status === 400) {
                    setError('此 Build 不是 FAILURE 狀態，無法查看 Fatal Errors。');
                } else {
                    setError('載入失敗：' + (err.response?.data?.error || err.message));
                }
            } finally {
                setLoading(false);
            }
        };
        
        fetchData();
    }, [buildId]);
    
    // 返回按鈕
    const handleGoBack = () => {
        navigate(-1);
    };
    
    if (loading) {
        return (
            <div style={{ 
                textAlign: 'center', 
                padding: '100px 0',
                backgroundColor: '#ffffff'
            }}>
                <Spin size="large" />
                <div style={{ marginTop: '16px' }}>載入 Fatal Errors 分析中...</div>
            </div>
        );
    }
    
    if (error) {
        return (
            <div style={{ padding: '24px' }}>
                <Button 
                    icon={<ArrowLeftOutlined />} 
                    onClick={handleGoBack}
                    style={{ marginBottom: '16px' }}
                >
                    返回
                </Button>
                <Alert
                    message="載入失敗"
                    description={error}
                    type="error"
                    showIcon
                />
            </div>
        );
    }
    
    return (
        <div style={{ padding: '24px', backgroundColor: '#f0f2f5', minHeight: '100vh' }}>
            {/* 返回按鈕 */}
            <Button 
                icon={<ArrowLeftOutlined />} 
                onClick={handleGoBack}
                style={{ marginBottom: '16px' }}
            >
                返回
            </Button>
            
            {/* Build 基本資訊 */}
            <Card 
                title={
                    <Space>
                        <FileTextOutlined />
                        Build 資訊
                    </Space>
                }
                style={{ marginBottom: '16px' }}
            >
                <Descriptions column={{ xs: 1, sm: 2, md: 3 }}>
                    <Descriptions.Item label="Job 名稱">
                        <strong>{buildInfo?.job_name || 'N/A'}</strong>
                    </Descriptions.Item>
                    <Descriptions.Item label="Build #">
                        <Tag color="blue">#{buildInfo?.build_number || 'N/A'}</Tag>
                    </Descriptions.Item>
                    <Descriptions.Item label="狀態">
                        <Tag color="red">{buildInfo?.result || 'N/A'}</Tag>
                    </Descriptions.Item>
                    <Descriptions.Item label="Jenkins Server">
                        {buildInfo?.job?.server?.name || 'N/A'}
                    </Descriptions.Item>
                    <Descriptions.Item label="Server IP">
                        {buildInfo?.job?.server?.ip_address || 'N/A'}
                    </Descriptions.Item>
                    <Descriptions.Item label="Build 時間">
                        <Space>
                            <ClockCircleOutlined />
                            {buildInfo?.timestamp ? new Date(buildInfo.timestamp).toLocaleString('zh-TW') : 'N/A'}
                        </Space>
                    </Descriptions.Item>
                </Descriptions>
            </Card>
            
            {/* Fatal 統計資料 */}
            <Card 
                title={
                    <Space>
                        <WarningOutlined style={{ color: '#ff4d4f' }} />
                        Fatal Error 統計
                    </Space>
                }
                style={{ marginBottom: '16px' }}
            >
                <Row gutter={16}>
                    <Col xs={24} sm={12} md={6}>
                        <Statistic
                            title="分析時間"
                            value={analysisData?.analyzed_at ? new Date(analysisData.analyzed_at).toLocaleString('zh-TW') : 'N/A'}
                            valueStyle={{ fontSize: '14px' }}
                        />
                    </Col>
                    <Col xs={24} sm={12} md={6}>
                        <Statistic
                            title="總行數"
                            value={analysisData?.total_lines || 0}
                            suffix="行"
                        />
                    </Col>
                    <Col xs={24} sm={12} md={6}>
                        <Statistic
                            title="Fatal Tasks"
                            value={analysisData?.fatal_count || 0}
                            valueStyle={{ color: '#cf1322' }}
                            prefix={<WarningOutlined />}
                            suffix="個"
                        />
                    </Col>
                    <Col xs={24} sm={12} md={6}>
                        <Statistic
                            title="總 Fatal 行數"
                            value={analysisData?.fatal_tasks?.reduce((sum, task) => sum + task.fatal_count, 0) || 0}
                            valueStyle={{ color: '#cf1322' }}
                            suffix="行"
                        />
                    </Col>
                </Row>
            </Card>
            
            {/* Fatal Tasks 列表 */}
            {analysisData?.fatal_tasks && analysisData.fatal_tasks.length > 0 ? (
                <FatalTaskTable fatalTasks={analysisData.fatal_tasks} />
            ) : (
                <Alert
                    message="無 Fatal Errors"
                    description="此 Build 未檢測到 Fatal Errors。"
                    type="info"
                    showIcon
                />
            )}
        </div>
    );
};

export default FatalErrorsDetail;
