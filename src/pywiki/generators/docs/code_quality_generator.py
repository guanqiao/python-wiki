"""
代码质量分析文档生成器
检测代码异味、分析技术债务、生成代码质量评分
"""

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from pywiki.generators.docs.base import (
    BaseDocGenerator,
    DocGeneratorContext,
    DocGeneratorResult,
    DocType,
)
from pywiki.config.models import Language


@dataclass
class CodeSmell:
    """代码异味"""
    type: str
    severity: str
    location: str
    description: str
    suggestion: str = ""


@dataclass
class QualityMetric:
    """质量指标"""
    name: str
    value: float
    max_value: float = 100.0
    description: str = ""
    category: str = "general"


@dataclass
class QualityScore:
    """质量评分"""
    overall: float
    categories: dict[str, float] = field(default_factory=dict)
    grade: str = "C"


class CodeQualityGenerator(BaseDocGenerator):
    """代码质量分析文档生成器"""

    doc_type = DocType.TSD
    template_name = "tsd.md.j2"

    def __init__(self, language: Language = Language.ZH, template_dir: Optional[Path] = None):
        super().__init__(language, template_dir)

    async def generate(self, context: DocGeneratorContext) -> DocGeneratorResult:
        """生成代码质量分析文档"""
        try:
            quality_data = {
                "code_smells": [],
                "metrics": [],
                "quality_score": {},
                "tech_debt_summary": {},
                "recommendations": [],
            }
            
            quality_data["code_smells"] = self._detect_code_smells(context)
            quality_data["metrics"] = self._calculate_metrics(context)
            quality_data["quality_score"] = self._calculate_quality_score(quality_data["metrics"], quality_data["code_smells"])
            quality_data["tech_debt_summary"] = self._summarize_tech_debt(quality_data["code_smells"])
            quality_data["recommendations"] = self._generate_recommendations(quality_data)
            
            if context.metadata.get("llm_client"):
                enhanced_data = await self._enhance_with_llm(
                    context,
                    quality_data,
                    context.metadata["llm_client"]
                )
                quality_data.update(enhanced_data)

            content = self.render_template(
                description=f"{context.project_name} 代码质量分析",
                code_smells=quality_data["code_smells"],
                metrics=quality_data["metrics"],
                quality_score=quality_data["quality_score"],
                tech_debt_summary=quality_data["tech_debt_summary"],
                recommendations=quality_data["recommendations"],
            )

            return self.create_result(
                content=content,
                context=context,
                success=True,
                message="代码质量分析文档生成成功",
                metadata={"quality_score": quality_data["quality_score"].get("overall", 0)},
            )

        except Exception as e:
            return self.create_result(
                content="",
                context=context,
                success=False,
                message=f"生成失败: {str(e)}",
            )

    def _detect_code_smells(self, context: DocGeneratorContext) -> list[dict[str, Any]]:
        """检测代码异味"""
        smells = []
        
        if not context.parse_result or not context.parse_result.modules:
            return smells
        
        for module in context.parse_result.modules:
            smells.extend(self._detect_long_methods(module))
            smells.extend(self._detect_large_classes(module))
            smells.extend(self._detect_long_parameter_lists(module))
            smells.extend(self._detect_deep_nesting(module))
            smells.extend(self._detect_duplicate_code(module))
            smells.extend(self._detect_dead_code(module))
            smells.extend(self._detect_magic_numbers(module))
            smells.extend(self._detect_complex_conditionals(module))
        
        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        smells.sort(key=lambda x: severity_order.get(x["severity"], 4))
        
        return smells[:50]

    def _detect_long_methods(self, module: Any) -> list[dict[str, Any]]:
        """检测过长方法"""
        smells = []
        
        for cls in module.classes:
            for method in cls.methods:
                if method.docstring and len(method.docstring.split("\n")) > 50:
                    smells.append({
                        "type": "Long Method",
                        "severity": "medium",
                        "location": f"{module.name}.{cls.name}.{method.name}",
                        "description": f"方法 {method.name} 过长，建议拆分",
                        "suggestion": "将方法拆分为多个更小的方法，每个方法只做一件事",
                    })
        
        for func in module.functions:
            if func.docstring and len(func.docstring.split("\n")) > 50:
                smells.append({
                    "type": "Long Method",
                    "severity": "medium",
                    "location": f"{module.name}.{func.name}",
                    "description": f"函数 {func.name} 过长，建议拆分",
                    "suggestion": "将函数拆分为多个更小的函数",
                })
        
        return smells

    def _detect_large_classes(self, module: Any) -> list[dict[str, Any]]:
        """检测过大类"""
        smells = []
        
        for cls in module.classes:
            method_count = len(cls.methods)
            property_count = len(cls.properties)
            
            if method_count > 20 or property_count > 15:
                smells.append({
                    "type": "Large Class",
                    "severity": "high" if method_count > 30 else "medium",
                    "location": f"{module.name}.{cls.name}",
                    "description": f"类 {cls.name} 过大（{method_count} 个方法，{property_count} 个属性）",
                    "suggestion": "考虑将类拆分为多个更小的类，遵循单一职责原则",
                })
        
        return smells

    def _detect_long_parameter_lists(self, module: Any) -> list[dict[str, Any]]:
        """检测过长参数列表"""
        smells = []
        
        for cls in module.classes:
            for method in cls.methods:
                param_count = len(method.parameters)
                if param_count > 5:
                    smells.append({
                        "type": "Long Parameter List",
                        "severity": "medium",
                        "location": f"{module.name}.{cls.name}.{method.name}",
                        "description": f"方法 {method.name} 有 {param_count} 个参数",
                        "suggestion": "考虑使用参数对象或配置字典来减少参数数量",
                    })
        
        for func in module.functions:
            param_count = len(func.parameters)
            if param_count > 5:
                smells.append({
                    "type": "Long Parameter List",
                    "severity": "medium",
                    "location": f"{module.name}.{func.name}",
                    "description": f"函数 {func.name} 有 {param_count} 个参数",
                    "suggestion": "考虑使用参数对象或配置字典来减少参数数量",
                })
        
        return smells

    def _detect_deep_nesting(self, module: Any) -> list[dict[str, Any]]:
        """检测深层嵌套"""
        smells = []
        
        nesting_indicators = ["if", "for", "while", "try", "with", "switch"]
        
        for cls in module.classes:
            for method in cls.methods:
                if method.docstring:
                    nesting_level = self._estimate_nesting_level(method.docstring)
                    if nesting_level > 3:
                        smells.append({
                            "type": "Deep Nesting",
                            "severity": "medium",
                            "location": f"{module.name}.{cls.name}.{method.name}",
                            "description": f"方法 {method.name} 嵌套层级过深（约 {nesting_level} 层）",
                            "suggestion": "使用提前返回、提取方法或策略模式来减少嵌套",
                        })
        
        return smells

    def _estimate_nesting_level(self, code: str) -> int:
        """估算嵌套层级"""
        lines = code.split("\n")
        max_indent = 0
        
        for line in lines:
            if line.strip():
                indent = len(line) - len(line.lstrip())
                max_indent = max(max_indent, indent)
        
        return max_indent // 4

    def _detect_duplicate_code(self, module: Any) -> list[dict[str, Any]]:
        """检测重复代码"""
        smells = []
        
        method_signatures = {}
        
        for cls in module.classes:
            for method in cls.methods:
                sig = f"{len(method.parameters)}_{method.return_type or 'None'}"
                if sig not in method_signatures:
                    method_signatures[sig] = []
                method_signatures[sig].append(f"{module.name}.{cls.name}.{method.name}")
        
        for sig, locations in method_signatures.items():
            if len(locations) > 3:
                smells.append({
                    "type": "Duplicate Code",
                    "severity": "low",
                    "location": ", ".join(locations[:3]),
                    "description": f"发现 {len(locations)} 个相似签名的方法",
                    "suggestion": "考虑提取公共逻辑到基类或工具类",
                })
        
        return smells[:5]

    def _detect_dead_code(self, module: Any) -> list[dict[str, Any]]:
        """检测死代码"""
        smells = []
        
        for cls in module.classes:
            for method in cls.methods:
                if method.name.startswith("_") and not method.docstring:
                    if not any(prop.name == method.name for prop in cls.properties):
                        pass
        
        return smells

    def _detect_magic_numbers(self, module: Any) -> list[dict[str, Any]]:
        """检测魔法数字"""
        smells = []
        
        magic_pattern = r'\b\d{2,}\b'
        
        for cls in module.classes:
            for method in cls.methods:
                if method.docstring:
                    matches = re.findall(magic_pattern, method.docstring)
                    if len(matches) > 2:
                        smells.append({
                            "type": "Magic Numbers",
                            "severity": "low",
                            "location": f"{module.name}.{cls.name}.{method.name}",
                            "description": f"方法 {method.name} 包含魔法数字",
                            "suggestion": "将数字提取为命名常量",
                        })
        
        return smells[:10]

    def _detect_complex_conditionals(self, module: Any) -> list[dict[str, Any]]:
        """检测复杂条件"""
        smells = []
        
        complex_patterns = [" and ", " or ", "&&", "||", " not ", "!"]
        
        for cls in module.classes:
            for method in cls.methods:
                if method.docstring:
                    complexity = sum(method.docstring.lower().count(p) for p in complex_patterns)
                    if complexity > 3:
                        smells.append({
                            "type": "Complex Conditional",
                            "severity": "medium",
                            "location": f"{module.name}.{cls.name}.{method.name}",
                            "description": f"方法 {method.name} 包含复杂条件逻辑",
                            "suggestion": "考虑提取条件为独立的方法或使用策略模式",
                        })
        
        return smells[:10]

    def _calculate_metrics(self, context: DocGeneratorContext) -> list[dict[str, Any]]:
        """计算质量指标"""
        metrics = []
        
        if not context.parse_result or not context.parse_result.modules:
            return metrics
        
        total_modules = len(context.parse_result.modules)
        total_classes = sum(len(m.classes) for m in context.parse_result.modules)
        total_functions = sum(len(m.functions) for m in context.parse_result.modules)
        total_methods = sum(len(cls.methods) for m in context.parse_result.modules for cls in m.classes)
        
        documented_modules = sum(1 for m in context.parse_result.modules if m.docstring)
        documented_classes = sum(1 for m in context.parse_result.modules for cls in m.classes if cls.docstring)
        documented_functions = sum(1 for m in context.parse_result.modules for func in m.functions if func.docstring)
        
        typed_functions = 0
        total_function_params = 0
        typed_params = 0
        
        for module in context.parse_result.modules:
            for func in module.functions:
                if func.return_type:
                    typed_functions += 1
                for param in func.parameters:
                    total_function_params += 1
                    if param.type_hint:
                        typed_params += 1
            
            for cls in module.classes:
                for method in cls.methods:
                    if method.return_type:
                        typed_functions += 1
                    for param in method.parameters:
                        total_function_params += 1
                        if param.type_hint:
                            typed_params += 1
        
        if total_modules > 0:
            metrics.append({
                "name": "模块文档覆盖率",
                "value": documented_modules / total_modules * 100,
                "description": f"{documented_modules}/{total_modules} 模块有文档",
                "category": "文档",
            })
        
        if total_classes > 0:
            metrics.append({
                "name": "类文档覆盖率",
                "value": documented_classes / total_classes * 100,
                "description": f"{documented_classes}/{total_classes} 类有文档",
                "category": "文档",
            })
        
        if total_functions + total_methods > 0:
            total_funcs = total_functions + total_methods
            metrics.append({
                "name": "函数文档覆盖率",
                "value": documented_functions / total_funcs * 100,
                "description": f"{documented_functions}/{total_funcs} 函数有文档",
                "category": "文档",
            })
        
        if total_function_params > 0:
            metrics.append({
                "name": "类型提示覆盖率",
                "value": typed_params / total_function_params * 100,
                "description": f"{typed_params}/{total_function_params} 参数有类型提示",
                "category": "类型安全",
            })
        
        async_functions = 0
        for module in context.parse_result.modules:
            for func in module.functions:
                if func.is_async:
                    async_functions += 1
            for cls in module.classes:
                for method in cls.methods:
                    if hasattr(method, 'is_async') and method.is_async:
                        async_functions += 1
        
        metrics.append({
            "name": "代码规模",
            "value": total_modules + total_classes + total_functions + total_methods,
            "description": f"{total_modules} 模块, {total_classes} 类, {total_functions + total_methods} 函数",
            "category": "规模",
        })
        
        return metrics

    def _calculate_quality_score(self, metrics: list[dict], smells: list[dict]) -> dict[str, Any]:
        """计算质量评分"""
        score = {
            "overall": 0,
            "categories": {},
            "grade": "C",
        }
        
        if not metrics:
            return score
        
        doc_metrics = [m for m in metrics if m["category"] == "文档"]
        if doc_metrics:
            avg_doc = sum(m["value"] for m in doc_metrics) / len(doc_metrics)
            score["categories"]["文档"] = avg_doc
        
        type_metrics = [m for m in metrics if m["category"] == "类型安全"]
        if type_metrics:
            avg_type = sum(m["value"] for m in type_metrics) / len(type_metrics)
            score["categories"]["类型安全"] = avg_type
        
        smell_penalty = min(len(smells) * 2, 30)
        
        if score["categories"]:
            base_score = sum(score["categories"].values()) / len(score["categories"])
            score["overall"] = max(0, base_score - smell_penalty)
        else:
            score["overall"] = max(0, 100 - smell_penalty)
        
        if score["overall"] >= 90:
            score["grade"] = "A"
        elif score["overall"] >= 80:
            score["grade"] = "B"
        elif score["overall"] >= 70:
            score["grade"] = "C"
        elif score["overall"] >= 60:
            score["grade"] = "D"
        else:
            score["grade"] = "F"
        
        return score

    def _summarize_tech_debt(self, smells: list[dict]) -> dict[str, Any]:
        """汇总技术债务"""
        summary = {
            "total_issues": len(smells),
            "by_severity": {},
            "by_type": {},
        }
        
        for smell in smells:
            severity = smell.get("severity", "unknown")
            summary["by_severity"][severity] = summary["by_severity"].get(severity, 0) + 1
            
            smell_type = smell.get("type", "unknown")
            summary["by_type"][smell_type] = summary["by_type"].get(smell_type, 0) + 1
        
        return summary

    def _generate_recommendations(self, quality_data: dict) -> list[dict[str, Any]]:
        """生成改进建议"""
        recommendations = []
        
        score = quality_data.get("quality_score", {})
        overall = score.get("overall", 0)
        
        if overall < 60:
            recommendations.append({
                "priority": "critical",
                "title": "代码质量需要紧急改进",
                "description": f"当前质量评分为 {overall:.1f} 分（等级 {score.get('grade', 'F')}）",
                "action": "优先解决高严重性的代码异味，增加文档覆盖率",
            })
        elif overall < 80:
            recommendations.append({
                "priority": "high",
                "title": "代码质量有提升空间",
                "description": f"当前质量评分为 {overall:.1f} 分",
                "action": "逐步改进代码异味，提高类型提示覆盖率",
            })
        
        tech_debt = quality_data.get("tech_debt_summary", {})
        critical_issues = tech_debt.get("by_severity", {}).get("critical", 0)
        high_issues = tech_debt.get("by_severity", {}).get("high", 0)
        
        if critical_issues > 0:
            recommendations.append({
                "priority": "critical",
                "title": "存在严重代码问题",
                "description": f"发现 {critical_issues} 个严重问题需要立即处理",
                "action": "优先修复严重级别的代码异味",
            })
        
        if high_issues > 5:
            recommendations.append({
                "priority": "high",
                "title": "高优先级问题较多",
                "description": f"发现 {high_issues} 个高优先级问题",
                "action": "制定计划逐步解决高优先级问题",
            })
        
        doc_score = score.get("categories", {}).get("文档", 0)
        if doc_score < 50:
            recommendations.append({
                "priority": "medium",
                "title": "文档覆盖率不足",
                "description": f"文档覆盖率仅为 {doc_score:.1f}%",
                "action": "为核心模块和公共 API 添加文档字符串",
            })
        
        type_score = score.get("categories", {}).get("类型安全", 0)
        if type_score < 70:
            recommendations.append({
                "priority": "low",
                "title": "类型提示覆盖率可提升",
                "description": f"类型提示覆盖率为 {type_score:.1f}%",
                "action": "为函数参数和返回值添加类型提示",
            })
        
        if not recommendations:
            recommendations.append({
                "priority": "low",
                "title": "代码质量良好",
                "description": "当前代码质量较好，继续保持",
                "action": "定期进行代码审查，保持代码质量",
            })
        
        return recommendations

    async def _enhance_with_llm(
        self,
        context: DocGeneratorContext,
        quality_data: dict[str, Any],
        llm_client: Any,
    ) -> dict[str, Any]:
        """使用 LLM 增强质量分析"""
        import json

        enhanced = {}
        
        score = quality_data.get("quality_score", {})
        smells = quality_data.get("code_smells", [])

        prompt = f"""基于以下代码质量分析，提供改进建议：

项目: {context.project_name}
质量评分: {score.get('overall', 0):.1f} 分（等级 {score.get('grade', 'F')}）
代码异味数量: {len(smells)}

请以 JSON 格式返回：
{{
    "refactoring_priorities": ["重构优先级1", "重构优先级2"],
    "best_practices": ["最佳实践建议1", "最佳实践建议2"],
    "architecture_improvements": ["架构改进建议1", "架构改进建议2"],
    "team_guidelines": ["团队规范建议1", "团队规范建议2"]
}}
"""

        try:
            response = await llm_client.agenerate(prompt)
            start = response.find("{")
            end = response.rfind("}")
            if start != -1 and end != -1:
                result = json.loads(response[start:end+1])
                enhanced["llm_recommendations"] = result
        except Exception:
            pass

        return enhanced
