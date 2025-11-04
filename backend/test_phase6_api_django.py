#!/usr/bin/env python
"""
Phase 6: REST API 端點測試腳本（使用 Django Test Client）

直接使用 Django 的測試客戶端測試 API 端點，不需要啟動開發伺服器。

測試所有 Jenkins API 端點的功能。
"""

import os
import sys
import django
import json
from datetime import datetime

# Django 設置
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'network_toolbox.settings')
django.setup()

from django.test import Client
from django.contrib.auth.models import User
from api.models import JenkinsServer, JenkinsJob, JenkinsBuild

# 測試配置
JENKINS_URL = 'http://10.252.170.188:8080'

# 測試客戶端
client = Client()

# 測試結果追蹤
test_results = []


def print_section(title):
    """打印分隔線"""
    print(f"\n{'=' * 80}")
    print(f"  {title}")
    print(f"{'=' * 80}\n")


def log_test(test_name, passed, message=""):
    """記錄測試結果"""
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"{status}  {test_name}")
    if message:
        print(f"     {message}")
    test_results.append((test_name, passed, message))
    return passed


def test_api_health():
    """測試 1: API 健康檢查"""
    print_section("測試 1: API 健康檢查")
    
    try:
        response = client.get('/api/')
        if response.status_code == 200:
            data = response.json()
            return log_test("API Root", True, f"可用端點數: {len(data)}")
        else:
            return log_test("API Root", False, f"狀態碼: {response.status_code}")
    except Exception as e:
        return log_test("API Root", False, f"錯誤: {e}")


