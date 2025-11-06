#!/usr/bin/env python3
"""
測試 Blue Ocean Pipeline Stage 功能

使用方式：
    docker exec nt-django python test_blue_ocean_stages.py
"""

import os
import sys
import django

# 設置 Django 環境
sys.path.insert(0, '/app')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'network_toolbox.settings')
django.setup()

from api.models import JenkinsServer, JenkinsJob, JenkinsBuild
from library.services.jenkins_client import JenkinsClient
from datetime import datetime
import pytz


def print_section(title):
    """打印區塊標題"""
    print(f"\n{'=' * 70}")
    print(f"  {title}")
    print('=' * 70)


def test_jenkins_client_blue_ocean():
    """測試 1: JenkinsClient Blue Ocean API 方法"""
    print_section("測試 1: JenkinsClient Blue Ocean API 方法")
    
    # 獲取一個有效的 Jenkins Server
    servers = JenkinsServer.objects.filter(status='online')
    if not servers.exists():
        print("❌ 找不到在線的 Jenkins Server")
        return None, None
    
    server = servers.first()
    print(f"✅ 使用 Jenkins Server: {server.name} ({server.url})")
    
    # 創建客戶端
    client = JenkinsClient(
        base_url=server.url,
        username=server.username,
        api_token=server.api_token
    )
    
    # 獲取一個失敗的 Build 用於測試
    failed_build = JenkinsBuild.objects.filter(
        job__server=server,
        result='FAILURE'
    ).first()
    
    if not failed_build:
        print("❌ 找不到失敗的 Build 用於測試")
        client.close()
        return None, None
    
    print(f"✅ 測試 Build: {failed_build.job.name} #{failed_build.build_number}")
    
    try:
        # 測試獲取 Pipeline Nodes
        print("\n📊 測試 get_blue_ocean_pipeline_nodes()...")
        nodes = client.get_blue_ocean_pipeline_nodes(
            failed_build.job.name,
            failed_build.build_number
        )
        
        if nodes:
            print(f"✅ 成功獲取 {len(nodes)} 個 Nodes")
            
            # 顯示所有 Stage
            stages = [n for n in nodes if n.get('type') == 'STAGE']
            print(f"\n📋 Pipeline Stages: (共 {len(stages)} 個)")
            for stage in stages:
                result = stage.get('result', 'UNKNOWN')
                duration = stage.get('durationInMillis', 0) / 1000
                
                status_icon = {
                    'SUCCESS': '✅',
                    'FAILURE': '❌',
                    'UNSTABLE': '⚠️',
                    'ABORTED': '🚫',
                }.get(result, '❓')
                
                print(f"  {status_icon} {stage.get('displayName')}: {result} ({duration:.1f}s)")
        else:
            print("❌ 無法獲取 Pipeline Nodes（可能不是 Pipeline Job）")
            client.close()
            return None, None
        
        # 測試獲取失敗的 Stage
        print("\n📊 測試 get_failed_stages()...")
        failed_stages = client.get_failed_stages(
            failed_build.job.name,
            failed_build.build_number
        )
        
        if failed_stages:
            print(f"✅ 找到 {len(failed_stages)} 個失敗的 Stage")
            for stage in failed_stages:
                print(f"\n  ❌ Stage: {stage['stage_name']}")
                print(f"     結果: {stage['result']}")
                print(f"     執行時間: {stage['duration_formatted']}")
                if stage.get('error_message'):
                    print(f"     錯誤訊息: {stage['error_message']}")
        else:
            print("✅ 沒有失敗的 Stage")
        
        # 測試獲取 Pipeline 摘要
        print("\n📊 測試 get_pipeline_summary()...")
        summary = client.get_pipeline_summary(
            failed_build.job.name,
            failed_build.build_number
        )
        
        print(f"✅ Pipeline 摘要:")
        print(f"   總 Stage 數: {summary['total_stages']}")
        print(f"   成功: {summary['successful_stages']}")
        print(f"   失敗: {summary['failed_stages']}")
        print(f"   不穩定: {summary['unstable_stages']}")
        print(f"   已中止: {summary['aborted_stages']}")
        
        client.close()
        return server, failed_build
        
    except Exception as e:
        print(f"❌ 測試失敗: {e}")
        import traceback
        traceback.print_exc()
        client.close()
        return None, None


