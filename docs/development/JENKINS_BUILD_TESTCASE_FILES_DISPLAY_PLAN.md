# Jenkins Build 測試案例檔案顯示規劃

## 📋 需求說明

在 RVT 分析頁面中，針對各個 Build：
1. **主機固定為 Job Name**：不需要選擇主機，直接使用與 Job 同名的主機
2. **讀取該主機的 testcase_set 參數**：從 inventory 檔案中讀取
3. **顯示測試案例目錄內容**：列出該測試案例集合下的所有測試檔案
4. **獨立一個 Block 展示**：在前端用 Drawer 或 Block 顯示
5. **先規劃不執行**

---

## 🔍 現況分析

### 1. Inventory 檔案結構

**檔案位置**：
```
/mnt/mdt/Team/PQ1-3/tool/jenkins_test_storage/{server_ip}/{job_name}/{build_number}/artifacts/inventory/hosts
```

**檔案內容範例**：
```ini
[PQ1_3]
Test-KVM01 ansible_host=10.250.71.22 device_number=PC-SSD-4632 testcase_set=testcases_demo
SAF3101_KVM03 ansible_host=10.250.120.114 device_number=PC-SSD-6151 testcase_set=testcases_production
```

**關鍵點**：
- 主機名稱（如 `Test-KVM01`）通常與 Job Name 相同
- `testcase_set` 欄位指向測試案例目錄名稱（如 `testcases_demo`）

---

### 2. 測試案例目錄結構（推測）

測試案例應該存放在 workspace 或特定目錄下：

```
148/
├── workspace/
│   ├── testcases_demo/              ← testcase_set 指向的目錄
│   │   ├── test_basic.py
│   │   ├── test_advanced.py
│   │   ├── test_performance.py
│   │   └── config.yaml
│   ├── testcases_production/
│   │   ├── test_smoke.py
│   │   ├── test_regression.py
│   │   └── requirements.txt
│   └── ...
└── artifacts/
    └── inventory/
        └── hosts
```

**或者**，測試案例在 NAS 的固定位置：

```
/mnt/mdt/Team/PQ1-3/testcases/
├── testcases_demo/
│   ├── test_*.py
│   └── config.yaml
└── testcases_production/
    ├── test_*.py
    └── config.yaml
```

---

## 🎯 解決方案設計

### 方案 A：從 Workspace 讀取測試案例 ✅ **推薦**

#### 優點
- ✅ 測試案例與 Build 緊密關聯
- ✅ 保證版本一致性（該 Build 使用的測試案例）
- ✅ 不需要額外配置路徑

#### 缺點
- ⚠️ 需要確保 workspace 已存儲到 NAS
- ⚠️ 測試案例目錄結構需要標準化

---

### 方案 B：從 NAS 固定路徑讀取

#### 優點
- ✅ 統一管理測試案例
- ✅ 測試案例可以獨立版本控制

#### 缺點
- ❌ 無法追蹤特定 Build 使用的測試案例版本
- ❌ 需要配置測試案例基礎路徑

---

## 📦 方案 A 詳細設計（推薦）

### 架構流程

```
用戶點擊「測試案例」按鈕
         ↓
前端組件：TestCaseFilesDrawer
         ↓
API 調用：GET /api/jenkins-builds/{id}/test-case-files/
         ↓
後端處理：
  1. 獲取 Build 資訊（job_name, build_number）
  2. 檢查 workspace 是否已存儲
  3. 從 inventory 獲取主機配置（主機名 = job_name）
  4. 讀取主機的 testcase_set 參數
  5. 列出 workspace/{testcase_set}/ 目錄內容
  6. 返回測試檔案列表
         ↓
前端顯示：
  - 測試案例集名稱
  - 測試檔案列表（樹狀結構）
  - 檔案類型、大小、修改時間
```

---

## 📦 後端實現

### 1. 新增 API 端點

**位置**：`backend/api/views/jenkins.py` - `JenkinsBuildViewSet`

