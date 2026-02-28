"""
技术栈文档生成器
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
            
            if context.parse_result and context.parse_result.modules:
                self._enhance_with_parse_result(analysis, context)
            
            if context.metadata.get("llm_client"):
                enhanced_analysis = await self._enhance_with_llm(
                    context,
                    analysis,
                    context.metadata["llm_client"]
                )
                if enhanced_analysis:
                    analysis = enhanced_analysis

            language_stats = self._calculate_language_stats(context)
            
            content = self.render_template(
                summary=analysis.summary,
                frameworks=[{
                    "name": f.name,
                    "version": f.version,
                    "description": f.description,
                    "usage_count": len(f.usage_locations),
                } for f in analysis.frameworks],
                databases=[{
                    "name": d.name,
                    "type": d.category.value,
                    "description": d.description,
                    "usage_count": len(d.usage_locations),
                } for d in analysis.databases],
                libraries=[{
                    "name": l.name,
                    "category": l.category.value,
                    "version": l.version,
                    "description": l.description,
                    "usage_count": len(l.usage_locations),
                } for l in analysis.libraries],
                tools=[{
                    "name": t.name,
                    "category": t.category.value,
                    "description": t.description,
                    "usage_count": len(t.usage_locations),
                } for t in analysis.tools],
                language_stats=language_stats,
                dependency_stats=self._extract_dependency_stats(context),
                code_metrics=self._calculate_code_metrics(context),
            )

            return self.create_result(
                content=content,
                context=context,
                success=True,
                message=self.labels.get("techstack_doc_success", "Tech stack documentation generated successfully"),
                metadata={"analysis": analysis.summary},
            )

        except Exception as e:
            return self.create_result(
                content="",
                context=context,
                success=False,
                message=f"{self.labels.get('generation_failed', 'Generation failed')}: {str(e)}",
            )

    def _enhance_with_parse_result(self, analysis: TechStackAnalysis, context: DocGeneratorContext) -> None:
        """使用 parse_result 增强技术栈分析"""
        if not context.parse_result or not context.parse_result.modules:
            return
        
        import_counts: dict[str, int] = {}
        import_locations: dict[str, list[str]] = {}
        
        for module in context.parse_result.modules:
            for imp in module.imports:
                if imp.module.startswith("."):
                    continue
                
                base_module = imp.module.split(".")[0]
                import_counts[base_module] = import_counts.get(base_module, 0) + 1
                
                if base_module not in import_locations:
                    import_locations[base_module] = []
                if module.name not in import_locations[base_module]:
                    import_locations[base_module].append(module.name)
        
        existing_names = {c.name.lower() for c in analysis.components}
        
        for module_name, count in import_counts.items():
            module_lower = module_name.lower()
            
            component = self.analyzer._identify_component(module_name)
            if component:
                if component.name.lower() not in existing_names:
                    component.usage_locations = import_locations.get(module_name, [])
                    analysis.components.append(component)
                    existing_names.add(component.name.lower())
                    
                    if component.category.value == "framework":
                        analysis.frameworks.append(component)
                    elif component.category.value == "database":
                        analysis.databases.append(component)
                    elif component.category.value in ("orm", "validation", "http_client", "frontend", "ui_library", "state_management"):
                        analysis.libraries.append(component)
                    else:
                        analysis.tools.append(component)
        
        analysis.summary = self.analyzer._generate_summary(analysis)
        analysis.summary["import_analysis"] = {
            "total_imports": sum(import_counts.values()),
            "unique_modules": len(import_counts),
            "top_imports": sorted(import_counts.items(), key=lambda x: x[1], reverse=True)[:10],
        }

    def _calculate_language_stats(self, context: DocGeneratorContext) -> dict[str, dict[str, Any]]:
        """计算语言统计"""
        stats = {}
        total_files = 0
        total_lines = 0

        lang_extensions = {
            "Python": [".py", ".pyi"],
            "TypeScript": [".ts", ".tsx"],
            "JavaScript": [".js", ".jsx", ".mjs"],
            "Java": [".java"],
            "Kotlin": [".kt", ".kts"],
            "Go": [".go"],
            "Rust": [".rs"],
            "C": [".c", ".h"],
            "C++": [".cpp", ".hpp", ".cc", ".cxx"],
            "C#": [".cs"],
            "Ruby": [".rb"],
            "PHP": [".php"],
            "Swift": [".swift"],
            "Objective-C": [".m", ".mm"],
            "Scala": [".scala"],
            "Markdown": [".md"],
            "YAML": [".yml", ".yaml"],
            "JSON": [".json"],
            "HTML": [".html", ".htm"],
            "CSS": [".css", ".scss", ".sass", ".less"],
            "Shell": [".sh", ".bash", ".zsh"],
            "SQL": [".sql"],
            "Vue": [".vue"],
            "Svelte": [".svelte"],
        }

        exclude_dirs = {"__pycache__", "node_modules", ".git", ".venv", "venv", "dist", "build", ".mypy_cache", "target", ".gradle", ".idea", ".vscode", "out", "bin", "obj"}

        for lang, extensions in lang_extensions.items():
            file_count = 0
            line_count = 0
            
            for ext in extensions:
                for file_path in context.project_path.rglob(f"*{ext}"):
                    if any(excluded in str(file_path) for excluded in exclude_dirs):
                        continue
                    
                    file_count += 1
                    try:
                        content = file_path.read_text(encoding="utf-8", errors="ignore")
                        line_count += len(content.splitlines())
                    except Exception:
                        pass
            
            if file_count > 0:
                stats[lang] = {
                    "files": file_count,
                    "lines": line_count,
                }
                total_files += file_count
                total_lines += line_count

        for lang in stats:
            if total_files > 0:
                stats[lang]["file_percentage"] = round(stats[lang]["files"] / total_files * 100, 1)
            if total_lines > 0:
                stats[lang]["line_percentage"] = round(stats[lang]["lines"] / total_lines * 100, 1)

        if context.parse_result and context.parse_result.modules:
            code_stats = self._extract_code_language_stats(context)
            for lang, data in code_stats.items():
                if lang in stats:
                    stats[lang].update(data)
                else:
                    stats[lang] = data

        sorted_stats = dict(sorted(stats.items(), key=lambda x: x[1].get("files", 0), reverse=True))
        return sorted_stats

    def _extract_code_language_stats(self, context: DocGeneratorContext) -> dict[str, dict[str, Any]]:
        """从解析结果提取代码语言统计"""
        stats = {}
        
        if not context.parse_result or not context.parse_result.modules:
            return stats
        
        total_modules = len(context.parse_result.modules)
        total_classes = 0
        total_functions = 0
        total_methods = 0
        async_functions = 0
        async_methods = 0
        
        for module in context.parse_result.modules:
            total_classes += len(module.classes) if module.classes else 0
            total_functions += len(module.functions) if module.functions else 0
            
            for func in (module.functions or []):
                if hasattr(func, 'is_async') and func.is_async:
                    async_functions += 1
            
            for cls in (module.classes or []):
                total_methods += len(cls.methods) if cls.methods else 0
                
                for method in (cls.methods or []):
                    if hasattr(method, 'is_async') and method.is_async:
                        async_methods += 1
        
        stats["Python"] = {
            "modules": total_modules,
            "classes": total_classes,
            "functions": total_functions,
            "methods": total_methods,
            "async_functions": async_functions,
            "async_methods": async_methods,
        }
        
        return stats

    def _extract_dependency_stats(self, context: DocGeneratorContext) -> dict[str, Any]:
        """提取依赖统计"""
        stats = {
            "total": 0,
            "production": 0,
            "development": 0,
            "by_category": {},
        }
        
        pyproject_path = context.project_path / "pyproject.toml"
        if pyproject_path.exists():
            try:
                import tomllib
                with open(pyproject_path, "rb") as f:
                    data = tomllib.load(f)
                
                if "tool" in data and "poetry" in data["tool"]:
                    deps = data["tool"]["poetry"].get("dependencies", {})
                    dev_deps = data["tool"]["poetry"].get("group", {}).get("dev", {}).get("dependencies", {})
                    
                    stats["production"] = len(deps)
                    stats["development"] = len(dev_deps)
                    stats["total"] = stats["production"] + stats["development"]
                    
                elif "project" in data:
                    deps = data["project"].get("dependencies", [])
                    dev_deps = data["project"].get("optional-dependencies", {}).get("dev", [])
                    
                    stats["production"] = len(deps)
                    stats["development"] = len(dev_deps)
                    stats["total"] = stats["production"] + stats["development"]
            except Exception:
                pass
        
        package_path = context.project_path / "package.json"
        if package_path.exists():
            try:
                content = package_path.read_text(encoding="utf-8")
                data = json.loads(content)
                
                deps = data.get("dependencies", {})
                dev_deps = data.get("devDependencies", {})
                
                stats["production"] = len(deps)
                stats["development"] = len(dev_deps)
                stats["total"] = stats["production"] + stats["development"]
            except Exception:
                pass
        
        requirements_path = context.project_path / "requirements.txt"
        if requirements_path.exists() and stats["total"] == 0:
            try:
                lines = requirements_path.read_text().split("\n")
                deps = [l for l in lines if l.strip() and not l.startswith("#")]
                stats["production"] = len(deps)
                stats["total"] = stats["production"]
            except Exception:
                pass

        pom_path = context.project_path / "pom.xml"
        if pom_path.exists() and stats["total"] == 0:
            try:
                import xml.etree.ElementTree as ET
                tree = ET.parse(pom_path)
                root = tree.getroot()
                ns = {'m': 'http://maven.apache.org/POM/4.0.0'}
                deps = root.findall('.//m:dependency', ns)
                stats["production"] = len(deps)
                stats["total"] = stats["production"]
            except Exception:
                pass
        
        return stats

    def _calculate_code_metrics(self, context: DocGeneratorContext) -> dict[str, Any]:
        """计算代码指标"""
        metrics = {
            "total_modules": 0,
            "total_classes": 0,
            "total_functions": 0,
            "total_methods": 0,
            "total_properties": 0,
            "async_ratio": 0.0,
            "class_to_module_ratio": 0.0,
            "method_to_class_ratio": 0.0,
            "has_tests": False,
            "test_coverage_estimate": "unknown",
        }
        
        if not context.parse_result or not context.parse_result.modules:
            return metrics
        
        total_async = 0
        total_sync = 0
        
        metrics["total_modules"] = len(context.parse_result.modules)
        
        for module in context.parse_result.modules:
            metrics["total_classes"] += len(module.classes) if module.classes else 0
            metrics["total_functions"] += len(module.functions) if module.functions else 0
            
            if "test" in module.name.lower():
                metrics["has_tests"] = True
            
            for func in (module.functions or []):
                if hasattr(func, 'is_async') and func.is_async:
                    total_async += 1
                else:
                    total_sync += 1
            
            for cls in (module.classes or []):
                metrics["total_methods"] += len(cls.methods) if cls.methods else 0
                metrics["total_properties"] += len(cls.properties) if cls.properties else 0
                
                for method in (cls.methods or []):
                    if hasattr(method, 'is_async') and method.is_async:
                        total_async += 1
                    else:
                        total_sync += 1
        
        total_funcs = total_async + total_sync
        if total_funcs > 0:
            metrics["async_ratio"] = round(total_async / total_funcs * 100, 1)
        
        if metrics["total_modules"] > 0:
            metrics["class_to_module_ratio"] = round(metrics["total_classes"] / metrics["total_modules"], 2)
        
        if metrics["total_classes"] > 0:
            metrics["method_to_class_ratio"] = round(metrics["total_methods"] / metrics["total_classes"], 2)
        
        if metrics["has_tests"]:
            test_modules = sum(1 for m in context.parse_result.modules if "test" in m.name.lower())
            metrics["test_coverage_estimate"] = f"{test_modules}/{metrics['total_modules']} 模块有测试"
        
        return metrics

    async def _enhance_with_llm(
        self,
        context: DocGeneratorContext,
        analysis: TechStackAnalysis,
        llm_client: Any,
    ) -> Optional[TechStackAnalysis]:
        """使用 LLM 增强技术栈分析"""

        framework_names = [f.name for f in analysis.frameworks]
        database_names = [d.name for d in analysis.databases]
        library_names = [l.name for l in analysis.libraries[:10]]
        tool_names = [t.name for t in analysis.tools[:5]]
        
        language_stats = self._calculate_language_stats(context)
        primary_languages = list(language_stats.keys())[:3] if language_stats else ["Unknown"]

        if self.language == Language.ZH:
            prompt = f"""基于以下技术栈分析数据，提供深入的架构洞察和专业建议。

