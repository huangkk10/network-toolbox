"""
MAC 地址處理工具模組

提供 MAC 地址格式轉換、驗證等通用功能。
主要用於處理 Windows DHCP ClientId 和標準化 MAC 地址格式。

作者: Network Toolbox Team
日期: 2025-10-30
"""

import re
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def parse_windows_client_id(client_id: str) -> Optional[str]:
    """
    解析 Windows DHCP ClientId 為標準 MAC 地址格式
    
    Windows DHCP ClientId 可能的格式：
    - 01-aa-bb-cc-dd-ee-ff (有類型前綴，第一個字節是類型)
    - aa-bb-cc-dd-ee-ff (無前綴)
    - 01:aa:bb:cc:dd:ee:ff (冒號分隔)
    - aabbccddeeff (無分隔符)
    
    Args:
        client_id: Windows DHCP ClientId 字串
    
    Returns:
        標準 MAC 地址格式 (aa:bb:cc:dd:ee:ff，小寫，冒號分隔)
        如果無法解析則返回 None
    
    Examples:
        >>> parse_windows_client_id('01-aa-bb-cc-dd-ee-ff')
        'aa:bb:cc:dd:ee:ff'
        
        >>> parse_windows_client_id('aa-bb-cc-dd-ee-ff')
        'aa:bb:cc:dd:ee:ff'
        
        >>> parse_windows_client_id('AABBCCDDEEFF')
        'aa:bb:cc:dd:ee:ff'
    """
    if not client_id:
        return None
    
    try:
        # 移除所有分隔符，統一處理
        clean_id = client_id.strip().replace('-', '').replace(':', '').replace('.', '').upper()
        
        # 判斷長度
        if len(clean_id) == 14:
            # 格式：01AABBCCDDEEFF (7 bytes，包含類型前綴)
            # 跳過前 2 個字符（第一個字節）
            mac_hex = clean_id[2:]
        elif len(clean_id) == 12:
            # 格式：AABBCCDDEEFF (6 bytes，標準 MAC)
            mac_hex = clean_id
        else:
            logger.warning(f'無效的 ClientId 長度: {client_id} (長度: {len(clean_id)})')
            return None
        
        # 轉換為標準格式 (小寫，冒號分隔)
        mac_address = ':'.join([mac_hex[i:i+2].lower() for i in range(0, 12, 2)])
        
        # 驗證格式
        if validate_mac_address(mac_address):
            return mac_address
        else:
            logger.warning(f'解析後的 MAC 地址格式無效: {mac_address}')
            return None
    
    except Exception as e:
        logger.error(f'MAC 地址解析失敗 ({client_id}): {str(e)}')
        return None


def normalize_mac_address(mac: str) -> Optional[str]:
    """
    標準化 MAC 地址格式
    
    接受多種格式的 MAC 地址，統一轉換為標準格式：
    - aa:bb:cc:dd:ee:ff (小寫，冒號分隔)
    
    支援的輸入格式：
    - aa:bb:cc:dd:ee:ff
    - aa-bb-cc-dd-ee-ff
    - aa.bb.cc.dd.ee.ff
    - aabbccddeeff
    - AABBCCDDEEFF
    
    Args:
        mac: MAC 地址字串
    
    Returns:
        標準 MAC 地址格式 (aa:bb:cc:dd:ee:ff)
        如果無法解析則返回 None
    
    Examples:
        >>> normalize_mac_address('AA-BB-CC-DD-EE-FF')
        'aa:bb:cc:dd:ee:ff'
        
        >>> normalize_mac_address('aabbccddeeff')
        'aa:bb:cc:dd:ee:ff'
        
        >>> normalize_mac_address('aa.bb.cc.dd.ee.ff')
        'aa:bb:cc:dd:ee:ff'
    """
    if not mac:
        return None
    
    try:
        # 移除所有分隔符
        clean_mac = mac.strip().replace(':', '').replace('-', '').replace('.', '').upper()
        
        # 確保長度正確
        if len(clean_mac) != 12:
            logger.warning(f'無效的 MAC 地址長度: {mac} (長度: {len(clean_mac)})')
            return None
        
        # 轉換為標準格式
        mac_address = ':'.join([clean_mac[i:i+2].lower() for i in range(0, 12, 2)])
        
        # 驗證格式
        if validate_mac_address(mac_address):
            return mac_address
        else:
            return None
    
    except Exception as e:
        logger.error(f'MAC 地址標準化失敗 ({mac}): {str(e)}')
        return None


