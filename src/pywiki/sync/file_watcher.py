"""
文件系统监控器
基于 watchdog 实现文件变更监控，支持防抖和排除模式
"""

import asyncio
import fnmatch
import threading
import time
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Optional

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer


class WatchEventType(str, Enum):
    CREATED = "created"
    MODIFIED = "modified"
    DELETED = "deleted"
    MOVED = "moved"


@dataclass
class FileWatchEvent:
    file_path: Path
    event_type: WatchEventType
    old_path: Optional[Path] = None
    timestamp: float = field(default_factory=time.time)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "file_path": str(self.file_path),
            "event_type": self.event_type.value,
            "old_path": str(self.old_path) if self.old_path else None,
            "timestamp": self.timestamp,
        }


@dataclass
class WatcherConfig:
    debounce_ms: int = 500
    include_patterns: list[str] = field(default_factory=lambda: ["*.py", "*.ts", "*.tsx", "*.js", "*.jsx", "*.java"])
    exclude_patterns: list[str] = field(default_factory=lambda: ["*.pyc", "__pycache__/*", ".git/*", "node_modules/*", "*.swp"])
    exclude_dirs: list[str] = field(default_factory=lambda: [".git", "__pycache__", "node_modules", ".venv", "venv", "build", "dist"])


class DebouncedEventHandler(FileSystemEventHandler):
    """
    防抖事件处理器
    聚合短时间内的多次事件，避免频繁触发
    """

    def __init__(
        self,
        callback: Callable[[list[FileWatchEvent]], None],
        config: WatcherConfig,
    ):
        super().__init__()
        self.callback = callback
        self.config = config
        self._pending_events: dict[str, FileWatchEvent] = {}
        self._lock = threading.Lock()
        self._debounce_timer: Optional[threading.Timer] = None
        self._last_trigger_time: float = 0

    def on_created(self, event: FileSystemEvent) -> None:
        if not event.is_directory:
            self._handle_event(event, WatchEventType.CREATED)

    def on_modified(self, event: FileSystemEvent) -> None:
        if not event.is_directory:
            self._handle_event(event, WatchEventType.MODIFIED)

    def on_deleted(self, event: FileSystemEvent) -> None:
        if not event.is_directory:
            self._handle_event(event, WatchEventType.DELETED)

    def on_moved(self, event: FileSystemEvent) -> None:
        if not event.is_directory:
            self._handle_event(event, WatchEventType.MOVED, old_path=Path(event.src_path))

    def _handle_event(
        self,
        event: FileSystemEvent,
        event_type: WatchEventType,
        old_path: Optional[Path] = None,
    ) -> None:
        file_path = Path(event.dest_path) if event_type == WatchEventType.MOVED else Path(event.src_path)

        if not self._should_process(file_path):
            return

        with self._lock:
            watch_event = FileWatchEvent(
                file_path=file_path,
                event_type=event_type,
                old_path=old_path,
            )

            key = str(file_path)
            existing = self._pending_events.get(key)

            if existing:
                if existing.event_type == WatchEventType.CREATED and event_type == WatchEventType.MODIFIED:
                    watch_event.event_type = WatchEventType.CREATED
                elif existing.event_type == WatchEventType.MODIFIED and event_type == WatchEventType.DELETED:
                    del self._pending_events[key]
                    return

            self._pending_events[key] = watch_event
            self._schedule_callback()

    def _should_process(self, file_path: Path) -> bool:
        if self.config.exclude_dirs:
            for exclude_dir in self.config.exclude_dirs:
                if exclude_dir in file_path.parts:
                    return False

        file_str = str(file_path)

        for pattern in self.config.exclude_patterns:
            if fnmatch.fnmatch(file_str, pattern) or fnmatch.fnmatch(file_path.name, pattern):
                return False

        if self.config.include_patterns:
            matched = False
            for pattern in self.config.include_patterns:
                if fnmatch.fnmatch(file_path.name, pattern):
                    matched = True
                    break
            if not matched:
                return False

        return True

    def _schedule_callback(self) -> None:
        if self._debounce_timer:
            self._debounce_timer.cancel()

        self._debounce_timer = threading.Timer(
            self.config.debounce_ms / 1000.0,
            self._trigger_callback,
        )
        self._debounce_timer.start()

    def _trigger_callback(self) -> None:
        with self._lock:
            if not self._pending_events:
                return

            events = list(self._pending_events.values())
            self._pending_events.clear()
            self._last_trigger_time = time.time()

        try:
            self.callback(events)
        except Exception:
            pass

    def flush(self) -> None:
        if self._debounce_timer:
            self._debounce_timer.cancel()
        self._trigger_callback()


