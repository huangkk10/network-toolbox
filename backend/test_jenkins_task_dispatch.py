#!/usr/bin/env python
"""
測試 Jenkins Jobs 同步任務派發

這個腳本用於診斷為什麼 Beat 發送的 sync_all_jenkins_jobs_task 任務無法到達 Worker
"""

import os
import sys
import django

# 設置 Django 環境
sys.path.append('/app')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'network_toolbox.settings')
django.setup()

from celery import current_app
from api.tasks import sync_all_jenkins_jobs_task
import json

print("=" * 80)
print("Jenkins Jobs 同步任務派發測試")
print("=" * 80)

# 1. 檢查任務註冊狀態
print("\n【步驟 1】檢查任務註冊狀態")
print("-" * 80)
registered_tasks = list(current_app.tasks.keys())
target_task = 'api.tasks.sync_all_jenkins_jobs_task'

if target_task in registered_tasks:
    print(f"✅ 任務已註冊：{target_task}")
else:
    print(f"❌ 任務未註冊：{target_task}")
    print(f"已註冊的任務列表（與 Jenkins 相關）：")
    for task in registered_tasks:
        if 'jenkins' in task.lower():
            print(f"   - {task}")

# 2. 檢查任務配置
print("\n【步驟 2】檢查任務配置")
print("-" * 80)
task_obj = current_app.tasks.get(target_task)
if task_obj:
    print(f"任務名稱：{task_obj.name}")
    print(f"綁定狀態：{task_obj.bind}")
    print(f"最大重試次數：{task_obj.max_retries}")
    print(f"時間限制：{task_obj.time_limit}")
    print(f"隊列名稱：{task_obj.queue if hasattr(task_obj, 'queue') else '未指定'}")

# 3. 檢查 Beat 調度配置
print("\n【步驟 3】檢查 Beat 調度配置")
print("-" * 80)
beat_schedule = current_app.conf.beat_schedule
if 'sync-jenkins-jobs-hourly' in beat_schedule:
    schedule_config = beat_schedule['sync-jenkins-jobs-hourly']
    print(f"調度名稱：sync-jenkins-jobs-hourly")
    print(f"任務名稱：{schedule_config['task']}")
    print(f"調度時間：{schedule_config['schedule']}")
    print(f"參數（kwargs）：{schedule_config.get('kwargs', {})}")
    print(f"選項（options）：{schedule_config.get('options', {})}")
else:
    print(f"❌ 未找到 sync-jenkins-jobs-hourly 調度配置")

# 4. 檢查資料庫中的 PeriodicTask
print("\n【步驟 4】檢查資料庫中的 PeriodicTask")
print("-" * 80)
try:
    from django_celery_beat.models import PeriodicTask
    task_db = PeriodicTask.objects.get(name='sync-jenkins-jobs-hourly')
    print(f"任務 ID：{task_db.id}")
    print(f"啟用狀態：{task_db.enabled}")
    print(f"任務名稱（task）：{task_db.task}")
    print(f"隊列名稱：{task_db.queue or '(使用默認隊列)'}")
    print(f"路由鍵：{task_db.routing_key or '(未設置)'}")
    print(f"參數（args）：{task_db.args}")
    print(f"參數（kwargs）：{task_db.kwargs}")
    print(f"最後執行時間：{task_db.last_run_at}")
    print(f"總執行次數：{task_db.total_run_count}")
    
    # 檢查 kwargs 是否有問題
    if task_db.kwargs:
        try:
            kwargs_dict = json.loads(task_db.kwargs)
            print(f"解析後的 kwargs：{kwargs_dict}")
        except json.JSONDecodeError as e:
            print(f"❌ kwargs 解析失敗：{e}")
except PeriodicTask.DoesNotExist:
    print(f"❌ 資料庫中找不到 sync-jenkins-jobs-hourly 任務")
except Exception as e:
    print(f"❌ 查詢資料庫時發生錯誤：{e}")

# 5. 測試手動派發任務
print("\n【步驟 5】測試手動派發任務")
print("-" * 80)
print("準備手動派發任務到 Celery...")

try:
    # 方式 1：使用 apply_async（與 Beat 相同的方式）
    result = sync_all_jenkins_jobs_task.apply_async(
        kwargs={'server_id': None},
        queue='default',
        expires=3300
    )
    print(f"✅ 任務已派發（apply_async）")
    print(f"   任務 ID：{result.id}")
    print(f"   任務狀態：{result.state}")
    
    # 等待 2 秒看任務是否被 Worker 接收
    import time
    time.sleep(2)
    print(f"   2 秒後狀態：{result.state}")
    
except Exception as e:
    print(f"❌ 派發任務失敗：{e}")
    import traceback
    traceback.print_exc()

# 6. 檢查 Celery 配置
print("\n【步驟 6】檢查 Celery 配置")
print("-" * 80)
print(f"Broker URL：{current_app.conf.broker_url}")
print(f"Result Backend：{current_app.conf.result_backend}")
print(f"時區設置：{current_app.conf.timezone}")
print(f"UTC 模式：{current_app.conf.enable_utc}")
print(f"任務序列化：{current_app.conf.task_serializer}")
print(f"結果序列化：{current_app.conf.result_serializer}")
print(f"接受內容類型：{current_app.conf.accept_content}")
print(f"默認隊列：{current_app.conf.task_default_queue}")

# 7. 檢查任務路由規則
print("\n【步驟 7】檢查任務路由規則")
print("-" * 80)
task_routes = current_app.conf.task_routes
if task_routes:
    print(f"任務路由規則：")
    if isinstance(task_routes, dict):
        for pattern, config in task_routes.items():
            print(f"   {pattern} -> {config}")
    else:
        print(f"   {task_routes}")
else:
    print("   (未配置任務路由規則)")

print("\n" + "=" * 80)
print("測試完成")
print("=" * 80)
