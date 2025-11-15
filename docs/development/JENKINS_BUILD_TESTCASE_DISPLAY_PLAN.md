# Jenkins Build 測試案例顯示規劃

## 📋 需求說明

在 RVT 分析頁面中，針對各個 Build 的配置資訊，需要能夠：
1. **從 NAS 的 inventory 檔案中讀取測試案例資訊**（`testcase_set` 欄位）
2. **在前端獨立顯示一個 Block 展示測試案例**
3. **可以分辨出每個 Build 使用的測試案例集合**
4. **先進行規劃，不立即執行**

---

## 🔍 現況分析

### Inventory 檔案結構

根據已有的文件，inventory 檔案位於：
```
/mnt/mdt/Team/PQ1-3/tool/jenkins_test_storage/{server_ip}/{job_name}/{build_number}/artifacts/inventory/hosts
```

檔案內容範例：
```ini
[PQ1_3]
Test-KVM01 ansible_host=10.250.71.22 device_number=PC-SSD-4632 sample_number=SM2703AB-02003 uart_id=KVM01 macaddress=CC:28:AA:86:C3:7F testcase_set=testcases_demo
Test-KVM07 ansible_host=10.250.71.23 device_number=PC-SSD-4633 sample_number=SM2703AB-02004 uart_id=KVM07 macaddress=CC:28:AA:86:C3:80 testcase_set=testcases_production
```

**關鍵欄位**：`testcase_set` - 代表該主機使用的測試案例集

---

## 🎯 解決方案設計

### 方案概述

在 RVT 分析頁面的每個 Build 行，新增一個「測試案例」按鈕，點擊後顯示該 Build 使用的所有測試案例集合。

### 架構設計

```
前端 (RVTAnalysisPage.js)
    ↓
    查看測試案例按鈕
    ↓
    打開 TestCaseDrawer (新組件)
    ↓
API 調用: GET /api/jenkins-builds/{id}/test-cases/
    ↓
後端 (JenkinsBuildViewSet)
    ↓
    1. 檢查 Build 是否已存儲 artifacts
    2. 定位 inventory 檔案路徑
    3. 使用 AnsibleInventoryService 解析
    4. 提取所有主機的 testcase_set 欄位
    5. 統計並返回結果
    ↓
前端顯示測試案例統計
```

---

## 📦 後端實現

### 1. 新增 API 端點

**位置**：`backend/api/views/jenkins.py` - `JenkinsBuildViewSet`

```python
@action(detail=True, methods=['get'], url_path='test-cases')
def get_test_cases(self, request, pk=None):
    """
    獲取 Build 的測試案例資訊
    
    GET /api/jenkins-builds/{id}/test-cases/
    
    Returns:
        {
            "success": true,
            "build_id": 123,
            "build_number": 148,
            "job_name": "Test-KVM01",
            "has_inventory": true,
            "test_cases": [
                {
                    "testcase_set": "testcases_demo",
                    "hosts": ["Test-KVM01", "Test-KVM03"],
                    "host_count": 2
                },
                {
                    "testcase_set": "testcases_production",
                    "hosts": ["Test-KVM07"],
                    "host_count": 1
                }
            ],
            "total_hosts": 3,
            "total_test_sets": 2,
            "hosts_without_testcase": []
        }
    """
    from library.services.ansible_inventory_service import AnsibleInventoryService
    from pathlib import Path
    
    build = self.get_object()
    
    # 1. 檢查是否已存儲 artifacts
    if not build.is_artifacts_stored:
        return Response({
            'success': False,
            'error': '該 Build 的 artifacts 尚未存儲到 NAS'
        }, status=status.HTTP_404_NOT_FOUND)
    
    # 2. 定位 inventory 檔案
    inventory_path = Path(build.artifacts_path) / 'inventory' / 'hosts'
    
    if not inventory_path.exists():
        return Response({
            'success': True,
            'build_id': build.id,
            'build_number': build.build_number,
            'job_name': build.job.name,
            'has_inventory': False,
            'message': '該 Build 沒有 inventory 檔案'
        })
    
    try:
        # 3. 使用 AnsibleInventoryService 解析
        service = AnsibleInventoryService(str(inventory_path))
        result = service.get_full_inventory(use_cache=True)
        
        if not result['success']:
            return Response({
                'success': False,
                'error': result.get('error', '解析 inventory 失敗')
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        inventory_data = result['data']
        hostvars = inventory_data.get('_meta', {}).get('hostvars', {})
        
        # 4. 提取測試案例資訊
        test_cases_map = {}  # {testcase_set: [hosts]}
        hosts_without_testcase = []
        
        for hostname, vars in hostvars.items():
            testcase_set = vars.get('testcase_set')
            
            if testcase_set:
                if testcase_set not in test_cases_map:
                    test_cases_map[testcase_set] = []
                test_cases_map[testcase_set].append(hostname)
            else:
                hosts_without_testcase.append(hostname)
        
        # 5. 格式化結果
        test_cases = [
            {
                'testcase_set': testcase_set,
                'hosts': sorted(hosts),
                'host_count': len(hosts)
            }
            for testcase_set, hosts in sorted(test_cases_map.items())
        ]
        
        return Response({
            'success': True,
            'build_id': build.id,
            'build_number': build.build_number,
            'job_name': build.job.name,
            'has_inventory': True,
            'test_cases': test_cases,
            'total_hosts': len(hostvars),
            'total_test_sets': len(test_cases_map),
            'hosts_without_testcase': sorted(hosts_without_testcase),
            'cached': result.get('cached', False)
        })
        
    except Exception as e:
        logger.error(f"獲取測試案例失敗: {e}", exc_info=True)
        return Response({
            'success': False,
            'error': str(e),
            'message': '獲取測試案例失敗'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
```

