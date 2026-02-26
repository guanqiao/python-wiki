"""
主窗口
"""

from pathlib import Path
from typing import Optional

from PyQt6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QSplitter,
    QStatusBar,
    QMenuBar,
    QMenu,
    QToolBar,
    QMessageBox,
    QFileDialog,
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QAction, QKeySequence, QShortcut

from pywiki.config.settings import Settings
from pywiki.config.models import ProjectConfig, LLMConfig
from pywiki.gui.panels.project_panel import ProjectPanel
from pywiki.gui.panels.config_panel import ConfigPanel
from pywiki.gui.panels.preview_panel import PreviewPanel
from pywiki.gui.panels.progress_panel import ProgressPanel
from pywiki.gui.dialogs.new_project_dialog import NewProjectDialog
from pywiki.gui.dialogs.llm_config_dialog import LLMConfigDialog


class MainWindow(QMainWindow):
    """主窗口"""

    project_changed = pyqtSignal(str)
    generation_started = pyqtSignal()
    generation_completed = pyqtSignal()
    generation_progress = pyqtSignal(int, str)

    def __init__(self, settings: Settings, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.settings = settings
        self._current_project: Optional[ProjectConfig] = None

        self._init_ui()
        self._init_menu()
        self._init_toolbar()
        self._init_statusbar()
        self._connect_signals()
        self._load_last_project()

    def _init_ui(self) -> None:
        self.setWindowTitle("Python Wiki - AI 文档生成器")
        self.setMinimumSize(1200, 800)
        self.resize(1400, 900)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        self.project_panel = ProjectPanel()
        splitter.addWidget(self.project_panel)

        right_splitter = QSplitter(Qt.Orientation.Vertical)

        self.preview_panel = PreviewPanel()
        right_splitter.addWidget(self.preview_panel)

        self.progress_panel = ProgressPanel()
        right_splitter.addWidget(self.progress_panel)

        right_splitter.setSizes([600, 200])

        splitter.addWidget(right_splitter)
        splitter.setSizes([250, 950])

        main_layout.addWidget(splitter)

    def _init_menu(self) -> None:
        menubar = self.menuBar()

        file_menu = menubar.addMenu("文件(&F)")

        new_project_action = QAction("新建项目(&N)", self)
        new_project_action.setShortcut(QKeySequence.StandardKey.New)
        new_project_action.triggered.connect(self._on_new_project)
        file_menu.addAction(new_project_action)

        open_project_action = QAction("打开项目(&O)", self)
        open_project_action.setShortcut(QKeySequence.StandardKey.Open)
        open_project_action.triggered.connect(self._on_open_project)
        file_menu.addAction(open_project_action)

        file_menu.addSeparator()

        export_action = QAction("导出文档(&E)", self)
        export_action.setShortcut(QKeySequence("Ctrl+E"))
        export_action.triggered.connect(self._on_export)
        file_menu.addAction(export_action)

        file_menu.addSeparator()

        exit_action = QAction("退出(&X)", self)
        exit_action.setShortcut(QKeySequence.StandardKey.Quit)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        edit_menu = menubar.addMenu("编辑(&E)")

        settings_action = QAction("设置(&S)", self)
        settings_action.setShortcut(QKeySequence("Ctrl+,"))
        settings_action.triggered.connect(self._on_settings)
        edit_menu.addAction(settings_action)

        llm_config_action = QAction("LLM 配置(&L)", self)
        llm_config_action.setShortcut(QKeySequence("Ctrl+L"))
        llm_config_action.triggered.connect(self._on_llm_config)
        edit_menu.addAction(llm_config_action)

        view_menu = menubar.addMenu("视图(&V)")

        refresh_action = QAction("刷新(&R)", self)
        refresh_action.setShortcut(QKeySequence.StandardKey.Refresh)
        refresh_action.triggered.connect(self._on_refresh)
        view_menu.addAction(refresh_action)

        help_menu = menubar.addMenu("帮助(&H)")

        about_action = QAction("关于(&A)", self)
        about_action.triggered.connect(self._on_about)
        help_menu.addAction(about_action)

    def _init_toolbar(self) -> None:
        toolbar = QToolBar("主工具栏")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        generate_action = QAction("生成 Wiki", self)
        generate_action.triggered.connect(self._on_generate)
        toolbar.addAction(generate_action)

        update_action = QAction("增量更新", self)
        update_action.triggered.connect(self._on_update)
        toolbar.addAction(update_action)

        sync_action = QAction("同步 Git", self)
        sync_action.triggered.connect(self._on_sync)
        toolbar.addAction(sync_action)

        toolbar.addSeparator()

        config_action = QAction("LLM 配置", self)
        config_action.triggered.connect(self._on_llm_config)
        toolbar.addAction(config_action)

    def _init_statusbar(self) -> None:
        self.statusbar = QStatusBar()
        self.setStatusBar(self.statusbar)
        self.statusbar.showMessage("就绪")

    def _connect_signals(self) -> None:
        self.project_panel.project_selected.connect(self._on_project_selected)
        self.generation_progress.connect(self._on_progress_update)

    def _load_last_project(self) -> None:
        config = self.settings.load_config()
        if config.last_project:
            project = self.settings.get_project(config.last_project)
            if project:
                self._set_current_project(project)

        self._refresh_project_list()

    def _refresh_project_list(self) -> None:
        config = self.settings.load_config()
        self.project_panel.set_projects(config.projects)

    def _set_current_project(self, project: ProjectConfig) -> None:
        self._current_project = project
        self.settings.set_last_project(project.name)
        self.project_changed.emit(project.name)
        self.statusbar.showMessage(f"当前项目: {project.name}")
        self.setWindowTitle(f"Python Wiki - {project.name}")

    def _on_project_selected(self, project_name: str) -> None:
        project = self.settings.get_project(project_name)
        if project:
            self._set_current_project(project)

    def _on_new_project(self) -> None:
        dialog = NewProjectDialog(self)
        if dialog.exec():
            project_config = dialog.get_project_config()
            if project_config:
                self.settings.add_project(project_config)
                self._set_current_project(project_config)
                self._refresh_project_list()

    def _on_open_project(self) -> None:
        folder = QFileDialog.getExistingDirectory(
            self,
            "选择项目目录",
            "",
            QFileDialog.Option.ShowDirsOnly
        )
        if folder:
            pass

    def _on_export(self) -> None:
        if not self._current_project:
            QMessageBox.warning(self, "警告", "请先选择一个项目")
            return

        folder = QFileDialog.getExistingDirectory(
            self,
            "选择导出目录",
            "",
            QFileDialog.Option.ShowDirsOnly
        )
        if folder:
            self.statusbar.showMessage(f"导出到: {folder}")

    def _on_settings(self) -> None:
        pass

    def _on_llm_config(self) -> None:
        config = self.settings.load_config()
        current_llm = config.default_llm or LLMConfig(api_key="")

        dialog = LLMConfigDialog(current_llm, self)
        if dialog.exec():
            new_llm = dialog.get_llm_config()
            if new_llm:
                self.settings.update_default_llm(new_llm)

    def _on_refresh(self) -> None:
        self._refresh_project_list()

    def _on_about(self) -> None:
        QMessageBox.about(
            self,
            "关于 Python Wiki",
            """<h2>Python Wiki</h2>
            <p>版本 0.1.0</p>
            <p>AI 驱动的 Wiki 文档生成器</p>
            <p>对标 Qoder Wiki 的 Python 实现</p>
            <p>支持:</p>
            <ul>
                <li>自动生成架构文档</li>
                <li>Mermaid 图表生成</li>
                <li>增量更新</li>
                <li>Git 集成</li>
            </ul>
            """
        )

    def _on_generate(self) -> None:
        if not self._current_project:
            QMessageBox.warning(self, "警告", "请先选择一个项目")
            return

        self.generation_started.emit()
        self.statusbar.showMessage("正在生成 Wiki...")
        self.progress_panel.start_generation()

    def _on_update(self) -> None:
        if not self._current_project:
            QMessageBox.warning(self, "警告", "请先选择一个项目")
            return

        self.statusbar.showMessage("正在增量更新...")

    def _on_sync(self) -> None:
        if not self._current_project:
            QMessageBox.warning(self, "警告", "请先选择一个项目")
            return

        self.statusbar.showMessage("正在同步 Git...")

    def _on_progress_update(self, progress: int, message: str) -> None:
        self.progress_panel.update_progress(progress, message)
        if progress >= 100:
            self.generation_completed.emit()
            self.statusbar.showMessage("Wiki 生成完成")
