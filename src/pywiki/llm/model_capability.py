"""
模型能力评估
评估不同 LLM 模型的能力和适用场景
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional


class CapabilityDimension(str, Enum):
    REASONING = "reasoning"
    CODING = "coding"
    CREATIVITY = "creativity"
    SPEED = "speed"
    CONTEXT_LENGTH = "context_length"
    MULTILINGUAL = "multilingual"
    INSTRUCTION_FOLLOWING = "instruction_following"
    FACTUAL_ACCURACY = "factual_accuracy"


@dataclass
class CapabilityScore:
    """能力评分"""
    dimension: CapabilityDimension
    score: float
    confidence: float = 1.0
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "dimension": self.dimension.value,
            "score": self.score,
            "confidence": self.confidence,
            "notes": self.notes,
        }


@dataclass
class ModelCapability:
    """模型能力评估"""
    model_name: str
    provider: str
    scores: dict[str, CapabilityScore] = field(default_factory=dict)
    overall_score: float = 0.0
    strengths: list[str] = field(default_factory=list)
    weaknesses: list[str] = field(default_factory=list)
    best_for: list[str] = field(default_factory=list)
    last_updated: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict[str, Any]:
        return {
            "model_name": self.model_name,
            "provider": self.provider,
            "scores": {k: v.to_dict() for k, v in self.scores.items()},
            "overall_score": round(self.overall_score, 2),
            "strengths": self.strengths,
            "weaknesses": self.weaknesses,
            "best_for": self.best_for,
            "last_updated": self.last_updated.isoformat(),
        }


class ModelCapabilityEvaluator:
    """
    模型能力评估器
    评估和比较不同 LLM 模型的能力
    """

    KNOWN_CAPABILITIES: dict[str, dict[str, float]] = {
        "gpt-4": {
            CapabilityDimension.REASONING.value: 0.95,
            CapabilityDimension.CODING.value: 0.92,
            CapabilityDimension.CREATIVITY.value: 0.88,
            CapabilityDimension.SPEED.value: 0.6,
            CapabilityDimension.CONTEXT_LENGTH.value: 0.7,
            CapabilityDimension.MULTILINGUAL.value: 0.9,
            CapabilityDimension.INSTRUCTION_FOLLOWING.value: 0.95,
            CapabilityDimension.FACTUAL_ACCURACY.value: 0.88,
        },
        "gpt-4-turbo": {
            CapabilityDimension.REASONING.value: 0.92,
            CapabilityDimension.CODING.value: 0.90,
            CapabilityDimension.CREATIVITY.value: 0.85,
            CapabilityDimension.SPEED.value: 0.85,
            CapabilityDimension.CONTEXT_LENGTH.value: 0.95,
            CapabilityDimension.MULTILINGUAL.value: 0.88,
            CapabilityDimension.INSTRUCTION_FOLLOWING.value: 0.92,
            CapabilityDimension.FACTUAL_ACCURACY.value: 0.85,
        },
        "gpt-3.5-turbo": {
            CapabilityDimension.REASONING.value: 0.75,
            CapabilityDimension.CODING.value: 0.75,
            CapabilityDimension.CREATIVITY.value: 0.7,
            CapabilityDimension.SPEED.value: 0.95,
            CapabilityDimension.CONTEXT_LENGTH.value: 0.5,
            CapabilityDimension.MULTILINGUAL.value: 0.8,
            CapabilityDimension.INSTRUCTION_FOLLOWING.value: 0.8,
            CapabilityDimension.FACTUAL_ACCURACY.value: 0.7,
        },
        "claude-3-opus": {
            CapabilityDimension.REASONING.value: 0.95,
            CapabilityDimension.CODING.value: 0.90,
            CapabilityDimension.CREATIVITY.value: 0.95,
            CapabilityDimension.SPEED.value: 0.5,
            CapabilityDimension.CONTEXT_LENGTH.value: 0.98,
            CapabilityDimension.MULTILINGUAL.value: 0.85,
            CapabilityDimension.INSTRUCTION_FOLLOWING.value: 0.93,
            CapabilityDimension.FACTUAL_ACCURACY.value: 0.90,
        },
        "claude-3-sonnet": {
            CapabilityDimension.REASONING.value: 0.85,
            CapabilityDimension.CODING.value: 0.82,
            CapabilityDimension.CREATIVITY.value: 0.80,
            CapabilityDimension.SPEED.value: 0.8,
            CapabilityDimension.CONTEXT_LENGTH.value: 0.95,
            CapabilityDimension.MULTILINGUAL.value: 0.82,
            CapabilityDimension.INSTRUCTION_FOLLOWING.value: 0.88,
            CapabilityDimension.FACTUAL_ACCURACY.value: 0.82,
        },
        "claude-3-haiku": {
            CapabilityDimension.REASONING.value: 0.7,
            CapabilityDimension.CODING.value: 0.68,
            CapabilityDimension.CREATIVITY.value: 0.65,
            CapabilityDimension.SPEED.value: 0.98,
            CapabilityDimension.CONTEXT_LENGTH.value: 0.9,
            CapabilityDimension.MULTILINGUAL.value: 0.75,
            CapabilityDimension.INSTRUCTION_FOLLOWING.value: 0.78,
            CapabilityDimension.FACTUAL_ACCURACY.value: 0.72,
        },
    }

    CAPABILITY_WEIGHTS: dict[str, float] = {
        CapabilityDimension.REASONING.value: 0.2,
        CapabilityDimension.CODING.value: 0.15,
        CapabilityDimension.CREATIVITY.value: 0.1,
        CapabilityDimension.SPEED.value: 0.1,
        CapabilityDimension.CONTEXT_LENGTH.value: 0.1,
        CapabilityDimension.MULTILINGUAL.value: 0.1,
        CapabilityDimension.INSTRUCTION_FOLLOWING.value: 0.15,
        CapabilityDimension.FACTUAL_ACCURACY.value: 0.1,
    }

    def __init__(self):
        self._evaluations: dict[str, ModelCapability] = {}
        self._load_known_capabilities()

    def _load_known_capabilities(self) -> None:
        """加载已知模型能力"""
        for model_name, scores in self.KNOWN_CAPABILITIES.items():
            capability = ModelCapability(
                model_name=model_name,
                provider=self._get_provider(model_name),
                scores={
                    dim: CapabilityScore(
                        dimension=CapabilityDimension(dim),
                        score=score,
                    )
                    for dim, score in scores.items()
                },
            )
            capability.overall_score = self._calculate_overall(scores)
            capability.strengths = self._identify_strengths(scores)
            capability.weaknesses = self._identify_weaknesses(scores)
            capability.best_for = self._determine_best_for(scores)

            self._evaluations[model_name] = capability

    def _get_provider(self, model_name: str) -> str:
        """获取模型提供商"""
        if "gpt" in model_name.lower():
            return "openai"
        elif "claude" in model_name.lower():
            return "anthropic"
        else:
            return "unknown"

    def _calculate_overall(self, scores: dict[str, float]) -> float:
        """计算综合得分"""
        total = 0.0
        for dim, score in scores.items():
            weight = self.CAPABILITY_WEIGHTS.get(dim, 0.1)
            total += score * weight
        return total

    def _identify_strengths(self, scores: dict[str, float]) -> list[str]:
        """识别优势"""
        strengths = []
        for dim, score in scores.items():
            if score >= 0.85:
                strengths.append(self._get_dimension_label(dim))
        return strengths[:3]

    def _identify_weaknesses(self, scores: dict[str, float]) -> list[str]:
        """识别劣势"""
        weaknesses = []
        for dim, score in scores.items():
            if score < 0.7:
                weaknesses.append(self._get_dimension_label(dim))
        return weaknesses[:3]

    def _determine_best_for(self, scores: dict[str, float]) -> list[str]:
        """确定最佳用途"""
        best_for = []

        if scores.get(CapabilityDimension.CODING.value, 0) >= 0.8:
            best_for.append("代码生成和分析")

        if scores.get(CapabilityDimension.REASONING.value, 0) >= 0.85:
            best_for.append("复杂推理任务")

        if scores.get(CapabilityDimension.CREATIVITY.value, 0) >= 0.8:
            best_for.append("创意写作")

        if scores.get(CapabilityDimension.SPEED.value, 0) >= 0.9:
            best_for.append("快速响应场景")

        if scores.get(CapabilityDimension.CONTEXT_LENGTH.value, 0) >= 0.9:
            best_for.append("长文本处理")

        return best_for[:4]

    def _get_dimension_label(self, dimension: str) -> str:
        """获取维度标签"""
        labels = {
            CapabilityDimension.REASONING.value: "推理能力",
            CapabilityDimension.CODING.value: "代码能力",
            CapabilityDimension.CREATIVITY.value: "创造力",
            CapabilityDimension.SPEED.value: "响应速度",
            CapabilityDimension.CONTEXT_LENGTH.value: "上下文长度",
            CapabilityDimension.MULTILINGUAL.value: "多语言支持",
            CapabilityDimension.INSTRUCTION_FOLLOWING.value: "指令遵循",
            CapabilityDimension.FACTUAL_ACCURACY.value: "事实准确性",
        }
        return labels.get(dimension, dimension)

    def get_capability(self, model_name: str) -> Optional[ModelCapability]:
        """获取模型能力评估"""
        return self._evaluations.get(model_name)

    def compare_models(
        self,
        model_names: list[str],
        dimension: Optional[CapabilityDimension] = None,
    ) -> dict[str, Any]:
        """
        比较多个模型

        Args:
            model_names: 模型名称列表
            dimension: 特定维度（可选）

        Returns:
            比较结果
        """
        comparison = {
            "models": [],
            "by_dimension": {},
            "ranking": [],
        }

        for name in model_names:
            cap = self._evaluations.get(name)
            if cap:
                comparison["models"].append(cap.to_dict())

        if dimension:
            dim_key = dimension.value
            scores = []
            for name in model_names:
                cap = self._evaluations.get(name)
                if cap and dim_key in cap.scores:
                    scores.append((name, cap.scores[dim_key].score))

            scores.sort(key=lambda x: x[1], reverse=True)
            comparison["ranking"] = scores
        else:
            scores = []
            for name in model_names:
                cap = self._evaluations.get(name)
                if cap:
                    scores.append((name, cap.overall_score))

            scores.sort(key=lambda x: x[1], reverse=True)
            comparison["ranking"] = scores

        for dim in CapabilityDimension:
            dim_scores = {}
            for name in model_names:
                cap = self._evaluations.get(name)
                if cap and dim.value in cap.scores:
                    dim_scores[name] = cap.scores[dim.value].score
            comparison["by_dimension"][dim.value] = dim_scores

        return comparison

    def get_best_model_for_task(
        self,
        task_requirements: dict[str, float],
        available_models: Optional[list[str]] = None,
    ) -> Optional[str]:
        """
        获取最适合特定任务的模型

        Args:
            task_requirements: 任务对各维度的要求（0-1）
            available_models: 可用模型列表

        Returns:
            最佳模型名称
        """
        models = available_models or list(self._evaluations.keys())

        best_model = None
        best_score = -1

        for model_name in models:
            cap = self._evaluations.get(model_name)
            if not cap:
                continue

            score = 0.0
            for dim, requirement in task_requirements.items():
                if dim in cap.scores:
                    capability_score = cap.scores[dim].score
                    if capability_score >= requirement:
                        score += capability_score * requirement
                    else:
                        score -= (requirement - capability_score) * 0.5

            if score > best_score:
                best_score = score
                best_model = model_name

        return best_model

    def register_capability(
        self,
        model_name: str,
        provider: str,
        scores: dict[str, float],
    ) -> ModelCapability:
        """注册模型能力"""
        capability = ModelCapability(
            model_name=model_name,
            provider=provider,
            scores={
                dim: CapabilityScore(
                    dimension=CapabilityDimension(dim),
                    score=score,
                )
                for dim, score in scores.items()
            },
        )
        capability.overall_score = self._calculate_overall(scores)
        capability.strengths = self._identify_strengths(scores)
        capability.weaknesses = self._identify_weaknesses(scores)
        capability.best_for = self._determine_best_for(scores)

        self._evaluations[model_name] = capability
        return capability

    def list_models(self) -> list[str]:
        """列出所有模型"""
        return list(self._evaluations.keys())

    def get_models_by_dimension(
        self,
        dimension: CapabilityDimension,
        min_score: float = 0.8,
    ) -> list[str]:
        """获取在特定维度表现好的模型"""
        result = []
        for name, cap in self._evaluations.items():
            if dimension.value in cap.scores:
                if cap.scores[dimension.value].score >= min_score:
                    result.append(name)
        return sorted(
            result,
            key=lambda x: self._evaluations[x].scores[dimension.value].score,
            reverse=True,
        )

    def get_capability_summary(self) -> dict[str, Any]:
        """获取能力摘要"""
        return {
            "total_models": len(self._evaluations),
            "models": {
                name: {
                    "overall_score": cap.overall_score,
                    "provider": cap.provider,
                    "best_for": cap.best_for,
                }
                for name, cap in self._evaluations.items()
            },
            "dimension_rankings": {
                dim.value: self.get_models_by_dimension(dim, min_score=0.0)[:5]
                for dim in CapabilityDimension
            },
        }
