"""
Git 原生变更检测器
使用 GitPython 实现基于 Git 的变更检测
"""

import hashlib
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Optional

from git import Repo, Commit, Diff, GitCommandError


class ChangeType(str, Enum):
    ADDED = "added"
    MODIFIED = "modified"
    DELETED = "deleted"
    RENAMED = "renamed"
    UNTRACKED = "untracked"


@dataclass
class FileChange:
    file_path: Path
    change_type: ChangeType
    old_path: Optional[Path] = None
    commit_hash: Optional[str] = None
    commit_message: Optional[str] = None
    author: Optional[str] = None
    timestamp: Optional[datetime] = None
    diff_content: Optional[str] = None
    additions: int = 0
    deletions: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "file_path": str(self.file_path),
            "change_type": self.change_type.value,
            "old_path": str(self.old_path) if self.old_path else None,
            "commit_hash": self.commit_hash,
            "commit_message": self.commit_message,
            "author": self.author,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "additions": self.additions,
            "deletions": self.deletions,
        }


@dataclass
class CommitInfo:
    hash: str
    message: str
    author: str
    email: str
    timestamp: datetime
    files_changed: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "hash": self.hash,
            "message": self.message,
            "author": self.author,
            "email": self.email,
            "timestamp": self.timestamp.isoformat(),
            "files_changed": self.files_changed,
        }


