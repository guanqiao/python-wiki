"""
主窗口
"""

import asyncio
import logging
import subprocess
import sys
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

from pydantic import SecretStr

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
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QThread, QUrl, QMimeData
from PyQt6.QtGui import QAction, QKeySequence, QDragEnterEvent, QDropEvent

from pywiki.config.settings import Settings
from pywiki.config.models import ProjectConfig, LLMConfig, WikiConfig, Language
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
from pywiki.monitor.logger import logger


class DocGeneratorThread(QThread):
    """文档生成线程"""
    
    progress_updated = pyqtSignal(int, str)
    generation_completed = pyqtSignal(bool, str)
    stage_changed = pyqtSignal(str, str)
    paused_state_changed = pyqtSignal(bool)
    
    def __init__(
        self,
        project: ProjectConfig,
        doc_types: list[DocType],
        llm_config: Optional[LLMConfig] = None,
        languages: list[Language] = None,
    ):
        super().__init__()
        self.project = project
        self.doc_types = doc_types
        self.llm_config = llm_config
        self.languages = languages or [Language.ZH]
        self._is_cancelled = False
        self._is_paused = False
        self._pause_condition = asyncio.Condition()
        logger.debug(f"DocGeneratorThread 初始化: 项目={project.name}, 文档类型={[d.value for d in doc_types]}, 语言={[l.value for l in self.languages]}")
    
    def run(self):
        logger.info(f"文档生成线程开始运行: {self.project.name}")
        try:
            asyncio.run(self._generate_docs())
        except Exception as e:
            logger.log_exception("文档生成线程运行失败", e)
            self.generation_completed.emit(False, str(e))
    
    async def _generate_docs(self):
        from pywiki.wiki.manager import WikiManager
        from pywiki.llm.client import LLMClient
        
        llm_client = None
        if self.llm_config:
            try:
                llm_client = LLMClient.from_config(self.llm_config)
                logger.info(f"LLM 客户端初始化成功: model={self.llm_config.model}")
            except Exception as e:
                logger.log_exception("LLM 客户端初始化失败", e)
                raise
        
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
        
        total = len(self.doc_types) * len(self.languages)
        current = 0
        
        for language in self.languages:
            lang_name = "中文" if language == Language.ZH else "English"
            self.progress_updated.emit(0, f"开始生成{lang_name}文档...")
            
            for doc_type in self.doc_types:
                if self._is_cancelled:
                    logger.info("文档生成已取消")
                    break
                
                while self._is_paused:
                    self.paused_state_changed.emit(True)
                    await asyncio.sleep(0.1)
                    if self._is_cancelled:
                        break
                
                if self._is_cancelled:
                    break
                
                self.paused_state_changed.emit(False)
                
                stage_name = f"{doc_type.value} ({lang_name})"
                self.stage_changed.emit(stage_name, "running")
                self.progress_updated.emit(
                    int((current / total) * 100),
                    f"[{lang_name}] 正在生成: {doc_type.value}"
                )
                logger.info(f"开始生成文档: {doc_type.value}, 语言: {language.value}")
                
                try:
                    result = await manager.generate_doc(doc_type, language=language)
                    if result.get("success"):
                        self.stage_changed.emit(stage_name, "completed")
                        logger.info(f"文档生成成功: {doc_type.value} ({lang_name})")
                    else:
                        self.stage_changed.emit(stage_name, "error")
                        logger.error(f"文档生成失败: {doc_type.value} ({lang_name}) - {result.get('message', '未知错误')}")
                except Exception as e:
                    logger.log_exception(f"文档生成异常: {doc_type.value} ({lang_name})", e)
                    self.stage_changed.emit(stage_name, "error")
                
                current += 1
            
            if self._is_cancelled:
                break
        
        logger.info(f"文档生成完成: {self.project.name}")
        self.generation_completed.emit(True, "文档生成完成")
    
    def cancel(self):
        logger.info("文档生成取消请求")
        self._is_cancelled = True
        self._is_paused = False
    
    def pause(self):
        logger.info("文档生成暂停请求")
        self._is_paused = True
    
    def resume(self):
        logger.info("文档生成恢复请求")
        self._is_paused = False
    
    def is_paused(self) -> bool:
        return self._is_paused


