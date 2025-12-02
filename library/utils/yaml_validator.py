"""
YAML 語法驗證器

提供帶有行號定位的 YAML 語法驗證功能，用於驗證 Ansible 的 group_vars 檔案。

功能：
- YAML 基本語法驗證（帶行號定位）
- Jinja2 變數語法檢查
- Testcase set 提取

Author: Network Toolbox Team
Created: 2025-12-02
"""

import re
import logging
from typing import Dict, List, Optional, Tuple, Set

import yaml

logger = logging.getLogger(__name__)


class YAMLValidator:
    """YAML 語法驗證器"""
    
    # Jinja2 變數的正則表達式
    JINJA2_VAR_PATTERN = re.compile(r'\{\{.*?\}\}')
    JINJA2_BLOCK_PATTERN = re.compile(r'\{%.*?%\}')
    JINJA2_COMMENT_PATTERN = re.compile(r'\{#.*?#\}')
    
    # 未加引號的 Jinja2 變數（可能造成 YAML 解析錯誤）
    UNQUOTED_JINJA2_PATTERN = re.compile(
        r':\s*(\{\{[^}]+\}\})(?:\s*$|\s+#)',
        re.MULTILINE
    )
    
    @staticmethod
    def validate_yaml_syntax(content: str) -> Dict:
        """
        驗證 YAML 語法
        
        Args:
            content: YAML 文件內容
            
        Returns:
            {
                'is_valid': bool,
                'error_message': str | None,
                'error_line': int | None,
                'error_column': int | None,
                'error_context': str | None
            }
        """
        result = {
            'is_valid': True,
            'error_message': None,
            'error_line': None,
            'error_column': None,
            'error_context': None
        }
        
        if not content or not content.strip():
            result['is_valid'] = False
            result['error_message'] = 'YAML 檔案內容為空'
            return result
        
        try:
            # 嘗試解析 YAML
            yaml.safe_load(content)
            logger.debug("YAML syntax validation passed")
            return result
            
        except yaml.YAMLError as e:
            result['is_valid'] = False
            
            # 提取錯誤位置資訊
            if hasattr(e, 'problem_mark') and e.problem_mark:
                mark = e.problem_mark
                result['error_line'] = mark.line + 1  # YAML 行號從 0 開始
                result['error_column'] = mark.column + 1
                
                # 提取錯誤行的內容
                lines = content.split('\n')
                if 0 <= mark.line < len(lines):
                    result['error_context'] = lines[mark.line]
            
            # 組合錯誤訊息
            error_parts = []
            if hasattr(e, 'problem') and e.problem:
                error_parts.append(e.problem)
            if hasattr(e, 'context') and e.context:
                error_parts.append(e.context)
            
            if error_parts:
                result['error_message'] = ' '.join(error_parts)
            else:
                result['error_message'] = str(e)
            
            # 根據錯誤類型和上下文提供更精確的提示
            error_msg_lower = result['error_message'].lower() if result['error_message'] else ''
            error_context = result.get('error_context', '') or ''
            
            if 'mapping values are not allowed' in error_msg_lower:
                # 檢查錯誤行是否包含 Jinja2 變數
                if '{{' in error_context and '}}' in error_context:
                    result['error_message'] += '\n💡 提示: 這通常是因為 Jinja2 變數 {{ ... }} 沒有用引號包起來'
                else:
                    result['error_message'] += '\n💡 提示: 請檢查該行的格式，可能是縮排錯誤、多餘的空格、或冒號使用不當'
            elif 'could not find expected' in error_msg_lower:
                result['error_message'] += '\n💡 提示: 請檢查該行附近的語法，可能缺少冒號、引號不匹配、或縮排問題'
            elif 'expected' in error_msg_lower and 'found' in error_msg_lower:
                result['error_message'] += '\n💡 提示: 請檢查縮排是否正確，YAML 對縮排非常敏感'
            elif 'scanner error' in error_msg_lower or 'scan' in error_msg_lower:
                result['error_message'] += '\n💡 提示: 請檢查是否有特殊字符或不正確的縮排'
            
            logger.warning(f"YAML syntax error at line {result['error_line']}: {result['error_message']}")
            return result
            
        except Exception as e:
            result['is_valid'] = False
            result['error_message'] = f'驗證過程發生錯誤: {str(e)}'
            logger.error(f"YAML validation exception: {e}", exc_info=True)
            return result
    
    @staticmethod
    def validate_jinja2_in_yaml(content: str) -> Dict:
        """
        驗證 YAML 中的 Jinja2 變數語法
        
        檢查項目：
        - {{ variable }} 是否有正確的引號包裹
        - Jinja2 語法是否平衡（開關括號匹配）
        
        Args:
            content: YAML 文件內容
            
        Returns:
            {
                'is_valid': bool,
                'warnings': List[str],
                'unquoted_jinja2': List[Dict],  # 未加引號的 Jinja2 變數
                'total_jinja2_vars': int
            }
        """
        result = {
            'is_valid': True,
            'warnings': [],
            'unquoted_jinja2': [],
            'total_jinja2_vars': 0
        }
        
        if not content:
            return result
        
        lines = content.split('\n')
        
        # 統計所有 Jinja2 變數
        all_jinja2 = YAMLValidator.JINJA2_VAR_PATTERN.findall(content)
        result['total_jinja2_vars'] = len(all_jinja2)
        
        # 逐行檢查未加引號的 Jinja2 變數
        for line_num, line in enumerate(lines, 1):
            # 跳過註釋行
            stripped = line.strip()
            if stripped.startswith('#'):
                continue
            
            # 檢查是否有 Jinja2 變數
            if '{{' not in line:
                continue
            
            # 檢查 Jinja2 變數是否正確引用
            # 正確格式: key: "{{ var }}" 或 key: '{{ var }}'
            # 錯誤格式: key: {{ var }}
            
            # 檢查是否是 key: {{ value }} 格式（未加引號）
            match = re.search(r':\s*(\{\{[^}]+\}\})(?:\s*$|\s+#|\s+\S)', line)
            if match:
                jinja2_expr = match.group(1)
                
                # 檢查這個 Jinja2 表達式前是否有引號
                before_match = line[:match.start(1)]
                
                # 如果冒號後面直接是 {{ 而不是 "{{ 或 '{{
                if not re.search(r'["\']s*$', before_match):
                    result['unquoted_jinja2'].append({
                        'line': line_num,
                        'content': line.strip(),
                        'expression': jinja2_expr
                    })
                    result['warnings'].append(
                        f"第 {line_num} 行: Jinja2 變數 {jinja2_expr} 建議用引號包裹"
                    )
        
        # 檢查括號平衡
        open_braces = content.count('{{')
        close_braces = content.count('}}')
        if open_braces != close_braces:
            result['is_valid'] = False
            result['warnings'].append(
                f"Jinja2 括號不平衡: {{ 出現 {open_braces} 次, }} 出現 {close_braces} 次"
            )
        
        # 如果有太多未加引號的變數，標記為可能有問題
        if len(result['unquoted_jinja2']) > 0:
            # 注意：在某些情況下，未加引號的 Jinja2 也能正常工作
            # 所以這裡只是警告，不標記為無效
            logger.debug(f"Found {len(result['unquoted_jinja2'])} unquoted Jinja2 variables")
        
        return result
    
    @staticmethod
    def extract_testcase_sets(content: str) -> Set[str]:
        """
        從 testcases.yml 提取所有定義的 testcase_set 名稱
        
        支援的結構格式：
        
        格式 1 - 直接作為 top-level key:
            UGSD_GSD_mix:
              - test1
              - test2
            POR:
              - test3
        
        格式 2 - 在 testcase_sets 或類似 key 下:
            testcase_sets:
              UGSD_GSD_mix:
                tests: [...]
              POR:
                tests: [...]
        
        格式 3 - 列表格式:
            testcase_sets:
              - name: UGSD_GSD_mix
                tests: [...]
              - name: POR
        
        Args:
            content: testcases.yml 文件內容
            
        Returns:
            Set of testcase_set names
        """
        testcase_sets = set()
        
        if not content:
            return testcase_sets
        
        try:
            data = yaml.safe_load(content)
            
            if not isinstance(data, dict):
                logger.warning("testcases.yml root is not a dictionary")
                return testcase_sets
            
            # 策略 1: 直接在 top-level 尋找 testcase 定義
            # 排除常見的非 testcase key
            excluded_keys = {
                'ansible_connection', 'ansible_user', 'ansible_password',
                'ansible_port', 'ansible_host', 'vars', 'hosts', 'children',
                'all', 'ungrouped', 'testcase_sets', 'testcases', 'settings',
                'config', 'defaults', 'common'
            }
            
            for key in data.keys():
                if key.lower() not in excluded_keys:
                    # 可能是一個 testcase_set 名稱
                    testcase_sets.add(key)
            
            # 策略 2: 在 testcase_sets 或 testcases key 下尋找
            for container_key in ['testcase_sets', 'testcases', 'test_sets', 'tests']:
                if container_key in data:
                    container = data[container_key]
                    
                    if isinstance(container, dict):
                        # 格式: testcase_sets: { set1: {...}, set2: {...} }
                        testcase_sets.update(container.keys())
                    
                    elif isinstance(container, list):
                        # 格式: testcase_sets: [{ name: set1 }, { name: set2 }]
                        for item in container:
                            if isinstance(item, dict):
                                # 嘗試多種可能的 name key
                                for name_key in ['name', 'set_name', 'testcase_set', 'id']:
                                    if name_key in item:
                                        testcase_sets.add(item[name_key])
                                        break
                            elif isinstance(item, str):
                                # 格式: testcase_sets: [set1, set2, set3]
                                testcase_sets.add(item)
            
            logger.info(f"Extracted {len(testcase_sets)} testcase_set names from YAML")
            return testcase_sets
            
        except yaml.YAMLError as e:
            logger.error(f"Failed to parse YAML for testcase extraction: {e}")
            return testcase_sets
        except Exception as e:
            logger.error(f"Error extracting testcase sets: {e}", exc_info=True)
            return testcase_sets
    
    @staticmethod
    def get_yaml_structure_summary(content: str) -> Dict:
        """
        獲取 YAML 檔案的結構摘要
        
        Args:
            content: YAML 文件內容
            
        Returns:
            {
                'is_valid': bool,
                'root_type': str,  # 'dict', 'list', 'scalar', 'empty'
                'top_level_keys': List[str],
                'total_keys': int,
                'has_jinja2': bool,
                'line_count': int
            }
        """
        result = {
            'is_valid': False,
            'root_type': 'unknown',
            'top_level_keys': [],
            'total_keys': 0,
            'has_jinja2': False,
            'line_count': 0
        }
        
        if not content:
            result['root_type'] = 'empty'
            return result
        
        result['line_count'] = len(content.split('\n'))
        result['has_jinja2'] = '{{' in content
        
        try:
            data = yaml.safe_load(content)
            result['is_valid'] = True
            
            if data is None:
                result['root_type'] = 'empty'
            elif isinstance(data, dict):
                result['root_type'] = 'dict'
                result['top_level_keys'] = list(data.keys())
                result['total_keys'] = len(data)
            elif isinstance(data, list):
                result['root_type'] = 'list'
                result['total_keys'] = len(data)
            else:
                result['root_type'] = 'scalar'
            
            return result
            
        except yaml.YAMLError:
            result['is_valid'] = False
            return result


