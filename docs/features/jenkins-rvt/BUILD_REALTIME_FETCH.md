# Build 實時獲取功能說明

## 📋 問題原因

當您點擊 Job 展開時，顯示「載入 0 個 Build」是因為：

1. **數據庫中沒有 Build 數據**
   - `sync_jobs` 只同步了 Jobs 列表
   - 沒有將 Builds 存入數據庫

2. **原本的 API 只查詢數據庫**
   - `/api/jenkins-jobs/{id}/builds/` 只從數據庫查詢
   - 數據庫為空，所以返回 0 個 Builds

---

## ✅ 解決方案

### 改為**從 Jenkins 實時獲取 Builds**

不將 Builds 存入數據庫，而是每次展開 Job 時，實時從 Jenkins API 獲取最新數據。

**優點**：
- ✅ **即時性**：永遠顯示最新的 Build 狀態
- ✅ **無需同步**：不需要定期同步 Builds 到數據庫
- ✅ **節省空間**：不佔用數據庫空間
- ✅ **簡單**：無需處理數據同步邏輯

**缺點**：
- ⚠️ **網路延遲**：每次展開需要請求 Jenkins API（通常很快，< 100ms）
- ⚠️ **依賴 Jenkins**：如果 Jenkins 離線，無法查看歷史數據

---

## 🔧 技術實現

### 1. 後端更改

#### 1.1 Jenkins Client 新增方法

```python
# library/services/jenkins_client.py

def get_job_builds(self, job_name: str, limit: int = 10) -> List[Dict[str, Any]]:
    """
    獲取指定 Job 的 Builds
    
    Args:
        job_name: Job 名稱
        limit: 返回的 Build 數量限制
        
    Returns:
        list: Build 列表（包含 number, url, result, timestamp, duration）
    """
    url = f"{self.base_url}/job/{job_name}/api/json?tree=builds[number,url,result,timestamp,duration,building]{{0,{limit}}}"
    response = self._make_request('GET', url)
    data = response.json()
    builds = data.get('builds', [])
    return builds
```

**API 調用範例**：
```bash
GET http://10.252.170.188:8080/job/SAF7514_K03/api/json?tree=builds[number,url,result,timestamp,duration,building]{0,10}
```

#### 1.2 Builds API 端點更新

```python
# backend/api/views/jenkins.py

@action(detail=True, methods=['get'])
def builds(self, request, pk=None):
    """
    獲取 Job 的所有 Build（從 Jenkins 實時獲取）
    
    GET /api/jenkins-jobs/{id}/builds/?limit=10
    """
    job = self.get_object()
    
    # 從 Jenkins 實時獲取
    client = JenkinsClient(
        base_url=job.server.url,
        username=job.server.username,
        api_token=job.server.api_token
    )
    
    jenkins_builds = client.get_job_builds(job.name, limit=limit)
    
    # 轉換格式並返回
    builds_data = [...]
    
    return Response({
        'job_id': job.id,
        'job_name': job.name,
        'total_builds': len(jenkins_builds),
        'builds': builds_data
    })
```

### 2. 前端更改

#### 2.1 handleExpand - 展開 Job 時獲取 Builds

```javascript
// frontend/src/pages/RVTAnalysisPage.js

const handleExpand = async (expanded, record) => {
    if (expanded && record.type === 'job' && record.children.length === 0) {
        try {
            const response = await axios.get(
                `/api/jenkins-jobs/${record.job_id}/builds/?limit=10`
            );
            
            const builds = response.data.builds.map(build => ({
                key: `build-${build.build_number}`,
                type: 'build',
                build_number: build.build_number,
                result: build.result,
                build_timestamp: build.build_timestamp,
                duration: build.duration_formatted,
                url: build.url,  // Jenkins Build URL
                job_id: record.job_id,
                job_name: record.name,
            }));
            
            // 更新 Tree Table
            setTreeData(prevData => {
                return prevData.map(item => {
                    if (item.key === record.key) {
                        return { ...item, children: builds };
                    }
                    return item;
                });
            });
            
            message.success(`載入了 ${builds.length} 個 Builds`);
        } catch (error) {
            message.error('載入 Builds 失敗');
        }
    }
};
```

#### 2.2 直接打開 Jenkins 頁面

**查看 Console Log**：
```javascript
const handleViewLog = (record) => {
    window.open(`${record.url}console`, '_blank');
    message.success('已在新視窗中打開 Console Log');
};
```

**查看 Build 詳情**：
```javascript
const handleViewDetail = (record) => {
    window.open(record.url, '_blank');
    message.success('已在新視窗中打開 Build 詳情');
};
```

---

## 📊 API 響應格式

### 請求

```bash
GET /api/jenkins-jobs/30/builds/?limit=5
```

### 響應

```json
{
    "job_id": 30,
    "job_name": "SAF222_K09",
    "total_builds": 1,
    "builds": [
        {
            "id": "jenkins-30-1",
            "build_number": 1,
            "result": "SUCCESS",
            "build_timestamp": "2025-09-15 17:46:47",
            "duration": 10.5,
            "duration_formatted": "10 秒",
            "url": "http://10.252.170.188:8080/job/SAF222_K09/1/",
            "building": false
        }
    ]
}
```

**字段說明**：
- `id`: 臨時 ID（格式：`jenkins-{job_id}-{build_number}`）
- `build_number`: Build 編號
- `result`: 構建結果（SUCCESS, FAILURE, UNSTABLE, ABORTED, RUNNING, UNKNOWN）
- `build_timestamp`: 構建時間（格式化為 YYYY-MM-DD HH:MM:SS）
- `duration`: 持續時間（秒）
- `duration_formatted`: 格式化的持續時間（例如：`10 秒`, `2 分 30 秒`, `1 小時 5 分`）
- `url`: Jenkins Build URL
- `building`: 是否正在構建中

