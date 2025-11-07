# Tests

本目錄包含 Network Toolbox 專案的所有測試文件。

## 📁 目錄結構

```
tests/
├── unit/                   # 單元測試
│   └── backend/           # 後端單元測試
│       └── test_log_parser.py
├── integration/            # 整合測試
│   ├── api/               # API 整合測試
│   ├── dhcp/              # DHCP 相關測試
│   ├── ipxe/              # iPXE 相關測試
│   ├── network/           # 網路設備測試
│   └── services/          # 服務層測試
└── README.md              # 本文件
```

## 🧪 測試類型

### 單元測試 (Unit Tests)
**位置**: `tests/unit/`

測試單一函數、類別或組件的功能。

**範例**:
- `test_log_parser.py` - 測試日誌解析器的各種解析邏輯

### 整合測試 (Integration Tests)
**位置**: `tests/integration/`

測試多個組件之間的交互、API 測試、服務連接測試。

#### API 測試 (`api/`)
- `test_logs_api.py` - 測試日誌 API 端點

#### DHCP 測試 (`dhcp/`)
- `test_dhcp_config_sync.py` - DHCP 配置同步測試
- `test_dhcp_options.py` - DHCP Options 解析測試
- `test_dhcp_ssh.py` - DHCP SSH 連接測試
- `test_sync_simple.py` - 簡單同步測試

#### iPXE 測試 (`ipxe/`)
- `test_ipxe_connection.py` - iPXE 服務連接測試
- `test_ipxe_detection.py` - iPXE 客戶端檢測測試
- `test_ipxe_detection_backend.py` - 後端 iPXE 檢測邏輯
- `test_ipxe_migration_poc.py` - iPXE 遷移概念驗證

#### 網路測試 (`network/`)
- `test_device_detection.py` - 網路設備檢測測試
- `test_find_switches.py` - 交換機查找測試

#### 服務測試 (`services/`)
- `test_mac_vendor.py` - MAC 廠商查詢測試
- `test_mac_vendor_simple.py` - 簡化版 MAC 查詢測試
- `test_nas_connection.py` - NAS 連接測試
- `test_ssh_service.py` - SSH 服務基礎測試
- `test_ssh_sync.py` - SSH 同步服務測試

## 🚀 執行測試

### 執行所有測試
```bash
# Django 測試框架
cd /home/owner/Codes/network-toolbox/backend
python manage.py test tests

# 或使用 pytest (如果已安裝)
pytest tests/
```

### 執行特定類型的測試
```bash
# 單元測試
python manage.py test tests.unit

# 整合測試
python manage.py test tests.integration

# 特定類別的整合測試
python manage.py test tests.integration.dhcp
python manage.py test tests.integration.ipxe
python manage.py test tests.integration.services
```

### 執行單一測試文件
```bash
# 使用完整路徑執行
python /home/owner/Codes/network-toolbox/tests/unit/backend/test_log_parser.py

# 使用 Django 測試框架
python manage.py test tests.unit.backend.test_log_parser
```

## 📝 測試命名規範

### 文件命名
- **格式**: `test_<功能名稱>.py`
- **範例**: `test_dhcp_config_sync.py`, `test_log_parser.py`

### 測試類別命名
- **格式**: `Test<功能名稱>`
- **範例**: `TestDHCPConfigSync`, `TestLogParser`

### 測試方法命名
- **格式**: `test_<測試場景>`
- **範例**: `test_parse_config_file()`, `test_invalid_input()`

## 📋 測試開發指南

### 1. 創建新測試

**步驟**:
1. 確定測試類型（單元測試 or 整合測試）
2. 選擇合適的子目錄
3. 創建 `test_<功能名稱>.py` 文件
4. 編寫測試用例

**單元測試範例**:
```python
# tests/unit/backend/test_example.py
from django.test import TestCase

class TestExampleFunction(TestCase):
    def setUp(self):
        """測試初始化"""
        pass
    
    def test_basic_functionality(self):
        """測試基本功能"""
        result = example_function()
        self.assertEqual(result, expected_value)
    
    def tearDown(self):
        """測試清理"""
        pass
```

**整合測試範例**:
```python
# tests/integration/services/test_example.py
from rest_framework.test import APITestCase
from rest_framework import status

class TestExampleAPI(APITestCase):
    def test_api_endpoint(self):
        """測試 API 端點"""
        response = self.client.get('/api/example/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
```

### 2. 測試最佳實踐

✅ **DO**:
- 使用描述性的測試名稱
- 每個測試只測試一個功能點
- 使用 `setUp()` 和 `tearDown()` 管理測試數據
- 添加文檔字串說明測試目的
- 測試邊界條件和異常情況

❌ **DON'T**:
- 測試依賴於執行順序
- 測試依賴於外部狀態
- 測試數據硬編碼
- 在測試中使用生產環境配置

### 3. 測試覆蓋率

檢查測試覆蓋率:
```bash
# 安裝 coverage
pip install coverage

# 執行測試並生成覆蓋率報告
coverage run --source='.' manage.py test tests
coverage report
coverage html  # 生成 HTML 報告
```

## 🔧 測試環境配置

### 環境變數
```bash
# .env.test
DJANGO_SETTINGS_MODULE=network_toolbox.settings.test
DATABASE_NAME=test_network_toolbox
DEBUG=False
```

### 測試資料庫
測試使用獨立的資料庫，避免影響開發環境：
- **開發**: `network_toolbox`
- **測試**: `test_network_toolbox`

### Docker 容器測試
```bash
# 在容器內執行測試
docker exec nt-django python manage.py test tests

# 查看測試日誌
docker exec nt-django cat /app/logs/django.log
```

## ⚠️ 注意事項

1. **不要在生產環境執行測試**
   - 測試可能會修改數據
   - 使用測試專用的伺服器和資料庫

2. **測試數據隔離**
   - 使用 Django 的 `TestCase`（自動回滾事務）
   - 每個測試應該獨立運行
   - 清理測試創建的資料

3. **SSH 和 API 憑證**
   - 不要在代碼中硬編碼密碼
   - 使用環境變數或配置文件
   - `.gitignore` 排除憑證文件

4. **測試執行時間**
   - 單元測試應該快速（< 1 秒）
   - 整合測試可以較慢（< 10 秒）
   - 避免在測試中使用 `sleep()`

## 📚 相關資源

- [Django Testing Documentation](https://docs.djangoproject.com/en/4.2/topics/testing/)
- [Django REST Framework Testing](https://www.django-rest-framework.org/api-guide/testing/)
- [Python unittest Documentation](https://docs.python.org/3/library/unittest.html)
- [pytest Documentation](https://docs.pytest.org/)

## 🤝 貢獻指南

添加新測試時請：
1. 遵循現有的目錄結構
2. 使用描述性的命名
3. 添加適當的文檔字串
4. 更新相關的 README
5. 確保測試可以獨立運行

---

**最後更新**: 2025-11-01  
**維護者**: Network Toolbox Team
