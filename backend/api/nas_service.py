"""
NAS 連線監控服務
用於定時檢測 NAS SMB 共享連線狀態，並記錄效能指標
"""
import logging
import time
import os
import tempfile
from datetime import datetime
from smb.SMBConnection import SMBConnection
from django.utils import timezone
from .models import NASConnectionLog

logger = logging.getLogger(__name__)

# NAS 配置
NAS_CONFIG = {
    'ip': '10.250.0.1',
    'username': 'mdt',
    'password': 'p@ssw0rd',
    'share': 'mdt',
    'test_path': 'Script/chunwei_tset/nas_test',  # 測試檔案路徑
    'domain': '',  # 工作組或域名（如果需要）
    'client_name': 'network_toolbox',  # 客戶端名稱
}


def check_nas_connection():
    """
    檢查 NAS 連線狀態
    返回: (status, response_time, upload_speed, download_speed, error_message)
    """
    start_time = time.time()
    status = 'failed'
    response_time = None
    upload_speed = None
    download_speed = None
    error_message = ''
    
    conn = None
    
    try:
        # 建立 SMB 連線
        conn = SMBConnection(
            NAS_CONFIG['username'],
            NAS_CONFIG['password'],
            NAS_CONFIG['client_name'],
            'NAS',  # 伺服器名稱
            domain=NAS_CONFIG['domain'],
            use_ntlm_v2=True,
            is_direct_tcp=True
        )
        
        # 連接到 NAS
        logger.info(f'正在連接 NAS: {NAS_CONFIG["ip"]}')
        connected = conn.connect(NAS_CONFIG['ip'], 445)
        
        if not connected:
            error_message = 'SMB 連線失敗'
            logger.error(error_message)
            return status, response_time, upload_speed, download_speed, error_message
        
        # 測量響應時間
        response_time = (time.time() - start_time) * 1000  # 轉換為毫秒
        logger.info(f'NAS 連線成功，響應時間: {response_time:.2f} ms')
        
        # 測試上傳速度（可選）
        upload_speed = test_upload_speed(conn)
        
        # 測試下載速度（可選）
        download_speed = test_download_speed(conn)
        
        status = 'success'
        
    except Exception as e:
        error_message = str(e)
        logger.error(f'NAS 連線檢測失敗: {error_message}', exc_info=True)
        
    finally:
        # 關閉連線
        if conn:
            try:
                conn.close()
            except:
                pass
    
    return status, response_time, upload_speed, download_speed, error_message


def test_upload_speed(conn, test_size_mb=1):
    """
    測試上傳速度
    :param conn: SMB 連線物件
    :param test_size_mb: 測試檔案大小（MB）
    :return: 上傳速度（MB/s）
    """
    try:
        # 生成測試檔案
        test_data = os.urandom(test_size_mb * 1024 * 1024)
        test_filename = f'upload_test_{int(time.time())}.tmp'
        test_path = f'{NAS_CONFIG["test_path"]}/{test_filename}'
        
        # 上傳測試
        start_time = time.time()
        
        with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
            tmp_file.write(test_data)
            tmp_file.flush()
            tmp_file.seek(0)
            
            # 上傳到 NAS
            conn.storeFile(NAS_CONFIG['share'], test_path, tmp_file)
        
        upload_time = time.time() - start_time
        upload_speed = test_size_mb / upload_time if upload_time > 0 else 0
        
        # 刪除測試檔案
        try:
            conn.deleteFiles(NAS_CONFIG['share'], test_path)
        except:
            pass
        
        logger.info(f'上傳速度: {upload_speed:.2f} MB/s')
        return upload_speed
        
    except Exception as e:
        logger.warning(f'上傳速度測試失敗: {str(e)}')
        return None


