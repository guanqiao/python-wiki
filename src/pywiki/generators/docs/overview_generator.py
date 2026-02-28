"""
项目概述文档生成器
"""

import json
import re
from pathlib import Path
from typing import Any, Optional

from pywiki.generators.docs.base import (
    BaseDocGenerator,
    DocGeneratorContext,
    DocGeneratorResult,
    DocType,
)
from pywiki.config.models import Language


class OverviewGenerator(BaseDocGenerator):
    """项目概述文档生成器"""

    doc_type = DocType.OVERVIEW
    template_name = "overview.md.j2"

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
            )

            return self.create_result(
                content=content,
                context=context,
                success=True,
                message="项目概述文档生成成功",
                metadata={"project_info": project_info},
            )

        except Exception as e:
            return self.create_result(
                content="",
                context=context,
                success=False,
                message=f"生成失败: {str(e)}",
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
        }

        info["description"] = await self._extract_description(context)
        info["features"] = await self._extract_features(context)
        info["tech_stack"] = await self._extract_tech_stack(context)
        info["architecture_diagram"] = self._generate_architecture_diagram(context)
        info["modules"] = self._extract_modules(context)
        info["metadata"] = self._extract_metadata(context)
        info["code_stats"] = self._extract_code_stats(context)

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
        
        return f"{context.project_name} 项目文档"

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
            
            features.append(f"包含 {module_count} 个模块")
            features.append(f"定义了 {class_count} 个类")
            features.append(f"提供了 {func_count} 个函数")

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
                            decorator_types.add("缓存装饰器")
                        elif "retry" in d.lower():
                            decorator_types.add("重试机制")
            
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
            features.append("异步编程支持")
        if has_dataclass:
            features.append("数据类支持")
        if has_context_manager:
            features.append("上下文管理器支持")
        if has_iterator:
            features.append("迭代器支持")
        if has_decorator:
            features.append("装饰器模式")
        if has_property:
            features.append("属性访问器")
        if has_classmethod:
            features.append("类方法支持")
        if has_staticmethod:
            features.append("静态方法支持")
        
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
                if hasattr(module, "file_path"):
                    ext = Path(module.file_path).suffix if module.file_path else ""
                    if ext:
                        languages.add(ext)
            
            if languages:
                tech_stack["语言"] = [ext.lstrip(".") for ext in languages]

        return tech_stack

    def _extract_tech_from_imports(self, context: DocGeneratorContext) -> dict[str, list[str]]:
        """从导入中提取技术栈"""
        tech_stack: dict[str, list[str]] = {}
        
        if not context.parse_result or not context.parse_result.modules:
            return tech_stack
        
        import_counts: dict[str, int] = {}
        
        for module in context.parse_result.modules:
            for imp in module.imports:
                if imp.module.startswith("."):
                    continue
                base_module = imp.module.split(".")[0]
                import_counts[base_module] = import_counts.get(base_module, 0) + 1
        
        categories = {
            "Web框架": ["flask", "django", "fastapi", "starlette", "tornado", "aiohttp", "express", "koa", "nestjs", "spring"],
            "数据库": ["sqlalchemy", "pymongo", "redis", "psycopg", "mysql", "mongoose", "prisma", "typeorm"],
            "HTTP客户端": ["requests", "httpx", "aiohttp", "urllib3", "axios", "fetch", "okhttp"],
            "测试": ["pytest", "unittest", "hypothesis", "jest", "mocha", "junit", "mockito"],
            "数据处理": ["pandas", "numpy", "scipy", "polars"],
            "机器学习": ["torch", "tensorflow", "sklearn", "transformers", "langchain"],
            "CLI": ["click", "typer", "argparse", "commander", "yargs"],
            "验证": ["pydantic", "marshmallow", "cerberus", "joi", "zod"],
            "日志": ["loguru", "logging", "winston", "log4j", "slf4j"],
            "配置": ["dotenv", "pydantic_settings", "configparser", "convict"],
        }
        
        for module_name, count in import_counts.items():
            module_lower = module_name.lower()
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
                    "Web框架": ["flask", "django", "fastapi", "starlette", "tornado", "aiohttp"],
                    "GUI": ["pyqt", "pyside", "tkinter", "wxpython"],
                    "数据处理": ["pandas", "numpy", "scipy", "polars"],
                    "机器学习": ["torch", "tensorflow", "sklearn", "transformers", "langchain"],
                    "数据库": ["sqlalchemy", "pymongo", "redis", "psycopg"],
                    "HTTP客户端": ["requests", "httpx", "aiohttp", "urllib3"],
                    "测试": ["pytest", "unittest", "hypothesis"],
                    "CLI": ["click", "typer", "argparse"],
                    "验证": ["pydantic", "marshmallow", "cerberus"],
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
                    "Web框架": ["spring-boot", "spring-webmvc", "spring-webflux", "struts", "play", "spark", "quarkus", "micronaut"],
                    "ORM框架": ["hibernate", "mybatis", "jpa", "jooq", "querydsl"],
                    "数据库": ["mysql", "postgresql", "mongodb", "redis", "h2", "oracle"],
                    "测试": ["junit", "mockito", "testng", "assertj", "cucumber"],
                    "构建工具": ["maven", "gradle"],
                    "日志": ["log4j", "logback", "slf4j"],
                    "JSON处理": ["jackson", "gson", "fastjson"],
                    "HTTP客户端": ["okhttp", "apache-httpclient", "retrofit", "feign"],
                    "微服务": ["spring-cloud", "dubbo", "grpc", "eureka", "nacos"],
                    "安全": ["spring-security", "shiro", "jwt"],
                }

                for group_id, artifact_id in dependencies:
                    artifact_lower = artifact_id.lower()
                    group_lower = group_id.lower()
                    for category, keywords in categories.items():
                        if any(kw in artifact_lower or kw in group_lower for kw in keywords):
                            if category not in tech_stack:
                                tech_stack[category] = []
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
                    "Web框架": ["spring-boot", "spring-webmvc", "spring-webflux", "struts", "play", "spark", "quarkus", "micronaut"],
                    "ORM框架": ["hibernate", "mybatis", "jpa", "jooq", "querydsl"],
                    "数据库": ["mysql", "postgresql", "mongodb", "redis", "h2", "oracle"],
                    "测试": ["junit", "mockito", "testng", "assertj", "cucumber"],
                    "构建工具": ["maven", "gradle"],
                    "日志": ["log4j", "logback", "slf4j"],
                    "JSON处理": ["jackson", "gson", "fastjson"],
                    "HTTP客户端": ["okhttp", "apache-httpclient", "retrofit", "feign"],
                    "微服务": ["spring-cloud", "dubbo", "grpc", "eureka", "nacos"],
                    "安全": ["spring-security", "shiro", "jwt"],
                }

                for group_id, artifact_id in implementations:
                    artifact_lower = artifact_id.lower()
                    group_lower = group_id.lower()
                    for category, keywords in categories.items():
                        if any(kw in artifact_lower or kw in group_lower for kw in keywords):
                            if category not in tech_stack:
                                tech_stack[category] = []
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
                    "前端框架": ["react", "vue", "angular", "svelte", "next", "nuxt", "gatsby", "solid"],
                    "UI组件库": ["antd", "element", "mui", "material", "chakra", "tailwind", "bootstrap"],
                    "状态管理": ["redux", "mobx", "zustand", "pinia", "vuex", "recoil", "jotai"],
                    "构建工具": ["webpack", "vite", "rollup", "esbuild", "parcel", "turbo"],
                    "测试": ["jest", "vitest", "mocha", "cypress", "playwright", "testing-library"],
                    "HTTP客户端": ["axios", "fetch", "ky", "got", "superagent"],
                    "类型检查": ["typescript", "flow"],
                    "代码质量": ["eslint", "prettier", "husky", "lint-staged"],
                    "后端框架": ["express", "nestjs", "fastify", "koa", "hapi", "trpc"],
                    "数据库": ["prisma", "typeorm", "sequelize", "mongoose", "drizzle"],
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

        modules = context.parse_result.modules[:15]
        
        lines = ["graph TB"]
        
        module_map = {}
        for module in modules:
            safe_name = module.name.replace(".", "_").replace("-", "_")[:25]
            module_map[module.name] = safe_name
            display_name = module.name.split(".")[-1] if "." in module.name else module.name
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

    def _extract_modules(self, context: DocGeneratorContext) -> list[dict[str, str]]:
        """提取模块列表"""
        modules = []
        
        if context.parse_result and context.parse_result.modules:
            for module in context.parse_result.modules:
                class_count = len(module.classes) if module.classes else 0
                func_count = len(module.functions) if module.functions else 0
                
                modules.append({
                    "name": module.name,
                    "path": module.name.replace(".", "/"),
                    "description": module.docstring.split("\n")[0] if module.docstring else "",
                    "class_count": class_count,
                    "func_count": func_count,
                })

        return modules[:20]

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

    async def _enhance_with_llm(
        self,
        context: DocGeneratorContext,
        project_info: dict[str, Any],
        llm_client: Any,
    ) -> dict[str, Any]:
        """使用 LLM 增强文档内容"""
        enhanced = {}
        
        code_stats = project_info.get("code_stats", {})
        
        prompt = f"""请分析以下项目信息，生成更详细的项目概述：

项目名称: {context.project_name}
模块数量: {code_stats.get('total_modules', 0)}
类数量: {code_stats.get('total_classes', 0)}
函数数量: {code_stats.get('total_functions', 0)}
异步函数: {code_stats.get('async_functions', 0) + code_stats.get('async_methods', 0)}
技术栈: {json.dumps(project_info.get('tech_stack', {}), ensure_ascii=False)}
功能特性: {json.dumps(project_info.get('features', []), ensure_ascii=False)}

请以 JSON 格式返回：
{{
    "enhanced_description": "更详细的项目描述",
    "key_features": ["核心功能1", "核心功能2"],
    "target_users": "目标用户群体",
    "use_cases": ["使用场景1", "使用场景2"]
}}
"""

        try:
            response = await llm_client.agenerate(prompt)
            start = response.find("{")
            end = response.rfind("}")
            if start != -1 and end != -1:
                result = json.loads(response[start:end+1])
                enhanced["description"] = result.get("enhanced_description", "")
                if result.get("key_features"):
                    enhanced["features"] = result["key_features"]
        except Exception:
            pass

        return enhanced
