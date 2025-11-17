# Build Configuration Validator - 自動觸發功能

## 📋 功能概述

當 Jenkins Build 非成功狀態時（不是 `SUCCESS`），Build Configuration Validator 會自動檢測並標記為自動觸發的驗證，幫助快速定位配置問題。

## ✨ 功能特性

### 1. 自動檢測非成功的 Build

- 當 Build 狀態**不是 SUCCESS** 時，自動標記為自動觸發
- 涵蓋所有非成功狀態：`FAILURE`、`UNSTABLE`、`ABORTED`、`NOT_BUILT`、`BUILDING`
- 在日誌中記錄警告訊息：`⚠️ Build {id} has {status} status (not SUCCESS), automatically triggering...`
- 可透過參數控制是否啟用（預設：開啟）

### 2. 驗證結果增強

在 `validation_results` 中新增兩個欄位：

```python
{
    'build_result': 'FAILURE',      # Build 的狀態 (SUCCESS/FAILURE/UNSTABLE/ABORTED/NOT_BUILT/BUILDING)
    'auto_triggered': True,         # 是否為自動觸發 (True/False)
    'overall_status': 'success',    # 整體驗證狀態
    'config_source': 'ansible_inventory',
    'checks': { ... },
    'summary': { ... }
}
```

### 3. 可配置參數

```python
BuildConfigValidator(
    build_id=1723,
    dhcp_server_ids=None,           # 可選：指定 DHCP 伺服器
    auto_check_on_failure=True      # 預設：開啟自動觸發
)
```

## 📝 使用方式

### 基本用法（預設開啟自動觸發）

```python
from library.services.build_config_validator import BuildConfigValidator

# 驗證 Build 配置
validator = BuildConfigValidator(build_id=1723)
result = validator.validate()

# 檢查是否為自動觸發
if result['auto_triggered']:
    print(f"⚠️ Build {result['build_result']} - 自動觸發配置檢查")
```

### 關閉自動觸發

```python
# 關閉自動觸發功能
validator = BuildConfigValidator(
    build_id=1723,
    auto_check_on_failure=False  # 關閉自動觸發
)
result = validator.validate()

# auto_triggered 將永遠為 False
```

### 指定 DHCP 伺服器

```python
# 指定特定的 DHCP 伺服器進行驗證
validator = BuildConfigValidator(
    build_id=1723,
    dhcp_server_ids=[1, 2, 3],
    auto_check_on_failure=True
)
result = validator.validate()
```

## 🧪 測試案例

### 測試案例 1: 成功的 Build（不觸發）

```python
validator = BuildConfigValidator(build_id=2161)  # SUCCESS Build
result = validator.validate()

assert result['build_result'] == 'SUCCESS'
assert result['auto_triggered'] == False  # ✅ 不觸發
```

**預期行為**：
- ✅ `auto_triggered = False`
- ✅ 無警告訊息
- ✅ 正常執行配置驗證

### 測試案例 2: 失敗的 Build（自動觸發）

```python
validator = BuildConfigValidator(build_id=1723)  # FAILURE Build
result = validator.validate()

assert result['build_result'] == 'FAILURE'
assert result['auto_triggered'] == True  # ✅ 自動觸發
```

**預期行為**：
- ✅ `auto_triggered = True`
- ✅ 日誌記錄警告訊息
- ✅ 正常執行配置驗證

### 測試案例 3: 不穩定的 Build（自動觸發）

```python
validator = BuildConfigValidator(build_id=1530)  # UNSTABLE Build
result = validator.validate()

assert result['build_result'] == 'UNSTABLE'
assert result['auto_triggered'] == True  # ✅ 自動觸發
```

**預期行為**：
- ✅ `auto_triggered = True`
- ✅ 日誌記錄警告訊息
- ✅ 正常執行配置驗證

### 測試案例 4: 中止的 Build（自動觸發）

```python
validator = BuildConfigValidator(build_id=1303)  # ABORTED Build
result = validator.validate()

assert result['build_result'] == 'ABORTED'
assert result['auto_triggered'] == True  # ✅ 自動觸發
```

**預期行為**：
- ✅ `auto_triggered = True`
- ✅ 日誌記錄警告訊息
- ✅ 正常執行配置驗證

### 測試案例 5: 關閉自動觸發

```python
validator = BuildConfigValidator(
    build_id=1723,  # FAILURE Build
    auto_check_on_failure=False
)
result = validator.validate()

assert result['build_result'] == 'FAILURE'
assert result['auto_triggered'] == False  # ✅ 已關閉
```

**預期行為**：
- ✅ `auto_triggered = False`
- ✅ 無警告訊息
- ✅ 正常執行配置驗證

## 📊 日誌記錄

### 自動觸發時的日誌訊息

