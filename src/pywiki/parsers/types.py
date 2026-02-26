"""
解析器类型定义
"""

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional


class Visibility(str, Enum):
    PUBLIC = "public"
    PROTECTED = "protected"
    PRIVATE = "private"


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
class ParseResult:
    modules: list[ModuleInfo] = field(default_factory=list)
    dependencies: list[DependencyInfo] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
