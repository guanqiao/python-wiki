"""
Python 代码解析器
使用 AST 解析 Python 代码
"""

import ast
import re
from pathlib import Path
from typing import Optional

from pywiki.parsers.base import BaseParser
from pywiki.parsers.types import (
    ClassInfo,
    DependencyInfo,
    FunctionInfo,
    ImportInfo,
    ModuleInfo,
    ParameterInfo,
    ParameterKind,
    ParseResult,
    PropertyInfo,
    Visibility,
)


class PythonParser(BaseParser):
    """Python AST 解析器

    支持 FastAPI、Pydantic、SQLAlchemy 等主流框架识别
    """

    # FastAPI 相关
    FASTAPI_METHODS = {"get", "post", "put", "delete", "patch", "head", "options", "trace"}
    FASTAPI_DECORATORS = {"route", "api_route", "websocket", "websocket_route"}

    # Pydantic 相关
    PYDANTIC_BASES = {"BaseModel", "pydantic.BaseModel"}

    # SQLAlchemy 相关
    SQLALCHEMY_BASES = {
        "declarative_base", "DeclarativeBase",
        "Base", "db.Model", "Model"
    }
    SQLALCHEMY_COLUMNS = {"Column", "Integer", "String", "Float", "Boolean", "DateTime", "Text"}

    def get_supported_extensions(self) -> list[str]:
        return [".py", ".pyi"]

    def parse_file(self, file_path: Path) -> ParseResult:
        result = ParseResult()

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                source = f.read()

            tree = ast.parse(source)
            module_info = self._parse_module(tree, file_path, source)
            result.modules.append(module_info)

            dependencies = self._extract_dependencies(module_info)
            result.dependencies.extend(dependencies)

        except SyntaxError as e:
            result.errors.append(f"Syntax error in {file_path}: {e}")
        except Exception as e:
            result.errors.append(f"Error parsing {file_path}: {e}")

        return result

    def parse_directory(self, directory: Path) -> ParseResult:
        result = ParseResult()

        for file_path in directory.rglob("*.py"):
            if self.should_parse(file_path):
                file_result = self.parse_file(file_path)
                result.modules.extend(file_result.modules)
                result.dependencies.extend(file_result.dependencies)
                result.errors.extend(file_result.errors)
                result.warnings.extend(file_result.warnings)

        return result

    def _parse_module(self, tree: ast.Module, file_path: Path, source: str) -> ModuleInfo:
        module_name = self._get_module_name(file_path)
        lines = source.split("\n")

        module_info = ModuleInfo(
            name=module_name,
            file_path=file_path,
            docstring=ast.get_docstring(tree),
            line_count=len(lines),
        )

        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.Import):
                module_info.imports.extend(self._parse_import(node))
            elif isinstance(node, ast.ImportFrom):
                module_info.imports.extend(self._parse_import_from(node))
            elif isinstance(node, ast.ClassDef):
                class_info = self._parse_class(node, module_name)
                if self.include_private or class_info.visibility != Visibility.PRIVATE:
                    module_info.classes.append(class_info)
            elif isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
                func_info = self._parse_function(node, module_name)
                if self.include_private or func_info.visibility != Visibility.PRIVATE:
                    module_info.functions.append(func_info)
            elif isinstance(node, ast.Assign):
                for var in self._parse_assignment(node):
                    module_info.variables.append(var)

        return module_info

    def _get_module_name(self, file_path: Path) -> str:
        parts = list(file_path.parts)
        if parts[-1] == "__init__.py":
            parts = parts[:-1]
        else:
            parts[-1] = file_path.stem
        return ".".join(parts)

    def _parse_import(self, node: ast.Import) -> list[ImportInfo]:
        imports = []
        for alias in node.names:
            imports.append(ImportInfo(
                module=alias.name,
                names=[alias.name],
                alias=alias.asname,
                is_from_import=False,
                line=node.lineno,
            ))
        return imports

    def _parse_import_from(self, node: ast.ImportFrom) -> list[ImportInfo]:
        module = node.module or ""
        names = [alias.name for alias in node.names]
        return [ImportInfo(
            module=module,
            names=names,
            is_from_import=True,
            line=node.lineno,
        )]

    def _parse_class(self, node: ast.ClassDef, module_name: str) -> ClassInfo:
        full_name = f"{module_name}.{node.name}"
        visibility = self._get_visibility(node.name)
        bases = [self._get_name(base) for base in node.bases]

        is_abstract = any(
            self._get_name(base) in ("ABC", "ABCMeta")
            for base in node.bases
        )
        is_enum = any(
            self._get_name(base) in ("Enum", "IntEnum", "StrEnum", "Flag", "IntFlag")
            for base in node.bases
        )
        is_dataclass = any(
            decorator.attr == "dataclass"
            if isinstance(decorator, ast.Call) and isinstance(decorator.func, ast.Name)
            else False
            for decorator in node.decorator_list
        )
        is_pydantic = any(
            self._get_name(base) in self.PYDANTIC_BASES
            for base in node.bases
        )
        is_sqlalchemy = any(
            self._get_name(base) in self.SQLALCHEMY_BASES
            for base in node.bases
        )

        class_info = ClassInfo(
            name=node.name,
            full_name=full_name,
            bases=bases,
            visibility=visibility,
            is_abstract=is_abstract,
            is_enum=is_enum,
            is_dataclass=is_dataclass,
            docstring=ast.get_docstring(node),
            decorators=[self._get_decorator_name(d) for d in node.decorator_list],
            line_start=node.lineno,
            line_end=node.end_lineno or node.lineno,
        )

        # 分析框架特性
        class_info = self._analyze_framework_features(
            class_info, node, is_pydantic, is_sqlalchemy
        )

        for item in node.body:
            if isinstance(item, ast.FunctionDef) or isinstance(item, ast.AsyncFunctionDef):
                method = self._parse_function(item, full_name, is_method=True)
                if self.include_private or method.visibility != Visibility.PRIVATE:
                    class_info.methods.append(method)
            elif isinstance(item, ast.Assign):
                for var in self._parse_assignment(item, is_class_var=True):
                    class_info.class_variables.append(var)
            elif isinstance(item, ast.AnnAssign):
                prop = self._parse_annotated_assignment(item)
                if prop:
                    class_info.properties.append(prop)
            elif isinstance(item, ast.ClassDef):
                nested = self._parse_class(item, full_name)
                class_info.nested_classes.append(nested)

        return class_info

    def _parse_function(
        self,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
        module_name: str,
        is_method: bool = False
    ) -> FunctionInfo:
        full_name = f"{module_name}.{node.name}"
        visibility = self._get_visibility(node.name)

        is_async = isinstance(node, ast.AsyncFunctionDef)
        is_classmethod = False
        is_staticmethod = False
        is_abstract = False
        is_fastapi_route = False
        route_info = None

        for decorator in node.decorator_list:
            dec_name = self._get_decorator_name(decorator)
            if dec_name == "classmethod":
                is_classmethod = True
            elif dec_name == "staticmethod":
                is_staticmethod = True
            elif dec_name == "abstractmethod":
                is_abstract = True
            elif self._is_fastapi_decorator(dec_name):
                is_fastapi_route = True
                route_info = self._extract_route_info(decorator, dec_name)

        parameters = self._parse_parameters(node.args)

        return_type = None
        if node.returns:
            return_type = self._get_annotation(node.returns)

        docstring = ast.get_docstring(node)
        description = self._extract_description(docstring)

        func_info = FunctionInfo(
            name=node.name,
            full_name=full_name,
            parameters=parameters,
            return_type=return_type,
            visibility=visibility,
            is_async=is_async,
            is_classmethod=is_classmethod,
            is_staticmethod=is_staticmethod,
            is_abstract=is_abstract,
            description=description,
            docstring=docstring,
            decorators=[self._get_decorator_name(d) for d in node.decorator_list],
            raises=self._extract_raises(docstring),
            line_start=node.lineno,
            line_end=node.end_lineno or node.lineno,
        )

        # 添加 FastAPI 路由信息
        if is_fastapi_route and route_info:
            func_info.docstring = f"FastAPI {route_info}\n{func_info.docstring or ''}".strip()

        return func_info

    def _parse_parameters(self, args: ast.arguments) -> list[ParameterInfo]:
        parameters = []

        for arg in args.posonlyargs:
            parameters.append(ParameterInfo(
                name=arg.arg,
                type_hint=self._get_annotation(arg.annotation),
                kind=ParameterKind.POSITIONAL,
            ))

        for arg in args.args:
            parameters.append(ParameterInfo(
                name=arg.arg,
                type_hint=self._get_annotation(arg.annotation),
                kind=ParameterKind.POSITIONAL_OR_KEYWORD,
            ))

        if args.vararg:
            parameters.append(ParameterInfo(
                name=args.vararg.arg,
                type_hint=self._get_annotation(args.vararg.annotation),
                kind=ParameterKind.VAR_POSITIONAL,
            ))

        for arg in args.kwonlyargs:
            parameters.append(ParameterInfo(
                name=arg.arg,
                type_hint=self._get_annotation(arg.annotation),
                kind=ParameterKind.KEYWORD_ONLY,
            ))

        if args.kwarg:
            parameters.append(ParameterInfo(
                name=args.kwarg.arg,
                type_hint=self._get_annotation(args.kwarg.annotation),
                kind=ParameterKind.VAR_KEYWORD,
            ))

        defaults = args.defaults
        if defaults:
            num_defaults = len(defaults)
            num_args = len(args.args)
            for i, default in enumerate(defaults):
                arg_index = num_args - num_defaults + i
                if arg_index < len(parameters):
                    parameters[arg_index].default_value = self._get_value(default)

        return parameters

    def _parse_assignment(
        self,
        node: ast.Assign,
        is_class_var: bool = False
    ) -> list[PropertyInfo]:
        properties = []
        for target in node.targets:
            if isinstance(target, ast.Name):
                name = target.id
                visibility = self._get_visibility(name)
                properties.append(PropertyInfo(
                    name=name,
                    visibility=visibility,
                ))
        return properties

    def _parse_annotated_assignment(self, node: ast.AnnAssign) -> Optional[PropertyInfo]:
        if not isinstance(node.target, ast.Name):
            return None

        name = node.target.id
        visibility = self._get_visibility(name)
        type_hint = self._get_annotation(node.annotation)
        is_readonly = node.value is None

        return PropertyInfo(
            name=name,
            type_hint=type_hint,
            visibility=visibility,
            is_readonly=is_readonly,
        )

    def _get_visibility(self, name: str) -> Visibility:
        if name.startswith("__") and not name.endswith("__"):
            return Visibility.PRIVATE
        elif name.startswith("_"):
            return Visibility.PROTECTED
        return Visibility.PUBLIC

    def _get_name(self, node: ast.AST) -> str:
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return f"{self._get_name(node.value)}.{node.attr}"
        elif isinstance(node, ast.Constant):
            return str(node.value)
        return ""

    def _get_annotation(self, node: Optional[ast.AST]) -> Optional[str]:
        if node is None:
            return None
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Constant):
            return str(node.value)
        elif isinstance(node, ast.Attribute):
            return self._get_name(node)
        elif isinstance(node, ast.Subscript):
            base = self._get_annotation(node.value)
            slice_val = self._get_annotation(node.slice)
            return f"{base}[{slice_val}]"
        elif isinstance(node, ast.Tuple):
            elements = [self._get_annotation(e) for e in node.elts]
            return ", ".join(e for e in elements if e)
        return None

    def _get_value(self, node: ast.AST) -> str:
        if isinstance(node, ast.Constant):
            return repr(node.value)
        elif isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.List):
            elements = [self._get_value(e) for e in node.elts]
            return f"[{', '.join(elements)}]"
        elif isinstance(node, ast.Dict):
            items = [f"{self._get_value(k)}: {self._get_value(v)}" for k, v in zip(node.keys, node.values)]
            return f"{{{', '.join(items)}}}"
        return "..."

    def _get_decorator_name(self, node: ast.AST) -> str:
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return self._get_name(node)
        elif isinstance(node, ast.Call):
            return self._get_decorator_name(node.func)
        return ""

    def _extract_description(self, docstring: Optional[str]) -> Optional[str]:
        if not docstring:
            return None
        lines = docstring.strip().split("\n")
        for line in lines:
            stripped = line.strip()
            if stripped and not stripped.startswith(":") and not stripped.startswith("@"):
                return stripped
        return None

    def _extract_raises(self, docstring: Optional[str]) -> list[str]:
        if not docstring:
            return []
        raises = []
        pattern = r":raises?\s+(\w+)"
        matches = re.findall(pattern, docstring)
        raises.extend(matches)
        return raises

    def _analyze_framework_features(
        self,
        class_info: ClassInfo,
        node: ast.ClassDef,
        is_pydantic: bool,
        is_sqlalchemy: bool
    ) -> ClassInfo:
        """分析 Python 框架特性"""
        framework_info = []

        # Pydantic 模型
        if is_pydantic:
            framework_info.append("Pydantic Model")
            # 检查是否使用 Field
            has_field = any(
                isinstance(item, ast.AnnAssign) and
                item.value and
                isinstance(item.value, ast.Call) and
                isinstance(item.value.func, ast.Name) and
                item.value.func.id == "Field"
                for item in node.body
            )
            if has_field:
                framework_info.append("使用 Field 验证")

        # SQLAlchemy 模型
        if is_sqlalchemy:
            framework_info.append("SQLAlchemy Model")
            # 检查是否有 __tablename__
            has_tablename = any(
                isinstance(item, ast.Assign) and
                any(isinstance(t, ast.Name) and t.id == "__tablename__" for t in item.targets)
                for item in node.body
            )
            if has_tablename:
                framework_info.append("自定义表名")

        if framework_info:
            existing_doc = class_info.docstring or ""
            class_info.docstring = f"{' | '.join(framework_info)}\n{existing_doc}".strip()

        return class_info

    def _is_fastapi_decorator(self, decorator_name: str) -> bool:
        """检查是否为 FastAPI 路由装饰器"""
        parts = decorator_name.split(".")
        base_name = parts[-1] if parts else decorator_name
        return base_name.lower() in self.FASTAPI_METHODS or base_name in self.FASTAPI_DECORATORS

    def _extract_route_info(self, decorator: ast.AST, decorator_name: str) -> Optional[str]:
        """提取 FastAPI 路由信息"""
        parts = decorator_name.split(".")
        method = parts[-1].upper() if parts else "GET"

        path = "/"
        if isinstance(decorator, ast.Call) and decorator.args:
            # 第一个参数通常是路径
            first_arg = decorator.args[0]
            if isinstance(first_arg, ast.Constant) and isinstance(first_arg.value, str):
                path = first_arg.value

        return f"[{method}] {path}"

    def _extract_dependencies(self, module_info: ModuleInfo) -> list[DependencyInfo]:
        dependencies = []

        for imp in module_info.imports:
            if imp.is_from_import:
                for name in imp.names:
                    dependencies.append(DependencyInfo(
                        source=module_info.name,
                        target=f"{imp.module}.{name}" if imp.module else name,
                        dependency_type="import",
                        line=imp.line,
                    ))
            else:
                for name in imp.names:
                    dependencies.append(DependencyInfo(
                        source=module_info.name,
                        target=name,
                        dependency_type="import",
                        line=imp.line,
                    ))

        return dependencies
