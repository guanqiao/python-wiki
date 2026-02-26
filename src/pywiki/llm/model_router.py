"""
多模型路由器
智能选择最优的 LLM 模型
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional


class TaskType(str, Enum):
    CODE_GENERATION = "code_generation"
    CODE_ANALYSIS = "code_analysis"
    DOCUMENTATION = "documentation"
    SUMMARIZATION = "summarization"
    TRANSLATION = "translation"
    REASONING = "reasoning"
    CREATIVE = "creative"
    EMBEDDING = "embedding"


class ModelProvider(str, Enum):
    OPENAI = "openai"
    AZURE = "azure"
    ANTHROPIC = "anthropic"
    CUSTOM = "custom"


@dataclass
class ModelConfig:
    """模型配置"""
    name: str
    provider: ModelProvider
    endpoint: str
    api_key: str
    max_tokens: int = 4096
    temperature: float = 0.7
    cost_per_1k_tokens: float = 0.0
    capabilities: list[TaskType] = field(default_factory=list)
    priority: int = 0
    is_default: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class RoutingDecision:
    """路由决策"""
    selected_model: str
    provider: ModelProvider
    reason: str
    alternatives: list[str] = field(default_factory=list)
    estimated_cost: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict[str, Any]:
        return {
            "selected_model": self.selected_model,
            "provider": self.provider.value,
            "reason": self.reason,
            "alternatives": self.alternatives,
            "estimated_cost": self.estimated_cost,
            "timestamp": self.timestamp.isoformat(),
        }


class ModelRouter:
    """
    多模型路由器
    根据任务类型、成本和性能智能选择模型
    """

    DEFAULT_MODELS: dict[str, ModelConfig] = {
        "gpt-4": ModelConfig(
            name="gpt-4",
            provider=ModelProvider.OPENAI,
            endpoint="https://api.openai.com/v1",
            api_key="",
            max_tokens=8192,
            cost_per_1k_tokens=0.03,
            capabilities=[
                TaskType.CODE_GENERATION,
                TaskType.CODE_ANALYSIS,
                TaskType.REASONING,
                TaskType.DOCUMENTATION,
            ],
            priority=10,
            is_default=True,
        ),
        "gpt-3.5-turbo": ModelConfig(
            name="gpt-3.5-turbo",
            provider=ModelProvider.OPENAI,
            endpoint="https://api.openai.com/v1",
            api_key="",
            max_tokens=4096,
            cost_per_1k_tokens=0.002,
            capabilities=[
                TaskType.SUMMARIZATION,
                TaskType.TRANSLATION,
                TaskType.DOCUMENTATION,
            ],
            priority=5,
        ),
        "gpt-4-turbo": ModelConfig(
            name="gpt-4-turbo",
            provider=ModelProvider.OPENAI,
            endpoint="https://api.openai.com/v1",
            api_key="",
            max_tokens=128000,
            cost_per_1k_tokens=0.01,
            capabilities=[
                TaskType.CODE_GENERATION,
                TaskType.CODE_ANALYSIS,
                TaskType.REASONING,
                TaskType.DOCUMENTATION,
                TaskType.SUMMARIZATION,
            ],
            priority=8,
        ),
        "claude-3-opus": ModelConfig(
            name="claude-3-opus",
            provider=ModelProvider.ANTHROPIC,
            endpoint="https://api.anthropic.com/v1",
            api_key="",
            max_tokens=200000,
            cost_per_1k_tokens=0.015,
            capabilities=[
                TaskType.CODE_GENERATION,
                TaskType.CODE_ANALYSIS,
                TaskType.REASONING,
                TaskType.CREATIVE,
            ],
            priority=9,
        ),
        "claude-3-sonnet": ModelConfig(
            name="claude-3-sonnet",
            provider=ModelProvider.ANTHROPIC,
            endpoint="https://api.anthropic.com/v1",
            api_key="",
            max_tokens=200000,
            cost_per_1k_tokens=0.003,
            capabilities=[
                TaskType.CODE_ANALYSIS,
                TaskType.DOCUMENTATION,
                TaskType.SUMMARIZATION,
            ],
            priority=7,
        ),
    }

    TASK_MODEL_PREFERENCES: dict[TaskType, list[str]] = {
        TaskType.CODE_GENERATION: ["gpt-4", "claude-3-opus", "gpt-4-turbo"],
        TaskType.CODE_ANALYSIS: ["gpt-4-turbo", "claude-3-sonnet", "gpt-4"],
        TaskType.DOCUMENTATION: ["gpt-4-turbo", "claude-3-sonnet", "gpt-3.5-turbo"],
        TaskType.SUMMARIZATION: ["gpt-3.5-turbo", "claude-3-sonnet", "gpt-4-turbo"],
        TaskType.TRANSLATION: ["gpt-3.5-turbo", "gpt-4-turbo"],
        TaskType.REASONING: ["gpt-4", "claude-3-opus", "gpt-4-turbo"],
        TaskType.CREATIVE: ["claude-3-opus", "gpt-4", "claude-3-sonnet"],
        TaskType.EMBEDDING: [],
    }

    def __init__(
        self,
        models: Optional[dict[str, ModelConfig]] = None,
        cost_optimization: bool = True,
        fallback_enabled: bool = True,
    ):
        self.models = models or self.DEFAULT_MODELS.copy()
        self.cost_optimization = cost_optimization
        self.fallback_enabled = fallback_enabled

        self._usage_stats: dict[str, dict[str, Any]] = {
            name: {"calls": 0, "tokens": 0, "errors": 0}
            for name in self.models
        }

    def register_model(self, config: ModelConfig) -> None:
        """注册模型"""
        self.models[config.name] = config
        self._usage_stats[config.name] = {"calls": 0, "tokens": 0, "errors": 0}

    def unregister_model(self, name: str) -> bool:
        """注销模型"""
        if name in self.models:
            del self.models[name]
            del self._usage_stats[name]
            return True
        return False

    def route(
        self,
        task_type: TaskType,
        prompt_length: int = 0,
        prefer_speed: bool = False,
        prefer_quality: bool = False,
        max_cost: Optional[float] = None,
    ) -> RoutingDecision:
        """
        路由到最优模型

        Args:
            task_type: 任务类型
            prompt_length: 提示词长度
            prefer_speed: 优先速度
            prefer_quality: 优先质量
            max_cost: 最大成本限制

        Returns:
            路由决策
        """
        candidates = self._get_candidates(task_type)

        if not candidates:
            default = self._get_default_model()
            if default:
                return RoutingDecision(
                    selected_model=default.name,
                    provider=default.provider,
                    reason="使用默认模型（无匹配模型）",
                )
            raise ValueError("没有可用的模型")

        candidates = self._filter_by_cost(candidates, max_cost)

        if prefer_quality:
            candidates = self._sort_by_quality(candidates)
        elif prefer_speed or self.cost_optimization:
            candidates = self._sort_by_cost(candidates)
        else:
            candidates = self._sort_by_priority(candidates)

        selected = candidates[0]
        alternatives = [m.name for m in candidates[1:4]]

        estimated_cost = self._estimate_cost(selected, prompt_length)

        return RoutingDecision(
            selected_model=selected.name,
            provider=selected.provider,
            reason=self._get_reason(selected, task_type, prefer_quality, prefer_speed),
            alternatives=alternatives,
            estimated_cost=estimated_cost,
        )

    def route_by_content(
        self,
        content: str,
        task_type: Optional[TaskType] = None,
    ) -> RoutingDecision:
        """
        根据内容自动路由

        Args:
            content: 内容
            task_type: 任务类型（可选，自动检测）

        Returns:
            路由决策
        """
        if task_type is None:
            task_type = self._detect_task_type(content)

        prompt_length = len(content)
        prefer_quality = self._needs_quality(content)
        prefer_speed = len(content) < 500

        return self.route(
            task_type=task_type,
            prompt_length=prompt_length,
            prefer_speed=prefer_speed,
            prefer_quality=prefer_quality,
        )

    def _get_candidates(self, task_type: TaskType) -> list[ModelConfig]:
        """获取候选模型"""
        preferences = self.TASK_MODEL_PREFERENCES.get(task_type, [])

        candidates = []
        for name in preferences:
            if name in self.models:
                config = self.models[name]
                if task_type in config.capabilities:
                    candidates.append(config)

        if not candidates:
            for config in self.models.values():
                if task_type in config.capabilities:
                    candidates.append(config)

        return candidates

    def _filter_by_cost(
        self,
        candidates: list[ModelConfig],
        max_cost: Optional[float],
    ) -> list[ModelConfig]:
        """按成本过滤"""
        if max_cost is None:
            return candidates

        return [
            c for c in candidates
            if c.cost_per_1k_tokens <= max_cost
        ]

    def _sort_by_quality(self, candidates: list[ModelConfig]) -> list[ModelConfig]:
        """按质量排序"""
        return sorted(candidates, key=lambda x: x.priority, reverse=True)

    def _sort_by_cost(self, candidates: list[ModelConfig]) -> list[ModelConfig]:
        """按成本排序"""
        return sorted(candidates, key=lambda x: x.cost_per_1k_tokens)

    def _sort_by_priority(self, candidates: list[ModelConfig]) -> list[ModelConfig]:
        """按优先级排序"""
        return sorted(candidates, key=lambda x: x.priority, reverse=True)

    def _get_default_model(self) -> Optional[ModelConfig]:
        """获取默认模型"""
        for config in self.models.values():
            if config.is_default:
                return config

        if self.models:
            return next(iter(self.models.values()))

        return None

    def _estimate_cost(self, config: ModelConfig, prompt_length: int) -> float:
        """估算成本"""
        estimated_tokens = prompt_length / 4
        return (estimated_tokens / 1000) * config.cost_per_1k_tokens

    def _get_reason(
        self,
        model: ModelConfig,
        task_type: TaskType,
        prefer_quality: bool,
        prefer_speed: bool,
    ) -> str:
        """获取选择原因"""
        reasons = []

        if prefer_quality:
            reasons.append(f"优先质量，选择高优先级模型")
        elif prefer_speed:
            reasons.append("优先速度")

        if self.cost_optimization:
            reasons.append("成本优化")

        reasons.append(f"适合 {task_type.value} 任务")

        return "；".join(reasons)

    def _detect_task_type(self, content: str) -> TaskType:
        """检测任务类型"""
        content_lower = content.lower()

        code_keywords = ["def ", "class ", "function", "import ", "code", "implement"]
        if any(kw in content_lower for kw in code_keywords):
            return TaskType.CODE_GENERATION

        doc_keywords = ["document", "文档", "readme", "说明", "guide"]
        if any(kw in content_lower for kw in doc_keywords):
            return TaskType.DOCUMENTATION

        summary_keywords = ["summarize", "总结", "brief", "overview"]
        if any(kw in content_lower for kw in summary_keywords):
            return TaskType.SUMMARIZATION

        return TaskType.REASONING

    def _needs_quality(self, content: str) -> bool:
        """判断是否需要高质量"""
        quality_indicators = [
            "important", "critical", "production",
            "重要", "关键", "生产",
        ]
        return any(ind in content.lower() for ind in quality_indicators)

    def record_usage(
        self,
        model_name: str,
        tokens: int,
        success: bool = True,
    ) -> None:
        """记录使用情况"""
        if model_name in self._usage_stats:
            self._usage_stats[model_name]["calls"] += 1
            self._usage_stats[model_name]["tokens"] += tokens
            if not success:
                self._usage_stats[model_name]["errors"] += 1

    def get_usage_stats(self) -> dict[str, Any]:
        """获取使用统计"""
        return self._usage_stats.copy()

    def get_model_config(self, name: str) -> Optional[ModelConfig]:
        """获取模型配置"""
        return self.models.get(name)

    def list_models(self) -> list[str]:
        """列出所有模型"""
        return list(self.models.keys())

    def get_models_by_capability(self, task_type: TaskType) -> list[str]:
        """获取具有特定能力的模型"""
        return [
            name for name, config in self.models.items()
            if task_type in config.capabilities
        ]
