import React from 'react';
import { Tag } from 'antd';
import { WarningOutlined } from '@ant-design/icons';
import './FatalSnippet.css';

/**
 * 渲染高亮的內容（與 CodeBlockWithHighlight 相同的邏輯）
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
    
    // 按位置排序
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
 * FatalSnippet 組件
 * 
 * 顯示單個 Fatal 錯誤的完整內容
 * - 直接顯示完整的 snippet 字串
 * - 高亮 TASK 標題和 Fatal 關鍵字
 */
const FatalSnippet = ({ snippet }) => {
    if (!snippet) return null;
    
    // snippet 是一個字串，包含完整的 Fatal Error 內容
    const lines = snippet.split('\n');
    
    return (
        <div className="fatal-snippet-container">
            <div className="fatal-snippet-content">
                <pre className="snippet-code">
                    {lines.map((line, idx) => (
                        <div key={idx} className="snippet-line">
                            <span className="line-content">
                                {renderHighlightedContent(line)}
                            </span>
                        </div>
                    ))}
                </pre>
            </div>
        </div>
    );
};

export default FatalSnippet;
