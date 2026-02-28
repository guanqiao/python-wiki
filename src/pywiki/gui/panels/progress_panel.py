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
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal


class ProgressPanel(QWidget):
    """Wiki 生成进度监控面板"""

    cancel_requested = pyqtSignal()
    pause_requested = pyqtSignal()
    resume_requested = pyqtSignal()

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._start_time: Optional[datetime] = None
        self._is_paused: bool = False
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        progress_group = QGroupBox("生成进度")
        progress_layout = QVBoxLayout(progress_group)

        progress_header = QHBoxLayout()
        
        self.overall_progress = QProgressBar()
        self.overall_progress.setRange(0, 100)
        self.overall_progress.setValue(0)
        self.overall_progress.setTextVisible(True)
        self.overall_progress.setStyleSheet("""
            QProgressBar {
                border: 1px solid #dee2e6;
                border-radius: 4px;
                text-align: center;
                background-color: #e9ecef;
            }
            QProgressBar::chunk {
                background-color: #28a745;
                border-radius: 3px;
            }
        """)
        progress_header.addWidget(self.overall_progress, 1)
        
        self.pause_button = QPushButton("暂停")
        self.pause_button.setStyleSheet("""
            QPushButton {
                background-color: #ffc107;
                color: #212529;
                padding: 4px 12px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #e0a800;
            }
        """)
        self.pause_button.clicked.connect(self._on_pause_clicked)
        self.pause_button.setVisible(False)
        progress_header.addWidget(self.pause_button)
        
        self.terminate_button = QPushButton("终止")
        self.terminate_button.setStyleSheet("""
            QPushButton {
                background-color: #dc3545;
                color: white;
                padding: 4px 12px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #c82333;
            }
        """)
        self.terminate_button.clicked.connect(self.cancel_requested.emit)
        self.terminate_button.setVisible(False)
        progress_header.addWidget(self.terminate_button)
        
        progress_layout.addLayout(progress_header)

        status_layout = QHBoxLayout()

        self.status_label = QLabel("就绪")
        self.status_label.setStyleSheet("font-weight: bold;")
        status_layout.addWidget(self.status_label)

        self.file_label = QLabel("")
        self.file_label.setStyleSheet("color: #6c757d;")
        status_layout.addWidget(self.file_label)

        status_layout.addStretch()

        self.time_label = QLabel("耗时: 0s")
        self.time_label.setStyleSheet("color: #6c757d;")
        status_layout.addWidget(self.time_label)

        progress_layout.addLayout(status_layout)
        layout.addWidget(progress_group)

        log_group = QGroupBox("日志")
        log_layout = QVBoxLayout(log_group)

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMinimumHeight(150)
        self.log_text.setStyleSheet("""
            QTextEdit {
                font-family: Consolas, Monaco, 'Courier New', monospace;
                font-size: 11px;
                background-color: #212529;
                color: #f8f9fa;
                border: 1px solid #343a40;
                border-radius: 4px;
            }
        """)
        log_layout.addWidget(self.log_text)

        log_buttons = QHBoxLayout()
        self.clear_log_button = QPushButton("清除日志")
        self.clear_log_button.clicked.connect(self.log_text.clear)
        log_buttons.addWidget(self.clear_log_button)
        log_buttons.addStretch()
        log_layout.addLayout(log_buttons)

        layout.addWidget(log_group, 1)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._update_time)

    def start_generation(self) -> None:
        self._start_time = datetime.now()
        self._is_paused = False
        self.overall_progress.setValue(0)
        self.status_label.setText("正在生成...")
        self.log_text.clear()
        self._timer.start(1000)
        self.pause_button.setVisible(True)
        self.pause_button.setText("暂停")
        self.pause_button.setStyleSheet("""
            QPushButton {
                background-color: #ffc107;
                color: #212529;
                padding: 4px 12px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #e0a800;
            }
        """)
        self.terminate_button.setVisible(True)

        self.add_log("INFO", "开始生成 Wiki...")

    def _on_pause_clicked(self) -> None:
        if self._is_paused:
            self._is_paused = False
            self.pause_button.setText("暂停")
            self.pause_button.setStyleSheet("""
                QPushButton {
                    background-color: #ffc107;
                    color: #212529;
                    padding: 4px 12px;
                    border-radius: 4px;
                }
                QPushButton:hover {
                    background-color: #e0a800;
                }
            """)
            self.status_label.setText("正在生成...")
            self.overall_progress.setStyleSheet("""
                QProgressBar {
                    border: 1px solid #dee2e6;
                    border-radius: 4px;
                    text-align: center;
                    background-color: #e9ecef;
                }
                QProgressBar::chunk {
                    background-color: #28a745;
                    border-radius: 3px;
                }
            """)
            self.resume_requested.emit()
        else:
            self._is_paused = True
            self.pause_button.setText("继续")
            self.pause_button.setStyleSheet("""
                QPushButton {
                    background-color: #28a745;
                    color: white;
                    padding: 4px 12px;
                    border-radius: 4px;
                }
                QPushButton:hover {
                    background-color: #218838;
                }
            """)
            self.status_label.setText("已暂停")
            self.overall_progress.setStyleSheet("""
                QProgressBar {
                    border: 1px solid #dee2e6;
                    border-radius: 4px;
                    text-align: center;
                    background-color: #e9ecef;
                }
                QProgressBar::chunk {
                    background-color: #ffc107;
                    border-radius: 3px;
                }
            """)
            self.pause_requested.emit()
    
    def set_paused_state(self, paused: bool) -> None:
        self._is_paused = paused
        if paused:
            self.pause_button.setText("继续")
            self.pause_button.setStyleSheet("""
                QPushButton {
                    background-color: #28a745;
                    color: white;
                    padding: 4px 12px;
                    border-radius: 4px;
                }
                QPushButton:hover {
                    background-color: #218838;
                }
            """)
            self.status_label.setText("已暂停")
            self.overall_progress.setStyleSheet("""
                QProgressBar {
                    border: 1px solid #dee2e6;
                    border-radius: 4px;
                    text-align: center;
                    background-color: #e9ecef;
                }
                QProgressBar::chunk {
                    background-color: #ffc107;
                    border-radius: 3px;
                }
            """)
        else:
            self.pause_button.setText("暂停")
            self.pause_button.setStyleSheet("""
                QPushButton {
                    background-color: #ffc107;
                    color: #212529;
                    padding: 4px 12px;
                    border-radius: 4px;
                }
                QPushButton:hover {
                    background-color: #e0a800;
                }
            """)
            self.status_label.setText("正在生成...")
            self.overall_progress.setStyleSheet("""
                QProgressBar {
                    border: 1px solid #dee2e6;
                    border-radius: 4px;
                    text-align: center;
                    background-color: #e9ecef;
                }
                QProgressBar::chunk {
                    background-color: #28a745;
                    border-radius: 3px;
                }
            """)

    def update_progress(self, progress: int, message: str) -> None:
        self.overall_progress.setValue(progress)
        self.status_label.setText(message)

    def set_stage(self, stage_id: str, status: str = "running") -> None:
        pass

    def set_current_file(self, file_path: str) -> None:
        self.file_label.setText(f"当前文件: {file_path}")

    def add_log(self, level: str, message: str) -> None:
        timestamp = datetime.now().strftime("%H:%M:%S")
        color_map = {
            "INFO": "#17a2b8",
            "WARN": "#ffc107",
            "ERROR": "#dc3545",
            "DEBUG": "#6c757d",
            "SUCCESS": "#28a745",
        }
        color = color_map.get(level, "#f8f9fa")
        self.log_text.append(
            f'<span style="color: {color};">[{timestamp}] {level}: {message}</span>'
        )

    def complete_generation(self) -> None:
        self._timer.stop()
        self._is_paused = False
        self.overall_progress.setValue(100)
        self.status_label.setText("✅ 生成完成")
        self.file_label.setText("")
        self.pause_button.setVisible(False)
        self.terminate_button.setVisible(False)
        self.overall_progress.setStyleSheet("""
            QProgressBar {
                border: 1px solid #dee2e6;
                border-radius: 4px;
                text-align: center;
                background-color: #e9ecef;
            }
            QProgressBar::chunk {
                background-color: #28a745;
                border-radius: 3px;
            }
        """)

        self.add_log("SUCCESS", "Wiki 生成完成")

    def error_generation(self, error: str) -> None:
        self._timer.stop()
        self._is_paused = False
        self.status_label.setText("❌ 生成失败")
        self.pause_button.setVisible(False)
        self.terminate_button.setVisible(False)
        self.overall_progress.setStyleSheet("""
            QProgressBar {
                border: 1px solid #dee2e6;
                border-radius: 4px;
                text-align: center;
                background-color: #e9ecef;
            }
            QProgressBar::chunk {
                background-color: #28a745;
                border-radius: 3px;
            }
        """)
        self.add_log("ERROR", error)

    def _update_time(self) -> None:
        if self._start_time:
            elapsed = (datetime.now() - self._start_time).total_seconds()
            if elapsed >= 60:
                minutes = int(elapsed // 60)
                seconds = int(elapsed % 60)
                self.time_label.setText(f"耗时: {minutes}m {seconds}s")
            else:
                self.time_label.setText(f"耗时: {int(elapsed)}s")
