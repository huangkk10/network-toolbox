# Build Configuration Validator - 開發規劃摘要

> 📅 創建日期：2025-11-15  
> 📍 狀態：規劃完成，等待執行  
> 🎯 目標：提供 Jenkins Build 配置自動檢查功能

---

## 🎯 核心需求

在 RVT Assistant 的 Jenkins Build 資料中，新增「檢查配置」按鈕，點擊後跳轉到獨立頁面自動檢查配置是否有問題。

---

## ✅ 檢查項目（Phase 1）

### 1️⃣ Host IP 檢查
- ✅ IP 格式驗證
- ✅ DHCP Server 租約檢查
- ✅ 租約活動狀態檢查
- ✅ 租約過期時間檢查

### 2️⃣ Host MAC 檢查
- ✅ MAC 格式驗證（**必須為 Linux 格式**：`30:C5:99:55:C9:D3`）
- ✅ DHCP Server 租約檢查
- ✅ MAC 與 IP 對應關係檢查

### 3️⃣ UART IP 檢查
- ✅ IP 格式驗證
- ✅ DHCP Server 租約檢查
- ✅ 租約活動狀態檢查

---

## 🏗️ 技術架構

```
前端（React）                    後端（Django）                      資料庫（PostgreSQL）
├─ RVTAnalysisPage              ├─ API Endpoint                    ├─ JenkinsBuild (現有)
│  └─ [檢查配置] 按鈕              │  /api/jenkins-builds/{id}/       │  - parameters (JSON)
│                                │    validate-config/              │  - ansible_config (JSON)
├─ BuildConfigValidatorPage     │                                  │
│  ├─ 配置概覽                    ├─ Service Layer                   ├─ DHCPLease (現有)
│  ├─ 檢查步驟 (Steps)            │  - BuildConfigValidator         │  - ip_address
│  └─ 檢查結果展示                │  - DHCPLeaseChecker             │  - mac_address
│                                │  - MACAddressValidator          │  - is_active
│                                │                                  │  - lease_end
└─ 使用 Ant Design 組件          └─ 返回 JSON 檢查結果               │
   (Steps, Result, Alert)                                         └─ DHCPServer (現有)
```

---

## 📋 需要開發的組件

### 後端

#### 1. Service Layer
- **文件**: `backend/library/services/build_config_validator.py`
- **類別**: `BuildConfigValidator`
- **方法**:
  - `validate_all()` - 執行所有檢查
  - `_check_host_ip()` - Host IP 檢查
  - `_check_host_mac()` - Host MAC 檢查
  - `_check_uart_ip()` - UART IP 檢查
  - `_extract_config_value()` - 從 parameters/ansible_config 提取值
  - `_is_valid_ip()` - IP 格式驗證
  - `_is_linux_mac_format()` - Linux MAC 格式驗證

#### 2. API Endpoint
- **URL**: `/api/jenkins-builds/{id}/validate-config/`
- **方法**: `POST`
- **ViewSet**: 在 `backend/api/views/jenkins.py` 的 `JenkinsBuildViewSet` 新增 `@action`

#### 3. 輔助 API（可選）
- `/api/dhcp-leases/check-ip/?ip={ip}`
- `/api/dhcp-leases/check-mac/?mac={mac}`
- `/api/utils/validate-mac/`

---

### 前端

#### 1. 新增頁面
- **文件**: `frontend/src/pages/BuildConfigValidatorPage.js`
- **路由**: `/rvt-analytics/build-config-validator/:buildId`
- **組件**:
  - Configuration Overview Card（Descriptions）
  - Validation Steps（Steps）
  - Results Section（Result + Alert）

#### 2. 修改現有頁面
- **文件**: `frontend/src/pages/RVTAnalysisPage.js`
- **修改**: 在 Build Table 的 Actions 列新增「檢查配置」按鈕
- **代碼**:
  ```javascript
  <Button 
      icon={<CheckCircleOutlined />}
      onClick={() => navigate(`/rvt-analytics/build-config-validator/${record.build_id}`)}
  >
      檢查配置
  </Button>
  ```

#### 3. 路由配置
- **文件**: `frontend/src/App.js`
- **新增路由**:
  ```javascript
  <Route 
      path="/rvt-analytics/build-config-validator/:buildId" 
      element={<BuildConfigValidatorPage />} 
  />
  ```

---

## 🎨 UI 設計重點

### 使用的 Ant Design 組件
- ✅ **Steps** - 顯示檢查進度
- ✅ **Result** - 顯示總體檢查結果
- ✅ **Descriptions** - 顯示配置詳情
- ✅ **Alert** - 顯示錯誤訊息和修正建議
- ✅ **Tag** - 顯示檢查狀態（✅ 通過 / ⚠️ 警告 / ❌ 失敗）
- ✅ **Card** - 組織內容區塊
- ✅ **Button** - 操作按鈕（返回、重新檢查）

### 顏色方案
```javascript
{
    passed: '#52c41a',    // 綠色
    warning: '#faad14',   // 橙色
    failed: '#ff4d4f',    // 紅色
    checking: '#1890ff',  // 藍色
}
```

---

## 📊 檢查邏輯流程

