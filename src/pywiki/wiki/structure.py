"""
Wiki 目录结构管理器
支持多语言和标准化的目录结构（对标 Qoder Wiki）
"""

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional

from pywiki.config.models import Language


class DocCategory(str, Enum):
    """文档分类"""
    OVERVIEW = "01-Overview"           # 项目概述
    ARCHITECTURE = "02-Architecture"   # 架构文档
    MODULES = "03-Modules"             # 模块文档
    DATABASE = "04-Database"           # 数据库文档
    API = "05-API"                     # API 文档
    CONFIGURATION = "06-Configuration" # 配置文档
    DEVELOPMENT = "07-Development"     # 开发文档
    DEPENDENCIES = "08-Dependencies"   # 依赖文档
    DESIGN_DECISIONS = "09-Design-Decisions"  # 设计决策


@dataclass
class WikiStructureConfig:
    """Wiki 结构配置"""
    # 基础目录名
    base_dir: str = ".python-wiki/repowiki"
    # 是否使用多语言
    multi_language: bool = True
    # 默认语言
    default_language: Language = Language.ZH
    # 支持的语言列表
    languages: list[Language] = field(default_factory=lambda: [Language.ZH])
    # 是否使用序号前缀
    use_numbering: bool = True
    # 是否创建 README.md 作为入口
    create_readme: bool = True


@dataclass
class WikiDirectory:
    """Wiki 目录定义"""
    name: str
    description: str
    default_files: list[str] = field(default_factory=list)
    subdirectories: list[str] = field(default_factory=list)


# 标准 Wiki 目录结构定义（对标 Qoder）
WIKI_DIRECTORIES: dict[DocCategory, WikiDirectory] = {
    DocCategory.OVERVIEW: WikiDirectory(
        name="01-Overview",
        description="项目概述和基本信息",
        default_files=[
            "README.md",           # 目录入口
            "features.md",         # 功能特性
            "quick-start.md",      # 快速开始
            "changelog.md",        # 变更日志
        ],
    ),
    DocCategory.ARCHITECTURE: WikiDirectory(
        name="02-Architecture",
        description="系统架构文档",
        default_files=[
            "README.md",
            "system-context.md",   # C4 上下文图
            "container-diagram.md", # C4 容器图
            "component-diagrams.md", # C4 组件图
            "code-diagrams.md",    # C4 代码图/类图
        ],
        subdirectories=[
            "diagrams",            # 架构图表
            "decisions",           # 架构决策
        ],
    ),
    DocCategory.MODULES: WikiDirectory(
        name="03-Modules",
        description="模块详细文档",
        default_files=[
            "README.md",
        ],
        # 子目录动态创建，每个模块一个子目录
    ),
    DocCategory.DATABASE: WikiDirectory(
        name="04-Database",
        description="数据库文档",
        default_files=[
            "README.md",
            "schema.md",           # 数据库 Schema
            "er-diagram.md",       # ER 图
            "migrations.md",       # 迁移记录
        ],
        subdirectories=[
            "entities",            # 实体定义
            "diagrams",            # 数据库图表
        ],
    ),
    DocCategory.API: WikiDirectory(
        name="05-API",
        description="API 接口文档",
        default_files=[
            "README.md",
            "overview.md",         # API 概览
        ],
        subdirectories=[
            "endpoints",           # 端点文档
            "schemas",             # 数据模型
            "examples",            # 请求示例
        ],
    ),
    DocCategory.CONFIGURATION: WikiDirectory(
        name="06-Configuration",
        description="配置文档",
        default_files=[
            "README.md",
            "environment.md",      # 环境变量
            "settings.md",         # 配置项说明
            "deployment.md",       # 部署配置
        ],
    ),
    DocCategory.DEVELOPMENT: WikiDirectory(
        name="07-Development",
        description="开发指南",
        default_files=[
            "README.md",
            "setup.md",            # 环境搭建
            "coding-guidelines.md", # 编码规范
            "testing.md",          # 测试指南
            "contributing.md",     # 贡献指南
        ],
        subdirectories=[
            "guides",              # 开发教程
            "troubleshooting",     # 故障排查
        ],
    ),
    DocCategory.DEPENDENCIES: WikiDirectory(
        name="08-Dependencies",
        description="依赖关系文档",
        default_files=[
            "README.md",
            "internal.md",         # 内部依赖
            "external.md",         # 外部依赖
            "dependency-graph.md", # 依赖图
        ],
    ),
    DocCategory.DESIGN_DECISIONS: WikiDirectory(
        name="09-Design-Decisions",
        description="设计决策记录 (ADR)",
        default_files=[
            "README.md",
        ],
        # 子目录动态创建，每个 ADR 一个文件
    ),
}


