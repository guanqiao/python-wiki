"""
架构文档生成器
支持多种架构风格的自动识别和智能图表生成
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
from pywiki.generators.diagrams.architecture import (
    ArchitectureDiagramGenerator,
    ArchitectureStyle,
    ComponentType,
)
from pywiki.generators.diagrams.package_diagram import PackageDiagramGenerator


class ArchitectureDocGenerator(BaseDocGenerator):
    """架构文档生成器"""

    doc_type = DocType.ARCHITECTURE
    template_name = "architecture.md.j2"

    STANDARD_LIBS = {
        "typing", "os", "sys", "json", "pathlib", "asyncio", "abc",
        "dataclasses", "collections", "functools", "itertools", "re",
        "logging", "time", "datetime", "copy", "enum", "io", "warnings",
        "contextlib", "threading", "multiprocessing", "concurrent",
        "subprocess", "shutil", "tempfile", "hashlib", "hmac", "secrets",
        "argparse", "configparser", "traceback", "inspect", "dis",
        "unittest", "pytest", "mock", "socket", "ssl", "http", "urllib",
        "email", "html", "xml", "csv", "sqlite3", "heapq", "bisect",
        "array", "weakref", "types", "numbers", "math", "random",
        "statistics", "decimal", "fractions", "operator", "pickle",
    }

    EXTERNAL_CATEGORIES = {
        "web_framework": ["fastapi", "flask", "django", "tornado", "starlette", "sanic", "aiohttp"],
        "database": ["sqlalchemy", "pymongo", "redis", "psycopg", "mysql", "sqlite", "databases"],
        "orm": ["sqlalchemy", "peewee", "tortoise", "django.db", "pony"],
        "validation": ["pydantic", "marshmallow", "cerberus", "voluptuous"],
        "testing": ["pytest", "unittest", "mock", "hypothesis", "faker"],
        "async": ["asyncio", "aiohttp", "aiofiles", "aioredis", "aiomysql"],
        "http_client": ["requests", "httpx", "aiohttp", "urllib3", "http.client"],
        "serialization": ["json", "pickle", "yaml", "msgpack", "orjson"],
        "cli": ["click", "argparse", "typer", "rich"],
        "config": ["pydantic", "dynaconf", "python-dotenv", "configparser"],
        "logging": ["logging", "loguru", "structlog"],
        "task_queue": ["celery", "rq", "dramatiq", "huey"],
        "cache": ["redis", "memcache", "cachetools", "aiocache"],
        "message_queue": ["kafka", "pika", "aio_pika", "celery"],
        "security": ["cryptography", "jwt", "passlib", "bcrypt"],
        "data_science": ["pandas", "numpy", "scipy", "sklearn"],
        "ml": ["torch", "tensorflow", "sklearn", "transformers"],
    }

    def __init__(
        self,
        language: Language = Language.ZH,
        template_dir: Optional[Path] = None,
    ):
        super().__init__(language, template_dir)
        self.architecture_agent = ArchitectureAgent()
        self.arch_diagram_gen = ArchitectureDiagramGenerator()
        self.package_diagram_gen = PackageDiagramGenerator()

    async def generate(self, context: DocGeneratorContext) -> DocGeneratorResult:
        """生成架构文档"""
        try:
            project_language = context.project_language or context.detect_project_language()
            
            arch_data = await self._analyze_architecture(context, project_language)
            
            if context.metadata.get("llm_client"):
                enhanced_data = await self._enhance_with_llm(
                    context,
                    arch_data,
                    context.metadata["llm_client"]
                )
                arch_data.update(enhanced_data)

            content = self.render_template(
                description=f"{context.project_name} 系统架构文档",
                architecture_style=arch_data.get("architecture_style", ""),
                architecture_diagram=arch_data.get("architecture_diagram", ""),
                c4_context=arch_data.get("c4_context", ""),
                c4_container=arch_data.get("c4_container", ""),
                c4_component=arch_data.get("c4_component", ""),
                dependency_graph=arch_data.get("dependency_graph", ""),
                package_diagram=arch_data.get("package_diagram", ""),
                data_flow_diagram=arch_data.get("data_flow_diagram", ""),
                layers=arch_data.get("layers", []),
                metrics=arch_data.get("metrics", []),
                quality_metrics=arch_data.get("quality_metrics", {}),
                circular_dependencies=arch_data.get("circular_dependencies", []),
                hot_spots=arch_data.get("hot_spots", []),
                recommendations=arch_data.get("recommendations", []),
                external_dependencies=arch_data.get("external_dependencies", []),
                strengths=arch_data.get("strengths", []),
                weaknesses=arch_data.get("weaknesses", []),
                risk_assessment=arch_data.get("risk_assessment", ""),
            )

            return self.create_result(
                content=content,
                context=context,
                success=True,
                message=self.labels.get("architecture_doc_success", "Architecture documentation generated successfully"),
                metadata={"architecture_data": arch_data.get("summary", {})},
            )

        except Exception as e:
            return self.create_result(
                content="",
                context=context,
                success=False,
                message=f"{self.labels.get('generation_failed', 'Generation failed')}: {str(e)}",
            )

    async def _analyze_architecture(self, context: DocGeneratorContext, project_language: str) -> dict[str, Any]:
        """分析架构"""
        arch_data = {
            "architecture_style": "",
            "architecture_diagram": "",
            "c4_context": "",
            "c4_container": "",
            "c4_component": "",
            "dependency_graph": "",
            "package_diagram": "",
            "data_flow_diagram": "",
            "layers": [],
            "metrics": [],
            "quality_metrics": {},
            "circular_dependencies": [],
            "hot_spots": [],
            "recommendations": [],
            "external_dependencies": [],
            "strengths": [],
            "weaknesses": [],
            "risk_assessment": "",
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

        arch_data["architecture_style"] = self._detect_architecture_style(context)
        arch_data["architecture_diagram"] = self._generate_architecture_diagram(context)
        arch_data["c4_context"] = self._generate_c4_context(context)
        arch_data["c4_container"] = self._generate_c4_container(context)
        arch_data["c4_component"] = self._generate_c4_component(context)
        arch_data["dependency_graph"] = self._generate_dependency_graph(context)
        arch_data["package_diagram"] = self._generate_package_diagram(context)
        arch_data["data_flow_diagram"] = self._generate_data_flow_diagram(context)
        arch_data["layers"] = self._analyze_layers(context, project_language)
        arch_data["quality_metrics"] = self._calculate_quality_metrics(context)
        arch_data["circular_dependencies"] = self._detect_circular_dependencies(context)
        arch_data["hot_spots"] = self._detect_hot_spots(context)
        arch_data["external_dependencies"] = self._analyze_external_dependencies(context)

        return arch_data

    def _detect_architecture_style(self, context: DocGeneratorContext) -> str:
        """检测架构风格"""
        if not context.parse_result or not context.parse_result.modules:
            return self.labels.get("monolithic_arch", "Monolithic Architecture")
        
        modules = context.parse_result.modules
        module_names = [m.name.lower() if hasattr(m, "name") else str(m).lower() for m in modules]
        
        service_count = sum(1 for name in module_names if "service" in name)
        controller_count = sum(1 for name in module_names if any(kw in name for kw in ["controller", "api", "router", "handler"]))
        repo_count = sum(1 for name in module_names if any(kw in name for kw in ["repository", "dao", "store"]))
        event_count = sum(1 for name in module_names if any(kw in name for kw in ["event", "queue", "message", "kafka", "rabbit"]))
        command_count = sum(1 for name in module_names if "command" in name)
        query_count = sum(1 for name in module_names if "query" in name)
        adapter_count = sum(1 for name in module_names if "adapter" in name)
        
        if event_count > 2:
            return self.labels.get("event_driven_arch", "Event-Driven Architecture")
        if command_count > 0 and query_count > 0:
            return self.labels.get("cqrs_arch", "CQRS Architecture")
        if adapter_count > 1:
            return self.labels.get("hexagonal_arch", "Hexagonal Architecture")
        if service_count > 5 and controller_count > 2:
            return self.labels.get("microservice_arch", "Microservice Architecture")
        if controller_count > 0 and service_count > 0 and repo_count > 0:
            return self.labels.get("layered_arch", "Layered Architecture")
        
        return self.labels.get("monolithic_arch", "Monolithic Architecture")

    def _generate_architecture_diagram(self, context: DocGeneratorContext) -> str:
        """生成智能架构图"""
        if not context.parse_result:
            return ""
        
        return self.arch_diagram_gen.generate_from_parse_result(
            context.parse_result,
            context.project_name,
            f"{context.project_name} {self.labels.get('system_arch', 'System Architecture')}"
        )

    def _generate_package_diagram(self, context: DocGeneratorContext) -> str:
        """生成包依赖图"""
        if not context.parse_result:
            return ""
        
        return self.package_diagram_gen.generate_from_parse_result(
            context.parse_result,
            context.project_name,
            f"{context.project_name} {self.labels.get('package_deps', 'Package Dependencies')}"
        )

    def _generate_data_flow_diagram(self, context: DocGeneratorContext) -> str:
        """生成数据流图"""
        if not context.parse_result or not context.parse_result.modules:
            return ""
        
        modules = context.parse_result.modules[:15]
        
        nodes = []
        flows = []
        
        nodes.append({
            "id": "client",
            "name": "Client",
            "type": "external_entity",
            "description": self.labels.get("external_client", "External Client"),
        })
        
        for module in modules:
            module_name = module.name if hasattr(module, "name") else str(module)
            name_lower = module_name.lower()
            
            if any(kw in name_lower for kw in ["api", "controller", "router", "handler", "endpoint"]):
                nodes.append({
                    "id": self._sanitize_id(module_name),
                    "name": module_name.split(".")[-1],
                    "type": "process",
                    "description": self.labels.get("api_entry", "API Entry"),
                })
                flows.append({
                    "source": "client",
                    "target": self._sanitize_id(module_name),
                    "data_name": "HTTP Request",
                })
            elif any(kw in name_lower for kw in ["service", "manager", "processor"]):
                nodes.append({
                    "id": self._sanitize_id(module_name),
                    "name": module_name.split(".")[-1],
                    "type": "process",
                    "description": self.labels.get("business_processing", "Business Processing"),
                })
            elif any(kw in name_lower for kw in ["repository", "dao", "store", "db", "database"]):
                nodes.append({
                    "id": self._sanitize_id(module_name),
                    "name": module_name.split(".")[-1],
                    "type": "data_store",
                    "description": self.labels.get("data_storage", "Data Storage"),
                })
        
        api_nodes = [n for n in nodes if "API" in n.get("description", "") or "Entry" in n.get("description", "")]
        service_nodes = [n for n in nodes if "Business" in n.get("description", "") or "业务" in n.get("description", "")]
        data_nodes = [n for n in nodes if n.get("type") == "data_store"]
        
        for api in api_nodes:
            for svc in service_nodes:
                flows.append({
                    "source": api["id"],
                    "target": svc["id"],
                    "data_name": self.labels.get("request", "Request"),
                })
        
        for svc in service_nodes:
            for data in data_nodes:
                flows.append({
                    "source": svc["id"],
                    "target": data["id"],
                    "data_name": self.labels.get("data_operation", "Data Operation"),
                })
        
        data = {"nodes": nodes[:12], "flows": flows[:20]}
        
        lines = ["graph LR"]
        for node in data["nodes"]:
            node_id = node.get("id", "")
            name = node.get("name", "")
            node_type = node.get("type", "process")
            
            if node_type == "external_entity":
                lines.append(f"    {node_id}[\"{name}\"]")
                lines.append(f"    style {node_id} fill:#e1f5fe,stroke:#01579b")
            elif node_type == "process":
                lines.append(f"    {node_id}({name})")
                lines.append(f"    style {node_id} fill:#fff3e0,stroke:#e65100")
            elif node_type == "data_store":
                lines.append(f"    {node_id}[[\"{name}\"]]")
                lines.append(f"    style {node_id} fill:#f3e5f5,stroke:#4a148c")
        
        for flow in data["flows"]:
            source = flow.get("source", "")
            target = flow.get("target", "")
            data_name = flow.get("data_name", "")
            if source and target:
                lines.append(f"    {source} -->|\"{data_name}\"| {target}")
        
        return "\n".join(lines)

    def _sanitize_id(self, name: str) -> str:
        """将名称转换为有效的 ID"""
        return name.replace(".", "_").replace("-", "_").replace(" ", "_")[:30]

    def _analyze_external_dependencies(self, context: DocGeneratorContext) -> list[dict[str, Any]]:
        """分析外部依赖"""
        if not context.parse_result or not context.parse_result.modules:
            return []
        
        dep_counts: dict[str, dict] = defaultdict(lambda: {"count": 0, "category": "other"})
        
        for module in context.parse_result.modules:
            if hasattr(module, "imports") and module.imports:
                for imp in module.imports:
                    imp_module = imp.module if hasattr(imp, "module") else str(imp)
                    base = imp_module.split(".")[0]
                    
                    if base in self.STANDARD_LIBS:
                        continue
                    
                    if base not in dep_counts:
                        category = "other"
                        for cat, libs in self.EXTERNAL_CATEGORIES.items():
                            if base in libs:
                                category = cat
                                break
                        dep_counts[base]["category"] = category
                    
                    dep_counts[base]["count"] += 1
        
        sorted_deps = sorted(dep_counts.items(), key=lambda x: x[1]["count"], reverse=True)[:15]
        
        return [
            {
                "name": name,
                "count": info["count"],
                "category": info["category"],
            }
            for name, info in sorted_deps
        ]

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

    def _analyze_layers(self, context: DocGeneratorContext, project_language: str) -> list[dict[str, Any]]:
        """分析分层架构"""
        layers = []

        layer_patterns = {
            self.labels.get("presentation_layer", "Presentation Layer"): {
                "keywords": ["api", "controller", "view", "handler", "endpoint", "route", "router", "http", "rest", "graphql", "web"],
                "description": self.labels.get("presentation_desc", "Handles external requests, responsible for data display and user interaction"),
            },
            self.labels.get("business_layer", "Business Layer"): {
                "keywords": ["service", "business", "domain", "usecase", "application", "logic", "manager", "processor"],
                "description": self.labels.get("business_desc", "Implements core business logic and business rules"),
            },
            self.labels.get("data_layer", "Data Layer"): {
                "keywords": ["repository", "dao", "model", "entity", "data", "persistence", "store", "mapper", "schema"],
                "description": self.labels.get("data_desc", "Responsible for data persistence and data access"),
            },
            self.labels.get("infrastructure_layer", "Infrastructure Layer"): {
                "keywords": ["infrastructure", "config", "util", "common", "helper", "lib", "core", "base", "foundation"],
                "description": self.labels.get("infrastructure_desc", "Provides technical support and infrastructure services"),
            },
            self.labels.get("proxy_layer", "Proxy Layer"): {
                "keywords": ["agent", "broker", "proxy", "client", "adapter", "connector"],
                "description": self.labels.get("proxy_desc", "Responsible for interacting and integrating with external systems"),
            },
        }

        java_layer_patterns = {
            self.labels.get("presentation_layer", "Presentation Layer"): {
                "keywords": ["controller", "restcontroller", "handler", "endpoint", "api", "web", "servlet", "filter"],
                "annotations": ["@Controller", "@RestController", "@RequestMapping", "@GetMapping", "@PostMapping"],
                "description": self.labels.get("java_presentation_desc", "Handles HTTP requests, responsible for API endpoints and web interface"),
            },
            self.labels.get("business_layer", "Business Layer"): {
                "keywords": ["service", "serviceimpl", "business", "domain", "usecase", "manager", "processor", "facade"],
                "annotations": ["@Service", "@Transactional", "@Component"],
                "description": self.labels.get("business_desc", "Implements core business logic and business rules"),
            },
            self.labels.get("data_layer", "Data Layer"): {
                "keywords": ["repository", "dao", "mapper", "entity", "model", "persistence", "jpa", "crud"],
                "annotations": ["@Repository", "@Entity", "@Table", "@Mapper"],
                "description": self.labels.get("data_desc", "Responsible for data persistence and data access"),
            },
            self.labels.get("infrastructure_layer", "Infrastructure Layer"): {
                "keywords": ["config", "configuration", "util", "common", "helper", "exception", "aspect", "interceptor"],
                "annotations": ["@Configuration", "@Component", "@Aspect", "@Bean"],
                "description": self.labels.get("infrastructure_desc", "Provides technical support and infrastructure services"),
            },
            self.labels.get("dto_layer", "DTO Layer"): {
                "keywords": ["dto", "vo", "request", "response", "form", "command", "query"],
                "annotations": [],
                "description": self.labels.get("dto_desc", "Data Transfer Objects for inter-layer data transfer"),
            },
        }

        typescript_layer_patterns = {
            self.labels.get("presentation_layer", "Presentation Layer"): {
                "keywords": ["controller", "handler", "endpoint", "api", "route", "resolver", "gateway"],
                "decorators": ["@Controller", "@Get", "@Post", "@Put", "@Delete", "@Patch", "@Resolver"],
                "description": self.labels.get("ts_presentation_desc", "Handles HTTP requests and GraphQL resolvers"),
            },
            self.labels.get("business_layer", "Business Layer"): {
                "keywords": ["service", "business", "domain", "usecase", "manager", "processor", "provider"],
                "decorators": ["@Service", "@Injectable", "@Provider"],
                "description": self.labels.get("business_desc", "Implements core business logic and business rules"),
            },
            self.labels.get("data_layer", "Data Layer"): {
                "keywords": ["repository", "dao", "mapper", "entity", "model", "schema", "prisma", "typeorm"],
                "decorators": ["@Entity", "@Repository", "@EntityRepository"],
                "description": self.labels.get("data_desc", "Responsible for data persistence and data access"),
            },
            self.labels.get("infrastructure_layer", "Infrastructure Layer"): {
                "keywords": ["config", "module", "middleware", "guard", "interceptor", "filter", "pipe", "util", "common"],
                "decorators": ["@Module", "@Middleware", "@UseGuards", "@UseInterceptors", "@UsePipes"],
                "description": self.labels.get("infrastructure_desc", "Provides technical support and infrastructure services"),
            },
            self.labels.get("dto_layer", "DTO Layer"): {
                "keywords": ["dto", "vo", "input", "output", "request", "response", "interface", "type"],
                "decorators": [],
                "description": self.labels.get("ts_dto_desc", "Data Transfer Objects and type definitions"),
            },
        }

        if project_language == "java":
            layer_patterns = java_layer_patterns
        elif project_language == "typescript":
            layer_patterns = typescript_layer_patterns

        if not context.parse_result or not context.parse_result.modules:
            return layers

        layer_modules: dict[str, list] = defaultdict(list)
        assigned_modules = set()

        for module in context.parse_result.modules:
            module_lower = module.name.lower()
            
            matched = False
            for layer_name, layer_info in layer_patterns.items():
                if any(kw in module_lower for kw in layer_info["keywords"]):
                    layer_modules[layer_name].append(module)
                    assigned_modules.add(module.name)
                    matched = True
                    break

            if not matched:
                for cls in (module.classes or []):
                    annotations = getattr(cls, 'annotations', []) or getattr(cls, 'decorators', [])
                    class_lower = cls.name.lower()
                    
                    for layer_name, layer_info in layer_patterns.items():
                        layer_keywords = layer_info.get("keywords", [])
                        layer_annotations = layer_info.get("annotations", []) or layer_info.get("decorators", [])
                        
                        if any(kw in class_lower for kw in layer_keywords):
                            layer_modules[layer_name].append(module)
                            assigned_modules.add(module.name)
                            matched = True
                            break
                        
                        for annotation in annotations:
                            if any(ann in annotation for ann in layer_annotations):
                                layer_modules[layer_name].append(module)
                                assigned_modules.add(module.name)
                                matched = True
                                break
                        
                        if matched:
                            break
                    
                    if matched:
                        break

        for module in context.parse_result.modules:
            if module.name not in assigned_modules:
                if module.classes:
                    has_entity = any(
                        "Model" in c.name or "Entity" in c.name or "DTO" in c.name or "Dto" in c.name
                        for c in module.classes
                    )
                    has_service = any("Service" in c.name for c in module.classes)
                    has_controller = any("Controller" in c.name for c in module.classes)
                    
                    if has_controller:
                        layer_modules["表现层"].append(module)
                    elif has_entity:
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

        if self.language == Language.ZH:
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

请务必使用中文回答。"""
        else:
            prompt = f"""Based on the following architecture analysis, provide deeper architectural insights:

Project: {context.project_name}
Layers: {[l['name'] for l in layers]}
Modules: {quality_metrics.get('module_count', 0)}
Classes: {quality_metrics.get('class_count', 0)}
Coupling: {quality_metrics.get('coupling', {}).get('level', 'unknown')}
Cohesion: {quality_metrics.get('cohesion', {}).get('level', 'unknown')}
Circular Dependencies: {len(arch_data.get('circular_dependencies', []))}
Hot Spots: {len(arch_data.get('hot_spots', []))}

Please return in JSON format:
{{
    "architecture_style": "Architecture style (e.g., layered architecture, microservices)",
    "strengths": ["strength1", "strength2"],
    "weaknesses": ["weakness1", "weakness2"],
    "improvement_suggestions": ["suggestion1", "suggestion2"],
    "risk_assessment": "Risk assessment"
}}

Please respond in English."""

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