```python
@action(detail=True, methods=['get'], url_path='test-case-files')
def get_test_case_files(self, request, pk=None):
    """
    獲取 Build 的測試案例檔案列表
    
    GET /api/jenkins-builds/{id}/test-case-files/
    
    流程：
    1. 主機名固定為 job_name（例如：Test-KVM01）
    2. 從 inventory 讀取該主機的 testcase_set 參數
    3. 列出 workspace/{testcase_set}/ 目錄下的所有檔案
    
    Returns:
        {
            "success": true,
            "build_id": 123,
            "build_number": 148,
            "job_name": "Test-KVM01",
            "host_name": "Test-KVM01",          // 與 job_name 相同
            "testcase_set": "testcases_demo",
            "testcase_path": "/mnt/.../workspace/testcases_demo",
            "files": [
                {
                    "name": "test_basic.py",
                    "path": "test_basic.py",
                    "type": "file",
                    "size": 1024,
                    "extension": ".py",
                    "modified_time": "2025-11-15T10:30:00Z"
                },
                {
                    "name": "config",
                    "path": "config",
                    "type": "directory",
                    "children": [...]
                }
            ],
            "total_files": 15,
            "total_size": 102400
        }
    """
    from library.services.ansible_inventory_service import AnsibleInventoryService
    from pathlib import Path
    import os
    from datetime import datetime
    
    build = self.get_object()
    
    # 1. 檢查 workspace 是否已存儲
    if not build.is_workspace_stored:
        return Response({
            'success': False,
            'error': '該 Build 的 workspace 尚未存儲到 NAS'
        }, status=status.HTTP_404_NOT_FOUND)
    
    # 2. 主機名稱固定為 job_name
    job_name = build.job.name
    host_name = job_name  # 主機名與 Job Name 相同
    
    # 3. 從 inventory 讀取 testcase_set 參數
    inventory_path = Path(build.artifacts_path) / 'inventory' / 'hosts'
    
    if not inventory_path.exists():
        return Response({
            'success': False,
            'error': '找不到 inventory 檔案',
            'message': '該 Build 沒有 inventory/hosts 檔案'
        }, status=status.HTTP_404_NOT_FOUND)
    
    try:
        # 使用 AnsibleInventoryService 解析 inventory
        service = AnsibleInventoryService(str(inventory_path))
        result = service.get_host_config(host_name, use_cache=True)
        
        if not result['success']:
            return Response({
                'success': False,
                'error': f'找不到主機 {host_name} 的配置',
                'message': '該主機可能不存在於 inventory 中'
            }, status=status.HTTP_404_NOT_FOUND)
        
        host_config = result['config']
        testcase_set = host_config.get('testcase_set')
        
        if not testcase_set:
            return Response({
                'success': False,
                'error': '該主機沒有配置 testcase_set 參數',
                'message': f'主機 {host_name} 的 inventory 中缺少 testcase_set 欄位'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # 4. 構建測試案例目錄路徑
        workspace_path = Path(build.workspace_path)
        testcase_path = workspace_path / testcase_set
        
        if not testcase_path.exists():
            return Response({
                'success': False,
                'error': f'測試案例目錄不存在: {testcase_set}',
                'message': f'workspace 中找不到 {testcase_set} 目錄'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # 5. 遞迴列出目錄內容
        def list_directory(path, base_path, max_depth=3, current_depth=0):
            """遞迴列出目錄內容（帶深度限制）"""
            if current_depth >= max_depth:
                return []
            
            items = []
            try:
                for item in sorted(path.iterdir()):
                    # 跳過隱藏檔案和常見的排除目錄
                    if item.name.startswith('.') or item.name in ['__pycache__', 'node_modules', '.git']:
                        continue
                    
                    relative_path = item.relative_to(base_path)
                    
                    if item.is_file():
                        stat_info = item.stat()
                        items.append({
                            'name': item.name,
                            'path': str(relative_path),
                            'type': 'file',
                            'size': stat_info.st_size,
                            'extension': item.suffix,
                            'modified_time': datetime.fromtimestamp(stat_info.st_mtime).isoformat()
                        })
                    elif item.is_dir():
                        children = list_directory(item, base_path, max_depth, current_depth + 1)
                        items.append({
                            'name': item.name,
                            'path': str(relative_path),
                            'type': 'directory',
                            'children': children
                        })
            except PermissionError:
                logger.warning(f"Permission denied: {path}")
            
            return items
        
        files = list_directory(testcase_path, testcase_path, max_depth=3)
        
        # 6. 計算統計資訊
        def count_files_and_size(items):
            """計算檔案數量和總大小"""
            total_files = 0
            total_size = 0
            
            for item in items:
                if item['type'] == 'file':
                    total_files += 1
                    total_size += item['size']
                elif item['type'] == 'directory' and 'children' in item:
                    child_files, child_size = count_files_and_size(item['children'])
                    total_files += child_files
                    total_size += child_size
            
            return total_files, total_size
        
        total_files, total_size = count_files_and_size(files)
        
        return Response({
            'success': True,
            'build_id': build.id,
            'build_number': build.build_number,
            'job_name': job_name,
            'host_name': host_name,
            'testcase_set': testcase_set,
            'testcase_path': str(testcase_path),
            'files': files,
            'total_files': total_files,
            'total_size': total_size,
            'cached': result.get('cached', False)
        })
        
    except Exception as e:
        logger.error(f"獲取測試案例檔案失敗: {e}", exc_info=True)
        return Response({
            'success': False,
            'error': str(e),
            'message': '獲取測試案例檔案失敗'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
```

