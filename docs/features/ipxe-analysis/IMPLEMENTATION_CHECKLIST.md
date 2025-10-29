# IPXE 管理功能實現檢查清單

## ✅ 實現進度追蹤

### Phase 1：後端基礎架構 (0/5)

- [ ] **1.1 創建數據模型**
  - 檔案：`backend/api/models.py`
  - 模型：
    - [ ] IPXEServer
    - [ ] IPXELog
    - [ ] IPXEStatistics
  - 參考：`DHCPServer`, `DHCPLog` 模型

- [ ] **1.2 執行數據庫遷移**
  ```bash
  docker exec nt-django python manage.py makemigrations
  docker exec nt-django python manage.py migrate
  ```

- [ ] **1.3 創建 Serializers**
  - 檔案：`backend/api/serializers.py`
  - 類別：
    - [ ] IPXEServerSerializer
    - [ ] IPXELogSerializer
    - [ ] IPXEStatisticsSerializer

- [ ] **1.4 創建 IPXEService**
  - 檔案：`backend/api/ipxe_service.py`
  - 方法：
    - [ ] connect_ssh()
    - [ ] execute_docker_command()
    - [ ] parse_mac_log()
    - [ ] parse_ipxe_log()
    - [ ] collect_logs_from_container()
    - [ ] sync_logs_to_db()
    - [ ] cleanup_old_logs()

- [ ] **1.5 註冊 API 路由**
  - 檔案：`backend/api/urls.py`
  - 路由：
    - [ ] `ipxe-servers/`
    - [ ] `ipxe-logs/`
    - [ ] `ipxe-servers/<id>/sync-logs/`
    - [ ] `ipxe-analytics/overview/`

---

### Phase 2：後端 API (0/5)

- [ ] **2.1 IPXEServerViewSet**
  - 檔案：`backend/api/views.py`
  - 功能：CRUD 操作
  - 測試：使用 Postman/curl 測試

- [ ] **2.2 IPXELogViewSet**
  - 檔案：`backend/api/views.py`
  - 功能：查詢、過濾
  - 過濾器：server, days, type, action, client_ip, mac

- [ ] **2.3 同步日誌 API**
  - 檔案：`backend/api/views.py`
  - 端點：`POST /api/ipxe-servers/<id>/sync-logs/`
  - 測試：手動觸發同步

- [ ] **2.4 統計分析 API**
  - 檔案：`backend/api/views.py`
  - 端點：`GET /api/ipxe-analytics/overview/`
  - 返回：total_requests, mac_operations, boot_requests, trend

- [ ] **2.5 SSH 連接測試**
  - 測試所有 10.250.x.2 伺服器
  - 驗證日誌解析正確性
  - 測試腳本：`test_ipxe_connection.py`

---

### Phase 3：定時任務 (0/3)

- [ ] **3.1 collect_ipxe_logs Command**
  - 檔案：`backend/api/management/commands/collect_ipxe_logs.py`
  - 測試：
    ```bash
    docker exec nt-django python manage.py collect_ipxe_logs
    docker exec nt-django python manage.py collect_ipxe_logs --server 1
    docker exec nt-django python manage.py collect_ipxe_logs --limit 500
    ```

- [ ] **3.2 cleanup_ipxe_logs Command**
  - 檔案：`backend/api/management/commands/cleanup_ipxe_logs.py`
  - 測試：
    ```bash
    docker exec nt-django python manage.py cleanup_ipxe_logs --days 7
    ```

- [ ] **3.3 配置 Cron**
  - 編輯：`crontab -e`
  - 配置：
    ```
    */10 * * * * docker exec nt-django python manage.py collect_ipxe_logs --limit 1000
    0 2 * * * docker exec nt-django python manage.py cleanup_ipxe_logs --days 7
    ```
  - 驗證：`crontab -l`

---

### Phase 4：前端頁面 (0/5)

- [ ] **4.1 IPXEManagementPage.js**
  - 檔案：`frontend/src/pages/IPXEManagementPage.js`
  - 參考：`DHCPServerManagementPage.js`
  - 組件：
    - [ ] 伺服器列表 Table
    - [ ] 新增/編輯 Modal
    - [ ] 刪除 Popconfirm
    - [ ] 同步日誌按鈕
  - API 端點：
    - [ ] GET `/api/ipxe-servers/`
    - [ ] POST `/api/ipxe-servers/`
    - [ ] PUT `/api/ipxe-servers/<id>/`
    - [ ] DELETE `/api/ipxe-servers/<id>/`
    - [ ] POST `/api/ipxe-servers/<id>/sync-logs/`

- [ ] **4.2 IPXEAnalyticsPage.js**
  - 檔案：`frontend/src/pages/IPXEAnalyticsPage.js`
  - 參考：`DHCPAnalyticsPage.js`
  - 組件：
    - [ ] 統計卡片（Statistic）
    - [ ] 日誌列表 Table
    - [ ] 伺服器選擇器 Select
    - [ ] 過濾器（類型、操作、時間）
  - API 端點：
    - [ ] GET `/api/ipxe-analytics/overview/`
    - [ ] GET `/api/ipxe-logs/`
  - 功能：
    - [ ] 自動刷新（10分鐘）
    - [ ] 分頁
    - [ ] 過濾和搜尋

