"""
Markdown 文档生成器
"""

from pathlib import Path
from typing import Optional

from jinja2 import Environment, FileSystemLoader, Template

from pywiki.config.models import Language
from pywiki.parsers.types import (
    ClassInfo,
    FunctionInfo,
    ModuleInfo,
)
from pywiki.generators.templates import TemplateManager


class MarkdownGenerator:
    """Markdown 文档生成器"""

    def __init__(
        self,
        language: Language = Language.ZH,
        template_dir: Optional[Path] = None,
    ):
        self.language = language
        self.template_manager = TemplateManager(template_dir)
        self._init_labels()

    def _init_labels(self) -> None:
        if self.language == Language.ZH:
            self.labels = {
                "overview": "概述",
                "module": "模块",
                "class": "类",
                "function": "函数",
                "parameters": "参数",
                "returns": "返回值",
                "raises": "异常",
                "example": "示例",
                "properties": "属性",
                "methods": "方法",
                "inheritance": "继承关系",
                "dependencies": "依赖",
                "description": "描述",
                "type": "类型",
                "default": "默认值",
                "visibility": "可见性",
                "architecture": "架构",
                "api_reference": "API 参考",
                "table_of_contents": "目录",
            }
        else:
            self.labels = {
                "overview": "Overview",
                "module": "Module",
                "class": "Class",
                "function": "Function",
                "parameters": "Parameters",
                "returns": "Returns",
                "raises": "Raises",
                "example": "Example",
                "properties": "Properties",
                "methods": "Methods",
                "inheritance": "Inheritance",
                "dependencies": "Dependencies",
                "description": "Description",
                "type": "Type",
                "default": "Default",
                "visibility": "Visibility",
                "architecture": "Architecture",
                "api_reference": "API Reference",
                "table_of_contents": "Table of Contents",
            }

    def generate_module_doc(self, module: ModuleInfo) -> str:
        """生成模块文档"""
        sections = []

        sections.append(f"# {module.name}\n")

        if module.docstring:
            sections.append(f"## {self.labels['overview']}\n\n{module.docstring}\n")

        if module.classes:
            sections.append(f"## {self.labels['class']}\n")
            for cls in module.classes:
                sections.append(self._generate_class_section(cls))

        if module.functions:
            sections.append(f"## {self.labels['function']}\n")
            for func in module.functions:
                sections.append(self._generate_function_section(func))

        return "\n".join(sections)

    def _generate_class_section(self, cls: ClassInfo, level: int = 3) -> str:
        """生成类文档部分"""
        sections = []
        prefix = "#" * level

        sections.append(f"{prefix} {cls.name}\n")

        if cls.bases:
            sections.append(f"**{self.labels['inheritance']}**: {', '.join(cls.bases)}\n")

        if cls.docstring:
            sections.append(f"{cls.docstring}\n")

        if cls.properties:
            sections.append(f"\n**{self.labels['properties']}**:\n")
            sections.append(self._generate_properties_table(cls.properties))

        if cls.methods:
            sections.append(f"\n**{self.labels['methods']}**:\n")
            for method in cls.methods:
                sections.append(self._generate_function_section(method, level + 1))

        return "\n".join(sections)

    def _generate_function_section(self, func: FunctionInfo, level: int = 4) -> str:
        """生成函数文档部分"""
        sections = []
        prefix = "#" * level

        sections.append(f"{prefix} `{func.name}`\n")

        if func.is_async:
            sections.append("*async*\n")

        if func.docstring:
            sections.append(f"\n{func.docstring}\n")

        if func.parameters:
            sections.append(f"\n**{self.labels['parameters']}**:\n")
            sections.append(self._generate_parameters_table(func.parameters))

        if func.return_type:
            sections.append(f"\n**{self.labels['returns']}**: `{func.return_type}`\n")

        if func.raises:
            sections.append(f"\n**{self.labels['raises']}**: {', '.join(f'`{r}`' for r in func.raises)}\n")

        return "\n".join(sections)

    def _generate_parameters_table(self, params: list) -> str:
        """生成参数表格"""
        lines = [
            f"| 名称 | {self.labels['type']} | {self.labels['default']} |",
            "|------|------|------|",
        ]
        for param in params:
            name = param.name
            type_hint = param.type_hint or "-"
            default = param.default_value or "-"
            lines.append(f"| `{name}` | `{type_hint}` | `{default}` |")
        return "\n".join(lines)

    def _generate_properties_table(self, props: list) -> str:
        """生成属性表格"""
        lines = [
            f"| 名称 | {self.labels['type']} | {self.labels['visibility']} |",
            "|------|------|------|",
        ]
        for prop in props:
            name = prop.name
            type_hint = prop.type_hint or "-"
            visibility = prop.visibility.value
            lines.append(f"| `{name}` | `{type_hint}` | `{visibility}` |")
        return "\n".join(lines)

    def generate_architecture_doc(
        self,
        title: str,
        description: str,
        diagram: str,
    ) -> str:
        """生成架构文档"""
        return f"""# {title}

## {self.labels['overview']}

{description}

## {self.labels['architecture']}

{diagram}
"""

    def generate_api_reference(
        self,
        modules: list[ModuleInfo],
        title: str = "API Reference",
    ) -> str:
        """生成 API 参考文档"""
        sections = [f"# {title}\n"]

        sections.append(f"## {self.labels['table_of_contents']}\n")
        for module in modules:
            sections.append(f"- [{module.name}](#{module.name.replace('.', '').lower()})\n")

        for module in modules:
            sections.append("\n---\n")
            sections.append(self.generate_module_doc(module))

        return "\n".join(sections)

    def generate_readme(
        self,
        project_name: str,
        description: str,
        features: list[str],
        installation: str,
        usage: str,
    ) -> str:
        """生成 README 文档"""
        template = self.template_manager.get_template("readme.md")
        return template.render(
            project_name=project_name,
            description=description,
            features=features,
            installation=installation,
            usage=usage,
            labels=self.labels,
        )
