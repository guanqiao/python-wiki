"""
模块文档生成器
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
    """模块文档生成器"""

    doc_type = DocType.MODULE
    template_name = "module.md.j2"

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
            
            content = self._generate_index_content(context, modules_info, dependency_graph, package_analysis, package_dependency_diagram)

            return self.create_result(
                content=content,
                context=context,
                success=True,
                message=self.labels.get("module_doc_success", "Module documentation generated successfully"),
                metadata={
                    "module_count": len(modules_info),
                    "total_classes": sum(len(m["classes"]) for m in modules_info),
                    "total_functions": sum(len(m["functions"]) for m in modules_info),
                    "package_count": package_analysis.get("total_packages", 0),
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

    def _generate_dependency_graph(self, context: DocGeneratorContext, modules_info: list[dict]) -> str:
        """生成模块依赖图"""
        if not modules_info or len(modules_info) < 2:
            return ""

        lines = ["graph LR"]
        
        module_map = {}
        for module in modules_info[:20]:
            safe_name = module["name"].replace(".", "_").replace("-", "_")[:25]
            module_map[module["name"]] = safe_name
            display_name = module["name"].split(".")[-1] if "." in module["name"] else module["name"]
            lines.append(f"    {safe_name}[{display_name}]")

        added_edges = set()
        for module in modules_info[:20]:
            source_safe = module_map[module["name"]]
            
            for imp in module.get("imports", []):
                imp_module = imp["module"]
                
                for other_module in modules_info[:20]:
                    if other_module["name"] == imp_module or other_module["name"].startswith(imp_module + "."):
                        target_safe = module_map[other_module["name"]]
                        edge_key = f"{source_safe}->{target_safe}"
                        if edge_key not in added_edges:
                            lines.append(f"    {source_safe} --> {target_safe}")
                            added_edges.add(edge_key)
                        break

        if len(added_edges) == 0:
            return ""

        return "\n".join(lines)

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

    def _generate_index_content(self, context: DocGeneratorContext, modules_info: list[dict], dependency_graph: str, package_analysis: dict[str, Any] = None, package_dependency_diagram: str = "") -> str:
        """生成模块索引内容"""
        lines = [
            f"# {context.project_name} {self.labels.get('module_documentation', 'Module Documentation')}",
            "",
        ]

        total_classes = sum(len(m["classes"]) for m in modules_info)
        total_functions = sum(len(m["functions"]) for m in modules_info)
        total_methods = sum(len(c["methods"]) for m in modules_info for c in m["classes"])
        total_async = sum(
            1 for m in modules_info 
            for f in m["functions"] 
            if f.get("is_async")
        ) + sum(
            1 for m in modules_info 
            for c in m["classes"] 
            for method in c["methods"] 
            if method.get("is_async")
        )

        lines.extend([
            f"## {self.labels.get('overview', 'Overview')}",
            "",
            f"| {self.labels.get('metrics', 'Metrics')} | {self.labels.get('count', 'Count')} |",
            f"|------|------|",
            f"| {self.labels.get('modules', 'Modules')} | {len(modules_info)} |",
            f"| {self.labels.get('classes', 'Classes')} | {total_classes} |",
            f"| {self.labels.get('functions', 'Functions')} | {total_functions} |",
            f"| {self.labels.get('methods', 'Methods')} | {total_methods} |",
            f"| {self.labels.get('async_functions_methods', 'Async Functions/Methods')} | {total_async} |",
            "",
        ])

        if dependency_graph:
            lines.extend([
                f"## {self.labels.get('module_dependencies', 'Module Dependencies')}",
                "",
                f"```mermaid",
                f"{dependency_graph}",
                f"```",
                "",
            ])

        if package_analysis:
            total_packages = package_analysis.get("total_packages", 0)
            total_pkg_deps = package_analysis.get("total_dependencies", 0)
            circular_deps = package_analysis.get("circular_dependencies", [])
            layers = package_analysis.get("layers", [])
            violations = package_analysis.get("violations", [])
            
            lines.extend([
                "## 包结构分析",
                "",
                f"| 指标 | 数值 |",
                f"|------|------|",
                f"| 子包数量 | {total_packages} |",
                f"| 包间依赖 | {total_pkg_deps} |",
                f"| 循环依赖 | {len(circular_deps)} |",
                f"| 层级违规 | {len(violations)} |",
                "",
            ])
            
            if layers:
                lines.extend([
                    "### 架构分层",
                    "",
                    "| 层级 | 包数量 | 描述 |",
                    "|------|--------|------|",
                ])
                for layer in layers:
                    lines.append(f"| {layer.get('name', '')} | {len(layer.get('packages', []))} | {layer.get('description', '')} |")
                lines.append("")

        if package_dependency_diagram:
            lines.extend([
                "## 包依赖关系图",
                "",
                "```mermaid",
                f"{package_dependency_diagram}",
                "```",
                "",
            ])

        lines.extend([
            f"## {self.labels.get('module_list', 'Module List')}",
            "",
        ])

        module_groups: dict[str, list] = defaultdict(list)
        for module in modules_info:
            parts = module["name"].split(".")
            group = parts[0] if len(parts) > 1 else "core"
            module_groups[group].append(module)

        for group, modules in sorted(module_groups.items()):
            lines.append(f"### {group}")
            lines.append("")
            
            for module in modules:
                lines.append(f"#### [{module['name']}](modules/{module['path']}.md)")
                
                if module['description']:
                    lines.append(f"> {module['description']}")
                
                stats_parts = []
                if module['classes']:
                    stats_parts.append(self.labels.get("n_classes", "{} classes").format(len(module['classes'])))
                if module['functions']:
                    stats_parts.append(self.labels.get("n_functions", "{} functions").format(len(module['functions'])))
                if stats_parts:
                    lines.append(f"**{self.labels.get('statistics', 'Statistics')}**: {', '.join(stats_parts)}")
                
                if module['classes']:
                    class_summary = []
                    for cls in module['classes'][:3]:
                        method_count = len(cls['methods'])
                        prop_count = len(cls['properties'])
                        class_summary.append(f"`{cls['name']}` ({self.labels.get('n_methods', '{} methods').format(method_count)}, {self.labels.get('n_properties', '{} properties').format(prop_count)})")
                    if len(module['classes']) > 3:
                        class_summary.append(self.labels.get("more_n_classes", "... and {} more classes").format(len(module['classes'])))
                    lines.append(f"\n**{self.labels.get('class_label', 'Class')}**: {', '.join(class_summary)}")
                
                if module['functions']:
                    func_summary = []
                    for func in module['functions'][:3]:
                        params = func.get('params_str', '')
                        if len(params) > 30:
                            params = params[:30] + "..."
                        return_type = f" -> {func['return_type']}" if func['return_type'] else ""
                        is_async = "async " if func.get('is_async') else ""
                        func_summary.append(f"`{is_async}{func['name']}({params}){return_type}`")
                    if len(module['functions']) > 3:
                        func_summary.append(self.labels.get("more_n_functions", "... and {} more functions").format(len(module['functions'])))
                    lines.append(f"\n**{self.labels.get('function_label', 'Function')}**: {', '.join(func_summary)}")
                
                external_imports = [i['module'] for i in module['imports'] if i['type'] == 'external'][:5]
                if external_imports:
                    lines.append(f"\n**{self.labels.get('external_deps', 'External Dependencies')}**: {', '.join(external_imports)}")
                
                lines.append("")

        lines.extend([
            "---",
            "",
            f"*{self.labels.get('doc_generated_at', 'Document generated at')}: {self._get_current_time()}*",
        ])

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
