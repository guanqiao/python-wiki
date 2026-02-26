"""
自动同步服务
协调 FileWatcher 和 GitHooks，提供统一的自动同步能力
"""

import asyncio
import json
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Optional

from pywiki.sync.file_watcher import (
    AsyncFileWatcher,
    FileWatcher,
    FileWatchEvent,
    WatcherConfig,
)
from pywiki.sync.git_hooks import GitHooksManager, HookType
from pywiki.sync.git_change_detector import GitChangeDetector


class SyncMode(str, Enum):
    MANUAL = "manual"
    AUTO = "auto"
    HYBRID = "hybrid"


class SyncStatus(str, Enum):
    IDLE = "idle"
    SYNCING = "syncing"
    ERROR = "error"
    PAUSED = "paused"


@dataclass
class SyncConfig:
    mode: SyncMode = SyncMode.HYBRID
    watch_enabled: bool = True
    hooks_enabled: bool = True
    auto_update_threshold: int = 5
    min_sync_interval_ms: int = 5000
    max_batch_size: int = 50
    include_patterns: list[str] = field(default_factory=lambda: ["*.py", "*.ts", "*.tsx", "*.js", "*.jsx", "*.java"])
    exclude_patterns: list[str] = field(default_factory=lambda: ["*.pyc", "__pycache__/*", ".git/*"])


@dataclass
class SyncState:
    status: SyncStatus = SyncStatus.IDLE
    last_sync_time: Optional[datetime] = None
    last_commit_hash: Optional[str] = None
    pending_changes: int = 0
    total_syncs: int = 0
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status.value,
            "last_sync_time": self.last_sync_time.isoformat() if self.last_sync_time else None,
            "last_commit_hash": self.last_commit_hash,
            "pending_changes": self.pending_changes,
            "total_syncs": self.total_syncs,
            "errors": self.errors[-10:],
        }


@dataclass
class SyncEvent:
    event_type: str
    timestamp: datetime = field(default_factory=datetime.now)
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_type": self.event_type,
            "timestamp": self.timestamp.isoformat(),
            "details": self.details,
        }


