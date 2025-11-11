"""
NTP 時間同步服務
用於檢測和記錄 NTP 時間同步狀態
"""

import ntplib
import time
import logging
from datetime import datetime
from typing import Dict, Optional
import pytz

logger = logging.getLogger(__name__)


class NTPService:
    """NTP 時間同步服務類"""
    
    def __init__(self, ntp_server: str = '10.10.10.51', timeout: int = 5):
        """
        初始化 NTP 服務
        
        Args:
            ntp_server: NTP 伺服器地址
            timeout: 超時時間（秒）
        """
        self.ntp_server = ntp_server
        self.timeout = timeout
        self.client = ntplib.NTPClient()
    
    def check_sync(self) -> Dict:
        """
        檢查 NTP 時間同步狀態
        
        Returns:
            Dict: 包含同步狀態的字典
            {
                'status': 'success' | 'failed',
                'ntp_server': str,
                'response_time': float (ms),
                'offset': float (ms),
                'stratum': int,
                'jitter': float (ms),
                'error_message': str
            }
        """
        result = {
            'status': 'failed',
            'ntp_server': self.ntp_server,
            'response_time': None,
            'offset': None,
            'stratum': None,
            'jitter': None,
            'error_message': ''
        }
        
        try:
            logger.info(f"開始檢查 NTP 同步狀態: {self.ntp_server}")
            start_time = time.time()
            
            # 發送 NTP 請求
            response = self.client.request(self.ntp_server, version=4, timeout=self.timeout)
            
            # 計算響應時間（毫秒）
            response_time = (time.time() - start_time) * 1000
            
            # 獲取時間偏移（毫秒）
            offset = response.offset * 1000
            
            # 獲取 Stratum（時間源層級）
            stratum = response.stratum
            
            # 獲取 Root Delay（作為 jitter 的估計值，毫秒）
            jitter = response.root_delay * 1000 if hasattr(response, 'root_delay') else None
            
            result.update({
                'status': 'success',
                'response_time': round(response_time, 2),
                'offset': round(offset, 3),
                'stratum': stratum,
                'jitter': round(jitter, 3) if jitter else None,
            })
            
            logger.info(
                f"NTP 同步成功 - Server: {self.ntp_server}, "
                f"Response: {response_time:.2f}ms, Offset: {offset:.3f}ms, "
                f"Stratum: {stratum}"
            )
            
        except ntplib.NTPException as e:
            error_msg = f"NTP 協議錯誤: {str(e)}"
            result['error_message'] = error_msg
            logger.error(f"NTP 同步失敗 ({self.ntp_server}): {error_msg}", exc_info=True)
            
        except OSError as e:
            error_msg = f"網路連接錯誤: {str(e)}"
            result['error_message'] = error_msg
            logger.error(f"NTP 同步失敗 ({self.ntp_server}): {error_msg}", exc_info=True)
            
        except Exception as e:
            error_msg = f"未知錯誤: {str(e)}"
            result['error_message'] = error_msg
            logger.error(f"NTP 同步失敗 ({self.ntp_server}): {error_msg}", exc_info=True)
        
        return result
    
    def get_ntp_info(self) -> Dict:
        """
        獲取 NTP 伺服器詳細資訊
        
        Returns:
            Dict: NTP 伺服器資訊
        """
        try:
            response = self.client.request(self.ntp_server, version=4, timeout=self.timeout)
            
            return {
                'server': self.ntp_server,
                'stratum': response.stratum,
                'precision': response.precision,
                'root_delay': response.root_delay * 1000,  # 轉換為毫秒
                'root_dispersion': response.root_dispersion * 1000,  # 轉換為毫秒
                'reference_id': response.ref_id,
                'reference_timestamp': datetime.fromtimestamp(
                    response.ref_time,
                    tz=pytz.timezone('Asia/Taipei')
                ).strftime('%Y-%m-%d %H:%M:%S'),
            }
        except Exception as e:
            logger.error(f"獲取 NTP 伺服器資訊失敗: {e}", exc_info=True)
            return None


def check_ntp_sync(ntp_server: str = '10.10.10.51') -> Dict:
    """
    便捷函數：檢查 NTP 時間同步狀態
    
    Args:
        ntp_server: NTP 伺服器地址
    
    Returns:
        Dict: 同步狀態字典
    """
    service = NTPService(ntp_server)
    return service.check_sync()
