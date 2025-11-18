"""
Ansible Inventory 錯誤定位工具

用於解析 Ansible 錯誤訊息並在內容中定位錯誤位置
"""
import re
from typing import Optional, Dict, List


class InventoryErrorLocator:
    """Inventory 錯誤定位器"""
    
    @staticmethod
    def extract_error_keyword(error_message: str) -> Optional[str]:
        """
        從 Ansible 錯誤訊息中提取關鍵錯誤文字
        
        Args:
            error_message: Ansible 錯誤訊息
            
        Returns:
            錯誤關鍵字，如果無法提取則返回 None
            
        Examples:
            "Expected key=value host variable assignment, got: FFF"
            -> "FFF"
            
            "Invalid section entry: '[]'"
            -> "[]"
        """
        # 模式 1: "got: XXX"
        match = re.search(r'got:\s*(.+?)(?:\n|$)', error_message)
        if match:
            keyword = match.group(1).strip()
            # 移除引號
            keyword = keyword.strip('\'"')
            return keyword
        
        # 模式 2: "Invalid section entry: 'XXX'"
        match = re.search(r"Invalid section entry:\s*['\"](.+?)['\"]", error_message)
        if match:
            return match.group(1)
        
        # 模式 3: 提取括號內的內容
        match = re.search(r'\[([^\]]*)\]', error_message)
        if match:
            return f"[{match.group(1)}]"
        
        return None
    
    @staticmethod
    def locate_error_line(content: str, error_keyword: str) -> Optional[int]:
        """
        在內容中定位包含錯誤關鍵字的行號
        
        Args:
            content: 文件內容
            error_keyword: 錯誤關鍵字
            
        Returns:
            行號（1-based），如果找不到則返回 None
        """
        if not error_keyword:
            return None
        
        lines = content.split('\n')
        for i, line in enumerate(lines, start=1):
            if error_keyword in line:
                return i
        
        return None
    
    @staticmethod
    def analyze_error(content: str, error_message: str) -> Dict:
        """
        分析錯誤並返回詳細資訊
        
        Args:
            content: 文件內容
            error_message: Ansible 錯誤訊息
            
        Returns:
            錯誤分析結果字典，包含：
            - error_keyword: 錯誤關鍵字
            - line_number: 錯誤行號（如果找到）
            - line_content: 錯誤行內容（如果找到）
            - suggestions: 修正建議
        """
        result = {
            'error_keyword': None,
            'line_number': None,
            'line_content': None,
            'suggestions': []
        }
        
        # 提取錯誤關鍵字
        error_keyword = InventoryErrorLocator.extract_error_keyword(error_message)
        result['error_keyword'] = error_keyword
        
        if not error_keyword:
            return result
        
        # 定位錯誤行
        line_number = InventoryErrorLocator.locate_error_line(content, error_keyword)
        result['line_number'] = line_number
        
        if line_number:
            lines = content.split('\n')
            if 0 < line_number <= len(lines):
                result['line_content'] = lines[line_number - 1]
        
        # 生成修正建議
        result['suggestions'] = InventoryErrorLocator._generate_suggestions(
            error_message, 
            error_keyword, 
            result['line_content']
        )
        
        return result
    
    @staticmethod
    def _generate_suggestions(
        error_message: str, 
        error_keyword: Optional[str],
        line_content: Optional[str]
    ) -> List[str]:
        """
        根據錯誤類型生成修正建議
        
        Args:
            error_message: 錯誤訊息
            error_keyword: 錯誤關鍵字
            line_content: 錯誤行內容
            
        Returns:
            建議列表
        """
        suggestions = []
        error_lower = error_message.lower()
        
        # 根據不同的錯誤類型給出建議
        if 'expected key=value' in error_lower:
            suggestions.append("變數格式錯誤，應為 'key=value' 格式")
            if error_keyword and '=' not in error_keyword:
                suggestions.append(f"'{error_keyword}' 缺少等號，請確認變數格式")
        
        elif 'invalid section' in error_lower or 'empty' in error_lower:
            suggestions.append("組名稱不能為空")
            suggestions.append("請使用格式：[group_name]")
        
        elif 'not enough values to unpack' in error_lower:
            suggestions.append("可能是缺少閉合的中括號 ']'")
            suggestions.append("請檢查組標題是否完整：[group_name]")
        
        elif 'unable to parse' in error_lower:
            suggestions.append("文件格式無法識別")
            suggestions.append("請確認使用 INI 格式，而非 YAML 格式")
        
        # 如果有具體的行內容，提供更詳細的建議
        if line_content:
            if line_content.strip().startswith('[') and not line_content.strip().endswith(']'):
                suggestions.append(f"建議修正為：{line_content.strip()}]")
            
            # 檢查是否有空格分隔的變數但缺少等號
            if ' ' in line_content and '=' not in line_content.split()[1:]:
                parts = line_content.split()
                if len(parts) >= 3:
                    suggestions.append(f"可能想輸入：{parts[0]} {parts[1]}={parts[2]}")
        
        return suggestions


def locate_error_in_content(content: str, error_message: str) -> Dict:
    """
    便捷函數：定位內容中的錯誤
    
    Args:
        content: 文件內容
        error_message: 錯誤訊息
        
    Returns:
        錯誤定位結果
    """
    return InventoryErrorLocator.analyze_error(content, error_message)