# 项目信息
- **项目名称**: {context.project_name}
- **主要编程语言**: {', '.join(primary_languages)}

# 技术栈分析
- **框架**: {', '.join(framework_names) if framework_names else '未检测到'}
- **数据库**: {', '.join(database_names) if database_names else '未检测到'}
- **核心库**: {', '.join(library_names) if library_names else '未检测到'}
- **工具**: {', '.join(tool_names) if tool_names else '未检测到'}

# 统计数据
- **技术组件总数**: {analysis.summary.get('total_components', 0)}
- **框架数量**: {analysis.summary.get('frameworks_count', 0)}
- **数据库数量**: {analysis.summary.get('databases_count', 0)}
- **核心库数量**: {analysis.summary.get('libraries_count', 0)}

# 输出要求
请以 JSON 格式返回以下字段（不要输出 markdown 代码块，直接输出 JSON）：
{{
    "architecture_pattern": "架构模式描述（如分层架构、微服务架构、前后端分离等，需说明判断依据和技术特点，100-200字）",
    "tech_maturity": "技术成熟度评估（分析技术栈的稳定性、社区活跃度、企业采用率等，100-150字）",
    "potential_risks": ["风险1（具体描述风险内容和可能影响）", "风险2", "风险3"],
    "optimization_suggestions": ["优化建议1（具体可执行的建议）", "优化建议2", "优化建议3"]
}}

