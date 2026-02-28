"""
文档生成器模块
对标 Qoder Wiki，支持生成多种类型的文档
"""

from pywiki.generators.docs.base import BaseDocGenerator, DocGeneratorResult
from pywiki.generators.docs.overview_generator import OverviewGenerator
from pywiki.generators.docs.techstack_generator import TechStackGenerator
from pywiki.generators.docs.api_generator import APIGenerator
from pywiki.generators.docs.architecture_generator import ArchitectureDocGenerator
from pywiki.generators.docs.module_generator import ModuleGenerator
from pywiki.generators.docs.dependencies_generator import DependenciesGenerator
from pywiki.generators.docs.config_generator import ConfigGenerator
from pywiki.generators.docs.development_generator import DevelopmentGenerator
from pywiki.generators.docs.deployment_generator import DeploymentGenerator
from pywiki.generators.docs.database_generator import DatabaseGenerator
from pywiki.generators.docs.tsd_generator import TSDGenerator
from pywiki.generators.docs.adr_generator import ADRGenerator
from pywiki.generators.docs.quest_generator import QuestDesignDocGenerator
from pywiki.generators.docs.technical_design_spec_generator import TechnicalDesignSpecGenerator

__all__ = [
    "BaseDocGenerator",
    "DocGeneratorResult",
    "OverviewGenerator",
    "TechStackGenerator",
    "APIGenerator",
    "ArchitectureDocGenerator",
    "ModuleGenerator",
    "DependenciesGenerator",
    "ConfigGenerator",
    "DevelopmentGenerator",
    "DeploymentGenerator",
    "DatabaseGenerator",
    "TSDGenerator",
    "ADRGenerator",
    "QuestDesignDocGenerator",
    "TechnicalDesignSpecGenerator",
]
