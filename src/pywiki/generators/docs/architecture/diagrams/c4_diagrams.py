"""
C4 模型图表生成器
生成 C4 上下文图、容器图、组件图
"""

import re
from collections import defaultdict
from typing import TYPE_CHECKING, Any

from pywiki.generators.diagrams.architecture import ArchitectureDiagramGenerator

if TYPE_CHECKING:
    from pywiki.generators.docs.base import DocGeneratorContext


class C4DiagramGenerator:
    """C4 模型图表生成器"""

    def __init__(self, arch_diagram_gen: ArchitectureDiagramGenerator):
        self.arch_diagram_gen = arch_diagram_gen

    def generate_context(self, context: "DocGeneratorContext", standard_libs: set) -> str:
        """生成 C4 上下文图"""
        lines = [
            "graph TB",
            f"    System[{context.project_name}<br/>软件系统]",
            "    User[用户]",
            "    User --> System",
        ]

        if context.parse_result and context.parse_result.modules:
            external_deps = {}
            for module in context.parse_result.modules:
                if not hasattr(module, "imports") or not module.imports:
                    continue
                for imp in module.imports:
                    if not hasattr(imp, "module"):
                        continue
                    imp_module = imp.module
                    if imp_module.startswith("."):
                        continue
                    project_prefix = context.project_name.split("-")[0] if "-" in context.project_name else context.project_name
                    if imp_module.startswith(project_prefix):
                        continue
                    base = imp_module.split(".")[0]
                    if base in standard_libs:
                        continue
                    if base not in external_deps:
                        external_deps[base] = 0
                    external_deps[base] += 1

            sorted_deps = sorted(external_deps.items(), key=lambda x: x[1], reverse=True)[:8]
            for dep, count in sorted_deps:
                safe_name = self._sanitize_id(dep)
                lines.append(f"    {safe_name}[{dep}<br/>外部系统]")
                lines.append(f"    System -->|使用| {safe_name}")

        return self.arch_diagram_gen.wrap_mermaid("\n".join(lines))

    def generate_container(self, context: "DocGeneratorContext", filter_modules_func) -> str:
        """生成 C4 容器图"""
        lines = [
            "graph TB",
            f"    subgraph System[{context.project_name}]",
        ]

        if context.parse_result and context.parse_result.modules:
            filtered_modules = filter_modules_func(context.parse_result.modules, context.project_name)

            if not filtered_modules:
                lines.append("    end")
                lines.append("    classDef container fill:#1168bd,stroke:#0b4884,color:#fff")
                return self.arch_diagram_gen.wrap_mermaid("\n".join(lines))

            # 识别业务模块
            business_modules = self._identify_business_modules(filtered_modules)

            # 识别技术容器
            tech_containers = self._identify_tech_containers(filtered_modules)

            # 添加业务模块容器
            if business_modules:
                lines.append("        subgraph BusinessModules[业务模块]")
                for module_name, info in list(business_modules.items())[:6]:
                    safe_name = self._sanitize_id(module_name)
                    display_name = info.get('display_name', module_name)
                    desc = info.get('description', '')
                    lines.append(f"            {safe_name}[{display_name}<br/>{desc}]")
                    lines.append(f"            style {safe_name} fill:#438dd5,stroke:#2e6299,color:#fff")
                lines.append("        end")

            # 添加技术容器
            if tech_containers:
                lines.append("        subgraph TechLayer[技术基础设施]")
                for container_name, info in list(tech_containers.items())[:4]:
                    safe_name = self._sanitize_id(container_name)
                    display_name = info.get('display_name', container_name)
                    tech = info.get('technology', '')
                    shape = "[(" if info.get('type') == 'database' else "["
                    close_shape = ")]" if info.get('type') == 'database' else "]"
                    lines.append(f"            {safe_name}{shape}\"{display_name}<br/>[{tech}]\"{close_shape}")
                    lines.append(f"            style {safe_name} fill:#438dd5,stroke:#2e6299,color:#fff")
                lines.append("        end")

        lines.append("    end")
        lines.append("    classDef container fill:#1168bd,stroke:#0b4884,color:#fff")

        return self.arch_diagram_gen.wrap_mermaid("\n".join(lines))

    def generate_component(self, context: "DocGeneratorContext", filter_modules_func) -> str:
        """生成 C4 组件图"""
        lines = ["graph TB"]

        if not context.parse_result or not context.parse_result.modules:
            return "\n".join(lines)

        filtered_modules = filter_modules_func(context.parse_result.modules, context.project_name)

        if not filtered_modules:
            return "\n".join(lines)

        module_groups: dict[str, list] = defaultdict(list)

        for module in filtered_modules:
            module_name = module.name if hasattr(module, "name") else str(module)
            group = self._extract_module_group(module_name)
            module_groups[group].append(module)

        for group, modules in list(module_groups.items())[:4]:
            safe_group = self._sanitize_id(group)
            display_group = self._extract_display_name(group)
            lines.append(f"    subgraph {safe_group}[{display_group}]")

            for module in modules[:5]:
                module_name = module.name if hasattr(module, "name") else str(module)
                safe_name = self._sanitize_id(module_name)
                display_name = self._extract_display_name(module_name)
                class_count = len(module.classes) if hasattr(module, "classes") and module.classes else 0
                func_count = len(module.functions) if hasattr(module, "functions") and module.functions else 0
                lines.append(f"        {safe_name}[{display_name}<br/>{class_count} 类, {func_count} 函数]")

            lines.append("    end")

        return self.arch_diagram_gen.wrap_mermaid("\n".join(lines))

    def _identify_business_modules(self, modules: list) -> dict:
        """识别业务模块"""
        business_modules = {}

        for module in modules:
            module_name = module.name if hasattr(module, "name") else str(module)

            patterns = [
                r'(?:^|\.)module[.-]([^.]+)',
                r'(?:^|\.)modules[.-]([^.]+)',
                r'(?:^|\.)([^.]+)-module',
                r'(?:^|\.)biz[.-]([^.]+)',
                r'(?:^|\.)business[.-]([^.]+)',
            ]

            matched = False
            for pattern in patterns:
                match = re.search(pattern, module_name.lower())
                if match:
                    module_key = match.group(1)
                    if module_key not in business_modules:
                        business_modules[module_key] = {
                            'display_name': module_key.replace('-', ' ').replace('_', ' ').title(),
                            'description': f'{len([m for m in modules if module_key in (m.name if hasattr(m, "name") else str(m)).lower()])} 模块',
                            'modules': [],
                        }
                    business_modules[module_key]['modules'].append(module)
                    matched = True
                    break

            if not matched:
                parts = module_name.split('.')
                if len(parts) >= 3:
                    org_prefixes = {'com', 'org', 'cn', 'net', 'io', 'me'}
                    start_idx = 1 if parts[0].lower() in org_prefixes else 0
                    if len(parts) > start_idx + 1:
                        group_key = '.'.join(parts[start_idx:start_idx+2])
                        if group_key not in business_modules:
                            business_modules[group_key] = {
                                'display_name': parts[start_idx+1] if len(parts) > start_idx + 1 else group_key,
                                'description': '核心模块',
                                'modules': [],
                            }
                        business_modules[group_key]['modules'].append(module)

        return business_modules

    def _identify_tech_containers(self, modules: list) -> dict:
        """识别技术容器"""
        tech_containers = {}

        for module in modules:
            module_name = module.name if hasattr(module, "name") else str(module)
            name_lower = module_name.lower()

            if any(kw in name_lower for kw in ['repository', 'dao', 'mapper', 'jpa', 'mybatis']):
                if 'Database' not in tech_containers:
                    tech_containers['Database'] = {
                        'display_name': 'Database',
                        'technology': 'MySQL/PostgreSQL',
                        'type': 'database',
                    }

            if any(kw in name_lower for kw in ['cache', 'redis', 'caffeine']):
                if 'Cache' not in tech_containers:
                    tech_containers['Cache'] = {
                        'display_name': 'Cache',
                        'technology': 'Redis',
                        'type': 'cache',
                    }

            if any(kw in name_lower for kw in ['mq', 'kafka', 'rabbitmq', 'message']):
                if 'MessageQueue' not in tech_containers:
                    tech_containers['MessageQueue'] = {
                        'display_name': 'Message Queue',
                        'technology': 'Kafka/RabbitMQ',
                        'type': 'queue',
                    }

            if any(kw in name_lower for kw in ['controller', 'web', 'api', 'rest']):
                if 'WebApplication' not in tech_containers:
                    tech_containers['WebApplication'] = {
                        'display_name': 'Web Application',
                        'technology': 'Spring Boot',
                        'type': 'web',
                    }

        return tech_containers

    def _extract_module_group(self, module_name: str) -> str:
        """从模块名提取分组名称"""
        if re.match(r'^[A-Za-z]:[\\/]', module_name) or module_name.startswith('/') or module_name.startswith('\\'):
            parts = re.split(r'[\\/]', module_name)
            meaningful_parts = [p for p in parts if p and p != '.' and p != '..' and not re.match(r'^[A-Za-z]:$', p)]
            if meaningful_parts:
                return meaningful_parts[-1].replace('.py', '').replace('.java', '').replace('.ts', '')
            return "core"

        parts = module_name.split(".")
        if len(parts) >= 3:
            org_prefixes = {'com', 'org', 'cn', 'net', 'io', 'me', 'dev', 'co', 'edu', 'gov'}
            start_idx = 0
            if parts[0].lower() in org_prefixes:
                start_idx = 1
            if len(parts) > start_idx + 2:
                end_idx = min(start_idx + 3, len(parts))
                return '.'.join(parts[start_idx:end_idx])
            elif len(parts) > start_idx:
                return '.'.join(parts[start_idx:])

        if len(parts) > 1:
            return parts[0]

        return "core"

    def _extract_display_name(self, name: str) -> str:
        """提取显示名称"""
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
