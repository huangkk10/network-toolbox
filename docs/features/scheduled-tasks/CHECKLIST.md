# ✅ 新增 iPXE Celery 任務檢查清單

## 開始之前

- [ ] Celery 服務正在運行（`docker compose ps | grep celery`）
- [ ] 了解要抓取的資料類型和來源
- [ ] 準備好測試用的 iPXE Server ID

---

## 步驟 1：創建服務文件 ⏱️ 5 分鐘

- [ ] 創建文件：`backend/library/services/your_service.py`
- [ ] 實現資料抓取邏輯
- [ ] 測試服務函數：
  ```bash
  docker exec -it nt-django python manage.py shell
  >>> from library.services.your_service import your_function
  >>> result = your_function(server_id=1)
  >>> print(result)
  ```

**參考範例**：`backend/library/services/ipxe_boot_record_service_example.py`

---

## 步驟 2：創建 Celery 任務 ⏱️ 3 分鐘

- [ ] 打開文件：`backend/api/tasks.py`
- [ ] 在文件末尾添加新任務
- [ ] 檢查任務名稱是否唯一（`name='api.tasks.your_task_name'`）
- [ ] 設定適當的超時時間和重試次數

**任務模板**：
```python
@shared_task(
    bind=True,
    name='api.tasks.your_task_name',
    max_retries=2,
    default_retry_delay=60,
    time_limit=300,
    soft_time_limit=270
)
def your_task_name(self, server_id):
    """任務說明"""
    try:
        from library.services.your_service import your_function
        result = your_function(server_id)
        return result
    except Exception as exc:
        raise self.retry(exc=exc)
```

---

## 步驟 3：配置排程 ⏱️ 2 分鐘

- [ ] 打開文件：`backend/network_toolbox/celery.py`
- [ ] 找到 `app.conf.beat_schedule = {`
- [ ] 在字典中添加新任務配置
- [ ] 檢查任務名稱（字典鍵）是否唯一

**排程模板**：
```python
'your-task-name-every-X-minutes': {
    'task': 'api.tasks.your_task_name',
    'schedule': crontab(minute='*/10'),  # 每 10 分鐘
    'kwargs': {'server_id': 1},
    'options': {'expires': 540},
},
```

**常用排程**：
- [ ] 每 5 分鐘：`crontab(minute='*/5')`
- [ ] 每 10 分鐘：`crontab(minute='*/10')`
- [ ] 每 15 分鐘：`crontab(minute='*/15')`
- [ ] 每小時：`crontab(minute=0)`
- [ ] 每天凌晨 2 點：`crontab(hour=2, minute=0)`

---

## 步驟 4：重啟服務 ⏱️ 1 分鐘

- [ ] 重啟 Celery Beat：
  ```bash
  docker compose restart celery_beat
  ```
- [ ] 重啟 Celery Worker：
  ```bash
  docker compose restart celery_worker
  ```
- [ ] 等待 10 秒讓服務完全啟動

---

## 步驟 5：驗證 ⏱️ 5 分鐘

### 檢查 1：任務已註冊
```bash
docker logs nt-celery-beat --tail 20 | grep "your-task-name"
```
- [ ] 看到任務名稱（✅ 成功）
- [ ] 沒有看到（❌ 檢查 celery.py 配置）

### 檢查 2：任務已排程
```bash
docker logs nt-celery-beat --tail 50
```
- [ ] 看到類似 `Scheduler: Sending due task your-task-name`（✅ 成功）
- [ ] 等待到下一個執行時間再檢查

### 檢查 3：任務執行狀態
```bash
docker logs nt-celery-worker --tail 100 | grep "your-task-name"
```
- [ ] 看到 `[Celery] 開始執行任務`（✅ 開始執行）
- [ ] 看到 `[Celery] 任務完成`（✅ 執行成功）
- [ ] 看到錯誤訊息（❌ 查看錯誤詳情）

### 檢查 4：使用 Flower 監控
```bash
# 在瀏覽器中訪問
http://localhost:5555
```
- [ ] 在 "Tasks" 頁面看到新任務（✅ 任務已註冊）
- [ ] 在 "Tasks (Runtime)" 看到正在執行的任務
- [ ] 在 "Tasks (History)" 看到執行歷史

### 檢查 5：手動執行測試
```bash
docker exec -it nt-django python manage.py shell
```
```python
>>> from api.tasks import your_task_name
>>> result = your_task_name.apply(kwargs={'server_id': 1})
>>> print(result.get())
```
- [ ] 返回成功結果（✅ 任務邏輯正確）
- [ ] 拋出異常（❌ 檢查服務代碼）

