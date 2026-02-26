"""
同步模块单元测试
"""

import asyncio
import tempfile
import threading
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from pywiki.sync.file_watcher import (
    AsyncFileWatcher,
    DebouncedEventHandler,
    FileWatcher,
    FileWatchEvent,
    WatcherConfig,
    WatchEventType,
)
from pywiki.sync.git_hooks import GitHooksManager, HookResult, HookType
from pywiki.sync.auto_sync_service import (
    AsyncAutoSyncService,
    AutoSyncService,
    SyncConfig,
    SyncMode,
    SyncStatus,
)


class TestWatcherConfig:
    def test_default_config(self):
        config = WatcherConfig()
        assert config.debounce_ms == 500
        assert "*.py" in config.include_patterns
        assert "*.pyc" in config.exclude_patterns

    def test_custom_config(self):
        config = WatcherConfig(
            debounce_ms=1000,
            include_patterns=["*.go"],
            exclude_patterns=["vendor/*"],
        )
        assert config.debounce_ms == 1000
        assert "*.go" in config.include_patterns
        assert "vendor/*" in config.exclude_patterns


class TestFileWatchEvent:
    def test_event_creation(self):
        event = FileWatchEvent(
            file_path=Path("/test/file.py"),
            event_type=WatchEventType.MODIFIED,
        )
        assert event.file_path == Path("/test/file.py")
        assert event.event_type == WatchEventType.MODIFIED
        assert event.old_path is None

    def test_event_to_dict(self):
        event = FileWatchEvent(
            file_path=Path("/test/file.py"),
            event_type=WatchEventType.MOVED,
            old_path=Path("/test/old_file.py"),
        )
        result = event.to_dict()
        assert Path(result["file_path"]) == Path("/test/file.py")
        assert result["event_type"] == "moved"
        assert Path(result["old_path"]) == Path("/test/old_file.py")


class TestDebouncedEventHandler:
    def test_should_process_included_file(self):
        config = WatcherConfig(include_patterns=["*.py"])
        handler = DebouncedEventHandler(callback=lambda x: None, config=config)

        assert handler._should_process(Path("/test/file.py")) is True
        assert handler._should_process(Path("/test/file.txt")) is False

    def test_should_process_excluded_file(self):
        config = WatcherConfig(exclude_patterns=["*.pyc"])
        handler = DebouncedEventHandler(callback=lambda x: None, config=config)

        assert handler._should_process(Path("/test/file.pyc")) is False
        assert handler._should_process(Path("/test/file.py")) is True

    def test_should_process_excluded_dir(self):
        config = WatcherConfig(exclude_dirs=["__pycache__", ".git"])
        handler = DebouncedEventHandler(callback=lambda x: None, config=config)

        assert handler._should_process(Path("/test/.git/config")) is False
        assert handler._should_process(Path("/test/__pycache__/module.pyc")) is False
        assert handler._should_process(Path("/test/src/module.py")) is True


