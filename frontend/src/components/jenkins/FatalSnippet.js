import React from 'react';
import { Tag } from 'antd';
import { WarningOutlined } from '@ant-design/icons';
import './FatalSnippet.css';

/**
 * FatalSnippet 組件
 * 
 * 顯示單個 Fatal 錯誤的上下文（前後 3 行）
 * 
 * Props:
 * - snippet: {
 *     line_number: int,
 *     content: string,
 *     context_before: string[],
 *     context_after: string[]
 *   }
 */
const FatalSnippet = ({ snippet }) => {
    if (!snippet) return null;
    
    const { line_number, content, context_before, context_after } = snippet;
    
    return (
        <div className="fatal-snippet-container">
            <div className="fatal-snippet-header">
                <Tag color="red" icon={<WarningOutlined />}>
                    Fatal 行號: {line_number}
                </Tag>
            </div>
            
            <div className="fatal-snippet-content">
                {/* 前置上下文 (灰色) */}
                {context_before && context_before.length > 0 && (
                    <div className="context-before">
                        {context_before.map((line, idx) => (
                            <div key={`before-${idx}`} className="context-line">
                                <span className="line-number">
                                    {line_number - context_before.length + idx}
                                </span>
                                <span className="line-content">{line}</span>
                            </div>
                        ))}
                    </div>
                )}
                
                {/* Fatal 行 (紅色高亮) */}
                <div className="fatal-line">
                    <span className="line-number fatal">{line_number}</span>
                    <span className="line-content fatal">{content}</span>
                </div>
                
                {/* 後置上下文 (灰色) */}
                {context_after && context_after.length > 0 && (
                    <div className="context-after">
                        {context_after.map((line, idx) => (
                            <div key={`after-${idx}`} className="context-line">
                                <span className="line-number">
                                    {line_number + idx + 1}
                                </span>
                                <span className="line-content">{line}</span>
                            </div>
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
};

export default FatalSnippet;
