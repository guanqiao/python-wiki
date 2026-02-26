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
    DocCategory.ARCH