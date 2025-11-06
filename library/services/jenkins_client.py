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
            list: Build 列表
        """
        # 使用 tree 參數只獲取需要的字段，提高效率
        url = f"{self.base_url}/job/{job_name}/api/json?tree=builds[number,url,result,timestamp,duration,building]{{0,{limit}}}"
        response = self._make_request('GET', url)
        data = response.json()
        builds = data.get('builds', [])
        
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
    
    def close(self):
        """關閉 Session"""
        self.session.close()
        logger.debug("JenkinsClient Session 已關閉")
