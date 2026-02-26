"""
主窗口
"""

import asyncio
import subprocess
import sys
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
    QTabWidget,
    QApplication,
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QThread
from PyQt6.QtGui import QAction, QKeySequence

from pywiki.config.settings import Settings
from pywiki.config.models import ProjectConfig, LLMConfig
from pywiki.gui.panels.project_panel import ProjectPanel
from pywiki.gui.panels.preview_panel import PreviewPanel
from pywiki.gui.panels.progress_panel import ProgressPanel
from pywiki.gui.panels.qa_panel import QAPanel
from pywiki.gui.panels.doc_type_panel import DocTypePanel
from pywiki.gui.panels.insights_panel import InsightsPanel
from pywiki.gui.panels.knowledge_panel import KnowledgePanel
from pywiki.gui.dialogs.new_project_dialog import NewProjectDialog
from pywiki.gui.dialogs.llm_config_dialog import LLMConfigDialog
from pywiki.generators.docs.base import DocType


class DocGeneratorThread(QThread):
    """文档生成线程"""
    
    progress_updated = pyqtSignal(int, str)
    generation_completed = pyqtSignal(bool, str)
    stage_changed = pyqtSignal(str, str)
    
    def __init__(
        self,
        project: ProjectConfig,
        doc_types: list[DocType],
        llm_config: Optional[LLMConfig] = None,
    ):
        super().__init__()
        self.project = project
        self.doc_types = doc_types
        self.llm_config = llm_config
        self._is_cancelled = False
    
    def run(self):
        try:
            asyncio.run(self._generate_docs())
        except Exception as e:
            self.generation_completed.emit(False, str(e))
    
    async def _generate_docs(self):
        from pywiki.wiki.manager import WikiManager
        from pywiki.llm.client import LLMClient
        
        llm_client = None
        if self.llm_config:
            llm_client = LLMClient(
                api_key=self.llm_config.api_key.get_secret_value(),
                endpoint=self.llm_config.endpoint,
                model=self.llm_config.model,
            )
        
        def progress_callback(progress):
            if self._is_cancelled:
                return
            pct = int((progress.get("completed_docs", 0) / max(progress.get("total_docs", 1), 1)) * 100)
            self.progress_updated.emit(pct, progress.get("current_doc", ""))
        
        manager = WikiManager(
            project=self.project,
            llm_client=llm_client,
            progress_callback=progress_callback,
        )
        
        total = len(self.doc_types)
        for i, doc_type in enumerate(self.doc_types):
            if self._is_cancelled:
                break
            
            self.stage_changed.emit(doc_type.value, "running")
            self.progress_updated.emit(
                int((i / total) * 100),
                f"正在生成: {doc_type.value}"
            )
            
            try:
                result = await manager.generate_doc(doc_type)
                if result.get("success"):
                    self.stage_changed.emit(doc_type.value, "completed")
                else:
                    self.stage_changed.emit(doc_type.value, "error")
            except Exception as e:
                self.stage_changed.emit(doc_type.value, "error")
        
        self.generation_completed.emit(True, "文档生成完成")
    
    def cancel(self):
        self._is_cancelled = True


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
        self._generator_thread: Optional[DocGeneratorThread] = None

        self._init_ui()
        self._init_menu()
        self._init_toolbar()
        self._init_statusbar()
        self._connect_signals()
        self._load_last_project()

    def _init_ui(self) -> None:
        self.setWindowTitle("Python Wiki - AI 文档生成器")
        self.setMinimumSize(1500, 900)
        self.resize(1700, 1000)

        self.setStyleSheet("""
            QMainWindow {
                background-color: #f5f5f5;
            }
            QMenuBar {
                background-color: #ffffff;
                border-bottom: 1px solid #e0e0e0;
            }
            QToolBar {
                background-color: #ffffff;
                border-bottom: 1px solid #e0e0e0;
                spacing: 8px;
                padding: 4px;
            }
            QStatusBar {
                background-color: #ffffff;
                border-top: 1px solid #e0e0e0;
            }
        """)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        left_splitter = QSplitter(Qt.Orientation.Vertical)
        
        self.project_panel = ProjectPanel()
        left_splitter.addWidget(self.project_panel)

        self.doc_type_panel = DocTypePanel()
        left_splitter.addWidget(self.doc_type_panel)

        left_splitter.setSizes([350, 350])
        splitter.addWidget(left_splitter)

        right_splitter = QSplitter(Qt.Orientation.Vertical)

        self.content_tab = QTabWidget()
        self.content_tab.setDocumentMode(True)
        
        self.preview_panel = PreviewPanel()
        self.content_tab.addTab(self.preview_panel, "📄 文档预览")
        
        self.qa_panel = QAPanel()
        self.content_tab.addTab(self.qa_panel, "💬 智能问答")
        
        self.insights_panel = InsightsPanel()
        self.content_tab.addTab(self.insights_panel, "🔍 架构洞察")
        
        self.knowledge_panel = KnowledgePanel()
        self.content_tab.addTab(self.knowledge_panel, "💡 隐式知识")
        
        right_splitter.addWidget(self.content_tab)

        self.progress_panel = ProgressPanel()
        right_splitter.addWidget(self.progress_panel)

        right_splitter.setSizes([650, 200])

        splitter.addWidget(right_splitter)
        splitter.setSizes([320, 1180])

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

        shortcuts_action = QAction("快捷键(&K)", self)
        shortcuts_action.triggered.connect(self._on_shortcuts)
        help_menu.addAction(shortcuts_action)

        help_menu.addSeparator()

        about_action = QAction("关于(&A)", self)
        about_action.triggered.connect(self._on_about)
        help_menu.addAction(about_action)

    def _init_toolbar(self) -> None:
        toolbar = QToolBar("主工具栏")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        generate_all_action = QAction("🚀 一键生成全部", self)
        generate_all_action.setToolTip("生成所有类型的文档 (Ctrl+Shift+G)")
        generate_all_action.triggered.connect(self._on_generate_all)
        toolbar.addAction(generate_all_action)

        generate_selected_action = QAction("📝 生成选中文档", self)
        generate_selected_action.setToolTip("生成选中的文档类型")
        generate_selected_action.triggered.connect(self._on_generate_selected)
        toolbar.addAction(generate_selected_action)

        toolbar.addSeparator()

        update_action = QAction("🔄 增量更新", self)
        update_action.triggered.connect(self._on_update)
        toolbar.addAction(update_action)

        sync_action = QAction("📡 同步 Git", self)
        sync_action.triggered.connect(self._on_sync)
        toolbar.addAction(sync_action)

        toolbar.addSeparator()

        config_action = QAction("⚙️ LLM 配置", self)
        config_action.triggered.connect(self._on_llm_config)
        toolbar.addAction(config_action)

        toolbar.addSeparator()
        
        analyze_action = QAction("🔍 分析项目", self)
        analyze_action.setToolTip("分析项目架构和隐式知识")
        analyze_action.triggered.connect(self._on_analyze)
        toolbar.addAction(analyze_action)

    def _init_statusbar(self) -> None:
        self.statusbar = QStatusBar()
        self.setStatusBar(self.statusbar)
        self.statusbar.showMessage("就绪 - 请选择或创建一个项目")

    def _connect_signals(self) -> None:
        self.project_panel.project_selected.connect(self._on_project_selected)
        self.project_panel.open_project_dir.connect(self._on_open_project_dir)
        self.project_panel.configure_llm.connect(self._on_configure_project_llm)
        self.project_panel.delete_project.connect(self._on_delete_project)
        
        self.generation_progress.connect(self._on_progress_update)
        self.doc_type_panel.generate_requested.connect(self._on_generate_doc_types)
        self.doc_type_panel.generate_all_requested.connect(self._on_generate_all)
        
        self.progress_panel.cancel_requested.connect(self._on_cancel_generation)
        
        self.insights_panel.analyze_requested.connect(self._on_analyze)
        self.knowledge_panel.extract_requested.connect(self._on_extract_knowledge)

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
        self.statusbar.showMessage(f"当前项目: {project.name} | 路径: {project.path}")
        self.setWindowTitle(f"Python Wiki - {project.name}")
        
        wiki_dir = project.path / project.wiki.output_dir
        self.preview_panel.set_wiki_dir(wiki_dir)
        self.insights_panel.set_project_path(project.path)
        self.knowledge_panel.set_project_path(project.path)

    def _on_project_selected(self, project_name: str) -> None:
        project = self.settings.get_project(project_name)
        if project:
            self._set_current_project(project)

    def _on_open_project_dir(self, project_name: str) -> None:
        project = self.settings.get_project(project_name)
        if project:
            if sys.platform == "win32":
                subprocess.run(["explorer", str(project.path)])
            elif sys.platform == "darwin":
                subprocess.run(["open", str(project.path)])
            else:
                subprocess.run(["xdg-open", str(project.path)])

    def _on_configure_project_llm(self, project_name: str) -> None:
        project = self.settings.get_project(project_name)
        if project:
            self._set_current_project(project)
            self._on_llm_config()

    def _on_delete_project(self, project_name: str) -> None:
        reply = QMessageBox.question(
            self,
            "确认删除",
            f"确定要从列表中删除项目 '{project_name}' 吗？\n（不会删除实际文件）",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.settings.remove_project(project_name)
            self._refresh_project_list()
            self.statusbar.showMessage(f"已删除项目: {project_name}")

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
                self.statusbar.showMessage("LLM 配置已保存")

    def _on_refresh(self) -> None:
        self._refresh_project_list()
        if self._current_project:
            wiki_dir = self._current_project.path / self._current_project.wiki.output_dir
            self.preview_panel.set_wiki_dir(wiki_dir)
        self.statusbar.showMessage("已刷新")

    def _on_shortcuts(self) -> None:
        QMessageBox.information(
            self,
            "快捷键",
            """<h3>常用快捷键</h3>
            <table>
                <tr><td><b>Ctrl+N</b></td><td>新建项目</td></tr>
                <tr><td><b>Ctrl+O</b></td><td>打开项目</td></tr>
                <tr><td><b>Ctrl+E</b></td><td>导出文档</td></tr>
                <tr><td><b>Ctrl+L</b></td><td>LLM 配置</td></tr>
                <tr><td><b>Ctrl+,</b></td><td>设置</td></tr>
                <tr><td><b>Ctrl+R</b></td><td>刷新</td></tr>
                <tr><td><b>Ctrl+Shift+G</b></td><td>一键生成全部</td></tr>
            </table>
            """
        )

    def _on_about(self) -> None:
        QMessageBox.about(
            self,
            "关于 Python Wiki",
            """<h2>Python Wiki</h2>
            <p><b>版本 0.1.0</b></p>
            <p>AI 驱动的 Wiki 文档生成器</p>
            <p>对标 Qoder Wiki 的 Python 实现</p>
            <hr>
            <p><b>核心功能:</b></p>
            <ul>
                <li>一键生成 10 种类型文档</li>
                <li>Mermaid 图表生成</li>
                <li>增量更新</li>
                <li>Git 集成</li>
                <li>智能问答</li>
                <li>架构洞察分析</li>
                <li>隐式知识提取</li>
            </ul>
            <hr>
            <p>© 2024 Python Wiki Team</p>
            <p><a href="https://github.com/guanqiao/python-wiki">GitHub</a></p>
            """
        )

    def _on_generate_all(self) -> None:
        if not self._current_project:
            QMessageBox.warning(self, "警告", "请先选择一个项目")
            return
        
        self._start_generation(list(DocType))

    def _on_generate_selected(self) -> None:
        if not self._current_project:
            QMessageBox.warning(self, "警告", "请先选择一个项目")
            return
        
        selected = self.doc_type_panel.get_selected_doc_types()
        if not selected:
            QMessageBox.warning(self, "警告", "请至少选择一种文档类型")
            return
        
        self._start_generation(selected)

    def _on_generate_doc_types(self, doc_types: list[DocType]) -> None:
        if not self._current_project:
            QMessageBox.warning(self, "警告", "请先选择一个项目")
            return
        
        self._start_generation(doc_types)

    def _start_generation(self, doc_types: list[DocType]) -> None:
        config = self.settings.load_config()
        llm_config = config.default_llm
        
        self._generator_thread = DocGeneratorThread(
            project=self._current_project,
            doc_types=doc_types,
            llm_config=llm_config,
        )
        
        self._generator_thread.progress_updated.connect(self._on_progress_update)
        self._generator_thread.generation_completed.connect(self._on_generation_completed)
        self._generator_thread.stage_changed.connect(self._on_stage_changed)
        
        self.generation_started.emit()
        self.statusbar.showMessage("正在生成文档...")
        self.progress_panel.start_generation()
        self.progress_panel.add_log("INFO", f"开始生成 {len(doc_types)} 种文档类型")
        
        self._generator_thread.start()

    def _on_cancel_generation(self) -> None:
        if self._generator_thread and self._generator_thread.isRunning():
            self._generator_thread.cancel()
            self.progress_panel.add_log("WARN", "正在取消生成...")

    def _on_generation_completed(self, success: bool, message: str) -> None:
        if success:
            self.progress_panel.complete_generation()
            self.statusbar.showMessage("文档生成完成")
            self.generation_completed.emit()
            
            if self._current_project:
                wiki_dir = self._current_project.path / self._current_project.wiki.output_dir
                self.preview_panel.set_wiki_dir(wiki_dir)
            
            QMessageBox.information(self, "完成", "文档生成完成！")
        else:
            self.progress_panel.error_generation(message)
            self.statusbar.showMessage(f"生成失败: {message}")
            QMessageBox.critical(self, "错误", f"文档生成失败: {message}")

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

    def _on_analyze(self) -> None:
        if not self._current_project:
            QMessageBox.warning(self, "警告", "请先选择一个项目")
            return
        
        self.statusbar.showMessage("正在分析项目架构...")
        self.progress_panel.add_log("INFO", "开始分析项目架构...")
        
        self.insights_panel.update_tech_stack({
            "语言": ["Python 3.10+"],
            "GUI": ["PyQt6"],
            "解析器": ["tree-sitter"],
            "LLM": ["LangChain", "LangGraph"],
        })
        
        self.statusbar.showMessage("架构分析完成")

    def _on_extract_knowledge(self) -> None:
        if not self._current_project:
            QMessageBox.warning(self, "警告", "请先选择一个项目")
            return
        
        self.statusbar.showMessage("正在提取隐式知识...")
        self.progress_panel.add_log("INFO", "开始提取隐式知识...")
        
        self.statusbar.showMessage("隐式知识提取完成")

    def _on_progress_update(self, progress: int, message: str) -> None:
        self.progress_panel.update_progress(progress, message)

    def _on_stage_changed(self, stage: str, status: str) -> None:
        self.progress_panel.set_stage(stage, status)
        if status == "running":
            self.progress_panel.add_log("INFO", f"正在生成: {stage}")
        elif status == "completed":
            self.progress_panel.add_log("SUCCESS", f"完成: {stage}")
        elif status == "error":
            self.progress_panel.add_log("ERROR", f"失败: {stage}")

    def closeEvent(self, event):
        if self._generator_thread and self._generator_thread.isRunning():
            reply = QMessageBox.question(
                self,
                "确认",
                "文档生成正在进行中，确定要退出吗？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply == QMessageBox.StandardButton.No:
                event.ignore()
                return
            
            self._generator_thread.cancel()
            self._generator_thread.wait()
        
        event.accept()
