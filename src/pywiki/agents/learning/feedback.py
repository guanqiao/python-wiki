"""
执行反馈收集器
收集 Agent 执行过程中的反馈信息
"""

import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Optional
from uuid import uuid4


class FeedbackType(str, Enum):
    SUCCESS = "success"
    PARTIAL_SUCCESS = "partial_success"
    FAILURE = "failure"
    ERROR = "error"
    TIMEOUT = "timeout"
    USER_CORRECTION = "user_correction"


class FeedbackSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class ExecutionFeedback:
    id: str = field(default_factory=lambda: str(uuid4()))
    agent_name: str = ""
    task_name: str = ""
    feedback_type: FeedbackType = FeedbackType.SUCCESS
    severity: FeedbackSeverity = FeedbackSeverity.INFO
    score: float = 0.0
    execution_time_ms: float = 0.0
    input_data: dict[str, Any] = field(default_factory=dict)
    output_data: dict[str, Any] = field(default_factory=dict)
    expected_output: Optional[dict[str, Any]] = None
    error_message: Optional[str] = None
    user_comment: Optional[str] = None
    suggestions: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "agent_name": self.agent_name,
            "task_name": self.task_name,
            "feedback_type": self.feedback_type.value,
            "severity": self.severity.value,
            "score": self.score,
            "execution_time_ms": self.execution_time_ms,
            "input_data": self.input_data,
            "output_data": self.output_data,
            "expected_output": self.expected_output,
            "error_message": self.error_message,
            "user_comment": self.user_comment,
            "suggestions": self.suggestions,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
        }

    @property
    def is_success(self) -> bool:
        return self.feedback_type in (FeedbackType.SUCCESS, FeedbackType.PARTIAL_SUCCESS)

    @property
    def needs_improvement(self) -> bool:
        return self.score < 0.7 or self.feedback_type in (
            FeedbackType.FAILURE,
            FeedbackType.ERROR,
            FeedbackType.TIMEOUT,
        )


