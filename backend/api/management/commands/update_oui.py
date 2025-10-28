"""
Django 管理命令：更新 IEEE OUI 資料庫

用法:
    python manage.py update_oui
    
說明:
    從 IEEE 官方來源下載最新的 OUI 資料庫
"""

import os
import urllib.request
import logging
from django.core.management.base import BaseCommand, CommandError
from api.utils.mac_vendor import reload_oui_database, get_vendor_stats, OUI_FILE

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = '從 IEEE 官方來源更新 OUI (MAC 廠商) 資料庫'
    
    # 官方 OUI 資料來源
    OUI_SOURCES = [
        {
            'name': 'IEEE Official (HTTPS)',
            'url': 'https://standards-oui.ieee.org/oui/oui.txt',
            'format': 'ieee',  # 官方格式（預設）
        },
        {
            'name': 'IEEE Official (HTTP)',
            'url': 'http://standards-oui.ieee.org/oui/oui.txt',
            'format': 'ieee',  # 官方格式（備用）
        },
        {
            'name': 'IEEE OUI (Gist Mirror)',
            'url': 'https://gist.githubusercontent.com/gildardoperez/eb73712613587358665916d8fa71f9d7/raw/ieee-oui.txt',
            'format': 'arp-scan',  # OUI<TAB>Vendor
        }
    ]
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--source',
            type=int,
            default=0,
            help='選擇資料來源 (0: Gist Mirror, 1: IEEE Official)',
        )
        
        parser.add_argument(
            '--backup',
            action='store_true',
            help='備份現有的 OUI 資料庫',
        )
    
    def handle(self, *args, **options):
        source_index = options['source']
        do_backup = options['backup']
        
        # 顯示當前資料庫狀態
        self.stdout.write(self.style.WARNING('=== 當前 OUI 資料庫狀態 ==='))
        stats = get_vendor_stats()
        self.stdout.write(f"資料庫檔案: {stats['database_file']}")
        self.stdout.write(f"檔案存在: {'是' if stats['file_exists'] else '否'}")
        if stats['file_exists']:
            self.stdout.write(f"總 OUI 記錄: {stats['total_oui_entries']:,}")
            self.stdout.write(f"唯一製造商: {stats['unique_vendors']:,}")
        
        # 備份現有資料庫
        if do_backup and os.path.exists(OUI_FILE):
            backup_file = f"{OUI_FILE}.backup"
            try:
                import shutil
                shutil.copy2(OUI_FILE, backup_file)
                self.stdout.write(self.style.SUCCESS(f"✓ 已備份到: {backup_file}"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"✗ 備份失敗: {str(e)}"))
        
        # 選擇資料來源
        if source_index < 0 or source_index >= len(self.OUI_SOURCES):
            raise CommandError(f'無效的資料來源索引: {source_index}')
        
        source = self.OUI_SOURCES[source_index]
        
        self.stdout.write(self.style.WARNING(f'\n=== 開始更新 OUI 資料庫 ==='))
        self.stdout.write(f"資料來源: {source['name']}")
        self.stdout.write(f"URL: {source['url']}")
        
        # 下載資料
        try:
            self.stdout.write('正在下載...')
            
            # 設置 User-Agent 避免被封鎖
            req = urllib.request.Request(
                source['url'],
                headers={'User-Agent': 'Network-Toolbox-OUI-Updater/1.0'}
            )
            
            with urllib.request.urlopen(req, timeout=30) as response:
                content = response.read()
            
            # 檢查下載內容
            if not content:
                raise CommandError('下載的資料為空')
            
            lines = content.decode('utf-8', errors='ignore').split('\n')
            self.stdout.write(self.style.SUCCESS(f"✓ 下載成功，共 {len(lines):,} 行"))
            
            # 如果是 arp-scan 格式，直接寫入
            if source['format'] == 'arp-scan':
                with open(OUI_FILE, 'wb') as f:
                    f.write(content)
                
                self.stdout.write(self.style.SUCCESS(f"✓ OUI 資料庫已更新: {OUI_FILE}"))
            
            # 如果是 IEEE 官方格式，需要轉換
            elif source['format'] == 'ieee':
                self._convert_ieee_format(content, OUI_FILE)
                self.stdout.write(self.style.SUCCESS(f"✓ OUI 資料庫已轉換並更新: {OUI_FILE}"))
            
            # 重新載入資料庫
            self.stdout.write('\n正在重新載入資料庫...')
            if reload_oui_database():
                new_stats = get_vendor_stats()
                self.stdout.write(self.style.SUCCESS('✓ 資料庫重新載入成功'))
                self.stdout.write(f"新總 OUI 記錄: {new_stats['total_oui_entries']:,}")
                self.stdout.write(f"新唯一製造商: {new_stats['unique_vendors']:,}")
            else:
                self.stdout.write(self.style.ERROR('✗ 資料庫重新載入失敗'))
            
            self.stdout.write(self.style.SUCCESS('\n=== OUI 資料庫更新完成 ==='))
            
        except urllib.error.URLError as e:
            raise CommandError(f'下載失敗: {str(e)}')
        except Exception as e:
            raise CommandError(f'更新失敗: {str(e)}')
    
    def _convert_ieee_format(self, content, output_file):
        """
        將 IEEE 官方格式轉換為 arp-scan 格式
        
        IEEE 官方格式範例:
        28-6F-B9   (hex)                Nokia Shanghai Bell Co., Ltd.
        286FB9     (base 16)            Nokia Shanghai Bell Co., Ltd.
                                        No.388 Ning Qiao Road...
        
        arp-scan 格式:
        286FB9<TAB>Nokia Shanghai Bell Co., Ltd.
        """
        lines = content.decode('utf-8', errors='ignore').split('\n')
        oui_entries = []
        oui_set = set()  # 用於去重
        
        for line in lines:
            line_stripped = line.strip()
            
            # 查找包含 (hex) 的行
            if '(hex)' in line_stripped:
                # 分割格式: "28-6F-B9   (hex)                Nokia Shanghai Bell Co., Ltd."
                parts = line_stripped.split('(hex)')
                if len(parts) == 2:
                    # 提取 OUI（移除連字符）
                    oui_hex = parts[0].strip().replace('-', '').upper()
                    # 提取廠商名稱
                    vendor = parts[1].strip()
                    
                    # 驗證 OUI 格式（6 個字符）和廠商名稱不為空
                    if len(oui_hex) == 6 and vendor and oui_hex not in oui_set:
                        oui_entries.append(f"{oui_hex}\t{vendor}")
                        oui_set.add(oui_hex)
        
        # 寫入檔案
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("# IEEE OUI Database - Converted from official IEEE format\n")
            f.write(f"# Source: https://standards-oui.ieee.org/oui/oui.txt\n")
            f.write(f"# Updated: {self._get_timestamp()}\n")
            f.write(f"# Total OUIs: {len(oui_entries):,}\n")
            f.write("# Format: OUI<TAB>Vendor\n")
            f.write("#\n")
            for entry in oui_entries:
                f.write(entry + '\n')
        
        self.stdout.write(self.style.SUCCESS(f"✓ 轉換完成，共 {len(oui_entries):,} 筆 OUI 記錄"))
    
    def _get_timestamp(self):
        """獲取當前時間戳"""
        from datetime import datetime
        return datetime.now().strftime('%Y-%m-%d %H:%M:%S')
