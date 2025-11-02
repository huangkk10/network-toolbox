"""
GitLab 連線品質測試服務
提供 Ping 測試、HTTP 連線測試、封包遺失率計算等功能
"""

import subprocess
import requests
import time
import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class GitLabConnectionService:
    """GitLab 連線品質測試服務"""
    
    def __init__(self, gitlab_url: str, gitlab_name: str = 'GitLab Server', timeout: int = 5):
        """
        初始化 GitLab 連線服務
        
        Args:
            gitlab_url: GitLab 伺服器 URL (例如: http://10.252.170.11/)
            gitlab_name: GitLab 伺服器名稱
            timeout: 連線超時時間（秒）
        """
        self.gitlab_url = gitlab_url.rstrip('/')
        self.gitlab_name = gitlab_name
        self.timeout = timeout
        
        # 從 URL 提取 IP 或域名
        self.host = self._extract_host(gitlab_url)
    
    def _extract_host(self, url: str) -> str:
        """從 URL 提取主機名或 IP"""
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            return parsed.hostname or parsed.netloc.split(':')[0]
        except Exception as e:
            logger.error(f'解析 URL 失敗: {e}')
            return url
    
    def test_ping(self, count: int = 4) -> Dict:
        """
        Ping 測試
        
        Args:
            count: Ping 次數
            
        Returns:
            dict: {
                'success': bool,
                'latency': float (ms),
                'packet_loss': float (percentage),
                'error': str (if failed)
            }
        """
        try:
            result = subprocess.run(
                ['ping', '-c', str(count), '-W', str(self.timeout), self.host],
                capture_output=True,
                text=True,
                timeout=self.timeout * count + 5
            )
            
            if result.returncode != 0:
                # Ping 失敗
                return {
                    'success': False,
                    'latency': None,
                    'packet_loss': 100.0,
                    'error': 'Ping failed: host unreachable'
                }
            
            # 解析 ping 輸出
            output = result.stdout
            
            # 提取平均延遲（從類似 "rtt min/avg/max/mdev = 0.345/0.378/0.421/0.032 ms" 的行）
            latency = None
            for line in output.split('\n'):
                if 'rtt' in line.lower() or 'round-trip' in line.lower():
                    try:
                        parts = line.split('=')[1].strip().split('/')
                        latency = float(parts[1])  # avg
                    except:
                        pass
            
            # 提取封包遺失率（從類似 "4 packets transmitted, 4 received, 0% packet loss" 的行）
            packet_loss = 0.0
            for line in output.split('\n'):
                if 'packet loss' in line.lower():
                    try:
                        loss_str = line.split(',')[-1].strip()
                        packet_loss = float(loss_str.split('%')[0])
                    except:
                        pass
            
            return {
                'success': True,
                'latency': latency,
                'packet_loss': packet_loss,
                'error': None
            }
        
        except subprocess.TimeoutExpired:
            logger.error(f'Ping 超時: {self.host}')
            return {
                'success': False,
                'latency': None,
                'packet_loss': 100.0,
                'error': 'Ping timeout'
            }
        except Exception as e:
            logger.error(f'Ping 測試失敗: {e}', exc_info=True)
            return {
                'success': False,
                'latency': None,
                'packet_loss': 100.0,
                'error': f'Ping error: {str(e)}'
            }
    
    def test_http(self) -> Dict:
        """
        HTTP 連線測試
        
        Returns:
            dict: {
                'success': bool,
                'response_time': float (seconds),
                'status_code': int,
                'error': str (if failed)
            }
        """
        try:
            start_time = time.time()
            response = requests.get(
                self.gitlab_url,
                timeout=self.timeout,
                allow_redirects=True,
                verify=False  # 忽略 SSL 憑證驗證（內部網路）
            )
            response_time = time.time() - start_time
            
            return {
                'success': response.status_code < 500,  # 5xx 視為失敗
                'response_time': response_time,
                'status_code': response.status_code,
                'error': None if response.status_code < 500 else f'HTTP {response.status_code}'
            }
        
        except requests.exceptions.Timeout:
            logger.error(f'HTTP 請求超時: {self.gitlab_url}')
            return {
                'success': False,
                'response_time': self.timeout,
                'status_code': None,
                'error': 'HTTP timeout'
            }
        except requests.exceptions.ConnectionError as e:
            logger.error(f'HTTP 連線失敗: {e}')
            return {
                'success': False,
                'response_time': None,
                'status_code': None,
                'error': f'Connection error: {str(e)}'
            }
        except Exception as e:
            logger.error(f'HTTP 測試失敗: {e}', exc_info=True)
            return {
                'success': False,
                'response_time': None,
                'status_code': None,
                'error': f'HTTP error: {str(e)}'
            }
    
    def run_full_test(self) -> Dict:
        """
        執行完整連線品質測試
        
        Returns:
            dict: {
                'gitlab_url': str,
                'gitlab_name': str,
                'ping_latency': float (ms),
                'http_response_time': float (seconds),
                'http_status_code': int,
                'status': str ('success', 'failed', 'timeout'),
                'is_reachable': bool,
                'packet_loss': float (percentage),
                'error_message': str
            }
        """
        logger.info(f'開始測試 GitLab 連線品質: {self.gitlab_url}')
        
        result = {
            'gitlab_url': self.gitlab_url,
            'gitlab_name': self.gitlab_name,
            'ping_latency': None,
            'http_response_time': None,
            'http_status_code': None,
            'status': 'failed',
            'is_reachable': False,
            'packet_loss': 100.0,
            'error_message': ''
        }
        
        # Ping 測試
        ping_result = self.test_ping()
        result['ping_latency'] = ping_result.get('latency')
        result['packet_loss'] = ping_result.get('packet_loss', 100.0)
        
        if not ping_result['success']:
            result['error_message'] = ping_result.get('error', 'Ping failed')
            result['status'] = 'timeout' if 'timeout' in result['error_message'].lower() else 'failed'
            logger.warning(f'Ping 失敗: {result["error_message"]}')
            return result
        
        # HTTP 測試
        http_result = self.test_http()
        result['http_response_time'] = http_result.get('response_time')
        result['http_status_code'] = http_result.get('status_code')
        
        if not http_result['success']:
            result['error_message'] = http_result.get('error', 'HTTP connection failed')
            result['status'] = 'timeout' if 'timeout' in result['error_message'].lower() else 'failed'
            result['is_reachable'] = True  # Ping 成功但 HTTP 失敗
            logger.warning(f'HTTP 連線失敗: {result["error_message"]}')
            return result
        
        # 全部成功
        result['status'] = 'success'
        result['is_reachable'] = True
        result['error_message'] = ''
        
        logger.info(
            f'GitLab 連線測試成功: '
            f'Ping={result["ping_latency"]:.2f}ms, '
            f'HTTP={result["http_response_time"]:.3f}s, '
            f'Status={result["http_status_code"]}'
        )
        
        return result


def test_gitlab_connection(gitlab_url: str, gitlab_name: str = 'GitLab Server') -> Dict:
    """
    便捷函數：測試 GitLab 連線品質
    
    Args:
        gitlab_url: GitLab 伺服器 URL
        gitlab_name: GitLab 伺服器名稱
        
    Returns:
        dict: 測試結果
    """
    service = GitLabConnectionService(gitlab_url, gitlab_name)
    return service.run_full_test()
