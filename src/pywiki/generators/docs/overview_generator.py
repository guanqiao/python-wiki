"""
项目概述文档生成器
"""

import json
import re
import time
from pathlib import Path
from typing import Any, Optional

from pywiki.generators.docs.base import (
    BaseDocGenerator,
    DocGeneratorContext,
    DocGeneratorResult,
    DocType,
)
from pywiki.config.models import Language
from pywiki.monitor.logger import logger
from pywiki.analysis.package_analyzer import PackageAnalyzer


class OverviewGenerator(BaseDocGenerator):
    """项目概述文档生成器"""

    doc_type = DocType.OVERVIEW
    template_name = "overview.md.j2"

    THIRD_PARTY_PREFIXES = {
        "org.", "com.", "io.", "net.", "javax.", "java.",
        "liquibase.", "flowable.", "activiti.", "camunda.",
        "springframework.", "hibernate.", "mybatis.", "apache.",
        "lombok.", "slf4j.", "log4j.", "junit.", "mockito.",
        "jackson.", "gson.", "fastjson.", "okhttp.",
        "retrofit.", "feign.", "dubbo.", "nacos.", "sentinel.",
        "sharding.", "druid.", "hikari.", "redis.", "mongodb.",
        "elasticsearch.", "kafka.", "rabbitmq.", "zookeeper.",
        "curator.", "netty.", "vertx.", "quarkus.", "micronaut.",
        "jakarta.", "sun.", "jdk.", "oracle.", "ibm.",
    }

    def __init__(
        self,
        language: Language = Language.ZH,
        template_dir: Optional[Path] = None,
    ):
        super().__init__(language, template_dir)

    async def generate(self, context: DocGeneratorContext) -> DocGeneratorResult:
        """生成项目概述文档"""
        try:
            project_info = await self._collect_project_info(context)
            
            if context.metadata.get("llm_client"):
                enhanced_info = await self._enhance_with_llm(
                    context, 
                    project_info, 
                    context.metadata["llm_client"]
                )
                project_info.update(enhanced_info)

            content = self.render_template(
                title=project_info.get("title", context.project_name),
                description=project_info.get("description", ""),
                features=project_info.get("features", []),
                tech_stack=project_info.get("tech_stack", {}),
                architecture_diagram=project_info.get("architecture_diagram", ""),
                modules=project_info.get("modules", []),
                metadata=project_info.get("metadata", {}),
                code_stats=project_info.get("code_stats", {}),
                package_analysis=project_info.get("package_analysis", {}),
            )

            return self.create_result(
                content=content,
                context=context,
                success=True,
                message=self.labels.get("overview_success", "Overview document generated successfully"),
                metadata={"project_info": project_info},
            )

        except Exception as e:
            return self.create_result(
                content="",
                context=context,
                success=False,
                message=f"{self.labels.get('generation_failed', 'Generation failed')}: {str(e)}",
            )

    async def _collect_project_info(self, context: DocGeneratorContext) -> dict[str, Any]:
        """收集项目信息"""
        info = {
            "title": context.project_name,
            "description": "",
            "features": [],
            "tech_stack": {},
            "architecture_diagram": "",
            "modules": [],
            "metadata": {},
            "code_stats": {},
            "package_analysis": {},
        }

        info["description"] = await self._extract_description(context)
        info["features"] = await self._extract_features(context)
        info["tech_stack"] = await self._extract_tech_stack(context)
        info["architecture_diagram"] = self._generate_architecture_diagram(context)
        info["modules"] = self._extract_modules(context)
        info["metadata"] = self._extract_metadata(context)
        info["code_stats"] = self._extract_code_stats(context)
        info["package_analysis"] = self._extract_package_analysis(context)

        return info

    async def _extract_description(self, context: DocGeneratorContext) -> str:
        """提取项目描述"""
        description_parts = []
        
        readme_path = context.project_path / "README.md"
        if readme_path.exists():
            content = readme_path.read_text(encoding="utf-8")
            lines = content.split("\n")
            description_lines = []
            in_description = False
            
            for line in lines:
                if line.startswith("# "):
                    if in_description:
                        break
                    in_description = True
                    continue
                if in_description and line.strip():
                    if line.startswith("##"):
                        break
                    description_lines.append(line)
            
            if description_lines:
                description_parts.append(" ".join(description_lines).strip())

        pyproject_path = context.project_path / "pyproject.toml"
        if pyproject_path.exists():
            try:
                import tomllib
                with open(pyproject_path, "rb") as f:
                    data = tomllib.load(f)
                if "tool" in data and "poetry" in data["tool"]:
                    desc = data["tool"]["poetry"].get("description", "")
                    if desc and desc not in description_parts:
                        description_parts.append(desc)
                if "project" in data:
                    desc = data["project"].get("description", "")
                    if desc and desc not in description_parts:
                        description_parts.append(desc)
            except Exception:
                pass

        if context.parse_result and context.parse_result.modules:
            main_module = self._find_main_module(context.parse_result.modules, context.project_name)
            if main_module and main_module.docstring:
                main_desc = main_module.docstring.split("\n")[0]
                if main_desc and main_desc not in " ".join(description_parts):
                    description_parts.append(main_desc)

        if description_parts:
            return "\n\n".join(description_parts)
        
        return f"{context.project_name} {self.labels.get('project_documentation', 'Project Documentation')}"

    def _find_main_module(self, modules: list, project_name: str) -> Optional[Any]:
        """查找主模块"""
        project_prefix = project_name.replace("-", "_").lower()
        
        for module in modules:
            module_lower = module.name.lower()
            if module_lower == project_prefix or module_lower == f"{project_prefix}.__main__":
                return module
            if module_lower.startswith(project_prefix) and module_lower.count(".") == 1:
                return module
        
        for module in modules:
            if "__init__" in module.name or module.name.endswith(".__init__"):
                continue
            if module.docstring and len(module.docstring) > 50:
                return module
        
        return modules[0] if modules else None

    async def _extract_features(self, context: DocGeneratorContext) -> list[str]:
        """提取功能特性"""
        features = []

        readme_path = context.project_path / "README.md"
        if readme_path.exists():
            content = readme_path.read_text(encoding="utf-8")
            lines = content.split("\n")
            in_features = False
            
            for line in lines:
                if "功能" in line or "Features" in line or "特性" in line:
                    in_features = True
                    continue
                if in_features:
                    if line.startswith("##"):
                        break
                    if line.strip().startswith("- ") or line.strip().startswith("* "):
                        feature = line.strip()[2:].strip()
                        if feature:
                            features.append(feature)

        code_features = self._extract_features_from_code(context)
        for feature in code_features:
            if feature not in features:
                features.append(feature)

        if not features and context.parse_result and context.parse_result.modules:
            module_count = len(context.parse_result.modules)
            class_count = sum(len(m.classes) for m in context.parse_result.modules)
            func_count = sum(len(m.functions) for m in context.parse_result.modules)
            
            features.append(self.labels.get("contains_modules", "Contains {} modules").format(module_count))
            features.append(self.labels.get("defined_classes", "Defines {} classes").format(class_count))
            features.append(self.labels.get("provided_functions", "Provides {} functions").format(func_count))

        return features[:15]

    def _extract_features_from_code(self, context: DocGeneratorContext) -> list[str]:
        """从代码中提取功能特性"""
        features = []
        
        if not context.parse_result or not context.parse_result.modules:
            return features
        
        has_async = False
        has_dataclass = False
        has_context_manager = False
        has_iterator = False
        has_decorator = False
        has_property = False
        has_classmethod = False
        has_staticmethod = False
        decorator_types = set()
        
        for module in context.parse_result.modules:
            for func in module.functions:
                if hasattr(func, 'is_async') and func.is_async:
                    has_async = True
                if hasattr(func, 'is_classmethod') and func.is_classmethod:
                    has_classmethod = True
                if hasattr(func, 'is_staticmethod') and func.is_staticmethod:
                    has_staticmethod = True
                if hasattr(func, 'decorators') and func.decorators:
                    has_decorator = True
                    for d in func.decorators:
                        if "property" in d.lower():
                            has_property = True
                        elif "cached" in d.lower() or "lru_cache" in d.lower():
                            decorator_types.add(self.labels.get("caching_decorator", "Caching Decorator"))
                        elif "retry" in d.lower():
                            decorator_types.add(self.labels.get("retry_mechanism", "Retry Mechanism"))
            
            for cls in module.classes:
                if hasattr(cls, 'is_dataclass') and cls.is_dataclass:
                    has_dataclass = True
                if hasattr(cls, 'decorators') and cls.decorators:
                    has_decorator = True
                
                for method in cls.methods:
                    if hasattr(method, 'is_async') and method.is_async:
                        has_async = True
                    if hasattr(method, 'is_classmethod') and method.is_classmethod:
                        has_classmethod = True
                    if hasattr(method, 'is_staticmethod') and method.is_staticmethod:
                        has_staticmethod = True
                    if hasattr(method, 'decorators') and method.decorators:
                        has_decorator = True
                    
                    method_lower = method.name.lower()
                    if method_lower == "__enter__" or method_lower == "__exit__":
                        has_context_manager = True
                    if method_lower == "__iter__" or method_lower == "__next__":
                        has_iterator = True
                
                for prop in cls.properties:
                    if hasattr(prop, 'decorators') and prop.decorators:
                        has_property = True
        
        if has_async:
            features.append(self.labels.get("async_support", "Async Programming Support"))
        if has_dataclass:
            features.append(self.labels.get("dataclass_support", "Dataclass Support"))
        if has_context_manager:
            features.append(self.labels.get("context_manager_support", "Context Manager Support"))
        if has_iterator:
            features.append(self.labels.get("iterator_support", "Iterator Support"))
        if has_decorator:
            features.append(self.labels.get("decorator_pattern", "Decorator Pattern"))
        if has_property:
            features.append(self.labels.get("property_accessor", "Property Accessor"))
        if has_classmethod:
            features.append(self.labels.get("classmethod_support", "Classmethod Support"))
        if has_staticmethod:
            features.append(self.labels.get("staticmethod_support", "Staticmethod Support"))
        
        features.extend(list(decorator_types)[:3])
        
        return features

    async def _extract_tech_stack(self, context: DocGeneratorContext) -> dict[str, list[str]]:
        """提取技术栈"""
        tech_stack: dict[str, list[str]] = {}
        
        project_language = context.project_language or context.detect_project_language()
        
        if project_language == "java":
            tech_stack = self._extract_java_tech_stack(context)
        elif project_language == "typescript":
            tech_stack = self._extract_typescript_tech_stack(context)
        else:
            tech_stack = self._extract_python_tech_stack(context)

        if context.parse_result and context.parse_result.modules:
            import_tech = self._extract_tech_from_imports(context)
            for category, techs in import_tech.items():
                if category not in tech_stack:
                    tech_stack[category] = []
                for tech in techs:
                    if tech not in tech_stack[category]:
                        tech_stack[category].append(tech)
            
            languages = set()
            for module in context.parse_result.modules:
                if self._is_third_party_module(module.name, context.project_name):
                    continue
                if hasattr(module, "file_path"):
                    ext = Path(module.file_path).suffix if module.file_path else ""
                    if ext:
                        languages.add(ext)
            
            if languages:
                tech_stack[self.labels.get("language", "Language")] = [ext.lstrip(".") for ext in languages]

        return tech_stack

    def _extract_tech_from_imports(self, context: DocGeneratorContext) -> dict[str, list[str]]:
        """从导入中提取技术栈"""
        tech_stack: dict[str, list[str]] = {}
        
        if not context.parse_result or not context.parse_result.modules:
            return tech_stack
        
        import_counts: dict[str, int] = {}
        project_language = context.project_language or context.detect_project_language()
        
        for module in context.parse_result.modules:
            if self._is_third_party_module(module.name, context.project_name):
                continue
            for imp in module.imports:
                if imp.module.startswith("."):
                    continue
                base_module = imp.module.split(".")[0]
                import_counts[base_module] = import_counts.get(base_module, 0) + 1
        
        categories = {
            self.labels.get("web_frameworks", "Web Frameworks"): ["flask", "django", "fastapi", "starlette", "tornado", "aiohttp", "express", "koa", "nestjs", "spring"],
            self.labels.get("databases_tech", "Databases"): ["sqlalchemy", "pymongo", "redis", "psycopg", "mysql", "mongoose", "prisma", "typeorm"],
            self.labels.get("http_clients", "HTTP Clients"): ["requests", "httpx", "aiohttp", "urllib3", "axios", "fetch", "okhttp"],
            self.labels.get("testing", "Testing"): ["pytest", "unittest", "hypothesis", "jest", "mocha", "junit", "mockito"],
            self.labels.get("data_processing", "Data Processing"): ["pandas", "numpy", "scipy", "polars"],
            self.labels.get("machine_learning", "Machine Learning"): ["torch", "tensorflow", "sklearn", "transformers", "langchain"],
            self.labels.get("cli_tools", "CLI"): ["click", "typer", "argparse", "commander", "yargs"],
            self.labels.get("validation", "Validation"): ["pydantic", "marshmallow", "cerberus", "joi", "zod"],
            self.labels.get("logging_tech", "Logging"): ["loguru", "logging", "winston", "log4j", "slf4j"],
            self.labels.get("config_tech", "Configuration"): ["dotenv", "pydantic_settings", "configparser", "convict"],
        }
        
        python_only_libs = {"argparse", "click", "typer", "pytest", "unittest", "flask", "django", "fastapi", "pandas", "numpy"}
        java_only_libs = {"spring", "junit", "mockito", "hibernate", "mybatis", "maven", "gradle", "log4j", "slf4j"}
        ts_only_libs = {"express", "nestjs", "jest", "mocha", "typescript", "webpack", "vite"}
        
        for module_name, count in import_counts.items():
            module_lower = module_name.lower()
            
            if project_language == "java" and module_lower in python_only_libs:
                continue
            if project_language == "python" and module_lower in java_only_libs:
                continue
            if project_language == "typescript" and module_lower in python_only_libs | java_only_libs:
                continue
            
            for category, keywords in categories.items():
                if any(kw in module_lower for kw in keywords):
                    if category not in tech_stack:
                        tech_stack[category] = []
                    if module_name not in tech_stack[category]:
                        tech_stack[category].append(module_name)
                    break
        
        return tech_stack
    
    def _extract_python_tech_stack(self, context: DocGeneratorContext) -> dict[str, list[str]]:
        """提取 Python 项目技术栈"""
        tech_stack: dict[str, list[str]] = {}

        pyproject_path = context.project_path / "pyproject.toml"
        if pyproject_path.exists():
            try:
                import tomllib
                with open(pyproject_path, "rb") as f:
                    data = tomllib.load(f)

                deps = {}
                if "tool" in data and "poetry" in data["tool"]:
                    deps = data["tool"]["poetry"].get("dependencies", {})
                elif "project" in data:
                    deps = {d.split("[")[0]: "" for d in data["project"].get("dependencies", [])}

                categories = {
                    self.labels.get("web_frameworks", "Web Frameworks"): ["flask", "django", "fastapi", "starlette", "tornado", "aiohttp"],
                    self.labels.get("gui_frameworks", "GUI"): ["pyqt", "pyside", "tkinter", "wxpython"],
                    self.labels.get("data_processing", "Data Processing"): ["pandas", "numpy", "scipy", "polars"],
                    self.labels.get("machine_learning", "Machine Learning"): ["torch", "tensorflow", "sklearn", "transformers", "langchain"],
                    self.labels.get("databases_tech", "Databases"): ["sqlalchemy", "pymongo", "redis", "psycopg"],
                    self.labels.get("http_clients", "HTTP Clients"): ["requests", "httpx", "aiohttp", "urllib3"],
                    self.labels.get("testing", "Testing"): ["pytest", "unittest", "hypothesis"],
                    self.labels.get("cli_tools", "CLI"): ["click", "typer", "argparse"],
                    self.labels.get("validation", "Validation"): ["pydantic", "marshmallow", "cerberus"],
                }

                for dep_name in deps.keys():
                    dep_lower = dep_name.lower()
                    for category, keywords in categories.items():
                        if any(kw in dep_lower for kw in keywords):
                            if category not in tech_stack:
                                tech_stack[category] = []
                            tech_stack[category].append(dep_name)
                            break

            except Exception:
                pass

        return tech_stack
    
    def _extract_java_tech_stack(self, context: DocGeneratorContext) -> dict[str, list[str]]:
        """提取 Java 项目技术栈"""
        tech_stack: dict[str, list[str]] = {}

        pom_path = context.project_path / "pom.xml"
        if pom_path.exists():
            try:
                content = pom_path.read_text(encoding="utf-8")
                
                dependencies = re.findall(r"<groupId>([^<]+)</groupId>\s*<artifactId>([^<]+)</artifactId>", content)
                
                categories = {
                    self.labels.get("web_frameworks", "Web Frameworks"): ["spring-boot", "spring-webmvc", "spring-webflux", "struts", "play", "spark", "quarkus", "micronaut"],
                    self.labels.get("orm_frameworks", "ORM Frameworks"): ["hibernate", "mybatis", "jpa", "jooq", "querydsl"],
                    self.labels.get("databases_tech", "Databases"): ["mysql", "postgresql", "mongodb", "redis", "h2", "oracle"],
                    self.labels.get("testing", "Testing"): ["junit", "mockito", "testng", "assertj", "cucumber"],
                    self.labels.get("build_tools", "Build Tools"): ["maven", "gradle"],
                    self.labels.get("logging_tech", "Logging"): ["log4j", "logback", "slf4j"],
                    self.labels.get("json_processing", "JSON Processing"): ["jackson", "gson", "fastjson"],
                    self.labels.get("http_clients", "HTTP Clients"): ["okhttp", "apache-httpclient", "retrofit", "feign"],
                    self.labels.get("microservices", "Microservices"): ["spring-cloud", "dubbo", "grpc", "eureka", "nacos"],
                    self.labels.get("security", "Security"): ["spring-security", "shiro", "jwt"],
                }

                for group_id, artifact_id in dependencies:
                    artifact_lower = artifact_id.lower()
                    group_lower = group_id.lower()
                    for category, keywords in categories.items():
                        if any(kw in artifact_lower or kw in group_lower for kw in keywords):
                            if category not in tech_stack:
                                tech_stack[category] = []
                            if artifact_id not in tech_stack[category]:
                                tech_stack[category].append(artifact_id)
                            break

            except Exception:
                pass

        gradle_path = context.project_path / "build.gradle"
        gradle_kts_path = context.project_path / "build.gradle.kts"
        if gradle_path.exists() or gradle_kts_path.exists():
            try:
                gradle_file = gradle_path if gradle_path.exists() else gradle_kts_path
                content = gradle_file.read_text(encoding="utf-8")
                
                implementations = re.findall(r"implementation\s*['\"]([^'\":]+):([^'\":]+)", content)
                implementations += re.findall(r"compile\s*['\"]([^'\":]+):([^'\":]+)", content)
                
                categories = {
                    self.labels.get("web_frameworks", "Web Frameworks"): ["spring-boot", "spring-webmvc", "spring-webflux", "struts", "play", "spark", "quarkus", "micronaut"],
                    self.labels.get("orm_frameworks", "ORM Frameworks"): ["hibernate", "mybatis", "jpa", "jooq", "querydsl"],
                    self.labels.get("databases_tech", "Databases"): ["mysql", "postgresql", "mongodb", "redis", "h2", "oracle"],
                    self.labels.get("testing", "Testing"): ["junit", "mockito", "testng", "assertj", "cucumber"],
                    self.labels.get("build_tools", "Build Tools"): ["maven", "gradle"],
                    self.labels.get("logging_tech", "Logging"): ["log4j", "logback", "slf4j"],
                    self.labels.get("json_processing", "JSON Processing"): ["jackson", "gson", "fastjson"],
                    self.labels.get("http_clients", "HTTP Clients"): ["okhttp", "apache-httpclient", "retrofit", "feign"],
                    self.labels.get("microservices", "Microservices"): ["spring-cloud", "dubbo", "grpc", "eureka", "nacos"],
                    self.labels.get("security", "Security"): ["spring-security", "shiro", "jwt"],
                }

                for group_id, artifact_id in implementations:
                    artifact_lower = artifact_id.lower()
                    group_lower = group_id.lower()
                    for category, keywords in categories.items():
                        if any(kw in artifact_lower or kw in group_lower for kw in keywords):
                            if category not in tech_stack:
                                tech_stack[category] = []
                            if artifact_id not in tech_stack[category]:
                                tech_stack[category].append(artifact_id)
                            break

            except Exception:
                pass

        return tech_stack
    
    def _extract_typescript_tech_stack(self, context: DocGeneratorContext) -> dict[str, list[str]]:
        """提取 TypeScript 项目技术栈"""
        tech_stack: dict[str, list[str]] = {}

        package_path = context.project_path / "package.json"
        if package_path.exists():
            try:
                content = package_path.read_text(encoding="utf-8")
                data = json.loads(content)
                
                deps = {}
                deps.update(data.get("dependencies", {}))
                deps.update(data.get("devDependencies", {}))

                categories = {
                    self.labels.get("frontend_frameworks", "Frontend Frameworks"): ["react", "vue", "angular", "svelte", "next", "nuxt", "gatsby", "solid"],
                    self.labels.get("ui_libraries", "UI Libraries"): ["antd", "element", "mui", "material", "chakra", "tailwind", "bootstrap"],
                    self.labels.get("state_management", "State Management"): ["redux", "mobx", "zustand", "pinia", "vuex", "recoil", "jotai"],
                    self.labels.get("build_tools", "Build Tools"): ["webpack", "vite", "rollup", "esbuild", "parcel", "turbo"],
                    self.labels.get("testing", "Testing"): ["jest", "vitest", "mocha", "cypress", "playwright", "testing-library"],
                    self.labels.get("http_clients", "HTTP Clients"): ["axios", "fetch", "ky", "got", "superagent"],
                    self.labels.get("type_checking", "Type Checking"): ["typescript", "flow"],
                    self.labels.get("code_quality", "Code Quality"): ["eslint", "prettier", "husky", "lint-staged"],
                    self.labels.get("backend_frameworks", "Backend Frameworks"): ["express", "nestjs", "fastify", "koa", "hapi", "trpc"],
                    self.labels.get("databases_tech", "Databases"): ["prisma", "typeorm", "sequelize", "mongoose", "drizzle"],
                    "GraphQL": ["graphql", "apollo", "urql", "relay"],
                }

                for dep_name in deps.keys():
                    dep_lower = dep_name.lower()
                    for category, keywords in categories.items():
                        if any(kw in dep_lower for kw in keywords):
                            if category not in tech_stack:
                                tech_stack[category] = []
                            tech_stack[category].append(dep_name)
                            break

            except Exception:
                pass

        return tech_stack

    def _generate_architecture_diagram(self, context: DocGeneratorContext) -> str:
        """生成架构图"""
        if not context.parse_result or not context.parse_result.modules:
            return ""

        filtered_modules = [
            m for m in context.parse_result.modules 
            if not self._is_third_party_module(m.name, context.project_name)
        ]
        
        if not filtered_modules:
            return ""
        
        modules = filtered_modules[:15]
        
        lines = ["graph TB"]
        
        module_map = {}
        for module in modules:
            safe_name = self._sanitize_id(module.name)
            module_map[module.name] = safe_name
            display_name = self._extract_display_name(module.name)
            lines.append(f"    {safe_name}[{display_name}]")

        added_edges = set()
        for module in modules:
            source_safe = module_map[module.name]
            
            if hasattr(module, 'imports') and module.imports:
                for imp in module.imports:
                    target_module = imp.module
                    
                    for other_module in modules:
                        if other_module.name == target_module or other_module.name.startswith(target_module + "."):
                            target_safe = module_map[other_module.name]
                            edge_key = f"{source_safe}->{target_safe}"
                            if edge_key not in added_edges:
                                lines.append(f"    {source_safe} --> {target_safe}")
                                added_edges.add(edge_key)
                            break

        if len(added_edges) == 0:
            for i, module in enumerate(modules):
                if i > 0:
                    safe_name = module_map[module.name]
                    prev_safe = module_map[modules[i-1].name]
                    edge_key = f"{prev_safe}->{safe_name}"
                    if edge_key not in added_edges:
                        lines.append(f"    {prev_safe} --> {safe_name}")
                        added_edges.add(edge_key)

        return "\n".join(lines)

    def _sanitize_id(self, name: str) -> str:
        """将名称转换为有效的 Mermaid ID"""
        sanitized = name.replace("\\", "_").replace("/", "_")
        sanitized = sanitized.replace(".", "_").replace("-", "_").replace(" ", "_")
        sanitized = sanitized.replace(":", "_").replace("(", "_").replace(")", "_")
        while "__" in sanitized:
            sanitized = sanitized.replace("__", "_")
        sanitized = sanitized.strip("_")
        return sanitized[:25]

    def _is_third_party_module(self, module_name: str, project_name: str) -> bool:
        """判断是否为第三方库模块"""
        module_lower = module_name.lower()
        
        for prefix in self.THIRD_PARTY_PREFIXES:
            if module_lower.startswith(prefix):
                return True
        
        if re.match(r'^[A-Za-z]:[\\/]', module_name) or module_name.startswith('/') or module_name.startswith('\\'):
            normalized = module_name.replace('\\', '/').lower()
            project_prefix = project_name.replace('-', '_').replace('.', '_').lower()
            parts = normalized.split('/')
            meaningful_parts = [p for p in parts if p and p != '.' and p != '..' and not re.match(r'^[A-Za-z]:$', p)]
            if meaningful_parts:
                first_meaningful = meaningful_parts[0].lower()
                if first_meaningful in self.THIRD_PARTY_PREFIXES or first_meaningful in {
                    'org', 'com', 'io', 'net', 'javax', 'java', 'liquibase', 'flowable'
                }:
                    return True
            return False
        
        return False

    def _extract_modules(self, context: DocGeneratorContext) -> list[dict[str, str]]:
        """提取模块列表"""
        project_language = context.project_language or context.detect_project_language()
        
        if project_language == "java":
            java_modules = self._extract_java_modules_from_build(context)
            if java_modules:
                return java_modules
        
        modules = []
        
        if context.parse_result and context.parse_result.modules:
            for module in context.parse_result.modules:
                if self._is_third_party_module(module.name, context.project_name):
                    continue
                
                class_count = len(module.classes) if module.classes else 0
                func_count = len(module.functions) if module.functions else 0
                
                display_name = self._extract_display_name(module.name)
                module_path = self._extract_module_path(module.name, context.project_name)
                
                modules.append({
                    "name": display_name,
                    "full_name": module.name,
                    "path": module_path,
                    "description": module.docstring.split("\n")[0] if module.docstring else "",
                    "class_count": class_count,
                    "func_count": func_count,
                })

        return modules[:20]

    def _extract_display_name(self, module_name: str) -> str:
        """提取模块显示名称"""
        if re.match(r'^[A-Za-z]:[\\/]', module_name) or module_name.startswith('/') or module_name.startswith('\\'):
            parts = re.split(r'[\\/]', module_name)
            meaningful_parts = [p for p in parts if p and p != '.' and p != '..' and not re.match(r'^[A-Za-z]:$', p)]
            if meaningful_parts:
                name = meaningful_parts[-1]
                return name.replace('.py', '').replace('.java', '').replace('.ts', '')
        
        if '.' in module_name:
            parts = module_name.split('.')
            for i in range(len(parts) - 1, -1, -1):
                if parts[i] and not parts[i].startswith('_'):
                    return parts[i]
            return parts[-1]
        
        return module_name

    def _extract_module_path(self, module_name: str, project_name: str) -> str:
        """提取模块路径（用于生成文档链接）"""
        if re.match(r'^[A-Za-z]:[\\/]', module_name) or module_name.startswith('/') or module_name.startswith('\\'):
            normalized = module_name.replace('\\', '/')
            parts = normalized.split('/')
            meaningful_parts = [p for p in parts if p and p != '.' and p != '..' and not re.match(r'^[A-Za-z]:$', p)]
            
            project_prefix = project_name.replace('-', '_').replace('.', '_').lower()
            start_idx = 0
            for i, part in enumerate(meaningful_parts):
                if part.lower().replace('-', '_') == project_prefix or i == 0:
                    start_idx = i
                    break
            
            relevant_parts = meaningful_parts[start_idx:]
            if relevant_parts:
                name = relevant_parts[-1].replace('.py', '').replace('.java', '').replace('.ts', '')
                return '/'.join(relevant_parts[:-1] + [name]) if len(relevant_parts) > 1 else name
            return meaningful_parts[-1] if meaningful_parts else module_name
        
        return module_name.replace('.', '/')

    def _extract_code_stats(self, context: DocGeneratorContext) -> dict[str, Any]:
        """提取代码统计"""
        stats = {
            "total_modules": 0,
            "total_classes": 0,
            "total_functions": 0,
            "total_methods": 0,
            "total_properties": 0,
            "async_functions": 0,
            "async_methods": 0,
            "has_tests": False,
        }
        
        if not context.parse_result or not context.parse_result.modules:
            return stats
        
        stats["total_modules"] = len(context.parse_result.modules)
        
        for module in context.parse_result.modules:
            stats["total_classes"] += len(module.classes) if module.classes else 0
            stats["total_functions"] += len(module.functions) if module.functions else 0
            
            if "test" in module.name.lower():
                stats["has_tests"] = True
            
            for func in (module.functions or []):
                if hasattr(func, 'is_async') and func.is_async:
                    stats["async_functions"] += 1
            
            for cls in (module.classes or []):
                stats["total_methods"] += len(cls.methods) if cls.methods else 0
                stats["total_properties"] += len(cls.properties) if cls.properties else 0
                
                for method in (cls.methods or []):
                    if hasattr(method, 'is_async') and method.is_async:
                        stats["async_methods"] += 1
        
        return stats

    def _extract_metadata(self, context: DocGeneratorContext) -> dict[str, str]:
        """提取元数据"""
        metadata = {
            "version": "",
            "license": "",
            "author": "",
            "homepage": "",
            "repository": "",
            "created_at": "",
        }

        pyproject_path = context.project_path / "pyproject.toml"
        if pyproject_path.exists():
            try:
                import tomllib
                with open(pyproject_path, "rb") as f:
                    data = tomllib.load(f)

                if "tool" in data and "poetry" in data["tool"]:
                    poetry = data["tool"]["poetry"]
                    metadata["version"] = poetry.get("version", "")
                    metadata["license"] = poetry.get("license", "")
                    if "authors" in poetry and poetry["authors"]:
                        if isinstance(poetry["authors"], list) and len(poetry["authors"]) > 0:
                            author = poetry["authors"][0]
                            if isinstance(author, dict):
                                metadata["author"] = author.get("name", str(author))
                            else:
                                metadata["author"] = str(author)
                    if "homepage" in poetry:
                        metadata["homepage"] = poetry["homepage"]
                    if "repository" in poetry:
                        metadata["repository"] = poetry["repository"]
                        
                elif "project" in data:
                    project = data["project"]
                    metadata["version"] = project.get("version", "")
                    if "authors" in project and project["authors"]:
                        if isinstance(project["authors"], list) and len(project["authors"]) > 0:
                            author = project["authors"][0]
                            if isinstance(author, dict):
                                metadata["author"] = author.get("name", str(author))
                            else:
                                metadata["author"] = str(author)
                    if "license" in project:
                        license_info = project["license"]
                        if isinstance(license_info, dict):
                            metadata["license"] = license_info.get("text", "")
                        else:
                            metadata["license"] = str(license_info)

            except Exception:
                pass

        package_path = context.project_path / "package.json"
        if package_path.exists() and not metadata["version"]:
            try:
                content = package_path.read_text(encoding="utf-8")
                data = json.loads(content)
                metadata["version"] = data.get("version", "")
                metadata["license"] = data.get("license", "")
                if "author" in data:
                    author = data["author"]
                    if isinstance(author, dict):
                        metadata["author"] = author.get("name", str(author))
                    else:
                        metadata["author"] = str(author)
                if "homepage" in data:
                    metadata["homepage"] = data["homepage"]
                if "repository" in data:
                    repo = data["repository"]
                    if isinstance(repo, dict):
                        metadata["repository"] = repo.get("url", "")
                    else:
                        metadata["repository"] = str(repo)
            except Exception:
                pass

        pom_path = context.project_path / "pom.xml"
        if pom_path.exists() and not metadata["version"]:
            try:
                content = pom_path.read_text(encoding="utf-8")
                version_match = re.search(r"<version>([^<]+)</version>", content)
                if version_match:
                    metadata["version"] = version_match.group(1)
                
                group_match = re.search(r"<groupId>([^<]+)</groupId>", content)
                artifact_match = re.search(r"<artifactId>([^<]+)</artifactId>", content)
                if group_match and artifact_match:
                    metadata["repository"] = f"{group_match.group(1)}/{artifact_match.group(1)}"
            except Exception:
                pass

        from datetime import datetime
        metadata["created_at"] = datetime.now().strftime("%Y-%m-%d")

        return metadata

    def _extract_package_analysis(self, context: DocGeneratorContext) -> dict[str, Any]:
        """提取包分析数据"""
        try:
            analysis = context.get_package_analysis()
            
            summary = analysis.get("summary", {})
            layers = analysis.get("layers", [])
            layer_distribution = analysis.get("layer_distribution", {})
            metrics = analysis.get("metrics", [])
            
            top_metrics = sorted(metrics, key=lambda m: m.get("coupling", 0), reverse=True)[:10]
            
            return {
                "total_packages": summary.get("total_packages", 0),
                "total_dependencies": summary.get("total_dependencies", 0),
                "circular_dependency_count": summary.get("circular_dependency_count", 0),
                "layer_violation_count": summary.get("layer_violation_count", 0),
                "avg_stability": round(summary.get("avg_stability", 0), 3),
                "avg_cohesion": round(summary.get("avg_cohesion", 0), 3),
                "layers": [
                    {
                        "name": layer.get("name", ""),
                        "package_count": len(layer.get("packages", [])),
                        "description": layer.get("description", ""),
                    }
                    for layer in layers
                ],
                "layer_distribution": {
                    k: len(v) for k, v in layer_distribution.items() if v
                },
                "top_packages_by_coupling": [
                    {
                        "package": m.get("package", ""),
                        "coupling": m.get("coupling", 0),
                        "stability": m.get("stability", 0),
                        "cohesion": m.get("cohesion", 0),
                    }
                    for m in top_metrics
                ],
                "subpackages": analysis.get("subpackages", [])[:20],
            }
        except Exception:
            return {}

    async def _enhance_with_llm(
        self,
        context: DocGeneratorContext,
        project_info: dict[str, Any],
        llm_client: Any,
    ) -> dict[str, Any]:
        """使用 LLM 增强文档内容"""
        enhanced = {}
        
        code_stats = project_info.get("code_stats", {})
        project_language = context.project_language or context.detect_project_language()
        
        modules = project_info.get("modules", [])
        module_names = [m.get("name", "").split(".")[-1] for m in modules[:10] if m.get("name")]
        
        tech_stack = project_info.get("tech_stack", {})
        tech_stack_summary = []
        for category, techs in tech_stack.items():
            if techs:
                tech_stack_summary.append(f"{category}: {', '.join(techs[:5])}")
        
        system_prompt = self._get_system_prompt()
        
        if self.language == Language.ZH:
            prompt = f"""# 任务
分析项目信息，生成专业的项目概述文档。

# 项目数据
- **项目名称**: {context.project_name}
- **项目语言**: {project_language.upper()}
- **模块数量**: {code_stats.get('total_modules', 0)}
- **类数量**: {code_stats.get('total_classes', 0)}
- **函数数量**: {code_stats.get('total_functions', 0)}
- **异步函数**: {code_stats.get('async_functions', 0) + code_stats.get('async_methods', 0)}
- **主要模块**: {', '.join(module_names) if module_names else '无'}
- **技术栈**: {chr(10).join('- ' + t for t in tech_stack_summary) if tech_stack_summary else '未检测到'}
- **功能特性**: {json.dumps(project_info.get('features', []), ensure_ascii=False)}

# 输出要求
请以 JSON 格式返回以下字段：
{{
    "enhanced_description": "项目描述（800-1000字，包含：项目背景与定位、核心价值主张、主要功能模块、技术架构特点、设计理念与原则、适用场景与优势）",
    "key_features": ["核心功能1（简洁描述）", "核心功能2", "核心功能3"],
    "target_users": "目标用户群体描述",
    "use_cases": ["典型使用场景1", "典型使用场景2"]
}}

# 质量标准
- 描述需全面详尽，结构清晰，分层次展开
- 项目背景需说明解决的问题和存在的意义
- 核心价值需突出项目的独特优势和竞争力
- 功能模块需按重要性排序，说明各模块职责
- 技术特点需具体说明技术选型的理由
- 设计理念需体现架构思想和最佳实践
- 避免泛泛而谈，每部分都需有实质性内容
- 必须基于项目语言({project_language.upper()})进行描述，不要错误地描述为其他语言

请务必使用中文回答。"""
        else:
            prompt = f"""# Task
Analyze project information and generate a professional project overview document.

# Project Data
- **Project Name**: {context.project_name}
- **Project Language**: {project_language.upper()}
- **Module Count**: {code_stats.get('total_modules', 0)}
- **Class Count**: {code_stats.get('total_classes', 0)}
- **Function Count**: {code_stats.get('total_functions', 0)}
- **Async Functions**: {code_stats.get('async_functions', 0) + code_stats.get('async_methods', 0)}
- **Main Modules**: {', '.join(module_names) if module_names else 'None'}
- **Tech Stack**: {chr(10).join('- ' + t for t in tech_stack_summary) if tech_stack_summary else 'Not detected'}
- **Features**: {json.dumps(project_info.get('features', []), ensure_ascii=False)}

# Output Requirements
Please return the following fields in JSON format:
{{
    "enhanced_description": "Project description (800-1000 words, including: project background and positioning, core value proposition, main functional modules, technical architecture characteristics, design philosophy and principles, applicable scenarios and advantages)",
    "key_features": ["core feature 1 (concise description)", "core feature 2", "core feature 3"],
    "target_users": "Target user group description",
    "use_cases": ["typical use case 1", "typical use case 2"]
}}

# Quality Standards
- Description should be comprehensive and well-structured, organized in layers
- Project background should explain the problem being solved and significance
- Core value should highlight unique advantages and competitiveness
- Functional modules should be ordered by importance with clear responsibilities
- Technical characteristics should explain rationale for technology choices
- Design philosophy should reflect architectural thinking and best practices
- Avoid generalizations, each section should have substantive content
- Must be based on the project language ({project_language.upper()}), do not incorrectly describe it as another language

Please respond in English."""

        start_time = time.time()
        prompt_length = len(prompt)
        logger.info(f"Overview LLM 增强开始: project={context.project_name}, prompt_length={prompt_length}")
        try:
            response = await llm_client.agenerate(prompt, system_prompt=system_prompt)
            start = response.find("{")
            end = response.rfind("}")
            if start != -1 and end != -1:
                result = json.loads(response[start:end+1])
                enhanced["description"] = result.get("enhanced_description", "")
                if result.get("key_features"):
                    enhanced["features"] = result["key_features"]
                duration_ms = (time.time() - start_time) * 1000
                logger.info(f"Overview LLM 增强完成: 耗时={duration_ms:.0f}ms, 解析成功")
            else:
                duration_ms = (time.time() - start_time) * 1000
                logger.warning(f"Overview LLM 增强完成但解析失败: 耗时={duration_ms:.0f}ms, 响应格式不正确")
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            logger.error(f"Overview LLM 增强失败: 耗时={duration_ms:.0f}ms, 错误={str(e)}")

        return enhanced