```
1. 前端發送 Build ID 到後端
   ↓
2. 後端從 JenkinsBuild 讀取 parameters 和 ansible_config
   ↓
3. 提取配置值（host_ip, host_mac, uart_ip）
   ↓
4. 逐項檢查：
   ├─ Host IP
   │  ├─ 格式驗證
   │  ├─ 查詢 DHCP Lease
   │  ├─ 檢查租約狀態
   │  └─ 檢查過期時間
   │
   ├─ Host MAC
   │  ├─ 格式驗證（必須為 Linux 格式）
   │  ├─ 查詢 DHCP Lease
   │  └─ 檢查 MAC-IP 對應關係
   │
   └─ UART IP
      ├─ 格式驗證
      ├─ 查詢 DHCP Lease
      └─ 檢查租約狀態
   ↓
5. 計算總體狀態（passed / warning / failed）
   ↓
6. 返回 JSON 結果給前端
   ↓
7. 前端以視覺化方式展示結果
```

---

## 📝 API 響應範例

```json
{
    "build_id": 123,
    "job_name": "RVT-Build-Backend",
    "build_number": 45,
    "overall_status": "warning",
    "check_results": [
        {
            "item": "host_ip",
            "status": "passed",
            "value": "192.168.1.100",
            "message": "IP 存在且租約有效",
            "details": {
                "lease_found": true,
                "lease_active": true,
                "lease_end": "2025-12-01T10:00:00Z",
                "hostname": "test-host-01"
            }
        },
        {
            "item": "host_mac",
            "status": "failed",
            "value": "30-C5-99-55-C9-D3",
            "message": "MAC 地址格式錯誤，必須使用冒號分隔（:）",
            "details": {
                "expected_format": "30:C5:99:55:C9:D3"
            }
        },
        {
            "item": "uart_ip",
            "status": "warning",
            "value": "192.168.1.200",
            "message": "租約即將在 12 小時後過期"
        }
    ],
    "checked_at": "2025-11-15T10:00:00Z"
}
```

---

## 🧪 測試計劃

### 單元測試
- **文件**: `tests/unit/backend/test_build_config_validator.py`
- **測試項目**:
  - ✅ Host IP 檢查通過
  - ✅ Host IP 檢查失敗（租約不存在）
  - ✅ Host MAC 格式錯誤檢測
  - ✅ MAC-IP 不一致檢測

### 整合測試
- **文件**: `tests/integration/api/test_build_config_api.py`
- **測試項目**:
  - ✅ API 端點正常返回
  - ✅ 檢查結果正確性
  - ✅ 錯誤處理

### E2E 測試
- **文件**: `tests/e2e/test_build_config_workflow.py`
- **測試流程**:
  1. 用戶點擊「檢查配置」按鈕
  2. 跳轉到檢查頁面
  3. 自動執行檢查
  4. 顯示檢查結果
  5. 返回 RVT Analysis 頁面

---

## 📅 開發時程（預估）

### Phase 1: 核心功能（2-3 週）

**Week 1: 後端開發**
- Day 1-2: 創建 `BuildConfigValidator` Service
- Day 3-4: 實現檢查邏輯（Host IP/MAC/UART）
- Day 5: 創建 API 端點
- Day 6-7: 編寫單元測試

**Week 2: 前端開發**
- Day 1-2: 創建 `BuildConfigValidatorPage` 頁面
- Day 3: 在 RVTAnalysisPage 新增按鈕
- Day 4-5: 實現檢查結果展示
- Day 6-7: UI 優化與測試

**Week 3: 整合與測試**
- Day 1-2: 整合測試
- Day 3-4: E2E 測試
- Day 5: 文檔撰寫
- Day 6-7: 內部測試與優化

---

## 🚀 未來擴展（Phase 2+）

### 更多檢查項目
- 🔄 Switch IP/Port 檢查
- 🔄 Ansible Playbook 檔案檢查
- 🔄 NAS 存儲路徑檢查
- 🔄 Jenkins Job 參數完整性檢查

### 進階功能
- 🔄 批量檢查（同時檢查多個 Build）
- 🔄 檢查歷史記錄
- 🔄 配置錯誤趨勢分析
- 🔄 自動修正建議
- 🔄 導出檢查報告（PDF/JSON）

---

## 📚 相關文檔

- **完整技術規劃**: [BUILD_CONFIGURATION_VALIDATOR.md](./BUILD_CONFIGURATION_VALIDATOR.md)
- **功能導航**: [README.md](./README.md)
- **開發指南**: [../../development/DEVELOPMENT.md](../../development/DEVELOPMENT.md)

---

## ✅ 規劃完成檢查清單

- [x] 分析現有架構和需求
- [x] 設計技術架構
- [x] 設計資料庫結構
- [x] 設計 API 端點
- [x] 設計前端 UI
- [x] 設計檢查邏輯
- [x] 規劃測試計劃
- [x] 撰寫完整文檔
- [x] 創建功能導航
- [ ] **開始實現（等待執行）**

---

**規劃完成日期**: 2025-11-15  
**預計開始日期**: 待定  
**負責人**: Network Toolbox Team

---

**🎉 規劃文檔已完成，可以開始實現了！**