class IncrementalUpdateThread(QThread):
    """增量更新线程"""
    
    progress_updated = pyqtSignal(int, str)
    update_completed = pyqtSignal(bool, str, int)
    
    def __init__(self, project: ProjectConfig, llm_config: Optional[LLMConfig] = None):
        super().__init__()
        self.project = project
        self.llm_config = llm_config
    
    def run(self):
        try:
            import asyncio
            from pywiki.sync.incremental_updater import IncrementalUpdater
            from pywiki.sync.change_detector import ChangeDetector
            from pywiki.wiki.manager import WikiManager
            from pywiki.llm.client import LLMClient
            
            llm_client = None
            if self.llm_config:
                llm_client = LLMClient.from_config(self.llm_config)
            
            wiki_manager = WikiManager(
                project=self.project,
                llm_client=llm_client,
            )
            
            change_detector = ChangeDetector()
            
            updater = IncrementalUpdater(
                wiki_manager=wiki_manager,
                change_detector=change_detector,
                progress_callback=lambda p, m: self.progress_updated.emit(p, m),
            )
            
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result = loop.run_until_complete(updater.update())
                self.update_completed.emit(
                    result.success,
                    result.error or "更新完成",
                    len(result.updated_files)
                )
            finally:
                loop.close()
                
        except Exception as e:
            logger.error(f"增量更新失败: {e}")
            self.update_completed.emit(False, str(e), 0)


class GitSyncThread(QThread):
    """Git 同步线程"""
    
    sync_completed = pyqtSignal(bool, str, list)
    
    def __init__(self, project_path: Path):
        super().__init__()
        self.project_path = project_path
    
    def run(self):
        try:
            from pywiki.sync.git_change_detector import GitChangeDetector
            
            detector = GitChangeDetector(self.project_path)
            changes = detector.get_uncommitted_changes()
            
            change_list = [
                f"{change.change_type.value}: {change.file_path.name}"
                for change in changes
            ]
            
            self.sync_completed.emit(True, "同步完成", change_list)
            
        except Exception as e:
            logger.error(f"Git 同步失败: {e}")
            self.sync_completed.emit(False, str(e), [])


class ProjectAnalyzeThread(QThread):
    """项目分析线程"""
    
    analysis_completed = pyqtSignal(bool, dict, list)
    
    def __init__(self, project_path: Path):
        super().__init__()
        self.project_path = project_path
    
    def run(self):
        try:
            from pywiki.insights.tech_stack_analyzer import TechStackAnalyzer
            
            analyzer = TechStackAnalyzer()
            analysis = analyzer.analyze_project(self.project_path)
            
            tech_stack = {}
            for component in analysis.components:
                category = component.category.value
                if category not in tech_stack:
                    tech_stack[category] = []
                tech_stack[category].append(component.name)
            
            self.analysis_completed.emit(True, tech_stack, [])
            
        except Exception as e:
            logger.error(f"项目分析失败: {e}")
            self.analysis_completed.emit(False, {}, [])


