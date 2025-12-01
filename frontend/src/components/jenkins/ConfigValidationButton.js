import React, { useState, useEffect } from 'react';
import { Button, Spin, Tooltip } from 'antd';
import { 
    CheckCircleOutlined, 
    CloseCircleOutlined, 
    ExclamationCircleOutlined 
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';

/**
 * Config Validation 按鈕組件
 * 
 * 根據配置檢查結果顯示不同狀態顏色：
 * - 綠色：檢查通過 (success)
 * - 橘色：有警告 (warning)
 * - 紅色：有錯誤 (error)
 * - 灰色：尚未檢查
 */
const ConfigValidationButton = ({ buildId }) => {
    const navigate = useNavigate();
    const [loading, setLoading] = useState(true);
    const [hasValidation, setHasValidation] = useState(false);
    const [overallStatus, setOverallStatus] = useState(null);
    
    useEffect(() => {
        const checkValidation = async () => {
            if (!buildId) {
                setLoading(false);
                return;
            }
            
            try {
                const response = await axios.get(
                    `/api/jenkins-builds/${buildId}/has_config_validation/`
                );
                
                setHasValidation(response.data.has_validation);
                setOverallStatus(response.data.overall_status);
            } catch (err) {
                console.error('檢查 Config Validation 失敗:', err);
            } finally {
                setLoading(false);
            }
        };
        
        checkValidation();
    }, [buildId]);
    
    // 點擊跳轉到配置檢查頁面
    const handleClick = () => {
        navigate(`/rvt-analytics/build-config-validator/${buildId}`);
    };
    
    // 載入中
    if (loading) {
        return (
            <Button size="small" disabled style={{ minWidth: '85px' }}>
                <Spin size="small" />
            </Button>
        );
    }
    
    // 根據狀態渲染不同樣式的按鈕
    if (hasValidation) {
        switch (overallStatus) {
            case 'success':
                return (
                    <Tooltip title="配置檢查通過">
                        <Button
                            size="small"
                            icon={<CheckCircleOutlined />}
                            onClick={handleClick}
                            style={{ 
                                backgroundColor: '#52c41a', 
                                borderColor: '#52c41a',
                                color: '#fff'
                            }}
                        >
                            檢查配置
                        </Button>
                    </Tooltip>
                );
            
            case 'warning':
                return (
                    <Tooltip title="配置檢查有警告">
                        <Button
                            size="small"
                            icon={<ExclamationCircleOutlined />}
                            onClick={handleClick}
                            style={{ 
                                backgroundColor: '#faad14', 
                                borderColor: '#faad14',
                                color: '#fff'
                            }}
                        >
                            檢查配置
                        </Button>
                    </Tooltip>
                );
            
            case 'error':
                return (
                    <Tooltip title="配置檢查有錯誤">
                        <Button
                            size="small"
                            type="primary"
                            danger
                            icon={<CloseCircleOutlined />}
                            onClick={handleClick}
                        >
                            檢查配置
                        </Button>
                    </Tooltip>
                );
            
            default:
                // 未知狀態，使用預設樣式（有結果但狀態未知）
                return (
                    <Tooltip title="查看配置檢查結果">
                        <Button
                            size="small"
                            icon={<CheckCircleOutlined />}
                            onClick={handleClick}
                        >
                            檢查配置
                        </Button>
                    </Tooltip>
                );
        }
    }
    
    // 尚未檢查 - 灰色按鈕
    return (
        <Tooltip title="尚未檢查配置（點擊手動檢查）">
            <Button
                size="small"
                icon={<CheckCircleOutlined style={{ color: '#999' }} />}
                onClick={handleClick}
                style={{ color: '#999', borderColor: '#d9d9d9' }}
            >
                檢查配置
            </Button>
        </Tooltip>
    );
};

export default ConfigValidationButton;