def test_download_speed(conn, test_size_mb=1):
    """
    測試下載速度
    :param conn: SMB 連線物件
    :param test_size_mb: 測試檔案大小（MB）
    :return: 下載速度（MB/s）
    """
    try:
        # 先上傳一個測試檔案
        test_data = os.urandom(test_size_mb * 1024 * 1024)
        test_filename = f'download_test_{int(time.time())}.tmp'
        test_path = f'{NAS_CONFIG["test_path"]}/{test_filename}'
        
        with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
            tmp_file.write(test_data)
            tmp_file.flush()
            tmp_file.seek(0)
            conn.storeFile(NAS_CONFIG['share'], test_path, tmp_file)
        
        # 下載測試
        start_time = time.time()
        
        with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
            conn.retrieveFile(NAS_CONFIG['share'], test_path, tmp_file)
        
        download_time = time.time() - start_time
        download_speed = test_size_mb / download_time if download_time > 0 else 0
        
        # 刪除測試檔案
        try:
            conn.deleteFiles(NAS_CONFIG['share'], test_path)
        except:
            pass
        
        logger.info(f'下載速度: {download_speed:.2f} MB/s')
        return download_speed
        
    except Exception as e:
        logger.warning(f'下載速度測試失敗: {str(e)}')
        return None


def record_nas_connection():
    """
    執行 NAS 連線檢測並記錄到數據庫
    這個函數會被定時任務調用
    """
    logger.info('開始執行 NAS 連線檢測...')
    
    try:
        # 執行連線檢測
        status, response_time, upload_speed, download_speed, error_message = check_nas_connection()
        
        # 記錄到數據庫
        log_entry = NASConnectionLog.objects.create(
            timestamp=timezone.now(),
            status=status,
            nas_ip=NAS_CONFIG['ip'],
            nas_share=NAS_CONFIG['share'],
            response_time=response_time,
            upload_speed=upload_speed,
            download_speed=download_speed,
            error_message=error_message,
        )
        
        logger.info(f'NAS 連線記錄已儲存: {log_entry}')
        
        # 清理舊數據（超過2週的記錄）
        cleanup_old_records()
        
        return True
        
    except Exception as e:
        logger.error(f'記錄 NAS 連線狀態失敗: {str(e)}', exc_info=True)
        return False


def cleanup_old_records():
    """
    清理超過2週的舊記錄
    """
    try:
        from datetime import timedelta
        cutoff_date = timezone.now() - timedelta(days=14)
        
        deleted_count, _ = NASConnectionLog.objects.filter(
            timestamp__lt=cutoff_date
        ).delete()
        
        if deleted_count > 0:
            logger.info(f'已清理 {deleted_count} 筆超過2週的 NAS 連線記錄')
        
    except Exception as e:
        logger.error(f'清理舊 NAS 記錄失敗: {str(e)}', exc_info=True)


def get_nas_statistics(days=7):
    """
    獲取 NAS 連線統計資料
    :param days: 統計天數
    :return: 統計資料字典
    """
    from datetime import timedelta
    
    start_time = timezone.now() - timedelta(days=days)
    logs = NASConnectionLog.objects.filter(timestamp__gte=start_time)
    
    total_records = logs.count()
    success_count = logs.filter(status='success').count()
    failed_count = logs.filter(status='failed').count()
    
    success_rate = (success_count / total_records * 100) if total_records > 0 else 0
    
    # 平均效能指標
    success_logs = logs.filter(status='success')
    avg_response_time = 0
    avg_upload_speed = 0
    avg_download_speed = 0
    
    if success_logs.exists():
        response_times = [log.response_time for log in success_logs if log.response_time]
        upload_speeds = [log.upload_speed for log in success_logs if log.upload_speed]
        download_speeds = [log.download_speed for log in success_logs if log.download_speed]
        
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0
        avg_upload_speed = sum(upload_speeds) / len(upload_speeds) if upload_speeds else 0
        avg_download_speed = sum(download_speeds) / len(download_speeds) if download_speeds else 0
    
    return {
        'total_records': total_records,
        'success_count': success_count,
        'failed_count': failed_count,
        'success_rate': round(success_rate, 2),
        'avg_response_time': round(avg_response_time, 2),
        'avg_upload_speed': round(avg_upload_speed, 2),
        'avg_download_speed': round(avg_download_speed, 2),
    }