class WikiStructureManager:
    """Wiki 目录结构管理器"""

    def __init__(self, config: Optional[WikiStructureConfig] = None):
        self.config = config or WikiStructureConfig()

    def get_wiki_root(self, project_path: Path, language: Optional[Language] = None) -> Path:
        """
        获取 Wiki 根目录路径
        
        Args:
            project_path: 项目路径
            language: 语言，如果启用多语言则创建子目录
            
        Returns:
            Wiki 根目录路径
        """
        wiki_root = project_path / self.config.base_dir

        if self.config.multi_language and language:
            wiki_root = wiki_root / language.value

        return wiki_root

    def create_structure(
        self,
        project_path: Path,
        languages: Optional[list[Language]] = None,
    ) -> dict[Language, Path]:
        """
        创建完整的 Wiki 目录结构
        
        Args:
            project_path: 项目路径
            languages: 语言列表，默认使用配置中的语言
            
        Returns:
            语言到 Wiki 根目录的映射
        """
        languages = languages or self.config.languages
        created_paths = {}

        for language in languages:
            wiki_root = self.get_wiki_root(project_path, language)
            created_paths[language] = wiki_root

            # 创建主目录
            for category, directory in WIKI_DIRECTORIES.items():
                dir_path = wiki_root / directory.name
                dir_path.mkdir(parents=True, exist_ok=True)

                # 创建默认文件
                for file_name in directory.default_files:
                    file_path = dir_path / file_name
                    if not file_path.exists():
                        content = self._generate_default_content(
                            file_name, directory, language
                        )
                        file_path.write_text(content, encoding="utf-8")

                # 创建子目录
                for subdir in directory.subdirectories:
                    (dir_path / subdir).mkdir(exist_ok=True)

            # 创建根 README.md
            if self.config.create_readme:
                readme_path = wiki_root / "README.md"
                if not readme_path.exists():
                    content = self._generate_root_readme(language)
                    readme_path.write_text(content, encoding="utf-8")

        return created_paths

    def get_category_path(
        self,
        project_path: Path,
        category: DocCategory,
        language: Optional[Language] = None,
    ) -> Path:
        """
        获取指定分类的目录路径
        
        Args:
            project_path: 项目路径
            category: 文档分类
            language: 语言
            
        Returns:
            分类目录路径
        """
        wiki_root = self.get_wiki_root(project_path, language)
        directory = WIKI_DIRECTORIES[category]
        return wiki_root / directory.name

    def get_module_path(
        self,
        project_path: Path,
        module_name: str,
        language: Optional[Language] = None,
    ) -> Path:
        """
        获取模块文档路径
        
        Args:
            project_path: 项目路径
            module_name: 模块名称
            language: 语言
            
        Returns:
            模块文档目录路径
        """
        modules_path = self.get_category_path(project_path, DocCategory.MODULES, language)
        return modules_path / module_name.replace(".", "_")

    def get_adr_path(
        self,
        project_path: Path,
        adr_number: int,
        title: str,
        language: Optional[Language] = None,
    ) -> Path:
        """
        获取 ADR 文档路径
        
        Args:
            project_path: 项目路径
            adr_number: ADR 编号
            title: ADR 标题
            language: 语言
            
        Returns:
            ADR 文件路径
        """
        decisions_path = self.get_category_path(
            project_path, DocCategory.DESIGN_DECISIONS, language
        )
        file_name = f"adr-{adr_number:04d}-{title.lower().replace(' ', '-')}.md"
        return decisions_path / file_name

    def _generate_default_content(
        self,
        file_name: str,
        directory: WikiDirectory,
        language: Language,
    ) -> str:
        """生成默认文件内容"""
        title = file_name.replace(".md", "").replace("-", " ").title()

        if language == Language.ZH:
            return f"""# {title}

> {directory.description}

## 概述

本文档待完善...

## 相关内容

- [返回上级](../README.md)

---
*自动生成于 Python Wiki*
"""
        else:
            return f"""# {title}

> {directory.description}

## Overview

This document is pending...

## Related

- [Parent Directory](../README.md)

---
*Generated by Python Wiki*
"""

    def _generate_root_readme(self, language: Language) -> str:
        """生成根 README.md 内容"""
        if language == Language.ZH:
            content = """# 项目 Wiki

> 本项目文档由 Python Wiki 自动生成

## 目录

"""
            for category, directory in WIKI_DIRECTORIES.items():
                content += f"- [{directory.name}](./{directory.name}/README.md) - {directory.description}\n"

            content += """
## 使用说明

本文档库包含项目的完整技术文档，包括：

- **项目概述** - 功能特性、快速开始
- **架构文档** - 系统架构图、设计决策
- **模块文档** - 各模块详细说明
- **数据库文档** - Schema、ER 图
- **API 文档** - 接口定义、使用示例
- **配置文档** - 环境配置、部署说明
- **开发文档** - 开发指南、编码规范
- **依赖文档** - 内部/外部依赖关系
- **设计决策** - 架构决策记录 (ADR)

## 更新说明

本文档与代码库保持同步，当代码变更时会自动更新。

---
*Generated by Python Wiki*
"""
        else:
            content = """# Project Wiki

> This documentation is auto-generated by Python Wiki

## Table of Contents

"""
            for category, directory in WIKI_DIRECTORIES.items():
                content += f"- [{directory.name}](./{directory.name}/README.md) - {directory.description}\n"

            content += """
## Usage

This wiki contains complete technical documentation for the project.

## Updates

This documentation stays in sync with the codebase and updates automatically when code changes.

---
*Generated by Python Wiki*
"""

        return content

    def migrate_from_old_structure(
        self,
        project_path: Path,
        old_wiki_dir: Path,
        language: Language = Language.ZH,
    ) -> Path:
        """
        从旧结构迁移到新结构
        
        Args:
            project_path: 项目路径
            old_wiki_dir: 旧 Wiki 目录
            language: 语言
            
        Returns:
            新的 Wiki 根目录
        """
        # 创建新结构
        new_paths = self.create_structure(project_path, [language])
        new_root = new_paths[language]

        # 迁移文件映射（简化版）
        migration_map = {
            "overview.md": (DocCategory.OVERVIEW, "README.md"),
            "tech-stack.md": (DocCategory.OVERVIEW, "tech-stack.md"),
            "architecture.md": (DocCategory.ARCHITECTURE, "README.md"),
            "api.md": (DocCategory.API, "README.md"),
            "database.md": (DocCategory.DATABASE, "README.md"),
            "configuration.md": (DocCategory.CONFIGURATION, "README.md"),
            "development.md": (DocCategory.DEVELOPMENT, "README.md"),
            "dependencies.md": (DocCategory.DEPENDENCIES, "README.md"),
            "tsd.md": (DocCategory.DESIGN_DECISIONS, "README.md"),
        }

        # 迁移文件
        for old_file, (category, new_file) in migration_map.items():
            old_path = old_wiki_dir / old_file
            if old_path.exists():
                new_dir = self.get_category_path(project_path, category, language)
                new_path = new_dir / new_file
                if not new_path.exists():
                    content = old_path.read_text(encoding="utf-8")
                    new_path.write_text(content, encoding="utf-8")

        return new_root
