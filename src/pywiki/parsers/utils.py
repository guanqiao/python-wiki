"""
解析器共享工具模块

提供跨解析器的通用功能，如注释提取、可见性检测等
"""

import re
from typing import Optional

from pywiki.parsers.types import Visibility


def get_visibility(name: str) -> Visibility:
    """根据名称获取可见性

    统一的可见性检测逻辑：
    - __name (双下划线开头，非双下划线结尾): PRIVATE
    - _name (单下划线开头): PROTECTED
    - name (无下划线): PUBLIC

    Args:
        name: 标识符名称

    Returns:
        Visibility 枚举值
    """
    if name.startswith("__") and not name.endswith("__"):
        return Visibility.PRIVATE
    elif name.startswith("_"):
        return Visibility.PROTECTED
    return Visibility.PUBLIC


def extract_jsdoc(source: str, line_start: int) -> Optional[str]:
    """提取 JSDoc 风格的注释

    Args:
        source: 源代码字符串
        line_start: 目标节点开始的行号（0-based）

    Returns:
        提取的注释内容，如果没有则返回 None
    """
    lines = source.split("\n")
    comments = []
    in_javadoc = False

    for i in range(line_start - 1, -1, -1):
        if i < 0:
            break

        line = lines[i].strip()

        if line.startswith("/**"):
            comments.insert(0, line)
            in_javadoc = True
            break
        elif line.startswith("*/"):
            in_javadoc = True
            comments.insert(0, line)
        elif line.startswith("*") and in_javadoc:
            comments.insert(0, line.lstrip("* "))
        elif line == "" and in_javadoc:
            continue
        elif line.startswith("//"):
            comments.insert(0, line[2:].strip())
        else:
            break

    if comments:
        # 清理 JSDoc 标记
        cleaned = []
        for line in comments:
            line = line.strip()
            if line.startswith("/**"):
                line = line[3:].strip()
            elif line.startswith("*/"):
                line = line[:-2].strip()
            elif line.startswith("*"):
                line = line[1:].strip()
            if line:
                cleaned.append(line)
        return "\n".join(cleaned)

    return None


def extract_javadoc(source: str, line_start: int) -> Optional[str]:
    """提取 Java Javadoc 风格的注释

    Args:
        source: 源代码字符串
        line_start: 目标节点开始的行号（0-based）

    Returns:
        提取的注释内容，如果没有则返回 None
    """
    lines = source.split("\n")
    comments = []
    in_javadoc = False

    for i in range(line_start - 1, -1, -1):
        if i < 0:
            break

        line = lines[i].strip()

        if line.startswith("/**"):
            comments.insert(0, line)
            in_javadoc = True
            break
        elif line.startswith("*/"):
            in_javadoc = True
            comments.insert(0, line)
        elif line.startswith("*") and in_javadoc:
            comments.insert(0, line.lstrip("* "))
        elif line == "" and in_javadoc:
            continue
        else:
            break

    if comments:
        # 清理 Javadoc 标记
        cleaned = []
        for line in comments:
            line = line.strip()
            if line.startswith("/**"):
                line = line[3:].strip()
            elif line.startswith("*/"):
                line = line[:-2].strip()
            elif line.startswith("*"):
                line = line[1:].strip()
            if line:
                cleaned.append(line)
        return "\n".join(cleaned)

    return None


def extract_python_docstring(docstring: Optional[str]) -> Optional[str]:
    """提取 Python 文档字符串的描述部分

    Args:
        docstring: Python 文档字符串

    Returns:
        描述部分的第一行
    """
    if not docstring:
        return None

    lines = docstring.strip().split("\n")
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith(":") and not stripped.startswith("@"):
            return stripped

    return None


def extract_raises(docstring: Optional[str]) -> list[str]:
    """从文档字符串中提取异常信息

    Args:
        docstring: Python 文档字符串

    Returns:
        异常类型列表
    """
    if not docstring:
        return []

    raises = []
    pattern = r":raises?\s+(\w+)"
    matches = re.findall(pattern, docstring)
    raises.extend(matches)
    return raises


def is_react_function_component(source_text: str, func_name: str = "") -> bool:
    """检测是否为 React 函数组件

    Args:
        source_text: 函数体源代码
        func_name: 函数名

    Returns:
        是否为 React 组件
    """
    # 检查是否返回 JSX
    if "React" in source_text or "jsx" in source_text.lower():
        return True

    # 检查函数名是否为大写开头（React 组件约定）
    if func_name and func_name[0].isupper():
        return True

    # 检查是否包含 JSX 语法
    if re.search(r'return\s*<\w+', source_text):
        return True

    return False


