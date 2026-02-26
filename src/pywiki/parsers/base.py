"""
解析器基类
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional

from pywiki.parsers.types import ParseResult


class BaseParser(ABC):
    """代码解析器基类"""

    def __init__(
        self,
        exclude_patterns: Optional[list[str]] = None,
        include_private: bool = False,
    ):
        self.exclude_patterns = exclude_patterns or []
        self.include_private = include_private

    @abstractmethod
    def parse_file(self, file_path: Path) -> ParseResult:
        """解析单个文件"""
        pass

    @abstractmethod
    def parse_directory(self, directory: Path) -> ParseResult:
        """解析整个目录"""
        pass

    @abstractmethod
    def get_supported_extensions(self) -> list[str]:
        """获取支持的文件扩展名"""
        pass

    def should_parse(self, file_path: Path) -> bool:
        """检查文件是否应该被解析"""
        if not file_path.is_file():
            return False

        ext = file_path.suffix.lower()
        if ext not in self.get_supported_extensions():
            return False

        for pattern in self.exclude_patterns:
            if pattern in str(file_path):
                return False

        return True
