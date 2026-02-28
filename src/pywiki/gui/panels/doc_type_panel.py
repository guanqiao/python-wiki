"""
文档类型选择面板
"""

from typing import Optional
from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QCheckBox,
    QPushButton,
    QLabel,
    QFrame,
    QScrollArea,
    QGroupBox,
)
from PyQt6.QtCore import Qt, pyqtSignal

from pywiki.generators.docs.base import DocType
from pywiki.config.models import Language


DOC_TYPE_INFO: dict[DocType, tuple[str, str]] = {
    DocType.OVERVIEW: ("概述", "项目概述文档，包含项目介绍、功能特性等"),
    DocType.TECH_STACK: ("技术栈", "项目使用的技术栈分析"),
    DocType.API: ("API 文档", "API 接口文档"),
    DocType.ARCHITECTURE: ("架构文档", "系统架构设计文档"),
    DocType.MODULE: ("模块文档", "各模块详细文档"),
    DocType.DATABASE: ("数据库文档", "数据库 Schema 文档"),
    DocType.CONFIGURATION: ("配置文档", "配置项说明文档"),
    DocType.DEVELOPMENT: ("开发文档", "开发指南文档"),
    DocType.DEPENDENCIES: ("依赖文档", "依赖关系文档"),
    DocType.DEPLOYMENT: ("部署文档", "部署配置和运维文档"),
    DocType.TSD: ("技术设计决策", "技术设计决策记录"),
    DocType.TECHNICAL_DESIGN_SPEC: ("技术设计规范", "综合性的技术设计规范文档，汇总所有技术文档"),
}


class DocTypePanel(QWidget):
    """文档类型选择面板"""

    generate_requested = pyqtSignal(list)
    generate_all_requested = pyqtSignal()
    language_changed = pyqtSignal(list)

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._checkboxes: dict[DocType, QCheckBox] = {}
        self._language_checkboxes: dict[Language, QCheckBox] = {}
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        title_label = QLabel("文档类型")
        title_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(title_label)

        language_layout = QHBoxLayout()
        language_label = QLabel("文档语言:")
        language_label.setStyleSheet("font-weight: bold;")
        language_layout.addWidget(language_label)
        
        self.zh_checkbox = QCheckBox("中文")
        self.zh_checkbox.setChecked(True)
        self.zh_checkbox.stateChanged.connect(self._on_language_changed)
        self.zh_checkbox.setStyleSheet("font-weight: normal; margin-left: 10px;")
        language_layout.addWidget(self.zh_checkbox)
        self._language_checkboxes[Language.ZH] = self.zh_checkbox
        
        self.en_checkbox = QCheckBox("English")
        self.en_checkbox.setChecked(True)
        self.en_checkbox.stateChanged.connect(self._on_language_changed)
        self.en_checkbox.setStyleSheet("font-weight: normal; margin-left: 5px;")
        language_layout.addWidget(self.en_checkbox)
        self._language_checkboxes[Language.EN] = self.en_checkbox
        
        language_layout.addStretch()
        layout.addLayout(language_layout)

        select_layout = QHBoxLayout()
        
        self.select_all_btn = QPushButton("全选")
        self.select_all_btn.clicked.connect(self._select_all)
        select_layout.addWidget(self.select_all_btn)

        self.deselect_all_btn = QPushButton("取消全选")
        self.deselect_all_btn.clicked.connect(self._deselect_all)
        select_layout.addWidget(self.deselect_all_btn)

        select_layout.addStretch()
        layout.addLayout(select_layout)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)

        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        scroll_layout.setContentsMargins(0, 0, 0, 0)
        scroll_layout.setSpacing(4)

        for doc_type in DocType:
            info = DOC_TYPE_INFO.get(doc_type, (doc_type.value, ""))
            checkbox = QCheckBox(f"{info[0]} ({doc_type.value})")
            checkbox.setToolTip(info[1])
            checkbox.setChecked(True)
            self._checkboxes[doc_type] = checkbox
            scroll_layout.addWidget(checkbox)

        scroll_layout.addStretch()
        scroll_area.setWidget(scroll_widget)
        layout.addWidget(scroll_area)

        button_layout = QVBoxLayout()
        button_layout.setSpacing(8)

        self.generate_all_btn = QPushButton("🚀 一键生成全部文档")
        self.generate_all_btn.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                padding: 10px;
                font-size: 14px;
                font-weight: bold;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
        """)
        self.generate_all_btn.clicked.connect(self._on_generate_all)
        button_layout.addWidget(self.generate_all_btn)

        self.generate_selected_btn = QPushButton("📝 生成选中文档")
        self.generate_selected_btn.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                padding: 8px;
                font-size: 13px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #219a52;
            }
        """)
        self.generate_selected_btn.clicked.connect(self._on_generate_selected)
        button_layout.addWidget(self.generate_selected_btn)

        layout.addLayout(button_layout)

    def _select_all(self) -> None:
        for checkbox in self._checkboxes.values():
            checkbox.setChecked(True)

    def _deselect_all(self) -> None:
        for checkbox in self._checkboxes.values():
            checkbox.setChecked(False)

    def _on_generate_all(self) -> None:
        self.generate_all_requested.emit()

    def _on_generate_selected(self) -> None:
        selected = self.get_selected_doc_types()
        if selected:
            self.generate_requested.emit(selected)

    def get_selected_doc_types(self) -> list[DocType]:
        return [
            doc_type for doc_type, checkbox in self._checkboxes.items()
            if checkbox.isChecked()
        ]

    def set_selected_doc_types(self, doc_types: list[DocType]) -> None:
        for doc_type, checkbox in self._checkboxes.items():
            checkbox.setChecked(doc_type in doc_types)

    def set_all_selected(self, selected: bool) -> None:
        for checkbox in self._checkboxes.values():
            checkbox.setChecked(selected)

    def _on_language_changed(self, state: int) -> None:
        """语言选择变更处理"""
        languages = self.get_selected_languages()
        self.language_changed.emit(languages)

    def get_selected_languages(self) -> list[Language]:
        """获取选中的语言列表"""
        languages = []
        for language, checkbox in self._language_checkboxes.items():
            if checkbox.isChecked():
                languages.append(language)
        if not languages:
            languages.append(Language.ZH)
        return languages

    def get_selected_language(self) -> Language:
        """获取首选语言（兼容旧接口）"""
        languages = self.get_selected_languages()
        return languages[0] if languages else Language.ZH

    def set_languages(self, languages: list[Language]) -> None:
        """设置选中的语言"""
        for language, checkbox in self._language_checkboxes.items():
            checkbox.setChecked(language in languages)
