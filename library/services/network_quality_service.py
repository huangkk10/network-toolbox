"""
網路品質監控服務

提供 DHCP Server 到各個 Switch 的網路品質檢測功能，
包括延遲、封包遺失率、抖動等指標的收集與分析。
"""

import subprocess
import re
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from django.utils import timezone
from django.db.models import Avg, Min, Max, Count

logger = logging.getLogger(__name__)


class NetworkQualityService:
    """網路品質服務類別（無狀態服務）"""
    
    # 品質閾值設定
    LATENCY_GOOD = 50       # 延遲 < 50ms 為良好
    LATENCY_WARNING = 100   # 延遲 50-100ms 為警告
    PACKET_LOSS_GOOD = 1    # 封包遺失 < 1% 為良好
    PACKET_LOSS_WARNING = 5 # 封包遺失 1-5% 為警告
    JITTER_GOOD = 10        # 抖動 < 10ms 為良好
    JITTER_WARNING = 30     # 抖動 10-30ms 為警告
        
    def test_switch_connectivity(self, target_ip: str) -> Dict:
        """
        測試到特定 IP 的網路連接品質
        
        Args:
            target_ip: 目標 IP 地址
            
        Returns:
            Dict: 包含測試結果的字典
        """
        if not target_ip:
            return {
                'success': False,
                'error': '沒有設定 IP 地址',
                'status': 'unknown'
            }
            
        try:
            # 執行 ping 測試（5 次）
            result = subprocess.run(
                ['ping', '-c', '5', '-W', '2', target_ip],
                capture_output=True,
                text=True,
                timeout=15
            )
            
            return self._parse_ping_result(result.stdout, result.returncode)
            
        except subprocess.TimeoutExpired:
            logger.warning(f"Ping 超時: {target_ip}")
            return {
                'success': False,
                'error': '連接超時',
                'status': 'critical',
                'latency': None,
                'packet_loss': 100.0,
                'jitter': None
            }
        except Exception as e:
            logger.error(f"Ping 執行錯誤: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
                'status': 'unknown'
            }
    
    def _parse_ping_result(self, output: str, return_code: int) -> Dict:
        """
        解析 ping 命令的輸出結果
        
        Args:
            output: ping 命令的標準輸出
            return_code: ping 命令的返回碼
            
        Returns:
            Dict: 解析後的結果
        """
        result = {
            'success': return_code == 0,
            'latency': None,
            'packet_loss': None,
            'jitter': None,
            'min_latency': None,
            'max_latency': None,
            'avg_latency': None,
            'status': 'unknown'
        }
        
        # 解析封包遺失率
        # 格式: "5 packets transmitted, 5 received, 0% packet loss"
        loss_match = re.search(r'(\d+(?:\.\d+)?)%\s+packet\s+loss', output)
        if loss_match:
            result['packet_loss'] = float(loss_match.group(1))
        
        # 解析 RTT 統計
        # 格式: "rtt min/avg/max/mdev = 0.123/0.456/0.789/0.111 ms"
        rtt_match = re.search(
            r'rtt\s+min/avg/max/mdev\s*=\s*([\d.]+)/([\d.]+)/([\d.]+)/([\d.]+)',
            output
        )
        
        if rtt_match:
            result['min_latency'] = float(rtt_match.group(1))
            result['avg_latency'] = float(rtt_match.group(2))
            result['max_latency'] = float(rtt_match.group(3))
            result['jitter'] = float(rtt_match.group(4))  # mdev 作為抖動
            result['latency'] = result['avg_latency']
        
        # 判斷狀態
        result['status'] = self._determine_status(
            result['latency'],
            result['packet_loss'],
            result['jitter']
        )
        
        return result
    
    def _determine_status(
        self, 
        latency: Optional[float], 
        packet_loss: Optional[float], 
        jitter: Optional[float]
    ) -> str:
        """
        根據測試結果判斷網路品質狀態
        
        Args:
            latency: 延遲（毫秒）
            packet_loss: 封包遺失率（百分比）
            jitter: 抖動（毫秒）
            
        Returns:
            str: 狀態（good, warning, critical, unknown）
        """
        if latency is None and packet_loss is None:
            return 'unknown'
            
        # 100% 封包遺失為嚴重
        if packet_loss is not None and packet_loss >= 100:
            return 'critical'
            
        # 計算各項指標的狀態分數
        scores = []
        
        if latency is not None:
            if latency < self.LATENCY_GOOD:
                scores.append(0)  # good
            elif latency < self.LATENCY_WARNING:
                scores.append(1)  # warning
            else:
                scores.append(2)  # critical
                
        if packet_loss is not None:
            if packet_loss < self.PACKET_LOSS_GOOD:
                scores.append(0)
            elif packet_loss < self.PACKET_LOSS_WARNING:
                scores.append(1)
            else:
                scores.append(2)
                
        if jitter is not None:
            if jitter < self.JITTER_GOOD:
                scores.append(0)
            elif jitter < self.JITTER_WARNING:
                scores.append(1)
            else:
                scores.append(2)
        
        if not scores:
            return 'unknown'
            
        # 取最差的狀態
        max_score = max(scores)
        status_map = {0: 'good', 1: 'warning', 2: 'critical'}
        return status_map.get(max_score, 'unknown')
    
    def collect_server_quality(self, server_id: int) -> Dict:
        """
        收集指定 DHCP Server 下所有 Switch 的網路品質數據
        
        Args:
            server_id: DHCP Server ID
            
        Returns:
            Dict: 收集結果
        """
        from api.models import DHCPServer, NetworkSwitch, NetworkQualityRecord
        
        try:
            server = DHCPServer.objects.get(id=server_id)
        except DHCPServer.DoesNotExist:
            return {'error': f'DHCP Server {server_id} not found'}
        
        # 取得此伺服器關聯的所有 Switch（有設置 IP 地址的）
        switches = NetworkSwitch.objects.filter(
            dhcp_server=server,
            ip_address__isnull=False
        )
        
        results = []
        success_count = 0
        error_count = 0
        
        for switch in switches:
            logger.info(f"測試 Switch {switch.name or switch.remote_id} ({switch.ip_address})")
            
            test_result = self.test_switch_connectivity(switch.ip_address)
            
            # 儲存測試結果到資料庫（適配現有模型欄位）
            is_reachable = test_result.get('success', False)
            latency = test_result.get('latency') or 0
            packet_loss = test_result.get('packet_loss') or (100 if not is_reachable else 0)
            
            record = NetworkQualityRecord.objects.create(
                dhcp_server=server,
                switch=switch,
                latency_ms=latency,
                latency_min_ms=test_result.get('min_latency'),
                latency_max_ms=test_result.get('max_latency'),
                packet_loss=packet_loss,
                jitter_ms=test_result.get('jitter'),
                is_reachable=is_reachable,
                packets_sent=5,  # ping -c 5
                packets_received=int(5 * (100 - packet_loss) / 100) if packet_loss is not None else 5,
                error_message=test_result.get('error', ''),
            )
            
            if is_reachable:
                success_count += 1
            else:
                error_count += 1
            
            results.append({
                'switch_id': switch.id,
                'switch_name': switch.name or switch.remote_id,
                'ip_address': switch.ip_address,
                'record_id': record.id,
                'status': record.quality_status,
                **test_result
            })
        
        return {
            'server_id': server_id,
            'server_name': server.name,
            'total_switches': len(switches),
            'total_records': len(results),
            'success_count': success_count,
            'error_count': error_count,
            'results': results
        }
    
    def get_current_quality(self, server_id: int) -> Dict:
        """
        獲取 DHCP Server 下所有 Switch 的最新網路品質狀態
        
        Args:
            server_id: DHCP Server ID
            
        Returns:
            Dict: 最新的品質數據
        """
        from api.models import DHCPServer, NetworkSwitch, NetworkQualityRecord
        
        try:
            server = DHCPServer.objects.get(id=server_id)
        except DHCPServer.DoesNotExist:
            return {'error': f'DHCP Server {server_id} not found'}
        
        switches = NetworkSwitch.objects.filter(dhcp_server=server)
        results = []
        
        for switch in switches:
            # 取得最新一筆記錄
            latest_record = NetworkQualityRecord.objects.filter(
                dhcp_server=server,
                switch=switch
            ).order_by('-recorded_at').first()
            
            if latest_record:
                results.append({
                    'switch_id': switch.id,
                    'switch_name': switch.name or switch.remote_id,
                    'ip_address': switch.ip_address,
                    'latency': latest_record.latency_ms,
                    'latency_min': latest_record.latency_min_ms,
                    'latency_max': latest_record.latency_max_ms,
                    'packet_loss': latest_record.packet_loss,
                    'jitter': latest_record.jitter_ms,
                    'status': latest_record.quality_status,
                    'is_reachable': latest_record.is_reachable,
                    'timestamp': latest_record.recorded_at.isoformat(),
                })
            else:
                results.append({
                    'switch_id': switch.id,
                    'switch_name': switch.name or switch.remote_id,
                    'ip_address': switch.ip_address,
                    'status': 'no_data',
                    'latency': None,
                    'packet_loss': None,
                    'jitter': None,
                    'timestamp': None
                })
                
        return {
            'server_id': server_id,
            'server_name': server.name,
            'switches': results,
            'total_switches': len(results)
        }
    
    def get_history(
        self, 
        server_id: int,
        time_range: str = '24h',
        switch_ids: Optional[List[int]] = None
    ) -> Dict:
        """
        獲取歷史品質數據
        
        Args:
            server_id: DHCP Server ID
            time_range: 時間範圍 (1h, 6h, 24h, 7d, 30d)
            switch_ids: 過濾的 Switch ID 列表（可選）
            
        Returns:
            Dict: 包含歷史數據和統計資訊
        """
        from api.models import DHCPServer, NetworkQualityRecord
        
        try:
            server = DHCPServer.objects.get(id=server_id)
        except DHCPServer.DoesNotExist:
            return {'error': f'DHCP Server {server_id} not found'}
        
        # 計算時間範圍
        now = timezone.now()
        time_deltas = {
            '1h': timedelta(hours=1),
            '6h': timedelta(hours=6),
            '24h': timedelta(hours=24),
            '7d': timedelta(days=7),
            '30d': timedelta(days=30),
        }
        delta = time_deltas.get(time_range, timedelta(hours=24))
        start_time = now - delta
        
        # 建立查詢
        queryset = NetworkQualityRecord.objects.filter(
            dhcp_server=server,
            recorded_at__gte=start_time
        )
        
        if switch_ids:
            queryset = queryset.filter(switch_id__in=switch_ids)
        
        # 獲取數據並按時間排序
        records = queryset.order_by('recorded_at')
        
        # 計算統計資訊
        stats = queryset.aggregate(
            avg_latency=Avg('latency_ms'),
            min_latency=Min('latency_ms'),
            max_latency=Max('latency_ms'),
            avg_packet_loss=Avg('packet_loss'),
            avg_jitter=Avg('jitter_ms'),
            total_tests=Count('id'),
        )
        
        # 計算可達/不可達的數量
        status_counts = {
            'reachable': queryset.filter(is_reachable=True).count(),
            'unreachable': queryset.filter(is_reachable=False).count(),
            'excellent': 0,
            'good': 0,
            'fair': 0,
            'poor': 0,
            'offline': 0,
        }
        
        # 計算各品質等級數量
        for record in records:
            status = record.quality_status
            if status in status_counts:
                status_counts[status] += 1
        
        # 格式化歷史數據（用於圖表）
        history_data = []
        for record in records:
            history_data.append({
                'timestamp': record.recorded_at.isoformat(),
                'switch_id': record.switch_id,
                'switch_name': record.switch.name if record.switch else 'Unknown',
                'latency': record.latency_ms,
                'latency_min': record.latency_min_ms,
                'latency_max': record.latency_max_ms,
                'packet_loss': record.packet_loss,
                'jitter': record.jitter_ms,
                'status': record.quality_status,
                'is_reachable': record.is_reachable,
            })
        
        return {
            'server_id': server_id,
            'server_name': server.name,
            'time_range': time_range,
            'start_time': start_time.isoformat(),
            'end_time': now.isoformat(),
            'statistics': {
                **stats,
                'status_counts': status_counts,
            },
            'history': history_data,
        }
    
    def cleanup_old_records(self, days: int = 30) -> int:
        """
        清理舊的品質記錄
        
        Args:
            days: 保留天數
            
        Returns:
            int: 刪除的記錄數量
        """
        from api.models import NetworkQualityRecord
        
        cutoff_date = timezone.now() - timedelta(days=days)
        deleted_count, _ = NetworkQualityRecord.objects.filter(
            recorded_at__lt=cutoff_date
        ).delete()
        
        logger.info(f"清理了 {deleted_count} 條舊的網路品質記錄（{days} 天前）")
        return deleted_count
    
    def collect_all_quality(self) -> Dict:
        """
        收集所有 DHCP Server 下所有 Switch 的網路品質數據
        
        Returns:
            Dict: 收集結果總覽
        """
        from api.models import DHCPServer
        
        servers = DHCPServer.objects.all()
        all_results = []
        total_records = 0
        total_success = 0
        total_error = 0
        
        for server in servers:
            result = self.collect_server_quality(server.id)
            if 'error' not in result:
                all_results.append(result)
                total_records += result.get('total_records', 0)
                total_success += result.get('success_count', 0)
                total_error += result.get('error_count', 0)
            else:
                logger.warning(f"跳過 Server {server.id}: {result.get('error')}")
        
        return {
            'total_servers': len(servers),
            'processed_servers': len(all_results),
            'total_records': total_records,
            'total_success': total_success,
            'total_error': total_error,
            'servers': all_results
        }
