"""
架构演进追踪器
跟踪架构变更历史
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Optional
import json


class ChangeType(str, Enum):
    MODULE_ADDED = "module_added"
    MODULE_REMOVED = "module_removed"
    CLASS_ADDED = "class_added"
    CLASS_REMOVED = "class_removed"
    FUNCTION_ADDED = "function_added"
    FUNCTION_REMOVED = "function_removed"
    DEPENDENCY_ADDED = "dependency_added"
    DEPENDENCY_REMOVED = "dependency_removed"
    PATTERN_INTRODUCED = "pattern_introduced"
    PATTERN_REMOVED = "pattern_removed"
    ARCHITECTURE_CHANGED = "architecture_changed"


@dataclass
class ArchitectureSnapshot:
    timestamp: datetime
    version: str
    modules: list[str] = field(default_factory=list)
    classes: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)
    patterns: list[str] = field(default_factory=list)
    metrics: dict = field(default_factory=dict)


@dataclass
class ArchitectureChange:
    change_type: ChangeType
    timestamp: datetime
    description: str
    affected_items: list[str] = field(default_factory=list)
    impact: str = "medium"
    details: dict = field(default_factory=dict)


class ArchitectureEvolutionTracker:
    """架构演进追踪器"""

    def __init__(self, project_path: Path):
        self.project_path = project_path
        self.history_dir = project_path / ".pywiki" / "architecture_history"
        self.history_dir.mkdir(parents=True, exist_ok=True)
        self.history_file = self.history_dir / "evolution.json"
        self._history: list[ArchitectureSnapshot] = []
        self._changes: list[ArchitectureChange] = []
        self._load_history()

    def _load_history(self) -> None:
        """加载历史记录"""
        if self.history_file.exists():
            with open(self.history_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            for snapshot_data in data.get("snapshots", []):
                snapshot = ArchitectureSnapshot(
                    timestamp=datetime.fromisoformat(snapshot_data["timestamp"]),
                    version=snapshot_data["version"],
                    modules=snapshot_data.get("modules", []),
                    classes=snapshot_data.get("classes", []),
                    dependencies=snapshot_data.get("dependencies", []),
                    patterns=snapshot_data.get("patterns", []),
                    metrics=snapshot_data.get("metrics", {}),
                )
                self._history.append(snapshot)

    def _save_history(self) -> None:
        """保存历史记录"""
        data = {
            "snapshots": [
                {
                    "timestamp": s.timestamp.isoformat(),
                    "version": s.version,
                    "modules": s.modules,
                    "classes": s.classes,
                    "dependencies": s.dependencies,
                    "patterns": s.patterns,
                    "metrics": s.metrics,
                }
                for s in self._history
            ],
            "changes": [
                {
                    "change_type": c.change_type.value,
                    "timestamp": c.timestamp.isoformat(),
                    "description": c.description,
                    "affected_items": c.affected_items,
                    "impact": c.impact,
                    "details": c.details,
                }
                for c in self._changes
            ],
        }

        with open(self.history_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def record_snapshot(
        self,
        version: str,
        modules: list[str],
        classes: list[str],
        dependencies: list[str],
        patterns: list[str],
        metrics: Optional[dict] = None,
    ) -> ArchitectureSnapshot:
        """记录架构快照"""
        snapshot = ArchitectureSnapshot(
            timestamp=datetime.now(),
            version=version,
            modules=modules,
            classes=classes,
            dependencies=dependencies,
            patterns=patterns,
            metrics=metrics or {},
        )

        if self._history:
            changes = self._compare_snapshots(self._history[-1], snapshot)
            self._changes.extend(changes)

        self._history.append(snapshot)
        self._save_history()

        return snapshot

    def _compare_snapshots(
        self,
        old: ArchitectureSnapshot,
        new: ArchitectureSnapshot
    ) -> list[ArchitectureChange]:
        """比较两个快照的差异"""
        changes = []

        old_modules = set(old.modules)
        new_modules = set(new.modules)

        for module in new_modules - old_modules:
            changes.append(ArchitectureChange(
                change_type=ChangeType.MODULE_ADDED,
                timestamp=new.timestamp,
                description=f"新增模块: {module}",
                affected_items=[module],
                impact="medium",
            ))

        for module in old_modules - new_modules:
            changes.append(ArchitectureChange(
                change_type=ChangeType.MODULE_REMOVED,
                timestamp=new.timestamp,
                description=f"移除模块: {module}",
                affected_items=[module],
                impact="high",
            ))

        old_classes = set(old.classes)
        new_classes = set(new.classes)

        for cls in new_classes - old_classes:
            changes.append(ArchitectureChange(
                change_type=ChangeType.CLASS_ADDED,
                timestamp=new.timestamp,
                description=f"新增类: {cls}",
                affected_items=[cls],
                impact="low",
            ))

        for cls in old_classes - new_classes:
            changes.append(ArchitectureChange(
                change_type=ChangeType.CLASS_REMOVED,
                timestamp=new.timestamp,
                description=f"移除类: {cls}",
                affected_items=[cls],
                impact="medium",
            ))

        old_deps = set(old.dependencies)
        new_deps = set(new.dependencies)

        for dep in new_deps - old_deps:
            changes.append(ArchitectureChange(
                change_type=ChangeType.DEPENDENCY_ADDED,
                timestamp=new.timestamp,
                description=f"新增依赖: {dep}",
                affected_items=[dep],
                impact="medium",
            ))

        for dep in old_deps - new_deps:
            changes.append(ArchitectureChange(
                change_type=ChangeType.DEPENDENCY_REMOVED,
                timestamp=new.timestamp,
                description=f"移除依赖: {dep}",
                affected_items=[dep],
                impact="medium",
            ))

        old_patterns = set(old.patterns)
        new_patterns = set(new.patterns)

        for pattern in new_patterns - old_patterns:
            changes.append(ArchitectureChange(
                change_type=ChangeType.PATTERN_INTRODUCED,
                timestamp=new.timestamp,
                description=f"引入设计模式: {pattern}",
                affected_items=[pattern],
                impact="medium",
            ))

        for pattern in old_patterns - new_patterns:
            changes.append(ArchitectureChange(
                change_type=ChangeType.PATTERN_REMOVED,
                timestamp=new.timestamp,
                description=f"移除设计模式: {pattern}",
                affected_items=[pattern],
                impact="medium",
            ))

        return changes

    def get_evolution_timeline(self) -> list[dict]:
        """获取演进时间线"""
        timeline = []

        for snapshot in self._history:
            timeline.append({
                "timestamp": snapshot.timestamp.isoformat(),
                "version": snapshot.version,
                "module_count": len(snapshot.modules),
                "class_count": len(snapshot.classes),
                "dependency_count": len(snapshot.dependencies),
                "pattern_count": len(snapshot.patterns),
            })

        return timeline

    def get_changes_in_period(
        self,
        start: datetime,
        end: datetime
    ) -> list[ArchitectureChange]:
        """获取指定时间段内的变更"""
        return [
            change for change in self._changes
            if start <= change.timestamp <= end
        ]

    def get_growth_metrics(self) -> dict:
        """获取增长指标"""
        if len(self._history) < 2:
            return {}

        first = self._history[0]
        last = self._history[-1]

        return {
            "module_growth": len(last.modules) - len(first.modules),
            "class_growth": len(last.classes) - len(first.classes),
            "dependency_growth": len(last.dependencies) - len(first.dependencies),
            "pattern_growth": len(last.patterns) - len(first.patterns),
            "time_span_days": (last.timestamp - first.timestamp).days,
        }

    def generate_evolution_report(self) -> dict:
        """生成演进报告"""
        return {
            "timeline": self.get_evolution_timeline(),
            "total_snapshots": len(self._history),
            "total_changes": len(self._changes),
            "growth_metrics": self.get_growth_metrics(),
            "recent_changes": [
                {
                    "type": c.change_type.value,
                    "description": c.description,
                    "timestamp": c.timestamp.isoformat(),
                    "impact": c.impact,
                }
                for c in self._changes[-10:]
            ],
        }