class FeedbackCollector:
    """
    反馈收集器
    收集和管理 Agent 执行反馈
    """

    def __init__(self, storage_path: Optional[Path] = None):
        self.storage_path = storage_path
        if storage_path:
            self.storage_path.mkdir(parents=True, exist_ok=True)

        self._feedbacks: list[ExecutionFeedback] = []
        self._by_agent: dict[str, list[str]] = {}
        self._by_task: dict[str, list[str]] = {}
        self._stats: dict[str, Any] = {
            "total": 0,
            "success": 0,
            "failure": 0,
            "avg_score": 0.0,
            "avg_time_ms": 0.0,
        }

    def record(
        self,
        agent_name: str,
        task_name: str,
        feedback_type: FeedbackType,
        score: float = 1.0,
        execution_time_ms: float = 0.0,
        input_data: Optional[dict] = None,
        output_data: Optional[dict] = None,
        expected_output: Optional[dict] = None,
        error_message: Optional[str] = None,
        user_comment: Optional[str] = None,
        suggestions: Optional[list[str]] = None,
        metadata: Optional[dict] = None,
    ) -> ExecutionFeedback:
        """
        记录执行反馈

        Args:
            agent_name: Agent 名称
            task_name: 任务名称
            feedback_type: 反馈类型
            score: 评分（0-1）
            execution_time_ms: 执行时间（毫秒）
            input_data: 输入数据
            output_data: 输出数据
            expected_output: 期望输出
            error_message: 错误消息
            user_comment: 用户评论
            suggestions: 改进建议
            metadata: 元数据

        Returns:
            创建的反馈对象
        """
        severity = self._determine_severity(feedback_type, score)

        feedback = ExecutionFeedback(
            agent_name=agent_name,
            task_name=task_name,
            feedback_type=feedback_type,
            severity=severity,
            score=score,
            execution_time_ms=execution_time_ms,
            input_data=input_data or {},
            output_data=output_data or {},
            expected_output=expected_output,
            error_message=error_message,
            user_comment=user_comment,
            suggestions=suggestions or [],
            metadata=metadata or {},
        )

        self._feedbacks.append(feedback)

        if agent_name not in self._by_agent:
            self._by_agent[agent_name] = []
        self._by_agent[agent_name].append(feedback.id)

        task_key = f"{agent_name}:{task_name}"
        if task_key not in self._by_task:
            self._by_task[task_key] = []
        self._by_task[task_key].append(feedback.id)

        self._update_stats(feedback)

        if self.storage_path:
            self._save_feedback(feedback)

        return feedback

    def record_success(
        self,
        agent_name: str,
        task_name: str,
        score: float = 1.0,
        execution_time_ms: float = 0.0,
        **kwargs: Any,
    ) -> ExecutionFeedback:
        """记录成功执行"""
        return self.record(
            agent_name=agent_name,
            task_name=task_name,
            feedback_type=FeedbackType.SUCCESS,
            score=score,
            execution_time_ms=execution_time_ms,
            **kwargs,
        )

    def record_failure(
        self,
        agent_name: str,
        task_name: str,
        error_message: str,
        execution_time_ms: float = 0.0,
        **kwargs: Any,
    ) -> ExecutionFeedback:
        """记录失败执行"""
        return self.record(
            agent_name=agent_name,
            task_name=task_name,
            feedback_type=FeedbackType.FAILURE,
            score=0.0,
            execution_time_ms=execution_time_ms,
            error_message=error_message,
            **kwargs,
        )

    def record_user_correction(
        self,
        agent_name: str,
        task_name: str,
        original_output: dict,
        corrected_output: dict,
        user_comment: Optional[str] = None,
        **kwargs: Any,
    ) -> ExecutionFeedback:
        """记录用户修正"""
        return self.record(
            agent_name=agent_name,
            task_name=task_name,
            feedback_type=FeedbackType.USER_CORRECTION,
            score=0.5,
            output_data=original_output,
            expected_output=corrected_output,
            user_comment=user_comment,
            **kwargs,
        )

    def get_feedback(self, feedback_id: str) -> Optional[ExecutionFeedback]:
        """获取反馈"""
        for feedback in self._feedbacks:
            if feedback.id == feedback_id:
                return feedback
        return None

    def get_agent_feedback(self, agent_name: str) -> list[ExecutionFeedback]:
        """获取 Agent 的所有反馈"""
        ids = self._by_agent.get(agent_name, [])
        return [f for f in self._feedbacks if f.id in ids]

    def get_task_feedback(self, agent_name: str, task_name: str) -> list[ExecutionFeedback]:
        """获取特定任务的反馈"""
        task_key = f"{agent_name}:{task_name}"
        ids = self._by_task.get(task_key, [])
        return [f for f in self._feedbacks if f.id in ids]

    def get_recent_feedback(self, limit: int = 100) -> list[ExecutionFeedback]:
        """获取最近的反馈"""
        return sorted(self._feedbacks, key=lambda x: x.created_at, reverse=True)[:limit]

    def get_failures(self, limit: int = 50) -> list[ExecutionFeedback]:
        """获取失败的反馈"""
        failures = [f for f in self._feedbacks if not f.is_success]
        return sorted(failures, key=lambda x: x.created_at, reverse=True)[:limit]

    def get_needs_improvement(self) -> list[ExecutionFeedback]:
        """获取需要改进的反馈"""
        return [f for f in self._feedbacks if f.needs_improvement]

    def get_agent_stats(self, agent_name: str) -> dict[str, Any]:
        """获取 Agent 统计"""
        feedbacks = self.get_agent_feedback(agent_name)
        if not feedbacks:
            return {"total": 0}

        success_count = sum(1 for f in feedbacks if f.is_success)
        total_time = sum(f.execution_time_ms for f in feedbacks)
        total_score = sum(f.score for f in feedbacks)

        return {
            "total": len(feedbacks),
            "success_count": success_count,
            "failure_count": len(feedbacks) - success_count,
            "success_rate": success_count / len(feedbacks),
            "avg_score": total_score / len(feedbacks),
            "avg_time_ms": total_time / len(feedbacks),
        }

    def get_task_stats(self, agent_name: str, task_name: str) -> dict[str, Any]:
        """获取任务统计"""
        feedbacks = self.get_task_feedback(agent_name, task_name)
        if not feedbacks:
            return {"total": 0}

        return {
            "total": len(feedbacks),
            "avg_score": sum(f.score for f in feedbacks) / len(feedbacks),
            "avg_time_ms": sum(f.execution_time_ms for f in feedbacks) / len(feedbacks),
            "improvement_needed": sum(1 for f in feedbacks if f.needs_improvement),
        }

    def _determine_severity(
        self,
        feedback_type: FeedbackType,
        score: float,
    ) -> FeedbackSeverity:
        """确定严重程度"""
        if feedback_type == FeedbackType.SUCCESS and score >= 0.9:
            return FeedbackSeverity.INFO
        elif feedback_type in (FeedbackType.FAILURE, FeedbackType.ERROR):
            return FeedbackSeverity.ERROR
        elif feedback_type == FeedbackType.TIMEOUT:
            return FeedbackSeverity.WARNING
        elif score < 0.5:
            return FeedbackSeverity.CRITICAL
        else:
            return FeedbackSeverity.WARNING

    def _update_stats(self, feedback: ExecutionFeedback) -> None:
        """更新统计"""
        self._stats["total"] += 1

        if feedback.is_success:
            self._stats["success"] += 1
        else:
            self._stats["failure"] += 1

        total = self._stats["total"]
        old_avg_score = self._stats["avg_score"]
        old_avg_time = self._stats["avg_time_ms"]

        self._stats["avg_score"] = (old_avg_score * (total - 1) + feedback.score) / total
        self._stats["avg_time_ms"] = (old_avg_time * (total - 1) + feedback.execution_time_ms) / total

    def _save_feedback(self, feedback: ExecutionFeedback) -> None:
        """保存反馈到文件"""
        if not self.storage_path:
            return

        file_path = self.storage_path / f"{feedback.id}.json"
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(feedback.to_dict(), f, ensure_ascii=False, indent=2)

    def export_feedbacks(self) -> list[dict[str, Any]]:
        """导出所有反馈"""
        return [f.to_dict() for f in self._feedbacks]

    def clear(self) -> None:
        """清空反馈"""
        self._feedbacks.clear()
        self._by_agent.clear()
        self._by_task.clear()
        self._stats = {
            "total": 0,
            "success": 0,
            "failure": 0,
            "avg_score": 0.0,
            "avg_time_ms": 0.0,
        }

    @property
    def stats(self) -> dict[str, Any]:
        return self._stats.copy()
