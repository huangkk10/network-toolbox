"""
Jenkins Storage Service

提供 Jenkins Workspace、日誌、配置文件的下載和存儲功能。
"""

import os
import logging
import json
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime
import requests
from django.conf import settings

logger = logging.getLogger(__name__)


class JenkinsStorageService:
    """Jenkins 存儲服務"""
    
    def __init__(self, jenkins_server_ip: str, job_name: str, build_number: int):
        """
        初始化存儲服務
        
        Args:
            jenkins_server_ip: Jenkins 伺服器 IP
            job_name: Job 名稱
            build_number: Build 編號
        """
        self.jenkins_server_ip = jenkins_server_ip
        self.job_name = job_name
        self.build_number = build_number
        
        # 構建 NAS 存儲路徑
        self.base_path = Path(settings.JENKINS_STORAGE_BASE_PATH)
        self.build_storage_path = self.base_path / jenkins_server_ip / job_name / str(build_number)
        
        logger.info(f"初始化 Jenkins Storage Service: {self.build_storage_path}")
    
    def check_storage_path_accessible(self) -> Dict[str, Any]:
        """
        檢查 NAS 存儲路徑是否可訪問和可寫
        
        Returns:
            dict: 檢查結果
                - accessible: bool
                - writable: bool
                - error: str (如果有錯誤)
        """
        try:
            # 檢查基礎路徑是否存在
            if not self.base_path.exists():
                return {
                    'accessible': False,
                    'writable': False,
                    'error': f'基礎路徑不存在: {self.base_path}'
                }
            
            # 檢查是否可寫
            try:
                # 嘗試創建測試目錄
                test_dir = self.base_path / '.test_write_permission'
                test_dir.mkdir(exist_ok=True)
                test_dir.rmdir()
                
                return {
                    'accessible': True,
                    'writable': True,
                }
            except PermissionError:
                return {
                    'accessible': True,
                    'writable': False,
                    'error': '沒有寫入權限'
                }
            except Exception as e:
                return {
                    'accessible': True,
                    'writable': False,
                    'error': f'無法測試寫入權限: {str(e)}'
                }
                
        except Exception as e:
            logger.error(f"檢查存儲路徑失敗: {e}", exc_info=True)
            return {
                'accessible': False,
                'writable': False,
                'error': str(e)
            }
    
    def store_workspace(
        self, 
        workspace_url: str, 
        username: Optional[str] = None, 
        api_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        下載並存儲 Jenkins Workspace
        
        Args:
            workspace_url: Workspace URL (例如: http://10.252.170.187:8080/job/SAF3201_KVM02/4/ws/)
            username: Jenkins 使用者名稱
            api_token: Jenkins API Token
            
        Returns:
            dict: 存儲結果
                - success: bool
                - workspace_path: str
                - workspace_size: int (bytes)
                - files_count: int
                - error: str (如果失敗)
        """
        try:
            # 創建存儲目錄
            workspace_path = self.build_storage_path / 'workspace'
            workspace_path.mkdir(parents=True, exist_ok=True)
            
            logger.info(f"開始下載 Workspace: {workspace_url}")
            
            # Jenkins Workspace 下載方式：
            # URL 格式：http://jenkins-url/job/job-name/build-number/ws/*zip*/workspace.zip
            zip_url = f"{workspace_url.rstrip('/')}/*zip*/workspace.zip"
            
            auth = None
            if username and api_token:
                auth = (username, api_token)
            
            logger.info(f"下載 Workspace ZIP: {zip_url}")
            
            response = requests.get(
                zip_url, 
                auth=auth, 
                stream=True, 
                timeout=300
            )
            response.raise_for_status()
            
            # 下載 ZIP 文件
            zip_file_path = self.build_storage_path / 'workspace.zip'
            self.build_storage_path.mkdir(parents=True, exist_ok=True)
            
            with open(zip_file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            logger.info(f"Workspace ZIP 下載完成: {zip_file_path}")
            
            # 解壓縮
            import zipfile
            with zipfile.ZipFile(zip_file_path, 'r') as zip_ref:
                zip_ref.extractall(workspace_path)
            
            logger.info(f"Workspace 解壓縮完成: {workspace_path}")
            
            # 刪除 ZIP 文件（節省空間）
            zip_file_path.unlink()
            
            # 計算總大小和文件數量
            total_size = 0
            files_count = 0
            for root, dirs, files in os.walk(workspace_path):
                for file in files:
                    file_path = Path(root) / file
                    if file_path.exists():
                        total_size += file_path.stat().st_size
                        files_count += 1
            
            logger.info(f"Workspace 存儲成功: {files_count} 個文件, {total_size / (1024**2):.2f} MB")
            
            return {
                'success': True,
                'workspace_path': str(workspace_path),
                'workspace_size': total_size,
                'files_count': files_count,
                'stored_at': datetime.now().isoformat(),
            }
            
        except requests.exceptions.RequestException as e:
            logger.error(f"下載 Workspace 失敗: {e}", exc_info=True)
            return {
                'success': False,
                'error': f'下載失敗: {str(e)}'
            }
        except Exception as e:
            logger.error(f"存儲 Workspace 失敗: {e}", exc_info=True)
            return {
                'success': False,
                'error': f'存儲失敗: {str(e)}'
            }
