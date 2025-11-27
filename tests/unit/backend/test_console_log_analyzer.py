"""
ConsoleLogAnalyzer 單元測試

測試 backend/library/utils/console_log_analyzer.py
"""
import unittest
import json
import tempfile
from pathlib import Path
from library.utils.console_log_analyzer import ConsoleLogAnalyzer


class TestConsoleLogAnalyzer(unittest.TestCase):
    """ConsoleLogAnalyzer 單元測試"""
    
    @classmethod
    def setUpClass(cls):
        """測試類初始化 - 準備測試數據路徑"""
        cls.fixtures_dir = Path(__file__).parent.parent.parent / 'fixtures'
        cls.sample_with_fatal = cls.fixtures_dir / 'sample_with_fatal.log'
        cls.sample_no_fatal = cls.fixtures_dir / 'sample_no_fatal.log'
        cls.sample_multiple_fatals = cls.fixtures_dir / 'sample_multiple_fatals.log'
        cls.sample_fatal_at_start = cls.fixtures_dir / 'sample_fatal_at_start.log'
        cls.sample_fatal_at_end = cls.fixtures_dir / 'sample_fatal_at_end.log'
    
    def test_initialization_with_file_path(self):
        """測試使用文件路徑初始化"""
        analyzer = ConsoleLogAnalyzer(log_file_path=str(self.sample_with_fatal))
        self.assertIsNotNone(analyzer.log_content)
        self.assertGreater(len(analyzer.lines), 0)
    
    def test_initialization_with_content(self):
        """測試使用內容初始化"""
        content = "10:00:00 TASK [Test] ***\nfatal: [host]: FAILED!"
        analyzer = ConsoleLogAnalyzer(log_content=content)
        self.assertEqual(len(analyzer.lines), 2)
    
    def test_initialization_without_params(self):
        """測試無參數初始化應拋出異常"""
        with self.assertRaises(ValueError) as context:
            ConsoleLogAnalyzer()
        self.assertIn("必須提供", str(context.exception))
    
    def test_find_fatal_lines_single_fatal(self):
        """測試查找單個 fatal"""
        analyzer = ConsoleLogAnalyzer(log_file_path=str(self.sample_with_fatal))
        fatal_lines = analyzer.find_fatal_lines()
        
        self.assertIsInstance(fatal_lines, list)
        self.assertEqual(len(fatal_lines), 1)
        self.assertEqual(fatal_lines[0], 16)  # Line 16: "fatal: [web-server-02]..."
    
    def test_find_fatal_lines_no_fatal(self):
        """測試無 fatal 的情況"""
        analyzer = ConsoleLogAnalyzer(log_file_path=str(self.sample_no_fatal))
        fatal_lines = analyzer.find_fatal_lines()
        
        self.assertEqual(len(fatal_lines), 0)
    
    def test_find_fatal_lines_multiple_fatals(self):
        """測試同一 Task 多個 fatal"""
        analyzer = ConsoleLogAnalyzer(log_file_path=str(self.sample_multiple_fatals))
        fatal_lines = analyzer.find_fatal_lines()
        
        self.assertEqual(len(fatal_lines), 3)  # 3個 fatal 錯誤
        self.assertIn(4, fatal_lines)  # host-02
        self.assertIn(6, fatal_lines)  # host-04
        self.assertIn(8, fatal_lines)  # host-05
    
    def test_parse_task_header_valid(self):
        """測試解析有效的 Task 標題"""
        line = "10:00:13  TASK [test : Validate test case STC-551] ***************************************"
        analyzer = ConsoleLogAnalyzer(log_content="dummy")
        
        task_name, timestamp = analyzer.parse_task_header(line)
        
        self.assertEqual(task_name, "test : Validate test case STC-551")
        self.assertEqual(timestamp, "10:00:13")
    
    def test_parse_task_header_gathering_facts(self):
        """測試解析 Gathering Facts 任務"""
        line = "10:00:01  TASK [Gathering Facts] *********************************************************"
        analyzer = ConsoleLogAnalyzer(log_content="dummy")
        
        task_name, timestamp = analyzer.parse_task_header(line)
        
        self.assertEqual(task_name, "Gathering Facts")
        self.assertEqual(timestamp, "10:00:01")
    
    def test_parse_task_header_invalid(self):
        """測試解析無效的行"""
        line = "Some random log line"
        analyzer = ConsoleLogAnalyzer(log_content="dummy")
        
        task_name, timestamp = analyzer.parse_task_header(line)
        
        self.assertIsNone(task_name)
        self.assertIsNone(timestamp)
    
    def test_find_task_boundary_upward(self):
        """測試向上查找 Task 邊界"""
        analyzer = ConsoleLogAnalyzer(log_file_path=str(self.sample_with_fatal))
        
        # Fatal 在 line 16，應該找到 line 13 的 TASK 標記
        boundary_line = analyzer.find_task_boundary(16, direction='up')
        
        self.assertEqual(boundary_line, 13)  # "TASK [test : Validate test case STC-551]"
    
    def test_find_task_boundary_downward(self):
        """測試向下查找 Task 邊界"""
        analyzer = ConsoleLogAnalyzer(log_file_path=str(self.sample_with_fatal))
        
        # Fatal 在 line 16，向下應找到 line 17 的下一個 TASK 或 PLAY RECAP
        boundary_line = analyzer.find_task_boundary(16, direction='down')
        
        self.assertIsNotNone(boundary_line)
        self.assertGreater(boundary_line, 16)
    
    def test_extract_task_block_single_fatal(self):
        """測試提取包含單個 fatal 的 Task Block"""
        analyzer = ConsoleLogAnalyzer(log_file_path=str(self.sample_with_fatal))
        fatal_lines = analyzer.find_fatal_lines()
        
        task_block = analyzer.extract_task_block(fatal_lines[0])
        
        self.assertIsNotNone(task_block)
        self.assertIn('task_name', task_block)
        self.assertIn('start_line', task_block)
        self.assertIn('end_line', task_block)
        self.assertIn('content', task_block)
        self.assertIn('fatal_line', task_block)
        
        self.assertEqual(task_block['task_name'], 'test : Validate test case STC-551')
        self.assertIn('fatal:', task_block['content'])
    
    def test_analyze_fatal_errors_with_fatal(self):
        """測試完整分析流程 - 有 fatal"""
        analyzer = ConsoleLogAnalyzer(log_file_path=str(self.sample_with_fatal))
        result = analyzer.analyze_fatal_errors()
        
        # 驗證結果結構
        self.assertIn('build_info', result)
        self.assertIn('summary', result)
        self.assertIn('fatal_tasks', result)
        
        # 驗證 summary
        self.assertEqual(result['summary']['total_fatal_count'], 1)
        self.assertEqual(result['summary']['unique_task_count'], 1)
        
        # 驗證 fatal_tasks
        self.assertEqual(len(result['fatal_tasks']), 1)
        task = result['fatal_tasks'][0]
        self.assertEqual(task['task_name'], 'test : Validate test case STC-551')
        self.assertEqual(len(task['fatal_occurrences']), 1)
        self.assertEqual(task['fatal_occurrences'][0]['line_number'], 16)
    
    def test_analyze_fatal_errors_no_fatal(self):
        """測試完整分析流程 - 無 fatal"""
        analyzer = ConsoleLogAnalyzer(log_file_path=str(self.sample_no_fatal))
        result = analyzer.analyze_fatal_errors()
        
        self.assertEqual(result['summary']['total_fatal_count'], 0)
        self.assertEqual(result['summary']['unique_task_count'], 0)
        self.assertEqual(len(result['fatal_tasks']), 0)
    
    def test_analyze_fatal_errors_multiple_fatals(self):
        """測試完整分析流程 - 多個 fatal"""
        analyzer = ConsoleLogAnalyzer(log_file_path=str(self.sample_multiple_fatals))
        result = analyzer.analyze_fatal_errors()
        
        self.assertEqual(result['summary']['total_fatal_count'], 3)
        self.assertEqual(result['summary']['unique_task_count'], 1)  # 同一個 Task
        
        # 驗證有 3 個 fatal_occurrences
        task = result['fatal_tasks'][0]
        self.assertEqual(len(task['fatal_occurrences']), 3)
    
    def test_analyze_fatal_at_start(self):
        """測試 fatal 在文件開頭的情況"""
        analyzer = ConsoleLogAnalyzer(log_file_path=str(self.sample_fatal_at_start))
        result = analyzer.analyze_fatal_errors()
        
        self.assertGreater(result['summary']['total_fatal_count'], 0)
        # 確保能正確處理沒有前置 TASK 標記的情況
        self.assertIsNotNone(result['fatal_tasks'][0])
    
    def test_analyze_fatal_at_end(self):
        """測試 fatal 在文件結尾的情況"""
        analyzer = ConsoleLogAnalyzer(log_file_path=str(self.sample_fatal_at_end))
        result = analyzer.analyze_fatal_errors()
        
        self.assertGreater(result['summary']['total_fatal_count'], 0)
        # 確保能正確處理沒有後續 TASK 標記的情況
        task = result['fatal_tasks'][0]
        self.assertIsNotNone(task['content'])
    
    def test_save_analysis_to_json(self):
        """測試保存分析結果為 JSON"""
        analyzer = ConsoleLogAnalyzer(log_file_path=str(self.sample_with_fatal))
        
        # 使用臨時文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp:
            output_path = Path(tmp.name)
        
        try:
            # 執行分析並保存
            result = analyzer.analyze_fatal_errors()
            saved_path = analyzer.save_analysis_to_json(output_path)
            
            # 驗證文件存在
            self.assertTrue(saved_path.exists())
            
            # 驗證 JSON 內容
            with open(saved_path, 'r', encoding='utf-8') as f:
                loaded_data = json.load(f)
            
            self.assertEqual(loaded_data['summary']['total_fatal_count'], 1)
            self.assertEqual(len(loaded_data['fatal_tasks']), 1)
            
        finally:
            # 清理臨時文件
            if output_path.exists():
                output_path.unlink()
    
    def test_build_info_structure(self):
        """測試 build_info 數據結構"""
        analyzer = ConsoleLogAnalyzer(
            log_file_path=str(self.sample_with_fatal),
            server_ip='10.252.170.171',
            job_name='Test-Job',
            build_number=123
        )
        
        result = analyzer.analyze_fatal_errors()
        build_info = result['build_info']
        
        self.assertEqual(build_info['server_ip'], '10.252.170.171')
        self.assertEqual(build_info['job_name'], 'Test-Job')
        self.assertEqual(build_info['build_number'], 123)
        self.assertIsNotNone(build_info['analyzed_at'])
    
    def test_extract_fatal_context(self):
        """測試提取 fatal 上下文（前後3行）"""
        analyzer = ConsoleLogAnalyzer(log_file_path=str(self.sample_with_fatal))
        result = analyzer.analyze_fatal_errors()
        
        fatal_occurrence = result['fatal_tasks'][0]['fatal_occurrences'][0]
        context_lines = fatal_occurrence['context_lines']
        
        # 應包含前後3行的上下文
        self.assertIsInstance(context_lines, list)
        self.assertGreater(len(context_lines), 0)
    
    def test_duration_calculation(self):
        """測試執行時間計算"""
        analyzer = ConsoleLogAnalyzer(log_file_path=str(self.sample_with_fatal))
        result = analyzer.analyze_fatal_errors()
        
        duration_ms = result['build_info']['analysis_duration_ms']
        
        self.assertIsInstance(duration_ms, (int, float))
        self.assertGreater(duration_ms, 0)
    
    def test_case_insensitive_fatal_detection(self):
        """測試大小寫不敏感的 fatal 檢測"""
        content = "10:00:00 TASK [Test] ***\nFATAL: [host]: error\nFatal: another error\nfatal: third error"
        analyzer = ConsoleLogAnalyzer(log_content=content)
        
        fatal_lines = analyzer.find_fatal_lines()
        
        # 應該檢測到所有大小寫變體
        self.assertEqual(len(fatal_lines), 3)


