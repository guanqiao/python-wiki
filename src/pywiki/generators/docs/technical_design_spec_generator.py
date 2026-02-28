"""
Technical Design Specification 文档生成器
综合运用已生成的其他文档内容，生成完整的技术设计规范文档
"""

import json
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


class TechnicalDesignSpecGenerator(BaseDocGenerator):
    """Technical Design Specification 文档生成器
    
    综合读取已生成的其他文档内容，生成完整的技术设计规范文档
    """

    doc_type = DocType.TECHNICAL_DESIGN_SPEC
    template_name = "technical-design-spec.md.j2"

    def __init__(
        self,
        language: Language = Language.ZH,
        template_dir: Optional[Path] = None,
    ):
        super().__init__(language, template_dir)

    async def generate(self, context: DocGeneratorContext) -> DocGeneratorResult:
        """生成 Technical Design Specification 文档"""
        try:
            logger.info(f"开始生成 Technical Design Specification: {context.project_name}")
            
            spec_data = await self._collect_spec_data(context)
            
            if context.metadata.get("llm_client"):
                enhanced_data = await self._enhance_with_llm(
                    context,
                    spec_data,
                    context.metadata["llm_client"]
                )
                spec_data.update(enhanced_data)

            content = self.render_template(
                project_name=context.project_name,
                description=spec_data.get("description", ""),
                overview=spec_data.get("overview", {}),
                architecture=spec_data.get("architecture", {}),
                tech_stack=spec_data.get("tech_stack", {}),
                api_design=spec_data.get("api_design", {}),
                data_model=spec_data.get("data_model", {}),
                dependencies=spec_data.get("dependencies", {}),
                configuration=spec_data.get("configuration", {}),
                development=spec_data.get("development", {}),
                design_decisions=spec_data.get("design_decisions", {}),
                code_analysis=spec_data.get("code_analysis", {}),
                security=spec_data.get("security", {}),
                performance=spec_data.get("performance", {}),
                deployment=spec_data.get("deployment", {}),
                appendix=spec_data.get("appendix", {}),
            )

            logger.info(f"Technical Design Specification 生成完成: {context.project_name}")

            return self.create_result(
                content=content,
                context=context,
                success=True,
                message="Technical Design Specification 文档生成成功",
                metadata={"spec_data": spec_data.get("summary", {})},
            )

        except Exception as e:
            logger.log_exception(f"Technical Design Specification 生成失败: {context.project_name}", e)
            return self.create_result(
                content="",
                context=context,
                success=False,
                message=f"生成失败: {str(e)}",
            )

    async def _collect_spec_data(self, context: DocGeneratorContext) -> dict[str, Any]:
        """收集技术设计规范数据"""
        spec_data = {
            "description": "",
            "overview": {},
            "architecture": {},
            "tech_stack": {},
            "api_design": {},
            "data_model": {},
            "dependencies": {},
            "configuration": {},
            "development": {},
            "design_decisions": {},
            "code_analysis": {},
            "security": {},
            "performance": {},
            "deployment": {},
            "appendix": {},
            "summary": {},
        }

        output_dir = context.output_dir

        spec_data["overview"] = self._read_overview_doc(output_dir)
        spec_data["architecture"] = self._read_architecture_doc(output_dir)
        spec_data["tech_stack"] = self._read_tech_stack_doc(output_dir, context)
        spec_data["api_design"] = self._read_api_doc(output_dir)
        spec_data["data_model"] = self._read_database_doc(output_dir)
        spec_data["dependencies"] = self._read_dependencies_doc(output_dir)
        spec_data["configuration"] = self._read_configuration_doc(output_dir)
        spec_data["development"] = self._read_development_doc(output_dir)
        spec_data["design_decisions"] = self._read_tsd_doc(output_dir)
        spec_data["code_analysis"] = self._read_code_analysis(output_dir)
        spec_data["security"] = self._analyze_security(context)
        spec_data["performance"] = self._analyze_performance(context)
        spec_data["deployment"] = self._analyze_deployment(context)
        spec_data["appendix"] = self._generate_appendix(context)

        spec_data["description"] = self._generate_description(spec_data, context)
        spec_data["summary"] = self._generate_summary(spec_data)

        return spec_data

    def _read_overview_doc(self, output_dir: Path) -> dict[str, Any]:
        """读取概述文档"""
        overview = {
            "title": "",
            "description": "",
            "features": [],
            "modules": [],
            "metadata": {},
            "code_stats": {},
        }

        overview_path = output_dir / "overview.md"
        if overview_path.exists():
            content = overview_path.read_text(encoding="utf-8")
            overview["raw_content"] = content
            overview["title"] = self._extract_title(content)
            overview["description"] = self._extract_description(content)
            overview["features"] = self._extract_features(content)
            overview["modules"] = self._extract_modules_list(content)
            overview["exists"] = True
        else:
            overview["exists"] = False

        return overview

    def _read_architecture_doc(self, output_dir: Path) -> dict[str, Any]:
        """读取架构文档"""
        architecture = {
            "title": "",
            "description": "",
            "layers": [],
            "diagrams": [],
            "quality_metrics": {},
            "recommendations": [],
        }

        arch_path = output_dir / "architecture" / "system-architecture.md"
        if arch_path.exists():
            content = arch_path.read_text(encoding="utf-8")
            architecture["raw_content"] = content
            architecture["title"] = self._extract_title(content)
            architecture["description"] = self._extract_description(content)
            architecture["layers"] = self._extract_architecture_layers(content)
            architecture["diagrams"] = self._extract_mermaid_diagrams(content)
            architecture["quality_metrics"] = self._extract_quality_metrics(content)
            architecture["recommendations"] = self._extract_recommendations(content)
            architecture["exists"] = True
        else:
            architecture["exists"] = False

        return architecture

    def _read_tech_stack_doc(self, output_dir: Path, context: DocGeneratorContext) -> dict[str, Any]:
        """读取技术栈文档"""
        tech_stack = {
            "title": "",
            "description": "",
            "categories": {},
            "languages": [],
            "frameworks": [],
            "tools": [],
        }

        tech_path = output_dir / "tech-stack.md"
        if tech_path.exists():
            content = tech_path.read_text(encoding="utf-8")
            tech_stack["raw_content"] = content
            tech_stack["title"] = self._extract_title(content)
            tech_stack["description"] = self._extract_description(content)
            tech_stack["categories"] = self._extract_tech_categories(content)
            tech_stack["exists"] = True
        else:
            tech_stack["exists"] = False
            tech_stack["categories"] = self._detect_tech_from_code(context)

        project_language = context.project_language or context.detect_project_language()
        tech_stack["primary_language"] = project_language

        return tech_stack

    def _read_api_doc(self, output_dir: Path) -> dict[str, Any]:
        """读取 API 文档"""
        api_design = {
            "title": "",
            "description": "",
            "endpoints": [],
            "modules": [],
            "openapi": {},
        }

        api_path = output_dir / "api" / "index.md"
        if api_path.exists():
            content = api_path.read_text(encoding="utf-8")
            api_design["raw_content"] = content
            api_design["title"] = self._extract_title(content)
            api_design["description"] = self._extract_description(content)
            api_design["endpoints"] = self._extract_api_endpoints(content)
            api_design["exists"] = True
        else:
            api_design["exists"] = False

        return api_design

    def _read_database_doc(self, output_dir: Path) -> dict[str, Any]:
        """读取数据库文档"""
        data_model = {
            "title": "",
            "description": "",
            "tables": [],
            "entities": [],
            "relationships": [],
            "er_diagram": "",
        }

        db_path = output_dir / "database" / "schema.md"
        if db_path.exists():
            content = db_path.read_text(encoding="utf-8")
            data_model["raw_content"] = content
            data_model["title"] = self._extract_title(content)
            data_model["description"] = self._extract_description(content)
            data_model["tables"] = self._extract_tables(content)
            data_model["er_diagram"] = self._extract_mermaid_diagrams(content)
            data_model["exists"] = True
        else:
            data_model["exists"] = False

        return data_model

    def _read_dependencies_doc(self, output_dir: Path) -> dict[str, Any]:
        """读取依赖文档"""
        dependencies = {
            "title": "",
            "description": "",
            "external": [],
            "internal": [],
            "dependency_graph": "",
        }

        dep_path = output_dir / "dependencies" / "external.md"
        if dep_path.exists():
            content = dep_path.read_text(encoding="utf-8")
            dependencies["raw_content"] = content
            dependencies["title"] = self._extract_title(content)
            dependencies["description"] = self._extract_description(content)
            dependencies["external"] = self._extract_dependencies_list(content)
            dependencies["exists"] = True
        else:
            dependencies["exists"] = False

        return dependencies

    def _read_configuration_doc(self, output_dir: Path) -> dict[str, Any]:
        """读取配置文档"""
        configuration = {
            "title": "",
            "description": "",
            "environment_variables": [],
            "config_files": [],
            "settings": {},
        }

        config_path = output_dir / "configuration" / "environment.md"
        if config_path.exists():
            content = config_path.read_text(encoding="utf-8")
            configuration["raw_content"] = content
            configuration["title"] = self._extract_title(content)
            configuration["description"] = self._extract_description(content)
            configuration["environment_variables"] = self._extract_env_vars(content)
            configuration["exists"] = True
        else:
            configuration["exists"] = False

        return configuration

    def _read_development_doc(self, output_dir: Path) -> dict[str, Any]:
        """读取开发文档"""
        development = {
            "title": "",
            "description": "",
            "prerequisites": [],
            "setup_steps": [],
            "testing": {},
            "contributing": "",
        }

        dev_path = output_dir / "development" / "getting-started.md"
        if dev_path.exists():
            content = dev_path.read_text(encoding="utf-8")
            development["raw_content"] = content
            development["title"] = self._extract_title(content)
            development["description"] = self._extract_description(content)
            development["prerequisites"] = self._extract_prerequisites(content)
            development["exists"] = True
        else:
            development["exists"] = False

        return development

    def _read_tsd_doc(self, output_dir: Path) -> dict[str, Any]:
        """读取技术设计决策文档"""
        design_decisions = {
            "title": "",
            "description": "",
            "decisions": [],
            "tech_debt": [],
            "patterns": [],
            "implicit_knowledge": [],
        }

        tsd_path = output_dir / "tsd" / "design-decisions.md"
        if tsd_path.exists():
            content = tsd_path.read_text(encoding="utf-8")
            design_decisions["raw_content"] = content
            design_decisions["title"] = self._extract_title(content)
            design_decisions["description"] = self._extract_description(content)
            design_decisions["decisions"] = self._extract_design_decisions(content)
            design_decisions["tech_debt"] = self._extract_tech_debt(content)
            design_decisions["patterns"] = self._extract_patterns(content)
            design_decisions["exists"] = True
        else:
            design_decisions["exists"] = False

        return design_decisions

    def _read_code_analysis(self, output_dir: Path) -> dict[str, Any]:
        """读取代码分析文档"""
        code_analysis = {
            "quality": {},
            "test_coverage": {},
            "implicit_knowledge": {},
        }

        quality_path = output_dir / "code-quality.md"
        if quality_path.exists():
            content = quality_path.read_text(encoding="utf-8")
            code_analysis["quality"]["raw_content"] = content
            code_analysis["quality"]["exists"] = True
        else:
            code_analysis["quality"]["exists"] = False

        test_path = output_dir / "test-coverage.md"
        if test_path.exists():
            content = test_path.read_text(encoding="utf-8")
            code_analysis["test_coverage"]["raw_content"] = content
            code_analysis["test_coverage"]["exists"] = True
        else:
            code_analysis["test_coverage"]["exists"] = False

        implicit_path = output_dir / "implicit-knowledge.md"
        if implicit_path.exists():
            content = implicit_path.read_text(encoding="utf-8")
            code_analysis["implicit_knowledge"]["raw_content"] = content
            code_analysis["implicit_knowledge"]["exists"] = True
        else:
            code_analysis["implicit_knowledge"]["exists"] = False

        return code_analysis

    def _analyze_security(self, context: DocGeneratorContext) -> dict[str, Any]:
        """分析安全设计"""
        security = {
            "authentication": "",
            "authorization": "",
            "data_protection": [],
            "security_considerations": [],
        }

        if not context.parse_result or not context.parse_result.modules:
            return security

        security_keywords = {
            "authentication": ["auth", "login", "token", "jwt", "session", "oauth", "saml"],
            "authorization": ["permission", "role", "access", "policy", "rbac", "abac"],
            "encryption": ["encrypt", "decrypt", "cipher", "crypto", "hash", "secret"],
            "validation": ["validate", "sanitize", "escape", "xss", "csrf", "injection"],
        }

        for module in context.parse_result.modules:
            module_lower = module.name.lower()
            
            for category, keywords in security_keywords.items():
                if any(kw in module_lower for kw in keywords):
                    security["security_considerations"].append({
                        "category": category,
                        "module": module.name,
                        "description": module.docstring.split("\n")[0] if module.docstring else "",
                    })

            for cls in module.classes:
                cls_lower = cls.name.lower()
                for category, keywords in security_keywords.items():
                    if any(kw in cls_lower for kw in keywords):
                        security["security_considerations"].append({
                            "category": category,
                            "module": f"{module.name}.{cls.name}",
                            "description": cls.docstring.split("\n")[0] if cls.docstring else "",
                        })

        return security

    def _analyze_performance(self, context: DocGeneratorContext) -> dict[str, Any]:
        """分析性能设计"""
        performance = {
            "caching": [],
            "async_operations": [],
            "optimizations": [],
            "considerations": [],
        }

        if not context.parse_result or not context.parse_result.modules:
            return performance

        for module in context.parse_result.modules:
            for func in module.functions:
                if hasattr(func, 'is_async') and func.is_async:
                    performance["async_operations"].append({
                        "name": func.name,
                        "module": module.name,
                        "description": func.docstring.split("\n")[0] if func.docstring else "",
                    })

            for cls in module.classes:
                for method in cls.methods:
                    if hasattr(method, 'is_async') and method.is_async:
                        performance["async_operations"].append({
                            "name": f"{cls.name}.{method.name}",
                            "module": module.name,
                            "description": method.docstring.split("\n")[0] if method.docstring else "",
                        })

        cache_keywords = ["cache", "memoize", "lru", "redis", "memcached"]
        for module in context.parse_result.modules:
            module_lower = module.name.lower()
            if any(kw in module_lower for kw in cache_keywords):
                performance["caching"].append({
                    "module": module.name,
                    "description": module.docstring.split("\n")[0] if module.docstring else "",
                })

        return performance

    def _analyze_deployment(self, context: DocGeneratorContext) -> dict[str, Any]:
        """分析部署架构"""
        deployment = {
            "containerization": [],
            "ci_cd": [],
            "infrastructure": [],
            "environments": [],
        }

        dockerfile = context.project_path / "Dockerfile"
        if dockerfile.exists():
            deployment["containerization"].append({
                "type": "Docker",
                "file": "Dockerfile",
            })

        docker_compose = context.project_path / "docker-compose.yml"
        if docker_compose.exists():
            deployment["containerization"].append({
                "type": "Docker Compose",
                "file": "docker-compose.yml",
            })

        k8s_dir = context.project_path / "k8s"
        if k8s_dir.exists():
            deployment["containerization"].append({
                "type": "Kubernetes",
                "directory": "k8s",
            })

        ci_files = [".github/workflows", ".gitlab-ci.yml", ".travis.yml", "Jenkinsfile"]
        for ci_file in ci_files:
            ci_path = context.project_path / ci_file
            if ci_path.exists():
                deployment["ci_cd"].append({
                    "type": ci_file,
                    "file": ci_file,
                })

        return deployment

    def _generate_appendix(self, context: DocGeneratorContext) -> dict[str, Any]:
        """生成附录"""
        appendix = {
            "glossary": [],
            "references": [],
            "changelog": "",
        }

        readme_path = context.project_path / "README.md"
        if readme_path.exists():
            content = readme_path.read_text(encoding="utf-8")
            refs = self._extract_references(content)
            if refs:
                appendix["references"] = refs

        changelog_path = context.project_path / "CHANGELOG.md"
        if changelog_path.exists():
            appendix["changelog"] = changelog_path.read_text(encoding="utf-8")[:2000]

        return appendix

    def _generate_description(self, spec_data: dict[str, Any], context: DocGeneratorContext) -> str:
        """生成文档描述"""
        overview = spec_data.get("overview", {})
        if overview.get("description"):
            return overview["description"]

        return f"{context.project_name} 技术设计规范文档"

    def _generate_summary(self, spec_data: dict[str, Any]) -> dict[str, Any]:
        """生成摘要"""
        return {
            "has_overview": spec_data.get("overview", {}).get("exists", False),
            "has_architecture": spec_data.get("architecture", {}).get("exists", False),
            "has_tech_stack": spec_data.get("tech_stack", {}).get("exists", False),
            "has_api": spec_data.get("api_design", {}).get("exists", False),
            "has_database": spec_data.get("data_model", {}).get("exists", False),
            "has_dependencies": spec_data.get("dependencies", {}).get("exists", False),
            "has_configuration": spec_data.get("configuration", {}).get("exists", False),
            "has_development": spec_data.get("development", {}).get("exists", False),
            "has_tsd": spec_data.get("design_decisions", {}).get("exists", False),
        }

    def _extract_title(self, content: str) -> str:
        """提取标题"""
        for line in content.split("\n"):
            if line.startswith("# "):
                return line[2:].strip()
        return ""

    def _extract_description(self, content: str) -> str:
        """提取描述"""
        lines = content.split("\n")
        descriptions = []
        started = False
        
        for line in lines:
            if line.startswith("# "):
                started = True
                continue
            if started and line.startswith("##"):
                break
            if started and line.strip():
                descriptions.append(line.strip())
        
        return " ".join(descriptions)[:500]

    def _extract_features(self, content: str) -> list[str]:
        """提取功能特性"""
        features = []
        in_features = False
        
        for line in content.split("\n"):
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
        
        return features[:15]

    def _extract_modules_list(self, content: str) -> list[str]:
        """提取模块列表"""
        modules = []
        for line in content.split("\n"):
            if line.strip().startswith("- [") or line.strip().startswith("* ["):
                if "]" in line:
                    module = line.split("]")[0].split("[")[-1]
                    modules.append(module)
        return modules[:20]

    def _extract_architecture_layers(self, content: str) -> list[dict[str, str]]:
        """提取架构分层"""
        layers = []
        current_layer = None
        
        for line in content.split("\n"):
            if line.startswith("### ") or line.startswith("#### "):
                if current_layer:
                    layers.append(current_layer)
                current_layer = {
                    "name": line.lstrip("#").strip(),
                    "description": "",
                }
            elif current_layer and line.strip() and not line.startswith("#"):
                current_layer["description"] += line.strip() + " "
        
        if current_layer:
            layers.append(current_layer)
        
        return layers[:10]

    def _extract_mermaid_diagrams(self, content: str) -> list[str]:
        """提取 Mermaid 图表"""
        diagrams = []
        in_diagram = False
        current_diagram = []
        
        for line in content.split("\n"):
            if "```mermaid" in line:
                in_diagram = True
                current_diagram = []
                continue
            if in_diagram and "```" in line:
                diagrams.append("\n".join(current_diagram))
                in_diagram = False
                continue
            if in_diagram:
                current_diagram.append(line)
        
        return diagrams

    def _extract_quality_metrics(self, content: str) -> dict[str, Any]:
        """提取质量指标"""
        metrics = {}
        
        if "耦合" in content or "coupling" in content.lower():
            metrics["coupling"] = "analyzed"
        if "内聚" in content or "cohesion" in content.lower():
            metrics["cohesion"] = "analyzed"
        
        return metrics

    def _extract_recommendations(self, content: str) -> list[str]:
        """提取建议"""
        recommendations = []
        in_recommendations = False
        
        for line in content.split("\n"):
            if "建议" in line or "Recommendation" in line:
                in_recommendations = True
                continue
            if in_recommendations and line.startswith("##"):
                break
            if in_recommendations and line.strip().startswith("- "):
                recommendations.append(line.strip()[2:])
        
        return recommendations[:10]

    def _extract_tech_categories(self, content: str) -> dict[str, list[str]]:
        """提取技术分类"""
        categories = {}
        current_category = None
        
        for line in content.split("\n"):
            if line.startswith("### ") or line.startswith("## "):
                current_category = line.lstrip("#").strip()
                categories[current_category] = []
            elif current_category and line.strip().startswith("- "):
                tech = line.strip()[2:].strip()
                categories[current_category].append(tech)
        
        return categories

    def _detect_tech_from_code(self, context: DocGeneratorContext) -> dict[str, list[str]]:
        """从代码检测技术栈"""
        categories = {}
        
        if not context.parse_result or not context.parse_result.modules:
            return categories
        
        import_counts = {}
        for module in context.parse_result.modules:
            for imp in module.imports:
                if not imp.module.startswith("."):
                    base = imp.module.split(".")[0]
                    import_counts[base] = import_counts.get(base, 0) + 1
        
        tech_mapping = {
            "Web框架": [
                "flask", "django", "fastapi", "starlette", "tornado", "aiohttp",
                "express", "koa", "spring", "spring-boot", "spring-webmvc", "spring-webflux",
                "struts", "play", "spark", "quarkus", "micronaut",
                "next", "nuxt", "gatsby", "sveltekit", "remix", "astro"
            ],
            "数据库": [
                "sqlalchemy", "pymongo", "redis", "psycopg", "mysql", "mongoose", "prisma",
                "hibernate", "mybatis", "jpa", "jooq", "querydsl", "jdbc", "hikari",
                "drizzle", "sequelize", "mikro-orm", "dexie", "lowdb"
            ],
            "HTTP": [
                "requests", "httpx", "urllib3", "aiohttp", "axios", "fetch", "okhttp",
                "apache-httpclient", "retrofit", "feign", "resttemplate", "webclient",
                "ky", "got", "superagent", "node-fetch"
            ],
            "测试": [
                "pytest", "unittest", "jest", "mocha", "junit",
                "testng", "assertj", "vitest", "cypress", "playwright",
                "testing-library", "supertest", "chai", "sinon"
            ],
            "CLI": ["click", "typer", "argparse", "commander", "yargs", "commander-js", "oclif"],
            "GUI": ["pyqt", "pyside", "tkinter", "electron", "tauri", "nw.js"],
            "验证": [
                "pydantic", "marshmallow", "cerberus", "joi", "zod", "yup",
                "class-validator", "ajv", "validation-api", "hibernate-validator"
            ],
            "日志": [
                "loguru", "logging", "winston", "log4j", "logback", "slf4j",
                "pino", "bunyan"
            ],
            "配置": ["dotenv", "pydantic_settings", "configparser", "convict", "config", "nconf"],
            "异步": ["asyncio", "trio", "anyio", "celery", "bull", "rabbitmq", "kafka"],
            "安全": [
                "cryptography", "passlib", "jwt", "authlib", "bcrypt",
                "passport", "helmet", "cors"
            ],
            "微服务": [
                "spring-cloud", "dubbo", "grpc", "eureka", "nacos", "consul", "etcd"
            ],
            "消息队列": ["kafka", "rabbitmq", "activemq", "zeromq", "nats", "pulsar", "rocketmq"],
            "缓存": ["redis", "memcached", "caffeine", "guava", "ehcache", "hazelcast"],
            "监控": ["prometheus", "grafana", "elk", "zipkin", "jaeger", "sentry", "datadog"],
            "构建工具": [
                "webpack", "vite", "rollup", "esbuild", "parcel", "turbo",
                "maven", "gradle"
            ],
            "前端框架": [
                "react", "vue", "angular", "svelte", "solid", "preact", "alpine", "htmx"
            ],
            "UI组件库": [
                "antd", "element", "mui", "material", "chakra", "tailwind", "bootstrap", "bulma"
            ],
            "状态管理": [
                "redux", "mobx", "zustand", "pinia", "vuex", "recoil", "jotai", "valtio"
            ],
            "GraphQL": [
                "graphql", "apollo", "urql", "relay", "graphql-yoga", "graphql-tools"
            ],
            "API文档": [
                "swagger", "openapi", "springdoc", "swagger-ui", "redoc"
            ],
        }
        
        for tech, keywords in tech_mapping.items():
            for imp, count in import_counts.items():
                if any(kw in imp.lower() for kw in keywords):
                    if tech not in categories:
                        categories[tech] = []
                    categories[tech].append(imp)
        
        return categories

    def _extract_api_endpoints(self, content: str) -> list[dict[str, str]]:
        """提取 API 端点"""
        endpoints = []
        
        for line in content.split("\n"):
            if any(method in line for method in ["GET", "POST", "PUT", "DELETE", "PATCH"]):
                parts = line.split("|")
                if len(parts) >= 2:
                    endpoints.append({
                        "method": parts[0].strip() if parts[0].strip() else "Unknown",
                        "path": parts[1].strip() if len(parts) > 1 else "",
                    })
        
        return endpoints[:30]

    def _extract_tables(self, content: str) -> list[dict[str, str]]:
        """提取数据表"""
        tables = []
        
        for line in content.split("\n"):
            if line.startswith("### ") or line.startswith("## "):
                table_name = line.lstrip("#").strip()
                if "表" in table_name or "Table" in table_name or "Entity" in table_name:
                    tables.append({"name": table_name})
        
        return tables[:20]

    def _extract_dependencies_list(self, content: str) -> list[dict[str, str]]:
        """提取依赖列表"""
        dependencies = []
        
        for line in content.split("\n"):
            if line.strip().startswith("- ") or line.strip().startswith("* "):
                dep = line.strip()[2:].strip()
                if dep and not dep.startswith("#"):
                    dependencies.append({"name": dep})
        
        return dependencies[:30]

    def _extract_env_vars(self, content: str) -> list[dict[str, str]]:
        """提取环境变量"""
        env_vars = []
        
        for line in content.split("\n"):
            if "=" in line and not line.startswith("#"):
                parts = line.split("=")
                if len(parts) >= 1:
                    env_vars.append({
                        "name": parts[0].strip(),
                        "description": parts[1].strip() if len(parts) > 1 else "",
                    })
        
        return env_vars[:20]

    def _extract_prerequisites(self, content: str) -> list[str]:
        """提取前置条件"""
        prerequisites = []
        in_prereq = False
        
        for line in content.split("\n"):
            if "前置" in line or "Prerequisite" in line or "环境要求" in line:
                in_prereq = True
                continue
            if in_prereq and line.startswith("##"):
                break
            if in_prereq and line.strip().startswith("- "):
                prerequisites.append(line.strip()[2:])
        
        return prerequisites[:10]

    def _extract_design_decisions(self, content: str) -> list[dict[str, str]]:
        """提取设计决策"""
        decisions = []
        current_decision = None
        
        for line in content.split("\n"):
            if line.startswith("### "):
                if current_decision:
                    decisions.append(current_decision)
                current_decision = {"title": line[4:].strip()}
            elif current_decision:
                if line.startswith("**") and "**" in line[2:]:
                    key = line.split("**")[1].strip(": ")
                    value = line.split("**")[-1].strip() if len(line.split("**")) > 2 else ""
                    current_decision[key.lower()] = value
        
        if current_decision:
            decisions.append(current_decision)
        
        return decisions[:10]

    def _extract_tech_debt(self, content: str) -> list[dict[str, str]]:
        """提取技术债务"""
        debts = []
        in_debt = False
        
        for line in content.split("\n"):
            if "技术债务" in line or "Tech Debt" in line:
                in_debt = True
                continue
            if in_debt and line.startswith("##"):
                break
            if in_debt and "|" in line:
                parts = line.split("|")
                if len(parts) >= 3:
                    debts.append({
                        "name": parts[1].strip(),
                        "severity": parts[2].strip() if len(parts) > 2 else "",
                    })
        
        return debts[:15]

    def _extract_patterns(self, content: str) -> list[dict[str, str]]:
        """提取设计模式"""
        patterns = []
        in_patterns = False
        
        for line in content.split("\n"):
            if "设计模式" in line or "Pattern" in line:
                in_patterns = True
                continue
            if in_patterns and line.startswith("##"):
                break
            if in_patterns and line.startswith("### "):
                patterns.append({"name": line[4:].strip()})
        
        return patterns[:10]

    def _extract_references(self, content: str) -> list[dict[str, str]]:
        """提取参考链接"""
        references = []
        
        for line in content.split("\n"):
            if "[" in line and "](" in line:
                import re
                matches = re.findall(r'\[([^\]]+)\]\(([^)]+)\)', line)
                for title, url in matches:
                    references.append({"title": title, "url": url})
        
        return references[:10]

    async def _enhance_with_llm(
        self,
        context: DocGeneratorContext,
        spec_data: dict[str, Any],
        llm_client: Any,
    ) -> dict[str, Any]:
        """使用 LLM 增强文档内容"""
        enhanced = {}

        summary = spec_data.get("summary", {})
        
        prompt = f"""基于以下项目信息，生成技术设计规范的综合分析：

项目: {context.project_name}
已有文档:
- 概述文档: {'是' if summary.get('has_overview') else '否'}
- 架构文档: {'是' if summary.get('has_architecture') else '否'}
- 技术栈文档: {'是' if summary.get('has_tech_stack') else '否'}
- API文档: {'是' if summary.get('has_api') else '否'}
- 数据库文档: {'是' if summary.get('has_database') else '否'}

技术栈: {json.dumps(spec_data.get('tech_stack', {}).get('categories', {}), ensure_ascii=False)}
主要语言: {spec_data.get('tech_stack', {}).get('primary_language', 'unknown')}

请以 JSON 格式返回：
{{
    "executive_summary": "执行摘要（100字以内）",
    "key_technical_decisions": ["关键技术决策1", "关键技术决策2"],
    "risk_assessment": ["风险1", "风险2"],
    "improvement_roadmap": ["改进建议1", "改进建议2"],
    "compliance_notes": "合规性说明"
}}
"""

        try:
            response = await llm_client.agenerate(prompt)
            start = response.find("{")
            end = response.rfind("}")
            if start != -1 and end != -1:
                result = json.loads(response[start:end+1])
                enhanced["executive_summary"] = result.get("executive_summary", "")
                enhanced["key_technical_decisions"] = result.get("key_technical_decisions", [])
                enhanced["risk_assessment"] = result.get("risk_assessment", [])
                enhanced["improvement_roadmap"] = result.get("improvement_roadmap", [])
                enhanced["compliance_notes"] = result.get("compliance_notes", "")
        except Exception as e:
            logger.debug(f"LLM 增强失败: {e}")

        return enhanced
