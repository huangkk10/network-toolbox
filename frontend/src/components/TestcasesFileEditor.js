import React, { useState, useEffect, useRef } from 'react';
import { Card, Button, Space, Tag, Alert, Modal, message, Spin, Descriptions, Collapse, Badge } from 'antd';
import { 
    SaveOutlined, 
    CheckCircleOutlined, 
    CloseCircleOutlined, 
    ReloadOutlined,
    WarningOutlined,
    FileTextOutlined,
    ExclamationCircleOutlined
} from '@ant-design/icons';
import Editor from '@monaco-editor/react';
import axios from 'axios';

const { Panel } = Collapse;

/**
 * Testcases 檔案編輯器
 * 
 * 功能：
 * - 載入和編輯 testcases.yml 檔案
 * - 即時 YAML 語法驗證（防抖 1 秒）
 * - Jinja2 變數檢查
 * - 與 Inventory 交叉驗證 testcase_set
 * - 自動草稿儲存
 */
const TestcasesFileEditor = ({ inventoryId, onSaved }) => {
    // 基本狀態
    const [content, setContent] = useState('');
    const [originalContent, setOriginalContent] = useState('');
    const [loading, setLoading] = useState(false);
    const [saving, setSaving] = useState(false);
    const [hasChanges, setHasChanges] = useState(false);
    const [fileExists, setFileExists] = useState(true);
    const [filePath, setFilePath] = useState('');
    
    // 驗證狀態
    const [syntaxValid, setSyntaxValid] = useState(true);
    const [syntaxError, setSyntaxError] = useState(null);
    const [errorLine, setErrorLine] = useState(null);
    const [validationDetails, setValidationDetails] = useState(null);
    
    // Refs
    const validateTimeoutRef = useRef(null);
    const editorRef = useRef(null);
    const monacoRef = useRef(null);
    
    // 草稿 Key
    const getDraftKey = () => `testcases_draft_${inventoryId}`;
    
    // 載入文件內容
    useEffect(() => {
        if (inventoryId) {
            loadContent();
        }
    }, [inventoryId]);
    
    // 當內容載入後，檢查草稿
    useEffect(() => {
        if (originalContent && inventoryId) {
            checkForDraft();
        }
    }, [originalContent, inventoryId]);
    
    const loadContent = async () => {
        setLoading(true);
        try {
            const response = await axios.get(
                `/api/ansible-inventory/${inventoryId}/testcases-content/`
            );
            
            if (response.data.success) {
                setContent(response.data.content);
                setOriginalContent(response.data.content);
                setFileExists(true);
                setFilePath(response.data.file_path);
                message.success('testcases.yml 載入成功');
                
                // 初始驗證
                validateSyntax(response.data.content);
            }
        } catch (error) {
            console.error('載入失敗：', error);
            
            if (error.response?.status === 404) {
                setFileExists(false);
                setContent('# Testcase definitions\n# 請在此定義 testcase_set\n\n');
                message.warning('testcases.yml 檔案不存在，您可以創建新的');
            } else {
                message.error('載入失敗：' + (error.response?.data?.error || error.message));
            }
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
                content: '是否要恢復之前未儲存的 testcases.yml 編輯內容？',
                okText: '恢復草稿',
                cancelText: '丟棄草稿',
                onOk: () => {
                    setContent(draft);
                    setHasChanges(true);
                    message.info('已恢復草稿');
                    validateSyntax(draft);
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
                '/api/ansible-inventory/validate-testcases/',
                { 
                    content: contentToValidate,
                    inventory_id: inventoryId
                }
            );
            
            setSyntaxValid(response.data.syntax_valid);
            setSyntaxError(response.data.error_message);
            setErrorLine(response.data.error_line);
            setValidationDetails(response.data);
            
            // 更新編輯器中的錯誤標記
            updateEditorMarkers(response.data);
            
            if (response.data.syntax_valid) {
                // 只在手動驗證時顯示成功訊息
            }
        } catch (error) {
            console.error('驗證失敗：', error);
            setSyntaxValid(false);
            setSyntaxError('驗證失敗：' + (error.response?.data?.error || error.message));
        }
    };
    
    // 更新編輯器錯誤標記
    const updateEditorMarkers = (validationResult) => {
        if (!monacoRef.current || !editorRef.current) return;
        
        const model = editorRef.current.getModel();
        if (!model) return;
        
        const markers = [];
        
        // 語法錯誤
        if (!validationResult.syntax_valid && validationResult.error_line) {
            markers.push({
                severity: monacoRef.current.MarkerSeverity.Error,
                startLineNumber: validationResult.error_line,
                startColumn: validationResult.error_column || 1,
                endLineNumber: validationResult.error_line,
                endColumn: 1000,
                message: validationResult.error_message || 'YAML 語法錯誤'
            });
        }
        
        // Jinja2 警告
        if (validationResult.jinja2_check?.warnings) {
            validationResult.jinja2_check.warnings.forEach(warning => {
                // 嘗試從警告訊息中提取行號
                const lineMatch = warning.match(/第 (\d+) 行/);
                if (lineMatch) {
                    markers.push({
                        severity: monacoRef.current.MarkerSeverity.Warning,
                        startLineNumber: parseInt(lineMatch[1]),
                        startColumn: 1,
                        endLineNumber: parseInt(lineMatch[1]),
                        endColumn: 1000,
                        message: warning
                    });
                }
            });
        }
        
        monacoRef.current.editor.setModelMarkers(model, 'testcases-validator', markers);
    };
    
    // 儲存到 NAS
    const handleSave = async () => {
        // 先驗證語法
        setLoading(true);
        try {
            const validateResponse = await axios.post(
                '/api/ansible-inventory/validate-testcases/',
                { 
                    content: content,
                    inventory_id: inventoryId
                }
            );
            
            setSyntaxValid(validateResponse.data.syntax_valid);
            setSyntaxError(validateResponse.data.error_message);
            setValidationDetails(validateResponse.data);
            
            if (!validateResponse.data.syntax_valid) {
                Modal.confirm({
                    title: '語法錯誤',
                    icon: <ExclamationCircleOutlined />,
                    content: (
                        <div>
                            <p>目前內容存在 YAML 語法錯誤：</p>
                            <pre style={{ 
                                background: '#fff2f0', 
                                padding: '12px', 
                                borderRadius: '4px',
                                maxHeight: '200px',
                                overflow: 'auto',
                                border: '1px solid #ffccc7'
                            }}>
                                {validateResponse.data.error_message}
                            </pre>
                            {validateResponse.data.error_line && (
                                <p style={{ marginTop: '8px', color: '#ff4d4f' }}>
                                    錯誤位置：第 {validateResponse.data.error_line} 行
                                </p>
                            )}
                            <p style={{ marginTop: '12px' }}>請修正錯誤後再儲存。</p>
                        </div>
                    ),
                    okText: '確定',
                    cancelText: null,
                    okCancel: false
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
            const response = await axios.put(
                `/api/ansible-inventory/${inventoryId}/testcases-content/`,
                { content: content }
            );
            
            if (response.data.success) {
                message.success('testcases.yml 已儲存到 NAS');
                setOriginalContent(content);
                setHasChanges(false);
                setFileExists(true);
                
                // 清除草稿
                localStorage.removeItem(getDraftKey());
                
                // 通知父組件
                if (onSaved) {
                    onSaved();
                }
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
        message.loading('正在驗證...', 0);
        validateSyntax().finally(() => {
            message.destroy();
            if (syntaxValid) {
                message.success('YAML 語法驗證通過');
            }
        });
    };
    
    // 重新載入
    const handleReload = () => {
        if (hasChanges) {
            Modal.confirm({
                title: '確認重新載入',
                content: '您有未儲存的變更，重新載入將會丟失這些變更。確定要繼續嗎？',
                okText: '重新載入',
                cancelText: '取消',
                okButtonProps: { danger: true },
                onOk: () => {
                    localStorage.removeItem(getDraftKey());
                    loadContent();
                }
            });
        } else {
            loadContent();
        }
    };
    
    // 跳轉到錯誤行
    const goToErrorLine = () => {
        if (editorRef.current && errorLine) {
            editorRef.current.revealLineInCenter(errorLine);
            editorRef.current.setPosition({ lineNumber: errorLine, column: 1 });
            editorRef.current.focus();
        }
    };
    
    // 編輯器掛載
    const handleEditorDidMount = (editor, monaco) => {
        editorRef.current = editor;
        monacoRef.current = monaco;
        
        // 添加快捷鍵：Ctrl+S 儲存
        editor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.KeyS, () => {
            if (hasChanges) {
                handleSave();
            }
        });
        
        // 初始驗證後更新標記
        if (validationDetails) {
            updateEditorMarkers(validationDetails);
        }
    };
    
    // 渲染交叉驗證結果
    const renderCrossValidation = () => {
        if (!validationDetails?.cross_validation) return null;
        
        const cv = validationDetails.cross_validation;
        const hasMissing = cv.missing_sets?.length > 0;
        const hasUnused = cv.unused_sets?.length > 0;
        
        return (
            <Collapse ghost style={{ marginBottom: 16 }}>
                <Panel 
                    header={
                        <Space>
                            <span>交叉驗證結果</span>
                            {hasMissing && <Badge status="error" text={`${cv.missing_sets.length} 個缺失`} />}
                            {hasUnused && <Badge status="warning" text={`${cv.unused_sets.length} 個未使用`} />}
                            {!hasMissing && !hasUnused && <Badge status="success" text="全部匹配" />}
                        </Space>
                    }
                    key="cross-validation"
                >
                    <Descriptions column={1} size="small">
                        <Descriptions.Item label="Inventory 引用的 testcase_set">
                            {cv.referenced_count} 個
                        </Descriptions.Item>
                        {hasMissing && (
                            <Descriptions.Item label={<span style={{ color: '#ff4d4f' }}>缺失的定義</span>}>
                                <Space wrap>
                                    {cv.missing_sets.map(s => (
                                        <Tag key={s} color="error">{s}</Tag>
                                    ))}
                                </Space>
                            </Descriptions.Item>
                        )}
                        {hasUnused && (
                            <Descriptions.Item label={<span style={{ color: '#faad14' }}>未使用的定義</span>}>
                                <Space wrap>
                                    {cv.unused_sets.slice(0, 20).map(s => (
                                        <Tag key={s} color="warning">{s}</Tag>
                                    ))}
                                    {cv.unused_sets.length > 20 && (
                                        <Tag>還有 {cv.unused_sets.length - 20} 個...</Tag>
                                    )}
                                </Space>
                            </Descriptions.Item>
                        )}
                    </Descriptions>
                </Panel>
            </Collapse>
        );
    };
    
    return (
        <Card
            title={
                <Space>
                    <FileTextOutlined />
                    <span>Testcases 檔案編輯</span>
                    {!fileExists && <Tag color="orange">新檔案</Tag>}
                </Space>
            }
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
                        <Tag 
                            color="error" 
                            icon={<CloseCircleOutlined />}
                            style={{ cursor: errorLine ? 'pointer' : 'default' }}
                            onClick={goToErrorLine}
                        >
                            語法錯誤 {errorLine ? `(第 ${errorLine} 行)` : ''}
                        </Tag>
                    )}
                    {validationDetails?.testcase_sets_count !== undefined && (
                        <Tag color="blue">
                            {validationDetails.testcase_sets_count} 個 testcase_set
                        </Tag>
                    )}
                    {validationDetails?.jinja2_check?.total_jinja2_vars > 0 && (
                        <Tag color="purple">
                            {validationDetails.jinja2_check.total_jinja2_vars} 個 Jinja2 變數
                        </Tag>
                    )}
                    <Button
                        onClick={handleReload}
                        icon={<ReloadOutlined />}
                        disabled={loading}
                    >
                        重新載入
                    </Button>
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
                        disabled={!hasChanges || !syntaxValid}
                        icon={<SaveOutlined />}
                    >
                        儲存到 NAS
                    </Button>
                </Space>
            }
            style={{ marginTop: 16 }}
        >
            {/* 語法錯誤提示 */}
            {syntaxError && (
                <Alert
                    message={
                        <Space>
                            <span>YAML 語法錯誤</span>
                            {errorLine && (
                                <Button 
                                    type="link" 
                                    size="small" 
                                    onClick={goToErrorLine}
                                    style={{ padding: 0 }}
                                >
                                    跳轉到第 {errorLine} 行
                                </Button>
                            )}
                        </Space>
                    }
                    description={
                        <pre style={{ 
                            whiteSpace: 'pre-wrap', 
                            wordBreak: 'break-word',
                            margin: 0,
                            maxHeight: '100px',
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
            
            {/* Jinja2 警告 */}
            {validationDetails?.jinja2_check?.warnings?.length > 0 && (
                <Alert
                    message="Jinja2 變數警告"
                    description={
                        <ul style={{ margin: 0, paddingLeft: 20 }}>
                            {validationDetails.jinja2_check.warnings.slice(0, 5).map((w, i) => (
                                <li key={i}>{w}</li>
                            ))}
                            {validationDetails.jinja2_check.warnings.length > 5 && (
                                <li>還有 {validationDetails.jinja2_check.warnings.length - 5} 個警告...</li>
                            )}
                        </ul>
                    }
                    type="warning"
                    closable
                    style={{ marginBottom: 16 }}
                />
            )}
            
            {/* 交叉驗證結果 */}
            {renderCrossValidation()}
            
            {/* 編輯器 */}
            <Spin spinning={loading} tip="載入中...">
                <div style={{ border: '1px solid #d9d9d9', borderRadius: '4px' }}>
                    <Editor
                        height="550px"
                        defaultLanguage="yaml"
                        value={content}
                        onChange={handleEditorChange}
                        onMount={handleEditorDidMount}
                        theme="vs-light"
                        options={{
                            minimap: { enabled: true },
                            lineNumbers: 'on',
                            scrollBeyondLastLine: false,
                            fontSize: 14,
                            wordWrap: 'off',
                            automaticLayout: true,
                            tabSize: 2,
                            insertSpaces: true,
                            renderWhitespace: 'selection',
                            bracketPairColorization: { enabled: true },
                            folding: true,
                            foldingStrategy: 'indentation',
                            scrollbar: {
                                horizontal: 'visible',
                                vertical: 'visible'
                            }
                        }}
                    />
                </div>
            </Spin>
            
            {/* 底部提示 */}
            <div style={{ 
                marginTop: 12, 
                color: '#8c8c8c', 
                fontSize: '12px',
                display: 'flex',
                justifyContent: 'space-between'
            }}>
                <span>
                    💡 提示：Ctrl+S 快速儲存 | Ctrl+/ 切換註解 | 內容會自動儲存到本地草稿
                </span>
                {filePath && (
                    <span title={filePath}>
                        📁 {filePath.split('/').slice(-3).join('/')}
                    </span>
                )}
            </div>
        </Card>
    );
};

export default TestcasesFileEditor;
