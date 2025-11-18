"""
Ansible Inventory Manager API Views

提供 Ansible Inventory 導入、查詢、編輯、驗證和儲存的 API 端點。
"""

import logging
from datetime import datetime
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny  # 開發環境使用，生產環境改為 IsAuthenticated

from api.models import (
    AnsibleInventoryImport,
    AnsibleHostConfig,
    InventoryVersion,
    InventoryEditLog
)
from api.serializers import (
    AnsibleInventoryImportSerializer,
    AnsibleHostConfigSerializer,
    AnsibleHostConfigListSerializer,
    InventoryVersionSerializer,
    InventoryEditLogSerializer
)
from library.services.ansible_inventory_service import AnsibleInventoryService

logger = logging.getLogger(__name__)


class AnsibleInventoryViewSet(viewsets.ModelViewSet):
    """Ansible Inventory 管理 ViewSet"""
    
    queryset = AnsibleInventoryImport.objects.all()
    serializer_class = AnsibleInventoryImportSerializer
    permission_classes = [AllowAny]  # 開發環境
    
    @action(detail=False, methods=['post'], url_path='import')
    def import_inventory(self, request):
        """
        導入 Inventory 文件
        
        POST /api/ansible-inventory/import/
        Body: {
            "nas_path": "\\\\10.250.0.1\\mdt\\Script\\...\\inventory",
            "file_name": "hosts"
        }
        """
        try:
            nas_path = request.data.get('nas_path')
            file_name = request.data.get('file_name', 'hosts')
            
            if not nas_path:
                return Response(
                    {'error': '請提供 NAS 路徑'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            logger.info(f"Importing inventory from {nas_path}/{file_name}")
            
            # 創建導入記錄
            inventory_import = AnsibleInventoryImport.objects.create(
                nas_path=nas_path,
                file_name=file_name,
                status='importing',
                imported_by=request.user if request.user.is_authenticated else None
            )
            
            # 初始化 Service 並從 NAS 導入
            inventory_service = AnsibleInventoryService()
            success, error_msg, parsed_data = inventory_service.import_from_nas(
                nas_path, file_name
            )
            
            if not success:
                inventory_import.status = 'failed'
                inventory_import.syntax_error = error_msg
                inventory_import.save()
                
                logger.error(f"Import failed: {error_msg}")
                return Response(
                    {'error': error_msg},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # 更新導入記錄
            inventory_import.status = 'success'
            inventory_import.syntax_valid = True
            inventory_import.total_hosts = parsed_data['total_hosts']
            inventory_import.total_groups = parsed_data['total_groups']
            inventory_import.save()
            
            # 批次創建 Host 配置
            host_configs = []
            for host_data in parsed_data['hosts']:
                host_config = AnsibleHostConfig(
                    inventory=inventory_import,
                    hostname=host_data['hostname'],
                    groups=host_data['groups'],
                    ansible_host=host_data.get('ansible_host'),
                    ansible_user=host_data.get('ansible_user'),
                    ansible_password=host_data.get('ansible_password'),
                    ansible_port=host_data.get('ansible_port', 22),
                    mac_address=host_data.get('mac_address'),
                    uart_host=host_data.get('uart_host'),
                    other_vars=host_data.get('other_vars', {})
                )
                host_configs.append(host_config)
            
            AnsibleHostConfig.objects.bulk_create(host_configs)
            
            # 記錄操作日誌
            InventoryEditLog.objects.create(
                inventory=inventory_import,
                action='import',
                success=True,
                created_by=request.user if request.user.is_authenticated else None,
                ip_address=request.META.get('REMOTE_ADDR')
            )
            
            logger.info(f"Successfully imported {inventory_import.total_hosts} hosts")
            
            serializer = self.get_serializer(inventory_import)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            logger.error(f"Import error: {e}", exc_info=True)
            return Response(
                {'error': f'導入失敗: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['get'], url_path='hosts')
    def get_hosts(self, request, pk=None):
        """
        獲取 Inventory 的 Host 列表
        
        GET /api/ansible-inventory/{id}/hosts/
        Query params:
            - group: 過濾特定 Group
            - validation_status: 過濾驗證狀態
        """
        try:
            inventory = self.get_object()
            hosts = inventory.hosts.all()
            
            # 過濾
            group_filter = request.query_params.get('group')
            if group_filter:
                hosts = hosts.filter(groups__contains=[group_filter])
            
            status_filter = request.query_params.get('validation_status')
            if status_filter:
                hosts = hosts.filter(validation_status=status_filter)
            
            serializer = AnsibleHostConfigListSerializer(hosts, many=True)
            
            return Response({
                'total': hosts.count(),
                'hosts': serializer.data
            })
            
        except Exception as e:
            logger.error(f"Get hosts error: {e}", exc_info=True)
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['patch'], url_path='hosts/(?P<hostname>[^/.]+)')
    def update_host(self, request, pk=None, hostname=None):
        """
        更新 Host 配置
        
        PATCH /api/ansible-inventory/{id}/hosts/{hostname}/
        Body: {
            "ansible_host": "10.250.53.84",
            "mac_address": "E8:9C:25:A5:2B:BB",
            ...
        }
        """
        try:
            inventory = self.get_object()
            
            # 檢查鎖定狀態
            if inventory.is_locked and inventory.locked_by != request.user:
                # 檢查鎖定是否超時（30分鐘）
                if inventory.locked_at:
                    time_diff = timezone.now() - inventory.locked_at
                    if time_diff.total_seconds() > 1800:  # 30 分鐘
                        # 自動解鎖
                        inventory.is_locked = False
                        inventory.locked_by = None
                        inventory.locked_at = None
                        inventory.save()
                    else:
                        return Response(
                            {
                                'error': f'該 Inventory 正在被 {inventory.locked_by.username} 編輯中',
                                'locked_by': inventory.locked_by.username,
                                'locked_at': inventory.locked_at
                            },
                            status=status.HTTP_423_LOCKED
                        )
            
            # 自動鎖定
            if not inventory.is_locked:
                inventory.is_locked = True
                inventory.locked_by = request.user if request.user.is_authenticated else None
                inventory.locked_at = timezone.now()
                inventory.save()
            
            # 獲取 Host
            try:
                host = inventory.hosts.get(hostname=hostname)
            except AnsibleHostConfig.DoesNotExist:
                return Response(
                    {'error': f'找不到 Host: {hostname}'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # 記錄變更前的值
            old_values = {
                'ansible_host': host.ansible_host,
                'ansible_user': host.ansible_user,
                'ansible_password': host.ansible_password,
                'ansible_port': host.ansible_port,
                'mac_address': host.mac_address,
                'uart_host': host.uart_host,
                'other_vars': host.other_vars
            }
            
            # 更新
            serializer = AnsibleHostConfigSerializer(
                host, data=request.data, partial=True
            )
            
            if serializer.is_valid():
                serializer.save()
                
                # 記錄變更
                changes = {}
                for field, old_value in old_values.items():
                    new_value = getattr(host, field)
                    if old_value != new_value:
                        changes[field] = {
                            'old': old_value,
                            'new': new_value
                        }
                
                if changes:
                    InventoryEditLog.objects.create(
                        inventory=inventory,
                        host_config=host,
                        action='edit',
                        changes=changes,
                        success=True,
                        created_by=request.user if request.user.is_authenticated else None,
                        ip_address=request.META.get('REMOTE_ADDR')
                    )
                
                logger.info(f"Updated host {hostname}: {list(changes.keys())}")
                
                return Response({
                    **serializer.data,
                    'is_modified': True
                })
            else:
                return Response(
                    serializer.errors,
                    status=status.HTTP_400_BAD_REQUEST
                )
            
        except Exception as e:
            logger.error(f"Update host error: {e}", exc_info=True)
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'], url_path='validate')
    def validate_inventory(self, request, pk=None):
        """
        驗證 Inventory 語法
        
        POST /api/ansible-inventory/{id}/validate/
        """
        try:
            inventory = self.get_object()
            
            # 重新驗證語法（未來實現）
            # 這裡可以添加配置檢查功能
            
            logger.info(f"Validated inventory {inventory.id}")
            
            return Response({
                'syntax_valid': inventory.syntax_valid,
                'message': '驗證完成'
            })
            
        except Exception as e:
            logger.error(f"Validation error: {e}", exc_info=True)
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['get'], url_path='versions')
    def get_versions(self, request, pk=None):
        """
        獲取版本歷史
        
        GET /api/ansible-inventory/{id}/versions/
        """
        try:
            inventory = self.get_object()
            versions = inventory.versions.all()
            
            serializer = InventoryVersionSerializer(versions, many=True)
            
            return Response({
                'current_version': inventory.current_version,
                'versions': serializer.data
            })
            
        except Exception as e:
            logger.error(f"Get versions error: {e}", exc_info=True)
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['get'], url_path='logs')
    def get_logs(self, request, pk=None):
        """
        獲取操作日誌
        
        GET /api/ansible-inventory/{id}/logs/
        """
        try:
            inventory = self.get_object()
            logs = inventory.edit_logs.all()[:50]  # 最近 50 條
            
            serializer = InventoryEditLogSerializer(logs, many=True)
            
            return Response({
                'total': inventory.edit_logs.count(),
                'logs': serializer.data
            })
            
        except Exception as e:
            logger.error(f"Get logs error: {e}", exc_info=True)
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['get'], url_path='content')
    def get_content(self, request, pk=None):
        """
        獲取 Inventory 文件內容（新增）
        
        GET /api/ansible-inventory/{id}/content/
        
        Response: {
            "content": "文件內容",
            "file_path": "/mnt/mdt/.../hosts",
            "last_modified": "2025-11-18T14:30:00Z"
        }
        """
        try:
            inventory = self.get_object()
            service = AnsibleInventoryService()
            
            # 獲取文件完整路徑
            linux_path = service.convert_windows_path_to_linux(inventory.nas_path)
            full_path = f"{linux_path}/{inventory.file_name}"
            
            # 讀取文件內容
            success, content, error_message = service.get_file_content(full_path)
            
            if not success:
                return Response(
                    {'error': error_message},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
            
            # 獲取文件修改時間
            import os
            from datetime import datetime
            last_modified = datetime.fromtimestamp(os.path.getmtime(full_path))
            
            logger.info(f"Retrieved content for inventory {pk}: {len(content)} characters")
            
            return Response({
                'content': content,
                'file_path': full_path,
                'last_modified': last_modified.isoformat()
            })
            
        except Exception as e:
            logger.error(f"Get content error: {e}", exc_info=True)
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'], url_path='update-content')
    def update_content(self, request, pk=None):
        """
        更新 Inventory 文件內容（新增）
        
        POST /api/ansible-inventory/{id}/update-content/
        Body: {
            "content": "新的文件內容",
            "change_summary": "修改摘要",
            "validate_only": false  // 可選，僅驗證不保存
        }
        
        Response: {
            "success": true,
            "syntax_valid": true,
            "version": 2,
            "backup_file": "/mnt/mdt/.../hosts.backup.xxx",
            "saved_at": "2025-11-18T14:45:00Z"
        }
        """
        try:
            inventory = self.get_object()
            content = request.data.get('content')
            change_summary = request.data.get('change_summary', '更新 Inventory 配置')
            validate_only = request.data.get('validate_only', False)
            
            if not content:
                return Response(
                    {'error': '缺少 content 參數'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            service = AnsibleInventoryService()
            
            # 如果只是驗證，使用 validate_content_syntax
            if validate_only:
                syntax_valid, syntax_error, parsed_stats = service.validate_content_syntax(content)
                return Response({
                    'success': syntax_valid,
                    'syntax_valid': syntax_valid,
                    'error_message': syntax_error,
                    'parsed_stats': parsed_stats
                })
            
            # 獲取文件完整路徑
            linux_path = service.convert_windows_path_to_linux(inventory.nas_path)
            full_path = f"{linux_path}/{inventory.file_name}"
            
            # 更新文件內容
            success, error_message, backup_path = service.update_file_content(
                full_path,
                content,
                create_backup=True
            )
            
            if not success:
                # 記錄失敗日誌
                InventoryEditLog.objects.create(
                    inventory=inventory,
                    action='save',
                    changes={'error': error_message},
                    success=False,
                    error_message=error_message,
                    created_by=request.user if request.user.is_authenticated else None,
                    ip_address=request.META.get('REMOTE_ADDR')
                )
                
                return Response(
                    {'error': error_message},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # 重新解析 Inventory
            success_parse, _, parsed_data = service.import_from_nas(
                inventory.nas_path,
                inventory.file_name
            )
            
            if success_parse:
                # 更新統計資訊
                inventory.total_hosts = parsed_data['total_hosts']
                inventory.total_groups = parsed_data['total_groups']
                inventory.syntax_valid = True
                inventory.syntax_error = None
            
            # 增加版本號
            inventory.current_version += 1
            inventory.updated_at = timezone.now()
            inventory.save()
            
            # 創建版本記錄
            if backup_path:
                InventoryVersion.objects.create(
                    inventory=inventory,
                    version_number=inventory.current_version,
                    backup_file_path=backup_path,
                    change_summary=change_summary,
                    created_by=request.user if request.user.is_authenticated else None
                )
            
            # 記錄成功日誌
            InventoryEditLog.objects.create(
                inventory=inventory,
                action='save',
                changes={'version': inventory.current_version, 'summary': change_summary},
                success=True,
                created_by=request.user if request.user.is_authenticated else None,
                ip_address=request.META.get('REMOTE_ADDR')
            )
            
            logger.info(f"Successfully updated inventory {pk} to version {inventory.current_version}")
            
            return Response({
                'success': True,
                'syntax_valid': True,
                'version': inventory.current_version,
                'backup_file': backup_path,
                'saved_at': inventory.updated_at.isoformat(),
                'total_hosts': inventory.total_hosts,
                'total_groups': inventory.total_groups
            })
            
        except Exception as e:
            logger.error(f"Update content error: {e}", exc_info=True)
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['post'], url_path='validate-content')
    def validate_content(self, request):
        """
        驗證內容語法（增強版 - 支援精確的錯誤行號定位）
        
        POST /api/ansible-inventory/validate-content/
        Body: {
            "content": "要驗證的內容"
        }
        
        Response (成功): {
            "syntax_valid": true,
            "error_message": null,
            "parsed_hosts": 15,
            "parsed_groups": 6
        }
        
        Response (錯誤): {
            "syntax_valid": false,
            "error_message": "第 3 行: 變數 'ansible_host' 缺少等號...",
            "error_line": 3,
            "error_line_content": "host2 ansible_host 192.168.1.2",
            "validation_method": "ansible_pre_check"
        }
        """
        try:
            content = request.data.get('content')
            
            if not content:
                return Response(
                    {'error': '缺少 content 參數'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            service = AnsibleInventoryService()
            
            # 驗證語法（使用增強版驗證器，可獲得行號）
            syntax_valid, error_message, parsed_stats = service.validate_content_syntax(content)
            
            response_data = {
                'syntax_valid': syntax_valid,
                'error_message': error_message
            }
            
            # 如果驗證通過，返回統計資訊
            if syntax_valid and parsed_stats:
                response_data.update({
                    'parsed_hosts': parsed_stats.get('total_hosts'),
                    'parsed_groups': parsed_stats.get('total_groups')
                })
                logger.info(f"Content validation passed: {parsed_stats.get('total_hosts')} hosts, {parsed_stats.get('total_groups')} groups")
            
            # 如果驗證失敗，返回錯誤定位資訊
            elif not syntax_valid and parsed_stats:
                response_data.update({
                    'error_line': parsed_stats.get('error_line'),
                    'error_line_content': parsed_stats.get('error_line_content'),
                    'validation_method': parsed_stats.get('validation_method')
                })
                logger.warning(f"Content validation failed at line {parsed_stats.get('error_line')}: {error_message}")
            
            return Response(response_data)
            
        except Exception as e:
            logger.error(f"Validate content error: {e}", exc_info=True)
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
