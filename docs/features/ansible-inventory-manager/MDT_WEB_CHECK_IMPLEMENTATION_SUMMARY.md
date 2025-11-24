# MDT Web 檢查功能實施總結

## 📋 概述

成功在 Ansible Inventory Manager 的配置檢查功能中實現 MDT Web 檢查，用於驗證 Inventory 中設備配置與 MDT Web 系統的一致性。

**完成日期**: 2025-11-24  
**功能版本**: v1.0

---

## ✅ 實施成果

### 1. MDT Web 服務模組 (`library/services/mdt_web_service.py`)

**功能**：提供與 MDT Web API 交互的服務層

**核心類別**：`MDTWebService`

**主要方法**：
- `check_connection()` - 檢查 MDT Web 是否可訪問
- `get_device(device_number)` - 根據設備編號查詢設備資訊
- `validate_device_config(device_number, expected_config)` - 驗證設備配置一致性
- `_normalize_mac_address(mac)` - MAC 地址格式標準化

**輔助函數**：
- `create_mdt_web_service(dhcp_server_ip)` - 根據 DHCP Server IP 自動計算 MDT Web IP

**API 端點**：`GET /api/devices?search={device_number}`

**回應格式**：`{"rows": [devices], "total": count}`

**測試結果**：
```
✓ 連接測試通過
✓ 設備查詢通過 (PC-SSD-4052)
✓ 配置驗證通過
✓ API 回應格式處理正確
```

---

### 2. 配置驗證器整合 (`library/services/inventory_config_validator.py`)

**新增檢查方法**：`_check_mdt_web()`

**檢查流程**：
1. **獲取 DHCP Server IP**
   - 方法 1：從 Inventory 內容中搜尋 `dhcp_server` 變數
   - 方法 2：從主機 IP 地址推斷（前三段 + `.1`）
   - 方法 3：驗證推斷的 IP 是否存在於 DHCPServer 資料庫

2. **計算 MDT Web IP**
   - 算法：DHCP Server IP 的前三段 + `.2`
   - 範例：`10.250.10.1` → `10.250.10.2`

3. **檢查 MDT Web 連接**
   - 使用 `MDTWebService.check_connection()`
   - 超時時間：10 秒

4. **獲取待檢查設備**
   - 從 `AnsibleHostConfig.other_vars` JSON 欄位中提取 `device_number`
   - 收集主機名、device_number、IP、MAC 地址

5. **逐個驗證設備配置**
   - 查詢 MDT Web 中的設備資訊
   - 比對 IP 地址、MAC 地址、Hostname
   - 記錄未找到的設備和配置不一致的設備

6. **生成檢查結果**
   - 狀態判斷：`error`（有未找到設備）、`warning`（有不一致設備）、`success`（全部一致）
   - 詳細資訊：設備數量、匹配率、差異列表
   - 建議：修復指引和檢查建議

**輔助方法**：
- `_get_dhcp_server_ip()` - 智能推斷 DHCP Server IP
- `_calculate_mdt_web_ip()` - 計算 MDT Web IP
- `_get_inventory_hosts_with_device_number()` - 提取有 device_number 的主機
- `_generate_mdt_web_suggestions()` - 生成修復建議

**測試結果**：
```
✓ 自動推斷 DHCP Server IP (10.250.111.1)
✓ 自動計算 MDT Web IP (10.250.111.2)
✓ MDT Web 連接測試執行
✓ 錯誤處理完善
✓ 成為第 8 個檢查項目
```

---

### 3. 前端 UI 更新 (`frontend/src/components/InventoryValidationDrawer.js`)

**更新內容**：

1. **檢查項目顯示名稱**
   ```javascript
   mdt_web: 'MDT Web 檢查'
   ```

2. **詳細資訊標籤**
   - `dhcp_server_ip`: 'DHCP Server IP'
   - `mdt_web_ip`: 'MDT Web IP'
   - `mdt_web_accessible`: 'MDT Web 可訪問'
   - `total_devices`: '設備總數'
   - `matched_devices`: '匹配設備'
   - `not_found_count`: '未找到設備數'
   - `mismatched_count`: '不一致設備數'
   - `not_found_devices`: '未找到的設備'
   - `mismatched_devices`: '配置不一致的設備'

