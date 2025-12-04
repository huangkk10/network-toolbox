/**
 * Ansible 配置查看器 Drawer
 * 
 * 整合所有標籤頁，提供完整的 Ansible Inventory 查看功能
 */

import React, { useState, useEffect } from 'react';
import { 
    Drawer, 
    Space, 
    Tag, 
    Button, 
    Alert,
    Spin,
    message,
} from 'antd';
import { 
    CheckCircleOutlined, 
    SyncOutlined,
    ReloadOutlined,
} from '@ant-design/icons';
import { 
    getAnsibleInventory,
    parseInventoryToHostList,
} from '../../services/ansibleService';
import HostConfigTab from './HostConfigTab';

const AnsibleConfigDrawer = ({ 
    visible, 
    onClose, 
    jobId, 
    jobName, 
    buildNumber,
    hostname  // 新增：用於過濾顯示的主機名稱
}) => {
    const [loading, setLoading] = useState(false);
    const [inventoryData, setInventoryData] = useState(null);
    const [hosts, setHosts] = useState([]);
    const [cached, setCached] = useState(false);
    const [error, setError] = useState(null);
    const [inventoryPath, setInventoryPath] = useState(null);  // Inventory 路徑
    const [selectedHostForConfig, setSelectedHostForConfig] = useState(null);

    // 當 Drawer 打開時載入資料
    useEffect(() => {
        if (visible && jobId) {
            fetchInventoryData();
        }
    }, [visible, jobId, buildNumber]);  // 新增 buildNumber 依賴

    // 獲取 Inventory 資料
    const fetchInventoryData = async (useCache = true) => {
        setLoading(true);
        setError(null);

        try {
            // 傳入 buildNumber 以獲取指定 Build 的 inventory
            const response = await getAnsibleInventory(jobId, useCache, buildNumber);
            
            if (response.success) {
                setInventoryData(response);
                setCached(response.cached);
                setInventoryPath(response.inventory_path || null);
                
                // 解析資料
                let hostList = parseInventoryToHostList(response);
                
                // 如果提供了 hostname，則過濾只顯示匹配的主機
                if (hostname) {
                    hostList = hostList.filter(h => h.hostname === hostname);
                }
                
                setHosts(hostList);
                
                message.success(
                    useCache && response.cached 
                        ? '已載入快取資料' 
                        : '已載入最新資料'
                );
            } else {
                throw new Error(response.message || '獲取 Inventory 失敗');
            }
        } catch (err) {
            console.error('Failed to fetch inventory:', err);
            
            if (err.response?.status === 404) {
                setError('此 Build 沒有 Ansible Inventory 資料');
            } else if (err.response?.status === 500) {
                setError('伺服器錯誤：' + (err.response?.data?.message || err.message));
            } else {
                setError('載入失敗：' + err.message);
            }
            
            message.error('載入失敗：' + err.message);
        } finally {
            setLoading(false);
        }
    };

    // 強制重新載入（不使用快取）
    const handleReload = () => {
        fetchInventoryData(false);
    };

    // Drawer 標題
    const drawerTitle = (
        <Space>
            <span>Ansible Inventory</span>
            <span style={{ color: '#666', fontWeight: 'normal' }}>
                - {jobName} #{buildNumber}
            </span>
            {cached && (
                <Tag icon={<CheckCircleOutlined />} color="success">
                    已快取
                </Tag>
            )}
            {!cached && inventoryData && (
                <Tag icon={<SyncOutlined />} color="orange">
                    即時獲取
                </Tag>
            )}
        </Space>
    );

    // Drawer 額外操作按鈕
    const drawerExtra = (
        <Space>
            <Button 
                icon={<ReloadOutlined />}
                onClick={handleReload}
                loading={loading}
            >
                重新載入
            </Button>
        </Space>
    );

    return (
        <Drawer
            title={drawerTitle}
            width={900}
            open={visible}
            onClose={onClose}
            extra={drawerExtra}
            destroyOnClose={false}
            styles={{
                body: { paddingBottom: 80 }
            }}
        >
            {/* Inventory 路徑顯示 */}
            {inventoryPath && (
                <Alert
                    message="Inventory 路徑"
                    description={inventoryPath}
                    type="info"
                    showIcon
                    style={{ marginBottom: 16 }}
                    closable={false}
                />
            )}

            {/* 載入中 */}
            {loading && !inventoryData && (
                <div style={{ 
                    textAlign: 'center', 
                    padding: '100px 0',
                }}>
                    <Spin size="large" tip="正在載入 Ansible Inventory..." />
                </div>
            )}

            {/* 錯誤訊息 */}
            {error && !loading && (
                <Alert
                    message="載入失敗"
                    description={error}
                    type="error"
                    showIcon
                    closable
                    onClose={() => setError(null)}
                    action={
                        <Button 
                            size="small" 
                            type="primary"
                            onClick={() => fetchInventoryData()}
                        >
                            重試
                        </Button>
                    }
                    style={{ marginBottom: 16 }}
                />
            )}

            {/* 主要內容 - 直接顯示配置詳情 */}
            {!error && inventoryData && (
                <HostConfigTab 
                    jobId={jobId}
                    hosts={hosts}
                    initialHostname={hostname || selectedHostForConfig}
                />
            )}

            {/* 底部提示 */}
            {inventoryData && (
                <div style={{ 
                    position: 'absolute',
                    bottom: 0,
                    left: 0,
                    right: 0,
                    padding: '12px 24px',
                    background: '#fafafa',
                    borderTop: '1px solid #f0f0f0',
                }}>
                    <Space split="|">
                        <span style={{ fontSize: '13px', color: '#666' }}>
                            📊 共 {hosts.length} 個主機
                        </span>
                        <span style={{ fontSize: '13px', color: '#666' }}>
                            {cached ? '⚡ 使用快取資料' : '🔄 即時獲取資料'}
                        </span>
                    </Space>
                </div>
            )}
        </Drawer>
    );
};

export default AnsibleConfigDrawer;
