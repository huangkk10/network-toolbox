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
    
    def _download_file_from_jenkins(
        self, 
        file_url: str, 
        save_path: Path,
        auth: Optional[tuple] = None
    ) -> bool:
        """
        從 Jenkins 下載單個文件
        
        Args:
            file_url: 文件 URL
            save_path: 保存路徑
            auth: 認證信息 (username, api_token)
            
        Returns:
            bool: 是否下載成功
        """
        try:
            response = requests.get(file_url, auth=auth, stream=True, timeout=60)
            response.raise_for_status()
            
            save_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(save_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            return True
        except Exception as e:
            logger.warning(f"下載文件失敗 {file_url}: {e}")
            return False
    
    def _download_workspace_recursively(
        self,
        workspace_url: str,
        target_path: Path,
        auth: Optional[tuple] = None,
        relative_path: str = ''
    ) -> tuple:
        """
        遞歸下載 Jenkins Workspace（HTML 目錄解析方式）
        
        Args:
            workspace_url: Workspace 根 URL
            target_path: 本地目標路徑
            auth: 認證信息
            relative_path: 相對路徑（用於遞歸）
            
        Returns:
            tuple: (files_count, total_size)
        """
        from bs4 import BeautifulSoup
        import urllib.parse

        files_count = 0
        total_size = 0

        # internal helper with depth and visited tracking
        def _walk(rel_path: str, depth: int, visited: set) -> tuple:
            if depth > 12:
                logger.warning(f"達到最大遞歸深度，停止在: {rel_path}")
                return 0, 0

            # 构建当前目录 URL
            current_url = urllib.parse.urljoin(workspace_url.rstrip('/') + '/', rel_path)

            # avoid revisiting same URL
            if current_url in visited:
                return 0, 0
            visited.add(current_url)

            logger.info(f"掃描目錄: {current_url}")

            try:
                response = requests.get(current_url, auth=auth, timeout=20)
                response.raise_for_status()
            except Exception as e:
                logger.debug(f"目錄請求失敗 {current_url}: {e}")
                return 0, 0

            try:
                soup = BeautifulSoup(response.text, 'html.parser')
            except Exception as e:
                logger.debug(f"解析 HTML 失敗 {current_url}: {e}")
                return 0, 0

            local_count = 0
            local_size = 0

            # Find candidate links - prefer the directory listing table if present
            candidates = []
            # Some Jenkins instances render a table with file links
            table = soup.find('table')
            if table:
                candidates = table.find_all('a', href=True)
            else:
                # fallback to all anchors
                candidates = soup.find_all('a', href=True)

            for link in candidates:
                href = link['href']

                # Normalize and filter links to avoid Jenkins UI links and external links
                if href.startswith('http'):
                    # external/absolute link - skip
                    continue
                if href.startswith('/'):
                    # absolute path in site - skip (not a relative workspace file)
                    continue
                if href.startswith('..'):
                    continue
                if href.startswith('#'):
                    # anchor link - skip
                    continue
                if any(token in href for token in ('login', 'signup', 'skip2content', 'blue/organizations', 'job/', 'execution/')):
                    # Jenkins UI navigation links - skip
                    continue
                if href.strip() == '':
                    continue

                is_directory = href.endswith('/')

                # name is the href without trailing slash
                name = href.rstrip('/')

                # prevent weird names
                if name in ('.', '..'):
                    continue

                # Build relative path for child
                child_rel = urllib.parse.urljoin(rel_path, href)
                # Ensure child_rel stays within workspace_url path (no climbing out)
                if child_rel.startswith('../') or child_rel.count('/') > 300:
                    continue

                if is_directory:
                    c_count, c_size = _walk(child_rel, depth + 1, visited)
                    local_count += c_count
                    local_size += c_size
                else:
                    # Download file
                    file_url = urllib.parse.urljoin(current_url, href)
                    save_path = target_path.joinpath(child_rel)
                    ok = self._download_file_from_jenkins(file_url, save_path, auth)
                    if ok and save_path.exists():
                        fs = save_path.stat().st_size
                        local_size += fs
                        local_count += 1
                        logger.info(f"  ✓ {child_rel} ({fs/1024:.2f} KB)")

            return local_count, local_size

        # start recursion with visited set
        try:
            visited = set()
            files_count, total_size = _walk(relative_path, 0, visited)
        except Exception as e:
            logger.error(f"遞歸下載失敗: {e}", exc_info=True)

        return files_count, total_size

    def _detect_pipeline_workspace_url(
        self,
        workspace_url: str,
        auth: Optional[tuple] = None
    ) -> str:
        """
        檢測 Pipeline Job 的實際 workspace URL
        
        對於 Pipeline 類型的 Job，workspace 通常位於:
        http://...job/JOB_NAME/BUILD/execution/node/NODE_ID/ws/
        而不是:
        http://...job/JOB_NAME/BUILD/ws/
        
        此方法會解析 /ws/ 頁面，找到實際的 workspace 連結
        
        Args:
            workspace_url: 原始 workspace URL
            auth: Jenkins 認證資訊 (username, api_token)
            
        Returns:
            str: 實際的 workspace URL（如果是 Pipeline）或原始 URL
        """
        try:
            # 訪問原始 workspace URL
            response = requests.get(workspace_url, auth=auth, timeout=10)
            response.raise_for_status()
            
            # 解析 HTML，查找 workspace 連結
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # 查找所有包含 /ws/ 的連結
            workspace_links = []
            for link in soup.find_all('a', href=True):
                href = link['href']
                # 查找 execution/node/X/ws/ 格式的連結
                if '/execution/node/' in href and '/ws/' in href:
                    # 轉換為絕對 URL
                    if href.startswith('/'):
                        # 構建完整 URL
                        from urllib.parse import urlparse
                        parsed = urlparse(workspace_url)
                        full_url = f"{parsed.scheme}://{parsed.netloc}{href}"
                        workspace_links.append(full_url)
                    elif href.startswith('http'):
                        workspace_links.append(href)
            
            if workspace_links:
                # 優先選擇包含 '/workspace' 的連結（主 workspace）
                # 而不是 '/workspace@script' 或其他變體
                main_workspace = None
                for link in workspace_links:
                    if '/workspace' in link and '/workspace@' not in link:
                        main_workspace = link
                        break
                
                # 如果沒找到主 workspace，使用第一個
                detected_url = main_workspace or workspace_links[0]
                
                # 確保 URL 以 / 結尾
                if not detected_url.endswith('/'):
                    detected_url += '/'
                
                logger.info(f"檢測到 Pipeline Workspace: {detected_url}")
                return detected_url
            
            # 沒有找到特殊的 workspace 連結，使用原始 URL
            logger.info(f"使用原始 Workspace URL: {workspace_url}")
            return workspace_url
            
        except Exception as e:
            logger.warning(f"檢測 Pipeline Workspace 失敗: {e}，使用原始 URL")
            return workspace_url
    
    def store_workspace(
        self, 
        workspace_url: str, 
        username: Optional[str] = None, 
        api_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        下載並存儲 Jenkins Workspace
        
        支持兩種下載方式：
        1. ZIP Archive（優先，如果可用）
        2. 遞歸下載（備用方案）
        
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
                - download_method: str (zip 或 recursive)
                - error: str (如果失敗)
        """
        try:
            # 創建存儲目錄
            workspace_path = self.build_storage_path / 'workspace'
            workspace_path.mkdir(parents=True, exist_ok=True)
            
            auth = None
            if username and api_token:
                auth = (username, api_token)
            
            # 自動檢測 Pipeline Workspace URL
            detected_url = self._detect_pipeline_workspace_url(workspace_url, auth)
            if detected_url != workspace_url:
                logger.info(f"使用檢測到的 Workspace URL: {detected_url}")
                workspace_url = detected_url
            
            logger.info(f"開始下載 Workspace: {workspace_url}")
            
            # 方法 1: 嘗試使用 ZIP Archive
            zip_url = f"{workspace_url.rstrip('/')}/*zip*/workspace.zip"
            logger.info(f"嘗試 ZIP 下載: {zip_url}")
            
            try:
                response = requests.head(zip_url, auth=auth, timeout=10)
                
                if response.status_code == 200:
                    logger.info("ZIP 端點可用，使用 ZIP 下載方式")
                    
                    # 下載 ZIP
                    response = requests.get(zip_url, auth=auth, stream=True, timeout=300)
                    response.raise_for_status()
                    
                    zip_file_path = self.build_storage_path / 'workspace.zip'
                    
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
                    
                    # 刪除 ZIP 文件
                    zip_file_path.unlink()
                    
                    download_method = 'zip'
                else:
                    raise Exception(f"ZIP 端點不可用: {response.status_code}")
                    
            except Exception as zip_error:
                logger.warning(f"ZIP 下載失敗: {zip_error}，改用遞歸下載方式")
                
                # 方法 2: 遞歸下載
                files_count, total_size = self._download_workspace_recursively(
                    workspace_url, 
                    workspace_path, 
                    auth
                )
                
                logger.info(f"遞歸下載完成: {files_count} 個文件, {total_size / (1024**2):.2f} MB")
                
                download_method = 'recursive'
            
            # 重新計算總大小和文件數量（確保準確）
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
                'download_method': download_method,
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
