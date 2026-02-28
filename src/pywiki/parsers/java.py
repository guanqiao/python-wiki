"""
Java 代码解析器
支持 Spring Boot / Spring MVC / MyBatis Plus / Dubbo / Validation 技术栈
"""

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

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


@dataclass
class AnnotationInfo:
    """注解信息"""
    name: str
    attributes: dict[str, Any] = field(default_factory=dict)
    raw_text: str = ""


@dataclass
class SpringEndpointInfo:
    """Spring端点信息"""
    path: str = ""
    method: str = "GET"
    consumes: list[str] = field(default_factory=list)
    produces: list[str] = field(default_factory=list)
    params: list[str] = field(default_factory=list)
    headers: list[str] = field(default_factory=list)


@dataclass
class JpaColumnInfo:
    """JPA列信息"""
    name: Optional[str] = None
    nullable: bool = True
    unique: bool = False
    length: Optional[int] = None
    precision: Optional[int] = None
    scale: Optional[int] = None
    column_definition: Optional[str] = None


@dataclass
class JavaDocTag:
    """JavaDoc标签信息"""
    name: str
    value: str = ""
    description: str = ""


@dataclass
class JavaDocInfo:
    """JavaDoc完整信息"""
    description: str = ""
    tags: list[JavaDocTag] = field(default_factory=list)
    params: dict[str, str] = field(default_factory=dict)
    returns: str = ""
    throws: list[tuple[str, str]] = field(default_factory=list)
    see_also: list[str] = field(default_factory=list)
    since: Optional[str] = None
    deprecated: bool = False
    author: Optional[str] = None
    version: Optional[str] = None