class GitChangeDetector:
    """
    Git 原生变更检测器
    基于 Git diff 实现精确的变更检测
    """

    def __init__(self, repo_path: Path):
        self.repo_path = Path(repo_path)
        self._repo: Optional[Repo] = None

    @property
    def repo(self) -> Repo:
        """获取 Git 仓库实例"""
        if self._repo is None:
            self._repo = Repo(self.repo_path)
        return self._repo

    def get_current_branch(self) -> str:
        """获取当前分支名"""
        try:
            return self.repo.active_branch.name
        except TypeError:
            return "HEAD"

    def get_current_commit(self) -> Optional[CommitInfo]:
        """获取当前 commit 信息"""
        try:
            commit = self.repo.head.commit
            return CommitInfo(
                hash=commit.hexsha,
                message=commit.message.strip(),
                author=commit.author.name,
                email=commit.author.email,
                timestamp=datetime.fromtimestamp(commit.committed_date),
                files_changed=[item.a_path for item in commit.stats.files.keys()],
            )
        except Exception:
            return None

    def get_changes_since_commit(
        self,
        commit_hash: str,
        file_patterns: Optional[list[str]] = None,
    ) -> list[FileChange]:
        """
        获取自指定 commit 以来的变更

        Args:
            commit_hash: 起始 commit hash
            file_patterns: 文件模式过滤（如 ["*.py", "*.ts"]）

        Returns:
            变更文件列表
        """
        changes = []

        try:
            commit = self.repo.commit(commit_hash)
            diffs = commit.diff(self.repo.head.commit)

            for diff in diffs:
                change = self._diff_to_change(diff)
                if change:
                    if file_patterns:
                        if not any(
                            change.file_path.match(pattern)
                            for pattern in file_patterns
                        ):
                            continue
                    changes.append(change)

        except GitCommandError:
            pass

        return changes

    def get_changes_between_commits(
        self,
        from_commit: str,
        to_commit: str,
        file_patterns: Optional[list[str]] = None,
    ) -> list[FileChange]:
        """获取两个 commit 之间的变更"""
        changes = []

        try:
            from_c = self.repo.commit(from_commit)
            to_c = self.repo.commit(to_commit)
            diffs = from_c.diff(to_c)

            for diff in diffs:
                change = self._diff_to_change(diff)
                if change:
                    if file_patterns:
                        if not any(
                            change.file_path.match(pattern)
                            for pattern in file_patterns
                        ):
                            continue
                    changes.append(change)

        except GitCommandError:
            pass

        return changes

    def get_uncommitted_changes(
        self,
        include_untracked: bool = True,
        file_patterns: Optional[list[str]] = None,
    ) -> list[FileChange]:
        """
        获取未提交的变更

        Args:
            include_untracked: 是否包含未跟踪文件
            file_patterns: 文件模式过滤

        Returns:
            变更文件列表
        """
        changes = []

        for item in self.repo.index.diff(None):
            change = self._diff_to_change(item)
            if change:
                if file_patterns:
                    if not any(
                        change.file_path.match(pattern)
                        for pattern in file_patterns
                    ):
                        continue
                changes.append(change)

        if include_untracked:
            for file_path in self.repo.untracked_files:
                path = self.repo_path / file_path
                if file_patterns:
                    if not any(path.match(pattern) for pattern in file_patterns):
                        continue

                changes.append(FileChange(
                    file_path=path,
                    change_type=ChangeType.UNTRACKED,
                ))

        return changes

    def get_staged_changes(
        self,
        file_patterns: Optional[list[str]] = None,
    ) -> list[FileChange]:
        """获取已暂存的变更"""
        changes = []

        try:
            diffs = self.repo.index.diff(self.repo.head.commit)

            for diff in diffs:
                change = self._diff_to_change(diff)
                if change:
                    if file_patterns:
                        if not any(
                            change.file_path.match(pattern)
                            for pattern in file_patterns
                        ):
                            continue
                    changes.append(change)

        except Exception:
            pass

        return changes

    def get_file_history(
        self,
        file_path: Path,
        limit: int = 10,
    ) -> list[CommitInfo]:
        """
        获取文件的历史记录

        Args:
            file_path: 文件路径
            limit: 返回数量限制

        Returns:
            commit 信息列表
        """
        commits = []

        try:
            relative_path = file_path.relative_to(self.repo_path)

            for commit in self.repo.iter_commits(
                paths=str(relative_path),
                max_count=limit,
            ):
                commits.append(CommitInfo(
                    hash=commit.hexsha,
                    message=commit.message.strip(),
                    author=commit.author.name,
                    email=commit.author.email,
                    timestamp=datetime.fromtimestamp(commit.committed_date),
                ))

        except Exception:
            pass

        return commits

    def get_commit_info(self, commit_hash: str) -> Optional[CommitInfo]:
        """获取 commit 详细信息"""
        try:
            commit = self.repo.commit(commit_hash)
            return CommitInfo(
                hash=commit.hexsha,
                message=commit.message.strip(),
                author=commit.author.name,
                email=commit.author.email,
                timestamp=datetime.fromtimestamp(commit.committed_date),
                files_changed=list(commit.stats.files.keys()),
            )
        except Exception:
            return None

    def get_file_content_at_commit(
        self,
        file_path: Path,
        commit_hash: str,
    ) -> Optional[str]:
        """获取文件在指定 commit 时的内容"""
        try:
            relative_path = file_path.relative_to(self.repo_path)
            commit = self.repo.commit(commit_hash)
            blob = commit.tree / str(relative_path)
            return blob.data_stream.read().decode("utf-8")
        except Exception:
            return None

    def get_diff_content(
        self,
        file_path: Path,
        from_commit: Optional[str] = None,
        to_commit: Optional[str] = None,
    ) -> Optional[str]:
        """
        获取文件的 diff 内容

        Args:
            file_path: 文件路径
            from_commit: 起始 commit（None 表示工作区）
            to_commit: 结束 commit（None 表示暂存区）

        Returns:
            diff 内容字符串
        """
        try:
            relative_path = str(file_path.relative_to(self.repo_path))

            if from_commit and to_commit:
                from_c = self.repo.commit(from_commit)
                to_c = self.repo.commit(to_commit)
                diff = from_c.diff(to_c, paths=relative_path)
            elif from_commit:
                from_c = self.repo.commit(from_commit)
                diff = from_c.diff(None, paths=relative_path)
            else:
                diff = self.repo.index.diff(None, paths=relative_path)

            if diff:
                return diff[0].diff.decode("utf-8")

        except Exception:
            pass

        return None

    def _diff_to_change(self, diff: Diff) -> Optional[FileChange]:
        """将 Git Diff 转换为 FileChange"""
        try:
            if diff.new_file:
                return FileChange(
                    file_path=self.repo_path / diff.a_path,
                    change_type=ChangeType.ADDED,
                )
            elif diff.deleted_file:
                return FileChange(
                    file_path=self.repo_path / diff.a_path,
                    change_type=ChangeType.DELETED,
                )
            elif diff.renamed_file:
                return FileChange(
                    file_path=self.repo_path / diff.b_path,
                    change_type=ChangeType.RENAMED,
                    old_path=self.repo_path / diff.a_path,
                )
            else:
                change = FileChange(
                    file_path=self.repo_path / diff.a_path,
                    change_type=ChangeType.MODIFIED,
                )

                try:
                    diff_text = diff.diff.decode("utf-8") if diff.diff else ""
                    change.additions = diff_text.count("\n+")
                    change.deletions = diff_text.count("\n-")
                    change.diff_content = diff_text
                except Exception:
                    pass

                return change

        except Exception:
            return None

    def get_recent_commits(self, limit: int = 10) -> list[CommitInfo]:
        """获取最近的 commits"""
        commits = []

        try:
            for commit in self.repo.iter_commits(max_count=limit):
                commits.append(CommitInfo(
                    hash=commit.hexsha,
                    message=commit.message.strip(),
                    author=commit.author.name,
                    email=commit.author.email,
                    timestamp=datetime.fromtimestamp(commit.committed_date),
                ))
        except Exception:
            pass

        return commits

    def get_changed_files_stats(
        self,
        since_commit: Optional[str] = None,
    ) -> dict[str, Any]:
        """获取变更统计"""
        stats = {
            "total_files": 0,
            "by_type": {},
            "by_author": {},
        }

        changes = []
        if since_commit:
            changes = self.get_changes_since_commit(since_commit)
        else:
            changes = self.get_uncommitted_changes()

        for change in changes:
            stats["total_files"] += 1

            type_key = change.change_type.value
            stats["by_type"][type_key] = stats["by_type"].get(type_key, 0) + 1

            if change.author:
                stats["by_author"][change.author] = stats["by_author"].get(change.author, 0) + 1

        return stats

    def is_ancestor(self, commit1: str, commit2: str) -> bool:
        """检查 commit1 是否是 commit2 的祖先"""
        try:
            return self.repo.is_ancestor(commit1, commit2)
        except Exception:
            return False

    def get_merge_base(self, branch1: str, branch2: str) -> Optional[str]:
        """获取两个分支的合并基点"""
        try:
            base = self.repo.merge_base(branch1, branch2)
            return base[0].hexsha if base else None
        except Exception:
            return None
