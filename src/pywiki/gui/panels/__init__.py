"""
GUI 面板模块
"""

from pywiki.gui.panels.project_panel import ProjectPanel
from pywiki.gui.panels.config_panel import ConfigPanel
from pywiki.gui.panels.preview_panel import PreviewPanel
from pywiki.gui.panels.progress_panel import ProgressPanel
from pywiki.gui.panels.qa_panel import QAPanel
from pywiki.gui.panels.doc_type_panel import DocTypePanel
from pywiki.gui.panels.insights_panel import InsightsPanel
from pywiki.gui.panels.knowledge_panel import KnowledgePanel

__all__ = [
    "ProjectPanel",
    "ConfigPanel",
    "PreviewPanel",
    "ProgressPanel",
    "QAPanel",
    "DocTypePanel",
    "InsightsPanel",
    "KnowledgePanel",
]