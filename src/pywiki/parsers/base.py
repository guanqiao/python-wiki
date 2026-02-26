"""
解析器基类
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional

from pywiki.parsers.types import ErrorType, ParseResult
from pywiki.parsers.utils import get_file_size_mb


class BaseParser(ABC):
    """代码解析器基类

    提供所有解析器的通用功能和接口定义。

    Attributes:
        exclude_patterns: 排除的文件路径模式列表
        include_private: 是否包含私有成员
        max_file_size_mb: 最大文件大小限制（MB），默认 10MB
    """

    DEFAULT_MAX_FILE_SIZE_MB = 10.0

    def __init__(
        self,
        exclude_patterns: Optional[list[str]] = None,
        include_private: bool = False,
        max_file_size_mb: float = DEFAULT_MAX_FILE_SIZE_MB,
    ):
        """初始化解析器

        Args:
            exclude_patterns: 排除的文件路径模式列表
            include_private: 是否包含私有成员
            max_file_size_mb: 最大文件大小限制（MB）
        """
        self.exclude_patterns = exclude_patterns or []
        self.include_private = include_private
        self.max_file_size_mb = max_file_size_mb

    @abstractmethod
    def parse_file(self, file_path: Path) -> ParseResult:
        """解析单个文件

        Args:
            file_path: 要解析的文件路径

        Returns:
            ParseResult 包含解析结果
        """
        pass

    @abstractmethod
    def parse_directory(self, directory: Path) -> ParseResult:
        """解析整个目录

        Args:
            directory: 要解析的目录路径

        Returns:
            ParseResult 包含解析结果
        """
        pass

    @abstractmethod
    def get_supported_extensions(self) -> list[str]:
        """获取支持的文件扩展名

        Returns:
            支持的文件扩展名列表（如 [".py", ".pyi"]）
        """
        pass

    def should_parse(self, file_path: Path) -> bool:
        """检查文件是否应该被解析

        检查条件：
        1. 是文件而非目录
        2. 扩展名在支持列表中
        3. 不在排除模式列表中
        4. 文件大小不超过限制

        Args:
            file_path: 文件路径

        Returns:
            是否应该解析该文件
        """
        if not file_path.is_file():
            return False

        ext = file_path.suffix.lower()
        if ext not in self.get_supported_extensions():
            return False

        for pattern in self.exclude_patterns:
            if pattern in str(file_path):
                return False

        return True

    def check_file_size(self, file_path: Path) -> tuple[bool, Optional[str]]:
        """检查文件大小是否在限制范围内

        Args:
            file_path: 文件路径

        Returns:
            (是否通过检查, 警告信息)
        """
        try:
            size_mb = get_file_size_mb(file_path)
            if size_mb > self.max_file_size_mb:
                return False, f"File too large: {size_mb:.2f}MB (max: {self.max_file_size_mb}MB)"
            return True, None
        except (OSError, IOError) as e:
            return False, f"Cannot check file size: {e}"

    def create_error_result(
        self,
        file_path: Path,
        error_type: ErrorType,
        message: str,
        line: Optional[int] = None,
        recoverable: bool = True
    ) -> ParseResult:
        """创建包含错误的解析结果

        Args:
            file_path: 文件路径
            error_type: 错误类型
            message: 错误消息
            line: 错误行号
            recoverable: 是否可恢复

        Returns:
            包含错误的 ParseResult
        """
        result = ParseResult()
        result.add_error(
            file_path=file_path,
            error_type=error_type,
            message=message,
            line=line,
            recoverable=recoverable
        )
        return result