---

## 🎨 前端實現

### 1. 新增 Service 方法

**位置**：`frontend/src/services/jenkinsService.js`（或建立新檔案）

```javascript
import axios from 'axios';

/**
 * 獲取 Build 的測試案例資訊
 * @param {number} buildId - Build ID
 * @returns {Promise} API 響應
 */
export const getBuildTestCases = async (buildId) => {
    try {
        const response = await axios.get(`/api/jenkins-builds/${buildId}/test-cases/`);
        return response.data;
    } catch (error) {
        console.error('獲取測試案例失敗:', error);
        throw error;
    }
};
```

---

### 2. 新增 TestCaseDrawer 組件

**位置**：`frontend/src/components/TestCaseDrawer.js`

```javascript
import React, { useState, useEffect } from 'react';
import {
    Drawer,
    Descriptions,
    Table,
    Tag,
    Space,
    Alert,
    Spin,
    Empty,
    Button,
    Tooltip,
} from 'antd';
import {
    ExperimentOutlined,
    InfoCircleOutlined,
    ReloadOutlined,
} from '@ant-design/icons';
import { getBuildTestCases } from '../services/jenkinsService';

/**
 * 測試案例 Drawer 組件
 * 
 * Props:
 * - visible: boolean - 是否顯示
 * - buildId: number - Build ID
 * - buildNumber: number - Build 編號
 * - jobName: string - Job 名稱
 * - onClose: function - 關閉回調
 */
export const TestCaseDrawer = ({ visible, buildId, buildNumber, jobName, onClose }) => {
    const [loading, setLoading] = useState(false);
    const [data, setData] = useState(null);

    // 載入測試案例資訊
    const loadTestCases = async () => {
        if (!buildId) return;

        setLoading(true);
        try {
            const result = await getBuildTestCases(buildId);
            setData(result);
        } catch (error) {
            console.error('載入測試案例失敗:', error);
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
            loadTestCases();
        }
    }, [visible, buildId]);

    // 重新載入
    const handleReload = () => {
        loadTestCases();
    };

    // Table 欄位定義
    const columns = [
        {
            title: '測試案例集',
            dataIndex: 'testcase_set',
            key: 'testcase_set',
            width: 200,
            render: (text) => (
                <Space>
                    <ExperimentOutlined style={{ color: '#1890ff' }} />
                    <span style={{ fontWeight: 500 }}>{text}</span>
                </Space>
            ),
        },
        {
            title: '主機數量',
            dataIndex: 'host_count',
            key: 'host_count',
            width: 100,
            align: 'center',
            render: (count) => <Tag color="blue">{count} 台</Tag>,
        },
        {
            title: '主機列表',
            dataIndex: 'hosts',
            key: 'hosts',
            render: (hosts) => (
                <Space wrap>
                    {hosts.map((host) => (
                        <Tag key={host} color="geekblue">
                            {host}
                        </Tag>
                    ))}
                </Space>
            ),
        },
    ];

    return (
        <Drawer
            title={
                <Space>
                    <ExperimentOutlined />
                    <span>測試案例資訊</span>
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
                    <Spin size="large" tip="正在載入測試案例資訊..." />
                </div>
            ) : data?.success === false ? (
                <Alert
                    message="載入失敗"
                    description={data.error || '無法獲取測試案例資訊'}
                    type="error"
                    showIcon
                />
            ) : !data?.has_inventory ? (
                <Empty
                    description="該 Build 沒有 Inventory 檔案"
                    image={Empty.PRESENTED_IMAGE_SIMPLE}
                />
            ) : (
                <>
                    {/* Build 基本資訊 */}
                    <Descriptions bordered size="small" column={2} style={{ marginBottom: 24 }}>
                        <Descriptions.Item label="Job 名稱">{jobName}</Descriptions.Item>
                        <Descriptions.Item label="Build 編號">#{buildNumber}</Descriptions.Item>
                        <Descriptions.Item label="總主機數">
                            {data.total_hosts} 台
                        </Descriptions.Item>
                        <Descriptions.Item label="測試案例集數量">
                            {data.total_test_sets} 個
                        </Descriptions.Item>
                    </Descriptions>

                    {/* 警告：主機沒有測試案例 */}
                    {data.hosts_without_testcase?.length > 0 && (
                        <Alert
                            message="部分主機未配置測試案例"
                            description={
                                <div>
                                    以下主機沒有 <code>testcase_set</code> 欄位：
                                    <div style={{ marginTop: 8 }}>
                                        {data.hosts_without_testcase.map((host) => (
                                            <Tag key={host} color="warning" style={{ marginBottom: 4 }}>
                                                {host}
                                            </Tag>
                                        ))}
                                    </div>
                                </div>
                            }
                            type="warning"
                            showIcon
                            style={{ marginBottom: 24 }}
                        />
                    )}

                    {/* 測試案例表格 */}
                    {data.test_cases?.length > 0 ? (
                        <Table
                            columns={columns}
                            dataSource={data.test_cases}
                            rowKey="testcase_set"
                            pagination={false}
                            size="small"
                        />
                    ) : (
                        <Empty description="沒有測試案例資訊" />
                    )}
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
import { TestCaseDrawer } from '../components/TestCaseDrawer';

// 在 State 管理區域新增
const [testCaseDrawer, setTestCaseDrawer] = useState({
    visible: false,
    buildId: null,
    buildNumber: null,
    jobName: null,
});
```

