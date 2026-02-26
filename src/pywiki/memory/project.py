
"""
项目上下文记忆
"""
import json
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Optional, List, Dict


@dataclass
class ArchitectureDecision:
    """架构决策记录"""
    id: str
    title: str
    context: str
    decision: str
    consequences: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    status: str = "accepted"


@dataclass
class ProjectContext:
    """项目上下文"""
    project_name: str
    architecture_pattern: Optional[str] = None
    tech_stack: List[str] = field(default_factory=list)
    key_modules: List[str] = field(default_factory=list)
    business_domains: List[str] = field(default_factory=list)
    architecture_decisions: List[ArchitectureDecision] = field(default_factory=list)
    custom_notes: Dict[str, Any] = field(default_factory=dict)
    last_updated: str = field(default_factory=lambda: datetime.now().isoformat())


class ProjectMemory:
    """项目上下文记忆管理器"""

    def __init__(self, storage_path: Path, project_name: str):
        self.storage_path = storage_path
        self.project_name = project_name
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self._context: Optional[ProjectContext] = None
        self._load_context()

    def _get_context_path(self) -&gt; Path:
        safe_name = self.project_name.replace("/", "_").replace("\\", "_")
        return self.storage_path / f"project_{safe_name}.json"

    def _load_context(self) -&gt; None:
        context_path = self._get_context_path()
        if context_path.exists():
            try:
                with open(context_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    decisions_data = data.pop("architecture_decisions", [])
                    decisions = [ArchitectureDecision(**d) for d in decisions_data]
                    self._context = ProjectContext(
                        architecture_decisions=decisions,
                        **data
                    )
            except Exception:
                self._context = ProjectContext(project_name=self.project_name)
        else:
            self._context = ProjectContext(project_name=self.project_name)

    def _save_context(self) -&gt; None:
        if self._context:
            self._context.last_updated = datetime.now().isoformat()
            context_path = self._get_context_path()
            data = asdict(self._context)
            with open(context_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

    def get_context(self) -&gt; ProjectContext:
        """获取项目上下文"""
        if self._context is None:
            self._load_context()
        return self._context

    def update_context(self, **kwargs: Any) -&gt; None:
        """更新项目上下文"""
        if self._context is None:
            self._load_context()
        
        for key, value in kwargs.items():
            if hasattr(self._context, key):
                setattr(self._context, key, value)
        
        self._save_context()

    def add_architecture_decision(
        self,
        title: str,
        context: str,
        decision: str,
        consequences: str,
        decision_id: Optional[str] = None,
    ) -&gt; ArchitectureDecision:
        """添加架构决策"""
        if self._context is None:
            self._load_context()
        
        adr_id = decision_id or f"ADR-{len(self._context.architecture_decisions) + 1:04d}"
        adr = ArchitectureDecision(
            id=adr_id,
            title=title,
            context=context,
            decision=decision,
            consequences=consequences,
        )
        
        self._context.architecture_decisions.append(adr)
        self._save_context()
        return adr

    def get_architecture_decision(self, decision_id: str) -&gt; Optional[ArchitectureDecision]:
        """获取架构决策"""
        if self._context is None:
            self._load_context()
        
        for adr in self._context.architecture_decisions:
            if adr.id == decision_id:
                return adr
        return None

    def list_architecture_decisions(self, status: Optional[str] = None) -&gt; List[ArchitectureDecision]:
        """列出架构决策"""
        if self._context is None:
            self._load_context()
        
        decisions = self._context.architecture_decisions
        if status:
            decisions = [d for d in decisions if d.status == status]
        return decisions

    def set_custom_note(self, key: str, value: Any) -&gt; None:
        """设置自定义备注"""
        if self._context is None:
            self._load_context()
        
        self._context.custom_notes[key] = value
        self._save_context()

    def get_custom_note(self, key: str, default: Any = None) -&gt; Any:
        """获取自定义备注"""
        if self._context is None:
            self._load_context()
        
        return self._context.custom_notes.get(key, default)
