"""
文档预览面板
"""

from typing import Optional

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
)
from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtWebEngineWidgets import QWebEngineView

import markdown


class PreviewPanel(QWidget):
    """文档预览面板"""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        toolbar = QHBoxLayout()

        self.doc_selector = QComboBox()
        self.doc_selector.setPlaceholderText("选择文档")
        toolbar.addWidget(self.doc_selector)

        self.refresh_button = QPushButton("刷新")
        toolbar.addWidget(self.refresh_button)

        self.export_button = QPushButton("导出")
        toolbar.addWidget(self.export_button)

        toolbar.addStretch()
        layout.addLayout(toolbar)

        self.tab_widget = QTabWidget()

        self.preview_view = QWebEngineView()
        self.tab_widget.addTab(self.preview_view, "预览")

        self.source_edit = QTextEdit()
        self.source_edit.setReadOnly(True)
        self.source_edit.setFontFamily("Consolas")
        self.tab_widget.addTab(self.source_edit, "源码")

        layout.addWidget(self.tab_widget)

    def set_content(self, content: str) -> None:
        self.source_edit.setPlainText(content)

        html = markdown.markdown(
            content,
            extensions=["tables", "fenced_code", "toc"]
        )

        styled_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
                    line-height: 1.6;
                    padding: 20px;
                    max-width: 900px;
                    margin: 0 auto;
                    color: #333;
                }}
                h1, h2, h3, h4, h5, h6 {{
                    margin-top: 24px;
                    margin-bottom: 16px;
                    font-weight: 600;
                    line-height: 1.25;
                }}
                h1 {{ font-size: 2em; border-bottom: 1px solid #eee; padding-bottom: .3em; }}
                h2 {{ font-size: 1.5em; border-bottom: 1px solid #eee; padding-bottom: .3em; }}
                h3 {{ font-size: 1.25em; }}
                code {{
                    padding: 0.2em 0.4em;
                    margin: 0;
                    font-size: 85%;
                    background-color: rgba(27,31,35,0.05);
                    border-radius: 3px;
                    font-family: Consolas, Monaco, 'Courier New', monospace;
                }}
                pre {{
                    padding: 16px;
                    overflow: auto;
                    font-size: 85%;
                    line-height: 1.45;
                    background-color: #f6f8fa;
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
                    border: 1px solid #dfe2e5;
                }}
                table th {{
                    font-weight: 600;
                    background-color: #f6f8fa;
                }}
                table tr:nth-child(2n) {{
                    background-color: #f6f8fa;
                }}
                blockquote {{
                    padding: 0 1em;
                    color: #6a737d;
                    border-left: 0.25em solid #dfe2e5;
                    margin: 0 0 16px 0;
                }}
            </style>
            <script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>
            <script>
                mermaid.initialize({{ startOnLoad: true }});
            </script>
        </head>
        <body>
            {html}
        </body>
        </html>
        """

        self.preview_view.setHtml(styled_html, QUrl("about:blank"))

    def clear(self) -> None:
        self.source_edit.clear()
        self.preview_view.setHtml("")
