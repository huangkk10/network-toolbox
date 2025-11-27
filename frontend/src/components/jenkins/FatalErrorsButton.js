import React, { useState, useEffect } from 'react';
import { Button, Badge, Spin, Tooltip } from 'antd';
import { WarningOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';

/**
 * Fatal Errors 按鈕組件
 * 
 * 用於在 Build 列表中顯示 Fatal Errors 入口
 * - 僅對 FAILURE Build 顯示
 * - 異步檢查是否有分析結果
 * - 顯示 Fatal Tasks 數量徽章
 * - 點擊跳轉到詳情頁面
 */
const FatalErrorsButton = ({ buildId, buildResult }) => {
    const navigate = useNavigate();
    const [loading, setLoading] = useState(true);
    const [hasAnalysis, setHasAnalysis] = useState(false);
    const [fatalCount, setFatalCount] = useState(0);
    
    useEffect(() => {
        // 只有 FAILURE Build 才需要檢查
        if (buildResult !== 'FAILURE') {
            setLoading(false);
            return;
        }
        
        // 檢查是否有 Fatal Analysis
        const checkAnalysis = async () => {
            try {
                const response = await axios.get(
                    `/api/jenkins-builds/${buildId}/has_fatal_analysis/`
                );
                
                if (response.data.has_analysis) {
                    setHasAnalysis(true);
                    setFatalCount(response.data.fatal_count || 0);
                }
            } catch (err) {
                console.error('檢查 Fatal Analysis 失敗:', err);
            } finally {
                setLoading(false);
            }
        };
        
        checkAnalysis();
    }, [buildId, buildResult]);
    
    // 不是 FAILURE Build，不顯示按鈕
    if (buildResult !== 'FAILURE') {
        return null;
    }
    
    // 載入中顯示 Spin
    if (loading) {
        return <Spin size="small" />;
    }
    
    // 沒有分析結果，顯示灰色 disabled 按鈕
    if (!hasAnalysis) {
        return (
            <Tooltip title="尚未分析或無 Fatal Errors">
                <Button 
                    icon={<WarningOutlined />} 
                    size="small" 
                    disabled
                >
                    Fatal
                </Button>
            </Tooltip>
        );
    }
    
    // 有分析結果，顯示可點擊的紅色按鈕
    return (
        <Badge count={fatalCount} offset={[-5, 5]}>
            <Button
                type="primary"
                danger
                icon={<WarningOutlined />}
                size="small"
                onClick={() => navigate(`/jenkins/builds/${buildId}/fatal-errors`)}
            >
                Fatal Errors
            </Button>
        </Badge>
    );
};

export default FatalErrorsButton;