```log
[WARNING] 2025-11-17 08:37:12,039 | library.services.build_config_validator | validate | Line 82 | ⚠️ Build 1723 has FAILURE status (not SUCCESS), automatically triggering config validation

[WARNING] 2025-11-17 08:37:15,370 | library.services.build_config_validator | validate | Line 82 | ⚠️ Build 1530 has UNSTABLE status (not SUCCESS), automatically triggering config validation

[WARNING] 2025-11-17 08:37:16,763 | library.services.build_config_validator | validate | Line 82 | ⚠️ Build 1303 has ABORTED status (not SUCCESS), automatically triggering config validation
```

### 日誌級別

- **WARNING**：當 Build 失敗並自動觸發時
- **INFO**：一般驗證過程訊息
- **ERROR**：驗證過程發生錯誤

### 查看日誌

```bash
# 查看所有自動觸發記錄
grep "⚠️.*FAILURE" logs/django.log

# 即時監控
tail -f logs/django.log | grep -E "⚠️|FAILURE|auto"
```

## 🎯 應用場景

### 1. 快速定位配置問題

當 Build 失敗時，立即檢查配置是否正確：
- HOST_IP 是否在 DHCP 租約中
- HOST_MAC 是否與 DHCP 記錄匹配
- UART_IP 是否正確解析

### 2. 自動化故障排查

整合到 CI/CD 流程中：
```python
if build.result == 'FAILURE':
    # 自動執行配置驗證
    validator = BuildConfigValidator(build_id=build.id)
    result = validator.validate()
    
    if result['auto_triggered']:
        # 發送通知或自動修復
        send_notification(result)
```

### 3. 數據分析

分析失敗 Build 的配置問題：
```python
# 統計自動觸發的驗證
failed_builds = JenkinsBuild.objects.filter(result='FAILURE')
for build in failed_builds:
    result = validate_build_config(build.id)
    if result['auto_triggered']:
        analyze_config_issues(result)
```

## 🔧 實現細節

### 檢測邏輯

```python
def validate(self) -> Dict:
    # 載入 Build
    self._load_build()
    
    # 檢查是否為非成功的 Build（修改後）
    if self.auto_check_on_failure and self.build.result != 'SUCCESS':
        self.validation_results['auto_triggered'] = True
        logger.warning(
            f"⚠️ Build {self.build_id} has {self.build.result} status (not SUCCESS), "
            f"automatically triggering config validation"
        )
    
    # 記錄 Build 結果
    self.validation_results['build_result'] = self.build.result
    
    # 執行驗證
    # ...
    
    return self.validation_results
```

### Build 狀態類型

`JenkinsBuild.result` 可能的值：
- `SUCCESS` - 成功 ✅ **不觸發**
- `FAILURE` - 失敗 ⚠️ **自動觸發**
- `UNSTABLE` - 不穩定 ⚠️ **自動觸發**
- `ABORTED` - 已中止 ⚠️ **自動觸發**
- `NOT_BUILT` - 未建置 ⚠️ **自動觸發**
- `BUILDING` - 建置中 ⚠️ **自動觸發**

## 📈 統計資訊

### 測試結果（2025-11-17 更新）

| 測試案例 | Build ID | Build 狀態 | auto_check_on_failure | auto_triggered | 結果 |
|---------|----------|-----------|----------------------|----------------|------|
| 案例 1  | 2161     | SUCCESS   | True（預設）          | ✅ False       | 通過 |
| 案例 2  | 1723     | FAILURE   | True                 | ✅ True        | 通過 |
| 案例 3  | 1530     | UNSTABLE  | True                 | ✅ True        | 通過 |
| 案例 4  | 1303     | ABORTED   | True                 | ✅ True        | 通過 |
| 案例 5  | 1723     | FAILURE   | False                | ✅ False       | 通過 |

**結論**：✅ 所有測試案例通過！只有 SUCCESS 狀態不觸發，所有其他狀態都會自動觸發。

## 🔗 相關文件

- [Build Configuration Validator](../api/BUILD_CONFIG_VALIDATOR.md)
- [DHCP Lease Management](../features/dhcp-lease-management.md)
- [Ansible Inventory Integration](../features/ansible-inventory.md)

## 📅 更新記錄

- **2025-11-17（第二版）**：擴展自動觸發範圍
  - ✅ 修改為所有非 SUCCESS 狀態都自動觸發
  - ✅ 涵蓋 FAILURE、UNSTABLE、ABORTED、NOT_BUILT、BUILDING
  - ✅ 更新日誌訊息為：`{status} (not SUCCESS)`
  - ✅ 測試通過 5 個案例（包含 UNSTABLE、ABORTED）

- **2025-11-17（第一版）**：新增自動觸發功能
  - 新增 `auto_check_on_failure` 參數（預設：True）
  - 新增 `build_result` 和 `auto_triggered` 欄位
  - 新增 WARNING 級別日誌記錄
  - 完成測試驗證（僅 FAILURE 狀態）

---

**維護者**：Network Toolbox Team  
**最後更新**：2025-11-17
