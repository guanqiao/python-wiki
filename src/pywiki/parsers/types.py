"""
解析器类型定义
"""

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional


class Visibility(str, Enum):
    """可见性枚举"""
    PUBLIC = "public"
    PROTECTED = "protected"
    PRIVATE = "private"
    PACKAGE = "package"


class ErrorType(str, Enum):
    """错误类型枚举"""
    SYNTAX = "syntax"
    IO = "io"
    MEMORY = "memory"
    TIMEOUT = "timeout"
    PARSE = "parse"
    UNKNOWN = "unknown"


class ParameterKind(str, Enum):
    POSITIONAL = "positional"
    POSITIONAL_OR_KEYWORD = "positional_or_keyword"
    VAR_POSITIONAL = "var_positional"
    KEYWORD_ONLY = "keyword_only"
    VAR_KEYWORD = "var_keyword"


@dataclass
class ParameterInfo:
    name: str
    type_hint: Optional[str] = None
    default_value: Optional[str] = None
    kind: ParameterKind = ParameterKind.POSITIONAL_OR_KEYWORD
    description: Optional[str] = None


@dataclass
class PropertyInfo:
    name: str
    type_hint: Optional[str] = None
    visibility: Visibility = Visibility.PUBLIC
    is_readonly: bool = False
    description: Optional[str] = None
    decorators: list[str] = field(default_factory=list)


@dataclass
class FunctionInfo:
    name: str
    full_name: str
    parameters: list[ParameterInfo] = field(default_factory=list)
    return_type: Optional[str] = None
    visibility: Visibility = Visibility.PUBLIC
    is_async: bool = False
    is_classmethod: bool = False
    is_staticmethod: bool = False
    is_abstract: bool = False
    description: Optional[str] = None
    docstring: Optional[str] = None
    decorators: list[str] = field(default_factory=list)
    raises: list[str] = field(default_factory=list)
    examples: list[str] = field(default_factory=list)
    line_start: int = 0
    line_end: int = 0


@dataclass
class ClassInfo:
    name: str
    full_name: str
    bases: list[str] = field(default_factory=list)
    methods: list[FunctionInfo] = field(default_factory=list)
    properties: list[PropertyInfo] = field(default_factory=list)
    class_variables: list[PropertyInfo] = field(default_factory=list)
    nested_classes: list["ClassInfo"] = field(default_factory=list)
    visibility: Visibility = Visibility.PUBLIC
    is_abstract: bool = False
    is_enum: bool = False
    is_dataclass: bool = False
    description: Optional[str] = None
    docstring: Optional[str] = None
    decorators: list[str] = field(default_factory=list)
    line_start: int = 0
    line_end: int = 0


@dataclass
class ImportInfo:
    module: str
    names: list[str] = field(default_factory=list)
    alias: Optional[str] = None
    is_from_import: bool = False
    line: int = 0


@dataclass
class ModuleInfo:
    name: str
    file_path: Path
    docstring: Optional[str] = None
    imports: list[ImportInfo] = field(default_factory=list)
    classes: list[ClassInfo] = field(default_factory=list)
    functions: list[FunctionInfo] = field(default_factory=list)
    variables: list[PropertyInfo] = field(default_factory=list)
    submodules: list[str] = field(default_factory=list)
    line_count: int = 0


@dataclass
class DependencyInfo:
    source: str
    target: str
    dependency_type: str
    line: Optional[int] = None


@dataclass
class ParseError:
    """结构化解析错误"""
    file_path: Path
    error_type: ErrorType
    message: str
    line: Optional[int] = None
    column: Optional[int] = None
    recoverable: bool = True

    def __str__(self) -> str:
        location = f" at line {self.line}" if self.line else ""
        return f"[{self.error_type.value.upper()}] {self.file_path}{location}: {self.message}"


@dataclass
class ParseResult:
    """解析结果容器"""
    modules: list[ModuleInfo] = field(default_factory=list)
    dependencies: list[DependencyInfo] = field(default_factory=list)
    errors: list[ParseError] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def add_error(
        self,
        file_path: Path,
        error_type: ErrorType,
        message: str,
        line: Optional[int] = None,
        column: Optional[int] = None,
        recoverable: bool = True
    ) -> None:
        """添加结构化错误"""
        self.errors.append(ParseError(
            file_path=file_path,
            error_type=error_type,
            message=message,
            line=line,
            column=column,
            recoverable=recoverable
        ))

    def get_errors_by_type(self, error_type: ErrorType) -> list[ParseError]:
        """按类型获取错误"""
        return [e for e in self.errors if e.error_type == error_type]

    def has_fatal_errors(self) -> bool:
        """检查是否有致命错误"""
        return any(not e.recoverable for e in self.errors)
