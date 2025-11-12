#!/usr/bin/env python
"""
批量解壓縮已存儲的 Jenkins Artifacts

這個腳本會掃描所有已存儲但未解壓縮的 Artifacts 目錄，
並對其中的 .7z 壓縮檔案進行解壓縮和清理。
"""

import os
import sys
import django
from pathlib import Path
import subprocess
import logging

# 設定 Django 環境
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'network_toolbox.settings')
django.setup()

from api.models import JenkinsBuild

# 設定日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def extract_7z_file(archive_path: Path, extract_to: Path) -> dict:
    """
    解壓縮 .7z 檔案
    
    Args:
        archive_path: 壓縮檔路徑
        extract_to: 解壓縮目標目錄
        
    Returns:
        dict: 解壓縮結果
    """
    try:
        logger.info(f"  正在解壓縮: {archive_path.name}")
        
        # 執行 7z 解壓縮命令
        result = subprocess.run(
            ['7z', 'x', str(archive_path), f'-o{extract_to}', '-y'],
            capture_output=True,
            text=True,
            timeout=300
        )
        
        if result.returncode == 0:
            # 計算解壓縮後的檔案
            files_count = 0
            total_size = 0
            
            for item in extract_to.rglob('*'):
                if item.is_file() and item != archive_path:
                    files_count += 1
                    total_size += item.stat().st_size
            
            logger.info(f"  ✓ 解壓縮成功: {files_count} 個檔案, {total_size / (1024**2):.2f} MB")
            
            # 刪除原始壓縮檔
            try:
                archive_path.unlink()
                logger.info(f"  ✓ 已刪除原始壓縮檔: {archive_path.name}")
            except Exception as del_error:
                logger.warning(f"  ⚠️  刪除原始壓縮檔失敗: {del_error}")
            
            return {
                'success': True,
                'files_count': files_count,
                'total_size': total_size
            }
        else:
            logger.error(f"  ✗ 7z 解壓縮失敗: {result.stderr}")
            return {'success': False, 'error': result.stderr}
            
    except FileNotFoundError:
        logger.error("  ✗ 7z 命令未找到，請安裝 p7zip-full")
        return {'success': False, 'error': '7z command not found'}
    except subprocess.TimeoutExpired:
        logger.error(f"  ✗ 解壓縮超時: {archive_path.name}")
        return {'success': False, 'error': 'Extraction timeout'}
    except Exception as e:
        logger.error(f"  ✗ 解壓縮失敗: {e}", exc_info=True)
        return {'success': False, 'error': str(e)}


def process_artifacts_directory(artifacts_path: Path) -> dict:
    """
    處理單個 artifacts 目錄
    
    Args:
        artifacts_path: artifacts 目錄路徑
        
    Returns:
        dict: 處理結果
    """
    # 查找目錄中的 .7z 檔案
    archive_files = list(artifacts_path.glob('*.7z'))
    
    if not archive_files:
        return {
            'has_archives': False,
            'processed': 0,
            'success': 0,
            'failed': 0
        }
    
    logger.info(f"📁 {artifacts_path}")
    logger.info(f"   發現 {len(archive_files)} 個壓縮檔")
    
    processed = 0
    success_count = 0
    failed_count = 0
    
    for archive_file in archive_files:
        result = extract_7z_file(archive_file, artifacts_path)
        processed += 1
        
        if result.get('success'):
            success_count += 1
        else:
            failed_count += 1
    
    return {
        'has_archives': True,
        'processed': processed,
        'success': success_count,
        'failed': failed_count
    }


def main():
    """主函數"""
    
    print('╔' + '=' * 78 + '╗')
    print('║' + ' 批量解壓縮已存儲的 Jenkins Artifacts '.center(78) + '║')
    print('╚' + '=' * 78 + '╝')
    print()
    
    # NAS 基礎路徑
    base_path = Path('/mnt/mdt/Team/PQ1-3/tool/jenkins_test_storage')
    
    if not base_path.exists():
        print('❌ NAS 路徑不存在，請確認 NAS 已掛載')
        return 1
    
    # 查詢所有已存儲 artifacts 的 builds
    stored_builds = JenkinsBuild.objects.filter(
        is_artifacts_stored=True
    ).select_related('job', 'job__server')
    
    total_builds = stored_builds.count()
    print(f'📊 找到 {total_builds} 個已存儲 Artifacts 的 Build')
    print()
    
    # 統計
    total_directories = 0
    has_archives = 0
    processed_archives = 0
    success_archives = 0
    failed_archives = 0
    
    print('=' * 80)
    print('開始處理...')
    print('=' * 80)
    print()
    
    for build in stored_builds:
        if not build.artifacts_path:
            continue
        
        artifacts_path = Path(build.artifacts_path)
        
        if not artifacts_path.exists():
            logger.warning(f"⚠️  路徑不存在: {artifacts_path}")
            continue
        
        total_directories += 1
        
        # 處理目錄
        result = process_artifacts_directory(artifacts_path)
        
        if result['has_archives']:
            has_archives += 1
            processed_archives += result['processed']
            success_archives += result['success']
            failed_archives += result['failed']
            print()
    
    # 顯示總結
    print('=' * 80)
    print('處理完成！')
    print('=' * 80)
    print()
    print(f'📊 統計資訊：')
    print(f'   - 檢查的目錄: {total_directories} 個')
    print(f'   - 包含壓縮檔的目錄: {has_archives} 個')
    print(f'   - 處理的壓縮檔: {processed_archives} 個')
    print(f'   - 成功解壓縮: {success_archives} 個 ✅')
    print(f'   - 失敗: {failed_archives} 個 ❌')
    print()
    print('=' * 80)
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
