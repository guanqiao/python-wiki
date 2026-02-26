"""
依赖文档生成器
"""

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
                recommendations=dep_data.get("recommendations", []),
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
            "recommendations": [],
            "summary": {},
        }

        external_deps: dict[str, dict] = {}
        internal_deps = []

        if context.parse_result and context.parse_result.modules:
            for module in context.parse_result.modules:
                for imp in module.imports:
                    if imp.module.startswith("."):
                        continue
                    
                    base_module = imp.module.split(".")[0]
                    
                    if base_module.startswith(context.project_name.split("-")[0]):
                        internal_deps.append({
                            "source": module.name,
                            "target": imp.module,
                            "type": "internal",
                        })
                    else:
                        if base_module not in external_deps:
                            external_deps[base_module] = {
                                "name": base_module,
                                "version": "",
                                "category": self._categorize_dependency(base_module),
                                "description": "",
                            }

        dep_data["external"] = list(external_deps.values())
        dep_data["internal"] = internal_deps[:50]

        try:
            graph = self.dependency_analyzer.analyze_modules(context.parse_result.modules)
            
            dep_data["circular"] = graph.circular_dependencies[:10]
            
            dep_data["hot_spots"] = [
                {
                    "module": module,
                    "count": sum(1 for e in graph.edges if e.target == module),
                    "risk": "high" if sum(1 for e in graph.edges if e.target == module) > 5 else "medium",
                }
                for module in graph.hot_spots
            ]
            
            report = self.dependency_analyzer.generate_dependency_report(graph)
            dep_data["recommendations"] = report.get("recommendations", [])
            dep_data["summary"] = report.get("summary", {})
            
        except Exception:
            pass

        return dep_data

    def _categorize_dependency(self, name: str) -> str:
        """分类依赖"""
        categories = {
            "Web框架": ["flask", "django", "fastapi", "starlette", "tornado", "aiohttp"],
            "数据库": ["sqlalchemy", "pymongo", "redis", "psycopg", "mysql"],
            "HTTP": ["requests", "httpx", "urllib3", "aiohttp"],
            "测试": ["pytest", "unittest", "mock", "hypothesis"],
            "数据处理": ["pandas", "numpy", "scipy"],
            "机器学习": ["torch", "tensorflow", "sklearn", "transformers", "langchain"],
            "GUI": ["pyqt", "pyside", "tkinter"],
            "CLI": ["click", "typer", "argparse"],
            "验证": ["pydantic", "marshmallow"],
            "工具": ["rich", "loguru", "python-dotenv"],
        }

        name_lower = name.lower()
        for category, keywords in categories.items():
            if any(kw in name_lower for kw in keywords):
                return category

        return "其他"

    async def _enhance_with_llm(
        self,
        context: DocGeneratorContext,
        dep_data: dict[str, Any],
        llm_client: Any,
    ) -> dict[str, Any]:
        """使用 LLM 增强依赖分析"""
        import json

        enhanced = {}

        prompt = f"""基于以下依赖分析，提供依赖管理建议：

项目: {context.project_name}
外部依赖数量: {len(dep_data.get('external', []))}
循环依赖数量: {len(dep_data.get('circular', []))}
热点模块数量: {len(dep_data.get('hot_spots', []))}

请以 JSON 格式返回：
{{
    "dependency_health": "依赖健康度评估（好/中/差）",
    "security_concerns": ["安全风险1", "安全风险2"],
    "update_recommendations": ["更新建议1", "更新建议2"],
    "cleanup_suggestions": ["清理建议1", "清理建议2"]
}}
"""

        try:
            response = await llm_client.agenerate(prompt)
            start = response.find("{")
            end = response.rfind("}")
            if start != -1 and end != -1:
                result = json.loads(response[start:end+1])
                
                if result.get("update_recommendations"):
                    for rec in result["update_recommendations"]:
                        dep_data["recommendations"].append({
                            "type": "更新建议",
                            "description": rec,
                        })
                
                if result.get("cleanup_suggestions"):
                    for rec in result["cleanup_suggestions"]:
                        dep_data["recommendations"].append({
                            "type": "清理建议",
                            "description": rec,
                        })
        except Exception:
            pass

        return enhanced
