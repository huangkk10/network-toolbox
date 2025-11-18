import React, { useState, useEffect, useRef } from 'react';
import { Card, Button, Space, Tag, Alert, Modal, message, Spin } from 'antd';
import { SaveOutlined, CheckCircleOutlined, CloseCircleOutlined } from '@ant-design/icons';
import Editor from '@monaco-editor/react';
import axios from 'axios';

const InventoryFileEditor = ({ inventoryId, onSaved }) => {
    const [content, setContent] = useState('');
    const [originalContent, setOriginalContent] = useState('');
    const [loading, setLoading] = useState(false);
    const [saving, setSaving] = useState(false);
    const [syntaxValid, setSyntaxValid] = useState(true);
    const [syntaxError, setSyntaxError] = useState(null);
    const [hasChanges, setHasChanges] = useState(false);
    const [parsedStats, setParsedStats] = useState(null);
    
    const validateTimeoutRef = useRef(null);
    const editorRef = useRef(null);
    
    // 草稿 Key
    const getDraftKey = () => `inventory_draft_${inventoryId}`;
    
    // 載入文件內容
    useEffect(() => {
        if (inventoryId) {
            loadContent();
            checkForDraft();
        }
    }, [inventoryId]);
    
    const loadContent = async () => {
        setLoading(true);
        try {
            const response = await axios.get(
                `/api/ansible-inventory/${inventoryId}/content/`
            );
            setContent(response.data.content);
            setOriginalContent(response.data.content);
            message.success('文件載入成功');
        } catch (error) {
            console.error('載入失敗：', error);
            message.error('載入失敗：' + (error.response?.data?.error || error.message));
        } finally {
            setLoading(false);
        }
    };
    
    // 檢查是否有草稿
    const checkForDraft = () => {
        const draft = localStorage.getItem(getDraftKey());
        if (draft && draft !== originalContent) {
            Modal.confirm({
                title: '發現未儲存的草稿',
                content: '是否要恢復之前未儲存的編輯內容？',
                okText: '恢復草稿',
                cancelText: '丟棄草稿',
                onOk: () => {
                    setContent(draft);
                    setHasChanges(true);
                    message.info('已恢復草稿');
                },
                onCancel: () => {
                    localStorage.removeItem(getDraftKey());
                    message.info('已丟棄草稿');
                }
            });
        }
    };
    
    // 內容變更處理
    const handleEditorChange = (value) => {
        setContent(value);
        setHasChanges(value !== originalContent);
        
        // 自動儲存草稿到 LocalStorage
        localStorage.setItem(getDraftKey(), value);
        
        // 防抖驗證（1 秒後自動驗證）
        if (validateTimeoutRef.current) {
            clearTimeout(validateTimeoutRef.current);
        }
        validateTimeoutRef.current = setTimeout(() => {
            validateSyntax(value);
        }, 1000);
    };
    
    // 驗證語法
    const validateSyntax = async (contentToValidate = content) => {
        try {
            const response = await axios.post(
                '/api/ansible-inventory/validate-content/',
                { content: contentToValidate }
            );
            setSyntaxValid(response.data.syntax_valid);
            setSyntaxError(response.data.error_message);
            setParsedStats(response.data.parsed_stats);
            
            if (response.data.syntax_valid) {
                message.success('語法驗證通過');
            }
        } catch (error) {
            console.error('驗證失敗：', error);
            setSyntaxValid(false);
            setSyntaxError('驗證失敗：' + (error.response?.data?.error || error.message));
        }
    };
    
    // 儲存到 NAS
    const handleSave = async () => {
        // 先驗證語法
        setLoading(true);
        try {
            const validateResponse = await axios.post(
                '/api/ansible-inventory/validate-content/',
                { content: content }
            );
            
            setSyntaxValid(validateResponse.data.syntax_valid);
            setSyntaxError(validateResponse.data.error_message);
            
            if (!validateResponse.data.syntax_valid) {
                Modal.confirm({
                    title: '語法錯誤',
                    content: (
                        <div>
                            <p>目前內容存在語法錯誤：</p>
                            <pre style={{ 
                                background: '#f5f5f5', 
                                padding: '12px', 
                                borderRadius: '4px',
                                maxHeight: '200px',
                                overflow: 'auto'
                            }}>
                                {validateResponse.data.error_message}
                            </pre>
                            <p style={{ marginTop: '12px' }}>是否仍要儲存？</p>
                        </div>
                    ),
                    okText: '強制儲存',
                    cancelText: '取消',
                    okButtonProps: { danger: true },
                    onOk: () => saveToNAS()
                });
                setLoading(false);
                return;
            }
            
            setLoading(false);
            saveToNAS();
            
        } catch (error) {
            console.error('驗證失敗：', error);
            message.error('驗證失敗：' + (error.response?.data?.error || error.message));
            setLoading(false);
        }
    };
    
    const saveToNAS = async () => {
        setSaving(true);
        try {
            const response = await axios.post(
                `/api/ansible-inventory/${inventoryId}/update-content/`,
                {
                    content: content,
                    change_summary: '更新 Inventory 配置'
                }
            );
            
            message.success(`已儲存到 NAS (版本 ${response.data.version})`);
            setOriginalContent(content);
            setHasChanges(false);
            
            // 清除草稿
            localStorage.removeItem(getDraftKey());
            
            // 通知父組件刷新
            if (onSaved) {
                onSaved();
            }
            
        } catch (error) {
            console.error('儲存失敗：', error);
            message.error('儲存失敗：' + (error.response?.data?.error || error.message));
        } finally {
            setSaving(false);
        }
    };
    
    // 手動驗證按鈕
    const handleManualValidate = () => {
        message.loading('正在驗證語法...', 0);
        validateSyntax().finally(() => {
            message.destroy();
        });
    };
    
    // 編輯器掛載
    const handleEditorDidMount = (editor, monaco) => {
        editorRef.current = editor;
        
        // 添加快捷鍵：Ctrl+S 儲存
        editor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.KeyS, () => {
            if (hasChanges) {
                handleSave();
            }
        });
    };
    
    return (
        <Card
            title="Inventory 文件編輯"
            extra={
                <Space>
                    {hasChanges && (
                        <Tag color="orange">未儲存</Tag>
                    )}
                    {syntaxValid ? (
                        <Tag color="success" icon={<CheckCircleOutlined />}>
                            語法正確
                        </Tag>
                    ) : (
                        <Tag color="error" icon={<CloseCircleOutlined />}>
                            語法錯誤
                        </Tag>
                    )}
                    {parsedStats && (
                        <Space size="small">
                            <Tag color="blue">{parsedStats.total_hosts} Hosts</Tag>
                            <Tag color="purple">{parsedStats.total_groups} Groups</Tag>
                        </Space>
                    )}
                    <Button
                        onClick={handleManualValidate}
                        icon={<CheckCircleOutlined />}
                        loading={loading && !saving}
                    >
                        驗證語法
                    </Button>
                    <Button
                        type="primary"
                        onClick={handleSave}
                        loading={saving}
                        disabled={!hasChanges}
                        icon={<SaveOutlined />}
                    >
                        儲存到 NAS
                    </Button>
                </Space>
            }
            style={{ marginTop: 16 }}
        >
            {syntaxError && (
                <Alert
                    message="語法錯誤"
                    description={
                        <pre style={{ 
                            whiteSpace: 'pre-wrap', 
                            wordBreak: 'break-word',
                            margin: 0,
                            maxHeight: '150px',
                            overflow: 'auto'
                        }}>
                            {syntaxError}
                        </pre>
                    }
                    type="error"
                    closable
                    onClose={() => setSyntaxError(null)}
                    style={{ marginBottom: 16 }}
                />
            )}
            
            <Spin spinning={loading} tip="載入中...">
                <div style={{ border: '1px solid #d9d9d9', borderRadius: '4px' }}>
                    <Editor
                        height="600px"
                        defaultLanguage="ini"
                        value={content}
                        onChange={handleEditorChange}
                        onMount={handleEditorDidMount}
                        theme="vs-light"
                        options={{
                            minimap: { enabled: true },
                            lineNumbers: 'on',
                            scrollBeyondLastLine: false,
                            fontSize: 14,
                            wordWrap: 'on',
                            automaticLayout: true,
                            tabSize: 2,
                            insertSpaces: true,
                            renderWhitespace: 'selection',
                            bracketPairColorization: { enabled: true }
                        }}
                    />
                </div>
            </Spin>
            
            <div style={{ 
                marginTop: 12, 
                color: '#8c8c8c', 
                fontSize: '12px',
                display: 'flex',
                justifyContent: 'space-between'
            }}>
                <span>
                    💡 提示：按 Ctrl+S 快速儲存，內容會自動儲存到本地草稿
                </span>
                {hasChanges && (
                    <span style={{ color: '#faad14' }}>
                        ⚠️ 有未儲存的變更
                    </span>
                )}
            </div>
        </Card>
    );
};

export default InventoryFileEditor;
