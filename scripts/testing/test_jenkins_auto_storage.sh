#!/bin/bash

# Jenkins Builds 自動存儲功能測試腳本
# 測試 Celery 定時任務和手動存儲功能

echo "========================================="
echo "Jenkins Builds 自動存儲功能測試"
echo "========================================="
echo ""

# 檢查 Django 容器是否運行
if ! docker ps | grep -q nt-django; then
    echo "❌ Django 容器未運行"
    exit 1
fi

echo "✅ Django 容器運行中"
echo ""

# ==================== 測試 1：檢查資料庫狀態 ====================
echo "========================================="
echo "測試 1：檢查資料庫中的 Jenkins Builds 狀態"
echo "========================================="
echo ""

docker exec nt-django python manage.py shell << 'EOF'
from api.models import JenkinsBuild
from django.db.models import Count, Q

# 統計未存儲的 Builds
total_builds = JenkinsBuild.objects.count()
not_stored = JenkinsBuild.objects.filter(is_workspace_stored=False, is_building=False).count()
stored = JenkinsBuild.objects.filter(is_workspace_stored=True).count()
building = JenkinsBuild.objects.filter(is_building=True).count()

print(f"總 Builds 數：{total_builds}")
print(f"已存儲：{stored}")
print(f"未存儲（已完成）：{not_stored}")
print(f"正在構建：{building}")
print("")

# 按結果統計未存儲的 Builds
print("未存儲的 Builds（按結果分類）：")
result_stats = JenkinsBuild.objects.filter(
    is_workspace_stored=False, 
    is_building=False
).values('result').annotate(count=Count('id')).order_by('-count')

for stat in result_stats:
    print(f"  {stat['result']}: {stat['count']}")

print("")
print("前 5 個未存儲的 Builds：")
for build in JenkinsBuild.objects.filter(
    is_workspace_stored=False, 
    is_building=False
).select_related('job', 'job__server').order_by('-build_timestamp')[:5]:
    print(f"  - {build.job.server.name} / {build.job.name} #{build.build_number} - {build.result}")

EOF

echo ""

# ==================== 測試 2：檢查 Celery 任務註冊 ====================
echo "========================================="
echo "測試 2：檢查 Celery 任務是否正確註冊"
echo "========================================="
echo ""

echo "檢查任務註冊情況..."
docker exec nt-django python -c "
from api.tasks import store_jenkins_build_task, auto_store_jenkins_builds_task

print('✅ store_jenkins_build_task:', store_jenkins_build_task.name)
print('✅ auto_store_jenkins_builds_task:', auto_store_jenkins_builds_task.name)
print('')
print('任務註冊成功！')
"

echo ""

# ==================== 測試 3：檢查 Celery Beat 排程 ====================
echo "========================================="
echo "測試 3：檢查 Celery Beat 定時排程"
echo "========================================="
echo ""

echo "檢查 Celery Beat 配置..."
docker exec nt-django python manage.py shell << 'EOF'
from network_toolbox.celery import app

beat_schedule = app.conf.beat_schedule

# 找出 Jenkins 相關的定時任務
jenkins_tasks = {k: v for k, v in beat_schedule.items() if 'jenkins' in k.lower()}

if jenkins_tasks:
    print(f"找到 {len(jenkins_tasks)} 個 Jenkins 相關的定時任務：")
    print("")
    for task_name, task_config in jenkins_tasks.items():
        print(f"任務名稱：{task_name}")
        print(f"  Task：{task_config['task']}")
        print(f"  排程：{task_config['schedule']}")
        if 'kwargs' in task_config:
            print(f"  參數：{task_config['kwargs']}")
        print("")
else:
    print("❌ 未找到 Jenkins 相關的定時任務")

EOF

echo ""

# ==================== 測試 4：檢查存儲策略配置 ====================
echo "========================================="
echo "測試 4：檢查存儲策略配置"
echo "========================================="
echo ""

docker exec nt-django python manage.py shell << 'EOF'
from django.conf import settings

policy = getattr(settings, 'JENKINS_STORAGE_POLICY', None)

if policy:
    print("存儲策略配置：")
    print("")
    for key, value in policy.items():
        print(f"  {key}: {value}")
else:
    print("❌ 未找到 JENKINS_STORAGE_POLICY 配置")

EOF

echo ""

# ==================== 測試 5：演練模式測試管理命令 ====================
echo "========================================="
echo "測試 5：演練模式測試管理命令"
echo "========================================="
echo ""

echo "執行演練模式（不實際存儲）..."
docker exec nt-django python manage.py store_jenkins_builds --limit 10 --dry-run

echo ""

# ==================== 測試 6：手動觸發單個 Build 存儲 ====================
echo "========================================="
echo "測試 6：手動觸發單個 Build 存儲（異步）"
echo "========================================="
echo ""