def test_update_build_pipeline_stages(server, build):
    """測試 2: 更新資料庫中的 Pipeline Stage 資訊"""
    print_section("測試 2: 更新資料庫中的 Pipeline Stage 資訊")
    
    if not server or not build:
        print("❌ 缺少測試資料")
        return False
    
    try:
        # 創建客戶端
        client = JenkinsClient(
            base_url=server.url,
            username=server.username,
            api_token=server.api_token
        )
        
        # 獲取 Pipeline Nodes
        nodes = client.get_blue_ocean_pipeline_nodes(build.job.name, build.build_number)
        
        if not nodes:
            print("❌ 無法獲取 Pipeline Nodes")
            client.close()
            return False
        
        # 提取 Stage 資訊
        stages = [
            {
                'id': node.get('id'),
                'name': node.get('displayName'),
                'result': node.get('result'),
                'state': node.get('state'),
                'duration_ms': node.get('durationInMillis', 0),
                'start_time': node.get('startTime'),
                'type': node.get('type'),
                'error': node.get('error')
            }
            for node in nodes if node.get('type') == 'STAGE'
        ]
        
        # 找出失敗的 Stage
        failed_stages_list = client.get_failed_stages(build.job.name, build.build_number)
        failed_stage_name = failed_stages_list[0]['stage_name'] if failed_stages_list else ''
        
        # 更新資料庫
        build.pipeline_stages = stages
        build.failed_stage = failed_stage_name
        build.save(update_fields=['pipeline_stages', 'failed_stage'])
        
        print(f"✅ 成功更新 Build #{build.build_number}")
        print(f"   Pipeline Stages: {len(stages)} 個")
        print(f"   失敗的 Stage: {failed_stage_name or '無'}")
        
        # 重新查詢以驗證
        build.refresh_from_db()
        print(f"\n✅ 驗證資料庫儲存:")
        print(f"   pipeline_stages 欄位: {len(build.pipeline_stages)} 個 Stage")
        print(f"   failed_stage 欄位: {build.failed_stage}")
        
        client.close()
        return True
        
    except Exception as e:
        print(f"❌ 更新失敗: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_query_builds_with_stages():
    """測試 3: 查詢有 Pipeline Stage 資訊的 Build"""
    print_section("測試 3: 查詢有 Pipeline Stage 資訊的 Build")
    
    try:
        # 查詢有 pipeline_stages 的 Build
        builds_with_stages = JenkinsBuild.objects.exclude(
            pipeline_stages=[]
        ).select_related('job', 'job__server')
        
        count = builds_with_stages.count()
        print(f"✅ 找到 {count} 個有 Pipeline Stage 資訊的 Build")
        
        if count > 0:
            print(f"\n📋 前 5 個 Build:")
            for build in builds_with_stages[:5]:
                print(f"\n  Build: {build.job.name} #{build.build_number}")
                print(f"  結果: {build.result}")
                print(f"  失敗 Stage: {build.failed_stage or '無'}")
                print(f"  Stage 數量: {len(build.pipeline_stages)}")
                
                # 統計 Stage 狀態
                if build.pipeline_stages:
                    success = sum(1 for s in build.pipeline_stages if s.get('result') == 'SUCCESS')
                    failed = sum(1 for s in build.pipeline_stages if s.get('result') == 'FAILURE')
                    print(f"  Stage 狀態: 成功 {success}, 失敗 {failed}")
        
        # 查詢有失敗 Stage 的 Build
        builds_with_failed_stages = JenkinsBuild.objects.exclude(
            failed_stage=''
        ).select_related('job')
        
        failed_count = builds_with_failed_stages.count()
        print(f"\n✅ 找到 {failed_count} 個有失敗 Stage 的 Build")
        
        if failed_count > 0:
            print(f"\n📋 失敗 Stage 統計:")
            for build in builds_with_failed_stages[:5]:
                print(f"  • {build.job.name} #{build.build_number}: {build.failed_stage}")
        
        return True
        
    except Exception as e:
        print(f"❌ 查詢失敗: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主測試流程"""
    print_section("🚀 Blue Ocean Pipeline Stage 功能測試")
    
    results = {
        'jenkins_client_test': False,
        'update_database_test': False,
        'query_test': False,
    }
    
    # 測試 1: JenkinsClient Blue Ocean API
    server, build = test_jenkins_client_blue_ocean()
    results['jenkins_client_test'] = (server is not None and build is not None)
    
    # 測試 2: 更新資料庫
    if results['jenkins_client_test']:
        results['update_database_test'] = test_update_build_pipeline_stages(server, build)
    
    # 測試 3: 查詢測試
    results['query_test'] = test_query_builds_with_stages()
    
    # 總結
    print_section("📊 測試結果總結")
    
    total_tests = len(results)
    passed_tests = sum(1 for v in results.values() if v)
    
    for test_name, passed in results.items():
        status = "✅ 通過" if passed else "❌ 失敗"
        print(f"{status} - {test_name}")
    
    print(f"\n總測試數: {total_tests}")
    print(f"通過: {passed_tests}")
    print(f"失敗: {total_tests - passed_tests}")
    
    if passed_tests == total_tests:
        print("\n🎉 所有測試通過！")
        return 0
    else:
        print("\n⚠️  部分測試失敗")
        return 1


if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)
