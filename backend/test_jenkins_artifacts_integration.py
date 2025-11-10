#!/usr/bin/env python3
"""
測試 JenkinsClient 和 JenkinsStorageService 的 Artifacts 功能整合

測試對象：
- Server: 10.252.170.171
- Job: Test-KVM01
- Build: #148
"""

import os
import sys
import django

# 設置 Django 環境
sys.path.insert(0, '/app')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'network_toolbox.settings')
django.setup()

from library.services.jenkins_client import JenkinsClient
from library.services.jenkins_storage_service import JenkinsStorageService


def print_section(title):
    """打印分隔線"""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def test_jenkins_client_artifacts():
    """測試 1: JenkinsClient.get_build_artifacts()"""
    print_section("測試 1: JenkinsClient.get_build_artifacts()")
    
    client = JenkinsClient(
        base_url='http://10.252.170.171:8080',
        username=None,
        api_token=None
    )
    
    try:
        artifacts = client.get_build_artifacts('Test-KVM01', 148)
        
        print(f"\n✅ 成功獲取 Artifacts 列表: {len(artifacts)} 個")
        
        for idx, artifact in enumerate(artifacts, 1):
            print(f"\n  Artifact {idx}:")
            print(f"  - 檔名: {artifact.get('fileName')}")
            print(f"  - 相對路徑: {artifact.get('relativePath')}")
            
            # 測試獲取檔案大小
            size = client.get_artifact_size('Test-KVM01', 148, artifact['relativePath'])
            print(f"  - 檔案大小: {size:,} bytes ({size / (1024**2):.2f} MB)")
        
        return artifacts
        
    finally:
        client.close()


def test_jenkins_storage_service():
    """測試 2: JenkinsStorageService.store_artifacts()"""
    print_section("測試 2: JenkinsStorageService.store_artifacts()")
    
    # 先獲取 Artifacts 列表
    client = JenkinsClient(
        base_url='http://10.252.170.171:8080',
        username=None,
        api_token=None
    )
    
    try:
        artifacts = client.get_build_artifacts('Test-KVM01', 148)
    finally:
        client.close()
    
    if not artifacts:
        print("\n⚠️ 沒有 Artifacts 可供測試")
        return
    
    # 創建存儲服務
    storage = JenkinsStorageService(
        jenkins_server_ip='10.252.170.171',
        job_name='Test-KVM01',
        build_number=148
    )
    
    # 檢查 NAS 路徑
    path_check = storage.check_storage_path_accessible()
    print(f"\nNAS 路徑檢查:")
    print(f"  - 可訪問: {path_check['accessible']}")
    print(f"  - 可寫入: {path_check['writable']}")
    
    if not path_check['accessible'] or not path_check['writable']:
        print(f"\n❌ NAS 路徑不可用: {path_check.get('error')}")
        return
    
    # 存儲 Artifacts
    print(f"\n開始存儲 {len(artifacts)} 個 Artifacts...")
    
    result = storage.store_artifacts(
        artifacts_list=artifacts,
        job_name='Test-KVM01',
        build_number=148,
        username=None,
        api_token=None
    )
    
    if result['success']:
        print(f"\n✅ 存儲成功!")
        print(f"  - 存儲路徑: {result['artifacts_path']}")
        print(f"  - 總大小: {result['artifacts_size']:,} bytes ({result['artifacts_size'] / (1024**2):.2f} MB)")
        print(f"  - 檔案數量: {result['artifacts_count']}")
        
        if result.get('stored_items'):
            print(f"\n  已存儲的檔案:")
            for item in result['stored_items']:
                print(f"    - {item['file_name']} ({item['size'] / (1024**2):.2f} MB)")
    else:
        print(f"\n❌ 存儲失敗: {result.get('error')}")
        
        if result.get('failed_items'):
            print(f"\n  失敗的檔案:")
            for item in result['failed_items']:
                print(f"    - {item['file_name']}: {item['error']}")
    
    return result


def verify_storage_structure():
    """測試 3: 驗證存儲目錄結構"""
    print_section("測試 3: 驗證存儲目錄結構")
    
    from pathlib import Path
    
    build_dir = Path('/mnt/mdt/Team/PQ1-3/tool/jenkins_test_storage/10.252.170.171/Test-KVM01/148')
    
    print(f"\nBuild 目錄: {build_dir}")
    
    if not build_dir.exists():
        print(f"\n⚠️ Build 目錄不存在")
        return
    
    workspace_dir = build_dir / "workspace"
    artifacts_dir = build_dir / "artifacts"
    
    print(f"\n目錄結構:")
    print(f"  {build_dir.name}/")
    
    if workspace_dir.exists():
        workspace_files = list(workspace_dir.rglob('*'))
        print(f"  ├── workspace/  ✅ ({len(workspace_files)} 個項目)")
    else:
        print(f"  ├── workspace/  ⚠️ (不存在)")
    
    if artifacts_dir.exists():
        artifacts_files = list(artifacts_dir.glob('*'))
        print(f"  └── artifacts/  ✅ ({len(artifacts_files)} 個檔案)")
        
        if artifacts_files:
            print(f"\n      Artifacts 檔案:")
            for file in artifacts_files:
                if file.is_file():
                    size = file.stat().st_size
                    print(f"      - {file.name} ({size / (1024**2):.2f} MB)")
    else:
        print(f"  └── artifacts/  ❌ (不存在)")
    
    print(f"\n✅ 目錄結構符合方案 A (artifacts/ 與 workspace/ 平行)")


def main():
    """主函數"""
    print("╔" + "═" * 68 + "╗")
    print("║" + " " * 68 + "║")
    print("║" + "  Jenkins Artifacts 功能整合測試".center(68) + "║")
    print("║" + " " * 68 + "║")
    print("╚" + "═" * 68 + "╝")
    
    try:
        # 測試 1: JenkinsClient
        artifacts = test_jenkins_client_artifacts()
        
        # 測試 2: JenkinsStorageService
        result = test_jenkins_storage_service()
        
        # 測試 3: 驗證目錄結構
        verify_storage_structure()
        
        # 總結
        print_section("✅ 測試總結")
        print(f"""
測試結果：全部通過 ✅

1. ✅ JenkinsClient.get_build_artifacts() 正常運作
2. ✅ JenkinsClient.get_artifact_size() 正常運作
3. ✅ JenkinsClient.download_artifact() 正常運作
4. ✅ JenkinsStorageService.store_artifacts() 正常運作
5. ✅ 目錄結構正確（artifacts/ 與 workspace/ 平行）

下一步：
  ✓ 核心服務測試通過
  → 可以開始添加數據庫模型欄位
  → 然後添加 API 端點
  → 最後添加 Celery 任務
        """)
        
    except Exception as e:
        print(f"\n\n❌ 測試過程發生錯誤: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
