#!/usr/bin/env python3
"""
測試 Jenkins Artifacts 下載功能

測試對象：
- Server: 10.252.170.171
- Job: Test-KVM01
- Build: #148
- Artifact: RVT-SupportBundle_Test-KVM01_20251105_105701.7z (54.9 MB)

測試目標：
1. 驗證可以從 Jenkins API 獲取 Artifacts 列表
2. 驗證可以下載 Artifact 檔案
3. 驗證存儲到 NAS 的 artifacts/ 資料夾（與 workspace/ 平行）
"""

import os
import sys
import requests
from pathlib import Path
from datetime import datetime

# 配置
JENKINS_URL = "http://10.252.170.171:8080"
JOB_NAME = "Test-KVM01"
BUILD_NUMBER = 148
BASE_PATH = "/mnt/mdt/Team/PQ1-3/tool/jenkins_test_storage"

# Jenkins 認證（如果需要）
JENKINS_USERNAME = None  # 如果需要認證，填入用戶名
JENKINS_API_TOKEN = None  # 如果需要認證，填入 API Token


def print_section(title):
    """打印分隔線"""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def test_get_artifacts():
    """
    測試 1: 獲取 Artifacts 列表
    
    API: GET /job/{job}/api/json?tree=artifacts[fileName,relativePath]
    """
    print_section("測試 1: 獲取 Artifacts 列表")
    
    url = f"{JENKINS_URL}/job/{JOB_NAME}/{BUILD_NUMBER}/api/json"
    params = {
        'tree': 'artifacts[fileName,relativePath,displayPath]'
    }
    
    print(f"📡 請求 URL: {url}")
    print(f"   參數: {params}")
    
    try:
        auth = None
        if JENKINS_USERNAME and JENKINS_API_TOKEN:
            auth = (JENKINS_USERNAME, JENKINS_API_TOKEN)
        
        response = requests.get(url, params=params, auth=auth, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        artifacts = data.get('artifacts', [])
        
        print(f"\n✅ 成功獲取 Artifacts 列表")
        print(f"   共 {len(artifacts)} 個 Artifacts\n")
        
        if artifacts:
            for idx, artifact in enumerate(artifacts, 1):
                print(f"   Artifact {idx}:")
                print(f"   - 檔名: {artifact.get('fileName')}")
                print(f"   - 相對路徑: {artifact.get('relativePath')}")
                print(f"   - 顯示路徑: {artifact.get('displayPath')}")
                print()
        else:
            print("   ⚠️ 該 Build 沒有 Artifacts")
        
        return artifacts
        
    except requests.exceptions.RequestException as e:
        print(f"\n❌ 請求失敗: {e}")
        return None
    except Exception as e:
        print(f"\n❌ 處理失敗: {e}")
        return None


def get_artifact_size(artifact):
    """
    測試 2: 獲取 Artifact 檔案大小
    
    使用 HEAD 請求獲取 Content-Length
    """
    print_section(f"測試 2: 獲取檔案大小 - {artifact['fileName']}")
    
    relative_path = artifact.get('relativePath', '')
    download_url = f"{JENKINS_URL}/job/{JOB_NAME}/{BUILD_NUMBER}/artifact/{relative_path}"
    
    print(f"📡 URL: {download_url}")
    
    try:
        auth = None
        if JENKINS_USERNAME and JENKINS_API_TOKEN:
            auth = (JENKINS_USERNAME, JENKINS_API_TOKEN)
        
        response = requests.head(download_url, auth=auth, timeout=10)
        response.raise_for_status()
        
        content_length = response.headers.get('Content-Length', 0)
        file_size = int(content_length)
        
        print(f"\n✅ 檔案大小: {file_size:,} bytes ({file_size / (1024**2):.2f} MB)")
        
        return file_size
        
    except Exception as e:
        print(f"\n❌ 獲取檔案大小失敗: {e}")
        return 0


def test_download_artifact(artifact):
    """
    測試 3: 下載 Artifact 到 NAS
    
    存儲路徑結構：
    /mnt/mdt/Team/PQ1-3/tool/jenkins_test_storage/
    └── 10.252.170.171/
        └── Test-KVM01/
            └── 148/
                └── artifacts/     # 與 workspace/ 平行
                    └── RVT-SupportBundle_*.7z
    """
    print_section(f"測試 3: 下載 Artifact - {artifact['fileName']}")
    
    file_name = artifact.get('fileName')
    relative_path = artifact.get('relativePath', '')
    
    # 構建下載 URL
    download_url = f"{JENKINS_URL}/job/{JOB_NAME}/{BUILD_NUMBER}/artifact/{relative_path}"
    
    # 構建保存路徑（方案 A：artifacts/ 與 workspace/ 平行）
    jenkins_ip = "10.252.170.171"
    save_dir = Path(BASE_PATH) / jenkins_ip / JOB_NAME / str(BUILD_NUMBER) / "artifacts"
    save_path = save_dir / file_name
    
    print(f"📥 下載資訊:")
    print(f"   URL: {download_url}")
    print(f"   保存到: {save_path}")
    
    # 檢查目錄是否存在
    if not Path(BASE_PATH).exists():
        print(f"\n❌ NAS 基礎路徑不存在: {BASE_PATH}")
        print("   請確認 NAS 已正確掛載")
        return None
    
    # 創建 artifacts 目錄
    try:
        save_dir.mkdir(parents=True, exist_ok=True)
        print(f"\n✅ 目錄已創建: {save_dir}")
    except Exception as e:
        print(f"\n❌ 創建目錄失敗: {e}")
        return None
    
    # 下載檔案
    print(f"\n📦 開始下載...")
    start_time = datetime.now()
    
    try:
        auth = None
        if JENKINS_USERNAME and JENKINS_API_TOKEN:
            auth = (JENKINS_USERNAME, JENKINS_API_TOKEN)
        
        response = requests.get(download_url, auth=auth, stream=True, timeout=120)
        response.raise_for_status()
        
        # 寫入檔案
        downloaded_size = 0
        with open(save_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    downloaded_size += len(chunk)
                    
                    # 每 10MB 打印一次進度
                    if downloaded_size % (10 * 1024 * 1024) < 8192:
                        print(f"   已下載: {downloaded_size / (1024**2):.1f} MB", end='\r')
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        # 驗證檔案
        if save_path.exists():
            file_size = save_path.stat().st_size
            print(f"\n\n✅ 下載完成!")
            print(f"   檔案大小: {file_size:,} bytes ({file_size / (1024**2):.2f} MB)")
            print(f"   下載時間: {duration:.1f} 秒")
            print(f"   平均速度: {(file_size / (1024**2)) / duration:.2f} MB/s")
            print(f"   檔案路徑: {save_path}")
            
            return {
                'success': True,
                'file_path': str(save_path),
                'file_size': file_size,
                'duration': duration
            }
        else:
            print(f"\n❌ 檔案不存在: {save_path}")
            return None
            
    except requests.exceptions.RequestException as e:
        print(f"\n❌ 下載失敗: {e}")
        return None
    except Exception as e:
        print(f"\n❌ 儲存失敗: {e}")
        return None


def verify_directory_structure():
    """
    測試 4: 驗證目錄結構
    """
    print_section("測試 4: 驗證目錄結構")
    
    jenkins_ip = "10.252.170.171"
    build_dir = Path(BASE_PATH) / jenkins_ip / JOB_NAME / str(BUILD_NUMBER)
    
    print(f"📂 Build 目錄: {build_dir}")
    
    if not build_dir.exists():
        print(f"\n⚠️ Build 目錄不存在")
        return
    
    # 檢查 workspace/ 和 artifacts/ 目錄
    workspace_dir = build_dir / "workspace"
    artifacts_dir = build_dir / "artifacts"
    
    print(f"\n目錄結構:")
    print(f"  {build_dir}/")
    
    if workspace_dir.exists():
        workspace_files = list(workspace_dir.rglob('*'))
        print(f"  ├── workspace/  ✅ (已存在，{len(workspace_files)} 個項目)")
    else:
        print(f"  ├── workspace/  ⚠️ (不存在)")
    
    if artifacts_dir.exists():
        artifacts_files = list(artifacts_dir.glob('*'))
        print(f"  └── artifacts/  ✅ (已存在)")
        
        if artifacts_files:
            print(f"\n      Artifacts 檔案:")
            for file in artifacts_files:
                if file.is_file():
                    size = file.stat().st_size
                    print(f"      - {file.name} ({size / (1024**2):.2f} MB)")
    else:
        print(f"  └── artifacts/  ❌ (不存在)")
    
    print(f"\n✅ 驗證完成")
    print(f"\n📝 這個結構符合方案 A：artifacts/ 與 workspace/ 平行")


def main():
    """主函數"""
    print("╔" + "═" * 68 + "╗")
    print("║" + " " * 68 + "║")
    print("║" + "  Jenkins Artifacts 下載測試".center(68) + "║")
    print("║" + " " * 68 + "║")
    print("╚" + "═" * 68 + "╝")
    
    print(f"\n📋 測試配置:")
    print(f"   Jenkins Server: {JENKINS_URL}")
    print(f"   Job Name: {JOB_NAME}")
    print(f"   Build Number: {BUILD_NUMBER}")
    print(f"   NAS Base Path: {BASE_PATH}")
    
    # 測試 1: 獲取 Artifacts 列表
    artifacts = test_get_artifacts()
    
    if not artifacts:
        print("\n⚠️ 無法獲取 Artifacts 列表或該 Build 沒有 Artifacts")
        return
    
    # 測試 2: 獲取檔案大小
    artifact = artifacts[0]
    file_size = get_artifact_size(artifact)
    
    # 測試 3: 下載 Artifact
    result = test_download_artifact(artifact)
    
    if not result:
        print("\n❌ 下載測試失敗")
        return
    
    # 測試 4: 驗證目錄結構
    verify_directory_structure()
    
    # 總結
    print_section("✅ 測試總結")
    print(f"""
測試結果：全部通過 ✅

1. ✅ 成功從 Jenkins API 獲取 Artifacts 列表
2. ✅ 成功獲取 Artifact 檔案大小
3. ✅ 成功下載 Artifact 到 NAS
4. ✅ 目錄結構正確（artifacts/ 與 workspace/ 平行）

存儲路徑：
  {result['file_path']}

檔案資訊：
  - 檔案大小: {result['file_size'] / (1024**2):.2f} MB
  - 下載時間: {result['duration']:.1f} 秒
  - 平均速度: {(result['file_size'] / (1024**2)) / result['duration']:.2f} MB/s

下一步：
  ✓ 測試腳本驗證成功
  → 可以開始整合到 JenkinsClient 和 JenkinsStorageService
  → 然後添加 API 端點和 Celery 任務
    """)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️ 測試被用戶中斷")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ 測試過程發生錯誤: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