---

## 🎨 前端實現

### 1. 新增 Service 方法

**位置**：`frontend/src/services/jenkinsService.js`

```javascript
/**
 * 獲取 Build 的測試案例檔案列表
 * @param {number} buildId - Build ID
 * @returns {Promise} API 響應
 */
export const getBuildTestCaseFiles = async (buildId) => {
    try {
        const response = await axios.get(`/api/jenkins-builds/${buildId}/test-case-files/`);
        return response.data;
    } catch (error) {
        console.error('獲取測試案例檔案失敗:', error);
        throw error;
    }
};
```

---

### 2. 新增 TestCaseFilesDrawer 組件

**位置**：`frontend/src/components/TestCaseFilesDrawer.js`

```javascript
import React, { useState, useEffect } from 'react';
import {
    Drawer,
    Descriptions,
    Tree,
    Tag,
    Space,
    Alert,
    Spin,
    Empty,
    Button,
    Tooltip,
    Typography,
} from 'antd';
import {
    ExperimentOutlined,
    FileOutlined,
    FolderOutlined,
    ReloadOutlined,
    InfoCircleOutlined,
} from '@ant-design/icons';
import { getBuildTestCaseFiles } from '../services/jenkinsService';

const { Text } = Typography;

/**
 * 測試案例檔案 Drawer 組件
 * 
 * Props:
 * - visible: boolean - 是否顯示
 * - buildId: number - Build ID
 * - buildNumber: number - Build 編號
 * - jobName: string - Job 名稱
 * - onClose: function - 關閉回調
 */
export const TestCaseFilesDrawer = ({ visible, buildId, buildNumber, jobName, onClose }) => {
    const [loading, setLoading] = useState(false);
    const [data, setData] = useState(null);
    const [expandedKeys, setExpandedKeys] = useState([]);

    // 載入測試案例檔案
    const loadTestCaseFiles = async () => {
        if (!buildId) return;

        setLoading(true);
        try {
            const result = await getBuildTestCaseFiles(buildId);
            setData(result);
            
            // 自動展開第一層
            if (result.success && result.files) {
                const firstLevelKeys = result.files
                    .filter(item => item.type === 'directory')
                    .map(item => item.path);
                setExpandedKeys(firstLevelKeys);
            }
        } catch (error) {
            console.error('載入測試案例檔案失敗:', error);
            setData({
                success: false,
                error: error.message,
            });
        } finally {
            setLoading(false);
        }
    };

    // 當 Drawer 打開時載入資料
    useEffect(() => {
        if (visible && buildId) {
            loadTestCaseFiles();
        }
    }, [visible, buildId]);

    // 重新載入
    const handleReload = () => {
        loadTestCaseFiles();
    };

    // 將檔案列表轉換為 Tree 資料格式
    const convertToTreeData = (files) => {
        return files.map(item => {
            const node = {
                key: item.path,
                title: (
                    <Space>
                        {item.type === 'directory' ? (
                            <FolderOutlined style={{ color: '#faad14' }} />
                        ) : (
                            <FileOutlined style={{ color: '#1890ff' }} />
                        )}
                        <Text>{item.name}</Text>
                        {item.type === 'file' && (
                            <Text type="secondary" style={{ fontSize: 12 }}>
                                ({formatFileSize(item.size)})
                            </Text>
                        )}
                    </Space>
                ),
                isLeaf: item.type === 'file',
            };

            if (item.type === 'directory' && item.children) {
                node.children = convertToTreeData(item.children);
            }

            return node;
        });
    };

    // 格式化檔案大小
    const formatFileSize = (bytes) => {
        if (bytes < 1024) return `${bytes} B`;
        if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
        return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
    };

    return (
        <Drawer
            title={
                <Space>
                    <ExperimentOutlined />
                    <span>測試案例檔案</span>
                    {data?.cached && (
                        <Tag color="green" icon={<InfoCircleOutlined />}>
                            從快取載入
                        </Tag>
                    )}
                </Space>
            }
            width={900}
            open={visible}
            onClose={onClose}
            extra={
                <Button
                    icon={<ReloadOutlined />}
                    onClick={handleReload}
                    loading={loading}
                >
                    重新載入
                </Button>
            }
        >
            {loading ? (
                <div style={{ textAlign: 'center', padding: '50px' }}>
                    <Spin size="large" tip="正在載入測試案例檔案..." />
                </div>
            ) : data?.success === false ? (
                <Alert
                    message="載入失敗"
                    description={data.error || '無法獲取測試案例檔案'}
                    type="error"
                    showIcon
                />
            ) : (
                <>
                    {/* Build 和測試案例資訊 */}
                    <Descriptions bordered size="small" column={2} style={{ marginBottom: 24 }}>
                        <Descriptions.Item label="Job 名稱">{jobName}</Descriptions.Item>
                        <Descriptions.Item label="Build 編號">#{buildNumber}</Descriptions.Item>
                        <Descriptions.Item label="主機名稱">{data?.host_name}</Descriptions.Item>
                        <Descriptions.Item label="測試案例集">
                            <Tag color="blue">{data?.testcase_set}</Tag>
                        </Descriptions.Item>
                        <Descriptions.Item label="檔案數量">
                            {data?.total_files} 個
                        </Descriptions.Item>
                        <Descriptions.Item label="總大小">
                            {formatFileSize(data?.total_size || 0)}
                        </Descriptions.Item>
                    </Descriptions>

                    {/* 檔案樹狀結構 */}
                    {data?.files && data.files.length > 0 ? (
                        <div
                            style={{
                                border: '1px solid #d9d9d9',
                                borderRadius: 4,
                                padding: 16,
                                backgroundColor: '#fafafa',
                            }}
                        >
                            <Tree
                                treeData={convertToTreeData(data.files)}
                                expandedKeys={expandedKeys}
                                onExpand={setExpandedKeys}
                                showLine
                                defaultExpandAll={false}
                            />
                        </div>
                    ) : (
                        <Empty description="沒有測試案例檔案" />
                    )}

                    {/* 測試案例路徑 */}
                    <Alert
                        message="測試案例路徑"
                        description={
                            <Text code copyable style={{ wordBreak: 'break-all' }}>
                                {data?.testcase_path}
                            </Text>
                        }
                        type="info"
                        showIcon
                        style={{ marginTop: 24 }}
                    />
                </>
            )}
        </Drawer>
    );
};
```

