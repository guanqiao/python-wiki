"""
进度监控
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Optional


class Stage(str, Enum):
    IDLE = "idle"
    SCANNING = "scanning"
    PARSING = "parsing"
    ANALYZING = "analyzing"
    GENERATING = "generating"
    SYNCING = "syncing"
    COMPLETED = "completed"
    ERROR = "error"


@dataclass
class ProgressInfo:
    stage: Stage = Stage.IDLE
    total: int = 0
    current: int = 0
    message: str = ""
    current_item: str = ""
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


class ProgressMonitor:
    """进度监控器"""

    def __init__(
        self,
        callback: Optional[Callable[[ProgressInfo], None]] = None,
    ):
        self.callback = callback
        self._progress = ProgressInfo()

    def start(self, total: int = 0, message: str = "") -> None:
        """开始进度"""
        self._progress = ProgressInfo(
            stage=Stage.SCANNING,
            total=total,
            message=message,
            start_time=datetime.now(),
        )
        self._notify()

    def set_stage(self, stage: Stage, message: str = "") -> None:
        """设置当前阶段"""
        self._progress.stage = stage
        self._progress.message = message
        self._notify()

    def update(
        self,
        current: Optional[int] = None,
        message: Optional[str] = None,
        current_item: Optional[str] = None,
    ) -> None:
        """更新进度"""
        if current is not None:
            self._progress.current = current
        if message is not None:
            self._progress.message = message
        if current_item is not None:
            self._progress.current_item = current_item
        self._notify()

    def increment(self, message: Optional[str] = None) -> None:
        """增加进度"""
        self._progress.current += 1
        if message:
            self._progress.message = message
        self._notify()

    def add_error(self, error: str) -> None:
        """添加错误"""
        self._progress.errors.append(error)
        self._notify()

    def add_warning(self, warning: str) -> None:
        """添加警告"""
        self._progress.warnings.append(warning)
        self._notify()

    def complete(self, message: str = "完成") -> None:
        """完成进度"""
        self._progress.stage = Stage.COMPLETED
        self._progress.message = message
        self._progress.end_time = datetime.now()
        self._progress.current = self._progress.total
        self._notify()

    def error(self, error: str) -> None:
        """错误状态"""
        self._progress.stage = Stage.ERROR
        self._progress.errors.append(error)
        self._progress.end_time = datetime.now()
        self._notify()

    def get_progress(self) -> ProgressInfo:
        """获取当前进度"""
        return self._progress

    def get_percentage(self) -> float:
        """获取进度百分比"""
        if self._progress.total == 0:
            return 0.0
        return (self._progress.current / self._progress.total) * 100

    def get_elapsed_time(self) -> float:
        """获取已用时间（秒）"""
        if self._progress.start_time is None:
            return 0.0
        end = self._progress.end_time or datetime.now()
        return (end - self._progress.start_time).total_seconds()

    def get_estimated_remaining(self) -> float:
        """获取预估剩余时间（秒）"""
        if self._progress.current == 0:
            return 0.0

        elapsed = self.get_elapsed_time()
        rate = self._progress.current / elapsed
        remaining = self._progress.total - self._progress.current

        if rate > 0:
            return remaining / rate
        return 0.0

    def _notify(self) -> None:
        if self.callback:
            self.callback(self._progress)

    def reset(self) -> None:
        """重置进度"""
        self._progress = ProgressInfo()
