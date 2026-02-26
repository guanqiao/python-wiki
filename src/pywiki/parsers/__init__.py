"""
代码解析器模块

支持多种编程语言的代码解析：
- Python (.py, .pyi)
- TypeScript/JavaScript (.ts, .tsx, .js, .jsx, .mjs)
- Vue Single File Components (.vue)
- Java (.java)

Example:
    >>> from pywiki.parsers import PythonParser, TypeScriptParser, JavaParser
    >>> from pywiki.parsers import ParserFactory, get_parser_for_file

    >>> # 使用特定语言的解析器
    >>> parser = PythonParser()
    >>> result = parser.parse_file(Path("example.py"))

    >>> # 使用工厂自动选择解析器
    >>> factory = ParserFactory.create_default()
    >>> parser = factory.get_parser(Path("example.ts"))
    >>> result = parser.parse_file(Path("example.ts"))

    >>> # 便捷函数
    >>> parser = get_parser_for_file(Path("example.java"))
    >>> if parser:
    ...     result = parser.parse_file(Path("example.java"))
"""

from pywiki.parsers.base import BaseParser
from pywiki.parsers.types import ParseResult
from pywiki.parsers.factory import (
    ParserFactory,
    get_parser_for_file,
    parse_file,
)
from pywiki.parsers.java import JavaParser
from pywiki.parsers.python import PythonParser
from pywiki.parsers.types import (
    ClassInfo,
    DependencyInfo,
    FunctionInfo,
    ImportInfo,
    ModuleInfo,
    ParameterInfo,
    ParameterKind,
    PropertyInfo,
    Visibility,
)
from pywiki.parsers.typescript import TypeScriptParser

__all__ = [
    # 解析器基类
    "BaseParser",
    "ParseResult",
    # 具体解析器实现
    "PythonParser",
    "TypeScriptParser",
    "JavaParser",
    # 工厂和便捷函数
    "ParserFactory",
    "get_parser_for_file",
    "parse_file",
    # 数据类型
    "ClassInfo",
    "FunctionInfo",
    "ModuleInfo",
    "ImportInfo",
    "PropertyInfo",
    "ParameterInfo",
    "DependencyInfo",
    "Visibility",
    "ParameterKind",
]
