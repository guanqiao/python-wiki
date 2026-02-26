"""
项目概述文档生成器
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


class OverviewGenerator(BaseDocGenerator):
    """项目概述文档生成器"""

    doc_type = DocType.OVERVIEW
    template_name = "overview.md.j2"

    def __init__(
        self,
        language: Language = Language.ZH,
        template_dir: Optional[Path] = None,
    ):
        super().__init__(language, template_dir)

    async def generate(self, context: DocGeneratorContext) -> DocGeneratorResult:
        """生成项目概述文档"""
        try:
            project_info = await self._collect_project_info(context)
            
            if context.metadata.get("llm_client"):
                enhanced_info = await self._enhance_with_llm(
                    context, 
                    project_info, 
                    context.metadata["llm_client"]
                )
                project_info.update(enhanced_info)

            content = self.render_template(
                title=project_info.get("title", context.project_name),
                description=project_info.get("description", ""),
                features=project_info.get("features", []),
                tech_stack=project_info.get("tech_stack", {}),
                architecture_diagram=project_info.get("architecture_diagram", ""),
                modules=project_info.get("modules", []),
                metadata=project_info.get("metadata", {}),
            )

            return self.create_result(
                content=content,
                context=context,
                success=True,
                message="项目概述文档生成成功",
                metadata={"project_info": project_info},
            )

        except Exception as e:
            return self.create_result(
                content="",
                context=context,
                success=False,
                message=f"生成失败: {str(e)}",
            )

    async def _collect_project_info(self, context: DocGeneratorContext) -> dict[str, Any]:
        """收集项目信息"""
        info = {
            "title": context.project_name,
            "description": "",
            "features": [],
            "tech_stack": {},
            "architecture_diagram": "",
            "modules": [],
            "metadata": {},
        }

        info["description"] = await self._extract_description(context)
        info["features"] = await self._extract_features(context)
        info["tech_stack"] = await self._extract_tech_stack(context)
        info["architecture_diagram"] = self._generate_architecture_diagram(context)
        info["modules"] = self._extract_modules(context)
        info["metadata"] = self._extract_metadata(context)

        return info

    async def _extract_description(self, context: DocGeneratorContext) -> str:
        """提取项目描述"""
        readme_path = context.project_path / "README.md"
        if readme_path.exists():
            content = readme_path.read_text(encoding="utf-8")
            lines = content.split("\n")
            description_lines = []
            in_description = False
            
            for line in lines:
                if line.startswith("# "):
                    if in_description:
                        break
                    in_description = True
                    continue
                if in_description and line.strip():
                    if line.startswith("##"):
                        break
                    description_lines.append(line)
            
            return " ".join(description_lines).strip()

        pyproject_path = context.project_path / "pyproject.toml"
        if pyproject_path.exists():
            try:
                import tomllib
                with open(pyproject_path, "rb") as f:
                    data = tomllib.load(f)
                if "tool" in data and "poetry" in data["tool"]:
                    return data["tool"]["poetry"].get("description", "")
                if "project" in data:
                    return data["project"].get("description", "")
            except Exception:
                pass

        return f"{context.project_name} 项目文档"

    async def _extract_features(self, context: DocGeneratorContext) -> list[str]:
        """提取功能特性"""
        features = []

        readme_path = context.project_path / "README.md"
        if readme_path.exists():
            content = readme_path.read_text(encoding="utf-8")
            lines = content.split("\n")
            in_features = False
            
            for line in lines:
                if "功能" in line or "Features" in line or "特性" in line:
                    in_features = True
                    continue
                if in_features:
                    if line.startswith("##"):
                        break
                    if line.strip().startswith("- ") or line.strip().startswith("* "):
                        feature = line.strip()[2:].strip()
                        if feature:
                            features.append(feature)

        if context.parse_result and context.parse_result.modules:
            module_count = len(context.parse_result.modules)
            class_count = sum(len(m.classes) for m in context.parse_result.modules)
            func_count = sum(len(m.functions) for m in context.parse_result.modules)
            
            if not features:
                features.append(f"包含 {module_count} 个模块")
                features.append(f"定义了 {class_count} 个类")
                features.append(f"提供了 {func_count} 个函数")

        return features[:10]

    async def _extract_tech_stack(self, context: DocGeneratorContext) -> dict[str, list[str]]:
        """提取技术栈"""
        tech_stack: dict[str, list[str]] = {}

        pyproject_path = context.project_path / "pyproject.toml"
        if pyproject_path.exists():
            try:
                import tomllib
                with open(pyproject_path, "rb") as f:
                    data = tomllib.load(f)

                deps = {}
                if "tool" in data and "poetry" in data["tool"]:
                    deps = data["tool"]["poetry"].get("dependencies", {})
                elif "project" in data:
                    deps = {d.split("[")[0]: "" for d in data["project"].get("dependencies", [])}

                categories = {
                    "Web框架": ["flask", "django", "fastapi", "starlette", "tornado", "aiohttp"],
                    "GUI": ["pyqt", "pyside", "tkinter", "wxpython"],
                    "数据处理": ["pandas", "numpy", "scipy", "polars"],
                    "机器学习": ["torch", "tensorflow", "sklearn", "transformers", "langchain"],
                    "数据库": ["sqlalchemy", "pymongo", "redis", "psycopg"],
                    "HTTP客户端": ["requests", "httpx", "aiohttp", "urllib3"],
                    "测试": ["pytest", "unittest", "hypothesis"],
                    "CLI": ["click", "typer", "argparse"],
                    "验证": ["pydantic", "marshmallow", "cerberus"],
                }

                for dep_name in deps.keys():
                    dep_lower = dep_name.lower()
                    for category, keywords in categories.items():
                        if any(kw in dep_lower for kw in keywords):
                            if category not in tech_stack:
                                tech_stack[category] = []
                            tech_stack[category].append(dep_name)
                            break

            except Exception:
                pass

        if context.parse_result and context.parse_result.modules:
            languages = set()
            for module in context.parse_result.modules:
                if hasattr(module, "file_path"):
                    ext = Path(module.file_path).suffix if module.file_path else ""
                    if ext:
                        languages.add(ext)
            
            if languages:
                tech_stack["语言"] = [ext.lstrip(".") for ext in languages]

        return tech_stack

    def _generate_architecture_diagram(self, context: DocGeneratorContext) -> str:
        """生成架构图"""
        if not context.parse_result or not context.parse_result.modules:
            return ""

        modules = context.parse_result.modules[:10]
        
        lines = ["graph TB"]
        
        for i, module in enumerate(modules):
            safe_name = module.name.replace(".", "_").replace("-", "_")
            lines.append(f"    {safe_name}[{module.name}]")

        for i, module in enumerate(modules):
            safe_name = module.name.replace(".", "_").replace("-", "_")
            if i > 0:
                prev_safe = modules[i-1].name.replace(".", "_").replace("-", "_")
                lines.append(f"    {prev_safe} --> {safe_name}")

        return "\n".join(lines)

    def _extract_modules(self, context: DocGeneratorContext) -> list[dict[str, str]]:
        """提取模块列表"""
        modules = []
        
        if context.parse_result and context.parse_result.modules:
            for module in context.parse_result.modules:
                modules.append({
                    "name": module.name,
                    "path": module.name.replace(".", "/"),
                    "description": module.docstring.split("\n")[0] if module.docstring else "",
                })

        return modules[:20]

    def _extract_metadata(self, context: DocGeneratorContext) -> dict[str, str]:
        """提取元数据"""
        metadata = {
            "version": "",
            "license": "",
            "created_at": "",
        }

        pyproject_path = context.project_path / "pyproject.toml"
        if pyproject_path.exists():
            try:
                import tomllib
                with open(pyproject_path, "rb") as f:
                    data = tomllib.load(f)

                if "tool" in data and "poetry" in data["tool"]:
                    poetry = data["tool"]["poetry"]
                    metadata["version"] = poetry.get("version", "")
                    metadata["license"] = poetry.get("license", "")
                elif "project" in data:
                    project = data["project"]
                    metadata["version"] = project.get("version", "")

            except Exception:
                pass

        from datetime import datetime
        metadata["created_at"] = datetime.now().strftime("%Y-%m-%d")

        return metadata

    async def _enhance_with_llm(
        self,
        context: DocGeneratorContext,
        project_info: dict[str, Any],
        llm_client: Any,
    ) -> dict[str, Any]:
        """使用 LLM 增强文档内容"""
        enhanced = {}

        prompt = f"""请分析以下项目信息，生成更详细的项目概述：

项目名称: {context.project_name}
模块数量: {len(project_info.get('modules', []))}
技术栈: {json.dumps(project_info.get('tech_stack', {}), ensure_ascii=False)}
功能特性: {json.dumps(project_info.get('features', []), ensure_ascii=False)}

请以 JSON 格式返回：
{{
    "enhanced_description": "更详细的项目描述",
    "key_features": ["核心功能1", "核心功能2"],
    "target_users": "目标用户群体",
    "use_cases": ["使用场景1", "使用场景2"]
}}
"""

        try:
            response = await llm_client.agenerate(prompt)
            start = response.find("{")
            end = response.rfind("}")
            if start != -1 and end != -1:
                result = json.loads(response[start:end+1])
                enhanced["description"] = result.get("enhanced_description", "")
                if result.get("key_features"):
                    enhanced["features"] = result["key_features"]
        except Exception:
            pass

        return enhanced