- [ ] **4.3 更新 Sidebar.js**
  - 檔案：`frontend/src/components/Sidebar.js`
  - 添加菜單項：
    ```javascript
    {
        key: 'ipxe-management',
        icon: <CloudServerOutlined />,
        label: 'IPXE 管理',
    }
    ```

- [ ] **4.4 更新 App.js**
  - 檔案：`frontend/src/App.js`
  - 添加路由：
    ```javascript
    <Route path="/admin/ipxe-management" element={<IPXEManagementPage />} />
    <Route path="/ipxe-analytics" element={<IPXEAnalyticsPage />} />
    ```

- [ ] **4.5 前端測試**
  - [ ] 訪問 http://localhost/admin/ipxe-management
  - [ ] 測試新增伺服器
  - [ ] 測試編輯伺服器
  - [ ] 測試刪除伺服器
  - [ ] 測試手動同步
  - [ ] 訪問 http://localhost/ipxe-analytics
  - [ ] 測試日誌過濾
  - [ ] 驗證自動刷新

---

### Phase 5：測試和優化 (0/5)

- [ ] **5.1 端對端測試**
  - [ ] 完整流程測試（新增伺服器 → 同步日誌 → 查看分析）
  - [ ] 多伺服器測試
  - [ ] 錯誤情境測試（SSH 失敗、容器不存在等）

- [ ] **5.2 性能優化**
  - [ ] 日誌收集效率（目標：每台 < 10秒）
  - [ ] 數據庫查詢優化（索引、分頁）
  - [ ] 前端渲染優化（虛擬滾動？）

- [ ] **5.3 錯誤處理**
  - [ ] SSH 連接失敗處理
  - [ ] Docker 命令失敗處理
  - [ ] 日誌解析異常處理
  - [ ] 前端錯誤提示完善

- [ ] **5.4 日誌記錄**
  - [ ] 後端操作日誌（INFO, ERROR）
  - [ ] 同步成功/失敗記錄
  - [ ] 性能監控日誌

- [ ] **5.5 文檔更新**
  - [ ] 更新 README.md
  - [ ] 添加 API 文檔
  - [ ] 添加使用說明
  - [ ] 添加故障排查指南

---

## 🔍 驗收標準

### 功能驗收

- [ ] 可以管理多台 IPXE 伺服器（新增、編輯、刪除）
- [ ] 可以手動觸發日誌同步
- [ ] 日誌能正確解析並存儲到資料庫
- [ ] 前端可以查看最近 7 天的日誌
- [ ] 支援按伺服器、類型、操作過濾
- [ ] 自動刷新功能正常（10 分鐘）
- [ ] 定時任務正常執行（Cron）
- [ ] 舊日誌能自動清理（超過 7 天）

### 性能驗收

- [ ] 單台伺服器日誌收集時間 < 10 秒
- [ ] 日誌解析速率 > 1000 行/秒
- [ ] 前端頁面載入時間 < 2 秒
- [ ] 支援 1000+ 條日誌的流暢展示

### 用戶體驗驗收

- [ ] 界面與 DHCP Server 管理風格一致
- [ ] 操作流程直觀易懂
- [ ] 錯誤提示清晰友好
- [ ] 響應式設計（手機、平板、桌面）

---

## 📊 時間估計

| Phase | 任務數 | 預估時間 | 實際時間 |
|-------|--------|----------|----------|
| Phase 1 | 5 | 2-3 小時 | - |
| Phase 2 | 5 | 2-3 小時 | - |
| Phase 3 | 3 | 1-2 小時 | - |
| Phase 4 | 5 | 2-3 小時 | - |
| Phase 5 | 5 | 1-2 小時 | - |
| **總計** | **23** | **8-13 小時** | **-** |

---

## 🐛 已知問題和注意事項

### 需要確認的事項

1. **伺服器列表**
   - [ ] 確認所有 10.250.x.2 伺服器的 IP
   - [ ] 確認各伺服器的 SSH 認證資訊
   - [ ] 確認容器名稱是否統一

2. **日誌格式**
   - [ ] 確認所有伺服器的日誌格式一致
   - [ ] 確認是否有其他類型的日誌需要收集

3. **安全性**
   - [ ] SSH 密碼是否需要加密存儲
   - [ ] 是否需要支援 SSH Key 認證
   - [ ] 是否需要 IP 白名單限制

### 潛在風險

1. **SSH 連接穩定性**
   - 網路中斷可能導致同步失敗
   - 建議：實現重試機制

2. **日誌量過大**
   - 每台伺服器可能產生大量日誌
   - 建議：分批讀取、限制行數

3. **Docker 權限**
   - Sudo 密碼可能變更
   - 建議：提供密碼更新機制

---

## 📞 支援和資源

- **設計文檔**：`docs/features/ipxe-analysis/IPXE_MANAGEMENT_DESIGN.md`
- **測試腳本**：`test_ipxe_connection.py`
- **參考實現**：`DHCPServerManagementPage.js`, `DHCPAnalyticsPage.js`
- **相關服務**：`ipxe_service.py` 參考 `ssh_powershell_service.py`

---

**最後更新**：2025-10-29  
**維護者**：Network Toolbox Team  
**版本**：v1.0.0
