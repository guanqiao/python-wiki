"""
性能指标收集器
"""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional
import json


@dataclass
class MetricRecord:
    timestamp: datetime
    name: str
    value: float
    unit: str = ""
    tags: dict[str, str] = field(default_factory=dict)


@dataclass
class GenerationMetrics:
    project_name: str
    start_time: datetime
    end_time: Optional[datetime] = None
    total_files: int = 0
    processed_files: int = 0
    failed_files: int = 0
    total_classes: int = 0
    total_functions: int = 0
    total_modules: int = 0
    diagrams_generated: int = 0
    llm_calls: int = 0
    llm_tokens_used: int = 0
    errors: list[str] = field(default_factory=list)


class MetricsCollector:
    """性能指标收集器"""

    def __init__(self, metrics_dir: Optional[Path] = None):
        self.metrics_dir = metrics_dir
        if metrics_dir:
            metrics_dir.mkdir(parents=True, exist_ok=True)

        self._metrics: list[MetricRecord] = []
        self._generation_metrics: Optional[GenerationMetrics] = None

    def start_generation(self, project_name: str) -> None:
        """开始生成指标收集"""
        self._generation_metrics = GenerationMetrics(
            project_name=project_name,
            start_time=datetime.now(),
        )

    def record_metric(
        self,
        name: str,
        value: float,
        unit: str = "",
        tags: Optional[dict[str, str]] = None,
    ) -> None:
        """记录指标"""
        record = MetricRecord(
            timestamp=datetime.now(),
            name=name,
            value=value,
            unit=unit,
            tags=tags or {},
        )
        self._metrics.append(record)

    def record_files(self, total: int, processed: int, failed: int = 0) -> None:
        """记录文件处理指标"""
        if self._generation_metrics:
            self._generation_metrics.total_files = total
            self._generation_metrics.processed_files = processed
            self._generation_metrics.failed_files = failed

    def record_code_elements(
        self,
        modules: int,
        classes: int,
        functions: int,
    ) -> None:
        """记录代码元素指标"""
        if self._generation_metrics:
            self._generation_metrics.total_modules = modules
            self._generation_metrics.total_classes = classes
            self._generation_metrics.total_functions = functions

    def record_diagram_generated(self) -> None:
        """记录图表生成"""
        if self._generation_metrics:
            self._generation_metrics.diagrams_generated += 1

    def record_llm_call(self, tokens: int = 0) -> None:
        """记录 LLM 调用"""
        if self._generation_metrics:
            self._generation_metrics.llm_calls += 1
            self._generation_metrics.llm_tokens_used += tokens

    def record_error(self, error: str) -> None:
        """记录错误"""
        if self._generation_metrics:
            self._generation_metrics.errors.append(error)

    def end_generation(self) -> Optional[GenerationMetrics]:
        """结束生成指标收集"""
        if self._generation_metrics:
            self._generation_metrics.end_time = datetime.now()

            if self.metrics_dir:
                self._save_generation_metrics()

            return self._generation_metrics
        return None

    def _save_generation_metrics(self) -> None:
        """保存生成指标"""
        if not self._generation_metrics or not self.metrics_dir:
            return

        metrics_file = self.metrics_dir / f"generation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        data = {
            "project_name": self._generation_metrics.project_name,
            "start_time": self._generation_metrics.start_time.isoformat(),
            "end_time": self._generation_metrics.end_time.isoformat() if self._generation_metrics.end_time else None,
            "duration_seconds": self._get_duration(),
            "total_files": self._generation_metrics.total_files,
            "processed_files": self._generation_metrics.processed_files,
            "failed_files": self._generation_metrics.failed_files,
            "total_modules": self._generation_metrics.total_modules,
            "total_classes": self._generation_metrics.total_classes,
            "total_functions": self._generation_metrics.total_functions,
            "diagrams_generated": self._generation_metrics.diagrams_generated,
            "llm_calls": self._generation_metrics.llm_calls,
            "llm_tokens_used": self._generation_metrics.llm_tokens_used,
            "errors": self._generation_metrics.errors,
        }

        with open(metrics_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def _get_duration(self) -> float:
        """获取生成耗时"""
        if not self._generation_metrics:
            return 0.0

        start = self._generation_metrics.start_time
        end = self._generation_metrics.end_time or datetime.now()

        return (end - start).total_seconds()

    def get_summary(self) -> dict[str, Any]:
        """获取指标摘要"""
        if not self._generation_metrics:
            return {}

        return {
            "project": self._generation_metrics.project_name,
            "duration": f"{self._get_duration():.2f}s",
            "files": f"{self._generation_metrics.processed_files}/{self._generation_metrics.total_files}",
            "modules": self._generation_metrics.total_modules,
            "classes": self._generation_metrics.total_classes,
            "functions": self._generation_metrics.total_functions,
            "diagrams": self._generation_metrics.diagrams_generated,
            "llm_calls": self._generation_metrics.llm_calls,
            "errors": len(self._generation_metrics.errors),
        }

    def clear(self) -> None:
        """清除指标"""
        self._metrics.clear()
        self._generation_metrics = None
