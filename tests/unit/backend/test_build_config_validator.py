"""
BuildConfigValidator Service 單元測試

測試範圍：
1. IP 格式驗證
2. MAC 格式驗證（Linux 格式）
3. DHCP 租約查詢（智能過濾）
4. 配置值提取
5. 總體狀態計算
"""

import unittest
from unittest.mock import Mock, patch
from datetime import timedelta
from django.test import TestCase
from django.utils import timezone

from library.services.build_config_validator import BuildConfigValidator
from api.models import JenkinsServer, JenkinsJob, JenkinsBuild, DHCPServer, DHCPLease


class BuildConfigValidatorTestCase(TestCase):
    """BuildConfigValidator 測試類"""
    
    def setUp(self):
        """測試初始化"""
        # 創建測試用 Jenkins Server
        self.server = JenkinsServer.objects.create(
            name='Test Server',
            url='http://test-jenkins.com',
            username='admin',
            api_token='test-token'
        )
        
        # 創建測試用 Jenkins Job
        self.job = JenkinsJob.objects.create(
            server=self.server,
            name='Test Job',
            url='http://test-jenkins.com/job/test'
        )
        
        # 創建測試用 Jenkins Build（包含配置參數）
        self.build = JenkinsBuild.objects.create(
            job=self.job,
            build_number=1,
            result='SUCCESS',
            parameters={
                'host_ip': '192.168.1.100',
                'host_mac': '30:C5:99:55:C9:D3',
                'uart_ip': '192.168.1.101'
            }
        )
        
        # 創建測試用 DHCP Server（online）
        self.dhcp_server_online = DHCPServer.objects.create(
            name='DHCP Server 1',
            ip_address='192.168.1.1',
            status='online'
        )
        
        # 創建測試用 DHCP Server（offline）
        self.dhcp_server_offline = DHCPServer.objects.create(
            name='DHCP Server 2',
            ip_address='192.168.1.2',
            status='offline'
        )
        
        # 創建測試用 DHCP Lease（有效租約，online server）
        self.lease_host_ip = DHCPLease.objects.create(
            server=self.dhcp_server_online,
            ip_address='192.168.1.100',
            mac_address='30:c5:99:55:c9:d3',
            hostname='test-host',
            lease_end=timezone.now() + timedelta(days=7),
            is_active=True
        )
        
        # 創建測試用 DHCP Lease（即將過期，online server）
        self.lease_uart_ip_expiring = DHCPLease.objects.create(
            server=self.dhcp_server_online,
            ip_address='192.168.1.101',
            mac_address='40:c5:99:55:c9:d4',
            hostname='test-uart',
            lease_end=timezone.now() + timedelta(hours=12),  # 12 小時後過期
            is_active=True
        )
    
    def test_is_valid_ip(self):
        """測試 IP 格式驗證"""
        validator = BuildConfigValidator(self.build)
        
        # 有效 IP
        self.assertTrue(validator._is_valid_ip('192.168.1.100'))
        self.assertTrue(validator._is_valid_ip('10.0.0.1'))
        self.assertTrue(validator._is_valid_ip('172.16.0.1'))
        
        # 無效 IP
        self.assertFalse(validator._is_valid_ip('256.1.1.1'))
        self.assertFalse(validator._is_valid_ip('abc.def.ghi.jkl'))
        self.assertFalse(validator._is_valid_ip('192.168.1'))
    
    def test_is_linux_mac_format(self):
        """測試 Linux MAC 格式驗證"""
        validator = BuildConfigValidator(self.build)
        
        # 有效 Linux MAC 格式
        self.assertTrue(validator._is_linux_mac_format('30:C5:99:55:C9:D3'))
        self.assertTrue(validator._is_linux_mac_format('00:11:22:33:44:55'))
        self.assertTrue(validator._is_linux_mac_format('aa:bb:cc:dd:ee:ff'))
        
        # 無效格式
        self.assertFalse(validator._is_linux_mac_format('30-C5-99-55-C9-D3'))  # Windows 格式
        self.assertFalse(validator._is_linux_mac_format('30C5.9955.C9D3'))     # Cisco 格式
        self.assertFalse(validator._is_linux_mac_format('30:C5:99:55:C9'))     # 不完整
        self.assertFalse(validator._is_linux_mac_format('GG:HH:II:JJ:KK:LL'))  # 非十六進制
    
    def test_extract_config_value_from_parameters(self):
        """測試從 parameters 提取配置值"""
        validator = BuildConfigValidator(self.build)
        
        # 從 parameters 提取
        self.assertEqual(validator._extract_config_value('host_ip'), '192.168.1.100')
        self.assertEqual(validator._extract_config_value('host_mac'), '30:C5:99:55:C9:D3')
        self.assertEqual(validator._extract_config_value('uart_ip'), '192.168.1.101')
        
        # 不存在的 key
        self.assertIsNone(validator._extract_config_value('non_existent_key'))
    
    def test_extract_config_value_from_ansible_config(self):
        """測試從 ansible_config 提取配置值"""
        build = JenkinsBuild.objects.create(
            job=self.job,
            build_number=2,
            result='SUCCESS',
            ansible_config={
                'host_ip': '192.168.2.100',
                'extra_vars': {
                    'uart_ip': '192.168.2.101'
                }
            }
        )
        
        validator = BuildConfigValidator(build)
        
        # 從 ansible_config 提取
        self.assertEqual(validator._extract_config_value('host_ip'), '192.168.2.100')
        
        # 從 ansible_config.extra_vars 提取
        self.assertEqual(validator._extract_config_value('uart_ip'), '192.168.2.101')
    
    def test_query_dhcp_lease_by_ip_online_server(self):
        """測試按 IP 查詢 DHCP 租約（只查詢 online server）"""
        validator = BuildConfigValidator(self.build)
        
        # 查詢存在的租約（online server）
        lease = validator._query_dhcp_lease_by_ip('192.168.1.100')
        self.assertIsNotNone(lease)
        self.assertEqual(lease.ip_address, '192.168.1.100')
        self.assertEqual(lease.server, self.dhcp_server_online)
    
    def test_query_dhcp_lease_by_ip_specific_server(self):
        """測試按 IP 查詢 DHCP 租約（指定 server_id）"""
        # 創建另一個 online server 的租約
        dhcp_server_3 = DHCPServer.objects.create(
            name='DHCP Server 3',
            ip_address='192.168.1.3',
            status='online'
        )
        lease_3 = DHCPLease.objects.create(
            server=dhcp_server_3,
            ip_address='192.168.1.200',
            mac_address='50:c5:99:55:c9:d5',
            hostname='test-host-3',
            lease_end=timezone.now() + timedelta(days=7),
            is_active=True
        )
        
        # 指定查詢 dhcp_server_3
        validator = BuildConfigValidator(self.build, dhcp_server_id=dhcp_server_3.id)
        lease = validator._query_dhcp_lease_by_ip('192.168.1.200')
        
        self.assertIsNotNone(lease)
        self.assertEqual(lease.server, dhcp_server_3)
    
    def test_query_dhcp_lease_by_mac(self):
        """測試按 MAC 查詢 DHCP 租約"""
        validator = BuildConfigValidator(self.build)
        
        # 查詢存在的租約（大小寫不敏感）
        lease = validator._query_dhcp_lease_by_mac('30:c5:99:55:c9:d3')
        self.assertIsNotNone(lease)
        self.assertEqual(lease.mac_address, '30:c5:99:55:c9:d3')
        
        lease_upper = validator._query_dhcp_lease_by_mac('30:C5:99:55:C9:D3')
        self.assertIsNotNone(lease_upper)
        self.assertEqual(lease_upper, lease)
    
    def test_check_host_ip_passed(self):
        """測試 Host IP 檢查（通過）"""
        validator = BuildConfigValidator(self.build)
        validator._check_host_ip()
        
        results = validator.results
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['item'], 'host_ip')
        self.assertEqual(results[0]['status'], 'passed')
        self.assertEqual(results[0]['value'], '192.168.1.100')
    
    def test_check_host_ip_expiring_warning(self):
        """測試 Host IP 檢查（租約即將過期 - 警告）"""
        # 修改租約為即將過期
        self.lease_host_ip.lease_end = timezone.now() + timedelta(hours=12)
        self.lease_host_ip.save()
        
        validator = BuildConfigValidator(self.build)
        validator._check_host_ip()
        
        results = validator.results
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['status'], 'warning')
        self.assertIn('即將在', results[0]['message'])
    
    def test_check_host_ip_not_found(self):
        """測試 Host IP 檢查（租約不存在 - 失敗）"""
        # 創建一個沒有租約的 Build
        build_no_lease = JenkinsBuild.objects.create(
            job=self.job,
            build_number=10,
            result='SUCCESS',
            parameters={
                'host_ip': '192.168.99.99'  # 不存在的 IP
            }
        )
        
        validator = BuildConfigValidator(build_no_lease)
        validator._check_host_ip()
        
        results = validator.results
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['status'], 'failed')
        self.assertIn('未在任何 DHCP Server 中找到', results[0]['message'])
    
    def test_check_host_mac_passed(self):
        """測試 Host MAC 檢查（通過）"""
        validator = BuildConfigValidator(self.build)
        validator._check_host_mac()
        
        results = validator.results
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['item'], 'host_mac')
        self.assertEqual(results[0]['status'], 'passed')
    
    def test_check_host_mac_format_error_windows(self):
        """測試 Host MAC 檢查（Windows 格式 - 失敗）"""
        build_windows_mac = JenkinsBuild.objects.create(
            job=self.job,
            build_number=20,
            result='SUCCESS',
            parameters={
                'host_mac': '30-C5-99-55-C9-D3'  # Windows 格式
            }
        )
        
        validator = BuildConfigValidator(build_windows_mac)
        validator._check_host_mac()
        
        results = validator.results
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['status'], 'failed')
        self.assertIn('必須使用冒號分隔', results[0]['message'])
        self.assertIn('30:C5:99:55:C9:D3', results[0]['details']['expected_format'])
    
    def test_check_uart_ip_warning_expiring(self):
        """測試 UART IP 檢查（即將過期 - 警告）"""
        validator = BuildConfigValidator(self.build)
        validator._check_uart_ip()
        
        results = validator.results
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['item'], 'uart_ip')
        self.assertEqual(results[0]['status'], 'warning')
        self.assertIn('即將在', results[0]['message'])
    
    def test_calculate_overall_status_all_passed(self):
        """測試總體狀態計算（全部通過）"""
        validator = BuildConfigValidator(self.build)
        validator.results = [
            {'status': 'passed'},
            {'status': 'passed'},
            {'status': 'passed'},
        ]
        
        overall_status = validator._calculate_overall_status()
        self.assertEqual(overall_status, 'passed')
    
    def test_calculate_overall_status_has_warning(self):
        """測試總體狀態計算（有警告）"""
        validator = BuildConfigValidator(self.build)
        validator.results = [
            {'status': 'passed'},
            {'status': 'warning'},
            {'status': 'passed'},
        ]
        
        overall_status = validator._calculate_overall_status()
        self.assertEqual(overall_status, 'warning')
    
    def test_calculate_overall_status_has_failed(self):
        """測試總體狀態計算（有失敗）"""
        validator = BuildConfigValidator(self.build)
        validator.results = [
            {'status': 'passed'},
            {'status': 'warning'},
            {'status': 'failed'},
        ]
        
        overall_status = validator._calculate_overall_status()
        self.assertEqual(overall_status, 'failed')
    
    def test_validate_all_integration(self):
        """測試完整的 validate_all 流程"""
        validator = BuildConfigValidator(self.build)
        result = validator.validate_all()
        
        # 檢查返回結構
        self.assertIn('build_id', result)
        self.assertIn('job_name', result)
        self.assertIn('build_number', result)
        self.assertIn('overall_status', result)
        self.assertIn('check_results', result)
        self.assertIn('checked_at', result)
        
        # 檢查結果數量（3 項檢查）
        self.assertEqual(len(result['check_results']), 3)
        
        # 檢查項目名稱
        items = [r['item'] for r in result['check_results']]
        self.assertIn('host_ip', items)
        self.assertIn('host_mac', items)
        self.assertIn('uart_ip', items)
    
    def tearDown(self):
        """測試清理"""
        JenkinsBuild.objects.all().delete()
        JenkinsJob.objects.all().delete()
        JenkinsServer.objects.all().delete()
        DHCPLease.objects.all().delete()
        DHCPServer.objects.all().delete()


if __name__ == '__main__':
    unittest.main()
