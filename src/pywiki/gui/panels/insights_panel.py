"""
架构洞察面板
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
)
from PyQt6.QtCore import Qt, pyqtSignal


class InsightCard(QFrame):
    """洞察卡片组件"""
    
    def __init__(self, title: str, description: str, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._init_ui(title, description)
    
    def _init_ui(self, title: str, description: str) -> None:
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setStyleSheet("""
            QFrame {
                background-color: #f8f9fa;
                border: 1px solid #e9ecef;
                border-radius: 8px;
                padding: 10px;
                margin: 4px;
            }
            QFrame:hover {
                background-color: #e9ecef;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)
        
        title_label = QLabel(title)
        title_label.setStyleSheet("font-weight: bold; font-size: 14px; color: #212529;")
        layout.addWidget(title_label)
        
        desc_label = QLabel(description)
        desc_label.setStyleSheet("color: #6c757d; font-size: 12px;")
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label)


class InsightsPanel(QWidget):
    """架构洞察面板"""

    analyze_requested = pyqtSignal()

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._project_path: Optional[Path] = None
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        header_layout = QHBoxLayout()
        
        title_label = QLabel("🔍 架构洞察")
        title_label.setStyleSheet("font-weight: bold; font-size: 16px;")
        header_layout.addWidget(title_label)
        
        header_layout.addStretch()
        
        self.analyze_button = QPushButton("分析项目")
        self.analyze_button.setStyleSheet("""
            QPushButton {
                background-color: #6f42c1;
                color: white;
                padding: 6px 16px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #5a32a3;
            }
        """)
        self.analyze_button.clicked.connect(self.analyze_requested.emit)
        header_layout.addWidget(self.analyze_button)
        
        layout.addLayout(header_layout)

        self.tab_widget = QTabWidget()

        patterns_tab = QWidget()
        patterns_layout = QVBoxLayout(patterns_tab)
        
        self.patterns_tree = QTreeWidget()
        self.patterns_tree.setHeaderLabels(["设计模式", "位置", "置信度"])
        self.patterns_tree.setColumnWidth(0, 200)
        self.patterns_tree.setColumnWidth(1, 300)
        self.patterns_tree.setColumnWidth(2, 80)
        patterns_layout.addWidget(self.patterns_tree)
        
        self.tab_widget.addTab(patterns_tab, "📐 设计模式")

        tech_stack_tab = QWidget()
        tech_stack_layout = QVBoxLayout(tech_stack_tab)
        
        self.tech_stack_text = QTextEdit()
        self.tech_stack_text.setReadOnly(True)
        self.tech_stack_text.setStyleSheet("""
            QTextEdit {
                background-color: #f8f9fa;
                border: 1px solid #e9ecef;
                border-radius: 4px;
                padding: 8px;
            }
        """)
        tech_stack_layout.addWidget(self.tech_stack_text)
        
        self.tab_widget.addTab(tech_stack_tab, "🛠️ 技术栈")

        evolution_tab = QWidget()
        evolution_layout = QVBoxLayout(evolution_tab)
        
        self.evolution_tree = QTreeWidget()
        self.evolution_tree.setHeaderLabels(["时间", "变更", "影响"])
        self.evolution_tree.setColumnWidth(0, 150)
        self.evolution_tree.setColumnWidth(1, 300)
        self.evolution_tree.setColumnWidth(2, 150)
        evolution_layout.addWidget(self.evolution_tree)
        
        self.tab_widget.addTab(evolution_tab, "📈 架构演进")

        business_tab = QWidget()
        business_layout = QVBoxLayout(business_tab)
        
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        scroll_layout.setContentsMargins(0, 0, 0, 0)
        
        self.business_cards_layout = QVBoxLayout()
        scroll_layout.addLayout(self.business_cards_layout)
        scroll_layout.addStretch()
        
        scroll_area.setWidget(scroll_widget)
        business_layout.addWidget(scroll_area)
        
        self.tab_widget.addTab(business_tab, "💼 业务逻辑")

        layout.addWidget(self.tab_widget)

    def set_project_path(self, path: Path) -> None:
        """设置项目路径"""
        self._project_path = path

    def update_patterns(self, patterns: list[dict]) -> None:
        """更新设计模式"""
        self.patterns_tree.clear()
        for pattern in patterns:
            item = QTreeWidgetItem([
                pattern.get("name", ""),
                pattern.get("location", ""),
                f"{pattern.get('confidence', 0) * 100:.0f}%"
            ])
            self.patterns_tree.addTopLevelItem(item)

    def update_tech_stack(self, tech_stack: dict) -> None:
        """更新技术栈"""
        content = "# 技术栈分析\n\n"
        for category, items in tech_stack.items():
            content += f"## {category}\n"
            for item in items:
                content += f"- {item}\n"
            content += "\n"
        self.tech_stack_text.setMarkdown(content)

    def update_evolution(self, evolution: list[dict]) -> None:
        """更新架构演进"""
        self.evolution_tree.clear()
        for event in evolution:
            item = QTreeWidgetItem([
                event.get("time", ""),
                event.get("change", ""),
                event.get("impact", "")
            ])
            self.evolution_tree.addTopLevelItem(item)

    def update_business_logic(self, business_logic: list[dict]) -> None:
        """更新业务逻辑"""
        while self.business_cards_layout.count():
            item = self.business_cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        for logic in business_logic:
            card = InsightCard(
                logic.get("name", ""),
                logic.get("description", "")
            )
            self.business_cards_layout.addWidget(card)

    def clear(self) -> None:
        """清空内容"""
        self.patterns_tree.clear()
        self.tech_stack_text.clear()
        self.evolution_tree.clear()
        
        while self.business_cards_layout.count():
            item = self.business_cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
