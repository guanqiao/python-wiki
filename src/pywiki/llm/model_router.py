"""
模型分级选择器
对标 Qoder 的模型分级功能
支持 Lite/Efficient/Performance/Auto 四级模型选择
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class ModelTier(str, Enum):
    """模型等级"""
    LITE = "lite"               # 轻量级 - 快速响应
    EFFICIENT = "efficient"     # 经济高效 - 平衡方案
    PERFORMANCE = "performance" # 极致性能 - 深度理解
    AUTO = "auto"               # 智能路由 - 自动选择


class TaskType(str, Enum):
    """任务类型"""
    CODE_COMPLETION = "code_completion"     # 代码补全
    DOC_GENERATION = "doc_generation"       # 文档生成
    CODE_REVIEW = "code_review"             # 代码审查
    ARCHITECTURE_ANALYSIS = "architecture_analysis"  # 架构分析
    QUEST_MODE = "quest_mode"               # Quest 模式


@dataclass
class ModelConfig:
    """模型配置"""
    name: str
    tier: ModelTier
    max_tokens: int
    cost_per_1k_tokens: float
    avg_response_time_ms: int
    context_window: int
    supports_streaming: bool = True


@dataclass
class TaskComplexity:
    """任务复杂度评估"""
    code_size: int = 0          # 代码规模（行数）
    file_count: int = 0         # 文件数量
    dependency_depth: int = 0   # 依赖深度
    reasoning_required: bool = False  # 是否需要推理
    creativity_required: bool = False  # 是否需要创造性


class ModelRegistry:
    """模型注册表"""

    # 预定义的模型配置
    MODELS = {
        # Lite 级别
        "gpt-3.5-turbo": ModelConfig(
            name="gpt-3.5-turbo",
            tier=ModelTier.LITE,
            max_tokens=4096,
            cost_per_1k_tokens=0.0015,
            avg_response_time_ms=500,
            context_window=16385,
        ),
        "claude-instant-1": ModelConfig(
            name="claude-instant-1",
            tier=ModelTier.LITE,
            max_tokens=4096,
            cost_per_1k_tokens=0.0016,
            avg_response_time_ms=400,
            context_window=100000,
        ),
        # Efficient 级别
        "gpt-4": ModelConfig(
            name="gpt-4",
            tier=ModelTier.EFFICIENT,
            max_tokens=8192,
            cost_per_1k_tokens=0.03,
            avg_response_time_ms=1500,
            context_window=8192,
        ),
        "claude-3-sonnet": ModelConfig(
            name="claude-3-sonnet",
            tier=ModelTier.EFFICIENT,
            max_tokens=4096,
            cost_per_1k_tokens=0.003,
            avg_response_time_ms=800,
            context_window=200000,
        ),
        # Performance 级别
        "gpt-4-turbo": ModelConfig(
            name="gpt-4-turbo",
            tier=ModelTier.PERFORMANCE,
            max_tokens=4096,
            cost_per_1k_tokens=0.01,
            avg_response_time_ms=2000,
            context_window=128000,
        ),
        "claude-3-opus": ModelConfig(
            name="claude-3-opus",
            tier=ModelTier.PERFORMANCE,
            max_tokens=4096,
            cost_per_1k_tokens=0.015,
            avg_response_time_ms=2500,
            context_window=200000,
        ),
    }

    @classmethod
    def get_models_by_tier(cls, tier: ModelTier) -> list[ModelConfig]:
        """获取指定等级的所有模型"""
        return [m for m in cls.MODELS.values() if m.tier == tier]

    @classmethod
    def get_model(cls, name: str) -> Optional[ModelConfig]:
        """获取模型配置"""
        return cls.MODELS.get(name)


class ModelRouter:
    """
    模型路由器
    
    根据任务类型和复杂度自动选择最适合的模型
    对标 Qoder 的智能路由功能
    """

    # 任务类型默认等级映射
    TASK_TIER_MAPPING = {
        TaskType.CODE_COMPLETION: ModelTier.LITE,
        TaskType.DOC_GENERATION: ModelTier.EFFICIENT,
        TaskType.CODE_REVIEW: ModelTier.EFFICIENT,
        TaskType.ARCHITECTURE_ANALYSIS: ModelTier.PERFORMANCE,
        TaskType.QUEST_MODE: ModelTier.PERFORMANCE,
    }

    # 复杂度阈值
    COMPLEXITY_THRESHOLDS = {
        "small": {"lines": 100, "files": 5},
        "medium": {"lines": 1000, "files": 20},
        "large": {"lines": 10000, "files": 100},
    }

    def __init__(self, default_tier: ModelTier = ModelTier.AUTO):
        self.default_tier = default_tier
        self.usage_stats = {}  # 模型使用统计

    def select_model(
        self,
        task_type: TaskType,
        complexity: Optional[TaskComplexity] = None,
        tier: Optional[ModelTier] = None,
        preferred_provider: Optional[str] = None,
    ) -> str:
        """
        选择最适合的模型
        
        Args:
            task_type: 任务类型
            complexity: 任务复杂度
            tier: 指定模型等级（如果为 AUTO 或 None 则自动选择）
            preferred_provider: 优先的提供商（openai/anthropic）
            
        Returns:
            选中的模型名称
        """
        # 确定模型等级
        selected_tier = self._determine_tier(task_type, complexity, tier)
        
        # 获取该等级的所有模型
        candidates = ModelRegistry.get_models_by_tier(selected_tier)
        
        if not candidates:
            # 回退到 Efficient 级别
            candidates = ModelRegistry.get_models_by_tier(ModelTier.EFFICIENT)
        
        # 根据偏好提供商筛选
        if preferred_provider:
            filtered = [m for m in candidates if preferred_provider in m.name]
            if filtered:
                candidates = filtered
        
        # 选择响应时间最短的模型
        selected = min(candidates, key=lambda m: m.avg_response_time_ms)
        
        # 记录使用统计
        self._record_usage(selected.name, task_type)
        
        return selected.name

    def _determine_tier(
        self,
        task_type: TaskType,
        complexity: Optional[TaskComplexity],
        tier: Optional[ModelTier],
    ) -> ModelTier:
        """确定模型等级"""
        # 如果指定了具体等级（非 AUTO），直接使用
        if tier and tier != ModelTier.AUTO:
            return tier
        
        # 根据任务类型获取默认等级
        base_tier = self.TASK_TIER_MAPPING.get(task_type, ModelTier.EFFICIENT)
        
        # 根据复杂度调整
        if complexity:
            adjusted_tier = self._adjust_tier_by_complexity(base_tier, complexity)
            return adjusted_tier
        
        return base_tier

    def _adjust_tier_by_complexity(
        self,
        base_tier: ModelTier,
        complexity: TaskComplexity,
    ) -> ModelTier:
        """根据复杂度调整等级"""
        # 计算复杂度分数
        score = 0
        
        if complexity.code_size > self.COMPLEXITY_THRESHOLDS["large"]["lines"]:
            score += 3
        elif complexity.code_size > self.COMPLEXITY_THRESHOLDS["medium"]["lines"]:
            score += 2
        elif complexity.code_size > self.COMPLEXITY_THRESHOLDS["small"]["lines"]:
            score += 1
        
        if complexity.file_count > self.COMPLEXITY_THRESHOLDS["large"]["files"]:
            score += 3
        elif complexity.file_count > self.COMPLEXITY_THRESHOLDS["medium"]["files"]:
            score += 2
        elif complexity.file_count > self.COMPLEXITY_THRESHOLDS["small"]["files"]:
            score += 1
        
        if complexity.dependency_depth > 3:
            score += 2
        
        if complexity.reasoning_required:
            score += 2
        
        if complexity.creativity_required:
            score += 1
        
        # 根据分数调整等级
        tier_levels = [ModelTier.LITE, ModelTier.EFFICIENT, ModelTier.PERFORMANCE]
        base_index = tier_levels.index(base_tier)
        
        # 分数越高，等级越高
        if score >= 6 and base_index < 2:
            return tier_levels[min(base_index + 2, 2)]
        elif score >= 3 and base_index < 2:
            return tier_levels[min(base_index + 1, 2)]
        
        return base_tier

    def _record_usage(self, model_name: str, task_type: TaskType):
        """记录模型使用统计"""
        key = f"{model_name}:{task_type.value}"
        self.usage_stats[key] = self.usage_stats.get(key, 0) + 1

    def get_usage_stats(self) -> dict[str, int]:
        """获取使用统计"""
        return self.usage_stats.copy()

    def estimate_cost(
        self,
        model_name: str,
        input_tokens: int,
        output_tokens: int,
    ) -> float:
        """
        估算调用成本
        
        Args:
            model_name: 模型名称
            input_tokens: 输入 token 数
            output_tokens: 输出 token 数
            
        Returns:
            预估成本（美元）
        """
        model = ModelRegistry.get_model(model_name)
        if not model:
            return 0.0
        
        # 大多数模型输入输出同价，这里简化计算
        total_tokens = input_tokens + output_tokens
        cost = (total_tokens / 1000) * model.cost_per_1k_tokens
        
        return round(cost, 4)

    def get_model_info(self, model_name: str) -> Optional[dict]:
        """获取模型信息"""
        model = ModelRegistry.get_model(model_name)
        if not model:
            return None
        
        return {
            "name": model.name,
            "tier": model.tier.value,
            "max_tokens": model.max_tokens,
            "cost_per_1k_tokens": model.cost_per_1k_tokens,
            "avg_response_time_ms": model.avg_response_time_ms,
            "context_window": model.context_window,
            "supports_streaming": model.supports_streaming,
        }


class ContextCompressor:
    """
    上下文压缩器
    
    智能压缩上下文，减少 Token 消耗
    对标 Qoder 的上下文智能压缩功能
    """

    def __init__(self, max_tokens: int = 4000):
        self.max_tokens = max_tokens
        # 平均每个 token 约 4 个字符（英文）
        self.chars_per_token = 4

    def compress(self, context: str, strategy: str = "smart") -> str:
        """
        压缩上下文
        
        Args:
            context: 原始上下文
            strategy: 压缩策略（smart/remove_comments/summarize）
            
        Returns:
            压缩后的上下文
        """
        estimated_tokens = len(context) / self.chars_per_token
        
        if estimated_tokens <= self.max_tokens:
            return context
        
        if strategy == "smart":
            return self._smart_compress(context)
        elif strategy == "remove_comments":
            return self._remove_comments(context)
        elif strategy == "summarize":
            return self._summarize(context)
        else:
            return self._truncate(context)

    def _smart_compress(self, context: str) -> str:
        """智能压缩 - 保留关键信息"""
        lines = context.split("\n")
        
        # 保留的关键模式
        important_patterns = [
            "def ",
            "class ",
            "import ",
            "from ",
            '@',
            '"""',
            "'''",
        ]
        
        compressed_lines = []
        for line in lines:
            # 保留重要行
            if any(pattern in line for pattern in important_patterns):
                compressed_lines.append(line)
            # 跳过空白行和纯注释
            elif line.strip() and not line.strip().startswith("#"):
                compressed_lines.append(line)
        
        result = "\n".join(compressed_lines)
        
        # 如果还是太长，截断
        if len(result) / self.chars_per_token > self.max_tokens:
            return self._truncate(result)
        
        return result

    def _remove_comments(self, context: str) -> str:
        """移除注释"""
        import re
        
        # 移除单行注释
        context = re.sub(r'#.*$', '', context, flags=re.MULTILINE)
        # 移除多行注释（简化版）
        context = re.sub(r'"""[\s\S]*?"""', '', context)
        context = re.sub(r"'''[\s\S]*?'''", '', context)
        
        return context.strip()

    def _summarize(self, context: str) -> str:
        """生成摘要（简化版）"""
        lines = context.split("\n")
        
        # 提取关键信息
        summary_lines = []
        
        # 添加文件头信息
        if lines:
            summary_lines.append(lines[0])
        
        # 提取类和方法定义
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("class ") or stripped.startswith("def "):
                summary_lines.append(line)
        
        return "\n".join(summary_lines) if summary_lines else self._truncate(context)

    def _truncate(self, context: str) -> str:
        """简单截断"""
        max_chars = int(self.max_tokens * self.chars_per_token)
        
        if len(context) <= max_chars:
            return context
        
        # 保留开头和结尾，中间用省略号
        head_len = max_chars // 2
        tail_len = max_chars // 2 - 100  # 为省略号预留空间
        
        return context[:head_len] + "\n... [内容已截断] ...\n" + context[-tail_len:]