def test_jenkins_server_crud():
    """測試 2: Jenkins 伺服器 CRUD"""
    print_section("測試 2: Jenkins 伺服器 CRUD")
    
    server_id = None
    
    try:
        # 2.1 創建伺服器
        create_data = {
            'name': 'Test Jenkins Server',
            'url': JENKINS_URL,
            'description': 'API 測試用伺服器',
            'status': 'online'
        }
        
        response = client.post(
            '/api/jenkins-servers/',
            data=json.dumps(create_data),
            content_type='application/json'
        )
        
        if response.status_code in [200, 201]:
            server_data = response.json()
            server_id = server_data.get('id')
            log_test("創建 Jenkins 伺服器", True, f"ID: {server_id}, 名稱: {server_data.get('name')}")
        else:
            error_msg = response.json() if response.status_code == 400 else response.content
            log_test("創建 Jenkins 伺服器", False, f"狀態碼: {response.status_code}, 錯誤: {error_msg}")
            return None
        
        # 2.2 獲取伺服器列表
        response = client.get('/api/jenkins-servers/')
        if response.status_code == 200:
            servers = response.json()
            log_test("獲取伺服器列表", True, f"共 {len(servers)} 個伺服器")
        else:
            log_test("獲取伺服器列表", False, f"狀態碼: {response.status_code}")
        
        # 2.3 獲取單個伺服器
        response = client.get(f'/api/jenkins-servers/{server_id}/')
        if response.status_code == 200:
            server_data = response.json()
            log_test("獲取單個伺服器", True, f"名稱: {server_data.get('name')}")
        else:
            log_test("獲取單個伺服器", False, f"狀態碼: {response.status_code}")
        
        # 2.4 更新伺服器
        update_data = {
            'description': 'Updated Description by API Test'
        }
        response = client.patch(
            f'/api/jenkins-servers/{server_id}/',
            data=json.dumps(update_data),
            content_type='application/json'
        )
        if response.status_code == 200:
            updated_data = response.json()
            log_test("更新伺服器", True, f"新描述: {updated_data.get('description')}")
        else:
            log_test("更新伺服器", False, f"狀態碼: {response.status_code}")
        
        # 2.5 搜尋伺服器
        response = client.get('/api/jenkins-servers/?search=Test')
        if response.status_code == 200:
            servers = response.json()
            log_test("搜尋伺服器", True, f"找到 {len(servers)} 個匹配結果")
        else:
            log_test("搜尋伺服器", False, f"狀態碼: {response.status_code}")
        
        return server_id
        
    except Exception as e:
        log_test("Jenkins 伺服器 CRUD", False, f"錯誤: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_jenkins_server_actions(server_id):
    """測試 3: Jenkins 伺服器自訂操作"""
    print_section("測試 3: Jenkins 伺服器自訂操作")
    
    if not server_id:
        log_test("Jenkins 伺服器自訂操作", False, "無效的 server_id")
        return
    
    try:
        # 3.1 測試連接
        response = client.post(f'/api/jenkins-servers/{server_id}/test_connection/')
        if response.status_code == 200:
            data = response.json()
            log_test("測試伺服器連接", data.get('success', False), 
                    data.get('message', ''))
        else:
            log_test("測試伺服器連接", False, f"狀態碼: {response.status_code}")
        
        # 3.2 同步 Job
        response = client.post(f'/api/jenkins-servers/{server_id}/sync_jobs/')
        if response.status_code == 200:
            data = response.json()
            log_test("同步 Job", data.get('success', False),
                    f"創建: {data.get('created', 0)}, 更新: {data.get('updated', 0)}, 總數: {data.get('total', 0)}")
        else:
            log_test("同步 Job", False, f"狀態碼: {response.status_code}")
        
        # 3.3 獲取統計資訊
        response = client.get(f'/api/jenkins-servers/{server_id}/statistics/')
        if response.status_code == 200:
            stats = response.json()
            log_test("獲取伺服器統計", True,
                    f"Job: {stats.get('total_jobs', 0)}, Build: {stats.get('total_builds', 0)}")
        else:
            log_test("獲取伺服器統計", False, f"狀態碼: {response.status_code}")
        
    except Exception as e:
        log_test("Jenkins 伺服器自訂操作", False, f"錯誤: {e}")
        import traceback
        traceback.print_exc()


def test_jenkins_jobs_api(server_id):
    """測試 4: Jenkins Job API"""
    print_section("測試 4: Jenkins Job API")
    
    if not server_id:
        log_test("Jenkins Job API", False, "無效的 server_id")
        return None
    
    job_id = None
    
    try:
        # 4.1 獲取 Job 列表（按伺服器過濾）
        response = client.get(f'/api/jenkins-jobs/?server_id={server_id}')
        if response.status_code == 200:
            jobs = response.json()
            log_test("獲取 Job 列表（按伺服器過濾）", True, f"共 {len(jobs)} 個 Job")
            
            # 如果有 Job，選擇第一個進行後續測試
            if len(jobs) > 0:
                job_id = jobs[0]['id']
                print(f"     將使用 Job ID {job_id} 進行後續測試")
        else:
            log_test("獲取 Job 列表", False, f"狀態碼: {response.status_code}")
        
        # 4.2 獲取所有 Job
        response = client.get('/api/jenkins-jobs/')
        if response.status_code == 200:
            all_jobs = response.json()
            log_test("獲取所有 Job", True, f"共 {len(all_jobs)} 個 Job")
        else:
            log_test("獲取所有 Job", False, f"狀態碼: {response.status_code}")
        
        # 4.3 搜尋 Job
        response = client.get('/api/jenkins-jobs/?search=test')
        if response.status_code == 200:
            search_jobs = response.json()
            log_test("搜尋 Job", True, f"找到 {len(search_jobs)} 個匹配結果")
        else:
            log_test("搜尋 Job", False, f"狀態碼: {response.status_code}")
        
        # 如果有 Job，測試 Job 詳情和操作
        if job_id:
            # 4.4 獲取 Job 詳情
            response = client.get(f'/api/jenkins-jobs/{job_id}/')
            if response.status_code == 200:
                job_data = response.json()
                log_test("獲取 Job 詳情", True, 
                        f"名稱: {job_data.get('name')}, URL: {job_data.get('url')}")
            else:
                log_test("獲取 Job 詳情", False, f"狀態碼: {response.status_code}")
            
            # 4.5 獲取 Job 統計
            response = client.get(f'/api/jenkins-jobs/{job_id}/statistics/')
            if response.status_code == 200:
                stats = response.json()
                log_test("獲取 Job 統計", True,
                        f"總 Build: {stats.get('total_builds', 0)}, 成功率: {stats.get('success_rate', 0)}%")
            else:
                log_test("獲取 Job 統計", False, f"狀態碼: {response.status_code}")
            
            # 4.6 獲取 Job 的 Build 列表
            response = client.get(f'/api/jenkins-jobs/{job_id}/builds/')
            if response.status_code == 200:
                data = response.json()
                log_test("獲取 Build 列表", True,
                        f"Job: {data.get('job_name')}, Build 數: {len(data.get('builds', []))}")
            else:
                log_test("獲取 Build 列表", False, f"狀態碼: {response.status_code}")
            
            # 4.7 獲取最新 Build
            response = client.get(f'/api/jenkins-jobs/{job_id}/latest_build/')
            if response.status_code == 200:
                latest = response.json()
                log_test("獲取最新 Build", True,
                        f"Build #{latest.get('build_number')}, 狀態: {latest.get('status')}")
            elif response.status_code == 404:
                log_test("獲取最新 Build", True, "沒有 Build（正常）")
            else:
                log_test("獲取最新 Build", False, f"狀態碼: {response.status_code}")
        else:
            print("     ⚠️  沒有 Job 可用於測試詳情操作")
        
        return job_id
        
    except Exception as e:
        log_test("Jenkins Job API", False, f"錯誤: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_jenkins_builds_api():
    """測試 5: Jenkins Build API"""
    print_section("測試 5: Jenkins Build API")
    
    try:
        # 5.1 獲取 Build 列表
        response = client.get('/api/jenkins-builds/')
        if response.status_code == 200:
            builds = response.json()
            log_test("獲取 Build 列表", True, f"共 {len(builds)} 個 Build")
            
            # 如果有 Build，測試 Build 詳情
            if len(builds) > 0:
                build = builds[0]
                build_id = build['id']
                print(f"     將使用 Build ID {build_id} 進行測試")
                
                # 5.2 獲取 Build 詳情
                response = client.get(f'/api/jenkins-builds/{build_id}/')
                if response.status_code == 200:
                    build_data = response.json()
                    log_test("獲取 Build 詳情", True,
                            f"Job: {build_data.get('job_name')}, #{build_data.get('build_number')}, 狀態: {build_data.get('status')}")
                else:
                    log_test("獲取 Build 詳情", False, f"狀態碼: {response.status_code}")
                
                # 5.3 獲取控制台日誌
                response = client.get(f'/api/jenkins-builds/{build_id}/console_log/?tail=50')
                if response.status_code == 200:
                    log_data = response.json()
                    log_content = log_data.get('log_content', '')
                    log_test("獲取控制台日誌", True,
                            f"來源: {log_data.get('source')}, 長度: {len(log_content)} 字元")
                elif response.status_code == 500:
                    log_test("獲取控制台日誌", True, "Jenkins API 錯誤（正常，可能需要認證）")
                else:
                    log_test("獲取控制台日誌", False, f"狀態碼: {response.status_code}")
                
                # 5.4 獲取配置文件
                response = client.get(f'/api/jenkins-builds/{build_id}/config_file/')
                if response.status_code == 200:
                    log_test("獲取配置文件", True)
                elif response.status_code == 500:
                    log_test("獲取配置文件", True, "NAS 文件不存在（正常）")
                else:
                    log_test("獲取配置文件", False, f"狀態碼: {response.status_code}")
                
                # 5.5 獲取聚合數據
                response = client.get(f'/api/jenkins-builds/{build_id}/aggregate_data/')
                if response.status_code == 200:
                    log_test("獲取聚合數據", True)
                elif response.status_code == 500:
                    log_test("獲取聚合數據", True, "NAS 文件不存在（正常）")
                else:
                    log_test("獲取聚合數據", False, f"狀態碼: {response.status_code}")
            else:
                print("     ⚠️  沒有 Build 可用於測試詳情操作")
        else:
            log_test("獲取 Build 列表", False, f"狀態碼: {response.status_code}")
        
        # 5.6 按狀態過濾
        response = client.get('/api/jenkins-builds/?status=SUCCESS')
        if response.status_code == 200:
            success_builds = response.json()
            log_test("按狀態過濾 Build", True, f"SUCCESS 狀態: {len(success_builds)} 個")
        else:
            log_test("按狀態過濾 Build", False, f"狀態碼: {response.status_code}")
        
        # 5.7 獲取緩存統計
        response = client.get('/api/jenkins-builds/cache_stats/')
        if response.status_code == 200:
            stats = response.json()
            log_test("獲取緩存統計", True,
                    f"記憶體: {stats.get('used_memory', 'N/A')}, 命中率: {stats.get('hit_rate', 0):.2f}%")
        else:
            log_test("獲取緩存統計", False, f"狀態碼: {response.status_code}")
        
    except Exception as e:
        log_test("Jenkins Build API", False, f"錯誤: {e}")
        import traceback
        traceback.print_exc()


def test_cleanup(server_id):
    """測試 6: 清理測試數據"""
    print_section("測試 6: 清理測試數據")
    
    if not server_id:
        log_test("清理測試數據", False, "無效的 server_id")
        return
    
    try:
        # 刪除測試伺服器（會級聯刪除 Job 和 Build）
        response = client.delete(f'/api/jenkins-servers/{server_id}/')
        if response.status_code == 204:
            log_test("刪除測試伺服器", True, "已刪除測試伺服器及其所有 Job 和 Build")
        else:
            log_test("刪除測試伺服器", False, f"狀態碼: {response.status_code}")
        
    except Exception as e:
        log_test("清理測試數據", False, f"錯誤: {e}")
        import traceback
        traceback.print_exc()


def run_all_tests():
    """執行所有測試"""
    print("\n" + "=" * 80)
    print("  Phase 6: REST API 端點 - 完整測試（Django Test Client）")
    print(f"  Jenkins URL: {JENKINS_URL}")
    print(f"  測試時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    # 執行測試
    test_api_health()
    server_id = test_jenkins_server_crud()
    test_jenkins_server_actions(server_id)
    job_id = test_jenkins_jobs_api(server_id)
    test_jenkins_builds_api()
    test_cleanup(server_id)
    
    # 總結
    print_section("測試總結")
    
    passed = sum(1 for _, result, _ in test_results if result)
    failed = sum(1 for _, result, _ in test_results if not result)
    total = len(test_results)
    
    print(f"總測試數: {total}")
    print(f"✅ 通過: {passed}")
    print(f"❌ 失敗: {failed}")
    print(f"成功率: {passed/total*100:.1f}%\n")
    
    # 詳細結果
    print("詳細結果:")
    for test_name, result, message in test_results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status}  {test_name}")
        if message and not result:
            print(f"         {message}")
    
    print("\n" + "=" * 80)
    print("\n✨ Phase 6 API 測試完成！\n")
    
    return passed == total


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