### 檢查 6：驗證資料庫記錄
```bash
docker exec -it nt-django python manage.py shell
```
```python
>>> from api.models import YourModel
>>> records = YourModel.objects.order_by('-created_at')[:10]
>>> for r in records:
...     print(r)
```
- [ ] 看到新增的記錄（✅ 資料已儲存）
- [ ] 沒有新記錄（❌ 檢查服務的儲存邏輯）

---

## 常見問題排查

### ❌ 問題：任務沒有執行

**檢查步驟**：
1. [ ] Celery Beat 是否運行？`docker compose ps | grep celery_beat`
2. [ ] Celery Worker 是否運行？`docker compose ps | grep celery_worker`
3. [ ] 排程配置正確？檢查 `celery.py`
4. [ ] 任務名稱拼寫正確？檢查 `tasks.py` 和 `celery.py`
5. [ ] 重啟後是否等待足夠時間？等待到下一個執行時間

**解決方案**：
```bash
# 重啟所有 Celery 服務
docker compose restart celery_beat celery_worker

# 查看啟動日誌
docker logs nt-celery-beat --tail 50
docker logs nt-celery-worker --tail 50
```

---

### ❌ 問題：任務一直失敗

**檢查步驟**：
1. [ ] 查看詳細錯誤日誌：`docker logs nt-celery-worker -f`
2. [ ] 查看應用程式日誌：`tail -f logs/django.log`
3. [ ] 手動執行服務函數測試
4. [ ] 檢查網路連接（如果抓取外部資料）
5. [ ] 檢查資料庫連接

**解決方案**：
```bash
# 查看完整錯誤堆疊
docker logs nt-celery-worker --tail 200

# 手動測試服務函數
docker exec -it nt-django python manage.py shell
>>> from library.services.your_service import your_function
>>> result = your_function(server_id=1)
```

---

### ❌ 問題：資料沒有儲存

**檢查步驟**：
1. [ ] 資料模型是否已遷移？`docker exec nt-django python manage.py showmigrations`
2. [ ] 服務函數是否有儲存邏輯？
3. [ ] 是否有異常但被捕獲了？檢查日誌
4. [ ] 資料庫連接是否正常？

**解決方案**：
```bash
# 執行遷移（如果有新模型）
docker exec nt-django python manage.py makemigrations
docker exec nt-django python manage.py migrate

# 檢查資料庫
docker exec -it nt-django python manage.py dbshell
```

---

### ❌ 問題：任務執行太慢

**優化步驟**：
1. [ ] 減少每次抓取的資料量（添加 limit 參數）
2. [ ] 增加超時時間（`time_limit`）
3. [ ] 優化資料庫查詢（使用 bulk_create）
4. [ ] 增加 Worker 並發數（celery_worker 的 `--concurrency` 參數）

**配置調整**：
```yaml
# docker-compose.yml
celery_worker:
  command: celery -A network_toolbox worker --loglevel=info --concurrency=4
```

---

## 完成檢查清單

### 功能驗證
- [ ] 任務在預定時間自動執行
- [ ] 任務執行成功並返回正確結果
- [ ] 資料正確儲存到資料庫
- [ ] 錯誤日誌記錄詳細
- [ ] 失敗時自動重試

### 監控驗證
- [ ] Flower 顯示任務狀態
- [ ] 可以在日誌中看到執行記錄
- [ ] 資料庫記錄持續增長

### 文檔驗證
- [ ] 在代碼中添加了註釋說明
- [ ] 更新了相關的 README（如果需要）

---

## 下一步

✅ **所有檢查通過？恭喜！您已成功添加新的 Celery 任務！**

📚 **相關文檔**：
- 詳細指南：[ADDING_NEW_CELERY_TASK_GUIDE.md](./ADDING_NEW_CELERY_TASK_GUIDE.md)
- 快速參考：[QUICK_REFERENCE.md](./QUICK_REFERENCE.md)
- Flower 監控：http://localhost:5555

🎯 **建議**：
- 定期檢查 Flower 監控面板
- 設置任務執行時間告警（如果需要）
- 根據實際情況調整執行頻率

---

**預計完成時間**：15-20 分鐘  
**難度等級**：⭐⭐⭐ (中等)  
**最後更新**：2025-11-01
