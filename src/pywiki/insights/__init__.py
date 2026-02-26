"""
架构洞察模块
"""

from pywiki.insights.pattern_detector import DesignPatternDetector
from pywiki.insights.tech_stack_analyzer import TechStackAnalyzer
from pywiki.insights.business_logic import BusinessLogicAnalyzer
from pywiki.insights.architecture_evolution import ArchitectureEvolutionTracker

__all__ = [
    "DesignPatternDetector",
    "TechStackAnalyzer",
    "BusinessLogicAnalyzer",
    "ArchitectureEvolutionTracker",
]
