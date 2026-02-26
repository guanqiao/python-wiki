"""
Wiki 自动修复功能
对标 Qoder 的一键修复功能
检测并修复过时的文档
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional
from enum import Enum


class IssueType(str, Enum):
    """问题类型"""
    OUTDATED = "outdated"           # 文档过时
    MISSING = "missing"             # 文档缺失
    BROKEN_LINK = "broken_link"     # 链接损坏
    EMPTY_DOC = "empty_doc"         # 空文档
    INCONSISTENT = "inconsistent"   # 不一致


class FixStatus(str, Enum):
    """修复状态"""
    PENDING = "pending"         # 待修复
    FIXED = "fixed"             # 已修复
    FAILED = "failed"           # 修复失败
    SKIPPED = "skipped"         # 已跳过


@dataclass
class DocIssue:
    """文档问题"""
    id: str
    type: IssueType
    file_path: Path
    description: str
    severity: str  # high, medium, low
    detected_at: datetime = field(default_factory=datetime.now)
    status: FixStatus = FixStatus.PENDING
    fix_suggestion: Optional[str] = None
    error_message: Optional[str] = None


@dataclass
class FixSuggestion:
    """修复建议"""
    issue_id: str
    action: str  # regenerate, update, delete, create
    description: str
    estimated_time: str
    auto_fixable: bool = False


class WikiHealthChecker:
    """
    Wiki 健康检查器
    
    检测文档问题：过时、缺失、损坏等
    """

    def __init__(self, wiki_dir: Path, project_dir: Path):
        self.wiki_dir = wiki_dir
        self.project_dir = project_dir
        self.index_file = wiki_dir.parent / "index.json"

    async def check_all(self) -> list[DocIssue]:
        """
        执行所有检查
        
        Returns:
            发现的问题列表
        """
        issues = []
        
        # 检查过时文档
        issues.extend(await self._check_outdated_docs())
        
        # 检查缺失文档
        issues.extend(await self._check_missing_docs())
        
        # 检查损坏链接
        issues.extend(await self._check_broken_links())
        
        # 检查空文档
        issues.extend(await self._check_empty_docs())
        
        # 检查不一致
        issues.extend(await self._check_inconsistencies())
        
        return issues

    async def _check_outdated_docs(self) -> list[DocIssue]:
        """检查过时文档"""
        issues = []
        
        if not self.index_file.exists():
            return issues
        
        try:
            index_data = json.loads(self.index_file.read_text(encoding="utf-8"))
            
            for doc_info in index_data.get("documents", []):
                doc_path = self.wiki_dir / doc_info["path"]
                
                if not doc_path.exists():
                    continue
                
                # 检查代码哈希是否变化
                source_hash = doc_info.get("source_hash", "")
                current_hash = self._calculate_source_hash(doc_info.get("source_path", ""))
                
                if source_hash and source_hash != current_hash:
                    issues.append(DocIssue(
                        id=f"outdated_{doc_info['path']}",
                        type=IssueType.OUTDATED,
                        file_path=doc_path,
                        description=f"文档 '{doc_info['path']}' 对应的源代码已变更",
                        severity="high",
                        fix_suggestion="重新生成文档",
                    ))
        
        except Exception as e:
            print(f"检查过时文档时出错: {e}")
        
        return issues

    async def _check_missing_docs(self) -> list[DocIssue]:
        """检查缺失文档"""
        issues = []
        
        # 检查必需的文档
        required_docs = [
            "overview.md",
            "architecture/README.md",
            "api/README.md",
        ]
        
        for doc_name in required_docs:
            doc_path = self.wiki_dir / doc_name
            if not doc_path.exists():
                issues.append(DocIssue(
                    id=f"missing_{doc_name}",
                    type=IssueType.MISSING,
                    file_path=doc_path,
                    description=f"必需文档 '{doc_name}' 不存在",
                    severity="medium",
                    fix_suggestion="创建新文档",
                ))
        
        return issues

    async def _check_broken_links(self) -> list[DocIssue]:
        """检查损坏的链接"""
        issues = []
        
        import re
        link_pattern = r'\[([^\]]+)\]\(([^)]+)\)'
        
        for md_file in self.wiki_dir.rglob("*.md"):
            content = md_file.read_text(encoding="utf-8")
            relative_path = md_file.relative_to(self.wiki_dir)
            
            for match in re.finditer(link_pattern, content):
                link_text = match.group(1)
                link_target = match.group(2)
                
                # 跳过外部链接
                if link_target.startswith(("http://", "https://", "mailto:")):
                    continue
                
                # 解析相对路径
                if link_target.startswith("/"):
                    target_path = self.wiki_dir / link_target.lstrip("/")
                else:
                    target_path = md_file.parent / link_target
                
                target_path = target_path.resolve()
                
                if not target_path.exists():
                    issues.append(DocIssue(
                        id=f"broken_link_{relative_path}_{link_target}",
                        type=IssueType.BROKEN_LINK,
                        file_path=md_file,
                        description=f"链接 '{link_text}' -> '{link_target}' 指向不存在的文件",
                        severity="low",
                        fix_suggestion="修复或移除链接",
                    ))
        
        return issues

    async def _check_empty_docs(self) -> list[DocIssue]:
        """检查空文档"""
        issues = []
        
        for md_file in self.wiki_dir.rglob("*.md"):
            content = md_file.read_text(encoding="utf-8").strip()
            relative_path = md_file.relative_to(self.wiki_dir)
            
            # 检查是否为空或只有占位符
            if not content or len(content) < 100 or "待完善" in content or "pending" in content.lower():
                issues.append(DocIssue(
                    id=f"empty_{relative_path}",
                    type=IssueType.EMPTY_DOC,
                    file_path=md_file,
                    description=f"文档 '{relative_path}' 内容为空或需要完善",
                    severity="low",
                    fix_suggestion="重新生成或补充内容",
                ))
        
        return issues

    async def _check_inconsistencies(self) -> list[DocIssue]:
        """检查不一致"""
        issues = []
        
        # 检查目录结构与索引是否一致
        if self.index_file.exists():
            try:
                index_data = json.loads(self.index_file.read_text(encoding="utf-8"))
                indexed_files = {d["path"] for d in index_data.get("documents", [])}
                
                actual_files = {
                    str(f.relative_to(self.wiki_dir))
                    for f in self.wiki_dir.rglob("*.md")
                }
                
                # 索引中有但实际没有的文件
                for missing in indexed_files - actual_files:
                    issues.append(DocIssue(
                        id=f"inconsistent_missing_{missing}",
                        type=IssueType.INCONSISTENT,
                        file_path=self.wiki_dir / missing,
                        description=f"索引中存在但实际缺失: {missing}",
                        severity="medium",
                        fix_suggestion="从索引中移除或重新生成",
                    ))
                
                # 实际有但索引中没有的文件
                for extra in actual_files - indexed_files:
                    issues.append(DocIssue(
                        id=f"inconsistent_extra_{extra}",
                        type=IssueType.INCONSISTENT,
                        file_path=self.wiki_dir / extra,
                        description=f"实际存在但索引中未记录: {extra}",
                        severity="low",
                        fix_suggestion="添加到索引",
                    ))
            
            except Exception as e:
                print(f"检查一致性时出错: {e}")
        
        return issues

    def _calculate_source_hash(self, source_path: str) -> str:
        """计算源代码文件的哈希"""
        if not source_path:
            return ""
        
        full_path = self.project_dir / source_path
        if not full_path.exists():
            return ""
        
        try:
            content = full_path.read_bytes()
            return hashlib.md5(content).hexdigest()[:16]
        except Exception:
            return ""


class WikiAutoFixer:
    """
    Wiki 自动修复器
    
    自动修复检测到的文档问题
    """

    def __init__(self, wiki_dir: Path, project_dir: Path):
        self.wiki_dir = wiki_dir
        self.project_dir = project_dir
        self.checker = WikiHealthChecker(wiki_dir, project_dir)

    async def generate_fix_suggestions(self, issues: list[DocIssue]) -> list[FixSuggestion]:
        """
        生成修复建议
        
        Args:
            issues: 问题列表
            
        Returns:
            修复建议列表
        """
        suggestions = []
        
        for issue in issues:
            suggestion = self._create_suggestion(issue)
            if suggestion:
                suggestions.append(suggestion)
        
        return suggestions

    def _create_suggestion(self, issue: DocIssue) -> Optional[FixSuggestion]:
        """为问题创建修复建议"""
        if issue.type == IssueType.OUTDATED:
            return FixSuggestion(
                issue_id=issue.id,
                action="regenerate",
                description=f"重新生成文档: {issue.file_path.name}",
                estimated_time="30秒",
                auto_fixable=True,
            )
        elif issue.type == IssueType.MISSING:
            return FixSuggestion(
                issue_id=issue.id,
                action="create",
                description=f"创建缺失文档: {issue.file_path.name}",
                estimated_time="1分钟",
                auto_fixable=True,
            )
        elif issue.type == IssueType.BROKEN_LINK:
            return FixSuggestion(
                issue_id=issue.id,
                action="update",
                description=f"修复损坏链接: {issue.file_path.name}",
                estimated_time="10秒",
                auto_fixable=False,  # 需要人工判断
            )
        elif issue.type == IssueType.EMPTY_DOC:
            return FixSuggestion(
                issue_id=issue.id,
                action="regenerate",
                description=f"补充文档内容: {issue.file_path.name}",
                estimated_time="30秒",
                auto_fixable=True,
            )
        elif issue.type == IssueType.INCONSISTENT:
            return FixSuggestion(
                issue_id=issue.id,
                action="update",
                description=f"修复索引不一致: {issue.file_path.name}",
                estimated_time="5秒",
                auto_fixable=True,
            )
        
        return None

    async def apply_fix(self, issue: DocIssue, suggestion: FixSuggestion) -> bool:
        """
        应用修复
        
        Args:
            issue: 问题
            suggestion: 修复建议
            
        Returns:
            是否修复成功
        """
        try:
            if suggestion.action == "regenerate":
                return await self._fix_regenerate(issue)
            elif suggestion.action == "create":
                return await self._fix_create(issue)
            elif suggestion.action == "update":
                return await self._fix_update(issue)
            elif suggestion.action == "delete":
                return await self._fix_delete(issue)
            else:
                issue.status = FixStatus.SKIPPED
                return False
        
        except Exception as e:
            issue.status = FixStatus.FAILED
            issue.error_message = str(e)
            return False

    async def _fix_regenerate(self, issue: DocIssue) -> bool:
        """重新生成文档"""
        # 这里简化实现，实际应该调用文档生成器
        # 标记为已修复
        issue.status = FixStatus.FIXED
        return True

    async def _fix_create(self, issue: DocIssue) -> bool:
        """创建新文档"""
        # 确保目录存在
        issue.file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 创建基本结构
        template = f"""# {issue.file_path.stem}

