# IPXE 網路品質監控 - 驗證檢查清單

## ✅ 功能驗證步驟

### 1. 後端 API 驗證

#### 1.1 檢查資料庫遷移
```bash
docker exec nt-django python manage.py showmigrations api | grep ipxenetworkquality
```
**預期結果**：顯示 `[X] 0016_ipxenetworkquality`

#### 1.2 測試統計 API
```bash
curl -s http://localhost/api/ipxe-network-quality/statistics/ | python3 -m json.tool | head -30
```
**預期結果**：返回 JSON 包含 `summary`, `daily_stats`, `hourly_stats`, `quality_trends`

#### 1.3 測試列表 API
```bash
curl -s http://localhost/api/ipxe-network-quality/ | python3 -m json.tool | head -20
```
**預期結果**：返回記錄陣列，包含所有測試指標

#### 1.4 檢查 Cron 任務
```bash
crontab -l | grep check_ipxe_network
```
**預期結果**：`*/5 * * * * /home/owner/Codes/network-toolbox/scripts/check_ipxe_network.sh`

#### 1.5 查看 Cron 日誌
```bash
tail -20 /home/owner/Codes/network-toolbox/logs/ipxe_network_cron.log
```
**預期結果**：顯示最近的執行記錄，包含測試結果

### 2. 前端頁面驗證

#### 2.1 檢查路由配置
```bash
grep -n "ipxe-network-quality" /home/owner/Codes/network-toolbox/frontend/src/App.js
```
**預期結果**：顯示路由定義行號

#### 2.2 檢查選單項目
```bash
grep -A 2 "ipxe-network-quality" /home/owner/Codes/network-toolbox/frontend/src/components/Sidebar.js
```
**預期結果**：顯示選單配置

#### 2.3 檢查頁面檔案
```bash
ls -lh /home/owner/Codes/network-toolbox/frontend/src/pages/IPXENetworkQualityPage.js
```
**預期結果**：檔案存在且大小 > 10KB

#### 2.4 React 編譯狀態
```bash
docker compose logs react --tail 10
```
**預期結果**：`webpack compiled with warnings` 或 `webpack compiled successfully`

### 3. 網頁瀏覽器測試

#### 3.1 訪問監控頁面
1. 開啟瀏覽器訪問：`http://localhost/ipxe-network-quality`
2. 確認頁面標題：「IPXE 網路品質監控」
3. 確認側邊欄選單有「IPXE 網路品質」項目

#### 3.2 檢查統計卡片
- [ ] 總檢測次數
- [ ] 成功率（%）
- [ ] 平均 Ping 延遲（ms）
- [ ] 平均丟包率（%）
- [ ] 平均 HTTP 響應時間（ms）
- [ ] 平均 SSH 響應時間（ms）
- [ ] 平均下載速度（MB/s）

#### 3.3 檢查圖表顯示
- [ ] Ping 延遲趨勢圖
- [ ] 響應時間對比圖（HTTP vs SSH）
- [ ] 丟包率趨勢圖
- [ ] 下載速度趨勢圖

#### 3.4 檢查記錄表格
- [ ] 時間欄位
- [ ] 狀態標籤（正常/部分失敗/失敗）
- [ ] Ping 延遲
- [ ] 丟包率
- [ ] HTTP 響應時間
- [ ] HTTP 狀態碼
- [ ] SSH 響應時間
- [ ] SSH 連接狀態
- [ ] 下載速度
- [ ] 錯誤訊息

#### 3.5 測試互動功能
- [ ] 時間範圍選擇器（1/3/7/14 天）
- [ ] 表格排序功能
- [ ] 表格篩選功能
- [ ] 表格分頁功能
- [ ] 頁面自動刷新（每 30 秒）

### 4. 服務層測試

#### 4.1 手動執行網路品質檢測
```bash
docker exec nt-django python manage.py shell -c "
from api.ipxe_network_service import record_ipxe_network_quality
result = record_ipxe_network_quality()
print('檢測結果:', result)
"
```
**預期結果**：顯示檢測結果摘要

#### 4.2 檢查資料庫記錄
```bash
docker exec nt-django python manage.py shell -c "
from api.models import IPXENetworkQuality
count = IPXENetworkQuality.objects.count()
latest = IPXENetworkQuality.objects.order_by('-timestamp').first()
print(f'總記錄數: {count}')
print(f'最新記錄: {latest.timestamp} - {latest.status}')
if latest.http_response_time:
    print(f'HTTP 響應: {latest.http_response_time:.2f} ms')
if latest.ssh_response_time:
    print(f'SSH 響應: {latest.ssh_response_time:.2f} ms')
"
```
**預期結果**：顯示資料庫中的記錄數量和最新記錄