@dataclass
class GenericTypeInfo:
    """泛型类型信息"""
    name: str = ""
    bounds: list[str] = field(default_factory=list)
    is_wildcard: bool = False
    wildcard_bound: Optional[str] = None
    wildcard_type: Optional[str] = None  # extends, super
    type_arguments: list[Any] = field(default_factory=list)


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

    SPRING_CONTROLLERS = {
        "Controller", "RestController", "RequestMapping",
        "GetMapping", "PostMapping", "PutMapping", "DeleteMapping",
        "PatchMapping"
    }
    SPRING_SERVICES = {"Service", "Component", "Repository"}
    SPRING_INJECTION = {"Autowired", "Inject", "Resource"}
    SPRING_CONFIG = {"Configuration", "Bean", "Value", "Profile", "ConditionalOnProperty", "ConditionalOnClass", "ConditionalOnBean"}
    SPRING_SECURITY = {"PreAuthorize", "PostAuthorize", "Secured", "RolesAllowed", "PermitAll", "DenyAll"}
    SPRING_PARAMS = {"RequestParam", "PathVariable", "RequestBody", "RequestHeader", "CookieValue", "MatrixVariable", "RequestPart"}
    SPRING_TRANSACTIONAL = {"Transactional"}
    SPRING_CACHE = {"Cacheable", "CacheEvict", "CachePut", "Caching", "CacheConfig"}
    SPRING_ASYNC = {"Async", "EventListener", "TransactionalEventListener"}
    SPRING_RETRY = {"Retryable", "Recover", "Backoff"}

    MYBATIS_PLUS = {"TableName", "TableId", "TableField", "Version", "LogicDelete"}
    MYBATIS_MAPPER = {"Mapper", "Select", "Insert", "Update", "Delete"}

    LOMBOK = {"Data", "Getter", "Setter", "Builder", "NoArgsConstructor",
              "AllArgsConstructor", "RequiredArgsConstructor", "ToString", "EqualsAndHashCode",
              "Slf4j", "Log4j2", "FieldNameConstants", "With", "Singular", "Builder.Default"}

    JPA_ENTITY = {"Entity", "Table", "Column", "Id", "GeneratedValue", "SequenceGenerator",
                  "Temporal", "Enumerated", "Lob", "Transient", "Version"}
    JPA_RELATIONSHIP = {"OneToOne", "OneToMany", "ManyToOne", "ManyToMany", "JoinColumn", "JoinTable"}
    JPA_INDEX = {"Index", "UniqueConstraint"}
    JPA_ID = {"IdClass", "EmbeddedId", "Embedded"}

    DUBBO = {"DubboService", "DubboReference", "Service", "Reference", "DubboComponent"}
    
    VALIDATION = {"NotNull", "NotEmpty", "NotBlank", "Null", "AssertTrue", "AssertFalse",
                  "Min", "Max", "DecimalMin", "DecimalMax", "Size", "Digits",
                  "Past", "PastOrPresent", "Future", "FutureOrPresent",
                  "Pattern", "Email", "Valid", "Positive", "PositiveOrZero", "Negative", "NegativeOrZero"}
    
    QUARTZ = {"Scheduled", "Schedules", "DisallowConcurrentExecution", "PersistJobDataAfterExecution"}
    
    FEIGN = {"FeignClient", "RequestMapping", "GetMapping", "PostMapping", "PutMapping", "DeleteMapping", "PatchMapping"}
    
    MAPSTRUCT = {"Mapper", "Mapping", "Mappings", "InheritInverseConfiguration", "BeanMapping"}

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
            elif child.type == "record_declaration":
                class_info = self._parse_record(child, source, module_info.name)
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
                for super_child in child.children:
                    if super_child.type == "type_identifier":
                        bases.append(self._get_node_text(super_child, source))
            elif child.type == "super_interfaces":
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
                        nested = self._parse_class(member, source, full_name)
                        class_info.nested_classes.append(nested)

        class_info = self._analyze_spring_features(class_info, annotations, source)
        class_info = self._analyze_lombok_features(class_info, annotations)
        class_info = self._analyze_jpa_features(class_info, annotations, source)
        class_info = self._analyze_dubbo_features(class_info, annotations, source)
        class_info = self._analyze_validation_features(class_info, annotations, source)
        class_info = self._analyze_feign_features(class_info, annotations, source)
        class_info = self._analyze_transactional_features(class_info, annotations, source)
        class_info = self._analyze_cache_features(class_info, annotations, source)
        class_info = self._analyze_async_features(class_info, annotations, source)
        class_info = self._analyze_mapstruct_features(class_info, annotations, source)

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

        class_info = self._analyze_mybatis_mapper(class_info, annotations)
        class_info = self._analyze_feign_features(class_info, annotations, source)
        class_info = self._analyze_dubbo_features(class_info, annotations, source)
        class_info = self._analyze_transactional_features(class_info, annotations, source)
        class_info = self._analyze_cache_features(class_info, annotations, source)
        class_info = self._analyze_mapstruct_features(class_info, annotations, source)

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
            elif child.type in ("annotation", "marker_annotation"):
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
            elif child.type == "generic_type":
                type_hint = self._parse_generic_type(child, source)
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
            if annotations:
                param_info.description = f"Annotations: {', '.join(annotations)}"
            return param_info
        return None

    def _parse_generic_type(self, node, source: str) -> str:
        """解析泛型类型，返回完整类型字符串"""
        result = []
        
        for child in node.children:
            if child.type == "type_identifier":
                result.append(self._get_node_text(child, source))
            elif child.type == "scoped_type_identifier":
                result.append(self._get_node_text(child, source))
            elif child.type == "type_arguments":
                args = self._parse_type_arguments(child, source)
                result.append(f"<{args}>")
            elif child.type == "generic_type":
                result.append(self._parse_generic_type(child, source))
        
        return "".join(result) if result else ""

    def _parse_type_arguments(self, node, source: str) -> str:
        """解析类型参数列表"""
        args = []
        
        for child in node.children:
            if child.type == "type_identifier":
                args.append(self._get_node_text(child, source))
            elif child.type == "scoped_type_identifier":
                args.append(self._get_node_text(child, source))
            elif child.type == "generic_type":
                args.append(self._parse_generic_type(child, source))
            elif child.type == "wildcard":
                args.append(self._parse_wildcard(child, source))
        
        return ", ".join(args)

    def _parse_wildcard(self, node, source: str) -> str:
        """解析通配符类型"""
        result = "?"
        
        for child in node.children:
            if child.type == "extends":
                bound_type = self._get_next_type(child, source)
                if bound_type:
                    result = f"? extends {bound_type}"
            elif child.type == "super":
                bound_type = self._get_next_type(child, source)
                if bound_type:
                    result = f"? super {bound_type}"
        
        return result

    def _get_next_type(self, node, source: str) -> Optional[str]:
        """获取节点后面的类型"""
        parent = node.parent
        if parent:
            found = False
            for child in parent.children:
                if found:
                    if child.type in ("type_identifier", "scoped_type_identifier"):
                        return self._get_node_text(child, source)
                    elif child.type == "generic_type":
                        return self._parse_generic_type(child, source)
                if child == node:
                    found = True
        return None

    def _parse_type_parameter(self, node, source: str) -> GenericTypeInfo:
        """解析类型参数（泛型定义）"""
        info = GenericTypeInfo()
        
        for child in node.children:
            if child.type == "type_identifier":
                info.name = self._get_node_text(child, source)
            elif child.type == "type_bound":
                for bound_child in child.children:
                    if bound_child.type in ("type_identifier", "scoped_type_identifier"):
                        info.bounds.append(self._get_node_text(bound_child, source))
        
        return info

    def _parse_field(self, node, source: str) -> list[PropertyInfo]:
        """解析字段声明"""
        fields = []
        type_hint = None
        visibility = Visibility.PACKAGE
        is_static = False
        is_final = False
        field_annotations = []

        for child in node.children:
            if child.type == "modifiers":
                mods, anns = self._parse_modifiers(child, source)
                visibility = self._get_visibility_from_modifiers(mods)
                is_static = "static" in mods
                is_final = "final" in mods
                field_annotations = anns
            elif child.type == "type_identifier" or child.type == "scoped_type_identifier":
                type_hint = self._get_node_text(child, source)
            elif child.type == "variable_declarator":
                for var_child in child.children:
                    if var_child.type == "identifier":
                        name = self._get_node_text(var_child, source)
                        prop = PropertyInfo(
                            name=name,
                            type_hint=type_hint,
                            visibility=visibility,
                            is_readonly=is_final,
                            decorators=field_annotations,
                        )
                        fields.append(prop)

        return fields

    def _parse_record(self, node, source: str, package_name: str) -> ClassInfo:
        """解析 Java 14+ Record"""
        name = ""
        visibility = Visibility.PUBLIC
        annotations = []

        for child in node.children:
            if child.type == "modifiers":
                mods, anns = self._parse_modifiers(child, source)
                visibility = self._get_visibility_from_modifiers(mods)
                annotations = anns
            elif child.type == "identifier":
                name = self._get_node_text(child, source)

        full_name = f"{package_name}.{name}" if package_name else name

        record_info = ClassInfo(
            name=name,
            full_name=full_name,
            visibility=visibility,
            docstring=f"Java Record\n{self._extract_javadoc(node, source) or ''}".strip(),
            line_start=node.start_point[0] + 1,
            line_end=node.end_point[0] + 1,
        )

        for child in node.children:
            if child.type == "formal_parameters":
                for param in child.children:
                    if param.type == "formal_parameter":
                        param_info = self._parse_parameter(param, source)
                        if param_info:
                            record_info.class_variables.append(PropertyInfo(
                                name=param_info.name,
                                type_hint=param_info.type_hint,
                                visibility=Visibility.PRIVATE,
                                is_readonly=True,
                            ))

        record_info = self._analyze_lombok_features(record_info, annotations)

        return record_info

    def _analyze_spring_features(
        self,
        class_info: ClassInfo,
        annotations: list[str],
        source: str
    ) -> ClassInfo:
        """分析 Spring 框架特性"""
        spring_info = []

        if any(ann in self.SPRING_CONTROLLERS for ann in annotations):
            spring_info.append("Spring Controller")
            endpoint = self._extract_spring_endpoint_info(source, annotations)
            if endpoint:
                spring_info.append(f"Route: {endpoint.path}")
                if endpoint.method != "GET":
                    spring_info.append(f"Method: {endpoint.method}")
                if endpoint.consumes:
                    spring_info.append(f"Consumes: {', '.join(endpoint.consumes)}")
                if endpoint.produces:
                    spring_info.append(f"Produces: {', '.join(endpoint.produces)}")

        if any(ann in self.SPRING_SERVICES for ann in annotations):
            spring_info.append("Spring Service")

        if any(ann in self.SPRING_CONFIG for ann in annotations):
            spring_info.append("Spring Configuration")
            if "ConditionalOnProperty" in annotations:
                spring_info.append("条件装配")
            if "ConditionalOnClass" in annotations or "ConditionalOnBean" in annotations:
                spring_info.append("条件加载")

        if any(ann in self.SPRING_SECURITY for ann in annotations):
            security_info = [ann for ann in annotations if ann in self.SPRING_SECURITY]
            spring_info.append(f"Security: {', '.join(security_info)}")

        if any(ann in self.MYBATIS_PLUS for ann in annotations):
            spring_info.append("MyBatis Plus Entity")
            table_name = self._extract_table_name(source)
            if table_name:
                spring_info.append(f"Table: {table_name}")

        if any(ann in self.JPA_ENTITY for ann in annotations):
            spring_info.append("JPA Entity")
            jpa_table = self._extract_jpa_table_name(source)
            if jpa_table:
                spring_info.append(f"Table: {jpa_table}")

        if spring_info:
            existing_doc = class_info.docstring or ""
            class_info.docstring = f"{' | '.join(spring_info)}\n{existing_doc}".strip()

        return class_info

    def _analyze_lombok_features(
        self,
        class_info: ClassInfo,
        annotations: list[str]
    ) -> ClassInfo:
        """分析 Lombok 注解特性"""
        lombok_info = []

        if any(ann in self.LOMBOK for ann in annotations):
            found_annotations = [ann for ann in annotations if ann in self.LOMBOK]
            if found_annotations:
                lombok_info.append(f"Lombok: {', '.join(found_annotations)}")

            if "Data" in annotations:
                lombok_info.append("自动生成 Getter/Setter/ToString/EqualsAndHashCode")

            if "Builder" in annotations:
                lombok_info.append("Builder 模式")

            if "Slf4j" in annotations:
                lombok_info.append("SLF4J Logger")
            if "Log4j2" in annotations:
                lombok_info.append("Log4j2 Logger")

        if lombok_info:
            existing_doc = class_info.docstring or ""
            class_info.docstring = f"{' | '.join(lombok_info)}\n{existing_doc}".strip()

        return class_info

    def _analyze_jpa_features(
        self,
        class_info: ClassInfo,
        annotations: list[str],
        source: str
    ) -> ClassInfo:
        """分析 JPA/Hibernate 特性"""
        jpa_info = []

        jpa_entity_annotations = self.JPA_ENTITY & set(annotations)
        if jpa_entity_annotations:
            jpa_info.append("JPA Entity")
            jpa_table = self._extract_jpa_table_name(source)
            if jpa_table:
                jpa_info.append(f"Table: {jpa_table}")

        all_jpa_rel = self.JPA_RELATIONSHIP & set(annotations)
        source_jpa_rel = set()
        for rel in self.JPA_RELATIONSHIP:
            if f"@{rel}" in source:
                source_jpa_rel.add(rel)

        combined_rel = all_jpa_rel | source_jpa_rel
        if combined_rel:
            relationships = []
            if "OneToOne" in combined_rel:
                relationships.append("一对一")
            if "OneToMany" in combined_rel:
                relationships.append("一对多")
            if "ManyToOne" in combined_rel:
                relationships.append("多对一")
            if "ManyToMany" in combined_rel:
                relationships.append("多对多")
            if relationships:
                jpa_info.append(f"关系: {', '.join(relationships)}")

        if jpa_info:
            existing_doc = class_info.docstring or ""
            class_info.docstring = f"{' | '.join(jpa_info)}\n{existing_doc}".strip()

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

        route_annotations = self.SPRING_CONTROLLERS & set(annotations)
        if route_annotations:
            endpoint = self._extract_spring_endpoint_info(source, annotations)
            if endpoint:
                method_info.append(f"Route: {endpoint.path}")
                method_info.append(f"Method: {endpoint.method}")
                if endpoint.consumes:
                    method_info.append(f"Consumes: {', '.join(endpoint.consumes)}")
                if endpoint.produces:
                    method_info.append(f"Produces: {', '.join(endpoint.produces)}")

        injection_annotations = self.SPRING_INJECTION & set(annotations)
        if injection_annotations:
            func_info.description = f"依赖注入: {', '.join(injection_annotations)}"

        sql_annotations = self.MYBATIS_MAPPER & set(annotations)
        if sql_annotations:
            func_info.description = f"MyBatis SQL: {', '.join(sql_annotations)}"

        security_annotations = self.SPRING_SECURITY & set(annotations)
        if security_annotations:
            method_info.append(f"Security: {', '.join(security_annotations)}")

        scheduled_info = self._extract_scheduled_info(source, annotations)
        if scheduled_info:
            method_info.append("定时任务")
            if "cron" in scheduled_info:
                method_info.append(f"Cron: {scheduled_info['cron']}")
            elif "fixedRate" in scheduled_info:
                method_info.append(f"FixedRate: {scheduled_info['fixedRate']}ms")
            elif "fixedDelay" in scheduled_info:
                method_info.append(f"FixedDelay: {scheduled_info['fixedDelay']}ms")

        if method_info:
            existing_doc = func_info.docstring or ""
            func_info.docstring = f"{' | '.join(method_info)}\n{existing_doc}".strip()

        return func_info

    def _analyze_dubbo_features(
        self,
        class_info: ClassInfo,
        annotations: list[str],
        source: str
    ) -> ClassInfo:
        """分析Dubbo服务特性"""
        dubbo_info = []

        dubbo_annotations = self.DUBBO & set(annotations)
        if dubbo_annotations:
            dubbo_info.append(f"Dubbo: {', '.join(dubbo_annotations)}")
            
            service_info = self._extract_dubbo_service_info(source, annotations)
            if service_info:
                if "version" in service_info:
                    dubbo_info.append(f"Version: {service_info['version']}")
                if "interface" in service_info:
                    dubbo_info.append(f"Interface: {service_info['interface']}")
                if "group" in service_info:
                    dubbo_info.append(f"Group: {service_info['group']}")
                if "timeout" in service_info:
                    dubbo_info.append(f"Timeout: {service_info['timeout']}ms")

        if dubbo_info:
            existing_doc = class_info.docstring or ""
            class_info.docstring = f"{' | '.join(dubbo_info)}\n{existing_doc}".strip()

        return class_info

    def _analyze_validation_features(
        self,
        class_info: ClassInfo,
        annotations: list[str],
        source: str
    ) -> ClassInfo:
        """分析Validation校验特性"""
        validation_info = []

        validation_annotations = self.VALIDATION & set(annotations)
        if validation_annotations:
            validation_info.append(f"Validation: {', '.join(validation_annotations)}")
        
        for prop in class_info.class_variables:
            prop_decorators = getattr(prop, 'decorators', [])
            if prop_decorators:
                for dec in prop_decorators:
                    if dec in self.VALIDATION:
                        if not any("Validation:" in v for v in validation_info):
                            validation_info.append(f"Validation: {dec}")
                        break

        if validation_info:
            existing_doc = class_info.docstring or ""
            class_info.docstring = f"{' | '.join(validation_info)}\n{existing_doc}".strip()

        return class_info

    def _analyze_feign_features(
        self,
        class_info: ClassInfo,
        annotations: list[str],
        source: str
    ) -> ClassInfo:
        """分析Feign客户端特性"""
        feign_info = []

        if "FeignClient" in annotations:
            feign_info.append("Feign Client")
            
            client_info = self._extract_feign_client_info(source, annotations)
            if client_info:
                if "name" in client_info:
                    feign_info.append(f"Service: {client_info['name']}")
                if "url" in client_info:
                    feign_info.append(f"URL: {client_info['url']}")
                if "path" in client_info:
                    feign_info.append(f"Path: {client_info['path']}")

        if feign_info:
            existing_doc = class_info.docstring or ""
            class_info.docstring = f"{' | '.join(feign_info)}\n{existing_doc}".strip()

        return class_info

    def _analyze_transactional_features(
        self,
        class_info: ClassInfo,
        annotations: list[str],
        source: str
    ) -> ClassInfo:
        """分析事务特性"""
        tx_info = []

        if "Transactional" in annotations:
            tx_info.append("事务管理")
            
            pattern = r'@Transactional\s*\(([^)]*)\)'
            match = re.search(pattern, source)
            if match:
                attrs_str = match.group(1)
                attrs = self._parse_annotation_attributes(attrs_str)
                
                if "propagation" in attrs:
                    tx_info.append(f"传播: {attrs['propagation']}")
                if "isolation" in attrs:
                    tx_info.append(f"隔离: {attrs['isolation']}")
                if "timeout" in attrs:
                    tx_info.append(f"超时: {attrs['timeout']}s")
                if "readOnly" in attrs and attrs['readOnly']:
                    tx_info.append("只读")
                if "rollbackFor" in attrs:
                    tx_info.append(f"回滚: {attrs['rollbackFor']}")

        if tx_info:
            existing_doc = class_info.docstring or ""
            class_info.docstring = f"{' | '.join(tx_info)}\n{existing_doc}".strip()

        return class_info

    def _analyze_cache_features(
        self,
        class_info: ClassInfo,
        annotations: list[str],
        source: str
    ) -> ClassInfo:
        """分析缓存特性"""
        cache_info = []

        cache_annotations = self.SPRING_CACHE & set(annotations)
        if cache_annotations:
            cache_info.append(f"缓存: {', '.join(cache_annotations)}")
            
            for ann in cache_annotations:
                pattern = rf'@{ann}\s*\(([^)]*)\)'
                match = re.search(pattern, source)
                if match:
                    attrs_str = match.group(1)
                    attrs = self._parse_annotation_attributes(attrs_str)
                    
                    if "value" in attrs or "cacheNames" in attrs:
                        cache_name = attrs.get("value") or attrs.get("cacheNames")
                        cache_info.append(f"缓存名: {cache_name}")
                    if "key" in attrs:
                        cache_info.append(f"Key: {attrs['key']}")
                    if "condition" in attrs:
                        cache_info.append(f"条件: {attrs['condition']}")

        if cache_info:
            existing_doc = class_info.docstring or ""
            class_info.docstring = f"{' | '.join(cache_info)}\n{existing_doc}".strip()

        return class_info

    def _analyze_async_features(
        self,
        class_info: ClassInfo,
        annotations: list[str],
        source: str
    ) -> ClassInfo:
        """分析异步特性"""
        async_info = []

        if "Async" in annotations:
            async_info.append("异步执行")
            
            pattern = r'@Async\s*\(([^)]*)\)'
            match = re.search(pattern, source)
            if match:
                attrs_str = match.group(1)
                attrs = self._parse_annotation_attributes(attrs_str)
                if "value" in attrs:
                    async_info.append(f"执行器: {attrs['value']}")

        if "EventListener" in annotations:
            async_info.append("事件监听器")
            
            pattern = r'@EventListener\s*\(([^)]*)\)'
            match = re.search(pattern, source)
            if match:
                attrs_str = match.group(1)
                attrs = self._parse_annotation_attributes(attrs_str)
                if "classes" in attrs:
                    async_info.append(f"事件类型: {attrs['classes']}")

        if "TransactionalEventListener" in annotations:
            async_info.append("事务事件监听器")

        if async_info:
            existing_doc = class_info.docstring or ""
            class_info.docstring = f"{' | '.join(async_info)}\n{existing_doc}".strip()

        return class_info

    def _analyze_mapstruct_features(
        self,
        class_info: ClassInfo,
        annotations: list[str],
        source: str
    ) -> ClassInfo:
        """分析MapStruct特性"""
        mapstruct_info = []

        if "Mapper" in annotations:
            mapstruct_info.append("MapStruct Mapper")
            
            pattern = r'@Mapper\s*\(([^)]*)\)'
            match = re.search(pattern, source)
            if match:
                attrs_str = match.group(1)
                attrs = self._parse_annotation_attributes(attrs_str)
                
                if "componentModel" in attrs:
                    mapstruct_info.append(f"组件模型: {attrs['componentModel']}")
                if "uses" in attrs:
                    mapstruct_info.append(f"引用: {attrs['uses']}")

        if mapstruct_info:
            existing_doc = class_info.docstring or ""
            class_info.docstring = f"{' | '.join(mapstruct_info)}\n{existing_doc}".strip()

        return class_info

    def _extract_route_mapping(self, source: str, annotations: list[str]) -> Optional[str]:
        """提取路由映射信息"""
        for ann in annotations:
            if ann in ("RequestMapping", "GetMapping", "PostMapping", "PutMapping", "DeleteMapping", "PatchMapping"):
                pattern = rf'@{ann}\s*\(\s*(?:value\s*=\s*)?["\']([^"\']+)["\']'
                match = re.search(pattern, source)
                if match:
                    return match.group(1)
                
                pattern2 = rf'@{ann}\s*\(\s*path\s*=\s*["\']([^"\']+)["\']'
                match2 = re.search(pattern2, source)
                if match2:
                    return match2.group(1)

        return None

    def _extract_table_name(self, source: str) -> Optional[str]:
        """提取 MyBatis Plus 表名"""
        import re

        pattern = r'@TableName\s*\(\s*["\']([^"\']+)["\']\s*\)'
        match = re.search(pattern, source)
        if match:
            return match.group(1)

        return None

    def _extract_jpa_table_name(self, source: str) -> Optional[str]:
        """提取 JPA 表名"""
        import re

        pattern = r'@Table\s*\(\s*name\s*=\s*["\']([^"\']+)["\']\s*\)'
        match = re.search(pattern, source)
        if match:
            return match.group(1)

        return None

    def _extract_javadoc(self, node, source: str) -> Optional[str]:
        """提取 Javadoc 注释"""
        line_start = node.start_point[0]
        lines = source.split("\n")

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

    def _parse_javadoc(self, javadoc_text: str) -> JavaDocInfo:
        """解析JavaDoc文本，提取标签信息"""
        info = JavaDocInfo()
        
        if not javadoc_text:
            return info
        
        lines = javadoc_text.split("\n")
        description_lines = []
        
        for line in lines:
            stripped = line.strip()
            
            if stripped.startswith("@param"):
                match = re.match(r'@param\s+(\w+)\s*(.*)', stripped)
                if match:
                    param_name = match.group(1)
                    param_desc = match.group(2).strip()
                    info.params[param_name] = param_desc
                    info.tags.append(JavaDocTag(name="param", value=param_name, description=param_desc))
            
            elif stripped.startswith("@return"):
                match = re.match(r'@return\s*(.*)', stripped)
                if match:
                    info.returns = match.group(1).strip()
                    info.tags.append(JavaDocTag(name="return", description=info.returns))
            
            elif stripped.startswith("@throws") or stripped.startswith("@exception"):
                match = re.match(r'@(?:throws|exception)\s+(\w+)\s*(.*)', stripped)
                if match:
                    exception_type = match.group(1)
                    exception_desc = match.group(2).strip()
                    info.throws.append((exception_type, exception_desc))
                    info.tags.append(JavaDocTag(name="throws", value=exception_type, description=exception_desc))
            
            elif stripped.startswith("@see"):
                match = re.match(r'@see\s+(.+)', stripped)
                if match:
                    see_ref = match.group(1).strip()
                    info.see_also.append(see_ref)
                    info.tags.append(JavaDocTag(name="see", description=see_ref))
            
            elif stripped.startswith("@since"):
                match = re.match(r'@since\s+(.+)', stripped)
                if match:
                    info.since = match.group(1).strip()
                    info.tags.append(JavaDocTag(name="since", description=info.since))
            
            elif stripped.startswith("@deprecated"):
                info.deprecated = True
                match = re.match(r'@deprecated\s*(.*)', stripped)
                if match:
                    info.tags.append(JavaDocTag(name="deprecated", description=match.group(1).strip()))
                else:
                    info.tags.append(JavaDocTag(name="deprecated"))
            
            elif stripped.startswith("@author"):
                match = re.match(r'@author\s+(.+)', stripped)
                if match:
                    info.author = match.group(1).strip()
                    info.tags.append(JavaDocTag(name="author", description=info.author))
            
            elif stripped.startswith("@version"):
                match = re.match(r'@version\s+(.+)', stripped)
                if match:
                    info.version = match.group(1).strip()
                    info.tags.append(JavaDocTag(name="version", description=info.version))
            
            elif stripped.startswith("@"):
                match = re.match(r'@(\w+)\s*(.*)', stripped)
                if match:
                    tag_name = match.group(1)
                    tag_value = match.group(2).strip()
                    info.tags.append(JavaDocTag(name=tag_name, description=tag_value))
            
            elif not stripped.startswith("@"):
                if not any(t.name in ("param", "return", "throws", "see", "since", "deprecated", "author", "version") for t in info.tags):
                    description_lines.append(line)
        
        info.description = self._process_inline_tags("\n".join(description_lines).strip())
        
        return info

    def _process_inline_tags(self, text: str) -> str:
        """处理内联标签 {@link}, {@code} 等"""
        if not text:
            return text
        
        text = re.sub(r'\{@link\s+([^}]+)\}', r'\1', text)
        text = re.sub(r'\{@code\s+([^}]+)\}', r'`\1`', text)
        text = re.sub(r'\{@literal\s+([^}]+)\}', r'\1', text)
        text = re.sub(r'\{@value\s*\}', '', text)
        
        return text

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

    def _parse_annotation_with_attributes(self, node, source: str) -> AnnotationInfo:
        """解析注解及其属性"""
        ann_text = self._get_node_text(node, source)
        ann_name = self._parse_annotation_name(node, source)
        
        attributes = {}
        
        if ann_text:
            pattern = rf'@{ann_name}\s*\(([^)]*)\)'
            match = re.search(pattern, ann_text)
            if match:
                attrs_str = match.group(1)
                attributes = self._parse_annotation_attributes(attrs_str)
        
        return AnnotationInfo(
            name=ann_name,
            attributes=attributes,
            raw_text=ann_text
        )

    def _parse_annotation_attributes(self, attrs_str: str) -> dict[str, Any]:
        """解析注解属性"""
        attributes = {}
        
        if not attrs_str.strip():
            return attributes
        
        simple_value_pattern = r'^\s*"([^"]*)"\s*$'
        simple_match = re.match(simple_value_pattern, attrs_str)
        if simple_match:
            attributes["value"] = simple_match.group(1)
            return attributes
        
        simple_value_pattern2 = r'^\s*\'([^\']*)\'\s*$'
        simple_match2 = re.match(simple_value_pattern2, attrs_str)
        if simple_match2:
            attributes["value"] = simple_match2.group(1)
            return attributes
        
        pattern = r'(\w+)\s*=\s*(?:"([^"]*)"|\'([^\']+)\'|(\d+)|(\w+))'
        matches = re.findall(pattern, attrs_str)
        
        for key, str_val1, str_val2, num_val, bool_val in matches:
            if str_val1:
                attributes[key] = str_val1
            elif str_val2:
                attributes[key] = str_val2
            elif num_val:
                attributes[key] = int(num_val)
            elif bool_val:
                attributes[key] = bool_val.lower() == "true"
            if key in ("produces", "consumes", "params", "headers"):
                attributes[key] = self._parse_array_value(attrs_str, key)
        
        return attributes
    
    def _parse_array_value(self, attrs_str: str, key: str) -> list[str]:
        """解析数组值"""
        values = []
        
        pattern = rf'{key}\s*=\s*\{{([^}}]*)\}}'
        match = re.search(pattern, attrs_str)
        if match:
            array_content = match.group(1)
            str_pattern = r'"([^"]*)"'
            values = re.findall(str_pattern, array_content)
        
        return values

    def _extract_spring_endpoint_info(self, source: str, annotations: list[str]) -> Optional[SpringEndpointInfo]:
        """提取Spring端点信息"""
        endpoint_info = SpringEndpointInfo()
        
        http_method_map = {
            "GetMapping": "GET",
            "PostMapping": "POST",
            "PutMapping": "PUT",
            "DeleteMapping": "DELETE",
            "PatchMapping": "PATCH",
        }
        
        for ann in annotations:
            if ann in http_method_map:
                endpoint_info.method = http_method_map[ann]
                
                pattern = rf'@{ann}\s*\(([^)]*)\)'
                match = re.search(pattern, source)
                if match:
                    attrs_str = match.group(1)
                    attrs = self._parse_annotation_attributes(attrs_str)
                    
                    if "value" in attrs:
                        endpoint_info.path = attrs["value"]
                    elif "path" in attrs:
                        endpoint_info.path = attrs["path"]
                    
                    if "consumes" in attrs:
                        consumes = attrs["consumes"]
                        if isinstance(consumes, str):
                            endpoint_info.consumes = [consumes]
                        elif isinstance(consumes, list):
                            endpoint_info.consumes = consumes
                    
                    if "produces" in attrs:
                        produces = attrs["produces"]
                        if isinstance(produces, str):
                            endpoint_info.produces = [produces]
                        elif isinstance(produces, list):
                            endpoint_info.produces = produces
                    
                    if "params" in attrs:
                        params = attrs["params"]
                        if isinstance(params, str):
                            endpoint_info.params = [params]
                        elif isinstance(params, list):
                            endpoint_info.params = params
                    
                    if "headers" in attrs:
                        headers = attrs["headers"]
                        if isinstance(headers, str):
                            endpoint_info.headers = [headers]
                        elif isinstance(headers, list):
                            endpoint_info.headers = headers
                
                return endpoint_info if endpoint_info.path else None
            
            elif ann == "RequestMapping":
                pattern = r'@RequestMapping\s*\(([^)]*)\)'
                match = re.search(pattern, source)
                if match:
                    attrs_str = match.group(1)
                    attrs = self._parse_annotation_attributes(attrs_str)
                    
                    if "value" in attrs:
                        endpoint_info.path = attrs["value"]
                    elif "path" in attrs:
                        endpoint_info.path = attrs["path"]
                    
                    if "method" in attrs:
                        method_str = attrs["method"]
                        if isinstance(method_str, str):
                            endpoint_info.method = method_str.upper()
                    
                    if "consumes" in attrs:
                        consumes = attrs["consumes"]
                        if isinstance(consumes, str):
                            endpoint_info.consumes = [consumes]
                        elif isinstance(consumes, list):
                            endpoint_info.consumes = consumes
                    
                    if "produces" in attrs:
                        produces = attrs["produces"]
                        if isinstance(produces, str):
                            endpoint_info.produces = [produces]
                        elif isinstance(produces, list):
                            endpoint_info.produces = produces
                
                return endpoint_info if endpoint_info.path else None
        
        return None

    def _extract_jpa_column_info(self, source: str) -> list[JpaColumnInfo]:
        """提取JPA列信息"""
        columns = []
        
        pattern = r'@Column\s*\(([^)]*)\)'
        matches = re.findall(pattern, source)
        
        for match in matches:
            attrs_str = match
            attrs = self._parse_annotation_attributes(attrs_str)
            
            column_info = JpaColumnInfo(
                name=attrs.get("name"),
                nullable=attrs.get("nullable", True),
                unique=attrs.get("unique", False),
                length=attrs.get("length"),
                precision=attrs.get("precision"),
                scale=attrs.get("scale"),
                column_definition=attrs.get("columnDefinition")
            )
            columns.append(column_info)
        
        return columns

    def _extract_validation_annotations(self, source: str) -> list[dict[str, Any]]:
        """提取校验注解信息"""
        validations = []
        
        for ann in self.VALIDATION:
            pattern = rf'@{ann}\s*(?:\(([^)]*)\))?'
            matches = re.finditer(pattern, source)
            
            for match in matches:
                attrs_str = match.group(1) or ""
                attrs = self._parse_annotation_attributes(attrs_str) if attrs_str else {}
                
                validations.append({
                    "name": ann,
                    "attributes": attrs
                })
        
        return validations

    def _extract_dubbo_service_info(self, source: str, annotations: list[str]) -> Optional[dict[str, Any]]:
        """提取Dubbo服务信息"""
        dubbo_info = {}
        
        for ann in annotations:
            if ann in self.DUBBO:
                pattern = rf'@{ann}\s*\(([^)]*)\)'
                match = re.search(pattern, source)
                if match:
                    attrs_str = match.group(1)
                    attrs = self._parse_annotation_attributes(attrs_str)
                    
                    dubbo_info["annotation"] = ann
                    if "version" in attrs:
                        dubbo_info["version"] = attrs["version"]
                    if "interface" in attrs:
                        dubbo_info["interface"] = attrs["interface"]
                    if "group" in attrs:
                        dubbo_info["group"] = attrs["group"]
                    if "timeout" in attrs:
                        dubbo_info["timeout"] = attrs["timeout"]
                    if "retries" in attrs:
                        dubbo_info["retries"] = attrs["retries"]
        
        return dubbo_info if dubbo_info else None

    def _extract_scheduled_info(self, source: str, annotations: list[str]) -> Optional[dict[str, Any]]:
        """提取定时任务信息"""
        scheduled_info = {}
        
        if "Scheduled" in annotations:
            pattern = r'@Scheduled\s*\(([^)]*)\)'
            match = re.search(pattern, source)
            if match:
                attrs_str = match.group(1)
                attrs = self._parse_annotation_attributes(attrs_str)
                
                scheduled_info["annotation"] = "Scheduled"
                if "cron" in attrs:
                    scheduled_info["cron"] = attrs["cron"]
                if "fixedRate" in attrs:
                    scheduled_info["fixedRate"] = attrs["fixedRate"]
                if "fixedDelay" in attrs:
                    scheduled_info["fixedDelay"] = attrs["fixedDelay"]
                if "initialDelay" in attrs:
                    scheduled_info["initialDelay"] = attrs["initialDelay"]
        
        return scheduled_info if scheduled_info else None

    def _extract_feign_client_info(self, source: str, annotations: list[str]) -> Optional[dict[str, Any]]:
        """提取Feign客户端信息"""
        feign_info = {}
        
        if "FeignClient" in annotations:
            pattern = r'@FeignClient\s*\(([^)]*)\)'
            match = re.search(pattern, source)
            if match:
                attrs_str = match.group(1)
                attrs = self._parse_annotation_attributes(attrs_str)
                
                feign_info["annotation"] = "FeignClient"
                if "name" in attrs:
                    feign_info["name"] = attrs["name"]
                if "value" in attrs:
                    feign_info["name"] = attrs["value"]
                if "url" in attrs:
                    feign_info["url"] = attrs["url"]
                if "path" in attrs:
                    feign_info["path"] = attrs["path"]
                if "configuration" in attrs:
                    feign_info["configuration"] = attrs["configuration"]
        
        return feign_info if feign_info else None
