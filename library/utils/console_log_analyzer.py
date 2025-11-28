"""
Jenkins Console Log Fatal Error 分析器

從 Ansible Console Log 中提取包含 fatal 關鍵字的完整 Task 範圍。

功能：
1. 查找所有包含 "fatal" 關鍵字的行（不區分大小寫）
2. 定位每個 fatal 所屬的 Ansible Task 範圍
3. 提取 Task 的完整內容（從 TASK 標記到下一個 TASK 或 PLAY RECAP）
4. 保存分析結果為 JSON 文件

使用方式：
    # 方式 1: 使用文件路徑
    analyzer = ConsoleLogAnalyzer(log_file_path='/path/to/console.log')
    result = analyzer.analyze_fatal_errors()
    
    # 方式 2: 使用已下載的內容
    analyzer = ConsoleLogAnalyzer(log_content=log_content_string)
    result = analyzer.analyze_fatal_errors()
    
    # 保存結果
    analyzer.save_analysis_to_json('/path/to/output.json')

作者: Network Toolbox Team
創建日期: 2025-11-27
版本: 1.0.0
"""

import re
import json
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)


class ConsoleLogAnalyzer:
    """Console Log Fatal Error 分析器類"""
    
    # 正則表達式模式
    TASK_HEADER_PATTERN = re.compile(
        r'^(\d{2}:\d{2}:\d{2})\s+TASK\s+\[(.*?)\]\s+\*+',
        re.IGNORECASE
    )
    FATAL_PATTERN = re.compile(r'\bfatal\b', re.IGNORECASE)
    PLAY_RECAP_PATTERN = re.compile(
        r'^(\d{2}:\d{2}:\d{2})\s+PLAY\s+RECAP\s+\*+',
        re.IGNORECASE
    )
    # ANSI 控制字符模式（用於清理彩色輸出）
    ANSI_ESCAPE_PATTERN = re.compile(r'\x1b\[[0-9;]*m')
    
    def __init__(
        self,
        log_file_path: Optional[str] = None,
        log_content: Optional[str] = None,
        server_ip: Optional[str] = None,
        job_name: Optional[str] = None,
        build_number: Optional[int] = None
    ):
        """
        初始化分析器
        
        Args:
            log_file_path: Console Log 文件路徑（與 log_content 二選一）
            log_content: Console Log 內容字串（與 log_file_path 二選一）
            server_ip: Jenkins 伺服器 IP（可選，用於記錄）
            job_name: Job 名稱（可選，用於記錄）
            build_number: Build 編號（可選，用於記錄）
        
        Raises:
            ValueError: 當 log_file_path 和 log_content 都未提供時
            FileNotFoundError: 當指定的文件不存在時
        """
        if not log_file_path and not log_content:
            raise ValueError("必須提供 log_file_path 或 log_content 其中之一")
        
        self.log_file_path = Path(log_file_path) if log_file_path else None
        self.server_ip = server_ip
        self.job_name = job_name
        self.build_number = build_number
        
        # 讀取日誌內容
        if log_content:
            self.log_content = log_content
        else:
            if not self.log_file_path.exists():
                raise FileNotFoundError(f"文件不存在: {self.log_file_path}")
            with open(self.log_file_path, 'r', encoding='utf-8', errors='ignore') as f:
                self.log_content = f.read()
        
        # 清理 ANSI 控制字符（Jenkins 彩色輸出）
        self.log_content = self.ANSI_ESCAPE_PATTERN.sub('', self.log_content)
        
        # 分割成行（保持行號對應）
        self.lines = self.log_content.split('\n')
        
        # 分析結果緩存
        self._analysis_result: Optional[Dict[str, Any]] = None
        
        logger.info(
            f"ConsoleLogAnalyzer 初始化完成 - "
            f"總行數: {len(self.lines)}, "
            f"來源: {'文件' if log_file_path else '內容'}"
        )
    
    def analyze_fatal_errors(self) -> Dict[str, Any]:
        """
        執行完整的 Fatal Error 分析
        
        分析流程：
        1. 掃描所有行，查找包含 "fatal" 的行號
        2. 對每個 fatal 行，定位其所屬的 Task 範圍
        3. 提取 Task 的完整內容
        4. 去重（同一 Task 可能有多個 fatal）
        5. 組織結構化數據
        
        Returns:
            Dict: 分析結果，包含以下結構：
                {
                    "build_info": {...},
                    "summary": {...},
                    "fatal_tasks": [...]
                }
        """
        start_time = datetime.now()
        logger.info("開始分析 Fatal Errors...")
        
        try:
            # 1. 查找所有 fatal 行
            fatal_lines = self.find_fatal_lines()
            logger.info(f"找到 {len(fatal_lines)} 個 fatal 錯誤")
            
            if not fatal_lines:
                # 沒有 fatal，返回空結果
                self._analysis_result = {
                    "build_info": self._build_info(start_time),
                    "summary": {
                        "total_fatal_count": 0,
                        "unique_task_count": 0,
                        "has_fatal_errors": False
                    },
                    "fatal_tasks": []
                }
                return self._analysis_result
            
            # 2. 提取每個 fatal 所屬的 Task Block
            task_blocks = []
            for line_num in fatal_lines:
                task_block = self.extract_task_block(line_num)
                if task_block:
                    task_blocks.append(task_block)
            
            # 3. 按 Task 去重並合併（同一 Task 可能有多個 fatal）
            unique_tasks = self._merge_duplicate_tasks(task_blocks)
            
            # 4. 組織最終結果
            self._analysis_result = {
                "build_info": self._build_info(start_time),
                "summary": {
                    "total_fatal_count": len(fatal_lines),
                    "unique_task_count": len(unique_tasks),
                    "has_fatal_errors": True
                },
                "fatal_tasks": unique_tasks
            }
            
            logger.info(
                f"分析完成 - 總 fatal: {len(fatal_lines)}, "
                f"唯一 Task: {len(unique_tasks)}"
            )
            return self._analysis_result
            
        except Exception as e:
            logger.error(f"分析過程發生錯誤: {e}", exc_info=True)
            raise
    
    def find_fatal_lines(self) -> List[int]:
        """
        查找所有包含 "fatal" 關鍵字的行號
        
        Returns:
            List[int]: 包含 fatal 的行號列表（0-based）
        """
        fatal_lines = []
        for line_num, line in enumerate(self.lines):
            if self.FATAL_PATTERN.search(line):
                fatal_lines.append(line_num)
        
        logger.debug(f"找到 {len(fatal_lines)} 行包含 fatal")
        return fatal_lines
    
    def extract_task_block(self, fatal_line_num: int) -> Optional[Dict[str, Any]]:
        """
        提取包含指定 fatal 行的完整 Task Block
        
        Args:
            fatal_line_num: fatal 錯誤的行號（0-based）
        
        Returns:
            Dict 或 None: Task Block 信息，包含：
                - task_name: Task 名稱
                - start_line: Task 起始行號
                - end_line: Task 結束行號
                - content: Task 完整內容
                - fatal_line: fatal 錯誤的行號
                - fatal_context: fatal 錯誤的上下文（前後3行）
        """
        try:
            # 1. 向上查找 TASK 標記
            task_start = self.find_task_boundary(fatal_line_num, direction='up')
            
            # 2. 向下查找下一個 TASK 或 PLAY RECAP
            task_end = self.find_task_boundary(fatal_line_num, direction='down')
            
            # 3. 提取 Task 名稱和時間戳
            if task_start is not None and task_start < len(self.lines):
                task_name, start_timestamp = self.parse_task_header(self.lines[task_start])
            else:
                task_name = "Unknown Task"
                start_timestamp = None
            
            # 4. 提取 Task 內容
            start_idx = task_start if task_start is not None else 0
            end_idx = task_end if task_end is not None else len(self.lines)
            task_content = '\n'.join(self.lines[start_idx:end_idx])
            
            # 5. 提取 fatal 上下文
            fatal_context = self._extract_fatal_context(fatal_line_num)
            
            return {
                "task_name": task_name,
                "start_line": start_idx + 1,  # 轉為 1-based
                "end_line": end_idx + 1,
                "start_timestamp": start_timestamp,
                "content": task_content,
                "fatal_line": fatal_line_num + 1,  # 轉為 1-based
                "fatal_context": fatal_context,
                "fatal_occurrences": [{
                    "line_number": fatal_line_num + 1,
                    "line_content": self.lines[fatal_line_num].strip(),
                    "timestamp": self._extract_timestamp(fatal_line_num),
                    "context_lines": fatal_context
                }]
            }
            
        except Exception as e:
            logger.error(f"提取 Task Block 失敗（行 {fatal_line_num}）: {e}", exc_info=True)
            return None
    
    def find_task_boundary(
        self,
        start_line: int,
        direction: str = 'up'
    ) -> Optional[int]:
        """
        查找 Task 邊界（向上或向下找到最近的 TASK 標記或 PLAY RECAP）
        
        Args:
            start_line: 起始行號
            direction: 搜索方向（'up' 或 'down'）
        
        Returns:
            int 或 None: 邊界行號，找不到則返回 None
        """
        if direction == 'up':
            # 向上搜索（從 start_line-1 開始）
            for line_num in range(start_line - 1, -1, -1):
                line = self.lines[line_num]
                if self.TASK_HEADER_PATTERN.match(line):
                    return line_num
                if self.PLAY_RECAP_PATTERN.match(line):
                    # 如果遇到 PLAY RECAP，說明已超出 Task 範圍
                    return None
            return None  # 到達文件開頭
        
        elif direction == 'down':
            # 向下搜索（從 start_line+1 開始）
            for line_num in range(start_line + 1, len(self.lines)):
                line = self.lines[line_num]
                if self.TASK_HEADER_PATTERN.match(line):
                    return line_num
                if self.PLAY_RECAP_PATTERN.match(line):
                    return line_num
            return len(self.lines)  # 到達文件末尾
        
        else:
            raise ValueError(f"無效的 direction: {direction}")
    
    def parse_task_header(self, line: str) -> Tuple[Optional[str], Optional[str]]:
        """
        解析 TASK 標記行，提取 Task 名稱和時間戳
        
        Args:
            line: TASK 標記行內容
        
        Returns:
            Tuple[task_name, timestamp]: (Task 名稱, 時間戳)
        
        範例:
            輸入: "10:00:13  TASK [test : Validate test case STC-551] *********"
            輸出: ("test : Validate test case STC-551", "10:00:13")
        """
        match = self.TASK_HEADER_PATTERN.match(line)
        if match:
            timestamp = match.group(1)
            task_name = match.group(2)
            return task_name, timestamp
        return None, None
    
    def save_analysis_to_json(
        self,
        output_path: Optional[Path] = None
    ) -> Path:
        """
        保存分析結果為 JSON 文件
        
        Args:
            output_path: 輸出文件路徑（可選）
                如果未提供，將使用默認命名：
                {server_ip}_{job_name}_{build_number}_fatal_analysis.json
        
        Returns:
            Path: 實際保存的文件路徑
        """
        # 確保已執行分析
        if self._analysis_result is None:
            self.analyze_fatal_errors()
        
        # 確定輸出路徑
        if output_path is None:
            filename = f"fatal_analysis.json"
            if self.server_ip and self.job_name and self.build_number:
                filename = (
                    f"{self.server_ip}_{self.job_name}_"
                    f"{self.build_number}_fatal_analysis.json"
                )
            output_path = Path(filename)
        else:
            output_path = Path(output_path)
        
        # 創建父目錄
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 寫入 JSON
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(
                self._analysis_result,
                f,
                ensure_ascii=False,
                indent=2
            )
        
        logger.info(f"分析結果已保存到: {output_path}")
        return output_path
    
    # ==================== 輔助方法 ====================
    
    def _extract_fatal_context(self, line_num: int, context_lines: int = 3) -> List[str]:
        """
        提取 fatal 行的上下文
        
        優先嘗試提取完整的 TASK 區塊（從 TASK 標題到 fatal 行 + 後續幾行）
        如果找不到 TASK 標題，則使用固定的前後 N 行
        """
        # 嘗試向上找到 TASK 標題
        task_start = None
        max_lookback = 50  # 最多向上回溯 50 行
        
        for i in range(line_num - 1, max(0, line_num - max_lookback) - 1, -1):
            line = self.lines[i]
            # 檢查是否為 TASK 標題行
            if re.search(r'TASK\s+\[', line) or re.search(r'PLAY\s+\[', line):
                task_start = i
                break
        
        # 如果找到 TASK 開頭，提取從 TASK 開頭到 fatal 行 + 後續幾行
        if task_start is not None:
            start = task_start
            end = min(len(self.lines), line_num + context_lines + 1)
        else:
            # Fallback: 使用固定的前後 N 行
            start = max(0, line_num - context_lines)
            end = min(len(self.lines), line_num + context_lines + 1)
        
        return [self.lines[i].strip() for i in range(start, end)]
    
    def _extract_timestamp(self, line_num: int) -> Optional[str]:
        """從行中提取時間戳（如果有）"""
        line = self.lines[line_num]
        # 嘗試匹配行首的時間戳格式 HH:MM:SS
        timestamp_pattern = re.compile(r'^(\d{2}:\d{2}:\d{2})')
        match = timestamp_pattern.match(line)
        return match.group(1) if match else None
    
    def _build_info(self, start_time: datetime) -> Dict[str, Any]:
        """構建 build_info 數據"""
        duration_ms = self._duration_ms(start_time)
        return {
            "server_ip": self.server_ip,
            "job_name": self.job_name,
            "build_number": self.build_number,
            "log_file_path": str(self.log_file_path) if self.log_file_path else None,
            "analyzed_at": datetime.now().isoformat(),
            "analysis_duration_ms": duration_ms,
            "total_lines": len(self.lines)
        }
    
    def _duration_ms(self, start_time: datetime) -> int:
        """計算執行時間（毫秒）"""
        delta = datetime.now() - start_time
        return int(delta.total_seconds() * 1000)
    
    def _merge_duplicate_tasks(self, task_blocks: List[Dict]) -> List[Dict]:
        """合併重複的 Task（同一 Task 有多個 fatal）"""
        task_map = {}
        
        for block in task_blocks:
            key = (block['task_name'], block['start_line'])
            
            if key in task_map:
                # 合併 fatal_occurrences
                task_map[key]['fatal_occurrences'].extend(block['fatal_occurrences'])
            else:
                task_map[key] = block
        
        # 轉為列表並排序
        unique_tasks = list(task_map.values())
        unique_tasks.sort(key=lambda x: x['start_line'])
        
        return unique_tasks


