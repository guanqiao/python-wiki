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
            )

            return self.create_result(
                content=content,
                context=context,
                success=True,
                message="依赖文档生成成功",
                metadata={"dependency_data": dep_data.get("summary", {})},
            )

        except Exception as e:
            return self.create_result(
                content="",
                context=context,
                success=False,
                message=f"生成失败: {str(e)}",
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
            list(external_deps.values()),
            key=lambda x: x["usage_count"],
            reverse=True
        )
        dep_data["internal"] = internal_deps[:100]
        
        dep_data["dependency_strength"] = self._analyze_dependency_strength(import_usage)
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
            
            dep_data["hot_spots"] = [
                {
                    "module": module,
                    "incoming": sum(1 for e in graph.edges if e.target == module),
                    "outgoing": sum(1 for e in graph.edges if e.source == module),
                    "total": sum(1 for e in graph.edges if e.target == module) + sum(1 for e in graph.edges if e.source == module),
                    "risk": "high" if sum(1 for e in graph.edges if e.target == module) > 5 else "medium",
                    "description": f"被 {sum(1 for e in graph.edges if e.target == module)} 个模块依赖",
                }
                for module in graph.hot_spots
            ]
            
            report = self.dependency_analyzer.generate_dependency_report(graph)
            dep_data["recommendations"] = report.get("recommendations", [])
            dep_data["summary"] = report.get("summary", {})
            
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

    def _categorize_dependency(self, name: str) -> str:
        """分类依赖"""
        categories = {
            "Web框架": ["flask", "django", "fastapi", "starlette", "tornado", "aiohttp", "express", "koa", "nestjs", "spring"],
            "数据库": ["sqlalchemy", "pymongo", "redis", "psycopg", "mysql", "mongoose", "prisma", "typeorm"],
            "HTTP": ["requests", "httpx", "urllib3", "aiohttp", "axios", "fetch", "okhttp"],
            "测试": ["pytest", "unittest", "mock", "hypothesis", "jest", "mocha", "junit"],
            "数据处理": ["pandas", "numpy", "scipy", "polars"],
            "机器学习": ["torch", "tensorflow", "sklearn", "transformers", "langchain"],
            "GUI": ["pyqt", "pyside", "tkinter"],
            "CLI": ["click", "typer", "argparse", "commander", "yargs"],
            "验证": ["pydantic", "marshmallow", "joi", "zod"],
            "工具": ["rich", "loguru", "python-dotenv", "lodash", "moment"],
            "日志": ["loguru", "logging", "winston", "log4j"],
            "配置": ["dotenv", "pydantic_settings", "configparser", "convict"],
            "异步": ["asyncio", "trio", "anyio", "celery"],
            "安全": ["cryptography", "passlib", "jwt", "authlib", "bcrypt"],
        }

        name_lower = name.lower()
        for category, keywords in categories.items():
            if any(kw in name_lower for kw in keywords):
                return category

        return "其他"

    def _get_dependency_description(self, name: str) -> str:
        """获取依赖描述"""
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
"""

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
