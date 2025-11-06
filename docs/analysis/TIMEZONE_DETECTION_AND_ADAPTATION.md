# Jenkins 時區檢測與自適應方案

## 📋 概述

本文檔說明如何檢測 Jenkins 伺服器的時區設定，並根據檢測結果自動選擇合適的時區處理策略。

---

## 🔍 如何檢測 Jenkins 時區

### 方法 1：執行 Groovy Script（最準確）✅

**需要權限**：Jenkins 管理員權限

**實現方式**：
```python
import requests

def detect_jenkins_timezone(server_url, username, password):
    """
    透過 Jenkins Script Console API 檢測時區
    """
    script_url = f"{server_url}/scriptText"
    
    groovy_script = """
import java.util.TimeZone

def tz = TimeZone.getDefault()
println "TIMEZONE_ID:" + tz.getID()
println "TIMEZONE_OFFSET:" + (tz.getRawOffset() / 3600000)
"""
    
    response = requests.post(
        script_url,
        data={'script': groovy_script},
        auth=(username, password),
        timeout=10,
        verify=False
    )
    
    if response.status_code == 200:
        lines = response.text.strip().split('\n')
        
        timezone_id = None
        offset_hours = None
        
        for line in lines:
            if 'TIMEZONE_ID:' in line:
                timezone_id = line.split(':', 1)[1].strip()
            if 'TIMEZONE_OFFSET:' in line:
                offset_hours = float(line.split(':', 1)[1].strip())
        
        return {
            'timezone_id': timezone_id,
            'offset_hours': offset_hours,
            'detected': True
        }
    
    return {'detected': False}

# 使用範例
result = detect_jenkins_timezone(
    'http://jenkins.example.com',
    'admin',
    'password'
)

if result['detected']:
    if result['timezone_id'] == 'Asia/Taipei':
        print("✅ Jenkins 使用 Taipei 時區")
        # 可以使用方案 B
    elif result['timezone_id'] in ['UTC', 'Etc/UTC']:
        print("✅ Jenkins 使用 UTC 時區")
        # 建議使用方案 A
    else:
        print(f"⚠️  Jenkins 使用 {result['timezone_id']} 時區")
        # 需要針對性處理
```

**優點**：
- ✅ 最準確
- ✅ 可以取得完整時區資訊
- ✅ 不受其他因素影響

**缺點**：
- ❌ 需要管理員權限
- ❌ 安全性考量（執行遠端代碼）

---

### 方法 2：檢查 Jenkins 啟動參數

**需要權限**：伺服器 SSH 存取權限

**實現方式**：
```bash
# 在 Jenkins 伺服器上執行
ps aux | grep jenkins | grep user.timezone

# 或者檢查 systemd service
systemctl cat jenkins | grep user.timezone

# 或者檢查環境變數
cat /etc/default/jenkins | grep JAVA_ARGS
```

**查找內容**：
```
-Duser.timezone=Asia/Taipei  # Taipei 時區
-Duser.timezone=UTC          # UTC 時區
```

**優點**：
- ✅ 準確
- ✅ 不需要 Jenkins API 權限

**缺點**：
- ❌ 需要伺服器存取權限
- ❌ 需要手動查看

---

### 方法 3：詢問系統管理員（最簡單）✅

**實現方式**：
1. 直接詢問 Jenkins 管理員
2. 或者登入 Jenkins UI 查看系統資訊

**Jenkins UI 查看方式**：
```
Jenkins → Manage Jenkins → System Information
搜尋：user.timezone
```

**優點**：
- ✅ 最簡單
- ✅ 最安全
- ✅ 不需要任何特殊權限

**缺點**：
- ❌ 需要人工查詢
- ❌ 無法自動化

---

### ⚠️ 方法 4：分析 Unix Timestamp（不可靠）❌

**為什麼不可靠**：

```python
# Jenkins API 回傳的是 Unix Timestamp（毫秒）
timestamp_ms = 1730800000000

# Unix Timestamp 代表的是「絕對時間點」
# 不論 Jenkins 使用什麼時區，這個數字都一樣！

# 範例
import datetime
import pytz

timestamp_sec = timestamp_ms / 1000

# 轉換為 UTC
dt_utc = datetime.fromtimestamp(timestamp_sec, tz=pytz.UTC)
print(dt_utc)  # 2024-11-05 09:46:40+00:00

# 轉換為 Taipei
dt_taipei = dt_utc.astimezone(pytz.timezone('Asia/Taipei'))
print(dt_taipei)  # 2024-11-05 17:46:40+08:00

# 結論：無法從 timestamp 判斷 Jenkins 的時區設定
```

**結論**：❌ **不要用這個方法**

---

## 🎯 自適應處理策略

### 策略 A：自動檢測並適配

