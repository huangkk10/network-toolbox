# 測試用 Console Log 範例

此目錄包含用於測試 ConsoleLogAnalyzer 的範例 Console Log 文件。

## 文件說明

- `sample_with_fatal.log` - 包含 fatal 錯誤的範例（標準情況）
- `sample_no_fatal.log` - 不包含 fatal 的正常範例
- `sample_multiple_fatals.log` - 同一 Task 包含多個 fatal
- `sample_fatal_at_start.log` - Fatal 在文件開頭
- `sample_fatal_at_end.log` - Fatal 在文件結尾

## 使用方式

```python
from library.utils.console_log_analyzer import ConsoleLogAnalyzer

analyzer = ConsoleLogAnalyzer(
    log_file_path='tests/fixtures/sample_with_fatal.log',
    jenkins_server='10.252.170.187',
    job_name='TestJob',
    build_number=1
)

result = analyzer.analyze_fatal_errors()
```