class AutoSyncService:
    """
    自动同步服务
    整合文件监控和 Git hooks，提供统一的自动同步能力
    """

    def __init__(
        self,
        project_path: Path,
        config: Optional[SyncConfig] = None,
        on_sync: Optional[Callable[[list[FileWatchEvent]], None]] = None,
        on_status_change: Optional[Callable[[SyncStatus], None]] = None,
    ):
        self.project_path = Path(project_path)
        self.config = config or SyncConfig()
        self.on_sync = on_sync
        self.on_status_change = on_status_change

        self._state = SyncState()
        self._watcher: Optional[FileWatcher] = None
        self._hooks_manager: Optional[GitHooksManager] = None
        self._change_detector: Optional[GitChangeDetector] = None

        self._pending_events: list[FileWatchEvent] = []
        self._sync_lock = threading.Lock()
        self._sync_thread: Optional[threading.Thread] = None
        self._running = False
        self._last_sync_timestamp: float = 0

        self._event_history: list[SyncEvent] = []
        self._state_file = self.project_path / ".python-wiki" / "sync_state.json"

    def start(self) -> bool:
        if self._running:
            return True

        if not self.project_path.exists():
            return False

        self._load_state()
        self._running = True

        if self.config.watch_enabled:
            self._start_watcher()

        if self.config.hooks_enabled:
            self._setup_hooks()

        self._update_status(SyncStatus.IDLE)
        self._record_event("service_started", {"mode": self.config.mode.value})

        return True

    def stop(self) -> None:
        if not self._running:
            return

        self._running = False

        if self._watcher:
            self._watcher.stop()
            self._watcher = None

        self._save_state()
        self._record_event("service_stopped", {})
        self._update_status(SyncStatus.IDLE)

    def _start_watcher(self) -> None:
        watcher_config = WatcherConfig(
            include_patterns=self.config.include_patterns,
            exclude_patterns=self.config.exclude_patterns,
        )

        self._watcher = FileWatcher(
            watch_path=self.project_path,
            config=watcher_config,
            on_changes=self._handle_file_changes,
        )

        self._watcher.start()

    def _setup_hooks(self) -> None:
        self._hooks_manager = GitHooksManager(
            repo_path=self.project_path,
            on_trigger=self._handle_hook_trigger,
        )

        if self._hooks_manager.is_git_repo():
            self._hooks_manager.install_hooks(
                hook_types=[HookType.POST_COMMIT, HookType.POST_MERGE],
                force=False,
            )

            try:
                self._change_detector = GitChangeDetector(self.project_path)
                commit = self._change_detector.get_current_commit()
                if commit:
                    self._state.last_commit_hash = commit.hash
            except Exception:
                pass

    def _handle_file_changes(self, events: list[FileWatchEvent]) -> None:
        if not self._running:
            return

        with self._sync_lock:
            self._pending_events.extend(events)
            self._state.pending_changes = len(self._pending_events)

        self._record_event("file_changes_detected", {"count": len(events)})

        if self.config.mode == SyncMode.AUTO:
            self._maybe_trigger_sync()

    def _handle_hook_trigger(self, hook_type: HookType, context: dict[str, Any]) -> None:
        if not self._running:
            return

        self._record_event("hook_triggered", {"hook_type": hook_type.value, "context": context})

        if hook_type == HookType.POST_COMMIT:
            self._handle_post_commit(context)
        elif hook_type == HookType.POST_MERGE:
            self._handle_post_merge(context)

    def _handle_post_commit(self, context: dict[str, Any]) -> None:
        if not self._change_detector:
            return

        try:
            commit = self._change_detector.get_current_commit()
            if commit and commit.hash != self._state.last_commit_hash:
                self._state.last_commit_hash = commit.hash
                self._trigger_sync(reason="post_commit")
        except Exception:
            pass

    def _handle_post_merge(self, context: dict[str, Any]) -> None:
        self._trigger_sync(reason="post_merge")

    def _maybe_trigger_sync(self) -> None:
        current_time = time.time()
        time_since_last = (current_time - self._last_sync_timestamp) * 1000

        if time_since_last < self.config.min_sync_interval_ms:
            return

        if len(self._pending_events) >= self.config.auto_update_threshold:
            self._trigger_sync(reason="threshold_reached")

    def _trigger_sync(self, reason: str = "manual") -> None:
        with self._sync_lock:
            if self._state.status == SyncStatus.SYNCING:
                return

            events_to_sync = self._pending_events[:self.config.max_batch_size]
            self._pending_events = self._pending_events[self.config.max_batch_size:]

        if not events_to_sync and reason == "manual":
            if self._change_detector:
                try:
                    changes = self._change_detector.get_uncommitted_changes()
                    events_to_sync = [
                        FileWatchEvent(
                            file_path=change.file_path,
                            event_type=self._map_change_type(change.change_type),
                        )
                        for change in changes
                    ]
                except Exception:
                    pass

        if not events_to_sync:
            return

        self._update_status(SyncStatus.SYNCING)
        self._record_event("sync_started", {"reason": reason, "events": len(events_to_sync)})

        try:
            if self.on_sync:
                self.on_sync(events_to_sync)

            self._state.last_sync_time = datetime.now()
            self._state.total_syncs += 1
            self._last_sync_timestamp = time.time()
            self._update_status(SyncStatus.IDLE)
            self._record_event("sync_completed", {"events_processed": len(events_to_sync)})

        except Exception as e:
            self._state.errors.append(str(e))
            self._update_status(SyncStatus.ERROR)
            self._record_event("sync_failed", {"error": str(e)})

        finally:
            self._state.pending_changes = len(self._pending_events)

    def _map_change_type(self, change_type: Any) -> "str":
        from pywiki.sync.file_watcher import WatchEventType
        mapping = {
            "added": WatchEventType.CREATED,
            "modified": WatchEventType.MODIFIED,
            "deleted": WatchEventType.DELETED,
            "renamed": WatchEventType.MOVED,
            "untracked": WatchEventType.CREATED,
        }
        return mapping.get(str(change_type.value), WatchEventType.MODIFIED)

    def force_sync(self) -> bool:
        if self._state.status == SyncStatus.SYNCING:
            return False

        self._trigger_sync(reason="manual")
        return True

    def pause(self) -> None:
        self._update_status(SyncStatus.PAUSED)
        self._record_event("service_paused", {})

    def resume(self) -> None:
        self._update_status(SyncStatus.IDLE)
        self._record_event("service_resumed", {})

    def _update_status(self, status: SyncStatus) -> None:
        old_status = self._state.status
        self._state.status = status

        if old_status != status and self.on_status_change:
            try:
                self.on_status_change(status)
            except Exception:
                pass

    def _record_event(self, event_type: str, details: dict[str, Any]) -> None:
        event = SyncEvent(event_type=event_type, details=details)
        self._event_history.append(event)

        if len(self._event_history) > 100:
            self._event_history = self._event_history[-100:]

    def _load_state(self) -> None:
        if not self._state_file.exists():
            return

        try:
            data = json.loads(self._state_file.read_text(encoding="utf-8"))
            self._state.last_commit_hash = data.get("last_commit_hash")
            if data.get("last_sync_time"):
                self._state.last_sync_time = datetime.fromisoformat(data["last_sync_time"])
            self._state.total_syncs = data.get("total_syncs", 0)
        except Exception:
            pass

    def _save_state(self) -> None:
        try:
            self._state_file.parent.mkdir(parents=True, exist_ok=True)
            data = {
                "last_commit_hash": self._state.last_commit_hash,
                "last_sync_time": self._state.last_sync_time.isoformat() if self._state.last_sync_time else None,
                "total_syncs": self._state.total_syncs,
            }
            self._state_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except Exception:
            pass

    @property
    def status(self) -> SyncStatus:
        return self._state.status

    @property
    def is_running(self) -> bool:
        return self._running

    def get_state(self) -> dict[str, Any]:
        return self._state.to_dict()

    def get_statistics(self) -> dict[str, Any]:
        return {
            "running": self._running,
            "mode": self.config.mode.value,
            "state": self._state.to_dict(),
            "watcher_active": self._watcher is not None and self._watcher.is_running,
            "hooks_installed": self._hooks_manager.get_installed_hooks() if self._hooks_manager else [],
            "recent_events": [e.to_dict() for e in self._event_history[-10:]],
        }