# 质量标准
- 架构模式判断需基于检测到的技术栈特征
- 风险分析需具体，避免空泛表述
- 优化建议需可执行，有针对性
- 所有描述需专业、准确、有价值

请务必使用中文回答，直接输出 JSON 格式，不要包含 markdown 代码块标记。"""
        else:
            prompt = f"""Based on the following tech stack analysis data, provide in-depth architectural insights and professional recommendations.

# Project Information
- **Project Name**: {context.project_name}
- **Primary Languages**: {', '.join(primary_languages)}

# Tech Stack Analysis
- **Frameworks**: {', '.join(framework_names) if framework_names else 'Not detected'}
- **Databases**: {', '.join(database_names) if database_names else 'Not detected'}
- **Core Libraries**: {', '.join(library_names) if library_names else 'Not detected'}
- **Tools**: {', '.join(tool_names) if tool_names else 'Not detected'}

# Statistics
- **Total Components**: {analysis.summary.get('total_components', 0)}
- **Frameworks Count**: {analysis.summary.get('frameworks_count', 0)}
- **Databases Count**: {analysis.summary.get('databases_count', 0)}
- **Libraries Count**: {analysis.summary.get('libraries_count', 0)}

# Output Requirements
Please return the following fields in JSON format (do not output markdown code blocks, output JSON directly):
{{
    "architecture_pattern": "Architecture pattern description (e.g., layered, microservices, frontend-backend separation, with reasoning and technical characteristics, 100-200 words)",
    "tech_maturity": "Technology maturity assessment (analyze stability, community activity, enterprise adoption rate, 100-150 words)",
    "potential_risks": ["risk 1 (specific description of risk and potential impact)", "risk 2", "risk 3"],
    "optimization_suggestions": ["suggestion 1 (actionable recommendation)", "suggestion 2", "suggestion 3"]
}}

# Quality Standards
- Architecture pattern should be determined based on detected tech stack features
- Risk analysis should be specific, avoid vague statements
- Optimization suggestions should be actionable and targeted
- All descriptions should be professional, accurate, and valuable

Please respond in English, output JSON format directly, do not include markdown code block markers."""

        try:
            response = await llm_client.agenerate(prompt)
            
            json_str = response.strip()
            if json_str.startswith("```"):
                lines = json_str.split("\n")
                json_str = "\n".join(lines[1:-1] if lines[-1].startswith("```") else lines[1:])
            
            start = json_str.find("{")
            end = json_str.rfind("}")
            if start != -1 and end != -1:
                insights = json.loads(json_str[start:end+1])
                
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