# ==================== 命令行工具 ====================

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(
        description='分析 Jenkins Console Log 中的 Fatal Errors'
    )
    parser.add_argument(
        'log_file',
        help='Console Log 文件路徑'
    )
    parser.add_argument(
        '-o', '--output',
        help='輸出 JSON 文件路徑（默認為自動生成）'
    )
    parser.add_argument(
        '--server-ip',
        help='Jenkins 伺服器 IP'
    )
    parser.add_argument(
        '--job-name',
        help='Job 名稱'
    )
    parser.add_argument(
        '--build-number',
        type=int,
        help='Build 編號'
    )
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='顯示詳細日誌'
    )
    
    args = parser.parse_args()
    
    # 配置日誌
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format='[%(levelname)s] %(message)s'
    )
    
    # 執行分析
    analyzer = ConsoleLogAnalyzer(
        log_file_path=args.log_file,
        server_ip=args.server_ip,
        job_name=args.job_name,
        build_number=args.build_number
    )
    
    result = analyzer.analyze_fatal_errors()
    
    # 保存結果
    output_path = analyzer.save_analysis_to_json(
        Path(args.output) if args.output else None
    )
    
    # 打印摘要
    print(f"\n分析完成！")
    print(f"總 fatal 數量: {result['summary']['total_fatal_count']}")
    print(f"唯一 Task 數量: {result['summary']['unique_task_count']}")
    print(f"結果已保存到: {output_path}")
