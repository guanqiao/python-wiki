"""
Wiki 版本历史测试
"""

import sys
from pathlib import Path
from datetime import datetime

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from pywiki.wiki.history import WikiHistory


class TestWikiHistory:
    """WikiHistory 测试"""

    @pytest.fixture
    def history_dir(self, tmp_path):
        """创建历史目录"""
        history = tmp_path / "history"
        history.mkdir(parents=True, exist_ok=True)
        return history

    @pytest.fixture
    def history(self, history_dir):
        """创建历史实例"""
        return WikiHistory(history_dir)

    def test_history_initialization(self, history_dir):
        """测试历史初始化"""
        history = WikiHistory(history_dir)

        assert history.history_dir == history_dir
        assert history.history_dir.exists()
        assert history._history_file.exists() is False

    def test_history_load_empty(self, history_dir):
        """测试加载空历史"""
        history = WikiHistory(history_dir)

        assert history._history == {"versions": {}}

    def test_history_load_existing(self, history_dir):
        """测试加载现有历史"""
        history_file = history_dir / "history.json"
        history_file.write_text('{"versions": {"test.md": [{"id": "v_001"}]}}', encoding="utf-8")

        history = WikiHistory(history_dir)

        assert "test.md" in history._history["versions"]

    def test_record_version(self, history, history_dir):
        """测试记录版本"""
        doc_path = Path("/tmp/test.md")
        content = "# Test Document\n\nContent here."

        version_id = history.record_version(doc_path, content)

        assert version_id.startswith("v_")
        assert (history_dir / f"{version_id}.md").exists()
        assert (history_dir / "history.json").exists()

    def test_record_version_with_message(self, history):
        """测试记录版本 - 带消息"""
        doc_path = Path("/tmp/test.md")
        content = "# Test"

        version_id = history.record_version(doc_path, content, message="Initial version")

        versions = history.get_history(doc_path)
        assert len(versions) == 1
        assert versions[0]["message"] == "Initial version"

    def test_record_version_with_author(self, history):
        """测试记录版本 - 带作者"""
        doc_path = Path("/tmp/test.md")
        content = "# Test"

        version_id = history.record_version(doc_path, content, author="user1")

        versions = history.get_history(doc_path)
        assert versions[0]["author"] == "user1"

    def test_record_multiple_versions(self, history):
        """测试记录多个版本"""
        doc_path = Path("/tmp/test.md")

        version_id1 = history.record_version(doc_path, "# Version 1")
        import time
        time.sleep(1.1)
        version_id2 = history.record_version(doc_path, "# Version 2")

        versions = history.get_history(doc_path)
        assert len(versions) == 2
        assert version_id1 != version_id2

    def test_get_history_empty(self, history):
        """测试获取空历史"""
        doc_path = Path("/tmp/nonexistent.md")

        versions = history.get_history(doc_path)

        assert versions == []

    def test_get_history_existing(self, history):
        """测试获取现有历史"""
        doc_path = Path("/tmp/test.md")
        history.record_version(doc_path, "# Test")

        versions = history.get_history(doc_path)

        assert len(versions) == 1
        assert "id" in versions[0]
        assert "timestamp" in versions[0]
        assert "hash" in versions[0]

    def test_get_version(self, history, history_dir):
        """测试获取特定版本"""
        doc_path = Path("/tmp/test.md")
        content = "# Test Content"

        version_id = history.record_version(doc_path, content)
        retrieved = history.get_version(version_id)

        assert retrieved == content

    def test_get_version_nonexistent(self, history):
        """测试获取不存在的版本"""
        result = history.get_version("v_nonexistent")

        assert result is None

    def test_restore_version(self, history, tmp_path):
        """测试恢复版本"""
        doc_path = tmp_path / "test.md"
        doc_path.write_text("# Current", encoding="utf-8")

        version_id = history.record_version(doc_path, "# Old Version")
        doc_path.write_text("# Current", encoding="utf-8")

        result = history.restore_version(doc_path, version_id)

        assert result is True
        assert doc_path.read_text(encoding="utf-8") == "# Old Version"

    def test_restore_version_nonexistent(self, history, tmp_path):
        """测试恢复不存在的版本"""
        doc_path = tmp_path / "test.md"

        result = history.restore_version(doc_path, "v_nonexistent")

        assert result is False

    def test_compare_versions(self, history):
        """测试比较版本"""
        doc_path = Path("/tmp/test.md")

        version_id1 = history.record_version(doc_path, "Line 1\nLine 2\nLine 3")
        import time
        time.sleep(1.1)
        version_id2 = history.record_version(doc_path, "Line 1\nLine Modified\nLine 3")

        result = history.compare_versions(version_id1, version_id2)

        assert result["version1"] == version_id1
        assert result["version2"] == version_id2
        assert "diff" in result
        assert len(result["diff"]) > 0

    def test_compare_versions_identical(self, history):
        """测试比较相同版本"""
        doc_path = Path("/tmp/test.md")

        version_id = history.record_version(doc_path, "Same content")

        result = history.compare_versions(version_id, version_id)

        assert len(result["diff"]) == 0

    def test_compare_versions_nonexistent(self, history):
        """测试比较不存在的版本"""
        result = history.compare_versions("v_001", "v_002")

        assert "error" in result

    def test_compare_versions_different_lengths(self, history):
        """测试比较不同长度的版本"""
        doc_path = Path("/tmp/test.md")

        version_id1 = history.record_version(doc_path, "Line 1\nLine 2")
        version_id2 = history.record_version(doc_path, "Line 1\nLine 2\nLine 3\nLine 4")

        result = history.compare_versions(version_id1, version_id2)

        assert "diff" in result

    def test_cleanup_old_versions(self, history):
        """测试清理旧版本"""
        doc_path = Path("/tmp/test.md")
        import time

        for i in range(15):
            history.record_version(doc_path, f"# Version {i}")
            time.sleep(0.1)

        deleted = history.cleanup_old_versions(keep_count=10)

        assert deleted >= 1
        versions = history.get_history(doc_path)
        assert len(versions) <= 10

    def test_cleanup_old_versions_fewer_than_keep(self, history):
        """测试清理 - 版本数少于保留数"""
        doc_path = Path("/tmp/test.md")

        for i in range(5):
            history.record_version(doc_path, f"# Version {i}")

        deleted = history.cleanup_old_versions(keep_count=10)

        assert deleted == 0
        versions = history.get_history(doc_path)
        assert len(versions) == 5

    def test_cleanup_old_versions_multiple_docs(self, history):
        """测试清理多个文档的旧版本"""
        doc_path1 = Path("/tmp/doc1.md")
        doc_path2 = Path("/tmp/doc2.md")
        import time

        for i in range(15):
            history.record_version(doc_path1, f"# Doc1 v{i}")
            history.record_version(doc_path2, f"# Doc2 v{i}")
            time.sleep(0.1)

        deleted = history.cleanup_old_versions(keep_count=10)

        assert deleted >= 1
        assert len(history.get_history(doc_path1)) <= 10
        assert len(history.get_history(doc_path2)) <= 10

    def test_history_persistence(self, history_dir):
        """测试历史持久化"""
        doc_path = Path("/tmp/test.md")

        history1 = WikiHistory(history_dir)
        history1.record_version(doc_path, "# Test")

        history2 = WikiHistory(history_dir)
        versions = history2.get_history(doc_path)

        assert len(versions) == 1

    def test_version_content_hash(self, history):
        """测试版本内容哈希"""
        doc_path = Path("/tmp/test.md")
        content = "# Test"

        version_id = history.record_version(doc_path, content)
        versions = history.get_history(doc_path)

        assert len(versions[0]["hash"]) == 32

    def test_version_timestamp(self, history):
        """测试版本时间戳"""
        doc_path = Path("/tmp/test.md")

        version_id = history.record_version(doc_path, "# Test")
        versions = history.get_history(doc_path)

        assert "timestamp" in versions[0]
        datetime.fromisoformat(versions[0]["timestamp"])

    def test_version_file_naming(self, history, history_dir):
        """测试版本文件命名"""
        doc_path = Path("/tmp/test.md")

        version_id = history.record_version(doc_path, "# Test")
        version_file = history_dir / f"{version_id}.md"

        assert version_file.exists()
        assert version_file.read_text(encoding="utf-8") == "# Test"

    def test_empty_content_version(self, history):
        """测试空内容版本"""
        doc_path = Path("/tmp/test.md")

        version_id = history.record_version(doc_path, "")

        assert version_id is not None
        assert history.get_version(version_id) == ""

    def test_unicode_content_version(self, history):
        """测试 Unicode 内容版本"""
        doc_path = Path("/tmp/test.md")
        content = "# 测试文档\n\n这是中文内容。"

        version_id = history.record_version(doc_path, content)
        retrieved = history.get_version(version_id)

        assert retrieved == content

    def test_large_content_version(self, history):
        """测试大内容版本"""
        doc_path = Path("/tmp/test.md")
        content = "# Large Document\n\n" + "Line content.\n" * 1000

        version_id = history.record_version(doc_path, content)
        retrieved = history.get_version(version_id)

        assert len(retrieved) == len(content)