---

### 3. 在 RVTAnalysisPage 中整合

**位置**：`frontend/src/pages/RVTAnalysisPage.js`

#### 3.1 引入組件和 State

```javascript
import { TestCaseFilesDrawer } from '../components/TestCaseFilesDrawer';

// 在 State 管理區域新增
const [testCaseFilesDrawer, setTestCaseFilesDrawer] = useState({
    visible: false,
    buildId: null,
    buildNumber: null,
    jobName: null,
});
```

#### 3.2 新增處理函數

```javascript
// 查看測試案例檔案
const handleViewTestCaseFiles = (record) => {
    // record 是 Build 行資料
    setTestCaseFilesDrawer({
        visible: true,
        buildId: record.build_id,
        buildNumber: record.build_number,
        jobName: record.job_name,
    });
};
```

#### 3.3 在 Table Columns 中新增按鈕

```javascript
{
    title: '操作',
    key: 'action',
    width: 350,
    render: (_, record) => {
        if (record.type === 'build') {
            return (
                <Space size="small">
                    {/* 現有按鈕... */}
                    
                    {/* 新增：測試案例按鈕 */}
                    <Tooltip title="查看測試案例檔案">
                        <Button
                            size="small"
                            icon={<ExperimentOutlined />}
                            onClick={() => handleViewTestCaseFiles(record)}
                        >
                            測試案例
                        </Button>
                    </Tooltip>
                    
                    {/* 其他按鈕... */}
                </Space>
            );
        }
        return null;
    },
},
```

