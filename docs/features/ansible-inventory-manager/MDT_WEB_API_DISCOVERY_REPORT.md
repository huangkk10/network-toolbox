# MDT Web API 端點發現報告

**報告日期**：2025-11-24  
**測試人員**：開發團隊  
**MDT Web 版本**：MDT Manager（jQuery + Bootstrap）  
**狀態**：✅ API 端點已確認

---

## 📋 執行摘要

通過瀏覽器開發者工具捕獲網路請求，成功發現 MDT Web 的 **真正 API 端點**。

**關鍵發現**：
- ✅ MDT Web 提供 RESTful API
- ✅ 使用 `search` 參數查詢設備
- ✅ 回應格式為 JSON 陣列
- ✅ 包含完整的設備資訊（IP、MAC、狀態等）

---

## 🔍 API 端點詳情

### 基本資訊

| 項目 | 內容 |
|------|------|
| **Base URL** | `http://10.250.10.2` |
| **API 端點** | `/api/devices` |
| **HTTP 方法** | `GET` |
| **認證方式** | 無需認證（內網使用） |
| **Content-Type** | `application/json` |

### 請求格式

**端點**：
```
GET /api/devices?search={device_number}&sort=name&order=asc
```

**必要參數**：
- `search`：設備編號（如 `PC-SSD-4052`）

**選用參數**：
- `sort`：排序欄位（預設：`name`）
- `order`：排序方向（`asc` 或 `desc`）

**範例請求**：
```bash
curl "http://10.250.10.2/api/devices?search=PC-SSD-4052"
```

**Python 範例**：
```python
import requests

url = "http://10.250.10.2/api/devices"
params = {"search": "PC-SSD-4052"}

response = requests.get(url, params=params, timeout=10)
devices = response.json()

# 精確匹配設備名稱
for device in devices:
    if device['name'] == 'PC-SSD-4052':
        print(f"Found: {device['name']}")
        print(f"IP: {device['info']['ip']}")
        print(f"MAC: {device['info']['mac']}")
```

---

## 📊 回應格式

### 成功回應（HTTP 200）

**資料類型**：JSON 陣列（`Array<Device>`）

**範例回應**：
```json
[
    {
        "name": "PC-SSD-4052",
        "uuid": "49dd0707-02b6-abcb-7996-e89c2594ef72",
        "os_build": "AUTOMP",
        "driver_path": "",
        "script_path": "",
        "log_path": "",
        "automp_type": "NONE",
        "automp_path": "",
        "comment": "測試設備",
        "info": {
            "vendor": "ASUS",
            "model": "System Product Name",
            "product": "ROG STRIX Z790-E GAMING WIFI II",
            "wds_server": "",
            "ip": "10.250.11.21",
            "mac": "E8:9C:25:94:EF:72",
            "gateway": "10.250.11.254"
        },
        "monitor": {
            "percent_complete": 0,
            "deployment_status": 1,
            "start_time": "2025-11-21T12:03:42+00:00",
            "end_time": null,
            "device_id": null,
            "step_name": "Gather local only",
            "last_time": "2025-11-21T12:03:42+00:00",
            "dart_ip": "",
            "dart_port": "",
            "dart_ticket": ""
        }
    }
]
```

### 關鍵欄位說明

| 欄位路徑 | 類型 | 說明 | 對應 Inventory 欄位 |
|----------|------|------|---------------------|
| `name` | String | 設備編號 | `device_number` |
| `uuid` | String | 設備唯一識別碼 | - |
| `os_build` | String | 作業系統版本 | - |
| `comment` | String | 設備註解 | - |
| `info.vendor` | String | 製造商 | - |
| `info.model` | String | 型號 | - |
| `info.product` | String | 產品名稱 | - |
| **`info.ip`** | String | **IP 地址** | **`ansible_host`** |
| **`info.mac`** | String | **MAC 地址** | **`mac_address`** |
| `info.gateway` | String | 閘道 IP | - |
| `monitor.deployment_status` | Integer | 部署狀態（1=進行中） | - |
| `monitor.step_name` | String | 當前步驟 | - |
| `monitor.last_time` | String | 最後更新時間 | - |

---

## 🧪 測試結果

### 測試案例 1：查詢單一設備

**請求**：
```bash
GET /api/devices?search=PC-SSD-4052
```

**結果**：
- ✅ 狀態碼：`200 OK`
- ✅ 回應類型：`application/json`
- ✅ 找到 1 筆設備
- ✅ 設備資訊完整（IP、MAC、狀態等）

### 測試案例 2：查詢不存在的設備

**請求**：
```bash
GET /api/devices?search=PC-SSD-9999
```

