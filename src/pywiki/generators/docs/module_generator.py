"""
模块文档生成器
支持多级分组和抽象聚合
"""

from collections import defaultdict
from pathlib import Path
from typing import Any, Optional

from pywiki.generators.docs.base import (
    BaseDocGenerator,
    DocGeneratorContext,
    DocGeneratorResult,
    DocType,
)
from pywiki.config.models import Language


class ModuleGenerator(BaseDocGenerator):
    """模块文档生成器 - 支持高阶抽象聚合"""

    doc_type = DocType.MODULE
    template_name = "module.md.j2"

    # 架构分层模式
    LAYER_PATTERNS = {
        "presentation": [
            "ui", "view", "component", "page", "screen", "controller",
            "api", "endpoint", "route", "handler", "web", "http", "rest",
            "servlet", "filter", "interceptor", "advice"
        ],
        "business": [
            "service", "usecase", "interactor", "domain", "logic",
            "manager", "processor", "application", "core", "biz",
            "workflow", "flow", "task"
        ],
        "data": [
            "repository", "dao", "model", "entity", "dto", "schema",
            "data", "store", "db", "persistence", "mapper", "po", "vo",
            "convert", "converter"
        ],
        "infrastructure": [
            "config", "util", "helper", "common", "base",
            "infrastructure", "infra", "shared", "lib",
            "annotation", "constant", "enum", "exception"
        ],
    }

    # 业务领域关键词
    DOMAIN_KEYWORDS = {
        "tenant": ["tenant", "多租户", "租户"],
        "dict": ["dict", "dictionary", "字典"],
        "excel": ["excel", "export", "import", "导出", "导入"],
        "quartz": ["quartz", "job", "schedule", "定时", "任务"],
        "mq": ["mq", "message", "queue", "kafka", "rabbitmq", "rocketmq", "消息"],
        "security": ["security", "auth", "permission", "role", "安全", "权限"],
        "flowable": ["flowable", "bpmn", "workflow", "流程"],
        "pay": ["pay", "payment", "order", "支付"],
        "member": ["member", "user", "用户", "会员"],
        "system": ["system", "sys", "系统"],
    }

    def __init__(
        self,
        language: Language = Language.ZH,
        template_dir: Optional[Path] = None,
    ):
        super().__init__(language, template_dir)

    async def generate(self, context: DocGeneratorContext) -> DocGeneratorResult:
        """生成模块索引文档"""
        try:
            modules_info = self._extract_modules_info(context)
            dependency_graph = self._generate_dependency_graph(context, modules_info)
            package_analysis = self._extract_package_analysis(context)
            package_dependency_diagram = self._generate_package_dependency_diagram(context, package_analysis)

            # 构建包层级结构
            package_tree = self._build_package_tree(modules_info)

            content = self._generate_index_content(
                context, modules_info, package_tree,
                dependency_graph, package_analysis, package_dependency_diagram
            )

            return self.create_result(
                content=content,
                context=context,
                success=True,
                message=self.labels.get("module_doc_success", "Module documentation generated successfully"),
                metadata={
                    "module_count": len(modules_info),
                    "total_classes": sum(len(m["classes"]) for m in modules_info),
                    "total_functions": sum(len(m["functions"]) for m in modules_info),
                    "package_count": len(package_tree),
                },
            )

        except Exception as e:
            return self.create_result(
                content="",
                context=context,
                success=False,
                message=f"{self.labels.get('generation_failed', 'Generation failed')}: {str(e)}",
            )

    def _extract_modules_info(self, context: DocGeneratorContext) -> list[dict[str, Any]]:
        """提取模块信息"""
        modules_info = []

        if not context.parse_result or not context.parse_result.modules:
            return modules_info

        invalid_module_patterns = [
            'package-info', 'package_info',
            'module-info', 'module_info',
            '.git', '.svn', '.hg',
            '__pycache__', '.pytest_cache',
            'node_modules', 'vendor',
            'target', 'build', 'dist', 'out',
            '.idea', '.vscode',
        ]

        for module in context.parse_result.modules:
            module_name = module.name

            is_invalid = False
            for pattern in invalid_module_patterns:
                if pattern in module_name.lower():
                    is_invalid = True
                    break

            if is_invalid:
                continue

            if len(module_name) < 3:
                continue

            clean_name = module_name.replace(';', '.').replace(' ', '')
            if not clean_name.replace('.', '').replace('_', '').isalnum():
                continue

            path = clean_name.replace(".", "/")

            # 检查模块是否有实质内容
            has_content = False
            if hasattr(module, 'classes') and module.classes:
                has_content = True
            if hasattr(module, 'functions') and module.functions:
                has_content = True
            if hasattr(module, 'variables') and module.variables:
                has_content = True

            if not has_content:
                submodules = getattr(module, 'submodules', [])
                if not submodules:
                    continue

            module_info = {
                "name": clean_name,
                "path": path,
                "file_path": str(module.file_path) if hasattr(module, 'file_path') and module.file_path else "",
                "description": module.docstring.split("\n")[0] if module.docstring else "",
                "full_docstring": module.docstring or "",
                "line_count": getattr(module, 'line_count', 0),
                "classes": [],
                "functions": [],
                "variables": [],
                "imports": [],
                "exports": [],
                "submodules": getattr(module, 'submodules', []),
            }

            for cls in (module.classes or []):
                class_info = {
                    "name": cls.name,
                    "docstring": cls.docstring or "",
                    "short_docstring": (cls.docstring or "").split("\n")[0],
                    "bases": cls.bases,
                    "decorators": getattr(cls, 'decorators', []),
                    "is_abstract": getattr(cls, 'is_abstract', False),
                    "is_dataclass": getattr(cls, 'is_dataclass', False),
                    "is_enum": getattr(cls, 'is_enum', False),
                    "line_start": getattr(cls, 'line_start', 0),
                    "line_end": getattr(cls, 'line_end', 0),
                    "properties": [],
                    "methods": [],
                    "class_variables": [],
                }

                for prop in (cls.properties or []):
                    class_info["properties"].append({
                        "name": prop.name,
                        "type_hint": prop.type_hint or "",
                        "visibility": prop.visibility.value if hasattr(prop.visibility, 'value') else str(prop.visibility),
                        "is_readonly": getattr(prop, 'is_readonly', False),
                        "default_value": getattr(prop, 'default_value', None),
                        "decorators": getattr(prop, 'decorators', []),
                    })

                for method in (cls.methods or []):
                    params = []
                    for p in (method.parameters or []):
                        params.append({
                            "name": p.name,
                            "type_hint": getattr(p, 'type_hint', '') or "",
                            "default_value": getattr(p, 'default_value', None),
                            "kind": getattr(p, 'kind', 'POSITIONAL_OR_KEYWORD'),
                        })

                    class_info["methods"].append({
                        "name": method.name,
                        "parameters": params,
                        "params_str": ", ".join([p["name"] + (f": {p['type_hint']}" if p['type_hint'] else "") for p in params]),
                        "return_type": method.return_type or "",
                        "docstring": method.docstring or "",
                        "short_docstring": (method.docstring or "").split("\n")[0],
                        "raises": getattr(method, 'raises', []) or [],
                        "examples": getattr(method, 'examples', []) or [],
                        "decorators": getattr(method, 'decorators', []),
                        "is_async": getattr(method, 'is_async', False),
                        "is_classmethod": getattr(method, 'is_classmethod', False),
                        "is_staticmethod": getattr(method, 'is_staticmethod', False),
                        "is_abstract": getattr(method, 'is_abstract', False),
                        "is_property": any("property" in d.lower() for d in getattr(method, 'decorators', [])),
                        "visibility": "private" if method.name.startswith("_") and not method.name.startswith("__") else "public",
                    })

                module_info["classes"].append(class_info)

            for func in (module.functions or []):
                params = []
                for p in (func.parameters or []):
                    params.append({
                        "name": p.name,
                        "type_hint": getattr(p, 'type_hint', '') or "",
                        "default_value": getattr(p, 'default_value', None),
                        "kind": getattr(p, 'kind', 'POSITIONAL_OR_KEYWORD'),
                    })

                module_info["functions"].append({
                    "name": func.name,
                    "parameters": params,
                    "params_str": ", ".join([p["name"] + (f": {p['type_hint']}" if p['type_hint'] else "") for p in params]),
                    "return_type": func.return_type or "",
                    "docstring": func.docstring or "",
                    "short_docstring": (func.docstring or "").split("\n")[0],
                    "raises": getattr(func, 'raises', []) or [],
                    "examples": getattr(func, 'examples', []) or [],
                    "decorators": getattr(func, 'decorators', []),
                    "is_async": getattr(func, 'is_async', False),
                    "is_classmethod": getattr(func, 'is_classmethod', False),
                    "is_staticmethod": getattr(func, 'is_staticmethod', False),
                    "visibility": "private" if func.name.startswith("_") and not func.name.startswith("__") else "public",
                })

            for var in (getattr(module, 'variables', []) or []):
                module_info["variables"].append({
                    "name": var.name,
                    "type_hint": getattr(var, 'type_hint', '') or "",
                    "value": getattr(var, 'value', None),
                    "visibility": "private" if var.name.startswith("_") and not var.name.startswith("__") else "public",
                })

            for imp in (module.imports or []):
                module_info["imports"].append({
                    "module": imp.module,
                    "names": getattr(imp, 'names', []) or [],
                    "alias": getattr(imp, 'alias', ''),
                    "type": "internal" if imp.module.startswith(".") or imp.module.startswith(module.name.split(".")[0]) else "external",
                    "line": getattr(imp, 'line', 0),
                })

            exported_names = []
            for cls in (module.classes or []):
                if not cls.name.startswith("_"):
                    exported_names.append(cls.name)
            for func in (module.functions or []):
                if not func.name.startswith("_"):
                    exported_names.append(func.name)
            module_info["exports"] = exported_names

            modules_info.append(module_info)

        return modules_info

    def _build_package_tree(self, modules_info: list[dict]) -> dict:
        """构建包层级树结构"""
        tree = {}

        for module in modules_info:
            name = module["name"]
            parts = name.split(".")

            # 构建树结构
            current = tree
            for i, part in enumerate(parts):
                if part not in current:
                    current[part] = {
                        "_modules": [],
                        "_children": {},
                        "_depth": i,
                    }
                if i == len(parts) - 1:
                    current[part]["_modules"].append(module)
                current = current[part]["_children"]

        return tree

    def _detect_layer(self, path: str) -> str:
        """检测架构分层"""
        path_lower = path.lower()
        for layer, patterns in self.LAYER_PATTERNS.items():
            for pattern in patterns:
                if pattern in path_lower:
                    return layer
        return "other"

    def _detect_domain(self, path: str) -> str:
        """检测业务领域"""
        path_lower = path.lower()
        for domain, keywords in self.DOMAIN_KEYWORDS.items():
            for keyword in keywords:
                if keyword in path_lower:
                    return domain
        return "other"

    def _aggregate_packages(self, modules_info: list[dict]) -> dict:
        """聚合包信息 - 按业务领域和架构分层"""
        domains = defaultdict(lambda: defaultdict(lambda: {
            "modules": [],
            "total_classes": 0,
            "total_methods": 0,
            "key_classes": [],
            "description_parts": [],
        }))

        for module in modules_info:
            name = module["name"]
            domain = self._detect_domain(name)
            layer = self._detect_layer(name)

            pkg_info = domains[domain][layer]
            pkg_info["modules"].append(module)
            pkg_info["total_classes"] += len(module.get("classes", []))

            method_count = sum(len(c.get("methods", [])) for c in module.get("classes", []))
            pkg_info["total_methods"] += method_count

            # 收集关键类（非私有、非内部类）
            for cls in module.get("classes", [])[:3]:
                if not cls["name"].startswith("_"):
                    pkg_info["key_classes"].append({
                        "name": cls["name"],
                        "module": name,
                        "method_count": len(cls.get("methods", [])),
                    })

            # 收集描述
            if module.get("description"):
                pkg_info["description_parts"].append(module["description"])

        return domains

    def _generate_package_summary(self, pkg_info: dict) -> str:
        """生成包摘要描述"""
        descriptions = pkg_info.get("description_parts", [])
        key_classes = pkg_info.get("key_classes", [])

        if descriptions:
            # 取最常见的描述
            from collections import Counter
            desc_counter = Counter([d[:50] for d in descriptions if len(d) > 10])
            if desc_counter:
                return desc_counter.most_common(1)[0][0]

        # 基于关键类生成描述
        if key_classes:
            class_names = [c["name"] for c in key_classes[:3]]
            return f"包含核心类: {', '.join(class_names)}"

        return ""

    def _generate_index_content(
        self, context: DocGeneratorContext,
        modules_info: list[dict],
        package_tree: dict,
        dependency_graph: str,
        package_analysis: dict[str, Any] = None,
        package_dependency_diagram: str = ""
    ) -> str:
        """生成模块索引内容 - 高阶抽象版本"""
        lines = [
            f"# {context.project_name} {self.labels.get('module_documentation', 'Module Documentation')}",
            "",
        ]

        total_classes = sum(len(m["classes"]) for m in modules_info)
        total_functions = sum(len(m["functions"]) for m in modules_info)
        total_methods = sum(len(c["methods"]) for m in modules_info for c in m["classes"])

        # 聚合包信息
        domains = self._aggregate_packages(modules_info)

        # 概述部分
        lines.extend([
            f"## {self.labels.get('overview', 'Overview')}",
            "",
            f"| {self.labels.get('metrics', 'Metrics')} | {self.labels.get('count', 'Count')} |",
            f"|------|------|",
            f"| {self.labels.get('modules', 'Modules')} | {len(modules_info)} |",
            f"| {self.labels.get('classes', 'Classes')} | {total_classes} |",
            f"| {self.labels.get('functions', 'Functions')} | {total_functions} |",
            f"| {self.labels.get('methods', 'Methods')} | {total_methods} |",
            f"| 业务领域 | {len(domains)} |",
            "",
        ])

        # 业务领域概览
        if domains:
            lines.extend([
                "## 业务领域概览",
                "",
                "| 领域 | 分层数 | 类总数 | 核心功能 |",
                "|------|--------|--------|----------|",
            ])

            for domain, layers in sorted(domains.items()):
                total_domain_classes = sum(l["total_classes"] for l in layers.values())
                layer_names = ", ".join(sorted(layers.keys()))

                # 提取核心功能关键词
                all_classes = []
                for layer_info in layers.values():
                    all_classes.extend([c["name"] for c in layer_info.get("key_classes", [])])

                core_keywords = self._extract_core_keywords(all_classes[:10])

                lines.append(f"| **{domain}** | {len(layers)} | {total_domain_classes} | {core_keywords} |")

            lines.append("")

        # 架构分层统计
        if package_analysis and package_analysis.get("layers"):
            lines.extend([
                "## 架构分层",
                "",
                "| 层级 | 包数量 | 描述 |",
                "|------|--------|------|",
            ])
            for layer in package_analysis.get("layers", []):
                lines.append(f"| {layer.get('name', '')} | {len(layer.get('packages', []))} | {layer.get('description', '')} |")
            lines.append("")

        # 包依赖关系图
        if package_dependency_diagram:
            lines.extend([
                "## 包依赖关系图",
                "",
                "```mermaid",
                f"{package_dependency_diagram}",
                "```",
                "",
            ])

        # 详细业务领域模块
        lines.extend([
            "## 业务领域详情",
            "",
        ])

        for domain, layers in sorted(domains.items()):
            lines.append(f"### {domain}")
            lines.append("")

            # 计算领域统计
            domain_modules = []
            domain_classes = 0
            for layer_info in layers.values():
                domain_modules.extend(layer_info["modules"])
                domain_classes += layer_info["total_classes"]

            lines.append(f"> **模块数**: {len(domain_modules)} | **类数**: {domain_classes}")
            lines.append("")

            # 按架构分层展示
            for layer, layer_info in sorted(layers.items()):
                if not layer_info["modules"]:
                    continue

                lines.append(f"#### {layer} 层")
                lines.append("")

                # 包摘要
                summary = self._generate_package_summary(layer_info)
                if summary:
                    lines.append(f"*{summary}*")
                    lines.append("")

                # 关键类列表（聚合展示，不展开每个模块）
                key_classes = layer_info.get("key_classes", [])
                if key_classes:
                    lines.append("**核心类**:")
                    for cls in sorted(key_classes, key=lambda x: x["method_count"], reverse=True)[:5]:
                        lines.append(f"- `{cls['name']}` ({cls['method_count']} 方法)")
                    lines.append("")

                # 只展示重要模块的链接（类数>1或有复杂功能的）
                important_modules = [
                    m for m in layer_info["modules"]
                    if len(m.get("classes", [])) > 1 or len(m.get("functions", [])) > 0
                ]

                if important_modules:
                    lines.append("**重要模块**:")
                    for module in sorted(important_modules, key=lambda x: len(x.get("classes", [])), reverse=True)[:5]:
                        class_count = len(module.get("classes", []))
                        func_count = len(module.get("functions", []))
                        lines.append(f"- [{module['name']}](modules/{module['path']}.md) ({class_count} 类, {func_count} 函数)")
                    lines.append("")

            lines.append("---")
            lines.append("")

        lines.extend([
            "",
            f"*{self.labels.get('doc_generated_at', 'Document generated at')}: {self._get_current_time()}*",
        ])

        return "\n".join(lines)

    def _extract_core_keywords(self, class_names: list[str]) -> str:
        """从类名中提取核心功能关键词"""
        keywords = []
        for name in class_names:
            # 提取有意义的词
            if "Controller" in name:
                keywords.append("API控制")
            elif "Service" in name:
                keywords.append("业务服务")
            elif "Repository" in name or "Dao" in name:
                keywords.append("数据访问")
            elif "Config" in name:
                keywords.append("配置")
            elif "Util" in name or "Utils" in name:
                keywords.append("工具")
            elif "Interceptor" in name:
                keywords.append("拦截器")
            elif "Listener" in name:
                keywords.append("监听器")
            elif "Handler" in name:
                keywords.append("处理器")

        if not keywords:
            return "-"

        # 去重并限制数量
        unique_keywords = list(dict.fromkeys(keywords))
        return ", ".join(unique_keywords[:3])

    def _generate_dependency_graph(self, context: DocGeneratorContext, modules_info: list[dict]) -> str:
        """生成模块依赖图"""
        if not modules_info or len(modules_info) < 2:
            return ""

        valid_modules = [m for m in modules_info if m.get("name") and len(m["name"]) > 2]

        valid_modules = [m for m in valid_modules if not any(
            p in m["name"].lower() for p in ['package-info', 'module-info']
        )]

        if not valid_modules or len(valid_modules) < 2:
            return ""

        lines = ["graph LR"]

        module_map = {}
        used_names = set()

        for idx, module in enumerate(valid_modules[:20]):
            safe_name = self._generate_safe_id(module["name"], idx, used_names)
            used_names.add(safe_name)
            module_map[module["name"]] = safe_name
            display_name = module["name"].split(".")[-1] if "." in module["name"] else module["name"]
            lines.append(f"    {safe_name}[\"{display_name}\"]")

        added_edges = set()
        for module in valid_modules[:20]:
            source_safe = module_map.get(module["name"])
            if not source_safe:
                continue

            for imp in module.get("imports", []):
                imp_module = imp["module"]

                for other_module in valid_modules[:20]:
                    if other_module["name"] == imp_module or other_module["name"].startswith(imp_module + "."):
                        target_safe = module_map.get(other_module["name"])
                        if target_safe and source_safe != target_safe:
                            edge_key = f"{source_safe}->{target_safe}"
                            if edge_key not in added_edges:
                                lines.append(f"    {source_safe} --> {target_safe}")
                                added_edges.add(edge_key)
                        break

        if len(added_edges) == 0:
            return ""

        return "\n".join(lines)

    def _generate_safe_id(self, name: str, index: int, used_names: set) -> str:
        """生成安全的 Mermaid ID"""
        parts = name.replace(".", "_").replace("-", "_").replace(";", "_").split("_")
        meaningful_parts = [p for p in parts if p and len(p) > 1 and not p.isdigit()]

        if meaningful_parts:
            candidate = "_".join(meaningful_parts[:3])
        else:
            candidate = f"mod_{index}"

        candidate = self._sanitize_name(candidate)

        base_candidate = candidate[:20]
        counter = 1
        while candidate in used_names:
            candidate = f"{base_candidate}_{counter}"
            counter += 1

        return candidate[:30]

    def _sanitize_name(self, name: str) -> str:
        """清理名称"""
        sanitized = name.replace(" ", "_").replace(":", "_")
        sanitized = sanitized.replace("(", "").replace(")", "")
        sanitized = sanitized.replace("[", "").replace("]", "")
        sanitized = sanitized.replace("{", "").replace("}", "")
        while "__" in sanitized:
            sanitized = sanitized.replace("__", "_")
        return sanitized.strip("_")[:30]

    def _extract_package_analysis(self, context: DocGeneratorContext) -> dict[str, Any]:
        """提取包分析数据"""
        try:
            analysis = context.get_package_analysis()
            return {
                "total_packages": analysis.get("summary", {}).get("total_packages", 0),
                "total_dependencies": analysis.get("summary", {}).get("total_dependencies", 0),
                "circular_dependencies": analysis.get("circular_dependencies", []),
                "layers": analysis.get("layers", []),
                "metrics": analysis.get("metrics", []),
                "subpackages": analysis.get("subpackages", []),
                "dependencies": analysis.get("dependencies", []),
                "violations": analysis.get("violations", []),
            }
        except Exception:
            return {}

    def _generate_package_dependency_diagram(self, context: DocGeneratorContext, package_analysis: dict[str, Any]) -> str:
        """生成包依赖图"""
        dependencies = package_analysis.get("dependencies", [])
        if not dependencies:
            return ""

        lines = ["graph LR"]

        package_map = {}
        for dep in dependencies[:30]:
            source = dep.get("source", "")
            target = dep.get("target", "")

            if source and source not in package_map:
                safe_name = source.replace(".", "_").replace(":", "_")[:25]
                package_map[source] = safe_name
                display_name = source.split(".")[-1] if "." in source else source
                lines.append(f"    {safe_name}[{display_name}]")

            if target and target not in package_map:
                safe_name = target.replace(".", "_").replace(":", "_")[:25]
                package_map[target] = safe_name
                display_name = target.split(".")[-1] if "." in target else target
                lines.append(f"    {safe_name}[{display_name}]")

        added_edges = set()
        for dep in dependencies[:30]:
            source = dep.get("source", "")
            target = dep.get("target", "")
            strength = dep.get("strength", 0)

            if source in package_map and target in package_map:
                edge_key = f"{package_map[source]}->{package_map[target]}"
                if edge_key not in added_edges:
                    label = f"|{strength:.1f}|" if strength > 0.3 else ""
                    lines.append(f"    {package_map[source]} -->{label} {package_map[target]}")
                    added_edges.add(edge_key)

        if len(added_edges) == 0:
            return ""

        return "\n".join(lines)

    def _get_current_time(self) -> str:
        """获取当前时间"""
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    async def generate_module_doc(
        self,
        module_info: dict[str, Any],
        context: DocGeneratorContext,
    ) -> str:
        """生成单个模块文档"""
        content = self.render_template(
            module_name=module_info["name"],
            description=module_info["description"],
            full_docstring=module_info["full_docstring"],
            classes=module_info["classes"],
            functions=module_info["functions"],
            variables=module_info["variables"],
            imports=module_info["imports"],
            exports=module_info["exports"],
        )
        return content