#### 3.2 新增處理函數

```javascript
// 查看測試案例
const handleViewTestCases = (record) => {
    // record 是 Build 行資料
    setTestCaseDrawer({
        visible: true,
        buildId: record.build_id,
        buildNumber: record.build_number,
        jobName: record.job_name,
    });
};
```

#### 3.3 在 Table Columns 中新增按鈕

在 `columns` 定義的 `操作` 欄位中新增按鈕：

```javascript
{
    title: '操作',
    key: 'action',
    width: 300,
    render: (_, record) => {
        if (record.type === 'build') {
            return (
                <Space size="small">
                    {/* 現有按鈕... */}
                    
                    {/* 新增：測試案例按鈕 */}
                    <Tooltip title="查看測試案例">
                        <Button
                            size="small"
                            icon={<ExperimentOutlined />}
                            onClick={() => handleViewTestCases(record)}
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

#### 3.4 渲染 TestCaseDrawer

在組件返回的 JSX 中新增：

```javascript
{/* 測試案例 Drawer */}
<TestCaseDrawer
    visible={testCaseDrawer.visible}
    buildId={testCaseDrawer.buildId}
    buildNumber={testCaseDrawer.buildNumber}
    jobName={testCaseDrawer.jobName}
    onClose={() => setTestCaseDrawer({ visible: false, buildId: null, buildNumber: null, jobName: null })}
