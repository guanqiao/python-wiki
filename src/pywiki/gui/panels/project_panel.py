"""
项目列表面板
"""

from typing import Optional

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QListWidget,
    QListWidgetItem,
    QLabel,
    QFrame,
)
from PyQt6.QtCore import Qt, pyqtSignal

from pywiki.config.models import ProjectConfig


class ProjectPanel(QWidget):
    """项目列表面板"""

    project_selected = pyqtSignal(str)

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._projects: list[ProjectConfig] = []
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        title_label = QLabel("项目列表")
        title_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(title_label)

        self.project_list = QListWidget()
        self.project_list.itemClicked.connect(self._on_item_clicked)
        self.project_list.setFrameShape(QFrame.Shape.StyledPanel)
        layout.addWidget(self.project_list)

        button_layout = QHBoxLayout()

        self.new_button = QPushButton("新建")
        self.new_button.clicked.connect(self._on_new_project)
        button_layout.addWidget(self.new_button)

        self.delete_button = QPushButton("删除")
        self.delete_button.clicked.connect(self._on_delete_project)
        button_layout.addWidget(self.delete_button)

        layout.addLayout(button_layout)

    def set_projects(self, projects: list[ProjectConfig]) -> None:
        self._projects = projects
        self.project_list.clear()

        for project in projects:
            item = QListWidgetItem(project.name)
            item.setData(Qt.ItemDataRole.UserRole, project.name)
            self.project_list.addItem(item)

    def _on_item_clicked(self, item: QListWidgetItem) -> None:
        project_name = item.data(Qt.ItemDataRole.UserRole)
        self.project_selected.emit(project_name)

    def _on_new_project(self) -> None:
        pass

    def _on_delete_project(self) -> None:
        current_item = self.project_list.currentItem()
        if current_item:
            self.project_list.takeItem(self.project_list.row(current_item))