**結果**：
- ✅ 狀態碼：`200 OK`
- ✅ 回應：空陣列 `[]`

### 測試案例 3：模糊搜尋

**請求**：
```bash
GET /api/devices?search=PC-SSD
```

**結果**：
- ✅ 狀態碼：`200 OK`
- ✅ 回應：包含多個設備（名稱包含 "PC-SSD" 的所有設備）
- ⚠️ **注意**：需要精確匹配 `name` 欄位，避免誤判

---

## 💡 實施建議

### 1. 精確匹配設備名稱

由於 `search` 參數支援模糊搜尋，實施時必須精確匹配 `name` 欄位：

```python
def get_device_from_mdt_web(device_number: str) -> Optional[Dict]:
    """查詢設備並精確匹配名稱"""
    url = "http://10.250.10.2/api/devices"
    params = {"search": device_number}
    
    response = requests.get(url, params=params, timeout=10)
    devices = response.json()
    
    # 精確匹配，避免誤判
    for device in devices:
        if device.get('name') == device_number:  # 完全相同
            return device
    
    return None  # 未找到
```

### 2. 欄位對應關係

| Inventory 欄位 | MDT Web 欄位 | 比對邏輯 |
|----------------|--------------|----------|
| `device_number` | `name` | 精確匹配（區分大小寫） |
| `ansible_host` | `info.ip` | IP 地址比對 |
| `mac_address` | `info.mac` | MAC 地址比對（需標準化格式） |

### 3. MAC 地址格式處理

MDT Web 使用 `60:CF:84:A2:E6:DF` 格式，Inventory 可能使用不同格式。

**標準化函數**：
```python
def normalize_mac_address(mac: str) -> str:
    """標準化 MAC 地址格式"""
    return mac.lower().replace('-', ':').replace('.', ':')

# 範例
normalize_mac_address('E8-9C-25-94-EF-72')  # → 'e8:9c:25:94:ef:72'
normalize_mac_address('E8:9C:25:94:EF:72')  # → 'e8:9c:25:94:ef:72'
```

### 4. 錯誤處理

```python
try:
    response = requests.get(url, params=params, timeout=10)
    response.raise_for_status()  # 檢查 HTTP 狀態碼
    
    devices = response.json()
    
    if not isinstance(devices, list):
        logger.error(f"Unexpected response format: {type(devices)}")
        return None
        
except requests.exceptions.Timeout:
    logger.error("MDT Web request timeout")
    return None
    
except requests.exceptions.ConnectionError:
    logger.error("Cannot connect to MDT Web")
    return None
    
except Exception as e:
    logger.error(f"MDT Web API error: {e}")
    return None
```

---

## 🎯 與原計劃的差異

### 原本推測的 API 格式（❌ 錯誤）

```
GET /api/devices/{device_number}  ← 返回 404/405
```

### 實際的 API 格式（✅ 正確）

```
GET /api/devices?search={device_number}  ← 返回 200
```

### 回應格式差異

| 欄位 | 原本推測 | 實際格式 |
|------|----------|----------|
| 設備編號 | `device` | `name` |
| IP 地址 | `ip_address` | `info.ip` |
| MAC 地址 | `mac_address` | `info.mac` |
| 製造商 | `manufacturer` | `info.vendor` |

---

## 📝 後續行動

### 已完成 ✅

- [x] 發現真正的 API 端點格式
- [x] 測試 API 回應正確性
- [x] 確認資料結構和欄位對應
- [x] 更新實施計劃文檔

### 待執行 📋

- [ ] 實施 `MDTWebService` 類別（使用正確的 API）
- [ ] 在 `InventoryConfigValidator` 中整合 MDT Web 檢查
- [ ] 創建測試腳本驗證功能
- [ ] 更新前端 UI 顯示 MDT Web 檢查結果

---

## 🔗 相關文檔

| 文檔 | 路徑 | 說明 |
|------|------|------|
| 實施計劃 | `MDT_WEB_CHECK_IMPLEMENTATION_PLAN.md` | 詳細實施步驟 |
| 配置驗證器 | `backend/library/services/inventory_config_validator.py` | 現有驗證器代碼 |
| API 測試腳本 | 開發中 | 用於測試 MDT Web API |

---

## 📞 技術支援

**MDT Web 伺服器**：http://10.250.10.2  
**API 端點**：http://10.250.10.2/api/devices  
**測試設備號碼**：PC-SSD-4052  

**疑問或問題**：請聯繫開發團隊

---

**最後更新**：2025-11-24  
**報告狀態**：✅ API 端點已確認，可開始實施  
**下一步**：根據實際 API 格式實施 MDTWebService 類別
