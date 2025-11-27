import React from 'react';
import './CodeBlockWithHighlight.css';

/**
 * 代碼高亮組件
 * 
 * 用於顯示 Console Log Task 內容並高亮 Fatal 行
 * - 顯示行號
 * - 高亮指定行（Fatal 行）
 * - 支持長內容滾動
 */
const CodeBlockWithHighlight = ({ 
    content, 
    highlightLines = [],  // 需要高亮的絕對行號陣列
    startLine = 1         // 內容的起始行號
}) => {
    if (!content) {
        return <div className="code-block-empty">無內容</div>;
    }
    
    const lines = content.split('\n');
    
    return (
        <div className="code-block-container">
            <pre className="code-block">
                {lines.map((line, index) => {
                    const lineNumber = startLine + index;
                    const isHighlight = highlightLines.includes(lineNumber);
                    
                    return (
                        <div 
                            key={index}
                            className={`code-line ${isHighlight ? 'highlight-fatal' : ''}`}
                        >
                            <span className="line-number">{lineNumber}</span>
                            <span className="line-content">{line}</span>
                        </div>
                    );
                })}
            </pre>
        </div>
    );
};

export default CodeBlockWithHighlight;