def validate_mac_address(mac: str) -> bool:
    """
    驗證 MAC 地址格式是否正確
    
    接受標準格式：aa:bb:cc:dd:ee:ff (小寫，冒號分隔)
    
    Args:
        mac: MAC 地址字串
    
    Returns:
        bool: True 表示格式正確，False 表示格式錯誤
    
    Examples:
        >>> validate_mac_address('aa:bb:cc:dd:ee:ff')
        True
        
        >>> validate_mac_address('aa-bb-cc-dd-ee-ff')
        False  # 錯誤的分隔符
        
        >>> validate_mac_address('invalid')
        False
    """
    if not mac:
        return False
    
    # 正則表達式：^([0-9a-f]{2}:){5}[0-9a-f]{2}$
    pattern = r'^([0-9a-f]{2}:){5}[0-9a-f]{2}$'
    
    return bool(re.match(pattern, mac))


def get_mac_oui(mac: str) -> Optional[str]:
    """
    提取 MAC 地址的 OUI（前 3 個字節）
    
    OUI (Organizationally Unique Identifier) 是 IEEE 分配給製造商的唯一識別碼。
    
    Args:
        mac: MAC 地址字串（任何格式）
    
    Returns:
        OUI 字串 (AA:BB:CC 格式)，如果無法解析則返回 None
    
    Examples:
        >>> get_mac_oui('aa:bb:cc:dd:ee:ff')
        'AA:BB:CC'
        
        >>> get_mac_oui('aa-bb-cc-dd-ee-ff')
        'AA:BB:CC'
    """
    normalized = normalize_mac_address(mac)
    if not normalized:
        return None
    
    # 提取前 3 個字節（前 8 個字符，包含 2 個冒號）
    oui = normalized[:8].upper()
    return oui


def is_multicast_mac(mac: str) -> bool:
    """
    判斷 MAC 地址是否為多播（Multicast）地址
    
    多播 MAC 地址的第一個字節的最低位為 1。
    
    Args:
        mac: MAC 地址字串
    
    Returns:
        bool: True 表示是多播地址
    
    Examples:
        >>> is_multicast_mac('01:00:5e:00:00:01')
        True
        
        >>> is_multicast_mac('00:11:22:33:44:55')
        False
    """
    normalized = normalize_mac_address(mac)
    if not normalized:
        return False
    
    # 提取第一個字節
    first_byte = int(normalized[:2], 16)
    
    # 檢查最低位（LSB）
    return (first_byte & 0x01) == 1


def is_locally_administered_mac(mac: str) -> bool:
    """
    判斷 MAC 地址是否為本地管理（Locally Administered）地址
    
    本地管理 MAC 地址的第一個字節的第二低位為 1。
    常見於虛擬機和虛擬網卡。
    
    Args:
        mac: MAC 地址字串
    
    Returns:
        bool: True 表示是本地管理地址
    
    Examples:
        >>> is_locally_administered_mac('02:00:00:00:00:01')
        True
        
        >>> is_locally_administered_mac('00:11:22:33:44:55')
        False
    """
    normalized = normalize_mac_address(mac)
    if not normalized:
        return False
    
    # 提取第一個字節
    first_byte = int(normalized[:2], 16)
    
    # 檢查第二低位
    return (first_byte & 0x02) == 2


def format_mac_for_display(mac: str, separator: str = ':', uppercase: bool = False) -> Optional[str]:
    """
    格式化 MAC 地址用於顯示
    
    Args:
        mac: MAC 地址字串
        separator: 分隔符（預設 ':'）
        uppercase: 是否使用大寫（預設 False）
    
    Returns:
        格式化後的 MAC 地址，如果無法解析則返回 None
    
    Examples:
        >>> format_mac_for_display('aabbccddeeff', separator='-', uppercase=True)
        'AA-BB-CC-DD-EE-FF'
        
        >>> format_mac_for_display('aa:bb:cc:dd:ee:ff', separator='.', uppercase=False)
        'aa.bb.cc.dd.ee.ff'
    """
    normalized = normalize_mac_address(mac)
    if not normalized:
        return None
    
    # 替換分隔符
    formatted = normalized.replace(':', separator)
    
    # 轉換大小寫
    if uppercase:
        formatted = formatted.upper()
    
    return formatted


# 向後兼容性：保留舊的函數名稱
parse_client_id = parse_windows_client_id  # 別名
