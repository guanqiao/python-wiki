"""
策略优化器
基于执行反馈优化 Agent 策略
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional
from uuid import uuid4

from pywiki.agents.learning.feedback import (
    FeedbackCollector,
    ExecutionFeedback,
    FeedbackType,
)


@dataclass
class OptimizationSuggestion:
    id: str = field(default_factory=lambda: str(uuid4()))
    agent_name: str = ""
    task_name: str = ""
    suggestion_type: str = ""
    description: str = ""
    priority: int = 0
    impact: str = ""
    implementation: str = ""
    confidence: float = 0.0
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "agent_name": self.agent_name,
            "task_name": self.task_name,
            "suggestion_type": self.suggestion_type,
            "description": self.description,
            "priority": self.priority,
            "impact": self.impact,
            "implementation": self.implementation,
            "confidence": self.confidence,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class AgentProfile:
    agent_name: str
    total_executions: int = 0
    success_rate: float = 0.0
    avg_score: float = 0.0
    avg_time_ms: float = 0.0
    common_errors: list[str] = field(default_factory=list)
    improvement_areas: list[str] = field(default_factory=list)
    strengths: list[str] = field(default_factory=list)
    last_updated: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict[str, Any]:
        return {
            "agent_name": self.agent_name,
            "total_executions": self.total_executions,
            "success_rate": self.success_rate,
            "avg_score": self.avg_score,
            "avg_time_ms": self.avg_time_ms,
            "common_errors": self.common_errors,
            "improvement_areas": self.improvement_areas,
            "strengths": self.strengths,
            "last_updated": self.last_updated.isoformat(),
        }


class StrategyOptimizer:
    """
    策略优化器
    分析执行反馈，生成优化建议
    """

    def __init__(self, feedback_collector: FeedbackCollector):
        self._collector = feedback_collector
        self._profiles: dict[str, AgentProfile] = {}
        self._suggestions: list[OptimizationSuggestion] = []

    def analyze(self) -> list[OptimizationSuggestion]:
        """
        分析反馈并生成优化建议

        Returns:
            优化建议列表
        """
        self._suggestions.clear()

        for agent_name in self._collector._by_agent.keys():
            self._update_profile(agent_name)
            suggestions = self._generate_suggestions(agent_name)
            self._suggestions.extend(suggestions)

        self._suggestions.sort(key=lambda x: (x.priority, x.confidence), reverse=True)

        return self._suggestions

    def _update_profile(self, agent_name: str) -> AgentProfile:
        """更新 Agent 配置"""
        feedbacks = self._collector.get_agent_feedback(agent_name)

        if not feedbacks:
            return AgentProfile(agent_name=agent_name)

        success_count = sum(1 for f in feedbacks if f.is_success)
        total_score = sum(f.score for f in feedbacks)
        total_time = sum(f.execution_time_ms for f in feedbacks)

        error_counts: dict[str, int] = {}
        for f in feedbacks:
            if f.error_message:
                error_key = f.error_message[:50]
                error_counts[error_key] = error_counts.get(error_key, 0) + 1

        common_errors = sorted(error_counts.keys(), key=lambda x: error_counts[x], reverse=True)[:5]

        improvement_areas = []
        strengths = []

        task_stats: dict[str, list[float]] = {}
        for f in feedbacks:
            if f.task_name not in task_stats:
                task_stats[f.task_name] = []
            task_stats[f.task_name].append(f.score)

        for task_name, scores in task_stats.items():
            avg_score = sum(scores) / len(scores)
            if avg_score < 0.7:
                improvement_areas.append(task_name)
            elif avg_score >= 0.9:
                strengths.append(task_name)

        profile = AgentProfile(
            agent_name=agent_name,
            total_executions=len(feedbacks),
            success_rate=success_count / len(feedbacks),
            avg_score=total_score / len(feedbacks),
            avg_time_ms=total_time / len(feedbacks),
            common_errors=common_errors,
            improvement_areas=improvement_areas,
            strengths=strengths,
            last_updated=datetime.now(),
        )

        self._profiles[agent_name] = profile
        return profile

    def _generate_suggestions(self, agent_name: str) -> list[OptimizationSuggestion]:
        """生成优化建议"""
        suggestions = []
        profile = self._profiles.get(agent_name)

        if not profile:
            return suggestions

        if profile.success_rate < 0.7:
            suggestions.append(OptimizationSuggestion(
                agent_name=agent_name,
                task_name="*",
                suggestion_type="reliability",
                description=f"Agent 成功率较低 ({profile.success_rate:.1%})，需要提高可靠性",
                priority=10,
                impact="提高整体执行成功率",
                implementation="检查常见错误并添加错误处理逻辑",
                confidence=0.9,
            ))

        if profile.avg_time_ms > 5000:
            suggestions.append(OptimizationSuggestion(
                agent_name=agent_name,
                task_name="*",
                suggestion_type="performance",
                description=f"Agent 平均执行时间较长 ({profile.avg_time_ms:.0f}ms)，可能需要优化",
                priority=7,
                impact="提高执行效率",
                implementation="分析耗时操作，考虑并行化或缓存",
                confidence=0.8,
            ))

        for error in profile.common_errors[:3]:
            suggestions.append(OptimizationSuggestion(
                agent_name=agent_name,
                task_name="*",
                suggestion_type="error_handling",
                description=f"常见错误: {error}",
                priority=8,
                impact="减少错误发生",
                implementation="添加针对此错误的预防和处理逻辑",
                confidence=0.85,
            ))

        for area in profile.improvement_areas[:3]:
            task_feedbacks = self._collector.get_task_feedback(agent_name, area)
            if task_feedbacks:
                failures = [f for f in task_feedbacks if not f.is_success]
                if failures:
                    suggestions.append(OptimizationSuggestion(
                        agent_name=agent_name,
                        task_name=area,
                        suggestion_type="task_improvement",
                        description=f"任务 '{area}' 需要改进，失败率较高",
                        priority=9,
                        impact="提高特定任务的成功率",
                        implementation=f"分析 {len(failures)} 次失败案例，找出共同问题",
                        confidence=0.85,
                    ))

        return suggestions

    def get_profile(self, agent_name: str) -> Optional[AgentProfile]:
        """获取 Agent 配置"""
        return self._profiles.get(agent_name)

    def get_suggestions(
        self,
        agent_name: Optional[str] = None,
        suggestion_type: Optional[str] = None,
        min_priority: int = 0,
    ) -> list[OptimizationSuggestion]:
        """
        获取优化建议

        Args:
            agent_name: 过滤 Agent 名称
            suggestion_type: 过滤建议类型
            min_priority: 最小优先级

        Returns:
            过滤后的建议列表
        """
        result = self._suggestions

        if agent_name:
            result = [s for s in result if s.agent_name == agent_name]

        if suggestion_type:
            result = [s for s in result if s.suggestion_type == suggestion_type]

        result = [s for s in result if s.priority >= min_priority]

        return result

    def get_high_priority_suggestions(self, limit: int = 10) -> list[OptimizationSuggestion]:
        """获取高优先级建议"""
        return sorted(self._suggestions, key=lambda x: x.priority, reverse=True)[:limit]

    def apply_suggestion(self, suggestion_id: str) -> bool:
        """
        应用建议（标记为已处理）

        Args:
            suggestion_id: 建议ID

        Returns:
            是否成功
        """
        for i, s in enumerate(self._suggestions):
            if s.id == suggestion_id:
                self._suggestions.pop(i)
                return True
        return False

    def generate_report(self) -> dict[str, Any]:
        """生成优化报告"""
        return {
            "generated_at": datetime.now().isoformat(),
            "total_suggestions": len(self._suggestions),
            "by_priority": self._count_by_priority(),
            "by_type": self._count_by_type(),
            "by_agent": self._count_by_agent(),
            "profiles": {
                name: profile.to_dict()
                for name, profile in self._profiles.items()
            },
            "top_suggestions": [s.to_dict() for s in self.get_high_priority_suggestions(5)],
        }

    def _count_by_priority(self) -> dict[str, int]:
        """按优先级统计"""
        counts: dict[str, int] = {}
        for s in self._suggestions:
            key = f"priority_{s.priority}"
            counts[key] = counts.get(key, 0) + 1
        return counts

    def _count_by_type(self) -> dict[str, int]:
        """按类型统计"""
        counts: dict[str, int] = {}
        for s in self._suggestions:
            counts[s.suggestion_type] = counts.get(s.suggestion_type, 0) + 1
        return counts

    def _count_by_agent(self) -> dict[str, int]:
        """按 Agent 统计"""
        counts: dict[str, int] = {}
        for s in self._suggestions:
            counts[s.agent_name] = counts.get(s.agent_name, 0) + 1
        return counts

    def clear(self) -> None:
        """清空优化器状态"""
        self._profiles.clear()
        self._suggestions.clear()
