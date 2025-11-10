# NAS Jenkins 存儲分析報告

## 📅 分析日期
**2025-11-10**

---

## 🔍 問題描述

用戶觀察到 NAS 上的 Jenkins 伺服器資料夾和 Job 資料夾數量似乎較少，懷疑可能有問題。

**NAS 路徑**：`/mnt/mdt/Team/PQ1-3/tool/jenkins_test_storage/`

---

## 📊 現狀分析

### 1. 資料庫統計

| 項目 | 數量 |
|------|------|
| **Jenkins 伺服器** | 2 個 |
| **Jenkins Jobs** | 246 個 |
| **Jenkins Builds** | 859 個 |

**伺服器詳情**：
- **10.252.170.187**: 202 jobs（資料庫記錄）
- **Performance**: 44 jobs（資料庫記錄）

---

### 2. NAS 存儲現況

#### 伺服器資料夾
```
/mnt/mdt/Team/PQ1-3/tool/jenkins_test_storage/
├── 10.252.170.187/     ← 有資料
└── 10.252.170.188/     ← 有資料
```

**發現問題**：
- ❌ **Performance 伺服器**（資料庫中有 44 個 Jobs）在 NAS 上沒有對應資料夾
- ✅ **10.252.170.187** 和 **10.252.170.188** 有資料夾

#### Job 資料夾統計

**10.252.170.187**（共 10 個 Job 資料夾）：
1. FW_QA_Secondary_Seed - 1 個 Build
2. SAF3202_KVM03 - 2 個 Builds (17, 18)
3. SAF3208_KVM06 - 2 個 Builds (31, 32)
4. SAF3208_KVM07 - 1 個 Build (34)
5. SAF3211_KVM11 - 1 個 Build (30)
6. SAF3211_KVM13 - 2 個 Builds (25, 26)
7. SAF3211_KVM14 - 1 個 Build (28)
8. SAF3212_KVM08 - 1 個 Build (26)
9. SAF3213_KVM02 - 1 個 Build (28)
10. SAF3213_KVM07 - 1 個 Build (28)

**總計**：約 13 個 Builds 有儲存

**10.252.170.188**（共 14 個 Job 資料夾）：
1. PC51Q_seed
2. SAF7522_K07
3. SAF7522_K08
4. SAF7522_K10
5. SAF7522_K11
6. SAF7522_K13
7. SAF7523_K04
8. SAF7523_K06
9. SAF7523_K09
10. SAF7523_K10
11. SAF7523_K13
12. SAF7523_K14
13. SAF7526_K12
14. SAF7526_K13
15. SAF7526_K14

---

### 3. Build 存儲內容檢查

**範例檢查**：`10.252.170.187/SAF3202_KVM03/18/`

**存儲內容**：
```
SAF3202_KVM03/18/
└── workspace/          ← 只有 workspace
    └── [完整的 workspace 檔案結構]
```

**問題發現**：
- ✅ **Workspace 已存儲**：完整的 Ansible 專案結構
- ❌ **缺少 config.xml**：Build 配置檔案未存儲
- ❌ **缺少 log.txt**：Build 日誌未存儲

---

## 🔴 問題總結

### 1. **伺服器資料夾不一致**
- **資料庫**：有 `10.252.170.187` 和 `Performance` 兩個伺服器
- **NAS**：只有 `10.252.170.187` 和 `10.252.170.188` 資料夾
- **問題**：資料庫中的伺服器名稱與實際 IP 不匹配

### 2. **Job 數量差異巨大**
- **資料庫**：202 個 Jobs（10.252.170.187）
- **NAS 存儲**：只有 10 個 Job 資料夾有資料
- **比例**：只有 **4.95%** 的 Jobs 有實際存儲資料

### 3. **Build 數量差異**
- **資料庫**：859 個 Builds
- **NAS 存儲**：大約只有 20-30 個 Builds 有實際檔案
- **比例**：只有 **2.3% - 3.5%** 的 Builds 被存儲

### 4. **存儲內容不完整**
- ✅ **Workspace**：有存儲
- ❌ **config.xml**：未存儲
- ❌ **log.txt**：未存儲

---

## 🎯 原因分析

### 1. **存儲功能尚未全面啟用**

根據代碼檢查，Jenkins 存儲功能是需要**手動觸發**的：

```python
# backend/api/views/jenkins.py
@action(detail=True, methods=['post'])
def store_workspace(self, request, pk=None):
    """手動存儲 Workspace"""
    # 這是一個手動觸發的 API
```

**結論**：
- ✅ 功能已實現
- ❌ **沒有自動存儲機制**（需要手動 POST 請求）
- ❌ 只有少數 Builds 被手動觸發存儲

### 2. **資料庫 IP 地址欄位為空**

```python
# 資料庫查詢結果
10.252.170.187: IP=None  # ← IP 欄位未填寫
Performance: IP=None     # ← IP 欄位未填寫
```

**問題**：
- 伺服器的 `ip_address` 欄位是 `null`
- NAS 資料夾名稱使用的是實際 IP（10.252.170.187, 10.252.170.188）
- 資料庫中的伺服器名稱無法對應到 NAS 資料夾

### 3. **存儲選擇性**

從存儲的 Builds 來看：
- 只存儲了**最近的少數 Builds**
- 可能是測試或開發時手動觸發的
- 沒有批量存儲歷史 Builds

### 4. **伺服器配置問題**

**猜測**：
- `Performance` 伺服器可能就是 `10.252.170.188`
- 但因為資料庫中名稱是 "Performance"，所以無法正確對應
- 需要確認實際的 IP 對應關係

---

## ✅ 結論

**這不是 Bug，而是正常的開發階段狀態：**

1. **功能正常**：
   - ✅ NAS 掛載正常
   - ✅ 存儲服務正常運作
   - ✅ Workspace 存儲功能正常

