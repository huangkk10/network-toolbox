"""
Jenkins REST API 客戶端服務

提供與 Jenkins 伺服器交互的 API 方法，支援直接 HTTP 連接（不使用 SSH Tunnel）
"""

import requests
import logging
from typing import Dict, List, Optional, Any
from bs4 import BeautifulSoup
import json
import re

logger = logging.getLogger(__name__)


class JenkinsClient:
    """Jenkins REST API 客戶端"""
    
    def __init__(
        self,
        base_url: str,
        username: Optional[str] = None,
        api_token: Optional[str] = None,
        timeout: int = 30
    ):
        """
        初始化 Jenkins 客戶端
        
        Args:
            base_url: Jenkins 伺服器 URL (例如: http://192.168.1.100:8080)
            username: Jenkins 使用者名稱（可選）
            api_token: Jenkins API Token（可選）
            timeout: 請求超時時間（秒）
        """
        self.base_url = base_url.rstrip('/')
        self.username = username
        self.api_token = api_token
        self.timeout = timeout
        self.session = requests.Session()
        
        # 設置認證
        if username and api_token:
            self.session.auth = (username, api_token)
        
        logger.info(f"JenkinsClient 初始化: {self.base_url}")
    
    def _make_request(
        self,
        method: str,
        url: str,
        **kwargs
    ) -> requests.Response:
        """
        發送 HTTP 請求
        
        Args:
            method: HTTP 方法 (GET, POST, etc.)
            url: 請求 URL
            **kwargs: 其他請求參數
            
        Returns:
            Response 對象
            
        Raises:
            requests.RequestException: 請求失敗
        """
        try:
            kwargs.setdefault('timeout', self.timeout)
            response = self.session.request(method, url, **kwargs)
            response.raise_for_status()
            return response
        except requests.RequestException as e:
            logger.error(f"Jenkins API 請求失敗: {url}", exc_info=True)
            raise
    
    def test_connection(self) -> bool:
        """
        測試連接是否正常
        
        Returns:
            bool: 連接是否成功
        """
        try:
            url = f"{self.base_url}/api/json"
            response = self._make_request('GET', url)
            logger.info(f"Jenkins 連接測試成功: {self.base_url}")
            return True
        except Exception as e:
            logger.error(f"Jenkins 連接測試失敗: {e}")
            return False
    
    def get_server_info(self) -> Dict[str, Any]:
        """
        獲取 Jenkins 伺服器資訊
        
        Returns:
            dict: 伺服器資訊
        """
        url = f"{self.base_url}/api/json"
        response = self._make_request('GET', url)
        data = response.json()
        
        logger.debug(f"獲取伺服器資訊: {data.get('nodeDescription', 'N/A')}")
        return data
    
    def list_jobs(self, folder_path: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        列出所有 Job
        
        Args:
            folder_path: 資料夾路徑（可選，用於多級目錄）
            
        Returns:
            list: Job 列表
        """
        if folder_path:
            url = f"{self.base_url}/job/{folder_path}/api/json"
        else:
            url = f"{self.base_url}/api/json?tree=jobs[name,url,buildable,color]"
        
        response = self._make_request('GET', url)
        data = response.json()
        jobs = data.get('jobs', [])
        
        logger.info(f"獲取 Job 列表: 共 {len(jobs)} 個 Job")
        return jobs
    
    def list_views(self) -> List[Dict[str, Any]]:
        """
        列出所有 View (視圖)
        
        Returns:
            list: View 列表
        """
        url = f"{self.base_url}/api/json"
        response = self._make_request('GET', url)
        data = response.json()
        views = data.get('views', [])
        
        logger.info(f"獲取 View 列表: 共 {len(views)} 個 View")
        return views
    
    def get_view_jobs(self, view_name: str) -> List[Dict[str, Any]]:
        """
        獲取指定 View 下的所有 Job
        
        Args:
            view_name: View 名稱
            
        Returns:
            list: Job 列表
        """
        url = f"{self.base_url}/view/{view_name}/api/json"
        response = self._make_request('GET', url)
        data = response.json()
        jobs = data.get('jobs', [])
        
        logger.info(f"獲取 View '{view_name}' 的 Job: 共 {len(jobs)} 個")
        return jobs
    
    def get_job_builds(self, job_name: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        獲取指定 Job 的 Builds
        
        Args:
            job_name: Job 名稱
            limit: 返回的 Build 數量限制
            
        Returns:
            list: Build 列表（包含 parameters 和 git_branch）
        """
        # 使用 tree 參數獲取需要的字段，包含 actions 以獲取 parameters 和 Git 資訊
        # actions[parameters[name,value]] 用於獲取 Build 參數
        # actions[lastBuiltRevision[branch[name]]] 用於獲取 Git branch（從 BuildData）
        url = f"{self.base_url}/job/{job_name}/api/json?tree=builds[number,url,result,timestamp,duration,building,actions[parameters[name,value],lastBuiltRevision[branch[name,SHA1]]]]{{0,{limit}}}"
        response = self._make_request('GET', url)
        data = response.json()
        builds = data.get('builds', [])
        
        # 解析每個 Build 的 parameters 和 git_branch
        for build in builds:
            parameters = {}
            git_branch = None
            git_sha = None
            
            actions = build.get('actions', [])
            for action in actions:
                if not action:
                    continue
                    
                # 解析 Build 參數
                if 'parameters' in action:
                    for param in action.get('parameters', []):
                        if param.get('name') and param.get('value') is not None:
                            parameters[param['name']] = param['value']
                
                # 解析 Git branch（從 hudson.plugins.git.util.BuildData）
                if 'lastBuiltRevision' in action:
                    revision = action.get('lastBuiltRevision', {})
                    branches = revision.get('branch', [])
                    if branches and len(branches) > 0:
                        branch_name = branches[0].get('name', '')
                        # 移除各種 Git ref 前綴，只保留 branch 名稱
                        # 例如: refs/remotes/origin/main -> main
                        #       refs/heads/main -> main
                        #       origin/main -> main
                        for prefix in ['refs/remotes/origin/', 'refs/heads/', 'origin/']:
                            if branch_name.startswith(prefix):
                                branch_name = branch_name[len(prefix):]
                                break
                        git_branch = branch_name
                        git_sha = branches[0].get('SHA1', '')
            
            build['parameters'] = parameters
            build['git_branch'] = git_branch
            build['git_sha'] = git_sha
        
        logger.info(f"獲取 Job '{job_name}' 的 Builds: 共 {len(builds)} 個")
        return builds
    
    def get_blue_ocean_pipeline_nodes(self, job_name: str, build_number: int) -> List[Dict[str, Any]]:
        """
        獲取 Blue Ocean Pipeline 的所有 Stage/Node 資訊
        
        Args:
            job_name: Job 名稱
            build_number: Build 編號
            
        Returns:
            list: Stage/Node 列表，包含每個 Stage 的狀態和詳細資訊
            
        Example:
            [
                {
                    'id': '3',
                    'displayName': 'Checkout',
                    'result': 'SUCCESS',
                    'state': 'FINISHED',
                    'durationInMillis': 1234,
                    'startTime': '2025-11-06T10:30:00.000+0000',
                    'type': 'STAGE'
                },
                {
                    'id': '5',
                    'displayName': 'Build',
                    'result': 'FAILURE',
                    'state': 'FINISHED',
                    'durationInMillis': 5678,
                    'startTime': '2025-11-06T10:30:05.000+0000',
                    'type': 'STAGE',
                    'error': {'message': 'Build failed'}
                }
            ]
        """
        try:
            # Blue Ocean API 端點
            url = f"{self.base_url}/blue/rest/organizations/jenkins/pipelines/{job_name}/runs/{build_number}/nodes/"
            response = self._make_request('GET', url)
            nodes = response.json()
            
            logger.info(f"獲取 Blue Ocean Pipeline Nodes: Job='{job_name}', Build={build_number}, Nodes={len(nodes)}")
            return nodes
            
        except Exception as e:
            logger.error(f"獲取 Blue Ocean Pipeline Nodes 失敗: {e}", exc_info=True)
            return []
    
    def get_failed_stages(self, job_name: str, build_number: int) -> List[Dict[str, Any]]:
        """
        獲取 Build 中失敗的 Stage 列表
        
        Args:
            job_name: Job 名稱
            build_number: Build 編號
            
        Returns:
            list: 失敗的 Stage 列表
            
        Example:
            [
                {
                    'stage_name': 'Build',
                    'result': 'FAILURE',
                    'duration_ms': 5678,
                    'duration_formatted': '5.7 秒',
                    'error_message': 'Build failed'
                }
            ]
        """
        nodes = self.get_blue_ocean_pipeline_nodes(job_name, build_number)
        
        failed_stages = []
        for node in nodes:
            # 只處理 STAGE 類型且失敗的節點
            if node.get('type') == 'STAGE' and node.get('result') in ['FAILURE', 'UNSTABLE', 'ABORTED']:
                duration_ms = node.get('durationInMillis', 0)
                duration_sec = duration_ms / 1000 if duration_ms else 0
                
                # 格式化執行時間
                if duration_sec >= 60:
                    duration_formatted = f"{int(duration_sec / 60)} 分 {int(duration_sec % 60)} 秒"
                else:
                    duration_formatted = f"{duration_sec:.1f} 秒"
                
                # 提取錯誤訊息
                error_message = None
                if 'error' in node and node['error']:
                    error_message = node['error'].get('message', 'Unknown error')
                
                failed_stages.append({
                    'stage_name': node.get('displayName', 'Unknown Stage'),
                    'result': node.get('result'),
                    'duration_ms': duration_ms,
                    'duration_formatted': duration_formatted,
                    'error_message': error_message,
                    'start_time': node.get('startTime'),
                })
        
        logger.info(f"找到 {len(failed_stages)} 個失敗的 Stage")
        return failed_stages
    
    def get_pipeline_summary(self, job_name: str, build_number: int) -> Dict[str, Any]:
        """
        獲取 Pipeline 執行摘要
        
        Args:
            job_name: Job 名稱
            build_number: Build 編號
            
        Returns:
            dict: Pipeline 摘要資訊
            
        Example:
            {
                'total_stages': 5,
                'successful_stages': 3,
                'failed_stages': 1,
                'aborted_stages': 0,
                'unstable_stages': 1,
                'stages': [...]
            }
        """
        nodes = self.get_blue_ocean_pipeline_nodes(job_name, build_number)
        
        # 統計各種狀態的 Stage
        stages = [node for node in nodes if node.get('type') == 'STAGE']
        
        summary = {
            'total_stages': len(stages),
            'successful_stages': sum(1 for s in stages if s.get('result') == 'SUCCESS'),
            'failed_stages': sum(1 for s in stages if s.get('result') == 'FAILURE'),
            'aborted_stages': sum(1 for s in stages if s.get('result') == 'ABORTED'),
            'unstable_stages': sum(1 for s in stages if s.get('result') == 'UNSTABLE'),
            'stages': [
                {
                    'name': s.get('displayName'),
                    'result': s.get('result'),
                    'duration_ms': s.get('durationInMillis', 0),
                }
                for s in stages
            ]
        }
        
        logger.info(f"Pipeline 摘要: 總共 {summary['total_stages']} 個 Stage, "
                   f"成功 {summary['successful_stages']}, "
                   f"失敗 {summary['failed_stages']}")
        
        return summary
    
    def get_build_artifacts(self, job_name: str, build_number: int) -> List[Dict[str, Any]]:
        """
        獲取 Build 的 Artifacts 列表
        
        Args:
            job_name: Job 名稱
            build_number: Build 編號
            
        Returns:
            list: Artifacts 列表
                [
                    {
                        'fileName': 'file.7z',
                        'relativePath': 'path/to/file.7z',
                        'displayPath': 'path/to/file.7z'
                    }
                ]
        """
        url = f"{self.base_url}/job/{job_name}/{build_number}/api/json"
        params = {'tree': 'artifacts[fileName,relativePath,displayPath]'}
        
        response = self._make_request('GET', url, params=params)
        data = response.json()
        artifacts = data.get('artifacts', [])
        
        logger.info(f"獲取 Build '{job_name}' #{build_number} 的 Artifacts: 共 {len(artifacts)} 個")
        return artifacts
    
    def get_console_log(self, job_name: str, build_number: int) -> str:
        """
        獲取 Build 的 Console Log
        
        Args:
            job_name: Job 名稱
            build_number: Build 編號
            
        Returns:
            str: Console Log 內容
            
        Raises:
            requests.RequestException: 請求失敗
            requests.HTTPError: 404 錯誤（Log 不存在）
        """
        url = f"{self.base_url}/job/{job_name}/{build_number}/consoleText"
        
        try:
            response = self._make_request('GET', url)
            log_content = response.text
            
            log_size_mb = len(log_content.encode('utf-8')) / (1024 * 1024)
            
            logger.info(
                f"獲取 Console Log 成功: {job_name} #{build_number} "
                f"({log_size_mb:.2f} MB)"
            )
            
            # 如果日誌較大，記錄警告
            if log_size_mb > 50:
                logger.warning(
                    f"Console Log 較大: {job_name} #{build_number} "
                    f"({log_size_mb:.2f} MB)，下載時間可能較長"
                )
            
            return log_content
            
        except requests.HTTPError as e:
            if e.response and e.response.status_code == 404:
                logger.warning(
                    f"Console Log 不存在（可能已被清理）: {job_name} #{build_number}"
                )
                raise requests.HTTPError(
                    f"404 Not Found: Console Log for {job_name} #{build_number}",
                    response=e.response
                )
            raise
        except requests.RequestException as e:
            logger.error(
                f"獲取 Console Log 失敗: {job_name} #{build_number} - {e}",
                exc_info=True
            )
            raise
    
    def get_artifact_size(self, job_name: str, build_number: int, artifact_path: str) -> int:
        """
        獲取 Artifact 檔案大小（使用 HEAD 請求）
        
        Args:
            job_name: Job 名稱
            build_number: Build 編號
            artifact_path: Artifact 相對路徑
            
        Returns:
            int: 檔案大小（bytes）
        """
        url = f"{self.base_url}/job/{job_name}/{build_number}/artifact/{artifact_path}"
        
        try:
            response = self._make_request('HEAD', url)
            content_length = response.headers.get('Content-Length', 0)
            file_size = int(content_length)
            
            logger.debug(f"Artifact 大小: {artifact_path} = {file_size / (1024**2):.2f} MB")
            return file_size
        except Exception as e:
            logger.warning(f"無法獲取 Artifact 大小 {artifact_path}: {e}")
            return 0
    
    def download_artifact(
        self, 
        job_name: str, 
        build_number: int, 
        artifact_path: str,
        save_path: str
    ) -> bool:
        """
        下載 Artifact 檔案
        
        Args:
            job_name: Job 名稱
            build_number: Build 編號
            artifact_path: Artifact 相對路徑（從 relativePath 取得）
            save_path: 本地保存路徑
            
        Returns:
            bool: 是否下載成功
        """
        from pathlib import Path
        
        url = f"{self.base_url}/job/{job_name}/{build_number}/artifact/{artifact_path}"
        
        try:
            logger.info(f"開始下載 Artifact: {artifact_path}")
            
            response = self._make_request('GET', url, stream=True)
            
            # 確保目錄存在
            save_file = Path(save_path)
            save_file.parent.mkdir(parents=True, exist_ok=True)
            
            # 下載文件
            with open(save_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            file_size = Path(save_path).stat().st_size
            logger.info(f"Artifact 下載成功: {artifact_path} ({file_size / (1024**2):.2f} MB)")
            return True
            
        except Exception as e:
            logger.error(f"Artifact 下載失敗 {artifact_path}: {e}")
            return False
    
    def close(self):
        """關閉 Session"""
        self.session.close()
        logger.debug("JenkinsClient Session 已關閉")
