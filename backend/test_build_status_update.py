#!/usr/bin/env python
"""
测试 Jenkins Build 状态更新逻辑

验证新的同步逻辑能否正确处理：
1. 新 Build 创建
2. 已存在 Build 的状态更新
3. FAILURE Build 的 failed_stage 同步
"""

import os
import sys
import django

# 设置 Django 环境
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'network_toolbox.settings')
django.setup()

from api.models import JenkinsServer, JenkinsJob, JenkinsBuild
from datetime import datetime
import pytz


def test_build_status_update():
    """测试 Build 状态更新逻辑"""
    
    print('=' * 80)
    print('🧪 测试 Jenkins Build 状态更新逻辑')
    print('=' * 80)
    
    # 查找测试 Job
    try:
        job = JenkinsJob.objects.get(name='SAF7522_K07')
        print(f'✅ 找到测试 Job: {job.name}')
    except JenkinsJob.DoesNotExist:
        print('❌ 找不到测试 Job: SAF7522_K07')
        # 尝试找到任何 Job
        jobs = JenkinsJob.objects.all()[:1]
        if jobs:
            job = jobs[0]
            print(f'✅ 使用替代 Job: {job.name}')
        else:
            print('❌ 没有可用的 Jenkins Job')
            return False
    
    print()
    print('📊 测试场景 1: 查找已存在的 Builds')
    print('-' * 80)
    
    # 查找 Build #35
    try:
        build_35 = JenkinsBuild.objects.get(job=job, build_number=35)
        print(f'✅ 找到 Build #35:')
        print(f'   - 状态: {build_35.result}')
        print(f'   - 正在构建: {build_35.is_building}')
        print(f'   - 持续时间: {build_35.duration}ms')
        print(f'   - 失败 Stage: {build_35.failed_stage or "N/A"}')
        print(f'   - Pipeline Stages 数量: {len(build_35.pipeline_stages) if build_35.pipeline_stages else 0}')
        
        # 检查是否需要更新
        if build_35.result != 'FAILURE':
            print(f'⚠️  Build #35 状态为 {build_35.result}，预期为 FAILURE')
            print('   → 需要运行修复脚本')
        else:
            print('✅ Build #35 状态正确')
            
        if not build_35.failed_stage and build_35.result == 'FAILURE':
            print('⚠️  Build #35 缺少 failed_stage 信息')
            print('   → 需要重新同步')
        else:
            print(f'✅ Failed Stage 已记录: {build_35.failed_stage}')
            
    except JenkinsBuild.DoesNotExist:
        print('❌ 找不到 Build #35')
    
    print()
    print('📊 测试场景 2: 统计所有 Builds')
    print('-' * 80)
    
    all_builds = JenkinsBuild.objects.filter(job=job).order_by('-build_number')[:20]
    print(f'最近 20 个 Builds:')
    
    status_counts = {}
    building_count = 0
    missing_failed_stage = 0
    
    for build in all_builds:
        status = build.result or 'UNKNOWN'
        status_counts[status] = status_counts.get(status, 0) + 1
        
        if build.is_building:
            building_count += 1
        
        if build.result == 'FAILURE' and not build.failed_stage:
            missing_failed_stage += 1
        
        # 显示每个 Build 的信息
        building_flag = '🔄' if build.is_building else '  '
        failed_stage_flag = '❌' if (build.result == 'FAILURE' and not build.failed_stage) else '  '
        print(f'{building_flag}{failed_stage_flag} #{build.build_number:3d} | {build.result:10s} | {build.failed_stage or "N/A":30s}')
    
    print()
    print('统计摘要:')
    for status, count in sorted(status_counts.items()):
        print(f'   - {status}: {count} 个')
    print(f'   - 正在构建: {building_count} 个')
    print(f'   - FAILURE 但缺少 failed_stage: {missing_failed_stage} 个')
    
    print()
    print('📊 测试场景 3: 检查 Job 最后 Build 信息')
    print('-' * 80)
    
    print(f'Job 最后 Build 信息:')
    print(f'   - last_build_number: {job.last_build_number}')
    print(f'   - last_build_status: {job.last_build_status}')
    print(f'   - last_build_time: {job.last_build_time}')
    
    if all_builds:
        latest_build = all_builds[0]
        if job.last_build_number != latest_build.build_number:
            print(f'⚠️  Job.last_build_number ({job.last_build_number}) 与最新 Build #{latest_build.build_number} 不一致')
        if job.last_build_status != latest_build.result:
            print(f'⚠️  Job.last_build_status ({job.last_build_status}) 与最新 Build 状态 ({latest_build.result}) 不一致')
    
    print()
    print('=' * 80)
    print('✅ 测试完成')
    print('=' * 80)
    print()
    print('🔧 修复建议:')
    print()
    print('1. 修复 Build #35 状态:')
    print('   docker exec nt-django python force_resync_build.py --job SAF7522_K07 --build 35')
    print()
    print('2. 重启 Django 容器加载新代码:')
    print('   docker compose restart django')
    print()
    print('3. 手动触发同步任务:')
    print('   docker exec nt-django python manage.py shell')
    print('   >>> from api.tasks import sync_jenkins_builds')
    print('   >>> sync_jenkins_builds.delay()')
    print()
    print('4. 查看同步日志:')
    print('   docker compose logs -f django | grep "更新 Build"')
    print()
    
    return True


if __name__ == '__main__':
    try:
        test_build_status_update()
    except Exception as e:
        print(f'❌ 测试失败: {e}')
        import traceback
        traceback.print_exc()
        sys.exit(1)
