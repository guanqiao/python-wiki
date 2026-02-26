"""
TypeScript/JavaScript 代码解析器
支持 TS/JS/React/Vue 文件解析
"""

import re
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


def _get_language():
    """获取 tree-sitter 语言实例"""
    try:
        import tree_sitter_javascript as ts_javascript
        import tree_sitter_typescript as ts_typescript

        JS_LANGUAGE = Language(ts_javascript.language())
        TS_LANGUAGE = Language(ts_typescript.language_typescript())
        TSX_LANGUAGE = Language(ts_typescript.language_tsx())
        return JS_LANGUAGE, TS_LANGUAGE, TSX_LANGUAGE
    except ImportError:
        return None, None, None


class TypeScriptParser(BaseParser):
    """TypeScript/JavaScript/React/Vue 解析器"""

    def __init__(
        self,
        exclude_patterns: Optional[list[str]] = None,
        include_private: bool = False,
    ):
        super().__init__(exclude_patterns, include_private)
        self._js_lang, self._ts_lang, self._tsx_lang = _get_language()
        self._parsers = {}
        if self._js_lang:
            self._parsers[".js"] = Parser(self._js_lang)
            self._parsers[".jsx"] = Parser(self._js_lang)
            self._parsers[".mjs"] = Parser(self._js_lang)
        if self._ts_lang:
            self._parsers[".ts"] = Parser(self._ts_lang)
        if self._tsx_lang:
            self._parsers[".tsx"] = Parser(self._tsx_lang)

    def get_supported_extensions(self) -> list[str]:
        return [".ts", ".tsx", ".js", ".jsx", ".mjs", ".vue"]

    def parse_file(self, file_path: Path) -> ParseResult:
        result = ParseResult()

        try:
            source = file_path.read_text(encoding="utf-8")

            if file_path.suffix == ".vue":
                module_info = self._parse_vue_file(source, file_path)
            else:
                module_info = self._parse_ts_file(source, file_path)

            if module_info:
                result.modules.append(module_info)
                dependencies = self._extract_dependencies(module_info)
                result.dependencies.extend(dependencies)

        except Exception as e:
            result.errors.append(f"Error parsing {file_path}: {e}")

        return result

    def parse_directory(self, directory: Path) -> ParseResult:
        result = ParseResult()

        for ext in self.get_supported_extensions():
            for file_path in directory.rglob(f"*{ext}"):
                if self.should_parse(file_path):
                    file_result = self.parse_file(file_path)
                    result.modules.extend(file_result.modules)
                    result.dependencies.extend(file_result.dependencies)
                    result.errors.extend(file_result.errors)
                    result.warnings.extend(file_result.warnings)

        return result

    def _parse_vue_file(self, source: str, file_path: Path) -> Optional[ModuleInfo]:
        """解析 Vue 单文件组件"""
        # 提取 <script> 或 <script setup> 内容
        script_match = re.search(
            r'<script\s*(?:lang="ts"|setup)?[^>]*>(.*?)</script>',
            source,
            re.DOTALL | re.IGNORECASE
        )

        if not script_match:
            return None

        script_content = script_match.group(1).strip()
        is_ts = 'lang="ts"' in script_match.group(0)

        # 解析 script 部分
        if is_ts:
            module_info = self._parse_ts_file(script_content, file_path)
        else:
            module_info = self._parse_ts_file(script_content, file_path, use_js=True)

        if module_info:
            # 提取 Vue 组件特有信息
            module_info = self._extract_vue_info(source, module_info)

        return module_info

    def _extract_vue_info(self, source: str, module_info: ModuleInfo) -> ModuleInfo:
        """提取 Vue 组件特有信息"""
        # 检查是否使用 Composition API
        is_composition_api = "setup" in source or "defineProps" in source or "defineEmits" in source
        is_options_api = False

        # 检查是否使用 Options API
        options_api_patterns = [
            r'\bdata\s*\(\s*\)\s*\{',
            r'\bmethods\s*:\s*\{',
            r'\bcomputed\s*:\s*\{',
            r'\bwatch\s*:\s*\{',
            r'\bprops\s*:\s*\{',
            r'\bemits\s*:\s*\[',
            r'\bcomponents\s*:\s*\{',
            r'\blifecycle\s*:\s*\{',
        ]
        for pattern in options_api_patterns:
            if re.search(pattern, source):
                is_options_api = True
                break

        if is_composition_api:
            module_info.docstring = f"{module_info.docstring or ''}\n使用 Composition API".strip()
        elif is_options_api:
            module_info.docstring = f"{module_info.docstring or ''}\n使用 Options API".strip()

        # 提取 Props 定义 (Composition API)
        props_match = re.search(r'defineProps<([^>]+)>', source)
        if props_match:
            props_type = props_match.group(1).strip()
            module_info.docstring = f"{module_info.docstring or ''}\nProps: {props_type}".strip()

        # 提取 Props 定义 (Options API)
        props_options_match = re.search(r'props\s*:\s*\{([^}]+)\}', source, re.DOTALL)
        if props_options_match and is_options_api:
            props_content = props_options_match.group(1).strip()
            # 提取 props 名称
            prop_names = re.findall(r'(\w+)\s*:', props_content)
            if prop_names:
                module_info.docstring = f"{module_info.docstring or ''}\nProps: {', '.join(prop_names)}".strip()

        # 提取 Emits 定义 (Composition API)
        emits_match = re.search(r'defineEmits<([^>]+)>', source)
        if emits_match:
            emits_type = emits_match.group(1).strip()
            module_info.docstring = f"{module_info.docstring or ''}\nEmits: {emits_type}".strip()

        # 提取 Emits 定义 (Options API)
        emits_options_match = re.search(r'emits\s*:\s*\[([^\]]+)\]', source)
        if emits_options_match and is_options_api:
            emits_list = emits_options_match.group(1).strip()
            emit_names = re.findall(r'["\']([^"\']+)["\']', emits_list)
            if emit_names:
                module_info.docstring = f"{module_info.docstring or ''}\nEmits: {', '.join(emit_names)}".strip()

        # 提取组件名称
        name_match = re.search(r'name\s*:\s*["\']([^"\']+)["\']', source)
        if name_match:
            component_name = name_match.group(1)
            module_info.docstring = f"{module_info.docstring or ''}\n组件名: {component_name}".strip()

        # 提取生命周期钩子
        lifecycle_hooks = [
            'beforeCreate', 'created', 'beforeMount', 'mounted',
            'beforeUpdate', 'updated', 'beforeUnmount', 'unmounted',
            'activated', 'deactivated', 'errorCaptured', 'renderTracked', 'renderTriggered'
        ]
        found_hooks = []
        for hook in lifecycle_hooks:
            if re.search(rf'\b{hook}\s*\(', source):
                found_hooks.append(hook)
        if found_hooks:
            module_info.docstring = f"{module_info.docstring or ''}\n生命周期: {', '.join(found_hooks)}".strip()

        # 提取 Computed 属性 (Options API)
        computed_match = re.search(r'computed\s*:\s*\{([^}]+)\}', source, re.DOTALL)
        if computed_match and is_options_api:
            computed_content = computed_match.group(1).strip()
            computed_names = re.findall(r'(\w+)\s*\(', computed_content)
            if computed_names:
                module_info.docstring = f"{module_info.docstring or ''}\nComputed: {', '.join(computed_names)}".strip()

        # 提取 Methods (Options API)
        methods_match = re.search(r'methods\s*:\s*\{([^}]+)\}', source, re.DOTALL)
        if methods_match and is_options_api:
            methods_content = methods_match.group(1).strip()
            method_names = re.findall(r'(\w+)\s*\(', methods_content)
            if method_names:
                module_info.docstring = f"{module_info.docstring or ''}\nMethods: {', '.join(method_names)}".strip()

        return module_info

    def _parse_ts_file(
        self,
        source: str,
        file_path: Path,
        use_js: bool = False
    ) -> Optional[ModuleInfo]:
        """解析 TypeScript/JavaScript 文件"""
        ext = ".js" if use_js else file_path.suffix
        parser = self._parsers.get(ext)

        if not parser:
            return None

        try:
            tree = parser.parse(bytes(source, "utf-8"))
            return self._parse_module(tree, source, file_path)
        except Exception as e:
            return None

    def _parse_module(
        self,
        tree: Tree,
        source: str,
        file_path: Path
    ) -> ModuleInfo:
        """解析模块"""
        module_name = self._get_module_name(file_path)
        lines = source.split("\n")

        module_info = ModuleInfo(
            name=module_name,
            file_path=file_path,
            line_count=len(lines),
        )

        root = tree.root_node

        for child in root.children:
            if child.type == "import_statement":
                module_info.imports.extend(self._parse_import(child, source))
            elif child.type == "import_specifier":
                module_info.imports.extend(self._parse_import_specifier(child, source))
            elif child.type == "export_statement":
                self._parse_export(child, source, module_info)
            elif child.type == "class_declaration":
                class_info = self._parse_class(child, source, module_name)
                if self.include_private or class_info.visibility != Visibility.PRIVATE:
                    module_info.classes.append(class_info)
            elif child.type == "function_declaration":
                func_info = self._parse_function(child, source, module_name)
                if self.include_private or func_info.visibility != Visibility.PRIVATE:
                    module_info.functions.append(func_info)
            elif child.type == "lexical_declaration":
                # const/let 声明，可能是函数、箭头函数或变量
                self._parse_lexical_declaration(child, source, module_info, module_name)
            elif child.type == "variable_declaration":
                # var 声明
                self._parse_variable_declaration(child, source, module_info, module_name)
            elif child.type == "interface_declaration":
                # TypeScript 接口
                class_info = self._parse_interface(child, source, module_name)
                if self.include_private or class_info.visibility != Visibility.PRIVATE:
                    module_info.classes.append(class_info)
            elif child.type == "type_alias_declaration":
                # TypeScript type 别名
                self._parse_type_alias(child, source, module_info)
            elif child.type == "enum_declaration":
                # TypeScript 枚举
                enum_info = self._parse_enum(child, source, module_name)
                if self.include_private or enum_info.visibility != Visibility.PRIVATE:
                    module_info.classes.append(enum_info)
            elif child.type == "namespace_declaration":
                # TypeScript 命名空间
                namespace_info = self._parse_namespace(child, source, module_name)
                if namespace_info:
                    module_info.submodules.append(namespace_info.name)
            elif child.type == "module_declaration":
                # TypeScript 模块
                module_decl_info = self._parse_module_declaration(child, source, module_name)
                if module_decl_info:
                    module_info.submodules.append(module_decl_info.name)

        return module_info

    def _get_module_name(self, file_path: Path) -> str:
        """获取模块名称"""
        return file_path.stem

    def _get_node_text(self, node, source: str) -> str:
        """获取节点文本"""
        return source[node.start_byte:node.end_byte]

    def _parse_import(self, node, source: str) -> list[ImportInfo]:
        """解析 import 语句"""
        imports = []

        # import { a, b } from 'module'
        # import * as name from 'module'
        # import defaultExport from 'module'

        source_clause = None
        names = []
        alias = None

        for child in node.children:
            if child.type == "string":
                source_clause = self._get_node_text(child, source).strip('"\'')
            elif child.type == "import_clause":
                for clause_child in child.children:
                    if clause_child.type == "identifier":
                        names.append(self._get_node_text(clause_child, source))
                    elif clause_child.type == "named_imports":
                        for specifier in clause_child.children:
                            if specifier.type == "import_specifier":
                                name = None
                                alias_name = None
                                for spec_child in specifier.children:
                                    if spec_child.type == "identifier":
                                        if name is None:
                                            name = self._get_node_text(spec_child, source)
                                        else:
                                            alias_name = self._get_node_text(spec_child, source)
                                if name:
                                    names.append(alias_name or name)
                    elif clause_child.type == "namespace_import":
                        # * as name
                        for ns_child in clause_child.children:
                            if ns_child.type == "identifier":
                                alias = self._get_node_text(ns_child, source)

        if source_clause:
            imports.append(ImportInfo(
                module=source_clause,
                names=names if names else [source_clause],
                alias=alias,
                is_from_import=True,
                line=node.start_point[0] + 1,
            ))

        return imports

    def _parse_import_specifier(self, node, source: str) -> list[ImportInfo]:
        """解析 import specifier"""
        return []

    def _parse_export(self, node, source: str, module_info: ModuleInfo) -> None:
        """解析 export 语句"""
        for child in node.children:
            if child.type == "class_declaration":
                class_info = self._parse_class(child, source, module_info.name)
                if self.include_private or class_info.visibility != Visibility.PRIVATE:
                    module_info.classes.append(class_info)
            elif child.type == "function_declaration":
                func_info = self._parse_function(child, source, module_info.name)
                if self.include_private or func_info.visibility != Visibility.PRIVATE:
                    module_info.functions.append(func_info)
            elif child.type == "lexical_declaration":
                self._parse_lexical_declaration(child, source, module_info, module_info.name)

    def _parse_class(self, node, source: str, module_name: str) -> ClassInfo:
        """解析类声明"""
        name = ""
        bases = []
        is_react_component = False

        for child in node.children:
            if child.type == "type_identifier" or child.type == "identifier":
                name = self._get_node_text(child, source)
            elif child.type == "class_heritage":
                # extends Clause
                for heritage_child in child.children:
                    if heritage_child.type == "extends_clause":
                        for ext_child in heritage_child.children:
                            if ext_child.type == "type_identifier" or ext_child.type == "identifier":
                                base_name = self._get_node_text(ext_child, source)
                                bases.append(base_name)
                                if base_name in ("Component", "React.Component", "PureComponent"):
                                    is_react_component = True

        full_name = f"{module_name}.{name}"
        visibility = self._get_visibility(name)

        class_info = ClassInfo(
            name=name,
            full_name=full_name,
            bases=bases,
            visibility=visibility,
            docstring=self._extract_jsdoc(node, source),
            line_start=node.start_point[0] + 1,
            line_end=node.end_point[0] + 1,
        )

        # 解析类体
        for child in node.children:
            if child.type == "class_body":
                for member in child.children:
                    if member.type == "method_definition":
                        method = self._parse_method(member, source, full_name)
                        if self.include_private or method.visibility != Visibility.PRIVATE:
                            class_info.methods.append(method)
                    elif member.type == "field_definition":
                        prop = self._parse_field(member, source)
                        if prop:
                            class_info.properties.append(prop)

        # React 组件特殊处理
        if is_react_component:
            class_info = self._extract_react_component_info(class_info, node, source)

        return class_info

    def _extract_react_component_info(
        self,
        class_info: ClassInfo,
        node,
        source: str
    ) -> ClassInfo:
        """提取 React 类组件特有信息"""
        class_info.docstring = f"{class_info.docstring or ''}\nReact Class Component".strip()

        # 检查 render 方法
        has_render = any(m.name == "render" for m in class_info.methods)
        if has_render:
            class_info.docstring = f"{class_info.docstring}\n有 render 方法".strip()

        return class_info

    def _parse_interface(self, node, source: str, module_name: str) -> ClassInfo:
        """解析 TypeScript 接口"""
        name = ""
        bases = []

        for child in node.children:
            if child.type == "type_identifier":
                name = self._get_node_text(child, source)
            elif child.type == "extends_clause":
                for ext_child in child.children:
                    if ext_child.type == "type_identifier":
                        bases.append(self._get_node_text(ext_child, source))

        full_name = f"{module_name}.{name}"
        visibility = self._get_visibility(name)

        class_info = ClassInfo(
            name=name,
            full_name=full_name,
            bases=bases,
            visibility=visibility,
            docstring=f"TypeScript Interface\n{self._extract_jsdoc(node, source) or ''}".strip(),
            line_start=node.start_point[0] + 1,
            line_end=node.end_point[0] + 1,
        )

        # 解析接口成员
        for child in node.children:
            if child.type == "object_type":
                for member in child.children:
                    if member.type == "property_signature":
                        prop = self._parse_property_signature(member, source)
                        if prop:
                            class_info.properties.append(prop)
                    elif member.type == "method_signature":
                        method = self._parse_method_signature(member, source, full_name)
                        if method:
                            class_info.methods.append(method)

        return class_info

    def _parse_property_signature(self, node, source: str) -> Optional[PropertyInfo]:
        """解析接口属性签名"""
        name = ""
        type_hint = None

        for child in node.children:
            if child.type == "property_identifier" or child.type == "identifier":
                name = self._get_node_text(child, source)
            elif child.type == "type_annotation":
                type_hint = self._get_node_text(child, source).lstrip(": ")

        if name:
            return PropertyInfo(
                name=name,
                type_hint=type_hint,
                visibility=self._get_visibility(name),
            )
        return None

    def _parse_method_signature(self, node, source: str, class_name: str) -> Optional[FunctionInfo]:
        """解析接口方法签名"""
        name = ""

        for child in node.children:
            if child.type == "property_identifier" or child.type == "identifier":
                name = self._get_node_text(child, source)

        if not name:
            return None

        full_name = f"{class_name}.{name}"

        return FunctionInfo(
            name=name,
            full_name=full_name,
            visibility=self._get_visibility(name),
            line_start=node.start_point[0] + 1,
            line_end=node.end_point[0] + 1,
        )

    def _parse_type_alias(self, node, source: str, module_info: ModuleInfo) -> None:
        """解析 TypeScript type 别名"""
        # type 别名作为变量存储
        name = ""
        type_value = ""

        for child in node.children:
            if child.type == "type_identifier":
                name = self._get_node_text(child, source)
            elif child.type == "type_annotation" or child.type == "type":
                type_value = self._get_node_text(child, source)

        if name:
            module_info.variables.append(PropertyInfo(
                name=name,
                type_hint=f"type = {type_value}",
                visibility=self._get_visibility(name),
            ))

    def _parse_function(
        self,
        node,
        source: str,
        module_name: str,
        is_method: bool = False
    ) -> FunctionInfo:
        """解析函数声明"""
        name = ""
        is_async = False

        for child in node.children:
            if child.type == "identifier":
                name = self._get_node_text(child, source)
            elif child.type == "async":
                is_async = True

        full_name = f"{module_name}.{name}"
        visibility = self._get_visibility(name)

        parameters = []
        return_type = None

        for child in node.children:
            if child.type == "formal_parameters":
                parameters = self._parse_parameters(child, source)
            elif child.type == "type_annotation":
                return_type = self._get_node_text(child, source).lstrip(": ")

        func_info = FunctionInfo(
            name=name,
            full_name=full_name,
            parameters=parameters,
            return_type=return_type,
            visibility=visibility,
            is_async=is_async,
            docstring=self._extract_jsdoc(node, source),
            line_start=node.start_point[0] + 1,
            line_end=node.end_point[0] + 1,
        )

        # React 函数组件检测
        if self._is_react_function_component(node, source):
            func_info.docstring = f"{func_info.docstring or ''}\nReact Function Component".strip()
            # 检测 Hooks
            hooks = self._detect_hooks(node, source)
            if hooks:
                func_info.docstring = f"{func_info.docstring}\n使用 Hooks: {', '.join(hooks)}".strip()

        return func_info

    def _parse_method(self, node, source: str, class_name: str) -> FunctionInfo:
        """解析类方法"""
        name = ""
        is_async = False
        is_static = False
        is_getter = False
        is_setter = False

        for child in node.children:
            if child.type == "property_identifier":
                name = self._get_node_text(child, source)
            elif child.type == "async":
                is_async = True
            elif child.type == "static":
                is_static = True
            elif child.type == "get":
                is_getter = True
            elif child.type == "set":
                is_setter = True

        full_name = f"{class_name}.{name}"
        visibility = self._get_visibility(name)

        parameters = []
        return_type = None

        for child in node.children:
            if child.type == "formal_parameters":
                parameters = self._parse_parameters(child, source)
            elif child.type == "type_annotation":
                return_type = self._get_node_text(child, source).lstrip(": ")

        return FunctionInfo(
            name=name,
            full_name=full_name,
            parameters=parameters,
            return_type=return_type,
            visibility=visibility,
            is_async=is_async,
            is_staticmethod=is_static,
            docstring=self._extract_jsdoc(node, source),
            line_start=node.start_point[0] + 1,
            line_end=node.end_point[0] + 1,
        )

    def _parse_field(self, node, source: str) -> Optional[PropertyInfo]:
        """解析类字段"""
        name = ""
        type_hint = None

        for child in node.children:
            if child.type == "property_identifier":
                name = self._get_node_text(child, source)
            elif child.type == "type_annotation":
                type_hint = self._get_node_text(child, source).lstrip(": ")

        if name:
            return PropertyInfo(
                name=name,
                type_hint=type_hint,
                visibility=self._get_visibility(name),
            )
        return None

    def _parse_parameters(self, node, source: str) -> list[ParameterInfo]:
        """解析函数参数"""
        parameters = []

        for child in node.children:
            if child.type == "identifier":
                # 简单参数
                name = self._get_node_text(child, source)
                parameters.append(ParameterInfo(
                    name=name,
                    kind=ParameterKind.POSITIONAL_OR_KEYWORD,
                ))
            elif child.type == "required_parameter" or child.type == "optional_parameter":
                # 带类型注解的参数
                param_info = self._parse_parameter(child, source)
                if param_info:
                    parameters.append(param_info)

        return parameters

    def _parse_parameter(self, node, source: str) -> Optional[ParameterInfo]:
        """解析单个参数"""
        name = ""
        type_hint = None
        default_value = None

        for child in node.children:
            if child.type == "identifier":
                name = self._get_node_text(child, source)
            elif child.type == "type_annotation":
                type_hint = self._get_node_text(child, source).lstrip(": ")
            elif child.type == "=":
                # 默认值
                pass
            elif child.prev_sibling and child.prev_sibling.type == "=":
                default_value = self._get_node_text(child, source)

        if name:
            return ParameterInfo(
                name=name,
                type_hint=type_hint,
                default_value=default_value,
                kind=ParameterKind.POSITIONAL_OR_KEYWORD,
            )
        return None

    def _parse_lexical_declaration(
        self,
        node,
        source: str,
        module_info: ModuleInfo,
        module_name: str
    ) -> None:
        """解析 const/let 声明"""
        for child in node.children:
            if child.type == "variable_declarator":
                name = ""
                is_arrow_function = False
                func_node = None

                for decl_child in child.children:
                    if decl_child.type == "identifier":
                        name = self._get_node_text(decl_child, source)
                    elif decl_child.type == "arrow_function":
                        is_arrow_function = True
                        func_node = decl_child
                    elif decl_child.type == "function":
                        is_arrow_function = True
                        func_node = decl_child

                if is_arrow_function and func_node:
                    # 箭头函数
                    func_info = self._parse_arrow_function(func_node, source, name, module_name)
                    if self.include_private or func_info.visibility != Visibility.PRIVATE:
                        module_info.functions.append(func_info)
                elif name:
                    # 普通变量
                    type_hint = None
                    for decl_child in child.children:
                        if decl_child.type == "type_annotation":
                            type_hint = self._get_node_text(decl_child, source).lstrip(": ")

                    module_info.variables.append(PropertyInfo(
                        name=name,
                        type_hint=type_hint,
                        visibility=self._get_visibility(name),
                    ))

    def _parse_variable_declaration(
        self,
        node,
        source: str,
        module_info: ModuleInfo,
        module_name: str
    ) -> None:
        """解析 var 声明"""
        self._parse_lexical_declaration(node, source, module_info, module_name)

    def _parse_arrow_function(
        self,
        node,
        source: str,
        name: str,
        module_name: str
    ) -> FunctionInfo:
        """解析箭头函数"""
        full_name = f"{module_name}.{name}"
        visibility = self._get_visibility(name)

        parameters = []
        return_type = None
        is_async = False

        for child in node.children:
            if child.type == "formal_parameters":
                parameters = self._parse_parameters(child, source)
            elif child.type == "type_annotation":
                return_type = self._get_node_text(child, source).lstrip(": ")
            elif child.type == "async":
                is_async = True

        func_info = FunctionInfo(
            name=name,
            full_name=full_name,
            parameters=parameters,
            return_type=return_type,
            visibility=visibility,
            is_async=is_async,
            docstring=self._extract_jsdoc(node, source),
            line_start=node.start_point[0] + 1,
            line_end=node.end_point[0] + 1,
        )

        # React 函数组件检测
        if self._is_react_function_component(node, source):
            func_info.docstring = f"{func_info.docstring or ''}\nReact Function Component".strip()
            hooks = self._detect_hooks(node, source)
            if hooks:
                func_info.docstring = f"{func_info.docstring}\n使用 Hooks: {', '.join(hooks)}".strip()

        return func_info

    def _is_react_function_component(self, node, source: str) -> bool:
        """检测是否为 React 函数组件"""
        source_text = self._get_node_text(node, source)
        # 检查是否返回 JSX
        if "React" in source_text or "jsx" in source_text or "<" in source_text:
            return True
        # 检查函数名是否为大写开头（React 组件约定）
        return False

    def _detect_hooks(self, node, source: str) -> list[str]:
        """检测使用的 React Hooks"""
        hooks = []
        source_text = self._get_node_text(node, source)

        hook_patterns = [
            "useState", "useEffect", "useContext", "useReducer",
            "useCallback", "useMemo", "useRef", "useImperativeHandle",
            "useLayoutEffect", "useDebugValue", "useId"
        ]

        for hook in hook_patterns:
            if hook in source_text:
                hooks.append(hook)

        return hooks

    def _get_visibility(self, name: str) -> Visibility:
        """获取可见性"""
        if name.startswith("__") and not name.endswith("__"):
            return Visibility.PRIVATE
        elif name.startswith("_"):
            return Visibility.PROTECTED
        return Visibility.PUBLIC

    def _extract_jsdoc(self, node, source: str) -> Optional[str]:
        """提取 JSDoc 注释"""
        # 查找节点前的注释
        line_start = node.start_point[0]

        # 简单实现：查找行前的注释
        lines = source.split("\n")
        comments = []

        for i in range(line_start - 1, -1, -1):
            line = lines[i].strip()
            if line.startswith("//"):
                comments.insert(0, line[2:].strip())
            elif line.startswith("/*") and not line.startswith("/**"):
                break
            elif line.startswith("/**"):
                comments.insert(0, line)
                break
            elif line == "" or line.startswith("*"):
                if line.startswith("*"):
                    comments.insert(0, line.lstrip("* "))
            else:
                break

        if comments:
            return "\n".join(comments)
        return None

    def _parse_enum(self, node, source: str, module_name: str) -> ClassInfo:
        """解析 TypeScript 枚举"""
        name = ""
        is_const = False

        for child in node.children:
            if child.type == "const":
                is_const = True
            elif child.type == "identifier":
                name = self._get_node_text(child, source)

        full_name = f"{module_name}.{name}"
        visibility = self._get_visibility(name)

        enum_info = ClassInfo(
            name=name,
            full_name=full_name,
            visibility=visibility,
            is_enum=True,
            docstring=f"{'const ' if is_const else ''}enum\n{self._extract_jsdoc(node, source) or ''}".strip(),
            line_start=node.start_point[0] + 1,
            line_end=node.end_point[0] + 1,
        )

        # 解析枚举成员
        for child in node.children:
            if child.type == "enum_body":
                for member in child.children:
                    if member.type == "property_identifier" or member.type == "identifier":
                        member_name = self._get_node_text(member, source)
                        enum_info.class_variables.append(PropertyInfo(
                            name=member_name,
                            visibility=Visibility.PUBLIC,
                        ))
                    elif member.type == "enum_assignment":
                        # 枚举成员赋值
                        for assign_child in member.children:
                            if assign_child.type == "property_identifier":
                                member_name = self._get_node_text(assign_child, source)
                                enum_info.class_variables.append(PropertyInfo(
                                    name=member_name,
                                    visibility=Visibility.PUBLIC,
                                ))

        return enum_info

    def _parse_namespace(self, node, source: str, module_name: str) -> Optional[ModuleInfo]:
        """解析 TypeScript 命名空间"""
        name = ""

        for child in node.children:
            if child.type == "identifier":
                name = self._get_node_text(child, source)

        if not name:
            return None

        full_name = f"{module_name}.{name}"

        namespace_info = ModuleInfo(
            name=full_name,
            file_path=Path(),  # 命名空间没有独立文件
            docstring=self._extract_jsdoc(node, source),
        )

        # 解析命名空间内容
        for child in node.children:
            if child.type == "statement_block":
                for stmt in child.children:
                    if stmt.type == "export_statement":
                        self._parse_export(stmt, source, namespace_info)
                    elif stmt.type == "class_declaration":
                        class_info = self._parse_class(stmt, source, full_name)
                        if self.include_private or class_info.visibility != Visibility.PRIVATE:
                            namespace_info.classes.append(class_info)
                    elif stmt.type == "interface_declaration":
                        interface_info = self._parse_interface(stmt, source, full_name)
                        if self.include_private or interface_info.visibility != Visibility.PRIVATE:
                            namespace_info.classes.append(interface_info)
                    elif stmt.type == "function_declaration":
                        func_info = self._parse_function(stmt, source, full_name)
                        if self.include_private or func_info.visibility != Visibility.PRIVATE:
                            namespace_info.functions.append(func_info)
                    elif stmt.type == "enum_declaration":
                        enum_info = self._parse_enum(stmt, source, full_name)
                        if self.include_private or enum_info.visibility != Visibility.PRIVATE:
                            namespace_info.classes.append(enum_info)

        return namespace_info

    def _parse_module_declaration(self, node, source: str, module_name: str) -> Optional[ModuleInfo]:
        """解析 TypeScript 模块声明"""
        name = ""

        for child in node.children:
            if child.type == "string":
                # 模块名可能是字符串，如 declare module "foo"
                name = self._get_node_text(child, source).strip('"\'')
            elif child.type == "identifier":
                name = self._get_node_text(child, source)

        if not name:
            return None

        full_name = f"{module_name}.{name}"

        module_decl_info = ModuleInfo(
            name=full_name,
            file_path=Path(),
            docstring=f"Module\n{self._extract_jsdoc(node, source) or ''}".strip(),
        )

        # 解析模块内容
        for child in node.children:
            if child.type == "statement_block":
                for stmt in child.children:
                    if stmt.type == "export_statement":
                        self._parse_export(stmt, source, module_decl_info)
                    elif stmt.type == "interface_declaration":
                        interface_info = self._parse_interface(stmt, source, full_name)
                        if self.include_private or interface_info.visibility != Visibility.PRIVATE:
                            module_decl_info.classes.append(interface_info)
                    elif stmt.type == "type_alias_declaration":
                        self._parse_type_alias(stmt, source, module_decl_info)

        return module_decl_info

    def _extract_dependencies(self, module_info: ModuleInfo) -> list[DependencyInfo]:
        """提取依赖关系"""
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
