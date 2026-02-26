"""
隐式知识面板
"""

from typing import Optional
from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QGroupBox,
    QTextEdit,
    QPushButton,
    QTreeWidget,
    QTreeWidgetItem,
    QTabWidget,
    QScrollArea,
    QFrame,
    QComboBox,
)
from PyQt6.QtCore import Qt, pyqtSignal


class KnowledgeCard(QFrame):
    """知识卡片组件"""
    
    def __init__(
        self,
        title: str,
        content: str,
        priority: str = "medium",
        parent: Optional[QWidget] = None
    ):
        super().__init__(parent)
        self._init_ui(title, content, priority)
    
    def _init_ui(self, title: str, content: str, priority: str) -> None:
        priority_colors = {
            "high": "#dc3545",
            "medium": "#ffc107",
            "low": "#28a745",
        }
        border_color = priority_colors.get(priority, "#6c757d")
        
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setStyleSheet(f"""
            QFrame {{
                background-color: #ffffff;
                border-left: 4px solid {border_color};
                border-radius: 4px;
                padding: 10px;
                margin: 4px;
            }}
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 8, 8)
        layout.setSpacing(6)
        
        header_layout = QHBoxLayout()
        
        title_label = QLabel(title)
        title_label.setStyleSheet("font-weight: bold; font-size: 13px;")
        header_layout.addWidget(title_label)
        
        priority_label = QLabel(f"优先级: {priority}")
        priority_label.setStyleSheet(f"color: {border_color}; font-size: 11px;")
        header_layout.addStretch()
        header_layout.addWidget(priority_label)
        
        layout.addLayout(header_layout)
        
        content_label = QLabel(content)
        content_label.setStyleSheet("color: #495057; font-size: 12px;")
        content_label.setWordWrap(True)
        layout.addWidget(content_label)


class KnowledgePanel(QWidget):
    """隐式知识面板"""

    extract_requested = pyqtSignal()
    export_adr_requested = pyqtSignal()

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._project_path: Optional[Path] = None
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        header_layout = QHBoxLayout()
        
        title_label = QLabel("💡 隐式知识")
        title_label.setStyleSheet("font-weight: bold; font-size: 16px;")
        header_layout.addWidget(title_label)
        
        header_layout.addStretch()
        
        self.extract_button = QPushButton("提取知识")
        self.extract_button.setStyleSheet("""
            QPushButton {
                background-color: #17a2b8;
                color: white;
                padding: 6px 16px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #138496;
            }
        """)
        self.extract_button.clicked.connect(self.extract_requested.emit)
        header_layout.addWidget(self.extract_button)
        
        self.export_button = QPushButton("导出 ADR")
        self.export_button.clicked.connect(self.export_adr_requested.emit)
        header_layout.addWidget(self.export_button)
        
        layout.addLayout(header_layout)

        self.tab_widget = QTabWidget()

        decisions_tab = QWidget()
        decisions_layout = QVBoxLayout(decisions_tab)
        
        self.decisions_tree = QTreeWidget()
        self.decisions_tree.setHeaderLabels(["设计决策", "上下文", "状态"])
        self.decisions_tree.setColumnWidth(0, 200)
        self.decisions_tree.setColumnWidth(1, 300)
        self.decisions_tree.setColumnWidth(2, 80)
        decisions_layout.addWidget(self.decisions_tree)
        
        self.tab_widget.addTab(decisions_tab, "📋 设计决策")

        debt_tab = QWidget()
        debt_layout = QVBoxLayout(debt_tab)
        
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        
        scroll_widget = QWidget()
        self.debt_cards_layout = QVBoxLayout(scroll_widget)
        self.debt_cards_layout.setContentsMargins(0, 0, 0, 0)
        self.debt_cards_layout.addStretch()
        
        scroll_area.setWidget(scroll_widget)
        debt_layout.addWidget(scroll_area)
        
        self.tab_widget.addTab(debt_tab, "⚠️ 技术债务")

        motivation_tab = QWidget()
        motivation_layout = QVBoxLayout(motivation_tab)
        
        self.motivation_text = QTextEdit()
        self.motivation_text.setReadOnly(True)
        self.motivation_text.setStyleSheet("""
            QTextEdit {
                background-color: #f8f9fa;
                border: 1px solid #e9ecef;
                border-radius: 4px;
                padding: 8px;
            }
        """)
        motivation_layout.addWidget(self.motivation_text)
        
        self.tab_widget.addTab(motivation_tab, "🎯 设计动机")

        architecture_tab = QWidget()
        architecture_layout = QVBoxLayout(architecture_tab)
        
        self.architecture_tree = QTreeWidget()
        self.architecture_tree.setHeaderLabels(["架构决策", "理由", "影响"])
        self.architecture_tree.setColumnWidth(0, 200)
        self.architecture_tree.setColumnWidth(1, 250)
        self.architecture_tree.setColumnWidth(2, 200)
        architecture_layout.addWidget(self.architecture_tree)
        
        self.tab_widget.addTab(architecture_tab, "🏛️ 架构决策")

        layout.addWidget(self.tab_widget)

    def set_project_path(self, path: Path) -> None:
        """设置项目路径"""
        self._project_path = path

    def update_design_decisions(self, decisions: list[dict]) -> None:
        """更新设计决策"""
        self.decisions_tree.clear()
        for decision in decisions:
            item = QTreeWidgetItem([
                decision.get("title", ""),
                decision.get("context", ""),
                decision.get("status", "")
            ])
            self.decisions_tree.addTopLevelItem(item)

    def update_tech_debt(self, debts: list[dict]) -> None:
        """更新技术债务"""
        while self.debt_cards_layout.count() > 1:
            item = self.debt_cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        for debt in debts:
            card = KnowledgeCard(
                debt.get("title", ""),
                debt.get("description", ""),
                debt.get("priority", "medium")
            )
            self.debt_cards_layout.insertWidget(self.debt_cards_layout.count() - 1, card)

    def update_motivations(self, motivations: str) -> None:
        """更新设计动机"""
        self.motivation_text.setMarkdown(motivations)

    def update_architecture_decisions(self, decisions: list[dict]) -> None:
        """更新架构决策"""
        self.architecture_tree.clear()
        for decision in decisions:
            item = QTreeWidgetItem([
                decision.get("decision", ""),
                decision.get("rationale", ""),
                decision.get("impact", "")
            ])
            self.architecture_tree.addTopLevelItem(item)

    def clear(self) -> None:
        """清空内容"""
        self.decisions_tree.clear()
        self.motivation_text.clear()
        self.architecture_tree.clear()
        
        while self.debt_cards_layout.count() > 1:
            item = self.debt_cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
