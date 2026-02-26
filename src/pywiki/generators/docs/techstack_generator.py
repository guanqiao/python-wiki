"""
技术栈文档生成器
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
from pywiki.insights.tech_stack_analyzer import TechStackAnalyzer, TechStackAnalysis


class TechStackGenerator(BaseDocGenerator):
    """技术栈文档生成器"""

    doc_type = DocType.TECH_STACK
    template_name = "tech-stack.md.j2"

    def __init__(
        self,
        language: Language = Language.ZH,
        template_dir: Optional[Path] = None,
    ):
        super().__init__(language, template_dir)
        self.analyzer = TechStackAnalyzer()

    async def generate(self, context: DocGeneratorContext) -> DocGeneratorResult:
        """生成技术栈文档"""
        try:
            analysis = self.analyzer.analyze_project(context.project_path)
            
            if context.metadata.get("llm_client"):
                enhanced_analysis = await self._enhance_with_llm(
                    context,
                    analysis,
                    context.metadata["llm_client"]
                )
                if enhanced_analysis:
                    analysis = enhanced_analysis

            content = self.render_template(
                summary=analysis.summary,
                frameworks=[{
                    "name": f.name,
                    "version": f.version,
                    "description": f.description,
                } for f in analysis.frameworks],
                databases=[{
                    "name": d.name,
                    "type": d.category.value,
                    "description": d.description,
                } for d in analysis.databases],
                libraries=[{
                    "name": l.name,
                    "category": l.category.value,
                    "version": l.version,
                    "description": l.description,
                } for l in analysis.libraries],
                tools=[{
                    "name": t.name,
                    "category": t.category.value,
                    "description": t.description,
                } for t in analysis.tools],
                language_stats=self._calculate_language_stats(context),
            )

            return self.create_result(
                content=content,
                context=context,
                success=True,
                message="技术栈文档生成成功",
                metadata={"analysis": analysis.summary},
            )

        except Exception as e:
            return self.create_result(
                content="",
                context=context,
                success=False,
                message=f"生成失败: {str(e)}",
            )

    def _calculate_language_stats(self, context: DocGeneratorContext) -> dict[str, dict[str, Any]]:
        """计算语言统计"""
        stats = {}
        total_files = 0

        lang_extensions = {
            "Python": [".py", ".pyi"],
            "TypeScript": [".ts", ".tsx", ".js", ".jsx", ".vue"],
            "Java": [".java"],
            "Markdown": [".md"],
            "YAML": [".yml", ".yaml"],
            "JSON": [".json"],
            "HTML": [".html", ".htm"],
            "CSS": [".css", ".scss", ".sass"],
        }

        for lang, extensions in lang_extensions.items():
            count = 0
            for ext in extensions:
                count += len(list(context.project_path.rglob(f"*{ext}")))
            if count > 0:
                stats[lang] = {"files": count}
                total_files += count

        for lang in stats:
            if total_files > 0:
                stats[lang]["percentage"] = round(stats[lang]["files"] / total_files * 100, 1)

        return stats

    async def _enhance_with_llm(
        self,
        context: DocGeneratorContext,
        analysis: TechStackAnalysis,
        llm_client: Any,
    ) -> Optional[TechStackAnalysis]:
        """使用 LLM 增强技术栈分析"""
        import json

        prompt = f"""基于以下技术栈分析，提供更深入的见解：

项目: {context.project_name}
框架: {[f.name for f in analysis.frameworks]}
数据库: {[d.name for d in analysis.databases]}
核心库: {[l.name for l in analysis.libraries[:5]]}

请分析并返回 JSON：
{{
    "architecture_pattern": "架构模式（如 MVC、微服务等）",
    "tech_maturity": "技术成熟度评估",
    "potential_risks": ["风险1", "风险2"],
    "optimization_suggestions": ["优化建议1", "优化建议2"]
}}
"""

        try:
            response = await llm_client.agenerate(prompt)
            start = response.find("{")
            end = response.rfind("}")
            if start != -1 and end != -1:
                insights = json.loads(response[start:end+1])
                
                if insights.get("architecture_pattern"):
                    analysis.summary["architecture_pattern"] = insights["architecture_pattern"]
                if insights.get("tech_maturity"):
                    analysis.summary["tech_maturity"] = insights["tech_maturity"]
                if insights.get("potential_risks"):
                    analysis.summary["potential_risks"] = insights["potential_risks"]
                if insights.get("optimization_suggestions"):
                    analysis.summary["optimization_suggestions"] = insights["optimization_suggestions"]

                return analysis
        except Exception:
            pass

        return None