/>
```

---

## 🎨 UI 設計說明

### Drawer 佈局

```
╔════════════════════════════════════════════════════╗
║  🧪 測試案例資訊                     [重新載入]    ║
╠════════════════════════════════════════════════════╣
║                                                    ║
║  【Build 基本資訊】                                ║
║  ┌──────────────────────────────────────────┐     ║
║  │ Job 名稱：Test-KVM01                     │     ║
║  │ Build 編號：#148                         │     ║
║  │ 總主機數：3 台                           │     ║
║  │ 測試案例集數量：2 個                     │     ║
║  └──────────────────────────────────────────┘     ║
║                                                    ║
║  【測試案例列表】                                  ║
║  ┌──────────────────────────────────────────┐     ║
║  │ 測試案例集      │ 主機數量 │ 主機列表     │     ║
║  ├──────────────────────────────────────────┤     ║
║  │ testcases_demo  │ 2 台     │ Test-KVM01  │     ║
║  │                 │          │ Test-KVM03  │     ║
║  ├──────────────────────────────────────────┤     ║
║  │ testcases_prod  │ 1 台     │ Test-KVM07  │     ║
║  └──────────────────────────────────────────┘     ║
║                                                    ║
╚════════════════════════════════════════════════════╝
```

### 顏色方案

- **主色調**：藍色 (#1890ff) - 測試相關元素
- **標籤顏色**：
  - 測試案例集：geekblue
  - 主機數量：blue
  - 快取狀態：green
  - 警告：warning/orange

---

## 📊 資料流程圖

```
用戶點擊「測試案例」按鈕
         ↓
setTestCaseDrawer({ visible: true, ... })
         ↓
TestCaseDrawer 組件掛載
         ↓
useEffect 觸發 loadTestCases()
         ↓
API 調用: GET /api/jenkins-builds/{id}/test-cases/
         ↓
後端處理：
  1. 檢查 artifacts_path
  2. 定位 inventory/hosts
  3. 使用 AnsibleInventoryService 解析
  4. 提取 testcase_set 欄位
  5. 統計並分組
         ↓
返回結果：
{
  success: true,
  test_cases: [
    { testcase_set: "xxx", hosts: [...], host_count: 2 }
  ],
  total_hosts: 3,
  total_test_sets: 2,
  ...
}
         ↓
前端渲染：
  - Descriptions 顯示統計
  - Table 顯示測試案例列表
  - Alert 顯示警告（如有）
```

---

## 🔧 技術細節

### 1. 快取機制

- **利用現有的 AnsibleInventoryService 快取**
- **快取時效**：7 天
- **快取位置**：`{build_dir}/cache/ansible_inventory.json`
- **前端顯示快取狀態**：綠色 Tag 標記「從快取載入」

### 2. 錯誤處理

#### 後端錯誤場景

| 錯誤情況                  | HTTP 狀態碼 | 錯誤訊息                                  |
| ------------------------- | ----------- | ----------------------------------------- |
| Build artifacts 未存儲    | 404         | 該 Build 的 artifacts 尚未存儲到 NAS      |
| inventory 檔案不存在      | 200 (特殊)  | has_inventory: false                      |
| 解析 inventory 失敗       | 500         | 解析 inventory 失敗                       |
| 其他異常                  | 500         | 獲取測試案例失敗                          |

#### 前端錯誤處理

- **載入失敗**：顯示紅色 Alert
- **沒有 inventory**：顯示 Empty 組件
- **沒有測試案例**：顯示 Empty 組件
- **部分主機無測試案例**：顯示橙色 Alert 警告

### 3. 效能考量

- **使用快取**：避免重複解析 inventory 檔案
- **按需載入**：只有在 Drawer 打開時才載入資料
- **資料結構優化**：後端已統計好，前端直接渲染

---

## 🧪 測試計劃

### 後端測試

#### 單元測試

```python
# backend/api/tests/test_jenkins_build_testcases.py

from django.test import TestCase
from rest_framework.test import APIClient
from api.models import JenkinsJob, JenkinsBuild, JenkinsServer

class TestJenkinsBuildTestCasesAPI(TestCase):
    
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
            is_artifacts_stored=True,
            artifacts_path='/mnt/mdt/Team/PQ1-3/tool/jenkins_test_storage/10.252.170.171/Test-KVM01/148/artifacts'
        )
    
    def test_get_test_cases_success(self):
        """測試成功獲取測試案例"""
        response = self.client.get(f'/api/jenkins-builds/{self.build.id}/test-cases/')
        
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['success'])
        self.assertIn('test_cases', response.data)
    
    def test_get_test_cases_no_artifacts(self):
        """測試 Build 沒有 artifacts"""
        self.build.is_artifacts_stored = False
        self.build.save()
        
        response = self.client.get(f'/api/jenkins-builds/{self.build.id}/test-cases/')
        
        self.assertEqual(response.status_code, 404)
        self.assertFalse(response.data['success'])
    
    def test_get_test_cases_no_inventory(self):
        """測試 Build 沒有 inventory 檔案"""
        # 修改路徑指向沒有 inventory 的位置
        self.build.artifacts_path = '/tmp/non_existent_path'
        self.build.save()
        
        response = self.client.get(f'/api/jenkins-builds/{self.build.id}/test-cases/')
        
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['success'])
        self.assertFalse(response.data['has_inventory'])
