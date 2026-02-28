"""
依赖文档生成器
"""

import json
import re
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
from pywiki.knowledge.dependency_analyzer import DeepDependencyAnalyzer


class DependenciesGenerator(BaseDocGenerator):
    """依赖文档生成器"""

    doc_type = DocType.DEPENDENCIES
    template_name = "dependencies.md.j2"

    def __init__(
        self,
        language: Language = Language.ZH,
        template_dir: Optional[Path] = None,
    ):
        super().__init__(language, template_dir)
        self.dependency_analyzer = DeepDependencyAnalyzer()

    async def generate(self, context: DocGeneratorContext) -> DocGeneratorResult:
        """生成依赖文档"""
        try:
            dep_data = await self._analyze_dependencies(context)
            
            if context.metadata.get("llm_client"):
                enhanced_data = await self._enhance_with_llm(
                    context,
                    dep_data,
                    context.metadata["llm_client"]
                )
                dep_data.update(enhanced_data)

            content = self.render_template(
                description=f"{context.project_name} 依赖关系分析",
                external=dep_data.get("external", []),
                internal=dep_data.get("internal", []),
                circular=dep_data.get("circular", []),
                hot_spots=dep_data.get("hot_spots", []),
                dependency_strength=dep_data.get("dependency_strength", {}),
                dependency_versions=dep_data.get("dependency_versions", {}),
                recommendations=dep_data.get("recommendations", []),
                summary=dep_data.get("summary", {}),
                package_dependencies=dep_data.get("package_dependencies", []),
                package_metrics=dep_data.get("package_metrics", []),
                layer_violations=dep_data.get("layer_violations", []),
            )

            return self.create_result(
                content=content,
                context=context,
                success=True,
                message=self.labels.get("dependencies_doc_success", "Dependencies documentation generated successfully"),
                metadata={"dependency_data": dep_data.get("summary", {})},
            )

        except Exception as e:
            return self.create_result(
                content="",
                context=context,
                success=False,
                message=f"{self.labels.get('generation_failed', 'Generation failed')}: {str(e)}",
            )

    async def _analyze_dependencies(self, context: DocGeneratorContext) -> dict[str, Any]:
        """分析依赖关系"""
        dep_data = {
            "external": [],
            "internal": [],
            "circular": [],
            "hot_spots": [],
            "dependency_strength": {},
            "dependency_versions": {},
            "recommendations": [],
            "summary": {},
        }

        external_deps: dict[str, dict] = {}
        internal_deps = []
        import_usage: dict[str, list] = defaultdict(list)
        
        project_prefix = context.project_name.replace("-", "_").split("_")[0].lower()
        project_language = context.project_language or context.detect_project_language()

        if project_language == "java":
            java_deps = self._extract_java_dependencies(context)
            external_deps.update(java_deps.get("external", {}))
            internal_deps.extend(java_deps.get("internal", []))
            dep_data["dependency_versions"] = java_deps.get("versions", {})
            dep_data["build_tool"] = java_deps.get("build_tool", "")

        if context.parse_result and context.parse_result.modules:
            for module in context.parse_result.modules:
                for imp in module.imports:
                    if imp.module.startswith("."):
                        rel_target = imp.module
                        internal_deps.append({
                            "source": module.name,
                            "target": rel_target,
                            "type": "relative_import",
                            "line": getattr(imp, 'line', 0),
                            "names": getattr(imp, 'names', []) or [],
                            "alias": getattr(imp, 'alias', ''),
                        })
                        continue
                    
                    base_module = imp.module.split(".")[0]
                    
                    if project_language == "java":
                        parts = imp.module.split(".")
                        if len(parts) >= 3 and parts[0] in ("org", "com", "io", "net", "cn", "javax", "jakarta"):
                            base_module = ".".join(parts[:3])
                        elif len(parts) >= 2:
                            base_module = ".".join(parts[:2])
                        else:
                            base_module = imp.module
                    
                    if base_module.lower().startswith(project_prefix):
                        internal_deps.append({
                            "source": module.name,
                            "target": imp.module,
                            "type": "internal",
                            "line": getattr(imp, 'line', 0),
                            "names": getattr(imp, 'names', []) or [],
                            "alias": getattr(imp, 'alias', ''),
                        })
                    else:
                        if base_module not in external_deps:
                            version = self._get_dependency_version(base_module, context)
                            external_deps[base_module] = {
                                "name": base_module,
                                "version": version,
                                "category": self._categorize_dependency(base_module),
                                "description": self._get_dependency_description(base_module),
                                "usage_count": 0,
                                "usage_locations": [],
                                "import_details": [],
                            }
                        
                        external_deps[base_module]["usage_count"] += 1
                        external_deps[base_module]["usage_locations"].append(module.name)
                        external_deps[base_module]["import_details"].append({
                            "module": module.name,
                            "line": getattr(imp, 'line', 0),
                            "full_import": imp.module,
                            "names": getattr(imp, 'names', []) or [],
                            "alias": getattr(imp, 'alias', ''),
                        })
                        
                        import_usage[base_module].append(module.name)

        dep_data["external"] = sorted(
            [d for d in external_deps.values() if self._is_valid_module_name(d["name"])],
            key=lambda x: x["usage_count"],
            reverse=True
        )
        dep_data["internal"] = internal_deps[:100]
        
        dep_data["dependency_strength"] = self._analyze_dependency_strength(import_usage)
        
        if not dep_data["dependency_versions"]:
            dep_data["dependency_versions"] = self._extract_all_versions(context)

        try:
            graph = self.dependency_analyzer.analyze_modules(context.parse_result.modules)
            
            dep_data["circular"] = [
                {
                    "cycle": cycle,
                    "severity": "high" if len(cycle) <= 3 else "medium",
                    "description": f"循环依赖: {' -> '.join(cycle)}",
                }
                for cycle in graph.circular_dependencies[:10]
            ]
            
            dep_data["hot_spots"] = []
            for module in graph.hot_spots:
                if not self._is_valid_module_name(module):
                    continue
                dep_data["hot_spots"].append({
                    "module": module,
                    "incoming": sum(1 for e in graph.edges if e.target == module),
                    "outgoing": sum(1 for e in graph.edges if e.source == module),
                    "total": sum(1 for e in graph.edges if e.target == module) + sum(1 for e in graph.edges if e.source == module),
                    "risk": "high" if sum(1 for e in graph.edges if e.target == module) > 5 else "medium",
                })
            
            report = self.dependency_analyzer.generate_dependency_report(graph)
            dep_data["recommendations"] = report.get("recommendations", [])
            dep_data["summary"] = report.get("summary", {})
            
        except Exception:
            pass

        try:
            package_analysis = context.get_package_analysis()
            dep_data["package_dependencies"] = package_analysis.get("dependencies", [])[:30]
            dep_data["package_metrics"] = package_analysis.get("metrics", [])[:20]
            dep_data["layer_violations"] = package_analysis.get("violations", [])
            
            pkg_circular = package_analysis.get("circular_dependencies", [])
            if pkg_circular and not dep_data.get("circular"):
                dep_data["circular"] = [
                    {
                        "cycle": cycle,
                        "severity": "high" if len(cycle) <= 3 else "medium",
                        "description": f"循环依赖: {' -> '.join(cycle)}",
                    }
                    for cycle in pkg_circular[:10]
                ]
        except Exception:
            pass

        dep_data["summary"].update({
            "total_external": len(external_deps),
            "total_internal": len(internal_deps),
            "total_circular": len(dep_data["circular"]),
            "total_hot_spots": len(dep_data["hot_spots"]),
            "top_dependencies": sorted(
                [(name, len(locations)) for name, locations in import_usage.items()],
                key=lambda x: x[1],
                reverse=True
            )[:10],
        })

        return dep_data

    def _extract_java_dependencies(self, context: DocGeneratorContext) -> dict[str, Any]:
        """提取Java项目依赖"""
        result = {
            "external": {},
            "internal": [],
            "versions": {},
            "build_tool": "",
        }
        
        pom_path = context.project_path / "pom.xml"
        if pom_path.exists():
            result["build_tool"] = "Maven"
            maven_deps = self._parse_maven_pom(pom_path, context)
            result["external"].update(maven_deps.get("external", {}))
            result["versions"].update(maven_deps.get("versions", {}))
        
        gradle_path = context.project_path / "build.gradle"
        gradle_kts_path = context.project_path / "build.gradle.kts"
        
        if gradle_path.exists() or gradle_kts_path.exists():
            if not result["build_tool"]:
                result["build_tool"] = "Gradle"
            gradle_file = gradle_path if gradle_path.exists() else gradle_kts_path
            gradle_deps = self._parse_gradle_build(gradle_file)
            result["external"].update(gradle_deps.get("external", {}))
            result["versions"].update(gradle_deps.get("versions", {}))
        
        if context.parse_result and context.parse_result.modules:
            for module in context.parse_result.modules:
                module_name = module.name
                for imp in module.imports:
                    imp_module = imp.module
                    
                    if imp_module.startswith("java.") or imp_module.startswith("javax.") or imp_module.startswith("jakarta."):
                        continue
                    
                    if imp_module.startswith("org.springframework.") or imp_module.startswith("com.baomidou."):
                        base_name = imp_module.split(".")[2] if imp_module.count(".") >= 2 else imp_module.split(".")[1]
                        group_id = ".".join(imp_module.split(".")[:3]) if imp_module.count(".") >= 2 else imp_module.split(".")[0]
                        
                        if base_name not in result["external"]:
                            version = result["versions"].get(group_id, "")
                            result["external"][base_name] = {
                                "name": base_name,
                                "group_id": group_id,
                                "version": version,
                                "category": self._categorize_dependency(base_name),
                                "description": self._get_dependency_description(base_name),
                                "usage_count": 1,
                                "usage_locations": [module_name],
                                "import_details": [{
                                    "module": module_name,
                                    "full_import": imp_module,
                                }],
                            }
                        else:
                            result["external"][base_name]["usage_count"] += 1
                            result["external"][base_name]["usage_locations"].append(module_name)
        
        return result

    def _parse_maven_pom(self, pom_path: Path, context: DocGeneratorContext) -> dict[str, Any]:
        """解析Maven pom.xml"""
        result = {
            "external": {},
            "versions": {},
        }
        
        try:
            content = pom_path.read_text(encoding="utf-8")
            
            properties = {}
            prop_pattern = r'<(\w+(?:\.\w+)*)>\s*([^<]+)\s*</\1>'
            for match in re.finditer(prop_pattern, content):
                prop_name = match.group(1)
                prop_value = match.group(2).strip()
                properties[prop_name] = prop_value
            
            dep_pattern = r'<dependency>\s*<groupId>([^<]+)</groupId>\s*<artifactId>([^<]+)</artifactId>(?:\s*<version>([^<]*)</version>)?'
            matches = re.findall(dep_pattern, content, re.DOTALL)
            
            for group_id, artifact_id, version in matches:
                group_id = group_id.strip()
                artifact_id = artifact_id.strip()
                version = version.strip() if version else ""
                
                if version and version.startswith("${"):
                    prop_name = version[2:-1]
                    version = properties.get(prop_name, "")
                
                if not version:
                    version = properties.get(f"{artifact_id}.version", "")
                if not version:
                    version = properties.get("version", "")
                
                result["versions"][artifact_id] = version
                result["versions"][group_id] = version
                
                category = self._categorize_dependency(artifact_id)
                description = self._get_dependency_description(artifact_id)
                
                result["external"][artifact_id] = {
                    "name": artifact_id,
                    "group_id": group_id,
                    "version": version,
                    "category": category,
                    "description": description,
                    "usage_count": 0,
                    "usage_locations": [],
                    "import_details": [],
                }
            
            parent_pattern = r'<parent>\s*<groupId>([^<]+)</groupId>\s*<artifactId>([^<]+)</artifactId>\s*<version>([^<]+)</version>'
            parent_match = re.search(parent_pattern, content, re.DOTALL)
            if parent_match:
                parent_group = parent_match.group(1).strip()
                parent_artifact = parent_match.group(2).strip()
                parent_version = parent_match.group(3).strip()
                
                result["versions"][parent_artifact] = parent_version
                result["versions"]["parent"] = f"{parent_group}:{parent_artifact}:{parent_version}"
        
        except Exception:
            pass
        
        return result

    def _parse_gradle_build(self, gradle_path: Path) -> dict[str, Any]:
        """解析Gradle build.gradle"""
        result = {
            "external": {},
            "versions": {},
        }
        
        try:
            content = gradle_path.read_text(encoding="utf-8")
            
            implementation_pattern = r'(?:implementation|api|compileOnly|runtimeOnly|testImplementation|testCompileOnly|testRuntimeOnly)\s*[\'"]([^\'":]+):([^\'":]+):?([^\'"]*)[\'"]'
            matches = re.findall(implementation_pattern, content)
            
            for group_id, artifact_id, version in matches:
                group_id = group_id.strip()
                artifact_id = artifact_id.strip()
                version = version.strip() if version else ""
                
                result["versions"][artifact_id] = version
                result["versions"][group_id] = version
                
                category = self._categorize_dependency(artifact_id)
                description = self._get_dependency_description(artifact_id)
                
                result["external"][artifact_id] = {
                    "name": artifact_id,
                    "group_id": group_id,
                    "version": version,
                    "category": category,
                    "description": description,
                    "usage_count": 0,
                    "usage_locations": [],
                    "import_details": [],
                }
            
            plugin_pattern = r'id\s*\(?[\'"]([^\'"]+)[\'"]\s*\)?\s*version\s*[\'"]([^\'"]+)[\'"]'
            plugin_matches = re.findall(plugin_pattern, content)
            
            for plugin_id, plugin_version in plugin_matches:
                result["versions"][plugin_id] = plugin_version
        
        except Exception:
            pass
        
        return result

    def _get_dependency_version(self, name: str, context: DocGeneratorContext) -> str:
        """获取依赖版本"""
        pyproject_path = context.project_path / "pyproject.toml"
        if pyproject_path.exists():
            try:
                import tomllib
                with open(pyproject_path, "rb") as f:
                    data = tomllib.load(f)
                
                if "project" in data and "dependencies" in data["project"]:
                    for dep in data["project"]["dependencies"]:
                        if dep.lower().startswith(name.lower()):
                            version = re.search(r'[\d.]+', dep)
                            if version:
                                return version.group()
                
                if "tool" in data and "poetry" in data["tool"]:
                    deps = data["tool"]["poetry"].get("dependencies", {})
                    for dep_name, dep_info in deps.items():
                        if dep_name.lower() == name.lower():
                            if isinstance(dep_info, str):
                                version = re.search(r'[\d.]+', dep_info)
                                return version.group() if version else dep_info
                            elif isinstance(dep_info, dict) and "version" in dep_info:
                                version = re.search(r'[\d.]+', dep_info["version"])
                                return version.group() if version else dep_info["version"]
            except Exception:
                pass

        req_path = context.project_path / "requirements.txt"
        if req_path.exists():
            try:
                for line in req_path.read_text().split("\n"):
                    line = line.strip()
                    if line.lower().startswith(name.lower()):
                        version = re.search(r'[\d.]+', line)
                        if version:
                            return version.group()
            except Exception:
                pass

        package_path = context.project_path / "package.json"
        if package_path.exists():
            try:
                content = package_path.read_text(encoding="utf-8")
                data = json.loads(content)
                
                for dep_section in ["dependencies", "devDependencies"]:
                    deps = data.get(dep_section, {})
                    for dep_name, version in deps.items():
                        if dep_name.lower() == name.lower():
                            clean_version = re.search(r'[\d.]+', version)
                            return clean_version.group() if clean_version else version
            except Exception:
                pass

        return ""

    def _extract_all_versions(self, context: DocGeneratorContext) -> dict[str, str]:
        """提取所有依赖版本"""
        versions = {}
        
        pyproject_path = context.project_path / "pyproject.toml"
        if pyproject_path.exists():
            try:
                import tomllib
                with open(pyproject_path, "rb") as f:
                    data = tomllib.load(f)
                
                if "project" in data and "dependencies" in data["project"]:
                    for dep in data["project"]["dependencies"]:
                        match = re.match(r'^([a-zA-Z0-9_-]+)\s*([<>=!~]+\s*[\d.]+)?', dep.strip())
                        if match:
                            name = match.group(1)
                            version = match.group(2).strip() if match.group(2) else ""
                            versions[name] = version
                
                if "tool" in data and "poetry" in data["tool"]:
                    deps = data["tool"]["poetry"].get("dependencies", {})
                    for name, info in deps.items():
                        if name.lower() == "python":
                            continue
                        if isinstance(info, str):
                            versions[name] = info
                        elif isinstance(info, dict) and "version" in info:
                            versions[name] = info["version"]
            except Exception:
                pass

        req_path = context.project_path / "requirements.txt"
        if req_path.exists():
            try:
                for line in req_path.read_text().split("\n"):
                    line = line.strip()
                    if line and not line.startswith("#"):
                        match = re.match(r'^([a-zA-Z0-9_-]+)\s*([<>=!~]+\s*[\d.]+)?', line)
                        if match:
                            name = match.group(1)
                            version = match.group(2).strip() if match.group(2) else ""
                            if name not in versions:
                                versions[name] = version
            except Exception:
                pass

        return versions

    def _analyze_dependency_strength(self, import_usage: dict[str, list]) -> dict[str, Any]:
        """分析依赖强度"""
        strength = {
            "strong": [],
            "medium": [],
            "weak": [],
        }
        
        for dep_name, locations in import_usage.items():
            usage_count = len(locations)
            
            if usage_count >= 5:
                strength["strong"].append({
                    "name": dep_name,
                    "usage_count": usage_count,
                    "locations": locations[:5],
                    "description": f"被 {usage_count} 个模块使用",
                })
            elif usage_count >= 2:
                strength["medium"].append({
                    "name": dep_name,
                    "usage_count": usage_count,
                    "locations": locations,
                })
            else:
                strength["weak"].append({
                    "name": dep_name,
                    "usage_count": usage_count,
                    "locations": locations,
                })
        
        strength["strong"].sort(key=lambda x: x["usage_count"], reverse=True)
        strength["medium"].sort(key=lambda x: x["usage_count"], reverse=True)
        
        return {
            "strong": strength["strong"][:10],
            "medium": strength["medium"][:15],
            "weak_count": len(strength["weak"]),
        }

    def _is_valid_module_name(self, name: str) -> bool:
        """验证模块名是否有效"""
        if not name or len(name) < 2:
            return False
        
        invalid_patterns = [
            '@', '(', ')', '{', '}', '<', '>', ';', '=', '\n', '\t',
            'Schema(', 'hema(desc', 'implements', 'extends', 'class ',
            'import ', 'package ', 'public ', 'private ', 'protected ',
        ]
        
        for pattern in invalid_patterns:
            if pattern in name:
                return False
        
        if name.startswith('.') or name.endswith('.'):
            return False
        
        if re.match(r'^[a-zA-Z_][a-zA-Z0-9_.]*$', name):
            return True
        
        return False

    def _categorize_dependency(self, name: str) -> str:
        """分类依赖"""
        categories = {
            self.labels.get("web_frameworks", "Web框架"): [
                "flask", "django", "fastapi", "starlette", "tornado", "aiohttp",
                "express", "koa", "nestjs", "spring-web", "spring-webmvc",
                "spring-webflux", "struts", "play", "spark", "quarkus", "micronaut",
                "next", "nuxt", "gatsby", "sveltekit", "remix", "astro"
            ],
            self.labels.get("databases_tech", "数据库"): [
                "sqlalchemy", "pymongo", "redis", "psycopg", "mysql", "mongoose", "prisma", "typeorm",
                "hibernate", "mybatis", "mybatisplus", "jpa", "jooq", "querydsl", "jdbc", "hikari",
                "druid", "drizzle", "sequelize", "mikro-orm", "dexie", "lowdb"
            ],
            self.labels.get("http_clients", "HTTP客户端"): [
                "requests", "httpx", "urllib3", "aiohttp", "axios", "fetch", "okhttp",
                "apache-httpclient", "retrofit", "feign", "resttemplate", "webclient",
                "ky", "got", "superagent", "node-fetch"
            ],
            self.labels.get("testing", "测试"): [
                "pytest", "unittest", "mock", "hypothesis", "jest", "mocha", "junit",
                "testng", "assertj", "mockito", "vitest", "cypress", "playwright",
                "testing-library", "supertest", "chai", "sinon"
            ],
            self.labels.get("data_processing", "数据处理"): ["pandas", "numpy", "scipy", "polars"],
            self.labels.get("machine_learning", "机器学习"): ["torch", "tensorflow", "sklearn", "transformers", "langchain"],
            self.labels.get("gui_frameworks", "GUI"): ["pyqt", "pyside", "tkinter", "electron", "tauri", "nw.js"],
            self.labels.get("cli_tools", "CLI"): ["click", "typer", "argparse", "commander", "yargs", "commander-js", "oclif"],
            self.labels.get("validation", "验证"): ["pydantic", "marshmallow", "cerberus", "joi", "zod", "yup", "class-validator", "ajv", "validation"],
            self.labels.get("utilities", "工具"): ["rich", "loguru", "python-dotenv", "lodash", "moment", "dayjs", "date-fns", "ramda", "hutool"],
            self.labels.get("logging_tech", "日志"): ["loguru", "logging", "winston", "log4j", "logback", "slf4j", "pino", "bunyan"],
            self.labels.get("config_tech", "配置"): ["dotenv", "pydantic_settings", "configparser", "convict", "convict", "config", "nconf"],
            self.labels.get("async_tech", "异步"): ["asyncio", "trio", "anyio", "celery", "bull", "rabbitmq", "kafka", "reactor", "netty", "webflux"],
            self.labels.get("security", "安全"): ["cryptography", "passlib", "jwt", "authlib", "bcrypt", "passport", "helmet", "cors", "security"],
            self.labels.get("microservices", "微服务"): [
                "spring-cloud", "dubbo", "grpc", "eureka", "nacos", "consul", "etcd",
                "kafka", "rabbitmq", "activemq", "zeromq", "nats"
            ],
            self.labels.get("message_queue", "消息队列"): ["kafka", "rabbitmq", "activemq", "zeromq", "nats", "pulsar", "rocketmq"],
            self.labels.get("caching", "缓存"): ["redis", "memcached", "caffeine", "guava", "ehcache", "hazelcast", "jedis", "redisson"],
            self.labels.get("monitoring", "监控"): ["prometheus", "grafana", "elk", "zipkin", "jaeger", "sentry", "datadog", "micrometer"],
            self.labels.get("build_tools", "构建工具"): ["webpack", "vite", "rollup", "esbuild", "parcel", "turbo", "maven", "gradle"],
            self.labels.get("frontend_frameworks", "前端框架"): ["react", "vue", "angular", "svelte", "solid", "preact", "alpine", "htmx"],
            self.labels.get("ui_libraries", "UI库"): ["antd", "element", "mui", "material", "chakra", "tailwind", "bootstrap", "bulma"],
            self.labels.get("state_management", "状态管理"): ["redux", "mobx", "zustand", "pinia", "vuex", "recoil", "jotai", "valtio"],
            "GraphQL": ["graphql", "apollo", "urql", "relay", "graphql-yoga", "graphql-tools"],
            self.labels.get("api_docs", "API文档"): ["swagger", "openapi", "springdoc", "swagger-ui", "redoc", "swagger", "knife4j"],
            self.labels.get("template_engine", "模板引擎"): ["thymeleaf", "freemarker", "velocity", "jinja2", "mustache", "handlebars"],
            self.labels.get("workflow", "工作流"): ["flowable", "activiti", "camunda"],
            self.labels.get("excel", "Excel处理"): ["easyexcel", "poi", "excel", "openpyxl", "xlsxwriter"],
            self.labels.get("json", "JSON处理"): ["jackson", "gson", "fastjson", "json", "orjson"],
            self.labels.get("orm", "ORM"): ["mybatis", "mybatisplus", "hibernate", "jpa", "sqlalchemy"],
        }

        name_lower = name.lower()
        
        if name_lower.startswith("org.springframework"):
            if "security" in name_lower:
                return self.labels.get("security", "安全")
            elif "data" in name_lower:
                return self.labels.get("orm", "ORM")
            elif "cloud" in name_lower:
                return self.labels.get("microservices", "微服务")
            elif "ai" in name_lower:
                return self.labels.get("machine_learning", "机器学习")
            elif "test" in name_lower:
                return self.labels.get("testing", "测试")
            elif "kafka" in name_lower or "rabbitmq" in name_lower:
                return self.labels.get("message_queue", "消息队列")
            else:
                return self.labels.get("web_frameworks", "Web框架")
        
        if name_lower.startswith("reactor"):
            return self.labels.get("async_tech", "异步")
        
        if name_lower.startswith("io.swagger"):
            return self.labels.get("api_docs", "API文档")
        
        if name_lower.startswith("com.baomidou"):
            return self.labels.get("orm", "ORM")
        
        if name_lower.startswith("cn.hutool"):
            return self.labels.get("utilities", "工具")
        
        if name_lower.startswith("org.flowable"):
            return self.labels.get("workflow", "工作流")
        
        for category, keywords in categories.items():
            if any(kw in name_lower for kw in keywords):
                return category

        return self.labels.get("other", "其他")

    def _get_dependency_description(self, name: str) -> str:
        """获取依赖描述"""
        if self.language == Language.ZH:
            descriptions = {
                "flask": "轻量级 Web 框架",
                "django": "全功能 Web 框架",
                "fastapi": "高性能异步 API 框架",
                "requests": "HTTP 客户端库",
                "httpx": "异步 HTTP 客户端",
                "pytest": "测试框架",
                "pydantic": "数据验证库",
                "sqlalchemy": "ORM 框架",
                "pandas": "数据分析库",
                "numpy": "科学计算库",
                "torch": "深度学习框架",
                "tensorflow": "机器学习框架",
                "click": "CLI 框架",
                "rich": "终端美化库",
                "loguru": "日志库",
                "spring-boot": "Spring Boot 框架",
                "spring-webmvc": "Spring Web MVC",
                "spring-webflux": "Spring WebFlux 响应式框架",
                "hibernate": "Hibernate ORM 框架",
                "mybatis": "MyBatis 持久层框架",
                "jpa": "Java Persistence API",
                "junit": "Java 单元测试框架",
                "mockito": "Java Mock 测试框架",
                "okhttp": "Square HTTP 客户端",
                "retrofit": "Square REST 客户端",
                "logback": "Java 日志框架",
                "slf4j": "Java 日志门面",
                "express": "Node.js Web 框架",
                "nestjs": "Node.js 企业级框架",
                "react": "React 前端框架",
                "vue": "Vue 前端框架",
                "angular": "Angular 前端框架",
                "typescript": "TypeScript 语言",
                "prisma": "Prisma ORM",
                "typeorm": "TypeORM 框架",
                "mongoose": "MongoDB ODM",
                "jest": "JavaScript 测试框架",
                "vitest": "Vite 测试框架",
                "axios": "HTTP 客户端",
                "zod": "TypeScript 数据验证",
                "winston": "Node.js 日志库",
                "tailwind": "Tailwind CSS 框架",
                "antd": "Ant Design UI 组件库",
                "redux": "Redux 状态管理",
                "graphql": "GraphQL 查询语言",
                "kafka": "Apache Kafka 消息队列",
                "redis": "Redis 缓存数据库",
                "mongodb": "MongoDB 文档数据库",
                "mysql": "MySQL 关系数据库",
                "postgresql": "PostgreSQL 关系数据库",
            }
        else:
            descriptions = {
                "flask": "Lightweight Web Framework",
                "django": "Full-featured Web Framework",
                "fastapi": "High-performance Async API Framework",
                "requests": "HTTP Client Library",
                "httpx": "Async HTTP Client",
                "pytest": "Testing Framework",
                "pydantic": "Data Validation Library",
                "sqlalchemy": "ORM Framework",
                "pandas": "Data Analysis Library",
                "numpy": "Scientific Computing Library",
                "torch": "Deep Learning Framework",
                "tensorflow": "Machine Learning Framework",
                "click": "CLI Framework",
                "rich": "Terminal Beautification Library",
                "loguru": "Logging Library",
                "spring-boot": "Spring Boot Framework",
                "spring-webmvc": "Spring Web MVC",
                "spring-webflux": "Spring WebFlux Reactive Framework",
                "hibernate": "Hibernate ORM Framework",
                "mybatis": "MyBatis Persistence Framework",
                "jpa": "Java Persistence API",
                "junit": "Java Unit Testing Framework",
                "mockito": "Java Mock Testing Framework",
                "okhttp": "Square HTTP Client",
                "retrofit": "Square REST Client",
                "logback": "Java Logging Framework",
                "slf4j": "Java Logging Facade",
                "express": "Node.js Web Framework",
                "nestjs": "Node.js Enterprise Framework",
                "react": "React Frontend Framework",
                "vue": "Vue Frontend Framework",
                "angular": "Angular Frontend Framework",
                "typescript": "TypeScript Language",
                "prisma": "Prisma ORM",
                "typeorm": "TypeORM Framework",
                "mongoose": "MongoDB ODM",
                "jest": "JavaScript Testing Framework",
                "vitest": "Vite Testing Framework",
                "axios": "HTTP Client",
                "zod": "TypeScript Data Validation",
                "winston": "Node.js Logging Library",
                "tailwind": "Tailwind CSS Framework",
                "antd": "Ant Design UI Component Library",
                "redux": "Redux State Management",
                "graphql": "GraphQL Query Language",
                "kafka": "Apache Kafka Message Queue",
                "redis": "Redis Cache Database",
                "mongodb": "MongoDB Document Database",
                "mysql": "MySQL Relational Database",
                "postgresql": "PostgreSQL Relational Database",
            }
        
        return descriptions.get(name.lower(), "")

    async def _enhance_with_llm(
        self,
        context: DocGeneratorContext,
        dep_data: dict[str, Any],
        llm_client: Any,
    ) -> dict[str, Any]:
        """使用 LLM 增强依赖分析"""

        enhanced = {}
        
        summary = dep_data.get("summary", {})

        if self.language == Language.ZH:
            prompt = f"""基于以下依赖分析，提供依赖管理建议：

项目: {context.project_name}
外部依赖数量: {summary.get('total_external', 0)}
内部依赖数量: {summary.get('total_internal', 0)}
循环依赖数量: {summary.get('total_circular', 0)}
热点模块数量: {summary.get('total_hot_spots', 0)}
强依赖数量: {len(dep_data.get('dependency_strength', {}).get('strong', []))}

请以 JSON 格式返回：
{{
    "dependency_health": "依赖健康度评估（好/中/差）",
    "security_concerns": ["安全风险1", "安全风险2"],
    "update_recommendations": ["更新建议1", "更新建议2"],
    "cleanup_suggestions": ["清理建议1", "清理建议2"],
    "architecture_impact": "依赖对架构的影响分析"
}}

请务必使用中文回答。"""
        else:
            prompt = f"""Based on the following dependency analysis, provide dependency management recommendations:

Project: {context.project_name}
External Dependencies: {summary.get('total_external', 0)}
Internal Dependencies: {summary.get('total_internal', 0)}
Circular Dependencies: {summary.get('total_circular', 0)}
Hot Spot Modules: {summary.get('total_hot_spots', 0)}
Strong Dependencies: {len(dep_data.get('dependency_strength', {}).get('strong', []))}

Please return in JSON format:
{{
    "dependency_health": "Dependency health assessment (good/medium/poor)",
    "security_concerns": ["security risk1", "security risk2"],
    "update_recommendations": ["update recommendation1", "update recommendation2"],
    "cleanup_suggestions": ["cleanup suggestion1", "cleanup suggestion2"],
    "architecture_impact": "Analysis of dependency impact on architecture"
}}

Please respond in English."""

        try:
            response = await llm_client.agenerate(prompt)
            start = response.find("{")
            end = response.rfind("}")
            if start != -1 and end != -1:
                result = json.loads(response[start:end+1])
                
                if result.get("dependency_health"):
                    enhanced["dependency_health"] = result["dependency_health"]
                
                if result.get("architecture_impact"):
                    enhanced["architecture_impact"] = result["architecture_impact"]
                
                if result.get("security_concerns"):
                    enhanced["security_concerns"] = result["security_concerns"]
                
                if result.get("update_recommendations"):
                    for rec in result["update_recommendations"]:
                        dep_data["recommendations"].append({
                            "type": "更新建议",
                            "priority": "medium",
                            "description": rec,
                        })
                
                if result.get("cleanup_suggestions"):
                    for rec in result["cleanup_suggestions"]:
                        dep_data["recommendations"].append({
                            "type": "清理建议",
                            "priority": "low",
                            "description": rec,
                        })
        except Exception:
            pass

        return enhanced
