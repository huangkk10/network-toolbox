"""
嚴格的 INI 格式驗證器
用於在 Ansible inventory 驗證前進行語法檢查
"""
import re
from typing import List, Tuple, Optional


class INIValidationError(Exception):
    """INI 驗證錯誤"""
    def __init__(self, message: str, line_number: int = None, line_content: str = None):
        self.message = message
        self.line_number = line_number
        self.line_content = line_content
        
        error_msg = message
        if line_number is not None:
            error_msg = f"第 {line_number} 行: {message}"
        if line_content:
            error_msg += f"\n內容: {line_content}"
        
        super().__init__(error_msg)


class INIValidator:
    """嚴格的 INI 語法驗證器"""
    
    # 有效的組名稱格式 (允許字母、數字、底線、連字符、點)
    GROUP_NAME_PATTERN = re.compile(r'^[a-zA-Z0-9_\-\.]+$')
    
    # 有效的主機名稱格式
    HOST_NAME_PATTERN = re.compile(r'^[a-zA-Z0-9_\-\.]+$')
    
    # 變數格式 (key=value)
    VARIABLE_PATTERN = re.compile(r'^([a-zA-Z_][a-zA-Z0-9_]*)=(.*)$')
    
    # 特殊的組類型
    SPECIAL_GROUP_TYPES = [':children', ':vars']
    
    def __init__(self, content: str):
        """
        初始化驗證器
        
        Args:
            content: INI 文件內容
        """
        self.content = content
        self.lines = content.split('\n')
        self.errors: List[INIValidationError] = []
        self.current_group: Optional[str] = None
        self.group_names: set = set()
        self.bracket_stack: List[Tuple[int, str]] = []  # 追蹤未閉合的括號
    
    def validate(self) -> Tuple[bool, List[INIValidationError]]:
        """
        執行完整驗證
        
        Returns:
            (是否有效, 錯誤列表)
        """
        self.errors.clear()
        self.current_group = None
        self.group_names.clear()
        self.bracket_stack.clear()
        
        # 逐行驗證
        for line_num, line in enumerate(self.lines, start=1):
            try:
                self._validate_line(line, line_num)
            except INIValidationError as e:
                self.errors.append(e)
        
        # 檢查是否有未閉合的括號
        if self.bracket_stack:
            for line_num, line_content in self.bracket_stack:
                self.errors.append(INIValidationError(
                    "未閉合的中括號",
                    line_number=line_num,
                    line_content=line_content
                ))
        
        return len(self.errors) == 0, self.errors
    
    def _validate_line(self, line: str, line_num: int):
        """驗證單行"""
        # 移除行尾空白
        line = line.rstrip()
        
        # 空行 - 允許
        if not line.strip():
            return
        
        # 註解 - 允許
        if line.strip().startswith('#') or line.strip().startswith(';'):
            return
        
        # 檢查是否為組標題 [group_name]
        if line.strip().startswith('['):
            self._validate_group_header(line, line_num)
            return
        
        # 檢查是否包含 YAML 語法 (冒號開頭且不是主機行)
        if line.strip().startswith('-') or (': ' in line and '=' not in line):
            raise INIValidationError(
                "不允許使用 YAML 語法，請使用 INI 格式",
                line_number=line_num,
                line_content=line.strip()
            )
        
        # 如果包含 = 號，驗證為變數定義
        if '=' in line:
            self._validate_variable(line, line_num)
            return
        
        # 否則應該是主機名稱
        self._validate_host(line, line_num)
    
    def _validate_group_header(self, line: str, line_num: int):
        """驗證組標題"""
        line = line.strip()
        
        # 檢查是否包含閉合括號
        if ']' not in line:
            # 沒有閉合括號
            self.bracket_stack.append((line_num, line))
            raise INIValidationError(
                "組標題缺少閉合的中括號 ']'",
                line_number=line_num,
                line_content=line
            )
        
        # 找到 ] 的位置
        bracket_end = line.index(']')
        
        # 檢查 ] 後面是否有多餘的內容
        after_bracket = line[bracket_end + 1:].strip()
        if after_bracket:
            # ] 後面有內容
            if after_bracket.startswith(';') or after_bracket.startswith('#'):
                # 這是註解，在 Ansible INI 中組標題行不允許行尾註解
                raise INIValidationError(
                    "組標題後不允許添加註解，請將註解移到單獨一行",
                    line_number=line_num,
                    line_content=line
                )
            else:
                # 其他多餘內容
                raise INIValidationError(
                    f"組標題 '{line[:bracket_end+1]}' 後有多餘的內容 '{after_bracket}'",
                    line_number=line_num,
                    line_content=line
                )
        
        # 提取組名稱
        group_content = line[1:bracket_end].strip()
        
        # 檢查組名稱是否為空
        if not group_content:
            raise INIValidationError(
                "組名稱不能為空",
                line_number=line_num,
                line_content=line
            )
        
        # 檢查是否為特殊組類型
        is_special = False
        base_group_name = group_content
        for special_type in self.SPECIAL_GROUP_TYPES:
            if group_content.endswith(special_type):
                is_special = True
                base_group_name = group_content[:-len(special_type)]
                break
        
        # 驗證組名稱格式
        if not self.GROUP_NAME_PATTERN.match(base_group_name):
            raise INIValidationError(
                f"組名稱 '{base_group_name}' 格式不正確，只能包含字母、數字、底線、連字符和點",
                line_number=line_num,
                line_content=line
            )
        
        # 記錄當前組
        self.current_group = group_content
        self.group_names.add(base_group_name)
    
    def _validate_variable(self, line: str, line_num: int):
        """驗證變數定義（僅在 [group:vars] 下）"""
        line = line.strip()
        
        # 檢查是否為純變數行（不是主機加內聯變數）
        # 如果行首有空格分隔的多個部分，可能是主機行
        parts = line.split(None, 1)
        if len(parts) > 1:
            # 這是主機行加內聯變數，交由 _validate_host 處理
            self._validate_host(line, line_num)
            return
        
        # 純變數行（在 :vars 組下）
        # 使用正則匹配變數格式
        match = self.VARIABLE_PATTERN.match(line)
        if not match:
            raise INIValidationError(
                "變數格式不正確，應為 'key=value' 格式",
                line_number=line_num,
                line_content=line
            )
        
        key, value = match.groups()
        
        # 驗證變數名稱格式 (必須以字母或底線開頭)
        if not key[0].isalpha() and key[0] != '_':
            raise INIValidationError(
                f"變數名稱 '{key}' 必須以字母或底線開頭",
                line_number=line_num,
                line_content=line
            )
    
    def _validate_host(self, line: str, line_num: int):
        """驗證主機定義"""
        import shlex
        
        line = line.strip()
        
        # 主機行可能包含內聯變數，例如: host1 ansible_host=192.168.1.1
        parts = line.split(None, 1)  # 最多分割一次
        host_name = parts[0]
        
        # 驗證主機名稱格式
        if not self.HOST_NAME_PATTERN.match(host_name):
            raise INIValidationError(
                f"主機名稱 '{host_name}' 格式不正確，只能包含字母、數字、底線、連字符和點",
                line_number=line_num,
                line_content=line
            )
        
        # 如果有內聯變數，驗證每個變數
        if len(parts) > 1:
            inline_vars_str = parts[1]
            
            # 使用 shlex 處理引號（正確分割包含空格的值）
            try:
                # shlex.split 會正確處理引號內的空格
                var_tokens = shlex.split(inline_vars_str)
            except ValueError as e:
                raise INIValidationError(
                    f"變數解析錯誤: {str(e)}",
                    line_number=line_num,
                    line_content=line
                )
            
            # 驗證每個變數 token
            for var_part in var_tokens:
                if '=' not in var_part:
                    raise INIValidationError(
                        f"內聯變數 '{var_part}' 缺少等號，格式應為 'key=value'",
                        line_number=line_num,
                        line_content=line
                    )


def validate_ini_syntax(content: str) -> Tuple[bool, Optional[str], List[INIValidationError]]:
    """
    驗證 INI 語法
    
    Args:
        content: INI 文件內容
        
    Returns:
        (是否有效, 錯誤訊息, 錯誤列表)
    """
    validator = INIValidator(content)
    is_valid, errors = validator.validate()
    
    if is_valid:
        return True, None, []
    
    # 生成錯誤訊息
    error_messages = []
    for error in errors:
        error_messages.append(str(error))
    
    combined_message = "\n".join(error_messages)
    
    return False, combined_message, errors


# 便捷函數
def quick_validate(content: str) -> bool:
    """
    快速驗證（僅返回布林值）
    
    Args:
        content: INI 文件內容
        
    Returns:
        是否有效
    """
    is_valid, _, _ = validate_ini_syntax(content)
    return is_valid