def validate_yaml_with_line_numbers(content: str) -> Dict:
    """
    便捷函數：驗證 YAML 並返回行號資訊
    
    Args:
        content: YAML 文件內容
        
    Returns:
        驗證結果字典
    """
    return YAMLValidator.validate_yaml_syntax(content)


def extract_testcase_sets_from_yaml(content: str) -> Set[str]:
    """
    便捷函數：從 YAML 提取 testcase_set 名稱
    
    Args:
        content: YAML 文件內容
        
    Returns:
        testcase_set 名稱集合
    """
    return YAMLValidator.extract_testcase_sets(content)


class PathValidator:
    """
    路徑驗證器
    
    支援自動偵測並驗證 Windows 和 Linux 路徑格式。
    
    功能：
    - 自動偵測路徑類型（Windows 本地、UNC、Linux）
    - 驗證斜線方向
    - 檢測混合斜線錯誤
    - 驗證磁碟代號格式
    - 檢測無效字符
    - 提供修正建議
    """
    
    # 需要驗證的路徑欄位及其預期類型
    # None 表示非路徑欄位，跳過驗證
    PATH_FIELDS = {
        'script_nas_file': 'path',           # UNC 或本地路徑
        'script_local_root': 'path',         # 本地目錄
        'script_exec': 'path',               # 本地可執行檔
        'log_path': 'path',                  # 本地檔案
        'archive_root': 'path',              # 本地目錄
        'archive_upload_dir': 'path',        # UNC 網路路徑
        'nas_path': 'path',                  # NAS 路徑
        'local_path': 'path',                # 本地路徑
        'remote_path': 'path',               # 遠端路徑
        'source_path': 'path',               # 來源路徑
        'dest_path': 'path',                 # 目的路徑
        'destination_path': 'path',          # 目的路徑
        'output_path': 'path',               # 輸出路徑
        'input_path': 'path',                # 輸入路徑
        'config_path': 'path',               # 配置檔路徑
        'work_dir': 'path',                  # 工作目錄
        'working_directory': 'path',         # 工作目錄
        'base_path': 'path',                 # 基礎路徑
        'root_path': 'path',                 # 根路徑
    }
    
    # 應該排除的欄位（萬用字符模式、正則表達式等）
    EXCLUDE_FIELDS = {
        'archive_patterns',      # 萬用字符模式
        'patterns',              # 模式
        'regex',                 # 正則表達式
        'pattern',               # 模式
        'glob',                  # glob 模式
        'filter',                # 過濾器
        'exclude',               # 排除模式
        'include',               # 包含模式
    }
    
    # Windows 路徑中不允許的字符（除了磁碟代號中的冒號）
    WINDOWS_INVALID_CHARS = re.compile(r'[<>"|?*]')
    
    # Linux 路徑中不允許的字符
    LINUX_INVALID_CHARS = re.compile(r'[\x00]')  # 只有 null 字符
    
    @staticmethod
    def detect_path_type(path: str) -> str:
        """
        自動偵測路徑類型
        
        Args:
            path: 路徑字串
            
        Returns:
            路徑類型：
            - 'windows_local'    : Windows 本地路徑 (C:\\path\\...)
            - 'windows_unc'      : Windows UNC 網路路徑 (\\\\server\\...)
            - 'linux'            : Linux 絕對路徑 (/path/...)
            - 'windows_relative' : Windows 相對路徑
            - 'linux_relative'   : Linux 相對路徑
            - 'mixed'            : 混合格式（錯誤）
            - 'windows_typo'     : Windows 路徑但磁碟代號有錯誤（如 C; 應為 C:）
            - 'ambiguous'        : 無法確定
            - 'empty'            : 空路徑
        """
        if not path or not path.strip():
            return 'empty'
        
        path = path.strip()
        
        # 優先檢查混合斜線（最常見的錯誤）
        has_backslash = '\\' in path
        has_forwardslash = '/' in path
        
        # 1. Windows UNC 路徑: \\server\share\...
        if path.startswith('\\\\'):
            # 檢查 UNC 路徑是否混用斜線
            if has_forwardslash:
                return 'mixed'
            return 'windows_unc'
        
        # 2. Windows 本地路徑: C:\ 或 D:\ 等
        if len(path) >= 2 and path[1] == ':':
            if path[0].upper() in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ':
                # 檢查 Windows 路徑是否混用斜線
                if has_backslash and has_forwardslash:
                    return 'mixed'
                return 'windows_local'
        
        # 2.1 檢查常見的磁碟代號錯誤（如 C; 應為 C:）
        if len(path) >= 2 and path[0].upper() in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ':
            # 檢查第二個字符是否是常見的打字錯誤
            if path[1] in ';':  # 分號是冒號的常見打字錯誤
                return 'windows_typo'
            # 如果第一個字符是磁碟代號，且後面直接接反斜線（缺少冒號）
            if path[1] == '\\':
                return 'windows_typo'
        
        # 3. Linux 絕對路徑: /path/to/...
        if path.startswith('/'):
            # 排除 // 開頭（可能是錯誤的 UNC 寫法）
            if path.startswith('//'):
                return 'ambiguous'
            # 檢查 Linux 路徑是否混用斜線
            if has_backslash:
                return 'mixed'
            return 'linux'
        
        # 4. 檢查混合斜線（相對路徑的情況）
        if has_backslash and has_forwardslash:
            return 'mixed'
        
        # 5. 只有反斜線，可能是 Windows 相對路徑
        if has_backslash:
            return 'windows_relative'
        
        # 6. 只有正斜線，可能是 Linux 相對路徑
        if has_forwardslash:
            return 'linux_relative'
        
        # 7. 無斜線，可能是檔名或簡單名稱
        return 'ambiguous'
    
    @staticmethod
    def validate_windows_path(path: str, path_type: str) -> Dict:
        """
        驗證 Windows 路徑格式
        
        Args:
            path: 路徑字串
            path_type: 偵測到的路徑類型 ('windows_local' 或 'windows_unc')
            
        Returns:
            {
                'is_valid': bool,
                'errors': List[str],
                'warnings': List[str],
                'suggestion': str | None
            }
        """
        result = {
            'is_valid': True,
            'errors': [],
            'warnings': [],
            'suggestion': None
        }
        
        original_path = path
        
        # 檢查是否混用斜線
        if '/' in path:
            result['is_valid'] = False
            result['errors'].append('Windows 路徑不應包含正斜線 (/)，請使用反斜線 (\\)')
            # 建議修正
            path = path.replace('/', '\\')
        
        if path_type == 'windows_local':
            # 驗證磁碟代號格式
            if len(path) >= 2:
                drive_letter = path[0]
                
                # 檢查磁碟代號是否為小寫
                if drive_letter.islower():
                    result['warnings'].append(f'磁碟代號建議使用大寫: {drive_letter.upper()}:')
                    path = drive_letter.upper() + path[1:]
                
                # 檢查磁碟代號後是否有反斜線
                if len(path) >= 3 and path[2] != '\\':
                    result['is_valid'] = False
                    result['errors'].append('磁碟代號後應該接反斜線，例如: C:\\')
                    path = path[:2] + '\\' + path[2:]
        
        elif path_type == 'windows_unc':
            # UNC 路徑應該以 \\ 開頭
            if not path.startswith('\\\\'):
                result['is_valid'] = False
                result['errors'].append('UNC 路徑必須以 \\\\ 開頭')
            
            # 檢查 UNC 路徑格式: \\server\share
            unc_parts = path.lstrip('\\').split('\\')
            if len(unc_parts) < 2:
                result['is_valid'] = False
                result['errors'].append('UNC 路徑格式不完整，應為 \\\\server\\share\\...')
        
        # 檢查無效字符
        invalid_match = PathValidator.WINDOWS_INVALID_CHARS.search(path)
        if invalid_match:
            result['is_valid'] = False
            result['errors'].append(f'路徑包含無效字符: {invalid_match.group()}')
        
        # 檢查連續的反斜線（除了 UNC 開頭）
        if path_type == 'windows_local' and '\\\\' in path:
            result['warnings'].append('路徑中有連續的反斜線，請確認是否正確')
        
        # 如果有修正，提供建議
        if path != original_path:
            result['suggestion'] = path
        
        return result
    
    @staticmethod
    def validate_linux_path(path: str) -> Dict:
        """
        驗證 Linux 路徑格式
        
        Args:
            path: 路徑字串
            
        Returns:
            {
                'is_valid': bool,
                'errors': List[str],
                'warnings': List[str],
                'suggestion': str | None
            }
        """
        result = {
            'is_valid': True,
            'errors': [],
            'warnings': [],
            'suggestion': None
        }
        
        original_path = path
        
        # 檢查是否混用斜線
        if '\\' in path:
            result['is_valid'] = False
            result['errors'].append('Linux 路徑不應包含反斜線 (\\)，請使用正斜線 (/)')
            path = path.replace('\\', '/')
        
        # Linux 絕對路徑應以 / 開頭
        if not path.startswith('/'):
            result['warnings'].append('Linux 絕對路徑應以 / 開頭')
        
        # 檢查連續的斜線
        if '//' in path:
            result['warnings'].append('路徑中有連續的斜線，請確認是否正確')
            # 修正連續斜線
            while '//' in path:
                path = path.replace('//', '/')
        
        # 檢查無效字符
        invalid_match = PathValidator.LINUX_INVALID_CHARS.search(path)
        if invalid_match:
            result['is_valid'] = False
            result['errors'].append('路徑包含無效字符 (null)')
        
        # 如果有修正，提供建議
        if path != original_path:
            result['suggestion'] = path
        
        return result
    
    @staticmethod
    def validate_path(path: str) -> Dict:
        """
        驗證單一路徑（自動偵測類型）
        
        Args:
            path: 路徑字串
            
        Returns:
            {
                'is_valid': bool,
                'path_type': str,
                'errors': List[str],
                'warnings': List[str],
                'suggestion': str | None
            }
        """
        path_type = PathValidator.detect_path_type(path)
        
        result = {
            'is_valid': True,
            'path_type': path_type,
            'errors': [],
            'warnings': [],
            'suggestion': None
        }
        
        if path_type == 'empty':
            result['warnings'].append('路徑為空')
            return result
        
        if path_type == 'windows_typo':
            result['is_valid'] = False
            # 判斷具體是什麼錯誤
            if len(path) >= 2 and path[1] == ';':
                result['errors'].append(f'磁碟代號格式錯誤: "{path[0]};\" 應該是 "{path[0]}:\\"（分號應改為冒號）')
                result['suggestion'] = path[0].upper() + ':' + path[2:]
            elif len(path) >= 2 and path[1] == '\\':
                result['errors'].append(f'磁碟代號格式錯誤: "{path[0]}\\" 缺少冒號，應該是 "{path[0].upper()}:\\"')
                result['suggestion'] = path[0].upper() + ':' + path[1:]
            else:
                result['errors'].append('磁碟代號格式錯誤')
            return result
        
        if path_type == 'mixed':
            result['is_valid'] = False
            result['errors'].append('路徑混用了正斜線 (/) 和反斜線 (\\)，請統一使用')
            # 嘗試判斷應該是哪種路徑
            if path[0].upper() in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ' and len(path) > 1 and path[1] == ':':
                result['suggestion'] = path.replace('/', '\\')
                result['errors'][-1] += '，建議使用 Windows 格式 (\\)'
            else:
                result['suggestion'] = path.replace('\\', '/')
                result['errors'][-1] += '，建議使用 Linux 格式 (/)'
            return result
        
        if path_type == 'ambiguous':
            result['warnings'].append('無法確定路徑類型，建議使用絕對路徑')
            return result
        
        if path_type in ('windows_local', 'windows_unc', 'windows_relative'):
            validation = PathValidator.validate_windows_path(path, path_type)
        elif path_type in ('linux', 'linux_relative'):
            validation = PathValidator.validate_linux_path(path)
        else:
            return result
        
        result['is_valid'] = validation['is_valid']
        result['errors'] = validation['errors']
        result['warnings'] = validation['warnings']
        result['suggestion'] = validation['suggestion']
        
        return result
    
    @staticmethod
    def validate_testcase_paths(content: str) -> Dict:
        """
        驗證 testcases.yml 中所有路徑欄位
        
        會自動偵測每個路徑的類型並進行對應的驗證。
        
        Args:
            content: testcases.yml 文件內容
            
        Returns:
            {
                'is_valid': bool,
                'path_errors': [
                    {
                        'line': 5,
                        'field': 'script_exec',
                        'value': 'C:/drivers/install.bat',
                        'path_type': 'windows_local',
                        'errors': ['Windows 路徑不應包含正斜線...'],
                        'warnings': [],
                        'suggestion': 'C:\\drivers\\install.bat'
                    }
                ],
                'path_warnings': [...],
                'total_paths_checked': int,
                'summary': {
                    'windows_local': int,
                    'windows_unc': int,
                    'linux': int,
                    'other': int
                }
            }
        """
        result = {
            'is_valid': True,
            'path_errors': [],
            'path_warnings': [],
            'total_paths_checked': 0,
            'summary': {
                'windows_local': 0,
                'windows_unc': 0,
                'linux': 0,
                'other': 0
            }
        }
        
        if not content:
            return result
        
        lines = content.split('\n')
        
        # 建立所有可能的路徑欄位名稱模式（包含 _path, _dir, _root 結尾）
        path_field_suffixes = ('_path', '_dir', '_root', '_file', '_directory')
        
        for line_num, line in enumerate(lines, 1):
            # 跳過註釋行和空行
            stripped = line.strip()
            if not stripped or stripped.startswith('#'):
                continue
            
            # 解析 key: value 格式
            if ':' not in line:
                continue
            
            # 分離 key 和 value
            colon_pos = line.find(':')
            key = line[:colon_pos].strip()
            value = line[colon_pos + 1:].strip()
            
            # 移除 value 中的引號
            if value and value[0] in '"\'':
                quote_char = value[0]
                if len(value) > 1 and value[-1] == quote_char:
                    value = value[1:-1]
            
            # 跳過空值或 Jinja2 變數
            if not value or value.startswith('{{'):
                continue
            
            # 判斷是否需要驗證此欄位
            should_validate = False
            
            # 先檢查是否是排除欄位
            if key in PathValidator.EXCLUDE_FIELDS:
                continue
            
            # 方式 1: 欄位名稱在預定義列表中
            if key in PathValidator.PATH_FIELDS:
                should_validate = True
            
            # 方式 2: 欄位名稱以路徑相關後綴結尾（但不包含排除後綴）
            elif key.endswith(path_field_suffixes):
                # 額外檢查是否包含排除關鍵字
                excluded_keywords = ('pattern', 'regex', 'glob', 'filter')
                if not any(kw in key.lower() for kw in excluded_keywords):
                    should_validate = True
            
            # 方式 3: 值看起來像是路徑
            elif PathValidator.detect_path_type(value) not in ('empty', 'ambiguous'):
                should_validate = True
            
            if not should_validate:
                continue
            
            # 驗證路徑
            validation = PathValidator.validate_path(value)
            result['total_paths_checked'] += 1
            
            # 更新統計
            path_type = validation['path_type']
            if path_type in ('windows_local', 'windows_relative'):
                result['summary']['windows_local'] += 1
            elif path_type == 'windows_unc':
                result['summary']['windows_unc'] += 1
            elif path_type in ('linux', 'linux_relative'):
                result['summary']['linux'] += 1
            else:
                result['summary']['other'] += 1
            
            # 收集錯誤
            if not validation['is_valid']:
                result['is_valid'] = False
                result['path_errors'].append({
                    'line': line_num,
                    'field': key,
                    'value': value,
                    'path_type': path_type,
                    'errors': validation['errors'],
                    'warnings': validation['warnings'],
                    'suggestion': validation['suggestion']
                })
            elif validation['warnings']:
                result['path_warnings'].append({
                    'line': line_num,
                    'field': key,
                    'value': value,
                    'path_type': path_type,
                    'warnings': validation['warnings'],
                    'suggestion': validation['suggestion']
                })
        
        logger.info(f"Path validation complete: {result['total_paths_checked']} paths checked, "
                   f"{len(result['path_errors'])} errors, {len(result['path_warnings'])} warnings")
        
        return result


def validate_paths_in_yaml(content: str) -> Dict:
    """
    便捷函數：驗證 YAML 中的路徑
    
    Args:
        content: YAML 文件內容
        
    Returns:
        驗證結果字典
    """
    return PathValidator.validate_testcase_paths(content)