```

#### 整合測試

```python
# backend/api/tests/test_jenkins_build_testcases_integration.py

from django.test import TestCase
from pathlib import Path
from api.models import JenkinsJob, JenkinsBuild
from library.services.ansible_inventory_service import AnsibleInventoryService

class TestJenkinsBuildTestCasesIntegration(TestCase):
    
    def test_real_inventory_parsing(self):
        """使用真實的 inventory 檔案測試"""
        inventory_path = Path('/mnt/mdt/Team/PQ1-3/tool/jenkins_test_storage/10.252.170.171/Test-KVM01/148/artifacts/inventory/hosts')
        
        if not inventory_path.exists():
            self.skipTest('Test inventory file not found')
        
        service = AnsibleInventoryService(str(inventory_path))
        result = service.get_full_inventory(use_cache=False)
        
        self.assertTrue(result['success'])
        
        hostvars = result['data']['_meta']['hostvars']
        
        # 檢查是否有 testcase_set 欄位
        test_cases_found = False
        for hostname, vars in hostvars.items():
            if 'testcase_set' in vars:
                test_cases_found = True
                break
        
        self.assertTrue(test_cases_found, '至少應該有一個主機有 testcase_set 欄位')
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
   - ✅ Build 基本資訊正確
   - ✅ 測試案例列表正確
   - ✅ 主機列表完整
   - ✅ 統計數字正確

5. **測試重新載入功能**
   - 點擊「重新載入」按鈕
   - 確認資料重新載入

6. **測試快取狀態**
   - 第一次載入：橙色「即時獲取」
   - 第二次載入：綠色「從快取載入」

7. **測試錯誤處理**
   - 測試沒有 inventory 的 Build
   - 測試沒有 artifacts 的 Build

---

## 📁 檔案結構

```
backend/
├── api/
│   ├── views/
│   │   └── jenkins.py                     # 新增 get_test_cases() 方法
│   └── tests/
│       ├── test_jenkins_build_testcases.py              # 新增單元測試
│       └── test_jenkins_build_testcases_integration.py  # 新增整合測試

frontend/
├── src/
│   ├── components/
│   │   └── TestCaseDrawer.js              # 新增組件
│   ├── pages/
│   │   └── RVTAnalysisPage.js             # 修改：新增按鈕和 Drawer
│   └── services/
│       └── jenkinsService.js              # 新增 getBuildTestCases() 方法

docs/
└── development/
    └── JENKINS_BUILD_TESTCASE_DISPLAY_PLAN.md  # 本文件
```

---

## 🚀 實施步驟

### Phase 1: 後端開發

1. ✅ 在 `JenkinsBuildViewSet` 中新增 `get_test_cases()` 方法
2. ✅ 編寫單元測試
3. ✅ 編寫整合測試
4. ✅ 測試 API 端點

### Phase 2: 前端開發

1. ✅ 建立 `TestCaseDrawer.js` 組件
2. ✅ 在 `jenkinsService.js` 中新增 `getBuildTestCases()` 方法
3. ✅ 修改 `RVTAnalysisPage.js`：
   - 新增 State
   - 新增處理函數
   - 新增按鈕
   - 渲染 Drawer
4. ✅ 測試前端功能

### Phase 3: 整合測試

1. ✅ 端到端測試
2. ✅ 效能測試
3. ✅ 錯誤處理測試

### Phase 4: 文件和部署

1. ✅ 更新 API 文件
2. ✅ 更新功能說明
3. ✅ 部署到測試環境
4. ✅ 部署到生產環境

---

## 📊 資料範例

### API 響應範例

#### 成功（有測試案例）

```json
{
  "success": true,
  "build_id": 123,
  "build_number": 148,
  "job_name": "Test-KVM01",
  "has_inventory": true,
  "test_cases": [
    {
      "testcase_set": "testcases_demo",
      "hosts": ["Test-KVM01", "Test-KVM03"],
      "host_count": 2
    },
    {
      "testcase_set": "testcases_production",
      "hosts": ["Test-KVM07"],
      "host_count": 1
    }
  ],
  "total_hosts": 3,
  "total_test_sets": 2,
  "hosts_without_testcase": [],
  "cached": true
}
```

#### 部分主機無測試案例

