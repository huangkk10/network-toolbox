# Backend Unit Tests

本目錄包含後端代碼的單元測試。

## 📁 測試文件

### test_log_parser.py
測試日誌解析器的功能。

**測試範圍**:
- `WindowsDHCPLogParser` - Windows DHCP 日誌解析
  - CSV 格式解析
  - 事件類型識別
  - 客戶端類型判斷（iPXE, PXE, WinPE, Windows）
  
- `DHCPLogParser` - Linux DHCP 日誌解析
  - Syslog 格式解析
  - dhcpd.log 格式解析
  
- `IPXELogParser` - iPXE 日誌解析
  - Nginx access log 格式
  - MAC Flask API 日誌
  - iPXE Boot 日誌

**執行測試**:
```bash
cd /home/owner/Codes/network-toolbox/backend
python manage.py test tests.unit.backend.test_log_parser
```

## 🧪 單元測試準則

單元測試應該：

✅ **快速執行** - 單個測試應在 1 秒內完成  
✅ **獨立運行** - 不依賴其他測試或外部狀態  
✅ **可重複** - 每次執行結果相同  
✅ **單一職責** - 每個測試只測試一個功能點  
✅ **清晰命名** - 測試名稱清楚說明測試內容

❌ **避免**：
- 依賴外部服務（資料庫、API、SSH）
- 依賴檔案系統
- 依賴網路連接
- 使用固定時間（使用 mock）

## 📝 測試範例

```python
from django.test import TestCase
from library.utils.log_parser import WindowsDHCPLogParser

class TestWindowsDHCPLogParser(TestCase):
    """測試 Windows DHCP 日誌解析器"""
    
    def test_parse_renew_event(self):
        """測試解析 Renew 事件"""
        line = '11,11/01/25,04:05:32,Renew,10.250.71.22,PC-001,AABBCCDDEEFF,,123456,0,,,,0x4D53465420352E30,MSFT 5.0,,'
        
        result = WindowsDHCPLogParser.parse_line(line)
        
        self.assertIsNotNone(result)
        self.assertEqual(result['event_type'], 'Renew')
        self.assertEqual(result['ip_address'], '10.250.71.22')
        self.assertEqual(result['hostname'], 'PC-001')
        self.assertEqual(result['mac_address'], 'aa:bb:cc:dd:ee:ff')
        self.assertEqual(result['client_type'], 'Windows')
    
    def test_identify_ipxe_client(self):
        """測試識別 iPXE 客戶端"""
        fields = ['11', '11/01/25', '10:00:00', 'Renew', '10.0.0.1', 
                  '', 'AABBCCDDEEFF', '', '', '0', '', '', '', '', 
                  '', '0x69505845', 'iPXE']
        
        result = WindowsDHCPLogParser.identify_client_type(fields)
        
        self.assertEqual(result['client_type'], 'iPXE')
        self.assertEqual(result['boot_stage'], 'iPXE Loading')
    
    def test_identify_windows_client(self):
        """測試識別 Windows 客戶端"""
        fields = ['11', '11/01/25', '10:00:00', 'Renew', '10.0.0.1', 
                  'PC-SSD-4632', 'AABBCCDDEEFF', '', '', '0', '', '', '', '', 
                  'MSFT 5.0', '', '']
        
        result = WindowsDHCPLogParser.identify_client_type(fields)
        
        self.assertEqual(result['client_type'], 'Windows')
        self.assertEqual(result['boot_stage'], 'Operating System')
```

## 🔄 測試生命週期

```python
class TestExample(TestCase):
    @classmethod
    def setUpClass(cls):
        """類別層級設定（所有測試前執行一次）"""
        super().setUpClass()
        # 初始化共用資源
    
    def setUp(self):
        """每個測試前執行"""
        # 創建測試數據
        self.test_data = {...}
    
    def test_something(self):
        """測試某功能"""
        # 執行測試
        result = do_something(self.test_data)
        self.assertEqual(result, expected)
    
    def tearDown(self):
        """每個測試後執行"""
        # 清理測試數據
        pass
    
    @classmethod
    def tearDownClass(cls):
        """類別層級清理（所有測試後執行一次）"""
        super().tearDownClass()
        # 清理共用資源
```

## 📊 測試覆蓋率

檢查單元測試覆蓋率：

```bash
# 執行測試並生成覆蓋率報告
coverage run --source='library/utils' manage.py test tests.unit.backend
coverage report

# 查看詳細報告
coverage html
# 在瀏覽器中打開 htmlcov/index.html
```

## 🔧 Mock 使用

對於需要外部依賴的情況，使用 mock：

```python
from unittest.mock import patch, MagicMock

class TestWithMock(TestCase):
    @patch('library.utils.log_parser.some_external_call')
    def test_with_mocked_dependency(self, mock_call):
        """測試使用 mock 的功能"""
        # 設定 mock 返回值
        mock_call.return_value = 'mocked_value'
        
        # 執行測試
        result = function_that_uses_external_call()
        
        # 驗證結果
        self.assertEqual(result, expected)
        
        # 驗證 mock 被調用
        mock_call.assert_called_once()
```

## 📚 相關資源

- [Django Testing Tools](https://docs.djangoproject.com/en/4.2/topics/testing/tools/)
- [Python unittest.mock](https://docs.python.org/3/library/unittest.mock.html)
- [Testing Best Practices](https://docs.python-guide.org/writing/tests/)

---

**最後更新**: 2025-11-01  
**維護者**: Network Toolbox Team