class FileWatcher:
    """
    文件系统监控器
    基于 watchdog 实现文件变更监控
    """

    def __init__(
        self,
        watch_path: Path,
        config: Optional[WatcherConfig] = None,
        on_changes: Optional[Callable[[list[FileWatchEvent]], None]] = None,
    ):
        self.watch_path = Path(watch_path)
        self.config = config or WatcherConfig()
        self.on_changes = on_changes

        self._observer: Optional[Observer] = None
        self._event_handler: Optional[DebouncedEventHandler] = None
        self._running = False
        self._change_count: int = 0
        self._last_change_time: float = 0

    def start(self) -> bool:
        if self._running:
            return True

        if not self.watch_path.exists():
            return False

        try:
            self._event_handler = DebouncedEventHandler(
                callback=self._handle_changes,
                config=self.config,
            )

            self._observer = Observer()
            self._observer.schedule(
                self._event_handler,
                str(self.watch_path),
                recursive=True,
            )
            self._observer.start()
            self._running = True
            return True

        except Exception:
            self._running = False
            return False

    def stop(self) -> None:
        if not self._running:
            return

        if self._event_handler:
            self._event_handler.flush()

        if self._observer:
            self._observer.stop()
            self._observer.join(timeout=5.0)
            self._observer = None

        self._running = False

    def _handle_changes(self, events: list[FileWatchEvent]) -> None:
        self._change_count += len(events)
        self._last_change_time = time.time()

        if self.on_changes:
            try:
                self.on_changes(events)
            except Exception:
                pass

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def statistics(self) -> dict[str, Any]:
        return {
            "running": self._running,
            "watch_path": str(self.watch_path),
            "change_count": self._change_count,
            "last_change_time": self._last_change_time,
            "debounce_ms": self.config.debounce_ms,
        }

    def __enter__(self) -> "FileWatcher":
        self.start()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.stop()


class AsyncFileWatcher:
    """
    异步文件监控器
    适配异步环境
    """

    def __init__(
        self,
        watch_path: Path,
        config: Optional[WatcherConfig] = None,
    ):
        self.watch_path = Path(watch_path)
        self.config = config or WatcherConfig()
        self._watcher: Optional[FileWatcher] = None
        self._event_queue: asyncio.Queue[list[FileWatchEvent]] = asyncio.Queue()
        self._running = False

    async def start(self) -> bool:
        if self._running:
            return True

        self._watcher = FileWatcher(
            watch_path=self.watch_path,
            config=self.config,
            on_changes=lambda events: self._event_queue.put_nowait(events),
        )

        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, self._watcher.start)
        self._running = result
        return result

    async def stop(self) -> None:
        if not self._running or not self._watcher:
            return

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._watcher.stop)
        self._running = False

    async def get_changes(self, timeout: float = 1.0) -> Optional[list[FileWatchEvent]]:
        if not self._running:
            return None

        try:
            return await asyncio.wait_for(
                self._event_queue.get(),
                timeout=timeout,
            )
        except asyncio.TimeoutError:
            return None

    @property
    def is_running(self) -> bool:
        return self._running

    async def __aenter__(self) -> "AsyncFileWatcher":
        await self.start()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        await self.stop()
