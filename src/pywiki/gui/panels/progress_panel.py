"""
进度监控面板
"""

from typing import Optional
from datetime import datetime

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QProgressBar,
    QLabel,
    QTextEdit,
    QPushButton,
    QGroupBox,
    QFrame,
)
from PyQt6.QtCore import Qt, QTimer


class ProgressPanel(QWidget):
    """Wiki 生成进度监控面板"""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._start_time: Optional[datetime] = None
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        progress_group = QGroupBox("生成进度")
        progress_layout = QVBoxLayout(progress_group)

        self.overall_progress = QProgressBar()
        self.overall_progress.setRange(0, 100)
        self.overall_progress.setValue(0)
        self.overall_progress.setTextVisible(True)
        progress_layout.addWidget(self.overall_progress)

        status_layout = QHBoxLayout()

        self.status_label = QLabel("就绪")
        status_layout.addWidget(self.status_label)

        self.file_label = QLabel("")
        status_layout.addWidget(self.file_label)

        status_layout.addStretch()

        self.time_label = QLabel("耗时: 0s")
        status_layout.addWidget(self.time_label)

        progress_layout.addLayout(status_layout)

        stages_layout = QHBoxLayout()

        self.stage_labels = {}
        stages = [
            ("scan", "代码扫描"),
            ("parse", "结构分析"),
            ("diagram", "图表生成"),
            ("doc", "文档生成"),
            ("sync", "Git 同步"),
        ]

        for stage_id, stage_name in stages:
            stage_frame = QFrame()
            stage_frame.setFrameShape(QFrame.Shape.StyledPanel)
            stage_layout = QVBoxLayout(stage_frame)
            stage_layout.setContentsMargins(4, 4, 4, 4)

            label = QLabel(stage_name)
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            stage_layout.addWidget(label)

            status = QLabel("○")
            status.setAlignment(Qt.AlignmentFlag.AlignCenter)
            status.setStyleSheet("font-size: 16px;")
            stage_layout.addWidget(status)

            stages_layout.addWidget(stage_frame)
            self.stage_labels[stage_id] = status

        progress_layout.addLayout(stages_layout)
        layout.addWidget(progress_group)

        log_group = QGroupBox("日志")
        log_layout = QVBoxLayout(log_group)

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(100)
        self.log_text.setStyleSheet("font-family: Consolas; font-size: 11px;")
        log_layout.addWidget(self.log_text)

        log_buttons = QHBoxLayout()
        self.clear_log_button = QPushButton("清除日志")
        self.clear_log_button.clicked.connect(self.log_text.clear)
        log_buttons.addWidget(self.clear_log_button)
        log_buttons.addStretch()
        log_layout.addLayout(log_buttons)

        layout.addWidget(log_group)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._update_time)

    def start_generation(self) -> None:
        self._start_time = datetime.now()
        self.overall_progress.setValue(0)
        self.status_label.setText("正在生成...")
        self.log_text.clear()
        self._timer.start(1000)

        for stage_id in self.stage_labels:
            self.stage_labels[stage_id].setText("○")
            self.stage_labels[stage_id].setStyleSheet("font-size: 16px; color: gray;")

        self.add_log("INFO", "开始生成 Wiki...")

    def update_progress(self, progress: int, message: str) -> None:
        self.overall_progress.setValue(progress)
        self.status_label.setText(message)

    def set_stage(self, stage_id: str, status: str = "running") -> None:
        if stage_id in self.stage_labels:
            if status == "running":
                self.stage_labels[stage_id].setText("●")
                self.stage_labels[stage_id].setStyleSheet("font-size: 16px; color: blue;")
            elif status == "completed":
                self.stage_labels[stage_id].setText("✓")
                self.stage_labels[stage_id].setStyleSheet("font-size: 16px; color: green;")
            elif status == "error":
                self.stage_labels[stage_id].setText("✗")
                self.stage_labels[stage_id].setStyleSheet("font-size: 16px; color: red;")

    def set_current_file(self, file_path: str) -> None:
        self.file_label.setText(f"当前文件: {file_path}")

    def add_log(self, level: str, message: str) -> None:
        timestamp = datetime.now().strftime("%H:%M:%S")
        color_map = {
            "INFO": "gray",
            "WARN": "orange",
            "ERROR": "red",
            "DEBUG": "blue",
        }
        color = color_map.get(level, "gray")
        self.log_text.append(f'<span style="color: {color};">[{timestamp}] {level}: {message}</span>')

    def complete_generation(self) -> None:
        self._timer.stop()
        self.overall_progress.setValue(100)
        self.status_label.setText("生成完成")
        self.file_label.setText("")

        for stage_id in self.stage_labels:
            if self.stage_labels[stage_id].text() == "●":
                self.set_stage(stage_id, "completed")

        self.add_log("INFO", "Wiki 生成完成")

    def error_generation(self, error: str) -> None:
        self._timer.stop()
        self.status_label.setText("生成失败")
        self.add_log("ERROR", error)

    def _update_time(self) -> None:
        if self._start_time:
            elapsed = (datetime.now() - self._start_time).total_seconds()
            self.time_label.setText(f"耗时: {int(elapsed)}s")