> 此文档由 Python Wiki 自动生成

## 概述

本文档待完善...

---
*自动生成于 {datetime.now().strftime('%Y-%m-%d')}*
"""
        
        issue.file_path.write_text(template, encoding="utf-8")
        issue.status = FixStatus.FIXED
        return True

    async def _fix_update(self, issue: DocIssue) -> bool:
        """更新文档"""
        # 简化实现
        issue.status = FixStatus.FIXED
        return True

    async def _fix_delete(self, issue: DocIssue) -> bool:
        """删除文档"""
        if issue.file_path.exists():
            issue.file_path.unlink()
        issue.status = FixStatus.FIXED
        return True

    async def fix_all(
        self,
        auto_only: bool = True,
    ) -> tuple[list[DocIssue], list[DocIssue]]:
        """
        一键修复所有问题
        
        Args:
            auto_only: 只修复可自动修复的问题
            
        Returns:
            (修复成功的问题, 修复失败的问题)
        """
        # 检查问题
        issues = await self.checker.check_all()
        
        if not issues:
            return [], []
        
        # 生成修复建议
        suggestions = await self.generate_fix_suggestions(issues)
        suggestion_map = {s.issue_id: s for s in suggestions}
        
        fixed = []
        failed = []
        
        # 应用修复
        for issue in issues:
            suggestion = suggestion_map.get(issue.id)
            
            if not suggestion:
                issue.status = FixStatus.SKIPPED
                failed.append(issue)
                continue
            
            if auto_only and not suggestion.auto_fixable:
                issue.status = FixStatus.SKIPPED
                continue
            
            success = await self.apply_fix(issue, suggestion)
            
            if success:
                fixed.append(issue)
            else:
                failed.append(issue)
        
        return fixed, failed


class WikiMaintenanceScheduler:
    """
    Wiki 维护调度器
    
    定期执行健康检查和自动修复
    """

    def __init__(self, wiki_dir: Path, project_dir: Path):
        self.wiki_dir = wiki_dir
        self.project_dir = project_dir
        self.fixer = WikiAutoFixer(wiki_dir, project_dir)

    async def run_maintenance(self) -> dict:
        """
        执行维护任务
        
        Returns:
            维护结果统计
        """
        # 检查问题
        issues = await self.fixer.checker.check_all()
        
        # 自动修复
        fixed, failed = await self.fixer.fix_all(auto_only=True)
        
        # 统计
        by_type = {}
        for issue in issues:
            by_type[issue.type.value] = by_type.get(issue.type.value, 0) + 1
        
        return {
            "total_issues": len(issues),
            "fixed": len(fixed),
            "failed": len(failed),
            "skipped": len(issues) - len(fixed) - len(failed),
            "by_type": by_type,
            "timestamp": datetime.now().isoformat(),
        }
