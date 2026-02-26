"""
解析器工厂模块
提供统一的解析器获取和注册机制
"""

from pathlib import Path
from typing import Optional, Type

from pywiki.parsers.base import BaseParser
from pywiki.parsers.java import JavaParser
from pywiki.parsers.python import PythonParser
from pywiki.parsers.typescript import TypeScriptParser


class ParserFactory:
    """解析器工厂类

    根据文件扩展名自动选择合适的解析器，支持注册自定义解析器。

    Example:
        >>> factory = ParserFactory()
        >>> parser = factory.get_parser(Path("example.py"))
        >>> result = parser.parse_file(Path("example.py"))

        >>> # 注册自定义解析器
        >>> factory.register_parser([".go"], GoParser)
    """

    _parsers: dict[str, Type[BaseParser]] = {
        ".py": PythonParser,
        ".pyi": PythonParser,
        ".ts": TypeScriptParser,
        ".tsx": TypeScriptParser,
        ".js": TypeScriptParser,
        ".jsx": TypeScriptParser,
        ".mjs": TypeScriptParser,
        ".vue": TypeScriptParser,
        ".java": JavaParser,
    }

    def __init__(
        self,
        exclude_patterns: Optional[list[str]] = None,
        include_private: bool = False,
    ):
        """初始化解析器工厂

        Args:
            exclude_patterns: 排除的文件路径模式列表
            include_private: 是否包含私有成员
        """
        self.exclude_patterns = exclude_patterns or []
        self.include_private = include_private
        self._parser_instances: dict[str, BaseParser] = {}

    def get_parser(self, file_path: Path) -> Optional[BaseParser]:
        """根据文件路径获取对应的解析器

        Args:
            file_path: 文件路径

        Returns:
            对应的解析器实例，如果不支持则返回 None
        """
        ext = file_path.suffix.lower()
        parser_class = self._parsers.get(ext)

        if not parser_class:
            return None

        # 缓存解析器实例
        if ext not in self._parser_instances:
            self._parser_instances[ext] = parser_class(
                exclude_patterns=self.exclude_patterns,
                include_private=self.include_private,
            )

        return self._parser_instances[ext]

    def get_parser_for_extension(self, extension: str) -> Optional[Type[BaseParser]]:
        """根据文件扩展名获取解析器类

        Args:
            extension: 文件扩展名（如 ".py", ".java"）

        Returns:
            解析器类，如果不支持则返回 None
        """
        return self._parsers.get(extension.lower())

    def register_parser(
        self,
        extensions: list[str],
        parser_class: Type[BaseParser],
        override: bool = False
    ) -> None:
        """注册新的解析器

        Args:
            extensions: 支持的文件扩展名列表
            parser_class: 解析器类
            override: 是否覆盖已存在的解析器

        Raises:
            ValueError: 如果扩展名已被注册且 override=False
        """
        for ext in extensions:
            ext = ext.lower()
            if ext in self._parsers and not override:
                raise ValueError(
                    f"Extension '{ext}' is already registered with "
                    f"{self._parsers[ext].__name__}. Use override=True to replace."
                )
            self._parsers[ext] = parser_class

        # 清除缓存，以便新注册的解析器生效
        for ext in extensions:
            ext = ext.lower()
            if ext in self._parser_instances:
                del self._parser_instances[ext]

    def unregister_parser(self, extensions: list[str]) -> None:
        """注销解析器

        Args:
            extensions: 要注销的文件扩展名列表
        """
        for ext in extensions:
            ext = ext.lower()
            if ext in self._parsers:
                del self._parsers[ext]
            if ext in self._parser_instances:
                del self._parser_instances[ext]

    def get_supported_extensions(self) -> list[str]:
        """获取所有支持的文件扩展名

        Returns:
            支持的文件扩展名列表
        """
        return list(self._parsers.keys())

    def is_supported(self, file_path: Path) -> bool:
        """检查文件是否受支持

        Args:
            file_path: 文件路径

        Returns:
            是否支持该文件类型
        """
        ext = file_path.suffix.lower()
        return ext in self._parsers

    def get_parser_info(self) -> dict[str, str]:
        """获取解析器信息

        Returns:
            扩展名到解析器类名的映射
        """
        return {ext: cls.__name__ for ext, cls in self._parsers.items()}

    @classmethod
    def create_default(cls) -> "ParserFactory":
        """创建默认的解析器工厂

        Returns:
            配置好的 ParserFactory 实例
        """
        return cls(
            exclude_patterns=["node_modules", ".git", "__pycache__", ".venv", "venv"],
            include_private=False,
        )


def get_parser_for_file(file_path: Path) -> Optional[BaseParser]:
    """便捷函数：根据文件路径获取解析器

    Args:
        file_path: 文件路径

    Returns:
        对应的解析器实例，如果不支持则返回 None

    Example:
        >>> parser = get_parser_for_file(Path("example.py"))
        >>> if parser:
        ...     result = parser.parse_file(Path("example.py"))
    """
    factory = ParserFactory.create_default()
    return factory.get_parser(file_path)


def parse_file(file_path: Path) -> Optional[object]:
    """便捷函数：直接解析文件

    Args:
        file_path: 文件路径

    Returns:
        解析结果，如果不支持该文件类型则返回 None
    """
    from pywiki.parsers.types import ParseResult

    parser = get_parser_for_file(file_path)
    if parser:
        return parser.parse_file(file_path)
    return None
