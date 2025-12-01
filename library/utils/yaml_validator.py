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
            
            # 特殊處理常見的 Jinja2 相關錯誤
            error_msg_lower = result['error_message'].lower() if result['error_message'] else ''
            if 'mapping values are not allowed' in error_msg_lower:
                result['error_message'] += '\n💡 提示: 這通常是因為 Jinja2 變數 {{ ... }} 沒有用引號包起來'
            elif 'expected' in error_msg_lower and 'found' in error_msg_lower:
                result['error_message'] += '\n💡 提示: 請檢查縮排是否正確，YAML 對縮排非常敏感'
            
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
