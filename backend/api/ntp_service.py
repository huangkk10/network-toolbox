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


class NTPSyncService(NTPService):
    """
    NTP 時間同步執行服務類
    繼承自 NTPService，新增實際同步系統時間的功能
    """
    
    def can_sync_now(self) -> tuple[bool, str]:
        """
        檢查是否可以執行時間同步
        
        檢查項目：
        1. 距離上次同步時間是否 >= 30 分鐘
        2. 是否有其他同步操作正在進行中
        
        Returns:
            tuple[bool, str]: (是否允許同步, 原因說明)
        """
        from api.models import NTPSyncOperation
        from django.utils import timezone
        from datetime import timedelta
        
        try:
            # 檢查是否有正在進行的同步操作
            pending_ops = NTPSyncOperation.objects.filter(status='pending').count()
            if pending_ops > 0:
                reason = f"有 {pending_ops} 個同步操作正在進行中，請稍後再試"
                logger.warning(f"can_sync_now: {reason}")
                return False, reason
            
            # 檢查上次同步時間
            last_sync = NTPSyncOperation.objects.filter(
                status='success'
            ).order_by('-timestamp').first()
            
            if last_sync:
                time_since_last = timezone.now() - last_sync.timestamp
                min_interval = timedelta(minutes=30)
                
                if time_since_last < min_interval:
                    remaining = min_interval - time_since_last
                    minutes = int(remaining.total_seconds() / 60)
                    reason = f"距離上次同步僅 {int(time_since_last.total_seconds() / 60)} 分鐘，請等待 {minutes} 分鐘後再試"
                    logger.info(f"can_sync_now: {reason}")
                    return False, reason
            
            reason = "允許執行時間同步"
            logger.info(f"can_sync_now: {reason}")
            return True, reason
            
        except Exception as e:
            error_msg = f"檢查同步權限時發生錯誤: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return False, error_msg
    
    def should_sync(self, threshold_ms: float = 200.0) -> tuple[bool, str, Optional[float]]:
        """
        判斷是否應該執行時間同步
        
        決策邏輯：
        1. 查詢最近 3 筆 NTPSyncLog 記錄
        2. 計算平均 offset（絕對值）
        3. 如果平均 offset > threshold_ms，則建議同步
        
        Args:
            threshold_ms: 閾值（毫秒），預設 200ms
        
        Returns:
            tuple[bool, str, Optional[float]]: (是否應該同步, 決策原因, 當前偏移量)
        """
        from api.models import NTPSyncLog
        
        try:
            # 獲取最近 3 筆日誌記錄
            recent_logs = NTPSyncLog.objects.filter(
                status='success'
            ).order_by('-check_time')[:3]
            
            if not recent_logs:
                reason = "無歷史 NTP 檢查記錄，建議執行首次同步"
                logger.info(f"should_sync: {reason}")
                return True, reason, None
            
            # 計算平均 offset（絕對值）
            offsets = [abs(log.offset) for log in recent_logs]
            avg_offset = sum(offsets) / len(offsets)
            
            logger.info(f"should_sync: 最近 {len(offsets)} 筆記錄平均偏移量 = {avg_offset:.3f}ms (閾值: {threshold_ms}ms)")
            
            if avg_offset > threshold_ms:
                reason = f"平均時間偏移 {avg_offset:.3f}ms 超過閾值 {threshold_ms}ms，建議同步"
                logger.warning(f"should_sync: {reason}")
                return True, reason, avg_offset
            else:
                reason = f"平均時間偏移 {avg_offset:.3f}ms 在可接受範圍內"
                logger.info(f"should_sync: {reason}")
                return False, reason, avg_offset
                
        except Exception as e:
            error_msg = f"判斷是否需要同步時發生錯誤: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return False, error_msg, None
    
    def sync_system_time(self, method: str = 'ntpdate', triggered_by: str = 'auto') -> Dict:
        """
        執行系統時間同步
        
        Args:
            method: 同步方法，可選 'ntpdate' 或 'chrony'（目前僅支援 ntpdate）
            triggered_by: 觸發方式 ('auto', 'manual', 'alert')
        
        Returns:
            Dict: 同步結果
            {
                'success': bool,
                'offset_before': float (ms),
                'offset_after': float (ms),
                'improvement': float (ms),
                'duration': float (秒),
                'command_output': str,
                'error_message': str
            }
        """
        import subprocess
        import time
        
        result = {
            'success': False,
            'offset_before': None,
            'offset_after': None,
            'improvement': None,
            'duration': None,
            'command_output': '',
            'error_message': ''
        }
        
        try:
            logger.info(f"開始執行時間同步 - Method: {method}, Triggered by: {triggered_by}")
            start_time = time.time()
            
            # Step 1: 檢查同步前的時間偏移
            logger.info("Step 1: 檢查同步前的時間偏移")
            before_check = self.check_sync()
            
            if before_check['status'] != 'success':
                result['error_message'] = f"同步前檢查失敗: {before_check['error_message']}"
                logger.error(result['error_message'])
                return result
            
            result['offset_before'] = before_check['offset']
            logger.info(f"同步前偏移量: {result['offset_before']:.3f}ms")
            
            # Step 2: 執行時間同步
            if method == 'ntpdate':
                logger.info("Step 2: 執行 ntpdate 同步命令")
                cmd = ['sudo', 'ntpdate', '-u', self.ntp_server]
                
                try:
                    # 執行同步命令
                    proc = subprocess.run(
                        cmd,
                        capture_output=True,
                        text=True,
                        timeout=30
                    )
                    
                    result['command_output'] = proc.stdout + proc.stderr
                    logger.info(f"ntpdate 輸出: {result['command_output']}")
                    
                    if proc.returncode != 0:
                        result['error_message'] = f"ntpdate 執行失敗 (Exit code: {proc.returncode}): {proc.stderr}"
                        logger.error(result['error_message'])
                        return result
                    
                except subprocess.TimeoutExpired:
                    result['error_message'] = "ntpdate 命令執行超時（30秒）"
                    logger.error(result['error_message'])
                    return result
                    
            else:
                result['error_message'] = f"不支援的同步方法: {method}"
                logger.error(result['error_message'])
                return result
            
            # Step 3: 等待 2 秒讓系統時間穩定
            logger.info("Step 3: 等待系統時間穩定...")
            time.sleep(2)
            
            # Step 4: 檢查同步後的時間偏移
            logger.info("Step 4: 檢查同步後的時間偏移")
            after_check = self.check_sync()
            
            if after_check['status'] != 'success':
                result['error_message'] = f"同步後檢查失敗: {after_check['error_message']}"
                logger.error(result['error_message'])
                # 注意：即使檢查失敗，同步可能已經成功
                result['success'] = True  # 標記為成功，但缺少 after 數據
                return result
            
            result['offset_after'] = after_check['offset']
            logger.info(f"同步後偏移量: {result['offset_after']:.3f}ms")
            
            # Step 5: 計算改善量
            result['improvement'] = abs(result['offset_before']) - abs(result['offset_after'])
            result['duration'] = time.time() - start_time
            result['success'] = True
            
            logger.info(
                f"✅ 時間同步成功 - "
                f"改善量: {result['improvement']:.3f}ms, "
                f"耗時: {result['duration']:.2f}秒"
            )
            
            return result
            
        except Exception as e:
            result['error_message'] = f"時間同步過程發生錯誤: {str(e)}"
            result['duration'] = time.time() - start_time if 'start_time' in locals() else None
            logger.error(result['error_message'], exc_info=True)
            return result


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