```json
{
  "success": true,
  "build_id": 124,
  "build_number": 149,
  "job_name": "Test-KVM02",
  "has_inventory": true,
  "test_cases": [
    {
      "testcase_set": "testcases_demo",
      "hosts": ["Test-KVM02"],
      "host_count": 1
    }
  ],
  "total_hosts": 3,
  "total_test_sets": 1,
  "hosts_without_testcase": ["Test-KVM08", "Test-KVM09"],
  "cached": false
}
```

#### 沒有 inventory 檔案

```json
{
  "success": true,
  "build_id": 125,
  "build_number": 150,
  "job_name": "Test-KVM03",
  "has_inventory": false,
  "message": "該 Build 沒有 inventory 檔案"
}
```

#### 錯誤（artifacts 未存儲）

```json
{
  "success": false,
  "error": "該 Build 的 artifacts 尚未存儲到 NAS"
}
```

---

## 🎯 預期效果

### 功能效果

1. **資訊透明化**
   - 用戶可以清楚看到每個 Build 使用的測試案例
   - 了解測試案例的分佈情況

2. **問題排查**
   - 快速定位哪些主機使用了特定的測試案例
   - 發現配置缺失（主機沒有 testcase_set）

3. **測試管理**
   - 統計測試案例的使用情況
   - 追踪測試案例的變更

### UI 效果

- 🎨 美觀的 Drawer 介面
- 📊 清晰的資料展示
- 🔄 流暢的互動體驗
- ⚡ 快速的載入速度（利用快取）

---

## ⚠️ 注意事項

### 1. 依賴關係

- **必須先存儲 artifacts**：Build 必須已執行 `store_artifacts` 或 `store_workspace`
- **必須有 inventory 檔案**：不是所有 Build 都有 inventory 檔案
- **Ansible 環境**：後端必須已安裝 Ansible（`ansible-inventory` 命令）

### 2. 效能考量

- **快取策略**：使用 7 天快取，避免重複解析
- **大檔案處理**：inventory 檔案可能很大，確保有超時處理
- **並發請求**：考慮多個用戶同時請求的情況

### 3. 錯誤處理

- **優雅降級**：即使出錯也不影響主頁面
- **友善提示**：清晰的錯誤訊息
- **日誌記錄**：記錄所有錯誤到日誌

---

## 📝 後續優化

### 短期優化

1. **新增篩選功能**
   - 按測試案例集篩選 Build
   - 按主機篩選 Build

2. **匯出功能**
   - 匯出測試案例報表
   - 匯出為 CSV/Excel

### 長期優化

1. **測試案例趨勢分析**
   - 統計測試案例使用頻率
   - 分析測試案例變更歷史

2. **智能推薦**
   - 根據 Job 類型推薦測試案例
   - 檢測測試案例配置異常

---

## ✅ 驗收標準

### 後端

- [ ] API 端點正常運作
- [ ] 所有測試通過
- [ ] 錯誤處理完善
- [ ] 日誌記錄正確

### 前端

- [ ] Drawer 正確顯示
- [ ] 資料載入正確
- [ ] 重新載入功能正常
- [ ] 錯誤提示友善
- [ ] UI 美觀流暢

### 整合

- [ ] 端到端測試通過
- [ ] 快取機制正常
- [ ] 效能符合要求
- [ ] 文件完整

---

## 📅 時間規劃

| 階段            | 預估時間 | 負責人  |
| --------------- | -------- | ------- |
| Phase 1: 後端   | 2-3 小時 | 後端開發 |
| Phase 2: 前端   | 3-4 小時 | 前端開發 |
| Phase 3: 測試   | 2 小時   | QA      |
| Phase 4: 部署   | 1 小時   | DevOps  |
| **總計**        | **8-10 小時** |     |

---

## 📚 相關文件

- [Ansible Inventory 後端實現規劃](../features/ansible-inventory/BACKEND_IMPLEMENTATION_PLAN.md)
- [Ansible Inventory 快取機制規劃](../features/ansible-inventory/CACHE_MECHANISM_PLAN.md)
- [Ansible Inventory 配置檢查機制規劃](../analysis/ANSIBLE_INVENTORY_VALIDATION_PLAN.md)
- [Jenkins Workspace 自動存儲到 NAS](../features/jenkins-workspace-storage/README.md)

---

**規劃日期**：2025-11-15  
**規劃者**：GitHub Copilot  
**版本**：v1.0.0  
**狀態**：✅ 規劃完成，待確認執行