echo "查找一個未存儲的 Build 並觸發存儲任務..."
TASK_ID=$(docker exec nt-django python manage.py shell << 'EOF'
from api.models import JenkinsBuild
from api.tasks import store_jenkins_build_task

# 找一個未存儲的 Build
build = JenkinsBuild.objects.filter(
    is_workspace_stored=False,
    is_building=False,
    url__isnull=False
).select_related('job', 'job__server').first()

if build:
    print(f"找到 Build: {build.job.server.name} / {build.job.name} #{build.build_number}")
    print(f"Build ID: {build.id}")
    print("")
    
    # 創建異步任務
    task = store_jenkins_build_task.delay(build.id)
    print(f"✅ 任務已創建")
    print(f"Task ID: {task.id}")
    print(task.id)
else:
    print("❌ 沒有找到未存儲的 Builds")
    print("NONE")

EOF
)

if [ "$TASK_ID" != "NONE" ] && [ ! -z "$TASK_ID" ]; then
    # 提取最後一行（Task ID）
    TASK_ID=$(echo "$TASK_ID" | tail -1)
    echo ""
    echo "💡 可以在 Celery Flower 中查看任務狀態："
    echo "   http://localhost:5555/task/$TASK_ID"
fi

echo ""

# ==================== 測試 7：手動觸發自動掃描任務 ====================
echo "========================================="
echo "測試 7：手動觸發自動掃描任務"
echo "========================================="
echo ""

echo "手動觸發一次自動掃描任務（處理 5 個 Builds）..."
docker exec nt-django python manage.py shell << 'EOF'
from api.tasks import auto_store_jenkins_builds_task

# 手動觸發任務
task = auto_store_jenkins_builds_task.delay(limit=5)

print(f"✅ 自動掃描任務已觸發")
print(f"Task ID: {task.id}")
print("")
print(f"💡 可以在 Celery Flower 中查看任務狀態：")
print(f"   http://localhost:5555/task/{task.id}")

EOF

echo ""

# ==================== 測試 8：檢查 NAS 存儲路徑 ====================
echo "========================================="
echo "測試 8：檢查 NAS 存儲路徑"
echo "========================================="
echo ""

echo "檢查 NAS 掛載和存儲路徑..."
docker exec nt-django python manage.py shell << 'EOF'
from django.conf import settings
from library.services.jenkins_storage_service import JenkinsStorageService
import os

base_path = settings.JENKINS_STORAGE_BASE_PATH
print(f"Jenkins 存儲基礎路徑：{base_path}")
print(f"路徑存在：{os.path.exists(base_path)}")
print(f"可寫入：{os.access(base_path, os.W_OK)}")
print("")

# 測試存儲服務
storage = JenkinsStorageService('test', 'test', 1)
result = storage.check_storage_path_accessible()

print("存儲路徑檢查結果：")
print(f"  可訪問：{result.get('accessible')}")
print(f"  可寫入：{result.get('writable')}")
if 'error' in result:
    print(f"  錯誤：{result.get('error')}")

EOF

echo ""

# ==================== 測試 9：查看最近的存儲記錄 ====================
echo "========================================="
echo "測試 9：查看最近的存儲記錄"
echo "========================================="
echo ""

docker exec nt-django python manage.py shell << 'EOF'
from api.models import JenkinsBuild

recently_stored = JenkinsBuild.objects.filter(
    is_workspace_stored=True
).select_related('job', 'job__server').order_by('-workspace_stored_at')[:10]

if recently_stored.exists():
    print(f"最近存儲的 10 個 Builds：")
    print("")
    for build in recently_stored:
        size_mb = build.workspace_size / 1024 / 1024 if build.workspace_size else 0
        stored_at = build.workspace_stored_at.strftime('%Y-%m-%d %H:%M:%S') if build.workspace_stored_at else 'N/A'
        print(f"  - {build.job.server.name} / {build.job.name} #{build.build_number}")
        print(f"    大小：{size_mb:.2f} MB | 存儲時間：{stored_at}")
        print(f"    路徑：{build.workspace_path}")
        print("")
else:
    print("❌ 還沒有已存儲的 Builds")

EOF

echo ""

# ==================== 測試總結 ====================
echo "========================================="
echo "測試完成"
echo "========================================="
echo ""
echo "✅ 所有測試項目已完成"
echo ""
echo "下一步操作："
echo ""
echo "1. 【監控定時任務】"
echo "   訪問 Celery Flower: http://localhost:5555"
echo "   查看 'auto-store-jenkins-builds-every-30-minutes' 任務"
echo ""
echo "2. 【手動批量存儲】"
echo "   # 演練模式（查看將要處理的 Builds）"
echo "   docker exec nt-django python manage.py store_jenkins_builds --limit 10 --dry-run"
echo ""
echo "   # 實際執行（異步模式，使用 Celery）"
echo "   docker exec nt-django python manage.py store_jenkins_builds --limit 10"
echo ""
echo "   # 同步模式（直接執行，適合少量 Builds）"
echo "   docker exec nt-django python manage.py store_jenkins_builds --limit 5 --sync"
echo ""
echo "3. 【查看存儲結果】"
echo "   # 在主機上查看 NAS 存儲"
echo "   docker exec nt-django ls -la /mnt/mdt/Team/PQ1-3/tool/jenkins_test_storage/"
echo ""
echo "4. 【監控日誌】"
echo "   tail -f logs/django.log | grep -i jenkins"
echo ""
echo "5. 【調整配置】"
echo "   編輯 backend/network_toolbox/settings.py 中的 JENKINS_STORAGE_POLICY"
echo "   修改後需要重啟 Django 和 Celery 服務"
echo ""