#### 3.4 渲染 TestCaseFilesDrawer

```javascript
{/* 測試案例檔案 Drawer */}
<TestCaseFilesDrawer
    visible={testCaseFilesDrawer.visible}
    buildId={testCaseFilesDrawer.buildId}
    buildNumber={testCaseFilesDrawer.buildNumber}
    jobName={testCaseFilesDrawer.jobName}
    onClose={() => setTestCaseFilesDrawer({ 
        visible: false, 
        buildId: null, 
        buildNumber: null, 
        jobName: null 
    })}
/>
```

---

## 🎨 UI 設計說明

### Drawer 佈局

```
╔════════════════════════════════════════════════════╗
║  🧪 測試案例檔案                    [重新載入]     ║
╠════════════════════════════════════════════════════╣
║                                                    ║
║  【Build 和測試案例資訊】                          ║
║  ┌──────────────────────────────────────────┐     ║
║  │ Job 名稱：Test-KVM01                     │     ║
║  │ Build 編號：#148                         │     ║
║  │ 主機名稱：Test-KVM01                     │     ║
║  │ 測試案例集：testcases_demo               │     ║
║  │ 檔案數量：15 個                          │     ║
║  │ 總大小：128.5 KB                         │     ║
║  └──────────────────────────────────────────┘     ║
║                                                    ║
║  【檔案樹狀結構】                                  ║
║  ┌──────────────────────────────────────────┐     ║
║  │ 📁 config/                               │     ║
║  │   └── 📄 pytest.ini (2.1 KB)            │     ║
║  │ 📁 tests/                                │     ║
║  │   ├── 📄 test_basic.py (5.4 KB)         │     ║
║  │   ├── 📄 test_advanced.py (8.2 KB)      │     ║
║  │   └── 📄 test_performance.py (12.3 KB)  │     ║
║  │ 📄 requirements.txt (1.5 KB)            │     ║
║  │ 📄 README.md (3.2 KB)                   │     ║
║  └──────────────────────────────────────────┘     ║
║                                                    ║
║  【測試案例路徑】                                  ║
║  /mnt/mdt/.../workspace/testcases_demo           ║
║                                                    ║
╚════════════════════════════════════════════════════╝
```

---

## 📊 資料流程圖

```
用戶點擊「測試案例」按鈕
         ↓
setTestCaseFilesDrawer({ visible: true, ... })
         ↓
TestCaseFilesDrawer 組件掛載
         ↓
useEffect 觸發 loadTestCaseFiles()
         ↓
API 調用：GET /api/jenkins-builds/{id}/test-case-files/
         ↓
後端處理：
  1. 檢查 workspace 是否已存儲
  2. 主機名 = job_name（固定）
  3. 從 inventory 讀取該主機的 testcase_set
  4. 定位 workspace/{testcase_set}/ 目錄
  5. 遞迴列出目錄內容（最深 3 層）
  6. 計算檔案數量和總大小
         ↓
返回結果：
{
  success: true,
  host_name: "Test-KVM01",
  testcase_set: "testcases_demo",
  files: [
    { name: "test_basic.py", type: "file", size: 5400, ... },
    { name: "config", type: "directory", children: [...] }
  ],
  total_files: 15,
  total_size: 131584
}
         ↓
前端渲染：
  - Descriptions 顯示資訊
  - Tree 顯示檔案樹狀結構
  - Alert 顯示路徑
```

---

## 🔧 技術細節

### 1. 主機名稱固定規則

```python
# 主機名稱直接使用 job_name
host_name = build.job.name

# 例如：
# Job Name: Test-KVM01  →  主機名: Test-KVM01
# Job Name: SAF3101_KVM03  →  主機名: SAF3101_KVM03
```

### 2. 測試案例目錄定位

```python
# 路徑構建
workspace_path = Path(build.workspace_path)  # /mnt/.../148/workspace
testcase_path = workspace_path / testcase_set  # /mnt/.../148/workspace/testcases_demo
```