### 5. 日誌系統驗證

#### 5.1 檢查日誌檔案
```bash
ls -lh /home/owner/Codes/network-toolbox/logs/ipxe_network_cron.log
```
**預期結果**：檔案存在

#### 5.2 監控即時日誌
```bash
tail -f /home/owner/Codes/network-toolbox/logs/ipxe_network_cron.log
```
**預期結果**：每 5 分鐘新增一筆記錄

#### 5.3 檢查 Django 日誌
```bash
grep "IPXE 網路品質" /home/owner/Codes/network-toolbox/logs/django.log | tail -10
```
**預期結果**：顯示相關操作日誌

### 6. 容器健康檢查

#### 6.1 檢查 Django 容器
```bash
docker exec nt-django python -c "
from api.ipxe_network_service import ping_test, http_test, ssh_test
print('服務層模組載入成功')
"
```
**預期結果**：`服務層模組載入成功`

#### 6.2 檢查依賴套件
```bash
docker exec nt-django python -c "
import requests
import paramiko
print('requests 版本:', requests.__version__)
print('paramiko 版本:', paramiko.__version__)
"
```
**預期結果**：顯示版本號

### 7. 已知問題驗證

#### 7.1 檢查 Ping 工具
```bash
docker exec nt-django which ping
```
**目前狀態**：應返回錯誤（未安裝）

**安裝方式**（可選）：
```bash
docker exec -u root nt-django apt-get update
docker exec -u root nt-django apt-get install -y iputils-ping
```

#### 7.2 驗證容錯機制
即使 Ping 失敗，其他測試應仍正常運行：
```bash
docker exec nt-django python manage.py shell -c "
from api.ipxe_network_service import check_ipxe_network_quality
from api.models import IPXEServer
server = IPXEServer.objects.first()
result = check_ipxe_network_quality(server)
print('狀態:', result['status'])
print('HTTP 測試:', 'OK' if result.get('http_response_time') else 'FAILED')
print('SSH 測試:', 'OK' if result.get('ssh_response_time') else 'FAILED')
"
```
**預期結果**：HTTP 和 SSH 測試應顯示 OK

## 📝 問題排查

### 問題 1：API 返回空數據

**原因**：尚未執行過網路品質檢測

**解決**：
```bash
# 手動執行一次檢測
docker exec nt-django python manage.py shell -c "
from api.ipxe_network_service import record_ipxe_network_quality
record_ipxe_network_quality()
"

# 等待 5 分鐘，讓 Cron 自動執行
```

### 問題 2：前端頁面顯示「未找到 IPXE 伺服器」

**原因**：資料庫中沒有 IPXE 伺服器記錄

**解決**：
1. 訪問「IPXE Server 管理」頁面
2. 添加 IPXE 伺服器資訊

### 問題 3：所有測試都顯示失敗

**檢查步驟**：
1. 確認 IPXE 伺服器 IP 正確
2. 確認 SSH 憑證正確
3. 檢查網路連通性
4. 查看錯誤訊息欄位

### 問題 4：圖表沒有數據

**原因**：數據點不足或時間範圍過大

**解決**：
- 縮短時間範圍（選擇 1 天或 3 天）
- 等待更多數據累積（每 5 分鐘一筆）

## ✨ 優化建議

### 1. 安裝 Ping 工具
```bash
# 編輯 backend/Dockerfile
# 在 RUN pip install 之前添加：
RUN apt-get update && \
    apt-get install -y iputils-ping && \
    rm -rf /var/lib/apt/lists/*

# 重建容器
docker compose up -d --build django
```

### 2. 設置告警閾值
在未來版本中，可以考慮添加：
- 成功率低於 95% 時發送通知
- Ping 延遲超過 100ms 時警告
- 丟包率超過 5% 時警告

### 3. 數據清理
設置定期清理舊數據：
```bash
# 添加到 crontab
0 2 * * 0 docker exec nt-django python manage.py shell -c "
from api.ipxe_network_service import cleanup_old_records
cleanup_old_records(days=30)
" >> /home/owner/Codes/network-toolbox/logs/cleanup.log 2>&1
```

## 📚 相關資源

- [使用說明](./README.md)
- [完整實施報告](./IMPLEMENTATION_REPORT.md)
- [系統部署文檔](../../deployment/DEPLOYMENT.md)

---

**驗證完成日期**：_____________  
**驗證人員**：_____________  
**備註**：_____________
