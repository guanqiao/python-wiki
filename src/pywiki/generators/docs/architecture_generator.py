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
from pywiki.generators.diagrams.flowchart import FlowchartGenerator
from pywiki.generators.diagrams.sequence import SequenceDiagramGenerator
from pywiki.generators.diagrams.class_diagram import ClassDiagramGenerator
from pywiki.generators.diagrams.state import StateDiagramGenerator
from pywiki.generators.diagrams.component import ComponentDiagramGenerator


class ArchitectureDocGenerator(BaseDocGenerator):
    """架构文档生成器"""

    doc_type = DocType.ARCHITECTURE
    template_name = "architecture.md.j2"

    THIRD_PARTY_PREFIXES = {
        "org.", "com.", "io.", "net.", "javax.", "java.",
        "liquibase.", "flowable.", "activiti.", "camunda.",
        "springframework.", "hibernate.", "mybatis.", "apache.",
        "lombok.", "slf4j.", "log4j.", "junit.", "mockito.",
        "jackson.", "gson.", "fastjson.", "okhttp.",
        "retrofit.", "feign.", "dubbo.", "nacos.", "sentinel.",
        "sharding.", "druid.", "hikari.", "redis.clients.", "mongodb.driver.",
        "elasticsearch.", "kafka.", "rabbitmq.", "zookeeper.",
        "curator.", "netty.", "vertx.", "quarkus.", "micronaut.",
        "jakarta.", "sun.", "jdk.", "oracle.", "ibm.",
    }

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
        self.flowchart_gen = FlowchartGenerator()
        self.sequence_gen = SequenceDiagramGenerator()
        self.class_diagram_gen = ClassDiagramGenerator()
        self.state_diagram_gen = StateDiagramGenerator()
        self.component_diagram_gen = ComponentDiagramGenerator()

    def _sanitize_id(self, name: str) -> str:
        """将名称转换为有效的 Mermaid ID"""
        return self.arch_diagram_gen.sanitize_id(name)

    def _is_third_party_module(self, module_name: str, project_name: str) -> bool:
        """判断是否为第三方库模块或需要过滤的非项目模块"""
        module_lower = module_name.lower()

        # 检查是否是第三方库前缀
        for prefix in self.THIRD_PARTY_PREFIXES:
            if module_lower.startswith(prefix):
                return True

        import re

        # 处理文件路径格式（如 Python 脚本路径）
        if re.match(r'^[A-Za-z]:[\\/]', module_name) or module_name.startswith('/') or module_name.startswith('\\'):
            normalized = module_name.replace('\\', '/').lower()
            parts = normalized.split('/')
            meaningful_parts = [p for p in parts if p and p != '.' and p != '..' and not re.match(r'^[A-Za-z]:$', p)]

            if not meaningful_parts:
                return True

            first_meaningful = meaningful_parts[0].lower()

            # 过滤掉工具脚本目录
            tool_dirs = {'tools', 'scripts', 'utils', 'convertor', 'converter', 'migration'}
            if first_meaningful in tool_dirs:
                return True

            # 如果是 Python 文件路径（包含 .py 文件），可能是工具脚本
            if any(p.endswith('.py') for p in meaningful_parts):
                # 检查是否在项目源码目录中
                src_indicators = {'src', 'main', 'java', 'python', 'kotlin'}
                if not any(p.lower() in src_indicators for p in meaningful_parts):
                    return True

            # 检查是否是 Java 包路径
            if first_meaningful in {'org', 'com', 'io', 'net', 'javax', 'java', 'liquibase', 'flowable'}:
                return True

            return False

        return False

    def _filter_project_modules(self, modules: list, project_name: str) -> list:
        """过滤出项目自身的模块"""
        return [m for m in modules if not self._is_third_party_module(
            m.name if hasattr(m, 'name') else str(m), 
            project_name
        )]

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
                flowchart=arch_data.get("flowchart", ""),
                sequence_diagram=arch_data.get("sequence_diagram", ""),
                class_diagram=arch_data.get("class_diagram", ""),
                state_diagram=arch_data.get("state_diagram", ""),
                component_diagram=arch_data.get("component_diagram", ""),
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
                package_analysis=arch_data.get("package_analysis", {}),
                package_metrics=arch_data.get("package_metrics", []),
                layer_violations=arch_data.get("layer_violations", []),
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
            "flowchart": "",
            "sequence_diagram": "",
            "class_diagram": "",
            "state_diagram": "",
            "component_diagram": "",
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
        
        # 生成 LLM 增强的高阶图
        if context.metadata.get("llm_client"):
            llm_client = context.metadata["llm_client"]
            arch_data["flowchart"] = await self._generate_flowchart_with_llm(context, llm_client)
            arch_data["sequence_diagram"] = await self._generate_sequence_diagram_with_llm(context, llm_client)
            arch_data["class_diagram"] = await self._generate_class_diagram_with_llm(context, llm_client)
            arch_data["state_diagram"] = await self._generate_state_diagram_with_llm(context, llm_client)
            arch_data["component_diagram"] = await self._generate_component_diagram_with_llm(context, llm_client)
        
        try:
            package_analysis = context.get_package_analysis()
            arch_data["package_analysis"] = {
                "total_packages": package_analysis.get("summary", {}).get("total_packages", 0),
                "total_dependencies": package_analysis.get("summary", {}).get("total_dependencies", 0),
                "circular_dependency_count": package_analysis.get("summary", {}).get("circular_dependency_count", 0),
                "layer_violation_count": package_analysis.get("summary", {}).get("layer_violation_count", 0),
                "avg_stability": package_analysis.get("summary", {}).get("avg_stability", 0),
                "avg_cohesion": package_analysis.get("summary", {}).get("avg_cohesion", 0),
                "layers": package_analysis.get("layers", []),
                "subpackages": package_analysis.get("subpackages", [])[:20],
            }
            arch_data["package_metrics"] = package_analysis.get("metrics", [])[:20]
            arch_data["layer_violations"] = package_analysis.get("violations", [])
        except Exception:
            arch_data["package_analysis"] = {}
            arch_data["package_metrics"] = []
            arch_data["layer_violations"] = []

        return arch_data

    def _detect_architecture_style(self, context: DocGeneratorContext) -> str:
        """检测架构风格"""
        if not context.parse_result or not context.parse_result.modules:
            return self.labels.get("monolithic_arch", "Monolithic Architecture")
        
        modules = context.parse_result.modules
        module_names = []
        for m in modules:
            if hasattr(m, "name"):
                module_names.append(m.name.lower())
            else:
                module_names.append(str(m).lower())
        
        if len(modules) <= 3:
            return self.labels.get("simple_script", "Simple Script / Utility")
        
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
        if service_count > 0 or controller_count > 0:
            return self.labels.get("modular_arch", "Modular Architecture")
        
        return self.labels.get("monolithic_arch", "Monolithic Architecture")

    def _generate_architecture_diagram(self, context: DocGeneratorContext) -> str:
        """生成智能架构图"""
        if not context.parse_result or not context.parse_result.modules:
            return ""
        
        filtered_modules = self._filter_project_modules(
            context.parse_result.modules, 
            context.project_name
        )
        
        if not filtered_modules:
            return ""
        
        from pywiki.parsers.types import ParseResult
        filtered_parse_result = ParseResult()
        filtered_parse_result.modules = filtered_modules
        
        return self.arch_diagram_gen.generate_from_parse_result(
            filtered_parse_result,
            context.project_name,
            f"{context.project_name} {self.labels.get('system_arch', 'System Architecture')}"
        )

    def _generate_package_diagram(self, context: DocGeneratorContext) -> str:
        """生成包依赖图"""
        if not context.parse_result or not context.parse_result.modules:
            return ""
        
        filtered_modules = self._filter_project_modules(
            context.parse_result.modules, 
            context.project_name
        )
        
        if not filtered_modules:
            return ""
        
        from pywiki.parsers.types import ParseResult
        filtered_parse_result = ParseResult()
        filtered_parse_result.modules = filtered_modules
        
        return self.package_diagram_gen.generate_from_parse_result(
            filtered_parse_result,
            context.project_name,
            f"{context.project_name} {self.labels.get('package_deps', 'Package Dependencies')}"
        )

    def _generate_data_flow_diagram(self, context: DocGeneratorContext) -> str:
        """生成数据流图"""
        if not context.parse_result or not context.parse_result.modules:
            return self.arch_diagram_gen.wrap_mermaid("graph LR\n    A[No Data]")

        filtered_modules = self._filter_project_modules(
            context.parse_result.modules,
            context.project_name
        )

        if not filtered_modules:
            return self.arch_diagram_gen.wrap_mermaid("graph LR\n    A[No Data]")
        
        modules = filtered_modules[:15]
        
        nodes = []
        flows = []
        
        nodes.append({
            "id": "client",
            "name": "Client",
            "type": "external_entity",
            "description": self.labels.get("external_client", "External Client"),
        })
        
        api_nodes = []
        service_nodes = []
        data_nodes = []
        
        for module in modules:
            module_name = module.name if hasattr(module, "name") else str(module)
            name_lower = module_name.lower()
            display_name = self._extract_display_name(module_name)
            node_id = self._sanitize_id(module_name)
            
            if any(kw in name_lower for kw in ["api", "controller", "router", "handler", "endpoint"]):
                nodes.append({
                    "id": node_id,
                    "name": display_name,
                    "type": "process",
                    "description": self.labels.get("api_entry", "API Entry"),
                })
                api_nodes.append(node_id)
                flows.append({
                    "source": "client",
                    "target": node_id,
                    "data_name": "HTTP Request",
                })
            elif any(kw in name_lower for kw in ["service", "manager", "processor"]):
                nodes.append({
                    "id": node_id,
                    "name": display_name,
                    "type": "process",
                    "description": self.labels.get("business_processing", "Business Processing"),
                })
                service_nodes.append(node_id)
            elif any(kw in name_lower for kw in ["repository", "dao", "store", "db", "database"]):
                nodes.append({
                    "id": node_id,
                    "name": display_name,
                    "type": "data_store",
                    "description": self.labels.get("data_storage", "Data Storage"),
                })
                data_nodes.append(node_id)
        
        if not api_nodes and not service_nodes and not data_nodes:
            for module in modules[:5]:
                module_name = module.name if hasattr(module, "name") else str(module)
                display_name = self._extract_display_name(module_name)
                node_id = self._sanitize_id(module_name)
                
                nodes.append({
                    "id": node_id,
                    "name": display_name,
                    "type": "process",
                    "description": "Processing",
                })
                flows.append({
                    "source": "client",
                    "target": node_id,
                    "data_name": "Input",
                })

        for api_id in api_nodes:
            for svc_id in service_nodes:
                flows.append({
                    "source": api_id,
                    "target": svc_id,
                    "data_name": self.labels.get("request", "Request"),
                })
        
        for svc_id in service_nodes:
            for data_id in data_nodes:
                flows.append({
                    "source": svc_id,
                    "target": data_id,
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
                lines.append(f"    {node_id}(\"{name}\")")
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

        return self.arch_diagram_gen.wrap_mermaid("\n".join(lines))

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
                if not hasattr(module, "imports") or not module.imports:
                    continue
                for imp in module.imports:
                    if not hasattr(imp, "module"):
                        continue
                    imp_module = imp.module
                    if imp_module.startswith("."):
                        continue
                    project_prefix = context.project_name.split("-")[0] if "-" in context.project_name else context.project_name
                    if imp_module.startswith(project_prefix):
                        continue
                    base = imp_module.split(".")[0]
                    if base in self.STANDARD_LIBS:
                        continue
                    if base not in external_deps:
                        external_deps[base] = 0
                    external_deps[base] += 1

            sorted_deps = sorted(external_deps.items(), key=lambda x: x[1], reverse=True)[:8]
            for dep, count in sorted_deps:
                safe_name = self._sanitize_id(dep)
                lines.append(f"    {safe_name}[{dep}<br/>外部系统]")
                lines.append(f"    System -->|使用| {safe_name}")

        return self.arch_diagram_gen.wrap_mermaid("\n".join(lines))

    def _generate_c4_container(self, context: DocGeneratorContext) -> str:
        """生成 C4 容器图 - 显示业务模块级别的容器"""
        lines = [
            "graph TB",
            f"    subgraph System[{context.project_name}]",
        ]

        if context.parse_result and context.parse_result.modules:
            filtered_modules = self._filter_project_modules(
                context.parse_result.modules,
                context.project_name
            )

            if not filtered_modules:
                lines.append("    end")
                lines.append("    classDef container fill:#1168bd,stroke:#0b4884,color:#fff")
                return self.arch_diagram_gen.wrap_mermaid("\n".join(lines))

            # 识别业务模块（如 yudao-module-system, yudao-module-trade）
            business_modules = self._identify_business_modules(filtered_modules)

            # 识别技术容器（Web应用、数据库、缓存等）
            tech_containers = self._identify_tech_containers(filtered_modules)

            # 添加业务模块容器
            if business_modules:
                lines.append("        subgraph BusinessModules[业务模块]")
                for module_name, info in list(business_modules.items())[:6]:
                    safe_name = self._sanitize_id(module_name)
                    display_name = info.get('display_name', module_name)
                    desc = info.get('description', '')
                    lines.append(f"            {safe_name}[{display_name}<br/>{desc}]")
                    lines.append(f"            style {safe_name} fill:#438dd5,stroke:#2e6299,color:#fff")
                lines.append("        end")

            # 添加技术容器
            if tech_containers:
                lines.append("        subgraph TechLayer[技术基础设施]")
                for container_name, info in list(tech_containers.items())[:4]:
                    safe_name = self._sanitize_id(container_name)
                    display_name = info.get('display_name', container_name)
                    tech = info.get('technology', '')
                    shape = "[(" if info.get('type') == 'database' else "["
                    close_shape = ")]" if info.get('type') == 'database' else "]"
                    lines.append(f"            {safe_name}{shape}\"{display_name}<br/>[{tech}]\"{close_shape}")
                    if info.get('type') == 'database':
                        lines.append(f"            style {safe_name} fill:#438dd5,stroke:#2e6299,color:#fff")
                    else:
                        lines.append(f"            style {safe_name} fill:#438dd5,stroke:#2e6299,color:#fff")
                lines.append("        end")

        lines.append("    end")
        lines.append("    classDef container fill:#1168bd,stroke:#0b4884,color:#fff")

        return self.arch_diagram_gen.wrap_mermaid("\n".join(lines))

    def _identify_business_modules(self, modules: list) -> dict:
        """识别业务模块（如 yudao-module-system, yudao-module-trade）"""
        business_modules = {}

        for module in modules:
            module_name = module.name if hasattr(module, "name") else str(module)

            # 匹配业务模块模式（如 yudao-module-system, module-trade 等）
            import re

            # 尝试匹配常见的业务模块命名模式
            patterns = [
                r'(?:^|\.)module[.-]([^.]+)',  # module-system, module-trade
                r'(?:^|\.)modules[.-]([^.]+)',  # modules-system
                r'(?:^|\.)([^.]+)-module',  # system-module
                r'(?:^|\.)biz[.-]([^.]+)',  # biz-order
                r'(?:^|\.)business[.-]([^.]+)',  # business-trade
            ]

            for pattern in patterns:
                match = re.search(pattern, module_name.lower())
                if match:
                    module_key = match.group(1)
                    if module_key not in business_modules:
                        business_modules[module_key] = {
                            'display_name': module_key.replace('-', ' ').replace('_', ' ').title(),
                            'description': f'{len([m for m in modules if module_key in (m.name if hasattr(m, "name") else str(m)).lower()])} 模块',
                            'modules': [],
                        }
                    business_modules[module_key]['modules'].append(module)
                    break
            else:
                # 如果没有匹配到业务模块模式，按包的前几级分组
                parts = module_name.split('.')
                if len(parts) >= 3:
                    # 跳过组织前缀，取接下来的 2-3 级
                    org_prefixes = {'com', 'org', 'cn', 'net', 'io', 'me'}
                    start_idx = 1 if parts[0].lower() in org_prefixes else 0
                    if len(parts) > start_idx + 1:
                        group_key = '.'.join(parts[start_idx:start_idx+2])
                        if group_key not in business_modules:
                            business_modules[group_key] = {
                                'display_name': parts[start_idx+1] if len(parts) > start_idx + 1 else group_key,
                                'description': '核心模块',
                                'modules': [],
                            }
                        business_modules[group_key]['modules'].append(module)

        return business_modules

    def _identify_tech_containers(self, modules: list) -> dict:
        """识别技术容器（数据库、缓存、消息队列等）"""
        tech_containers = {}

        for module in modules:
            module_name = module.name if hasattr(module, "name") else str(module)
            name_lower = module_name.lower()

            # 识别数据库相关
            if any(kw in name_lower for kw in ['repository', 'dao', 'mapper', 'jpa', 'mybatis']):
                if 'Database' not in tech_containers:
                    tech_containers['Database'] = {
                        'display_name': 'Database',
                        'technology': 'MySQL/PostgreSQL',
                        'type': 'database',
                    }

            # 识别缓存相关
            if any(kw in name_lower for kw in ['cache', 'redis', 'caffeine']):
                if 'Cache' not in tech_containers:
                    tech_containers['Cache'] = {
                        'display_name': 'Cache',
                        'technology': 'Redis',
                        'type': 'cache',
                    }

            # 识别消息队列
            if any(kw in name_lower for kw in ['mq', 'kafka', 'rabbitmq', 'message']):
                if 'MessageQueue' not in tech_containers:
                    tech_containers['MessageQueue'] = {
                        'display_name': 'Message Queue',
                        'technology': 'Kafka/RabbitMQ',
                        'type': 'queue',
                    }

            # 识别 Web/API 层
            if any(kw in name_lower for kw in ['controller', 'web', 'api', 'rest']):
                if 'WebApplication' not in tech_containers:
                    tech_containers['WebApplication'] = {
                        'display_name': 'Web Application',
                        'technology': 'Spring Boot',
                        'type': 'web',
                    }

        return tech_containers

    def _extract_module_group(self, module_name: str) -> str:
        """从模块名提取分组名称"""
        import re

        # 处理文件路径格式（如 Python 脚本路径）
        if re.match(r'^[A-Za-z]:[\\/]', module_name) or module_name.startswith('/') or module_name.startswith('\\'):
            parts = re.split(r'[\\/]', module_name)
            meaningful_parts = [p for p in parts if p and p != '.' and p != '..' and not re.match(r'^[A-Za-z]:$', p)]
            if meaningful_parts:
                # 返回最后一个有意义的目录名（通常是模块名）
                return meaningful_parts[-1].replace('.py', '').replace('.java', '').replace('.ts', '')
            return "core"

        # 处理 Java 包名格式（如 cn.iocoder.yudao.module.system）
        parts = module_name.split(".")
        if len(parts) >= 3:
            # 跳过常见的组织前缀 (com, org, cn, net, me 等)
            org_prefixes = {'com', 'org', 'cn', 'net', 'io', 'me', 'dev', 'co', 'edu', 'gov'}
            start_idx = 0
            if parts[0].lower() in org_prefixes:
                start_idx = 1
            # 提取业务模块名称（如 yudao.module.system）
            if len(parts) > start_idx + 2:
                # 返回前 3-4 级作为模块标识
                end_idx = min(start_idx + 3, len(parts))
                return '.'.join(parts[start_idx:end_idx])
            elif len(parts) > start_idx:
                return '.'.join(parts[start_idx:])

        if len(parts) > 1:
            return parts[0]

        return "core"
    
    def _extract_display_name(self, name: str) -> str:
        """提取显示名称"""
        import re
        
        if re.match(r'^[A-Za-z]:[\\/]', name) or name.startswith('/') or name.startswith('\\'):
            parts = re.split(r'[\\/]', name)
            meaningful_parts = [p for p in parts if p and p != '.' and p != '..' and not re.match(r'^[A-Za-z]:$', p)]
            if meaningful_parts:
                return meaningful_parts[-1].replace('.py', '').replace('.java', '').replace('.ts', '')
        
        if '.' in name:
            return name.split('.')[-1]
        
        return name

    def _generate_c4_component(self, context: DocGeneratorContext) -> str:
        """生成 C4 组件图"""
        lines = ["graph TB"]

        if not context.parse_result or not context.parse_result.modules:
            return self.arch_diagram_gen.wrap_mermaid("\n".join(lines))

        filtered_modules = self._filter_project_modules(
            context.parse_result.modules,
            context.project_name
        )

        if not filtered_modules:
            return self.arch_diagram_gen.wrap_mermaid("\n".join(lines))

        module_groups: dict[str, list] = defaultdict(list)
        
        for module in filtered_modules:
            module_name = module.name if hasattr(module, "name") else str(module)
            group = self._extract_module_group(module_name)
            module_groups[group].append(module)

        for group, modules in list(module_groups.items())[:4]:
            safe_group = self._sanitize_id(group)
            display_group = self._extract_display_name(group)
            lines.append(f"    subgraph {safe_group}[{display_group}]")
            
            for module in modules[:5]:
                module_name = module.name if hasattr(module, "name") else str(module)
                safe_name = self._sanitize_id(module_name)
                display_name = self._extract_display_name(module_name)
                class_count = len(module.classes) if hasattr(module, "classes") and module.classes else 0
                func_count = len(module.functions) if hasattr(module, "functions") and module.functions else 0
                lines.append(f"        {safe_name}[{display_name}<br/>{class_count} 类, {func_count} 函数]")
            
            lines.append("    end")

        return self.arch_diagram_gen.wrap_mermaid("\n".join(lines))

    def _generate_dependency_graph(self, context: DocGeneratorContext) -> str:
        """生成依赖关系图"""
        lines = ["graph LR"]

        if not context.parse_result or not context.parse_result.modules:
            return self.arch_diagram_gen.wrap_mermaid("\n".join(lines))

        filtered_modules = self._filter_project_modules(
            context.parse_result.modules,
            context.project_name
        )

        if not filtered_modules:
            return self.arch_diagram_gen.wrap_mermaid("\n".join(lines))
        
        modules = filtered_modules[:20]
        
        module_map = {}
        for module in modules:
            module_name = module.name if hasattr(module, "name") else str(module)
            safe_name = self._sanitize_id(module_name)
            module_map[module_name] = safe_name
            display_name = self._extract_display_name(module_name)
            lines.append(f"    {safe_name}[{display_name}]")

        dependency_counts: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
        
        for module in modules:
            module_name = module.name if hasattr(module, "name") else str(module)
            source_safe = module_map[module_name]
            
            if hasattr(module, 'imports') and module.imports:
                for imp in module.imports:
                    if not hasattr(imp, "module"):
                        continue
                    target_module = None
                    
                    for other_module in modules:
                        other_name = other_module.name if hasattr(other_module, "name") else str(other_module)
                        if other_name == imp.module or other_name.startswith(imp.module + "."):
                            target_module = other_name
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

        return self.arch_diagram_gen.wrap_mermaid("\n".join(lines))

    def _analyze_layers(self, context: DocGeneratorContext, project_language: str) -> list[dict[str, Any]]:
        """分析分层架构"""
        layers = []

        if not context.parse_result or not context.parse_result.modules:
            return layers
        
        filtered_modules = self._filter_project_modules(
            context.parse_result.modules, 
            context.project_name
        )
        
        if not filtered_modules:
            return layers

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

        layer_modules: dict[str, list] = defaultdict(list)
        assigned_modules = set()

        for module in filtered_modules:
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

        for module in filtered_modules:
            if module.name not in assigned_modules:
                if module.classes:
                    has_entity = any(
                        "Model" in c.name or "Entity" in c.name or "DO" in c.name
                        for c in module.classes
                    )
                    has_dto = any(
                        "DTO" in c.name or "Dto" in c.name or "VO" in c.name or "Request" in c.name or "Response" in c.name
                        for c in module.classes
                    )
                    has_service = any("Service" in c.name for c in module.classes)
                    has_controller = any("Controller" in c.name for c in module.classes)
                    # 识别基础设施类：枚举、工具类、异常、常量等
                    has_infrastructure = any(
                        "Enum" in c.name or "Utils" in c.name or "Util" in c.name or
                        "Exception" in c.name or "Constant" in c.name or "Config" in c.name or
                        "Helper" in c.name or "Common" in c.name or "Base" in c.name
                        for c in module.classes
                    )
                    # 根据包路径判断
                    module_lower = module.name.lower()
                    is_infrastructure_pkg = any(kw in module_lower for kw in [
                        "enums", "constant", "util", "common", "config", "exception",
                        "framework", "core", "base", "helper"
                    ])
                    is_data_pkg = any(kw in module_lower for kw in [
                        "entity", "model", "domain", "repository", "dao", "mapper"
                    ])

                    if has_controller:
                        layer_modules[self.labels.get("presentation_layer", "Presentation Layer")].append(module)
                    elif has_service:
                        layer_modules[self.labels.get("business_layer", "Business Layer")].append(module)
                    elif has_entity or (is_data_pkg and not has_infrastructure_pkg):
                        layer_modules[self.labels.get("data_layer", "Data Layer")].append(module)
                    elif has_dto:
                        # DTO 可以放在数据层或专门的 DTO 层
                        layer_modules[self.labels.get("data_layer", "Data Layer")].append(module)
                    elif has_infrastructure_pkg or is_infrastructure_pkg or has_infrastructure:
                        layer_modules[self.labels.get("infrastructure_layer", "Infrastructure Layer")].append(module)
                    else:
                        # 默认归类到基础设施层
                        layer_modules[self.labels.get("infrastructure_layer", "Infrastructure Layer")].append(module)

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
            # 统计模块级别的函数（顶层函数）
            func_count = len(module.functions) if module.functions else 0

            total_classes += class_count
            total_functions += func_count

            # 统计类中的方法
            for cls in (module.classes or []):
                method_count = len(cls.methods) if cls.methods else 0
                total_methods += method_count
                # 将方法也计入总函数数
                total_functions += method_count

            for imp in (module.imports or []):
                if not imp.module.startswith("."):
                    base = imp.module.split(".")[0]
                    import_counts[base] += 1
                    total_imports += 1

        metrics["class_count"] = total_classes
        # 总函数数 = 顶层函数 + 类方法
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
        
        system_prompt = self._get_system_prompt()

        if self.language == Language.ZH:
            prompt = f"""# 任务
基于架构分析数据，提供深入的架构洞察和专业建议。

# 架构数据
- **项目名称**: {context.project_name}
- **分层结构**: {[l['name'] for l in layers]}
- **模块数量**: {quality_metrics.get('module_count', 0)}
- **类数量**: {quality_metrics.get('class_count', 0)}
- **耦合度**: {quality_metrics.get('coupling', {}).get('level', 'unknown')}
- **内聚性**: {quality_metrics.get('cohesion', {}).get('level', 'unknown')}
- **循环依赖**: {len(arch_data.get('circular_dependencies', []))}
- **热点模块**: {len(arch_data.get('hot_spots', []))}

# 输出要求
请以 JSON 格式返回以下字段：
{{
    "architecture_style": "架构风格（如分层架构、微服务、事件驱动等，需说明判断依据）",
    "strengths": ["架构优势1（具体说明）", "架构优势2"],
    "weaknesses": ["架构劣势1（具体说明）", "架构劣势2"],
    "improvement_suggestions": ["改进建议1（可执行）", "改进建议2"],
    "risk_assessment": "风险评估（包含潜在风险和影响范围）"
}}

# 质量标准
- 架构风格判断需基于分层、模块化等特征
- 优劣势分析需结合具体指标数据
- 改进建议需具体可执行，避免空泛表述
- 风险评估需考虑可维护性、扩展性、性能等方面

请务必使用中文回答。"""
        else:
            prompt = f"""# Task
Based on architecture analysis data, provide in-depth architectural insights and professional recommendations.

# Architecture Data
- **Project Name**: {context.project_name}
- **Layer Structure**: {[l['name'] for l in layers]}
- **Module Count**: {quality_metrics.get('module_count', 0)}
- **Class Count**: {quality_metrics.get('class_count', 0)}
- **Coupling**: {quality_metrics.get('coupling', {}).get('level', 'unknown')}
- **Cohesion**: {quality_metrics.get('cohesion', {}).get('level', 'unknown')}
- **Circular Dependencies**: {len(arch_data.get('circular_dependencies', []))}
- **Hot Spots**: {len(arch_data.get('hot_spots', []))}

# Output Requirements
Please return the following fields in JSON format:
{{
    "architecture_style": "Architecture style (e.g., layered, microservices, event-driven, with reasoning)",
    "strengths": ["strength 1 (specific explanation)", "strength 2"],
    "weaknesses": ["weakness 1 (specific explanation)", "weakness 2"],
    "improvement_suggestions": ["suggestion 1 (actionable)", "suggestion 2"],
    "risk_assessment": "Risk assessment (including potential risks and impact scope)"
}}

# Quality Standards
- Architecture style should be determined based on layering, modularization features
- Strengths/weaknesses analysis should reference specific metric data
- Improvement suggestions should be actionable, avoid vague statements
- Risk assessment should consider maintainability, scalability, performance aspects

Please respond in English."""

        try:
            response = await llm_client.agenerate(prompt, system_prompt=system_prompt)
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

    async def _generate_flowchart_with_llm(self, context: DocGeneratorContext, llm_client: Any) -> str:
        """使用 LLM 生成业务流程图"""
        if not context.parse_result or not context.parse_result.modules:
            return ""

        # 提取关键模块信息供 LLM 分析
        module_info = []
        filtered_modules = self._filter_project_modules(context.parse_result.modules, context.project_name)
        for module in filtered_modules[:20]:
            classes = []
            if hasattr(module, 'classes') and module.classes:
                for cls in module.classes[:5]:
                    methods = [m.name for m in cls.methods[:3]] if hasattr(cls, 'methods') and cls.methods else []
                    classes.append({"name": cls.name, "methods": methods})
            
            functions = []
            if hasattr(module, 'functions') and module.functions:
                functions = [f.name for f in module.functions[:3]]
            
            module_info.append({
                "name": module.name if hasattr(module, 'name') else str(module),
                "classes": classes,
                "functions": functions,
            })

        system_prompt = "你是一名资深架构师，擅长从代码中抽象出业务流程和系统流程。请分析项目结构，识别核心业务场景，生成高层次的流程图描述。"

        prompt = f"""# 任务
分析以下项目代码结构，识别核心业务场景，生成高层次的业务流程图描述。

# 项目信息
- 项目名称: {context.project_name}
- 模块数量: {len(filtered_modules)}

# 关键模块信息
```json
{json.dumps(module_info, ensure_ascii=False, indent=2)}
```

# 输出要求
请以 JSON 格式返回流程图数据：
{{
    "title": "流程图标题",
    "description": "流程图描述",
    "nodes": [
        {{"id": "node1", "label": "开始/结束", "type": "start"}},
        {{"id": "node2", "label": "处理步骤", "type": "node"}},
        {{"id": "node3", "label": "条件判断", "type": "decision"}},
        {{"id": "node4", "label": "子流程", "type": "subroutine"}},
        {{"id": "node5", "label": "数据库", "type": "database"}}
    ],
    "edges": [
        {{"source": "node1", "target": "node2", "label": ""}},
        {{"source": "node2", "target": "node3", "label": ""}},
        {{"source": "node3", "target": "node4", "label": "是"}},
        {{"source": "node3", "target": "node5", "label": "否"}}
    ],
    "direction": "TD"
}}

# 质量要求
1. 从代码中抽象出业务流程，不要直接映射代码结构
2. 识别核心业务场景（如用户注册、订单处理、数据同步等）
3. 节点类型选择：start/end（开始结束）、node（处理）、decision（判断）、subroutine（子流程）、database（数据库）
4. 流程图应该反映业务逻辑，而非技术实现细节
5. 节点数量控制在 5-12 个

请务必返回合法的 JSON 格式。"""

        try:
            response = await llm_client.agenerate(prompt, system_prompt=system_prompt)
            start = response.find("{")
            end = response.rfind("}")
            if start != -1 and end != -1:
                data = json.loads(response[start:end+1])
                return self.flowchart_gen.generate(data)
        except Exception:
            pass
        
        return ""

    async def _generate_sequence_diagram_with_llm(self, context: DocGeneratorContext, llm_client: Any) -> str:
        """使用 LLM 生成交互序列图"""
        if not context.parse_result or not context.parse_result.modules:
            return ""

        # 提取模块交互信息
        module_info = []
        filtered_modules = self._filter_project_modules(context.parse_result.modules, context.project_name)
        
        # 分析模块间的依赖关系
        dependencies = {}
        for module in filtered_modules[:20]:
            module_name = module.name if hasattr(module, 'name') else str(module)
            deps = []
            if hasattr(module, 'imports') and module.imports:
                for imp in module.imports:
                    imp_module = imp.module if hasattr(imp, 'module') else str(imp)
                    # 只保留项目内部依赖
                    if any(m.name == imp_module or imp_module.startswith(m.name + ".") for m in filtered_modules[:20]):
                        deps.append(imp_module)
            dependencies[module_name] = deps[:5]
            
            # 提取类和方法信息
            classes = []
            if hasattr(module, 'classes') and module.classes:
                for cls in module.classes[:3]:
                    methods = [m.name for m in cls.methods[:2]] if hasattr(cls, 'methods') and cls.methods else []
                    classes.append({"name": cls.name, "methods": methods})
            
            module_info.append({
                "name": module_name,
                "classes": classes,
                "dependencies": deps[:3],
            })

        system_prompt = "你是一名资深架构师，擅长分析系统组件间的交互关系。请从代码中抽象出关键的交互场景，生成高层次的序列图描述。"

        prompt = f"""# 任务
分析以下项目结构和模块依赖，识别关键的组件交互场景，生成高层次的序列图描述。

# 项目信息
- 项目名称: {context.project_name}
- 模块数量: {len(filtered_modules)}

# 模块信息
```json
{json.dumps(module_info, ensure_ascii=False, indent=2)}
```

# 输出要求
请以 JSON 格式返回序列图数据：
{{
    "title": "序列图标题",
    "description": "交互场景描述",
    "participants": [
        {{"name": "User", "type": "actor", "alias": "用户"}},
        {{"name": "API", "type": "participant"}},
        {{"name": "Service", "type": "participant"}},
        {{"name": "DB", "type": "participant"}}
    ],
    "messages": [
        {{"source": "User", "target": "API", "content": "请求操作", "type": "sync"}},
        {{"source": "API", "target": "Service", "content": "调用服务", "type": "sync"}},
        {{"source": "Service", "target": "DB", "content": "查询数据", "type": "sync"}},
        {{"source": "DB", "target": "Service", "content": "返回数据", "type": "return"}},
        {{"source": "Service", "target": "API", "content": "处理结果", "type": "return"}},
        {{"source": "API", "target": "User", "content": "响应", "type": "return"}}
    ]
}}

# 质量要求
1. 从代码中抽象出典型的交互场景（如用户请求处理、数据操作、事件处理等）
2. 参与者应该是高层次的组件/角色，而非具体的类
3. 消息类型：sync（同步调用）、async（异步调用）、return（返回）
4. 展示关键的交互步骤，控制在 6-10 个消息
5. 反映业务层面的交互，而非技术细节

请务必返回合法的 JSON 格式。"""

        try:
            response = await llm_client.agenerate(prompt, system_prompt=system_prompt)
            start = response.find("{")
            end = response.rfind("}")
            if start != -1 and end != -1:
                data = json.loads(response[start:end+1])
                return self.sequence_gen.generate(data)
        except Exception:
            pass
        
        return ""

    async def _generate_class_diagram_with_llm(self, context: DocGeneratorContext, llm_client: Any) -> str:
        """使用 LLM 生成领域模型类图"""
        if not context.parse_result or not context.parse_result.modules:
            return ""

        # 提取类信息
        class_info = []
        filtered_modules = self._filter_project_modules(context.parse_result.modules, context.project_name)
        
        for module in filtered_modules[:15]:
            if hasattr(module, 'classes') and module.classes:
                for cls in module.classes[:5]:
                    attributes = []
                    if hasattr(cls, 'properties') and cls.properties:
                        for prop in cls.properties[:4]:
                            attributes.append({
                                "name": prop.name,
                                "type": getattr(prop, 'type_hint', ''),
                                "visibility": getattr(prop, 'visibility', 'public')
                            })
                    
                    methods = []
                    if hasattr(cls, 'methods') and cls.methods:
                        for method in cls.methods[:3]:
                            methods.append({
                                "name": method.name,
                                "visibility": getattr(method, 'visibility', 'public')
                            })
                    
                    bases = getattr(cls, 'bases', [])
                    
                    class_info.append({
                        "name": cls.name,
                        "module": module.name if hasattr(module, 'name') else str(module),
                        "attributes": attributes,
                        "methods": methods,
                        "bases": bases[:2],
                        "is_abstract": getattr(cls, 'is_abstract', False),
                    })

        system_prompt = "你是一名资深架构师，擅长领域驱动设计。请从代码中识别领域模型，抽象出核心实体及其关系，生成高层次的类图描述。"

        prompt = f"""# 任务
分析以下项目中的类定义，识别领域模型，抽象出核心实体及其关系，生成高层次的类图描述。

# 项目信息
- 项目名称: {context.project_name}
- 类数量: {len(class_info)}

# 类信息
```json
{json.dumps(class_info, ensure_ascii=False, indent=2)}
```

# 输出要求
请以 JSON 格式返回类图数据：
{{
    "title": "领域模型类图",
    "description": "核心领域实体及其关系",
    "classes": [
        {{
            "name": "User",
            "is_abstract": false,
            "is_interface": false,
            "attributes": [
                {{"name": "id", "type": "int", "visibility": "public"}},
                {{"name": "name", "type": "string", "visibility": "private"}}
            ],
            "methods": [
                {{"name": "login", "visibility": "public"}},
                {{"name": "logout", "visibility": "public"}}
            ]
        }}
    ],
    "relationships": [
        {{"source": "User", "target": "Order", "type": "association", "label": "places", "multiplicity": "1 *"}},
        {{"source": "Customer", "target": "User", "type": "inheritance"}},
        {{"source": "Order", "target": "Payment", "type": "composition"}}
    ]
}}

# 关系类型说明
- association: 关联 (--)
- inheritance: 继承 (--|>)
- implementation: 实现 (..|>)
- composition: 组合 (*--)
- aggregation: 聚合 (o--)
- dependency: 依赖 (..>)

# 质量要求
1. 识别核心业务实体（如用户、订单、产品等），过滤掉工具类、配置类
2. 提取实体的关键属性和方法
3. 识别实体间的关系（继承、关联、组合等）
4. 类数量控制在 4-8 个核心实体
5. 反映领域模型，而非技术实现

请务必返回合法的 JSON 格式。"""

        try:
            response = await llm_client.agenerate(prompt, system_prompt=system_prompt)
            start = response.find("{")
            end = response.rfind("}")
            if start != -1 and end != -1:
                data = json.loads(response[start:end+1])
                return self.class_diagram_gen.generate(data)
        except Exception:
            pass
        
        return ""

    async def _generate_state_diagram_with_llm(self, context: DocGeneratorContext, llm_client: Any) -> str:
        """使用 LLM 生成状态转移图"""
        if not context.parse_result or not context.parse_result.modules:
            return ""

        # 提取可能包含状态的类和枚举
        state_candidates = []
        filtered_modules = self._filter_project_modules(context.parse_result.modules, context.project_name)
        
        for module in filtered_modules[:20]:
            # 查找枚举（可能是状态定义）
            if hasattr(module, 'classes') and module.classes:
                for cls in module.classes:
                    # 检查类名是否包含状态相关关键词
                    name_lower = cls.name.lower()
                    if any(kw in name_lower for kw in ['state', 'status', 'phase', 'stage', 'mode']):
                        values = []
                        if hasattr(cls, 'properties') and cls.properties:
                            values = [p.name for p in cls.properties[:6]]
                        state_candidates.append({
                            "type": "enum/class",
                            "name": cls.name,
                            "module": module.name if hasattr(module, 'name') else str(module),
                            "values": values,
                        })
            
            # 查找包含状态字段的类
            if hasattr(module, 'classes') and module.classes:
                for cls in module.classes:
                    if hasattr(cls, 'properties') and cls.properties:
                        for prop in cls.properties:
                            prop_name_lower = prop.name.lower()
                            if any(kw in prop_name_lower for kw in ['state', 'status']):
                                state_candidates.append({
                                    "type": "field",
                                    "class": cls.name,
                                    "field": prop.name,
                                    "module": module.name if hasattr(module, 'name') else str(module),
                                })

        system_prompt = "你是一名资深架构师，擅长状态机建模。请从代码中识别业务实体的生命周期和状态转换，生成高层次的状态图描述。"

        prompt = f"""# 任务
分析以下项目中可能包含状态定义的类、枚举和字段，识别业务实体的生命周期，生成高层次的状态转移图描述。

# 项目信息
- 项目名称: {context.project_name}

# 状态候选信息
```json
{json.dumps(state_candidates, ensure_ascii=False, indent=2)}
```

# 输出要求
请以 JSON 格式返回状态图数据：
{{
    "title": "订单状态机",
    "entity": "Order",
    "states": [
        {{"name": "Pending", "description": "待处理"}},
        {{"name": "Processing", "description": "处理中"}},
        {{"name": "Completed", "description": "已完成"}},
        {{"name": "Cancelled", "description": "已取消"}}
    ],
    "transitions": [
        {{"source": "[*]", "target": "Pending", "event": "create", "guard": "", "action": ""}},
        {{"source": "Pending", "target": "Processing", "event": "submit", "guard": "", "action": ""}},
        {{"source": "Processing", "target": "Completed", "event": "complete", "guard": "", "action": ""}},
        {{"source": "Processing", "target": "Failed", "event": "error", "guard": "", "action": ""}},
        {{"source": "Pending", "target": "Cancelled", "event": "cancel", "guard": "", "action": ""}},
        {{"source": "Completed", "target": "[*]", "event": "", "guard": "", "action": ""}}
    ]
}}

# 质量要求
1. 识别核心业务实体的生命周期（如订单、任务、用户等）
2. 定义清晰的状态节点
3. 状态转换应该反映业务规则
4. 可以包含守卫条件(guard)和动作(action)
5. 使用 [*] 表示初始状态和终止状态
6. 状态数量控制在 4-8 个

请务必返回合法的 JSON 格式。"""

        try:
            response = await llm_client.agenerate(prompt, system_prompt=system_prompt)
            start = response.find("{")
            end = response.rfind("}")
            if start != -1 and end != -1:
                data = json.loads(response[start:end+1])
                return self.state_diagram_gen.generate(data)
        except Exception:
            pass
        
        return ""

    async def _generate_component_diagram_with_llm(self, context: DocGeneratorContext, llm_client: Any) -> str:
        """使用 LLM 生成组件架构图"""
        if not context.parse_result or not context.parse_result.modules:
            return ""

        # 提取模块和依赖信息
        module_info = []
        filtered_modules = self._filter_project_modules(context.parse_result.modules, context.project_name)
        
        for module in filtered_modules[:25]:
            module_name = module.name if hasattr(module, 'name') else str(module)
            name_lower = module_name.lower()
            
            # 推断模块类型
            module_type = "core"
            if any(kw in name_lower for kw in ['api', 'controller', 'web', 'rest']):
                module_type = "api"
            elif any(kw in name_lower for kw in ['service', 'business', 'domain']):
                module_type = "service"
            elif any(kw in name_lower for kw in ['repository', 'dao', 'data', 'db']):
                module_type = "data"
            elif any(kw in name_lower for kw in ['config', 'util', 'common']):
                module_type = "infrastructure"
            elif any(kw in name_lower for kw in ['client', 'sdk', 'integration']):
                module_type = "integration"
            
            # 提取依赖
            dependencies = []
            if hasattr(module, 'imports') and module.imports:
                for imp in module.imports:
                    imp_module = imp.module if hasattr(imp, 'module') else str(imp)
                    # 只保留项目内部依赖
                    if any(m.name == imp_module or imp_module.startswith(m.name + ".") for m in filtered_modules[:25]):
                        dependencies.append(imp_module.split(".")[0])
            
            module_info.append({
                "name": module_name,
                "type": module_type,
                "dependencies": list(set(dependencies))[:5],
            })

        system_prompt = "你是一名资深架构师，擅长组件化设计。请从代码模块中抽象出系统组件架构，识别组件边界和依赖关系，生成高层次的组件图描述。"

        prompt = f"""# 任务
分析以下项目模块结构和依赖关系，抽象出系统组件架构，识别组件边界和依赖关系，生成高层次的组件图描述。

# 项目信息
- 项目名称: {context.project_name}
- 模块数量: {len(filtered_modules)}

# 模块信息
```json
{json.dumps(module_info, ensure_ascii=False, indent=2)}
```

# 输出要求
请以 JSON 格式返回组件图数据：
{{
    "title": "系统组件架构",
    "description": "组件及其依赖关系",
    "components": [
        {{"name": "WebApp", "type": "component", "label": "Web Application"}},
        {{"name": "APIGateway", "type": "interface", "label": "API Gateway"}},
        {{"name": "UserService", "type": "component", "label": "User Service"}},
        {{"name": "OrderService", "type": "component", "label": "Order Service"}},
        {{"name": "Database", "type": "database", "label": "Database"}},
        {{"name": "MessageQueue", "type": "queue", "label": "Message Queue"}}
    ],
    "connections": [
        {{"source": "WebApp", "target": "APIGateway", "type": "sync", "label": "HTTP"}},
        {{"source": "APIGateway", "target": "UserService", "type": "sync", "label": "RPC"}},
        {{"source": "APIGateway", "target": "OrderService", "type": "sync", "label": "RPC"}},
        {{"source": "OrderService", "target": "UserService", "type": "sync", "label": "调用"}},
        {{"source": "UserService", "target": "Database", "type": "sync", "label": "SQL"}},
        {{"source": "OrderService", "target": "Database", "type": "sync", "label": "SQL"}},
        {{"source": "OrderService", "target": "MessageQueue", "type": "async", "label": "事件"}}
    ],
    "groups": [
        {{
            "name": "Frontend",
            "components": ["WebApp"]
        }},
        {{
            "name": "Backend Services",
            "components": ["UserService", "OrderService"]
        }},
        {{
            "name": "Infrastructure",
            "components": ["Database", "MessageQueue"]
        }}
    ]
}}

# 组件类型
- component: 普通组件 []
- database: 数据库 [()]
- queue: 消息队列 {{}}
- interface: 接口 [()]

# 连接类型
- sync: 同步调用 -->
- async: 异步调用 -.->
- bidirectional: 双向 ---
- dependency: 依赖 -..->

# 质量要求
1. 从模块中抽象出高层次的组件（服务、层、外部系统）
2. 识别组件间的依赖关系和交互方式
3. 将组件分组展示（如前端、后端服务、基础设施）
4. 组件数量控制在 6-12 个
5. 反映架构层面的组件划分，而非代码模块的直接映射

请务必返回合法的 JSON 格式。"""

        try:
            response = await llm_client.agenerate(prompt, system_prompt=system_prompt)
            start = response.find("{")
            end = response.rfind("}")
            if start != -1 and end != -1:
                data = json.loads(response[start:end+1])
                return self.component_diagram_gen.generate(data)
        except Exception:
            pass
        
        return ""
