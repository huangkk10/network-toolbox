"""
MAC 地址製造商識別工具 - 使用完整 IEEE OUI 資料庫
根據 MAC 地址前綴（OUI）識別設備製造商

資料來源：
- IEEE OUI Database (ieee-oui.txt)
- 支援 23,000+ 製造商

特性：
- 內存緩存：第一次載入後緩存，查詢速度快
- 支援多種 MAC 格式：xx:xx:xx, xx-xx-xx, xxxxxx
- 自動更新：可使用管理命令更新 OUI 資料庫
"""

import os
import logging
from functools import lru_cache

logger = logging.getLogger(__name__)

# OUI 資料庫檔案路徑
OUI_FILE = os.path.join(os.path.dirname(__file__), 'ieee-oui.txt')

# 全局緩存
_OUI_CACHE = None


def _load_oui_database():
    """
    載入 IEEE OUI 資料庫到內存
    
    返回:
        dict: OUI -> 製造商名稱的字典
    """
    global _OUI_CACHE
    
    if _OUI_CACHE is not None:
        return _OUI_CACHE
    
    logger.info('開始載入 IEEE OUI 資料庫...')
    oui_map = {}
    
    try:
        if not os.path.exists(OUI_FILE):
            logger.warning(f'OUI 資料庫檔案不存在: {OUI_FILE}，使用空資料庫')
            _OUI_CACHE = {}
            return _OUI_CACHE
        
        with open(OUI_FILE, 'r', encoding='utf-8', errors='ignore') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                
                # 跳過註釋和空行
                if not line or line.startswith('#'):
                    continue
                
                # 解析格式: OUI<TAB>Vendor
                parts = line.split('\t', 1)
                if len(parts) == 2:
                    oui_hex = parts[0].strip().upper()
                    vendor = parts[1].strip()
                    
                    # 轉換為標準格式 (XX:XX:XX)
                    if len(oui_hex) == 6:
                        formatted_oui = ':'.join([oui_hex[i:i+2] for i in range(0, 6, 2)])
                        oui_map[formatted_oui] = vendor
        
        _OUI_CACHE = oui_map
        logger.info(f'成功載入 {len(oui_map)} 筆 OUI 記錄')
        
    except Exception as e:
        logger.error(f'載入 OUI 資料庫失敗: {str(e)}', exc_info=True)
        _OUI_CACHE = {}
    
    return _OUI_CACHE


def get_vendor_from_mac(mac_address):
    """
    根據 MAC 地址識別製造商（支援完整 IEEE OUI 資料庫）
    
    參數:
        mac_address: MAC 地址字串，支援以下格式：
                     - xx:xx:xx:xx:xx:xx
                     - xx-xx-xx-xx-xx-xx
                     - xxxxxxxxxxxx
    
    返回:
        製造商名稱，如果無法識別則返回 'Unknown'
    
    範例:
        >>> get_vendor_from_mac('00:50:BA:11:22:33')
        'D-Link Corporation'
        
        >>> get_vendor_from_mac('48-21-0B-AA-BB-CC')
        'Intel'
        
        >>> get_vendor_from_mac('AABBCCDDEEFF')
        'Unknown'
    """
    if not mac_address:
        return 'Unknown'
    
    try:
        # 標準化 MAC 地址格式，移除所有分隔符
        mac_clean = mac_address.strip().upper().replace(':', '').replace('-', '').replace('.', '')
        
        # 確保至少有 6 個字符（OUI 部分）
        if len(mac_clean) < 6:
            return 'Unknown'
        
        # 提取前 6 個字符（OUI）並轉換為 XX:XX:XX 格式
        oui_hex = mac_clean[:6]
        oui_formatted = ':'.join([oui_hex[i:i+2] for i in range(0, 6, 2)])
        
        # 載入 OUI 資料庫
        oui_db = _load_oui_database()
        
        # 查詢製造商
        vendor = oui_db.get(oui_formatted, 'Unknown')
        
        return vendor
        
    except Exception as e:
        logger.warning(f'解析 MAC 地址失敗 ({mac_address}): {str(e)}')
        return 'Unknown'


def get_all_vendors():
    """
    獲取所有已知的製造商列表（從 OUI 資料庫）
    
    返回:
        製造商名稱列表（去重並排序）
    """
    oui_db = _load_oui_database()
    vendors = set(oui_db.values())
    return sorted(list(vendors))


def get_vendor_stats():
    """
    獲取 OUI 資料庫統計資訊
    
    返回:
        dict: 包含總 OUI 數、製造商數等統計資訊
    """
    oui_db = _load_oui_database()
    vendors = set(oui_db.values())
    
    return {
        'total_oui_entries': len(oui_db),
        'unique_vendors': len(vendors),
        'database_loaded': _OUI_CACHE is not None,
        'database_file': OUI_FILE,
        'file_exists': os.path.exists(OUI_FILE),
    }


def reload_oui_database():
    """
    重新載入 OUI 資料庫（清除緩存）
    
    用於更新 OUI 資料庫後重新載入
    
    返回:
        bool: 是否成功重新載入
    """
    global _OUI_CACHE
    _OUI_CACHE = None
    
    logger.info('重新載入 OUI 資料庫...')
    oui_db = _load_oui_database()
    
    return len(oui_db) > 0


# 向後兼容性：保留舊的函數簽名
def get_vendor(mac_address):
    """
    [已棄用] 使用 get_vendor_from_mac() 代替
    """
    return get_vendor_from_mac(mac_address)

