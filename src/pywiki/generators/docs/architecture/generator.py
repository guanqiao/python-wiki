"""
架构文档生成器
支持多种架构风格的自动识别和智能图表生成
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
from pywiki.agents.architecture_agent import ArchitectureAgent, AgentContext
from pywiki.generators.diagrams.architecture import ArchitectureDiagramGenerator
from pywiki.generators.diagrams.package_diagram import PackageDiagramGenerator
from pywiki.generators.diagrams.flowchart import FlowchartGenerator
from pywiki.generators.diagrams.sequence import SequenceDiagramGenerator
from pywiki.generators.diagrams.class_diagram import ClassDiagramGenerator
from pywiki.generators.diagrams.state import StateDiagramGenerator
from pywiki.generators.diagrams.component import ComponentDiagramGenerator

from .analyzers import (
    ModuleFilter,
    StyleAnalyzer,
    LayerAnalyzer,
    MetricsAnalyzer,
    DependencyAnalyzer,
)
from .diagrams import (
    C4DiagramGenerator,
    SystemArchitectureDiagram,
    DataFlowDiagramGenerator,
    DependencyGraphGenerator,
)
from .llm_diagrams import LLMDiagramGenerator, LLMEnhancer


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

        # 初始化图表生成器
        self.arch_diagram_gen = ArchitectureDiagramGenerator()
        self.package_diagram_gen = PackageDiagramGenerator()
        self.flowchart_gen = FlowchartGenerator()
        self.sequence_gen = SequenceDiagramGenerator()
        self.class_diagram_gen = ClassDiagramGenerator()
        self.state_diagram_gen = StateDiagramGenerator()
        self.component_diagram_gen = ComponentDiagramGenerator()

        # 初始化架构 Agent
        self.architecture_agent = ArchitectureAgent()

        # 初始化分析器
        self.style_analyzer = StyleAnalyzer(self.labels)
        self.layer_analyzer = LayerAnalyzer(self.labels)
        self.metrics_analyzer = MetricsAnalyzer()
        self.dependency_analyzer = DependencyAnalyzer(self.labels)

        # 初始化图表生成器
        self.c4_generator = C4DiagramGenerator(self.arch_diagram_gen)
        self.system_arch_generator = SystemArchitectureDiagram(self.arch_diagram_gen)
        self.data_flow_generator = DataFlowDiagramGenerator(self.arch_diagram_gen)
        self.dependency_graph_generator = DependencyGraphGenerator(self.arch_diagram_gen)

        # 初始化 LLM 增强器
        self.llm_diagram_generator = LLMDiagramGenerator(
            self.flowchart_gen,
            self.sequence_gen,
            self.class_diagram_gen,
            self.state_diagram_gen,
            self.component_diagram_gen,
        )
        self.llm_enhancer = LLMEnhancer(self.labels)

    async def generate(self, context: DocGeneratorContext) -> DocGeneratorResult:
        """生成架构文档"""
        try:
            project_language = context.project_language or context.detect_project_language()

            arch_data = await self._analyze_architecture(context, project_language)

            if context.metadata.get("llm_client"):
                enhanced_data = await self.llm_enhancer.enhance(
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

        # 执行架构 Agent
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

        # 执行各种分析
        arch_data["architecture_style"] = self.style_analyzer.analyze(context)
        arch_data["layers"] = self.layer_analyzer.analyze(context, project_language)
        arch_data["quality_metrics"] = self.metrics_analyzer.analyze(context)
        arch_data["circular_dependencies"] = self.dependency_analyzer.detect_circular(context)
        arch_data["hot_spots"] = self.dependency_analyzer.detect_hot_spots(context)
        arch_data["external_dependencies"] = self.dependency_analyzer.analyze_external(context)

        # 生成各种图表
        arch_data["architecture_diagram"] = self.system_arch_generator.generate(
            context, ModuleFilter.filter_project_modules, self.labels
        )
        arch_data["c4_context"] = self.c4_generator.generate_context(
            context, ModuleFilter.STANDARD_LIBS
        )
        arch_data["c4_container"] = self.c4_generator.generate_container(
            context, ModuleFilter.filter_project_modules
        )
        arch_data["c4_component"] = self.c4_generator.generate_component(
            context, ModuleFilter.filter_project_modules
        )
        arch_data["dependency_graph"] = self.dependency_graph_generator.generate(
            context, ModuleFilter.filter_project_modules
        )
        arch_data["data_flow_diagram"] = self.data_flow_generator.generate(
            context, ModuleFilter.filter_project_modules, self.labels
        )

        # 生成包图
        arch_data["package_diagram"] = self._generate_package_diagram(context)

        # 生成 LLM 增强的高阶图
        if context.metadata.get("llm_client"):
            llm_client = context.metadata["llm_client"]
            llm_diagrams = await self.llm_diagram_generator.generate_all(context, llm_client)
            arch_data.update(llm_diagrams)

        # 获取包分析
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

    def _generate_package_diagram(self, context: DocGeneratorContext) -> str:
        """生成包依赖图"""
        if not context.parse_result or not context.parse_result.modules:
            return ""

        filtered_modules = ModuleFilter.filter_project_modules(
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