### 3. 目錄遞迴列出規則

- **最大深度**：3 層（避免過深導致效能問題）
- **排除規則**：
  - 隱藏檔案（`.` 開頭）
  - `__pycache__`
  - `node_modules`
  - `.git`
- **排序**：檔案名稱排序

### 4. 檔案資訊

每個檔案/目錄返回：
- `name`：檔案名稱
- `path`：相對路徑
- `type`：`file` 或 `directory`
- `size`：檔案大小（bytes）
- `extension`：副檔名（檔案）
- `modified_time`：修改時間
- `children`：子項目（目錄）

---

## 🧪 測試計劃

### 後端測試

#### 單元測試

```python
# backend/api/tests/test_jenkins_build_testcase_files.py

from django.test import TestCase
from rest_framework.test import APIClient
from api.models import JenkinsJob, JenkinsBuild, JenkinsServer

class TestJenkinsBuildTestCaseFilesAPI(TestCase):
    
    def setUp(self):
        self.client = APIClient()
        
        # 創建測試資料
        self.server = JenkinsServer.objects.create(
            name='Test Server',
            url='http://10.252.170.171:8080'
        )
        self.job = JenkinsJob.objects.create(
            name='Test-KVM01',
            server=self.server
        )
        self.build = JenkinsBuild.objects.create(
            job=self.job,
            build_number=148,
            is_workspace_stored=True,
            workspace_path='/mnt/mdt/.../148/workspace',
            artifacts_path='/mnt/mdt/.../148/artifacts'
        )
    
    def test_get_test_case_files_success(self):
        """測試成功獲取測試案例檔案"""
        response = self.client.get(
            f'/api/jenkins-builds/{self.build.id}/test-case-files/'
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['host_name'], 'Test-KVM01')
        self.assertIn('testcase_set', response.data)
        self.assertIn('files', response.data)
    
    def test_get_test_case_files_no_workspace(self):
        """測試 workspace 未存儲"""
        self.build.is_workspace_stored = False
        self.build.save()
        
        response = self.client.get(
            f'/api/jenkins-builds/{self.build.id}/test-case-files/'
        )
        
        self.assertEqual(response.status_code, 404)
        self.assertFalse(response.data['success'])
    
    def test_get_test_case_files_no_inventory(self):
        """測試沒有 inventory 檔案"""
        self.build.artifacts_path = '/tmp/non_existent'
        self.build.save()
        
        response = self.client.get(
            f'/api/jenkins-builds/{self.build.id}/test-case-files/'
        )
        
        self.assertEqual(response.status_code, 404)
        self.assertIn('inventory', response.data['error'].lower())
    
    def test_get_test_case_files_no_testcase_set(self):
        """測試主機沒有 testcase_set 參數"""
        # 這個需要實際的 inventory 檔案測試
        pass
```

---

### 前端測試

#### 手動測試步驟

1. **訪問 RVT 分析頁面**
   - URL: `http://localhost/rvt-analytics?tab=details`

2. **展開一個 Job**
   - 選擇 `Test-KVM01`
   - 查看 Build 列表

3. **點擊「測試案例」按鈕**
   - 觀察 Drawer 是否正確打開
   - 確認 loading 動畫顯示

4. **檢查資料顯示**
   - ✅ Build 和測試案例資訊正確
   - ✅ 主機名稱 = Job 名稱
   - ✅ testcase_set 正確顯示
   - ✅ 檔案樹狀結構完整
   - ✅ 檔案大小、數量統計正確

5. **測試樹狀結構互動**
   - 展開/收起目錄
   - 查看檔案資訊

6. **測試重新載入功能**
   - 點擊「重新載入」按鈕
   - 確認資料重新載入

7. **測試錯誤處理**
   - 測試沒有 workspace 的 Build
   - 測試沒有 inventory 的 Build
   - 測試沒有 testcase_set 的主機

---

## 📁 檔案結構

```
backend/
├── api/
│   ├── views/
│   │   └── jenkins.py                          # 新增 get_test_case_files() 方法
│   └── tests/
│       └── test_jenkins_build_testcase_files.py  # 新增測試

frontend/
├── src/
│   ├── components/
│   │   └── TestCaseFilesDrawer.js              # 新增組件
│   ├── pages/
│   │   └── RVTAnalysisPage.js                  # 修改：新增按鈕和 Drawer
│   └── services/
│       └── jenkinsService.js                   # 新增 getBuildTestCaseFiles() 方法

docs/
└── development/
    └── JENKINS_BUILD_TESTCASE_FILES_DISPLAY_PLAN.md  # 本文件
```

