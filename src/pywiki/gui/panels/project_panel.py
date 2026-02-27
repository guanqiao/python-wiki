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
    QMenu,
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QAction

from pywiki.config.models import ProjectConfig


class ProjectItemWidget(QFrame):
    """项目项组件"""
    
    clicked = pyqtSignal(str)
    double_clicked = pyqtSignal(str)
    
    def __init__(self, project: ProjectConfig, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.project = project
        self._init_ui()
    
    def _init_ui(self) -> None:
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setStyleSheet("""
            QFrame {
                background-color: #f8f9fa;
                border: 1px solid #e9ecef;
                border-radius: 5px;
                padding: 5px;
                margin: 2px;
            }
            QFrame:hover {
                background-color: #e9ecef;
                border-color: #dee2e6;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(4)
        
        header_layout = QHBoxLayout()
        
        self.name_label = QLabel(f"📁 {self.project.name}")
        self.name_label.setStyleSheet("font-weight: bold; font-size: 13px;")
        header_layout.addWidget(self.name_label)
        
        self.status_label = QLabel()
        self._update_status()
        header_layout.addWidget(self.status_label)
        header_layout.addStretch()
        
        layout.addLayout(header_layout)
        
        self.path_label = QLabel(f"📂 {self.project.path}")
        self.path_label.setStyleSheet("color: #6c757d; font-size: 11px;")
        self.path_label.setWordWrap(True)
        layout.addWidget(self.path_label)
        
        if self.project.description:
            self.desc_label = QLabel(f"📝 {self.project.description}")
            self.desc_label.setStyleSheet("color: #495057; font-size: 11px;")
            self.desc_label.setWordWrap(True)
            layout.addWidget(self.desc_label)
    
    def _update_status(self) -> None:
        has_llm = bool(self.project.llm and self.project.llm.api_key)
        if has_llm:
            self.status_label.setText("✅ 已配置")
            self.status_label.setStyleSheet("color: #28a745; font-size: 11px;")
        else:
            self.status_label.setText("⚠️ 未配置 LLM")
            self.status_label.setStyleSheet("color: #ffc107; font-size: 11px;")


class ProjectPanel(QWidget):
    """项目列表面板"""

    project_selected = pyqtSignal(str)
    project_double_clicked = pyqtSignal(str)
    open_project_dir = pyqtSignal(str)
    configure_llm = pyqtSignal(str)
    delete_project = pyqtSignal(str)

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._projects: list[ProjectConfig] = []
        self._project_widgets: dict[str, ProjectItemWidget] = {}
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        title_label = QLabel("项目列表")
        title_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(title_label)

        self.project_list = QListWidget()
        self.project_list.setFrameShape(QFrame.Shape.NoFrame)
        self.project_list.setSpacing(2)
        self.project_list.itemClicked.connect(self._on_item_clicked)
        self.project_list.itemDoubleClicked.connect(self._on_item_double_clicked)
        self.project_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.project_list.customContextMenuRequested.connect(self._show_context_menu)
        layout.addWidget(self.project_list)

        button_layout = QHBoxLayout()

        self.new_button = QPushButton("➕ 新建项目")
        self.new_button.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                padding: 6px 12px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #218838;
            }
        """)
        self.new_button.clicked.connect(self._on_new_project)
        button_layout.addWidget(self.new_button)

        self.open_button = QPushButton("📂 打开目录")
        self.open_button.clicked.connect(self._on_open_dir)
        button_layout.addWidget(self.open_button)

        layout.addLayout(button_layout)

    def set_projects(self, projects: list[ProjectConfig]) -> None:
        self._projects = projects
        self.project_list.clear()
        self._project_widgets.clear()

        for project in projects:
            item = QListWidgetItem(self.project_list)
            item.setData(Qt.ItemDataRole.UserRole, project.name)
            
            widget = ProjectItemWidget(project)
            widget.adjustSize()
            item.setSizeHint(widget.sizeHint())
            
            self.project_list.setItemWidget(item, widget)
            self._project_widgets[project.name] = widget

    def _on_item_clicked(self, item: QListWidgetItem) -> None:
        project_name = item.data(Qt.ItemDataRole.UserRole)
        self.project_selected.emit(project_name)

    def _on_item_double_clicked(self, item: QListWidgetItem) -> None:
        project_name = item.data(Qt.ItemDataRole.UserRole)
        self.project_double_clicked.emit(project_name)

    def _show_context_menu(self, pos) -> None:
        item = self.project_list.itemAt(pos)
        if not item:
            return
        
        project_name = item.data(Qt.ItemDataRole.UserRole)
        
        menu = QMenu(self)
        
        open_dir_action = QAction("打开项目目录", self)
        open_dir_action.triggered.connect(lambda: self.open_project_dir.emit(project_name))
        menu.addAction(open_dir_action)
        
        config_llm_action = QAction("配置 LLM", self)
        config_llm_action.triggered.connect(lambda: self.configure_llm.emit(project_name))
        menu.addAction(config_llm_action)
        
        menu.addSeparator()
        
        delete_action = QAction("删除项目", self)
        delete_action.triggered.connect(lambda: self.delete_project.emit(project_name))
        menu.addAction(delete_action)
        
        menu.exec(self.project_list.mapToGlobal(pos))

    def _on_new_project(self) -> None:
        pass

    def _on_open_dir(self) -> None:
        current_item = self.project_list.currentItem()
        if current_item:
            project_name = current_item.data(Qt.ItemDataRole.UserRole)
            self.open_project_dir.emit(project_name)

    def get_current_project_name(self) -> Optional[str]:
        current_item = self.project_list.currentItem()
        if current_item:
            return current_item.data(Qt.ItemDataRole.UserRole)
        return None