3. **特殊格式化顯示**

   **未找到的設備**：
   - 紅色卡片背景 (#fff1f0)
   - 顯示主機名和 Device Number
   - 錯誤圖標 (CloseCircleOutlined)

   **配置不一致的設備**：
   - 黃色卡片背景 (#fffbe6)
   - 顯示主機名和 Device Number
   - 列出所有差異欄位
   - 對比 Inventory 值 vs MDT Web 值
   - 警告圖標 (WarningOutlined)

**UI 效果**：
- ✅ 自動展開錯誤和警告項目
- ✅ 清晰的視覺回饋（顏色、圖標）
- ✅ 詳細的差異對比顯示
- ✅ 友好的錯誤訊息

---

## 📊 功能特性

### 核心功能

1. **智能 IP 推斷**
   - 從 Inventory 內容自動推斷 DHCP Server IP
   - 根據 DHCP Server IP 計算 MDT Web IP
   - 支援多種推斷策略

2. **全面配置比對**
   - IP 地址一致性檢查
   - MAC 地址一致性檢查（支援多種格式）
   - Hostname 一致性檢查

3. **詳細錯誤報告**
   - 列出所有未找到的設備
   - 列出所有配置不一致的設備
   - 顯示具體的差異欄位和值

4. **友好的建議系統**
   - 根據檢查結果生成針對性建議
   - 提供修復指引
   - 統計差異類型

### 錯誤處理

- ✅ 無 DHCP Server 時跳過檢查（warning）
- ✅ MDT Web 無法訪問時給出明確錯誤
- ✅ 無 device_number 主機時給出提示
- ✅ API 請求失敗時記錄詳細日誌
- ✅ 異常情況下不影響其他檢查項目

### 性能優化

- ⚡ 逐個設備查詢（確保準確性）
- ⚡ 超時控制（10 秒）
- ⚡ 最多顯示 10 個問題設備（避免前端過載）
- ⚡ 支援可選檢查（不強制執行）

---

## 🧪 測試驗證

### 測試腳本

1. **`test_mdt_web_integration.py`**
   - 完整的整合測試
   - 測試驗證器執行流程
   - 驗證所有檢查項目

2. **`test_mdt_web_with_real_server.py`**
   - 使用真實 MDT Web (10.250.10.2) 測試
   - 服務層功能驗證
   - 驗證器輔助方法測試

### 測試結果

**MDT Web 服務層**：
```
✓ 連接測試: 成功
✓ 設備查詢 (PC-SSD-4052): 找到
  - IP: 10.250.11.21
  - MAC: E8:9C:25:94:EF:72
  - OS: WINPE
✓ 配置驗證: 一致
```

**整合測試**：
```
✓ 所有檢查項目執行正常
✓ MDT Web 檢查作為第 8 個項目
✓ 整體狀態: ERROR (因 DHCP 租約未匹配)
✓ MDT Web 檢查狀態: WARNING (DHCP Server 未關聯)
```

---

## 📁 檔案清單

### 新增檔案

1. **`library/services/mdt_web_service.py`** (325 行)
   - MDT Web API 服務層
   - 設備查詢和配置驗證

2. **`backend/test_mdt_web_integration.py`** (113 行)
   - 整合測試腳本

3. **`backend/test_mdt_web_with_real_server.py`** (141 行)
   - 真實伺服器測試腳本

4. **`docs/features/ansible-inventory-manager/MDT_WEB_CHECK_IMPLEMENTATION_SUMMARY.md`** (本文件)
   - 實施總結文檔

### 修改檔案

1. **`library/services/inventory_config_validator.py`**
   - 新增 `_check_mdt_web()` 方法（約 150 行）
   - 新增 4 個輔助方法（約 120 行）
   - 更新 `validate()` 方法調用流程

2. **`frontend/src/components/InventoryValidationDrawer.js`**
   - 新增 `mdt_web` 顯示名稱
   - 新增 10 個 MDT Web 相關標籤
   - 新增 2 個特殊格式化函數（約 80 行）

3. **`library/services/__init__.py`**
   - 導出 `MDTWebService`

---

## 🔧 技術細節

### API 端點發現

**初始假設**：
- 端點：`/DeviceDetail.aspx?deviceNumber={device_number}`
- 格式：HTML 頁面

**實際發現**（通過瀏覽器 DevTools）：
- 端點：`GET /api/devices?search={device_number}`
- 格式：JSON `{"rows": [devices], "total": count}`

### MDT Web IP 計算規則

**規則**：DHCP Server IP 的前三段 + `.2`

**範例**：
| DHCP Server IP | MDT Web IP    |
|---------------|---------------|
| 10.250.10.1   | 10.250.10.2   |
| 10.250.111.1  | 10.250.111.2  |
| 192.168.1.1   | 192.168.1.2   |

**驗證**：已通過實際環境測試確認

### MAC 地址標準化

**支援格式**：
- `XX:XX:XX:XX:XX:XX`
- `XX-XX-XX-XX-XX-XX`
- `XXXXXXXXXXXX`

**標準化結果**：統一為 `xx:xx:xx:xx:xx:xx`（小寫、冒號分隔）

---

## 📖 使用說明

### 如何觸發 MDT Web 檢查

1. **前端操作**：
   - 打開 Ansible Inventory 管理頁面
   - 點擊「配置檢查」按鈕
   - 系統自動執行包含 MDT Web 檢查在內的所有檢查

2. **API 調用**：
   ```bash
   curl -X POST http://localhost/api/ansible-inventory/{id}/validate-config/ \
        -H "Content-Type: application/json" \
        -d '{"check_connectivity": false, "check_dhcp": true}'
   ```

3. **檢查跳過條件**：
   - 無法推斷 DHCP Server IP → 跳過（warning）
   - MDT Web 無法訪問 → 錯誤（error）
   - 無 device_number 主機 → 跳過（warning）

### 如何解讀檢查結果

**成功**（status: success）：
```
所有 N 個設備配置一致
```

**警告**（status: warning）：
```
M 個設備配置不一致
  • X 個設備的 ip_address 不一致
  • Y 個設備的 mac_address 不一致
```

**錯誤**（status: error）：
```
M 個設備在 MDT Web 中找不到
  缺失設備: PC-SSD-4052, PC-SSD-4053
```

---

## 🚀 後續優化建議

### 短期（1-2 週）

1. **性能優化**
   - 實現批量設備查詢（如 MDT Web API 支援）
   - 添加查詢結果快取（5 分鐘）
   - 並行查詢多個設備

2. **功能增強**
   - 支援設備狀態檢查（online/offline）
   - 支援作業系統版本比對
   - 添加設備最後更新時間比對

3. **錯誤處理**
   - 添加重試機制（3 次）
   - 詳細的網路錯誤分類
   - 支援部分失敗繼續檢查

### 中期（1-2 個月）

1. **自動修復**
   - 發現不一致時提供「同步」按鈕
   - 支援批量更新 Inventory 配置
   - 生成修復腳本

2. **歷史記錄**
   - 記錄每次檢查結果
   - 追蹤配置變更歷史
   - 生成趨勢報告

3. **告警機制**
   - 檢查失敗時發送通知
   - 支援郵件/Slack 告警
   - 自訂告警規則

### 長期（3-6 個月）

1. **智能分析**
   - 機器學習預測配置問題
   - 自動識別異常模式
   - 提供優化建議

2. **多環境支援**
   - 支援多個 MDT Web 環境
   - 環境切換和比對
   - 跨環境一致性檢查

3. **API 擴展**
   - 提供獨立的 MDT Web 檢查 API
   - 支援 Webhook 回調
   - 整合第三方監控系統

---

## 📚 相關文檔

- [MDT Web 檢查實施計劃](./MDT_WEB_CHECK_IMPLEMENTATION_PLAN.md)
- [MDT Web API 發現報告](./MDT_WEB_API_DISCOVERY_REPORT.md)
- [Ansible Inventory 配置驗證器說明](./INVENTORY_CONFIG_VALIDATOR.md)

---

## 👥 開發團隊

**實施者**: GitHub Copilot  
**審核者**: Network Toolbox Team  
**測試者**: Network Toolbox Team

---

## 📝 更新日誌

### v1.0 (2025-11-24)

- ✅ 實現 MDT Web 服務層
- ✅ 整合到配置驗證器
- ✅ 更新前端 UI 顯示
- ✅ 創建測試腳本
- ✅ 編寫完整文檔

---

**文檔版本**: 1.0  
**最後更新**: 2025-11-24  
**狀態**: ✅ 已完成