2. **存儲比例低的原因**：
   - ⚠️ 存儲功能是**手動觸發**，不是自動的
   - ⚠️ 只有測試時手動觸發的 Builds 被存儲
   - ⚠️ 沒有批量存儲歷史記錄的機制

3. **內容不完整的原因**：
   - ⚠️ 目前只實現了 **Workspace 存儲**
   - ⚠️ **config.xml** 和 **log.txt** 存儲可能尚未實現或未觸發

---

## 🚀 建議改進

### 1. **實現自動存儲機制**

**優先級**：🔴 高

```python
# 建議使用 Celery 定時任務
@shared_task
def auto_store_jenkins_builds():
    """自動存儲新的 Jenkins Builds"""
    # 找出未存儲的 Builds
    builds = JenkinsBuild.objects.filter(
        is_workspace_stored=False,
        result__in=['SUCCESS', 'FAILURE', 'UNSTABLE']  # 排除正在構建的
    )
    
    for build in builds:
        # 觸發存儲
        store_workspace_task.delay(build.id)
```

**時機選擇**：
- **選項 A**：Build 完成時自動觸發（即時性）
- **選項 B**：定時任務掃描未存儲的 Builds（批量處理）
- **選項 C**：混合方式（新 Builds 即時存儲 + 定時補掃）

### 2. **修正伺服器 IP 配置**

**優先級**：🟡 中

```python
# 更新資料庫中的 IP 地址
from api.models import JenkinsServer

# 方案 A：根據 URL 解析 IP
server = JenkinsServer.objects.get(name='10.252.170.187')
# 從 server.url 解析並填寫 IP

# 方案 B：手動設定
JenkinsServer.objects.filter(name='Performance').update(
    ip_address='10.252.170.188'
)
```

### 3. **完善存儲內容**

**優先級**：🟢 低

目前只存儲 **Workspace**，建議補充：

```python
# library/services/jenkins_storage_service.py
def store_build_complete_data(self):
    """存儲完整的 Build 資料"""
    self.store_workspace()       # ✅ 已實現
    self.store_config_xml()      # ⚠️ 待實現
    self.store_log_file()        # ⚠️ 待實現
    self.store_test_results()    # ⚠️ 待實現（如果有）
```

### 4. **批量存儲歷史 Builds**

**優先級**：🟢 低（可選）

```bash
# 創建管理命令
python manage.py backfill_jenkins_storage --server 10.252.170.187 --limit 100
```

**注意事項**：
- ⚠️ 會佔用大量 NAS 空間
- ⚠️ 需要評估存儲策略（保留多久、保留哪些狀態）
- ⚠️ 可能需要時間較長

### 5. **添加存儲策略配置**

**優先級**：🟡 中

```python
# settings.py
JENKINS_STORAGE_POLICY = {
    'auto_store': True,              # 是否自動存儲
    'store_workspace': True,          # 存儲 Workspace
    'store_config': True,             # 存儲 config.xml
    'store_logs': True,               # 存儲日誌
    'retention_days': 90,             # 保留天數
    'store_results': ['FAILURE'],     # 只存儲失敗的（或全部）
    'max_workspace_size_mb': 500,     # 單個 Workspace 大小限制
}
```

---

## 📈 存儲容量規劃

### 當前使用量估算

**假設**：
- 每個 Workspace 平均 **50 MB**
- 當前約 **25 個 Builds** 已存儲
- **當前使用量**：約 **1.25 GB**

### 全量存儲估算

如果存儲所有 859 個 Builds：
- **預估容量**：859 × 50 MB = **42.95 GB**
- **加上配置和日誌**：約 **50 GB**

### 月度增量估算

假設每天新增 10 個 Builds：
- **每日增量**：10 × 50 MB = **500 MB**
- **每月增量**：約 **15 GB**

**建議**：
- ✅ NAS 空間充足（預留 **100 GB** 以上）
- ⚠️ 建議設定**保留期限**（如 90 天）
- ⚠️ 定期清理舊的存儲檔案

---

## 🔧 快速驗證步驟

### 1. 確認伺服器 IP 對應

```bash
docker exec nt-django python manage.py shell -c "
from api.models import JenkinsServer
for s in JenkinsServer.objects.all():
    print(f'Name: {s.name}')
    print(f'URL: {s.url}')
    print(f'IP: {s.ip_address}')
    print('---')
"
```

### 2. 測試手動存儲

```bash
# 找一個未存儲的 Build
curl -X POST http://localhost/api/jenkins-builds/{build_id}/store_workspace/
```

### 3. 檢查存儲結果

```bash
# 查看 NAS 上的檔案
ls -lah /mnt/mdt/Team/PQ1-3/tool/jenkins_test_storage/{server_ip}/{job_name}/{build_number}/
```

---

## 📝 總結

### ✅ 沒有問題的部分
1. NAS 掛載正常
2. 存儲服務功能正常
3. 已存儲的資料完整（Workspace 部分）

### ⚠️ 需要改進的部分
1. **存儲比例低**：只有 2-5% 的 Builds 被存儲
2. **手動觸發**：需要實現自動存儲機制
3. **內容不完整**：只有 Workspace，缺少 config 和 log
4. **IP 配置問題**：資料庫 IP 欄位為空

### 🎯 建議優先級
1. 🔴 **高優先級**：實現自動存儲機制（Celery 任務）
2. 🟡 **中優先級**：修正伺服器 IP 配置、添加存儲策略
3. 🟢 **低優先級**：完善存儲內容（config.xml, log.txt）、批量存儲歷史

---

**分析完成日期**：2025-11-10  
**分析執行者**：GitHub Copilot  
**系統狀態**：✅ 正常運作（功能未全面啟用）