class KnowledgeExtractThread(QThread):
    """知识提取线程"""
    
    extraction_completed = pyqtSignal(bool, dict)
    
    def __init__(self, project_path: Path):
        super().__init__()
        self.project_path = project_path
    
    def run(self):
        try:
            from pywiki.knowledge.implicit_extractor import ImplicitKnowledgeExtractor
            from pywiki.parsers.python import PythonParser
            
            extractor = ImplicitKnowledgeExtractor()
            parser = PythonParser()
            
            all_knowledge = []
            
            for py_file in self.project_path.rglob("*.py"):
                try:
                    if ".venv" in str(py_file) or "__pycache__" in str(py_file):
                        continue
                    
                    content = py_file.read_text(encoding="utf-8")
                    result = parser.parse_file(py_file)
                    
                    for module in result.modules:
                        knowledge = extractor.extract_from_module(
                            self.project_path,
                            module,
                            content
                        )
                        all_knowledge.extend(knowledge)
                        
                except Exception:
                    continue
            
            decisions = [
                {
                    "title": k.title,
                    "context": k.description,
                    "status": k.priority.value
                }
                for k in all_knowledge
                if k.knowledge_type.value == "design_decision"
            ]
            
            tech_debts = [
                {
                    "title": k.title,
                    "description": k.description,
                    "priority": k.priority.value
                }
                for k in all_knowledge
                if k.knowledge_type.value == "tech_debt"
            ]
            
            motivations = "\n".join([
                f"### {k.title}\n{k.description}"
                for k in all_knowledge
                if k.knowledge_type.value == "trade_off"
            ])
            
            report = {
                "total_knowledge": len(all_knowledge),
                "decisions": decisions[:20],
                "tech_debts": tech_debts[:20],
                "motivations": motivations,
            }
            
            self.extraction_completed.emit(True, report)
            
        except Exception as e:
            logger.error(f"知识提取失败: {e}")
            self.extraction_completed.emit(False, {})


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

        self.setAcceptDrops(True)

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
        self.progress_panel.pause_requested.connect(self._on_pause_generation)
        self.progress_panel.resume_requested.connect(self._on_resume_generation)
        
        self.insights_panel.analyze_requested.connect(self._on_analyze)
        self.knowledge_panel.extract_requested.connect(self._on_extract_knowledge)
        self.knowledge_panel.export_adr_requested.connect(self._on_export_adr)

    def _load_last_project(self) -> None:
        config = self.settings.load_config()
        if config.last_project:
            project = self.settings.get_project(config.last_project)
            if project:
                self._set_current_project(project)

        self._refresh_project_list()

    def _refresh_project_list(self) -> None:
        config = self.settings.load_config()
        self.project_panel.set_projects(config.projects, config.default_llm)

    def _set_current_project(self, project: ProjectConfig) -> None:
        self._current_project = project
        self.settings.set_last_project(project.name)
        self.project_changed.emit(project.name)
        self.statusbar.showMessage(f"当前项目: {project.name} | 路径: {project.path}")
        self.setWindowTitle(f"Python Wiki - {project.name}")
        
        logger.info(f"切换到项目: {project.name} (路径: {project.path})")
        
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
            logger.info(f"已从列表删除项目: {project_name}")

    def _on_new_project(self) -> None:
        dialog = NewProjectDialog(self)
        if dialog.exec():
            project_config = dialog.get_project_config()
            if project_config:
                self.settings.add_project(project_config)
                self._set_current_project(project_config)
                self._refresh_project_list()
                logger.info(f"创建新项目: {project_config.name}")

    def _on_open_project(self) -> None:
        folder = QFileDialog.getExistingDirectory(
            self,
            "选择项目目录",
            "",
            QFileDialog.Option.ShowDirsOnly
        )
        if folder:
            self._open_project_from_path(Path(folder))

    def _open_project_from_path(self, project_path: Path) -> None:
        if not project_path.exists() or not project_path.is_dir():
            logger.warning(f"目录不存在或不是有效目录: {project_path}")
            QMessageBox.warning(self, "警告", f"目录不存在或不是有效目录: {project_path}")
            return

        project_name = project_path.name
        logger.info(f"尝试打开项目: {project_name} (路径: {project_path})")

        existing_project = self.settings.get_project(project_name)
        if existing_project:
            reply = QMessageBox.question(
                self,
                "项目已存在",
                f"项目 '{project_name}' 已存在，是否打开该项目？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply == QMessageBox.StandardButton.Yes:
                self._set_current_project(existing_project)
            return

        project_config = ProjectConfig(
            name=project_name,
            path=project_path,
            wiki=WikiConfig(),
            llm=LLMConfig(api_key=SecretStr("")),
        )

        self.settings.add_project(project_config)
        self._set_current_project(project_config)
        self._refresh_project_list()
        self.statusbar.showMessage(f"已打开项目: {project_name}")
        logger.info(f"成功打开项目: {project_name}")

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
        current_llm = config.default_llm or LLMConfig(api_key=SecretStr(""))

        dialog = LLMConfigDialog(current_llm, self)
        if dialog.exec():
            new_llm = dialog.get_llm_config()
            if new_llm:
                self.settings.update_default_llm(new_llm)
                self._refresh_project_list()
                self.statusbar.showMessage("LLM 配置已保存")
                logger.info("LLM 配置已更新")

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
        languages = self.doc_type_panel.get_selected_languages()
        
        logger.info(f"开始生成文档: 类型={[d.value for d in doc_types]}, 语言={[l.value for l in languages]}, LLM配置={'已设置' if llm_config else '未设置'}")
        
        self._generator_thread = DocGeneratorThread(
            project=self._current_project,
            doc_types=doc_types,
            llm_config=llm_config,
            languages=languages,
        )
        
        self._generator_thread.progress_updated.connect(self._on_progress_update)
        self._generator_thread.generation_completed.connect(self._on_generation_completed)
        self._generator_thread.stage_changed.connect(self._on_stage_changed)
        self._generator_thread.paused_state_changed.connect(self._on_paused_state_changed)
        
        self.generation_started.emit()
        self.statusbar.showMessage("正在生成文档...")
        self.progress_panel.start_generation()
        lang_names = "、".join(["中文" if l == Language.ZH else "English" for l in languages])
        self.progress_panel.add_log("INFO", f"开始生成 {len(doc_types)} 种文档类型（{lang_names}）")
        
        self._generator_thread.start()

    def _on_cancel_generation(self) -> None:
        if self._generator_thread and self._generator_thread.isRunning():
            self._generator_thread.cancel()
            self.progress_panel.add_log("WARN", "正在终止生成...")

    def _on_pause_generation(self) -> None:
        if self._generator_thread and self._generator_thread.isRunning():
            self._generator_thread.pause()
            self.progress_panel.add_log("INFO", "生成已暂停")
            self.statusbar.showMessage("文档生成已暂停")

    def _on_resume_generation(self) -> None:
        if self._generator_thread and self._generator_thread.isRunning():
            self._generator_thread.resume()
            self.progress_panel.add_log("INFO", "生成已恢复")
            self.statusbar.showMessage("正在生成文档...")

    def _on_paused_state_changed(self, paused: bool) -> None:
        self.progress_panel.set_paused_state(paused)

    def _on_generation_completed(self, success: bool, message: str) -> None:
        if success:
            self.progress_panel.complete_generation()
            self.statusbar.showMessage("文档生成完成")
            self.generation_completed.emit()
            logger.info(f"文档生成完成: {message}")
            
            if self._current_project:
                wiki_dir = self._current_project.path / self._current_project.wiki.output_dir
                self.preview_panel.set_wiki_dir(wiki_dir)
            
            QMessageBox.information(self, "完成", "文档生成完成！")
        else:
            self.progress_panel.error_generation(message)
            self.statusbar.showMessage(f"生成失败: {message}")
            logger.error(f"文档生成失败: {message}")
            QMessageBox.critical(self, "错误", f"文档生成失败: {message}")

    def _on_update(self) -> None:
        if not self._current_project:
            QMessageBox.warning(self, "警告", "请先选择一个项目")
            return

        logger.info(f"开始增量更新: {self._current_project.name}")
        self.statusbar.showMessage("正在增量更新...")
        self.progress_panel.add_log("INFO", "开始增量更新...")
        
        self._update_thread = IncrementalUpdateThread(
            self._current_project,
            self.settings.load_config().default_llm,
        )
        self._update_thread.progress_updated.connect(self._on_progress_update)
        self._update_thread.update_completed.connect(self._on_update_completed)
        self._update_thread.start()

    def _on_update_completed(self, success: bool, message: str, updated_count: int) -> None:
        if success:
            self.progress_panel.add_log("SUCCESS", f"增量更新完成: 更新了 {updated_count} 个文件")
            self.statusbar.showMessage(f"增量更新完成: {updated_count} 个文件")
            
            wiki_dir = self._current_project.path / self._current_project.wiki.output_dir
            self.preview_panel.set_wiki_dir(wiki_dir)
            
            QMessageBox.information(self, "完成", f"增量更新完成！\n更新了 {updated_count} 个文件")
        else:
            self.progress_panel.add_log("ERROR", f"增量更新失败: {message}")
            self.statusbar.showMessage(f"增量更新失败: {message}")
            QMessageBox.warning(self, "失败", f"增量更新失败: {message}")

    def _on_sync(self) -> None:
        if not self._current_project:
            QMessageBox.warning(self, "警告", "请先选择一个项目")
            return

        logger.info(f"开始 Git 同步: {self._current_project.name}")
        self.statusbar.showMessage("正在同步 Git...")
        self.progress_panel.add_log("INFO", "开始 Git 同步...")
        
        self._sync_thread = GitSyncThread(self._current_project.path)
        self._sync_thread.sync_completed.connect(self._on_sync_completed)
        self._sync_thread.start()

    def _on_sync_completed(self, success: bool, message: str, changes: list) -> None:
        if success:
            change_count = len(changes)
            self.progress_panel.add_log("SUCCESS", f"Git 同步完成: 发现 {change_count} 个变更")
            self.statusbar.showMessage(f"Git 同步完成: {change_count} 个变更")
            
            if change_count > 0:
                change_summary = "\n".join([f"• {c}" for c in changes[:10]])
                if change_count > 10:
                    change_summary += f"\n... 还有 {change_count - 10} 个变更"
                QMessageBox.information(self, "同步完成", f"发现 {change_count} 个变更:\n{change_summary}")
            else:
                QMessageBox.information(self, "同步完成", "没有发现新的变更")
        else:
            self.progress_panel.add_log("ERROR", f"Git 同步失败: {message}")
            self.statusbar.showMessage(f"Git 同步失败: {message}")
            QMessageBox.warning(self, "失败", f"Git 同步失败: {message}")

    def _on_analyze(self) -> None:
        if not self._current_project:
            QMessageBox.warning(self, "警告", "请先选择一个项目")
            return
        
        logger.info(f"开始分析项目架构: {self._current_project.name}")
        self.statusbar.showMessage("正在分析项目架构...")
        self.progress_panel.add_log("INFO", "开始分析项目架构...")
        
        self._analyze_thread = ProjectAnalyzeThread(self._current_project.path)
        self._analyze_thread.analysis_completed.connect(self._on_analyze_completed)
        self._analyze_thread.start()

    def _on_analyze_completed(self, success: bool, tech_stack: dict, patterns: list) -> None:
        if success:
            self.progress_panel.add_log("SUCCESS", "项目架构分析完成")
            self.statusbar.showMessage("架构分析完成")
            
            self.insights_panel.update_tech_stack(tech_stack)
            if patterns:
                self.insights_panel.update_patterns(patterns)
        else:
            self.progress_panel.add_log("ERROR", "项目架构分析失败")
            self.statusbar.showMessage("架构分析失败")

    def _on_extract_knowledge(self) -> None:
        if not self._current_project:
            QMessageBox.warning(self, "警告", "请先选择一个项目")
            return
        
        logger.info(f"开始提取隐式知识: {self._current_project.name}")
        self.statusbar.showMessage("正在提取隐式知识...")
        self.progress_panel.add_log("INFO", "开始提取隐式知识...")
        
        self._knowledge_thread = KnowledgeExtractThread(self._current_project.path)
        self._knowledge_thread.extraction_completed.connect(self._on_knowledge_completed)
        self._knowledge_thread.start()

    def _on_knowledge_completed(self, success: bool, knowledge_report: dict) -> None:
        if success:
            self.progress_panel.add_log("SUCCESS", "隐式知识提取完成")
            self.statusbar.showMessage("隐式知识提取完成")
            
            decisions = knowledge_report.get("decisions", [])
            debts = knowledge_report.get("tech_debts", [])
            motivations = knowledge_report.get("motivations", "")
            
            self.knowledge_panel.update_design_decisions(decisions)
            self.knowledge_panel.update_tech_debt(debts)
            if motivations:
                self.knowledge_panel.update_motivations(motivations)
            
            total = knowledge_report.get("total_knowledge", 0)
            QMessageBox.information(self, "完成", f"隐式知识提取完成！\n发现 {total} 条知识")
        else:
            self.progress_panel.add_log("ERROR", "隐式知识提取失败")
            self.statusbar.showMessage("隐式知识提取失败")

    def _on_export_adr(self) -> None:
        if not self._current_project:
            QMessageBox.warning(self, "警告", "请先选择一个项目")
            return

        folder = QFileDialog.getExistingDirectory(
            self,
            "选择 ADR 导出目录",
            str(self._current_project.path),
            QFileDialog.Option.ShowDirsOnly
        )
        if folder:
            self.statusbar.showMessage(f"ADR 导出到: {folder}")
            QMessageBox.information(self, "导出完成", f"ADR 已导出到: {folder}")

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

    def dragEnterEvent(self, event: QDragEnterEvent | None) -> None:
        if event is None:
            return
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            for url in urls:
                if url.isLocalFile():
                    path = Path(url.toLocalFile())
                    if path.is_dir():
                        event.acceptProposedAction()
                        return
        event.ignore()

    def dropEvent(self, event: QDropEvent | None) -> None:
        if event is None:
            return
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            for url in urls:
                if url.isLocalFile():
                    path = Path(url.toLocalFile())
                    if path.is_dir():
                        self._open_project_from_path(path)
                        event.acceptProposedAction()
                        return
        event.ignore()

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
