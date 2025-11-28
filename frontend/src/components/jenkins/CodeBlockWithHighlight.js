import React from 'react';
import './CodeBlockWithHighlight.css';

/**
 * 渲染高亮的內容
 * - TASK 標題行使用粗體黑色
 * - Fatal 關鍵字使用紅色 + 粗體
 */
const renderHighlightedContent = (line) => {
    // 檢查是否為 TASK/PLAY 標題行（僅用於加粗，不高亮顏色）
    const isTaskLine = /TASK\s+\[|PLAY\s+\[/.test(line);
    
    // Fatal 關鍵字模式
    const fatalPatterns = [
        { regex: /\bfatal:/gi, className: 'fatal-keyword' },
        { regex: /FAILED!/g, className: 'fatal-keyword' },
        { regex: /\[ERROR\]/g, className: 'fatal-keyword' },
        { regex: /failed=\d+/g, className: 'fatal-keyword' },
        { regex: /\bFAILURE\b/g, className: 'fatal-keyword' }
    ];
    
    // 收集所有匹配位置
    const matches = [];
    fatalPatterns.forEach(({ regex, className }) => {
        const pattern = new RegExp(regex);
        let match;
        while ((match = pattern.exec(line)) !== null) {
            matches.push({
                start: match.index,
                end: match.index + match[0].length,
                text: match[0],
                className
            });
        }
    });
    
    // 按位置排序並去重
    matches.sort((a, b) => a.start - b.start);
    
    // 如果沒有匹配，直接返回
    if (matches.length === 0) {
        return isTaskLine ? <strong>{line}</strong> : line;
    }
    
    // 構建帶高亮的內容
    const parts = [];
    let lastIndex = 0;
    
    matches.forEach((match, i) => {
        // 避免重疊
        if (match.start < lastIndex) return;
        
        // 添加普通文本
        if (match.start > lastIndex) {
            parts.push(
                <span key={`text-${i}`}>
                    {line.substring(lastIndex, match.start)}
                </span>
            );
        }
        
        // 添加高亮文本
        parts.push(
            <span key={`highlight-${i}`} className={match.className}>
                {match.text}
            </span>
        );
        
        lastIndex = match.end;
    });
    
    // 添加剩餘文本
    if (lastIndex < line.length) {
        parts.push(
            <span key="text-end">{line.substring(lastIndex)}</span>
        );
    }
    
    // 如果是 TASK 行，整行加粗
    return isTaskLine ? <strong>{parts}</strong> : <>{parts}</>;
};

/**
 * 代碼高亮組件
 * 
 * 用於顯示 Console Log Task 內容並高亮 Fatal 行
 * - 顯示行號
 * - 高亮指定行（Fatal 行）
 * - TASK 標題行使用粗體
 * - Fatal 關鍵字使用紅色 + 粗體
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
                            <span className="line-content">
                                {renderHighlightedContent(line)}
                            </span>
                        </div>
                    );
                })}
            </pre>
        </div>
    );
};

export default CodeBlockWithHighlight;
