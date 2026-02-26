"""
记忆系统测试
"""

from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from pywiki.memory.base import BaseMemory, MemoryRegistry
from pywiki.memory.global_memory import GlobalMemory, CodingStyle, TechStackPreference
from pywiki.memory.memory_prioritizer import (
    MemoryPrioritizer,
    MemoryItem,
    MemoryPriority,
    PrioritizationConfig,
)
from pywiki.memory.style_learner import StyleLearner, StyleObservation


class TestBaseMemory:
    """BaseMemory 测试"""

    def test_serialize_datetime(self):
        dt = datetime(2024, 1, 15, 10, 30, 0)
        result = BaseMemory._serialize_datetime(dt)
        assert result == "2024-01-15T10:30:00"

    def test_serialize_datetime_none(self):
        result = BaseMemory._serialize_datetime(None)
        assert result is None

    def test_deserialize_datetime(self):
        result = BaseMemory._deserialize_datetime("2024-01-15T10:30:00")
        assert result == datetime(2024, 1, 15, 10, 30, 0)

    def test_deserialize_datetime_none(self):
        result = BaseMemory._deserialize_datetime(None)
        assert result is None

    def test_serialize_path(self):
        path = Path("/test/path")
        result = BaseMemory._serialize_path(path)
        assert "test" in result and "path" in result

    def test_deserialize_path(self):
        result = BaseMemory._deserialize_path("/test/path")
        assert result == Path("/test/path")


class TestMemoryRegistry:
    """MemoryRegistry 测试"""

    def test_register_memory(self, tmp_path: Path):
        registry = MemoryRegistry(storage_path=tmp_path)
        memory = GlobalMemory(storage_path=tmp_path / "test")

        registry.register("test_memory", memory)

        assert registry.get("test_memory") == memory

    def test_unregister_memory(self, tmp_path: Path):
        registry = MemoryRegistry(storage_path=tmp_path)
        memory = GlobalMemory(storage_path=tmp_path / "test")

        registry.register("test_memory", memory)
        result = registry.unregister("test_memory")

        assert result is True
        assert registry.get("test_memory") is None

    def test_save_all(self, tmp_path: Path):
        registry = MemoryRegistry(storage_path=tmp_path)
        memory = GlobalMemory(storage_path=tmp_path / "test")
        memory.set_preference("key", "value")

        registry.register("test_memory", memory)
        registry.save_all()

        assert (tmp_path / "test" / "preferences.json").exists()

    def test_export_all(self, tmp_path: Path):
        registry = MemoryRegistry(storage_path=tmp_path)
        memory = GlobalMemory(storage_path=tmp_path / "test")
        memory.set_preference("key", "value")

        registry.register("test_memory", memory)
        exported = registry.export_all()

        assert "test_memory" in exported
        assert "preferences" in exported["test_memory"] or "data" in exported["test_memory"]


@pytest.fixture
def global_memory(tmp_path: Path) -> GlobalMemory:
    return GlobalMemory(storage_path=tmp_path / "global_memory")


@pytest.fixture
def memory_prioritizer() -> MemoryPrioritizer:
    return MemoryPrioritizer()


class TestGlobalMemory:
    """GlobalMemory 测试"""

    def test_set_and_get_preference(self, global_memory: GlobalMemory):
        global_memory.set_preference(
            key="test_key",
            value="test_value",
            category="test",
        )

        value = global_memory.get_preference("test_key")
        assert value == "test_value"

    def test_get_nonexistent_preference(self, global_memory: GlobalMemory):
        value = global_memory.get_preference("nonexistent", default="default")
        assert value == "default"

    def test_update_coding_style(self, global_memory: GlobalMemory):
        global_memory.update_coding_style(
            indent_style="tab",
            indent_size=2,
            quote_style="single",
        )

        style = global_memory.get_coding_style()

        assert style.indent_style == "tab"
        assert style.indent_size == 2
        assert style.quote_style == "single"

    def test_update_tech_stack(self, global_memory: GlobalMemory):
        global_memory.update_tech_stack(
            language="Python",
            frameworks=["FastAPI", "Pydantic"],
            libraries=["httpx", "tenacity"],
            expertise_level="advanced",
        )

        ts = global_memory.get_tech_stack("Python")

        assert ts["language"] == "Python"
        assert "FastAPI" in ts["frameworks"]
        assert "Pydantic" in ts["frameworks"]

    def test_get_preferred_languages(self, global_memory: GlobalMemory):
        global_memory.update_tech_stack("Python", ["FastAPI"])
        global_memory.update_tech_stack("TypeScript", ["React"])

        languages = global_memory.get_preferred_languages()

        assert "Python" in languages
        assert "TypeScript" in languages

    def test_add_and_get_knowledge(self, global_memory: GlobalMemory):
        global_memory.add_knowledge("pattern_singleton", "Use __new__ for singleton")

        value = global_memory.get_knowledge("pattern_singleton")
        assert value == "Use __new__ for singleton"

    def test_export_and_import(self, global_memory: GlobalMemory):
        global_memory.set_preference("key1", "value1")
        global_memory.update_coding_style(indent_size=4)

        exported = global_memory.export()

        assert "preferences" in exported
        assert "coding_style" in exported

        global_memory.clear()
        global_memory.import_data(exported)

        assert global_memory.get_preference("key1") == "value1"

    def test_clear(self, global_memory: GlobalMemory):
        global_memory.set_preference("key", "value")
        global_memory.clear()

        assert global_memory.get_preference("key") is None


