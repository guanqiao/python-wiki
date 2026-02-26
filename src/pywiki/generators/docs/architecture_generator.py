"""
架构文档生成器
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
        arch_data["dependency_graph"] = self._generate_dependency_graph(context)
        arch_data["layers"] = self._analyze_layers(context)

        return arch_data

    def _generate_c4_context(self, context: DocGeneratorContext) -> str:
        """生成 C4 上下文图"""
        lines = [
            "graph TB",
            f"    System[{context.project_name}]",
            "    User[用户]",
            "    User --> System",
        ]

        if context.parse_result and context.parse_result.modules:
            external_deps = set()
            for module in context.parse_result.modules:
                for imp in module.imports:
                    if not imp.module.startswith(".") and not imp.module.startswith(context.project_name.split("-")[0]):
                        base = imp.module.split(".")[0]
                        if base not in ("typing", "os", "sys", "json", "pathlib", "asyncio", "abc", "dataclasses"):
                            external_deps.add(base)

            for dep in list(external_deps)[:5]:
                safe_name = dep.replace("-", "_").replace(".", "_")
                lines.append(f"    {safe_name}[{dep}]")
                lines.append(f"    System --> {safe_name}")

        return "\n".join(lines)

    def _generate_c4_container(self, context: DocGeneratorContext) -> str:
        """生成 C4 容器图"""
        lines = [
            "graph TB",
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

            for group, modules in list(module_groups.items())[:8]:
                safe_name = group.replace("-", "_").replace(".", "_")
                lines.append(f"    {safe_name}[{group}]")
                lines.append(f"    {safe_name}:::container")

        lines.append("    classDef container fill:#1168bd,stroke:#0b4884,color:#fff")

        return "\n".join(lines)

    def _generate_dependency_graph(self, context: DocGeneratorContext) -> str:
        """生成依赖关系图"""
        lines = ["graph LR"]

        if context.parse_result and context.parse_result.modules:
            modules = context.parse_result.modules[:15]
            
            for module in modules:
                safe_name = module.name.replace(".", "_").replace("-", "_")[:20]
                lines.append(f"    {safe_name}[{module.name.split('.')[-1]}]")

            for module in modules:
                safe_name = module.name.replace(".", "_").replace("-", "_")[:20]
                for imp in module.imports[:3]:
                    if imp.module.startswith("."):
                        continue
                    target_safe = imp.module.split(".")[-1].replace("-", "_")[:20]
                    if target_safe != safe_name:
                        lines.append(f"    {safe_name} --> {target_safe}")

        return "\n".join(lines)

    def _analyze_layers(self, context: DocGeneratorContext) -> list[dict[str, Any]]:
        """分析分层架构"""
        layers = []

        layer_patterns = {
            "表现层": ["api", "controller", "view", "handler", "endpoint", "route"],
            "业务层": ["service", "business", "domain", "usecase", "application"],
            "数据层": ["repository", "dao", "model", "entity", "data", "persistence"],
            "基础设施层": ["infrastructure", "config", "util", "common", "helper"],
        }

        if context.parse_result and context.parse_result.modules:
            for layer_name, keywords in layer_patterns.items():
                components = []
                for module in context.parse_result.modules:
                    module_lower = module.name.lower()
                    if any(kw in module_lower for kw in keywords):
                        components.append({
                            "name": module.name.split(".")[-1],
                            "responsibility": module.docstring.split("\n")[0] if module.docstring else "",
                        })

                if components:
                    layers.append({
                        "name": layer_name,
                        "description": f"包含 {len(components)} 个组件",
                        "components": components[:5],
                    })

        return layers

    async def _enhance_with_llm(
        self,
        context: DocGeneratorContext,
        arch_data: dict[str, Any],
        llm_client: Any,
    ) -> dict[str, Any]:
        """使用 LLM 增强架构文档"""
        import json

        enhanced = {}

        prompt = f"""基于以下架构分析，提供更深入的架构洞察：

项目: {context.project_name}
分层: {[l['name'] for l in arch_data.get('layers', [])]}
指标: {arch_data.get('summary', {})}

请以 JSON 格式返回：
{{
    "architecture_style": "架构风格（如分层架构、微服务等）",
    "strengths": ["优势1", "优势2"],
    "weaknesses": ["劣势1", "劣势2"],
    "improvement_suggestions": ["改进建议1", "改进建议2"]
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
