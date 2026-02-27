"""
新建项目对话框
"""

from pathlib import Path
from typing import Optional

from pydantic import SecretStr

from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QFormLayout,
    QLineEdit,
    QPushButton,
    QFileDialog,
    QComboBox,
    QHBoxLayout,
    QWidget,
)
from PyQt6.QtCore import Qt

from pywiki.config.models import ProjectConfig, WikiConfig, LLMConfig, Language


class NewProjectDialog(QDialog):
    """新建项目对话框"""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setWindowTitle("新建项目")
        self.setMinimumWidth(500)
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)

        form_layout = QFormLayout()

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("项目名称")
        form_layout.addRow("项目名称:", self.name_edit)

        path_layout = QHBoxLayout()
        self.path_edit = QLineEdit()
        self.path_edit.setPlaceholderText("项目路径")
        self.path_button = QPushButton("浏览...")
        self.path_button.clicked.connect(self._browse_path)
        path_layout.addWidget(self.path_edit)
        path_layout.addWidget(self.path_button)
        form_layout.addRow("项目路径:", path_layout)

        self.description_edit = QLineEdit()
        self.description_edit.setPlaceholderText("项目描述 (可选)")
        form_layout.addRow("描述:", self.description_edit)

        self.language_combo = QComboBox()
        for lang in Language:
            self.language_combo.addItem(lang.value, lang)
        form_layout.addRow("文档语言:", self.language_combo)

        layout.addLayout(form_layout)

        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.cancel_button = QPushButton("取消")
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_button)

        self.create_button = QPushButton("创建")
        self.create_button.clicked.connect(self.accept)
        self.create_button.setDefault(True)
        button_layout.addWidget(self.create_button)

        layout.addLayout(button_layout)

    def _browse_path(self) -> None:
        folder = QFileDialog.getExistingDirectory(
            self,
            "选择项目目录",
            "",
            QFileDialog.Option.ShowDirsOnly
        )
        if folder:
            self.path_edit.setText(folder)

    def get_project_config(self) -> Optional[ProjectConfig]:
        name = self.name_edit.text().strip()
        path = self.path_edit.text().strip()

        if not name or not path:
            return None

        return ProjectConfig(
            name=name,
            path=Path(path),
            description=self.description_edit.text().strip() or None,
            wiki=WikiConfig(
                language=self.language_combo.currentData(),
            ),
            llm=LLMConfig(api_key=SecretStr("")),
        )
