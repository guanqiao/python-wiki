"""
文档预览面板
"""

from typing import Optional
from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QTabWidget,
    QTextEdit,
    QLabel,
    QComboBox,
    QPushButton,
    QSplitter,
    QTreeWidget,
    QTreeWidgetItem,
    QFileDialog,
    QLineEdit,
    QMessageBox,
)
from PyQt6.QtCore import Qt, QUrl, pyqtSignal
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtGui import QIcon

import markdown

LANGUAGE_DISPLAY_NAMES = {
    "zh": "中文",
    "en": "English",
}


class PreviewPanel(QWidget):
    """文档预览面板"""

    document_loaded = pyqtSignal(str)

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._wiki_dir: Optional[Path] = None
        self._current_doc: Optional[str] = None
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        toolbar = QHBoxLayout()

        self.doc_selector = QComboBox()
        self.doc_selector.setPlaceholderText("选择文档")
        self.doc_selector.setMinimumWidth(200)
        self.doc_selector.currentTextChanged.connect(self._on_doc_selected)
        toolbar.addWidget(self.doc_selector)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("搜索文档...")
        self.search_input.setMaximumWidth(200)
        self.search_input.textChanged.connect(self._on_search)
        toolbar.addWidget(self.search_input)

        self.refresh_button = QPushButton("🔄 刷新")
        self.refresh_button.clicked.connect(self._on_refresh)
        toolbar.addWidget(self.refresh_button)

        self.export_button = QPushButton("📤 导出")
        self.export_button.clicked.connect(self._on_export)
        toolbar.addWidget(self.export_button)

        self.browser_button = QPushButton("🌐 浏览器")
        self.browser_button.clicked.connect(self._on_open_in_browser)
        toolbar.addWidget(self.browser_button)

        toolbar.addStretch()
        layout.addLayout(toolbar)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        self.doc_tree = QTreeWidget()
        self.doc_tree.setHeaderLabel("文档目录")
        self.doc_tree.setMaximumWidth(200)
        self.doc_tree.itemClicked.connect(self._on_tree_item_clicked)
        splitter.addWidget(self.doc_tree)

        self.tab_widget = QTabWidget()

        self.preview_view = QWebEngineView()
        self.tab_widget.addTab(self.preview_view, "预览")

        self.source_edit = QTextEdit()
        self.source_edit.setReadOnly(True)
        self.source_edit.setStyleSheet("""
            QTextEdit {
                font-family: Consolas, Monaco, 'Courier New', monospace;
                font-size: 12px;
                background-color: #f8f9fa;
            }
        """)
        self.tab_widget.addTab(self.source_edit, "源码")

        splitter.addWidget(self.tab_widget)
        splitter.setSizes([200, 800])

        layout.addWidget(splitter)

    def set_wiki_dir(self, wiki_dir: Path) -> None:
        """设置 Wiki 目录"""
        self._wiki_dir = wiki_dir
        self._load_document_list()

    def _load_document_list(self) -> None:
        """加载文档列表"""
        if not self._wiki_dir or not self._wiki_dir.exists():
            return

        self.doc_selector.clear()
        self.doc_tree.clear()

        language_dirs = self._detect_language_dirs()

        root_item = QTreeWidgetItem(self.doc_tree, ["📁 文档根目录"])
        root_item.setData(0, Qt.ItemDataRole.UserRole, str(self._wiki_dir))

        if language_dirs:
            for lang_code, lang_dir in language_dirs.items():
                lang_name = LANGUAGE_DISPLAY_NAMES.get(lang_code, lang_code)
                lang_item = QTreeWidgetItem(root_item, [f"🌐 {lang_name} ({lang_code})"])
                lang_item.setData(0, Qt.ItemDataRole.UserRole, "")
                self._build_tree_for_dir(lang_item, lang_dir, self._wiki_dir)
                lang_item.setExpanded(True)
        else:
            self._build_tree_for_dir(root_item, self._wiki_dir, self._wiki_dir)

        self.doc_tree.expandAll()

    def _detect_language_dirs(self) -> dict[str, Path]:
        """检测语言子目录"""
        language_dirs = {}
        if not self._wiki_dir or not self._wiki_dir.exists():
            return language_dirs

        for lang_code in LANGUAGE_DISPLAY_NAMES.keys():
            lang_path = self._wiki_dir / lang_code
            if lang_path.is_dir():
                md_files = list(lang_path.rglob("*.md"))
                if md_files:
                    language_dirs[lang_code] = lang_path

        return language_dirs

    def _build_tree_for_dir(
        self,
        parent_item: QTreeWidgetItem,
        target_dir: Path,
        base_dir: Path,
    ) -> None:
        """为指定目录构建文档树"""
        md_files = list(target_dir.rglob("*.md"))

        for md_file in sorted(md_files):
            rel_path = md_file.relative_to(target_dir)
            display_name = str(md_file.relative_to(base_dir))

            self.doc_selector.addItem(display_name, str(md_file))

            parts = rel_path.parts
            current_parent = parent_item
            for i, part in enumerate(parts[:-1]):
                found = False
                for j in range(current_parent.childCount()):
                    child = current_parent.child(j)
                    if child.text(0) == f"📁 {part}":
                        current_parent = child
                        found = True
                        break
                if not found:
                    new_item = QTreeWidgetItem(current_parent, [f"📁 {part}"])
                    new_item.setData(0, Qt.ItemDataRole.UserRole, "")
                    current_parent = new_item

            file_item = QTreeWidgetItem(current_parent, [f"📄 {parts[-1]}"])
            file_item.setData(0, Qt.ItemDataRole.UserRole, str(md_file))

    def _on_doc_selected(self, doc_name: str) -> None:
        if not doc_name:
            return
        
        doc_path = self.doc_selector.currentData()
        if doc_path:
            self._load_document(Path(doc_path))

    def _on_tree_item_clicked(self, item: QTreeWidgetItem, column: int) -> None:
        doc_path = item.data(0, Qt.ItemDataRole.UserRole)
        if doc_path and doc_path.endswith(".md"):
            self._load_document(Path(doc_path))

    def _on_search(self, text: str) -> None:
        for i in range(self.doc_selector.count()):
            item_text = self.doc_selector.itemText(i)
            if text.lower() in item_text.lower():
                self.doc_selector.setCurrentIndex(i)
                break

    def _on_refresh(self) -> None:
        self._load_document_list()
        if self._current_doc:
            self._load_document(Path(self._current_doc))

    def _on_export(self) -> None:
        if not self._current_doc:
            QMessageBox.warning(self, "警告", "请先选择一个文档")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "导出文档",
            Path(self._current_doc).name,
            "Markdown 文件 (*.md);;HTML 文件 (*.html);;所有文件 (*)"
        )
        
        if file_path:
            content = self.source_edit.toPlainText()
            if file_path.endswith(".html"):
                content = self._render_html(content)
            
            Path(file_path).write_text(content, encoding="utf-8")
            QMessageBox.information(self, "成功", f"文档已导出到: {file_path}")

    def _on_open_in_browser(self) -> None:
        if self._current_doc:
            self.preview_view.page().openUrlInNewTab(QUrl.fromLocalFile(self._current_doc))

    def _load_document(self, doc_path: Path) -> None:
        """加载文档"""
        if not doc_path.exists():
            return

        self._current_doc = str(doc_path)
        content = doc_path.read_text(encoding="utf-8")
        
        self.source_edit.setPlainText(content)
        
        html = self._render_html(content)
        self.preview_view.setHtml(html, QUrl.fromLocalFile(str(doc_path.parent) + "/"))
        
        self.document_loaded.emit(str(doc_path))

    def _render_html(self, content: str) -> str:
        """渲染 HTML"""
        html = markdown.markdown(
            content,
            extensions=["tables", "fenced_code", "toc", "codehilite"]
        )

        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                :root {{
                    --bg-color: #ffffff;
                    --text-color: #24292f;
                    --code-bg: #f6f8fa;
                    --border-color: #d0d7de;
                }}
                
                @media (prefers-color-scheme: dark) {{
                    :root {{
                        --bg-color: #0d1117;
                        --text-color: #c9d1d9;
                        --code-bg: #161b22;
                        --border-color: #30363d;
                    }}
                }}
                
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
                    line-height: 1.6;
                    padding: 20px;
                    max-width: 900px;
                    margin: 0 auto;
                    color: var(--text-color);
                    background-color: var(--bg-color);
                }}
                h1, h2, h3, h4, h5, h6 {{
                    margin-top: 24px;
                    margin-bottom: 16px;
                    font-weight: 600;
                    line-height: 1.25;
                }}
                h1 {{ font-size: 2em; border-bottom: 1px solid var(--border-color); padding-bottom: .3em; }}
                h2 {{ font-size: 1.5em; border-bottom: 1px solid var(--border-color); padding-bottom: .3em; }}
                h3 {{ font-size: 1.25em; }}
                code {{
                    padding: 0.2em 0.4em;
                    margin: 0;
                    font-size: 85%;
                    background-color: var(--code-bg);
                    border-radius: 3px;
                    font-family: Consolas, Monaco, 'Courier New', monospace;
                }}
                pre {{
                    padding: 16px;
                    overflow: auto;
                    font-size: 85%;
                    line-height: 1.45;
                    background-color: var(--code-bg);
                    border-radius: 6px;
                }}
                pre code {{
                    background-color: transparent;
                    padding: 0;
                }}
                table {{
                    border-spacing: 0;
                    border-collapse: collapse;
                    width: 100%;
                    margin-bottom: 16px;
                }}
                table th, table td {{
                    padding: 6px 13px;
                    border: 1px solid var(--border-color);
                }}
                table th {{
                    font-weight: 600;
                    background-color: var(--code-bg);
                }}
                table tr:nth-child(2n) {{
                    background-color: var(--code-bg);
                }}
                blockquote {{
                    padding: 0 1em;
                    color: #6a737d;
                    border-left: 0.25em solid var(--border-color);
                    margin: 0 0 16px 0;
                }}
                a {{
                    color: #0969da;
                    text-decoration: none;
                }}
                a:hover {{
                    text-decoration: underline;
                }}
            </style>
            <script>
                function initMermaid() {{
                    if (typeof mermaid !== 'undefined') {{
                        var codeBlocks = document.querySelectorAll('pre code.language-mermaid');
                        codeBlocks.forEach(function(block) {{
                            var pre = block.parentElement;
                            var div = document.createElement('div');
                            div.className = 'mermaid';
                            div.textContent = block.textContent;
                            pre.parentNode.replaceChild(div, pre);
                        }});
                        mermaid.initialize({{ 
                            startOnLoad: true,
                            theme: 'default'
                        }});
                    }}
                }}
            </script>
            <script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js" onload="initMermaid()" onerror="console.error('Mermaid 加载失败')"></script>
        </head>
        <body>
            {html}
        </body>
        </html>
        """

    def set_content(self, content: str) -> None:
        self.source_edit.setPlainText(content)
        html = self._render_html(content)
        self.preview_view.setHtml(html, QUrl("about:blank"))

    def clear(self) -> None:
        self.source_edit.clear()
        self.preview_view.setHtml("")
        self._current_doc = None
