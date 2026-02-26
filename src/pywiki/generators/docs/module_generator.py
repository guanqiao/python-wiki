"""
模块文档生成器
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


class ModuleGenerator(BaseDocGenerator):
    """模块文档生成器"""

    doc_type = DocType.MODULE
    template_name = "module.md.j2"

    def __init__(
        self,
        language: Language = Language.ZH,
        template_dir: Optional[Path] = None,
    ):
        super().__init__(language, template_dir)

    async def generate(self, context: DocGeneratorContext) -> DocGeneratorResult:
        """生成模块索引文档"""
        try:
            modules_info = self._extract_modules_info(context)
            
            content = self._generate_index_content(context, modules_info)

            return self.create_result(
                content=content,
                context=context,
                success=True,
                message="模块文档生成成功",
                metadata={"module_count": len(modules_info)},
            )

        except Exception as e:
            return self.create_result(
                content="",
                context=context,
                success=False,
                message=f"生成失败: {str(e)}",
            )

    def _extract_modules_info(self, context: DocGeneratorContext) -> list[dict[str, Any]]:
        """提取模块信息"""
        modules_info = []

        if not context.parse_result or not context.parse_result.modules:
            return modules_info

        for module in context.parse_result.modules:
            module_info = {
                "name": module.name,
                "path": module.name.replace(".", "/"),
                "description": module.docstring.split("\n")[0] if module.docstring else "",
                "classes": [],
                "functions": [],
                "imports": [],
            }

            for cls in module.classes:
                class_info = {
                    "name": cls.name,
                    "docstring": cls.docstring or "",
                    "bases": cls.bases,
                    "properties": [],
                    "methods": [],
                }

                for prop in cls.properties:
                    class_info["properties"].append({
                        "name": prop.name,
                        "type_hint": prop.type_hint or "",
                        "visibility": prop.visibility.value if hasattr(prop.visibility, 'value') else str(prop.visibility),
                    })

                for method in cls.methods:
                    class_info["methods"].append({
                        "name": method.name,
                        "parameters": method.parameters,
                        "return_type": method.return_type or "",
                        "docstring": method.docstring or "",
                        "raises": method.raises or [],
                    })

                module_info["classes"].append(class_info)

            for func in module.functions:
                module_info["functions"].append({
                    "name": func.name,
                    "parameters": func.parameters,
                    "return_type": func.return_type or "",
                    "docstring": func.docstring or "",
                })

            for imp in module.imports:
                module_info["imports"].append({
                    "module": imp.module,
                    "type": "internal" if imp.module.startswith(".") else "external",
                })

            modules_info.append(module_info)

        return modules_info

    def _generate_index_content(self, context: DocGeneratorContext, modules_info: list[dict]) -> str:
        """生成模块索引内容"""
        lines = [
            f"# {context.project_name} 模块文档",
            "",
            "## 模块列表",
            "",
        ]

        for module in modules_info:
            lines.append(f"### [{module['name']}](modules/{module['path']}.md)")
            if module['description']:
                lines.append(f"{module['description']}")
            
            if module['classes']:
                lines.append(f"\n**类**: {', '.join([c['name'] for c in module['classes'][:5]])}")
            
            if module['functions']:
                lines.append(f"\n**函数**: {', '.join([f['name'] for f in module['functions'][:5]])}")
            
            lines.append("")

        lines.extend([
            "---",
            f"\n总计: {len(modules_info)} 个模块",
        ])

        return "\n".join(lines)

    async def generate_module_doc(
        self,
        module_info: dict[str, Any],
        context: DocGeneratorContext,
    ) -> str:
        """生成单个模块文档"""
        content = self.render_template(
            module_name=module_info["name"],
            description=module_info["description"],
            classes=module_info["classes"],
            functions=module_info["functions"],
            imports=module_info["imports"],
        )
        return content