class TestEdgeCases(unittest.TestCase):
    """邊界情況測試"""
    
    def test_empty_log_content(self):
        """測試空的日誌內容"""
        analyzer = ConsoleLogAnalyzer(log_content="")
        result = analyzer.analyze_fatal_errors()
        
        self.assertEqual(result['summary']['total_fatal_count'], 0)
    
    def test_log_with_only_fatal_no_task(self):
        """測試只有 fatal 沒有 TASK 標記的日誌"""
        content = "fatal: [host]: Connection failed"
        analyzer = ConsoleLogAnalyzer(log_content=content)
        result = analyzer.analyze_fatal_errors()
        
        # 應該能處理無 TASK 標記的情況
        self.assertGreater(result['summary']['total_fatal_count'], 0)
    
    def test_nonexistent_file(self):
        """測試讀取不存在的文件"""
        with self.assertRaises(FileNotFoundError):
            ConsoleLogAnalyzer(log_file_path='/nonexistent/path/to/file.log')
    
    def test_unicode_content(self):
        """測試包含 Unicode 字符的日誌"""
        content = "10:00:00 TASK [測試任務] ***\nfatal: [主機]: 連接失敗 ❌"
        analyzer = ConsoleLogAnalyzer(log_content=content)
        result = analyzer.analyze_fatal_errors()
        
        self.assertEqual(result['summary']['total_fatal_count'], 1)
        # 確保 Unicode 字符正確處理
        self.assertIn('測試任務', result['fatal_tasks'][0]['task_name'])


if __name__ == '__main__':
    unittest.main()