class AsyncAutoSyncService:
    """
    异步自动同步服务
    适配异步环境
    """

    def __init__(
        self,
        project_path: Path,
        config: Optional[SyncConfig] = None,
    ):
        self.project_path = Path(project_path)
        self.config = config or SyncConfig()
        self._sync_service: Optional[AutoSyncService] = None
        self._async_watcher: Optional[AsyncFileWatcher] = None
        self._running = False
        self._sync_queue: asyncio.Queue[list[FileWatchEvent]] = asyncio.Queue()

    async def start(self) -> bool:
        if self._running:
            return True

        loop = asyncio.get_event_loop()

        self._sync_service = AutoSyncService(
            project_path=self.project_path,
            config=self.config,
            on_sync=lambda events: self._sync_queue.put_nowait(events),
        )

        result = await loop.run_in_executor(None, self._sync_service.start)
        self._running = result
        return result

    async def stop(self) -> None:
        if not self._running or not self._sync_service:
            return

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._sync_service.stop)
        self._running = False

    async def wait_for_sync(self, timeout: float = 30.0) -> Optional[list[FileWatchEvent]]:
        if not self._running:
            return None

        try:
            return await asyncio.wait_for(
                self._sync_queue.get(),
                timeout=timeout,
            )
        except asyncio.TimeoutError:
            return None

    async def force_sync(self) -> bool:
        if not self._sync_service:
            return False

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._sync_service.force_sync)

    @property
    def is_running(self) -> bool:
        return self._running

    def get_state(self) -> dict[str, Any]:
        if self._sync_service:
            return self._sync_service.get_state()
        return {}