class TestCodingStyle:
    """CodingStyle 测试"""

    def test_create_default(self):
        style = CodingStyle()

        assert style.indent_style == "space"
        assert style.indent_size == 4
        assert style.quote_style == "double"

    def test_to_dict(self):
        style = CodingStyle(
            indent_style="tab",
            indent_size=2,
            quote_style="single",
        )

        data = style.to_dict()

        assert data["indent_style"] == "tab"
        assert data["indent_size"] == 2


class TestMemoryPrioritizer:
    """MemoryPrioritizer 测试"""

    def test_add_memory(self, memory_prioritizer: MemoryPrioritizer):
        item = memory_prioritizer.add_memory(
            key="test_memory",
            value="Test content",
            priority=MemoryPriority.HIGH,
            importance=0.8,
        )

        assert item.key == "test_memory"
        assert item.priority == MemoryPriority.HIGH

    def test_get_memory(self, memory_prioritizer: MemoryPrioritizer):
        memory_prioritizer.add_memory("key", "value")

        item = memory_prioritizer.get_memory("key")

        assert item is not None
        assert item.value == "value"
        assert item.access_count == 1

    def test_update_priority(self, memory_prioritizer: MemoryPrioritizer):
        memory_prioritizer.add_memory("key", "value")

        success = memory_prioritizer.update_priority("key", MemoryPriority.CRITICAL)

        assert success
        assert memory_prioritizer.get_memory("key").priority == MemoryPriority.CRITICAL

    def test_calculate_score(self, memory_prioritizer: MemoryPrioritizer):
        item = memory_prioritizer.add_memory(
            key="test",
            value="content",
            priority=MemoryPriority.HIGH,
            importance=0.9,
        )

        score = memory_prioritizer.calculate_score(item)

        assert 0 <= score <= 1

    def test_get_sorted_memories(self, memory_prioritizer: MemoryPrioritizer):
        memory_prioritizer.add_memory("low", "low priority", priority=MemoryPriority.LOW)
        memory_prioritizer.add_memory("high", "high priority", priority=MemoryPriority.HIGH)
        memory_prioritizer.add_memory("critical", "critical", priority=MemoryPriority.CRITICAL)

        sorted_items = memory_prioritizer.get_sorted_memories(limit=10)

        assert len(sorted_items) == 3
        assert sorted_items[0].priority == MemoryPriority.CRITICAL

    def test_apply_decay(self, memory_prioritizer: MemoryPrioritizer):
        memory_prioritizer.add_memory("test", "content", importance=1.0)

        count = memory_prioritizer.apply_decay()

        assert count == 1
        item = memory_prioritizer._memories.get("test")
        assert item is not None
        assert item.importance <= 1.0

    def test_get_stats(self, memory_prioritizer: MemoryPrioritizer):
        memory_prioritizer.add_memory("high", "content", priority=MemoryPriority.HIGH)
        memory_prioritizer.add_memory("low", "content", priority=MemoryPriority.LOW)

        stats = memory_prioritizer.get_stats()

        assert stats["total_memories"] == 2
        assert stats["by_priority"]["high"] == 1
        assert stats["by_priority"]["low"] == 1


class TestStyleLearner:
    """StyleLearner 测试"""

    @pytest.fixture
    def style_learner(self, tmp_path: Path) -> StyleLearner:
        global_memory = GlobalMemory(storage_path=tmp_path / "global")
        return StyleLearner(global_memory=global_memory)

    def test_detect_indent_style(self, style_learner: StyleLearner):
        content = "def hello():\n    print('hello')"

        style = style_learner._detect_indent_style(content)

        assert style == "space"

    def test_detect_quote_style(self, style_learner: StyleLearner):
        content = 'message = "Hello World"'

        style = style_learner._detect_quote_style(content)

        assert style == "double"

    def test_detect_naming_convention(self, style_learner: StyleLearner):
        snake_content = "def my_function(): pass"
        camel_content = "def myFunction(): pass"

        snake_style = style_learner._detect_naming_convention(snake_content)
        camel_style = style_learner._detect_naming_convention(camel_content)

        assert snake_style == "snake_case"
        assert camel_style == "camelCase"

    def test_analyze_file(self, style_learner: StyleLearner, tmp_path: Path):
        test_file = tmp_path / "test.py"
        test_file.write_text(
            '"""Test module"""\n'
            'def hello_world():\n'
            '    """Say hello"""\n'
            '    message = "Hello"\n'
            '    return message\n',
            encoding="utf-8",
        )

        result = style_learner.analyze_file(test_file)

        assert "indent_style" in result
        assert "quote_style" in result
        assert "naming_convention" in result

    def test_record_observations(self, style_learner: StyleLearner):
        result = {
            "indent_style": "space",
            "quote_style": "double",
        }

        style_learner._record_observations(result, "test.py")

        assert len(style_learner._observations) == 2