---

## 🚀 實施步驟

### Phase 1: 後端開發（2-3 小時）

1. ✅ 在 `JenkinsBuildViewSet` 中新增 `get_test_case_files()` 方法
2. ✅ 實現目錄遞迴列出邏輯
3. ✅ 實現統計邏輯（檔案數量、總大小）
4. ✅ 編寫單元測試
5. ✅ 測試 API 端點

### Phase 2: 前端開發（3-4 小時）

1. ✅ 建立 `TestCaseFilesDrawer.js` 組件
2. ✅ 實現樹狀結構顯示
3. ✅ 在 `jenkinsService.js` 中新增方法
4. ✅ 修改 `RVTAnalysisPage.js`
5. ✅ 測試前端功能

### Phase 3: 整合測試（1-2 小時）

1. ✅ 端到端測試
2. ✅ 錯誤處理測試
3. ✅ UI/UX 優化

### Phase 4: 文件和部署（1 小時）

1. ✅ 更新 API 文件
2. ✅ 更新使用說明
3. ✅ 部署到測試環境

**總計**：7-10 小時

---

## 📊 資料範例

### API 響應範例

#### 成功（有測試案例檔案）

```json
{
  "success": true,
  "build_id": 123,
  "build_number": 148,
  "job_name": "Test-KVM01",
  "host_name": "Test-KVM01",
  "testcase_set": "testcases_demo",
  "testcase_path": "/mnt/mdt/.../148/workspace/testcases_demo",
  "files": [
    {
      "name": "config",
      "path": "config",
      "type": "directory",
      "children": [
        {
          "name": "pytest.ini",
          "path": "config/pytest.ini",
          "type": "file",
          "size": 2150,
          "extension": ".ini",
          "modified_time": "2025-11-15T10:30:00Z"
        }
      ]
    },
    {
      "name": "tests",
      "path": "tests",
      "type": "directory",
      "children": [
        {
          "name": "test_basic.py",
          "path": "tests/test_basic.py",
          "type": "file",
          "size": 5400,
          "extension": ".py",
          "modified_time": "2025-11-15T09:20:00Z"
        },
        {
          "name": "test_advanced.py",
          "path": "tests/test_advanced.py",
          "type": "file",
          "size": 8200,
          "extension": ".py",
          "modified_time": "2025-11-15T09:25:00Z"
        }
      ]
    },
    {
      "name": "requirements.txt",
      "path": "requirements.txt",
      "type": "file",
      "size": 1500,
      "extension": ".txt",
      "modified_time": "2025-11-14T16:00:00Z"
    }
  ],
  "total_files": 15,
  "total_size": 131584,
  "cached": true
}
```

#### 錯誤（workspace 未存儲）

```json
{
  "success": false,
  "error": "該 Build 的 workspace 尚未存儲到 NAS"
}
```

#### 錯誤（沒有 testcase_set）

```json
{
  "success": false,
  "error": "該主機沒有配置 testcase_set 參數",
  "message": "主機 Test-KVM01 的 inventory 中缺少 testcase_set 欄位"
}
```

---

## 🎯 預期效果

### 功能效果

1. **自動定位主機**
   - 主機名稱 = Job 名稱，無需選擇
   - 簡化用戶操作

2. **顯示測試案例內容**
   - 列出測試案例目錄下的所有檔案
   - 樹狀結構清晰展示

3. **統計資訊**
   - 檔案數量
   - 總大小
   - 檔案類型分佈

4. **快速定位**
   - 顯示完整路徑
   - 可複製路徑

### UI 效果

- 🎨 清晰的樹狀結構
- 📊 直觀的統計資訊
- 🔍 完整的檔案列表
- ⚡ 流暢的互動體驗

---

## ⚠️ 注意事項

### 1. 前置條件

- **必須先存儲 workspace**：Build 必須已執行 `store_workspace`
- **必須有 inventory 檔案**：需要從 inventory 讀取 testcase_set
- **主機名稱必須與 Job Name 一致**：這是固定規則

