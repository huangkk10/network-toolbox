"""
IPXE 伺服器網路品質監控服務
用於定時檢測 IPXE Server 的網路狀況，包括 Ping、HTTP、SSH 測試
"""
import logging
import time
import subprocess
import re
import requests
import paramiko
from datetime import datetime, timedelta
from django.utils import timezone
from .models import IPXEServer, IPXENetworkQuality

logger = logging.getLogger(__name__)


def ping_test(ip_address, count=4):
    """
    執行 Ping 測試
    :param ip_address: 目標 IP
    :param count: Ping 次數
    :return: (平均延遲(ms), 丟包率(%))
    """
    try:
        # 執行 ping 命令
        result = subprocess.run(
            ['ping', '-c', str(count), '-W', '2', ip_address],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        output = result.stdout
        
        # 解析丟包率
        packet_loss = 0
        loss_match = re.search(r'(\d+)% packet loss', output)
        if loss_match:
            packet_loss = float(loss_match.group(1))
        
        # 解析平均延遲
        avg_latency = None
        # Linux ping 輸出格式: rtt min/avg/max/mdev = 0.123/0.456/0.789/0.012 ms
        latency_match = re.search(r'rtt min/avg/max/mdev = [\d.]+/([\d.]+)/[\d.]+/[\d.]+', output)
        if latency_match:
            avg_latency = float(latency_match.group(1))
        
        logger.info(f'Ping {ip_address}: 延遲={avg_latency}ms, 丟包率={packet_loss}%')
        return avg_latency, packet_loss
        
    except subprocess.TimeoutExpired:
        logger.error(f'Ping {ip_address} 超時')
        return None, 100.0
    except Exception as e:
        logger.error(f'Ping {ip_address} 失敗: {str(e)}', exc_info=True)
        return None, 100.0


def http_test(ip_address, port=80, timeout=5):
    """
    執行 HTTP 測試
    :param ip_address: 目標 IP
    :param port: HTTP 端口
    :param timeout: 超時時間（秒）
    :return: (響應時間(ms), HTTP 狀態碼)
    """
    try:
        url = f'http://{ip_address}:{port}/'
        start_time = time.time()
        
        response = requests.get(url, timeout=timeout)
        
        response_time = (time.time() - start_time) * 1000  # 轉換為毫秒
        status_code = response.status_code
        
        logger.info(f'HTTP {url}: 響應時間={response_time:.2f}ms, 狀態碼={status_code}')
        return response_time, status_code
        
    except requests.exceptions.Timeout:
        logger.error(f'HTTP {ip_address} 超時')
        return None, 0
    except Exception as e:
        logger.error(f'HTTP {ip_address} 失敗: {str(e)}')
        return None, 0


def ssh_test(ip_address, username, password, port=22, timeout=5):
    """
    執行 SSH 連線測試
    :param ip_address: 目標 IP
    :param username: SSH 用戶名
    :param password: SSH 密碼
    :param port: SSH 端口
    :param timeout: 超時時間（秒）
    :return: (響應時間(ms), 是否成功)
    """
    try:
        start_time = time.time()
        
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        ssh.connect(
            ip_address,
            port=port,
            username=username,
            password=password,
            timeout=timeout,
            look_for_keys=False,
            allow_agent=False
        )
        
        response_time = (time.time() - start_time) * 1000  # 轉換為毫秒
        
        ssh.close()
        
        logger.info(f'SSH {ip_address}: 響應時間={response_time:.2f}ms')
        return response_time, True
        
    except Exception as e:
        logger.error(f'SSH {ip_address} 失敗: {str(e)}')
        return None, False


def download_speed_test(ip_address, port=80, test_file_size_kb=100, timeout=10):
    """
    執行下載速度測試
    :param ip_address: 目標 IP
    :param port: HTTP 端口
    :param test_file_size_kb: 測試檔案大小（KB）
    :param timeout: 超時時間（秒）
    :return: 下載速度（MB/s）
    """
    try:
        # 嘗試下載一個小檔案來測試速度
        # 假設 IPXE Server 有提供某個檔案，如果沒有就跳過
        url = f'http://{ip_address}:{port}/boot.ipxe'  # 使用 boot.ipxe 作為測試檔案
        
        start_time = time.time()
        response = requests.get(url, timeout=timeout, stream=True)
        
        # 下載內容
        total_bytes = 0
        for chunk in response.iter_content(chunk_size=8192):
            total_bytes += len(chunk)
        
        download_time = time.time() - start_time
        
        if download_time > 0:
            # 轉換為 MB/s
            download_speed = (total_bytes / (1024 * 1024)) / download_time
            logger.info(f'下載速度 {ip_address}: {download_speed:.2f} MB/s')
            return download_speed
        
        return None
        
    except Exception as e:
        logger.warning(f'下載速度測試 {ip_address} 失敗: {str(e)}')
        return None


def check_ipxe_network_quality(server_id):
    """
    檢查 IPXE 伺服器網路品質
    :param server_id: IPXE Server ID
    :return: (status, ping_latency, packet_loss, http_response_time, http_status, ssh_response_time, ssh_connected, download_speed, error_message)
    """
    try:
        server = IPXEServer.objects.get(id=server_id)
    except IPXEServer.DoesNotExist:
        logger.error(f'IPXE Server ID {server_id} 不存在')
        return ('failed', None, None, None, None, None, False, None, f'IPXE Server ID {server_id} 不存在')
    
    logger.info(f'開始檢測 IPXE Server: {server.name} ({server.ip_address})')
    
    error_messages = []
    success_tests = 0
    total_tests = 0
    
    # 1. Ping 測試（可選，因為容器中可能沒有 ping）
    ping_latency, packet_loss = ping_test(server.ip_address)
    if ping_latency is not None:
        total_tests += 1
        if packet_loss < 100:
            success_tests += 1
        else:
            error_messages.append('Ping 丟包率 100%')
    else:
        # Ping 失敗不算致命錯誤（可能是容器沒有 ping 工具）
        error_messages.append('Ping 測試失敗')
    
    # 2. HTTP 測試（重要）
    http_response_time, http_status = http_test(server.ip_address)
    total_tests += 1
    if http_response_time is not None and http_status in [200, 301, 302]:
        success_tests += 1
    else:
        error_messages.append(f'HTTP 測試失敗 (狀態碼: {http_status})')
    
    # 3. SSH 測試（如果有配置）
    ssh_response_time = None
    ssh_connected = False
    if server.ssh_username and server.ssh_password:
        total_tests += 1
        ssh_response_time, ssh_connected = ssh_test(
            server.ip_address,
            server.ssh_username,
            server.ssh_password,
            server.ssh_port
        )
        if ssh_connected:
            success_tests += 1
        else:
            error_messages.append('SSH 連接失敗')
    
    # 4. 下載速度測試（可選）
    download_speed = download_speed_test(server.ip_address)
    
    # 判斷整體狀態
    if total_tests == 0:
        status = 'failed'
    elif success_tests == total_tests:
        status = 'success'
    elif success_tests > 0:
        status = 'partial'  # 部分成功
    else:
        status = 'failed'
    
    error_message = '; '.join(error_messages) if error_messages else ''
    
    return (
        status,
        ping_latency,
        packet_loss,
        http_response_time,
        http_status,
        ssh_response_time,
        ssh_connected,
        download_speed,
        error_message
    )


def record_ipxe_network_quality(server_id):
    """
    執行 IPXE 網路品質檢測並記錄到數據庫
    這個函數會被定時任務調用
    """
    logger.info(f'開始執行 IPXE 網路品質檢測 (Server ID: {server_id})...')
    
    try:
        # 執行檢測
        (
            status,
            ping_latency,
            packet_loss,
            http_response_time,
            http_status,
            ssh_response_time,
            ssh_connected,
            download_speed,
            error_message
        ) = check_ipxe_network_quality(server_id)
        
        # 獲取 server 物件
        server = IPXEServer.objects.get(id=server_id)
        
        # 記錄到數據庫
        log_entry = IPXENetworkQuality.objects.create(
            server=server,
            timestamp=timezone.now(),
            status=status,
            ping_latency=ping_latency,
            ping_packet_loss=packet_loss,
            http_response_time=http_response_time,
            http_status_code=http_status,
            ssh_response_time=ssh_response_time,
            ssh_connected=ssh_connected,
            download_speed=download_speed,
            error_message=error_message,
        )
        
        logger.info(f'IPXE 網路品質記錄已儲存: {log_entry}')
        
        # 清理舊數據（超過2週的記錄）
        cleanup_old_records(server_id)
        
        return True
        
    except Exception as e:
        logger.error(f'記錄 IPXE 網路品質失敗: {str(e)}', exc_info=True)
        return False


def cleanup_old_records(server_id, days=14):
    """
    清理超過指定天數的舊記錄
    :param server_id: IPXE Server ID
    :param days: 保留天數（預設14天）
    """
    try:
        cutoff_date = timezone.now() - timedelta(days=days)
        
        deleted_count, _ = IPXENetworkQuality.objects.filter(
            server_id=server_id,
            timestamp__lt=cutoff_date
        ).delete()
        
        if deleted_count > 0:
            logger.info(f'已清理 {deleted_count} 筆超過 {days} 天的 IPXE 網路品質記錄 (Server ID: {server_id})')
        
    except Exception as e:
        logger.error(f'清理舊 IPXE 網路品質記錄失敗: {str(e)}', exc_info=True)


def get_ipxe_network_statistics(server_id, days=7):
    """
    獲取 IPXE 網路品質統計資料
    :param server_id: IPXE Server ID
    :param days: 統計天數
    :return: 統計資料字典
    """
    from datetime import timedelta
    from django.db.models import Avg, Max, Min
    
    start_time = timezone.now() - timedelta(days=days)
    logs = IPXENetworkQuality.objects.filter(
        server_id=server_id,
        timestamp__gte=start_time
    )
    
    total_records = logs.count()
    success_count = logs.filter(status='success').count()
    failed_count = logs.filter(status='failed').count()
    
    success_rate = (success_count / total_records * 100) if total_records > 0 else 0
    
    # 平均指標（只統計成功的記錄）
    success_logs = logs.filter(status='success')
    
    stats = success_logs.aggregate(
        avg_ping_latency=Avg('ping_latency'),
        min_ping_latency=Min('ping_latency'),
        max_ping_latency=Max('ping_latency'),
        avg_packet_loss=Avg('ping_packet_loss'),
        avg_http_response=Avg('http_response_time'),
        avg_download_speed=Avg('download_speed'),
    )
    
    return {
        'total_records': total_records,
        'success_count': success_count,
        'failed_count': failed_count,
        'success_rate': round(success_rate, 2),
        'avg_ping_latency': round(stats['avg_ping_latency'] or 0, 2),
        'min_ping_latency': round(stats['min_ping_latency'] or 0, 2),
        'max_ping_latency': round(stats['max_ping_latency'] or 0, 2),
        'avg_packet_loss': round(stats['avg_packet_loss'] or 0, 2),
        'avg_http_response': round(stats['avg_http_response'] or 0, 2),
        'avg_download_speed': round(stats['avg_download_speed'] or 0, 2),
    }
