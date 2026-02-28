"""
LLM 增强器
使用 LLM 增强架构文档
"""

import json
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pywiki.generators.docs.base import DocGeneratorContext


class LLMEnhancer:
    """LLM 增强器"""

    def __init__(self, labels: dict):
        self.labels = labels

    async def enhance(
        self,
        context: "DocGeneratorContext",
        arch_data: dict[str, Any],
        llm_client: Any,
    ) -> dict[str, Any]:
        """使用 LLM 增强架构文档"""
        enhanced = {}

        quality_metrics = arch_data.get("quality_metrics", {})
        layers = arch_data.get("layers", [])

        system_prompt = self._get_system_prompt()

        if self.labels.get("language") == "zh":
            prompt = f"""# 任务
基于架构分析数据，提供深入的架构洞察和专业建议。

# 架构数据
- **项目名称**: {context.project_name}
- **分层结构**: {[l['name'] for l in layers]}
- **模块数量**: {quality_metrics.get('module_count', 0)}
- **类数量**: {quality_metrics.get('class_count', 0)}
- **耦合度**: {quality_metrics.get('coupling', {}).get('level', 'unknown')}
- **内聚性**: {quality_metrics.get('cohesion', {}).get('level', 'unknown')}
- **循环依赖**: {len(arch_data.get('circular_dependencies', []))}
- **热点模块**: {len(arch_data.get('hot_spots', []))}

# 输出要求
请以 JSON 格式返回以下字段：
{{
    "architecture_style": "架构风格（如分层架构、微服务、事件驱动等，需说明判断依据）",
    "strengths": ["架构优势1", "架构优势2"],
    "weaknesses": ["架构劣势1", "架构劣势2"],
    "risk_assessment": "风险评估"
}}

请务必使用中文回答。"""
        else:
            prompt = f"""# Task
Based on architecture analysis data, provide in-depth architectural insights.

# Architecture Data
- **Project Name**: {context.project_name}
- **Layer Structure**: {[l['name'] for l in layers]}
- **Module Count**: {quality_metrics.get('module_count', 0)}
- **Class Count**: {quality_metrics.get('class_count', 0)}
- **Coupling**: {quality_metrics.get('coupling', {}).get('level', 'unknown')}
- **Cohesion**: {quality_metrics.get('cohesion', {}).get('level', 'unknown')}

# Output Requirements
Please return the following fields in JSON format:
{{
    "architecture_style": "Architecture style with reasoning",
    "strengths": ["strength 1", "strength 2"],
    "weaknesses": ["weakness 1", "weakness 2"],
    "risk_assessment": "Risk assessment"
}}

Please respond in English."""

        try:
            response = await llm_client.agenerate(prompt, system_prompt=system_prompt)
            start = response.find("{")
            end = response.rfind("}")
            if start != -1 and end != -1:
                result = json.loads(response[start:end+1])

                if result.get("architecture_style"):
                    enhanced["architecture_style"] = result["architecture_style"]

                if result.get("strengths"):
                    enhanced["strengths"] = result["strengths"]

                if result.get("weaknesses"):
                    enhanced["weaknesses"] = result["weaknesses"]

                if result.get("risk_assessment"):
                    enhanced["risk_assessment"] = result["risk_assessment"]

                if result.get("improvement_suggestions"):
                    for suggestion in result["improvement_suggestions"]:
                        arch_data["recommendations"].append({
                            "title": "AI 建议",
                            "priority": "medium",
                            "description": suggestion,
                        })
        except Exception:
            pass

        return enhanced

    def _get_system_prompt(self) -> str:
        """获取系统提示词"""
        return "你是一名资深软件架构师，擅长分析系统架构并提供专业建议。"