def detect_react_hooks(source_text: str) -> list[str]:
    """检测使用的 React Hooks

    Args:
        source_text: 源代码

    Returns:
        使用的 Hooks 列表
    """
    hooks = []
    hook_patterns = [
        "useState", "useEffect", "useContext", "useReducer",
        "useCallback", "useMemo", "useRef", "useImperativeHandle",
        "useLayoutEffect", "useDebugValue", "useId",
        "useTransition", "useDeferredValue", "useSyncExternalStore",
        "useInsertionEffect"
    ]

    for hook in hook_patterns:
        if hook in source_text:
            hooks.append(hook)

    return hooks


def extract_route_mapping(source: str, annotation: str) -> Optional[str]:
    """从源码中提取 Spring 路由映射

    Args:
        source: 源代码
        annotation: 注解名称

    Returns:
        路由路径
    """
    pattern = rf'@{annotation}\s*\(\s*["\']([^"\']+)["\']\s*\)'
    match = re.search(pattern, source)
    if match:
        return match.group(1)

    # 尝试匹配 value 属性
    pattern = rf'@{annotation}\s*\(\s*value\s*=\s*["\']([^"\']+)["\']\s*\)'
    match = re.search(pattern, source)
    if match:
        return match.group(1)

    # 尝试匹配 path 属性
    pattern = rf'@{annotation}\s*\(\s*path\s*=\s*["\']([^"\']+)["\']\s*\)'
    match = re.search(pattern, source)
    if match:
        return match.group(1)

    return None


def is_vue_composition_api(source: str) -> bool:
    """检测 Vue 文件是否使用 Composition API

    Args:
        source: script 部分源代码

    Returns:
        是否使用 Composition API
    """
    indicators = [
        "setup",
        "defineProps",
        "defineEmits",
        "defineExpose",
        "ref(",
        "reactive(",
        "computed(",
        "watch(",
        "watchEffect",
        "onMounted",
        "onUnmounted",
        "provide(",
        "inject("
    ]

    for indicator in indicators:
        if indicator in source:
            return True

    return False


def is_vue_options_api(source: str) -> bool:
    """检测 Vue 文件是否使用 Options API

    Args:
        source: script 部分源代码

    Returns:
        是否使用 Options API
    """
    indicators = [
        r'\bdata\s*\(\s*\)\s*\{',
        r'\bmethods\s*:\s*\{',
        r'\bcomputed\s*:\s*\{',
        r'\bwatch\s*:\s*\{',
        r'\bprops\s*:\s*\{',
        r'\bemits\s*:\s*\[',
        r'\bcomponents\s*:\s*\{',
    ]

    for pattern in indicators:
        if re.search(pattern, source):
            return True

    return False


def normalize_type_hint(type_hint: Optional[str]) -> Optional[str]:
    """规范化类型提示字符串

    Args:
        type_hint: 原始类型提示

    Returns:
        规范化后的类型提示
    """
    if not type_hint:
        return None

    # 移除多余空格
    type_hint = type_hint.strip()

    # 移除开头的冒号（TypeScript 风格）
    if type_hint.startswith(":"):
        type_hint = type_hint[1:].strip()

    return type_hint if type_hint else None


def merge_docstrings(*docs: Optional[str]) -> Optional[str]:
    """合并多个文档字符串

    Args:
        *docs: 多个文档字符串

    Returns:
        合并后的文档字符串
    """
    non_empty = [d.strip() for d in docs if d and d.strip()]
    if not non_empty:
        return None

    return "\n".join(non_empty)


def get_node_text(node, source: str) -> str:
    """从 tree-sitter 节点提取文本

    Args:
        node: tree-sitter 节点
        source: 源代码字符串

    Returns:
        节点对应的源代码文本
    """
    return source[node.start_byte:node.end_byte]


def get_file_size_mb(file_path) -> float:
    """获取文件大小（MB）

    Args:
        file_path: 文件路径

    Returns:
        文件大小（MB）
    """
    try:
        return file_path.stat().st_size / (1024 * 1024)
    except (OSError, IOError):
        return 0.0
