"""
架构文档生成器
"""

import json
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
from pywiki.agents.architecture_agent import ArchitectureAgent, AgentContext


class ArchitectureDocGenerator(BaseDocGenerator):
    """架构文档生成器"""

    doc_type = DocType.ARCHITECTURE
    template_name = "architecture.md.j2"

    def __init__(
        self,
        language: Language = Language.ZH,
        template_dir: Optional[Path] = None,
    ):
        super().__init__(language, template_dir)
        self.architecture_agent = ArchitectureAgent()

    async def generate(self, context: DocGeneratorContext) -> DocGeneratorResult:
        """生成架构文档"""
        try:
            arch_data = await self._analyze_architecture(context)
            
            if context.metadata.get("llm_client"):
                enhanced_data = await self._enhance_with_llm(
                    context,
                    arch_data,
                    context.metadata["llm_client"]
                )
                arch_data.update(enhanced_data)

            content = self.render_template(
                description=f"{context.project_name} 系统架构文档",
                c4_context=arch_data.get("c4_context", ""),
                c4_container=arch_data.get("c4_container", ""),
                c4_component=arch_data.get("c4_component", ""),
                dependency_graph=arch_data.get("dependency_graph", ""),
                layers=arch_data.get("layers", []),
                metrics=arch_data.get("metrics", []),
                quality_metrics=arch_data.get("quality_metrics", {}),
                circular_dependencies=arch_data.get("circular_dependencies", []),
                hot_spots=arch_data.get("hot_spots", []),
                recommendations=arch_data.get("recommendations", []),
            )

            return self.create_result(
                content=content,
                context=context,
                success=True,
                message="架构文档生成成功",
                metadata={"architecture_data": arch_data.get("summary", {})},
            )

        except Exception as e:
            return self.create_result(
                content="",
                context=context,
                success=False,
                message=f"生成失败: {str(e)}",
            )

    async def _analyze_architecture(self, context: DocGeneratorContext) -> dict[str, Any]:
        """分析架构"""
        arch_data = {
            "c4_context": "",
            "c4_container": "",
            "c4_component": "",
            "dependency_graph": "",
            "layers": [],
            "metrics": [],
            "quality_metrics": {},
            "circular_dependencies": [],
            "hot_spots": [],
            "recommendations": [],
            "summary": {},
        }

        if context.metadata.get("llm_client"):
            self.architecture_agent.llm_client = context.metadata["llm_client"]

        agent_context = AgentContext(
            project_path=context.project_path,
            project_name=context.project_name,
        )

        try:
            result = await self.architecture_agent.execute(agent_context)
            
            if result.success and result.data:
                data = result.data
                
                if "metrics" in data:
                    arch_data["metrics"] = [
                        {
                            "name": name,
                            "score": info.get("score", 0),
                            "description": info.get("description", ""),
                        }
                        for name, info in data["metrics"].items()
                    ]
                
                if "recommendations" in data:
                    arch_data["recommendations"] = data["recommendations"]
                
                if "dependencies" in data:
                    arch_data["summary"]["dependencies"] = data["dependencies"]
                
                arch_data["summary"]["overall_score"] = data.get("overall_score", 0)
        except Exception:
            pass

        arch_data["c4_context"] = self._generate_c4_context(context)
        arch_data["c4_container"] = self._generate_c4_container(context)
        arch_data["c4_component"] = self._generate_c4_component(context)
        arch_data["dependency_graph"] = self._generate_dependency_graph(context)
        arch_data["layers"] = self._analyze_layers(context)
        arch_data["quality_metrics"] = self._calculate_quality_metrics(context)
        arch_data["circular_dependencies"] = self._detect_circular_dependencies(context)
        arch_data["hot_spots"] = self._detect_hot_spots(context)

        return arch_data

    def _generate_c4_context(self, context: DocGeneratorContext) -> str:
        """生成 C4 上下文图"""
        lines = [
            "graph TB",
            f"    System[{context.project_name}<br/>软件系统]",
            "    User[用户]",
            "    User --> System",
        ]

        if context.parse_result and context.parse_result.modules:
            external_deps = {}
            for module in context.parse_result.modules:
                for imp in module.imports:
                    if not imp.module.startswith(".") and not imp.module.startswith(context.project_name.split("-")[0]):
                        base = imp.module.split(".")[0]
                        if base not in ("typing", "os", "sys", "json", "pathlib", "asyncio", "abc", "dataclasses", "collections", "functools", "itertools", "re", "logging", "time", "datetime", "copy", "enum", "io", "warnings", "contextlib", "threading", "multiprocessing", "concurrent"):
                            if base not in external_deps:
                                external_deps[base] = 0
                            external_deps[base] += 1

            sorted_deps = sorted(external_deps.items(), key=lambda x: x[1], reverse=True)[:8]
            for dep, count in sorted_deps:
                safe_name = dep.replace("-", "_").replace(".", "_")
                lines.append(f"    {safe_name}[{dep}<br/>外部系统]")
                lines.append(f"    System -->|使用| {safe_name}")

        return "\n".join(lines)

    def _generate_c4_container(self, context: DocGeneratorContext) -> str:
        """生成 C4 容器图"""
        lines = [
            "graph TB",
            f"    subgraph System[{context.project_name}]",
        ]

        if context.parse_result and context.parse_result.modules:
            module_groups: dict[str, list] = {}
            
            for module in context.parse_result.modules:
                parts = module.name.split(".")
                if len(parts) > 1:
                    group = parts[0]
                else:
                    group = "core"
                
                if group not in module_groups:
                    module_groups[group] = []
                module_groups[group].append(module.name)

            group_info = []
            for group, modules in module_groups.items():
                class_count = sum(1 for m in context.parse_result.modules if m.name in modules for _ in m.classes) if context.parse_result else 0
                group_info.append((group, len(modules), class_count))
            
            group_info.sort(key=lambda x: x[1], reverse=True)
            
            for group, module_count, class_count in group_info[:8]:
                safe_name = group.replace("-", "_").replace(".", "_")
                lines.append(f"        {safe_name}[{group}<br/>{module_count} 模块]")
                lines.append(f"        {safe_name}:::container")

        lines.append("    end")
        lines.append("    classDef container fill:#1168bd,stroke:#0b4884,color:#fff")

        return "\n".join(lines)

    def _generate_c4_component(self, context: DocGeneratorContext) -> str:
        """生成 C4 组件图"""
        lines = ["graph TB"]

        if not context.parse_result or not context.parse_result.modules:
            return "\n".join(lines)

        module_groups: dict[str, list] = defaultdict(list)
        
        for module in context.parse_result.modules:
            parts = module.name.split(".")
            group = parts[0] if len(parts) > 1 else "core"
            module_groups[group].append(module)

        for group, modules in list(module_groups.items())[:4]:
            safe_group = group.replace("-", "_").replace(".", "_")
            lines.append(f"    subgraph {safe_group}[{group}]")
            
            for module in modules[:5]:
                safe_name = module.name.replace(".", "_").replace("-", "_")[:20]
                display_name = module.name.split(".")[-1]
                class_count = len(module.classes) if module.classes else 0
                func_count = len(module.functions) if module.functions else 0
                lines.append(f"        {safe_name}[{display_name}<br/>{class_count} 类, {func_count} 函数]")
            
            lines.append("    end")

        return "\n".join(lines)

    def _generate_dependency_graph(self, context: DocGeneratorContext) -> str:
        """生成依赖关系图"""
        lines = ["graph LR"]

        if not context.parse_result or not context.parse_result.modules:
            return "\n".join(lines)

        modules = context.parse_result.modules[:20]
        
        module_map = {}
        for module in modules:
            safe_name = module.name.replace(".", "_").replace("-", "_")[:25]
            module_map[module.name] = safe_name
            display_name = module.name.split(".")[-1] if "." in module.name else module.name
            lines.append(f"    {safe_name}[{display_name}]")

        dependency_counts: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
        
        for module in modules:
            source_safe = module_map[module.name]
            
            if hasattr(module, 'imports') and module.imports:
                for imp in module.imports:
                    target_module = None
                    
                    for other_module in modules:
                        if other_module.name == imp.module or other_module.name.startswith(imp.module + "."):
                            target_module = other_module.name
                            break
                    
                    if target_module and target_module in module_map:
                        target_safe = module_map[target_module]
                        dependency_counts[source_safe][target_safe] += 1

        added_edges = set()
        for source, targets in dependency_counts.items():
            for target, count in targets.items():
                edge_key = f"{source}->{target}"
                if edge_key not in added_edges:
                    if count > 2:
                        lines.append(f"    {source} -->|{count}x| {target}")
                    else:
                        lines.append(f"    {source} --> {target}")
                    added_edges.add(edge_key)

        return "\n".join(lines)

    def _analyze_layers(self, context: DocGeneratorContext) -> list[dict[str, Any]]:
        """分析分层架构"""
        layers = []

        layer_patterns = {
            "表现层": {
                "keywords": ["api", "controller", "view", "handler", "endpoint", "route", "router", "http", "rest", "graphql", "web"],
                "description": "处理外部请求，负责数据展示和用户交互",
            },
            "业务层": {
                "keywords": ["service", "business", "domain", "usecase", "application", "logic", "manager", "processor"],
                "description": "实现核心业务逻辑和业务规则",
            },
            "数据层": {
                "keywords": ["repository", "dao", "model", "entity", "data", "persistence", "store", "mapper", "schema"],
                "description": "负责数据持久化和数据访问",
            },
            "基础设施层": {
                "keywords": ["infrastructure", "config", "util", "common", "helper", "lib", "core", "base", "foundation"],
                "description": "提供技术支持和基础设施服务",
            },
            "代理层": {
                "keywords": ["agent", "broker", "proxy", "client", "adapter", "connector"],
                "description": "负责与外部系统交互和集成",
            },
        }

        if not context.parse_result or not context.parse_result.modules:
            return layers

        layer_modules: dict[str, list] = defaultdict(list)
        assigned_modules = set()

        for module in context.parse_result.modules:
            module_lower = module.name.lower()
            
            for layer_name, layer_info in layer_patterns.items():
                if any(kw in module_lower for kw in layer_info["keywords"]):
                    layer_modules[layer_name].append(module)
                    assigned_modules.add(module.name)
                    break

        for module in context.parse_result.modules:
            if module.name not in assigned_modules:
                if module.classes:
                    has_entity = any("Model" in c.name or "Entity" in c.name for c in module.classes)
                    has_service = any("Service" in c.name for c in module.classes)
                    
                    if has_entity:
                        layer_modules["数据层"].append(module)
                    elif has_service:
                        layer_modules["业务层"].append(module)
                    else:
                        layer_modules["基础设施层"].append(module)

        for layer_name, layer_info in layer_patterns.items():
            modules = layer_modules.get(layer_name, [])
            if modules:
                components = []
                for module in modules[:8]:
                    class_count = len(module.classes) if module.classes else 0
                    func_count = len(module.functions) if module.functions else 0
                    
                    components.append({
                        "name": module.name.split(".")[-1],
                        "full_name": module.name,
                        "responsibility": module.docstring.split("\n")[0] if module.docstring else "",
                        "class_count": class_count,
                        "func_count": func_count,
                    })

                layers.append({
                    "name": layer_name,
                    "description": layer_info["description"],
                    "component_count": len(modules),
                    "components": components,
                })

        return layers

    def _calculate_quality_metrics(self, context: DocGeneratorContext) -> dict[str, Any]:
        """计算架构质量指标"""
        metrics = {
            "coupling": {"value": 0, "level": "unknown", "description": ""},
            "cohesion": {"value": 0, "level": "unknown", "description": ""},
            "dependency_depth": {"value": 0, "level": "unknown", "description": ""},
            "module_count": 0,
            "class_count": 0,
            "function_count": 0,
            "avg_methods_per_class": 0,
            "avg_functions_per_module": 0,
        }

        if not context.parse_result or not context.parse_result.modules:
            return metrics

        modules = context.parse_result.modules
        metrics["module_count"] = len(modules)

        total_classes = 0
        total_functions = 0
        total_methods = 0
        total_imports = 0
        import_counts: dict[str, int] = defaultdict(int)

        for module in modules:
            class_count = len(module.classes) if module.classes else 0
            func_count = len(module.functions) if module.functions else 0
            
            total_classes += class_count
            total_functions += func_count

            for cls in (module.classes or []):
                total_methods += len(cls.methods) if cls.methods else 0

            for imp in (module.imports or []):
                if not imp.module.startswith("."):
                    base = imp.module.split(".")[0]
                    import_counts[base] += 1
                    total_imports += 1

        metrics["class_count"] = total_classes
        metrics["function_count"] = total_functions

        if total_classes > 0:
            metrics["avg_methods_per_class"] = round(total_methods / total_classes, 1)

        if len(modules) > 0:
            metrics["avg_functions_per_module"] = round(total_functions / len(modules), 1)

        if len(modules) > 1:
            unique_imports = len(import_counts)
            coupling_ratio = unique_imports / len(modules)
            
            if coupling_ratio < 0.3:
                metrics["coupling"] = {"value": round(coupling_ratio * 100, 1), "level": "low", "description": "模块间耦合度较低，架构清晰"}
            elif coupling_ratio < 0.6:
                metrics["coupling"] = {"value": round(coupling_ratio * 100, 1), "level": "medium", "description": "模块间存在适度耦合"}
            else:
                metrics["coupling"] = {"value": round(coupling_ratio * 100, 1), "level": "high", "description": "模块间耦合度较高，建议重构"}

        if total_classes > 0 and total_methods > 0:
            avg_methods = total_methods / total_classes
            if avg_methods > 10:
                metrics["cohesion"] = {"value": round(avg_methods, 1), "level": "low", "description": "类可能职责过多，内聚性较低"}
            elif avg_methods > 5:
                metrics["cohesion"] = {"value": round(avg_methods, 1), "level": "medium", "description": "类内聚性适中"}
            else:
                metrics["cohesion"] = {"value": round(avg_methods, 1), "level": "high", "description": "类职责单一，内聚性较好"}

        max_depth = 0
        for module in modules:
            depth = module.name.count(".")
            max_depth = max(max_depth, depth)
        
        metrics["dependency_depth"] = {"value": max_depth, "level": "ok" if max_depth < 4 else "deep", "description": f"最大依赖深度 {max_depth} 层"}

        return metrics

    def _detect_circular_dependencies(self, context: DocGeneratorContext) -> list[dict[str, Any]]:
        """检测循环依赖"""
        circular = []

        if not context.parse_result or not context.parse_result.modules:
            return circular

        module_names = {m.name for m in context.parse_result.modules}
        dependencies: dict[str, set] = defaultdict(set)

        for module in context.parse_result.modules:
            for imp in module.imports:
                if imp.module in module_names or imp.module.startswith("."):
                    target = imp.module if imp.module in module_names else module.name.rsplit(".", 1)[0] + imp.module
                    if target in module_names:
                        dependencies[module.name].add(target)

        def find_cycle(start: str, current: str, path: list, visited: set) -> Optional[list]:
            if current in visited:
                if current == start and len(path) > 1:
                    return path
                return None
            
            visited.add(current)
            path.append(current)
            
            for dep in dependencies.get(current, []):
                result = find_cycle(start, dep, path.copy(), visited.copy())
                if result:
                    return result
            
            return None

        found_cycles = set()
        for module in context.parse_result.modules:
            cycle = find_cycle(module.name, module.name, [], set())
            if cycle:
                cycle_key = "->".join(sorted(cycle))
                if cycle_key not in found_cycles:
                    found_cycles.add(cycle_key)
                    circular.append({
                        "cycle": cycle,
                        "severity": "high" if len(cycle) <= 3 else "medium",
                        "description": f"循环依赖: {' -> '.join(cycle)}",
                    })

        return circular[:5]

    def _detect_hot_spots(self, context: DocGeneratorContext) -> list[dict[str, Any]]:
        """检测热点模块（被大量依赖的模块）"""
        hot_spots = []

        if not context.parse_result or not context.parse_result.modules:
            return hot_spots

        incoming_counts: dict[str, int] = defaultdict(int)
        outgoing_counts: dict[str, int] = defaultdict(int)
        module_names = {m.name for m in context.parse_result.modules}

        for module in context.parse_result.modules:
            for imp in module.imports:
                if imp.module in module_names:
                    incoming_counts[imp.module] += 1
                    outgoing_counts[module.name] += 1

        for module in context.parse_result.modules:
            incoming = incoming_counts.get(module.name, 0)
            outgoing = outgoing_counts.get(module.name, 0)
            
            if incoming > 3 or outgoing > 5:
                hot_spots.append({
                    "name": module.name,
                    "incoming": incoming,
                    "outgoing": outgoing,
                    "total": incoming + outgoing,
                    "risk": "high" if incoming > 5 else "medium",
                    "description": f"被 {incoming} 个模块依赖，依赖 {outgoing} 个模块",
                })

        hot_spots.sort(key=lambda x: x["total"], reverse=True)
        return hot_spots[:10]

    async def _enhance_with_llm(
        self,
        context: DocGeneratorContext,
        arch_data: dict[str, Any],
        llm_client: Any,
    ) -> dict[str, Any]:
        """使用 LLM 增强架构文档"""

        enhanced = {}
        
        quality_metrics = arch_data.get("quality_metrics", {})
        layers = arch_data.get("layers", [])

        prompt = f"""基于以下架构分析，提供更深入的架构洞察：

项目: {context.project_name}
分层: {[l['name'] for l in layers]}
模块数: {quality_metrics.get('module_count', 0)}
类数: {quality_metrics.get('class_count', 0)}
耦合度: {quality_metrics.get('coupling', {}).get('level', 'unknown')}
内聚性: {quality_metrics.get('cohesion', {}).get('level', 'unknown')}
循环依赖: {len(arch_data.get('circular_dependencies', []))}
热点模块: {len(arch_data.get('hot_spots', []))}

请以 JSON 格式返回：
{{
    "architecture_style": "架构风格（如分层架构、微服务等）",
    "strengths": ["优势1", "优势2"],
    "weaknesses": ["劣势1", "劣势2"],
    "improvement_suggestions": ["改进建议1", "改进建议2"],
    "risk_assessment": "风险评估"
}}
"""

        try:
            response = await llm_client.agenerate(prompt)
            start = response.find("{")
            end = response.rfind("}")
            if start != -1 and end != -1:
                result = json.loads(response[start:end+1])
                
                if result.get("architecture_style"):
                    enhanced["architecture_style"] = result["architecture_style"]
                
                if result.get("strengths"):
                    enhanced["strengths"] = result["strengths"]
                
                if result.get("weaknesses"):
                    enhanced["weaknesses"] = result["weaknesses"]
                
                if result.get("risk_assessment"):
                    enhanced["risk_assessment"] = result["risk_assessment"]
                
                if result.get("improvement_suggestions"):
                    for suggestion in result["improvement_suggestions"]:
                        arch_data["recommendations"].append({
                            "title": "AI 建议",
                            "priority": "medium",
                            "description": suggestion,
                        })
        except Exception:
            pass

        return enhanced