```python
from api.models import JenkinsServer
import requests

class JenkinsTimezoneAdapter:
    """Jenkins 時區自適應器"""
    
    def __init__(self, server):
        self.server = server
        self.jenkins_timezone = self.detect_timezone()
    
    def detect_timezone(self):
        """檢測 Jenkins 時區"""
        try:
            # 方法 1：執行 Groovy Script
            result = self._detect_via_script()
            if result['detected']:
                return result['timezone_id']
        except:
            pass
        
        # 方法 2：從配置檔讀取（如果有儲存）
        if hasattr(self.server, 'timezone') and self.server.timezone:
            return self.server.timezone
        
        # 預設：假設使用 UTC
        return 'UTC'
    
    def _detect_via_script(self):
        """透過 Groovy Script 檢測"""
        script_url = f"{self.server.url}/scriptText"
        groovy_script = """
import java.util.TimeZone
def tz = TimeZone.getDefault()
println "TIMEZONE_ID:" + tz.getID()
"""
        
        response = requests.post(
            script_url,
            data={'script': groovy_script},
            auth=(self.server.username, self.server.password),
            timeout=10,
            verify=False
        )
        
        if response.status_code == 200:
            for line in response.text.strip().split('\n'):
                if 'TIMEZONE_ID:' in line:
                    timezone_id = line.split(':', 1)[1].strip()
                    return {
                        'detected': True,
                        'timezone_id': timezone_id
                    }
        
        return {'detected': False}
    
    def should_use_naive_datetime(self):
        """判斷是否應該使用 naive datetime（方案 B）"""
        return self.jenkins_timezone == 'Asia/Taipei'
    
    def get_recommended_settings(self):
        """取得建議的 Django 設定"""
        if self.jenkins_timezone == 'Asia/Taipei':
            return {
                'USE_TZ': False,
                'TIME_ZONE': 'Asia/Taipei',
                'strategy': 'B',
                'description': 'Jenkins 和資料庫都使用 Taipei 時區'
            }
        else:
            return {
                'USE_TZ': True,
                'TIME_ZONE': 'Asia/Taipei',
                'strategy': 'A',
                'description': '資料庫使用 UTC，顯示時轉換為 Taipei'
            }

# 使用範例
server = JenkinsServer.objects.first()
adapter = JenkinsTimezoneAdapter(server)

print(f"Jenkins 時區: {adapter.jenkins_timezone}")
print(f"建議設定: {adapter.get_recommended_settings()}")

if adapter.should_use_naive_datetime():
    print("✅ 可以使用方案 B（直接儲存 Taipei 時間）")
else:
    print("✅ 建議使用方案 A（儲存 UTC）")
```

---

### 策略 B：配置檔管理

**在 JenkinsServer Model 中新增欄位**：

```python
# backend/api/models.py

class JenkinsServer(models.Model):
    name = models.CharField(max_length=100)
    url = models.URLField()
    username = models.CharField(max_length=100)
    password = models.CharField(max_length=100)
    
    # 新增：時區設定
    timezone = models.CharField(
        max_length=50,
        default='UTC',
        choices=[
            ('UTC', 'UTC'),
            ('Asia/Taipei', 'Asia/Taipei (UTC+8)'),
            ('America/New_York', 'America/New_York (UTC-5/-4)'),
            # 其他時區...
        ],
        help_text='Jenkins 伺服器的時區設定'
    )
    
    # 新增：是否已檢測時區
    timezone_detected = models.BooleanField(
        default=False,
        help_text='是否已自動檢測時區'
    )
    
    # 新增：最後檢測時間
    timezone_detected_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='最後檢測時區的時間'
    )
```

**管理命令：檢測所有伺服器時區**：

```python
# backend/api/management/commands/detect_jenkins_timezones.py

from django.core.management.base import BaseCommand
from api.models import JenkinsServer
from datetime import datetime

class Command(BaseCommand):
    help = '檢測所有 Jenkins 伺服器的時區設定'
    
    def handle(self, *args, **options):
        servers = JenkinsServer.objects.all()
        
        for server in servers:
            self.stdout.write(f"檢測 {server.name}...")
            
            adapter = JenkinsTimezoneAdapter(server)
            detected_tz = adapter.jenkins_timezone
            
            if detected_tz and detected_tz != 'UTC':
                server.timezone = detected_tz
                server.timezone_detected = True
                server.timezone_detected_at = datetime.now()
                server.save()
                
                self.stdout.write(
                    self.style.SUCCESS(
                        f"  ✅ 檢測到時區：{detected_tz}"
                    )
                )
            else:
                self.stdout.write(
                    self.style.WARNING(
                        f"  ⚠️  使用預設時區：UTC"
                    )
                )
```

**執行檢測**：
```bash
docker exec nt-django python manage.py detect_jenkins_timezones
```

---

## 📊 決策流程圖

