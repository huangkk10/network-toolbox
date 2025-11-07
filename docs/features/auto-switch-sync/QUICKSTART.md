# 📘 自動 Switch 同步 - 快速開始

## 🎯 問題回答

**問題**：「以後我如果新加一個 DHCP Server，還會出現這樣的問題嗎？如何改善？」

**答案**：✅ **不會了！系統已經實施自動化機制。**

---

## ✨ 已實施的改善

### 自動化機制

當您新增一個 DHCP Server 時，系統會自動：

1. ⏰ **10 秒後**：自動同步 DHCP Scope 配置
2. ⏰ **60 秒後**：自動識別 Switch 設備
3. 📊 **自動更新**：Switch 統計資訊
4. ✅ **自動顯示**：Switch 出現在管理頁面

**您完全不需要手動操作「立即同步」按鈕！**

---

## 🚀 使用方式

### 正常使用（自動化）

```
1. 在前端新增 DHCP Server
   └─ 填寫資訊：名稱、IP、SSH 憑證等
   
2. 點擊「儲存」
   └─ 系統自動觸發後台任務
   
3. 等待 1-2 分鐘
   └─ 喝杯咖啡 ☕
   
4. 重新整理 Switch 管理頁面
   └─ ✅ Switch 自動出現！
```

### 快速測試

想驗證自動化是否正常工作？

```bash
# 執行測試腳本（約需 2 分鐘）
./test_auto_switch_sync.sh
```

這個腳本會：
- ✅ 創建測試 DHCP Server
- ✅ 驗證信號觸發
- ✅ 等待 Switch 識別
- ✅ 驗證結果
- ✅ 清理測試數據

---

## 📋 前提條件

自動化機制需要以下服務運行：

```bash
# 檢查服務狀態
docker compose ps

# 必須運行的服務：
✅ nt-django         (Django 後端)
✅ nt-celery-worker  (Celery Worker)
✅ nt-celery-beat    (定時任務調度)
```

如果服務未運行：

```bash
# 啟動所有服務
docker compose up -d

# 或單獨啟動
docker compose up -d celery_worker celery_beat
```

---

## 🔍 監控自動化

### 查看自動化日誌

```bash
# 監控 Django 信號觸發
docker compose logs django -f | grep "\[Signal\]"

# 監控 Celery 任務執行
docker compose logs celery_worker -f | grep "auto_identify_switches"
```

### 預期看到的日誌

**創建 Server 後 10 秒內**：
```
[Signal] 偵測到新建 DHCP Server: YOUR-SERVER (10.250.X.X)
[Signal] 排程 Scope 初始同步任務 - Server ID: X
[Signal] 排程 Switch 自動識別任務 - Server ID: X
```

**創建 Server 後 60 秒內**：
```
[Celery] 開始 Switch 自動識別 - Server ID: X
[Celery] 找到 X 個 Switch 設備
[Celery] 創建: X, 更新: 0
```

---

## 🐛 如果出現問題

### 問題：Switch 沒有自動出現

**步驟 1**：檢查 Celery 服務

```bash
docker compose ps celery_worker

# 如果沒運行
docker compose up -d celery_worker
```

**步驟 2**：檢查租約中是否有 Switch

```bash
docker exec nt-django python manage.py shell -c "
from api.models import DHCPServer, DHCPLease
from api.serializers import DHCPLeaseSerializer

server = DHCPServer.objects.get(ip_address='YOUR_SERVER_IP')
switch_vendors = ['Cisco', 'HP', 'Zyxel', 'D-Link']

count = 0
for lease in DHCPLease.objects.filter(server=server)[:100]:
    serializer = DHCPLeaseSerializer(lease)
    vendor = serializer.data.get('vendor', '')
    if any(v.lower() in vendor.lower() for v in switch_vendors):
        print(f'{lease.ip_address}: {vendor}')
        count += 1

print(f'\n找到 {count} 個 Switch 設備')
"
```

**步驟 3**：手動觸發識別

```python
# 在 Django Shell 中執行
from api.signals import trigger_switch_identification_for_server

task_id = trigger_switch_identification_for_server(
    server_id=YOUR_SERVER_ID,  # 替換成您的 Server ID
    delay_seconds=5
)

print(f"Task ID: {task_id}")
```

---

## 📚 詳細文檔

| 文檔 | 說明 | 路徑 |
|------|------|------|
| 📖 完整說明 | 自動化機制的完整技術說明 | [README.md](./README.md) |
| 🧪 測試指南 | 詳細的測試案例和步驟 | [TESTING_GUIDE.md](./TESTING_GUIDE.md) |
| 📊 解決方案總結 | 問題分析和解決過程 | [SOLUTION_SUMMARY.md](./SOLUTION_SUMMARY.md) |

---

## 🎉 總結

### 改善前 vs 改善後

| 操作 | 改善前 | 改善後 |
|------|--------|--------|
| 新增 Server | ✅ 手動建立 | ✅ 手動建立 |
| Switch 識別 | ❌ **手動點擊「立即同步」** | ✅ **自動識別** |
| 等待時間 | 5-10 分鐘 | 1-2 分鐘 |
| 人工介入 | **需要** | **不需要** |

### 核心優勢

✅ **完全自動化** - 無需手動操作  
✅ **省時省力** - 節省 80% 的時間  
✅ **避免遺漏** - 系統自動處理  
✅ **容錯機制** - 失敗自動重試  
✅ **完整日誌** - 可追蹤每個步驟

---

## 💡 提示

1. **首次使用**：建議先執行測試腳本驗證功能
2. **正常使用**：新增 Server 後等待 1-2 分鐘再檢查
3. **遇到問題**：查看日誌或使用手動觸發方法
4. **性能考量**：延遲時間已經過優化，無需調整

---

**版本**：1.0  
**更新日期**：2025-11-07  
**狀態**：✅ 已實施並測試  
**維護者**：Network Toolbox Team