class TestFileWatcher:
    def test_watcher_creation(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            watcher = FileWatcher(Path(tmpdir))
            assert watcher.watch_path == Path(tmpdir)
            assert not watcher.is_running

    def test_watcher_start_stop(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            watcher = FileWatcher(Path(tmpdir))
            assert watcher.start() is True
            assert watcher.is_running is True
            watcher.stop()
            assert watcher.is_running is False

    def test_watcher_nonexistent_path(self):
        watcher = FileWatcher(Path("/nonexistent/path"))
        assert watcher.start() is False

    def test_watcher_context_manager(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with FileWatcher(Path(tmpdir)) as watcher:
                assert watcher.is_running is True
            assert watcher.is_running is False

    def test_watcher_statistics(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            watcher = FileWatcher(Path(tmpdir))
            stats = watcher.statistics
            assert stats["running"] is False
            assert stats["watch_path"] == tmpdir


class TestAsyncFileWatcher:
    @pytest.mark.asyncio
    async def test_async_watcher_start_stop(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            watcher = AsyncFileWatcher(Path(tmpdir))
            result = await watcher.start()
            assert result is True
            assert watcher.is_running is True
            await watcher.stop()
            assert watcher.is_running is False

    @pytest.mark.asyncio
    async def test_async_watcher_context_manager(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            async with AsyncFileWatcher(Path(tmpdir)) as watcher:
                assert watcher.is_running is True
            assert watcher.is_running is False


class TestGitHooksManager:
    def test_hooks_manager_creation(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = GitHooksManager(Path(tmpdir))
            assert manager.repo_path == Path(tmpdir)

    def test_non_git_repo(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = GitHooksManager(Path(tmpdir))
            assert manager.is_git_repo() is False

    def test_get_hooks_status_non_git(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = GitHooksManager(Path(tmpdir))
            status = manager.get_hooks_status()
            assert status["is_git_repo"] is False
            assert status["installed_hooks"] == []

    def test_trigger_hook(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = GitHooksManager(Path(tmpdir))
            result = manager.trigger_hook(HookType.POST_COMMIT)
            assert isinstance(result, HookResult)
            assert result.hook_type == HookType.POST_COMMIT


class TestSyncConfig:
    def test_default_config(self):
        config = SyncConfig()
        assert config.mode == SyncMode.HYBRID
        assert config.watch_enabled is True
        assert config.hooks_enabled is True

    def test_custom_config(self):
        config = SyncConfig(
            mode=SyncMode.AUTO,
            watch_enabled=False,
            auto_update_threshold=10,
        )
        assert config.mode == SyncMode.AUTO
        assert config.watch_enabled is False
        assert config.auto_update_threshold == 10


class TestAutoSyncService:
    def test_service_creation(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            service = AutoSyncService(Path(tmpdir))
            assert service.project_path == Path(tmpdir)
            assert not service.is_running

    def test_service_start_stop(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            service = AutoSyncService(Path(tmpdir))
            assert service.start() is True
            assert service.is_running is True
            service.stop()
            assert service.is_running is False

    def test_service_get_state(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            service = AutoSyncService(Path(tmpdir))
            state = service.get_state()
            assert state["status"] == "idle"

    def test_service_pause_resume(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            service = AutoSyncService(Path(tmpdir))
            service.start()
            service.pause()
            assert service.status == SyncStatus.PAUSED
            service.resume()
            assert service.status == SyncStatus.IDLE
            service.stop()

    def test_service_statistics(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            service = AutoSyncService(Path(tmpdir))
            stats = service.get_statistics()
            assert stats["running"] is False
            assert stats["mode"] == "hybrid"

    def test_service_with_callback(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            callback_called = []
            
            def on_sync(events):
                callback_called.append(len(events))

            service = AutoSyncService(
                Path(tmpdir),
                on_sync=on_sync,
            )
            service.start()
            service._pending_events = [
                FileWatchEvent(
                    file_path=Path("/test/file.py"),
                    event_type=WatchEventType.MODIFIED,
                )
            ]
            service.force_sync()
            service.stop()
            
            assert len(callback_called) == 1


class TestAsyncAutoSyncService:
    @pytest.mark.asyncio
    async def test_async_service_start_stop(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            service = AsyncAutoSyncService(Path(tmpdir))
            result = await service.start()
            assert result is True
            assert service.is_running is True
            await service.stop()
            assert service.is_running is False

    @pytest.mark.asyncio
    async def test_async_service_get_state(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            service = AsyncAutoSyncService(Path(tmpdir))
            await service.start()
            state = service.get_state()
            assert "status" in state
            await service.stop()


class TestSyncMode:
    def test_sync_mode_values(self):
        assert SyncMode.MANUAL.value == "manual"
        assert SyncMode.AUTO.value == "auto"
        assert SyncMode.HYBRID.value == "hybrid"


class TestSyncStatus:
    def test_sync_status_values(self):
        assert SyncStatus.IDLE.value == "idle"
        assert SyncStatus.SYNCING.value == "syncing"
        assert SyncStatus.ERROR.value == "error"
        assert SyncStatus.PAUSED.value == "paused"