```
開始
  │
  ▼
檢測 Jenkins 時區
  │
  ├─ 成功檢測？
  │   │
  │   ├─ Yes → 時區 = Asia/Taipei？
  │   │         │
  │   │         ├─ Yes → ✅ 可以使用方案 B
  │   │         │         - USE_TZ = False
  │   │         │         - 直接儲存 Taipei 時間
  │   │         │         - 不需要時區轉換
  │   │         │
  │   │         └─ No → ✅ 使用方案 A
  │   │                   - USE_TZ = True
  │   │                   - 儲存 UTC
  │   │                   - 顯示時轉換
  │   │
  │   └─ No → ⚠️  無法檢測
  │             │
  │             └─ 詢問管理員
  │                 │
  │                 └─ 手動設定時區
  │
  ▼
完成
```

---

## ⚠️ 重要注意事項

### 1. Unix Timestamp 的誤區

```python
# ❌ 錯誤認知
"Jenkins 使用 Taipei 時區，所以 timestamp 是 Taipei 時間"

# ✅ 正確理解
"Jenkins 使用什麼時區都不影響 Unix Timestamp"
"Unix Timestamp 永遠代表 UTC 絕對時間點"

# 範例
timestamp = 1730800000  # Unix Timestamp

# 不論 Jenkins 設定什麼時區，這個數字都一樣！
# Jenkins UTC:    timestamp = 1730800000
# Jenkins Taipei: timestamp = 1730800000  # 一模一樣！

# 只是 Jenkins UI 顯示的「人類可讀時間」不同：
# Jenkins UTC:    2024-11-05 09:46:40
# Jenkins Taipei: 2024-11-05 17:46:40
```

### 2. 為什麼還要檢測時區？

**理由**：
1. **一致性**：如果 Jenkins 使用 Taipei，你的系統也用 Taipei，UI 顯示會一致
2. **簡化**：不需要時區轉換邏輯
3. **除錯**：對應 Jenkins UI 和你的系統 UI 更容易

**但是**：
- Unix Timestamp 的轉換邏輯完全不需要改變
- 資料庫儲存的邏輯才需要根據時區調整

### 3. 實際上不需要檢測的理由

```python
# 因為 Unix Timestamp 已經是絕對時間
# 所以無論 Jenkins 使用什麼時區：

# 步驟 1：從 Jenkins API 取得 timestamp
timestamp_ms = jenkins_api_response['timestamp']  # 例如 1730800000000

# 步驟 2：轉換為 UTC datetime（永遠正確）
timestamp_sec = timestamp_ms / 1000
dt_utc = datetime.fromtimestamp(timestamp_sec, tz=pytz.UTC)

# 步驟 3：儲存或顯示
# 方案 A：儲存 UTC，顯示時轉換 → USE_TZ=True
# 方案 B：儲存 Taipei → 轉換後儲存，USE_TZ=False

# 結論：檢測 Jenkins 時區只是為了「一致性」和「方便」
#       不是為了「正確性」
```

---

## 🎯 最終建議

### 建議 1：不需要檢測（推薦）✅

**理由**：
- Unix Timestamp 已經是絕對時間，不受 Jenkins 時區影響
- 使用方案 A（USE_TZ=True）可以處理任何 Jenkins 時區
- 實施成本最低，風險最小

**實施方式**：
```python
# settings.py
USE_TZ = True
TIME_ZONE = 'Asia/Taipei'

# 所有 Jenkins 時區都能正確處理：
# - Jenkins UTC → 正確 ✅
# - Jenkins Taipei → 正確 ✅
# - Jenkins 任何時區 → 正確 ✅
```

### 建議 2：如果一定要檢測

**前提條件**：
1. ✅ 確認 Jenkins 使用 **Asia/Taipei** 時區
2. ✅ 未來不會支援其他時區
3. ✅ 願意承擔方案 B 的風險和成本

**檢測方式**：
1. **一次性手動檢查**（推薦）
   - 登入 Jenkins UI → System Information
   - 查看 `user.timezone` 設定
   - 在配置檔記錄結果

2. **自動檢測**（需要管理員權限）
   - 使用 Groovy Script API
   - 定期檢測並更新配置

**實施步驟**：
```bash
# 1. 檢測 Jenkins 時區
python manage.py detect_jenkins_timezones

# 2. 根據結果決定設定
if timezone == 'Asia/Taipei':
    USE_TZ = False  # 方案 B
else:
    USE_TZ = True   # 方案 A
```

---

## 📝 總結

| 方案 | 需要檢測？ | 相容性 | 推薦度 |
|------|-----------|--------|--------|
| **方案 A（USE_TZ=True）** | ❌ 不需要 | 所有時區 | ⭐⭐⭐⭐⭐ |
| **方案 B（USE_TZ=False）** | ✅ 必須 | 僅 Taipei | ⭐⭐ |

**最終建議**：
- ✅ **使用方案 A**，不需要檢測 Jenkins 時區
- ✅ Unix Timestamp 已經解決了時區問題
- ✅ 檢測時區只是為了「一致性」，不是「必要性」

---

**相關文檔**：
- [時區配置選項比較](./TIMEZONE_OPTIONS_COMPARISON.md)
- [時區處理指南](../development/TIMEZONE_GUIDE.md)
- [UTC/Taipei 相容性分析](./TIMEZONE_ANALYSIS.md)