### 2. 測試案例目錄結構

需要確認實際的測試案例目錄結構：
- 測試案例是否在 workspace 下？
- 目錄名稱是否與 testcase_set 一致？
- 是否有標準的目錄結構？

### 3. 效能考量

- **目錄深度限制**：最多遞迴 3 層
- **檔案數量限制**：如果檔案過多，考慮分頁或懶載入
- **大檔案處理**：不載入檔案內容，只顯示元資訊

---

## 📝 後續優化

### 短期優化

1. **檔案預覽**
   - 點擊檔案可預覽內容
   - 支援 .py, .txt, .md 等文字檔案

2. **檔案下載**
   - 支援單個檔案下載
   - 支援整個目錄打包下載

### 長期優化

1. **測試案例執行狀態**
   - 標記哪些測試案例被執行過
   - 顯示測試結果（成功/失敗）

2. **測試案例對比**
   - 對比不同 Build 的測試案例差異
   - 追蹤測試案例變更歷史

---

## ✅ 驗收標準

### 後端

- [ ] API 端點正常運作
- [ ] 主機名稱固定為 job_name
- [ ] 正確讀取 testcase_set 參數
- [ ] 正確列出測試案例目錄內容
- [ ] 錯誤處理完善
- [ ] 日誌記錄正確

### 前端

- [ ] Drawer 正確顯示
- [ ] 樹狀結構互動流暢
- [ ] 資料載入正確
- [ ] 統計資訊準確
- [ ] 錯誤提示友善
- [ ] UI 美觀

### 整合

- [ ] 端到端測試通過
- [ ] 效能符合要求
- [ ] 文件完整

---

## 🔄 與現有功能整合

### 與 Ansible Inventory 功能整合

- 利用現有的 `AnsibleInventoryService`
- 使用快取機制（7 天）
- 統一錯誤處理

### 與 Workspace 存儲功能整合

- 依賴 `is_workspace_stored` 欄位
- 使用 `workspace_path` 欄位
- 確保 workspace 已存儲才能顯示測試案例

---

## 📅 時間規劃

| 階段            | 預估時間 | 優先級 |
| --------------- | -------- | ------ |
| Phase 1: 後端   | 2-3 小時 | 🔴 高   |
| Phase 2: 前端   | 3-4 小時 | 🔴 高   |
| Phase 3: 測試   | 1-2 小時 | 🟡 中   |
| Phase 4: 部署   | 1 小時   | 🟡 中   |
| **總計**        | **7-10 小時** |   |

---

## 📚 相關文件

- [Ansible Inventory 後端實現規劃](../features/ansible-inventory/BACKEND_IMPLEMENTATION_PLAN.md)
- [Jenkins Workspace 自動存儲到 NAS](../features/jenkins-workspace-storage/README.md)
- [Jenkins Build 測試案例顯示規劃（舊版）](./JENKINS_BUILD_TESTCASE_DISPLAY_PLAN.md)

---

**規劃日期**：2025-11-15  
**規劃者**：GitHub Copilot  
**版本**：v2.0.0  
**狀態**：✅ 規劃完成，待確認執行

---

## 🔍 關鍵差異說明

### 與舊版規劃的差異

| 項目             | 舊版規劃                      | 新版規劃（本文件）            |
| ---------------- | ----------------------------- | ----------------------------- |
| 主機選擇         | 需要選擇主機                  | **固定為 job_name**           |
| 顯示內容         | 測試案例集名稱和使用的主機    | **測試案例目錄下的檔案列表**  |
| 資料來源         | inventory 的 testcase_set 欄位 | **workspace 目錄內容**        |
| UI 展示          | 表格顯示測試案例分佈          | **樹狀結構顯示檔案**          |
| API 端點         | `/test-cases/`                | **`/test-case-files/`**       |
| 組件名稱         | `TestCaseDrawer`              | **`TestCaseFilesDrawer`**     |

### 新版規劃的優勢

1. ✅ **更直觀**：直接顯示測試檔案，而非只顯示測試案例集名稱
2. ✅ **更簡單**：主機固定為 job_name，無需選擇
3. ✅ **更實用**：可以看到測試案例的具體內容和結構
4. ✅ **更完整**：顯示檔案大小、修改時間等元資訊
