"""
系统架构图生成器
"""
from typing import TYPE_CHECKING

from pywiki.generators.diagrams.architecture import ArchitectureDiagramGenerator
from pywiki.parsers.types import ParseResult

if TYPE_CHECKING:
    from pywiki.generators.docs.base import DocGeneratorContext


class SystemArchitectureDiagram:
    """系统架构图生成器"""

    def __init__(self, arch_diagram_gen: ArchitectureDiagramGenerator):
        self.arch_diagram_gen = arch_diagram_gen

    def generate(self, context: "DocGeneratorContext", filter_modules_func, labels: dict) -> str:
        """生成智能架构图"""
        if not context.parse_result or not context.parse_result.modules:
            return ""

        filtered_modules = filter_modules_func(
            context.parse_result.modules,
            context.project_name
        )

        if not filtered_modules:
            return ""

        filtered_parse_result = ParseResult()
        filtered_parse_result.modules = filtered_modules

        return self.arch_diagram_gen.generate_from_parse_result(
            filtered_parse_result,
            context.project_name,
            f"{context.project_name} {labels.get('system_arch', 'System Architecture')}"
        )
