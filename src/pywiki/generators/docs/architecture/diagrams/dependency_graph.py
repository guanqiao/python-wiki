"""
依赖关系图生成器
"""
from collections import defaultdict
from typing import TYPE_CHECKING

from pywiki.generators.diagrams.architecture import ArchitectureDiagramGenerator

if TYPE_CHECKING:
    from pywiki.generators.docs.base import DocGeneratorContext


class DependencyGraphGenerator:
    """依赖关系图生成器"""

    def __init__(self, arch_diagram_gen: ArchitectureDiagramGenerator):
        self.arch_diagram_gen = arch_diagram_gen

    def generate(self, context: "DocGeneratorContext", filter_modules_func) -> str:
        """生成依赖关系图"""
        lines = ["graph LR"]

        if not context.parse_result or not context.parse_result.modules:
            return "\n".join(lines)

        filtered_modules = filter_modules_func(
            context.parse_result.modules,
            context.project_name
        )

        if not filtered_modules:
            return "\n".join(lines)

        modules = filtered_modules[:20]

        module_map = {}
        for module in modules:
            module_name = module.name if hasattr(module, "name") else str(module)
            safe_name = self._sanitize_id(module_name)
            module_map[module_name] = safe_name
            display_name = self._extract_display_name(module_name)
            lines.append(f'    {safe_name}[{display_name}]')

        dependency_counts: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))

        for module in modules:
            module_name = module.name if hasattr(module, "name") else str(module)
            source_safe = module_map[module_name]

            if hasattr(module, 'imports') and module.imports:
                for imp in module.imports:
                    if not hasattr(imp, "module"):
                        continue
                    target_module = None

                    for other_module in modules:
                        other_name = other_module.name if hasattr(other_module, "name") else str(other_module)
                        if other_name == imp.module or other_name.startswith(imp.module + "."):
                            target_module = other_name
                            break

                    if target_module and target_module in module_map:
                        target_safe = module_map[target_module]
                        dependency_counts[source_safe][target_safe] += 1

        added_edges = set()
        for source, targets in dependency_counts.items():
            for target, count in targets.items():
                edge_key = f"{source}->{target}"
                if edge_key not in added_edges:
                    if count > 2:
                        lines.append(f"    {source} -->|{count}x| {target}")
                    else:
                        lines.append(f"    {source} --> {target}")
                    added_edges.add(edge_key)

        return self.arch_diagram_gen.wrap_mermaid("\n".join(lines))

    def _extract_display_name(self, name: str) -> str:
        """提取显示名称"""
        import re
        if re.match(r'^[A-Za-z]:[\\/]', name) or name.startswith('/') or name.startswith('\\'):
            parts = re.split(r'[\\/]', name)
            meaningful_parts = [p for p in parts if p and p != '.' and p != '..' and not re.match(r'^[A-Za-z]:$', p)]
            if meaningful_parts:
                return meaningful_parts[-1].replace('.py', '').replace('.java', '').replace('.ts', '')

        if '.' in name:
            return name.split('.')[-1]

        return name

    def _sanitize_id(self, name: str) -> str:
        """将名称转换为有效的 Mermaid ID"""
        return self.arch_diagram_gen.sanitize_id(name)
