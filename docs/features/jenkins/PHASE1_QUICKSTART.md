# Jenkins 整合 - Phase 1 快速安裝指南

## 🚀 快速開始

### 1. 安裝新的 Python 依賴

```bash
# 重建 Django 容器（推薦）
docker compose up -d --build django

# 或者進入容器手動安裝
docker exec -it nt-django pip install -r requirements.txt
```

### 2. 驗證 Redis 連接

```bash
# 測試 Redis
docker exec -it nt-redis redis-cli ping
# 應該返回：PONG

# 測試 Django 緩存
docker exec -it nt-django python manage.py shell
```

在 Python Shell 中執行：
```python
from django.core.cache import cache
cache.set('test', 'OK', 60)
print(cache.get('test'))  # 應該輸出：OK
exit()
```

### 3. 查看服務狀態

```bash
# 查看所有容器
docker compose ps

# 查看 Redis 日誌
docker compose logs redis --tail 50

# 查看 Django 日誌
docker compose logs django --tail 50
```

### 4. (可選) 配置 NAS 掛載

**如果您的 NAS 已掛載到 `/mnt/mdt`：**

1. 編輯 `docker-compose.yml`，找到 Django 服務的 volumes 部分
2. 取消註釋這一行：
   ```yaml
   - /mnt/mdt:/mnt/mdt:ro
   ```
3. 重啟容器：
   ```bash
   docker compose down
   docker compose up -d
   ```
4. 驗證掛載：
   ```bash
   docker exec nt-django ls -la /mnt/mdt/
   ```

---

## ✅ 驗證清單

- [ ] Redis 容器運行正常（`docker compose ps` 顯示 `healthy`）
- [ ] Redis 連接測試成功（`redis-cli ping` 返回 `PONG`）
- [ ] Django 緩存測試成功（能夠 set/get 緩存值）
- [ ] Django 容器沒有錯誤日誌
- [ ] (可選) NAS 掛載成功（能訪問 `/mnt/mdt`）

---

## 🎯 下一步

Phase 1 完成後，可以開始 **Phase 2: Django 模型設計與遷移**

---

## 📚 相關文檔

- [完整報告](./PHASE1_COMPLETION_REPORT.md)
- [環境變數配置](../../../backend/.env.example)
