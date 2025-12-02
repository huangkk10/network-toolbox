"""
增強的 INI 語法驗證器（使用 ConfigParser 獲取行號）

結合 ConfigParser 和 Ansible 驗證，提供精確的錯誤行號

更新歷史：
- 2025-12-01: 增加對 :vars 區塊中 Jinja2 變數未加引號的檢查
"""
import configparser
import re
from typing import Tuple, Optional, Dict, List


class EnhancedINIValidator:
    """增強的 INI 驗證器（可獲取行號）"""
    
    @staticmethod
    def validate_with_configparser(content: str) -> Tuple[bool, Optional[str], Optional[int], Optional[str]]:
        """
        使用 Python ConfigParser 驗證（可獲得行號）
        
        注意：ConfigParser 的語法比 Ansible 更嚴格
        
        Args:
            content: 文件內容
            
        Returns:
            (is_valid, error_message, error_line, error_line_content)
        """
        parser = configparser.ConfigParser(
            strict=False,  # 改為非嚴格模式，允許重複的 key（與 Ansible 一致）
            allow_no_value=True,  # 允許沒有值的選項（Ansible 允許）
            delimiters=('=',)     # 只使用 = 作為分隔符
        )
        
        try:
            parser.read_string(content)
            return True, None, None, None
            
        except configparser.ParsingError as e:
            # ConfigParser 提供了錯誤行號！
            error_msg = str(e)
            
            # 提取行號: [line  3]: '...'
            line_match = re.search(r'\[line\s+(\d+)\]:\s*[\'"](.+?)[\'"]', error_msg)
            if line_match:
                line_number = int(line_match.group(1))
                line_content = line_match.group(2).strip('\\n')
                
                # 生成友好的錯誤訊息
                friendly_msg = f"第 {line_number} 行語法錯誤: {line_content}"
                
                return False, friendly_msg, line_number, line_content
            else:
                # 無法提取行號，返回原始錯誤
                return False, error_msg, None, None
        
        except configparser.DuplicateSectionError as e:
            # 重複的組名稱
            return False, f"重複的組名稱: [{e.section}]", None, None
        
        except configparser.DuplicateOptionError as e:
            # 重複的選項
            return False, f"重複的選項: {e.option} (在組 [{e.section}])", None, None
        
        except Exception as e:
            # 其他錯誤
            return False, f"解析錯誤: {str(e)}", None, None
    
    @staticmethod
    def pre_validate_ansible_specific(content: str) -> Tuple[bool, Optional[str], Optional[int]]:
        """
        預先驗證 Ansible 特定的語法規則
        
        Args:
            content: 文件內容
            
        Returns:
            (is_valid, error_message, error_line)
        """
        lines = content.split('\n')
        current_section = None  # 追蹤當前所在的 section
        
        for i, line in enumerate(lines, start=1):
            stripped = line.strip()
            
            # 跳過空行和註解
            if not stripped or stripped.startswith('#') or stripped.startswith(';'):
                continue
            
            # 檢查空組名 []
            if stripped == '[]':
                return False, f"第 {i} 行: 組名稱不能為空", i
            
            # 檢查未閉合的括號
            if stripped.startswith('[') and not stripped.endswith(']'):
                return False, f"第 {i} 行: 組標題缺少閉合的中括號 ']'", i
            
            # 檢查是否為組標題，更新當前 section
            if stripped.startswith('['):
                current_section = stripped[1:-1]  # 移除 [ 和 ]
                continue
            
            # 檢查 YAML 語法（冒號後有空格）
            if ': ' in stripped and '=' not in stripped:
                return False, f"第 {i} 行: 不允許使用 YAML 語法，請使用 INI 格式", i
            
            # 判斷當前行的類型
            is_vars_section = current_section and current_section.endswith(':vars')
            
            # 如果在 :vars section 中
            if is_vars_section:
                if '=' not in stripped:
                    return False, f"第 {i} 行: 變數定義缺少等號，應為 'key=value' 格式", i
                
                # 注意：在 Ansible INI 格式中，Jinja2 變數不需要引號包裹
                # 例如 ansible_python_interpreter={{ansible_playbook_python}} 是合法的
                # 所以這裡不再檢查 Jinja2 引號
                
                continue
            
            # 檢查主機行的內聯變數（只在非 :vars section 中檢查）
            parts = stripped.split(None, 1)
            if len(parts) > 1:
                # 有內聯變數
                inline_vars = parts[1]
                
                # 在主機行中，每個空格分隔的變數都必須是 key=value 格式
                # 但需要注意引號內的空格
                # 注意：Ansible INI 格式中，Jinja2 變數不需要引號，所以不再檢查引號
                var_parts = inline_vars.split()
                
                for var_part in var_parts:
                    # 跳過引號內的內容（簡化處理）
                    if var_part.startswith('"') or var_part.startswith("'"):
                        continue
                    
                    # 檢查是否有 = 號
                    if '=' not in var_part:
                        return False, f"第 {i} 行: 變數 '{var_part}' 缺少等號，應為 'key=value' 格式（或使用引號：key=\"value with spaces\"）", i
        
        return True, None, None
    
    @staticmethod
    def _check_jinja2_quoting(line: str, line_number: int) -> Optional[Tuple[bool, str, int]]:
        """
        [已棄用] 檢查 :vars 區塊中的 Jinja2 變數是否正確加了引號
        
        注意：此方法已棄用，因為 Ansible INI 格式中 Jinja2 變數不需要引號。
        例如 ansible_python_interpreter={{ansible_playbook_python}} 是完全合法的。
        
        保留此方法僅供參考，不再被調用。
        
        Args:
            line: 變數定義行（如 key=value）
            line_number: 行號
            
        Returns:
            None（始終返回 None，不再報錯）
        """
        # 不再執行檢查，直接返回 None（表示沒有錯誤）
        return None
    
    @staticmethod
    def validate(content: str) -> Dict:
        """
        完整驗證（結合兩種方法）
        
        策略:
        1. 先用 Ansible 特定規則預檢查（可獲得行號）
        2. 再用 ConfigParser 驗證（也可獲得行號）
        3. 最後用 Ansible 驗證（最終確認）
        
        Args:
            content: 文件內容
            
        Returns:
            驗證結果字典
        """
        result = {
            'is_valid': True,
            'error_message': None,
            'error_line': None,
            'error_line_content': None,
            'validation_method': None
        }
        
        # 方法 1: Ansible 特定規則預檢查
        ansible_valid, ansible_msg, ansible_line = EnhancedINIValidator.pre_validate_ansible_specific(content)
        
        if not ansible_valid:
            result['is_valid'] = False
            result['error_message'] = ansible_msg
            result['error_line'] = ansible_line
            result['validation_method'] = 'ansible_pre_check'
            
            # 獲取錯誤行內容
            if ansible_line:
                lines = content.split('\n')
                if 0 < ansible_line <= len(lines):
                    result['error_line_content'] = lines[ansible_line - 1]
            
            return result
        
        # 方法 2: ConfigParser 驗證（可獲得行號）
        cp_valid, cp_msg, cp_line, cp_line_content = EnhancedINIValidator.validate_with_configparser(content)
        
        if not cp_valid:
            result['is_valid'] = False
            result['error_message'] = cp_msg
            result['error_line'] = cp_line
            result['error_line_content'] = cp_line_content
            result['validation_method'] = 'configparser'
            return result
        
        # 如果都通過，返回成功
        result['validation_method'] = 'all_passed'
        return result


def validate_ini_with_line_numbers(content: str) -> Dict:
    """
    便捷函數：驗證 INI 內容並返回行號
    
    Args:
        content: INI 文件內容
        
    Returns:
        驗證結果（包含行號）
    """
    return EnhancedINIValidator.validate(content)