---

## 🎯 使用方式

### 1. 查看 Builds

1. 訪問：http://localhost/rvt-analytics
2. 找到任意 Job
3. 點擊 Job 左側的 **展開圖標（▶）**
4. 系統會自動從 Jenkins 獲取最新的 10 個 Builds
5. 顯示成功訊息：「載入了 X 個 Builds」

### 2. 查看 Console Log

1. 展開 Job 後，找到想查看的 Build
2. 點擊該 Build 的「日誌」按鈕
3. 系統會在**新視窗**中打開 Jenkins 的 Console 輸出頁面
4. URL 格式：`http://10.252.170.188:8080/job/{job_name}/{build_number}/console`

### 3. 查看 Build 詳情

1. 展開 Job 後，找到想查看的 Build
2. 點擊該 Build 的「詳情」按鈕
3. 系統會在**新視窗**中打開 Jenkins 的 Build 詳情頁面
4. URL 格式：`http://10.252.170.188:8080/job/{job_name}/{build_number}/`

---

## 🧪 測試驗證

### 測試 API 端點

```bash
# 測試獲取 Builds（Job ID: 30，限制 5 個）
curl -s "http://localhost/api/jenkins-jobs/30/builds/?limit=5" | python3 -m json.tool

# 測試不同的 Job
curl -s "http://localhost/api/jenkins-jobs/29/builds/?limit=3" | python3 -m json.tool

# 檢查返回的數據結構
curl -s "http://localhost/api/jenkins-jobs/30/builds/" | jq '.builds[0]'
```

### 驗證 Jenkins Client

```python
from library.services.jenkins_client import JenkinsClient

client = JenkinsClient(base_url='http://10.252.170.188:8080')
builds = client.get_job_builds('SAF7514_K03', limit=5)

print(f'獲取了 {len(builds)} 個 Builds')
for build in builds:
    print(f"  - Build #{build['number']}: {build['result']}")
```

---

## 📈 性能考量

### 響應時間

**實測數據**：
```bash
# 從 Jenkins 獲取 10 個 Builds
$ time curl -s "http://localhost/api/jenkins-jobs/30/builds/?limit=10" > /dev/null
real    0m0.052s  # 52 毫秒
```

**結論**：
- ✅ 響應時間 < 100ms（非常快）
- ✅ 用戶體驗良好（幾乎無感知延遲）

### 優化建議

1. **限制 Build 數量**
   - 預設限制 10 個 Builds
   - 前端可根據需求調整（`?limit=20`）

2. **使用 tree 參數**
   - Jenkins API 支持只獲取需要的字段
   - 減少傳輸數據量
   - 範例：`tree=builds[number,url,result,timestamp,duration]{0,10}`

3. **考慮添加快取**（未來優化）
   - 可以添加短期快取（例如 30 秒）
   - 減少對 Jenkins 的請求頻率

---

## 🔍 故障排查

### 問題 1：顯示「載入 0 個 Builds」

**可能原因**：
- Jenkins 中該 Job 確實沒有 Builds
- Jenkins URL 配置錯誤
- Jenkins 認證失敗

**檢查方法**：
```bash
# 1. 查看 Django 錯誤日誌
tail -f logs/django_error.log

# 2. 測試 API
curl -s "http://localhost/api/jenkins-jobs/30/builds/" | jq

# 3. 直接測試 Jenkins API
curl -s "http://10.252.170.188:8080/job/SAF7514_K03/api/json" | jq '.builds | length'
```

### 問題 2：點擊「日誌」或「詳情」無法打開

**可能原因**：
- Build URL 為空或無效
- 瀏覽器阻止彈出視窗

**解決方法**：
1. 檢查瀏覽器控制台是否有錯誤
2. 允許瀏覽器彈出視窗
3. 檢查 Build 數據中的 `url` 字段是否正確

### 問題 3：Jenkins 連接失敗

**檢查清單**：
```bash
# 1. 測試 Jenkins 連接
curl -I http://10.252.170.188:8080

# 2. 檢查 Django 容器是否能訪問
docker exec nt-django curl -I http://10.252.170.188:8080

# 3. 查看 JenkinsServer 配置
docker exec nt-django python manage.py shell -c "
from api.models import JenkinsServer
server = JenkinsServer.objects.first()
print(f'URL: {server.url}')
print(f'Username: {server.username}')
print(f'Has Token: {bool(server.api_token)}')
"
```

---

## 📚 相關文檔

- **Jenkins REST API**: https://www.jenkins.io/doc/book/using/remote-access-api/
- **JenkinsClient**: `/library/services/jenkins_client.py`
- **API Views**: `/backend/api/views/jenkins.py`
- **RVTAnalysisPage**: `/frontend/src/pages/RVTAnalysisPage.js`

---

## 🎉 總結

現在系統已完全支持**從 Jenkins 實時獲取 Builds**：

✅ **功能正常**：
- 展開 Job 可以看到最新的 Builds
- 點擊「日誌」打開 Jenkins Console 頁面
- 點擊「詳情」打開 Jenkins Build 頁面

✅ **性能良好**：
- 響應時間 < 100ms
- 無需數據庫存儲

✅ **即時更新**：
- 每次展開都從 Jenkins 獲取最新狀態
- 可以看到正在構建中的 Builds（RUNNING）

---

**更新日期**：2025-11-04  
**版本**：v2.0  
**維護者**：Network Toolbox Team
