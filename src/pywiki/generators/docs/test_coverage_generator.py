"""
测试覆盖分析文档生成器
分析测试文件和测试用例，生成测试覆盖率报告
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
class TestCase:
    """测试用例"""
    name: str
    description: str = ""
    location: str = ""
    test_type: str = "unit"
    is_async: bool = False
    parameters: list[str] = field(default_factory=list)


@dataclass
class TestModule:
    """测试模块"""
    name: str
    path: str
    test_count: int = 0
    test_cases: list[TestCase] = field(default_factory=list)


@dataclass
class CoverageReport:
    """覆盖率报告"""
    total_modules: int = 0
    tested_modules: int = 0
    total_functions: int = 0
    tested_functions: int = 0
    total_classes: int = 0
    tested_classes: int = 0
    untested_items: list[dict] = field(default_factory=list)


class TestCoverageGenerator(BaseDocGenerator):
    """测试覆盖分析文档生成器"""

    doc_type = DocType.TSD
    template_name = "tsd.md.j2"

    def __init__(self, language: Language = Language.ZH, template_dir: Optional[Path] = None):
        super().__init__(language, template_dir)

    async def generate(self, context: DocGeneratorContext) -> DocGeneratorResult:
        """生成测试覆盖分析文档"""
        try:
            project_language = context.project_language or context.detect_project_language()
            
            test_data = {
                "test_modules": [],
                "coverage_report": {},
                "test_statistics": {},
                "recommendations": [],
            }
            
            test_data["test_modules"] = self._extract_test_modules(context, project_language)
            test_data["coverage_report"] = self._analyze_coverage(context, test_data["test_modules"], project_language)
            test_data["test_statistics"] = self._calculate_statistics(test_data["test_modules"])
            test_data["recommendations"] = self._generate_recommendations(test_data["coverage_report"])
            
            if context.metadata.get("llm_client"):
                enhanced_data = await self._enhance_with_llm(
                    context,
                    test_data,
                    context.metadata["llm_client"]
                )
                test_data.update(enhanced_data)

            content = self.render_template(
                description=f"{context.project_name} 测试覆盖分析",
                test_modules=test_data["test_modules"],
                coverage_report=test_data["coverage_report"],
                test_statistics=test_data["test_statistics"],
                recommendations=test_data["recommendations"],
            )

            return self.create_result(
                content=content,
                context=context,
                success=True,
                message=self.labels.get("test_coverage_doc_success", "Test coverage analysis generated successfully"),
                metadata={"test_count": test_data["test_statistics"].get("total_tests", 0)},
            )

        except Exception as e:
            return self.create_result(
                content="",
                context=context,
                success=False,
                message=f"{self.labels.get('generation_failed', 'Generation failed')}: {str(e)}",
            )

    def _extract_test_modules(self, context: DocGeneratorContext, project_language: str) -> list[dict[str, Any]]:
        """提取测试模块"""
        test_modules = []
        
        if not context.parse_result or not context.parse_result.modules:
            return test_modules
        
        test_keywords = self._get_test_keywords(project_language)
        
        for module in context.parse_result.modules:
            is_test_module = self._is_test_module(module.name, test_keywords)
            
            if is_test_module:
                test_module = {
                    "name": module.name,
                    "path": module.name.replace(".", "/"),
                    "test_count": 0,
                    "test_cases": [],
                }
                
                for cls in module.classes:
                    for method in cls.methods:
                        if self._is_test_method(method.name, project_language):
                            test_case = {
                                "name": f"{cls.name}.{method.name}",
                                "description": method.docstring.split("\n")[0] if method.docstring else "",
                                "location": f"{module.name}.{cls.name}",
                                "test_type": self._determine_test_type(method.name),
                                "is_async": method.is_async if hasattr(method, 'is_async') else False,
                            }
                            test_module["test_cases"].append(test_case)
                            test_module["test_count"] += 1
                
                for func in module.functions:
                    if self._is_test_function(func.name, project_language):
                        test_case = {
                            "name": func.name,
                            "description": func.docstring.split("\n")[0] if func.docstring else "",
                            "location": module.name,
                            "test_type": self._determine_test_type(func.name),
                            "is_async": func.is_async if hasattr(func, 'is_async') else False,
                        }
                        test_module["test_cases"].append(test_case)
                        test_module["test_count"] += 1
                
                if test_module["test_count"] > 0:
                    test_modules.append(test_module)
        
        return test_modules

    def _get_test_keywords(self, project_language: str) -> dict[str, list[str]]:
        """获取测试关键词"""
        if project_language == "java":
            return {
                "module": ["test", "tests"],
                "function": ["@Test", "@ParameterizedTest", "@RepeatedTest"],
                "class": ["Test", "Tests", "IT", "E2E"],
            }
        elif project_language == "typescript":
            return {
                "module": ["test", "tests", "spec", "__tests__"],
                "function": ["test", "it", "describe", "expect"],
                "class": ["Test", "Spec"],
            }
        else:
            return {
                "module": ["test", "tests"],
                "function": ["test_", "async_test_", "pytest"],
                "class": ["Test", "Tests"],
            }

    def _is_test_module(self, module_name: str, keywords: dict) -> bool:
        """判断是否为测试模块"""
        module_lower = module_name.lower()
        return any(kw in module_lower for kw in keywords["module"])

    def _is_test_method(self, method_name: str, project_language: str) -> bool:
        """判断是否为测试方法"""
        if project_language == "java":
            return method_name.startswith("test") or "Test" in method_name
        elif project_language == "typescript":
            return method_name in ["test", "it", "beforeEach", "afterEach", "beforeAll", "afterAll"]
        else:
            return method_name.startswith("test_")

    def _is_test_function(self, func_name: str, project_language: str) -> bool:
        """判断是否为测试函数"""
        if project_language == "java":
            return False
        elif project_language == "typescript":
            return func_name in ["test", "it", "describe"]
        else:
            return func_name.startswith("test_")

    def _determine_test_type(self, name: str) -> str:
        """确定测试类型"""
        name_lower = name.lower()
        
        if "integration" in name_lower or "e2e" in name_lower or "it" in name_lower:
            return "integration"
        elif "unit" in name_lower:
            return "unit"
        elif "functional" in name_lower:
            return "functional"
        elif "performance" in name_lower or "benchmark" in name_lower or "load" in name_lower:
            return "performance"
        elif "security" in name_lower:
            return "security"
        else:
            return "unit"

    def _analyze_coverage(self, context: DocGeneratorContext, test_modules: list[dict], project_language: str) -> dict[str, Any]:
        """分析测试覆盖率"""
        coverage = {
            "total_modules": 0,
            "tested_modules": 0,
            "total_functions": 0,
            "tested_functions": 0,
            "total_classes": 0,
            "tested_classes": 0,
            "module_coverage": 0.0,
            "function_coverage": 0.0,
            "class_coverage": 0.0,
            "untested_modules": [],
            "untested_functions": [],
            "untested_classes": [],
        }
        
        if not context.parse_result or not context.parse_result.modules:
            return coverage
        
        test_module_names = set()
        for tm in test_modules:
            base_name = tm["name"].replace("test_", "").replace("_test", "").replace("Test", "").replace("Tests", "")
            test_module_names.add(base_name.lower())
        
        for module in context.parse_result.modules:
            module_lower = module.name.lower()
            if "test" in module_lower:
                continue
            
            coverage["total_modules"] += 1
            
            base_name = module.name.split(".")[-1].lower()
            is_tested = any(base_name in tm or tm in base_name for tm in test_module_names)
            
            if is_tested:
                coverage["tested_modules"] += 1
            else:
                coverage["untested_modules"].append({
                    "name": module.name,
                    "functions": len(module.functions),
                    "classes": len(module.classes),
                })
            
            for func in module.functions:
                coverage["total_functions"] += 1
            
            for cls in module.classes:
                coverage["total_classes"] += 1
        
        if coverage["total_modules"] > 0:
            coverage["module_coverage"] = coverage["tested_modules"] / coverage["total_modules"] * 100
        
        if coverage["total_functions"] > 0:
            coverage["function_coverage"] = coverage["tested_functions"] / coverage["total_functions"] * 100
        
        if coverage["total_classes"] > 0:
            coverage["class_coverage"] = coverage["tested_classes"] / coverage["total_classes"] * 100
        
        return coverage

    def _calculate_statistics(self, test_modules: list[dict]) -> dict[str, Any]:
        """计算测试统计"""
        statistics = {
            "total_tests": 0,
            "total_test_modules": 0,
            "by_type": {},
            "by_module": [],
        }
        
        for module in test_modules:
            statistics["total_tests"] += module["test_count"]
            statistics["total_test_modules"] += 1
            
            statistics["by_module"].append({
                "name": module["name"],
                "count": module["test_count"],
            })
            
            for test_case in module["test_cases"]:
                test_type = test_case.get("test_type", "unit")
                statistics["by_type"][test_type] = statistics["by_type"].get(test_type, 0) + 1
        
        statistics["by_module"].sort(key=lambda x: x["count"], reverse=True)
        
        return statistics

    def _generate_recommendations(self, coverage_report: dict) -> list[dict[str, Any]]:
        """生成测试改进建议"""
        recommendations = []
        
        module_coverage = coverage_report.get("module_coverage", 0)
        
        if module_coverage < 50:
            recommendations.append({
                "priority": "high",
                "title": "测试覆盖率严重不足",
                "description": f"模块测试覆盖率仅为 {module_coverage:.1f}%，建议优先为核心模块添加测试",
                "action": "为关键业务模块创建测试文件",
            })
        elif module_coverage < 80:
            recommendations.append({
                "priority": "medium",
                "title": "测试覆盖率需要提升",
                "description": f"模块测试覆盖率为 {module_coverage:.1f}%，建议继续补充测试用例",
                "action": "为未测试的模块添加单元测试",
            })
        
        untested_modules = coverage_report.get("untested_modules", [])
        if untested_modules:
            important_untested = [m for m in untested_modules if m["functions"] > 5 or m["classes"] > 2]
            if important_untested:
                recommendations.append({
                    "priority": "high",
                    "title": "重要模块缺少测试",
                    "description": f"发现 {len(important_untested)} 个重要模块缺少测试",
                    "action": f"优先为 {important_untested[0]['name']} 等模块添加测试",
                })
        
        if not recommendations:
            recommendations.append({
                "priority": "low",
                "title": "测试覆盖良好",
                "description": "当前测试覆盖率较好，建议持续维护",
                "action": "定期运行测试并更新测试用例",
            })
        
        return recommendations

    async def _enhance_with_llm(
        self,
        context: DocGeneratorContext,
        test_data: dict[str, Any],
        llm_client: Any,
    ) -> dict[str, Any]:
        """使用 LLM 增强测试分析"""
        import json

        enhanced = {}
        
        coverage = test_data.get("coverage_report", {})
        statistics = test_data.get("test_statistics", {})

        if self.language == Language.ZH:
            prompt = f"""基于以下测试分析，提供测试改进建议：

项目: {context.project_name}
测试总数: {statistics.get('total_tests', 0)}
模块覆盖率: {coverage.get('module_coverage', 0):.1f}%
未测试模块数: {len(coverage.get('untested_modules', []))}

请以 JSON 格式返回：
{{
    "testing_strategy": "测试策略建议",
    "priority_areas": ["优先测试区域1", "优先测试区域2"],
    "test_quality_tips": ["测试质量建议1", "测试质量建议2"],
    "ci_cd_recommendations": ["CI/CD 建议1", "CI/CD 建议2"]
}}

请务必使用中文回答。"""
        else:
            prompt = f"""Based on the following test analysis, provide test improvement suggestions:

Project: {context.project_name}
Total Tests: {statistics.get('total_tests', 0)}
Module Coverage: {coverage.get('module_coverage', 0):.1f}%
Untested Modules: {len(coverage.get('untested_modules', []))}

Please return in JSON format:
{{
    "testing_strategy": "Testing strategy recommendation",
    "priority_areas": ["priority area1", "priority area2"],
    "test_quality_tips": ["quality tip1", "quality tip2"],
    "ci_cd_recommendations": ["CI/CD recommendation1", "CI/CD recommendation2"]
}}

Please respond in English."""

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
