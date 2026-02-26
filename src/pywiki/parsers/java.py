"""
Java 代码解析器
支持 Spring Boot / Spring MVC / MyBatis Plus 技术栈
"""

from pathlib import Path
from typing import Optional

from tree_sitter import Language, Parser, Tree

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


def _get_java_language():
    """获取 tree-sitter Java 语言实例"""
    try:
        import tree_sitter_java as ts_java

        JAVA_LANGUAGE = Language(ts_java.language())
        return JAVA_LANGUAGE
    except ImportError:
        return None


class JavaParser(BaseParser):
    """Java 解析器，支持 Spring 和 MyBatis Plus"""

    # Spring 相关注解
    SPRING_CONTROLLERS = {
        "Controller", "RestController", "RequestMapping",
        "GetMapping", "PostMapping", "PutMapping", "DeleteMapping",
        "PatchMapping"
    }
    SPRING_SERVICES = {"Service", "Component", "Repository"}
    SPRING_INJECTION = {"Autowired", "Inject", "Resource"}
    SPRING_CONFIG = {"Configuration", "Bean", "Value", "Profile"}

    # MyBatis Plus 相关注解
    MYBATIS_PLUS = {"TableName", "TableId", "TableField", "Version", "LogicDelete"}
    MYBATIS_MAPPER = {"Mapper", "Select", "Insert", "Update", "Delete"}

    def __init__(
        self,
        exclude_patterns: Optional[list[str]] = None,
        include_private: bool = False,
    ):
        super().__init__(exclude_patterns, include_private)
        self._java_lang = _get_java_language()
        self._parser = None
        if self._java_lang:
            self._parser = Parser(self._java_lang)

    def get_supported_extensions(self) -> list[str]:
        return [".java"]

    def parse_file(self, file_path: Path) -> ParseResult:
        result = ParseResult()

        try:
            source = file_path.read_text(encoding="utf-8")
            tree = self._parser.parse(bytes(source, "utf-8"))
            module_info = self._parse_module(tree, source, file_path)

            if module_info:
                result.modules.append(module_info)
                dependencies = self._extract_dependencies(module_info)
                result.dependencies.extend(dependencies)

        except Exception as e:
            result.errors.append(f"Error parsing {file_path}: {e}")

        return result

    def parse_directory(self, directory: Path) -> ParseResult:
        result = ParseResult()

        for file_path in directory.rglob("*.java"):
            if self.should_parse(file_path):
                file_result = self.parse_file(file_path)
                result.modules.extend(file_result.modules)
                result.dependencies.extend(file_result.dependencies)
                result.errors.extend(file_result.errors)
                result.warnings.extend(file_result.warnings)

        return result

    def _parse_module(
        self,
        tree: Tree,
        source: str,
        file_path: Path
    ) -> ModuleInfo:
        """解析 Java 文件模块"""
        module_name = self._get_module_name(file_path)
        lines = source.split("\n")

        module_info = ModuleInfo(
            name=module_name,
            file_path=file_path,
            line_count=len(lines),
        )

        root = tree.root_node

        for child in root.children:
            if child.type == "package_declaration":
                package_name = self._extract_package_name(child, source)
                module_info.name = f"{package_name}.{module_name}"
            elif child.type == "import_declaration":
                module_info.imports.extend(self._parse_import(child, source))
            elif child.type == "class_declaration":
                class_info = self._parse_class(child, source, module_info.name)
                if self.include_private or class_info.visibility != Visibility.PRIVATE:
                    module_info.classes.append(class_info)
            elif child.type == "interface_declaration":
                class_info = self._parse_interface(child, source, module_info.name)
                if self.include_private or class_info.visibility != Visibility.PRIVATE:
                    module_info.classes.append(class_info)
            elif child.type == "enum_declaration":
                class_info = self._parse_enum(child, source, module_info.name)
                if self.include_private or class_info.visibility != Visibility.PRIVATE:
                    module_info.classes.append(class_info)
            elif child.type == "annotation_type_declaration":
                class_info = self._parse_annotation(child, source, module_info.name)
                if self.include_private or class_info.visibility != Visibility.PRIVATE:
                    module_info.classes.append(class_info)

        return module_info

    def _get_module_name(self, file_path: Path) -> str:
        """获取模块名称"""
        return file_path.stem

    def _get_node_text(self, node, source: str) -> str:
        """获取节点文本"""
        return source[node.start_byte:node.end_byte]

    def _extract_package_name(self, node, source: str) -> str:
        """提取包名"""
        for child in node.children:
            if child.type == "scoped_identifier" or child.type == "identifier":
                return self._get_node_text(child, source)
        return ""

    def _parse_import(self, node, source: str) -> list[ImportInfo]:
        """解析 import 语句"""
        imports = []

        module = ""
        is_static = False
        is_wildcard = False

        for child in node.children:
            if child.type == "static":
                is_static = True
            elif child.type == "asterisk":
                is_wildcard = True
            elif child.type == "scoped_identifier" or child.type == "identifier":
                module = self._get_node_text(child, source)

        if module:
            imports.append(ImportInfo(
                module=module,
                names=["*" if is_wildcard else module],
                is_from_import=True,
                line=node.start_point[0] + 1,
            ))

        return imports

    def _parse_class(self, node, source: str, package_name: str) -> ClassInfo:
        """解析类声明"""
        name = ""
        bases = []
        annotations = []
        visibility = Visibility.PUBLIC
        is_abstract = False

        for child in node.children:
            if child.type == "modifiers":
                mods, anns = self._parse_modifiers(child, source)
                visibility = self._get_visibility_from_modifiers(mods)
                is_abstract = "abstract" in mods
                annotations = anns
            elif child.type == "identifier":
                name = self._get_node_text(child, source)
            elif child.type == "superclass":
                # extends
                for super_child in child.children:
                    if super_child.type == "type_identifier":
                        bases.append(self._get_node_text(super_child, source))
            elif child.type == "super_interfaces":
                # implements
                for iface_child in child.children:
                    if iface_child.type == "type_identifier":
                        bases.append(self._get_node_text(iface_child, source))
                    elif iface_child.type == "interface_type_list":
                        for type_node in iface_child.children:
                            if type_node.type == "type_identifier":
                                bases.append(self._get_node_text(type_node, source))

        full_name = f"{package_name}.{name}" if package_name else name

        class_info = ClassInfo(
            name=name,
            full_name=full_name,
            bases=bases,
            visibility=visibility,
            is_abstract=is_abstract,
            docstring=self._extract_javadoc(node, source),
            line_start=node.start_point[0] + 1,
            line_end=node.end_point[0] + 1,
        )

        # 解析类体
        for child in node.children:
            if child.type == "class_body":
                for member in child.children:
                    if member.type == "method_declaration":
                        method = self._parse_method(member, source, full_name)
                        if self.include_private or method.visibility != Visibility.PRIVATE:
                            class_info.methods.append(method)
                    elif member.type == "constructor_declaration":
                        method = self._parse_constructor(member, source, full_name)
                        if self.include_private or method.visibility != Visibility.PRIVATE:
                            class_info.methods.append(method)
                    elif member.type == "field_declaration":
                        fields = self._parse_field(member, source)
                        for field in fields:
                            class_info.class_variables.append(field)
                    elif member.type == "class_declaration":
                        # 嵌套类
                        nested = self._parse_class(member, source, full_name)
                        class_info.nested_classes.append(nested)

        # 分析 Spring/MyBatis 特性
        class_info = self._analyze_spring_features(class_info, annotations, source)

        return class_info

    def _parse_interface(self, node, source: str, package_name: str) -> ClassInfo:
        """解析接口声明"""
        name = ""
        bases = []
        annotations = []
        visibility = Visibility.PUBLIC

        for child in node.children:
            if child.type == "modifiers":
                mods, anns = self._parse_modifiers(child, source)
                visibility = self._get_visibility_from_modifiers(mods)
                annotations = anns
            elif child.type == "identifier":
                name = self._get_node_text(child, source)
            elif child.type == "extends_interfaces":
                for ext_child in child.children:
                    if ext_child.type == "type_identifier":
                        bases.append(self._get_node_text(ext_child, source))
                    elif ext_child.type == "interface_type_list":
                        for type_node in ext_child.children:
                            if type_node.type == "type_identifier":
                                bases.append(self._get_node_text(type_node, source))

        full_name = f"{package_name}.{name}" if package_name else name

        class_info = ClassInfo(
            name=name,
            full_name=full_name,
            bases=bases,
            visibility=visibility,
            docstring=f"Interface\n{self._extract_javadoc(node, source) or ''}".strip(),
            line_start=node.start_point[0] + 1,
            line_end=node.end_point[0] + 1,
        )

        # 解析接口体
        for child in node.children:
            if child.type == "interface_body":
                for member in child.children:
                    if member.type == "method_declaration":
                        method = self._parse_method(member, source, full_name)
                        if self.include_private or method.visibility != Visibility.PRIVATE:
                            class_info.methods.append(method)
                    elif member.type == "constant_declaration":
                        fields = self._parse_field(member, source)
                        for field in fields:
                            class_info.class_variables.append(field)

        # 分析是否为 MyBatis Mapper
        class_info = self._analyze_mybatis_mapper(class_info, annotations)

        return class_info

    def _parse_enum(self, node, source: str, package_name: str) -> ClassInfo:
        """解析枚举声明"""
        name = ""
        annotations = []
        visibility = Visibility.PUBLIC

        for child in node.children:
            if child.type == "modifiers":
                mods, anns = self._parse_modifiers(child, source)
                visibility = self._get_visibility_from_modifiers(mods)
                annotations = anns
            elif child.type == "identifier":
                name = self._get_node_text(child, source)

        full_name = f"{package_name}.{name}" if package_name else name

        class_info = ClassInfo(
            name=name,
            full_name=full_name,
            visibility=visibility,
            is_enum=True,
            docstring=f"Enum\n{self._extract_javadoc(node, source) or ''}".strip(),
            line_start=node.start_point[0] + 1,
            line_end=node.end_point[0] + 1,
        )

        # 解析枚举常量
        for child in node.children:
            if child.type == "enum_body":
                for enum_const in child.children:
                    if enum_const.type == "enum_constant":
                        const_name = ""
                        for const_child in enum_const.children:
                            if const_child.type == "identifier":
                                const_name = self._get_node_text(const_child, source)
                        if const_name:
                            class_info.class_variables.append(PropertyInfo(
                                name=const_name,
                                visibility=Visibility.PUBLIC,
                            ))

        return class_info

    def _parse_annotation(self, node, source: str, package_name: str) -> ClassInfo:
        """解析注解声明"""
        name = ""
        visibility = Visibility.PUBLIC

        for child in node.children:
            if child.type == "modifiers":
                mods, _ = self._parse_modifiers(child, source)
                visibility = self._get_visibility_from_modifiers(mods)
            elif child.type == "identifier":
                name = self._get_node_text(child, source)

        full_name = f"{package_name}.{name}" if package_name else name

        return ClassInfo(
            name=name,
            full_name=full_name,
            visibility=visibility,
            docstring=f"Annotation\n{self._extract_javadoc(node, source) or ''}".strip(),
            line_start=node.start_point[0] + 1,
            line_end=node.end_point[0] + 1,
        )

    def _parse_modifiers(self, node, source: str) -> tuple[list[str], list[str]]:
        """解析修饰符和注解"""
        modifiers = []
        annotations = []

        for child in node.children:
            if child.type in ("public", "private", "protected", "static", "final",
                             "abstract", "synchronized", "volatile", "transient",
                             "native", "strictfp"):
                modifiers.append(child.type)
            elif child.type == "annotation":
                ann_name = self._parse_annotation_name(child, source)
                if ann_name:
                    annotations.append(ann_name)

        return modifiers, annotations

    def _parse_annotation_name(self, node, source: str) -> str:
        """解析注解名称"""
        for child in node.children:
            if child.type == "identifier" or child.type == "type_identifier":
                return self._get_node_text(child, source)
        return ""

    def _get_visibility_from_modifiers(self, modifiers: list[str]) -> Visibility:
        """从修饰符获取可见性"""
        if "private" in modifiers:
            return Visibility.PRIVATE
        elif "protected" in modifiers:
            return Visibility.PROTECTED
        return Visibility.PUBLIC

    def _parse_method(self, node, source: str, class_name: str) -> FunctionInfo:
        """解析方法声明"""
        name = ""
        visibility = Visibility.PUBLIC
        is_static = False
        is_abstract = False
        annotations = []

        for child in node.children:
            if child.type == "modifiers":
                mods, anns = self._parse_modifiers(child, source)
                visibility = self._get_visibility_from_modifiers(mods)
                is_static = "static" in mods
                is_abstract = "abstract" in mods
                annotations = anns
            elif child.type == "identifier":
                name = self._get_node_text(child, source)

        full_name = f"{class_name}.{name}"

        parameters = []
        return_type = None

        for child in node.children:
            if child.type == "formal_parameters":
                parameters = self._parse_parameters(child, source)
            elif child.type == "type_identifier" or child.type == "scoped_type_identifier":
                return_type = self._get_node_text(child, source)

        func_info = FunctionInfo(
            name=name,
            full_name=full_name,
            parameters=parameters,
            return_type=return_type,
            visibility=visibility,
            is_staticmethod=is_static,
            is_abstract=is_abstract,
            docstring=self._extract_javadoc(node, source),
            line_start=node.start_point[0] + 1,
            line_end=node.end_point[0] + 1,
        )

        # 分析 Spring/MyBatis 方法特性
        func_info = self._analyze_method_features(func_info, annotations, source)

        return func_info

    def _parse_constructor(self, node, source: str, class_name: str) -> FunctionInfo:
        """解析构造方法"""
        name = "<init>"
        visibility = Visibility.PUBLIC

        for child in node.children:
            if child.type == "modifiers":
                mods, _ = self._parse_modifiers(child, source)
                visibility = self._get_visibility_from_modifiers(mods)

        full_name = f"{class_name}.{name}"

        parameters = []

        for child in node.children:
            if child.type == "formal_parameters":
                parameters = self._parse_parameters(child, source)

        return FunctionInfo(
            name=name,
            full_name=full_name,
            parameters=parameters,
            return_type=None,
            visibility=visibility,
            docstring=self._extract_javadoc(node, source),
            line_start=node.start_point[0] + 1,
            line_end=node.end_point[0] + 1,
        )

    def _parse_parameters(self, node, source: str) -> list[ParameterInfo]:
        """解析方法参数"""
        parameters = []

        for child in node.children:
            if child.type == "formal_parameter":
                param_info = self._parse_parameter(child, source)
                if param_info:
                    parameters.append(param_info)

        return parameters

    def _parse_parameter(self, node, source: str) -> Optional[ParameterInfo]:
        """解析单个参数"""
        name = ""
        type_hint = None
        annotations = []

        for child in node.children:
            if child.type == "identifier":
                name = self._get_node_text(child, source)
            elif child.type == "type_identifier" or child.type == "scoped_type_identifier":
                type_hint = self._get_node_text(child, source)
            elif child.type == "annotation":
                ann_name = self._parse_annotation_name(child, source)
                if ann_name:
                    annotations.append(ann_name)

        if name:
            param_info = ParameterInfo(
                name=name,
                type_hint=type_hint,
                kind=ParameterKind.POSITIONAL_OR_KEYWORD,
            )
            # 添加参数注解信息
            if annotations:
                param_info.description = f"Annotations: {', '.join(annotations)}"
            return param_info
        return None

    def _parse_field(self, node, source: str) -> list[PropertyInfo]:
        """解析字段声明"""
        fields = []
        type_hint = None
        visibility = Visibility.PACKAGE
        is_static = False
        is_final = False

        for child in node.children:
            if child.type == "modifiers":
                mods, _ = self._parse_modifiers(child, source)
                visibility = self._get_visibility_from_modifiers(mods)
                is_static = "static" in mods
                is_final = "final" in mods
            elif child.type == "type_identifier" or child.type == "scoped_type_identifier":
                type_hint = self._get_node_text(child, source)
            elif child.type == "variable_declarator":
                for var_child in child.children:
                    if var_child.type == "identifier":
                        name = self._get_node_text(var_child, source)
                        fields.append(PropertyInfo(
                            name=name,
                            type_hint=type_hint,
                            visibility=visibility,
                            is_readonly=is_final,
                        ))

        return fields

    def _analyze_spring_features(
        self,
        class_info: ClassInfo,
        annotations: list[str],
        source: str
    ) -> ClassInfo:
        """分析 Spring 框架特性"""
        spring_info = []

        # 检查 Controller
        if any(ann in self.SPRING_CONTROLLERS for ann in annotations):
            spring_info.append("Spring Controller")
            # 提取路由映射
            route = self._extract_route_mapping(source, annotations)
            if route:
                spring_info.append(f"Route: {route}")

        # 检查 Service
        if any(ann in self.SPRING_SERVICES for ann in annotations):
            spring_info.append("Spring Service")

        # 检查 Configuration
        if any(ann in self.SPRING_CONFIG for ann in annotations):
            spring_info.append("Spring Configuration")

        # 检查 MyBatis Plus Entity
        if any(ann in self.MYBATIS_PLUS for ann in annotations):
            spring_info.append("MyBatis Plus Entity")
            table_name = self._extract_table_name(source)
            if table_name:
                spring_info.append(f"Table: {table_name}")

        if spring_info:
            existing_doc = class_info.docstring or ""
            class_info.docstring = f"{' | '.join(spring_info)}\n{existing_doc}".strip()

        return class_info

    def _analyze_mybatis_mapper(
        self,
        class_info: ClassInfo,
        annotations: list[str]
    ) -> ClassInfo:
        """分析 MyBatis Mapper 接口"""
        if "Mapper" in annotations:
            existing_doc = class_info.docstring or ""
            class_info.docstring = f"MyBatis Mapper\n{existing_doc}".strip()

        return class_info

    def _analyze_method_features(
        self,
        func_info: FunctionInfo,
        annotations: list[str],
        source: str
    ) -> FunctionInfo:
        """分析方法特性"""
        method_info = []

        # 检查 Spring 路由映射
        route_annotations = self.SPRING_CONTROLLERS & set(annotations)
        if route_annotations:
            route = self._extract_route_mapping(source, annotations)
            if route:
                method_info.append(f"Route: {route}")

        # 检查依赖注入
        injection_annotations = self.SPRING_INJECTION & set(annotations)
        if injection_annotations:
            func_info.description = f"依赖注入: {', '.join(injection_annotations)}"

        # 检查 MyBatis SQL 注解
        sql_annotations = self.MYBATIS_MAPPER & set(annotations)
        if sql_annotations:
            func_info.description = f"MyBatis SQL: {', '.join(sql_annotations)}"

        if method_info:
            existing_doc = func_info.docstring or ""
            func_info.docstring = f"{' | '.join(method_info)}\n{existing_doc}".strip()

        return func_info

    def _extract_route_mapping(self, source: str, annotations: list[str]) -> Optional[str]:
        """提取路由映射信息"""
        # 简化实现，从源码中提取路由路径
        import re

        for ann in annotations:
            if ann in ("RequestMapping", "GetMapping", "PostMapping", "PutMapping", "DeleteMapping"):
                # 查找注解中的路径
                pattern = rf'@{ann}\s*\(\s*["\']([^"\']+)["\']\s*\)'
                match = re.search(pattern, source)
                if match:
                    return match.group(1)

        return None

    def _extract_table_name(self, source: str) -> Optional[str]:
        """提取 MyBatis Plus 表名"""
        import re

        pattern = r'@TableName\s*\(\s*["\']([^"\']+)["\']\s*\)'
        match = re.search(pattern, source)
        if match:
            return match.group(1)

        return None

    def _extract_javadoc(self, node, source: str) -> Optional[str]:
        """提取 Javadoc 注释"""
        line_start = node.start_point[0]
        lines = source.split("\n")

        # 查找节点前的 Javadoc 注释
        comments = []
        in_javadoc = False

        for i in range(line_start - 1, -1, -1):
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

    def _extract_dependencies(self, module_info: ModuleInfo) -> list[DependencyInfo]:
        """提取依赖关系"""
        dependencies = []

        for imp in module_info.imports:
            dependencies.append(DependencyInfo(
                source=module_info.name,
                target=imp.module,
                dependency_type="import",
                line=imp.line,
            ))

        return dependencies
