"""
Wiki 日志系统
"""

import logging
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional


class LogLevel(str, Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class WikiLogger:
    """Wiki 日志记录器"""

    def __init__(
        self,
        name: str = "pywiki",
        log_file: Optional[Path] = None,
        level: LogLevel = LogLevel.INFO,
    ):
        self.name = name
        self.log_file = log_file
        self.level = level

        self._logger = logging.getLogger(name)
        self._logger.setLevel(getattr(logging, level.value))

        self._setup_handlers()

    def _setup_handlers(self) -> None:
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )

        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        self._logger.addHandler(console_handler)

        if self.log_file:
            self.log_file.parent.mkdir(parents=True, exist_ok=True)
            file_handler = logging.FileHandler(self.log_file, encoding="utf-8")
            file_handler.setFormatter(formatter)
            self._logger.addHandler(file_handler)

    def debug(self, message: str) -> None:
        self._logger.debug(message)

    def info(self, message: str) -> None:
        self._logger.info(message)

    def warning(self, message: str) -> None:
        self._logger.warning(message)

    def error(self, message: str) -> None:
        self._logger.error(message)

    def critical(self, message: str) -> None:
        self._logger.critical(message)

    def exception(self, message: str) -> None:
        self._logger.exception(message)

    def log_generation_start(self, project_name: str) -> None:
        self.info(f"开始生成 Wiki: {project_name}")

    def log_generation_complete(
        self,
        project_name: str,
        duration: float,
        files_processed: int,
    ) -> None:
        self.info(
            f"Wiki 生成完成: {project_name} - "
            f"耗时: {duration:.2f}s, 处理文件: {files_processed}"
        )

    def log_generation_error(self, project_name: str, error: str) -> None:
        self.error(f"Wiki 生成失败: {project_name} - {error}")

    def log_file_processed(self, file_path: str, success: bool) -> None:
        if success:
            self.debug(f"文件处理成功: {file_path}")
        else:
            self.warning(f"文件处理失败: {file_path}")

    def log_diagram_generated(self, diagram_type: str, output_path: str) -> None:
        self.info(f"图表生成: {diagram_type} -> {output_path}")

    def log_sync_start(self, project_name: str) -> None:
        self.info(f"开始同步 Git: {project_name}")

    def log_sync_complete(self, project_name: str, commits: int) -> None:
        self.info(f"Git 同步完成: {project_name} - 提交数: {commits}")


logger = WikiLogger()
